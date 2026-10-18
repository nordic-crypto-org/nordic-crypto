// Private admin API for /admin/ on the site. Used by worker.js.
//   POST /api/admin/login       {email}  -> always 202 {"ok":true} (same answer for every address, no enumeration). Only
//                               an address whose domain is exactly ADMIN_EMAIL_DOMAIN (default nordiccrypto.no) gets a
//                               one-time link, valid 15 minutes, single use. Rate-limited per IP (scope "admin") and per address.
//   POST /api/admin/verify      {token}  -> 200 {"ok":true, token, email, expires} – a bearer session token (7 days).
//                               POST, not GET: the link points at the site (…/admin/#t=…) and the page posts the token, so
//                               mail scanners that prefetch links never burn it, and the token is never in a server log.
//   App (iOS) sign-in, no link and no cookie: POST /api/admin/login {email, challenge} where challenge = base64url(SHA-256(
//                               verifier)) and the verifier stays in the app. The email then holds an 8-digit code instead of
//                               a link. POST /api/admin/verify {code, verifier} -> the same bearer session. A code works once,
//                               for 15 minutes, only with the verifier of the app that asked, and dies after CODE_TRIES misses.
//   POST /api/admin/logout      (bearer) -> deletes the session.
//   GET  /api/admin/me          (bearer) -> {"ok":true, email}
//   GET  /api/admin/subscribers (bearer) -> every subscriber with the issues each has received.
//   POST /api/admin/deliveries  (bearer ADMIN_DELIVERY_TOKEN, a secret) {deliveries:[{subscriber_id, issue}]} – used by
//                               newsletter/send_issue.py when it is not writing to D1 directly.
//   GET  /api/admin/press-sends (bearer) -> press release sends with their recipients (migrations/0008_press_history.sql).
//   POST /api/admin/press-sends (bearer ADMIN_DELIVERY_TOKEN) {send:{id, release_id, at, from, dry_run, recipients:[{email,status,error}]}}
//                               – used by tools/press_history.py; idempotent by send id.
// Why bearer and not a cookie: the page is on nordiccrypto.no and the Worker on workers.dev, a different site; browsers
// (Safari, Firefox strict, Chrome's third-party-cookie limits) drop cross-site cookies. CORS here allows only ADMIN_ORIGIN.
import { sendMail } from "./mailer.js";

export const LOGIN_TTL = 15 * 60, SESSION_TTL = 7 * 86400, PER_EMAIL_N = 3, ADMIN_RATE_N = 5, CODE_TRIES = 5;
export const ADMIN_ORIGIN = "https://nordiccrypto.no";
const enc = new TextEncoder();
const hex = (b) => [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
export const sha256 = async (s) => hex(await crypto.subtle.digest("SHA-256", enc.encode(s)));
const b64url = (u8) => btoa(String.fromCharCode(...u8)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
export const newToken = () => b64url(crypto.getRandomValues(new Uint8Array(32)));
export const challengeOf = async (v) => b64url(new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(v))));
const CHALLENGE_RE = /^[A-Za-z0-9_-]{43}$/, VERIFIER_RE = /^[A-Za-z0-9_-]{43,128}$/;
export function newCode() {   // 8 digits, uniform (rejection sampling)
  const lim = 4294967296 - (4294967296 % 1e8), u = new Uint32Array(1);
  do crypto.getRandomValues(u); while (u[0] >= lim);
  return String(u[0] % 1e8).padStart(8, "0");
}
const now = () => Math.floor(Date.now() / 1000);
const nowIso = () => new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00");
const LOCAL_RE = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}$/;

export const adminDomain = (env) => String((env && env.ADMIN_EMAIL_DOMAIN) || "nordiccrypto.no").trim().toLowerCase();

// Returns the lower-cased address when it is allowed, else null. Exactly one "@", a plain local part, and a domain that
// equals the admin domain exactly: no subdomains (x@a.nordiccrypto.no), no lookalikes (x@evil-nordiccrypto.no,
// x@nordiccrypto.no.evil.com), no trailing dot, no display names or whitespace.
export function allowedAdmin(email, env) {
  if (typeof email !== "string") return null;
  const e = email.trim().toLowerCase();
  if (e.length > 254 || /\s/.test(e)) return null;
  const parts = e.split("@");
  if (parts.length !== 2) return null;
  const [local, domain] = parts;
  if (!LOCAL_RE.test(local) || local.startsWith(".") || local.endsWith(".") || local.includes("..")) return null;
  const want = adminDomain(env);
  if (!want || domain !== want) return null;
  return e;
}

