// node --test tests/flags.test.mjs — app feature flags: public read defaults off, admin session toggles.
import test from "node:test"; import assert from "node:assert/strict";
import { readFileSync } from "node:fs"; import { DatabaseSync } from "node:sqlite";
import worker from "../src/worker.js";
import { TEST_OUTBOX } from "../src/mailer.js";

class SqliteD1 {
  constructor(db) { this.db = db; }
  prepare(sql) { const db = this.db; const b = (...p) => ({
      run: async () => { const i = db.prepare(sql).run(...p); return { meta: { last_row_id: Number(i.lastInsertRowid), changes: i.changes } }; },
      first: async () => db.prepare(sql).get(...p) ?? null, all: async () => ({ results: db.prepare(sql).all(...p) }) });
    return { bind: (...p) => b(...p), ...b() }; }
  async batch(s) { const o = []; for (const x of s) o.push(await x.run()); return o; }
}
function env(withFlags = true) {
  const db = new DatabaseSync(":memory:");
  const ms = ["0001_tips.sql", "0003_subscribers.sql", "0007_admin.sql", "0009_admin_app_code.sql", "0012_admin_login_requester.sql"].concat(withFlags ? ["0011_app_flags.sql"] : []);
  for (const m of ms) db.exec(readFileSync(new URL("../migrations/" + m, import.meta.url), "utf8"));
  return { DB: new SqliteD1(db), SUBSCRIBE_TEST: "1" };
}
let ipn = 1;
const call = (e, method, path, { body, token } = {}) => worker.fetch(new Request("https://w.test" + path, { method,
  headers: { "Content-Type": "application/json", "CF-Connecting-IP": "198.51.100." + (ipn++ % 250), Origin: "https://nordiccrypto.no", ...(token ? { Authorization: "Bearer " + token } : {}) },
  body: body ? JSON.stringify(body) : undefined }), e);
async function signIn(e) {
  await call(e, "POST", "/api/admin/login", { body: { email: "jqrgen@nordiccrypto.no" } });
  const t = TEST_OUTBOX.at(-1).text.match(/#t=([A-Za-z0-9_-]+)/)[1];
  return (await (await call(e, "POST", "/api/admin/verify", { body: { token: t } })).json()).token;
}

test("public flags default off, also without the table", async () => {
  for (const e of [env(), env(false)]) assert.deepEqual(await (await call(e, "GET", "/api/flags")).json(), { nft: { ios: false } });
});

test("admin session toggles nft_ios", async () => {
  const e = env();
  assert.equal((await call(e, "POST", "/api/admin/flags", { body: { nft_ios: true } })).status, 401);
  const tok = await signIn(e);
  assert.deepEqual((await (await call(e, "GET", "/api/admin/flags", { token: tok })).json()).flags, { nft_ios: false });
  assert.equal((await call(e, "POST", "/api/admin/flags", { body: { nft_ios: "yes" }, token: tok })).status, 400);
  assert.equal((await call(e, "POST", "/api/admin/flags", { body: { other: true }, token: tok })).status, 400);
  assert.equal((await call(e, "POST", "/api/admin/flags", { body: { nft_ios: true }, token: tok })).status, 200);
  assert.deepEqual(await (await call(e, "GET", "/api/flags")).json(), { nft: { ios: true } });
  await call(e, "POST", "/api/admin/flags", { body: { nft_ios: false }, token: tok });
  assert.deepEqual(await (await call(e, "GET", "/api/flags")).json(), { nft: { ios: false } });
});
