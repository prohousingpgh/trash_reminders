from __future__ import annotations

import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from api.db import _now_iso, row_to_dict

LOGIN_TOKEN_HOURS = 1
SESSION_DAYS = 30

_ACCOUNT_SCHEMA = """
CREATE TABLE IF NOT EXISTS login_tokens (
  token TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_at TEXT
);

CREATE TABLE IF NOT EXISTS account_sessions (
  token TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_login_tokens_email ON login_tokens(email);
CREATE INDEX IF NOT EXISTS idx_subscriptions_email_lower ON subscriptions(email);
"""


def init_account_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(_ACCOUNT_SCHEMA)
    conn.commit()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def count_subscriptions_for_email(conn: sqlite3.Connection, email: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS n FROM subscriptions
        WHERE active = 1
          AND email IS NOT NULL
          AND LOWER(email) = LOWER(?)
          AND (email_enabled = 1 OR sms_enabled = 1)
        """,
        (email,),
    ).fetchone()
    return int(row["n"]) if row else 0


def list_subscriptions_for_email(
    conn: sqlite3.Connection, email: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM subscriptions
        WHERE active = 1
          AND email IS NOT NULL
          AND LOWER(email) = LOWER(?)
        ORDER BY created_at DESC
        """,
        (email,),
    ).fetchall()
    return [dict(r) for r in rows]


def create_login_token(conn: sqlite3.Connection, email: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=LOGIN_TOKEN_HOURS)
    conn.execute(
        """
        INSERT INTO login_tokens (token, email, created_at, expires_at, used_at)
        VALUES (?, ?, ?, ?, NULL)
        """,
        (token, normalize_email(email), now.isoformat(), expires.isoformat()),
    )
    conn.commit()
    return token


def consume_login_token(conn: sqlite3.Connection, token: str) -> str | None:
    row = conn.execute(
        "SELECT * FROM login_tokens WHERE token = ?", (token,)
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    if data.get("used_at"):
        return None
    expires = datetime.fromisoformat(data["expires_at"])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        return None
    conn.execute(
        "UPDATE login_tokens SET used_at = ? WHERE token = ?",
        (_now_iso(), token),
    )
    conn.commit()
    return data["email"]


def create_session(conn: sqlite3.Connection, email: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=SESSION_DAYS)
    conn.execute(
        """
        INSERT INTO account_sessions (token, email, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (token, normalize_email(email), now.isoformat(), expires.isoformat()),
    )
    conn.commit()
    return token


def get_session_email(conn: sqlite3.Connection, session_token: str) -> str | None:
    row = conn.execute(
        "SELECT * FROM account_sessions WHERE token = ?", (session_token,)
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    expires = datetime.fromisoformat(data["expires_at"])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        conn.execute("DELETE FROM account_sessions WHERE token = ?", (session_token,))
        conn.commit()
        return None
    return data["email"]


def delete_session(conn: sqlite3.Connection, session_token: str) -> None:
    conn.execute("DELETE FROM account_sessions WHERE token = ?", (session_token,))
    conn.commit()


def update_subscription_settings(
    conn: sqlite3.Connection,
    sub_id: str,
    *,
    holiday_only: bool | None = None,
    email_enabled: bool | None = None,
) -> dict[str, Any] | None:
    sub = row_to_dict(
        conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
    )
    if not sub:
        return None

    updates: list[str] = []
    params: list[Any] = []
    if holiday_only is not None:
        updates.append("holiday_only = ?")
        params.append(int(holiday_only))
    if email_enabled is not None:
        updates.append("email_enabled = ?")
        params.append(int(email_enabled))
        if not email_enabled:
            updates.append("email_verified = 0")

    if not updates:
        return sub

    params.append(sub_id)
    conn.execute(
        f"UPDATE subscriptions SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    conn.commit()
    return row_to_dict(
        conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
    )


def deactivate_subscription(conn: sqlite3.Connection, sub_id: str) -> dict[str, Any] | None:
    conn.execute(
        """
        UPDATE subscriptions
        SET active = 0, email_enabled = 0, sms_enabled = 0, email_verified = 0, sms_verified = 0
        WHERE id = ?
        """,
        (sub_id,),
    )
    conn.commit()
    return row_to_dict(
        conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
    )
