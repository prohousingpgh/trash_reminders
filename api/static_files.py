from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from starlette.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from api.config import STATIC_DIR

logger = logging.getLogger(__name__)

_ASSET_CACHE = "public, max-age=31536000, immutable"
_HTML_CACHE = "no-cache"


class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code != 200:
            return response

        request_path = scope.get("path", "")
        if request_path.startswith("/assets/") or path.startswith("assets/"):
            response.headers["Cache-Control"] = _ASSET_CACHE
        elif path in ("", "index.html") or request_path in ("", "/"):
            response.headers["Cache-Control"] = _HTML_CACHE
        elif Path(path).suffix in {".webp", ".svg", ".png", ".ico", ".woff2"}:
            response.headers["Cache-Control"] = _ASSET_CACHE

        return response


def install_static_files(app: FastAPI) -> None:
    if not STATIC_DIR.is_dir():
        logger.warning("Static directory missing (%s); UI will not be served", STATIC_DIR)
        return

    index = STATIC_DIR / "index.html"
    if index.is_file():

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str) -> FileResponse:
            """Serve index.html for client-side routes (e.g. /schedule)."""
            if full_path.startswith(("api/", "webhooks/", "assets/")):
                raise HTTPException(status_code=404)
            # Let the static mount serve files like favicon.svg
            if "." in full_path.rsplit("/", 1)[-1]:
                raise HTTPException(status_code=404)
            return FileResponse(index, media_type="text/html", headers={"Cache-Control": _HTML_CACHE})

    app.mount(
        "/",
        CachedStaticFiles(directory=STATIC_DIR, html=True),
        name="spa",
    )
