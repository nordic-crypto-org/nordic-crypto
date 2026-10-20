// The card index the site build publishes at /assets/nft/cards.json.
// The Worker mints only what is listed there: the event, the kind, the time
// window and one entry per numbered edition (a Nexa zip and its hash, or a
// Bitcoin Cash commitment). Nothing about the card comes from the request.
//
// Every edition is a different zip with a different image, so no two minted
// NFTs are the same token. The edition number is public; the holder is not.

const DEFAULT_URL = "https://nordiccrypto.no/assets/nft/cards.json";
const TTL_MS = 5 * 60 * 1000;
const KINDS = new Set(["pre", "ongoing"]);

let cached = null;

export function resetCardCache() {
  cached = null;
}

export async function fetchCards(env, nowMs = Date.now(), fetcher = fetch) {
  const url = (env && env.CARD_INDEX_URL) || DEFAULT_URL;
  if (cached && cached.url === url && nowMs - cached.at < TTL_MS) return cached.doc;
  let doc = null;
  try {
    const res = await fetcher(url, { cf: { cacheTtl: 60 } });
    if (res.ok) doc = await res.json();
  } catch {
    doc = null;
  }
  if (!doc || !Array.isArray(doc.cards)) return cached && cached.url === url ? cached.doc : null;
  cached = { url, at: nowMs, doc };
  return doc;
}

export function validKind(kind) {
  return KINDS.has(kind);
}

export function findCard(doc, chain, eventId, kind) {
  if (!doc || !Array.isArray(doc.cards)) return null;
  return doc.cards.find((c) => c && c.chain === chain && c.event_id === eventId && c.kind === kind) || null;
}

// "pre" runs until the start. "ongoing" runs from the start to the end,
// both instants included, the same rule as tools/event_select.phase.
export function windowState(card, now) {
  const t = now.getTime();
  const from = card.window && card.window.from ? Date.parse(card.window.from) : null;
  const to = card.window && card.window.to ? Date.parse(card.window.to) : null;
  if (to == null || Number.isNaN(to)) return "closed";
  if (from != null && !Number.isNaN(from) && t < from) return "not_yet";
  if (t > to) return "closed";
  return "open";
}

export function editionOf(card, n) {
  if (!card || !Array.isArray(card.editions)) return null;
  return card.editions.find((e) => e && e.n === n) || null;
}

const ZIP_PREFIX = "https://nordiccrypto.no/assets/nft/";
const HEX64 = /^[0-9a-f]{64}$/;

// A malformed index row is refused rather than signed.
export function usableEdition(chain, edition) {
  if (!edition) return false;
  if (chain === "nexa") {
    return typeof edition.zip_url === "string" && edition.zip_url.startsWith(ZIP_PREFIX)
      && edition.zip_url.endsWith(".zip") && HEX64.test(String(edition.zip_hash || ""));
  }
  return HEX64.test(String(edition.commitment_hex || ""));
}
