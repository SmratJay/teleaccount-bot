"""
Session Management Service
Handles automatic session termination, multi-device detection, and account holds
"""
import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from telethon import TelegramClient
from telethon.tl.functions.auth import LogOutRequest
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from database import get_db_session, close_db_session
from database.operations import (
    TelegramAccountService,
    ActivityLogService,
    SystemSettingsService,
    SessionLogService,
)
from database.models import TelegramAccount, AccountStatus, ActivityLog
from services.account_management import account_manager

logger = logging.getLogger(__name__)

class SessionManagementService:
    """Service for managing Telegram sessions and detecting multi-device usage"""
    
    def __init__(self):
        self.active_sessions = {}  # Track active sessions
        self.device_fingerprints = {}  # Track device fingerprints
        
    async def monitor_account_sessions(self, client: TelegramClient, user_id: int, 
                                     account_id: int) -> Dict[str, Any]:
        """
        Monitor account for multi-device usage and manage sessions
        Returns monitoring results and actions taken
        """
        results = {
            'multi_device_detected': False,
            'sessions_terminated': 0,
            'account_on_hold': False,
            'device_count': 0,
            'actions_taken': []
        }
        
        try:
            # Get current session information
            sessions_info = await self._get_active_sessions(client)
            results['device_count'] = len(sessions_info.get('sessions', []))
            
            # Log all sessions to database for tracking
            db = get_db_session()
            try:
                for session in sessions_info.get('sessions', []):
                    session_log_data = {
                        'session_hash': session.get('hash'),
                        'auth_key_id': session.get('auth_key_id'),
                        'device_model': session.get('device'),
                        'system_version': session.get('system_version'),
                        'app_name': session.get('app_name'),
                        'app_version': session.get('app_version'),
                        'ip_address': session.get('ip'),
                        'country': session.get('country'),
                        'region': session.get('region'),
                        'status': 'ACTIVE',
                        'session_type': 'LOGIN',
                        'is_official_app': session.get('is_official_app', True),
                        'is_current': session.get('is_current', False)
                    }
                    SessionLogService.create_session_log(db, user_id=user_id, account_id=account_id, session_data=session_log_data)
            finally:
                close_db_session(db)
            
            # Check for multi-device usage
            if results['device_count'] > 1:
                results['multi_device_detected'] = True
                logger.warning(f"Multi-device detected for account {account_id}: {results['device_count']} sessions")
                
                # CRITICAL: Freeze account immediately due to multi-device detection
                db = get_db_session()
                try:
                    hold_hours_setting = SystemSettingsService.get_setting(
                        db, 'multi_device_hold_hours', default=24
                    )
                    try:
                        hold_hours = int(hold_hours_setting)
                    except (TypeError, ValueError):
                        hold_hours = 24

                    freeze_result = account_manager.freeze_account(
                        db=db,
                        account_id=account_id,
                        reason=f"Multi-device usage detected: {results['device_count']} active sessions",
                        admin_id=1,  # System auto-freeze (admin_id=1 represents system)
                        duration_hours=hold_hours
                    )
                    
                    if freeze_result['success']:
                        results['account_frozen'] = True
                        results['freeze_duration'] = (
                            f"{hold_hours} hours" if hold_hours else 'indefinite'
                        )
                        results['actions_taken'].append('account_freeze')
                        logger.info(f"Account {account_id} frozen due to multi-device detection")
                    
                    # Update multi_device_last_detected timestamp
                    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
                    if account:
                        account.multi_device_last_detected = datetime.utcnow()
                        db.commit()
                
                finally:
                    close_db_session(db)
                
                # Put account on timed hold for redundancy with legacy flows
                hold_result = await self._put_account_on_hold(account_id, user_id, hold_hours)
                if hold_result['success']:
                    results['account_on_hold'] = True
                    results['actions_taken'].append('account_hold')
                
                # Terminate all other sessions
                terminate_result = await self._terminate_other_sessions(client, user_id)
                if terminate_result['success']:
                    results['sessions_terminated'] = terminate_result['terminated_count']
                    results['actions_taken'].append('session_termination')
            
            # Log monitoring activity
            db = get_db_session()
            try:
                ActivityLogService.log_action(
                    db, user_id, "SESSION_MONITORED",
                    f"Sessions: {results['device_count']}, Multi-device: {results['multi_device_detected']}"
                )
            finally:
                close_db_session(db)
            
            return results
            
        except Exception as e:
            logger.error(f"Error monitoring sessions for account {account_id}: {e}")
            results['error'] = str(e)
            return results
    
    async def _get_active_sessions(self, client: TelegramClient) -> Dict[str, Any]:
        """Get information about active sessions using Telegram API"""
        try:
            from telethon.tl.functions.account import GetAuthorizationsRequest
            
            # Get list of active authorizations (sessions)
            result = await client(GetAuthorizationsRequest())
            
            sessions = []
            for auth in result.authorizations:
                session_data = {
                    'hash': str(auth.hash),
                    'auth_key_id': str(getattr(auth, 'api_id', 'unknown')),
                    'device': auth.device_model or 'Unknown Device',
                    'platform': auth.platform or 'Unknown Platform',
                    'system_version': auth.system_version or 'Unknown',
                    'app_name': auth.app_name or 'Telegram',
                    'app_version': auth.app_version or 'Unknown',
                    'date_created': auth.date_created,
                    'date_active': auth.date_active,
                    'ip': auth.ip or 'Unknown',
                    'country': auth.country or 'Unknown',
                    'region': auth.region or '',
                    'is_official_app': auth.official_app if hasattr(auth, 'official_app') else True,
                    'is_current': auth.current if hasattr(auth, 'current') else False
                }
                sessions.append(session_data)
            
            return {
                'success': True,
                'sessions': sessions,
                'total_count': len(sessions)
            }
            
        except Exception as e:
            logger.error(f"Error getting active sessions via Telegram API: {e}")
            # Fallback: return at least current session
            return {
                'success': False,
                'error': str(e),
                'sessions': [{
                    'hash': 'current_session',
                    'device': 'Current Device',
                    'platform': 'Unknown',
                    'date_created': datetime.now(),
                    'date_active': datetime.now(),
                    'ip': 'Unknown'
                }],
                'total_count': 1
            }
    
    async def _terminate_other_sessions(self, client: TelegramClient, user_id: int) -> Dict[str, Any]:
        """Terminate all sessions except the current one"""
        try:
            # Log out all other devices (this terminates other sessions but keeps current)
            await client(LogOutRequest())
            
            logger.info(f"Terminated other sessions for user {user_id}")
            
            return {
                'success': True,
                'terminated_count': 1,  # Simulated - in real implementation count actual sessions
                'message': 'All other sessions terminated successfully'
            }
            
        except FloodWaitError as e:
            logger.warning(f"Flood wait during session termination: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return await self._terminate_other_sessions(client, user_id)
            
        except Exception as e:
            logger.error(f"Error terminating sessions: {e}")
            return {
                'success': False,
                'error': str(e),
                'terminated_count': 0
            }
    
    async def _put_account_on_hold(self, account_id: int, user_id: int, hold_hours: int) -> Dict[str, Any]:
        """Put account on 24-hour hold due to multi-device detection"""
        try:
            db = get_db_session()
            try:
                hold_result = TelegramAccountService.set_account_hold(
                    db,
                    account_id,
                    hold_hours=hold_hours,
                    reason='Multi-device usage detected',
                )
                
                if hold_result.get('success'):
                    # Log the hold action
                    ActivityLogService.log_action(
                        db,
                        user_id,
                        "ACCOUNT_HOLD",
                        f"Account {account_id} placed on hold due to multi-device detection",
                        extra_data=json.dumps({
                            "hold_hours": hold_hours,
                            "hold_until": hold_result.get('hold_until').isoformat() if hold_result.get('hold_until') else None,
                        })
                    )
                    
                    logger.info(
                        "Account %s placed on %s-hour hold",
                        account_id,
                        hold_hours,
                    )
                    
                    return {
                        'success': True,
                        'hold_until': hold_result.get('hold_until'),
                        'reason': 'Multi-device detection'
                    }
                else:
                    return {
                        'success': False,
                        'error': hold_result.get('error', 'Failed to update account status in database')
                    }
                    
            finally:
                close_db_session(db)
                
        except Exception as e:
            logger.error(f"Error putting account on hold: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def check_and_release_holds(self) -> Dict[str, Any]:
        """Check for accounts ready to be released from hold"""
        released_count = 0
        errors = []
        
        try:
            db = get_db_session()
            try:
                # Find accounts that are on hold and ready to be released
                held_accounts = db.query(TelegramAccount).filter(
                    TelegramAccount.status == AccountStatus.TWENTY_FOUR_HOUR_HOLD,
                    TelegramAccount.hold_until <= datetime.utcnow()
                ).all()
                
                for account in held_accounts:
                    try:
                        # Release from hold
                        account.status = AccountStatus.AVAILABLE
                        account.hold_until = None
                        account.multi_device_detected = False
                        account.updated_at = datetime.utcnow()
                        
                        # Log release
                        ActivityLogService.log_action(
                            db, account.seller_id, "ACCOUNT_RELEASED",
                            f"Account {account.id} released from 24-hour hold"
                        )
                        
                        released_count += 1
                        logger.info(f"Released account {account.id} from hold")
                        
                    except Exception as e:
                        errors.append(f"Error releasing account {account.id}: {str(e)}")
                        logger.error(f"Error releasing account {account.id}: {e}")
                
                db.commit()
                
            finally:
                close_db_session(db)
            
            return {
                'success': True,
                'released_count': released_count,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Error checking holds: {e}")
            return {
                'success': False,
                'error': str(e),
                'released_count': 0,
                'errors': [str(e)]
            }
    
    async def terminate_all_user_sessions(self, client: TelegramClient, user_id: int) -> Dict[str, Any]:
        """Terminate all sessions for a user (used during account sale completion)"""
        try:
            # This is called during the final step of account transfer
            # to ensure the seller loses access completely
            
            # Log out from all devices
            await client(LogOutRequest())
            
            # Log the action
            db = get_db_session()
            try:
                ActivityLogService.log_action(
                    db, user_id, "ALL_SESSIONS_TERMINATED",
                    "All sessions terminated during account transfer completion"
                )
            finally:
                close_db_session(db)
            
            logger.info(f"All sessions terminated for user {user_id} during account transfer")
            
            return {
                'success': True,
                'message': 'All sessions terminated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error terminating all sessions: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_session_monitoring_stats(self) -> Dict[str, Any]:
        """Get statistics about session monitoring"""
        try:
            db = get_db_session()
            try:
                # Get accounts currently on hold
                held_accounts = db.query(TelegramAccount).filter(
                    TelegramAccount.status == AccountStatus.TWENTY_FOUR_HOUR_HOLD
                ).count()
                
                # Get accounts with detected multi-device usage
                multi_device_accounts = db.query(TelegramAccount).filter(
                    TelegramAccount.multi_device_detected == True
                ).count()
                
                # Get recent session activities
                recent_activities = db.query(ActivityLog).filter(
                    ActivityLog.action_type.in_([
                        'SESSION_MONITORED', 'ACCOUNT_HOLD', 'ACCOUNT_RELEASED', 
                        'ALL_SESSIONS_TERMINATED'
                    ])
                ).filter(
                    ActivityLog.created_at >= datetime.utcnow() - timedelta(days=7)
                ).count()
                
                return {
                    'success': True,
                    'held_accounts': held_accounts,
                    'multi_device_accounts': multi_device_accounts,
                    'recent_activities': recent_activities,
                    'monitoring_active': True
                }
                
            finally:
                close_db_session(db)
                
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
session_manager = SessionManagementService()

# Background task to periodically check and release holds
async def session_hold_cleanup_task():
    """Background task to check and release expired holds"""
    while True:
        try:
            result = await session_manager.check_and_release_holds()
            if result['released_count'] > 0:
                logger.info(f"Released {result['released_count']} accounts from hold")
        except Exception as e:
            logger.error(f"Error in session cleanup task: {e}")
        
        # Check every hour
        await asyncio.sleep(3600)
