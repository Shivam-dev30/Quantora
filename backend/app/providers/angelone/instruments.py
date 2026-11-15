"""Angel One Instrument Master downloader, parser, and categorizer."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiofiles
import httpx
from backend.app.core.logging import get_logger
from backend.app.models.instrument import AssetClass, InstrumentDefinition

logger = get_logger("angelone_instruments")

SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
FALLBACK_SCRIP_MASTER_URL = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"
CACHE_DIR = Path("data")
CACHE_FILE = CACHE_DIR / "angel_scrip_master.json"


class AngelOneInstrumentService:
    """Fetches, parses, and normalizes Angel One instruments across Equity, F&O, and Commodities."""

    def __init__(self, cache_file: Path = CACHE_FILE, cache_ttl_hours: int = 168) -> None:
        self.cache_file = cache_file
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._instruments: List[InstrumentDefinition] = []

    def _classify_asset_class(self, exch_seg: str, instrument_type: str, symbol: str) -> Optional[AssetClass]:
        """Classify raw Angel One scrip into standard AssetClass."""
        exch = exch_seg.upper()
        itype = (instrument_type or "").upper()

        if exch == "NSE":
            return "equity"

        if exch == "BSE":
            return "equity"

        if exch in ("NFO", "BFO"):
            if itype in ("FUTIDX", "FUTSTK", "FUTCOM", "FUTCUR"):
                return "equity_futures"
            if itype in ("OPTIDX", "OPTSTK", "OPTCOM", "OPTCUR") or symbol.endswith("CE") or symbol.endswith("PE"):
                return "equity_options"
            return "equity_futures"

        if exch in ("MCX", "NCDEX"):
            # Exclude all Options (OPTCOM, OPTFUT, OPTIDX, CE, PE) - Commodities support Futures only
            if (
                itype in ("OPTCOM", "OPTFUT", "OPTIDX", "OPTCUR")
                or symbol.endswith("CE")
                or symbol.endswith("PE")
            ):
                return None
            if itype in ("FUTCOM", "FUTIDX") or symbol.endswith("FUT"):
                return "commodity"
            return "commodity"

        return None

    def _normalize_raw_item(self, item: Dict[str, Any]) -> Optional[InstrumentDefinition]:
        """Convert Angel One JSON item into normalized InstrumentDefinition."""
        token = str(item.get("token", "")).strip()
        symbol = str(item.get("symbol", "")).strip()
        exch_seg = str(item.get("exch_seg", "")).strip()
        instrument_type = str(item.get("instrumenttype", "")).strip()
        name = str(item.get("name", "")).strip()

        if not token or not symbol or not exch_seg:
            return None

        asset_class = self._classify_asset_class(exch_seg, instrument_type, symbol)
        if not asset_class:
            return None

        # Expiry handling
        expiry_raw = item.get("expiry", "")
        expiry = str(expiry_raw).strip() if expiry_raw else None

        # Strike handling
        strike_raw = item.get("strike", "-1")
        strike = None
        try:
            val = float(strike_raw)
            if val > 0:
                # Angel One strikes are often in paise or standard currency
                strike = val / 100.0 if val > 100000 else val
        except (ValueError, TypeError):
            pass

        # Option type
        option_type = None
        if asset_class == "equity_options":
            if symbol.endswith("CE"):
                option_type = "CE"
            elif symbol.endswith("PE"):
                option_type = "PE"

        # Lot size & tick size
        lot_size = 1
        try:
            lot_size = int(item.get("lotsize", 1))
        except (ValueError, TypeError):
            pass

        tick_size = 0.05
        try:
            ts = float(item.get("tick_size", 0.05))
            if ts > 0:
                tick_size = ts / 100.0 if ts >= 5.0 else ts
        except (ValueError, TypeError):
            pass

        return InstrumentDefinition(
            provider="angelone",
            exchange=exch_seg,
            symbol=symbol,
            instrument_id=token,
            name=name or symbol.split("-")[0],
            asset_class=asset_class,
            instrument_type=instrument_type or "EQUITY",
            expiry=expiry,
            strike=strike,
            option_type=option_type,
            lot_size=lot_size,
            tick_size=tick_size,
            is_active=True,
            underlying=name,
        )

    async def fetch_instruments(self, force_refresh: bool = False) -> List[InstrumentDefinition]:
        """Fetch instruments from local cache or official Angel One Scrip Master URL."""
        if not force_refresh and self.cache_file.exists():
            mtime = datetime.fromtimestamp(self.cache_file.stat().st_mtime)
            if datetime.now() - mtime < self.cache_ttl:
                try:
                    logger.info(f"Loading Angel One instruments from local cache: {self.cache_file}")
                    async with aiofiles.open(self.cache_file, "r", encoding="utf-8") as f:
                        content = await f.read()
                        raw_data = json.loads(content)
                        self._instruments = self._parse_raw_list(raw_data)
                        if self._instruments:
                            logger.info(f"Loaded {len(self._instruments)} cached Angel One instruments.")
                            return self._instruments
                except Exception as e:
                    logger.warning(f"Failed to read cached instrument file: {e}. Downloading fresh.")

        # Download from Angel One
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        for url in [SCRIP_MASTER_URL, FALLBACK_SCRIP_MASTER_URL]:
            try:
                logger.info(f"Downloading Angel One Scrip Master from {url} ...")
                async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        raw_data = resp.json()
                        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                        async with aiofiles.open(self.cache_file, "w", encoding="utf-8") as f:
                            await f.write(json.dumps(raw_data))

                        self._instruments = self._parse_raw_list(raw_data)
                        logger.info(f"Successfully downloaded and parsed {len(self._instruments)} Angel One instruments.")
                        return self._instruments
                    else:
                        logger.warning(f"HTTP {resp.status_code} fetching Scrip Master from {url}.")
            except Exception as e:
                logger.warning(f"Failed to fetch Angel One Scrip Master from {url}: {e}")

        # If download fails or in offline environment, load high-liquidity seed instruments
        self._instruments = self._get_seed_instruments()
        return self._instruments

    def _parse_raw_list(self, raw_data: List[Dict[str, Any]]) -> List[InstrumentDefinition]:
        parsed = []
        for item in raw_data:
            normalized = self._normalize_raw_item(item)
            if normalized:
                parsed.append(normalized)
        return parsed

    def _get_seed_instruments(self) -> List[InstrumentDefinition]:
        """High-liquidity seed instruments across NSE Equity, NFO Futures/Options, and MCX Commodity."""
        return [
            # NSE Equity
            InstrumentDefinition(
                provider="angelone",
                exchange="NSE",
                symbol="RELIANCE-EQ",
                instrument_id="2885",
                name="RELIANCE",
                asset_class="equity",
                instrument_type="EQUITY",
                lot_size=1,
                tick_size=0.05,
            ),
            InstrumentDefinition(
                provider="angelone",
                exchange="NSE",
                symbol="TCS-EQ",
                instrument_id="11536",
                name="TCS",
                asset_class="equity",
                instrument_type="EQUITY",
                lot_size=1,
                tick_size=0.05,
            ),
            InstrumentDefinition(
                provider="angelone",
                exchange="NSE",
                symbol="INFY-EQ",
                instrument_id="1594",
                name="INFY",
                asset_class="equity",
                instrument_type="EQUITY",
                lot_size=1,
                tick_size=0.05,
            ),
            InstrumentDefinition(
                provider="angelone",
                exchange="NSE",
                symbol="HDFCBANK-EQ",
                instrument_id="1333",
                name="HDFCBANK",
                asset_class="equity",
                instrument_type="EQUITY",
                lot_size=1,
                tick_size=0.05,
            ),
            InstrumentDefinition(
                provider="angelone",
                exchange="NSE",
                symbol="SBIN-EQ",
                instrument_id="3045",
                name="SBIN",
                asset_class="equity",
                instrument_type="EQUITY",
                lot_size=1,
                tick_size=0.05,
            ),
            InstrumentDefinition(
                provider="angelone",
                exchange="NSE",
                symbol="ICICIBANK-EQ",
                instrument_id="4963",
                name="ICICIBANK",
                asset_class="equity",
                instrument_type="EQUITY",
                lot_size=1,
                tick_size=0.05,
            ),
            # NFO Futures
            InstrumentDefinition(
                provider="angelone",
                exchange="NFO",
                symbol="NIFTY26OCTFUT",
                instrument_id="35001",
                name="NIFTY",
                asset_class="equity_futures",
                instrument_type="FUTIDX",
                expiry="29OCT2026",
                lot_size=25,
                tick_size=0.05,
                underlying="NIFTY",
            ),
            InstrumentDefinition(
                provider="angelone",
                exchange="NFO",
                symbol="BANKNIFTY26OCTFUT",
                instrument_id="35002",
                name="BANKNIFTY",
                asset_class="equity_futures",
                instrument_type="FUTIDX",
                expiry="29OCT2026",
                lot_size=15,
                tick_size=0.05,
                underlying="BANKNIFTY",
            ),
            # NFO Options
            InstrumentDefinition(
                provider="angelone",
                exchange="NFO",
                symbol="NIFTY26OCT25000CE",
                instrument_id="45001",
                name="NIFTY",
                asset_class="equity_options",
                instrument_type="OPTIDX",
                expiry="29OCT2026",
                strike=25000.0,
                option_type="CE",
                lot_size=25,
                tick_size=0.05,
                underlying="NIFTY",
            ),
            # MCX Commodity Futures
            InstrumentDefinition(
                provider="angelone",
                exchange="MCX",
                symbol="CRUDEOIL19OCTFUT",
                instrument_id="230001",
                name="CRUDEOIL",
                asset_class="commodity",
                instrument_type="FUTCOM",
                expiry="19OCT2026",
                lot_size=100,
                tick_size=1.0,
                underlying="CRUDEOIL",
            ),
            InstrumentDefinition(
                provider="angelone",
                exchange="MCX",
                symbol="NATURALGAS26OCTFUT",
                instrument_id="230002",
                name="NATURALGAS",
                asset_class="commodity",
                instrument_type="FUTCOM",
                expiry="26OCT2026",
                lot_size=1250,
                tick_size=0.1,
                underlying="NATURALGAS",
            ),
            InstrumentDefinition(
                provider="angelone",
                exchange="MCX",
                symbol="GOLD05DECFUT",
                instrument_id="230003",
                name="GOLD",
                asset_class="commodity",
                instrument_type="FUTCOM",
                expiry="05DEC2026",
                lot_size=100,
                tick_size=1.0,
                underlying="GOLD",
            ),
            InstrumentDefinition(
                provider="angelone",
                exchange="MCX",
                symbol="SILVER05DECFUT",
                instrument_id="230004",
                name="SILVER",
                asset_class="commodity",
                instrument_type="FUTCOM",
                expiry="05DEC2026",
                lot_size=30,
                tick_size=1.0,
                underlying="SILVER",
            ),
        ]
