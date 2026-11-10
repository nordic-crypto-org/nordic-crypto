// iCal for approved events. Same fields as tools/event_ics.py.
// Contact details are removed before a line is written.

const PRODID = "-//Nordic Crypto//Calendar//EN";

export function redactText(value) {
  if (typeof value !== "string" || !value) return value;
  let text = value.replace(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g, "");
  text = text.replace(/\+?\d[\d\s().-]{7,}\d/g, (raw) => {
    if (!/[+()\s]/.test(raw)) return raw;
    const digits = raw.replace(/\D/g, "");
    return digits.length >= 8 && digits.length <= 15 ? "" : raw;
  });
  return text.replace(/[ \t]{2,}/g, " ").trim();
}

function stamp(value) {
  const when = new Date(value);
  if (Number.isNaN(when.getTime())) return "";
  const y = when.getUTCFullYear();
  const m = String(when.getUTCMonth() + 1).padStart(2, "0");
  const d = String(when.getUTCDate()).padStart(2, "0");
  const h = String(when.getUTCHours()).padStart(2, "0");
  const min = String(when.getUTCMinutes()).padStart(2, "0");
  const s = String(when.getUTCSeconds()).padStart(2, "0");
  return `${y}${m}${d}T${h}${min}${s}Z`;
}

function escapeText(value) {
  return redactText(String(value || ""))
    .replace(/\\/g, "\\\\")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/\n/g, "\\n")
    .replace(/,/g, "\\,")
    .replace(/;/g, "\\;");
}

function fold(line) {
  const raw = new TextEncoder().encode(line);
  if (raw.length <= 75) return line;
  const parts = [];
  let offset = 0;
  while (offset < raw.length) {
    const limit = parts.length ? 74 : 75;
    let cut = Math.min(limit, raw.length - offset);
    while (cut > 0 && (raw[offset + cut] & 0xc0) === 0x80) cut -= 1;
    // Keep a TEXT escape (backslash + the next byte) on one physical line.
    if (cut > 1 && raw[offset + cut - 1] === 0x5c) cut -= 1;
    if (cut <= 0) cut = 1;
    const piece = new TextDecoder().decode(raw.slice(offset, offset + cut));
    parts.push((parts.length ? " " : "") + piece);
    offset += cut;
  }
  return parts.join("\r\n");
}

// A URI property value is written raw, so it must not carry anything that
// could end the content line: no whitespace, controls or Unicode line breaks.
const URI = /^https:\/\/[^\s\x00-\x1f\x7f-\x9f\u2028\u2029]+$/;

function uriValue(value) {
  return typeof value === "string" && URI.test(value) ? value : "";
}

function httpsUrl(value) {
  if (typeof value !== "string") return "";
  const text = value.trim();
  return text.startsWith("https://") ? text : "";
}

function locationOf(event) {
  const place = typeof event.place === "string" ? event.place.trim() : "";
  const city = typeof event.city === "string" ? event.city.trim() : "";
  if (event.online && !place && !city) return "Online";
  const parts = [];
  if (place) parts.push(place);
  if (city && !parts.includes(city)) parts.push(city);
  if (event.online && parts.length && parts[0].toLowerCase().indexOf("online") < 0) parts.push("Online");
  return parts.join(", ");
}

function descriptionOf(event, address) {
  const note = redactText(event.note || "") || "";
  const parts = note ? [note] : [];
  const link = httpsUrl(event.map_url);
  if (link && address && note.indexOf(link) < 0) parts.push(link);
  return parts.join("\n");
}

export function eventsToIcs(events, now) {
  const stampNow = stamp(now || new Date().toISOString());
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:" + PRODID,
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Nordic Crypto",
  ];
  const rows = (events || [])
    .filter((event) => event && event.id && event.start && event.title)
    .slice()
    .sort((a, b) => String(a.start).localeCompare(String(b.start)) || String(a.id).localeCompare(String(b.id)));
  for (const event of rows) {
    const start = stamp(event.start);
    if (!start) continue;
    lines.push("BEGIN:VEVENT");
    lines.push("UID:" + String(event.id).replace(/[^A-Za-z0-9]/g, "") + "@nordiccrypto.no");
    lines.push("DTSTAMP:" + stampNow);
    lines.push("DTSTART:" + start);
    if (event.end && stamp(event.end)) lines.push("DTEND:" + stamp(event.end));
    lines.push("SUMMARY:" + escapeText(event.title));
    const address = locationOf(event);
    const loc = address || httpsUrl(event.map_url);
    if (loc) lines.push("LOCATION:" + escapeText(loc));
    const url = uriValue(event.url);
    if (url) lines.push("URL:" + url);
    const desc = descriptionOf(event, address);
    if (desc) lines.push("DESCRIPTION:" + escapeText(desc));
    lines.push("END:VEVENT");
  }
  lines.push("END:VCALENDAR");
  return lines.map(fold).join("\r\n") + "\r\n";
}
