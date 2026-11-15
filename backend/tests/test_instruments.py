"""Unit tests for Instrument Manager, symbol filtering, and F&O expiry resolution."""

import pytest
from backend.app.config.settings import FullSystemConfig, MarketConfig, load_config
from backend.app.market_data.instrument_manager import InstrumentManager
from backend.app.models.instrument import InstrumentDefinition
from backend.app.providers.angelone.instruments import AngelOneInstrumentService
from backend.app.providers.delta.client import DeltaClient


def test_angel_one_scrip_classification():
    """Verify Angel One instrument categorization across equity, F&O, and commodity."""
    service = AngelOneInstrumentService()

    # Cash Equity
    eq = service._normalize_raw_item({
        "token": "2885",
        "symbol": "RELIANCE-EQ",
        "name": "RELIANCE",
        "exch_seg": "NSE",
        "instrumenttype": "",
    })
    assert eq is not None
    assert eq.asset_class == "equity"
    assert eq.exchange == "NSE"

    # Index Futures
    fut = service._normalize_raw_item({
        "token": "35001",
        "symbol": "NIFTY29OCT26FUT",
        "name": "NIFTY",
        "exch_seg": "NFO",
        "instrumenttype": "FUTIDX",
        "expiry": "29OCT2026",
    })
    assert fut is not None
    assert fut.asset_class == "equity_futures"
    assert fut.expiry == "29OCT2026"

    # Index Option
    opt = service._normalize_raw_item({
        "token": "45001",
        "symbol": "NIFTY29OCT2625000CE",
        "name": "NIFTY",
        "exch_seg": "NFO",
        "instrumenttype": "OPTIDX",
        "expiry": "29OCT2026",
        "strike": "2500000.000000",
    })
    assert opt is not None
    assert opt.asset_class == "equity_options"
    assert opt.option_type == "CE"
    assert opt.strike == 25000.0

    # Commodity Futures
    comm = service._normalize_raw_item({
        "token": "230001",
        "symbol": "CRUDEOIL19OCTFUT",
        "name": "CRUDEOIL",
        "exch_seg": "MCX",
        "instrumenttype": "FUTCOM",
        "expiry": "19OCT2026",
    })
    assert comm is not None
    assert comm.asset_class == "commodity"
    assert comm.exchange == "MCX"


def test_instrument_manager_universe_filtering():
    """Verify resolution of configured symbols and expiry modes."""
    cfg = load_config()
    mgr = InstrumentManager(cfg)

    seed_angel = AngelOneInstrumentService()._get_seed_instruments()
    seed_delta = DeltaClient()._get_seed_instruments()

    mgr.register_instruments("angelone", seed_angel)
    mgr.register_instruments("delta", seed_delta)

    monitored = mgr.resolve_monitored_universe()
    assert len(monitored) > 0

    monitored_symbols = {i.symbol for i in monitored}
    # Check that RELIANCE is included
    assert "RELIANCE-EQ" in monitored_symbols
    # Check that BTCUSD is included
    assert "BTCUSD" in monitored_symbols
