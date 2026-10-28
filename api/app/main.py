"""BillSaathi API entry point."""

import os

from fastapi import FastAPI

from app.config import get_settings

VERSION = "0.1.0"

app = FastAPI(title="BillSaathi API", version=VERSION)


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
