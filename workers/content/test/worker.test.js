import test from "node:test";
import assert from "node:assert/strict";
import { applyEventReview, applySourceUpsert, applyStoryReview, editorAuthorized, handle, planAcademiaUpsert, publicAcademia, publicEvent, publicImage, publicSource, publicStory } from "../src/worker.js";

const TOKEN = "editor-token-for-tests";

function storyRow(extra = {}) {
  const payload = {
    id: "abc",
    url: "https://example.com/a",
    title: "Headline",
    status: "pending",
    summary: null,
    matched: ["\\bkrypto"],
    origin: "reader tip #4",
    reject_reason: "old",
    teaser_local_only: "do not publish this sentence",
    ...extra.payload,
  };
  return {
    id: "abc",
    url: payload.url,
    title: payload.title,
    payload: JSON.stringify(payload),
    review_status: "pending",
    item_status: "pending",
    ...extra.row,
  };
}

test("public story drops working fields", () => {
  const pub = publicStory({
    id: "abc",
    url: "https://example.com/a",
    title: "Headline",
    status: "published",
    summary: "Two sentences about the story. The second says what happened.",
    summary_i18n: { nn: "To setningar." },
    summary_i18n_review: "approved",
    matched: ["secret-pattern"],
    origin: "reader tip #4",
    reject_reason: "no",
    teaser_local_only: "copied teaser",
    approved_by: "Editor",
  });
  assert.equal(pub.summary.startsWith("Two"), true);
  assert.equal(pub.matched, undefined);
  assert.equal(pub.origin, undefined);
  assert.equal(pub.reject_reason, undefined);
  assert.equal(pub.teaser_local_only, undefined);
  assert.equal(pub.approved_by, undefined);
  assert.equal(publicStory({ status: "pending", summary: "x", id: "a" }), null);
  assert.equal(publicStory({
    status: "published",
    summary: "Kept.",
    summary_i18n: { nn: "Utkast." },
    summary_i18n_review: "pending",
    id: "a",
    title: "t",
  }).summary_i18n, undefined);
});

test("public event and source stay on the public fields", () => {
  const event = publicEvent({
    id: "e1",
    title: "Meetup",
    start: "2026-10-08T18:00:00+02:00",
    note: "Paid entry.",
    editor_title_en: "English",
    status: "pending",
  }, "approved");
  assert.equal(event.status, "published");
  assert.equal(event.note, "Paid entry.");
  assert.equal(event.editor_title_en, undefined);
  assert.equal(publicEvent({ id: "e1", title: "Meetup" }, "pending"), null);
  assert.deepEqual(publicSource({ id: "firi", name: "Firi", country: "NO", feed: "https://secret.example/rss", status: "ok" }), {
    id: "firi", name: "Firi", country: "NO",
  });
});

test("story approval needs a summary and records who and when", () => {
  const missing = applyStoryReview(storyRow(), { action: "approve", summary: "  " }, "Editor", "2026-10-10T12:00:00Z");
  assert.equal(missing.status, 400);
  const plan = applyStoryReview(storyRow(), {
    action: "approve",
    summary: "The company said it uses crypto mining. The letter is on the record.",
    title_en: "English headline",
  }, "Editor", "2026-10-10T12:00:00Z");
  assert.equal(plan.review_status, "approved");
  assert.equal(plan.reviewed_by, "Editor");
  assert.equal(plan.reviewed_at, "2026-10-10T12:00:00Z");
  assert.equal(plan.payload.status, "published");
  assert.equal(plan.payload.title_en, "English headline");
  assert.equal(plan.payload.reject_reason, undefined);
  assert.equal(plan.payload.matched[0], "\\bkrypto");
  const rejected = applyStoryReview(storyRow(), { action: "reject", reason: "Not Nordic." }, "Editor", "2026-10-10T12:00:00Z");
  assert.equal(rejected.review_status, "rejected");
  assert.equal(rejected.review_note, "Not Nordic.");
  assert.equal(rejected.payload.summary, null);
});

