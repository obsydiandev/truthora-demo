"""FastAPI application entry point."""

from fastapi import FastAPI

from api.routes import analyze, claims, health

app = FastAPI(
    title="Truthora",
    description="Open Multilingual Claim Detection & Matching API",
    version="0.1.0",
)

app.include_router(health.router, tags=["health"])
app.include_router(analyze.router, tags=["analyze"])
app.include_router(claims.router, tags=["claims"])
