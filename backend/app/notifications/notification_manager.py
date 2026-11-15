"""Notification Manager coordinating channel dispatches with strict failure isolation."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.app.config.settings import FullSystemConfig
from backend.app.core.logging import get_logger
from backend.app.core.market_hours import MarketHoursManager
from backend.app.database.models import NotificationDeliveryModel
from backend.app.database.session import get_db_session
from backend.app.models.alert import AlertNotification, NotificationDetailMode
from backend.app.models.signal import SignalEvent
from backend.app.notifications.base import NotificationProvider
from backend.app.notifications.email import EmailProvider
from backend.app.notifications.telegram import TelegramProvider
from backend.app.notifications.whatsapp import WhatsAppProvider

logger = get_logger("notification_manager")


class NotificationManager:
    """Dispatches alerts concurrently across all enabled channels with complete failure isolation."""

    def __init__(self, config: FullSystemConfig) -> None:
        self.config = config
        self.market_hours = MarketHoursManager(
            display_tz=config.display.get("timezone", "Asia/Kolkata"),
            respect_hours=config.market_hours.get("respect_exchange_hours", True),
        )

        # Initialize providers
        self.providers: Dict[str, NotificationProvider] = {
            "telegram": TelegramProvider(config.notifications.telegram),
            "email": EmailProvider(config.notifications.email),
            "whatsapp": WhatsAppProvider(config.notifications.whatsapp),
        }
        self.detail_mode = NotificationDetailMode(config.notifications.detail_mode)
        self.currency_map = config.display.get("currency_symbols", {})

    def _prepare_alert(
        self,
        signal: SignalEvent,
        current_price: Optional[float] = None,
        drift_points: Optional[float] = None,
        drift_percent: Optional[float] = None,
        elapsed_time_str: Optional[str] = None,
    ) -> AlertNotification:
        """Create formatted AlertNotification object from SignalEvent."""
        curr_sym = self.currency_map.get(signal.exchange.upper(), "₹" if signal.exchange != "DELTA" else "$")

        # Market display name
        market_display_map = {
            "equity": "Indian Equity",
            "equity_futures": "Indian Equity Futures",
            "equity_options": "Indian Equity Options",
            "commodity": "Indian Commodity",
            "crypto": "Cryptocurrency",
        }
        market_name = market_display_map.get(signal.asset_class, signal.asset_class.title())

        # Formatted values
        formatted_price = f"{curr_sym}{signal.price:,.2f}"
        formatted_ema100 = f"{curr_sym}{signal.ema100:,.2f}"
        formatted_ema200 = f"{curr_sym}{signal.ema200:,.2f}"
        formatted_prev_100 = f"{curr_sym}{signal.previous_ema100:,.2f}"
        formatted_prev_200 = f"{curr_sym}{signal.previous_ema200:,.2f}"
        formatted_current_price = f"{curr_sym}{current_price:,.2f}" if current_price is not None else None

        display_time = self.market_hours.to_display_time(signal.candle_timestamp)

        return AlertNotification(
            signal=signal,
            detail_mode=self.detail_mode,
            display_time=display_time,
            currency_symbol=curr_sym,
            formatted_price=formatted_price,
            formatted_ema100=formatted_ema100,
            formatted_ema200=formatted_ema200,
            formatted_prev_ema100=formatted_prev_100,
            formatted_prev_ema200=formatted_prev_200,
            market_display_name=market_name,
            current_price=current_price,
            formatted_current_price=formatted_current_price,
            drift_points=drift_points,
            drift_percent=drift_percent,
            elapsed_time_str=elapsed_time_str,
        )

    async def dispatch(
        self,
        signal: SignalEvent,
        current_price: Optional[float] = None,
        drift_points: Optional[float] = None,
        drift_percent: Optional[float] = None,
        elapsed_time_str: Optional[str] = None,
    ) -> Dict[str, bool]:
        """Dispatch alert concurrently to all active notification providers."""
        alert = self._prepare_alert(
            signal,
            current_price=current_price,
            drift_points=drift_points,
            drift_percent=drift_percent,
            elapsed_time_str=elapsed_time_str,
        )
        results: Dict[str, bool] = {}

        tasks = []
        for name, provider in self.providers.items():
            if provider.enabled:
                tasks.append(self._dispatch_channel(name, provider, alert))

        if not tasks:
            logger.info(f"No notification channels enabled for signal {signal.signal_id}.")
            return results

        # Run all channel deliveries concurrently without blocking each other
        delivered = await asyncio.gather(*tasks, return_exceptions=True)
        for res in delivered:
            if isinstance(res, tuple):
                chan_name, success = res
                results[chan_name] = success

        return results

    async def _dispatch_channel(
        self, channel_name: str, provider: NotificationProvider, alert: AlertNotification
    ) -> tuple[str, bool]:
        """Execute delivery on a single channel and log delivery status to DB."""
        sig_id = alert.signal.signal_id
        error_msg: Optional[str] = None
        status = "PENDING"
        attempts = 1

        try:
            success = await provider.send(alert)
            status = "SENT" if success else "FAILED"
            return (channel_name, success)
        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            logger.error(f"Notification failure on {channel_name} for signal {sig_id}: {e}")
            return (channel_name, False)
        finally:
            # Persist delivery attempt in notification_deliveries table
            try:
                async with get_db_session() as session:
                    delivery = NotificationDeliveryModel(
                        signal_id=sig_id,
                        channel=channel_name,
                        status=status,
                        attempt_count=attempts,
                        error_message=error_msg,
                        sent_at=datetime.utcnow() if status == "SENT" else None,
                    )
                    session.add(delivery)
                    await session.commit()
            except Exception as db_err:
                logger.error(f"Error persisting delivery record to DB: {db_err}")

    async def get_health_status(self) -> Dict[str, Any]:
        """Collect health status across all configured channels."""
        health = {}
        for name, provider in self.providers.items():
            health[name] = await provider.health_check()
        return health
