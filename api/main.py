from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from urllib.request import urlopen

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from api import db
from api.admin import router as admin_router
from api.config import CORS_ORIGINS
from api.geocode import router as geocode_router
from api.locate import router as locate_router
from api.mailchimp import mailchimp_status
from api.notifications import (
    handle_inbound_sms_keyword,
    normalize_phone,
    notifications_status,
    parse_sns_inbound_sms,
)
from api.scheduler import run_reminder_job
from api.static_files import install_static_files
from api.subscriptions import router as subscriptions_router

logger = logging.getLogger(__name__)
webhooks_router = APIRouter(prefix="/webhooks", tags=["webhooks"])
unsub_router = APIRouter(tags=["unsubscribe"])
scheduler = AsyncIOScheduler(timezone="America/New_York")


@asynccontextmanager
async def lifespan(app):
    conn = db.get_connection()
    db.init_db(conn)
    app.state.db = conn

    async def reminder_job():
        await run_reminder_job(app.state.db)

    scheduler.add_job(
        reminder_job,
        CronTrigger(hour=18, minute=0, timezone="America/New_York"),
        id="daily_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started (daily reminders at 6:00 PM ET)")

    yield

    scheduler.shutdown(wait=False)
    app.state.db.close()


app = FastAPI(title="PGH Pickup Reminders API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "notifications": notifications_status(),
        "mailchimp": mailchimp_status(),
    }


@webhooks_router.post("/sns")
async def sns_webhook(request: Request):
    """Handle SNS subscription confirmations and inbound SMS (two-way SMS)."""
    try:
        payload = json.loads(await request.body())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    msg_type = payload.get("Type")

    if msg_type == "SubscriptionConfirmation":
        subscribe_url = payload.get("SubscribeURL")
        if subscribe_url:
            urlopen(subscribe_url)  # noqa: S310
            logger.info("Confirmed SNS subscription")
        return {"status": "subscription_confirmed"}

    if msg_type == "UnsubscribeConfirmation":
        return {"status": "unsubscribed"}

    if msg_type == "Notification":
        parsed = parse_sns_inbound_sms(payload)
        if not parsed:
            return {"status": "ignored"}

        phone, body = parsed
        conn = request.app.state.db
        keyword = handle_inbound_sms_keyword(body)

        if keyword == "stop":
            count = db.deactivate_by_phone(conn, phone)
            return {"status": "stop", "updated": count}

        if keyword == "start":
            count = db.reactivate_sms_by_phone(conn, phone)
            return {"status": "start", "updated": count}

        return {"status": "ignored", "hint": "Reply STOP to unsubscribe"}

    return {"status": "ignored"}


@unsub_router.get("/api/unsubscribe/{token}")
def unsubscribe_api(
    token: str,
    request: Request,
    channel: str | None = None,
):
    conn = request.app.state.db
    sub = db.unsubscribe(conn, token, channel=channel)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {
        "status": "unsubscribed",
        "channel": channel or "all",
        "subscription": {
            "house_number": sub["house_number"],
            "street": sub["street"],
            "zip": sub["zip"],
            "active": bool(sub["active"]),
            "email_enabled": bool(sub["email_enabled"]),
            "sms_enabled": bool(sub["sms_enabled"]),
        },
    }


app.include_router(geocode_router)
app.include_router(locate_router)
app.include_router(subscriptions_router)
app.include_router(admin_router)
app.include_router(webhooks_router)
app.include_router(unsub_router)

install_static_files(app)
