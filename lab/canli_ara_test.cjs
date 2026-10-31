// v151 · Canlı arama uçtan uca testi (Playwright; sahte iddaa canlı bülteni + sahte ESPN + gerçek data/fixtures.json)
// Kullanım: python3 -m http.server 8766 (depo kökünde) → node lab/canli_ara_test.cjs [ekran_görüntüsü_klasörü]
//   BASE=http://localhost:8766 · UZUN=0 (30 sn gerçek bekleme testini atlar)
// Saat 31.10.2026 17:38 TSİ'ye sabitlenir (zaman akar): Bayer Leverkusen – VfB Stuttgart 17:30'da başlamış, iddaa canlı listesinde YOK.
const fs = require("fs"), path = require("path");
let chromium; try { ({ chromium } = require("playwright")); } catch (e) { ({ chromium } = require(path.join(process.env.HOME || "/root", ".npm-global/lib/node_modules/playwright"))); }
const ROOT = path.resolve(__dirname, "..");
const BASE = process.env.BASE || "http://localhost:8766";
const UZUN = process.env.UZUN !== "0";
const SHOTS = path.resolve(process.argv[2] || path.join(ROOT, "lab", "_shots"));
fs.mkdirSync(SHOTS, { recursive: true });
const T0 = Date.parse("2026-10-31T17:38:00+03:00");
let pass = 0, fail = 0; const FAILS = [];
const ok = (c, msg) => { if (c) { pass++; console.log("  ✓", msg); } else { fail++; FAILS.push(msg); console.log("  ✗", msg); } };
const YASAK = /bahis|ganyan|banko|bulut|kupon/i;

function fakeLive(sp, now) {
  const s = Math.floor(now / 1000);
  if (sp === 2) return { data: { events: [
    { eventId: 8001, phase: 1, ci: 701, homeTeam: "Anadolu Efes", awayTeam: "Fenerbahçe Beko", eventDate: s - 50 * 60 },
    { eventId: 8002, phase: 1, ci: 702, homeTeam: "Real Madrid", awayTeam: "Olympiacos", eventDate: s - 40 * 60 }],
    competitions: { 701: { n: "Türkiye Basketbol Süper Ligi", cid: "TR" }, 702: { n: "EuroLeague", cid: "EU" } },
    sc: { 8001: { ht: { c: 61, qs: [{ s: 20 }, { s: 21 }, { s: 20 }] }, at: { c: 58, qs: [{ s: 19 }, { s: 20 }, { s: 19 }] }, min: 28, sec: 0, s: 5, t: now },
      8002: { ht: { c: 40 }, at: { c: 38 }, min: 18, sec: 0, s: 3, t: now } } } };
  return { data: { events: [
    { eventId: 7001, phase: 1, ci: 501, homeTeam: "Bayern Münih (K)", awayTeam: "Real Madrid (K)", eventDate: s - 53 * 60 },
    { eventId: 7002, phase: 1, ci: 502, homeTeam: "Beşiktaş", awayTeam: "Trabzonspor", eventDate: s - 23 * 60 }],
    competitions: { 501: { n: "UEFA Kadınlar Şampiyonlar Ligi", cid: "EU" }, 502: { n: "Türkiye Süper Lig", cid: "TR" } },
    sc: { 7001: { ht: { c: 1, ht: 1, co: 4, yc: 0, rc: 0 }, at: { c: 2, ht: 2, co: 0, yc: 1, rc: 0 }, min: 38, sec: 0, s: 2, t: now },
      7002: { ht: { c: 0, ht: 0, co: 2, yc: 0, rc: 0 }, at: { c: 1, ht: 0, co: 1, yc: 1, rc: 0 }, min: 23, sec: 0, s: 2, t: now } } } };
}
const espnLev = now => ({ events: [{ id: "777001", date: new Date(T0 - 8 * 60e3).toISOString(), status: { displayClock: "9'", type: { state: "in", shortDetail: "9'" } },
  competitions: [{ competitors: [{ homeAway: "home", team: { id: "1", displayName: "Bayer Leverkusen" }, score: "1" }, { homeAway: "away", team: { id: "2", displayName: "VfB Stuttgart" }, score: "0" }] }] }] });

