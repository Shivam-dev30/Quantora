"""Official WhatsApp Business Cloud API and Twilio API Notification Provider."""

import asyncio
from typing import Any, Dict, Optional
import httpx
from backend.app.config.settings import WhatsAppConfig
from backend.app.core.exceptions import NotificationError
from backend.app.core.logging import get_logger
from backend.app.models.alert import AlertNotification
from backend.app.notifications.base import NotificationProvider
from backend.app.notifications.formatter import AlertFormatter

logger = get_logger("whatsapp_notifier")


class WhatsAppProvider(NotificationProvider):
    """
    Legitimate official WhatsApp provider utilizing Meta Cloud API or Twilio.
    Strictly adheres to official APIs: NO web scrapers, NO browser automation, NO QR hacks.
    """

    def __init__(self, config: WhatsAppConfig) -> None:
        super().__init__(name="whatsapp", enabled=config.enabled)
        self.config = config
        self.provider_type = config.provider  # "meta_cloud" | "twilio"
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay_seconds

    @property
    def is_configured(self) -> bool:
        if self.provider_type == "meta_cloud":
            return bool(
                self.config.phone_number_id
                and self.config.access_token
                and self.config.recipient_phone
            )
        elif self.provider_type == "twilio":
            return bool(
                self.config.twilio_account_sid
                and self.config.twilio_auth_token
                and self.config.twilio_from_phone
                and self.config.twilio_to_phone
            )
        return False

    async def send(self, alert: AlertNotification) -> bool:
        if not self.enabled:
            return False

        if not self.is_configured:
            logger.warning("WhatsApp alert skipped: Official API credentials not configured.")
            return False

        text_message = AlertFormatter.format_text(alert)

        if self.provider_type == "meta_cloud":
            return await self._send_meta_cloud(text_message)
        else:
            return await self._send_twilio(text_message)

    async def _send_meta_cloud(self, text: str) -> bool:
        """Send message using official Meta WhatsApp Cloud API."""
        url = f"https://graph.facebook.com/v20.0/{self.config.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.config.recipient_phone,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code in (200, 201):
                        logger.info(f"Official Meta WhatsApp alert sent successfully (attempt {attempt}).")
                        return True
                    logger.error(f"Meta WhatsApp Cloud API error {resp.status_code}: {resp.text}")
            except httpx.HTTPError as e:
                logger.warning(f"Meta WhatsApp network error (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)

        raise NotificationError("Failed to deliver WhatsApp message via Meta Cloud API.")

    async def _send_twilio(self, text: str) -> bool:
        """Send message using official Twilio WhatsApp API."""
        sid = self.config.twilio_account_sid
        token = self.config.twilio_auth_token
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

        from_phone = self.config.twilio_from_phone or ""
        if not from_phone.startswith("whatsapp:"):
            from_phone = f"whatsapp:{from_phone}"

        to_phone = self.config.twilio_to_phone or ""
        if not to_phone.startswith("whatsapp:"):
            to_phone = f"whatsapp:{to_phone}"

        data = {
            "From": from_phone,
            "To": to_phone,
            "Body": text,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(auth=(sid or "", token or ""), timeout=12.0) as client:
                    resp = await client.post(url, data=data)
                    if resp.status_code in (200, 201):
                        logger.info(f"Twilio WhatsApp alert sent successfully (attempt {attempt}).")
                        return True
                    logger.error(f"Twilio WhatsApp API error {resp.status_code}: {resp.text}")
            except httpx.HTTPError as e:
                logger.warning(f"Twilio WhatsApp network error (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)

        raise NotificationError("Failed to deliver WhatsApp message via Twilio.")

    async def health_check(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"channel": "whatsapp", "status": "disabled"}
        if not self.is_configured:
            return {"channel": "whatsapp", "status": "unconfigured"}
        return {
            "channel": "whatsapp",
            "provider": self.provider_type,
            "status": "configured",
            "official_api": True,
        }
