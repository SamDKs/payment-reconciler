-- Expected invoices: unique references and positive amounts in minor units.
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    amount_minor INTEGER NOT NULL CHECK(amount_minor > 0),
    currency TEXT NOT NULL CHECK(currency IN ('COP','USD')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','paid')),
    created_at TEXT NOT NULL,
    paid_at TEXT
);
-- Each event represents a payment reconciled within the same request.
CREATE TABLE IF NOT EXISTS payment_events (
    id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL,
    event_id TEXT NOT NULL,
    invoice_reference TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK(amount_minor > 0),
    currency TEXT NOT NULL CHECK(currency IN ('COP','USD')),
    result TEXT CHECK(result IN ('matched','unmatched','discrepancy','requires_review')),
    reason TEXT,
    invoice_id INTEGER REFERENCES invoices(id),
    created_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE(provider,event_id) -- Prevent duplicate event registration.
);
-- Enforce at most one matched payment per invoice even if application code fails.
CREATE UNIQUE INDEX IF NOT EXISTS one_match_per_invoice ON payment_events(invoice_id) WHERE result = 'matched';
-- Payment audit history committed in the same transaction as the outcome.
CREATE TABLE IF NOT EXISTS audit_entries (
    id INTEGER PRIMARY KEY,
    payment_event_id INTEGER NOT NULL REFERENCES payment_events(id),
    action TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);
