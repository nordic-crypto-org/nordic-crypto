import { eventsToIcs, redactText } from "./ics.js";

// Nordic Crypto story and event review, and a read-only copy of the public API.
//
// The static site on GitHub Pages stays the public site. This Worker is optional.
// GET  /api/v1/news.json, /api/v1/news/:id.json
//      each story includes image.url when a generated picture is stored
// GET  /story-images/:id.png   the picture itself, from the R2 binding STORY_IMAGES
// GET  /api/v1/events.json, /api/v1/events/:id.json, /api/v1/events.ics
// GET  /api/v1/academia.json, /api/v1/academia/:section.json, /api/v1/academia/:id.json
// GET  /api/v1/sources.json
// GET  /api/review/pending          Authorization: Bearer EDITOR_TOKEN
// POST /api/review                  the same token; approve, reject, upsert a source, or upsert academia rows
//
// Teasers, match rules, reject reasons and the private term list are not returned.
// Nothing is logged. EDITOR_TOKEN and GITHUB_DISPATCH_TOKEN are Worker secrets.

export const PUBLIC_STORY_KEYS = [
  "id", "url", "title", "title_en", "title_i18n", "source", "source_name", "country",
  "language", "published", "topics", "summary", "summary_i18n", "paywall", "links", "status",
];

export const PUBLIC_EVENT_KEYS = [
  "id", "title", "title_orig", "start", "end", "place", "city", "country", "online",
  "organiser", "url", "source", "source_url", "paid", "sponsored", "note", "note_i18n",
  "description", "status", "map_url",
];

const PUBLIC_CACHE = "public, max-age=60, s-maxage=60, stale-while-revalidate=300";

const STORY_SELECT = "SELECT id, payload, review_status, item_status, reviewed_by, reviewed_at, review_note, summary, url, title, country, published_at, created_at FROM stories WHERE id = ?";
const EVENT_SELECT = "SELECT id, payload, review_status, item_status, reviewed_by, reviewed_at, review_note, url, title, country, start_at, created_at FROM events WHERE id = ?";

export function timingSafeEqual(a, b) {
  const enc = new TextEncoder();
  const left = enc.encode(String(a || ""));
  const right = enc.encode(String(b || ""));
  const length = Math.max(left.length, right.length);
  let mismatch = left.length === right.length ? 0 : 1;
  for (let i = 0; i < length; i++) mismatch |= (left[i] || 0) ^ (right[i] || 0);
  return mismatch === 0;
}

export function editorAuthorized(request, token) {
  if (!token) return false;
  const header = request.headers.get("authorization") || "";
  const match = header.match(/^Bearer\s+(\S+)\s*$/i);
  if (!match) return false;
  return timingSafeEqual(match[1], token);
}

export function publicStory(payload) {
  if (!payload || payload.status !== "published") return null;
  if (!String(payload.summary || "").trim()) return null;
  const copy = { ...payload };
  if ((copy.summary_i18n_review || "approved") !== "approved") delete copy.summary_i18n;
  const out = { status: "published" };
  for (const key of PUBLIC_STORY_KEYS) {
    if (key === "status") continue;
    if (copy[key] !== undefined && copy[key] !== null) out[key] = copy[key];
  }
  return out;
}

export function publicEvent(payload, reviewStatus) {
  if (reviewStatus !== "approved" || !payload) return null;
  const out = { status: "published" };
  for (const key of PUBLIC_EVENT_KEYS) {
    if (key === "status") continue;
    if (payload[key] !== undefined && payload[key] !== null) out[key] = payload[key];
  }
  if (typeof out.note === "string") out.note = redactText(out.note);
  if (out.description && typeof out.description === "object" && typeof out.description.text === "string") {
    out.description = { ...out.description, text: redactText(out.description.text) };
  }
  if (typeof out.map_url !== "string" || !out.map_url.startsWith("https://")) delete out.map_url;
  return out;
}

export function publicSource(payload) {
  const out = {};
  for (const key of ["id", "name", "country", "kind", "url", "enabled", "language", "paywall"]) {
    if (payload && payload[key] !== undefined && payload[key] !== null) out[key] = payload[key];
  }
  return out;
}

