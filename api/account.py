from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from api import account_db
from api.account_db import normalize_email
from api.config import APP_BASE_URL, SESSION_COOKIE_NAME
from api.notifications import send_login_link_email

router = APIRouter(prefix="/api/account", tags=["account"])


class LoginRequest(BaseModel):
    email: EmailStr


class LoginVerifyRequest(BaseModel):
    token: str = Field(min_length=10)


class SubscriptionUpdate(BaseModel):
    holiday_only: bool | None = None
    email_enabled: bool | None = None


def get_db(request: Request):
    return request.app.state.db


def _secure_cookie() -> bool:
    return APP_BASE_URL.startswith("https://")


def _set_session_cookie(response: Response, session_token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        max_age=account_db.SESSION_DAYS * 86400,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
    )


def _session_token(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE_NAME)


def require_account(request: Request, conn=Depends(get_db)) -> str:
    token = _session_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not signed in")
    email = account_db.get_session_email(conn, token)
    if not email:
        raise HTTPException(status_code=401, detail="Session expired — request a new sign-in link")
    return email


def _owns_subscription(sub: dict[str, Any], email: str) -> bool:
    sub_email = sub.get("email")
    if not sub_email:
        return False
    return normalize_email(sub_email) == normalize_email(email)


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


@router.post("/login/request")
def request_login(body: LoginRequest, conn=Depends(get_db)) -> dict[str, str]:
    email = normalize_email(str(body.email))
    if account_db.count_subscriptions_for_email(conn, email) > 0:
        token = account_db.create_login_token(conn, email)
        send_login_link_email(email, token)

    return {
        "message": "If that address has pickup reminders, we sent a sign-in link. Check your inbox."
    }


@router.post("/login/verify")
def verify_login(
    body: LoginVerifyRequest,
    response: Response,
    conn=Depends(get_db),
) -> dict[str, Any]:
    email = account_db.consume_login_token(conn, body.token)
    if not email:
        raise HTTPException(status_code=404, detail="Invalid or expired sign-in link")

    session_token = account_db.create_session(conn, email)
    _set_session_cookie(response, session_token)
    return {"authenticated": True, "email": email}


@router.get("/session")
def get_session(request: Request, conn=Depends(get_db)) -> dict[str, Any]:
    token = _session_token(request)
    if not token:
        return {"authenticated": False}
    email = account_db.get_session_email(conn, token)
    if not email:
        return {"authenticated": False}
    return {"authenticated": True, "email": email}


@router.post("/logout")
def logout(request: Request, response: Response, conn=Depends(get_db)) -> dict[str, str]:
    token = _session_token(request)
    if token:
        account_db.delete_session(conn, token)
    _clear_session_cookie(response)
    return {"message": "Signed out"}


@router.get("/subscriptions")
def list_my_subscriptions(
    email: str = Depends(require_account),
    conn=Depends(get_db),
) -> dict[str, Any]:
    subs = account_db.list_subscriptions_for_email(conn, email)
    return {
        "email": email,
        "subscriptions": [_public_subscription(s) for s in subs],
    }


@router.patch("/subscriptions/{sub_id}")
def update_my_subscription(
    sub_id: str,
    body: SubscriptionUpdate,
    email: str = Depends(require_account),
    conn=Depends(get_db),
) -> dict[str, Any]:
    from api.db import get_subscription

    sub = get_subscription(conn, sub_id)
    if not sub or not _owns_subscription(sub, email):
        raise HTTPException(status_code=404, detail="Subscription not found")

    if body.holiday_only is None and body.email_enabled is None:
        raise HTTPException(status_code=400, detail="No updates provided")

    updated = account_db.update_subscription_settings(
        conn,
        sub_id,
        holiday_only=body.holiday_only,
        email_enabled=body.email_enabled,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"subscription": _public_subscription(updated)}


@router.delete("/subscriptions/{sub_id}")
def cancel_my_subscription(
    sub_id: str,
    email: str = Depends(require_account),
    conn=Depends(get_db),
) -> dict[str, Any]:
    from api.db import get_subscription

    sub = get_subscription(conn, sub_id)
    if not sub or not _owns_subscription(sub, email):
        raise HTTPException(status_code=404, detail="Subscription not found")

    updated = account_db.deactivate_subscription(conn, sub_id)
    return {"subscription": _public_subscription(updated or sub), "message": "Reminders cancelled for this address"}
