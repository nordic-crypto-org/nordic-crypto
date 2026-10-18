// node --test tests/schedule.test.mjs — campaigns/schedule overview on /admin/: admin-only read, token-only write, cron next run.
import test from "node:test"; import assert from "node:assert/strict";
import { readFileSync } from "node:fs"; import { DatabaseSync } from "node:sqlite";
import worker from "../src/worker.js";
import { nextRun, osloIso, parseCron, listSchedule } from "../src/schedule.js";
import { TEST_OUTBOX } from "../src/mailer.js";

class SqliteD1 {
  constructor(db) { this.db = db; }
  prepare(sql) { const db = this.db; const b = (...p) => ({
      run: async () => { const i = db.prepare(sql).run(...p); return { meta: { last_row_id: Number(i.lastInsertRowid), changes: i.changes } }; },
      first: async () => db.prepare(sql).get(...p) ?? null, all: async () => ({ results: db.prepare(sql).all(...p) }) });
    return { bind: (...p) => b(...p), ...b() }; }
  async batch(s) { const o = []; for (const x of s) o.push(await x.run()); return o; }
}
const O = "https://nordiccrypto.no", SECRET = "s".repeat(40);
function env() {
  const db = new DatabaseSync(":memory:");
  for (const m of ["0001_tips.sql", "0003_subscribers.sql", "0007_admin.sql", "0009_admin_app_code.sql", "0010_admin_schedule.sql"]) db.exec(readFileSync(new URL("../migrations/" + m, import.meta.url), "utf8"));
  return { DB: new SqliteD1(db), raw: db, SUBSCRIBE_TEST: "1", ADMIN_DELIVERY_TOKEN: SECRET };
}
let ipn = 1;
const call = (e, method, path, { body, token } = {}) => worker.fetch(new Request("https://w.test" + path, { method,
  headers: { "Content-Type": "application/json", "CF-Connecting-IP": "198.51.100." + (ipn++ % 250), Origin: O, ...(token ? { Authorization: "Bearer " + token } : {}) },
  body: body ? JSON.stringify(body) : undefined }), e);
async function signIn(e) {
  await call(e, "POST", "/api/admin/login", { body: { email: "jqrgen@nordiccrypto.no" } });
  const t = TEST_OUTBOX.at(-1).text.match(/#t=([A-Za-z0-9_-]+)/)[1];
  return (await (await call(e, "POST", "/api/admin/verify", { body: { token: t } })).json()).token;
}
const DATA = { campaigns: [{ id: "c1", name: "Campaign", channels: "Telegram,X", status: "active", starts_at: "2026-10-18T20:00", ends_at: "2026-10-31T23:59" }],
  schedule: [{ id: "daily", channel: "Site", what: "Daily", cron: "15 8 * * *", status: "active", source: "routine" },
    { id: "gha", channel: "X", what: "Weekly", cron: "45 6 * * 1", tz: "UTC", status: "paused", source: "workflow:x-newsletter.yml" },
    { id: "once", channel: "Web", what: "One-off", at: "2026-10-20T13:00", status: "awaiting_approval", source: "campaign", campaign_id: "c1" }] };

test("cron next run in Oslo time, across the DST change", () => {
  assert.equal(parseCron("61 * * * *"), null); assert.equal(parseCron("* * *"), null);
  assert.deepEqual(parseCron("5 9 * * 1-5")[4], [1, 2, 3, 4, 5]);
  const now = Date.parse("2026-10-18T18:00:00Z");   // Sun 20:00 Oslo (CEST)
  assert.equal(osloIso(nextRun("15 8 * * *", "Europe/Oslo", now)), "2026-10-19T08:15+02:00");
  assert.equal(osloIso(nextRun("20 10 * * 2,5", "Europe/Oslo", now)), "2026-10-20T10:20+02:00");
  assert.equal(osloIso(nextRun("0 5 * * 1", "Europe/Oslo", Date.parse("2026-10-19T03:00:00Z"))), "2026-10-26T05:00+01:00");
  assert.equal(osloIso(nextRun("45 6 * * 1", "UTC", now)), "2026-10-19T08:45+02:00");
  assert.equal(osloIso(nextRun("5 9 * * 1-5", "Europe/Oslo", Date.parse("2026-10-23T08:00:00Z"))), "2026-10-26T09:05+01:00");
});

test("schedule: read needs an admin session, write needs ADMIN_DELIVERY_TOKEN", async () => {
  const e = env();
  assert.equal((await call(e, "GET", "/api/admin/schedule")).status, 401);
  assert.equal((await call(e, "POST", "/api/admin/schedule", { body: DATA })).status, 401);
  const tok = await signIn(e);
  assert.equal((await call(e, "POST", "/api/admin/schedule", { body: DATA, token: tok })).status, 401, "a session cannot write");
  assert.equal((await call(e, "POST", "/api/admin/schedule", { body: { ...DATA, schedule: [{ ...DATA.schedule[0], cron: "bad" }] }, token: SECRET })).status, 400);
  const w = await call(e, "POST", "/api/admin/schedule", { body: DATA, token: SECRET }); assert.equal(w.status, 200);
  assert.deepEqual(await w.json(), { ok: true, campaigns: 1, schedule: 3 });
  const r = await call(e, "GET", "/api/admin/schedule", { token: tok }); assert.equal(r.status, 200);
  assert.equal(r.headers.get("Cache-Control"), "no-store");
  const d = await r.json(); assert.equal(d.campaigns[0].name, "Campaign"); assert.equal(d.schedule.length, 3);
  await call(e, "POST", "/api/admin/schedule", { body: { campaigns: [], schedule: [DATA.schedule[0]] }, token: SECRET });
  assert.equal((await (await call(e, "GET", "/api/admin/schedule", { token: tok })).json()).schedule.length, 1, "replaces");
});

test("listSchedule: sorted by next run, past one-offs have none", async () => {
  const e = env(); await call(e, "POST", "/api/admin/schedule", { body: DATA, token: SECRET });
  const d = await listSchedule(e, Date.parse("2026-10-19T12:00:00Z"));
  assert.deepEqual(d.schedule.map((r) => [r.id, r.next_run]), [["daily", "2026-10-20T08:15+02:00"], ["once", "2026-10-20T13:00+02:00"], ["gha", "2026-10-26T07:45+01:00"]]);
  assert.equal((await listSchedule(e, Date.parse("2026-10-21T00:00:00Z"))).schedule.find((r) => r.id === "once").next_run, null);
});