// Public picture record. The prompt stays in D1 and is not copied here.
export function publicImage(row, origin, alt) {
  if (!row || !row.story_id) return null;
  const base = String(origin || "").replace(/\/$/, "");
  const version = row.created_at ? "?v=" + encodeURIComponent(row.created_at) : "";
  return {
    url: base + "/story-images/" + row.story_id + ".png" + version,
    width: Number(row.width) || 1280,
    height: Number(row.height) || 720,
    alt: alt || "Nordic Crypto",
    style: row.style_id || null,
    kind: row.kind === "fallback" ? "fallback" : "original",
  };
}

export async function storyImageResponse(bucket, id) {
  if (!bucket || typeof bucket.get !== "function") {
    return json({ error: "not found" }, 404);
  }
  let object = null;
  try {
    object = await bucket.get("story-images/" + id + ".png");
  } catch (err) {
    object = null;
  }
  if (!object || !object.body) return json({ error: "not found" }, 404);
  const type = (object.httpMetadata && object.httpMetadata.contentType) || "image/png";
  return new Response(object.body, {
    status: 200,
    headers: {
      "content-type": type,
      "cache-control": "public, max-age=86400",
      "access-control-allow-origin": "*",
      "x-content-type-options": "nosniff",
    },
  });
}

function parsePayload(row) {
  if (!row) return null;
  if (typeof row.payload === "string") return JSON.parse(row.payload);
  return row.payload || null;
}

export function applyStoryReview(row, body, actor, at) {
  const payload = parsePayload(row);
  if (!payload) return { error: "story has no payload", status: 500 };
  const action = body && body.action;
  if (action === "approve") {
    const summary = String(body.summary || "").trim();
    if (!summary) return { error: "a story approval needs a summary", status: 400 };
    payload.status = "published";
    payload.summary = summary;
    payload.approved_by = actor;
    payload.approved_at = at;
    delete payload.reject_reason;
    for (const key of ["title_en", "topics", "summary_i18n", "summary_i18n_source", "summary_i18n_review", "title_i18n", "title_i18n_source", "primary_source"]) {
      if (body[key] !== undefined && body[key] !== null) payload[key] = body[key];
    }
    return {
      payload,
      review_status: "approved",
      item_status: "published",
      summary,
      reviewed_by: actor,
      reviewed_at: at,
      review_note: null,
    };
  }
  if (action === "reject") {
    payload.status = "rejected";
    payload.summary = null;
    delete payload.approved_by;
    delete payload.approved_at;
    if (body.reason) payload.reject_reason = body.reason;
    return {
      payload,
      review_status: "rejected",
      item_status: "rejected",
      summary: null,
      reviewed_by: actor,
      reviewed_at: at,
      review_note: body.reason || null,
    };
  }
  return { error: "action must be approve or reject", status: 400 };
}

export function applyEventReview(row, body, actor, at) {
  const payload = parsePayload(row);
  if (!payload) return { error: "event has no payload", status: 500 };
  const action = body && body.action;
  if (action === "approve") {
    if (body.note !== undefined) payload.note = body.note;
    if (body.note_i18n !== undefined) payload.note_i18n = body.note_i18n;
    return {
      payload,
      review_status: "approved",
      item_status: "published",
      reviewed_by: actor,
      reviewed_at: at,
      review_note: null,
    };
  }
  if (action === "reject") {
    payload.status = "rejected";
    if (body.reason) payload.reject_reason = body.reason;
    return {
      payload,
      review_status: "rejected",
      item_status: "rejected",
      reviewed_by: actor,
      reviewed_at: at,
      review_note: body.reason || null,
    };
  }
  return { error: "action must be approve or reject", status: 400 };
}

function flag(value, fallback) {
  if (value === true || value === 1 || value === "true") return true;
  if (value === false || value === 0 || value === "false") return false;
  return fallback;
}

const ACADEMIA_SECTIONS = ["courses", "groups", "publications", "research"];
const ACADEMIA_STATUS = new Set(["pending", "approved", "out", "unverified"]);
const ACADEMIA_GUARDS = [
  ["groups", ["cbs bitcoin"]],
  ["groups", ["blockchain student group"]],
  ["groups", ["aalto bitcoin"]],
  ["research", ["cobra"]],
  ["courses", ["cs-aj0100"]],
  ["courses", ["comm.net.500"]],
  ["courses", ["lt00df90"]],
];

