# PGH Pickup Reminders

A Pittsburgh trash, recycling, and yard waste schedule lookup with **email and SMS reminders** — filling the gap while [pgh.st](https://pgh.st) notifications are offline.

**Repository:** [github.com/prohousingpgh/trash_reminders](https://github.com/prohousingpgh/trash_reminders)
## Features

- Address lookup (proxies pgh.st `/locate` API with caching)
- Disambiguation when multiple street segments match
- Email reminders via [Amazon SES](https://aws.amazon.com/ses/)
- SMS reminders via [Amazon SNS](https://aws.amazon.com/sns/) with YES/STOP support (two-way SMS)
- Daily reminders at 6:00 PM ET the evening before pickup
- Holiday-only notification mode
- Admin page for weather/holiday delay banners

## Prerequisites

- Python 3.11+
- Node.js 20+
- AWS account with SES and SNS enabled

## Local development

### Backend

```powershell
cd "c:\Users\david\Documents\Dev Projects\pghst-reminders"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts\init_db.py
uvicorn api.main:app --reload --port 8000
```

### Frontend

```powershell
cd web
npm install
npm run dev
```

Open http://localhost:5174

## Environment variables

Copy `.env.example` to `.env` and configure:

| Variable | Purpose |
|----------|---------|
| `PGHST_BASE_URL` | pgh.st base URL (default `https://pgh.st`) |
| `DATABASE_PATH` | SQLite path (default `./data/app.db`) |
| `APP_BASE_URL` | Public site URL for verification/unsubscribe links |
| `AWS_REGION` | SES/SNS region (e.g. `us-east-1`) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | IAM credentials (optional if using instance role) |
| `SES_FROM_EMAIL` | Verified SES sender address |
| `SNS_ORIGINATION_NUMBER` | Optional two-way SMS number |
| `ADMIN_PASSWORD` | Password for `/admin/alerts` |
| `MAILCHIMP_API_KEY` | Mailchimp API key for optional Pro-Housing Pittsburgh newsletter signup |
| `MAILCHIMP_AUDIENCE_ID` | Mailchimp audience (list) ID |

Without AWS credentials, lookup and signup still work; notifications are logged as skipped.
Without Mailchimp credentials, pickup signup still works; the newsletter checkbox is ignored server-side.

**Setup guide:** see [SETUP_NOTIFICATIONS.md](SETUP_NOTIFICATIONS.md) for step-by-step SES + SNS configuration. For the optional Pro-Housing Pittsburgh newsletter, see [SETUP_MAILCHIMP.md](SETUP_MAILCHIMP.md).

## Deploy

See **[DEPLOY.md](DEPLOY.md)** for GitHub + Fly.io setup (app name `trash-reminders`, org repo `prohousingpgh/trash_reminders`).

Quick reference:

```powershell
fly auth login
fly apps create trash-reminders
fly volumes create trash_reminders_data --region iad --size 1 -a trash-reminders
fly secrets set -a trash-reminders APP_BASE_URL=https://trash-reminders.fly.dev ADMIN_PASSWORD=... AWS_REGION=us-east-2 ...
fly deploy -a trash-reminders
```

Add **`FLY_API_TOKEN`** to GitHub Actions secrets for automatic deploys on push to `main`.
## Project layout

| Path | Purpose |
|------|---------|
| `api/` | FastAPI backend, scheduler, notifications |
| `web/` | Vite + React frontend |
| `scripts/init_db.py` | Initialize SQLite schema |
| `data/` | SQLite database (gitignored) |

## Privacy

Contact information is used only for pickup reminders. See `/privacy` in the app.

Schedule data is sourced from public City of Pittsburgh collection information via pgh.st.
