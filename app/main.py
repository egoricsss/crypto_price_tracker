from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.core.logging import setup_logging, get_logger
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Application startup: connecting to services...")
    yield
    logger.info("Application shutdown: cleaning up resources...")


app = FastAPI(title="Crypto Price Tracker", lifespan=lifespan)


if __name__ == "__main__":
    uvicorn.run(app="app.main:app")