function academiaNorm(value) {
  return String(value || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function academiaBlob(row) {
  return [row && row.name, row && row.title, row && row.code].filter(Boolean).join(" ").toLowerCase();
}

function academiaCanon(url) {
  try {
    const parsed = new URL(String(url || "").trim());
    let host = parsed.hostname.toLowerCase();
    if (host.startsWith("www.")) host = host.slice(4);
    const path = parsed.pathname.replace(/\/$/, "") || "/";
    const kept = [...parsed.searchParams.entries()].filter(([key]) => !/^(utm_|fbclid|gclid)/i.test(key));
    const query = kept.length
      ? "?" + kept.map(([key, value]) => encodeURIComponent(key) + "=" + encodeURIComponent(value)).join("&")
      : "";
    return host + path + query;
  } catch (err) {
    return "";
  }
}

export function academiaDedupeKey(section, row) {
  const record = row || {};
  if (section === "publications") {
    const doi = String(record.doi || "").trim().toLowerCase();
    if (doi) return "doi:" + doi;
    const url = academiaCanon(record.url);
    return url ? "url:" + url : "";
  }
  if (section === "courses") {
    const code = String(record.code || "").replace(/\s+/g, "").toUpperCase();
    const country = String(record.country || "").trim().toUpperCase();
    if (code) return "code:" + country + ":" + code;
    const url = academiaCanon(record.url);
    return url ? "url:" + url : "";
  }
  const name = academiaNorm(record.name || record.title);
  if (name) return "name:" + name;
  const url = academiaCanon(record.url);
  return url ? "url:" + url : "";
}

function academiaSafeId(value) {
  return String(value || "").replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^[-._]+|[-._]+$/g, "").slice(0, 120);
}

function assignAcademiaId(section, row, n, used) {
  let base;
  if (section === "publications" && row.doi) base = "doi-" + academiaSafeId(String(row.doi).split("/").join("_"));
  else if (section === "courses" && row.code) base = academiaSafeId((row.country || "xx") + "-" + row.code);
  else if (row.url) base = academiaSafeId(section + "-" + String(row.url).replace(/^https?:\/\//, "").replace(/\/$/, ""));
  else base = academiaSafeId(row.name || row.title || section + "-" + n);
  base = (base || section + "-" + n).slice(0, 120);
  let cand = base;
  let i = 2;
  while (used.has(cand)) {
    cand = base + "-" + i;
    i += 1;
  }
  used.add(cand);
  return cand;
}

export function publicAcademia(payload, id, section) {
  if (!payload || payload.status !== "approved") return null;
  const out = {};
  for (const [key, value] of Object.entries(payload)) {
    if (key === "editor_note" || key === "status" || key === "id" || String(key).startsWith("_")) continue;
    out[key] = value;
  }
  out.id = id;
  out.section = section;
  return out;
}

function academiaDocumentFrom(body) {
  if (!body || typeof body !== "object") return { error: "academia body must be a JSON object", status: 400 };
  const singular = { course: "courses", group: "groups", publication: "publications", research: "research" };
  if (body.payload && body.section) {
    const section = singular[body.section] || body.section;
    if (!ACADEMIA_SECTIONS.includes(section)) {
      return { error: "section must be courses, groups, publications or research", status: 400 };
    }
    return { document: { [section]: [body.payload] } };
  }
  const source = body.document && typeof body.document === "object" ? body.document : body;
  const document = {};
  let any = false;
  for (const section of ACADEMIA_SECTIONS) {
    if (source[section] == null) continue;
    if (!Array.isArray(source[section])) return { error: section + " must be a list", status: 400 };
    document[section] = source[section];
    any = true;
  }
  if (!any) return { error: "academia needs courses, groups, publications or research", status: 400 };
  return { document };
}

function academiaGuarded(section, row, blobs) {
  const blob = academiaBlob(row);
  if (!blob) return false;
  return ACADEMIA_GUARDS.some(([sec, tokens]) => {
    if (sec !== section || !tokens.every((token) => blob.includes(token))) return false;
    return blobs.some(([existingSection, existingBlob]) => existingSection === section && tokens.every((token) => existingBlob.includes(token)));
  });
}

export function planAcademiaUpsert(existing, body) {
  const parsed = academiaDocumentFrom(body);
  if (parsed.error) return parsed;
  const update = !!(body && body.update);
  const byKey = new Map();
  const blobs = [];
  const used = new Set();
  for (const row of existing || []) {
    let payload = row.payload;
    if (typeof payload === "string") {
      try { payload = JSON.parse(payload); } catch (err) { payload = {}; }
    }
    byKey.set(row.section + "\0" + row.dedupe_key, row);
    blobs.push([row.section, academiaBlob(payload || {})]);
    if (row.id) used.add(row.id);
  }
  const rows = [];
  const guarded = [];
  let n = 0;
  for (const section of ACADEMIA_SECTIONS) {
    for (const raw of parsed.document[section] || []) {
      n += 1;
      if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        return { error: "an academia row is not an object", status: 400 };
      }
      if (!ACADEMIA_STATUS.has(raw.status)) {
        return { error: "an academia row has a status outside pending, approved, out, unverified", status: 400 };
      }
      const key = academiaDedupeKey(section, raw);
      if (!key || key.endsWith(":")) return { error: "an academia row needs a name, course code, DOI or url", status: 400 };
      const label = raw.name || raw.title || raw.code || key;
      const found = byKey.get(section + "\0" + key);
      if (!found && academiaGuarded(section, raw, blobs)) {
        guarded.push(label);
        continue;
      }
      if (!found) {
        const id = assignAcademiaId(section, raw, n, used);
        const payload = { ...raw, id };
        rows.push({ insert: true, id, section, key, payload, label });
        byKey.set(section + "\0" + key, { id, section, dedupe_key: key });
        blobs.push([section, academiaBlob(raw)]);
        continue;
      }
      rows.push({ insert: false, id: found.id, section, key, payload: { ...raw, id: found.id }, label, skip: !update });
    }
  }
  return { rows, guarded };
}

async function academiaMeta(db) {
  try {
    return await db.prepare("SELECT updated, rules FROM academia_meta WHERE id = 1").first();
  } catch (err) {
    return null;
  }
}

async function listAcademia(db, section) {
  try {
    const sql = section
      ? "SELECT id, section, payload FROM academia WHERE section = ? AND status = 'approved' ORDER BY country, id"
      : "SELECT id, section, payload FROM academia WHERE status = 'approved' ORDER BY section, country, id";
    const stmt = db.prepare(sql);
    const out = section ? await stmt.bind(section).all() : await stmt.all();
    const items = [];
    for (const row of out.results || []) {
      const pub = publicAcademia(JSON.parse(row.payload), row.id, row.section || section);
      if (pub) items.push(pub);
    }
    return items;
  } catch (err) {
    return [];
  }
}

function academiaCatalogue(items, meta) {
  const sections = { courses: [], groups: [], publications: [], research: [] };
  for (const item of items) {
    if (sections[item.section]) sections[item.section].push(item);
  }
  let rules = [];
  if (meta && meta.rules) {
    try {
      const parsed = JSON.parse(meta.rules);
      if (Array.isArray(parsed)) rules = parsed.filter((rule) => typeof rule === "string");
    } catch (err) {
      rules = [];
    }
  }
  return {
    updated: (meta && meta.updated) || null,
    inclusion_rules: rules,
    counts: {
      courses: sections.courses.length,
      groups: sections.groups.length,
      publications: sections.publications.length,
      research: sections.research.length,
    },
    ...sections,
  };
}

export async function sha256Hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(text)));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// Upsert a source. source_kind is news or event. A manual source with no enabled
// flag is stored off, so the fetch does not request it. The note stays out of the payload.
export function applySourceUpsert(existing, body, actor, at) {
  const raw = body && body.payload;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return { error: "a source payload is required", status: 400 };
  }
  const kind = body.source_kind;
  if (kind !== "news" && kind !== "event") {
    return { error: "source_kind must be news or event", status: 400 };
  }
  const payload = { ...raw };
  const id = String(payload.id || (body && body.id) || "").trim();
  if (!id || id.length > 200 || /[\n\r\t]/.test(id)) {
    return { error: "a source needs an id", status: 400 };
  }
  payload.id = id;
  let enabled;
  if (body.enabled !== undefined && body.enabled !== null) enabled = flag(body.enabled, null);
  else if (payload.enabled !== undefined && payload.enabled !== null) enabled = flag(payload.enabled, null);
  else if (payload.type === "manual") enabled = false;
  else enabled = true;
  if (enabled === null) return { error: "enabled must be true or false", status: 400 };
  payload.enabled = enabled;
  if (!existing && !payload.name && !payload.url) {
    return { error: "a new source needs a name or a url", status: 400 };
  }
  const note = body.note !== undefined ? body.note : (existing && existing.review_note) || null;
  return {
    id,
    kind,
    payload,
    enabled: enabled ? 1 : 0,
    name: payload.name || null,
    country: payload.country || null,
    url: payload.url || null,
    review_status: "approved",
    reviewed_by: actor,
    reviewed_at: at,
    review_note: note,
    insert: !existing,
  };
}

