"""Utility helpers for retrieving runtime configuration and cached metrics."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from database import get_db_session, close_db_session
from database.operations import SystemSettingsService
from database.models import AccountSale

_DEFAULT_CACHE_TTL = 120  # seconds
_cache: Dict[str, Dict[str, Any]] = {}

DEFAULT_SUPPORT_CONFIG = {
    "main_button_label": "💬 Support",
    "main_button_url": "https://t.me/YourSupportChannel",
    "live_chat_label": "@support_bot",
    "live_chat_url": "https://t.me/BujhlamNaKiHolo",
    "channel_label": "@telegram_bot_support",
    "channel_url": "https://t.me/telegram_bot_support",
    "email": "support@telegrambot.com",
    "response_time": "< 2 hours",
}

DEFAULT_VERIFICATION_CHANNELS: List[Dict[str, str]] = [
    {
        "name": "📢 Bot Updates",
        "username": "telegram_account_bot_updates",
        "description": "Get the latest bot updates and announcements",
        "link": "https://t.me/telegram_account_bot_updates",
    },
    {
        "name": "💰 Selling Community",
        "username": "telegram_selling_community",
        "description": "Join our community of account sellers",
        "link": "https://t.me/telegram_selling_community",
    },
    {
        "name": "🆘 Support Channel",
        "username": "telegram_bot_support_channel",
        "description": "Get help and support from our team",
        "link": "https://t.me/telegram_bot_support_channel",
    },
]

DEFAULT_SALE_PRICE_DEFAULTS = {
    "min": 15.0,
    "max": 35.0,
    "avg": 25.0,
}


def _now() -> datetime:
    return datetime.utcnow()


def _get_cached(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if not entry:
        return None
    if entry["expires_at"] <= _now():
        _cache.pop(key, None)
        return None
    return entry["value"]


def _set_cached(key: str, value: Any, ttl_seconds: int = _DEFAULT_CACHE_TTL) -> None:
    _cache[key] = {
        "value": value,
        "expires_at": _now() + timedelta(seconds=ttl_seconds),
    }


def _maybe_parse_json(value: str) -> Any:
    """Attempt to parse a JSON string; fall back to raw value."""
    if not isinstance(value, str):
        return value
    trimmed = value.strip()
    if not trimmed:
        return None
    if trimmed.lower() in {"true", "false"}:
        return trimmed.lower() == "true"
    if trimmed[0] in "[{":
        try:
            return json.loads(trimmed)
        except json.JSONDecodeError:
            return value
    return value


def get_config_value(*, setting_key: Optional[str] = None, env_var: Optional[str] = None, default: Any = None) -> Any:
    """Resolve a configuration value from SystemSettings, env, or default."""
    value: Any = None

    if setting_key:
        cache_key = f"setting:{setting_key}"
        cached = _get_cached(cache_key)
        if cached is not None:
            value = cached
        else:
            db = get_db_session()
            try:
                value = SystemSettingsService.get_setting(db, setting_key, None)
            finally:
                close_db_session(db)
            if value is not None:
                _set_cached(cache_key, value)

    if (value is None or value == "") and env_var:
        env_value = os.getenv(env_var)
        if env_value:
            value = _maybe_parse_json(env_value)

    if value is None or value == "":
        value = default

    return value


def get_support_settings() -> Dict[str, Any]:
    cached = _get_cached("support_settings")
    if cached:
        return cached

    support_config = DEFAULT_SUPPORT_CONFIG.copy()
    support_config.update(
        {
            "main_button_label": get_config_value(
                setting_key="support_main_button_label",
                env_var="SUPPORT_MAIN_BUTTON_LABEL",
                default=DEFAULT_SUPPORT_CONFIG["main_button_label"],
            ),
            "main_button_url": get_config_value(
                setting_key="support_main_button_url",
                env_var="SUPPORT_MAIN_BUTTON_URL",
                default=DEFAULT_SUPPORT_CONFIG["main_button_url"],
            ),
            "live_chat_label": get_config_value(
                setting_key="support_live_chat_label",
                env_var="SUPPORT_LIVE_CHAT_LABEL",
                default=DEFAULT_SUPPORT_CONFIG["live_chat_label"],
            ),
            "live_chat_url": get_config_value(
                setting_key="support_live_chat_url",
                env_var="SUPPORT_LIVE_CHAT_URL",
                default=DEFAULT_SUPPORT_CONFIG["live_chat_url"],
            ),
            "channel_label": get_config_value(
                setting_key="support_channel_label",
                env_var="SUPPORT_CHANNEL_LABEL",
                default=DEFAULT_SUPPORT_CONFIG["channel_label"],
            ),
            "channel_url": get_config_value(
                setting_key="support_channel_url",
                env_var="SUPPORT_CHANNEL_URL",
                default=DEFAULT_SUPPORT_CONFIG["channel_url"],
            ),
            "email": get_config_value(
                setting_key="support_email",
                env_var="SUPPORT_EMAIL",
                default=DEFAULT_SUPPORT_CONFIG["email"],
            ),
            "response_time": get_config_value(
                setting_key="support_response_time",
                env_var="SUPPORT_RESPONSE_TIME",
                default=DEFAULT_SUPPORT_CONFIG["response_time"],
            ),
        }
    )

    _set_cached("support_settings", support_config, ttl_seconds=60)
    return support_config


def get_verification_channels() -> List[Dict[str, Any]]:
    cached = _get_cached("verification_channels")
    if cached is not None:
        return cached

    channels = get_config_value(
        setting_key="verification_required_channels",
        env_var="VERIFICATION_REQUIRED_CHANNELS",
        default=None,
    )

    parsed: Optional[List[Dict[str, Any]]] = None
    if channels:
        if isinstance(channels, list):
            parsed = channels
        elif isinstance(channels, str):
            parsed = _maybe_parse_json(channels)  # type: ignore
            if not isinstance(parsed, list):
                parsed = None

    if not parsed:
        parsed = DEFAULT_VERIFICATION_CHANNELS

    # Normalize channel dictionaries to expected keys
    normalized: List[Dict[str, Any]] = []
    for channel in parsed:
        if not isinstance(channel, dict):
            continue
        normalized.append(
            {
                "name": channel.get("name"),
                "username": channel.get("username"),
                "description": channel.get("description"),
                "link": channel.get("link"),
            }
        )

    _set_cached("verification_channels", normalized, ttl_seconds=300)
    return normalized


def _coalesce_price(value: Optional[float], fallback: float) -> float:
    if value is None:
        return fallback
    return round(float(value), 2)


def get_sale_stats() -> Dict[str, Any]:
    cached = _get_cached("sale_stats")
    if cached:
        return cached

    defaults = get_config_value(
        setting_key="sale_price_defaults",
        env_var="SALE_PRICE_DEFAULTS",
        default=DEFAULT_SALE_PRICE_DEFAULTS,
    ) or DEFAULT_SALE_PRICE_DEFAULTS

    db = get_db_session()
    try:
        total_sales = db.query(func.count(AccountSale.id)).scalar() or 0
        completed_sales = (
            db.query(func.count(AccountSale.id))
            .filter(AccountSale.status == "COMPLETED")
            .scalar()
            or 0
        )
        price_min, price_avg, price_max = (
            db.query(
                func.min(AccountSale.sale_price),
                func.avg(AccountSale.sale_price),
                func.max(AccountSale.sale_price),
            )
            .filter(AccountSale.status == "COMPLETED")
            .one()
        )
    finally:
        close_db_session(db)

    stats = {
        "total_sales": int(total_sales),
        "completed_sales": int(completed_sales),
        "completion_rate": (completed_sales / total_sales) if total_sales else None,
        "price_min": _coalesce_price(price_min, defaults["min"]),
        "price_avg": _coalesce_price(price_avg, defaults["avg"]),
        "price_max": _coalesce_price(price_max, defaults["max"]),
    }

    _set_cached("sale_stats", stats, ttl_seconds=120)
    return stats


def get_recommended_sale_price() -> float:
    stats = get_sale_stats()
    avg_price = stats.get("price_avg")
    if avg_price:
        return round(float(avg_price), 2)
    defaults = get_config_value(
        setting_key="sale_price_defaults",
        env_var="SALE_PRICE_DEFAULTS",
        default=DEFAULT_SALE_PRICE_DEFAULTS,
    )
    return round(float(defaults.get("avg", DEFAULT_SALE_PRICE_DEFAULTS["avg"])), 2)


def get_user_sales_metrics(user_id: int) -> Dict[str, Any]:
    cache_key = f"user_sales:{user_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    db = get_db_session()
    try:
        total_sales = db.query(func.count(AccountSale.id)).filter(AccountSale.seller_id == user_id).scalar() or 0
        completed_sales = (
            db.query(func.count(AccountSale.id))
            .filter(AccountSale.seller_id == user_id, AccountSale.status == "COMPLETED")
            .scalar()
            or 0
        )
        total_earnings = (
            db.query(func.coalesce(func.sum(AccountSale.sale_price), 0.0))
            .filter(AccountSale.seller_id == user_id, AccountSale.status == "COMPLETED")
            .scalar()
            or 0.0
        )
    finally:
        close_db_session(db)

    metrics = {
        "total_sales": int(total_sales),
        "completed_sales": int(completed_sales),
        "completion_rate": (completed_sales / total_sales) if total_sales else None,
        "total_earnings": round(float(total_earnings), 2),
    }

    _set_cached(cache_key, metrics, ttl_seconds=120)
    return metrics