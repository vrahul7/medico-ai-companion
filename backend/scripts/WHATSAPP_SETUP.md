# WhatsApp Bot — 15-Minute Setup Guide

## Prerequisites
- ✅ FastAPI backend running (`uvicorn app.main:app --reload`)
- ✅ Free Twilio account at [twilio.com](https://twilio.com)
- ✅ ngrok installed at [ngrok.com/download](https://ngrok.com/download)

---

## Step 1 — Open Twilio WhatsApp Sandbox

1. Log in at **console.twilio.com**
2. Left sidebar → **Messaging** → **Try it out** → **Send a WhatsApp message**
3. You'll see your sandbox number: `+1-415-523-8886` and a join code like `join bright-tiger`

---

## Step 2 — Get Your Twilio Credentials

From the Twilio Console home page, copy:
- **Account SID** → looks like `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Auth Token** → hidden by default, click the eye icon

Open `backend/.env` and fill in:
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_actual_auth_token
```

---

## Step 3 — Add Approved Doctor Numbers

In `backend/.env`, add the WhatsApp number(s) you want to grant access to (E.164 format):
```
WHATSAPP_APPROVED_NUMBERS=+919876543210,+918765432109
```

> ⚠️ Use the full country code. India numbers start with `+91`.

---

## Step 4 — Start the Tunnel

1. Double-click `backend/scripts/start_tunnel.bat`
2. Copy the **HTTPS** URL it shows — e.g.: `https://abc123.ngrok-free.app`

---

## Step 5 — Set Webhook URL in Twilio

1. Twilio Console → **Messaging** → **Try WhatsApp** → **Sandbox settings** tab
2. Under **"When a message comes in"**, paste:
   ```
   https://abc123.ngrok-free.app/api/whatsapp/webhook
   ```
3. Set method to **POST**
4. Click **Save**

---

## Step 6 — Activate Your Number (One-Time)

From your WhatsApp, send this message to `+14155238886`:
```
join bright-tiger
```
(Use your actual code from the Twilio sandbox page)

You'll receive: *"You are now connected to the sandbox."*

---

## Step 7 — Send Your First Clinical Query!

WhatsApp `+14155238886` and send:
```
DDx for 4yo male with fever, wheeze, SpO2 94%, worse at night
```

You should receive a cited AI response within **5–8 seconds** 🎉

---

## Commands Available to Doctors

| Command | Response |
|---|---|
| Any clinical question | AI-synthesized answer with citations |
| `HELP` | Menu of available commands |
| `CLEAR` | Clears conversation history (new session) |
| `LIMIT` | Shows how many queries used today |

---

## Message Format

```
🩺 *Medico AI*
─────────────────────────
[2-3 paragraph clinical answer]

📚 *Sources:*
[1] Nelson Pediatrics, Ch.142, Emergency Management
    "...salbutamol 0.15mg/kg via nebuliser..."
[2] PubMed PMID 35147928 (2024)

─────────────────────────
_For clinical support only. Not medical advice._
```

---

## Rate Limits

- **Free tier**: 20 queries/day per WhatsApp number
- **Pro tier**: Unlimited (Supabase billing integration — coming soon)
- Resets daily at midnight IST

---

## Production Upgrade (Future)

When ready to move from sandbox to production:
1. Apply for **Meta WhatsApp Business API** verification (~3 days)
2. Get a dedicated Indian phone number (e.g., via Exotel/Kaleyra for HSM templates)
3. Swap credentials in `.env` — architecture remains identical
4. Remove the daily sandbox restart requirement

---

## Troubleshooting

| Issue | Fix |
|---|---|
| "Webhook verification failed" | Check ngrok URL is correct in Twilio console |
| No response on WhatsApp | Ensure `WHATSAPP_APPROVED_NUMBERS` includes your number with `+91` |
| "Access Restricted" message | Your number is not in the whitelist — add it to `.env` |
| Response truncated | Normal — WhatsApp has 1600 char limit, full answer in web UI |
