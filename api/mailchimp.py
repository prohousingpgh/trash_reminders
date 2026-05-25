from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx

from api.config import (
    MAILCHIMP_API_KEY,
    MAILCHIMP_AUDIENCE_ID,
    MAILCHIMP_DEFAULT_MUNICIPALITY,
    MAILCHIMP_MERGE_MUNICIPALITY,
    MAILCHIMP_MERGE_NEIGHBORHOOD,
    MAILCHIMP_MERGE_ZIP,
)

logger = logging.getLogger(__name__)


def mailchimp_configured() -> bool:
    return bool(MAILCHIMP_API_KEY and MAILCHIMP_AUDIENCE_ID)


def mailchimp_status() -> dict[str, bool | str]:
    dc = _datacenter(MAILCHIMP_API_KEY) if MAILCHIMP_API_KEY else ""
    return {
        "configured": mailchimp_configured(),
        "audience_id_set": bool(MAILCHIMP_AUDIENCE_ID),
        "datacenter": dc or "",
        "merge_municipality": MAILCHIMP_MERGE_MUNICIPALITY,
        "merge_neighborhood": MAILCHIMP_MERGE_NEIGHBORHOOD,
        "merge_zip": MAILCHIMP_MERGE_ZIP,
    }


def _datacenter(api_key: str) -> str | None:
    parts = api_key.rsplit("-", 1)
    if len(parts) != 2 or not parts[1]:
        return None
    return parts[1]


def _subscriber_hash(email: str) -> str:
    return hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()


def _build_merge_fields(
    *,
    municipality: str | None,
    neighborhood: str | None,
    zip_code: str | None,
) -> dict[str, str]:
    fields: dict[str, str] = {}
    if MAILCHIMP_MERGE_MUNICIPALITY and municipality:
        fields[MAILCHIMP_MERGE_MUNICIPALITY] = municipality
    if MAILCHIMP_MERGE_NEIGHBORHOOD and neighborhood:
        fields[MAILCHIMP_MERGE_NEIGHBORHOOD] = neighborhood
    if MAILCHIMP_MERGE_ZIP and zip_code:
        fields[MAILCHIMP_MERGE_ZIP] = zip_code
    return fields


async def subscribe_to_newsletter(
    email: str,
    *,
    neighborhood: str | None = None,
    zip_code: str | None = None,
    municipality: str | None = None,
) -> bool:
    """Add or update a member on the Pro-Housing Pittsburgh Mailchimp audience."""
    if not mailchimp_configured():
        logger.warning("Mailchimp not configured; skipping newsletter subscribe for %s", email)
        return False

    dc = _datacenter(MAILCHIMP_API_KEY)
    if not dc:
        logger.error("Mailchimp API key must include datacenter suffix (e.g. key-us19)")
        return False

    normalized = email.strip().lower()
    url = (
        f"https://{dc}.api.mailchimp.com/3.0/lists/"
        f"{MAILCHIMP_AUDIENCE_ID}/members/{_subscriber_hash(normalized)}"
    )
    merge_fields = _build_merge_fields(
        municipality=municipality or MAILCHIMP_DEFAULT_MUNICIPALITY,
        neighborhood=neighborhood,
        zip_code=zip_code,
    )
    payload: dict[str, Any] = {
        "email_address": normalized,
        "status_if_new": "subscribed",
        "status": "subscribed",
    }
    if merge_fields:
        payload["merge_fields"] = merge_fields

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.put(
                url,
                auth=("anystring", MAILCHIMP_API_KEY),
                json=payload,
            )
        if response.is_success:
            return True
        logger.warning(
            "Mailchimp subscribe failed for %s: %s %s",
            normalized,
            response.status_code,
            response.text[:500],
        )
        return False
    except httpx.HTTPError:
        logger.exception("Mailchimp request failed for %s", normalized)
        return False
