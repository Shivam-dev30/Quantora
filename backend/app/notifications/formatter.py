"""Alert Message Formatter supporting MINIMAL, STANDARD, and DETAILED modes."""

from backend.app.models.alert import AlertNotification, NotificationDetailMode
from backend.app.models.signal import SignalType


class AlertFormatter:
    """Formats alert payloads according to the configured detail mode and target channel."""

    @staticmethod
    def format_text(alert: AlertNotification) -> str:
        sig = alert.signal
        is_bull = sig.signal_type == SignalType.BULLISH
        icon = "🟢" if is_bull else "🔴"
        action = "BULLISH EMA CROSSOVER (Golden Cross)" if is_bull else "BEARISH EMA CROSSOVER (Death Cross)"
        operator = ">" if is_bull else "<"
        is_catchup = getattr(sig, "is_catchup", False)
        catchup_prefix = "⚡ [STARTUP CATCH-UP] " if is_catchup else ""

        # Price drift string if available
        drift_str = ""
        if alert.formatted_current_price and alert.drift_percent is not None:
            sign = "+" if alert.drift_percent > 0 else ""
            drift_str = f"\nCurrent Price: {alert.formatted_current_price} ({sign}{alert.drift_percent:.2f}% from trigger)"

        # MINIMAL MODE
        if alert.detail_mode == NotificationDetailMode.MINIMAL:
            return f"{catchup_prefix}{icon} {sig.symbol} | EMA100 {operator} EMA200 | {sig.timeframe}{drift_str}"

        # STANDARD MODE
        if alert.detail_mode == NotificationDetailMode.STANDARD:
            msg = (
                f"{catchup_prefix}{icon} {sig.symbol}\n"
                f"{action}\n"
                f"Timeframe: {sig.timeframe}\n"
                f"Trigger Price: {alert.formatted_price}"
                f"{drift_str}\n"
                f"Market: {alert.market_display_name}\n"
                f"Candle Time: {alert.display_time}"
            )
            if is_catchup:
                msg += "\n⚠️ Trade Setup Triggered Prior to Server Start • Regime is Active!"
            return msg.strip()

        # DETAILED MODE
        provider_display = "Angel One SmartAPI" if sig.provider == "angelone" else "Delta Exchange"
        header = "⚡ STARTUP CATCH-UP TRADE OPPORTUNITY" if is_catchup else "🚨 LIVE MARKET ALERT"
        lines = [
            f"{header}\n",
            f"{icon} {action}\n",
            f"Asset: {sig.symbol}",
            f"Market: {alert.market_display_name} ({sig.exchange})",
            f"Timeframe: {sig.timeframe}",
            f"Trigger Price: {alert.formatted_price}",
        ]
        if alert.formatted_current_price:
            sign = "+" if (alert.drift_percent or 0) > 0 else ""
            drift_val = f" ({sign}{alert.drift_percent:.2f}% / {sign}{alert.drift_points})" if alert.drift_percent is not None else ""
            lines.append(f"Current Price: {alert.formatted_current_price}{drift_val}")
        lines.extend([
            f"\nEMA 100: {alert.formatted_ema100}",
            f"EMA 200: {alert.formatted_ema200}",
            f"Previous EMA 100 / 200: {alert.formatted_prev_ema100} / {alert.formatted_prev_ema200}\n",
            f"Candle Time: {alert.display_time}" + (f" ({alert.elapsed_time_str})" if alert.elapsed_time_str else ""),
            f"Provider: {provider_display}",
        ])
        if is_catchup:
            lines.append(
                "\n📌 Quant Execution Note: This crossover occurred prior to server startup.\n"
                "The indicator regime remains CURRENT and ACTIVE. Evaluate trade entry against current market price."
            )
        return "\n".join(lines)

    @staticmethod
    def format_html(alert: AlertNotification) -> str:
        sig = alert.signal
        icon = "🟢" if sig.signal_type == SignalType.BULLISH else "🔴"
        color = "#10b981" if sig.signal_type == SignalType.BULLISH else "#ef4444"
        action = "BULLISH EMA CROSSOVER" if sig.signal_type == SignalType.BULLISH else "BEARISH EMA CROSSOVER"
        provider_display = "Angel One SmartAPI" if sig.provider == "angelone" else "Delta Exchange"

        return f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 520px; background: #0f172a; color: #f8fafc; border-radius: 12px; padding: 24px; border: 1px solid #334155;">
            <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #1e293b; padding-bottom: 12px; margin-bottom: 16px;">
                <span style="font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8;">Market Alert Platform</span>
                <span style="background: rgba(255,255,255,0.08); padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 500;">{sig.timeframe}</span>
            </div>
            <div style="margin-bottom: 20px;">
                <h2 style="margin: 0; color: {color}; font-size: 22px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                    {icon} {sig.symbol}
                </h2>
                <div style="font-size: 14px; color: #cbd5e1; margin-top: 4px; font-weight: 500;">
                    {action}
                </div>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px;">
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 8px 0; color: #94a3b8;">Market / Exchange</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: 600;">{alert.market_display_name} ({sig.exchange})</td>
                </tr>
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 8px 0; color: #94a3b8;">Candle Close Price</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: 700; font-size: 16px; color: #38bdf8;">{alert.formatted_price}</td>
                </tr>
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 8px 0; color: #94a3b8;">EMA 100 (Fast)</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: 600;">{alert.formatted_ema100}</td>
                </tr>
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 8px 0; color: #94a3b8;">EMA 200 (Slow)</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: 600;">{alert.formatted_ema200}</td>
                </tr>
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 8px 0; color: #94a3b8;">Previous EMA 100 / 200</td>
                    <td style="padding: 8px 0; text-align: right; color: #64748b;">{alert.formatted_prev_ema100} / {alert.formatted_prev_ema200}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Candle Time</td>
                    <td style="padding: 8px 0; text-align: right; font-size: 12px; color: #cbd5e1;">{alert.display_time}</td>
                </tr>
            </table>
            <div style="font-size: 11px; color: #64748b; text-align: center; border-top: 1px solid #1e293b; padding-top: 12px;">
                Data Source: {provider_display} &bull; Strict Closed-Candle Execution &bull; Alert Only
            </div>
        </div>
        """