function json(data, status, extra) {
  const headers = {
    "content-type": "application/json; charset=utf-8",
    "access-control-allow-origin": "*",
    "cache-control": extra && extra.cache ? extra.cache : "no-store",
  };
  return new Response(JSON.stringify(data), { status, headers });
}

function storyIdFrom(pathname) {
  const match = pathname.match(/^\/api\/v1\/news\/([A-Za-z0-9]+)(?:\.json)?$/);
  return match ? match[1] : null;
}

function eventIdFrom(pathname) {
  const match = pathname.match(/^\/api\/v1\/events\/([A-Za-z0-9]+)(?:\.json)?$/);
  return match ? match[1] : null;
}

async function imageMap(db) {
  try {
    const out = await db.prepare(
      "SELECT story_id, style_id, width, height, created_at, kind FROM story_images"
    ).all();
    const map = new Map();
    for (const row of out.results || []) map.set(row.story_id, row);
    return map;
  } catch (err) {
    return new Map();
  }
}

async function imageFor(db, id) {
  try {
    return await db.prepare(
      "SELECT story_id, style_id, width, height, created_at, kind FROM story_images WHERE story_id = ?"
    ).bind(id).first();
  } catch (err) {
    return null;
  }
}

function withImage(pub, row, origin) {
  if (!pub) return null;
  const image = publicImage(row, origin, pub.title_en || pub.title);
  if (image) pub.image = image;
  return pub;
}

