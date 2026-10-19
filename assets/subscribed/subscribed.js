(function () {
  "use strict";
  var D = document, W = window, root = D.documentElement;
  var RM = W.matchMedia && W.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var cfg = {}; try { cfg = JSON.parse(D.getElementById("sub-cfg").textContent); } catch (e) {}
  var lang = root.lang || "en";
  function graphemes(s) {
    if (W.Intl && Intl.Segmenter) return Array.from(new Intl.Segmenter(lang, { granularity: "grapheme" }).segment(s), function (x) { return x.segment; });
    return Array.from(s);
  }

  /* next issue: Monday about 08:30 Oslo time */
  function osloParts(d) {
    var o = {};
    new Intl.DateTimeFormat("en-US", { timeZone: "Europe/Oslo", hourCycle: "h23", year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric", second: "numeric", weekday: "short" })
      .formatToParts(d).forEach(function (p) { o[p.type] = p.value; });
    return o;
  }
  function osloOffset(d) {
    var p = osloParts(d);
    return Date.UTC(+p.year, p.month - 1, +p.day, +p.hour, +p.minute, +p.second) - Math.floor(d.getTime() / 1000) * 1000;
  }
  function nextIssue(now) {
    try {
      var p = osloParts(now), dow = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(p.weekday);
      var ahead = (8 - dow) % 7;
      if (ahead === 0 && (+p.hour * 60 + +p.minute) >= 510) ahead = 7;
      var wall = Date.UTC(+p.year, p.month - 1, +p.day + ahead, 8, 30);
      var t = wall - osloOffset(now);
      return t - (osloOffset(new Date(t)) - osloOffset(now));
    } catch (e) {
      var n = new Date(now); n.setDate(n.getDate() + ((8 - n.getDay()) % 7 || 7)); n.setHours(8, 30, 0, 0); return n.getTime();
    }
  }
  var cdEls = {}; [].forEach.call(D.querySelectorAll("#cd [data-u]"), function (b) { cdEls[b.getAttribute("data-u")] = b; });
  var target = nextIssue(new Date());
  function tick() {
    var ms = target - Date.now();
    if (ms < 0) { target = nextIssue(new Date(Date.now() + 60000)); ms = target - Date.now(); }
    var s = Math.floor(ms / 1000), v = { d: Math.floor(s / 86400), h: Math.floor(s / 3600) % 24, m: Math.floor(s / 60) % 60, s: s % 60 };
    for (var k in v) {
      var el = cdEls[k]; if (!el) continue;
      var txt = (v[k] < 10 ? "0" : "") + v[k];
      if (el.textContent !== txt) {
        el.textContent = txt;
        if (!RM) { el.classList.remove("flip"); void el.offsetWidth; el.classList.add("flip"); }
      }
    }
  }
  tick(); setInterval(tick, 1000);

  if (RM) return;   /* calm version: static sky, everything visible, countdown in plain digits */
  clearTimeout(W.__ncF);
  root.classList.add("go");

  /* kinetic headline */
  var kin = D.querySelector(".kin-a");
  if (kin) {
    var txt = kin.textContent, bits = /[\u0590-\u08FF\u0900-\u0DFF\uFB1D-\uFEFC]/.test(txt) ? txt.split(/(\s+)/) : graphemes(txt);
    kin.textContent = "";
    bits.forEach(function (ch, i) {
      if (!ch) return;
      var s = D.createElement("span"); s.className = "ch"; s.style.setProperty("--i", i); s.textContent = ch; kin.appendChild(s);
    });
  }

  /* reveal on scroll */
  var rev = D.querySelectorAll(".card,.stats,.cta,.foot");
  function countUp(el) {
    var to = +el.getAttribute("data-count") || 0, t0 = performance.now();
    (function f(now) {
      var k = Math.min(1, (now - t0) / 1600), e = k === 1 ? 1 : 1 - Math.pow(2, -10 * k);
      el.textContent = Math.round(to * e); if (k < 1) requestAnimationFrame(f);
    })(t0);
  }
  function show(el) {
    if (el.classList.contains("in")) return;
    el.classList.add("in");
    [].forEach.call(el.querySelectorAll("[data-count]"), countUp);
  }
  if ("IntersectionObserver" in W) {
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { show(e.target); io.unobserve(e.target); } }); }, { threshold: 0.15 });
    setTimeout(function () { [].forEach.call(rev, function (el) { io.observe(el); }); }, 3200);
  } else setTimeout(function () { [].forEach.call(rev, show); }, 3200);

  /* typewriter of what arrives each week */
  var tw = D.getElementById("tw"), lines = (cfg.type || []).map(graphemes), li = 0, ci = 0, del = false;
  function type() {
    if (!tw || !lines.length) return;
    var g = lines[li], wait = del ? 16 : 34;
    if (!del) { ci++; if (ci >= g.length) { del = true; wait = 1900; } }
    else { ci--; if (ci <= 0) { del = false; li = (li + 1) % lines.length; wait = 350; } }
    tw.textContent = g.slice(0, ci).join("");
    setTimeout(type, wait);
  }
  setTimeout(type, 3300);

  /* canvases */
  var sky = D.getElementById("sky"), fx = D.getElementById("fx");
  if (!sky || !sky.getContext) return;
  var sc = sky.getContext("2d"), fc = fx.getContext("2d");
  var aur = D.createElement("canvas"), ac = aur.getContext("2d");
  var Wd = 0, Ht = 0, dpr = 1, nodes = [], stars = [], pulses = [], parts = [], boost = 0, pointer = { x: -1e4, y: -1e4 };
  var small = W.innerWidth < 600;
  function rnd(a, b) { return a + Math.random() * (b - a); }
  function size() {
    Wd = W.innerWidth; Ht = W.innerHeight; dpr = Math.min(W.devicePixelRatio || 1, small ? 1.5 : 2);
    [sky, fx].forEach(function (c) { c.width = Math.round(Wd * dpr); c.height = Math.round(Ht * dpr); });
    sc.setTransform(dpr, 0, 0, dpr, 0, 0); fc.setTransform(dpr, 0, 0, dpr, 0, 0);
    aur.width = Math.max(180, Math.round(Wd / 6)); aur.height = Math.round(aur.width * Ht / Wd);
    var n = Math.max(16, Math.min(56, Math.round(Wd * Ht / 26000)));
    while (nodes.length < n) nodes.push({ x: rnd(0, Wd), y: rnd(0, Ht), vx: rnd(-12, 12), vy: rnd(-12, 12), f: 0, r: rnd(1.4, 2.6) });
    nodes.length = n;
    stars = []; for (var i = 0; i < (small ? 70 : 140); i++) stars.push({ x: rnd(0, Wd), y: rnd(0, Ht * 0.75), r: rnd(0.3, 1.2), p: rnd(0, 6.3), s: rnd(0.6, 2) });
  }
  size(); W.addEventListener("resize", size);
  W.addEventListener("pointermove", function (e) { pointer.x = e.clientX; pointer.y = e.clientY; }, { passive: true });
  W.addEventListener("pointerleave", function () { pointer.x = pointer.y = -1e4; });

  var bands = [
    { c: [64, 224, 160], y: 0.06, a: 0.08, f: 2.1, s: 0.13, h: 0.30, o: 0 },
    { c: [43, 190, 175], y: 0.00, a: 0.07, f: 3.3, s: -0.09, h: 0.24, o: 2 },
    { c: [140, 110, 220], y: -0.06, a: 0.05, f: 1.6, s: 0.07, h: 0.16, o: 4 },
    { c: [217, 160, 52], y: 0.12, a: 0.04, f: 2.7, s: 0.11, h: 0.10, o: 1 }
  ];
  function drawAurora(t) {
    var w = aur.width, h = aur.height;
    ac.clearRect(0, 0, w, h);
    ac.globalCompositeOperation = "lighter";
    bands.forEach(function (b) {
      var H = b.h * Math.min(h, aur.width * 0.9), g = ac.createLinearGradient(0, 0, 0, -H), c = b.c.join(",");
      g.addColorStop(0, "rgba(" + c + ",0)"); g.addColorStop(0.08, "rgba(" + c + ",.9)"); g.addColorStop(0.35, "rgba(" + c + ",.35)"); g.addColorStop(1, "rgba(" + c + ",0)");
      ac.fillStyle = g;
      for (var x = 0; x < w; x++) {
        var u = x / w, y = h * (b.y + 0.18) + Math.sin(u * b.f * 6.28 + t * b.s * 6 + b.o) * b.a * h + Math.sin(u * 13 - t * 0.7 + b.o) * 0.015 * h;
        var ray = 0.55 + 0.45 * Math.sin(x * 0.35 + t * 1.3 + b.o) * Math.sin(x * 0.11 - t * 0.6);
        ac.globalAlpha = Math.max(0, Math.min(1, (0.16 + 0.36 * ray) * (0.7 + boost)));
        ac.setTransform(1, 0, 0, 1, x, y); ac.fillRect(0, -H, 1.5, H);
      }
      ac.setTransform(1, 0, 0, 1, 0, 0);
    });
    ac.globalAlpha = 1; ac.globalCompositeOperation = "source-over";
  }

  var last = 0, raf = 0, t0 = performance.now(), linkD = small ? 110 : 150;
  function frame(now) {
    raf = requestAnimationFrame(frame);
    var dt = Math.min(0.05, (now - (last || now)) / 1000); last = now;
    var t = (now - t0) / 1000;
    boost *= Math.pow(0.4, dt);
    sc.clearRect(0, 0, Wd, Ht);
    drawAurora(t);
    sc.imageSmoothingEnabled = true; sc.globalAlpha = 0.95; sc.drawImage(aur, 0, 0, Wd, Ht); sc.globalAlpha = 1;
    stars.forEach(function (s) {
      sc.globalAlpha = 0.35 + 0.65 * Math.abs(Math.sin(s.p + t * s.s));
      sc.fillStyle = "#fff"; sc.fillRect(s.x, s.y, s.r * 2, s.r * 2);
    });
    sc.globalAlpha = 1;
    var i, j, a, b, dx, dy, d;
    for (i = 0; i < nodes.length; i++) {
      a = nodes[i];
      dx = pointer.x - a.x; dy = pointer.y - a.y; d = dx * dx + dy * dy;
      if (d < 40000) { a.vx += dx * 0.0009; a.vy += dy * 0.0009; }
      a.vx *= 0.995; a.vy *= 0.995;
      var sp = Math.hypot(a.vx, a.vy); if (sp > 40) { a.vx *= 40 / sp; a.vy *= 40 / sp; } if (sp < 4) { a.vx += rnd(-2, 2); a.vy += rnd(-2, 2); }
      a.x += a.vx * dt; a.y += a.vy * dt;
      if (a.x < -20) a.x = Wd + 20; if (a.x > Wd + 20) a.x = -20; if (a.y < -20) a.y = Ht + 20; if (a.y > Ht + 20) a.y = -20;
      a.f *= Math.pow(0.1, dt);
    }
    sc.lineWidth = 1;
    var links = [];
    for (i = 0; i < nodes.length; i++) for (j = i + 1; j < nodes.length; j++) {
      a = nodes[i]; b = nodes[j]; dx = a.x - b.x; dy = a.y - b.y; d = Math.sqrt(dx * dx + dy * dy);
      if (d < linkD) {
        links.push([i, j]);
        sc.strokeStyle = "rgba(160,220,210," + (0.22 * (1 - d / linkD)).toFixed(3) + ")";
        sc.beginPath(); sc.moveTo(a.x, a.y); sc.lineTo(b.x, b.y); sc.stroke();
      }
    }
    if (links.length && Math.random() < dt * (2.5 + boost * 8)) {
      var L = links[(Math.random() * links.length) | 0]; pulses.push({ a: L[0], b: L[1], k: 0 });
    }
    for (i = pulses.length - 1; i >= 0; i--) {
      var p = pulses[i]; p.k += dt * 1.4; a = nodes[p.a]; b = nodes[p.b];
      if (p.k >= 1) { b.f = 1; pulses.splice(i, 1); if (Math.random() < 0.55) { var nb = links.filter(function (l) { return l[0] === p.b || l[1] === p.b; }); if (nb.length && pulses.length < 30) { var q = nb[(Math.random() * nb.length) | 0]; pulses.push({ a: p.b, b: q[0] === p.b ? q[1] : q[0], k: 0 }); } } continue; }
      var x = a.x + (b.x - a.x) * p.k, y = a.y + (b.y - a.y) * p.k;
      sc.fillStyle = "rgba(243,210,122,.95)"; sc.beginPath(); sc.arc(x, y, 2.2, 0, 6.283); sc.fill();
      sc.fillStyle = "rgba(243,210,122,.18)"; sc.beginPath(); sc.arc(x, y, 7, 0, 6.283); sc.fill();
    }
    for (i = 0; i < nodes.length; i++) {
      a = nodes[i];
      sc.fillStyle = a.f > 0.05 ? "rgba(243,210,122," + (0.5 + a.f * 0.5) + ")" : "rgba(200,235,228,.7)";
      sc.beginPath(); sc.arc(a.x, a.y, a.r + a.f * 3, 0, 6.283); sc.fill();
      if (a.f > 0.05) { sc.fillStyle = "rgba(243,210,122," + (a.f * 0.25) + ")"; sc.beginPath(); sc.arc(a.x, a.y, 6 + a.f * 12, 0, 6.283); sc.fill(); }
    }
    drawFx(dt);
  }

  /* coins and confetti */
  var KEY = "M32 8.5A8.5 8.5 0 0 1 32 25.5L32 20.8A3.8 3.8 0 0 0 32 13.2ZM32 24H35.4V49H32ZM35.4 36.5H45V41H40.5V44.5H45V49H35.4ZM32 8.5A8.5 8.5 0 0 0 32 25.5L32 20.8A3.8 3.8 0 0 1 32 13.2ZM28.6 24H32V49H28.6Z";
  function coinSprite(dark) {
    var c = D.createElement("canvas"), x = c.getContext("2d"), R = 32; c.width = c.height = R * 2;
    var g = x.createRadialGradient(R * 0.7, R * 0.6, 2, R, R, R);
    if (dark) { g.addColorStop(0, "#C99232"); g.addColorStop(1, "#7A5414"); } else { g.addColorStop(0, "#FFF1C2"); g.addColorStop(0.45, "#F3C95E"); g.addColorStop(1, "#B9821F"); }
    x.fillStyle = g; x.beginPath(); x.arc(R, R, R - 1, 0, 6.283); x.fill();
    x.strokeStyle = dark ? "#5E3F0C" : "#9C6A15"; x.lineWidth = 3; x.beginPath(); x.arc(R, R, R - 6, 0, 6.283); x.stroke();
    if (!dark && W.Path2D) { x.save(); x.translate(R - 21, R - 22); x.scale(0.9, 0.9); x.translate(-10, 2); x.fillStyle = "#1E3A45"; x.fill(new Path2D(KEY)); x.restore(); }
    return c;
  }
  var COIN = coinSprite(false), COINB = coinSprite(true);
  var CONF = ["#D9A034", "#F3D27A", "#4FD1C5", "#40E0A0", "#FFFFFF", "#8C6EDC"];
  function burst(x, y, n) {
    var k = small ? 0.6 : 1;
    for (var i = 0; i < n * k; i++) {
      var ang = rnd(-Math.PI, 0) + rnd(-0.3, 0.3), v = rnd(320, 900), coin = Math.random() < 0.45;
      parts.push({ x: x, y: y, vx: Math.cos(ang) * v * rnd(0.6, 1.1), vy: Math.sin(ang) * v, rot: rnd(0, 6.28), vr: rnd(-8, 8), sp: rnd(0, 6.28), vs: rnd(6, 16),
        s: coin ? rnd(9, 16) : rnd(5, 9), coin: coin, c: CONF[(Math.random() * CONF.length) | 0], life: 0 });
    }
    boost = Math.min(1.4, boost + 1);
    nodes.forEach(function (a) { var dx = a.x - x, dy = a.y - y, d = Math.hypot(dx, dy) || 1; if (d < 380) { a.vx += dx / d * 90; a.vy += dy / d * 90; a.f = 1; } });
  }
  var rainUntil = 0;
  function drawFx(dt) {
    fc.clearRect(0, 0, Wd, Ht);
    if (performance.now() < rainUntil && Math.random() < dt * (small ? 6 : 12))
      parts.push({ x: rnd(0, Wd), y: -20, vx: rnd(-30, 30), vy: rnd(40, 120), rot: 0, vr: rnd(-2, 2), sp: rnd(0, 6.28), vs: rnd(4, 9), s: rnd(7, 12), coin: true, life: 0, rain: true });
    for (var i = parts.length - 1; i >= 0; i--) {
      var p = parts[i];
      p.life += dt;
      var drag = p.coin ? 0.6 : 2.6;
      p.vx -= p.vx * drag * dt; p.vy += (p.coin ? 980 : 520) * dt - p.vy * drag * dt * (p.coin ? 0.3 : 1);
      if (!p.coin) p.vx += Math.sin(p.life * 5 + p.sp) * 30 * dt;
      p.x += p.vx * dt; p.y += p.vy * dt; p.rot += p.vr * dt; p.sp += p.vs * dt;
      if (p.y > Ht + 40 || p.life > 9) { parts.splice(i, 1); continue; }
      var sx = Math.cos(p.sp);
      fc.save(); fc.translate(p.x, p.y); fc.rotate(p.rot);
      if (p.coin) { fc.scale(Math.max(0.08, Math.abs(sx)), 1); fc.drawImage(sx >= 0 ? COIN : COINB, -p.s, -p.s, p.s * 2, p.s * 2); }
      else { fc.scale(1, sx); fc.fillStyle = p.c; fc.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2); }
      fc.restore();
    }
  }
  var emblem = D.querySelector(".emblem"), shield = D.querySelector(".shield"), again = D.getElementById("again");
  function center() { var r = emblem.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height * 0.45]; }
  function replay(sel) { [].forEach.call(D.querySelectorAll(sel), function (el) { el.style.animation = "none"; void el.getBoundingClientRect(); el.style.animation = ""; }); }
  function celebrate(rain) {
    var c = center(); burst(c[0], c[1], 150);
    setTimeout(function () { var c2 = center(); burst(c2[0] - 120, c2[1] + 40, 50); burst(c2[0] + 120, c2[1] + 40, 50); }, 260);
    if (rain) rainUntil = performance.now() + 5500;
  }
  setTimeout(function () { celebrate(true); if (again) again.hidden = false; }, 2050);
  if (again) again.addEventListener("click", function () { replay(".ring,.sh-glint"); celebrate(true); });
  if (emblem) {
    emblem.addEventListener("click", function (e) { burst(e.clientX, e.clientY, 60); replay(".ring"); });
    W.addEventListener("pointermove", function (e) {
      if (e.pointerType !== "mouse") return;
      var r = emblem.getBoundingClientRect(), rx = (e.clientY - (r.top + r.height / 2)) / Ht, ry = (e.clientX - (r.left + r.width / 2)) / Wd;
      shield.style.transform = "rotateX(" + (-rx * 22).toFixed(2) + "deg) rotateY(" + (ry * 28).toFixed(2) + "deg)";
    }, { passive: true });
  }
  function start() { if (!raf) { last = 0; raf = requestAnimationFrame(frame); } }
  function stop() { cancelAnimationFrame(raf); raf = 0; }
  D.addEventListener("visibilitychange", function () { if (D.hidden) stop(); else start(); });
  start();
})();
