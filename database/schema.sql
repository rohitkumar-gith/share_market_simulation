-- Share Market Simulation Database Schema (V2 - Virtual Economy)

-- ==========================================
-- 1. USERS & AUTH
-- ==========================================
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    wallet_balance REAL DEFAULT 100000.0,
    is_admin BOOLEAN DEFAULT 0,  -- New: Admin Privileges
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- ==========================================
-- 2. COMPANIES
-- ==========================================
CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT UNIQUE NOT NULL,
    owner_id INTEGER NOT NULL,
    ticker_symbol TEXT UNIQUE NOT NULL,
    share_price REAL DEFAULT 100.0,
    total_shares INTEGER NOT NULL,
    available_shares INTEGER NOT NULL,
    company_wallet REAL DEFAULT 0.0,
    net_worth REAL DEFAULT 0.0,
    description TEXT,
    is_bankrupt BOOLEAN DEFAULT 0, -- New: Bankruptcy Status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(user_id)
);

-- ==========================================
-- 3. TRADING CORE (Shares & Orders)
-- ==========================================
CREATE TABLE IF NOT EXISTS shares (
    share_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    issue_price REAL NOT NULL,
    shares_issued INTEGER NOT NULL,
    issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS share_orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    order_type TEXT NOT NULL, -- 'buy' or 'sell'
    quantity INTEGER NOT NULL,
    price_per_share REAL NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS user_holdings (
    holding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    average_buy_price REAL NOT NULL,
    total_invested REAL NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    UNIQUE(user_id, company_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER NOT NULL,
    seller_id INTEGER,
    company_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price_per_share REAL NOT NULL,
    total_amount REAL NOT NULL,
    transaction_type TEXT NOT NULL, -- 'ipo', 'trade'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (buyer_id) REFERENCES users(user_id),
    FOREIGN KEY (seller_id) REFERENCES users(user_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS price_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    price REAL NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- ==========================================
-- 4. FINANCE (Wallets & Dividends)
-- ==========================================
CREATE TABLE IF NOT EXISTS wallet_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    amount REAL NOT NULL,
    balance_after REAL NOT NULL,
    description TEXT,
    reference_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS company_wallet_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL, -- 'DEPOSIT', 'WITHDRAW', 'REVENUE', 'EXPENSE'
    amount REAL NOT NULL,
    balance_after REAL NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS dividends (
    dividend_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    dividend_per_share REAL NOT NULL,
    total_amount REAL NOT NULL,
    record_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payment_date TIMESTAMP,
    status TEXT DEFAULT 'declared',
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- ==========================================
-- 5. ASSET ECONOMY (Cars & Real Estate)
-- ==========================================
-- The Catalog (Created by Admin)
CREATE TABLE IF NOT EXISTS master_assets (
    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,         -- e.g., "Tesla Model S", "Downtown Office"
    asset_type TEXT NOT NULL,   -- 'CAR', 'REAL_ESTATE'
    base_price REAL NOT NULL,   -- Cost to buy from system
    revenue_rate REAL DEFAULT 0, -- Passive income per minute (for Companies)
    description TEXT,
    total_supply INTEGER DEFAULT -1, -- -1 for infinite
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- The Instances (Owned by Users or Companies)
CREATE TABLE IF NOT EXISTS owned_assets (
    instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    master_asset_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,
    owner_type TEXT NOT NULL, -- 'USER', 'COMPANY'
    acquired_price REAL NOT NULL,
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (master_asset_id) REFERENCES master_assets(asset_id)
);

-- The Marketplace (Second-hand Sales)
CREATE TABLE IF NOT EXISTS marketplace_listings (
    listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id INTEGER NOT NULL,
    seller_id INTEGER NOT NULL,
    seller_type TEXT NOT NULL, -- 'USER', 'COMPANY'
    asking_price REAL NOT NULL,
    status TEXT DEFAULT 'ACTIVE', -- 'ACTIVE', 'SOLD', 'CANCELLED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES owned_assets(instance_id)
);

-- ==========================================
-- 6. LOANS (Bank & B2B)
-- ==========================================
-- Bank Loans (System to User)
CREATE TABLE IF NOT EXISTS loans (
    loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    loan_amount REAL NOT NULL,
    interest_rate REAL NOT NULL,
    remaining_balance REAL NOT NULL,
    monthly_payment REAL NOT NULL,
    loan_term_months INTEGER NOT NULL,
    status TEXT DEFAULT 'active',
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS loan_payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id INTEGER NOT NULL,
    payment_amount REAL NOT NULL,
    principal_amount REAL NOT NULL,
    interest_amount REAL NOT NULL,
    remaining_balance REAL NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
);

-- B2B Loans (Company to Company)
CREATE TABLE IF NOT EXISTS inter_company_loans (
    loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lender_company_id INTEGER NOT NULL,
    borrower_company_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    interest_rate REAL NOT NULL,
    total_repayment REAL NOT NULL,
    status TEXT DEFAULT 'PENDING', -- 'PENDING', 'ACTIVE', 'COMPLETED', 'DEFAULTED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lender_company_id) REFERENCES companies(company_id),
    FOREIGN KEY (borrower_company_id) REFERENCES companies(company_id)
);

-- ==========================================
-- 7. SOCIAL & SYSTEM
-- ==========================================
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS bots (
    bot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_name TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    wallet_balance REAL DEFAULT 50000.0,
    strategy TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ==========================================
-- 8. INDEXES
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_user_holdings ON user_holdings(user_id, company_id);
CREATE INDEX IF NOT EXISTS idx_transactions ON transactions(buyer_id, seller_id, company_id);
CREATE INDEX IF NOT EXISTS idx_share_orders ON share_orders(user_id, company_id, status);
CREATE INDEX IF NOT EXISTS idx_price_history ON price_history(company_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_chat ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_marketplace ON marketplace_listings(status);