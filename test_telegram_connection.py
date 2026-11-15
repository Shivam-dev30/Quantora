"""
Test script to verify Telegram Bot configuration and send a dummy test alert.
"""

import asyncio
import os
import sys
from datetime import datetime
import httpx

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath("."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.app.config.settings import load_config
from backend.app.models.signal import SignalEvent, SignalType
from backend.app.models.alert import AlertNotification, NotificationDetailMode
from backend.app.notifications.telegram import TelegramProvider
from backend.app.notifications.formatter import AlertFormatter


async def main():
    print("=" * 60)
    print("TELEGRAM BOT CONNECTIVITY & ALERT TEST")
    print("=" * 60)

    # 1. Load system config
    config = load_config()
    tg_config = config.notifications.telegram

    print(f"[*] Configuration Status:")
    print(f"    - Telegram Enabled : {tg_config.enabled}")
    masked_token = (
        tg_config.bot_token[:10] + "..." + tg_config.bot_token[-5:]
        if tg_config.bot_token and len(tg_config.bot_token) > 15
        else (tg_config.bot_token or "None")
    )
    print(f"    - Bot Token        : {masked_token}")
    print(f"    - Chat ID          : {tg_config.chat_id}")

    if not tg_config.bot_token or not tg_config.chat_id:
        print("[!] ERROR: Missing bot token or chat ID in configuration!")
        return False

    provider = TelegramProvider(tg_config)

    # 2. Check Bot Identity via getMe
    print("\n[*] Step 1: Testing Bot Authentication (getMe)...")
    health = await provider.health_check()
    print(f"    - Health status: {health}")

    if health.get("status") != "healthy":
        print(f"[!] Authentication failed: {health}")
        return False

    bot_username = health.get("bot_username")
    print(f"[+] Bot Verified successfully: @{bot_username}")

    # 3. Create dummy signal & alert notification
    print("\n[*] Step 2: Preparing Dummy Alert Notification...")
    now = datetime.now()
    dummy_signal = SignalEvent.create(
        provider="angelone",
        asset_class="equity",
        exchange="NSE",
        instrument_id="NIFTY",
        symbol="NIFTY 50",
        timeframe="15m",
        signal_type=SignalType.BULLISH,
        candle_timestamp=now,
        price=24950.75,
        ema100=24910.20,
        ema200=24855.40,
        previous_ema100=24850.10,
        previous_ema200=24853.80,
    )

    dummy_alert = AlertNotification(
        signal=dummy_signal,
        detail_mode=NotificationDetailMode.DETAILED,
        display_time=now.strftime("%Y-%m-%d %I:%M:%S %p IST"),
        currency_symbol="₹",
        formatted_price="₹24,950.75",
        formatted_ema100="₹24,910.20",
        formatted_ema200="₹24,855.40",
        formatted_prev_ema100="₹24,850.10",
        formatted_prev_ema200="₹24,853.80",
        market_display_name="Indian Equity",
    )

    formatted_msg = AlertFormatter.format_text(dummy_alert)
    print("---------------- Formatted Message Preview ----------------")
    print(formatted_msg)
    print("-----------------------------------------------------------")

    # 4. Send test notification via TelegramProvider
    print("\n[*] Step 3: Sending Dummy Notification via TelegramProvider...")
    try:
        success = await provider.send(dummy_alert)
        if success:
            print("[+] SUCCESS: Telegram dummy notification was successfully sent and delivered!")
            return True
        else:
            print("[!] Provider returned False (check logs).")
            return False
    except Exception as e:
        print(f"[!] Exception while sending notification: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
