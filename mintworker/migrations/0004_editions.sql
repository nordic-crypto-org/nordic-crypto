-- Numbered editions. Every mint takes the next free edition of its card, so
-- each minted NFT is a different token with its own image. The row is reserved
-- before signing and deleted if the mint does not go out.
-- Still no raw NexaID, no raw address and no txid on this row.

ALTER TABLE mint_claim ADD COLUMN kind TEXT;
ALTER TABLE mint_claim ADD COLUMN edition INTEGER;

CREATE UNIQUE INDEX mint_claim_edition ON mint_claim (chain, event_id, kind, edition);
