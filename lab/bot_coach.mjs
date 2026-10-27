// 💬 Sohbet koçu (her gece, GitHub Actions): OXXai sohbet asistanını her gün biraz daha iyi anlayan hale getirir.
//
// 1) Günün verisinden (fikstür, lig adları, karne; KULLANICI MESAJI YOK) aday bilgi üretir: takım takma adları ve Türkçe okunuşları,
//    lig adları, eş anlamlı kelimeler, yazım hataları, kalıp cümleler, terimler, öne çıkan maçlar.
// 2) Her adayı, uygulamanın kendisini başsız tarayıcıda açıp bot'a soru sorarak sınar: aday olmadan yanlış anlaşılan soru, adayla doğru
//    anlaşılıyorsa aday kabul edilir; zaten anlaşılıyorsa yalnız teste eklenir (test kümesi her gün büyür).
// 3) Kapı: tüm test kümesi (sabit 224 soru + biriken üretilmiş sorular) dünkü bilgi bankasıyla ve yeni bilgi bankasıyla çalıştırılır.
//    Yeni banka yalnız niyet doğruluğu VE faydalı cevap oranı düşmüyorsa ve sayfa hatası yoksa yayınlanır; yoksa dünkü banka kalır.
// Çıktılar: data/bot_kb.json (yayınlanan banka), data/bot_tests.json (biriken sorular), data/bot_coach.json (rapor + geçmiş), data/gelisim.json (olay).
// Kullanım: node lab/bot_coach.mjs [--dry]   (BOT_COACH_TIME=2026-10-25T12:00:00+03:00 ile saat sabitlenebilir; BOT_COACH_INDEX=dosya ile başka index.html sınanabilir)
import fs from "fs";
import path from "path";
import http from "http";
import { createRequire } from "module";
import { fileURLToPath } from "url";
const require = createRequire(import.meta.url);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const DATA = path.join(ROOT, "data");
const { judge } = require("./bot/judge.cjs");
const SUITE = require("./bot/suite.cjs");
const BANK = require("./bot/banks.cjs");
const DRY = process.argv.includes("--dry");
const ONLY_EVAL = process.argv.includes("--eval");   // yalnız mevcut bankayla test kümesini çalıştır, hiçbir şey yazma
const T0 = Date.now();
const log = (...a) => console.log("[koç]", ...a);

// ---------------- yardımcılar ----------------
const N = s => String(s || "").toLocaleLowerCase("tr").replace(/ç/g, "c").replace(/ğ/g, "g").replace(/ı/g, "i").replace(/ö/g, "o").replace(/ş/g, "s").replace(/ü/g, "u")
  .normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
