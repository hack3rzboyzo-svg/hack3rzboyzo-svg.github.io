// Cloudflare Worker for the suggestion boxes + arcade boards.
//
// movs.html → POST { text, hints }
// hidden.html → POST { text, page:"hidden", hints }
// GET ?page=hidden&limit=&since=
// GET ?stats=1
// GET /scores?game=X
// POST /scores { game, score, name }
// POST /wipe { token }
// GET /ping
// POST /start
//
// Metadata is captured server-side from request.cf
// public file and KV unless SHOW_IP=0. A salted hash is always written too.
//
// Bindings required:
// GITHUB_TOKEN secret, fine-grained, this repo only, Contents+Issues RW
// IP_SALT secret, any long random string
// LOG KV namespace (rate limits, counters, metadata log)
// SCORES KV namespace (arcade boards — separate from LOG)
// Optional: SHOW_IP=0 to hide raw IPs, HOME_LAT/HOME_LON for distance,
// REVERSE_GEO=1 for Nominatim lookups.

const VERSION = "v7";

const OWNER = "hack3rzboyzo-svg";
const REPO = "hack3rzboyzo-svg.github.io";
const ISSUE_LABEL = "suggestion";
const FILE_PATH = "suggestions.json";
const ALLOWED_ORIGIN = "https://hack3rzboyzo-svg.github.io";
const DEV_ORIGINS = new Set([
  ALLOWED_ORIGIN,
  "http://localhost:8000",
  "http://127.0.0.1:8000",
  "null"
]);
const MAX_LENGTH = 500;
const MAX_ENTRIES = 300; // oldest are dropped past this
const RATE_LIMIT = 8;
const RATE_TTL = 3600;

const GAMES = ["stack", "smash", "muncher", "hell", "arena"];
const GAME_RE = /^[a-z0-9_-]{2,16}$/;
const validGame = g => GAMES.includes(g) || GAME_RE.test(String(g || ""));

const WIPE_AT = 50000, MAX_SCORE = 5000000, TOP = 25;
const SCORE_WINDOW = 1200; // ms between accepted submits per game+IP
const lastHit = new Map();

const GH = `https://api.github.com/repos/${OWNER}/${REPO}`;

const WEATHER = {0:"clear",1:"mostly clear",2:"partly cloudy",3:"overcast",45:"fog",48:"freezing fog",51:"light drizzle",53:"drizzle",55:"heavy drizzle",61:"light rain",63:"rain",65:"heavy rain",71:"light snow",73:"snow",75:"heavy snow",77:"snow grains",80:"showers",81:"showers",82:"violent showers",85:"snow showers",86:"heavy snow showers",95:"thunderstorm",96:"thunderstorm + hail",99:"thunderstorm + heavy hail"};
const COMPASS = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"];

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get("Origin");
    const out = (status, data, extra) => cors(status, data, origin, extra);

    if (request.method === "OPTIONS") return out(204, null);

    try {
      return await handle(request, env, ctx, out);
    } catch (e) {
      // guarantees CORS headers even on a hard failure
      return out(500, { ok: false, error: "worker exception", detail: String((e && e.message) || e) });
    }
  }
};

