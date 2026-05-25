from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from api import db
from api.config import ADMIN_PASSWORD
from api.notifications import normalize_phone, notifications_status, send_email, send_sms

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AlertCreate(BaseModel):
    message: str
    division: str | None = None


class TestNotification(BaseModel):
    email: str | None = None
    phone: str | None = None


def get_db(request: Request):
    return request.app.state.db


def _check_admin(x_admin_password: str | None) -> None:
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/alerts")
def list_alerts(
    conn=Depends(get_db),
    x_admin_password: str | None = Header(default=None, alias="X-Admin-Password"),
) -> dict[str, Any]:
    _check_admin(x_admin_password)
    return {"alerts": db.list_active_alerts(conn)}


@router.post("/alerts")
def create_alert(
    body: AlertCreate,
    conn=Depends(get_db),
    x_admin_password: str | None = Header(default=None, alias="X-Admin-Password"),
) -> dict[str, Any]:
    _check_admin(x_admin_password)
    alert = db.create_alert(conn, message=body.message.strip(), division=body.division)
    return {"alert": alert}


@router.delete("/alerts/{alert_id}")
def delete_alert(
    alert_id: str,
    conn=Depends(get_db),
    x_admin_password: str | None = Header(default=None, alias="X-Admin-Password"),
) -> dict[str, str]:
    _check_admin(x_admin_password)
    if not db.deactivate_alert(conn, alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "deactivated"}


@router.get("/notifications/status")
def notification_status(
    x_admin_password: str | None = Header(default=None, alias="X-Admin-Password"),
) -> dict[str, object]:
    _check_admin(x_admin_password)
    return {"notifications": notifications_status()}


@router.post("/notifications/test")
def test_notifications(
    body: TestNotification,
    x_admin_password: str | None = Header(default=None, alias="X-Admin-Password"),
) -> dict[str, object]:
    _check_admin(x_admin_password)
    if not body.email and not body.phone:
        raise HTTPException(status_code=400, detail="Provide email and/or phone")

    results: dict[str, bool] = {}
    if body.email:
        results["email"] = send_email(
            body.email,
            "PGH Pickup Reminders test",
            "<p>If you received this, email reminders are working.</p>",
        )
    if body.phone:
        try:
            phone = normalize_phone(body.phone)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        results["sms"] = send_sms(
            phone,
            "PGH Pickup Reminders: test message. Reply STOP to unsubscribe.",
        )
    return {"results": results, "notifications": notifications_status()}
