"""
System Status and Capacity Management Service
Handles global system status messages and user status management
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from database import get_db_session, close_db_session
from database.operations import UserService, SystemSettingsService, ActivityLogService
from database.models import User, UserStatus

logger = logging.getLogger(__name__)

class SystemStatusService:
    """Service for managing system status and capacity information"""
    
    def __init__(self):
        self.status_levels = {
            'normal': '🟢 Normal Load - All systems operational',
            'moderate': '🟡 Moderate Load - Slightly increased traffic',
            'high': '🟠 High Load - System under heavy use',
            'overload': '🔴 System Overload - Reduced performance',
            'maintenance': '⚪ Maintenance Mode - Limited functionality'
        }
        
        self.capacity_thresholds = {
            'normal': (0, 70),      # 0-70% capacity
            'moderate': (70, 85),   # 70-85% capacity
            'high': (85, 95),       # 85-95% capacity
            'overload': (95, 100),  # 95-100% capacity
        }
    
    async def get_system_capacity_info(self) -> Dict[str, Any]:
        """Get comprehensive system capacity and status information"""
        db = get_db_session()
        try:
            # Get current system metrics
            metrics = await self._calculate_system_metrics(db)
            
            # Determine current status level
            capacity_percentage = metrics['capacity_percentage']
            status_level = self._get_status_level(capacity_percentage)
            
            # Get custom system message if set by admin
            custom_message = SystemSettingsService.get_setting(
                db, "system_status_message", None
            )
            
            status_info = {
                'status_level': status_level,
                'status_message': custom_message or self.status_levels[status_level],
                'capacity_percentage': capacity_percentage,
                'metrics': metrics,
                'last_updated': datetime.now().isoformat(),
                'active_users_24h': metrics['active_users_24h'],
                'total_sales_today': metrics['sales_today'],
                'pending_withdrawals': metrics['pending_withdrawals'],
                'system_uptime': self._get_system_uptime(),
                'recommendations': self._get_user_recommendations(status_level)
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting system capacity info: {e}")
            return {
                'status_level': 'normal',
                'status_message': '🟢 System Status Available',
                'capacity_percentage': 0,
                'error': str(e)
            }
        finally:
            close_db_session(db)
    
    async def _calculate_system_metrics(self, db) -> Dict[str, Any]:
        """Calculate various system metrics for capacity assessment"""
        try:
            # Time boundaries
            now = datetime.now()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            last_24h = now - timedelta(hours=24)
            
            # User metrics
            total_users = db.query(User).count()
            active_users_24h = db.query(User).filter(
                User.last_activity >= last_24h
            ).count() if hasattr(User, 'last_activity') else 0
            
            # Account sales metrics (would need TelegramAccount model)
            sales_today = 0  # Would calculate from actual sales
            pending_withdrawals = 0  # Would calculate from withdrawal requests
            
            # Calculate capacity percentage based on various factors
            base_capacity = max(total_users * 0.1, 10)  # Base load from total users
            active_load = active_users_24h * 2  # Active users create more load
            sales_load = sales_today * 5  # Each sale creates significant load
            
            total_load = base_capacity + active_load + sales_load
            max_capacity = 1000  # Configurable maximum system capacity
            
            capacity_percentage = min((total_load / max_capacity) * 100, 100)
            
            return {
                'total_users': total_users,
                'active_users_24h': active_users_24h,
                'sales_today': sales_today,
                'pending_withdrawals': pending_withdrawals,
                'capacity_percentage': round(capacity_percentage, 1),
                'total_load': total_load,
                'max_capacity': max_capacity,
                'calculated_at': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating system metrics: {e}")
            return {
                'total_users': 0,
                'active_users_24h': 0,
                'sales_today': 0,
                'pending_withdrawals': 0,
                'capacity_percentage': 0.0,
                'error': str(e)
            }
    
    def _get_status_level(self, capacity_percentage: float) -> str:
        """Determine status level based on capacity percentage"""
        for level, (min_cap, max_cap) in self.capacity_thresholds.items():
            if min_cap <= capacity_percentage < max_cap:
                return level
        return 'overload'  # If over 100%
    
    def _get_system_uptime(self) -> str:
        """Get system uptime information"""
        # This would typically track actual system start time
        # For now, return a placeholder
        return "System operational since startup"
    
    def _get_user_recommendations(self, status_level: str) -> List[str]:
        """Get user recommendations based on current system status"""
        recommendations = {
            'normal': [
                "✅ All features fully available",
                "⚡ Fast processing times",
                "🚀 Optimal time for account sales"
            ],
            'moderate': [
                "⏳ Slightly slower processing",
                "📊 Monitor your transactions",
                "💡 Consider off-peak hours for large operations"
            ],
            'high': [
                "🐌 Expect delayed responses",
                "⏰ Avoid non-urgent operations",
                "📱 Check back later for better performance"
            ],
            'overload': [
                "⚠️ System under heavy load",
                "🚫 Some features may be temporarily limited",
                "⏰ Please try again in a few minutes"
            ],
            'maintenance': [
                "🔧 System maintenance in progress",
                "🚫 Limited functionality available",
                "⏰ Normal service will resume shortly"
            ]
        }
        
        return recommendations.get(status_level, [])
    
    async def update_system_status(self, admin_id: int, new_status: str, 
                                 custom_message: Optional[str] = None) -> Dict[str, Any]:
        """Admin function to manually update system status"""
        db = get_db_session()
        try:
            # Validate status level
            if new_status not in self.status_levels:
                return {
                    'success': False,
                    'error': f'Invalid status level. Must be one of: {list(self.status_levels.keys())}'
                }
            
            # Update system settings
            if custom_message:
                SystemSettingsService.set_setting(db, "system_status_message", custom_message)
            else:
                SystemSettingsService.set_setting(db, "system_status_message", self.status_levels[new_status])
            
            SystemSettingsService.set_setting(db, "system_status_level", new_status)
            SystemSettingsService.set_setting(db, "status_last_updated", datetime.now().isoformat())
            
            # Log admin action
            admin_user = UserService.get_user_by_telegram_id(db, admin_id)
            if admin_user:
                ActivityLogService.log_action(
                    db, admin_user.id, "SYSTEM_STATUS_UPDATE",
                    f"System status changed to: {new_status}",
                    extra_data=json.dumps({
                        'new_status': new_status,
                        'custom_message': custom_message,
                        'previous_status': SystemSettingsService.get_setting(db, "system_status_level", "normal")
                    })
                )
            
            return {
                'success': True,
                'new_status': new_status,
                'message': custom_message or self.status_levels[new_status],
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating system status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            close_db_session(db)

class UserStatusService:
    """Service for managing individual user status"""
    
    def __init__(self):
        self.status_descriptions = {
            UserStatus.ACTIVE: "✅ Active - Full access to all features",
            UserStatus.PENDING_VERIFICATION: "⏳ Pending - Completing verification process",
            UserStatus.FROZEN: "❄️ Frozen - Account temporarily restricted",
            UserStatus.BANNED: "🚫 Banned - Account access denied",
            UserStatus.SUSPENDED: "⏸️ Suspended - Temporary account suspension"
        }
    
    async def get_user_status_info(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user status information"""
        db = get_db_session()
        try:
            user = UserService.get_user_by_telegram_id(db, user_id)
            if not user:
                return {
                    'status': 'unknown',
                    'description': 'User not found',
                    'error': 'User not in database'
                }
            
            status_info = {
                'status': user.status.value,
                'description': self.status_descriptions.get(user.status, "Unknown status"),
                'is_admin': user.is_admin,
                'is_leader': user.is_leader,
                'balance': user.balance,
                'member_since': user.created_at.strftime('%Y-%m-%d'),
                'last_activity': user.last_activity.strftime('%Y-%m-%d %H:%M') if hasattr(user, 'last_activity') and user.last_activity else 'Unknown',
                'total_sales': user.total_accounts_sold,
                'total_earnings': user.total_earnings,
                'verification_completed': user.verification_completed,
                'restrictions': self._get_user_restrictions(user),
                'next_actions': self._get_next_actions(user)
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting user status info: {e}")
            return {
                'status': 'error',
                'description': 'Error retrieving status',
                'error': str(e)
            }
        finally:
            close_db_session(db)
    
    def _get_user_restrictions(self, user: User) -> List[str]:
        """Get list of current user restrictions based on status"""
        restrictions = []
        
        if user.status == UserStatus.FROZEN:
            restrictions.extend([
                "🚫 Cannot sell accounts",
                "🚫 Cannot request withdrawals",
                "📞 Contact support to resolve"
            ])
        elif user.status == UserStatus.BANNED:
            restrictions.extend([
                "🚫 All features disabled",
                "🚫 Account access restricted",
                "📞 Appeal process available"
            ])
        elif user.status == UserStatus.SUSPENDED:
            restrictions.extend([
                "⏸️ Temporary feature limitation",
                "⏰ Suspension period active",
                "📞 Contact admin for details"
            ])
        elif user.status == UserStatus.PENDING_VERIFICATION:
            restrictions.extend([
                "⏳ Complete verification first",
                "🧩 Finish CAPTCHA and channel joins",
                "✅ Then access all features"
            ])
        
        if not restrictions:
            restrictions.append("🎉 No restrictions - Full access!")
        
        return restrictions
    
    def _get_next_actions(self, user: User) -> List[str]:
        """Get recommended next actions for user based on their status"""
        actions = []
        
        if user.status == UserStatus.PENDING_VERIFICATION:
            actions.extend([
                "🔓 Complete verification process",
                "🧩 Solve CAPTCHA challenge",
                "📢 Join required channels"
            ])
        elif user.status == UserStatus.ACTIVE:
            if user.balance > 50:
                actions.append("💸 Consider making a withdrawal")
            actions.append("📱 Sell more accounts to increase earnings")
            if not user.is_leader and user.total_accounts_sold > 10:
                actions.append("👑 You may qualify for leader status")
        elif user.status in [UserStatus.FROZEN, UserStatus.BANNED, UserStatus.SUSPENDED]:
            actions.extend([
                "📞 Contact support for assistance",
                "📧 Review account restrictions",
                "⏰ Wait for admin review"
            ])
        
        return actions
    
    async def update_user_status(self, admin_id: int, target_user_id: int, 
                               new_status: UserStatus, reason: str = "") -> Dict[str, Any]:
        """Admin function to manually update user status"""
        db = get_db_session()
        try:
            # Verify admin permissions
            admin_user = UserService.get_user_by_telegram_id(db, admin_id)
            if not admin_user or not admin_user.is_admin:
                return {
                    'success': False,
                    'error': 'Insufficient permissions'
                }
            
            # Get target user
            target_user = UserService.get_user_by_telegram_id(db, target_user_id)
            if not target_user:
                return {
                    'success': False,
                    'error': 'Target user not found'
                }
            
            # Store previous status
            previous_status = target_user.status
            
            # Update status
            target_user.status = new_status
            target_user.status_updated_at = datetime.now()
            target_user.status_updated_by = admin_user.id
            db.commit()
            
            # Log the action
            ActivityLogService.log_action(
                db, target_user.id, "STATUS_UPDATED",
                f"Status changed from {previous_status.value} to {new_status.value} by admin",
                extra_data=json.dumps({
                    'previous_status': previous_status.value,
                    'new_status': new_status.value,
                    'admin_id': admin_id,
                    'reason': reason
                })
            )
            
            return {
                'success': True,
                'previous_status': previous_status.value,
                'new_status': new_status.value,
                'reason': reason,
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating user status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            close_db_session(db)

# Global service instances
system_status_service = SystemStatusService()
user_status_service = UserStatusService()