async function handle(request, env, ctx, out) {
  const url = new URL(request.url);

  // ---- diagnostics ----
  if (url.pathname === "/ping") {
    return out(200, {
      ok: true,
      version: VERSION,
      colo: request.cf?.colo ?? null,
      kv: !!env.LOG,
      scores: !!env.SCORES,
      token: !!env.GITHUB_TOKEN,
      salt: !!env.IP_SALT,
      showIp: env.SHOW_IP !== "0",
      origin: request.headers.get("Origin"),
      allowed: pickOrigin(request.headers.get("Origin"))
    });
  }

  // ---- arcade run token (lets a client prove it started a run) ----
  if (url.pathname === "/start" && request.method === "POST") {
    return out(200, { ok: true, id: crypto.randomUUID(), serverTime: Date.now() });
  }

  // ---- arcade boards ----
  if (url.pathname === "/scores" || url.pathname === "/wipe") return scores(request, env, url, out);

  // ---- read the saved list / stats ----
  if (request.method === "GET") {
    const page = url.searchParams.get("page");
    if (page && page !== "hidden") {
      return out(400, { ok: false, error: "Unknown page" });
    }
    const { items, error } = await readFile(env);
    if (error) return out(502, { ok: false, error });

    if (url.searchParams.get("stats") === "1") {
      return out(200, { ok: true, stats: tally(items) });
    }

    const since = Date.parse(url.searchParams.get("since") || "") || 0;
    const limit = Math.min(+(url.searchParams.get("limit") || MAX_ENTRIES) || MAX_ENTRIES, 500);
    const pageItems = items
      .filter(i => !since || Date.parse(i.ts) > since)
      .slice(-limit)
      .reverse();

    return out(200, { ok: true, items: pageItems, total: items.length });
  }

  if (request.method !== "POST") {
    return out(405, { ok: false, error: "Method not allowed" });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return out(400, { ok: false, error: "Invalid JSON" });
  }

  const text = (body.text || "").toString().trim();
  if (!text) return out(400, { ok: false, error: "Empty suggestion" });
  if (text.length > MAX_LENGTH) {
    return out(400, { ok: false, error: `Max ${MAX_LENGTH} characters` });
  }

  // ---- rate limit + repeat-submitter counter (KV, optional) ----
  const ip = request.headers.get("CF-Connecting-IP") || "0.0.0.0";
  const ipHash = await hashIp(ip, env.IP_SALT || "nosalt");

  const rlKey = `rl:${ipHash}`;
  const hits = +(await kvGet(env, rlKey)) || 0;
  if (hits >= RATE_LIMIT) {
    return out(429, { ok: false, error: "Too many submissions, try again in an hour" });
  }
  ctx.waitUntil(kvPut(env, rlKey, String(hits + 1), { expirationTtl: RATE_TTL }));

  const seenKey = `seen:${ipHash}`;
  const prior = +(await kvGet(env, seenKey)) || 0;
  ctx.waitUntil(kvPut(env, seenKey, String(prior + 1), { expirationTtl: 60 * 60 * 24 * 365 }));

  // ---- how fast is the GitHub API right now ----
  const t0 = Date.now();
  ctx.waitUntil(fetch(GH, { headers: ghHeaders(env) }).catch(() => {}));
  const ghLatency = Date.now() - t0;

  const m = await collect(request, env, ctx, ipHash, prior, body.hints || {}, ghLatency);

  // ---- hidden.html: save into the repo file ----
  if (body.page === "hidden") {
    for (let attempt = 0; attempt < 3; attempt++) {
      const { items, sha, error } = await readFile(env);
      if (error) return out(502, { ok: false, error });

      items.push({ ts: new Date().toISOString(), text, meta: m.compact });
      const trimmed = items.slice(-MAX_ENTRIES);

      const put = await fetch(`${GH}/contents/${FILE_PATH}`, {
        method: "PUT",
        headers: ghHeaders(env),
        body: JSON.stringify({
          message: `New suggestion from hidden.html (${m.compact.cc || "??"})`,
          content: toBase64(JSON.stringify(trimmed, null, 2) + "\n"),
          ...(sha ? { sha } : {})
        })
      });

      if (put.ok) {
        ctx.waitUntil(logToKv(env, ip, ipHash, text, m.full));
        ctx.waitUntil(bumpPop(env, m.full.colo));
        return out(200, { ok: true, entry: { ts: new Date().toISOString(), text, meta: m.compact } });
      }
      if (put.status !== 409 && put.status !== 422) {
        return out(502, { ok: false, error: "GitHub rejected the save", detail: await put.text() });
      }
    }
    return out(503, { ok: false, error: "Busy, try again" });
  }

  // ---- movs.html: create a GitHub Issue ----
  const labels = [ISSUE_LABEL];
  if (prior === 0) labels.push("first-timer");
  if (m.full.tzMismatch || m.full.vpnish) labels.push("vpn-suspect");
  if (m.full.bot?.verified) labels.push("bot");

  const safe = text.replace(/<\/details/gi, "&lt;/details");
  const badge = m.full.bot?.verified ? "🤖" : prior === 0 ? "🆕" : `#${prior + 1}`;

  const ghResponse = await fetch(`${GH}/issues`, {
    method: "POST",
    headers: ghHeaders(env),
    body: JSON.stringify({
      title: `${badge} Suggestion · ${m.full.location || "unknown"} · ${new Date().toISOString().slice(0, 16).replace("T", " ")}`,
      body: [safe, "", renderMeta(m.full)].join("\n"),
      labels
    })
  });
  if (!ghResponse.ok) {
    return out(502, { ok: false, error: "GitHub rejected the request", detail: await ghResponse.text() });
  }

  const issue = await ghResponse.json();

  if (m.full.bot?.verified) {
    ctx.waitUntil(fetch(`${GH}/issues/${issue.number}`, {
      method: "PATCH",
      headers: ghHeaders(env),
      body: JSON.stringify({ state: "closed", state_reason: "not_planned" })
    }).catch(() => {}));
  }

  ctx.waitUntil(logToKv(env, ip, ipHash, text, m.full));
  ctx.waitUntil(bumpPop(env, m.full.colo));
  return out(200, { ok: true, url: issue.html_url });
}

