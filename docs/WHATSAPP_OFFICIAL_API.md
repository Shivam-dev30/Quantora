# Official WhatsApp Provider Architecture & Setup Guide

## 1. Compliance & Security Notice
This platform strictly interfaces **ONLY** with official, approved Meta/WhatsApp Cloud APIs or Twilio APIs.

### 🚫 Prohibited Methods
We do **NOT** use and strongly advise against:
- Unofficial WhatsApp Web automation (e.g. Selenium, Puppeteer)
- QR-code session scrapers or headless Chromium hacks
- Reverse-engineered protocol libraries (e.g. Baileys, yowsup, venom-bot)

Using unofficial methods violates WhatsApp Terms of Service and regularly results in permanent phone number bans.

---

## 2. Meta WhatsApp Cloud API Pricing & Free-Tier Availability

### Official Free Tier
- **1,000 Free Service Conversations per Month**:
  Meta grants each WhatsApp Business Account (WABA) 1,000 free **service conversations** each month across all business phone numbers.
- **Service vs Utility Conversations**:
  - *Service conversations* are user-initiated (a user sends a message to the bot, opening a 24-hour service window where bot responses are 100% free).
  - *Business-initiated alert notifications* (sending an alert proactively without prior user message within 24h) are classified by Meta as **Utility Conversations**.

### Commercial Pricing (Utility Conversations)
- For proactive alerts initiated by the system, Meta charges a low per-conversation fee:
  - **India (IN)**: Approximately ₹0.12 to ₹0.35 per 24-hour conversation window.
  - **USA/Europe**: Approximately $0.005 to $0.035 per 24-hour conversation window.
- Once a conversation window is opened, all subsequent alert messages sent within that 24-hour period incur **zero additional cost**.

---

## 3. Configuring Meta WhatsApp Cloud API

1. Go to the [Meta for Developers Portal](https://developers.facebook.com/).
2. Create an App under **Business** type and add the **WhatsApp** product.
3. In the WhatsApp Getting Started page:
   - Note down your **Phone Number ID**.
   - Generate a System User **Permanent Access Token** with `whatsapp_business_messaging` permissions.
4. Set in `.env`:
   ```env
   WHATSAPP_ENABLED=true
   WHATSAPP_PROVIDER=meta_cloud
   WHATSAPP_PHONE_NUMBER_ID=109283746592834
   WHATSAPP_ACCESS_TOKEN=EAA...
   WHATSAPP_RECIPIENT_PHONE=+919876543210
   ```

---

## 4. Alternative: Twilio WhatsApp API
For enterprise teams already utilizing Twilio:
1. Register at [Twilio Console](https://console.twilio.com) and enable the WhatsApp Sandbox or approved Sender.
2. Set in `.env`:
   ```env
   WHATSAPP_ENABLED=true
   WHATSAPP_PROVIDER=twilio
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
   TWILIO_FROM_PHONE=whatsapp:+14155238886
   TWILIO_TO_PHONE=whatsapp:+919876543210
   ```