function cors(req, extra = {}) {
  const h = new Headers({ "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", ...extra });
  if (req.headers.get("Origin") === ADMIN_ORIGIN) { h.set("Access-Control-Allow-Origin", ADMIN_ORIGIN); h.set("Vary", "Origin"); }
  return h;
}
const json = (req, code, obj) => new Response(JSON.stringify(obj), { status: code, headers: cors(req, { "Content-Type": "application/json; charset=utf-8" }) });

export function adminPreflight(req) {
  if (req.headers.get("Origin") !== ADMIN_ORIGIN) return json(req, 403, { ok: false });
  return new Response(null, { status: 204, headers: cors(req, { "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization", "Access-Control-Max-Age": "600" }) });
}

async function body(req, h) {
  const raw = await h.readCapped(req, 1024);
  if (raw === null) return null;
  try { const f = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(raw)); return f && typeof f === "object" && !Array.isArray(f) ? f : null; }
  catch { return null; }
}
const bearer = (req) => { const m = (req.headers.get("Authorization") || "").match(/^Bearer ([A-Za-z0-9_-]{20,200})$/); return m ? m[1] : null; };
const sameStr = (a, b) => { if (a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0; };

export async function session(req, env) {
  const t = bearer(req); if (!t) return null;
  const row = await env.DB.prepare("SELECT email, expires_at FROM admin_sessions WHERE token_hash = ?").bind(await sha256(t)).first();
  if (!row || row.expires_at <= now()) return null;
  return allowedAdmin(row.email, env) ? row : null;   // domain changed since login -> session no longer valid
}

export function loginEmail(link) {
  return { subject: "Nordic Crypto admin sign-in link",
    text: `Sign in to the Nordic Crypto admin page:\n\n${link}\n\nThe link works once and expires in 15 minutes. If you did not ask for it, ignore this email.\n` };
}

export function codeEmail(code) {
  return { subject: "Nordic Crypto admin sign-in code",
    text: `Your sign-in code for the admin screen in the Nordic Crypto app:\n\n${code.slice(0, 4)} ${code.slice(4)}\n\nIt works once, only in the app that asked for it, and expires in 15 minutes. If you did not ask for it, ignore this email.\n` };
}

async function login(req, env, h) {
  const origin = req.headers.get("Origin");
  if (origin !== null && origin !== ADMIN_ORIGIN) return json(req, 403, { ok: false });
  const f = await body(req, h);
  if (!f) return json(req, 400, { ok: false, error: "invalid" });
  const app = f.challenge !== undefined;
  if (app && (typeof f.challenge !== "string" || !CHALLENGE_RE.test(f.challenge))) return json(req, 400, { ok: false, error: "invalid" });
  const generic = () => json(req, 202, { ok: true, message: `If that address may sign in, a ${app ? "code" : "link"} is on its way.` });
  const ip = (req.headers.get("CF-Connecting-IP") || "unknown").trim().slice(0, 64);
  try { if (!(await h.rateOk(env.DB, ip, "admin", ADMIN_RATE_N))) return json(req, 429, { ok: false, error: "rate" }); }
  catch { return json(req, 503, { ok: false }); }
  const email = allowedAdmin(f.email, env);
  if (!email) return generic();
  const t = now();
  await env.DB.prepare("DELETE FROM admin_login_tokens WHERE expires_at < ?").bind(t - 86400).run();
  const c = await env.DB.prepare("SELECT COUNT(*) AS n FROM admin_login_tokens WHERE email = ? AND created_at > ?").bind(email, t - LOGIN_TTL).first();
  if (c.n >= PER_EMAIL_N) return generic();   // per-address cap, silent (no enumeration)
  const token = newToken();
  if (app) {   // the row's token is never sent; only the code (bound to the challenge) can redeem it
    const code = newCode(), th = await sha256(token);
    await env.DB.prepare("INSERT INTO admin_login_tokens (token_hash, email, created_at, expires_at, challenge, code_hash) VALUES (?, ?, ?, ?, ?, ?)")
      .bind(th, email, t, t + LOGIN_TTL, f.challenge, await sha256(th + ":" + code)).run();
    await sendMail(env, { to: email, site: "nordic-crypto", lang: "en", kind: "admin-login-code", ...codeEmail(code) });
    return generic();
  }
  await env.DB.prepare("INSERT INTO admin_login_tokens (token_hash, email, created_at, expires_at) VALUES (?, ?, ?, ?)")
    .bind(await sha256(token), email, t, t + LOGIN_TTL).run();
  const link = `${ADMIN_ORIGIN}/admin/#t=${token}`;
  await sendMail(env, { to: email, site: "nordic-crypto", lang: "en", kind: "admin-login", ...loginEmail(link) });
  return generic();
}

async function verify(req, env, h) {
  if (req.headers.get("Origin") !== null && req.headers.get("Origin") !== ADMIN_ORIGIN) return json(req, 403, { ok: false });
  const f = await body(req, h);
  if (f && f.code !== undefined) return verifyCode(req, env, f);
  const tok = f && typeof f.token === "string" && /^[A-Za-z0-9_-]{20,200}$/.test(f.token) ? f.token : null;
  const bad = () => json(req, 401, { ok: false, error: "The link is invalid, used or expired. Ask for a new one." });
  if (!tok) return bad();
  const t = now(), th = await sha256(tok);
  // Single use: the UPDATE only succeeds once, even for two concurrent requests.
  const u = await env.DB.prepare("UPDATE admin_login_tokens SET used_at = ? WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?").bind(t, th, t).run();
  if (!u.meta || u.meta.changes !== 1) return bad();
  const row = await env.DB.prepare("SELECT email FROM admin_login_tokens WHERE token_hash = ?").bind(th).first();
  const email = row && allowedAdmin(row.email, env);
  if (!email) return bad();
  return newSession(req, env, email, t);
}

async function verifyCode(req, env, f) {
  const bad = () => json(req, 401, { ok: false, error: "The code is invalid, used or expired. Ask for a new one." });
  const code = typeof f.code === "string" ? f.code.replace(/[\s-]/g, "") : "";
  if (!/^\d{8}$/.test(code) || typeof f.verifier !== "string" || !VERIFIER_RE.test(f.verifier)) return bad();
  const t = now();
  const row = await env.DB.prepare("SELECT token_hash, email, code_hash, attempts FROM admin_login_tokens WHERE challenge = ? AND used_at IS NULL AND expires_at > ? ORDER BY created_at DESC")
    .bind(await challengeOf(f.verifier), t).first();
  if (!row || !row.code_hash || row.attempts >= CODE_TRIES) return bad();
  if (!sameStr(await sha256(row.token_hash + ":" + code), row.code_hash)) {
    await env.DB.prepare("UPDATE admin_login_tokens SET attempts = attempts + 1, used_at = CASE WHEN attempts + 1 >= ? THEN ? ELSE used_at END WHERE token_hash = ?")
      .bind(CODE_TRIES, t, row.token_hash).run();
    return bad();
  }
  const u = await env.DB.prepare("UPDATE admin_login_tokens SET used_at = ? WHERE token_hash = ? AND used_at IS NULL").bind(t, row.token_hash).run();
  if (!u.meta || u.meta.changes !== 1) return bad();
  const email = allowedAdmin(row.email, env);
  if (!email) return bad();
  return newSession(req, env, email, t);
}

async function newSession(req, env, email, t) {
  const st = newToken();
  await env.DB.batch([
    env.DB.prepare("DELETE FROM admin_sessions WHERE expires_at <= ?").bind(t),
    env.DB.prepare("INSERT INTO admin_sessions (token_hash, email, created_at, expires_at) VALUES (?, ?, ?, ?)").bind(await sha256(st), email, t, t + SESSION_TTL),
    env.DB.prepare("INSERT INTO admin_logins (email, at) VALUES (?, ?)").bind(email, nowIso()),
  ]);
  return json(req, 200, { ok: true, token: st, email, expires: t + SESSION_TTL });
}

async function logout(req, env) {
  const t = bearer(req);
  if (t) await env.DB.prepare("DELETE FROM admin_sessions WHERE token_hash = ?").bind(await sha256(t)).run();
  return json(req, 200, { ok: true });
}

export async function listSubscribers(env) {
  const subs = (await env.DB.prepare("SELECT id, email, site, lang, status, created_at, confirmed_at, unsubscribed_at FROM subscribers ORDER BY id").all()).results || [];
  const dels = (await env.DB.prepare("SELECT subscriber_id, issue, sent_at FROM newsletter_deliveries ORDER BY issue").all()).results || [];
  const by = new Map();
  for (const d of dels) { if (!by.has(d.subscriber_id)) by.set(d.subscriber_id, []); by.get(d.subscriber_id).push(d.issue); }
  const rows = subs.map((s) => { const issues = by.get(s.id) || []; return { ...s, issues, last_issue: issues.length ? Math.max(...issues) : null }; });
  const totals = { all: rows.length, pending: 0, confirmed: 0, unsubscribed: 0, deliveries: dels.length };
  for (const r of rows) if (r.status in totals) totals[r.status]++;
  const last = dels.length ? Math.max(...dels.map((d) => d.issue)) : null;
  return { rows, totals, last_issue: last };
}

async function recordDeliveries(req, env, h) {
  const t = bearer(req), secret = env.ADMIN_DELIVERY_TOKEN || "";
  if (!t || secret.length < 32 || !sameStr(t, secret)) return json(req, 401, { ok: false });
  const raw = await h.readCapped(req, 65536);
  let f; try { f = JSON.parse(new TextDecoder().decode(raw)); } catch { return json(req, 400, { ok: false }); }
  const list = f && Array.isArray(f.deliveries) ? f.deliveries : null;
  if (!list || list.length > 500 || !list.every((d) => Number.isInteger(d.subscriber_id) && Number.isInteger(d.issue) && d.issue > 0 && d.issue < 100000))
    return json(req, 400, { ok: false });
  const at = nowIso();
  if (list.length) await env.DB.batch(list.map((d) => env.DB.prepare("INSERT OR IGNORE INTO newsletter_deliveries (subscriber_id, issue, sent_at) VALUES (?, ?, ?)").bind(d.subscriber_id, d.issue, at)));
  return json(req, 200, { ok: true, recorded: list.length });
}

const PRESS_ID = /^[A-Za-z0-9_-]{1,120}$/, PRESS_ST = new Set(["sent", "failed", "dry_run"]);
const isEmail = (e) => typeof e === "string" && e.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);