const jl = (f, d) => { try { return JSON.parse(fs.readFileSync(path.join(DATA, f), "utf8")); } catch (e) { return d; } };
const jw = (f, o) => fs.writeFileSync(path.join(DATA, f), JSON.stringify(o, null, 1) + "\n");
const pc = (x, n) => n ? Math.round(x / n * 1000) / 10 : 0;
const reS = r => r instanceof RegExp ? { re: r.source, f: r.flags } : r;
const reL = r => (r && typeof r === "object" && !(r instanceof RegExp) && "re" in r) ? new RegExp(r.re, r.f || "") : r;
const cSer = c => Object.fromEntries(Object.entries(c || {}).map(([k, v]) => [k, reS(v)]));
const cDes = c => Object.fromEntries(Object.entries(c || {}).map(([k, v]) => [k, reL(v)]));
const escRe = s => String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
function rng(seed) { let a = 0; for (const ch of seed) a = (a * 31 + ch.charCodeAt(0)) >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

// ---------------- saat ve günler (İstanbul) ----------------
// Saat veriyle tutarlı olmalı: data/fixtures.json'daki gün aralığının dışındaki bir saatle (ör. eski bir BOT_COACH_TIME, veri bir gün
// ilerlediğinde) "bugün" soruları boş bülten görür, gün adı soruları başka güne düşer ve ölçüm yapay olarak çöker (v123 öncesi %84,9).
// Bu yüzden saat (BOT_COACH_TIME ya da gerçek saat) veri aralığının dışındaysa saat-dakika korunarak verinin ilk gününe kaydırılır.
// BOT_COACH_STRICT=1 ile kaydırma kapatılır (yalnız uyarı).
const istDay = d => new Date(d).toLocaleDateString("sv-SE", { timeZone: "Europe/Istanbul" });
function dataDays() {
  try { const F = JSON.parse(fs.readFileSync(path.join(DATA, "fixtures.json"), "utf8")); const ds = (Array.isArray(F) ? F : []).map(x => x && x.d).filter(d => /^\d{4}-\d\d-\d\d$/.test(d || "")).sort();
    return ds.length ? { from: ds[0], to: ds[ds.length - 1] } : null; } catch (e) { return null; }
}
const DDAYS = dataDays();
const NOW_ASKED = process.env.BOT_COACH_TIME ? new Date(process.env.BOT_COACH_TIME) : new Date();
const NOW = (() => {
  const d = istDay(NOW_ASKED); if (!DDAYS || (d >= DDAYS.from && d < DDAYS.to)) return NOW_ASKED;
  const hm = NOW_ASKED.toLocaleTimeString("sv-SE", { timeZone: "Europe/Istanbul", hour: "2-digit", minute: "2-digit" });
  const alt = new Date(`${DDAYS.from}T${hm}:00+03:00`);
  console.log(`[koç] UYARI: saat ${NOW_ASKED.toISOString()} (${d}) veri aralığının (${DDAYS.from} … ${DDAYS.to}) dışında` + (process.env.BOT_COACH_STRICT === "1" ? "; BOT_COACH_STRICT=1, kaydırılmadı" : `; ${alt.toISOString()} kullanılıyor`));
  return process.env.BOT_COACH_STRICT === "1" ? NOW_ASKED : alt;
})();
const TODAY = istDay(NOW);
const WDN = ["Paz", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt"];
const MON = ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık"];
const dayAt = k => new Date(Date.parse(TODAY + "T12:00:00+03:00") + k * 864e5);
const wdOf = k => WDN[dayAt(k).getUTCDay()];
const resolveDay = arr => arr ? arr.map(x => /^\+\d+$/.test(x) ? wdOf(+x.slice(1)) : x) : arr;
const WDQ = [[/\bpazartesi\b/, "Pzt"], [/\bsali\b/, "Sal"], [/\bcarsamba\b/, "Çar"], [/\bpersembe\b/, "Per"], [/\bcumartesi\b/, "Cmt"], [/\bcuma\b/, "Cum"], [/\bpazar\b/, "Paz"]];
const wdInQ = q => { const n = N(q); if (/\bhafta ?sonu/.test(n)) return null; const hit = WDQ.filter(([re]) => re.test(n)); return hit.length === 1 ? hit[0][1] : null; };
const fillQ = q => q.replace(/\{D\+(\d+)\}/g, (_, k) => { const d = dayAt(+k); return `${d.getUTCDate()} ${MON[d.getUTCMonth()]}`; })
  .replace(/\{DOT\+(\d+)\}/g, (_, k) => { const d = dayAt(+k); return `${d.getUTCDate()}.${String(d.getUTCMonth() + 1).padStart(2, "0")}`; });

// ---------------- index.html'den bot sözlüğü (çakışma kontrolü için) ----------------
const INDEX = process.env.BOT_COACH_INDEX ? path.resolve(process.env.BOT_COACH_INDEX) : path.join(ROOT, "index.html");
const HTML = fs.readFileSync(INDEX, "utf8");
function lexicon() {
  const L = { stop: new Set(), sl: new Set(), botlg: new Set(), raw: [], gen: new Set() };
  const m1 = /const STOPW=new Set\(\(([\s\S]*?)\)\.split\(" "\)\)/.exec(HTML);
  if (m1) for (const s of m1[1].match(/"([^"]*)"/g) || []) for (const w of s.slice(1, -1).split(" ")) if (w) L.stop.add(w);
  const m2 = /const SL=\{([\s\S]*?)\};/.exec(HTML); if (m2) for (const k of m2[1].matchAll(/([a-zçğıöşü]+):"/g)) L.sl.add(N(k[1]));
  const m3 = /const BOT_LG=\{([\s\S]*?)\};/.exec(HTML); if (m3) for (const k of m3[1].matchAll(/"([^"]+)":"/g)) { L.botlg.add(N(k[1])); N(k[1]).split(" ").forEach(w => L.stop.add(w)); }
  const m4 = /const RAW=\{([\s\S]*?)\n\}/.exec(HTML);
  if (m4) for (const ln of m4[1].matchAll(/(\w+):"([^"]*)"/g)) for (const ent of ln[2].split(";")) { const [name, al] = ent.split("|"); L.raw.push({ lg: ln[1], name, al: (al || "").split(",").map(x => x.trim()).filter(Boolean) }); }
  const m5 = /const TM_GEN=new Set\("([^"]+)"/.exec(HTML); if (m5) m5[1].split(" ").forEach(w => L.gen.add(w));
  const m6 = /const NLU_STOP=new Set\(\[([^\]]*)\]/.exec(HTML); if (m6) for (const s of m6[1].match(/"([^"]*)"/g) || []) L.stop.add(N(s.slice(1, -1)));
  const extra = "ana ekran oyun gol kart kirmizi sari beyaz siyah mavi yesil aslan kartal kanarya gunes deniz yildiz kral kara bir iki uc dort bes alti yedi sekiz dokuz on maclar maci mac takim lig kupa final yari son ilk evet hayir tamam iyi kotu guzel cok az daha en ben sen biz siz onlar bunu sunu".split(" ");
  extra.forEach(w => L.stop.add(w));
  return L;
}
const LEX = lexicon();

// ---------------- yerel sunucu ----------------
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".webmanifest": "application/manifest+json", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".css": "text/css" };
function serve() {
  return new Promise(res => { const srv = http.createServer((req, r) => {
    let p = decodeURIComponent((req.url || "/").split("?")[0]); if (p === "/") p = "/index.html";
    const f = p === "/index.html" ? INDEX : path.join(ROOT, path.normalize(p).replace(/^(\.\.[/\\])+/, ""));
    if (!f.startsWith(ROOT) && f !== INDEX) { r.writeHead(403); return r.end(); }
    fs.readFile(f, (e, b) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream", "cache-control": "no-store" }); r.end(b); });
  }); srv.listen(0, "127.0.0.1", () => res(srv)); });
}

// ---------------- tarayıcı ----------------
let chromium;
try { ({ chromium } = require("playwright")); } catch (e) { ({ chromium } = await import("playwright")); }
async function openPage(browser, port, kb, coach) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: "block" });
  await ctx.addInitScript(() => { localStorage.setItem("bx-terms", JSON.stringify({ v: "2.0", at: Date.now(), kvkk: true, inst: Date.now() })); localStorage.setItem("bx-oxxai-hos", "1"); localStorage.setItem("bx-oxxai-ikon", "1"); });
  const p = await ctx.newPage(); const errs = [];
  p.on("pageerror", e => errs.push(String(e && e.message || e).slice(0, 300)));
  p.on("dialog", d => d.dismiss().catch(() => { }));
  await p.clock.setFixedTime(NOW);
  await p.route(/iddaa\.com|espn|jasoncameron|jsdelivr|api-sports|huggingface|googleapis|gstatic/, r => r.fulfill({ status: 404, body: "" }));
  await p.route(/\/data\/bot_kb\.json/, r => kb ? r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(kb) }) : r.fulfill({ status: 404, body: "" }));
  await p.route(/\/data\/bot_coach\.json/, r => coach ? r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(coach) }) : r.fulfill({ status: 404, body: "" }));
  await p.goto(`http://127.0.0.1:${port}/index.html`, { timeout: 90000 });
  await p.waitForTimeout(3000);
  for (let i = 0; i < 45; i++) {
    const st = await p.evaluate(() => { try { if (FIXTURES.length && window.PL_RESET) PL_RESET(); return [FIXTURES.length, Pick.list().length, !!DAILY]; } catch (e) { return [0, 0, false]; } });
    if (st[0] && st[1] && st[2]) break;
    if (i % 5 === 4) await p.evaluate(() => { try { dailyLoad(); } catch (e) { } });
    await p.waitForTimeout(1000);
  }
  try { await p.waitForLoadState("networkidle", { timeout: 20000 }); } catch (e) { }
  await p.waitForTimeout(1500);
  await p.evaluate(async () => { try { PL_RESET(); GOLD.set = null; } catch (e) { } try { await (window.BOT70 && BOT70.ready); } catch (e) { } });
  await p.waitForTimeout(1000);
  return { ctx, p, errs };
}

