-- ============================================
-- STRIPE BILLING COLUMNS ON users
-- ============================================

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(32),
    ADD COLUMN IF NOT EXISTS subscription_current_period_end TIMESTAMP WITH TIME ZONE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_stripe_customer_id
    ON users(stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_stripe_subscription_id
    ON users(stripe_subscription_id)
    WHERE stripe_subscription_id IS NOT NULL;
