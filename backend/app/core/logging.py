"""Secure logging module with automatic secret redaction and dual console/file handlers."""

import logging
import re
import sys
from pathlib import Path
from typing import List, Optional

# Secret patterns to automatically mask in log output
_REDACTION_PATTERNS = [
    re.compile(r"(api[-_]?key[\s:=]+)(['\"]?)([\w\-]{8,})(['\"]?)", re.IGNORECASE),
    re.compile(r"(secret[\s:=]+)(['\"]?)([\w\-]{8,})(['\"]?)", re.IGNORECASE),
    re.compile(r"(password[\s:=]+)(['\"]?)([^\s'\"]+)(['\"]?)", re.IGNORECASE),
    re.compile(r"(totp[\s:=]+)(['\"]?)([\w\-]+)(['\"]?)", re.IGNORECASE),
    re.compile(r"(jwtToken[\s:=]+)(['\"]?)([\w\-.]+)('\"?)", re.IGNORECASE),
    re.compile(r"(bot[0-9]{8,}:[a-zA-Z0-9_-]{20,})", re.IGNORECASE),  # Telegram bot tokens
    re.compile(r"(Bearer\s+)([a-zA-Z0-9_\-\.]{15,})", re.IGNORECASE),
]


class SecretMaskingFilter(logging.Filter):
    """Filter that masks sensitive tokens, passwords, and API keys from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self.mask_secrets(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self.mask_secrets(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True

    @staticmethod
    def mask_secrets(text: str) -> str:
        masked = text
        for pattern in _REDACTION_PATTERNS:
            masked = pattern.sub(r"\1***REDACTED***", masked)
        return masked


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    log_file_name: str = "market_alerts.log",
) -> logging.Logger:
    """Configure system root logger with console and rotating file output."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    full_file_path = log_path / log_file_name

    logger = logging.getLogger("market_alert")
    logger.setLevel(level)
    logger.propagate = False

    # Clear existing handlers to prevent duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s:%(module)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    mask_filter = SecretMaskingFilter()

    # Console Handler (Ensuring UTF-8 on Windows)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(mask_filter)
    logger.addHandler(console_handler)

    # File Handler
    try:
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            full_file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(mask_filter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Failed to setup file logger: {e}", file=sys.stderr)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a child logger inheriting system settings and redaction filters."""
    base = logging.getLogger("market_alert")
    if name:
        return base.getChild(name)
    return base
