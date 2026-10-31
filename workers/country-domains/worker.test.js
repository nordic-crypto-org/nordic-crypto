// node --test workers/country-domains/  (pure routing and link mapping; HTMLRewriter is only used at runtime)
import test from "node:test";
import assert from "node:assert/strict";
import worker, { route, mapUrl, toCountryPath } from "./worker.js";

test("routing on nordiccrypto.se", () => {
  assert.deepEqual(route("/", "sv", ""), { origin: "/sv/" });
  assert.deepEqual(route("/", "sv", "nc_lang=sv"), { origin: "/sv/" });
  assert.deepEqual(route("/", "sv", "a=1; nc_lang=en"), { redirect: "/en/", status: 302 });
  assert.deepEqual(route("/", "sv", "nc_lang=da"), { redirect: "/da/", status: 302 });
  assert.deepEqual(route("/sv/", "sv", ""), { redirect: "/", status: 301 });
  assert.deepEqual(route("/en/", "sv", ""), { origin: "/", english: true });
  assert.deepEqual(route("/en/sv/", "sv", ""), { redirect: "/", status: 302 });
  assert.deepEqual(route("/sv/about/", "sv", ""), { origin: "/sv/about/" });
  assert.deepEqual(route("/api/v1/news.json", "sv", ""), { origin: "/api/v1/news.json" });
});

test("link mapping keeps readers on the country domain", () => {
  const page = "https://nordiccrypto.no/sv/";
  assert.equal(mapUrl("../", page, "sv"), "/en/");
  assert.equal(mapUrl("../sv/", page, "sv"), "/");
  assert.equal(mapUrl("stories/abc/", page, "sv"), "/sv/stories/abc/");
  assert.equal(mapUrl("../assets/x.webp", page, "sv"), "/assets/x.webp");
  assert.equal(mapUrl("https://nordiccrypto.no/da/", page, "sv"), "/da/");
  assert.equal(mapUrl("https://x.com/nordiccryptobot", page, "sv"), null);
  assert.equal(mapUrl("#top", page, "sv"), null);
  assert.equal(mapUrl("mailto:a@b.c", page, "sv"), null);
  assert.equal(toCountryPath("/fi/index.html", "fi"), "/");
});

test("proxied requests always go to nordiccrypto.no", async () => {
  const seen = [];
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (u) => { seen.push(new URL(u)); return new Response("ok", { headers: { "Content-Type": "text/plain" } }); };
  try {
    for (const path of ["/about/", "//example.com/x", "/\\example.com/x", "//example.com", "/%2F%2Fexample.com/x"]) {
      await worker.fetch(new Request(`https://nordiccrypto.se${path}?q=1`));
    }
  } finally {
    globalThis.fetch = realFetch;
  }
  assert.equal(seen.length, 5);
  for (const u of seen) assert.equal(u.origin, "https://nordiccrypto.no");
  assert.equal(seen[0].pathname + seen[0].search, "/about/?q=1");
});
