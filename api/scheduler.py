from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from api import db
from api.locate import fetch_locate
from api.notifications import send_reminder_email, send_reminder_sms

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%m-%d-%Y").date()
    except ValueError:
        return None


def _tomorrow_et() -> date:
    return (datetime.now(ET) + timedelta(days=1)).date()


def _pickup_types_for_tomorrow(schedule: dict[str, Any], tomorrow: date) -> list[str]:
    types: list[str] = []
    if _parse_date(schedule.get("next_pickup_date")) == tomorrow:
        types.append("Trash")
    if _parse_date(schedule.get("next_recycling_date")) == tomorrow:
        types.append("Recycling")
    if _parse_date(schedule.get("next_yard_date")) == tomorrow:
        types.append("Yard waste")
    return types


def _active_alert_message(
    alerts: list[dict[str, Any]], division: str | None
) -> str | None:
    for alert in alerts:
        alert_division = alert.get("division")
        if alert_division and division and alert_division != division:
            continue
        return alert.get("message")
    return None


async def run_reminder_job(conn) -> dict[str, int]:
    tomorrow = _tomorrow_et()
    subs = db.list_active_subscriptions(conn)
    alerts = db.list_active_alerts(conn)
    stats = {"checked": 0, "email_sent": 0, "sms_sent": 0, "skipped": 0, "errors": 0}

    for sub in subs:
        stats["checked"] += 1
        try:
            results = await fetch_locate(sub["house_number"], sub["street"], sub["zip"])
            schedule = next(
                (
                    r
                    for r in results
                    if str(r.get("number")) == sub["house_number"]
                    and r.get("street") == sub["street"]
                    and str(r.get("zip")) == sub["zip"]
                ),
                results[0] if results else None,
            )
            if not schedule:
                stats["skipped"] += 1
                continue

            pickup_types = _pickup_types_for_tomorrow(schedule, tomorrow)
            holiday_flag = bool(schedule.get("holiday_cancellation"))
            alert_message = _active_alert_message(alerts, sub.get("division"))

            if sub.get("holiday_only"):
                if not holiday_flag and not alert_message:
                    stats["skipped"] += 1
                    continue
                if not pickup_types and alert_message:
                    pickup_types = ["Service update"]

            if not pickup_types:
                stats["skipped"] += 1
                continue

            if (
                sub.get("email_enabled")
                and sub.get("email_verified")
                and sub.get("email")
            ):
                if send_reminder_email(
                    sub, pickup_types, alert_message=alert_message
                ):
                    stats["email_sent"] += 1

            if sub.get("sms_enabled") and sub.get("sms_verified") and sub.get("phone"):
                if send_reminder_sms(sub, pickup_types, alert_message=alert_message):
                    stats["sms_sent"] += 1

        except Exception:
            logger.exception("Reminder failed for subscription %s", sub.get("id"))
            stats["errors"] += 1

    logger.info("Reminder job complete: %s", stats)
    return stats
