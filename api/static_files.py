from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from api.config import STATIC_DIR

logger = logging.getLogger(__name__)

_ASSET_CACHE = "public, max-age=31536000, immutable"
_HTML_CACHE = "no-cache"


def _apply_cache_headers(response: Response, path: str, request_path: str) -> Response:
    if response.status_code != 200:
        return response

    if request_path.startswith("/assets/") or path.startswith("assets/"):
        response.headers["Cache-Control"] = _ASSET_CACHE
    elif path in ("", "index.html") or request_path in ("", "/"):
        response.headers["Cache-Control"] = _HTML_CACHE
    elif Path(path).suffix in {".webp", ".svg", ".png", ".ico", ".woff2", ".css", ".js"}:
        response.headers["Cache-Control"] = _ASSET_CACHE

    return response


def _should_fallback_to_spa(request_path: str) -> bool:
    if not request_path or request_path == "/":
        return False
    if request_path.startswith(("/api/", "/webhooks/", "/assets/")):
        return False
    last_segment = request_path.rsplit("/", 1)[-1]
    if "." in last_segment:
        return False
    return True


class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        request_path = scope.get("path", "")

        try:
            response = await super().get_response(path, scope)
            return _apply_cache_headers(response, path, request_path)
        except HTTPException as exc:
            if exc.status_code != 404 or not self.html:
                raise
            if not _should_fallback_to_spa(request_path):
                raise
            index_response = await super().get_response("index.html", scope)
            return _apply_cache_headers(index_response, "index.html", request_path)


def install_static_files(app: FastAPI) -> None:
    if not STATIC_DIR.is_dir():
        logger.warning("Static directory missing (%s); UI will not be served", STATIC_DIR)
        return

    app.mount(
        "/",
        CachedStaticFiles(directory=STATIC_DIR, html=True),
        name="spa",
    )
