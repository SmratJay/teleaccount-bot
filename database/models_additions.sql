-- Database additions for Account Management System
-- Add these columns to telegram_accounts table:

ALTER TABLE telegram_accounts 
ADD COLUMN IF NOT EXISTS multi_device_last_detected TIMESTAMP;

-- Note: freeze management fields already exist:
-- freeze_reason, frozen_by_admin_id, freeze_timestamp, freeze_duration_hours, can_be_sold

-- Create account_sale_logs table for admin approval system
CREATE TABLE IF NOT EXISTS account_sale_logs (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES telegram_accounts(id) ON DELETE CASCADE,
    seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Sale details
    sale_price FLOAT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    
    -- Account snapshot
    account_phone VARCHAR(20) NOT NULL,
    account_original_name VARCHAR(255),
    account_original_username VARCHAR(255),
    account_is_frozen BOOLEAN DEFAULT FALSE,
    account_freeze_reason TEXT,
    
    -- Seller info
    seller_telegram_id INTEGER NOT NULL,
    seller_username VARCHAR(255),
    seller_name VARCHAR(255),
    
    -- Buyer info
    buyer_telegram_id INTEGER,
    buyer_username VARCHAR(255),
    buyer_name VARCHAR(255),
    
    -- Admin actions
    reviewed_by_admin_id INTEGER REFERENCES users(id),
    admin_action_notes TEXT,
    admin_action_timestamp TIMESTAMP,
    rejection_reason TEXT,
    
    -- Timestamps
    sale_initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sale_completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_sale_logs_status ON account_sale_logs(status);
CREATE INDEX IF NOT EXISTS idx_sale_logs_seller ON account_sale_logs(seller_id);
CREATE INDEX IF NOT EXISTS idx_sale_logs_account ON account_sale_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_sale_logs_frozen ON account_sale_logs(account_is_frozen);
CREATE INDEX IF NOT EXISTS idx_telegram_accounts_frozen ON telegram_accounts(can_be_sold);
