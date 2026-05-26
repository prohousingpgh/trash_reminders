from __future__ import annotations

import json
import logging
import re
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from api.config import (
    APP_BASE_URL,
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    SES_FROM_EMAIL,
    SNS_ORIGINATION_NUMBER,
)

logger = logging.getLogger(__name__)

_ses_client = None
_sns_client = None


def _boto_kwargs() -> dict[str, str]:
    kwargs: dict[str, str] = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
    return kwargs


def _has_aws_credentials() -> bool:
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        return True
    return boto3.Session(**_boto_kwargs()).get_credentials() is not None


def _ses():
    global _ses_client
    if _ses_client is None:
        _ses_client = boto3.client("ses", **_boto_kwargs())
    return _ses_client


def _sns():
    global _sns_client
    if _sns_client is None:
        _sns_client = boto3.client("sns", **_boto_kwargs())
    return _sns_client


def notifications_status() -> dict[str, bool | str]:
    creds = _has_aws_credentials()
    return {
        "provider": "aws",
        "region": AWS_REGION,
        "email_configured": creds and bool(SES_FROM_EMAIL),
        "sms_configured": creds,
        "from_email": SES_FROM_EMAIL if SES_FROM_EMAIL else "",
        "origination_number": SNS_ORIGINATION_NUMBER or "",
    }


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if phone.startswith("+") and len(digits) >= 10:
        return f"+{digits}"
    raise ValueError("Enter a valid US phone number")


def send_email(
    to: str,
    subject: str,
    html: str,
    *,
    list_unsubscribe_url: str | None = None,
) -> bool:
    if not SES_FROM_EMAIL:
        logger.warning("SES_FROM_EMAIL not set; skipping email to %s", to)
        return False
    if not _has_aws_credentials():
        logger.warning("AWS credentials not configured; skipping email to %s", to)
        return False

    _ = list_unsubscribe_url  # unsubscribe link is included in HTML body

    try:
        _ses().send_email(
            Source=SES_FROM_EMAIL,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html, "Charset": "UTF-8"}},
            },
        )
        return True
    except (ClientError, BotoCoreError):
        logger.exception("SES failed to send email to %s", to)
        return False


def send_sms(to: str, body: str) -> bool:
    if not _has_aws_credentials():
        logger.warning("AWS credentials not configured; skipping SMS to %s", to)
        return False

    params: dict[str, Any] = {
        "PhoneNumber": to,
        "Message": body,
        "MessageAttributes": {
            "AWS.SNS.SMS.SMSType": {
                "DataType": "String",
                "StringValue": "Transactional",
            }
        },
    }
    if SNS_ORIGINATION_NUMBER:
        params["MessageAttributes"]["AWS.MM.SMS.OriginationNumber"] = {
            "DataType": "String",
            "StringValue": SNS_ORIGINATION_NUMBER,
        }

    try:
        _sns().publish(**params)
        return True
    except (ClientError, BotoCoreError):
        logger.exception("SNS failed to send SMS to %s", to)
        return False


def format_address(sub: dict[str, Any]) -> str:
    return f"{sub['house_number']} {sub['street']}, Pittsburgh PA {sub['zip']}"


def send_verification_email(sub: dict[str, Any]) -> bool:
    verify_url = f"{APP_BASE_URL}/verify/email?token={sub['verify_token']}"
    unsub_url = f"{APP_BASE_URL}/unsubscribe/{sub['unsubscribe_token']}?channel=email"
    address = format_address(sub)
    html = f"""
    <p>Confirm your email for trash &amp; recycling reminders at:</p>
    <p><strong>{address}</strong></p>
    <p><a href="{verify_url}">Verify email address</a></p>
    <p style="color:#666;font-size:12px;">
      If you did not sign up, ignore this message.
      <a href="{unsub_url}">Unsubscribe</a>
    </p>
    """
    return send_email(
        sub["email"],
        "Confirm your Pittsburgh pickup reminders",
        html,
        list_unsubscribe_url=unsub_url,
    )


def send_login_link_email(email: str, token: str) -> bool:
    login_url = f"{APP_BASE_URL}/account/verify?token={token}"
    html = f"""
    <p>Sign in to manage your Pittsburgh pickup reminders:</p>
    <p><a href="{login_url}">Open my reminders</a></p>
    <p style="color:#666;font-size:12px;">
      This link expires in one hour. If you did not request this, you can ignore this email.
    </p>
    """
    return send_email(email, "Sign in to PGH Pickup Reminders", html)


def send_sms_opt_in(sub: dict[str, Any]) -> bool:
    address = format_address(sub)
    body = (
        f"PGH Pickup Reminders: Confirm reminders for {address}. "
        "Reply YES to confirm. Reply STOP to cancel."
    )
    return send_sms(sub["phone"], body)


def send_reminder_email(
    sub: dict[str, Any],
    pickup_types: list[str],
    *,
    alert_message: str | None = None,
) -> bool:
    address = format_address(sub)
    unsub_url = f"{APP_BASE_URL}/unsubscribe/{sub['unsubscribe_token']}?channel=email"
    types_text = ", ".join(pickup_types)
    alert_html = ""
    if alert_message:
        alert_html = f'<p style="background:#fff3cd;padding:12px;"><strong>Alert:</strong> {alert_message}</p>'

    html = f"""
    <p>Reminder for <strong>{address}</strong>:</p>
    <p>Pickup tomorrow: <strong>{types_text}</strong></p>
    {alert_html}
    <p>Set out bins tonight. Recycling bins should not exceed 32 gallons.</p>
    <p style="color:#666;font-size:12px;">
      <a href="{unsub_url}">Unsubscribe from email reminders</a>
    </p>
    """
    return send_email(
        sub["email"],
        f"Pickup reminder: {types_text}",
        html,
        list_unsubscribe_url=unsub_url,
    )


def send_reminder_sms(
    sub: dict[str, Any],
    pickup_types: list[str],
    *,
    alert_message: str | None = None,
) -> bool:
    types_text = " & ".join(pickup_types)
    body = f"PGH Pickup Reminders: {types_text} pickup tomorrow."
    if alert_message:
        body += f" Alert: {alert_message}"
    body += " Reply STOP to unsubscribe."
    return send_sms(sub["phone"], body)


def handle_inbound_sms_keyword(body: str) -> str | None:
    """Return 'stop', 'start', or None for unrecognized messages."""
    normalized = body.strip().upper()
    if normalized in {"STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"}:
        return "stop"
    if normalized in {"START", "UNSTOP", "YES"}:
        return "start"
    return None


def parse_sns_inbound_sms(payload: dict[str, Any]) -> tuple[str, str] | None:
    """Extract (phone_e164, message_body) from an SNS notification payload."""
    if payload.get("Type") != "Notification":
        return None

    raw = payload.get("Message")
    if not raw:
        return None

    try:
        message = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return None

    if not isinstance(message, dict):
        return None

    phone = (
        message.get("originationNumber")
        or message.get("OriginationNumber")
    )
    body = (
        message.get("messageBody")
        or message.get("MessageBody")
        or message.get("message")
        or message.get("Body")
        or ""
    )

    if not phone or not isinstance(phone, str):
        return None

    try:
        phone = normalize_phone(phone)
    except ValueError:
        return phone

    return phone, str(body).strip()