async function listNews(db, origin) {
  const out = await db.prepare(
    "SELECT payload FROM stories WHERE review_status = 'approved' AND item_status = 'published' ORDER BY published_at DESC"
  ).all();
  const images = await imageMap(db);
  const items = [];
  for (const row of out.results || []) {
    const payload = JSON.parse(row.payload);
    const pub = withImage(publicStory(payload), images.get(payload.id), origin);
    if (pub) items.push(pub);
  }
  return items;
}

async function listEvents(db) {
  const out = await db.prepare(
    "SELECT payload, review_status FROM events WHERE review_status = 'approved' ORDER BY start_at"
  ).all();
  const events = [];
  for (const row of out.results || []) {
    const pub = publicEvent(JSON.parse(row.payload), row.review_status);
    if (pub) events.push(pub);
  }
  return events;
}

async function dispatchRedeploy(env) {
  if (!env.GITHUB_DISPATCH_TOKEN || !env.GITHUB_REPOSITORY) return "scheduled";
  const response = await fetch(`https://api.github.com/repos/${env.GITHUB_REPOSITORY}/dispatches`, {
    method: "POST",
    headers: {
      authorization: "Bearer " + env.GITHUB_DISPATCH_TOKEN,
      accept: "application/vnd.github+json",
      "content-type": "application/json",
      "user-agent": "nordic-crypto-content",
    },
    body: JSON.stringify({ event_type: "d1-approved" }),
  });
  return response.ok ? "dispatched" : "scheduled";
}

