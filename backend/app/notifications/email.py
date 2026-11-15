"""SMTP Asynchronous Email Notification Provider."""

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional
import aiosmtplib
from backend.app.config.settings import EmailConfig
from backend.app.core.exceptions import NotificationError
from backend.app.core.logging import get_logger
from backend.app.models.alert import AlertNotification
from backend.app.models.signal import SignalType
from backend.app.notifications.base import NotificationProvider
from backend.app.notifications.formatter import AlertFormatter

logger = get_logger("email_notifier")


class EmailProvider(NotificationProvider):
    """Sends rich HTML & plain text market alerts via asynchronous SMTP."""

    def __init__(self, config: EmailConfig) -> None:
        super().__init__(name="email", enabled=config.enabled)
        self.config = config
        self.host = config.smtp_host
        self.port = config.smtp_port
        self.username = config.smtp_username
        self.password = config.smtp_password
        self.email_from = config.email_from
        self.email_to = config.email_to
        self.use_tls = config.smtp_use_tls
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.email_from and self.email_to)

    async def send(self, alert: AlertNotification) -> bool:
        if not self.enabled:
            return False

        if not self.is_configured:
            logger.warning("Email alert skipped: SMTP configuration incomplete.")
            return False

        sig = alert.signal
        direction = "Bullish Crossover" if sig.signal_type == SignalType.BULLISH else "Bearish Crossover"
        subject = f"[EMA ALERT] {sig.symbol} | {direction} | {sig.timeframe}"

        # Construct multipart MIME message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = self.email_to

        plain_text = AlertFormatter.format_text(alert)
        html_text = AlertFormatter.format_html(alert)

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_text, "html", "utf-8"))

        for attempt in range(1, self.max_retries + 1):
            try:
                # Use starttls for port 587, direct tls for port 465
                start_tls = self.use_tls and self.port == 587
                use_tls = self.use_tls and self.port == 465

                await aiosmtplib.send(
                    msg,
                    hostname=self.host,
                    port=self.port,
                    username=self.username or None,
                    password=self.password or None,
                    start_tls=start_tls,
                    use_tls=use_tls,
                    timeout=15.0,
                )
                logger.info(f"Email alert sent successfully for {sig.symbol} (attempt {attempt}).")
                return True

            except Exception as e:
                logger.warning(f"Email delivery failed (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)

        raise NotificationError(f"Failed to deliver Email alert after {self.max_retries} attempts.")

    async def health_check(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"channel": "email", "status": "disabled"}
        if not self.is_configured:
            return {"channel": "email", "status": "unconfigured"}

        try:
            # Simple connection check
            smtp = aiosmtplib.SMTP(hostname=self.host, port=self.port, timeout=5.0)
            await smtp.connect()
            await smtp.quit()
            return {"channel": "email", "status": "healthy", "host": self.host, "port": self.port}
        except Exception as e:
            return {"channel": "email", "status": "unhealthy", "message": str(e)}
