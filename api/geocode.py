from __future__ import annotations

import logging
import re
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

from api.config import PITTSBURGH_ZIPS
from api.locate import fetch_locate, parse_address

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["geocode"])

CENSUS_GEOCODER_URL = (
    "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
)

_autocomplete_cache: dict[str, tuple[float, list[dict[str, str]]]] = {}
_AUTOCOMPLETE_TTL = 300


def _title_case(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split())


def _build_street(components: dict[str, Any]) -> str:
    parts = [
        components.get("preDirection", ""),
        components.get("streetName", ""),
        components.get("suffixType", ""),
    ]
    street = " ".join(p for p in parts if p).strip()
    return _title_case(street)


def _parse_census_match(match: dict[str, Any]) -> dict[str, str] | None:
    components = match.get("addressComponents") or {}
    city = (components.get("city") or "").upper()
    if city != "PITTSBURGH":
        return None

    zip_code = str(components.get("zip") or "")[:5]
    if not zip_code or zip_code not in PITTSBURGH_ZIPS:
        return None

    house_number = str(components.get("fromAddress") or "").strip()
    street = _build_street(components)
    if not house_number or not street:
        return None

    label = match.get("matchedAddress") or f"{house_number} {street}, Pittsburgh, PA {zip_code}"
    return {
        "label": label,
        "house_number": house_number,
        "street": street,
        "zip": zip_code,
    }


def _from_locate_results(results: list[dict[str, Any]], limit: int) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for result in results:
        house_number = str(result.get("number") or "")
        street = str(result.get("street") or "")
        zip_code = str(result.get("zip") or "")[:5]
        if not house_number or not street or zip_code not in PITTSBURGH_ZIPS:
            continue
        key = (house_number, street.lower(), zip_code)
        if key in seen:
            continue
        seen.add(key)
        hood = result.get("hood")
        label = f"{house_number} {street}, Pittsburgh, PA {zip_code}"
        if hood:
            label += f" ({hood})"
        suggestions.append(
            {
                "label": label,
                "house_number": house_number,
                "street": street,
                "zip": zip_code,
            }
        )
        if len(suggestions) >= limit:
            break
    return suggestions


async def _fetch_census(query: str, limit: int) -> list[dict[str, str]]:
    address = query.strip()
    if not re.search(r"pittsburgh", address, re.IGNORECASE):
        address = f"{address}, Pittsburgh, PA"

    params = {
        "address": address,
        "benchmark": "Public_AR_Current",
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(CENSUS_GEOCODER_URL, params=params)
        response.raise_for_status()
        data = response.json()

    suggestions: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for match in (data.get("result") or {}).get("addressMatches") or []:
        parsed = _parse_census_match(match)
        if not parsed:
            continue
        key = (parsed["house_number"], parsed["street"].lower(), parsed["zip"])
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(parsed)
        if len(suggestions) >= limit:
            break
    return suggestions


async def _fetch_pghst_fallback(query: str, limit: int) -> list[dict[str, str]]:
    try:
        house, street = parse_address(query)
    except ValueError:
        return []
    results = await fetch_locate(house, street, "")
    return _from_locate_results(results, limit)


async def _fetch_suggestions(query: str, limit: int) -> list[dict[str, str]]:
    cleaned = query.strip()
    cache_key = f"{cleaned.lower()}|{limit}"
    now = time.time()
    cached = _autocomplete_cache.get(cache_key)
    if cached and now - cached[0] < _AUTOCOMPLETE_TTL:
        return cached[1]

    try:
        suggestions = await _fetch_census(cleaned, limit)
        if not suggestions:
            suggestions = await _fetch_pghst_fallback(cleaned, limit)
    except httpx.HTTPError as exc:
        logger.exception("Census geocoder failed for %r", query)
        try:
            suggestions = await _fetch_pghst_fallback(cleaned, limit)
        except Exception:
            raise HTTPException(status_code=502, detail="Address search unavailable") from exc
        if not suggestions:
            raise HTTPException(status_code=502, detail="Address search unavailable") from exc

    _autocomplete_cache[cache_key] = (now, suggestions)
    return suggestions


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=3),
    limit: int = Query(8, ge=1, le=15),
) -> dict[str, Any]:
    suggestions = await _fetch_suggestions(q.strip(), limit)
    return {"query": q.strip(), "suggestions": suggestions}