test("event rejection keeps the row and sets the audit fields", () => {
  const row = { id: "e1", payload: JSON.stringify({ id: "e1", title: "Meetup", status: "pending" }) };
  const plan = applyEventReview(row, { action: "reject", reason: "No Nordic link." }, "Editor", "2026-10-10T12:00:00Z");
  assert.equal(plan.review_status, "rejected");
  assert.equal(plan.item_status, "rejected");
  assert.equal(plan.reviewed_by, "Editor");
  assert.equal(plan.payload.reject_reason, "No Nordic link.");
});

function fakeDb(seed) {
  const stories = new Map(seed.stories || []);
  const events = new Map(seed.events || []);
  const images = new Map(seed.images || []);
  const sources = new Map(seed.sources || []);
  const academia = new Map(seed.academia || []);
  const academiaMeta = seed.academiaMeta || null;
  const audits = [];
  function prepare(sql) {
    const state = { sql, params: [] };
    const api = {
      bind(...params) {
        state.params = params;
        return api;
      },
      async first() {
        if (state.sql.includes("FROM story_images")) return images.get(state.params[0]) || null;
        if (state.sql.includes("FROM academia_meta")) return academiaMeta;
        if (state.sql.includes("FROM academia WHERE id")) return academia.get(state.params[0]) || null;
        if (state.sql.includes("FROM stories")) return stories.get(state.params[0]) || null;
        if (state.sql.includes("FROM events")) return events.get(state.params[0]) || null;
        if (state.sql.includes("FROM sources")) return sources.get(state.params[0]) || null;
        return null;
      },
      async all() {
        if (state.sql.includes("FROM story_images")) return { results: [...images.values()] };
        if (state.sql.includes("dedupe_key") && state.sql.includes("FROM academia")) {
          return { results: [...academia.values()] };
        }
        if (state.sql.includes("FROM academia WHERE section = ?") && state.sql.includes("status = 'approved'")) {
          const section = state.params[0];
          return { results: [...academia.values()].filter((row) => row.section === section && row.status === "approved") };
        }
        if (state.sql.includes("FROM academia WHERE status = 'approved'")) {
          return { results: [...academia.values()].filter((row) => row.status === "approved") };
        }
        if (state.sql.includes("FROM academia WHERE status != 'approved'")) {
          return { results: [...academia.values()].filter((row) => row.status !== "approved").map((row) => ({ id: row.id, section: row.section, name: row.name, country: row.country, status: row.status })) };
        }
        if (state.sql.includes("FROM stories") && state.sql.includes("review_status = 'approved'")) {
          return { results: [...stories.values()].filter((row) => row.review_status === "approved").map((row) => ({ payload: row.payload })) };
        }
        if (state.sql.includes("FROM stories") && state.sql.includes("item_status = 'pending'")) {
          return { results: [...stories.values()].filter((row) => row.review_status === "pending" && row.item_status === "pending").map((row) => ({ id: row.id, title: row.title, country: row.country, url: row.url })) };
        }
        if (state.sql.includes("FROM events") && state.sql.includes("review_status = 'approved'")) {
          return { results: [...events.values()].filter((row) => row.review_status === "approved") };
        }
        if (state.sql.includes("FROM events") && state.sql.includes("item_status = 'pending'")) {
          return { results: [...events.values()].filter((row) => row.review_status === "pending" && row.item_status === "pending") };
        }
        if (state.sql.includes("FROM sources")) {
          const rows = [...sources.values()].filter((row) => row.review_status === "approved");
          return { results: rows.map((row) => ({ payload: row.payload })) };
        }
        return { results: [] };
      },
      async run() {
        if (state.sql.startsWith("UPDATE stories")) {
          const id = state.params[state.params.length - 1];
          const row = stories.get(id);
          row.payload = state.params[0];
          row.review_status = state.params[2];
          row.item_status = state.params[3];
          row.summary = state.params[4];
          row.reviewed_by = state.params[5];
          row.reviewed_at = state.params[6];
        } else if (state.sql.startsWith("UPDATE events")) {
          const id = state.params[state.params.length - 1];
          const row = events.get(id);
          row.payload = state.params[0];
          row.review_status = state.params[1];
          row.item_status = state.params[2];
          row.reviewed_by = state.params[3];
          row.reviewed_at = state.params[4];
        } else if (state.sql.startsWith("INSERT INTO sources")) {
          const id = state.params[0];
          sources.set(id, {
            id,
            kind: state.params[1],
            name: state.params[2],
            country: state.params[3],
            url: state.params[4],
            enabled: state.params[5],
            review_status: state.params[6],
            reviewed_by: state.params[7],
            reviewed_at: state.params[8],
            review_note: state.params[9],
            payload: state.params[10],
            content_hash: state.params[11],
          });
        } else if (state.sql.startsWith("UPDATE sources")) {
          const id = state.params[state.params.length - 1];
          const row = sources.get(id);
          row.kind = state.params[0];
          row.name = state.params[1];
          row.enabled = state.params[4];
          row.review_status = state.params[5];
          row.review_note = state.params[8];
          row.payload = state.params[9];
        } else if (state.sql.startsWith("INSERT INTO academia")) {
          const id = state.params[0];
          academia.set(id, {
            id,
            section: state.params[1],
            country: state.params[2],
            name: state.params[3],
            code: state.params[4],
            status: state.params[8],
            dedupe_key: state.params[12],
            payload: state.params[13],
            content_hash: state.params[14],
          });
        } else if (state.sql.startsWith("UPDATE academia")) {
          const id = state.params[state.params.length - 1];
          const row = academia.get(id);
          if (row) {
            row.payload = state.params[10];
            row.status = state.params[6];
            row.name = state.params[1];
          }
        } else if (state.sql.startsWith("INSERT INTO review_audit")) {
          audits.push(state.params);
        }
        return { success: true };
      },
    };
    return api;
  }
  return { prepare, stories, events, sources, academia, audits };
}

