-- Who asked for each admin sign-in token, as SHA-256(daily rate_salt | "admin-login" | IP), never the raw IP. The per-address
-- cap counts per requester, so requests from other addresses can't use up the owner's sign-ins (src/admin.js login()).
ALTER TABLE admin_login_tokens ADD COLUMN requester TEXT;
CREATE INDEX IF NOT EXISTS admin_login_tokens_requester ON admin_login_tokens(email, requester, created_at);
