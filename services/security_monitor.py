"""
Advanced Security Monitoring and Alert System
Detects and responds to Telegram security threats in real-time
"""
import asyncio
import logging
import json
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
from telethon import events
from database import get_db_session, close_db_session
from database.operations import ActivityLogService

logger = logging.getLogger(__name__)

@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_type: str
    phone_number: str
    timestamp: datetime
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    metadata: Dict[str, Any]
    resolved: bool = False

@dataclass
class ThreatIndicator:
    """Threat detection indicator"""
    pattern: str
    severity: str
    action: str
    description: str

class SecurityMonitor:
    """Advanced security monitoring system"""
    
    def __init__(self):
        self.active_monitors = {}  # phone_number -> client
        self.security_events = []
        self.threat_indicators = self._load_threat_indicators()
        self.alert_callbacks = []
        self.rate_limiters = defaultdict(list)
        
    def _load_threat_indicators(self) -> List[ThreatIndicator]:
        """Load threat detection patterns"""
        return [
            ThreatIndicator(
                pattern=r"login.*attempt.*blocked",
                severity="critical",
                action="immediate_pause",
                description="Login attempt blocked by Telegram"
            ),
            ThreatIndicator(
                pattern=r"suspicious.*activity.*detected",
                severity="high",
                action="delay_and_retry",
                description="Suspicious activity detected"
            ),
            ThreatIndicator(
                pattern=r"verification.*code.*\d{5}",
                severity="medium",
                action="auto_extract_code",
                description="Verification code received"
            ),
            ThreatIndicator(
                pattern=r"account.*security.*warning",
                severity="high",
                action="security_review",
                description="Account security warning"
            ),
            ThreatIndicator(
                pattern=r"unusual.*login.*location",
                severity="medium",
                action="location_verification",
                description="Unusual login location detected"
            ),
            ThreatIndicator(
                pattern=r"two.factor.*authentication.*required",
                severity="medium",
                action="2fa_handling",
                description="2FA requirement detected"
            )
        ]
    
    async def start_monitoring(self, client, phone_number: str) -> bool:
        """Start comprehensive monitoring for a phone number"""
        try:
            if phone_number in self.active_monitors:
                logger.warning(f"Already monitoring {phone_number}")
                return False
            
            # Store monitoring info
            self.active_monitors[phone_number] = {
                'client': client,
                'started_at': datetime.now(),
                'events_count': 0,
                'last_activity': datetime.now()
            }
            
            # Set up event handlers
            await self._setup_event_handlers(client, phone_number)
            
            logger.info(f"Started comprehensive monitoring for {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting monitoring for {phone_number}: {e}")
            return False
    
    async def _setup_event_handlers(self, client, phone_number: str):
        """Set up comprehensive event handlers"""
        
        # Message monitoring for security notifications
        @client.on(events.NewMessage(incoming=True))
        async def message_handler(event):
            await self._handle_incoming_message(event, phone_number)
        
        # Connection state monitoring
        @client.on(events.Raw)
        async def raw_handler(event):
            await self._handle_raw_event(event, phone_number)
    
    async def _handle_incoming_message(self, event, phone_number: str):
        """Handle incoming messages for security analysis"""
        try:
            if not event.message or not event.message.message:
                return
            
            message_text = event.message.message.lower()
            sender_id = getattr(event, 'sender_id', None)
            
            # Check against threat indicators
            for indicator in self.threat_indicators:
                import re
                if re.search(indicator.pattern, message_text, re.IGNORECASE):
                    await self._trigger_security_event(
                        phone_number, indicator, message_text, event
                    )
            
            # Update activity tracking
            if phone_number in self.active_monitors:
                self.active_monitors[phone_number]['last_activity'] = datetime.now()
                self.active_monitors[phone_number]['events_count'] += 1
                
        except Exception as e:
            logger.error(f"Error handling message for {phone_number}: {e}")
    
    async def _handle_raw_event(self, event, phone_number: str):
        """Handle raw Telegram events for deep monitoring"""
        try:
            event_type = type(event).__name__
            
            # Monitor for connection issues
            if 'disconnect' in event_type.lower() or 'error' in event_type.lower():
                await self._log_connection_event(phone_number, event_type, event)
            
            # Monitor for authentication events
            if 'auth' in event_type.lower() or 'login' in event_type.lower():
                await self._log_auth_event(phone_number, event_type, event)
                
        except Exception as e:
            logger.error(f"Error handling raw event for {phone_number}: {e}")
    
    async def _trigger_security_event(self, phone_number: str, indicator: ThreatIndicator, 
                                     message: str, event):
        """Trigger security event and execute appropriate response"""
        try:
            # Create security event
            security_event = SecurityEvent(
                event_type=indicator.action,
                phone_number=phone_number,
                timestamp=datetime.now(),
                severity=indicator.severity,
                message=indicator.description,
                metadata={
                    'original_message': message,
                    'pattern_matched': indicator.pattern,
                    'sender_id': getattr(event, 'sender_id', None),
                    'event_id': getattr(event, 'id', None)
                }
            )
            
            # Store event
            self.security_events.append(security_event)
            
            # Log to database
            await self._log_security_event(security_event)
            
            # Execute response action
            await self._execute_security_response(security_event)
            
            # Trigger alerts
            await self._trigger_alerts(security_event)
            
        except Exception as e:
            logger.error(f"Error triggering security event: {e}")
    
    async def _execute_security_response(self, event: SecurityEvent):
        """Execute automated response to security event"""
        try:
            action = event.event_type
            phone_number = event.phone_number
            
            if action == "immediate_pause":
                # Pause all operations for this phone
                await self._pause_operations(phone_number, duration=3600)  # 1 hour
                logger.critical(f"IMMEDIATE PAUSE triggered for {phone_number}")
                
            elif action == "delay_and_retry":
                # Add delay before next operation
                delay = self._calculate_adaptive_delay(phone_number)
                await self._add_operation_delay(phone_number, delay)
                logger.warning(f"Adaptive delay {delay}s added for {phone_number}")
                
            elif action == "auto_extract_code":
                # Extract verification code automatically
                code = self._extract_verification_code(event.metadata['original_message'])
                if code:
                    await self._store_extracted_code(phone_number, code)
                    logger.info(f"Auto-extracted code for {phone_number}: {code}")
                    
            elif action == "security_review":
                # Mark for manual security review
                await self._mark_for_security_review(phone_number, event)
                logger.warning(f"Marked {phone_number} for security review")
                
            elif action == "location_verification":
                # Verify and adjust location-based settings
                await self._verify_location_settings(phone_number)
                
            elif action == "2fa_handling":
                # Handle 2FA requirement
                await self._handle_2fa_requirement(phone_number, event)
                
        except Exception as e:
            logger.error(f"Error executing security response: {e}")
    
    def _extract_verification_code(self, message: str) -> Optional[str]:
        """Extract verification code from message"""
        import re
        # Look for 5-digit codes
        code_match = re.search(r'\b(\d{5})\b', message)
        if code_match:
            return code_match.group(1)
        return None
    
    async def _store_extracted_code(self, phone_number: str, code: str):
        """Store extracted code for automatic use"""
        # Implementation would store in temporary cache
        logger.info(f"Storing extracted code for {phone_number}")
    
    def _calculate_adaptive_delay(self, phone_number: str) -> int:
        """Calculate adaptive delay based on recent events"""
        recent_events = [
            e for e in self.security_events 
            if e.phone_number == phone_number and 
            e.timestamp > datetime.now() - timedelta(hours=1)
        ]
        
        # Increase delay based on number of recent events
        base_delay = 300  # 5 minutes
        event_multiplier = len(recent_events) * 60  # 1 minute per event
        max_delay = 3600  # 1 hour max
        
        return min(base_delay + event_multiplier, max_delay)
    
    async def _pause_operations(self, phone_number: str, duration: int):
        """Pause all operations for specified duration"""
        if phone_number in self.active_monitors:
            self.active_monitors[phone_number]['paused_until'] = (
                datetime.now() + timedelta(seconds=duration)
            )
    
    async def _add_operation_delay(self, phone_number: str, delay: int):
        """Add delay before next operation"""
        if phone_number in self.active_monitors:
            self.active_monitors[phone_number]['next_operation_delay'] = delay
    
    async def _log_security_event(self, event: SecurityEvent):
        """Log security event to database"""
        try:
            db = get_db_session()
            
            ActivityLogService.log_action(
                db, 
                phone_number=event.phone_number,
                action=f"SECURITY_EVENT_{event.event_type.upper()}",
                details=f"{event.message} - Severity: {event.severity}"
            )
            
            close_db_session(db)
            
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
    
    async def _trigger_alerts(self, event: SecurityEvent):
        """Trigger alerts for security events"""
        try:
            for callback in self.alert_callbacks:
                await callback(event)
                
            # Console alert for critical events
            if event.severity == "critical":
                print(f"\n🚨 CRITICAL SECURITY ALERT 🚨")
                print(f"Phone: {event.phone_number}")
                print(f"Event: {event.message}")
                print(f"Time: {event.timestamp}")
                print(f"Action: {event.event_type}")
                print("=" * 50)
                
        except Exception as e:
            logger.error(f"Error triggering alerts: {e}")
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for security alerts"""
        self.alert_callbacks.append(callback)
    
    async def get_security_status(self, phone_number: str) -> Dict[str, Any]:
        """Get current security status for phone number"""
        try:
            if phone_number not in self.active_monitors:
                return {'status': 'not_monitored'}
            
            monitor_info = self.active_monitors[phone_number]
            recent_events = [
                asdict(e) for e in self.security_events 
                if e.phone_number == phone_number and 
                e.timestamp > datetime.now() - timedelta(hours=24)
            ]
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(phone_number)
            
            return {
                'status': 'monitored',
                'monitoring_duration': (datetime.now() - monitor_info['started_at']).total_seconds(),
                'events_count': monitor_info['events_count'],
                'last_activity': monitor_info['last_activity'].isoformat(),
                'recent_events': recent_events,
                'risk_score': risk_score,
                'is_paused': 'paused_until' in monitor_info,
                'next_delay': monitor_info.get('next_operation_delay', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting security status: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _calculate_risk_score(self, phone_number: str) -> float:
        """Calculate risk score based on recent events"""
        try:
            recent_events = [
                e for e in self.security_events 
                if e.phone_number == phone_number and 
                e.timestamp > datetime.now() - timedelta(hours=24)
            ]
            
            severity_weights = {
                'low': 1,
                'medium': 3,
                'high': 6,
                'critical': 10
            }
            
            total_score = sum(
                severity_weights.get(event.severity, 1) 
                for event in recent_events
            )
            
            # Normalize to 0-100 scale
            max_possible_score = 50  # Arbitrary maximum
            risk_score = min(total_score / max_possible_score * 100, 100)
            
            return round(risk_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 0.0
    
    async def stop_monitoring(self, phone_number: str) -> bool:
        """Stop monitoring for a phone number"""
        try:
            if phone_number in self.active_monitors:
                del self.active_monitors[phone_number]
                logger.info(f"Stopped monitoring for {phone_number}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error stopping monitoring for {phone_number}: {e}")
            return False

# Global security monitor instance
security_monitor = SecurityMonitor()
