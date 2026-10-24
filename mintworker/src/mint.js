// One mint. The card comes from the published card index, never from the
// request, and the event must be inside its window. The policy runs next.
// Signing and broadcast run only when the feature flag is on and the network
// is testnet. The claim row, with the next free edition number, is reserved
// before signing and released again if the mint does not go out, so two
// requests at once cannot both broadcast for one identity or one edition.

import { evaluate } from "./policy.js";
import { loadHotKey, signingEnabled } from "./secrets.js";
import { signNexaMint } from "./nexa/sign.js";
import { verifyNexaChallenge } from "./nexa/message.js";
import { signBchMint } from "./bch/sign.js";
import { verifyBchChallenge } from "./bch/message.js";
import { readObservedSats, writeObservedSats } from "./balance.js";
import { policyAmount, recordLedger } from "./history.js";
import { tokenConfig } from "./setup.js";
import { turnstileOk } from "./turnstile.js";
import { editionOf, fetchCards, findCard, usableEdition, validKind, windowState } from "./cards.js";

const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");

export async function identityHash(chain, identity, eventId) {
  const raw = chain + "|" + String(identity || "").trim() + "|" + String(eventId || "").trim();
  return hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(raw)));
}

function fail(reason, extra = {}) {
  return { allow: false, reason, signed: false, broadcast: false, ...extra };
}

async function already(env, hash) {
  if (!env || !env.DB) return false;
  const row = await env.DB.prepare("SELECT 1 AS x FROM mint_claim WHERE h = ?").bind(hash).first();
  return !!row;
}

async function counts(env, chain, eventId, day) {
  if (!env || !env.DB) return { claims: new Set(), eventCounts: {}, dayCounts: {} };
  const eventRow = await env.DB.prepare("SELECT COUNT(*) AS n FROM mint_claim WHERE chain = ? AND event_id = ?").bind(chain, eventId).first();
  const dayRow = await env.DB.prepare("SELECT COUNT(*) AS n FROM mint_claim WHERE chain = ? AND day = ?").bind(chain, day).first();
  return {
    claims: new Set(),
    eventCounts: { [chain + "|" + eventId]: Number(eventRow.n) },
    dayCounts: { [chain + "|" + day]: Number(dayRow.n) },
  };
}

async function observedSats(env, chain) {
  const raw = await readObservedSats(env, chain);
  if (raw == null) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

export async function reserveEdition(db, { hash, chain, eventId, kind, day, at }) {
  // One statement picks and takes the edition. A clash on the edition index
  // (another request took that number first) tries the next one.
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      await db.prepare(
        "INSERT INTO mint_claim (h, chain, event_id, kind, edition, day, created_at) " +
        "SELECT ?, ?, ?, ?, COALESCE(MAX(edition), 0) + 1, ?, ? FROM mint_claim WHERE chain = ? AND event_id = ? AND kind = ?"
      ).bind(hash, chain, eventId, kind, day, at, chain, eventId, kind).run();
      break;
    } catch (e) {
      const msg = String(e && e.message);
      if (/mint_claim\.h\b/.test(msg) || /PRIMARY KEY/i.test(msg)) return { ok: false, reason: "identity_used" };
      if (!/UNIQUE/i.test(msg) || attempt === 2) throw e;
    }
  }
  const row = await db.prepare("SELECT edition FROM mint_claim WHERE h = ?").bind(hash).first();
  return row && row.edition ? { ok: true, edition: Number(row.edition) } : { ok: false, reason: "reserve_failed" };
}

export async function releaseEdition(db, hash) {
  await db.prepare("DELETE FROM mint_claim WHERE h = ?").bind(hash).run();
}

