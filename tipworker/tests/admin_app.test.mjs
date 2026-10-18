// node --test tests/admin_app.test.mjs — app (iOS) admin sign-in: emailed 8-digit code bound to a PKCE-style challenge.
// node:sqlite as D1, mail goes to the in-memory test outbox (SUBSCRIBE_TEST=1). No network, nothing deployed, no email sent.
import test from "node:test"; import assert from "node:assert/strict";
import { readFileSync } from "node:fs"; import { DatabaseSync } from "node:sqlite";
import worker from "../src/worker.js";
import { challengeOf, newCode, CODE_TRIES } from "../src/admin.js";
import { TEST_OUTBOX } from "../src/mailer.js";

class SqliteD1 {
  constructor(db) { this.db = db; }
  prepare(sql) { const db = this.db; const b = (...p) => ({
      run: async () => { const i = db.prepare(sql).run(...p); return { meta: { last_row_id: Number(i.lastInsertRowid), changes: i.changes } }; },
      first: async () => db.prepare(sql).get(...p) ?? null, all: async () => ({ results: db.prepare(sql).all(...p) }) });
    return { bind: (...p) => b(...p), ...b() }; }
  async batch(s) { const o = []; for (const x of s) o.push(await x.run()); return o; }
}
function env() {
  const db = new DatabaseSync(":memory:");
  for (const m of ["0001_tips.sql", "0003_subscribers.sql", "0007_admin.sql", "0009_admin_app_code.sql"]) db.exec(readFileSync(new URL("../migrations/" + m, import.meta.url), "utf8"));
  return { DB: new SqliteD1(db), raw: db, SUBSCRIBE_TEST: "1" };
}
let ipn = 1;
// The app sends no Origin header.
const call = (e, method, path, { body, token, origin } = {}) => worker.fetch(new Request("https://w.test" + path, { method,
  headers: { "Content-Type": "application/json", "CF-Connecting-IP": "203.0.113." + (ipn++ % 250), ...(origin ? { Origin: origin } : {}), ...(token ? { Authorization: "Bearer " + token } : {}) },
  body: body ? JSON.stringify(body) : undefined }), e);
const verifier = () => Buffer.from(crypto.getRandomValues(new Uint8Array(32))).toString("base64url");
const lastCode = () => TEST_OUTBOX.at(-1).text.match(/\n(\d{4}) (\d{4})\n/).slice(1).join("");
async function start(e, email = "jqrgen@nordiccrypto.no") {
  const v = verifier(); const r = await call(e, "POST", "/api/admin/login", { body: { email, challenge: await challengeOf(v) } });
  return { v, r };
}

test("newCode: 8 digits", () => { for (let i = 0; i < 2000; i++) assert.match(newCode(), /^\d{8}$/); });

test("app login: same answer for every address, a code (no link) only for the domain, bad challenge refused", async () => {
  const e = env(); const n0 = TEST_OUTBOX.length;
  const a = (await start(e, "x@evil-nordiccrypto.no")).r, b = (await start(e)).r;
  assert.equal(a.status, 202); assert.equal(b.status, 202); assert.deepEqual(await a.json(), await b.json());
  assert.equal(TEST_OUTBOX.length, n0 + 1); const m = TEST_OUTBOX.at(-1);
  assert.equal(m.to, "jqrgen@nordiccrypto.no"); assert.equal(m.kind, "admin-login-code");
  assert.ok(!/https?:|#t=/.test(m.text), "no link in the app email"); assert.match(lastCode(), /^\d{8}$/);
  assert.equal(e.raw.prepare("SELECT COUNT(*) n FROM admin_login_tokens WHERE code_hash LIKE ?").get("%" + lastCode() + "%").n, 0, "code stored hashed");
  for (const challenge of ["short", 5, "x".repeat(44), "a+b/" + "c".repeat(39)])
    assert.equal((await call(e, "POST", "/api/admin/login", { body: { email: "jqrgen@nordiccrypto.no", challenge } })).status, 400);
});

test("code + verifier gives a bearer session; single use; works without Origin; data needs the session", async () => {
  const e = env(); const { v } = await start(e); const code = lastCode();
  assert.equal((await call(e, "GET", "/api/admin/subscribers")).status, 401);
  assert.equal((await call(e, "POST", "/api/admin/verify", { body: { code, verifier: verifier() } })).status, 401, "other app's verifier");
  const r = await call(e, "POST", "/api/admin/verify", { body: { code: code.slice(0, 4) + " " + code.slice(4), verifier: v } });
  assert.equal(r.status, 200); assert.equal(r.headers.get("Access-Control-Allow-Origin"), null); assert.equal(r.headers.get("Cache-Control"), "no-store");
  const s = await r.json(); assert.equal(s.email, "jqrgen@nordiccrypto.no"); assert.match(s.token, /^[A-Za-z0-9_-]{43}$/);
  assert.equal((await call(e, "POST", "/api/admin/verify", { body: { code, verifier: v } })).status, 401, "single use");
  assert.equal((await (await call(e, "GET", "/api/admin/me", { token: s.token })).json()).email, "jqrgen@nordiccrypto.no");
  const l = await call(e, "GET", "/api/admin/subscribers", { token: s.token }); assert.equal(l.status, 200); assert.equal((await l.json()).totals.all, 0);
  assert.equal((await call(e, "POST", "/api/admin/logout", { token: s.token })).status, 200);
  assert.equal((await call(e, "GET", "/api/admin/me", { token: s.token })).status, 401);
});

test("wrong codes burn the request after CODE_TRIES; expired codes are refused; the code is not a link token", async () => {
  const e = env(); let { v } = await start(e); let code = lastCode();
  const wrong = String((Number(code) + 1) % 1e8).padStart(8, "0");
  for (let i = 0; i < CODE_TRIES; i++) assert.equal((await call(e, "POST", "/api/admin/verify", { body: { code: wrong, verifier: v } })).status, 401);
  assert.equal((await call(e, "POST", "/api/admin/verify", { body: { code, verifier: v } })).status, 401, "burned");
  ({ v } = await start(e, "b@nordiccrypto.no")); code = lastCode();
  assert.equal((await call(e, "POST", "/api/admin/verify", { body: { token: code + "x".repeat(20) } })).status, 401);
  e.raw.exec("UPDATE admin_login_tokens SET expires_at = 1");
  assert.equal((await call(e, "POST", "/api/admin/verify", { body: { code, verifier: v } })).status, 401, "expired");
  for (const body of [{ code, verifier: "short" }, { code: "1234567", verifier: v }, { code: 12345678, verifier: v }])
    assert.equal((await call(e, "POST", "/api/admin/verify", { body })).status, 401);
});

test("web link sign-in is unchanged with the new columns", async () => {
  const e = env();
  await call(e, "POST", "/api/admin/login", { body: { email: "w@nordiccrypto.no" }, origin: "https://nordiccrypto.no" });
  const tok = TEST_OUTBOX.at(-1).text.match(/#t=([A-Za-z0-9_-]+)/)[1];
  assert.equal((await call(e, "POST", "/api/admin/verify", { body: { token: tok }, origin: "https://nordiccrypto.no" })).status, 200);
});