/* ------------------------------ */
/* arcade                         */
/* ------------------------------ */

async function getList(env, g) {
  try { return JSON.parse((await env.SCORES.get("s:" + g)) || "[]"); } catch { return []; }
}

async function scores(request, env, url, out) {
  if (!env.SCORES) return out(503, { ok: false, error: "SCORES binding missing" });

  if (request.method === "GET") {
    if (url.pathname === "/wipe") return out(405, { ok: false, error: "Method not allowed" });
    const g = url.searchParams.get("game");

    // no ?game → every board at once
    if (!g) {
      const scores = {};
      for (const k of GAMES) scores[k] = await getList(env, k);
      return out(200, { ok: true, games: GAMES, scores });
    }
    if (!validGame(g)) return out(400, { ok: false, error: "Unknown game" });
    return out(200, { ok: true, scores: await getList(env, g) });
  }

  if (request.method !== "POST") return out(405, { ok: false, error: "Method not allowed" });

  let b;
  try { b = await request.json(); } catch { return out(400, { ok: false, error: "Invalid JSON" }); }

  if (url.pathname === "/wipe") {
    const k = "wipe:" + b.token;
    if (!b.token || !(await env.SCORES.get(k))) return out(403, { ok: false, error: "Not allowed" });
    await env.SCORES.delete(k); // one-time token
    for (const g of GAMES) {
      const cur = await env.SCORES.get("s:" + g);
      if (cur) await env.SCORES.put("backup:" + g, cur); // last board kept as backup:<game>
      await env.SCORES.put("s:" + g, "[]");
    }
    return out(200, { ok: true });
  }

  // ---- validate BEFORE throttling, so a rejected submit never blocks its own retry ----
  const ip = request.headers.get("CF-Connecting-IP") || "?", now = Date.now();

  const g = String(b.game || "").trim().toLowerCase();
  const s = Math.floor(Number(String(b.score).replace(/[,_\s]/g, "")));

  if (!validGame(g)) return out(400, { ok: false, error: "Bad score", detail: "unknown game: " + g });
  if (!Number.isFinite(s) || s < 0) return out(400, { ok: false, error: "Bad score", detail: "non-numeric score" });
  if (s > MAX_SCORE) return out(400, { ok: false, error: "Bad score", detail: "over max" });

  const lock = g + ":" + ip;
  const since = now - (lastHit.get(lock) || 0);
  if (since < SCORE_WINDOW) {
    const wait = Math.max(1, Math.ceil((SCORE_WINDOW - since) / 1000));
    return out(429, { ok: false, error: "Slow down", retryAfter: wait }, { "Retry-After": String(wait) });
  }
  lastHit.set(lock, now);
  if (lastHit.size > 5000) lastHit.clear();

  const name = (b.name || "").toString().replace(/[^\w .!\-]/g, "").trim().slice(0, 12) || "ANON";
  const list = await getList(env, g);

  const uid = crypto.randomUUID();
  list.push({ n: name, s, t: now, id: uid });
  list.sort((x, y) => y.s - x.s);
  const rank = list.findIndex(e => e.id === uid) + 1;

  await env.SCORES.put("s:" + g, JSON.stringify(list.slice(0, TOP)));

  const result = { ok: true, rank: rank > 0 && rank <= TOP ? rank : null };
  if (s >= WIPE_AT) { // unlocks the retro "purge all scores" option
    result.wipe = crypto.randomUUID();
    await env.SCORES.put("wipe:" + result.wipe, "1", { expirationTtl: 600 });
  }
  return out(200, result);
}