// sayfadan günün "dünyası": botun gerçekten gördüğü maçlar, takımlar, ligler
async function world(p) {
  // veri yüklemesi bitene kadar bekle: maç havuzu iki ölçümde aynı kalınca (en çok ~15 sn). Yükleme süresi oynak olduğundan
  // erken toplanan "dünya" eksik lig etiketi verip lig sorularını haksız yere düşürüyordu.
  let prev = -1;
  for (let i = 0; i < 15; i++) {
    const n = await p.evaluate(() => { try { const now = Date.now(); return botPre({ from: now, to: now + 3 * 864e5 }).length; } catch (e) { return -1; } });
    if (n > 0 && n === prev) break; prev = n; await p.waitForTimeout(1000);
  }
  return p.evaluate(() => {
    const now = Date.now(), out = { today: istDay(new Date()), m: [], teams: [], lgs: {}, gold: false, v70: !!window.BOT70 };
    try { out.gold = goldCalc().size > 0; } catch (e) { }
    let pre = []; try { pre = botPre({ from: now, to: now + 3 * 864e5 }); } catch (e) { }
    for (const x of pre) { const f = x.f; out.m.push({ h: x.m.h, a: x.m.a, lg: x.m.lg, lab: (f && (f.cn || f.ln)) || botLgName(x.m.lg), t: x.m.dt.getTime(), cp: x.R.cp }); }
    const seen = new Set();
    for (const m of Pick.list()) { const t = m.dt.getTime(); if (m.started || m.live || t < now || t > now + 8 * 864e5) continue; for (const n of [m.h, m.a]) if (!seen.has(n)) { seen.add(n); out.teams.push({ n, lg: m.lg }); } }
    for (const [k, v] of Object.entries(LEAGUES)) out.lgs[k] = v.n;
    return out;
  });
}

// her konuşma için "anlamlı mı" kontrolü (veri koşulu)
async function needs(p, convs) {
  const list = convs.map(cv => cv.map(t => t.need).filter(Boolean));
  return p.evaluate(list => {
    const fold = s => String(s || "").toLocaleLowerCase("tr").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ı/g, "i");
    const now = Date.now(), D = 864e5, d0 = d => Date.parse(d + "T00:00:00+03:00"), T = istDay(new Date());
    const P = Pick.list().filter(m => !m.started && !m.live && m.dt.getTime() >= now && m.dt.getTime() < now + 8 * D);
    const GX = /\((k|esw|wsl|w)\)|women|kadin|\bu ?\d\d\b|\bii\b|reserves?/i, adult = n => !GX.test(n);   // kadın / genç takımları "takım var" saymaz (soru onları istemiyorsa)
    const has = t => P.some(m => (adult(m.h) && fold(m.h).includes(fold(t))) || (adult(m.a) && fold(m.a).includes(fold(t))) || (GX.test(t) && fold(m.h + " | " + m.a).includes(fold(t))));
    let gold = false; try { gold = goldCalc().size > 0; } catch (e) { }
    const ok1 = n => {
      if (n.teams && !n.teams.every(has)) return false;
      if (n.match && !P.some(m => (n.match.some(t => GX.test(t)) || (adult(m.h) && adult(m.a))) && n.match.every(t => fold(m.h + " | " + m.a).includes(fold(t))))) return false;
      if (n.gold && !gold) return false;
      if (n.days) { const WD = ["Paz", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt"]; let any = false;
        for (let k = 0; k <= 6 && !any; k++) { const f = d0(T) + k * D, wd = WD[new Date(f + 12 * 3600e3).getUTCDay()]; if (!n.days.includes(wd)) continue;
          // bugün: kalan maçlar saatle azalır, önerilebilir (oranlı) maç kalmadıysa soru uygulanamaz; diğer günler: başlamamış maç olması yeter
          if (k === 0) { try { any = botPre({ from: now, to: f + D }).length > 0; } catch (e) { any = true; } }
          else any = Pick.list().some(m => { const t = m.dt.getTime(); return !m.started && t >= f && t < f + D; }); }
        if (!any) return false; }
      if (n.lg) { let from = now, to = now + 4 * D; if (n.day) { const k = +n.day.slice(1); from = Math.max(now, d0(T) + k * D); to = d0(T) + (k + 1) * D; }
        let L = []; try { L = botPre({ lg: n.lg, from, to }); } catch (e) { } if (!L.length) return false; }
      return true; };
    return list.map(ns => ns.every(ok1));
  }, list);
}

// bir konuşmayı çalıştır
async function runConv(p, conv) {
  await p.evaluate(() => {
    BOT.ctx = null; BOT.hist = []; Object.assign(BOT.st, { ad: "", lg: {}, tm: {}, risk: "orta", oner: [], karne: { n: 0, hit: 0 } });
    if (BOT.v69) BOT.v69 = {}; CP.items.length = 0; try { cpSave(); } catch (e) { }
    if (window.BOT70) { BOT70.resetSession(); BOT70.testMode(true); }
  });
  const res = []; let prev = null;
  for (const t of conv) {
    const r = await p.evaluate(async q => {
      const cpBefore = CP.items.length; let R, err = null;
      try { R = await botAnswer(q); } catch (e) { err = String(e && e.stack || e); R = { html: "" }; }
      const d = document.createElement("div"); d.innerHTML = R.html || "";
      return { html: R.html || "", text: d.textContent.replace(/\s+/g, " ").trim(), chips: R.chips || [], cpBefore, cpAfter: CP.items.length, err };
    }, t.q);
    const j = judge(t, r, prev);
    res.push({ q: t.q, k: t.k, intent: j.intent, useful: j.useful, unk: j.unk, text: r.text.slice(0, 300), err: r.err });
    if (j.cards.length) prev = { cards: j.cards };
  }
  return res;
}
async function setKB(p, kb) { await p.evaluate(kb => BOT70.setKB(kb), kb || null); }

// test hazırlama: gün belirteçleri, şablon tarih, lig etiketleri
let LGLAB = {};
const NSTATIC = SUITE.core.length + SUITE.holdout.length;   // sabit küme konuşma sayısı (raporda ayrıca gösterilir)
function prep(t) {
  const c = cDes(t.c);
  // eski üretilmiş testler gün adını göreli "+k" ile saklıyordu ("pazartesi maclari" → +6, üretildiği güne göre): başka gün
  // çalıştırılınca yanlış güne bakıyordu. Soruda tek bir gün adı varsa beklenen gün o addır.
  const wq = c.day && c.day.every(x => /^\+\d+$/.test(x)) ? wdInQ(t.q) : null;
  if (wq) c.day = [wq];
  if (c.day) c.day = resolveDay(c.day);
  // gün belirten soru: o gün(ler)de bültende önerilebilir (başlamamış, oranlı) maç yoksa soru o saatte uygulanamaz (iki tarafta da aynı)
  let need = t.need || null;
  if (c.day && c.day.length) need = Object.assign({}, need || {}, { days: c.day });
  if (c.lgCode) { const labs = LGLAB[c.lgCode] || []; c.lg = labs.length ? new RegExp(labs.map(escRe).join("|")) : /^$/; }
  return { q: fillQ(t.q), k: t.k, c, need, id: t.id || null };
}
async function runSuite(p, convs, label) {
  const ok = await needs(p, convs); const out = []; let skip = 0;
  for (let i = 0; i < convs.length; i++) { if (!ok[i]) { skip += convs[i].length; continue; } for (const r of await runConv(p, convs[i])) out.push(Object.assign(r, { ci: i })); }
  const byK = {}; for (const o of out) { const a = byK[o.k] = byK[o.k] || { n: 0, i: 0, u: 0, x: 0 }; a.n++; a.i += o.intent; a.u += o.useful; a.x += o.unk; }
  const tot = out.reduce((a, o) => (a.n++, a.i += o.intent, a.u += o.useful, a.x += o.unk, a), { n: 0, i: 0, u: 0, x: 0 });
  const sab = out.filter(o => o.ci < NSTATIC).reduce((a, o) => (a.n++, a.i += o.intent, a.u += o.useful, a.x += o.unk, a), { n: 0, i: 0, u: 0, x: 0 });
  log(`${label}: ${tot.n} soru (uygulanamaz ${skip}) · niyet %${pc(tot.i, tot.n)} · faydalı %${pc(tot.u, tot.n)} · anlamadı %${pc(tot.x, tot.n)} | sabit küme ${sab.n}: niyet %${pc(sab.i, sab.n)} · faydalı %${pc(sab.u, sab.n)}`);
  return { byK, tot, out, skip, sab };
}

