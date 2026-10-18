-- App sign-in for the admin screen in the iOS app (src/admin.js): an 8-digit emailed code bound to a PKCE-style challenge.
ALTER TABLE admin_login_tokens ADD COLUMN challenge TEXT;                  -- base64url(SHA-256(verifier)); the verifier never leaves the app until verify
ALTER TABLE admin_login_tokens ADD COLUMN code_hash TEXT;                  -- SHA-256(token_hash ":" code)
ALTER TABLE admin_login_tokens ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS admin_login_tokens_challenge ON admin_login_tokens(challenge);
