// Shared test fixtures: a card index like the one the site build publishes,
// and an in-memory stand-in for the mint_claim table.

export const NOW = "2026-10-07T12:00:00.000Z";

export function testCards({ from = "2026-10-07T10:00:00Z", to = "2026-10-07T14:00:00Z", editions = 3 } = {}) {
  const hex = (n, c) => (c + n.toString(16).padStart(2, "0")).repeat(32).slice(0, 64);
  const cards = [];
  for (const kind of ["pre", "ongoing"]) {
    const window = kind === "pre" ? { from: null, to: from } : { from, to };
    cards.push({
      chain: "nexa", event_id: "evt", kind, window,
      editions: Array.from({ length: editions }, (_, i) => ({
        n: i + 1,
        zip_url: `https://nordiccrypto.no/assets/nft/evt-${kind}-nexa-${String(i + 1).padStart(3, "0")}.zip`,
        zip_hash: hex(i + 1, "c"),
      })),
    });
    cards.push({
      chain: "bch", event_id: "evt", kind, window,
      editions: Array.from({ length: editions }, (_, i) => ({ n: i + 1, commitment_hex: hex(i + 1, "b") })),
    });
  }
  return { version: 1, cards };
}

export const loadTestCards = async () => testCards();

export function claimTable() {
  const rows = [];
  return {
    rows,
    first(sql, args) {
      if (!sql.includes("mint_claim WHERE h")) return undefined;
      const row = rows.find((r) => r.h === args[0]);
      if (!row) return null;
      return sql.includes("SELECT edition") ? { edition: row.edition } : { x: 1 };
    },
    run(sql, args) {
      if (sql.startsWith("INSERT INTO mint_claim")) {
        if (rows.some((r) => r.h === args[0])) throw new Error("UNIQUE constraint failed: mint_claim.h");
        const [h, chain, event_id, kind, day, created_at] = args;
        const taken = rows.filter((r) => r.chain === chain && r.event_id === event_id && r.kind === kind);
        const edition = taken.reduce((m, r) => Math.max(m, r.edition), 0) + 1;
        rows.push({ h, chain, event_id, kind, edition, day, created_at });
        return true;
      }
      if (sql.startsWith("DELETE FROM mint_claim")) {
        const i = rows.findIndex((r) => r.h === args[0]);
        if (i >= 0) rows.splice(i, 1);
        return true;
      }
      return undefined;
    },
  };
}