/* ------------------------------ */
/* collection                     */
/* ------------------------------ */

async function collect(request, env, ctx, ipHash, prior, hints, ghLatency) {
  const cf = request.cf || {};
  const h = request.headers;
  const now = new Date();

  const lat = cf.latitude ? +cf.latitude : null;
  const lon = cf.longitude ? +cf.longitude : null;
  const tz = cf.timezone || null;
  const cc = cf.country || null;

  const full = {
    submitted: now.toISOString(),
    ip: env.SHOW_IP === "0" ? null : (h.get("CF-Connecting-IP") || ""),
    ipHash,
    country: cc,
    countryName: cc ? safeIntl(() => new Intl.DisplayNames(["en"], { type: "region" }).of(cc)) : null,
    flag: cc ? [...cc].map(c => String.fromCodePoint(127397 + c.charCodeAt())).join("") : null,
    location: [cf.city, cf.region, cc].filter(Boolean).join(", ") || null,
    region: cf.region || null,
    city: cf.city || null,
    postal: cf.postalCode || null,
    lat, lon,
    tz,
    utcOffset: offsetOf(tz),
    localTime: localTimeOf(tz),
    localHour: localHourOf(tz),
    weekday: safeIntl(() => new Intl.DateTimeFormat("en-GB", { timeZone: tz, weekday: "long" }).format(now)),
    isEU: cf.isEUCountry === "1",
    continent: cf.continent || null,
    asn: cf.asn || null,
    org: cf.asOrganization || null,
    vpnish: /(vpn|proxy|hosting|server|cloud|aws|amazon|digitalocean|hetzner|ovh|m247|linode|vultr|azure|google|oracle|contabo)/i.test(cf.asOrganization || ""),
    tor: cf.asn === 396982 || /tor exit/i.test(cf.asOrganization || ""),
    colo: cf.colo || null,
    http: cf.httpProtocol || null,
    tls: cf.tlsVersion || null,
    tlsCipher: cf.tlsCipher || null,
    rtt: cf.clientTcpRtt ?? null,
    acceptEncoding: cf.clientAcceptEncoding || null,
    ghLatency,
    bot: cf.botManagement ? {
      score: cf.botManagement.score,
      verified: cf.botManagement.verifiedBot,
      category: cf.botManagement.verifiedBotCategory || null,
      corporateProxy: cf.botManagement.corporateProxy ?? null,
      jsPassed: cf.botManagement.jsDetection?.passed ?? null
    } : null,
    ua: (h.get("User-Agent") || "").slice(0, 250),
    accept: (h.get("Accept") || "").slice(0, 200),
    lang: h.get("Accept-Language") || null,
    langName: h.get("Accept-Language") ? safeIntl(() => new Intl.DisplayNames(["en"], { type: "language" }).of((h.get("Accept-Language") || "").split(/[,;-]/)[0])) : null,
    referer: h.get("Referer") || null,
    secFetch: [h.get("Sec-Fetch-Site"), h.get("Sec-Fetch-Mode"), h.get("Sec-Fetch-Dest")].filter(Boolean).join(" / ") || null,
    chUa: [h.get("Sec-CH-UA-Platform"), h.get("Sec-CH-UA-Mobile"), h.get("Sec-CH-UA-Model")].filter(Boolean).join(" ") || null,
    chHigh: [
      h.get("Sec-CH-UA-Arch") && `arch ${h.get("Sec-CH-UA-Arch")}`,
      h.get("Sec-CH-UA-Bitness") && `bits ${h.get("Sec-CH-UA-Bitness")}`,
      h.get("Sec-CH-UA-Platform-Version") && `os ${h.get("Sec-CH-UA-Platform-Version")}`,
      h.get("Sec-CH-UA-Full-Version-List"),
      h.get("Sec-CH-UA-WoW64") === "?1" && "wow64",
      h.get("Device-Memory") && `ram ${h.get("Device-Memory")}GB`,
      h.get("DPR") && `dpr ${h.get("DPR")}`,
      h.get("Save-Data") === "on" && "save-data"
    ].filter(Boolean).join(" · ") || null,
    dnt: h.get("DNT") === "1" || h.get("Sec-GPC") === "1",
    priority: h.get("Priority") || null,
    prior,
    hints,
    tzMismatch: hints.tz && tz && hints.tz !== tz ? `${hints.tz} ≠ ${tz}` : null,
    pasted: hints.pasted === true,
    fillMs: Number.isFinite(hints.fillMs) ? hints.fillMs : null
  };

  if (lat !== null && env.HOME_LAT && env.HOME_LON) {
    const km = haversine(+env.HOME_LAT, +env.HOME_LON, lat, lon);
    full.distance = `${Math.round(km).toLocaleString("en-US")} km ${bearing(+env.HOME_LAT, +env.HOME_LON, lat, lon)}`;
  }

  if (lat !== null) {
    full.map = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=11/${lat}/${lon}`;
    full.staticMap = `https://staticmap.openstreetmap.de/staticmap.php?center=${lat},${lon}&zoom=10&size=600x260&markers=${lat},${lon},red-pushpin`;

    const w = await getJson(
      `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
      `&current=temperature_2m,apparent_temperature,weather_code,is_day,wind_speed_10m` +
      `&daily=sunrise,sunset,daylight_duration&timezone=auto&forecast_days=1`
    );
    if (w?.current) {
      full.weather = `${Math.round(w.current.temperature_2m)}°C (feels ${Math.round(w.current.apparent_temperature)}°C), ` +
        `${WEATHER[w.current.weather_code] || "?"}, wind ${Math.round(w.current.wind_speed_10m)} km/h, ` +
        `${w.current.is_day ? "daylight" : "night"}`;
      full.sun = `${(w.daily?.sunrise?.[0] || "").slice(11)} → ${(w.daily?.sunset?.[0] || "").slice(11)}` +
        (w.daily?.daylight_duration?.[0] ? ` (${(w.daily.daylight_duration[0] / 3600).toFixed(1)}h daylight)` : "");
    }
    const e = await getJson(`https://api.open-meteo.com/v1/elevation?latitude=${lat}&longitude=${lon}`);
    if (e?.elevation?.[0] != null) full.elevation = `${Math.round(e.elevation[0])} m`;
  }

  full.moon = moonPhase(now);

  // ---- network enrichment ----
  if (full.ip) {
    const [ptr, torList, info] = await Promise.all([
      dnsPtr(full.ip),
      torExits(env),
      getJson(`https://ipinfo.io/${full.ip}/json`, { headers: { "User-Agent": "suggestion-box-worker" } })
    ]);
    if (ptr) full.ptr = ptr;
    if (torList && torList.has(full.ip)) full.tor = true;
    if (info) {
      full.ipinfo = { hostname: info.hostname || null, org: info.org || null, city: info.city || null, anycast: info.anycast ?? null };
    }
    // TCP RTT is a hard floor on distance from the edge PoP
    if (full.rtt != null) full.rttKm = Math.round(full.rtt * 0.1);
  }

  if (lat !== null && env.REVERSE_GEO === "1") {
    const key = `geo:${lat.toFixed(2)},${lon.toFixed(2)}`;
    let place = await kvGet(env, key);
    if (!place) {
      const n = await getJson(
        `https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=14&lat=${lat}&lon=${lon}`,
        { headers: { "User-Agent": "suggestion-box-worker (contact: you@example.com)" } }
      );
      place = n?.display_name?.split(",").slice(0, 3).join(",").trim() || "";
      if (place) ctx.waitUntil(kvPut(env, key, place, { expirationTtl: 60 * 60 * 24 * 30 }));
    }
    full.near = place || null;
  }

  const compact = {
    hash: ipHash,
    ip: full.ip,
    h: hints,
    ptr: full.ptr || null,
    ipinfo: full.ipinfo || null,
    rttKm: full.rttKm || null,
    cc, flag: full.flag, city: full.city, region: full.region, near: full.near || null,
    lat, lon, tz, off: full.utcOffset, t: full.localTime, hl: full.localHour,
    dow: full.weekday, isp: full.org, vpn: full.vpnish ? 1 : 0, tor: full.tor ? 1 : 0,
    wx: full.weather || null, moon: full.moon, elev: full.elevation || null,
    d: full.distance || null, pop: full.colo, prev: prior,
    bot: full.bot?.verified ? 1 : 0, gh: ghLatency
  };

  return { full, compact };
}

function renderMeta(m) {
  const rows = [
    ["Submitted", m.submitted],
    ["Their clock", m.localTime ? `${m.localTime} (${m.tz}, UTC${m.utcOffset >= 0 ? "+" : ""}${(m.utcOffset / 60).toFixed(1)})` : "unknown"],
    ["Their weekday", m.weekday || "n/a"],
    ["Location", m.location || "unknown"],
    ["Map", m.map || "n/a"],
    ["Near", m.near || "n/a"],
    ["Distance from you", m.distance || "n/a"],
    ["Weather", m.weather || "n/a"],
    ["Sun", m.sun || "n/a"],
    ["Moon", m.moon],
    ["Elevation", m.elevation || "n/a"],
    ["ISP / ASN", `${m.org || "?"} (AS${m.asn || "?"})${m.vpnish ? " — likely VPN/hosting" : ""}${m.tor ? " — Tor exit" : ""}`],
    ["IP", m.ip ? m.ip : `hidden, hash ${m.ipHash}`],
    ["PTR", m.ptr || "n/a"],
    ["ipinfo", m.ipinfo ? [m.ipinfo.org, m.ipinfo.city, m.ipinfo.hostname].filter(Boolean).join(" · ") : "n/a"],
    ["RTT floor", m.rttKm != null ? `${m.rttKm} km` : "n/a"],
    ["Timezone", m.tz || "n/a"],
    ["Client tz vs IP tz", m.tzMismatch || "match"],
    ["EU", m.isEU ? "yes" : "no"],
    ["Browser", m.ua || "n/a"],
    ["UA client hints", m.chUa || "n/a"],
    ["Client hints (entropy)", m.chHigh || m.hints.uaData || "n/a"],
    ["Language", m.lang ? `${m.lang} (${m.langName || "?"})` : "n/a"],
    ["Referrer", m.referer || "direct"],
    ["Sec-Fetch", m.secFetch || "n/a"],
    ["Do Not Track / GPC", m.dnt ? "yes" : "no"],
    ["Device hints", m.hints.screen ? `${m.hints.screen} · ${m.hints.cores ?? "?"} cores · ${m.hints.ram ?? "?"} GB · touch:${m.hints.touch ? "yes" : "no"} · dpr ${m.hints.dpr ?? "?"}` : "n/a"],
    ["GPU", m.hints.gpu || "n/a"],
    ["Dark mode", m.hints.dark ? "yes" : "no"],
    ["Connection", m.hints.conn ? `${m.hints.conn} · ~${m.hints.down ?? "?"} Mbps · rtt ${m.hints.connRtt ?? "?"}ms` : "n/a"],
    ["Battery", m.hints.battery || "n/a"],
    ["Canvas fp", m.hints.canvas || "n/a"],
    ["Audio fp", m.hints.audio || "n/a"],
    ["Fonts", m.hints.fonts || "n/a"],
    ["Storage quota", m.hints.storage || "n/a"],
    ["Devices", m.hints.devices || "n/a"],
    ["TTS voices", m.hints.voices ?? "n/a"],
    ["Webdriver", m.hints.webdriver ? "yes" : "no"],
    ["Save-Data", m.hints.saveData ? "yes" : "no"],
    ["Zoom", m.hints.zoom ?? "n/a"],
    ["Window", m.hints.window || "n/a"],
    ["History length", m.hints.historyLen ?? "n/a"],
    ["Typed vs pasted", m.pasted ? "pasted" : "typed"],
    ["Time on form", m.fillMs != null ? `${(m.fillMs / 1000).toFixed(1)}s` : "n/a"],
    ["Edge", `${m.colo || "?"} · ${m.http || "?"} · TLS ${m.tls || "?"} · ${m.tlsCipher || "?"} · rtt ${m.rtt ?? "?"}ms`],
    ["GitHub API latency", `${m.ghLatency}ms`],
    ["Accept-Encoding", m.acceptEncoding || "n/a"],
    ["Bot score", m.bot ? `${m.bot.score} (verified: ${m.bot.verified}, ${m.bot.category || "none"}, proxy: ${m.bot.corporateProxy})` : "n/a"],
    ["Prior submissions", String(m.prior)]
  ];

  return [
    "<details><summary>🕵️ Submission metadata</summary>",
    "",
    m.staticMap ? `![map](${m.staticMap})` : "",
    "",
    "| | |",
    "|---|---|",
    ...rows.map(([k, v]) => `| **${k}** | ${String(v ?? "n/a").replace(/\|/g, "\\|")} |`),
    "",
    "</details>"
  ].join("\n");
}

function tally(items) {
  const hours = Array(24).fill(0);
  const dows = {};
  const countries = {};
  const pops = {};
  const hashes = new Set();
  let vpn = 0, geotagged = 0, bots = 0, ips = 0;

  for (const i of items) {
    const m = i.meta || {};
    if (m.hl != null && m.hl >= 0 && m.hl < 24) hours[m.hl]++;
    if (m.dow) dows[m.dow] = (dows[m.dow] || 0) + 1;
    if (m.cc) countries[m.cc] = (countries[m.cc] || 0) + 1;
    if (m.pop) pops[m.pop] = (pops[m.pop] || 0) + 1;
    if (m.lat != null) geotagged++;
    if (m.vpn) vpn++;
    if (m.bot) bots++;
    if (m.ip) ips++;
    if (m.hash) hashes.add(m.hash);
  }

  return {
    total: items.length,
    geotagged, vpn, bots, ips,
    unique: hashes.size,
    hours, dows,
    countries: top(countries, 15),
    pops: top(pops, 10)
  };
}

function top(obj, n) {
  return Object.entries(obj).sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => [k, v]);
}

