// Campaigns and scheduled posts for /admin/ (migrations/0010_admin_schedule.sql). Routed from admin.js:
//   GET  /api/admin/schedule (admin session)          -> {campaigns, schedule} with next_run in Oslo time
//   POST /api/admin/schedule (ADMIN_DELIVERY_TOKEN)   {campaigns, schedule} replaces both tables (tools/admin_schedule.py)
export const OSLO = "Europe/Oslo";
export const STATUSES = new Set(["active", "paused", "awaiting_approval", "awaiting_setup", "done"]);
const RANGES = [[0, 59], [0, 23], [1, 31], [1, 12], [0, 7]];

// 5-field cron -> [minutes, hours, days, months, weekdays] as sorted number arrays (+ flags for day-of-month/week "*"), or null.
export function parseCron(s) {
  const f = typeof s === "string" ? s.trim().split(/\s+/) : [];
  if (f.length !== 5) return null;
  const out = [];
  for (let i = 0; i < 5; i++) {
    const [lo, hi] = RANGES[i], set = new Set();
    for (const part of f[i].split(",")) {
      const m = part.match(/^(\*|(\d+)(?:-(\d+))?)(?:\/(\d+))?$/);
      if (!m) return null;
      let a = m[1] === "*" ? lo : +m[2], b = m[1] === "*" ? hi : m[3] !== undefined ? +m[3] : m[4] ? hi : a;
      const step = m[4] ? +m[4] : 1;
      if (a < lo || b > hi || a > b || step < 1) return null;
      for (let v = a; v <= b; v += step) set.add(i === 4 && v === 7 ? 0 : v);
    }
    out.push([...set].sort((x, y) => x - y));
  }
  out.domAny = f[2] === "*"; out.dowAny = f[4] === "*";
  return out;
}

const fmts = new Map();
function parts(ms, tz) {
  if (!fmts.has(tz)) fmts.set(tz, new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric" }));
  const p = {}; for (const x of fmts.get(tz).formatToParts(new Date(ms))) p[x.type] = +x.value;
  return p;
}
const offset = (ms, tz) => { const p = parts(ms, tz); return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute) - Math.floor(ms / 60000) * 60000; };
function toUtc(y, mo, d, h, mi, tz) {
  const g = Date.UTC(y, mo - 1, d, h, mi); let t = g - offset(g, tz); const o2 = offset(t, tz);
  if (g - o2 !== t) t = g - o2;
  return t;
}

// Next run strictly after nowMs, as epoch ms, or null (no match within ~400 days).
export function nextRun(cron, tz, nowMs) {
  const c = parseCron(cron); if (!c) return null;
  const [mins, hours, days, months, dows] = c, p = parts(nowMs, tz);
  for (let i = 0; i < 400; i++) {
    const day = new Date(Date.UTC(p.year, p.month - 1, p.day + i));
    const y = day.getUTCFullYear(), mo = day.getUTCMonth() + 1, d = day.getUTCDate(), wd = day.getUTCDay();
    if (!months.includes(mo)) continue;
    const domOk = days.includes(d), dowOk = dows.includes(wd);
    if (!(c.domAny || c.dowAny ? domOk && dowOk : domOk || dowOk)) continue;
    for (const h of hours) for (const mi of mins) { const t = toUtc(y, mo, d, h, mi, tz); if (t > nowMs) return t; }
  }
  return null;
}

export function osloIso(ms) {
  const p = parts(ms, OSLO), off = offset(ms, OSLO) / 60000, pad = (n) => String(n).padStart(2, "0");
  return `${p.year}-${pad(p.month)}-${pad(p.day)}T${pad(p.hour)}:${pad(p.minute)}${off < 0 ? "-" : "+"}${pad(Math.abs(off) / 60 | 0)}:${pad(Math.abs(off) % 60)}`;
}
const osloMs = (s) => { const m = /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)/.exec(s || ""); return m ? toUtc(+m[1], +m[2], +m[3], +m[4], +m[5], OSLO) : null; };

export async function listSchedule(env, nowMs = Date.now()) {
  const campaigns = (await env.DB.prepare("SELECT id, name, channels, what, starts_at, ends_at, status FROM admin_campaigns ORDER BY starts_at, id").all()).results || [];
  const rows = (await env.DB.prepare("SELECT id, channel, what, cron, tz, at, status, source, campaign_id FROM admin_schedule").all()).results || [];
  const schedule = rows.map((r) => {
    const t = r.cron ? nextRun(r.cron, r.tz, nowMs) : osloMs(r.at);
    return { ...r, next_run: t != null && t > nowMs && r.status !== "done" ? osloIso(t) : null };
  }).sort((a, b) => (a.next_run === null) - (b.next_run === null) || (osloMs(a.next_run) || 0) - (osloMs(b.next_run) || 0) || a.id.localeCompare(b.id));
  return { campaigns, schedule, now: osloIso(nowMs) };
}

const ID = /^[A-Za-z0-9_.:-]{1,80}$/, ISO = /^\d{4}-\d\d-\d\dT\d\d:\d\d/;
const str = (v, n, opt) => (opt && (v === undefined || v === null)) || (typeof v === "string" && v.length <= n);
const tzOk = (tz) => { try { new Intl.DateTimeFormat("en-US", { timeZone: tz }); return true; } catch { return false; } };
const okCampaign = (c) => c && ID.test(c.id || "") && str(c.name, 200) && str(c.channels, 200, 1) && str(c.what, 500, 1)
  && (c.starts_at == null || ISO.test(c.starts_at)) && (c.ends_at == null || ISO.test(c.ends_at)) && STATUSES.has(c.status);
const okRow = (r) => r && ID.test(r.id || "") && str(r.channel, 80) && str(r.what, 300) && STATUSES.has(r.status)
  && (r.cron ? parseCron(r.cron) !== null : ISO.test(r.at || "")) && (r.tz == null || (typeof r.tz === "string" && tzOk(r.tz)))
  && str(r.source, 120, 1) && (r.campaign_id == null || ID.test(r.campaign_id));

export async function recordSchedule(env, f) {
  const cs = f && f.campaigns, rs = f && f.schedule;
  if (!Array.isArray(cs) || !Array.isArray(rs) || cs.length > 200 || rs.length > 500 || !cs.every(okCampaign) || !rs.every(okRow)) return null;
  const at = new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00");
  await env.DB.batch([
    env.DB.prepare("DELETE FROM admin_campaigns"), env.DB.prepare("DELETE FROM admin_schedule"),
    ...cs.map((c) => env.DB.prepare("INSERT INTO admin_campaigns (id, name, channels, what, starts_at, ends_at, status, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
      .bind(c.id, c.name, c.channels || "", c.what || "", c.starts_at || null, c.ends_at || null, c.status, at)),
    ...rs.map((r) => env.DB.prepare("INSERT INTO admin_schedule (id, channel, what, cron, tz, at, status, source, campaign_id, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
      .bind(r.id, r.channel, r.what, r.cron || null, r.tz || OSLO, r.cron ? null : r.at, r.status, r.source || "", r.campaign_id || null, at)),
  ]);
  return { campaigns: cs.length, schedule: rs.length };
}
