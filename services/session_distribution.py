"""
Session distribution service
Handles storing Telegram session artifacts per country and delivering them to
country-specific operations channels.
"""
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from telegram import Bot
from telegram.error import TelegramError

from database.operations import SystemSettingsService
from services.session_manager import SessionManager
from services.telegram_logger import TelegramChannelLogger

logger = logging.getLogger(__name__)


@dataclass
class ChannelTarget:
    """Runtime configuration for a session drop-off channel."""

    channel_id: int
    topic_id: Optional[int] = None
    label: Optional[str] = None


class SessionDistributionService:
    """Persist session files by country and forward them to the right channel."""

    SETTINGS_KEY = "session_distribution_channels"

    def __init__(self, base_sessions_dir: str = "sessions", bot_token: Optional[str] = None) -> None:
        self.session_manager = SessionManager(base_sessions_dir=base_sessions_dir)
        self.bot_token = bot_token or os.getenv("BOT_TOKEN")
        self.bot: Optional[Bot] = None

        if self.bot_token:
            try:
                self.bot = Bot(token=self.bot_token)
            except TelegramError as exc:
                logger.warning("Failed to initialise Telegram bot for session distribution: %s", exc)
                self.bot = None
        else:
            logger.info("BOT_TOKEN missing; session bundles will be stored but not forwarded")

    async def save_and_distribute(
        self,
        *,
        db,
        phone: str,
        client,
        account,
        seller,
        country_code: Optional[str],
        sale_price: float,
        config_changes,
        new_2fa_password: Optional[str],
        terminate_result: Dict[str, Any],
        monitoring_result: Dict[str, Any],
        sale_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist the session artefacts and forward them to the mapped channel."""

        result: Dict[str, Any] = {
            "saved": False,
            "distributed": False,
            "country_code": country_code,
            "channel_summary": None,
            "session_info": None,
        }

        session_path = getattr(getattr(client, "session", None), "filename", None)
        if not session_path:
            logger.warning("Unable to determine session file path for phone %s", phone)
            result["reason"] = "missing_session_path"
            return result

        # Ensure Telethon flushes pending changes to disk before copying.
        try:
            client.session.save()
        except Exception as exc:  # pragma: no cover - defensive, Telethon usually succeeds
            logger.debug("Telethon session save warning for %s: %s", phone, exc)

        if not os.path.exists(session_path):
            logger.warning("Session file %s not found on disk", session_path)
            result["reason"] = "session_file_missing"
            return result

        metadata_payload = {
            "account_id": getattr(account, "id", None),
            "seller_id": getattr(seller, "id", None),
            "seller_telegram_id": getattr(seller, "telegram_user_id", None),
            "sale_price": sale_price,
            "changes": list(config_changes or []),
            "twofa_set": bool(new_2fa_password),
            "terminated_sessions": terminate_result.get("success") if terminate_result else None,
            "device_count": monitoring_result.get("device_count") if monitoring_result else None,
            "multi_device_detected": monitoring_result.get("multi_device_detected") if monitoring_result else None,
            "distributed_at": datetime.now(timezone.utc).isoformat(),
            "status": "sold",
        }

        if sale_metadata:
            metadata_payload.update(sale_metadata)

        saved_bundle = self.session_manager.save_session_by_country(
            phone=phone,
            session_file=session_path,
            metadata=metadata_payload,
        )

        if not saved_bundle:
            logger.error("Failed to persist session bundle for phone %s", phone)
            result["reason"] = "save_failed"
            return result

        result["saved"] = True
        result["session_info"] = saved_bundle

        if not self.bot:
            logger.info("Skipping distribution for %s (bot unavailable)", phone)
            result["reason"] = "bot_unavailable"
            return result

        target = self._resolve_channel_target(db=db, country_code=country_code)
        if not target:
            logger.warning("No channel mapping for country %s; distribution skipped", country_code)
            result["reason"] = "channel_missing"
            return result

        send_result = await self._send_bundle(target=target, phone=phone, bundle=saved_bundle, account=account, seller=seller)
        if send_result.get('sent'):
            result["distributed"] = True
        else:
            result["distributed"] = False
            result["send_errors"] = send_result.get('errors')
        if target.label:
            result["channel_summary"] = f"{target.label} ({target.channel_id})"
        else:
            result["channel_summary"] = f"{target.channel_id}"

        return result

    def _resolve_channel_target(self, *, db, country_code: Optional[str]) -> Optional[ChannelTarget]:
        """Resolve which Telegram channel should receive the bundle."""
        # If db is not available (tests, offline), skip reading settings
        mapping = None
        try:
            if db is not None:
                mapping = SystemSettingsService.get_setting(db, self.SETTINGS_KEY, default=None)
        except Exception:
            mapping = None
        country_key = (country_code or "").upper() if country_code else None

        channel_config: Optional[Dict[str, Any]] = None

        if isinstance(mapping, dict):
            if country_key and country_key in mapping:
                channel_config = mapping[country_key]
            elif country_key and country_key.lower() in mapping:
                channel_config = mapping[country_key.lower()]
            else:
                channel_config = mapping.get("default")
        elif mapping:
            channel_config = {"channel_id": mapping}

        if not channel_config:
            # Fallback to the global operations channel used by TelegramChannelLogger
            return ChannelTarget(
                channel_id=TelegramChannelLogger.WITHDRAWAL_CHANNEL_ID,
                topic_id=TelegramChannelLogger.WITHDRAWAL_TOPIC_ID,
                label="fallback",
            )

        channel_id = channel_config.get("channel_id") if isinstance(channel_config, dict) else channel_config
        topic_id = channel_config.get("topic_id") if isinstance(channel_config, dict) else None
        label = channel_config.get("label") if isinstance(channel_config, dict) else None

        try:
            channel_id = int(channel_id)
        except (TypeError, ValueError):
            logger.error("Invalid channel_id configured for country %s: %s", country_code, channel_id)
            return None

        if topic_id is not None:
            try:
                topic_id = int(topic_id)
            except (TypeError, ValueError):
                logger.warning("topic_id '%s' is not numeric; ignoring", topic_id)
                topic_id = None

        return ChannelTarget(channel_id=channel_id, topic_id=topic_id, label=label)

    async def _send_bundle(self, *, target: ChannelTarget, phone: str, bundle: Dict[str, Any], account, seller) -> Dict[str, Any]:
        """Send session message and artefacts to the resolved Telegram channel."""

        if not self.bot:
            return {"sent": False, "errors": ["bot_unavailable"]}

        message_lines = [
            "📦 *Session Ready for Delivery*",
            f"• Phone: `{phone}`",
            f"• Account ID: `{getattr(account, 'id', 'N/A')}`",
            f"• Seller ID: `{getattr(seller, 'id', 'N/A')}`",
            f"• Seller Telegram: `{getattr(seller, 'telegram_user_id', 'N/A')}`",
            f"• Stored At: `{bundle.get('session_file')}`",
        ]

        message = "\n".join(message_lines)

        kwargs = {}
        if target.topic_id is not None:
            kwargs["message_thread_id"] = target.topic_id

        errors = []
        try:
            await self.bot.send_message(
                chat_id=target.channel_id,
                text=message,
                parse_mode="Markdown",
                **kwargs,
            )
        except TelegramError as exc:
            logger.error("Failed to send session summary for %s: %s", phone, exc)
            errors.append(str(exc))

        # Send artefacts one by one to the same thread/channel.
        for key in ("session_file", "metadata_file", "cookies_file"):
            file_path = bundle.get(key)
            if not file_path:
                continue

            try:
                with open(file_path, "rb") as fh:
                    await self.bot.send_document(
                        chat_id=target.channel_id,
                        document=fh,
                        filename=os.path.basename(file_path),
                        **kwargs,
                    )
            except FileNotFoundError:
                logger.warning("Expected file missing during distribution: %s", file_path)
                errors.append(f"missing:{file_path}")
            except TelegramError as exc:
                logger.error("Failed to upload %s for %s: %s", key, phone, exc)
                errors.append(str(exc))

        sent_ok = len(errors) == 0
        return {"sent": sent_ok, "errors": errors}


session_distribution = SessionDistributionService()
