"""
Lightweight test for session distribution service.
Creates a dummy session file and a minimal client, calls save_and_distribute,
verifies files saved to a country folder and that distribution was skipped when
BOT_TOKEN is not set.
"""
import os
import shutil
import asyncio
from types import SimpleNamespace
from pathlib import Path

from services.session_distribution import SessionDistributionService


def prepare_dummy_session(phone: str, filename: str) -> str:
    # Create an empty session file in the workspace
    with open(filename, 'wb') as fh:
        fh.write(b'')
    return os.path.abspath(filename)


async def run_test():
    base_dir = 'sessions_test'

    # Cleanup previous runs
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)

    # Initialize service (no BOT_TOKEN -> bot unavailable)
    svc = SessionDistributionService(base_sessions_dir=base_dir, bot_token=None)

    phone = '+919821757044'
    phone_clean = ''.join(filter(str.isdigit, phone))
    session_filename = f"{phone_clean}_20251020_000000.session"
    session_path = prepare_dummy_session(phone, session_filename)

    # Minimal fake Telethon client with session.filename and save()
    class DummySession:
        def __init__(self, filename):
            self.filename = filename
        def save(self):
            # no-op for test
            return True

    client = SimpleNamespace(session=DummySession(session_path))

    account = SimpleNamespace(id=42)
    seller = SimpleNamespace(id=7, telegram_user_id=999999)

    result = await svc.save_and_distribute(
        db=None,
        phone=phone,
        client=client,
        account=account,
        seller=seller,
        country_code='IN',
        sale_price=100.0,
        config_changes=['name_changed'],
        new_2fa_password=None,
        terminate_result={'success': True, 'terminated_count': 1},
        monitoring_result={'device_count': 1, 'multi_device_detected': False},
        sale_metadata={'note': 'unit-test'}
    )

    print('\n=== Distribution Result ===')
    print(result)

    # Verify saved files exist in base_dir/IN
    country_dir = Path(base_dir) / 'IN'
    metadata_files = list(country_dir.glob('*_metadata.json')) if country_dir.exists() else []
    session_files = list(country_dir.glob('*.session')) if country_dir.exists() else []

    print('\n=== Files in sessions_test/IN ===')
    print('metadata_files:', [str(p) for p in metadata_files])
    print('session_files:', [str(p) for p in session_files])

    # Assertions (rudimentary)
    assert result.get('saved') is True, 'Expected saved True'
    assert result.get('distributed') in (False, None), 'Expected not distributed when BOT_TOKEN is None'
    assert country_dir.exists(), 'Country directory should exist'
    assert len(metadata_files) >= 1, 'Expected at least one metadata file'
    assert len(session_files) >= 1 or os.path.exists(session_path), 'Expected session file present in country dir or original'

    print('\n✅ Test passed')


if __name__ == '__main__':
    asyncio.run(run_test())
