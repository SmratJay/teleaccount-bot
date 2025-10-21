"""
Country-Based Session File Management System
Manages Telegram sessions organized by country code with metadata tracking
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.tl.functions.auth import CheckPasswordRequest

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages Telegram session files organized by country"""
    
    def __init__(self, base_sessions_dir: str = "sessions"):
        """
        Initialize session manager
        
        Args:
            base_sessions_dir: Base directory for storing session files (default: 'sessions/')
        """
        self.base_dir = Path(base_sessions_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Create metadata directory
        self.metadata_dir = self.base_dir / "_metadata"
        self.metadata_dir.mkdir(exist_ok=True)
        
        logger.info(f"SessionManager initialized with base directory: {self.base_dir}")
    
    def get_country_code_from_phone(self, phone: str) -> str:
        """
        Extract country code from phone number
        
        Args:
            phone: Phone number (e.g., '+919821757044')
        
        Returns:
            Country code (e.g., 'IN' for India, 'US' for USA)
        """
        phone = phone.replace('+', '').replace(' ', '').replace('-', '')
        
        # Country code mappings (top countries)
        country_mappings = {
            '1': 'US',      # USA/Canada
            '7': 'RU',      # Russia
            '20': 'EG',     # Egypt
            '27': 'ZA',     # South Africa
            '30': 'GR',     # Greece
            '31': 'NL',     # Netherlands
            '32': 'BE',     # Belgium
            '33': 'FR',     # France
            '34': 'ES',     # Spain
            '36': 'HU',     # Hungary
            '39': 'IT',     # Italy
            '40': 'RO',     # Romania
            '41': 'CH',     # Switzerland
            '43': 'AT',     # Austria
            '44': 'GB',     # UK
            '45': 'DK',     # Denmark
            '46': 'SE',     # Sweden
            '47': 'NO',     # Norway
            '48': 'PL',     # Poland
            '49': 'DE',     # Germany
            '51': 'PE',     # Peru
            '52': 'MX',     # Mexico
            '53': 'CU',     # Cuba
            '54': 'AR',     # Argentina
            '55': 'BR',     # Brazil
            '56': 'CL',     # Chile
            '57': 'CO',     # Colombia
            '58': 'VE',     # Venezuela
            '60': 'MY',     # Malaysia
            '61': 'AU',     # Australia
            '62': 'ID',     # Indonesia
            '63': 'PH',     # Philippines
            '64': 'NZ',     # New Zealand
            '65': 'SG',     # Singapore
            '66': 'TH',     # Thailand
            '81': 'JP',     # Japan
            '82': 'KR',     # South Korea
            '84': 'VN',     # Vietnam
            '86': 'CN',     # China
            '90': 'TR',     # Turkey
            '91': 'IN',     # India
            '92': 'PK',     # Pakistan
            '93': 'AF',     # Afghanistan
            '94': 'LK',     # Sri Lanka
            '95': 'MM',     # Myanmar
            '98': 'IR',     # Iran
            '212': 'MA',    # Morocco
            '213': 'DZ',    # Algeria
            '216': 'TN',    # Tunisia
            '218': 'LY',    # Libya
            '220': 'GM',    # Gambia
            '221': 'SN',    # Senegal
            '222': 'MR',    # Mauritania
            '223': 'ML',    # Mali
            '224': 'GN',    # Guinea
            '225': 'CI',    # Ivory Coast
            '226': 'BF',    # Burkina Faso
            '227': 'NE',    # Niger
            '228': 'TG',    # Togo
            '229': 'BJ',    # Benin
            '230': 'MU',    # Mauritius
            '231': 'LR',    # Liberia
            '232': 'SL',    # Sierra Leone
            '233': 'GH',    # Ghana
            '234': 'NG',    # Nigeria
            '235': 'TD',    # Chad
            '236': 'CF',    # Central African Republic
            '237': 'CM',    # Cameroon
            '238': 'CV',    # Cape Verde
            '239': 'ST',    # Sao Tome and Principe
            '240': 'GQ',    # Equatorial Guinea
            '241': 'GA',    # Gabon
            '242': 'CG',    # Republic of Congo
            '243': 'CD',    # Democratic Republic of Congo
            '244': 'AO',    # Angola
            '245': 'GW',    # Guinea-Bissau
            '246': 'IO',    # British Indian Ocean Territory
            '248': 'SC',    # Seychelles
            '249': 'SD',    # Sudan
            '250': 'RW',    # Rwanda
            '251': 'ET',    # Ethiopia
            '252': 'SO',    # Somalia
            '253': 'DJ',    # Djibouti
            '254': 'KE',    # Kenya
            '255': 'TZ',    # Tanzania
            '256': 'UG',    # Uganda
            '257': 'BI',    # Burundi
            '258': 'MZ',    # Mozambique
            '260': 'ZM',    # Zambia
            '261': 'MG',    # Madagascar
            '262': 'RE',    # Reunion
            '263': 'ZW',    # Zimbabwe
            '264': 'NA',    # Namibia
            '265': 'MW',    # Malawi
            '266': 'LS',    # Lesotho
            '267': 'BW',    # Botswana
            '268': 'SZ',    # Swaziland
            '269': 'KM',    # Comoros
            '290': 'SH',    # Saint Helena
            '291': 'ER',    # Eritrea
            '297': 'AW',    # Aruba
            '298': 'FO',    # Faroe Islands
            '299': 'GL',    # Greenland
            '350': 'GI',    # Gibraltar
            '351': 'PT',    # Portugal
            '352': 'LU',    # Luxembourg
            '353': 'IE',    # Ireland
            '354': 'IS',    # Iceland
            '355': 'AL',    # Albania
            '356': 'MT',    # Malta
            '357': 'CY',    # Cyprus
            '358': 'FI',    # Finland
            '359': 'BG',    # Bulgaria
            '370': 'LT',    # Lithuania
            '371': 'LV',    # Latvia
            '372': 'EE',    # Estonia
            '373': 'MD',    # Moldova
            '374': 'AM',    # Armenia
            '375': 'BY',    # Belarus
            '376': 'AD',    # Andorra
            '377': 'MC',    # Monaco
            '378': 'SM',    # San Marino
            '380': 'UA',    # Ukraine
            '381': 'RS',    # Serbia
            '382': 'ME',    # Montenegro
            '383': 'XK',    # Kosovo
            '385': 'HR',    # Croatia
            '386': 'SI',    # Slovenia
            '387': 'BA',    # Bosnia and Herzegovina
            '389': 'MK',    # North Macedonia
            '420': 'CZ',    # Czech Republic
            '421': 'SK',    # Slovakia
            '423': 'LI',    # Liechtenstein
            '501': 'BZ',    # Belize
            '502': 'GT',    # Guatemala
            '503': 'SV',    # El Salvador
            '504': 'HN',    # Honduras
            '505': 'NI',    # Nicaragua
            '506': 'CR',    # Costa Rica
            '507': 'PA',    # Panama
            '508': 'PM',    # Saint Pierre and Miquelon
            '509': 'HT',    # Haiti
            '590': 'GP',    # Guadeloupe
            '591': 'BO',    # Bolivia
            '592': 'GY',    # Guyana
            '593': 'EC',    # Ecuador
            '594': 'GF',    # French Guiana
            '595': 'PY',    # Paraguay
            '596': 'MQ',    # Martinique
            '597': 'SR',    # Suriname
            '598': 'UY',    # Uruguay
            '599': 'AN',    # Netherlands Antilles
            '670': 'TL',    # East Timor
            '672': 'NF',    # Norfolk Island
            '673': 'BN',    # Brunei
            '674': 'NR',    # Nauru
            '675': 'PG',    # Papua New Guinea
            '676': 'TO',    # Tonga
            '677': 'SB',    # Solomon Islands
            '678': 'VU',    # Vanuatu
            '679': 'FJ',    # Fiji
            '680': 'PW',    # Palau
            '681': 'WF',    # Wallis and Futuna
            '682': 'CK',    # Cook Islands
            '683': 'NU',    # Niue
            '685': 'WS',    # Samoa
            '686': 'KI',    # Kiribati
            '687': 'NC',    # New Caledonia
            '688': 'TV',    # Tuvalu
            '689': 'PF',    # French Polynesia
            '690': 'TK',    # Tokelau
            '691': 'FM',    # Micronesia
            '692': 'MH',    # Marshall Islands
            '850': 'KP',    # North Korea
            '852': 'HK',    # Hong Kong
            '853': 'MO',    # Macau
            '855': 'KH',    # Cambodia
            '856': 'LA',    # Laos
            '880': 'BD',    # Bangladesh
            '886': 'TW',    # Taiwan
            '960': 'MV',    # Maldives
            '961': 'LB',    # Lebanon
            '962': 'JO',    # Jordan
            '963': 'SY',    # Syria
            '964': 'IQ',    # Iraq
            '965': 'KW',    # Kuwait
            '966': 'SA',    # Saudi Arabia
            '967': 'YE',    # Yemen
            '968': 'OM',    # Oman
            '970': 'PS',    # Palestinian Territory
            '971': 'AE',    # United Arab Emirates
            '972': 'IL',    # Israel
            '973': 'BH',    # Bahrain
            '974': 'QA',    # Qatar
            '975': 'BT',    # Bhutan
            '976': 'MN',    # Mongolia
            '977': 'NP',    # Nepal
            '992': 'TJ',    # Tajikistan
            '993': 'TM',    # Turkmenistan
            '994': 'AZ',    # Azerbaijan
            '995': 'GE',    # Georgia
            '996': 'KG',    # Kyrgyzstan
            '998': 'UZ',    # Uzbekistan
        }
        
        # Try to match country code (longest match first)
        for code_len in [3, 2, 1]:
            prefix = phone[:code_len]
            if prefix in country_mappings:
                return country_mappings[prefix]
        
        # Default to XX if unknown
        return 'XX'
    
    def get_country_dir(self, country_code: str) -> Path:
        """
        Get directory path for a specific country
        
        Args:
            country_code: ISO country code (e.g., 'IN', 'US')
        
        Returns:
            Path to country-specific directory
        """
        country_dir = self.base_dir / country_code.upper()
        country_dir.mkdir(exist_ok=True)
        return country_dir
    
    def save_session_by_country(
        self,
        phone: str,
        session_file: str,
        metadata: Optional[Dict[str, Any]] = None,
        cookies: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Save session file organized by country code
        
        Args:
            phone: Phone number (e.g., '+919821757044')
            session_file: Path to existing .session file
            metadata: Optional metadata (status, 2FA, etc.)
            cookies: Optional cookies data
        
        Returns:
            Dictionary with paths to saved files
        """
        try:
            country_code = self.get_country_code_from_phone(phone)
            country_dir = self.get_country_dir(country_code)
            
            # Generate clean phone identifier
            phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Copy session file
            session_filename = f"{phone_clean}_{timestamp}.session"
            session_dest = country_dir / session_filename
            
            if os.path.exists(session_file):
                shutil.copy2(session_file, session_dest)
                logger.info(f"✅ Session file copied: {session_dest}")
            else:
                logger.warning(f"⚠️ Session file not found: {session_file}")
            
            # Save metadata JSON
            metadata_dict = {
                'phone': phone,
                'phone_clean': phone_clean,
                'country_code': country_code,
                'session_file': session_filename,
                'created_at': datetime.now().isoformat(),
                'status': 'active',
                'has_2fa': False,
                'username': None,
                'user_id': None,
                'last_activity': None,
            }
            
            # Merge with provided metadata
            if metadata:
                metadata_dict.update(metadata)
            
            metadata_file = country_dir / f"{phone_clean}_{timestamp}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Metadata saved: {metadata_file}")
            
            # Save cookies if provided
            cookies_file = None
            if cookies:
                cookies_file = country_dir / f"{phone_clean}_{timestamp}_cookies.json"
                with open(cookies_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, indent=2)
                logger.info(f"✅ Cookies saved: {cookies_file}")
            
            # Update global index
            self._update_global_index(country_code, phone_clean, metadata_dict)
            
            return {
                'country_code': country_code,
                'session_file': str(session_dest),
                'metadata_file': str(metadata_file),
                'cookies_file': str(cookies_file) if cookies_file else None,
                'phone': phone,
            }
            
        except Exception as e:
            logger.error(f"❌ Error saving session by country: {e}", exc_info=True)
            return {}
    
    def get_country_sessions(self, country_code: str) -> List[Dict[str, Any]]:
        """
        Get all sessions for a specific country
        
        Args:
            country_code: ISO country code (e.g., 'IN')
        
        Returns:
            List of session metadata dictionaries
        """
        try:
            country_dir = self.get_country_dir(country_code)
            sessions = []
            
            # Find all metadata files
            for metadata_file in country_dir.glob("*_metadata.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        metadata['metadata_file'] = str(metadata_file)
                        sessions.append(metadata)
                except Exception as e:
                    logger.error(f"Error loading metadata {metadata_file}: {e}")
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting country sessions for {country_code}: {e}")
            return []
    
    def organize_existing_sessions(self, source_dir: str = ".") -> Dict[str, int]:
        """
        Organize existing .session files into country-based structure
        
        Args:
            source_dir: Directory containing existing session files
        
        Returns:
            Dictionary with statistics (organized, failed, skipped)
        """
        stats = {'organized': 0, 'failed': 0, 'skipped': 0}
        
        try:
            source_path = Path(source_dir)
            
            # Find all .session files
            session_files = list(source_path.glob("*.session"))
            logger.info(f"Found {len(session_files)} session files to organize")
            
            for session_file in session_files:
                try:
                    # Extract phone number from filename
                    # Patterns: secure_b336237c.session, clean_otp_6733908384.session
                    filename = session_file.stem
                    
                    # Try to extract phone from session using Telethon
                    phone = self._extract_phone_from_session(str(session_file))
                    
                    if not phone:
                        logger.warning(f"⚠️ Could not extract phone from {session_file.name}, skipping")
                        stats['skipped'] += 1
                        continue
                    
                    # Save to country-based structure
                    result = self.save_session_by_country(
                        phone=phone,
                        session_file=str(session_file),
                        metadata={'original_filename': session_file.name}
                    )
                    
                    if result:
                        logger.info(f"✅ Organized {session_file.name} → {result['country_code']}/")
                        stats['organized'] += 1
                    else:
                        stats['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error organizing {session_file.name}: {e}")
                    stats['failed'] += 1
            
            logger.info(f"Organization complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error organizing sessions: {e}", exc_info=True)
            return stats
    
    def _extract_phone_from_session(self, session_file: str) -> Optional[str]:
        """
        Extract phone number from session file using Telethon
        
        Args:
            session_file: Path to .session file
        
        Returns:
            Phone number or None
        """
        try:
            # Try to read session metadata
            # Session files store phone in internal structure
            # This is a simplified approach - you may need API credentials
            import sqlite3
            
            # Telethon sessions are SQLite databases
            conn = sqlite3.connect(session_file)
            cursor = conn.cursor()
            
            # Try to get phone from session
            cursor.execute("SELECT phone FROM sessions")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return result[0]
            
        except Exception as e:
            logger.debug(f"Could not extract phone from {session_file}: {e}")
        
        return None
    
    def _update_global_index(self, country_code: str, phone_clean: str, metadata: Dict):
        """
        Update global index file with session information
        
        Args:
            country_code: Country code
            phone_clean: Cleaned phone number
            metadata: Session metadata
        """
        try:
            index_file = self.metadata_dir / "global_index.json"
            
            # Load existing index
            index = {}
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
            
            # Update index
            if country_code not in index:
                index[country_code] = {}
            
            index[country_code][phone_clean] = {
                'phone': metadata.get('phone'),
                'created_at': metadata.get('created_at'),
                'status': metadata.get('status'),
                'session_file': metadata.get('session_file'),
            }
            
            # Save index
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error updating global index: {e}")
    
    def get_session_info(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific session
        
        Args:
            phone: Phone number
        
        Returns:
            Session metadata or None
        """
        try:
            country_code = self.get_country_code_from_phone(phone)
            sessions = self.get_country_sessions(country_code)
            
            phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '')
            
            for session in sessions:
                if session.get('phone_clean') == phone_clean:
                    return session
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting session info for {phone}: {e}")
            return None
    
    async def test_session(self, session_file: str, api_id: int, api_hash: str) -> Dict[str, Any]:
        """
        Test if a session file is still valid and authorized
        
        Args:
            session_file: Path to .session file
            api_id: Telegram API ID
            api_hash: Telegram API hash
        
        Returns:
            Dictionary with test results
        """
        try:
            client = TelegramClient(session_file.replace('.session', ''), api_id, api_hash)
            await client.connect()
            
            result = {
                'connected': True,
                'authorized': False,
                'phone': None,
                'user_id': None,
                'username': None,
                'error': None
            }
            
            if await client.is_user_authorized():
                result['authorized'] = True
                me = await client.get_me()
                result['phone'] = me.phone
                result['user_id'] = me.id
                result['username'] = me.username
            
            await client.disconnect()
            return result
            
        except Exception as e:
            return {
                'connected': False,
                'authorized': False,
                'error': str(e)
            }


# Standalone functions for session manipulation
async def enable_2fa(
    client: TelegramClient,
    password: str,
    hint: str = "",
    email: Optional[str] = None
) -> bool:
    """
    Enable 2FA (Two-Factor Authentication) on account
    
    Args:
        client: Connected and authorized Telethon client
        password: New password to set
        hint: Password hint
        email: Recovery email (optional)
    
    Returns:
        True if successful
    """
    try:
        from telethon.tl.functions.account import UpdatePasswordSettingsRequest, GetPasswordRequest
        from telethon.tl.types.account import PasswordInputSettings
        
        # Get current password state
        password_state = await client(GetPasswordRequest())
        
        # Set new password
        await client(UpdatePasswordSettingsRequest(
            password=password_state,
            new_settings=PasswordInputSettings(
                new_algo=password_state.new_algo,
                new_password_hash=password.encode(),
                hint=hint,
                email=email,
            )
        ))
        
        logger.info("✅ 2FA enabled successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enabling 2FA: {e}")
        return False


async def change_username(client: TelegramClient, new_username: str) -> bool:
    """
    Change account username
    
    Args:
        client: Connected and authorized Telethon client
        new_username: New username (without @)
    
    Returns:
        True if successful
    """
    try:
        await client(UpdateUsernameRequest(new_username))
        logger.info(f"✅ Username changed to @{new_username}")
        return True
    except Exception as e:
        logger.error(f"❌ Error changing username: {e}")
        return False


async def update_profile(
    client: TelegramClient,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    about: Optional[str] = None
) -> bool:
    """
    Update profile information
    
    Args:
        client: Connected and authorized Telethon client
        first_name: New first name
        last_name: New last name
        about: New bio/about text
    
    Returns:
        True if successful
    """
    try:
        await client(UpdateProfileRequest(
            first_name=first_name or "",
            last_name=last_name or "",
            about=about or ""
        ))
        logger.info("✅ Profile updated successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating profile: {e}")
        return False


async def set_profile_photo(client: TelegramClient, photo_path: str) -> bool:
    """
    Set profile photo
    
    Args:
        client: Connected and authorized Telethon client
        photo_path: Path to photo file
    
    Returns:
        True if successful
    """
    try:
        await client(UploadProfilePhotoRequest(
            file=await client.upload_file(photo_path)
        ))
        logger.info(f"✅ Profile photo set from {photo_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Error setting profile photo: {e}")
        return False


async def delete_profile_photos(client: TelegramClient, delete_all: bool = False) -> bool:
    """
    Delete profile photos
    
    Args:
        client: Connected and authorized Telethon client
        delete_all: If True, delete all photos. If False, delete current photo only.
    
    Returns:
        True if successful
    """
    try:
        photos = await client.get_profile_photos('me')
        
        if not photos:
            logger.info("No profile photos to delete")
            return True
        
        photos_to_delete = photos if delete_all else [photos[0]]
        
        await client(DeletePhotosRequest(photos_to_delete))
        logger.info(f"✅ Deleted {len(photos_to_delete)} profile photo(s)")
        return True
    except Exception as e:
        logger.error(f"❌ Error deleting profile photos: {e}")
        return False

