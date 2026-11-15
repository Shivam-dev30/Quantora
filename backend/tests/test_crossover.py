"""Unit tests for EMA Crossover Detector covering bullish, bearish, equality, and repeated states."""

import pytest
from backend.app.models.signal import SignalType
from backend.app.signals.crossover_detector import CrossoverDetector


def test_bullish_crossover():
    """Previous closed: Fast <= Slow, Current closed: Fast > Slow -> BULLISH."""
    detector = CrossoverDetector()

    # Fast crosses above Slow
    signal = detector.detect(
        prev_fast=100.0,
        prev_slow=105.0,
        curr_fast=106.0,
        curr_slow=105.5,
    )
    assert signal == SignalType.BULLISH


def test_bearish_crossover():
    """Previous closed: Fast >= Slow, Current closed: Fast < Slow -> BEARISH."""
    detector = CrossoverDetector()

    # Fast crosses below Slow
    signal = detector.detect(
        prev_fast=110.0,
        prev_slow=105.0,
        curr_fast=104.0,
        curr_slow=105.2,
    )
    assert signal == SignalType.BEARISH


def test_crossover_from_exact_equality():
    """Previous closed: Fast == Slow, Current closed: Fast > Slow -> BULLISH."""
    detector = CrossoverDetector()

    signal = detector.detect(
        prev_fast=100.0,
        prev_slow=100.0,
        curr_fast=101.0,
        curr_slow=100.2,
    )
    assert signal == SignalType.BULLISH

    # Previous closed: Fast == Slow, Current closed: Fast < Slow -> BEARISH
    signal = detector.detect(
        prev_fast=100.0,
        prev_slow=100.0,
        curr_fast=99.0,
        curr_slow=99.8,
    )
    assert signal == SignalType.BEARISH


def test_no_crossover_when_staying_above():
    """Fast was above Slow and remains above Slow -> NONE (prevents repeated alerts)."""
    detector = CrossoverDetector()

    signal = detector.detect(
        prev_fast=110.0,
        prev_slow=105.0,
        curr_fast=112.0,
        curr_slow=106.0,
    )
    assert signal == SignalType.NONE


def test_no_crossover_when_staying_below():
    """Fast was below Slow and remains below Slow -> NONE."""
    detector = CrossoverDetector()

    signal = detector.detect(
        prev_fast=90.0,
        prev_slow=100.0,
        curr_fast=92.0,
        curr_slow=99.0,
    )
    assert signal == SignalType.NONE


def test_no_crossover_on_identical_flatline():
    """Flatline -> NONE."""
    detector = CrossoverDetector()

    signal = detector.detect(
        prev_fast=100.0,
        prev_slow=100.0,
        curr_fast=100.0,
        curr_slow=100.0,
    )
    assert signal == SignalType.NONE
