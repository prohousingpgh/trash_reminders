# Deploying trash_reminders

GitHub: [prohousingpgh/trash_reminders](https://github.com/prohousingpgh/trash_reminders)

Production runs on [Fly.io](https://fly.io) as app **`trash-reminders`** (https://trash-reminders.fly.dev).

## One-time setup

### 1. GitHub repository

```powershell
cd "c:\Users\david\Documents\Dev Projects\pghst-reminders"
git remote add origin https://github.com/prohousingpgh/trash_reminders.git
git branch -M main
git push -u origin main
```

If the repo does not exist yet (org admin):

```powershell
gh repo create prohousingpgh/trash_reminders --public --source=. --remote=origin --push
```

### 2. GitHub Actions secret

1. Create a Fly deploy token: `fly tokens create deploy -a trash-reminders`
2. In GitHub → **Settings → Secrets and variables → Actions**, add:
   - **`FLY_API_TOKEN`** — the token from step 1

Pushes to **`main`** run CI, then the deploy workflow builds the Docker image on Fly and releases it.

### 3. Fly.io app and volume

```powershell
fly auth login
fly apps create trash-reminders
fly volumes create trash_reminders_data --region iad --size 1 -a trash-reminders
```

### 4. Fly secrets

Set secrets once (replace values; never commit these):

```powershell
fly secrets set -a trash-reminders `
  APP_BASE_URL=https://trash-reminders.fly.dev `
  ADMIN_PASSWORD=your-strong-password `
  AWS_REGION=us-east-2 `
  AWS_ACCESS_KEY_ID=... `
  AWS_SECRET_ACCESS_KEY=... `
  SES_FROM_EMAIL=reminders@alerts.prohousingpgh.org `
  MAILCHIMP_API_KEY=... `
  MAILCHIMP_AUDIENCE_ID=9192ba01cf `
  MAILCHIMP_DEFAULT_MUNICIPALITY="City of Pittsburgh" `
  MAILCHIMP_MERGE_MUNICIPALITY=MUNI `
  MAILCHIMP_MERGE_NEIGHBORHOOD=HOOD `
  MAILCHIMP_MERGE_ZIP=ZIP
```

Optional (SMS, when ready):

```powershell
fly secrets set -a trash-reminders SNS_ORIGINATION_NUMBER=+1...
```

Then subscribe the SNS inbound topic to `https://trash-reminders.fly.dev/webhooks/sns`.

### 5. First deploy

```powershell
fly deploy -a trash-reminders
```

Or push to `main` and let GitHub Actions deploy.

Verify: https://trash-reminders.fly.dev/api/health

## Custom domain (optional)

```powershell
fly certs add reminders.prohousingpgh.org -a trash-reminders
```

Add the DNS records Fly shows, then update secrets:

```powershell
fly secrets set -a trash-reminders APP_BASE_URL=https://reminders.prohousingpgh.org
```

## CI/CD summary

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** | PR + push to `main` | Build frontend, compile Python |
| **Deploy** | Push to `main`, manual | `flyctl deploy --remote-only` |

## Local Docker smoke test

```powershell
docker build -t trash-reminders .
docker run --rm -p 8080:8080 -e DATABASE_PATH=/tmp/app.db trash-reminders
```

Open http://localhost:8080
