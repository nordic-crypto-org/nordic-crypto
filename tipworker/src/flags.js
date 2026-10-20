// App feature flags. Unknown or missing keys are off.
//   GET /api/flags              public -> {"nft":{"ios":false}}
//   GET /api/admin/flags        (admin session) -> {ok, flags:{nft_ios}}
//   POST /api/admin/flags       (admin session) {nft_ios:bool}
export const FLAGS = ["nft_ios"];

export async function readFlags(env) {
  const out = Object.fromEntries(FLAGS.map((k) => [k, false]));
  try {
    const rows = (await env.DB.prepare("SELECT key, enabled FROM app_flags").all()).results || [];
    for (const r of rows) if (FLAGS.includes(r.key)) out[r.key] = r.enabled === 1;
  } catch { /* table missing: all off */ }
  return out;
}

export async function writeFlags(env, f, email) {
  const keys = Object.keys(f || {});
  if (!keys.length || !keys.every((k) => FLAGS.includes(k) && typeof f[k] === "boolean")) return false;
  const at = new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00");
  await env.DB.batch(keys.map((k) => env.DB.prepare(
    "INSERT INTO app_flags (key, enabled, updated_at, updated_by) VALUES (?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET enabled = excluded.enabled, updated_at = excluded.updated_at, updated_by = excluded.updated_by")
    .bind(k, f[k] ? 1 : 0, at, email)));
  return true;
}

export async function publicFlags(env) {
  const f = await readFlags(env);
  return new Response(JSON.stringify({ nft: { ios: f.nft_ios } }), { status: 200, headers: {
    "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=60",
    "Access-Control-Allow-Origin": "*", "X-Content-Type-Options": "nosniff" } });
}
