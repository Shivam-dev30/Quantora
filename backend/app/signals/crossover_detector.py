"""Deterministic EMA Crossover Detector."""

from typing import Tuple
from backend.app.models.signal import SignalType


class CrossoverDetector:
    """Evaluates EMA fast (100) and slow (200) values across two consecutive closed bars."""

    @staticmethod
    def detect(
        prev_fast: float,
        prev_slow: float,
        curr_fast: float,
        curr_slow: float,
    ) -> SignalType:
        """
        Detect crossover conditions strictly following specifications:

        🟢 BULLISH CROSSOVER:
            Previous closed candle: EMA100 <= EMA200
            AND
            Current closed candle: EMA100 > EMA200

        🔴 BEARISH CROSSOVER:
            Previous closed candle: EMA100 >= EMA200
            AND
            Current closed candle: EMA100 < EMA200
        """
        # Bullish condition
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return SignalType.BULLISH

        # Bearish condition
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return SignalType.BEARISH

        return SignalType.NONE
