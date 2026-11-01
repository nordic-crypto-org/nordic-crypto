import assert from "node:assert/strict";
import test from "node:test";
import { readdirSync, readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { Address, AddressType, GroupToken, Networks, PrivateKey } from "libnexa-ts";
import { fetchCards, findCard, resetCardCache, usableEdition, windowState } from "../src/cards.js";
import { performMint, releaseEdition, reserveEdition } from "../src/mint.js";
import { signNexaChallenge } from "../src/nexa/message.js";
import { turnstileOk } from "../src/turnstile.js";
import { NOW, testCards } from "./fixtures.mjs";

const caps = JSON.parse(readFileSync(new URL("../caps.json", import.meta.url)));
const AUTH = GroupToken.authFlags.AUTHORITY | GroupToken.authFlags.MINT | GroupToken.authFlags.BATON | GroupToken.authFlags.SUBGROUP;

// D1's prepare/bind/first/run/all over a real SQLite with every migration applied.
function sqliteD1() {
  const db = new DatabaseSync(":memory:");
  const dir = new URL("../migrations/", import.meta.url);
  for (const f of readdirSync(dir).filter((n) => n.endsWith(".sql")).sort()) {
    db.exec(readFileSync(new URL(f, dir), "utf8"));
  }
  return {
    raw: db,
    prepare(sql) {
      return {
        bind(...args) {
          const st = db.prepare(sql);
          return {
            async first() { return st.get(...args) ?? null; },
            async run() { return st.run(...args); },
            async all() { return { results: st.all(...args) }; },
          };
        },
      };
    },
  };
}

function signingEnv(DB) {
  DB.raw.prepare("INSERT INTO hot_observed (chain, amount, observed_at) VALUES ('nexa', 5000000, ?)").run(NOW);
  return {
    DB,
    NC_EVENT_NFT: "1",
    MINT_NETWORK: "testnet",
    NEXA_HOT_KEY: PrivateKey.fromRandom("testnet").toWIF(),
    NEXA_PARENT_GROUP: new Address(Uint8Array.from({ length: 32 }, (_, i) => i + 1), Networks.testnet, AddressType.GroupIdAddress).toString(),
  };
}

function visitorBody(extra = {}) {
  const visitor = PrivateKey.fromRandom("testnet");
  const address = visitor.toAddress().toString();
  return {
    chain: "nexa",
    event_id: "evt",
    kind: "ongoing",
    identity: address,
    signature: signNexaChallenge(visitor.toWIF(), "evt", address),
    ...extra,
  };
}

function mintDeps(over = {}) {
  return {
    now: () => new Date(NOW),
    loadCards: async () => testCards(),
    fetchUtxos: async () => ({
      authority: { outpoint: "11".repeat(32), satoshis: 2000, groupAmount: AUTH },
      funds: [{ outpoint: "22".repeat(32), satoshis: 500000 }],
    }),
    broadcast: async () => ({ ok: true }),
    ...over,
  };
}

test("the window follows the event: pre until the start, ongoing until the end", () => {
  const doc = testCards();
  const pre = findCard(doc, "nexa", "evt", "pre");
  const on = findCard(doc, "nexa", "evt", "ongoing");
  assert.equal(windowState(pre, new Date("2026-10-07T09:59:59Z")), "open");
  assert.equal(windowState(pre, new Date("2026-10-07T10:00:01Z")), "closed");
  assert.equal(windowState(on, new Date("2026-10-07T09:59:59Z")), "not_yet");
  assert.equal(windowState(on, new Date("2026-10-07T10:00:00Z")), "open");
  assert.equal(windowState(on, new Date("2026-10-07T14:00:00Z")), "open");
  assert.equal(windowState(on, new Date("2026-10-07T14:00:01Z")), "closed");
  assert.equal(findCard(doc, "nexa", "other", "ongoing"), null);
});

test("an unknown event or a closed window is refused before the policy", async () => {
  const env = signingEnv(sqliteD1());
  let calls = 0;
  const deps = mintDeps({ fetchUtxos: async () => { calls += 1; return null; } });
  const unknown = await performMint(env, visitorBody({ event_id: "made-up" }), caps, deps);
  assert.equal(unknown.reason, "unknown_card");
  const late = await performMint(env, visitorBody(), caps, { ...deps, now: () => new Date("2026-10-08T00:00:00Z") });
  assert.equal(late.reason, "outside_window");
  assert.equal(late.window, "closed");
  const early = await performMint(env, visitorBody({ kind: "pre" }), caps, deps);
  assert.equal(early.reason, "outside_window");
  const noKind = await performMint(env, visitorBody({ kind: "anything" }), caps, deps);
  assert.equal(noKind.reason, "bad_request");
  const noIndex = await performMint(env, visitorBody(), caps, { ...deps, loadCards: async () => null });
  assert.equal(noIndex.reason, "cards_unavailable");
  assert.equal(calls, 0);
});

test("each mint gets its own edition and the request cannot pick the card", async () => {
  const DB = sqliteD1();
  const env = signingEnv(DB);
  const seen = [];
  const deps = mintDeps({ broadcast: async (_chain, hex) => { seen.push(hex); return { ok: true }; } });
  const first = await performMint(env, visitorBody({
    zip_url: "https://nordiccrypto.no/assets/nft/evil.zip",
    zip_hash: "ee".repeat(32),
  }), caps, deps);
  assert.equal(first.broadcast, true, first.reason);
  assert.equal(first.edition, 1);
  const second = await performMint(env, visitorBody(), caps, deps);
  assert.equal(second.edition, 2);
  assert.notEqual(seen[0], seen[1]);
  assert.equal(seen[0].includes("ee".repeat(32)), false);
  const zip1 = Buffer.from("https://nordiccrypto.no/assets/nft/evt-ongoing-nexa-001.zip").toString("hex");
  const zip2 = Buffer.from("https://nordiccrypto.no/assets/nft/evt-ongoing-nexa-002.zip").toString("hex");
  assert.equal(seen[0].includes(zip1), true);
  assert.equal(seen[1].includes(zip2), true);
  const rows = DB.raw.prepare("SELECT kind, edition FROM mint_claim ORDER BY edition").all();
  assert.deepEqual(rows.map((r) => [r.kind, r.edition]), [["ongoing", 1], ["ongoing", 2]]);
});

test("the same identity cannot mint twice for one event", async () => {
  const env = signingEnv(sqliteD1());
  let broadcasts = 0;
  const deps = mintDeps({ broadcast: async () => { broadcasts += 1; return { ok: true }; } });
  const body = visitorBody();
  assert.equal((await performMint(env, body, caps, deps)).broadcast, true);
  const again = await performMint(env, body, caps, deps);
  assert.equal(again.reason, "identity_used");
  assert.equal(broadcasts, 1);
});

test("a rejected broadcast releases the edition", async () => {
  const DB = sqliteD1();
  const env = signingEnv(DB);
  const body = visitorBody();
  const rejected = await performMint(env, body, caps, mintDeps({ broadcast: async () => ({ ok: false, error: "missing inputs" }) }));
  assert.equal(rejected.reason, "broadcast_rejected");
  assert.equal(DB.raw.prepare("SELECT COUNT(*) AS n FROM mint_claim").get().n, 0);
  const thrown = await performMint(env, body, caps, mintDeps({ fetchUtxos: async () => { throw new Error("socket closed"); } }));
  assert.equal(thrown.reason, "utxo_unavailable");
  const retry = await performMint(env, body, caps, mintDeps());
  assert.equal(retry.broadcast, true, retry.reason);
  assert.equal(retry.edition, 1);
});

test("when the editions run out the mint stops", async () => {
  const env = signingEnv(sqliteD1());
  const deps = mintDeps({ loadCards: async () => testCards({ editions: 1 }) });
  assert.equal((await performMint(env, visitorBody(), caps, deps)).edition, 1);
  const out = await performMint(env, visitorBody(), caps, deps);
  assert.equal(out.reason, "editions_exhausted");
  assert.equal(out.broadcast, false);
});

test("the reservation takes the next number in one statement and refuses a second claim", async () => {
  const DB = sqliteD1();
  const row = { chain: "nexa", eventId: "evt", kind: "ongoing", day: "2026-10-07", at: NOW };
  assert.deepEqual(await reserveEdition(DB, { ...row, hash: "a" }), { ok: true, edition: 1 });
  assert.deepEqual(await reserveEdition(DB, { ...row, hash: "b" }), { ok: true, edition: 2 });
  assert.deepEqual(await reserveEdition(DB, { ...row, kind: "pre", hash: "c" }), { ok: true, edition: 1 });
  assert.deepEqual(await reserveEdition(DB, { ...row, hash: "a" }), { ok: false, reason: "identity_used" });
  await releaseEdition(DB, "b");
  assert.deepEqual(await reserveEdition(DB, { ...row, hash: "d" }), { ok: true, edition: 2 });
});

test("a malformed index row is not signed", () => {
  assert.equal(usableEdition("nexa", { zip_url: "https://evil.example/x.zip", zip_hash: "ab".repeat(32) }), false);
  assert.equal(usableEdition("nexa", { zip_url: "https://nordiccrypto.no/assets/nft/x.zip", zip_hash: "zz" }), false);
  assert.equal(usableEdition("nexa", { zip_url: "https://nordiccrypto.no/assets/nft/x.zip", zip_hash: "ab".repeat(32) }), true);
  assert.equal(usableEdition("bch", { commitment_hex: "ab".repeat(32) }), true);
  assert.equal(usableEdition("bch", {}), false);
});

test("the card index is cached and a bad fetch keeps the last good copy", async () => {
  resetCardCache();
  let calls = 0;
  const good = async () => { calls += 1; return new Response(JSON.stringify(testCards())); };
  const bad = async () => { calls += 1; return new Response("nope", { status: 500 }); };
  assert.ok(await fetchCards({}, 0, good));
  assert.ok(await fetchCards({}, 1000, bad));
  assert.equal(calls, 1);
  assert.ok(await fetchCards({}, 10 * 60 * 1000, bad));
  assert.equal(calls, 2);
  resetCardCache();
  assert.equal(await fetchCards({}, 0, bad), null);
});

test("a Bitcoin Cash mint needs a Turnstile token that Cloudflare accepts", async () => {
  const sent = [];
  const answer = (success) => async (url, init) => {
    sent.push({ url, body: String(init.body) });
    return new Response(JSON.stringify({ success }));
  };
  const env = { TURNSTILE_SECRET: "turnstile-secret-for-tests" };
  assert.equal(await turnstileOk(env, "", answer(true)), "missing");
  assert.equal(sent.length, 0);
  assert.equal(await turnstileOk(env, "anything-at-all", answer(false)), "bad");
  assert.equal(sent[0].url, "https://challenges.cloudflare.com/turnstile/v0/siteverify");
  assert.equal(sent[0].body.includes("response=anything-at-all"), true);
  assert.equal(await turnstileOk(env, "real-token", answer(true)), "ok");
  assert.equal(await turnstileOk(env, "real-token", async () => { throw new Error("down"); }), "bad");
  assert.equal(await turnstileOk({}, "real-token", answer(true)), "unconfigured");

  const body = { chain: "bch", event_id: "evt", kind: "ongoing", identity: "bchtest:zsomeone" };
  const deps = { now: () => new Date(NOW), loadCards: async () => testCards() };
  const forged = await performMint(env, { ...body, turnstile: "forged" }, caps, {
    ...deps, verifyTurnstile: (e, t) => turnstileOk(e, t, answer(false)),
  });
  assert.equal(forged.reason, "turnstile_failed");
  const missing = await performMint(env, body, caps, { ...deps, verifyTurnstile: (e, t) => turnstileOk(e, t, answer(true)) });
  assert.equal(missing.reason, "turnstile_required");
  const passed = await performMint(env, { ...body, turnstile: "real-token" }, caps, {
    ...deps, verifyTurnstile: (e, t) => turnstileOk(e, t, answer(true)),
  });
  assert.notEqual(passed.reason, "turnstile_failed");
  assert.notEqual(passed.reason, "turnstile_required");
});