/* ------------------------------ */
/* helpers                        */
/* ------------------------------ */

async function kvGet(env, key) {
  try { return env.LOG ? await env.LOG.get(key) : null; } catch { return null; }
}

async function kvPut(env, key, value, opts) {
  try { if (env.LOG) await env.LOG.put(key, value, opts); } catch {}
}

async function logToKv(env, ip, ipHash, text, meta) {
  await kvPut(env, `log:${Date.now()}:${ipHash}`, JSON.stringify({ ip, ipHash, text, meta }), { expirationTtl: 60 * 60 * 24 * 180 });
}

async function bumpPop(env, colo) {
  if (!colo) return;
  const k = `pop:${colo}`;
  const n = +(await kvGet(env, k)) || 0;
  await kvPut(env, k, String(n + 1), { expirationTtl: 60 * 60 * 24 * 365 });
}

async function dnsPtr(ip) {
  if (!ip.includes(".")) return null;
  try {
    const name = ip.split(".").reverse().join(".") + ".in-addr.arpa";
    const r = await fetch(`https://cloudflare-dns.com/dns-query?name=${name}&type=PTR`, {
      headers: { Accept: "application/dns-json" },
      signal: AbortSignal.timeout(2000)
    });
    if (!r.ok) return null;
    const j = await r.json();
    return (j.Answer?.[0]?.data || "").replace(/\.$/, "") || null;
  } catch { return null; }
}