// ---------------- aday üretimi ----------------
const TOPLG = ["tr1", "en", "es", "it", "de", "fr", "ucl", "uel", "uecl", "nl", "pt", "be", "tr2"];
function distinct(name) { return N(name).replace(/\bk\b/g, " ").split(" ").filter(w => w.length >= 3 && !LEX.gen.has(w) && !/^\d+$|^(youth|reserves?|women|kadin)$/.test(w)); }
const PHON = [[/tsch/g, "c"], [/sch/g, "s"], [/ch/g, "s"], [/ch/g, "k"], [/w/g, "v"], [/x/g, "ks"], [/q/g, "k"], [/ph/g, "f"], [/th/g, "t"], [/eau/g, "o"], [/ou/g, "u"], [/ei/g, "ay"], [/eu/g, "oy"],
  [/ae/g, "e"], [/oe/g, "o"], [/ue/g, "u"], [/ille$/, "il"], [/(.)\1/g, "$1"], [/^j/, "y"], [/y$/, "i"], [/c(?=[ei])/g, "s"], [/gn/g, "ny"], [/eaux?$/, "o"], [/ea/g, "i"], [/ee/g, "i"], [/oo/g, "o"], [/ij/g, "ay"]];
function phonetic(tok) {
  const out = new Set(); let all = tok;
  for (const [re, to] of PHON) { const v = tok.replace(re, to); if (v !== tok) out.add(v); all = all.replace(re, to); }
  if (all !== tok) out.add(all);
  return [...out].filter(v => v.length >= 4 && v !== tok);
}
function typos(w, R) {
  const out = new Set();
  for (let i = 1; i < w.length - 1; i++) out.add(w.slice(0, i) + w.slice(i + 1));                // harf atlama
  for (let i = 1; i < w.length - 2; i++) out.add(w.slice(0, i) + w[i + 1] + w[i] + w.slice(i + 2)); // yer değiştirme
  return [...out].filter(x => x !== w && x.length >= 4).sort(() => R() - .5);
}
function collides(key, kbA) {
  const k = N(key); if (!k || k.length < 3) return true;
  return k.split(" ").some(w => LEX.stop.has(w)) || LEX.sl.has(k) || LEX.botlg.has(k) || (kbA && ((kbA.takim || {})[k] || (kbA.esanlam || {})[k] || (kbA.yazim || {})[k]));
}