export async function handle(request, env) {
  const url = new URL(request.url);
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "access-control-allow-origin": "*",
        "access-control-allow-methods": "GET, POST, OPTIONS",
        "access-control-allow-headers": "authorization, content-type",
        "access-control-max-age": "86400",
      },
    });
  }
  if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
    return json({ ok: true, service: "nordic-crypto-content" }, 200, { cache: "no-store" });
  }
  const imageId = url.pathname.match(/^\/story-images\/([A-Za-z0-9][A-Za-z0-9_-]{0,80})\.png$/);
  if (request.method === "GET" && imageId) {
    return storyImageResponse(env.STORY_IMAGES, imageId[1]);
  }

  const db = env.DB;
  if (!db) return json({ error: "database is not bound" }, 500);

  if (request.method === "GET" && url.pathname === "/api/v1/news.json") {
    return json({ items: await listNews(db, url.origin) }, 200, { cache: PUBLIC_CACHE });
  }
  const storyId = storyIdFrom(url.pathname);
  if (request.method === "GET" && storyId) {
    const row = await db.prepare(STORY_SELECT).bind(storyId).first();
    const pub = row && row.review_status === "approved" ? publicStory(JSON.parse(row.payload)) : null;
    if (!pub) return json({ error: "not found" }, 404);
    const image = publicImage(await imageFor(db, storyId), url.origin, pub.title_en || pub.title);
    if (image) pub.image = image;
    return json(pub, 200, { cache: PUBLIC_CACHE });
  }
  if (request.method === "GET" && (url.pathname === "/api/v1/events.ics" || url.pathname === "/calendar.ics")) {
    const body = eventsToIcs(await listEvents(db));
    return new Response(body, {
      status: 200,
      headers: {
        "content-type": "text/calendar; charset=utf-8",
        "access-control-allow-origin": "*",
        "cache-control": PUBLIC_CACHE,
      },
    });
  }
  if (request.method === "GET" && url.pathname === "/api/v1/events.json") {
    return json({ events: await listEvents(db) }, 200, { cache: PUBLIC_CACHE });
  }
  const eventId = eventIdFrom(url.pathname);
  if (request.method === "GET" && eventId) {
    const row = await db.prepare(EVENT_SELECT).bind(eventId).first();
    const pub = row ? publicEvent(JSON.parse(row.payload), row.review_status) : null;
    if (!pub) return json({ error: "not found" }, 404);
    return json(pub, 200, { cache: PUBLIC_CACHE });
  }
  if (request.method === "GET" && url.pathname === "/api/v1/academia.json") {
    const items = await listAcademia(db);
    return json(academiaCatalogue(items, await academiaMeta(db)), 200, { cache: PUBLIC_CACHE });
  }
  const academiaSection = url.pathname.match(/^\/api\/v1\/academia\/(courses|groups|publications|research)\.json$/);
  if (request.method === "GET" && academiaSection) {
    const items = await listAcademia(db, academiaSection[1]);
    return json({ section: academiaSection[1], count: items.length, items }, 200, { cache: PUBLIC_CACHE });
  }
  const academiaId = url.pathname.match(/^\/api\/v1\/academia\/([A-Za-z0-9._-]{1,160})\.json$/);
  if (request.method === "GET" && academiaId) {
    let row = null;
    try {
      row = await db.prepare("SELECT id, section, payload, status FROM academia WHERE id = ?").bind(academiaId[1]).first();
    } catch (err) {
      row = null;
    }
    const payload = row && row.payload ? JSON.parse(row.payload) : null;
    const pub = row && row.status === "approved" ? publicAcademia(payload, row.id, row.section) : null;
    if (!pub) return json({ error: "not found" }, 404);
    return json(pub, 200, { cache: PUBLIC_CACHE });
  }
  if (request.method === "GET" && url.pathname === "/api/v1/sources.json") {
    const out = await db.prepare(
      "SELECT payload FROM sources WHERE review_status = 'approved' ORDER BY kind, id"
    ).all();
    const sources = (out.results || []).map((row) => publicSource(JSON.parse(row.payload)));
    return json({ sources }, 200, { cache: PUBLIC_CACHE });
  }

  if (url.pathname === "/api/review/pending" || url.pathname === "/api/review") {
    if (!env.EDITOR_TOKEN) return json({ error: "editor token is not set" }, 503);
    if (!editorAuthorized(request, env.EDITOR_TOKEN)) return json({ error: "unauthorized" }, 401);
  }

  if (request.method === "GET" && url.pathname === "/api/review/pending") {
    const stories = await db.prepare(
      "SELECT id, title, country, url, published_at FROM stories WHERE review_status = 'pending' AND item_status = 'pending' ORDER BY published_at DESC"
    ).all();
    const events = await db.prepare(
      "SELECT id, title, country, url, start_at FROM events WHERE review_status = 'pending' AND item_status = 'pending' ORDER BY start_at"
    ).all();
    let academia = [];
    try {
      const pendingAcademia = await db.prepare(
        "SELECT id, section, name, country, status FROM academia WHERE status != 'approved' ORDER BY section, country, name"
      ).all();
      academia = pendingAcademia.results || [];
    } catch (err) {
      academia = [];
    }
    return json({ stories: stories.results || [], events: events.results || [], academia }, 200);
  }

  if (request.method === "POST" && url.pathname === "/api/review") {
    let body;
    try {
      body = await request.json();
    } catch (err) {
      return json({ error: "body must be JSON" }, 400);
    }
    if (!body || (body.kind !== "story" && body.kind !== "event" && body.kind !== "source" && body.kind !== "academia")) {
      return json({ error: "kind (story, event, source or academia) is required" }, 400);
    }
    if (body.kind !== "source" && body.kind !== "academia" && !body.id) {
      return json({ error: "kind and id are required" }, 400);
    }
    const actor = String(body.by || "Nordic Crypto redaktør");
    const at = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
    if (body.kind === "source") {
      const sourceId = String((body.payload && body.payload.id) || body.id || "").trim();
      const existing = sourceId
        ? await db.prepare("SELECT id, review_note, created_at FROM sources WHERE id = ?").bind(sourceId).first()
        : null;
      const plan = applySourceUpsert(existing, body, actor, at);
      if (plan.error) return json({ error: plan.error }, plan.status);
      const text = JSON.stringify(plan.payload);
      const hash = await sha256Hex(text);
      if (plan.insert) {
        await db.prepare(
          "INSERT INTO sources (id, kind, name, country, url, enabled, review_status, reviewed_by, reviewed_at, review_note, payload, content_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ).bind(
          plan.id, plan.kind, plan.name, plan.country, plan.url, plan.enabled, plan.review_status,
          plan.reviewed_by, plan.reviewed_at, plan.review_note, text, hash, at, at,
        ).run();
      } else {
        await db.prepare(
          "UPDATE sources SET kind = ?, name = ?, country = ?, url = ?, enabled = ?, review_status = ?, reviewed_by = ?, reviewed_at = ?, review_note = ?, payload = ?, content_hash = ?, updated_at = ? WHERE id = ?"
        ).bind(
          plan.kind, plan.name, plan.country, plan.url, plan.enabled, plan.review_status,
          plan.reviewed_by, plan.reviewed_at, plan.review_note, text, hash, at, plan.id,
        ).run();
      }
      await db.prepare(
        "INSERT INTO review_audit (kind, item_id, action, actor, at, detail) VALUES ('source', ?, ?, ?, ?, ?)"
      ).bind(plan.id, plan.insert ? "add" : "edit", actor, at, plan.kind).run();
      let redeploy = "scheduled";
      try {
        redeploy = await dispatchRedeploy(env);
      } catch (err) {
        redeploy = "scheduled";
      }
      return json({
        ok: true, kind: "source", id: plan.id, source_kind: plan.kind, enabled: plan.enabled === 1, redeploy,
      }, 200);
    }
    if (body.kind === "academia") {
      let existing = [];
      try {
        const out = await db.prepare(
          "SELECT id, section, dedupe_key, payload, content_hash FROM academia"
        ).all();
        existing = out.results || [];
      } catch (err) {
        return json({ error: "academia table is missing" }, 503);
      }
      const plan = planAcademiaUpsert(existing, body);
      if (plan.error) return json({ error: plan.error }, plan.status);
      let inserted = 0;
      let updated = 0;
      let kept = 0;
      for (const row of plan.rows) {
        if (!row.insert && row.skip) {
          kept += 1;
          continue;
        }
        const text = JSON.stringify(row.payload);
        const hash = await sha256Hex(text);
        const active = row.section === "groups" ? (row.payload.active === true ? 1 : row.payload.active === false ? 0 : null) : null;
        const institution = Array.isArray(row.payload.institution)
          ? row.payload.institution.filter(Boolean).join(", ")
          : (row.payload.institution || null);
        const year = Number.isInteger(row.payload.year) ? row.payload.year : null;
        if (row.insert) {
          await db.prepare(
            "INSERT INTO academia (id, section, country, name, code, institution, url, doi, status, active, year, pub_type, dedupe_key, payload, content_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
          ).bind(
            row.id, row.section, row.payload.country || null, row.payload.name || row.payload.title || null,
            row.payload.code || null, institution, row.payload.url || null,
            row.payload.doi ? String(row.payload.doi).trim().toLowerCase() : null,
            row.payload.status, active, year, row.section === "publications" ? (row.payload.type || null) : null,
            row.key, text, hash, at, at,
          ).run();
          inserted += 1;
        } else {
          await db.prepare(
            "UPDATE academia SET country = ?, name = ?, code = ?, institution = ?, url = ?, doi = ?, status = ?, active = ?, year = ?, pub_type = ?, payload = ?, content_hash = ?, updated_at = ? WHERE id = ?"
          ).bind(
            row.payload.country || null, row.payload.name || row.payload.title || null, row.payload.code || null,
            institution, row.payload.url || null,
            row.payload.doi ? String(row.payload.doi).trim().toLowerCase() : null,
            row.payload.status, active, year, row.section === "publications" ? (row.payload.type || null) : null,
            text, hash, at, row.id,
          ).run();
          updated += 1;
        }
        await db.prepare(
          "INSERT INTO review_audit (kind, item_id, action, actor, at, detail) VALUES ('academia', ?, ?, ?, ?, ?)"
        ).bind(row.id, row.insert ? "add" : "edit", actor, at, row.section).run();
      }
      let redeploy = "scheduled";
      try {
        redeploy = await dispatchRedeploy(env);
      } catch (err) {
        redeploy = "scheduled";
      }
      return json({
        ok: true, kind: "academia", inserted, updated, kept, guarded: plan.guarded, redeploy,
      }, 200);
    }
    if (body.kind === "story") {
      const row = await db.prepare(STORY_SELECT).bind(body.id).first();
      if (!row) return json({ error: "no story" }, 404);
      const plan = applyStoryReview(row, body, actor, at);
      if (plan.error) return json({ error: plan.error }, plan.status);
      const text = JSON.stringify(plan.payload);
      await db.prepare(
        "UPDATE stories SET payload = ?, content_hash = ?, review_status = ?, item_status = ?, summary = ?, reviewed_by = ?, reviewed_at = ?, review_note = ?, updated_at = ?, title = ?, url = ? WHERE id = ?"
      ).bind(
        text, "", plan.review_status, plan.item_status, plan.summary, plan.reviewed_by, plan.reviewed_at,
        plan.review_note, at, plan.payload.title || null, plan.payload.url || row.url, body.id,
      ).run();
      await db.prepare(
        "INSERT INTO review_audit (kind, item_id, action, actor, at, detail) VALUES ('story', ?, ?, ?, ?, ?)"
      ).bind(body.id, body.action, actor, at, plan.review_status).run();
      let redeploy = "scheduled";
      try {
        redeploy = await dispatchRedeploy(env);
      } catch (err) {
        redeploy = "scheduled";
      }
      return json({ ok: true, kind: "story", id: body.id, review_status: plan.review_status, redeploy }, 200);
    }
    const row = await db.prepare(EVENT_SELECT).bind(body.id).first();
    if (!row) return json({ error: "no event" }, 404);
    const plan = applyEventReview(row, body, actor, at);
    if (plan.error) return json({ error: plan.error }, plan.status);
    const text = JSON.stringify(plan.payload);
    await db.prepare(
      "UPDATE events SET payload = ?, review_status = ?, item_status = ?, reviewed_by = ?, reviewed_at = ?, review_note = ?, updated_at = ?, title = ? WHERE id = ?"
    ).bind(
      text, plan.review_status, plan.item_status, plan.reviewed_by, plan.reviewed_at, plan.review_note, at,
      plan.payload.title || null, body.id,
    ).run();
    await db.prepare(
      "INSERT INTO review_audit (kind, item_id, action, actor, at, detail) VALUES ('event', ?, ?, ?, ?, ?)"
    ).bind(body.id, body.action, actor, at, plan.review_status).run();
    let redeploy = "scheduled";
    try {
      redeploy = await dispatchRedeploy(env);
    } catch (err) {
      redeploy = "scheduled";
    }
    return json({ ok: true, kind: "event", id: body.id, review_status: plan.review_status, redeploy }, 200);
  }

  return json({ error: "not found" }, 404);
}

// Public reads are cached at the edge for EDGE_TTL seconds, so D1 is read at most about
// once a minute per colo. Review endpoints are never cached.
export const EDGE_TTL = 60;

export async function cachedHandle(request, env, ctx) {
  const url = new URL(request.url);
  const cacheable = request.method === "GET" && (url.pathname.startsWith("/api/v1/") || url.pathname.startsWith("/story-images/"));
  const cache = cacheable && typeof caches !== "undefined" ? caches.default : null;
  const key = cache ? new Request(url.origin + url.pathname + url.search, { method: "GET" }) : null;
  if (cache) {
    const hit = await cache.match(key);
    if (hit) return hit;
  }
  const response = await handle(request, env);
  if (cache && response.status === 200) {
    const put = cache.put(key, response.clone());
    if (ctx && ctx.waitUntil) ctx.waitUntil(put); else await put;
  }
  return response;
}

export default { fetch: (request, env, ctx) => cachedHandle(request, env, ctx) };