async function torExits(env) {
  try {
    const cached = await kvGet(env, "tor:list");
    if (cached) return new Set(cached.split("\n"));
    const r = await fetch("https://check.torproject.org/torbulkexitlist", { signal: AbortSignal.timeout(3000) });
    if (!r.ok) return null;
    const text = await r.text();
    await kvPut(env, "tor:list", text, { expirationTtl: 3600 });
    return new Set(text.split("\n"));
  } catch { return null; }
}

async function readFile(env) {
  const res = await fetch(`${GH}/contents/${FILE_PATH}`, { headers: ghHeaders(env) });
  if (res.status === 404) return { items: [], sha: null };
  if (!res.ok) return { error: "Could not read " + FILE_PATH };
  const data = await res.json();
  try {
    const raw = fromBase64(data.content).trim();
    if (!raw) return { items: [], sha: data.sha }; // empty file counts as []
    const parsed = JSON.parse(raw);
    return { items: Array.isArray(parsed) ? parsed : [], sha: data.sha };
  } catch {
    return { error: FILE_PATH + " isn't valid JSON" };
  }
}

function ghHeaders(env) {
  return {
    "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
    "Accept": "application/vnd.github+json",
    "User-Agent": "lunar-gooner-suggestions-worker",
    "Content-Type": "application/json"
  };
}

