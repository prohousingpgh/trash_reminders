# Mailchimp newsletter signup

When someone signs up for **email pickup reminders**, they can optionally (checked by default) join the **Pro-Housing Pittsburgh** email list. That uses Mailchimp — completely separate from Amazon SES verification and reminder emails.

## 1. Get your audience ID

1. Log in to [Mailchimp](https://mailchimp.com).
2. Go to **Audience** → **All contacts**.
3. **Settings** → **Audience name and defaults**.
4. Copy the **Audience ID** (looks like `a1b2c3d4e5`).

## 2. Create an API key

1. Profile icon → **Account & billing** → **Extras** → **API keys**.
2. Create a key. It looks like `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-us19`.
3. The suffix after the last hyphen (`us19`) is your datacenter — the app reads this automatically.

## 3. Add to `.env`

```env
MAILCHIMP_API_KEY=your-key-us19
MAILCHIMP_AUDIENCE_ID=your-audience-id
```

Restart the API. Check:

```powershell
curl http://127.0.0.1:8000/api/health
```

You should see `"mailchimp": { "configured": true, ... }`.

## 4. Merge fields (municipality, neighborhood, zip)

On signup, the app sends these **merge fields** with each new subscriber:

| Data | Default Mailchimp tag | Source |
|------|----------------------|--------|
| Municipality | `MUNICIPAL` | `City of Pittsburgh` (configurable) |
| Neighborhood | `NEIGHBORHO` | pgh.st `hood` for the registered address |
| Zip code | `ZIPCODE` | Address ZIP from signup |

Create matching fields in Mailchimp:

1. **Audience** → **Settings** → **Audience fields and *|MERGE|* tags**.
2. Add three **Text** fields with tags exactly **`MUNICIPAL`**, **`NEIGHBORHO`**, and **`ZIPCODE`** (or change the tags in `.env` to match fields you already use).

Optional `.env` overrides:

```env
MAILCHIMP_DEFAULT_MUNICIPALITY=City of Pittsburgh
MAILCHIMP_MERGE_MUNICIPALITY=MUNICIPAL
MAILCHIMP_MERGE_NEIGHBORHOOD=NEIGHBORHO
MAILCHIMP_MERGE_ZIP=ZIPCODE
```

If tags in Mailchimp do not match, signup to Mailchimp will fail (pickup reminders still work). Check API logs for Mailchimp error details.

## 5. Double opt-in

If your Mailchimp audience requires **double opt-in**, Mailchimp may send its own confirmation email when someone is added. The pickup-reminder verification email (SES) is still separate.

For a single opt-in audience, members are added with status `subscribed` when they submit the form with the box checked.

## 6. Production

Set the same secrets on Fly.io:

```powershell
fly secrets set MAILCHIMP_API_KEY=... MAILCHIMP_AUDIENCE_ID=...
```

Pickup reminder signup succeeds even if Mailchimp fails; the user sees a note if newsletter signup could not be completed.
