// Cloudflare Turnstile check for Bitcoin Cash mints, the same siteverify call
// the tip Worker makes (tipworker/src/shouts.js). A token is only accepted when
// Cloudflare says success. A network or parse error is a refusal.

const SITEVERIFY = "https://challenges.cloudflare.com/turnstile/v0/siteverify";

export async function turnstileOk(env, token, fetcher = fetch) {
  const secret = env && env.TURNSTILE_SECRET;
  if (!secret) return "unconfigured";
  if (!token || typeof token !== "string") return "missing";
  let res;
  try {
    res = await fetcher(SITEVERIFY, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ secret, response: token.slice(0, 2048) }),
    });
  } catch {
    return "bad";
  }
  let data;
  try { data = await res.json(); } catch { return "bad"; }
  return data && data.success === true ? "ok" : "bad";
}