async function hashIp(ip, salt) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(ip + salt));
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
}

function haversine(a1, o1, a2, o2) {
  const R = 6371, r = Math.PI / 180;
  const dA = (a2 - a1) * r, dO = (o2 - o1) * r;
  const x = Math.sin(dA / 2) ** 2 + Math.cos(a1 * r) * Math.cos(a2 * r) * Math.sin(dO / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
}

function bearing(a1, o1, a2, o2) {
  const r = Math.PI / 180;
  const y = Math.sin((o2 - o1) * r) * Math.cos(a2 * r);
  const x = Math.cos(a1 * r) * Math.sin(a2 * r) - Math.sin(a1 * r) * Math.cos(a2 * r) * Math.cos((o2 - o1) * r);
  return COMPASS[Math.round(((Math.atan2(y, x) / r + 360) % 360) / 22.5) % 16];
}

function localTimeOf(tz) {
  if (!tz) return null;
  return safeIntl(() => new Intl.DateTimeFormat("en-GB", { timeZone: tz, dateStyle: "medium", timeStyle: "short" }).format(new Date()));
}

function localHourOf(tz) {
  if (!tz) return null;
  return safeIntl(() => +new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "2-digit", hourCycle: "h23" }).format(new Date()));
}

function offsetOf(tz) {
  if (!tz) return 0;
  const s = safeIntl(() => new Intl.DateTimeFormat("en-US", { timeZone: tz, timeZoneName: "longOffset" })
    .formatToParts(new Date()).find(p => p.type === "timeZoneName")?.value);
  const mt = /GMT([+-])(\d{2}):(\d{2})/.exec(s || "");
  return mt ? (mt[1] === "-" ? -1 : 1) * (+mt[2] * 60 + +mt[3]) : 0;
}

