"""Application configuration loader combining YAML and environment variables."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MarketConfig(BaseModel):
    enabled: bool = True
    provider: str = "angelone"
    exchange: str = "NSE"
    mode: str = "selected"  # "all" | "selected"
    symbols: List[str] = Field(default_factory=list)
    expiry_mode: Optional[str] = "current"  # "current" | "next" | "specific"
    monitor_underlying_only: Optional[bool] = False


class StrategyConfig(BaseModel):
    name: str = "ema_crossover"
    version: str = "ema100_200_v1"
    ema_fast: int = 100
    ema_slow: int = 200
    timeframes: List[str] = Field(default_factory=lambda: ["5m", "15m", "30m", "1h"])
    instrument_timeframes: Dict[str, List[str]] = Field(default_factory=dict)
    default_timeframe: str = "15m"
    min_warmup_candles: int = 250


class TelegramConfig(BaseModel):
    enabled: bool = True
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    max_retries: int = 3
    retry_delay_seconds: float = 2.0


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: Optional[str] = None
    smtp_use_tls: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 5.0


class WhatsAppConfig(BaseModel):
    enabled: bool = False
    provider: str = "meta_cloud"  # "meta_cloud" | "twilio"
    phone_number_id: Optional[str] = None
    access_token: Optional[str] = None
    recipient_phone: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_phone: Optional[str] = None
    twilio_to_phone: Optional[str] = None
    max_retries: int = 2
    retry_delay_seconds: float = 5.0


class NotificationsConfig(BaseModel):
    detail_mode: str = "STANDARD"  # "MINIMAL" | "STANDARD" | "DETAILED"
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./market_alerts.db"
    display_timezone: str = "Asia/Kolkata"
    config_file_path: str = "backend/app/config/default_config.yaml"

    # Angel One credentials
    angel_api_key: Optional[str] = None
    angel_client_code: Optional[str] = None
    angel_password: Optional[str] = None
    angel_totp_secret: Optional[str] = None

    # Delta credentials
    delta_api_key: Optional[str] = None
    delta_api_secret: Optional[str] = None
    delta_rest_url: str = "https://api.india.delta.exchange"
    delta_ws_url: str = "wss://socket.india.delta.exchange"

    # Notification overrides from env
    telegram_enabled: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    email_enabled: Optional[bool] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: Optional[str] = None
    smtp_use_tls: Optional[bool] = None

    whatsapp_enabled: Optional[bool] = None
    whatsapp_provider: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_access_token: Optional[str] = None
    whatsapp_recipient_phone: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_phone: Optional[str] = None
    twilio_to_phone: Optional[str] = None

    # Host & Port
    host: str = "0.0.0.0"
    port: int = 8000

    # Security, Auth & CORS settings
    cors_allowed_origins: str = "http://localhost:8000,http://localhost:5173,http://127.0.0.1:8000,http://127.0.0.1:5173"
    secret_key: str = "quantora-default-dev-secret-key-32bytes-min"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    admin_api_key: Optional[str] = None
    auth_enabled: bool = False
    rate_limit_per_minute: int = 120

    def get_cors_origins(self) -> List[str]:
        if not self.cors_allowed_origins:
            return ["http://localhost:8000", "http://127.0.0.1:8000"]
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    def is_production(self) -> bool:
        return self.app_env.lower() in ("production", "prod")



class FullSystemConfig(BaseModel):
    settings: AppSettings
    markets: Dict[str, MarketConfig]
    strategy: StrategyConfig
    notifications: NotificationsConfig
    market_hours: Dict[str, Any]
    display: Dict[str, Any]


_cached_config: Optional[FullSystemConfig] = None


def load_config(config_path: Optional[str] = None) -> FullSystemConfig:
    """Load configuration merging YAML with environment variables."""
    global _cached_config

    env_settings = AppSettings()
    target_yaml_path = config_path or env_settings.config_file_path

    yaml_data: Dict[str, Any] = {}
    path_obj = Path(target_yaml_path)
    if not path_obj.is_absolute():
        # Check relative to workspace
        for candidate in [
            path_obj,
            Path.cwd() / target_yaml_path,
            Path(__file__).parent / "default_config.yaml",
        ]:
            if candidate.exists():
                path_obj = candidate
                break

    if path_obj.exists():
        with open(path_obj, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

    # Parse markets
    markets_data = yaml_data.get("markets", {})
    markets: Dict[str, MarketConfig] = {}
    for market_name, m_cfg in markets_data.items():
        markets[market_name] = MarketConfig(**m_cfg)

    # Parse strategy
    strategy_data = yaml_data.get("strategy", {})
    strategy = StrategyConfig(**strategy_data) if strategy_data else StrategyConfig()

    # Parse notifications and merge env overrides
    notif_data = yaml_data.get("notifications", {})
    telegram_data = notif_data.get("telegram", {})
    email_data = notif_data.get("email", {})
    whatsapp_data = notif_data.get("whatsapp", {})

    telegram_cfg = TelegramConfig(**telegram_data)
    if env_settings.telegram_enabled is not None:
        telegram_cfg.enabled = env_settings.telegram_enabled
    if env_settings.telegram_bot_token:
        telegram_cfg.bot_token = env_settings.telegram_bot_token
    if env_settings.telegram_chat_id:
        telegram_cfg.chat_id = env_settings.telegram_chat_id

    email_cfg = EmailConfig(**email_data)
    if env_settings.email_enabled is not None:
        email_cfg.enabled = env_settings.email_enabled
    if env_settings.smtp_host:
        email_cfg.smtp_host = env_settings.smtp_host
    if env_settings.smtp_port:
        email_cfg.smtp_port = env_settings.smtp_port
    if env_settings.smtp_username:
        email_cfg.smtp_username = env_settings.smtp_username
    if env_settings.smtp_password:
        email_cfg.smtp_password = env_settings.smtp_password
    if env_settings.email_from:
        email_cfg.email_from = env_settings.email_from
    if env_settings.email_to:
        email_cfg.email_to = env_settings.email_to
    if env_settings.smtp_use_tls is not None:
        email_cfg.smtp_use_tls = env_settings.smtp_use_tls

    whatsapp_cfg = WhatsAppConfig(**whatsapp_data)
    if env_settings.whatsapp_enabled is not None:
        whatsapp_cfg.enabled = env_settings.whatsapp_enabled
    if env_settings.whatsapp_provider:
        whatsapp_cfg.provider = env_settings.whatsapp_provider
    if env_settings.whatsapp_phone_number_id:
        whatsapp_cfg.phone_number_id = env_settings.whatsapp_phone_number_id
    if env_settings.whatsapp_access_token:
        whatsapp_cfg.access_token = env_settings.whatsapp_access_token
    if env_settings.whatsapp_recipient_phone:
        whatsapp_cfg.recipient_phone = env_settings.whatsapp_recipient_phone
    if env_settings.twilio_account_sid:
        whatsapp_cfg.twilio_account_sid = env_settings.twilio_account_sid
    if env_settings.twilio_auth_token:
        whatsapp_cfg.twilio_auth_token = env_settings.twilio_auth_token
    if env_settings.twilio_from_phone:
        whatsapp_cfg.twilio_from_phone = env_settings.twilio_from_phone
    if env_settings.twilio_to_phone:
        whatsapp_cfg.twilio_to_phone = env_settings.twilio_to_phone

    notifications = NotificationsConfig(
        detail_mode=notif_data.get("detail_mode", "STANDARD"),
        telegram=telegram_cfg,
        email=email_cfg,
        whatsapp=whatsapp_cfg,
    )

    market_hours = yaml_data.get("market_hours", {"respect_exchange_hours": True})
    display = yaml_data.get(
        "display",
        {
            "timezone": env_settings.display_timezone,
            "currency_symbols": {"NSE": "₹", "NFO": "₹", "MCX": "₹", "DELTA": "$"},
        },
    )

    full_cfg = FullSystemConfig(
        settings=env_settings,
        markets=markets,
        strategy=strategy,
        notifications=notifications,
        market_hours=market_hours,
        display=display,
    )

    _cached_config = full_cfg
    return full_cfg


def get_config() -> FullSystemConfig:
    global _cached_config
    if _cached_config is None:
        return load_config()
    return _cached_config
