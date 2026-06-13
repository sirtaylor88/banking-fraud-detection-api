"""Home route handlers."""

from fastapi import APIRouter

from src.backend.app.core.logging import get_logger

logger = get_logger()

router = APIRouter()


@router.get("/")
def home() -> dict[str, str]:
    """Return a welcome message."""
    logger.info("Home page accessed.")
    return {"message": "Welcome to NextGen Bank - FastAPI!"}
