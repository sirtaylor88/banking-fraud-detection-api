"""NextGen Bank FastAPI application."""

from fastapi import FastAPI

app = FastAPI(
    title="NextGen Bank - FastAPI",
    description=(
        "Full-featured banking application built with FastAPI, providing secure "
        "and efficient financial services."
    ),
)


@app.get("/")
def home() -> dict[str, str]:
    """Return a welcome message."""
    return {"message": "Welcome to NextGen Bank - FastAPI!"}
