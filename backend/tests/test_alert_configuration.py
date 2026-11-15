"""Tests for dynamic Alert Configuration and Available Instruments API."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import create_app, app_state
from backend.app.config.settings import get_config
from backend.app.market_data.instrument_manager import InstrumentManager
from backend.app.market_data.stream_manager import StreamManager
from backend.app.models.instrument import InstrumentDefinition


@pytest.fixture
def test_app():
    return create_app()


@pytest.mark.asyncio
async def test_alert_endpoints_lifecycle(test_app):
    cfg = get_config()
    inst_mgr = InstrumentManager(cfg)
    
    # Register mock instruments
    inst_mgr.register_instruments("delta", [
        InstrumentDefinition(
            provider="delta",
            exchange="DELTA",
            symbol="BTCUSD",
            instrument_id="139",
            name="Bitcoin Perpetual",
            asset_class="crypto",
            instrument_type="PERPETUAL_FUTURES",
            is_active=True,
        ),
        InstrumentDefinition(
            provider="delta",
            exchange="DELTA",
            symbol="STRKUSD",
            instrument_id="2001",
            name="Starknet Perpetual",
            asset_class="crypto",
            instrument_type="PERPETUAL_FUTURES",
            is_active=True,
        ),
    ])
    
    inst_mgr.register_instruments("angelone", [
        InstrumentDefinition(
            provider="angelone",
            exchange="NSE",
            symbol="RELIANCE-EQ",
            instrument_id="2885",
            name="RELIANCE",
            asset_class="equity",
            instrument_type="EQUITY",
            is_active=True,
        ),
    ])

    inst_mgr.resolve_monitored_universe()
    app_state.instrument_manager = inst_mgr
    app_state.config = cfg

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # 1. Test Available Instruments endpoint
        resp = await client.get("/api/available-instruments")
        assert resp.status_code == 200
        data = resp.json()
        assert "crypto" in data["instruments"]
        assert "equity" in data["instruments"]
        crypto_syms = [c["symbol"] for c in data["instruments"]["crypto"]]
        assert "BTCUSD" in crypto_syms
        assert "STRKUSD" in crypto_syms

        # 2. Test Active Alerts endpoint
        resp_active = await client.get("/api/active-alerts")
        assert resp_active.status_code == 200
        active_data = resp_active.json()
        assert active_data["strategy"]["ema_fast"] == 100
        assert active_data["strategy"]["ema_slow"] == 200
