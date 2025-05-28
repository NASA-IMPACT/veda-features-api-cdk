"""feature services fastapi"""
from contextlib import asynccontextmanager

from src.config import FeaturesAPISettings as APISettings
from tipg import __version__ as tipg_version
from tipg.collections import register_collection_catalog
from tipg.database import close_db_connection, connect_to_db
from tipg.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from tipg.factory import Endpoints
from tipg.middleware import CacheControlMiddleware, CatalogUpdateMiddleware
from tipg.settings import CustomSQLSettings, DatabaseSettings

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from starlette_cramjam.middleware import CompressionMiddleware

from src.monitoring import LoggerRouteHandler

settings = APISettings()
postgres_settings = settings.load_postgres_settings()
db_settings = DatabaseSettings(
    datetime_extent=False,
    spatial_extent=False
)
custom_sql_settings = CustomSQLSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """reload catalogs"""
    await connect_to_db(
        app,
        schemas=[
            "public",
        ],
        settings=postgres_settings,
    )

    # Register Collection Catalog
    await register_collection_catalog(
        app,
        db_settings=db_settings,
    )

    yield

    # Close the Connection Pool
    await close_db_connection(app)


app = FastAPI(
    title=settings.name,
    version=tipg_version,
    openapi_url="/api",
    docs_url="/docs",
    lifespan=lifespan,
    root_path=settings.root_path,
)

ogc_api = Endpoints(
    title=settings.name,
    with_tiles_viewer=settings.add_tiles_viewer,
)
app.include_router(ogc_api.router)
app.router.route_class = LoggerRouteHandler

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=[settings.cors_origins],
)
app.add_middleware(CacheControlMiddleware, cachecontrol=settings.cachecontrol)
app.add_middleware(CompressionMiddleware)
app.add_middleware(
    CatalogUpdateMiddleware,
    func=register_collection_catalog,
    ttl=settings.catalog_ttl,
    db_settings=db_settings,
)

add_exception_handlers(app, DEFAULT_STATUS_CODES)


@app.get(
    "/healthz",
    description="Health Check.",
    summary="Health Check.",
    operation_id="healthCheck",
    tags=["Health Check"],
)
def ping():
    """Health check."""
    return {"ping": "pong!"}


@app.get("/refresh")
async def refresh(request: Request):
    """refresh catalog"""
    
    await register_collection_catalog(
        request.app,
        db_settings=db_settings,
    )
    return request.app.state.collection_catalog
