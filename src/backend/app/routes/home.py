"""Home route handlers."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def home() -> dict[str, str]:
    """Return a welcome message."""
    return {"message": "Welcome to NextGen Bank - FastAPI!"}
