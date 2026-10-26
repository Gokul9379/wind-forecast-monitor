"""FastAPI application entry point.

Run locally with:  uvicorn app.main:app --reload
Interactive API docs:  http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routes import router

app = FastAPI(
    title="Wind Forecast Monitor API",
    description="Compares Elexon WINDFOR forecasts with FUELHH actual wind generation (GB, January 2026).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": "wind-forecast-monitor", "docs": "/docs", "health": "/api/health"}
