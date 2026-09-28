"""CORS headers through the application's full middleware stack."""

import os
from datetime import datetime

import pytest

# The app builds its database settings at import; nothing connects until the
# lifespan runs, which a bare TestClient never starts.
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")

from starlette.testclient import TestClient  # noqa: E402

from src.app import app  # noqa: E402
from src.config import FeaturesAPISettings  # noqa: E402


@pytest.fixture
def client():
    """A client whose catalog is fresh, so no refresh reaches the database."""
    app.state.collection_catalog = {
        "collections": {},
        "last_updated": datetime.now(),
    }
    return TestClient(app)


@pytest.mark.parametrize(
    "origin", ["http://localhost:8889", "https://dashboard.example.com"]
)
def test_every_origin_gets_the_same_wildcard(client, origin):
    # A CDN caches one copy per URL. If the header named the requesting
    # origin, the next site to hit that copy would be refused.
    response = client.get("/healthz", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers


def test_preflight_allows_any_origin(client):
    response = client.options(
        "/healthz",
        headers={
            "Origin": "https://dashboard.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_cors_origins_reads_a_comma_separated_list():
    settings = FeaturesAPISettings(cors_origins="https://a.example, https://b.example")

    assert settings.cors_origin_list == ["https://a.example", "https://b.example"]


def test_cors_origins_defaults_to_any_origin():
    assert FeaturesAPISettings().cors_origin_list == ["*"]