function request(method, path, { token, body } = {}) {
  const headers = new Headers();
  if (token) headers.set("authorization", "Bearer " + token);
  if (body) headers.set("content-type", "application/json");
  return new Request("https://content.example" + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
}

test("the review API refuses a missing or wrong token and does not publish teasers", async () => {
  const db = fakeDb({
    stories: [["abc", storyRow()]],
    events: [["e1", {
      id: "e1",
      payload: JSON.stringify({ id: "e1", title: "Meetup", start: "2026-11-01T18:00:00+02:00", teaser_local_only: "hidden" }),
      review_status: "approved",
      item_status: "published",
    }]],
  });
  const env = { DB: db, EDITOR_TOKEN: TOKEN, GITHUB_REPOSITORY: "nordic-crypto-org/nordic-crypto" };
  assert.equal((await handle(request("GET", "/api/review/pending"), env)).status, 401);
  assert.equal((await handle(request("GET", "/api/review/pending", { token: "nope" }), env)).status, 401);
  assert.equal((await handle(request("POST", "/api/review", { token: TOKEN, body: { kind: "story", id: "abc", action: "approve" } }), env)).status, 400);
  const pending = await handle(request("GET", "/api/review/pending", { token: TOKEN }), env);
  const pendingBody = await pending.json();
  assert.equal(pendingBody.stories.length, 1);
  assert.equal(JSON.stringify(pendingBody).includes("do not publish"), false);
  const approved = await handle(request("POST", "/api/review", {
    token: TOKEN,
    body: { kind: "story", id: "abc", action: "approve", summary: "Own words. What the story says.", by: "Editor" },
  }), env);
  const approvedBody = await approved.json();
  assert.equal(approvedBody.review_status, "approved");
  assert.equal(approvedBody.redeploy, "scheduled");
  assert.equal(db.stories.get("abc").reviewed_by, "Editor");
  assert.equal(db.audits.length, 1);
  const news = await (await handle(request("GET", "/api/v1/news.json"), env)).json();
  assert.equal(news.items.length, 1);
  assert.equal(JSON.stringify(news).includes("teaser_local_only"), false);
  assert.equal(JSON.stringify(news).includes("reader tip"), false);
  const events = await (await handle(request("GET", "/api/v1/events.json"), env)).json();
  assert.equal(events.events[0].title, "Meetup");
  assert.equal(JSON.stringify(events).includes("hidden"), false);
});

test("a configured dispatch token is not required for the approval to stick", () => {
  assert.equal(editorAuthorized(request("GET", "/api/review/pending", { token: TOKEN }), TOKEN), true);
  assert.equal(editorAuthorized(request("GET", "/api/review/pending"), TOKEN), false);
  assert.equal(editorAuthorized(request("GET", "/api/review/pending", { token: TOKEN }), ""), false);
});

test("a story image URL is public and the prompt is not", async () => {
  const row = storyRow({
    payload: { status: "published", summary: "The exchange replaced the assets. The figure is about 90 percent." },
    row: { review_status: "approved", item_status: "published" },
  });
  const image = {
    story_id: "abc",
    style_id: "woodcut-mining",
    width: 1280,
    height: 720,
    created_at: "2026-11-06T12:00:00Z",
    kind: "ai",
    prompt: "do not publish this prompt",
  };
  const db = fakeDb({ stories: [["abc", row]], images: [["abc", image]] });
  const png = new Uint8Array([137, 80, 78, 71, 13, 10]);
  const env = {
    DB: db,
    STORY_IMAGES: {
      async get(key) {
        if (key !== "story-images/abc.png") return null;
        return { body: png, httpMetadata: { contentType: "image/png" } };
      },
    },
  };
  const news = await (await handle(request("GET", "/api/v1/news.json"), env)).json();
  assert.equal(news.items.length, 1);
  assert.equal(news.items[0].image.kind, "original");
  assert.equal(news.items[0].image.width, 1280);
  assert.match(news.items[0].image.url, /^https:\/\/content\.example\/story-images\/abc\.png\?v=/);
  assert.equal(JSON.stringify(news).includes("do not publish"), false);
  assert.equal(JSON.stringify(news).includes("prompt"), false);
  const one = await (await handle(request("GET", "/api/v1/news/abc.json"), env)).json();
  assert.equal(one.image.style, "woodcut-mining");
  const bytes = await handle(request("GET", "/story-images/abc.png"), env);
  assert.equal(bytes.status, 200);
  assert.equal(bytes.headers.get("content-type"), "image/png");
  assert.equal((await bytes.arrayBuffer()).byteLength, png.length);
  const missing = await handle(request("GET", "/story-images/nope.png"), env);
  assert.equal(missing.status, 404);
  const bare = publicImage(image, "https://api.nordiccrypto.no", "Headline");
  assert.equal(bare.prompt, undefined);
  assert.equal(bare.alt, "Headline");
});

test("a manual source is stored off and is not fetched by being public feed config", async () => {
  const missing = applySourceUpsert(null, { source_kind: "event", payload: { name: "x" } }, "Editor", "2026-11-09T12:00:00Z");
  assert.equal(missing.status, 400);
  const plan = applySourceUpsert(null, {
    source_kind: "event",
    note: "Checked by hand.",
    payload: { id: "undoqo-plebs", name: "Undoqo", url: "https://example.org/plebs", type: "manual" },
  }, "Editor", "2026-11-09T12:00:00Z");
  assert.equal(plan.insert, true);
  assert.equal(plan.enabled, 0);
  assert.equal(plan.payload.enabled, false);
  assert.equal(plan.payload.note, undefined);
  assert.equal(plan.review_note, "Checked by hand.");
  const db = fakeDb({ sources: [] });
  const env = { DB: db, EDITOR_TOKEN: TOKEN };
  const added = await handle(request("POST", "/api/review", {
    token: TOKEN,
    body: {
      kind: "source",
      source_kind: "event",
      note: "Checked by hand.",
      payload: { id: "undoqo-plebs", name: "Undoqo", url: "https://example.org/plebs", type: "manual", enabled: false },
    },
  }), env);
  const body = await added.json();
  assert.equal(added.status, 200);
  assert.equal(body.ok, true);
  assert.equal(body.enabled, false);
  const row = db.sources.get("undoqo-plebs");
  assert.equal(row.review_status, "approved");
  assert.equal(row.review_note, "Checked by hand.");
  assert.equal(JSON.parse(row.payload).type, "manual");
  const catalogue = await (await handle(request("GET", "/api/v1/sources.json"), env)).json();
  assert.equal(catalogue.sources[0].id, "undoqo-plebs");
  assert.equal(catalogue.sources[0].enabled, false);
  assert.equal(JSON.stringify(catalogue).includes("Checked by hand"), false);
  const again = await handle(request("POST", "/api/review", {
    token: TOKEN,
    body: {
      kind: "source",
      source_kind: "event",
      id: "undoqo-plebs",
      payload: { id: "undoqo-plebs", name: "Undoqo Plebs", url: "https://example.org/plebs", type: "manual", enabled: false },
    },
  }), env);
  assert.equal((await again.json()).ok, true);
  assert.equal(JSON.parse(db.sources.get("undoqo-plebs").payload).name, "Undoqo Plebs");
  assert.equal(db.sources.get("undoqo-plebs").review_note, "Checked by hand.");
});

test("academia API shows approved rows only and will not duplicate a guarded name", async () => {
  const approved = {
    id: "DK-cbs-bitcoin",
    section: "groups",
    country: "DK",
    name: "CBS Bitcoin",
    status: "approved",
    dedupe_key: "name:cbs bitcoin",
    payload: JSON.stringify({
      country: "DK", name: "CBS Bitcoin", institution: "CBS", about: "Student group.",
      activity: "Active.", active: true, url: "https://example.org/cbs-bitcoin",
      source: "https://example.org/cbs-bitcoin", checked: "2026-11-01", status: "approved",
      editor_note: "do not publish this note", id: "DK-cbs-bitcoin",
    }),
  };
  const pending = {
    id: "DK-cbs-fintech",
    section: "groups",
    country: "DK",
    name: "CBS Fintech",
    status: "pending",
    dedupe_key: "name:cbs fintech",
    payload: JSON.stringify({
      country: "DK", name: "CBS Fintech", status: "pending", active: false,
      url: "https://example.org/cbs-fintech", editor_note: "still pending",
    }),
  };
  const db = fakeDb({
    academia: [[approved.id, approved], [pending.id, pending]],
    academiaMeta: { updated: "2026-11-09", rules: JSON.stringify(["Only approved rows."]) },
  });
  const env = { DB: db, EDITOR_TOKEN: TOKEN };
  const catalogue = await (await handle(request("GET", "/api/v1/academia.json"), env)).json();
  assert.equal(catalogue.counts.groups, 1);
  assert.equal(catalogue.groups[0].name, "CBS Bitcoin");
  assert.equal(catalogue.groups[0].editor_note, undefined);
  assert.equal(JSON.stringify(catalogue).includes("do not publish"), false);
  assert.equal(JSON.stringify(catalogue).includes("CBS Fintech"), false);
  const section = await (await handle(request("GET", "/api/v1/academia/groups.json"), env)).json();
  assert.equal(section.count, 1);
  const one = await handle(request("GET", "/api/v1/academia/DK-cbs-bitcoin.json"), env);
  assert.equal(one.status, 200);
  assert.equal((await one.json()).id, "DK-cbs-bitcoin");
  const hidden = await handle(request("GET", "/api/v1/academia/DK-cbs-fintech.json"), env);
  assert.equal(hidden.status, 404);
  const blocked = planAcademiaUpsert([approved], {
    section: "groups",
    payload: {
      country: "DK", name: "CBS Bitcoin", institution: "CBS", about: "Again.",
      activity: "none", active: false, url: "https://example.org/other",
      source: "https://example.org/other", checked: "2026-11-09", status: "approved", editor_note: "x",
    },
  });
  assert.equal(blocked.rows.length, 1);
  assert.equal(blocked.rows[0].insert, false);
  const cobra = planAcademiaUpsert([{
    id: "research-cobra",
    section: "research",
    dedupe_key: "name:cobra concordium blockchain research center aarhus",
    payload: JSON.stringify({ name: "COBRA – Concordium Blockchain Research Center Aarhus", status: "pending" }),
  }], {
    section: "research",
    payload: {
      country: "DK", name: "COBRA Aarhus", institution: "Aarhus", about: "Again.",
      url: "https://example.org/cobra", source: "https://example.org/cobra",
      checked: "2026-11-09", status: "approved", editor_note: "x",
    },
  });
  assert.equal(cobra.rows.length, 0);
  assert.equal(cobra.guarded.length, 1);
  const added = await handle(request("POST", "/api/review", {
    token: TOKEN,
    body: {
      kind: "academia",
      research: [{
        country: "DK", name: "European Blockchain Center (EBC)", institution: "ITU",
        about: "Centre.", url: "https://example.org/ebc", source: "https://example.org/ebc",
        checked: "2026-11-09", status: "approved", editor_note: "secret note",
      }],
    },
  }), env);
  const body = await added.json();
  assert.equal(added.status, 200);
  assert.equal(body.inserted, 1);
  const again = await (await handle(request("GET", "/api/v1/academia/research.json"), env)).json();
  assert.equal(again.count, 1);
  assert.equal(again.items[0].editor_note, undefined);
  assert.equal(publicAcademia({ status: "pending", name: "Hidden" }, "x", "research"), null);
});

test("public event ics drops a private email and keeps a verified map link", async () => {
  const payload = {
    id: "abc123",
    title: "Meetup",
    start: "2026-11-19T18:00:00+01:00",
    end: "2026-11-19T19:15:00+01:00",
    place: "Sturegatan 15",
    city: "Stockholm",
    country: "SE",
    online: false,
    organiser: "Unga Aktiesparare",
    url: "https://example.org/e",
    map_url: "https://www.google.com/maps/search/?api=1&query=Sturegatan",
    note: "Write a@b.co or call +46 70 123 45 67",
    status: "pending",
  };
  const pub = publicEvent(payload, "approved");
  assert.equal(pub.map_url, payload.map_url);
  assert.equal(pub.note.includes("@"), false);
  assert.equal(pub.note.includes("123 45 67"), false);
  assert.equal(publicEvent({ ...payload, map_url: "javascript:alert(1)" }, "approved").map_url, undefined);
  const db = fakeDb({
    events: [["abc123", { id: "abc123", review_status: "approved", payload: JSON.stringify(payload) }]],
  });
  const res = await handle(request("GET", "/api/v1/events.ics"), { DB: db });
  assert.equal(res.status, 200);
  assert.equal(res.headers.get("content-type"), "text/calendar; charset=utf-8");
  const text = await res.text();
  const same = await handle(request("GET", "/calendar.ics"), { DB: db });
  assert.equal(same.status, 200);
  assert.equal(await same.text(), text);
  assert.equal(text.startsWith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"), true);
  assert.equal(text.endsWith("END:VCALENDAR\r\n"), true);
  assert.equal(text.replace(/\r\n/g, "").includes("\n"), false);
  for (const line of text.split("\r\n")) {
    assert.ok(new TextEncoder().encode(line).length <= 75);
  }
  const flat = text.replace(/\r\n[ \t]/g, "");
  assert.match(flat, /PRODID:-\/\/Nordic Crypto\/\/Calendar\/\/EN/);
  assert.match(flat, /UID:abc123@nordiccrypto\.no/);
  assert.match(flat, /DTSTART:20261119T170000Z/);
  assert.match(flat, /SUMMARY:Meetup/);
  assert.match(flat, /https:\/\/www\.google\.com\/maps\/search\/\?api=1&query=Sturegatan/);
  assert.equal(flat.includes("a@b.co"), false);
  assert.equal(flat.includes("123 45 67"), false);
});