async function recordPressSend(req, env, h) {
  const t = bearer(req), secret = env.ADMIN_DELIVERY_TOKEN || "";
  if (!t || secret.length < 32 || !sameStr(t, secret)) return json(req, 401, { ok: false });
  const raw = await h.readCapped(req, 262144);
  let f; try { f = JSON.parse(new TextDecoder().decode(raw)); } catch { return json(req, 400, { ok: false }); }
  const s = f && f.send, rs = s && Array.isArray(s.recipients) ? s.recipients : null;
  if (!s || !PRESS_ID.test(s.id || "") || !PRESS_ID.test(s.release_id || "") || typeof s.at !== "string" || s.at.length > 40
      || typeof s.from !== "string" || s.from.length > 200 || !/@/.test(s.from) || !rs || rs.length > 1000
      || !rs.every((r) => r && isEmail(r.email) && PRESS_ST.has(r.status) && (r.error == null || (typeof r.error === "string" && r.error.length <= 80))))
    return json(req, 400, { ok: false });
  const n = (st) => rs.filter((r) => r.status === st).length;
  await env.DB.batch([
    env.DB.prepare("INSERT OR IGNORE INTO press_sends (id, release_id, at, from_addr, dry_run, sent, failed) VALUES (?, ?, ?, ?, ?, ?, ?)")
      .bind(s.id, s.release_id, s.at, s.from, s.dry_run ? 1 : 0, n("sent"), n("failed")),
    ...rs.map((r) => env.DB.prepare("INSERT OR IGNORE INTO press_send_recipients (send_id, email, status, error) VALUES (?, ?, ?, ?)")
      .bind(s.id, r.email.toLowerCase(), r.status, r.error || "")),
  ]);
  return json(req, 200, { ok: true, recorded: rs.length });
}

