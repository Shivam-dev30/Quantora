"""Indicator Engine managing multi-asset and multi-timeframe indicator states."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from backend.app.config.settings import StrategyConfig
from backend.app.core.logging import get_logger
from backend.app.models.candle import MarketCandle
from backend.app.indicators.ema import EMACalculator, EMAState

logger = get_logger("indicator_engine")


@dataclass
class IndicatorUpdatedEvent:
    """Event emitted whenever indicators are updated for a closed candle."""

    candle: MarketCandle
    state: EMAState


class IndicatorEngine:
    """Coordinates EMA calculators across all monitored instruments and timeframes."""

    def __init__(self, strategy_config: StrategyConfig) -> None:
        self.config = strategy_config
        self.calculator = EMACalculator(
            period_fast=strategy_config.ema_fast,
            period_slow=strategy_config.ema_slow,
        )
        # Registry of indicator states: Key = (provider, instrument_id, timeframe)
        self._states: Dict[Tuple[str, str, str], EMAState] = {}

    def get_or_create_state(self, candle: MarketCandle) -> EMAState:
        key = (candle.provider, candle.instrument_id, candle.timeframe)
        if key not in self._states:
            self._states[key] = EMAState(
                provider=candle.provider,
                exchange=candle.exchange,
                instrument_id=candle.instrument_id,
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                period_fast=self.config.ema_fast,
                period_slow=self.config.ema_slow,
            )
        return self._states[key]

    def process_closed_candle(self, candle: MarketCandle) -> Optional[IndicatorUpdatedEvent]:
        """
        Process a closed candle and update indicator state.
        Returns IndicatorUpdatedEvent if indicator is ready.
        """
        state = self.get_or_create_state(candle)
        self.calculator.update(state, candle)

        if state.is_ready:
            return IndicatorUpdatedEvent(candle=candle, state=state)
        else:
            logger.debug(
                f"Warming up {state.symbol} [{state.timeframe}]: "
                f"{state.bars_processed}/{state.period_slow} bars"
            )
            return None

    def get_state(self, provider: str, instrument_id: str, timeframe: str) -> Optional[EMAState]:
        return self._states.get((provider, instrument_id, timeframe))

    def get_all_states(self) -> List[EMAState]:
        return list(self._states.values())
