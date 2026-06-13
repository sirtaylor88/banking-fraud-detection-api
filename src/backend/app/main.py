"""NextGen Bank FastAPI application."""

from fastapi import FastAPI

from src.backend.app.api.main import api_router

app = FastAPI(
    title="NextGen Bank - FastAPI",
    description=(
        "Full-featured banking application built with FastAPI, providing secure "
        "and efficient financial services."
    ),
)

app.include_router(api_router)