export async function listPressSends(env) {
  const sends = (await env.DB.prepare("SELECT id, release_id, at, from_addr, dry_run, sent, failed FROM press_sends ORDER BY at DESC").all()).results || [];
  const rec = (await env.DB.prepare("SELECT send_id, email, status, error FROM press_send_recipients ORDER BY email").all()).results || [];
  const by = new Map(sends.map((s) => [s.id, []]));
  for (const r of rec) if (by.has(r.send_id)) by.get(r.send_id).push({ email: r.email, status: r.status, error: r.error });
  return { sends: sends.map((s) => ({ ...s, dry_run: !!s.dry_run, recipients: by.get(s.id) })) };
}

export async function admin(req, env, h, path) {
  try {
    if (req.method === "OPTIONS") return adminPreflight(req);
    if (req.method === "POST" && path === "/api/admin/login") return await login(req, env, h);
    if (req.method === "POST" && path === "/api/admin/verify") return await verify(req, env, h);
    if (req.method === "POST" && path === "/api/admin/logout") return await logout(req, env);
    if (req.method === "POST" && path === "/api/admin/deliveries") return await recordDeliveries(req, env, h);
    if (req.method === "POST" && path === "/api/admin/press-sends") return await recordPressSend(req, env, h);
    if (req.method === "GET" && (path === "/api/admin/me" || path === "/api/admin/subscribers" || path === "/api/admin/press-sends")) {
      const s = await session(req, env);
      if (!s) return json(req, 401, { ok: false, error: "auth" });
      if (path === "/api/admin/me") return json(req, 200, { ok: true, email: s.email });
      if (path === "/api/admin/press-sends") return json(req, 200, { ok: true, ...(await listPressSends(env)) });
      return json(req, 200, { ok: true, email: s.email, ...(await listSubscribers(env)) });
    }
    return json(req, 404, { ok: false });
  } catch { return json(req, 503, { ok: false }); }
}
