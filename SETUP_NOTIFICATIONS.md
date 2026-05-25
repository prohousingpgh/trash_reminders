# Email & SMS setup (Amazon SES + SNS)

Reminders use **Amazon SES** for email and **Amazon SNS** for SMS. One AWS account covers both.

## 1. Create `.env`

```powershell
cd "c:\Users\david\Documents\Dev Projects\pghst-reminders"
copy .env.example .env
```

## 2. AWS credentials

Create an IAM user (or use a role on Fly.io) with this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ses:SendEmail", "ses:SendRawEmail"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "*"
    }
  ]
}
```

Add to `.env`:

```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
SES_FROM_EMAIL=reminders@yourdomain.com
```

On **Fly.io**, you can skip access keys and attach an IAM role with the same permissions instead.

## 3. Amazon SES (email)

1. Open [SES console](https://console.aws.amazon.com/ses/) in your chosen region (`AWS_REGION`)
2. **Verified identities** → verify your domain or a single email address
3. Set `SES_FROM_EMAIL` to that address (e.g. `reminders@yourdomain.com`)
4. New accounts are in **sandbox mode** — you can only send to verified addresses until you [request production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)

Verification and reminder emails link to `APP_BASE_URL` for confirm/unsubscribe.

## 4. Amazon SNS (SMS)

1. Open [SNS console](https://console.aws.amazon.com/sns/) in the same region
2. Ensure your account can send SMS ([SMS spending limits](https://console.aws.amazon.com/sns/v3/home#/mobile/text-messaging))
3. US transactional messages work without a custom origination number (AWS uses a shared sender)
4. For a **dedicated number** and **YES/STOP replies**, request a **two-way SMS origination number** in [AWS End User Messaging](https://console.aws.amazon.com/sms-voice/home) and set `SNS_ORIGINATION_NUMBER=+1412...`

### Inbound SMS (YES / STOP)

When using two-way SMS, configure AWS to publish inbound messages to an SNS topic, then subscribe your API:

| Environment | HTTPS endpoint |
|-------------|----------------|
| Production | `https://your-app.fly.dev/webhooks/sns` |
| Local | ngrok → `https://xxxx.ngrok.io/webhooks/sns` |

Protocol: **HTTPS**, POST. Confirm the subscription when AWS sends `SubscriptionConfirmation`.

Users reply **YES** to confirm SMS opt-in and **STOP** to unsubscribe.

Without two-way SMS, users can still confirm via the **“I replied YES”** button on the website after signup.

## 5. Install & restart

```powershell
.venv\Scripts\pip install -r requirements.txt
$env:PYTHONPATH = "."
.venv\Scripts\uvicorn api.main:app --reload --port 8000
```

Check status:

```powershell
curl http://127.0.0.1:8000/api/health
```

Expect `"provider": "aws"` and `"email_configured": true` when SES is set up.

## 6. Send test messages

```powershell
.venv\Scripts\python scripts\test_notifications.py --email you@example.com
.venv\Scripts\python scripts\test_notifications.py --phone 4125551234
```

In sandbox mode, the email must be a verified SES identity.

## 7. Production (Fly.io)

```powershell
fly secrets set `
  AWS_REGION=us-east-1 `
  AWS_ACCESS_KEY_ID=AKIA... `
  AWS_SECRET_ACCESS_KEY=... `
  SES_FROM_EMAIL=reminders@yourdomain.com `
  APP_BASE_URL=https://trash-reminders.fly.dev `
  ADMIN_PASSWORD=...
```

Subscribe your SNS inbound topic to `https://trash-reminders.fly.dev/webhooks/sns` if using two-way SMS.

## Costs (approximate)

| Service | Typical US cost |
|---------|-----------------|
| SES email | ~$0.10 per 1,000 emails |
| SNS SMS | ~$0.006–$0.02 per message |

AWS Free Tier includes limited SES messages for 12 months on new accounts.
