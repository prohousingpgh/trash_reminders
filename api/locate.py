from __future__ import annotations

import logging
import re
import time
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Query

from api.config import LOCATE_CACHE_TTL_SECONDS, PGHST_BASE_URL, PITTSBURGH_ZIPS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["locate"])

_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def parse_address(raw: str) -> tuple[str, str]:
    """Split '1199 N Clair St' into house number and street name."""
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("Address is required")

    match = re.match(r"^(\d+)\s+(.+)$", cleaned)
    if not match:
        raise ValueError("Enter a house number followed by a street name")

    house_number = match.group(1)
    street = re.sub(r"[-!$%^&*()_+|~=`{}\[\]:\";'<>?,./]", "", match.group(2)).strip()
    if not street:
        raise ValueError("Street name is required")
    return house_number, street


def _cache_key(house: str, street: str, zip_code: str) -> str:
    return f"{house}|{street.lower()}|{zip_code}"


async def fetch_locate(house: str, street: str, zip_code: str = "") -> list[dict[str, Any]]:
    key = _cache_key(house, street, zip_code)
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached[0] < LOCATE_CACHE_TTL_SECONDS:
        return cached[1]

    url = f"{PGHST_BASE_URL}/locate/{quote(house)}/{quote(street)}/{quote(zip_code)}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.exception("Locate request failed: %s", url)
        raise HTTPException(status_code=502, detail="Schedule lookup service unavailable") from exc

    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Unexpected schedule response")

    _cache[key] = (now, data)
    return data


@router.get("/zips")
def list_zips() -> dict[str, list[str]]:
    return {"zips": PITTSBURGH_ZIPS}


@router.get("/locate")
async def locate(
    address: str = Query(..., min_length=3),
    zip: str = Query("", alias="zip"),
) -> dict[str, Any]:
    try:
        house, street = parse_address(address)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if zip and zip not in PITTSBURGH_ZIPS:
        raise HTTPException(status_code=400, detail="Invalid Pittsburgh ZIP code")

    results = await fetch_locate(house, street, zip)
    if not results:
        raise HTTPException(
            status_code=404,
            detail=(
                "Address not found. Try a partial street name (e.g. '1199 Clair') "
                "or confirm you live within Pittsburgh city limits."
            ),
        )

    return {
        "query": {"house_number": house, "street": street, "zip": zip or None},
        "results": results,
        "disambiguation_required": len(results) > 1,
    }


@router.get("/locate/{house}/{street}")
async def locate_path(
    house: str,
    street: str,
    zip: str = Query("", alias="zip"),
) -> dict[str, Any]:
    if zip and zip not in PITTSBURGH_ZIPS:
        raise HTTPException(status_code=400, detail="Invalid Pittsburgh ZIP code")

    results = await fetch_locate(house, street, zip)
    if not results:
        raise HTTPException(status_code=404, detail="Address not found")

    return {
        "query": {"house_number": house, "street": street, "zip": zip or None},
        "results": results,
        "disambiguation_required": len(results) > 1,
    }
