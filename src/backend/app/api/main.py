"""API router aggregator."""

from fastapi import APIRouter

from src.backend.app.routes import home

api_router = APIRouter()
api_router.include_router(home.router, tags=["Home"])
