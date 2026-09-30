"""Test configuration.

Integration tests run against the docker-compose ``database`` service:

    docker compose up -d database
    cd features_api/runtime && python -m pytest

Override the connection with the standard ``POSTGRES_*`` variables (for example
``POSTGRES_PORT=55432``). Integration tests are skipped when the database is
unreachable.
"""

import asyncio
import logging
import os

import pytest

os.environ.setdefault("POSTGRES_USER", "username")
os.environ.setdefault("POSTGRES_PASS", "password")
os.environ.setdefault("POSTGRES_DBNAME", "postgis")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POWERTOOLS_TRACE_DISABLED", "true")
os.environ.setdefault("POWERTOOLS_METRICS_NAMESPACE", "veda-backend")


def database_url() -> str:
    """DSN built from the POSTGRES_* variables."""
    e = os.environ
    return (
        f"postgresql://{e['POSTGRES_USER']}:{e['POSTGRES_PASS']}"
        f"@{e['POSTGRES_HOST']}:{e['POSTGRES_PORT']}/{e['POSTGRES_DBNAME']}"
    )


def run_sql(*statements: str) -> None:
    """Run SQL statements on a fresh connection."""
    import asyncpg

    async def _run():
        conn = await asyncpg.connect(database_url())
        try:
            for statement in statements:
                await conn.execute(statement)
        finally:
            await conn.close()

    asyncio.run(_run())


def fetch_sql(query: str) -> list:
    """Fetch rows on a fresh connection."""
    import asyncpg

    async def _fetch():
        conn = await asyncpg.connect(database_url())
        try:
            return await conn.fetch(query)
        finally:
            await conn.close()

    return asyncio.run(_fetch())


@pytest.fixture(scope="session")
def database():
    """Skip when the test database is unreachable."""
    try:
        run_sql("SELECT 1")
    except Exception as e:
        pytest.skip(f"test database unreachable at {database_url()}: {e}")


@pytest.fixture
def catalog_logs(caplog):
    """Capture records from the powertools logger (which does not propagate)."""
    from src.monitoring import logger

    powertools_logger = logging.getLogger(logger.service)
    powertools_logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger=logger.service)
    yield caplog
    powertools_logger.removeHandler(caplog.handler)
