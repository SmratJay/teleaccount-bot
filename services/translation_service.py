"""
Translation Service for Bot Interface
Provides multilingual support for bot messages and interface elements
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TranslationService:
    """Handle all translation functionality for the bot."""
    
    def __init__(self):
        self.translations = {
            'en': {
                # Main Menu
                'welcome_message': "🎯 **Welcome to TeleAccount Bot!**\n\n💰 **Sell your Telegram accounts safely and get paid instantly!**\n\n📱 We help you sell verified Telegram accounts quickly and securely.",
                'lfg_sell': "🚀 LFG (Sell)",
                'account_details': "📋 Account Details", 
                'check_balance': "💰 Check Balance",
                'withdraw_menu': "💸 Withdraw",
                'language_menu': "🌍 Language",
                'system_capacity': "⚡ System Capacity",
                'main_menu': "🏠 Main Menu",
                'back_menu': "← Back to Menu",
                
                # Account Details
                'account_details_title': "📄 **Account Details**",
                'user_information': "👤 **User Information:**",
                'name_label': "• **Name:**",
                'username_label': "• **Username:**",
                'user_id_label': "• **User ID:**",
                'member_since_label': "• **Member Since:**",
                'account_statistics': "📱 **Account Statistics:**",
                'total_accounts': "• **Total Accounts:**",
                'available_to_sell': "• **Available to Sell:**",
                'already_sold': "• **Already Sold:**",
                'on_hold': "• **On Hold:**",
                'financial_summary': "💰 **Financial Summary:**",
                'current_balance': "• **Current Balance:**",
                'total_sold': "• **Total Sold:**",
                'total_earnings': "• **Total Earnings:**",
                'average_per_account': "• **Average per Account:**",
                'performance': "🎯 **Performance:**",
                'success_rate': "• **Success Rate:**",
                'status_label': "• **Status:**",
                
                # Withdrawal
                'withdraw_title': "💸 **Withdrawal Menu**",
                'select_currency': "Select your preferred cryptocurrency:",
                'withdraw_trx': "🟡 Withdraw TRX",
                'withdraw_usdt': "💚 Withdraw USDT",
                'withdraw_binance': "🟠 Withdraw BNB",
                'withdrawal_history': "📜 Withdrawal History",
                'minimum_amount': "Minimum withdrawal amount: $10.00",
                
                # Language
                'language_title': "🌍 **Language Selection**",
                'choose_language': "Choose your preferred language:",
                'available_languages': "**Available Languages:**",
                'language_applied': "*Language will be applied to all bot messages*",
                'language_updated': "✅ **Language Updated**",
                'language_changed_to': "Your language has been changed to",
                'language_active': "All bot interactions will now use",
                
                # Buttons
                'view_all_accounts': "📊 View All Accounts",
                'change_language': "🌍 Change Language",
                
                # Status messages
                'no_username': "No username",
                'error_loading': "❌ Error loading account details. Please try again.",
                'invalid_selection': "❌ Invalid language selection",
                'feature_coming_soon': "This feature is coming soon!",
                
                # Withdrawal status
                'withdrawal_approved': "✅ **Withdrawal Approved!**",
                'withdrawal_rejected': "❌ **Withdrawal Rejected**",
                'withdrawal_pending': "⏳ **Withdrawal Pending**",
                'withdrawal_completed': "🎉 **Withdrawal Completed!**",
                'amount_deducted': "Amount has been deducted from your balance.",
                'notification_sent': "You will receive updates on your withdrawal status."
            },
            'es': {
                # Main Menu
                'welcome_message': "🎯 **¡Bienvenido a TeleAccount Bot!**\n\n💰 **¡Vende tus cuentas de Telegram de forma segura y recibe pagos al instante!**\n\n📱 Te ayudamos a vender cuentas verificadas de Telegram de forma rápida y segura.",
                'lfg_sell': "🚀 LFG (Vender)",
                'account_details': "📋 Detalles de Cuenta",
                'check_balance': "💰 Verificar Saldo",
                'withdraw_menu': "💸 Retirar",
                'language_menu': "🌍 Idioma",
                'system_capacity': "⚡ Capacidad del Sistema",
                'main_menu': "🏠 Menú Principal",
                'back_menu': "← Volver al Menú",
                
                # Account Details
                'account_details_title': "📄 **Detalles de la Cuenta**",
                'user_information': "👤 **Información del Usuario:**",
                'name_label': "• **Nombre:**",
                'username_label': "• **Usuario:**",
                'user_id_label': "• **ID de Usuario:**",
                'member_since_label': "• **Miembro Desde:**",
                'account_statistics': "📱 **Estadísticas de Cuenta:**",
                'total_accounts': "• **Cuentas Totales:**",
                'available_to_sell': "• **Disponibles para Vender:**",
                'already_sold': "• **Ya Vendidas:**",
                'on_hold': "• **En Espera:**",
                'financial_summary': "💰 **Resumen Financiero:**",
                'current_balance': "• **Saldo Actual:**",
                'total_sold': "• **Total Vendido:**",
                'total_earnings': "• **Ganancias Totales:**",
                'average_per_account': "• **Promedio por Cuenta:**",
                'performance': "🎯 **Rendimiento:**",
                'success_rate': "• **Tasa de Éxito:**",
                'status_label': "• **Estado:**",
                
                # Language
                'language_title': "🌍 **Selección de Idioma**",
                'choose_language': "Elige tu idioma preferido:",
                'available_languages': "**Idiomas Disponibles:**",
                'language_applied': "*El idioma se aplicará a todos los mensajes del bot*",
                'language_updated': "✅ **Idioma Actualizado**",
                'language_changed_to': "Tu idioma ha sido cambiado a",
                'language_active': "Todas las interacciones del bot ahora usarán",
                
                # Buttons
                'view_all_accounts': "📊 Ver Todas las Cuentas",
                'change_language': "🌍 Cambiar Idioma",
                
                # Status messages
                'no_username': "Sin usuario",
                'error_loading': "❌ Error al cargar los detalles de la cuenta. Inténtalo de nuevo.",
                'invalid_selection': "❌ Selección de idioma inválida",
                
                # Withdrawal status
                'withdrawal_approved': "✅ **¡Retiro Aprobado!**",
                'withdrawal_rejected': "❌ **Retiro Rechazado**",
                'withdrawal_pending': "⏳ **Retiro Pendiente**",
                'withdrawal_completed': "🎉 **¡Retiro Completado!**",
                'amount_deducted': "El monto ha sido deducido de tu saldo.",
                'notification_sent': "Recibirás actualizaciones sobre el estado de tu retiro."
            },
            'fr': {
                # Main Menu
                'welcome_message': "🎯 **Bienvenue sur TeleAccount Bot!**\n\n💰 **Vendez vos comptes Telegram en toute sécurité et soyez payé instantanément!**\n\n📱 Nous vous aidons à vendre des comptes Telegram vérifiés rapidement et en toute sécurité.",
                'lfg_sell': "🚀 LFG (Vendre)",
                'account_details': "📋 Détails du Compte",
                'check_balance': "💰 Vérifier le Solde",
                'withdraw_menu': "💸 Retirer",
                'language_menu': "🌍 Langue",
                'system_capacity': "⚡ Capacité Système",
                'main_menu': "🏠 Menu Principal",
                'back_menu': "← Retour au Menu",
                
                'language_title': "🌍 **Sélection de Langue**",
                'choose_language': "Choisissez votre langue préférée:",
                'language_updated': "✅ **Langue Mise à Jour**",
                'language_changed_to': "Votre langue a été changée pour",
                'language_active': "Toutes les interactions du bot utiliseront maintenant",
            },
            'de': {
                'welcome_message': "🎯 **Willkommen bei TeleAccount Bot!**\n\n💰 **Verkaufen Sie Ihre Telegram-Konten sicher und werden Sie sofort bezahlt!**\n\n📱 Wir helfen Ihnen, verifizierte Telegram-Konten schnell und sicher zu verkaufen.",
                'lfg_sell': "🚀 LFG (Verkaufen)",
                'account_details': "📋 Kontodetails",
                'language_menu': "🌍 Sprache",
                'language_title': "🌍 **Sprachauswahl**",
                'language_updated': "✅ **Sprache Aktualisiert**",
                'language_changed_to': "Ihre Sprache wurde geändert zu",
            },
            'ru': {
                'welcome_message': "🎯 **Добро пожаловать в TeleAccount Bot!**\n\n💰 **Продавайте свои аккаунты Telegram безопасно и получайте мгновенную оплату!**\n\n📱 Мы поможем вам быстро и безопасно продать верифицированные аккаунты Telegram.",
                'lfg_sell': "🚀 LFG (Продать)",
                'account_details': "📋 Детали Аккаунта",
                'language_menu': "🌍 Язык",
                'language_title': "🌍 **Выбор Языка**",
                'language_updated': "✅ **Язык Обновлен**",
                'language_changed_to': "Ваш язык был изменен на",
            },
            'zh': {
                'welcome_message': "🎯 **欢迎使用 TeleAccount Bot！**\n\n💰 **安全出售您的 Telegram 账户并即时获得付款！**\n\n📱 我们帮助您快速安全地出售已验证的 Telegram 账户。",
                'lfg_sell': "🚀 LFG (出售)",
                'account_details': "📋 账户详情",
                'language_menu': "🌍 语言",
                'language_title': "🌍 **语言选择**",
                'language_updated': "✅ **语言已更新**",
                'language_changed_to': "您的语言已更改为",
            },
            'hi': {
                'welcome_message': "🎯 **TeleAccount Bot में आपका स्वागत है!**\n\n💰 **अपने Telegram खाते सुरक्षित रूप से बेचें और तुरंत भुगतान पाएं!**\n\n📱 हम आपको सत्यापित Telegram खाते जल्दी और सुरक्षित रूप से बेचने में मदद करते हैं।",
                'lfg_sell': "🚀 LFG (बेचें)",
                'account_details': "📋 खाता विवरण",
                'language_menu': "🌍 भाषा",
                'language_title': "🌍 **भाषा चयन**",
                'language_updated': "✅ **भाषा अपडेट की गई**",
                'language_changed_to': "आपकी भाषा बदल दी गई है",
            },
            'ar': {
                'welcome_message': "🎯 **مرحباً بكم في TeleAccount Bot!**\n\n💰 **بيع حسابات Telegram الخاصة بك بأمان واحصل على الدفع فوراً!**\n\n📱 نساعدك على بيع حسابات Telegram المحققة بسرعة وأمان.",
                'lfg_sell': "🚀 LFG (بيع)",
                'account_details': "📋 تفاصيل الحساب",
                'language_menu': "🌍 اللغة",
                'language_title': "🌍 **اختيار اللغة**",
                'language_updated': "✅ **تم تحديث اللغة**",
                'language_changed_to': "تم تغيير لغتك إلى",
            }
        }
        
        self.language_names = {
            'en': '🇺🇸 English',
            'es': '🇪🇸 Español',
            'fr': '🇫🇷 Français', 
            'de': '🇩🇪 Deutsch',
            'ru': '🇷🇺 Русский',
            'zh': '🇨🇳 中文',
            'hi': '🇮🇳 हिंदी',
            'ar': '🇦🇪 العربية'
        }
    
    def get_text(self, key: str, language: str = 'en', **kwargs) -> str:
        """Get translated text for a specific key and language."""
        try:
            # Get the translation dict for the language, fallback to English
            lang_dict = self.translations.get(language, self.translations['en'])
            
            # Get the text, fallback to English if key not found
            text = lang_dict.get(key, self.translations['en'].get(key, f"[Missing: {key}]"))
            
            # Format with any provided kwargs
            if kwargs:
                text = text.format(**kwargs)
                
            return text
        except Exception as e:
            logger.error(f"Translation error for key '{key}' in language '{language}': {e}")
            return f"[Translation Error: {key}]"
    
    def get_language_name(self, language_code: str) -> str:
        """Get the display name for a language code."""
        return self.language_names.get(language_code, '🇺🇸 English')
    
    def get_user_language(self, context: Any) -> str:
        """Get user's preferred language from context."""
        return context.user_data.get('language', 'en')
    
    def set_user_language(self, context: Any, language: str) -> None:
        """Set user's preferred language in context."""
        context.user_data['language'] = language

# Global translation service instance
translation_service = TranslationService()