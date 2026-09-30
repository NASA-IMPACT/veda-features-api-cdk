"""Tests for the persisted tipg collection catalog.

The integration tests drop tables and the tipg_cache schema in whatever database
POSTGRES_* points at; run them only against the docker-compose database.
"""

import asyncio

import pytest
from conftest import database_url, fetch_sql, run_sql
from fastapi.testclient import TestClient
from tipg import __version__ as tipg_version
from tipg.collections import PgCollection

# Schema-qualified: the pgstac image puts ``pgstac`` first on the search_path.
TABLE_A = ID_A = "public.catalog_cache_test_a"
TABLE_B = ID_B = "public.catalog_cache_test_b"


def test_pgcollection_round_trip():
    """A dumped PgCollection validates back to an equal model."""
    ts = {"name": "observed", "type": "timestamptz"}
    geom = {
        "name": "geom",
        "type": "geometry",
        "geometry_type": "POINT",
        "srid": 4326,
        "bounds": [-180, -90, 180, 90],
    }
    value = {"name": "value", "type": "double precision"}
    collection = PgCollection(
        type="Table",
        id="public.no_pk",
        table="no_pk",
        schema="public",
        description="no primary key",
        table_columns=[ts, geom, value],
        properties=[ts, geom, value],
        id_column=None,
        datetime_column=ts,
        geometry_column=geom,
    )

    meta = collection.model_dump(by_alias=True, mode="json")
    assert meta["schema"] == "public"

    restored = PgCollection.model_validate(meta)
    assert restored == collection
    assert restored.dbschema == "public"
    assert restored.id_column is None
    assert restored._qualified_name == '"public"."no_pk"'
    assert restored.datetime_column.is_datetime
    assert restored.geometry_column.is_geometry


def _create_tables():
    run_sql(
        f"DROP TABLE IF EXISTS {TABLE_A}, {TABLE_B}",
        "DROP SCHEMA IF EXISTS tipg_cache CASCADE",
        f"CREATE TABLE {TABLE_A} (id int PRIMARY KEY, geom geometry(Point, 4326))",
        f"CREATE TABLE {TABLE_B} (observed timestamptz, geom geometry(Point, 4326))",
    )


def _test_ids(ids) -> set:
    """Only this module's tables (tipg also lists PostGIS functions)."""
    return {i for i in ids if i in (ID_A, ID_B)}


def _collection_ids(client: TestClient) -> set:
    return _test_ids(client.app.state.collection_catalog["collections"])


@pytest.fixture
def app(database):
    """The API app, with test tables created and cleaned up."""
    from src.app import app

    _create_tables()
    yield app
    run_sql(
        f"DROP TABLE IF EXISTS {TABLE_A}, {TABLE_B}",
        "DROP SCHEMA IF EXISTS tipg_cache CASCADE",
    )


def _refresh(app) -> dict:
    with TestClient(app) as client:
        response = client.get("/refresh")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        return response.json()


def test_refresh_writes_cache_and_init_reads_it(app, catalog_logs):
    """/refresh fills the cache; a restarted app serves it without introspecting."""
    body = _refresh(app)
    assert body["tipg_version"] == tipg_version
    assert body["built_at"]

    rows = fetch_sql("SELECT collection_id, tipg_version FROM tipg_cache.catalog")
    assert body["collections"] == len(rows)
    assert _test_ids(r["collection_id"] for r in rows) == {ID_A, ID_B}
    assert {r["tipg_version"] for r in rows} == {tipg_version}
    cached = len(rows)

    run_sql(f"DROP TABLE {TABLE_B}")
    catalog_logs.clear()

    with TestClient(app) as client:
        assert _collection_ids(client) == {ID_A, ID_B}
        response = client.get("/collections")
        assert response.status_code == 200
        listed = _test_ids(c["id"] for c in response.json()["collections"])
        assert listed == {ID_A, ID_B}

    assert (
        f"Collection catalog loaded from cache: {cached} collections"
        in catalog_logs.text
    )


def test_missing_cache_table_falls_back_to_live(app, catalog_logs):
    """Without the cache table, init builds the catalog live."""
    _refresh(app)
    run_sql("DROP TABLE tipg_cache.catalog", f"DROP TABLE {TABLE_B}")
    catalog_logs.clear()

    with TestClient(app) as client:
        assert _collection_ids(client) == {ID_A}

    assert "UndefinedTableError" in catalog_logs.text
    assert "Collection catalog loaded from live" in catalog_logs.text


def test_version_mismatch_falls_back_to_live(app, catalog_logs):
    """A cache row from another tipg version sends init to the live build."""
    _refresh(app)
    run_sql(
        f"UPDATE tipg_cache.catalog SET tipg_version = '0.0.0' "
        f"WHERE collection_id = '{ID_A}'",
        f"DROP TABLE {TABLE_B}",
    )
    catalog_logs.clear()

    with TestClient(app) as client:
        assert _collection_ids(client) == {ID_A}

    assert "0.0.0" in catalog_logs.text
    assert "Collection catalog loaded from live" in catalog_logs.text


def test_unreadable_cache_shape_falls_back_to_live(app, catalog_logs):
    """Any Postgres error on the cache SELECT falls back rather than failing init."""
    _refresh(app)
    run_sql(
        "ALTER TABLE tipg_cache.catalog DROP COLUMN tipg_version",
        f"DROP TABLE {TABLE_B}",
    )
    catalog_logs.clear()

    with TestClient(app) as client:
        assert _collection_ids(client) == {ID_A}

    assert "UndefinedColumnError" in catalog_logs.text
    assert "Collection catalog loaded from live" in catalog_logs.text


def test_concurrent_writes_both_succeed(app):
    """Overlapping refreshes serialize on the advisory lock; last commit wins."""
    from fastapi import FastAPI
    from src.app import db_settings
    from src.catalog_cache import write_collection_catalog
    from tipg.collections import register_collection_catalog
    from tipg.database import close_db_connection, connect_to_db
    from tipg.settings import PostgresSettings

    async def _run():
        writer = FastAPI()
        await connect_to_db(
            writer,
            schemas=["public"],
            # Two warm connections so the writes actually overlap.
            settings=PostgresSettings(database_url=database_url(), db_min_conn_size=2),
        )
        try:
            await register_collection_catalog(writer, db_settings=db_settings)
            results = []
            # First pair races on the first-ever CREATE SCHEMA; second pair
            # overlaps DELETE+INSERT on an existing table.
            for _ in range(2):
                results += await asyncio.gather(
                    write_collection_catalog(writer),
                    write_collection_catalog(writer),
                )
            return results, len(writer.state.collection_catalog["collections"])
        finally:
            await close_db_connection(writer)

    results, expected = asyncio.run(_run())

    assert [r["collections"] for r in results] == [expected] * 4
    (row,) = fetch_sql("SELECT count(*) AS n FROM tipg_cache.catalog")
    assert row["n"] == expected
    assert _test_ids(
        r["collection_id"] for r in fetch_sql("SELECT collection_id FROM tipg_cache.catalog")
    ) == {ID_A, ID_B}
