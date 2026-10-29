"""BillSaathi API entry point."""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.checks import router as checks_router
from app.bbps_mock.router import router as bbps_mock_router
from app.config import get_settings

VERSION = "0.2.0"

logging.basicConfig(level=get_settings().log_level)

app = FastAPI(title="BillSaathi API", version=VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,  # only our web app
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Last-Event-ID"],
)
app.include_router(checks_router)
app.include_router(bbps_mock_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "BillSaathi API", "docs": "/docs"}


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": VERSION,
        "git_sha": os.environ.get("GIT_SHA", "unknown"),
        "env": get_settings().app_env,
    }
