"""Tests for session restoration helper in :mod:`services.real_telegram`."""
import os
import tempfile
import unittest
from unittest.mock import patch

from services import real_telegram


AUTHORIZATION_BY_SESSION = {}


class DummyTelegramClient:
    """Minimal async substitute for :class:`telethon.TelegramClient`."""

    def __init__(self, session_key: str, api_id: int, api_hash: str):
        self.session_key = session_key
        self.api_id = api_id
        self.api_hash = api_hash
        self._connected = False
        self._authorized = AUTHORIZATION_BY_SESSION.get(session_key, True)

    async def connect(self):
        self._connected = True

    def is_connected(self):
        return self._connected

    async def is_user_authorized(self):
        return self._authorized

    async def disconnect(self):
        self._connected = False


class DummyBypass:
    """Placeholder for bypass systems during unit tests."""


class DummyFlaggedHandler:
    """Placeholder for flagged account handler during unit tests."""


class RealTelegramServiceSessionTests(unittest.IsolatedAsyncioTestCase):
    """Validate the logic in ``get_client_from_session``."""

    def setUp(self):
        AUTHORIZATION_BY_SESSION.clear()
        self.env_patch = patch.dict(os.environ, {"API_ID": "123456", "API_HASH": "test_hash_value"})
        self.client_patch = patch.object(real_telegram, "TelegramClient", DummyTelegramClient)
        self.bypass_patch = patch.object(real_telegram, "AdvancedTelegramBypass", DummyBypass)
        self.flagged_patch = patch.object(real_telegram, "FlaggedAccountHandler", DummyFlaggedHandler)

        self.env_patch.start()
        self.client_patch.start()
        self.bypass_patch.start()
        self.flagged_patch.start()

    def tearDown(self):
        self.flagged_patch.stop()
        self.bypass_patch.stop()
        self.client_patch.stop()
        self.env_patch.stop()

    async def test_missing_session_file_returns_none(self):
        service = real_telegram.RealTelegramService()
        result = await service.get_client_from_session("missing")
        self.assertIsNone(result)

    async def test_hydrates_new_client_when_session_exists(self):
        session_key = "hydrate_me"
        AUTHORIZATION_BY_SESSION[session_key] = True

        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                open(f"{session_key}.session", "w", encoding="utf-8").close()
                service = real_telegram.RealTelegramService()
                client = await service.get_client_from_session(session_key)

                self.assertIsNotNone(client)
                self.assertTrue(client.is_connected())
                self.assertIs(service.clients[session_key], client)
            finally:
                os.chdir(cwd)

    async def test_reuses_cached_client(self):
        session_key = "cached"
        AUTHORIZATION_BY_SESSION[session_key] = True

        service = real_telegram.RealTelegramService()
        cached_client = DummyTelegramClient(session_key, service.api_id, service.api_hash)
        cached_client._connected = False
        service.clients[session_key] = cached_client

        client = await service.get_client_from_session(session_key)

        self.assertIs(client, cached_client)
        self.assertTrue(client.is_connected())

    async def test_unauthorized_session_returns_none(self):
        session_key = "unauthorized"
        AUTHORIZATION_BY_SESSION[session_key] = False

        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                open(f"{session_key}.session", "w", encoding="utf-8").close()
                service = real_telegram.RealTelegramService()
                client = await service.get_client_from_session(session_key)

                self.assertIsNone(client)
                self.assertNotIn(session_key, service.clients)
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
