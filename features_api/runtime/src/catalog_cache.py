"""Persisted tipg collection catalog.

tipg rebuilds its collection catalog by introspecting every table on each
container start. That takes about 5 s for ~3,000 tables. This module stores the
finished ``PgCollection`` models in ``tipg_cache.catalog`` so new containers can
load them with one ``SELECT``. ``/refresh`` is the only path that introspects.
"""

import datetime
from typing import Any, Dict, Optional

import asyncpg
from fastapi import FastAPI
from pydantic import ValidationError
from src.monitoring import logger
from tipg import __version__ as tipg_version
from tipg.collections import Catalog, PgCollection, register_collection_catalog
from tipg.settings import DatabaseSettings

CREATE_CACHE_SQL = """
CREATE SCHEMA IF NOT EXISTS tipg_cache;
CREATE TABLE IF NOT EXISTS tipg_cache.catalog (
    collection_id text PRIMARY KEY,
    built_at      timestamptz NOT NULL,
    tipg_version  text NOT NULL,
    meta          jsonb NOT NULL
);
"""

# Arbitrary fixed key for pg_advisory_xact_lock, held while /refresh writes the cache.
CACHE_WRITE_LOCK_ID = 7_395_040_231_126_802

SELECT_CACHE_SQL = "SELECT collection_id, tipg_version, meta FROM tipg_cache.catalog"

INSERT_CACHE_SQL = """
INSERT INTO tipg_cache.catalog (collection_id, built_at, tipg_version, meta)
VALUES ($1, $2, $3, $4::text::jsonb)
"""


async def _read_cached_collections(app: FastAPI) -> Dict[str, PgCollection]:
    """Return the cached collections, or raise LookupError with the reason."""
    try:
        async with app.state.pool.acquire() as conn:
            rows = await conn.fetch(SELECT_CACHE_SQL)
    except asyncpg.PostgresError as e:
        # Missing table, missing privilege, or a table whose shape has drifted:
        # any of these must not fail Lambda init, so fall back to the live build.
        raise LookupError(f"cache table unreadable ({type(e).__name__}: {e})") from e

    if not rows:
        raise LookupError("cache table is empty")

    versions = {row["tipg_version"] for row in rows}
    if versions != {tipg_version}:
        raise LookupError(
            f"cache built with tipg {sorted(versions)}, running tipg {tipg_version}"
        )

    try:
        return {
            row["collection_id"]: PgCollection.model_validate(row["meta"])
            for row in rows
        }
    except ValidationError as e:
        raise LookupError(f"cache rows failed validation ({e})") from e


async def load_collection_catalog(
    app: FastAPI,
    db_settings: Optional[DatabaseSettings] = None,
) -> None:
    """Load the collection catalog from the cache, else build it live.

    Same signature as ``tipg.collections.register_collection_catalog`` so it can
    be used at startup and as ``CatalogUpdateMiddleware``'s ``func``. It never
    writes the cache; only ``/refresh`` does.
    """
    try:
        collections = await _read_cached_collections(app)
    except LookupError as e:
        logger.warning(f"Collection catalog cache not used, building live: {e}")
        await register_collection_catalog(app, db_settings=db_settings)
        source = "live"
    else:
        app.state.collection_catalog = Catalog(
            collections=collections,
            last_updated=datetime.datetime.now(),
        )
        source = "cache"

    count = len(app.state.collection_catalog["collections"])
    logger.info(f"Collection catalog loaded from {source}: {count} collections")


async def write_collection_catalog(app: FastAPI) -> Dict[str, Any]:
    """Replace the cache with the catalog currently in ``app.state``."""
    collections = app.state.collection_catalog["collections"]
    built_at = datetime.datetime.now(datetime.timezone.utc)
    records = [
        (
            collection_id,
            built_at,
            tipg_version,
            # Sent as text: tipg's jsonb codec encodes to bytes, which asyncpg
            # rejects for parameters. Same JSON as model_dump(mode="json").
            collection.model_dump_json(by_alias=True),
        )
        for collection_id, collection in collections.items()
    ]

    async with app.state.pool.acquire() as conn:
        async with conn.transaction():
            # Serialize overlapping refreshes: two DELETE+INSERT writers would
            # collide on the primary key, and the first CREATE SCHEMA could race.
            await conn.execute(
                "SELECT pg_advisory_xact_lock($1)", CACHE_WRITE_LOCK_ID
            )
            await conn.execute(CREATE_CACHE_SQL)
            # DELETE, not TRUNCATE: TRUNCATE holds ACCESS EXCLUSIVE until commit,
            # which blocks cold-start reads; DELETE lets them see the old rows.
            await conn.execute("DELETE FROM tipg_cache.catalog")
            await conn.executemany(INSERT_CACHE_SQL, records)

    return {
        "collections": len(records),
        "built_at": built_at.isoformat(),
        "tipg_version": tipg_version,
    }
