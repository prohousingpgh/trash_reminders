from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

STATIC_DIR = Path(os.environ.get("STATIC_DIR", ROOT / "web" / "dist"))
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "app.db"))

_default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
_extra = os.environ.get("ALLOWED_ORIGINS", "").strip()
CORS_ORIGINS = [
    o.strip()
    for o in (_default_origins + ("," + _extra if _extra else "")).split(",")
    if o.strip()
]

PGHST_BASE_URL = os.environ.get("PGHST_BASE_URL", "https://pgh.st").rstrip("/")
LOCATE_CACHE_TTL_SECONDS = int(os.environ.get("LOCATE_CACHE_TTL_SECONDS", "3600"))

# Amazon SES (email) and SNS (SMS)
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
SES_FROM_EMAIL = os.environ.get("SES_FROM_EMAIL", "")
SNS_ORIGINATION_NUMBER = os.environ.get("SNS_ORIGINATION_NUMBER", "")

APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5174").rstrip("/")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

# Mailchimp (optional Pro-Housing Pittsburgh newsletter — separate from SES)
MAILCHIMP_API_KEY = os.environ.get("MAILCHIMP_API_KEY", "")
MAILCHIMP_AUDIENCE_ID = os.environ.get("MAILCHIMP_AUDIENCE_ID", "")
MAILCHIMP_DEFAULT_MUNICIPALITY = os.environ.get(
    "MAILCHIMP_DEFAULT_MUNICIPALITY", "City of Pittsburgh"
)
# Merge field tags in Mailchimp (max 10 chars); must match your audience settings
MAILCHIMP_MERGE_MUNICIPALITY = os.environ.get("MAILCHIMP_MERGE_MUNICIPALITY", "MUNICIPAL")
MAILCHIMP_MERGE_NEIGHBORHOOD = os.environ.get("MAILCHIMP_MERGE_NEIGHBORHOOD", "NEIGHBORHO")
MAILCHIMP_MERGE_ZIP = os.environ.get("MAILCHIMP_MERGE_ZIP", "ZIPCODE")

PITTSBURGH_ZIPS = [
    "15106", "15120", "15201", "15203", "15204", "15205", "15206", "15207",
    "15208", "15210", "15211", "15212", "15213", "15214", "15216", "15217",
    "15218", "15219", "15220", "15221", "15222", "15224", "15226", "15227",
    "15232", "15233", "15234", "15235",
]