export async function performMint(env, body, caps, deps = {}) {
  const chain = body && body.chain;
  const eventId = body && typeof body.event_id === "string" ? body.event_id : "";
  const identity = body && typeof body.identity === "string" ? body.identity.trim() : "";
  const kind = body && body.kind;
  if (!caps[chain] || !eventId || !identity || !validKind(kind)) return fail("bad_request");
  if (chain === "bch" && caps.bch.turnstile && env && env.TURNSTILE_SECRET) {
    const gate = await (deps.verifyTurnstile || turnstileOk)(env, body.turnstile);
    if (gate === "missing") return fail("turnstile_required", { needs_funding: false });
    if (gate !== "ok") return fail("turnstile_failed", { needs_funding: false });
  }
  const now = deps.now ? deps.now() : new Date();
  const cards = await (deps.loadCards || ((e) => fetchCards(e, now.getTime())))(env);
  if (!cards) return fail("cards_unavailable", { needs_funding: false });
  const card = findCard(cards, chain, eventId, kind);
  if (!card) return fail("unknown_card", { needs_funding: false });
  const window = windowState(card, now);
  if (window !== "open") return fail("outside_window", { window, needs_funding: false });

  const hash = await identityHash(chain, identity, eventId);
  const day = now.toISOString().slice(0, 10);
  const rawSats = await observedSats(env, chain);
  const balance = policyAmount(chain, rawSats);
  const state = await counts(env, chain, eventId, day);
  if (await already(env, hash)) state.claims.add(hash);
  const decision = evaluate(caps, state, { chain, eventId, day, balance, identityHash: hash });
  if (!decision.allow) return { ...decision, signed: false, broadcast: false };
  if (!signingEnabled(env)) return { ...decision, signed: false, broadcast: false };

  const key = loadHotKey(env, chain);
  if (!key) return fail("key_missing", { status: decision.status, needs_funding: decision.needs_funding });
  const signatureOk = chain === "nexa"
    ? verifyNexaChallenge({ address: identity, eventId, signature: body.signature })
    : await verifyBchChallenge({ address: identity, eventId, signature: body.signature });
  if (!signatureOk) return fail("signature_invalid", { status: decision.status, needs_funding: false });

  if (!env || !env.DB) return fail("db_missing", { status: decision.status });
  const at = now.toISOString();
  const held = await reserveEdition(env.DB, { hash, chain, eventId, kind, day, at });
  if (!held.ok) return fail(held.reason, { status: decision.status, needs_funding: decision.needs_funding });
  const release = async (reason, extra = {}) => {
    await releaseEdition(env.DB, hash);
    return fail(reason, { status: decision.status, ...extra });
  };
  const edition = editionOf(card, held.edition);
  if (!edition) return release("editions_exhausted", { needs_funding: false });
  if (!usableEdition(chain, edition)) return release("card_invalid", { needs_funding: false });

  const fetchUtxos = deps.fetchUtxos;
  if (!fetchUtxos) return release("utxo_unavailable", { needs_funding: false });
  const utxos = await fetchUtxos(chain, key).catch(() => null);
  if (!utxos) return release("utxo_unavailable", { needs_funding: false });

  let signed;
  try {
    if (chain === "nexa") {
      const parent = await tokenConfig(env, "nexa");
      if (!parent) return release("config_missing");
      signed = signNexaMint({
        secret: key,
        recipient: identity,
        parentGroup: parent.public_id,
        zipUrl: edition.zip_url,
        zipHash: edition.zip_hash,
        authority: utxos.authority,
        funds: utxos.funds,
        airdropNexa: caps.nexa.airdrop,
        feeCeilingSats: caps.nexa.network * 100,
      });
    } else {
      const category = await tokenConfig(env, "bch");
      if (!category) return release("config_missing");
      signed = await signBchMint({
        secret: key,
        recipient: identity,
        categoryHex: category.public_id,
        commitmentHex: edition.commitment_hex,
        minting: utxos.minting,
        funding: utxos.funding,
        airdropSats: caps.bch.airdrop,
        feeCeilingSats: caps.bch.network,
      });
    }
  } catch (e) {
    return release(e.code || "sign_failed", { needs_funding: e.code === "insufficient_funds" });
  }

  const broadcast = deps.broadcast;
  if (!broadcast) return release("broadcast_unavailable");
  const sent = await broadcast(chain, signed.hex).catch((e) => ({ ok: false, error: String(e && e.message || e) }));
  if (!sent || !sent.ok) return release("broadcast_rejected", { node: sent && sent.error ? sent.error : undefined });

  const spent = chain === "nexa" ? signed.airdropSats + signed.feeSats : signed.spentSats;
  await recordLedger(env.DB, { txid: signed.txid, chain, kind: "mint", amount: spent, at, event_id: eventId });
  if (rawSats != null) await writeObservedSats(env.DB, chain, rawSats - spent, at);
  return {
    ...decision,
    signed: true,
    broadcast: true,
    txid: signed.txid,
    fee: signed.feeSats,
    kind,
    edition: held.edition,
    editions: card.editions.length,
  };
}