// RAW takım adı (uygulamanın listesi) ile bültendeki ad aynı takım mı? Genel kelimeler ("city", "united", "real"…) atılarak
// karşılaştırılırken bu kelimeler iki adda da aynı olmalı: aksi halde "Manchester United" = "Manchester City" sanılıyordu
// ("man utd maçı" testi Manchester City bekliyordu).
const GENKEY = n => N(n).split(" ").filter(w => w.length >= 4 && LEX.gen.has(w)).sort().join(" ");
function rawSame(rname, tname) {
  const rn = N(rname), tn = N(tname);
  if (tn === rn || tn.startsWith(rn + " ") || rn.startsWith(tn + " ")) return true;
  return distinct(rname).length >= 1 && tn.split(" ").filter(w => !LEX.gen.has(w)).join(" ") === distinct(rname).join(" ") && GENKEY(rname) === GENKEY(tname);
}
// eski gecelerde üretilmiş, kısaltması yanlış takıma bağlanmış testler değerlendirmeye alınmaz
function aliasTestOk(t) {
  if (t.kaynak !== "takim-kisaltma" || !t.c || !t.c.team) return true;
  const al = N(t.q.replace(/\s+ma[çc]\S*\s*$/i, ""));
  const rs = LEX.raw.filter(r => r.al.some(a => N(a) === al)); if (!rs.length) return true;
  return rs.some(r => rawSame(r.name, t.c.team));
}
function candidates(W, kbA, done) {
  const R = rng(TODAY), C = [], pure = [];
  const seenQ = new Set(done);
  const addC = (sec, key, val, test) => { if (seenQ.has(N(test.q))) return; seenQ.add(N(test.q)); C.push({ sec, key: N(key), val, test }); };
  const addT = (t) => { if (seenQ.has(N(t.q))) return; seenQ.add(N(t.q)); pure.push(t); };
  // takımlar: dünya adları ve belirgin kelimeler (gençler / kadınlar / yedekler hariç: takma ad onlara gitmemeli)
  const YOUTH = /\b(u ?1\d|u ?2\d|youth|women|kadin|reserves?|ii|b|w|wsl|nwsl|fem|femenino|feminine)\b|\(k\)/i;
  const WLG = lg => /kad[iı]n|women|\bwsl\b|\(k\)|femen/i.test(W.lgs[lg] || "");   // kadın ligleri (takım adında işaret olmasa da)
  const teams = W.teams.map(t => ({ n: t.n, lg: t.lg, tok: distinct(t.n), y: YOUTH.test(N(t.n)) || /\(k\)/i.test(t.n) || WLG(t.lg) })).filter(t => t.tok.length);
  const senior = teams.filter(t => !t.y);
  const tokCount = {}; for (const t of teams) for (const w of new Set(t.tok)) tokCount[w] = (tokCount[w] || 0) + 1;
  const allTok = new Set(teams.flatMap(t => t.tok));
  const playing = new Set(W.m.flatMap(m => [m.h, m.a]));
  const big = n => BANK.buyuk.some(b => N(n).includes(N(b)));
  const rank = t => (TOPLG.includes(t.lg) ? 0 : 2) + (big(t.n) ? 0 : 1) + (playing.has(t.n) ? 0 : 1);
  // a) uygulamanın kendi takım listesindeki kısaltmalar (RAW): "spurs", "wolves", "gladbach"… — yalnız ad birebir eşleşirse
  for (const r of LEX.raw) for (const al of r.al) {
    const key = N(al); if (key.length < 3 || collides(key, kbA) || LEX.gen.has(key)) continue;
    const tg = senior.filter(t => rawSame(r.name, t.n));
    if (tg.length !== 1) continue;
    addC("takim", key, tg[0].n, { q: `${al} maçı`, k: "takim", c: { team: tg[0].n }, need: { teams: [tg[0].n] }, kaynak: "takim-kisaltma" });
  }
  // b) Türkçe okunuşlar ("volfsburg", "şalke", "laypzig") ve baş harfler — üst ligler ve büyük takımlar
  let nPh = 0;
  for (const t of senior.filter(t => TOPLG.includes(t.lg) || big(t.n)).sort((a, b) => rank(a) - rank(b))) { if (nPh >= 40) break;
    const tok = t.tok.slice().sort((a, b) => b.length - a.length)[0]; if (!tok || tok.length < 5 || tokCount[tok] > 1) continue;
    for (const v of phonetic(tok).slice(-2)) { if (v.length < 5 || collides(v, kbA) || allTok.has(v)) continue;
      addC("takim", v, t.n, { q: `${v} maçı ne olur`, k: "takim", c: { team: t.n }, need: { teams: [t.n] }, kaynak: "takim-okunus" }); nPh++; }
    const ws = N(t.n).split(" ").filter(w => w.length >= 2 && !LEX.gen.has(w)); if (ws.length >= 3 && TOPLG.includes(t.lg)) { const ini = ws.map(w => w[0]).join(""); if (ini.length >= 3 && ini.length <= 4 && !collides(ini, kbA) && !allTok.has(ini))
      addC("takim", ini, t.n, { q: `${ini} maçı`, k: "takim", c: { team: t.n }, need: { teams: [t.n] }, kaynak: "takim-basharf" }); }
  }
  // c) ligler: bültende maçı olan ligin adı ("norveç eliteserien", "eliteserien") — tek bir lige gidiyorsa
  const byLg = {}; for (const m of W.m) { (byLg[m.lg] = byLg[m.lg] || { n: 0, labs: new Set() }).n++; byLg[m.lg].labs.add(m.lab); }
  LGLAB = Object.fromEntries(Object.entries(byLg).map(([k, v]) => [k, [...v.labs]]));
  const GENLG = new Set("lig ligi league premier super pro primera division liga ligue serie profesyonel futbol ulusal national kupa kupasi a b c i ii 1 2 3 adalari".split(" "));
  const formsOf = lab => { const n = N(lab).replace(/\b(kapanis|acilis|final)\b/g, " ").replace(/\s+/g, " ").trim(); const ws = n.split(" "); const out = [n];
    if (ws.length >= 2) { const rest = ws.slice(1); if (rest.some(w => w.length >= 4 && !GENLG.has(w) && !LEX.stop.has(w))) out.push(rest.join(" ")); }
    return out; };
  const phraseLg = {}; for (const [lg, v] of Object.entries(byLg)) for (const lab of v.labs) for (const f of formsOf(lab)) (phraseLg[f] = phraseLg[f] || new Set()).add(lg);
  let nL = 0;
  const lgOrder = Object.entries(byLg).sort((a, b) => (TOPLG.includes(a[0]) ? 0 : 1) - (TOPLG.includes(b[0]) ? 0 : 1) || b[1].n - a[1].n);
  for (const [lg, v] of lgOrder) { if (v.n < 2 || !W.lgs[lg] || nL >= 30) continue;
    for (const lab of v.labs) { if (/women|kadin|\(k\)|amator|group|grup|juvenil|u\d\d/i.test(N(lab))) continue;
      for (const f of formsOf(lab)) { if (!f || f.length < 5 || /^\d+$/.test(f) || LEX.botlg.has(f) || phraseLg[f].size > 1 || (kbA && kbA.lig && kbA.lig[f])) continue;
        if (f.split(" ").every(w => LEX.stop.has(w) || GENLG.has(w))) continue;
        addC("lig", f, lg, { q: `${f} maçları`, k: "lig", c: { lgCode: lg }, need: { lg }, kaynak: "lig" }); nL++; } } }
  // d) kalıp cümleler ve eş anlamlılar (banka; her gece en fazla 45 yeni cümle)
  let nP = 0;
  for (const b of BANK.para) { if (nP >= 45) break; if (seenQ.has(N(b.q))) continue;
    addC("para", b.q, b.canon, { q: b.q, k: b.k, c: cSer(b.c), kaynak: "kalip" }); nP++; }
  // e) terimler
  for (const g of BANK.sozluk) { if (kbA && (kbA.sozluk || []).some(x => x.k === g.k)) continue;
    addC("sozluk", g.k, g, { q: g.q, k: "terim", c: cSer({ kw: g.kw, kw2: g.kw2 }), kaynak: "terim" }); }
  // f) yazım hataları (her gece 3 tane, tarihle değişir)
  let nY = 0;
  for (const [w, tpl, k, c] of BANK.yazimKelime.slice().sort(() => R() - .5)) { if (nY >= 3) break;
    for (const ty of typos(w, R)) { if (collides(ty, kbA) || LEX.sl.has(ty) || BANK.yazimKelime.some(x => x[0] === ty)) continue;
      addC("yazim", ty, w, { q: tpl.replace("{w}", ty), k, c: cSer(c), kaynak: "yazim" }); nY++; break; } }
  // g) saf testler: günün takımları, maç analizi, tarih biçimleri (bilgi eklemez, test kümesini büyütür)
  const top = W.m.slice().sort((a, b) => (TOPLG.includes(a.lg) ? 0 : 1) - (TOPLG.includes(b.lg) ? 0 : 1) || b.cp - a.cp);
  const shortOf = n => { const d = distinct(n).filter(w => tokCount[w] === 1); return d.length ? d.sort((a, b) => b.length - a.length)[0] : null; };
  let nT = 0; for (const m of top) { if (nT >= 8) break; const name = R() < .5 ? m.h : m.a, s = shortOf(name); if (!s) continue;
    addT({ q: `${s} maçı`, k: "takim", c: { team: name }, need: { teams: [name] }, kaynak: "gunun-takimi" }); nT++; }
  let nA = 0; for (const m of top) { if (nA >= 5) break; const a = shortOf(m.h), b = shortOf(m.a); if (!a || !b) continue;
    addT({ q: `${a} ${b} ${["ne olur", "kim kazanır", "maçı analiz", "skor tahmini"][nA % 4]}`, k: "analiz", c: { teams: [m.h, m.a] }, need: { match: [m.h, m.a] }, kaynak: "gunun-maci" }); nA++; }
  const wdTr = ["pazar", "pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi"];
  for (let k = 2; k <= 6; k++) { const wd = dayAt(k).getUTCDay(); const forms = [`${N(wdTr[wd])} maclari`, `{D+${k}} için tahmin`, `${k} gün sonra ne var`, `{DOT+${k}} tahminleri`];
    const f = forms[Math.floor(R() * forms.length)]; addT({ q: f, k: "tarih", c: { day: [f === forms[0] ? WDN[wd] : `+${k}`] }, kaynak: "tarih" }); }
  const on = notable(W)[0];   // öne çıkan maç sorusu (bilgi bankasındaki "onemli" listesini sınar)
  if (on) addT({ q: ["günün önemli maçı hangisi", "bugünün büyük maçı", "öne çıkan maçlar neler"][Math.floor(R() * 3)], k: "onemli", c: {}, need: { match: [on.h, on.a] }, kaynak: "onemli" });
  return { C, pure };
}

