"""Static web application hosting for production releases."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.types import Scope


class SPAStaticFiles(StaticFiles):
    """Serve the SPA entry point when a browser route has no static asset."""

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code == 404 and scope["method"] in {"GET", "HEAD"}:
                return await super().get_response("index.html", scope)
            raise


def mount_static_ui(app: FastAPI, directory: Path) -> None:
    """Mount a built UI only when its entry point is available."""
    if directory.is_dir() and (directory / "index.html").is_file():
        app.mount("/", SPAStaticFiles(directory=directory, html=True), name="appui")
