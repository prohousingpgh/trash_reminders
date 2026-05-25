from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from api.config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
  id TEXT PRIMARY KEY,
  house_number TEXT NOT NULL,
  street TEXT NOT NULL,
  zip TEXT NOT NULL,
  hood TEXT,
  division TEXT,
  regular_trash_pickup_day INTEGER,
  email TEXT,
  phone TEXT,
  email_enabled INTEGER DEFAULT 0,
  sms_enabled INTEGER DEFAULT 0,
  holiday_only INTEGER DEFAULT 0,
  email_verified INTEGER DEFAULT 0,
  sms_verified INTEGER DEFAULT 0,
  verify_token TEXT UNIQUE,
  unsubscribe_token TEXT UNIQUE NOT NULL,
  active INTEGER DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS service_alerts (
  id TEXT PRIMARY KEY,
  message TEXT NOT NULL,
  division TEXT,
  active INTEGER DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(active);
CREATE INDEX IF NOT EXISTS idx_subscriptions_phone ON subscriptions(phone);
CREATE INDEX IF NOT EXISTS idx_subscriptions_verify ON subscriptions(verify_token);
CREATE INDEX IF NOT EXISTS idx_service_alerts_active ON service_alerts(active);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def create_subscription(
    conn: sqlite3.Connection,
    *,
    house_number: str,
    street: str,
    zip_code: str,
    hood: str | None,
    division: str | None,
    regular_trash_pickup_day: int | None,
    email: str | None,
    phone: str | None,
    email_enabled: bool,
    sms_enabled: bool,
    holiday_only: bool,
) -> dict[str, Any]:
    sub_id = str(uuid.uuid4())
    verify_token = str(uuid.uuid4()) if email_enabled else None
    unsubscribe_token = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO subscriptions (
          id, house_number, street, zip, hood, division, regular_trash_pickup_day,
          email, phone, email_enabled, sms_enabled, holiday_only,
          email_verified, sms_verified, verify_token, unsubscribe_token, active, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sub_id,
            house_number,
            street,
            zip_code,
            hood,
            division,
            regular_trash_pickup_day,
            email,
            phone,
            int(email_enabled),
            int(sms_enabled),
            int(holiday_only),
            0,
            0,
            verify_token,
            unsubscribe_token,
            1,
            _now_iso(),
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
    return row_to_dict(row)  # type: ignore[return-value]


def get_subscription(conn: sqlite3.Connection, sub_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
    return row_to_dict(row)


def get_subscription_by_verify_token(
    conn: sqlite3.Connection, token: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE verify_token = ?", (token,)
    ).fetchone()
    return row_to_dict(row)


def get_subscription_by_unsubscribe_token(
    conn: sqlite3.Connection, token: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE unsubscribe_token = ?", (token,)
    ).fetchone()
    return row_to_dict(row)


def verify_email(conn: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    sub = get_subscription_by_verify_token(conn, token)
    if not sub:
        return None
    conn.execute(
        "UPDATE subscriptions SET email_verified = 1, verify_token = NULL WHERE id = ?",
        (sub["id"],),
    )
    conn.commit()
    return get_subscription(conn, sub["id"])


def verify_sms(conn: sqlite3.Connection, sub_id: str) -> dict[str, Any] | None:
    conn.execute(
        "UPDATE subscriptions SET sms_verified = 1 WHERE id = ?",
        (sub_id,),
    )
    conn.commit()
    return get_subscription(conn, sub_id)


def unsubscribe(
    conn: sqlite3.Connection, token: str, *, channel: str | None = None
) -> dict[str, Any] | None:
    sub = get_subscription_by_unsubscribe_token(conn, token)
    if not sub:
        return None

    if channel == "email":
        conn.execute(
            """
            UPDATE subscriptions
            SET email_enabled = 0, email_verified = 0
            WHERE id = ?
            """,
            (sub["id"],),
        )
    elif channel == "sms":
        conn.execute(
            """
            UPDATE subscriptions
            SET sms_enabled = 0, sms_verified = 0
            WHERE id = ?
            """,
            (sub["id"],),
        )
    else:
        conn.execute(
            "UPDATE subscriptions SET active = 0, email_enabled = 0, sms_enabled = 0 WHERE id = ?",
            (sub["id"],),
        )

    conn.commit()
    return get_subscription(conn, sub["id"])


def deactivate_by_phone(conn: sqlite3.Connection, phone: str) -> int:
    cur = conn.execute(
        """
        UPDATE subscriptions
        SET sms_enabled = 0, sms_verified = 0
        WHERE phone = ? AND active = 1
        """,
        (phone,),
    )
    conn.commit()
    return cur.rowcount


def reactivate_sms_by_phone(conn: sqlite3.Connection, phone: str) -> int:
    cur = conn.execute(
        """
        UPDATE subscriptions
        SET sms_enabled = 1, sms_verified = 1
        WHERE phone = ? AND active = 1
        """,
        (phone,),
    )
    conn.commit()
    return cur.rowcount


def list_active_subscriptions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM subscriptions
        WHERE active = 1 AND (email_enabled = 1 OR sms_enabled = 1)
        """
    ).fetchall()
    return [dict(r) for r in rows]


def list_active_alerts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM service_alerts WHERE active = 1 ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def create_alert(
    conn: sqlite3.Connection, *, message: str, division: str | None = None
) -> dict[str, Any]:
    alert_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO service_alerts (id, message, division, active, created_at)
        VALUES (?, ?, ?, 1, ?)
        """,
        (alert_id, message, division, _now_iso()),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM service_alerts WHERE id = ?", (alert_id,)).fetchone()
    return row_to_dict(row)  # type: ignore[return-value]


def deactivate_alert(conn: sqlite3.Connection, alert_id: str) -> bool:
    cur = conn.execute(
        "UPDATE service_alerts SET active = 0 WHERE id = ?",
        (alert_id,),
    )
    conn.commit()
    return cur.rowcount > 0