function moonPhase(d) {
  const syn = 29.530588853;
  const days = (d.getTime() - Date.UTC(2000, 0, 6, 18, 14)) / 86400000;
  const age = ((days % syn) + syn) % syn;
  const names = ["new","waxing crescent","first quarter","waxing gibbous","full","waning gibbous","last quarter","waning crescent"];
  return `${names[Math.floor((age / syn) * 8 + 0.5) % 8]} (${age.toFixed(1)}d)`;
}

function safeIntl(fn) { try { return fn() || null; } catch { return null; } }

async function getJson(url, opts = {}) {
  try {
    const r = await fetch(url, { ...opts, signal: AbortSignal.timeout(2500) });
    return r.ok ? await r.json() : null;
  } catch { return null; }
}

// UTF-8 safe base64 (btoa/atob alone break on emoji etc.)
function toBase64(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

function fromBase64(b64) {
  const bin = atob(b64.replace(/\n/g, ""));
  return new TextDecoder().decode(Uint8Array.from(bin, c => c.charCodeAt(0)));
}

function pickOrigin(o) {
  return o && DEV_ORIGINS.has(o) ? o : ALLOWED_ORIGIN;
}

function cors(status, data, origin, extra) {
  return new Response(data ? JSON.stringify(data) : null, {
    status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      "Access-Control-Allow-Origin": pickOrigin(origin),
      "Access-Control-Expose-Headers": "Retry-After",
      "Vary": "Origin, Sec-CH-UA-Model, Sec-CH-UA-Platform-Version, Sec-CH-UA-Arch, Device-Memory, DPR",
      "Accept-CH": "Sec-CH-UA-Model, Sec-CH-UA-Platform-Version, Sec-CH-UA-Arch, Sec-CH-UA-Bitness, Sec-CH-UA-Full-Version-List, Sec-CH-UA-WoW64, Device-Memory, DPR, Viewport-Width, Width, RTT, Downlink, ECT, Save-Data",
      "Critical-CH": "Sec-CH-UA-Model, Sec-CH-UA-Platform-Version",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      ...(extra || {})
    }
  });
}