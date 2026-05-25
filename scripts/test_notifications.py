#!/usr/bin/env python3
"""Send test email and/or SMS to verify notification credentials."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.notifications import normalize_phone, notifications_status, send_email, send_sms


def main() -> None:
    parser = argparse.ArgumentParser(description="Test PGH Pickup Reminders notifications")
    parser.add_argument("--email", help="Email address for test message")
    parser.add_argument("--phone", help="Phone number for test SMS (e.g. 4125551234)")
    args = parser.parse_args()

    status = notifications_status()
    print("Notification config:")
    print(f"  provider:         {status.get('provider', 'aws')}")
    print(f"  region:           {status.get('region', '')}")
    print(f"  email_configured: {status['email_configured']}")
    print(f"  sms_configured:   {status['sms_configured']}")
    if status.get("from_email"):
        print(f"  from_email:       {status['from_email']}")
    if status.get("origination_number"):
        print(f"  origination_number: {status['origination_number']}")

    if not args.email and not args.phone:
        parser.error("Provide --email and/or --phone")

    ok = True
    if args.email:
        sent = send_email(
            args.email,
            "PGH Pickup Reminders test",
            "<p>If you received this, email reminders are working.</p>",
        )
        print(f"Email to {args.email}: {'sent' if sent else 'FAILED'}")
        ok = ok and sent

    if args.phone:
        try:
            phone = normalize_phone(args.phone)
        except ValueError as exc:
            print(f"Invalid phone: {exc}")
            sys.exit(1)
        sent = send_sms(
            phone,
            "PGH Pickup Reminders: test message. Reply STOP to unsubscribe.",
        )
        print(f"SMS to {phone}: {'sent' if sent else 'FAILED'}")
        ok = ok and sent

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
