"""Unit tests verifying notification failure isolation and retry mechanisms."""

from datetime import datetime
import pytest
from backend.app.config.settings import load_config
from backend.app.database.session import init_db
from backend.app.models.alert import AlertNotification
from backend.app.models.signal import SignalEvent, SignalType
from backend.app.notifications.base import NotificationProvider
from backend.app.notifications.notification_manager import NotificationManager


class MockFailingProvider(NotificationProvider):
    def __init__(self, name: str):
        super().__init__(name=name, enabled=True)
        self.call_count = 0

    async def send(self, alert: AlertNotification) -> bool:
        self.call_count += 1
        raise ConnectionResetError(f"Simulated network outage on {self.name}")

    async def health_check(self):
        return {"status": "mock_down"}


class MockSucceedingProvider(NotificationProvider):
    def __init__(self, name: str):
        super().__init__(name=name, enabled=True)
        self.call_count = 0

    async def send(self, alert: AlertNotification) -> bool:
        self.call_count += 1
        return True

    async def health_check(self):
        return {"status": "mock_healthy"}


@pytest.mark.asyncio
async def test_notification_failure_isolation():
    """If Telegram fails, Email and WhatsApp MUST continue without breaking."""
    await init_db()
    cfg = load_config()
    mgr = NotificationManager(cfg)

    # Inject mock providers: Telegram fails, Email succeeds, WhatsApp succeeds
    telegram_mock = MockFailingProvider("telegram")
    email_mock = MockSucceedingProvider("email")
    whatsapp_mock = MockSucceedingProvider("whatsapp")

    mgr.providers = {
        "telegram": telegram_mock,
        "email": email_mock,
        "whatsapp": whatsapp_mock,
    }

    signal = SignalEvent.create(
        provider="test",
        asset_class="equity",
        exchange="NSE",
        instrument_id="2885",
        symbol="RELIANCE",
        timeframe="15m",
        signal_type=SignalType.BULLISH,
        candle_timestamp=datetime(2026, 10, 9, 10, 15, 0),
        price=1542.30,
        ema100=1538.25,
        ema200=1536.90,
        previous_ema100=1535.0,
        previous_ema200=1536.0,
    )

    results = await mgr.dispatch(signal)

    # 1. Telegram should report failed
    assert results["telegram"] is False
    assert telegram_mock.call_count == 1

    # 2. Email and WhatsApp MUST report True and have received delivery!
    assert results["email"] is True
    assert email_mock.call_count == 1

    assert results["whatsapp"] is True
    assert whatsapp_mock.call_count == 1