async function run(vw, vh, tag, espn) {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: 1, locale: "tr-TR", timezoneId: "Europe/Istanbul", hasTouch: vw < 900, isMobile: vw < 900 });
  await ctx.addInitScript(t0 => {
    const RD = Date, off = t0 - RD.now();
    class FD extends RD { constructor(...a) { if (a.length) super(...a); else super(RD.now() + off); } static now() { return RD.now() + off; } }
    window.Date = FD;
    localStorage.setItem("bx-terms", JSON.stringify({ v: "2.0", at: Date.now(), kvkk: true, inst: Date.now() })); localStorage.setItem("bx-oxxai-hos", "1"); localStorage.setItem("bx-oxxai-ikon", "1"); localStorage.setItem("bx-coach", "1");
  }, T0);
  const p = await ctx.newPage(); const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  const req = { l1: 0 };
  await p.route(/iddaa\.com|espn|jsdelivr|googleapis|gstatic|web3forms|abacus|api\./, r => r.fulfill({ status: 404, body: "" }));
  await p.route(/statisticsv2\.iddaa\.com\/live-results\?sportId=(\d)/, r => { const sp = +/sportId=(\d)/.exec(r.request().url())[1]; if (sp === 1) req.l1++; r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fakeLive(sp, Date.now() + (T0 - Date.now()))) }); });
  await p.route(/sportsbookv2\.iddaa\.com\/sportsbook\/events/, r => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ data: { events: [] } }) }));
  await p.route(/site\.api\.espn\.com\/apis\/site\/v2\/sports\/soccer\/[^/]+\/scoreboard/, r => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(espn && /ger\.1\//.test(r.request().url()) ? espnLev() : { events: [] }) }));
  await p.goto(BASE + "/index.html");
  for (let i = 0; i < 60; i++) { const r = await p.evaluate(() => { try { return FIXTURES.length > 0 && IDL.ok[1]; } catch (e) { return false; } }); if (r) break; await p.waitForTimeout(500); }
  await p.evaluate(() => { const g = document.getElementById("gate"); if (g) g.remove(); });
  if (espn) await p.evaluate(async () => { try { await Pick.loadEspn(); } catch (e) {} });
  await p.evaluate(() => document.querySelector('nav.tabs button[data-v="canli"]').click());
  await p.waitForTimeout(1200);
  const box = async () => p.evaluate(() => {
    const t = id => { const e = document.getElementById(id); return e ? e.innerText : ""; };
    const i = document.getElementById("cvQi");
    const nx = [...document.querySelectorAll("#nxBox .fxrow")].map(r => r.innerText.replace(/\s+/g, " ")).join("\n");
    return { idl: t("idlBox"), nx, nxAll: t("nxBox"), val: i && i.value, foc: document.activeElement === i, q: IDLV.q, x: !(document.getElementById("cvQx") || {}).hidden };
  });
  const yaz = async q => { await p.click("#cvQi", { clickCount: 3 }); await p.keyboard.press("Control+A"); await p.keyboard.press("Backspace"); await p.keyboard.type(q, { delay: 25 }); await p.waitForTimeout(900); };
  const both = s => s.idl + "\n" + s.nx;

  // 1) futbol aramaları
  const CASES = [
    ["Leverkusen", s => /Leverkusen/.test(s.nx) && /Stuttgart/.test(s.nx) && (espn ? /1-0/.test(s.nx) : /canlı skor bekleniyor/.test(s.nx))],
    ["leverkusen", s => /Leverkusen/.test(s.nx)],
    ["Stuttgart", s => /Leverkusen/.test(s.nx)],
    ["B. Leverkusen", s => /Leverkusen/.test(s.nx)],
    ["Bayer 04", s => /Leverkusen/.test(s.nx)],
    ["fenerbahce", s => /Fenerbahçe/.test(s.nx) && /G[oö]ztep/.test(s.nx)],
    ["besiktas", s => /Beşiktaş/.test(s.idl)],
    ["Real Madrid", s => /Real Madrid Kadın/.test(s.idl) && /Racing Santander/.test(s.nx)],
    ["Münih", s => /Bayern Münih/.test(s.idl) && /Bayern München/.test(s.nx)],
    ["Bundesliga", s => /Leverkusen/.test(s.nx) && /Dortmund/.test(s.nx)],
  ];
  for (const [q, f] of CASES) { await yaz(q); const s = await box(); const g = f(s) && s.val === q; ok(g, `${tag} "${q}" → beklenen maç (${(s.nx.match(/[^\n]*(Leverkusen|Fenerbahçe|Racing Santander|Dortmund|München)[^\n]*/) || [""])[0].slice(0, 70)})`); if (!g) console.log("     q/val:", s.q, "/", s.val, "\n     idl:", s.idl.replace(/\s+/g, " ").slice(0, 200), "\n     nx:", s.nxAll.replace(/\s+/g, " ").slice(0, 200)); }

  // 2) başlamış maç satırına dokununca maç penceresi
  await yaz("Leverkusen");
  await p.screenshot({ path: path.join(SHOTS, `${tag}_leverkusen.png`) });
  const gap = await p.evaluate(() => { const a = { bottom: Math.max(...[...document.getElementById("idlBox").children].map(c => c.getBoundingClientRect().bottom)) }, n = document.getElementById("nxBox").getBoundingClientRect(); return Math.round(n.top - a.bottom); });
  ok(gap >= 0 && gap < 60, `${tag} sonuçlar canlı listenin hemen altında (boşluk ${gap}px)`);
  const opened = await p.evaluate(() => { const r = document.querySelector("#nxBox .nx-st [data-om]"); if (!r) return "satır yok"; r.click(); const el = document.getElementById("msheet"); return !!(el && !el.hidden && /Leverkusen/.test(el.innerText)); });
  ok(opened === true, `${tag} başlamış maç satırı maç penceresini açıyor (${opened})`);
  if (opened === true) await p.evaluate(() => { try { history.back(); } catch (e) {} });
  await p.waitForTimeout(400);

  // 3) yenilemede kalıcılık (10 sn Canlı + 15 sn nabız döngüleri)
  await yaz("Leverkusen");
  const s0 = await box(); const l0 = req.l1;
  if (UZUN) await p.waitForTimeout(31000); else { await p.evaluate(async () => { await IDL.load(1, true); idlRenderAll(); }); await p.waitForTimeout(500); }
  const s1 = await box();
  ok(s1.val === "Leverkusen" && s1.q === "Leverkusen" && s1.foc && s1.nx === s0.nx && s1.idl.replace(/Güncellendi.*|\d\d:\d\d:\d\d/g, "") === s0.idl.replace(/Güncellendi.*|\d\d:\d\d:\d\d/g, ""),
    `${tag} ${UZUN ? "31 sn" : "zorla yenileme"} sonra sonuç, değer ve odak korunuyor (canlı istek +${req.l1 - l0}, odak ${s1.foc})`);

  // 4) sekme değişip dönünce
  await p.evaluate(() => document.querySelector('nav.tabs button[data-v="bulten"]').click()); await p.waitForTimeout(500);
  await p.evaluate(() => document.querySelector('nav.tabs button[data-v="canli"]').click()); await p.waitForTimeout(800);
  const s2 = await box(); ok(s2.val === "Leverkusen" && s2.q === "Leverkusen" && /Leverkusen/.test(s2.nx) && !/Bayern Münih/.test(s2.idl), `${tag} sekme dönüşünde arama ve süzme tutarlı`);

  // 5) Enter / Esc / temizle
  await p.click("#cvQi"); await p.keyboard.press("Control+A"); await p.keyboard.type("stuttgart"); await p.keyboard.press("Enter"); await p.waitForTimeout(80);
  const s3 = await box(); ok(s3.q === "stuttgart" && /Leverkusen/.test(s3.nx), `${tag} Enter hemen uygular`);
  await p.click("#cvQi"); await p.keyboard.press("Escape"); await p.waitForTimeout(400);
  const s4 = await box(); ok(s4.val === "" && s4.q === "" && /Beşiktaş/.test(s4.idl) && /Bayern Münih/.test(s4.idl) && !s4.x, `${tag} Esc temizler`);
  await yaz("Trabzon"); const s5a = await box();
  await p.click("#cvQx"); await p.waitForTimeout(400); const s5 = await box();
  ok(/Trabzon/.test(s5a.idl) && !/Bayern Münih/.test(s5a.idl) && s5.val === "" && s5.q === "" && /Bayern Münih/.test(s5.idl), `${tag} ✕ temizle düğmesi`);

  // 6) basketbol
  await p.evaluate(() => document.querySelector('#idlBox [data-sp="2"]').click()); await p.waitForTimeout(900);
  await yaz("efes"); const s6 = await box();
  ok(/Anadolu Efes/.test(s6.idl) && !/Olympiacos/.test(s6.idl), `${tag} basket "efes" süzülüyor`);
  await yaz("Olimpiakos"); const s7 = await box();
  ok(/Olympiacos/.test(s7.idl) && !/Anadolu Efes/.test(s7.idl), `${tag} basket yazım toleransı "Olimpiakos"`);
  if (UZUN) { await p.waitForTimeout(12000); const s8 = await box(); ok(s8.val === "Olimpiakos" && /Olympiacos/.test(s8.idl) && !/Anadolu Efes/.test(s8.idl), `${tag} basket 12 sn sonra korunuyor`); }
  await p.screenshot({ path: path.join(SHOTS, `${tag}_basket.png`) });
  await p.evaluate(() => document.querySelector('#idlBox [data-sp="1"]').click()); await p.waitForTimeout(500);

  // 7) taşma ve yasak kelime
  await yaz("Leverkusen");
  const ov = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, vw: document.documentElement.clientWidth, t: document.getElementById("v-canli").innerText }));
  ok(ov.sw <= ov.vw + 1, `${tag} yatay taşma yok (${ov.sw}/${ov.vw})`);
  const yk = (ov.t.match(YASAK) || [])[0]; ok(!yk, `${tag} görünür metinde yasak kelime yok${yk ? " (" + yk + ")" : ""}`);
  ok(errs.length === 0, `${tag} sayfa hatası yok ${errs.slice(0, 3).join(" | ")}`);
  await b.close();
}

(async () => {
  const W = (process.env.GEN || "390,1366").split(",").map(Number);
  for (const w of W) { console.log(`\n== ${w}px · ESPN yok ==`); await run(w, w > 900 ? 820 : 844, `w${w}`, false); }
  console.log(`\n== 390px · ESPN skoru var ==`); await run(390, 844, "w390e", true);
  console.log(`\n${pass} geçti, ${fail} kaldı`); if (fail) { console.log(FAILS.join("\n")); process.exit(1); }
})();
