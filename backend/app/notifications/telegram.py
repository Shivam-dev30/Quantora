"""Telegram Bot Notification Provider."""

import asyncio
from typing import Any, Dict, Optional
import httpx
from backend.app.config.settings import TelegramConfig
from backend.app.core.exceptions import NotificationError
from backend.app.core.logging import get_logger
from backend.app.models.alert import AlertNotification
from backend.app.notifications.base import NotificationProvider
from backend.app.notifications.formatter import AlertFormatter

logger = get_logger("telegram_notifier")


class TelegramProvider(NotificationProvider):
    """Sends real-time market alerts to a configured Telegram chat or channel."""

    def __init__(self, config: TelegramConfig) -> None:
        super().__init__(name="telegram", enabled=config.enabled)
        self.config = config
        self.bot_token = config.bot_token
        self.chat_id = config.chat_id
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send(self, alert: AlertNotification) -> bool:
        if not self.enabled:
            return False

        if not self.is_configured:
            logger.warning("Telegram alert skipped: bot_token or chat_id not configured.")
            return False

        text_message = AlertFormatter.format_text(alert)
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text_message,
            "disable_web_page_preview": True,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)

                    if resp.status_code == 200:
                        logger.info(f"Telegram alert sent successfully for {alert.signal.symbol} (attempt {attempt}).")
                        return True

                    if resp.status_code == 429:
                        retry_after = float(resp.headers.get("Retry-After", self.retry_delay * attempt))
                        logger.warning(f"Telegram rate limited. Waiting {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue

                    logger.error(f"Telegram API HTTP error {resp.status_code}: {resp.text}")

            except httpx.HTTPError as e:
                logger.warning(f"Telegram network failure (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)

        raise NotificationError(f"Failed to deliver Telegram notification after {self.max_retries} attempts.")

    async def health_check(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"channel": "telegram", "status": "disabled"}
        if not self.is_configured:
            return {"channel": "telegram", "status": "unconfigured"}

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    bot_info = resp.json().get("result", {})
                    return {
                        "channel": "telegram",
                        "status": "healthy",
                        "bot_username": bot_info.get("username"),
                    }
                return {"channel": "telegram", "status": "unhealthy", "code": resp.status_code}
        except Exception as e:
            return {"channel": "telegram", "status": "error", "message": str(e)}
