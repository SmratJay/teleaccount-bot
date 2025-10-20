"""Add missing model classes to database/models.py"""

missing_classes = '''

class AccountSaleLog:
    """Stub AccountSaleLog model for tracking account sales."""
    def __init__(self, account_id, buyer_id, price, **kwargs):
        self.id = 1
        self.account_id = account_id
        self.buyer_id = buyer_id
        self.price = price
        self.status = kwargs.get('status', 'pending')
        self.created_at = kwargs.get('created_at')
        self.frozen_until = kwargs.get('frozen_until')


class AccountSale:
    """Stub AccountSale model for analytics."""
    def __init__(self, account_id, buyer_id, price, **kwargs):
        self.id = 1
        self.account_id = account_id
        self.buyer_id = buyer_id
        self.price = price
        self.status = kwargs.get('status', 'completed')
        self.created_at = kwargs.get('created_at')


class SaleLogStatus:
    """Stub SaleLogStatus enum."""
    PENDING = 'pending'
    FROZEN = 'frozen'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
'''

with open('d:/teleaccount_bot/database/models.py', 'a', encoding='utf-8') as f:
    f.write(missing_classes)

print("✅ Added missing model classes to database/models.py")

# Test import
from database.models import AccountSaleLog, AccountSale, SaleLogStatus
print("✅ All models import successfully!")
