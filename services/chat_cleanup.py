"""Utilities for managing chat history retention for privacy controls."""
from __future__ import annotations

import logging
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


async def purge_bot_history(
    bot: Bot,
    chat_id: int,
    latest_message_id: Optional[int],
    *,
    keep_last: int = 1,
    max_delete: int = 40,
    log: Optional[logging.Logger] = None,
) -> int:
    """Attempt to delete recent bot messages for a chat.

    Parameters
    ----------
    bot:
        The Telegram Bot instance used for API calls.
    chat_id:
        The identifier of the chat whose history should be purged.
    latest_message_id:
        The most recent message id sent by the bot that should remain visible.
        When ``None`` the purge is skipped.
    keep_last:
        Number of most recent bot messages to keep (for example, the final
        summary message). Defaults to ``1``.
    max_delete:
        Maximum number of earlier messages to attempt deleting. Defaults to 40.
    log:
        Optional logger to use instead of the module logger.

    Returns
    -------
    int
        Count of messages successfully deleted. Failures are silently ignored
        with debug logging so the overall flow never crashes.
    """

    if latest_message_id is None:
        return 0

    log = log or logger
    deleted = 0

    # Determine the lowest message id we will attempt to delete.
    # Message ids in private chats increment sequentially, so walking backwards
    # is usually sufficient even though some ids may belong to the user (those
    # deletions will simply fail and be skipped).
    start_id = max(1, latest_message_id - keep_last)
    end_id = max(0, start_id - max_delete)

    for message_id in range(start_id, end_id, -1):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            deleted += 1
        except TelegramError as exc:  # pragma: no cover - depends on Telegram
            error_text = getattr(exc, "message", "").lower()
            # Ignore expected failures (e.g., trying to delete user messages or
            # messages that are too old). These failures are harmless.
            expected_patterns = (
                "message can't be deleted",
                "message to delete not found",
                "message was deleted",
                "message_id_invalid",
            )
            if not any(pattern in error_text for pattern in expected_patterns):
                log.debug(
                    "Failed to delete message %s in chat %s: %s",
                    message_id,
                    chat_id,
                    exc,
                )
        except Exception as exc:  # pragma: no cover - safety net
            log.debug(
                "Unexpected error deleting message %s in chat %s: %s",
                message_id,
                chat_id,
                exc,
            )

    return deleted
