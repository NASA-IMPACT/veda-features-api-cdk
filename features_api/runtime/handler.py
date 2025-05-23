"""AWS Lambda handler."""

import asyncio
import logging
import os

from mangum import Mangum
from src.app import app
from src.monitoring import logger, metrics, tracer

logging.getLogger("mangum.lifespan").setLevel(logging.DEBUG)
logging.getLogger("mangum.http").setLevel(logging.DEBUG)

handler = Mangum(app, lifespan="on")

if "AWS_EXECUTION_ENV" in os.environ:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.router.startup())

# Add tracing
handler.__name__ = "handler"  # tracer requires __name__ to be set
handler = tracer.capture_lambda_handler(handler)
# Add logging
handler = logger.inject_lambda_context(handler, clear_state=True)
# Add metrics last to properly flush metrics.
handler = metrics.log_metrics(handler, capture_cold_start_metric=True)