// öne çıkan maçlar: büyük takımlar / üst lig
function notable(W) {
  const big = n => BANK.buyuk.some(b => N(n).includes(N(b)));
  const sc = m => (TOPLG.slice(0, 9).includes(m.lg) ? 2 : 0) + (big(m.h) ? 2 : 0) + (big(m.a) ? 2 : 0) + (istDay(m.t) === TODAY ? 1 : 0);
  return W.m.filter(m => istDay(m.t) <= istDay(Date.parse(TODAY + "T12:00:00+03:00") + 864e5)).map(m => ({ m, s: sc(m) })).filter(x => x.s >= 4)
    .sort((a, b) => b.s - a.s || a.m.t - b.m.t).slice(0, 5).map(x => ({ h: x.m.h, a: x.m.a, lg: x.m.lg, d: istDay(x.m.t) }));
}

function fillGloss(g) {
  const D = jl("daily.json", {}) || {}, T = D.toplam || {}, Rs = jl("research.json", {}) || {};
  const karne = T.n ? ` Kilitli arşivde şimdiye kadar ${T.n.toLocaleString("tr-TR")} öneri puanlandı; %${Math.round((T.hit || 0) * 100)}'i tuttu.` : "";
  const dv = { power: "power", prop: "oransal", shin: "Shin", hibrit: "hibrit" }[Rs.devig] || Rs.devig;
  return { k: g.k, re: g.re, html: g.html.replace("{karne}", karne).replace("{devig}", dv ? ` Şu an kullanılan ayıklama yöntemi: <b>${dv}</b> (araştırmacı bot her gece sınar).` : "") };
}
function mergeKB(base, fixes) {
  const kb = JSON.parse(JSON.stringify(base || {}));
  for (const s of ["takim", "esanlam", "yazim", "lig", "para"]) kb[s] = kb[s] || {};
  kb.sozluk = kb.sozluk || []; kb.gor = kb.gor || {};
  for (const f of fixes) {
    if (f.sec === "sozluk") { kb.sozluk = kb.sozluk.filter(x => x.k !== f.val.k).concat([fillGloss(f.val)]); continue; }
    kb[f.sec][f.key] = f.val; if (f.sec === "takim") kb.gor[f.key] = TODAY;
  }
  return kb;
}
function finalizeKB(kb, W) {
  // görülmeyen takım adları 60 gün sonra silinir; terim metinleri günün verisiyle tazelenir
  const alive = new Set(W.teams.map(t => t.n));
  for (const [k, v] of Object.entries(kb.takim || {})) { if (alive.has(v)) kb.gor[k] = TODAY; else if (kb.gor[k] && (Date.parse(TODAY) - Date.parse(kb.gor[k])) / 864e5 > 60) { delete kb.takim[k]; delete kb.gor[k]; } }
  kb.sozluk = (kb.sozluk || []).map(g => { const b = BANK.sozluk.find(x => x.k === g.k); return b ? fillGloss(b) : g; });
  kb.onemli = notable(W);
  const D = jl("daily.json", {}) || {}, T = D.toplam || {};
  kb.karne = T.n ? { n: T.n, hit: T.hit, guclu_n: T.guclu_n || 0, guclu_hit: T.guclu_hit || null } : null;
  kb.sayim = { takim: Object.keys(kb.takim).length, lig: Object.keys(kb.lig).length, esanlam: Object.keys(kb.esanlam).length, yazim: Object.keys(kb.yazim).length, para: Object.keys(kb.para).length, sozluk: kb.sozluk.length };
  kb.sayim.toplam = Object.values(kb.sayim).reduce((a, b) => a + b, 0);
  kb.v = kb.v || `${TODAY}.aday`; kb.tarih = TODAY; kb.uretim = new Date().toISOString();
  kb.not = "Bu dosya her gece lab/bot_coach.mjs tarafından yalnız uygulama verisinden üretilir; kullanıcı mesajı içermez.";
  return kb;
}

