// Live calendar from the content Worker (Cloudflare D1), with this site's
// static HTML and /api/v1/events.json as the fallback. Read-only. No credentials.
// window.NC_LIVE_EVENTS = {api, root, lang}
(function () {
  "use strict";
  var cfg = window.NC_LIVE_EVENTS || {};
  var list = document.getElementById("evlist");
  if (!list || !window.fetch) return;

  function get(url, ms) {
    var ctl = window.AbortController ? new AbortController() : null;
    var timer = ctl && setTimeout(function () { ctl.abort(); }, ms);
    return fetch(url, { signal: ctl && ctl.signal, credentials: "omit" }).then(function (r) {
      if (timer) clearTimeout(timer);
      if (!r.ok) throw new Error("HTTP " + r.status);
      var kind = r.headers.get("content-type") || "";
      return kind.indexOf("json") >= 0 ? r.json() : r.text();
    });
  }

  function load() {
    var live = cfg.api ? get(cfg.api.replace(/\/$/, "") + "/api/v1/events.json", 4000) : Promise.reject(new Error("no api"));
    return live.catch(function () { return get((cfg.root || "") + "api/v1/events.json", 6000); });
  }

  function label(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso || "";
    try {
      return d.toLocaleString(cfg.lang || undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    } catch (err) {
      return iso;
    }
  }

  function placeOf(ev) {
    if (ev.online && !ev.place && !ev.city) return "Online";
    var parts = [];
    if (ev.place) parts.push(ev.place);
    if (ev.city && (!ev.place || String(ev.place).indexOf(ev.city) < 0)) parts.push(ev.city);
    return parts.join(", ");
  }

  function setTime(el, ev) {
    var time = el.querySelector("time");
    if (!time) return;
    time.setAttribute("datetime", ev.start || "");
    var bold = time.querySelector("b");
    if (bold) bold.textContent = label(ev.start);
    else time.textContent = label(ev.start);
    el.setAttribute("data-start", ev.start || "");
    if (ev.end) el.setAttribute("data-end", ev.end);
  }

  function row(ev) {
    var li = document.createElement("li");
    li.id = "e-" + ev.id;
    li.setAttribute("data-c", ev.country || "");
    li.setAttribute("data-start", ev.start || "");
    li.setAttribute("data-end", ev.end || "");
    li.setAttribute("data-phase", "upcoming");
    var wrap = document.createElement("div");
    wrap.className = "evt";
    var h = document.createElement("h3");
    var a = document.createElement("a");
    a.href = (ev.url && /^https:\/\//.test(ev.url)) ? ev.url : (ev.id + "/");
    if (/^https:\/\//.test(a.href)) { a.rel = "noopener"; a.target = "_blank"; }
    a.textContent = ev.title || "";
    h.appendChild(a);
    wrap.appendChild(h);
    li.appendChild(wrap);
    var meta = document.createElement("div");
    meta.className = "meta";
    var time = document.createElement("time");
    time.setAttribute("datetime", ev.start || "");
    var b = document.createElement("b");
    b.textContent = label(ev.start);
    time.appendChild(b);
    meta.appendChild(time);
    var where = placeOf(ev);
    if (where) meta.appendChild(document.createTextNode(" · " + where));
    li.appendChild(meta);
    return li;
  }

  load().then(function (doc) {
    var events = (doc && doc.events) || [];
    events.forEach(function (ev) {
      if (!ev || !ev.id || !ev.start || (ev.status && ev.status !== "published")) return;
      var el = document.getElementById("e-" + ev.id);
      if (el) setTime(el, ev);
      else if (new Date(ev.start).getTime() >= Date.now() - 86400000) list.appendChild(row(ev));
    });
    var ics = document.querySelector("[data-live-ics]");
    if (ics && cfg.api) {
      var href = cfg.api.replace(/\/$/, "") + "/api/v1/events.ics";
      get(href, 4000).then(function () { ics.setAttribute("href", href); }).catch(function () {});
    }
  }).catch(function () { /* keep the static page */ });
})();
