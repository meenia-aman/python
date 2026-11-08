"""Run only v3: uv run uvicorn src.module_v3.main:app --reload."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.module_v3.db import engine
from src.module_v3.router import api_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Unit of Work v3", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"success": True, "message": "Service working"}