// ---------------- ana akış ----------------
const kbA = jl("bot_kb.json", null);
const coachPrev = jl("bot_coach.json", { gecmis: [] }) || { gecmis: [] };
const genStore = jl("bot_tests.json", { v: 1, testler: [] }) || { v: 1, testler: [] };
const srv = await serve(); const port = srv.address().port;
const browser = await chromium.launch();
let report = null;
try {
  // 1) dünkü bankayla aç, günün dünyasını oku
  const A = await openPage(browser, port, kbA, coachPrev.son ? coachPrev : null);
  if (!ONLY_EVAL && !(await A.p.evaluate(() => !!window.BOT70))) throw new Error("index.html'de bot-v70 katmanı yok");
  const W = await world(A.p);
  log(`saat ${NOW.toISOString()}${DDAYS ? ` (veri ${DDAYS.from} … ${DDAYS.to})` : ""}`);
  log(`gün ${TODAY}: ${W.m.length} tahminli maç (3 gün), ${W.teams.length} takım, altın: ${W.gold}`);
  // 2) sınanacak test kümesi
  const fresh = d => !d || (Date.parse(TODAY) - Date.parse(d)) / 864e5 <= 21;
  let gen = genStore.testler.filter(t => !t.need || fresh(t.eklendi));      // veriye bağlı üretilmiş sorular 21 gün sonra emekli olur
  const nBad = gen.filter(t => !aliasTestOk(t)).length; if (nBad) { log(`${nBad} üretilmiş test yanlış takıma bağlı (kısaltma hatası), atlandı`); gen = gen.filter(aliasTestOk); }
  const staticConvs = SUITE.core.concat(SUITE.holdout);
  const toConvs = (list) => list.map(t => [prep(t)]);
  if (ONLY_EVAL) {
    const byM = {}; W.m.forEach(m => (byM[m.lg] = byM[m.lg] || new Set()).add(m.lab)); LGLAB = Object.fromEntries(Object.entries(byM).map(([k, v]) => [k, [...v]]));
    const r = await runSuite(A.p, staticConvs.map(cv => cv.map(prep)).concat(toConvs(gen)), "değerlendirme");
    fs.writeFileSync(path.join(process.env.BOT_COACH_OUT || HERE, "bot_eval.json"), JSON.stringify(r, null, 1));
    log(`pageerror: ${A.errs.length}`, A.errs.slice(0, 5)); await browser.close(); srv.close(); process.exit(0);
  }
  // 3) adaylar
  const { C, pure } = candidates(W, kbA, gen.map(t => t.q));
  log(`aday: ${C.length} bilgi (${Object.entries(C.reduce((a, c) => (a[c.sec] = (a[c.sec] || 0) + 1, a), {})).map(([k, v]) => k + " " + v).join(", ")}), ${pure.length} saf test`);
  // 3a) adayların sorularını dünkü bankayla sor
  await setKB(A.p, kbA);
  const candConvs = C.map(c => [prep(c.test)]);
  const okNeed = await needs(A.p, candConvs);
  const C2 = C.filter((c, i) => okNeed[i]);
  const resA = []; for (const c of C2) resA.push((await runConv(A.p, [prep(c.test)]))[0]);
  const passA = C2.filter((c, i) => resA[i].intent && resA[i].useful), failA = C2.filter((c, i) => !(resA[i].intent && resA[i].useful));
  // 3b) kalıp cümle yanlışsa önce genel eş anlamlıyı dene (daha çok cümleye yarar)
  const synFix = [];
  for (const c of failA.filter(c => c.sec === "para")) {
    const nq = N(c.test.q), toks = nq.split(" ");
    for (const [k, v] of Object.entries(BANK.esanlam)) if (toks.includes(k) && !(kbA && kbA.esanlam && kbA.esanlam[k])) synFix.push({ sec: "esanlam", key: k, val: v, forQ: c.test.q });
    for (const [k, v] of Object.entries(BANK.esanlamIfade)) if (` ${nq} `.includes(` ${k} `) && !(kbA && kbA.esanlam && kbA.esanlam[k])) synFix.push({ sec: "esanlam", key: k, val: v, forQ: c.test.q });
  }
  const accepted = [], learnedTests = [], failed = [];
  if (synFix.length) {
    await setKB(A.p, mergeKB(kbA, synFix));
    for (const c of failA.filter(c => c.sec === "para")) { const r = (await runConv(A.p, [prep(c.test)]))[0]; if (r.intent && r.useful) { c.bySyn = true; } }
  }
  // 3c) tüm düzeltmeleri birlikte dene: önce eş anlamlı (genel), sonra kalıp/ad/lig/terim/yazım
  const fixes = [];
  const usedSyn = new Set();
  for (const c of failA) { if (c.sec === "para" && c.bySyn) { for (const s of synFix.filter(s => s.forQ === c.test.q)) if (!usedSyn.has(s.key)) { usedSyn.add(s.key); fixes.push(s); } } else fixes.push(c); }
  await setKB(A.p, finalizeKB(mergeKB(kbA, fixes), W));
  const keep = new Set();
  for (const c of failA) { const r = (await runConv(A.p, [prep(c.test)]))[0]; if (r.intent && r.useful) { learnedTests.push(c.test); if (!(c.sec === "para" && c.bySyn)) keep.add(c); } else failed.push(c.test.q); }
  // kabul: soruyu düzelten bilgiler (eş anlamlılar, bir cümleyi düzelttiyse)
  for (const f of fixes) { if (f.forQ) { if (learnedTests.some(t => t.q === f.forQ)) accepted.push(f); } else if (keep.has(f)) accepted.push(f); }
  log(`sınama: ${passA.length} zaten doğru, ${accepted.length} yeni bilgi kabul, ${failed.length} öğrenilemedi`);
  // 3d) sabit kümede bölüm bazlı gerileme taraması: gerileten tek tek bilgileri ayıkla
  const newTests = passA.map(c => c.test).concat(learnedTests, pure).map(t => Object.assign({}, t, { eklendi: TODAY }));
  const allGen = gen.concat(newTests);
  const suiteConvs = staticConvs.map(cv => cv.map(prep)).concat(toConvs(allGen));
  // 4) KAPI: dünkü banka (A) ile yeni banka (B) aynı sorularla. Yayın koşulu: niyet ve faydalı oranı düşmez,
  //    A'nın doğru bildiği HİÇBİR soru B'de yanlışa dönmez (iki kez sorularak doğrulanır), sayfa hatası yok.
  await setKB(A.p, kbA); A.errs.length = 0;
  const RA = await runSuite(A.p, suiteConvs, "dünkü banka");
  const key = o => o.ci + "|" + o.q, pass = o => o.intent && o.useful;
  const aOk = new Map(RA.out.map(o => [key(o), pass(o)]));
  let fixSet = accepted.slice(), kbB = finalizeKB(mergeKB(kbA, fixSet), W), RB = null, Bp = null, tries = 0, why = "", regN = 0;
  while (true) {
    Bp = await openPage(browser, port, kbB, coachPrev.son ? coachPrev : null);   // yeni banka, gerçek yükleme yolundan
    RB = await runSuite(Bp.p, suiteConvs, `yeni banka${tries ? " (ayıklanmış)" : ""}`);
    let regCi = [...new Set(RB.out.filter(o => aOk.get(key(o)) && !pass(o)).map(o => o.ci))];
    if (regCi.length) { const still = []; for (const i of regCi) { const rr = await runConv(Bp.p, suiteConvs[i]); if (!rr.every(pass)) still.push(i); } regCi = still; }
    regN = regCi.length;
    const better = RB.tot.i * RA.tot.n >= RA.tot.i * RB.tot.n && RB.tot.u * RA.tot.n >= RA.tot.u * RB.tot.n;
    const ok = better && regN === 0 && Bp.errs.length === 0 && RB.tot.n === RA.tot.n;
    if (ok) break;
    why = Bp.errs.length ? `sayfa hatası: ${Bp.errs[0]}` : regN ? `${regN} soru dünkü bankada doğruyken yeni bankada yanlışa döndü` : `test başarısı düştü (niyet %${pc(RA.tot.i, RA.tot.n)}→%${pc(RB.tot.i, RB.tot.n)}, faydalı %${pc(RA.tot.u, RA.tot.n)}→%${pc(RB.tot.u, RB.tot.n)})`;
    if (tries >= 2 || !fixSet.length || Bp.errs.length || !regN) break;
    // suçlu arama: her yeni bilgiyi tek tek çıkarıp yalnız gerileyen sorularda dene; çıkarılınca düzelen bilgi atılır
    const regConvs = regCi.map(i => suiteConvs[i]);
    log(`gerileme: ${regConvs.length} konuşma; suçlu bilgi aranıyor`);
    const drop = new Set();
    for (const f of fixSet.slice(0, 150)) {
      await setKB(Bp.p, finalizeKB(mergeKB(kbA, fixSet.filter(x => x !== f && !drop.has(x))), W));
      for (const cv of regConvs) { const rr = await runConv(Bp.p, cv); if (rr.every(pass)) { drop.add(f); break; } }
    }
    await Bp.ctx.close(); fixSet = fixSet.filter(f => !drop.has(f)); kbB = finalizeKB(mergeKB(kbA, fixSet), W); tries++; why = "";
    log(`${drop.size} bilgi ayıklandı, yeniden deneniyor`);
  }
  const publish = !why;
  const cnt = fixSet.reduce((a, f) => (a[f.sec] = (a[f.sec] || 0) + 1, a), {});
  const yeni = publish ? fixSet.length : 0;
  const kbV = publish ? `${TODAY}.${((kbA && kbA.surum_no) || 0) + 1}` : (kbA && kbA.v) || null;
  if (publish) { kbB.v = kbV; kbB.surum_no = ((kbA && kbA.surum_no) || 0) + 1; }
  const byK = Object.fromEntries(Object.entries(RB.byK).map(([k, a]) => [k, { n: a.n, niyet: pc(a.i, a.n), faydali: pc(a.u, a.n) }]));
  const R0 = publish ? RB : RA;
  report = {
    tarih: TODAY, saat: new Date().toISOString(), n: RB.tot.n, niyet: pc(RB.tot.i, RB.tot.n), faydali: pc(RB.tot.u, RB.tot.n), anlamadi: pc(RB.tot.x, RB.tot.n),
    onceki: { n: RA.tot.n, niyet: pc(RA.tot.i, RA.tot.n), faydali: pc(RA.tot.u, RA.tot.n) },
    sabit: { n: RB.sab.n, niyet: pc(RB.sab.i, RB.sab.n), faydali: pc(RB.sab.u, RB.sab.n), onceki_niyet: pc(RA.sab.i, RA.sab.n), onceki_faydali: pc(RA.sab.u, RA.sab.n) }, gerileme: regN,
    yeni, eklenen: { takim: cnt.takim || 0, lig: cnt.lig || 0, esanlam: cnt.esanlam || 0, yazim: cnt.yazim || 0, para: cnt.para || 0, sozluk: cnt.sozluk || 0 },
    denenen: C2.length, zaten_dogru: passA.length, ogrenilemedi: failed.length, yeni_soru: newTests.length,
    test_sayisi: { sabit: staticConvs.flat().length, uretilen: allGen.length, uygulanamaz: RB.skip },
    yayin: publish, neden: why || "niyet ve faydalı cevap oranı düşmedi, sayfa hatası yok", kb_v: kbV, pageerror: Bp.errs.length, sure_sn: Math.round((Date.now() - T0) / 1000), kategoriler: byK,
  };
  log(JSON.stringify({ yayin: publish, yeni, n: report.n, once: report.onceki, sonra: { niyet: report.niyet, faydali: report.faydali }, neden: report.neden }));
  if (!DRY) {
    if (publish) jw("bot_kb.json", kbB);
    jw("bot_tests.json", { v: 1, not: "Sohbet koçunun her gece ürettiği test soruları (uygulama verisinden; kullanıcı mesajı yok).", testler: allGen.slice(-900).map(t => ({ q: t.q, k: t.k, c: cSer(t.c), need: t.need || null, eklendi: t.eklendi, kaynak: t.kaynak || null })) });
    const pubScore = publish ? { tarih: TODAY, n: R0.tot.n, niyet: pc(R0.tot.i, R0.tot.n), faydali: pc(R0.tot.u, R0.tot.n), kb_v: kbV } : (coachPrev.yayin || { tarih: TODAY, n: RA.tot.n, niyet: pc(RA.tot.i, RA.tot.n), faydali: pc(RA.tot.u, RA.tot.n), kb_v: kbV });
    const hist = (coachPrev.gecmis || []).filter(h => h.tarih !== TODAY).concat([{ tarih: TODAY, n: report.n, niyet: report.niyet, faydali: report.faydali, onceki_niyet: report.onceki.niyet, onceki_faydali: report.onceki.faydali, yeni, yayin: publish, kb_v: kbV }]).slice(-120);
    jw("bot_coach.json", { not: "Sohbet koçu raporu: her gece yeni bilgi bankası, dünkü bankayla aynı sorularda karşılaştırılır; düşüş varsa yayınlanmaz.", son: report, yayin: pubScore, gecmis: hist });
    if (publish && yeni > 0) {
      const G = jl("gelisim.json", { olaylar: [] }) || { olaylar: [] }; const ev = G.olaylar || (G.olaylar = []); const key = `${TODAY}-botkb`;
      const parts = [["takim", "takım adı"], ["lig", "lig adı"], ["esanlam", "eş anlamlı kelime"], ["yazim", "yazım hatası"], ["para", "kalıp cümle"], ["sozluk", "terim"]].filter(([k]) => report.eklenen[k]).map(([k, n]) => `${report.eklenen[k]} ${n}`);
      const e = { tarih: TODAY, tur: "ogrenme", baslik: `💬 Sohbet koçu: OXXai ${yeni} yeni şey öğrendi`, detay: `${parts.join(", ")}. ${report.n} soruluk testte faydalı cevap %${report.faydali} (önceki banka %${report.onceki.faydali}); başarıyı düşüren bilgi yayınlanmaz.`, anahtar: key };
      const i = ev.findIndex(x => x.anahtar === key); if (i >= 0) ev[i] = e; else ev.push(e);
      G.olaylar = ev.slice(-150); jw("gelisim.json", G);
    }
  }
  if (process.env.BOT_COACH_OUT) fs.writeFileSync(path.join(process.env.BOT_COACH_OUT, "coach_detail.json"), JSON.stringify({ RA, RB, accepted: fixSet.map(f => ({ sec: f.sec, key: f.key, val: f.sec === "sozluk" ? f.val.k : f.val })), failed }, null, 1));
} catch (e) {
  console.error("[koç] hata:", e && e.stack || e);
  if (!DRY && !ONLY_EVAL) { const prev = jl("bot_coach.json", { gecmis: [] }) || { gecmis: [] }; prev.hata = { tarih: TODAY, mesaj: String(e && e.message || e).slice(0, 300) }; try { jw("bot_coach.json", prev); } catch (_) { } }
} finally {
  await browser.close().catch(() => { }); srv.close();
}
process.exit(0);
