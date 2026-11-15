"""Angel One SmartAPI REST client for historical candle fetching and session queries."""

import asyncio
from datetime import datetime, timedelta
import math
from typing import Any, Dict, List, Optional
import httpx
import pytz
from backend.app.core.exceptions import HistoricalDataError, RateLimitExceededError
from backend.app.core.logging import get_logger
from backend.app.models.candle import MarketCandle
from backend.app.models.instrument import InstrumentDefinition
from backend.app.providers.angelone.auth import AngelOneAuthManager

logger = get_logger("angelone_client")
IST = pytz.timezone("Asia/Kolkata")
UTC = pytz.UTC

INTERVAL_MAP = {
    "1m": "ONE_MINUTE",
    "3m": "THREE_MINUTE",
    "5m": "FIVE_MINUTE",
    "10m": "TEN_MINUTE",
    "15m": "FIFTEEN_MINUTE",
    "30m": "THIRTY_MINUTE",
    "1h": "ONE_HOUR",
    "1d": "ONE_DAY",
}


class AngelOneClient:
    """HTTP client interacting with Angel One SmartAPI historical candle endpoints."""

    def __init__(self, auth_manager: AngelOneAuthManager, max_retries: int = 3) -> None:
        self.auth = auth_manager
        self.max_retries = max_retries
        self._rate_limiter = asyncio.Semaphore(3)  # Respect max 3 concurrent requests

    async def get_historical_candles(
        self,
        instrument: InstrumentDefinition,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[MarketCandle]:
        """Fetch historical closed candles from SmartAPI or synthetic generator if unconfigured."""
        if not self.auth.is_configured:
            # Generate deterministic synthetic candles for warm-up in test/offline modes
            return self._generate_synthetic_candles(instrument, timeframe, start, end)

        interval = INTERVAL_MAP.get(timeframe.lower())
        if not interval:
            raise HistoricalDataError(f"Unsupported timeframe for Angel One: {timeframe}")

        # Convert start & end datetimes to IST string format: YYYY-MM-DD HH:MM
        start_ist = start.astimezone(IST) if start.tzinfo else IST.localize(start)
        end_ist = end.astimezone(IST) if end.tzinfo else IST.localize(end)

        from_date_str = start_ist.strftime("%Y-%m-%d %H:%M")
        to_date_str = end_ist.strftime("%Y-%m-%d %H:%M")

        payload = {
            "exchange": instrument.exchange,
            "symboltoken": instrument.instrument_id,
            "interval": interval,
            "fromdate": from_date_str,
            "todate": to_date_str,
        }

        url = f"{self.auth.base_url}/rest/secure/angelbroking/historical/v1/getCandleData"

        for attempt in range(1, self.max_retries + 1):
            async with self._rate_limiter:
                try:
                    await self.auth.get_valid_jwt()
                    headers = self.auth.get_auth_headers()

                    async with httpx.AsyncClient(timeout=20.0) as client:
                        resp = await client.post(url, json=payload, headers=headers)

                        if resp.status_code == 429:
                            wait_sec = 2.0 * attempt
                            logger.warning(f"Angel One rate limit hit, backing off {wait_sec}s...")
                            await asyncio.sleep(wait_sec)
                            continue

                        data = resp.json()
                        if resp.status_code != 200 or not data.get("status"):
                            error_msg = data.get("message", "Historical data request failed")
                            logger.error(f"Angel One historical candle error: {error_msg}")
                            raise HistoricalDataError(f"SmartAPI historical candle failure: {error_msg}")

                        raw_candles = data.get("data") or []
                        return self._parse_candles(raw_candles, instrument, timeframe)

                except httpx.HTTPError as e:
                    if attempt == self.max_retries:
                        raise HistoricalDataError(f"Angel One network error after {attempt} tries: {e}")
                    await asyncio.sleep(1.0 * attempt)

        return []

    async def search_scrip(self, exchange: str, searchscrip: str) -> List[Dict[str, Any]]:
        """Search SmartAPI live for uncataloged or newly listed scrips."""
        if not self.auth.is_configured:
            return []
        url = f"{self.auth.base_url}/rest/secure/angelbroking/order/v1/searchScrip"
        payload = {"exchange": exchange.upper(), "searchscrip": searchscrip.strip().upper()}
        try:
            await self.auth.get_valid_jwt()
            headers = self.auth.get_auth_headers()
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status"):
                        return data.get("data") or []
        except Exception as e:
            logger.warning(f"Error querying Angel One searchScrip for {searchscrip}: {e}")
        return []

    def _parse_candles(
        self,
        raw_candles: List[List[Any]],
        instrument: InstrumentDefinition,
        timeframe: str,
    ) -> List[MarketCandle]:
        """Convert SmartAPI [[timestamp, open, high, low, close, volume], ...] into MarketCandle."""
        candles: List[MarketCandle] = []
        for row in raw_candles:
            try:
                # Format: "2026-10-08T09:15:00+05:30" or "2026-10-08 09:15:00"
                ts_raw = str(row[0])
                if "T" in ts_raw:
                    dt = datetime.fromisoformat(ts_raw)
                else:
                    dt = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S")

                # Convert to UTC
                if dt.tzinfo is None:
                    dt = IST.localize(dt)
                dt_utc = dt.astimezone(UTC).replace(tzinfo=None)

                candles.append(
                    MarketCandle(
                        provider="angelone",
                        asset_class=instrument.asset_class,
                        exchange=instrument.exchange,
                        symbol=instrument.symbol,
                        instrument_id=instrument.instrument_id,
                        timeframe=timeframe,
                        timestamp=dt_utc,
                        open=float(row[1]),
                        high=float(row[2]),
                        low=float(row[3]),
                        close=float(row[4]),
                        volume=float(row[5]),
                        is_closed=True,
                    )
                )
            except Exception as e:
                logger.warning(f"Error parsing candle row {row}: {e}")
        return candles

    def _generate_synthetic_candles(
        self,
        instrument: InstrumentDefinition,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[MarketCandle]:
        """Generate realistic synthetic OHLCV candles for testing & offline warm-up."""
        tf_minutes = 15
        if timeframe == "1m":
            tf_minutes = 1
        elif timeframe == "5m":
            tf_minutes = 5
        elif timeframe == "1h":
            tf_minutes = 60
        elif timeframe == "1d":
            tf_minutes = 1440

        base_price = 1500.0
        if "NIFTY" in instrument.symbol:
            base_price = 25000.0
        elif "BANKNIFTY" in instrument.symbol:
            base_price = 51000.0
        elif "CRUDEOIL" in instrument.symbol:
            base_price = 6200.0
        elif "GOLD" in instrument.symbol:
            base_price = 78000.0

        current_dt = start
        candles: List[MarketCandle] = []
        price = base_price

        # Deterministic wave generation for warm-up
        step = 0
        while current_dt <= end:
            step += 1
            # Wave fluctuation
            change = math.sin(step / 10.0) * (base_price * 0.002)
            c_open = price
            c_close = price + change
            c_high = max(c_open, c_close) + abs(change) * 0.5 + 0.5
            c_low = min(c_open, c_close) - abs(change) * 0.5 - 0.5
            c_volume = 1000.0 + (step % 50) * 100.0
            price = c_close

            dt_utc = current_dt.replace(tzinfo=None) if current_dt.tzinfo else current_dt

            candles.append(
                MarketCandle(
                    provider="angelone",
                    asset_class=instrument.asset_class,
                    exchange=instrument.exchange,
                    symbol=instrument.symbol,
                    instrument_id=instrument.instrument_id,
                    timeframe=timeframe,
                    timestamp=dt_utc,
                    open=round(c_open, 2),
                    high=round(c_high, 2),
                    low=round(c_low, 2),
                    close=round(c_close, 2),
                    volume=round(c_volume, 1),
                    is_closed=True,
                )
            )
            current_dt += timedelta(minutes=tf_minutes)

        return candles
