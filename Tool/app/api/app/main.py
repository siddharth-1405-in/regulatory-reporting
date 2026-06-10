"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .routers.api import router
from .routers.data_layer import router as data_layer_router
from .routers.platform import router as platform_router
from .routers.report import router as report_router
from .routers.rules import router as rules_router
from .routers.sources import router as sources_router

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(data_layer_router)
app.include_router(platform_router)
app.include_router(sources_router)
app.include_router(rules_router)
app.include_router(report_router)


@app.get("/")
def root():
    return {"service": settings.app_name, "docs": "/docs", "api": "/api/health"}
