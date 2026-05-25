from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from api import db
from api.locate import fetch_locate
from api.mailchimp import subscribe_to_newsletter
from api.notifications import (
    normalize_phone,
    send_sms_opt_in,
    send_verification_email,
)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


class SubscriptionCreate(BaseModel):
    house_number: str
    street: str
    zip: str = Field(min_length=5, max_length=5)
    hood: str | None = None
    division: str | None = None
    regular_trash_pickup_day: int | None = None
    email: str | None = None
    phone: str | None = None
    email_enabled: bool = False
    sms_enabled: bool = False
    holiday_only: bool = False
    prohousing_newsletter: bool = False

    @model_validator(mode="after")
    def validate_channels(self) -> "SubscriptionCreate":
        if not self.email_enabled and not self.sms_enabled:
            raise ValueError("Enable email and/or SMS reminders")
        if self.email_enabled and not self.email:
            raise ValueError("Email is required for email reminders")
        if self.sms_enabled and not self.phone:
            raise ValueError("Phone is required for SMS reminders")
        if self.prohousing_newsletter and not self.email_enabled:
            raise ValueError("Newsletter signup requires email reminders")
        return self


def get_db(request: Request):
    return request.app.state.db


@router.post("")
async def create_subscription(
    body: SubscriptionCreate,
    conn=Depends(get_db),
) -> dict[str, Any]:
    phone = None
    if body.sms_enabled and body.phone:
        try:
            phone = normalize_phone(body.phone)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Confirm address still resolves
    results = await fetch_locate(body.house_number, body.street, body.zip)
    match = next(
        (
            r
            for r in results
            if str(r.get("number")) == body.house_number
            and r.get("street") == body.street
            and str(r.get("zip")) == body.zip
        ),
        None,
    )
    if not match:
        raise HTTPException(status_code=400, detail="Address could not be verified")

    sub = db.create_subscription(
        conn,
        house_number=body.house_number,
        street=body.street,
        zip_code=body.zip,
        hood=body.hood or match.get("hood"),
        division=body.division or match.get("division"),
        regular_trash_pickup_day=body.regular_trash_pickup_day
        if body.regular_trash_pickup_day is not None
        else match.get("regular_trash_pickup_day"),
        email=body.email.strip() if body.email else None,
        phone=phone,
        email_enabled=body.email_enabled,
        sms_enabled=body.sms_enabled,
        holiday_only=body.holiday_only,
    )

    if body.email_enabled and sub.get("verify_token"):
        email_sent = send_verification_email(sub)
    else:
        email_sent = None
    if body.sms_enabled and phone:
        sms_sent = send_sms_opt_in(sub)
    else:
        sms_sent = None

    newsletter_subscribed: bool | None = None
    if body.prohousing_newsletter and body.email_enabled and body.email:
        newsletter_subscribed = await subscribe_to_newsletter(
            body.email.strip(),
            neighborhood=sub.get("hood"),
            zip_code=sub.get("zip"),
        )

    return {
        "subscription": _public_subscription(sub),
        "message": _signup_message(
            sub,
            email_sent=email_sent,
            sms_sent=sms_sent,
            newsletter_subscribed=newsletter_subscribed,
            newsletter_requested=body.prohousing_newsletter,
        ),
        "email_sent": email_sent,
        "sms_sent": sms_sent,
        "newsletter_subscribed": newsletter_subscribed,
    }


@router.get("/verify/{token}")
def verify_email(token: str, conn=Depends(get_db)) -> dict[str, Any]:
    sub = db.verify_email(conn, token)
    if not sub:
        raise HTTPException(status_code=404, detail="Invalid or expired verification link")
    return {
        "subscription": _public_subscription(sub),
        "message": "Email verified. You will receive reminders the evening before pickup.",
    }


@router.post("/{sub_id}/confirm-sms")
def confirm_sms(sub_id: str, conn=Depends(get_db)) -> dict[str, Any]:
    sub = db.get_subscription(conn, sub_id)
    if not sub or not sub.get("sms_enabled"):
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub = db.verify_sms(conn, sub_id)
    return {
        "subscription": _public_subscription(sub),
        "message": "SMS reminders confirmed.",
    }


def _signup_message(
    sub: dict[str, Any],
    *,
    email_sent: bool | None = None,
    sms_sent: bool | None = None,
    newsletter_requested: bool = False,
    newsletter_subscribed: bool | None = None,
) -> str:
    parts: list[str] = []
    if sub.get("email_enabled"):
        if email_sent is False:
            parts.append("Email verification could not be sent (check server notification settings)")
        else:
            parts.append("Check your email to verify your address")
    if sub.get("sms_enabled"):
        if sms_sent is False:
            parts.append("Confirmation text could not be sent (check server notification settings)")
        else:
            parts.append("Reply YES to the confirmation text to enable SMS reminders")
    if newsletter_requested:
        if newsletter_subscribed is False:
            parts.append(
                "We could not add you to the Pro-Housing Pittsburgh email list (try again later)"
            )
        elif newsletter_subscribed:
            parts.append("You are subscribed to Pro-Housing Pittsburgh updates")
    return ". ".join(parts) + "."


def _public_subscription(sub: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": sub["id"],
        "house_number": sub["house_number"],
        "street": sub["street"],
        "zip": sub["zip"],
        "hood": sub["hood"],
        "email_enabled": bool(sub["email_enabled"]),
        "sms_enabled": bool(sub["sms_enabled"]),
        "email_verified": bool(sub["email_verified"]),
        "sms_verified": bool(sub["sms_verified"]),
        "holiday_only": bool(sub["holiday_only"]),
        "active": bool(sub["active"]),
        "created_at": sub["created_at"],
    }
