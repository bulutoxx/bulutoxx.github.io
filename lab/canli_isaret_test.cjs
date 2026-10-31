// v140 · Canlı altın İŞARET uçtan uca testi (Playwright, 390 px; sahte iddaa canlı bülteni)
// Kullanım: python3 -m http.server 8766 (depo kökünde ya da yayın kopyasında) → node lab/canli_isaret_test.cjs [ekran_görüntüsü_klasörü]
//   (a) 5. dk 0-0, olasılık < %80 → rozet yok · (b) 30. dk 2-0, %80+ → rozet: Canlı sekmesi + bülten satırı + maç penceresi
//   (c) olasılık %78 → rozet kalır (histerezis), %76 → kalkar · (d) 76. dk → rozet yok, "son dakikalarda" notu
//   (e) rozetteki yüzde = satırdaki gösterilen yüzde · sayfa hatası 0 · yatay taşma yok · yeni metinlerde yasak kelime yok
const fs = require("fs"), path = require("path");
let chromium; try { ({ chromium } = require("playwright")); } catch (e) { ({ chromium } = require(path.join(process.env.HOME || "/root", ".npm-global/lib/node_modules/playwright"))); }
const ROOT = path.resolve(__dirname, "..");
const BASE = process.env.BASE || "http://localhost:8766";
const SHOTS = path.resolve(process.argv[2] || path.join(ROOT, "lab", "_shots"));
fs.mkdirSync(SHOTS, { recursive: true });
const T0 = Date.parse("2026-10-26T20:30:00+03:00");
let pass = 0, fail = 0;
const ok = (c, msg) => { c ? pass++ : fail++; console.log(c ? "  ✓" : "  ✗", msg); };
const YASAK = /bahis|ganyan|banko|bulut|kupon/i;

const S = { a: { min: 5, hs: 0, as: 0 }, b: { min: 30, hs: 2, as: 0 } };
function fakeLive(now) {
  const ev = [
    { eventId: 8001, phase: 1, ci: 601, homeTeam: "Alfaspor", awayTeam: "Betaspor", eventDate: Math.floor((now - (S.a.min + 2) * 60e3) / 1000) },
    { eventId: 8002, phase: 1, ci: 601, homeTeam: "Testspor", awayTeam: "Örnekspor", eventDate: Math.floor((now - (S.b.min + 17) * 60e3) / 1000) }];
  const sc = {
    8001: { ht: { c: S.a.hs, ht: 0, co: 1, yc: 0, rc: 0 }, at: { c: S.a.as, ht: 0, co: 0, yc: 0, rc: 0 }, min: S.a.min, sec: 0, s: 2, t: now },
    8002: { ht: { c: S.b.hs, ht: 2, co: 4, yc: 1, rc: 0 }, at: { c: S.b.as, ht: 0, co: 1, yc: 2, rc: 0 }, min: S.b.min, sec: 0, s: S.b.min > 45 ? 3 : 2, t: now } };
  return { data: { events: ev, competitions: { 601: { n: "Test Ligi", cid: "TR" } }, sc } };
}
const fakeSb = { data: { events: [
  { i: 8001, s: 1, m: [{ t: 4, st: 1, s: 1, o: [{ n: "1", odd: 2.5 }, { n: "0", odd: 3.1 }, { n: "2", odd: 2.9 }] }, { t: 4, st: 14, s: 1, sov: 2.5, o: [{ n: "Alt", odd: 1.8 }, { n: "Üst", odd: 1.9 }] }] },
  { i: 8002, s: 1, m: [{ t: 4, st: 1, s: 1, o: [{ n: "1", odd: 1.12 }, { n: "0", odd: 7 }, { n: "2", odd: 19 }] },
    { t: 4, st: 34, s: 1, sov: 3, o: [{ n: "1", odd: 2.1 }, { n: "Olmaz", odd: 4.5 }, { n: "2", odd: 3.2 }] }] }] } };

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, locale: "tr-TR", timezoneId: "Europe/Istanbul" });
  await ctx.addInitScript(() => { localStorage.setItem("bx-terms", JSON.stringify({ v: "2.0", at: Date.now(), kvkk: true, inst: Date.now() })); localStorage.setItem("bx-oxxai-hos", "1"); localStorage.setItem("bx-oxxai-ikon", "1"); localStorage.setItem("bx-coach", "1"); });
  const p = await ctx.newPage(); const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  let now = T0;
  await p.clock.setFixedTime(new Date(now));
  await p.route(/iddaa\.com|espn|jsdelivr|googleapis|gstatic|web3forms|abacus|api\./, r => r.fulfill({ status: 404, body: "" }));
  await p.route(/statisticsv2\.iddaa\.com\/live-results\?sportId=1$/, r => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fakeLive(now)) }));
  await p.route(/sportsbookv2\.iddaa\.com\/sportsbook\/events\?st=1/, r => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fakeSb) }));
  await p.goto(BASE + "/index.html");
  for (let i = 0; i < 60; i++) { const r = await p.evaluate(() => { try { return FIXTURES.length > 0 && typeof window.aiDeco === "function" && typeof window.liveProbs === "function" && !!(DAILY && DAILY.canli); } catch (e) { return false; } }); if (r) break; await p.waitForTimeout(500); }
  const reload = async () => { now += 10e3; await p.clock.setFixedTime(new Date(now)); await p.evaluate(async () => { IDL.lam["8001"] = [1.3, 1.2]; IDL.lam["8002"] = [1.9, 0.95]; await IDL.load(1, true); idlRenderAll(); }); await p.waitForTimeout(250); };
  await p.evaluate(() => { document.querySelector('nav.tabs button[data-v="canli"]').click(); });
  await p.waitForTimeout(500); await reload();
  const row = id => p.evaluate(id => { const r = document.querySelector(`#v-canli .lv-c[data-id="${id}"]`); if (!r) return null; const s = r.querySelector(".ai-seal"), x = r.querySelector(".ai-x");
    const box = [...r.querySelectorAll(".lv-od span")].find(e => ((e.querySelector("u") || {}).textContent || "").replace(/^🔥\s*/, "").trim() === "1");
    return { seal: s ? s.textContent : null, late: x ? x.textContent : null, on: r.classList.contains("ai-on"), box1: box ? (box.querySelector("small") || {}).textContent : null,
      st: window.aiST.get(String(id)) || null, pr: (r.querySelector(".lv-pr") || {}).textContent || "" }; }, id);
  const lgf = await p.evaluate(() => LGF.isaret);
  // eşikler bayraktan (data/canli_altin.json → isaret) okunur; sabit değer yazılmaz (bayrak 0,80 → 0,85 değişince test bozulmasın)
  const DOSYA = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "canli_altin.json"), "utf8")).isaret || {};
  ok(lgf && lgf.esik > 0.5 && lgf.esik < 1 && lgf.kapanis < lgf.esik && lgf.dkmax > 45 && (DOSYA.esik == null || DOSYA.esik === lgf.esik), `bayrak okundu: ${JSON.stringify(lgf && { esik: lgf.esik, kapanis: lgf.kapanis, dkmax: lgf.dkmax, durum: lgf.durum })}`);
  const E = lgf.esik, K = lgf.kapanis, DK = lgf.dkmax, P = x => Math.round(x * 100);
  const ARA = Math.round((K + Math.min(0.01, (E - K) / 2)) * 100) / 100, ALT = Math.round((K - 0.01) * 100) / 100, UST = Math.round((E + 0.01) * 100) / 100;

  // (a)
  let A = await row(8001);
  const pa = await p.evaluate(() => { const m = IDL.byId[1][8001], K = idlPick(m, idlPred(m)); const c = K.all.filter(c => c.o && c.o >= 1.03 && c.p >= .6).sort((a, b) => b.p - a.p)[0]; return c ? liveCal(c.p).p : Math.max(...K.all.map(c => c.p)); });
  ok(A && !A.seal && !A.on && pa < E, `(a) 5. dk 0-0: en iyi seçim %${Math.round(pa * 100)} < %${P(E)} → rozet yok`);
  // (b)
  let B = await row(8002);
  const pctB = B && B.seal ? +(/%(\d+)/.exec(B.seal) || [])[1] : null;
  ok(B && B.seal && B.on && /^ALTIN · MS 1 %\d+$/.test(B.seal.trim()) && pctB >= P(E), `(b) 30. dk 2-0: Canlı sekmesi satırında rozet "${B && B.seal}"`);
  ok(B && B.box1 === "%" + pctB, `(e) rozet yüzdesi = satırdaki MS 1 yüzdesi (${B && B.box1} / %${pctB})`);
  await p.evaluate(() => document.querySelector('#v-canli .lv-c[data-id="8002"]').scrollIntoView({ block: "center" }));
  await p.screenshot({ path: path.join(SHOTS, "isaret_01_canli_satir.png") });
  const note = await p.evaluate(() => (document.querySelector("#idlBox .ai-note") || {}).textContent || "");
  ok(/Canlı altın işaret/.test(note) && new RegExp(DK + "\\. dk sonrası").test(note) && /garanti değildir/.test(note), `Canlı sekmesinde açıklama notu: "${note.slice(0, 80)}…"`);
  // dokununca açıklama, maç açılmaz
  await p.evaluate(() => document.querySelector('#v-canli .lv-c[data-id="8002"] .ai-seal').click());
  await p.waitForTimeout(200);
  const tst = await p.evaluate(() => { const t = document.getElementById("toast"), m = document.getElementById("msheet"); return { t: t && !t.hidden ? t.textContent : "", ms: !!(m && !m.hidden && MS.m) }; });
  ok(/tahmindir, garanti değildir/i.test(tst.t) && !tst.ms, `rozete dokununca kısa açıklama, maç penceresi açılmaz ("${tst.t.slice(0, 60)}…")`);
  // bülten (arama) satırı
  const bt = await p.evaluate(async () => { document.querySelector('nav.tabs button[data-v="bulten"]').click(); await new Promise(r => setTimeout(r, 300)); BT.q = "Testspor"; renderBulten(); await new Promise(r => setTimeout(r, 150));
    const r = document.querySelector('#btList .lv-c[data-id="8002"]'); return r ? { seal: (r.querySelector(".ai-seal") || {}).textContent || null, on: r.classList.contains("ai-on") } : null; });
  ok(bt && bt.seal && bt.seal === B.seal && bt.on, `(b) bülten canlı satırında aynı rozet "${bt && bt.seal}"`);
  await p.evaluate(() => document.querySelector('#btList .lv-c[data-id="8002"]').scrollIntoView({ block: "center" }));
  await p.screenshot({ path: path.join(SHOTS, "isaret_02_bulten_satir.png") });
  // maç penceresi
  const ms = await p.evaluate(async () => { openMatch(IDL.byId[1][8002]); await new Promise(r => setTimeout(r, 600)); const s = document.querySelector("#msheet .ai-ms .ai-seal"); return s ? s.textContent : null; });
  ok(ms && ms === B.seal, `(b) canlı maç penceresinde rozet "${ms}"`);
  await p.screenshot({ path: path.join(SHOTS, "isaret_03_pencere.png") });
  const ovf = async tag => { const o = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, vw: document.documentElement.clientWidth })); ok(o.sw <= o.vw + 1, `${tag}: yatay taşma yok (${o.sw}/${o.vw})`); };
  await ovf("pencere");
  await p.evaluate(() => { closeMatch(); BT.q = ""; document.querySelector('nav.tabs button[data-v="canli"]').click(); });
  await p.waitForTimeout(400);
  await ovf("Canlı sekmesi");

  // (c) histerezis: olasılık zorla %78 → kalır, %76 → kalkar, %78 (kapalıyken) → açılmaz
  await p.evaluate(() => { const _p = idlPred; window.__f = null; idlPred = function (m) { const P = _p.apply(this, arguments); const f = window.__f && window.__f[m.id]; return f != null && P ? Object.assign({}, P, { H: f, D: (1 - f) * .6, A: (1 - f) * .4, nextH: Math.min(P.nextH, .5) }) : P; }; });
  const force = async f => { await p.evaluate(f => { window.__f = { 8002: f }; }, f); await reload(); return row(8002); };
  let C = await force(ARA);
  ok(C && C.seal && new RegExp("%" + P(ARA) + "$").test(C.seal.trim()) && C.box1 === "%" + P(ARA), `(c) %${P(ARA)}'e düştü → rozet kalır (histerezis) "${C && C.seal}", satır ${C && C.box1}`);
  C = await force(ALT);
  ok(C && !C.seal && !C.on, `(c) %${P(ALT)} → rozet kalkar`);
  C = await force(ARA);
  ok(C && !C.seal, `(c) kapalıyken %${P(ARA)} → yeniden açılmaz (açılış eşiği %${P(E)})`);
  C = await force(UST);
  ok(C && C.seal && new RegExp("%" + P(UST) + "$").test(C.seal.trim()), `(c) %${P(UST)} → yeniden açılır "${C && C.seal}"`);
  // bülten satırı: canlı nabız yenilemesinde (IDL.load, yeniden çizim yok) rozet yerinde güncellenir
  const nb = await p.evaluate(async () => { document.querySelector('nav.tabs button[data-v="bulten"]').click(); await new Promise(r => setTimeout(r, 300)); BT.q = "Testspor"; renderBulten();
    const q = () => { const r = document.querySelector('#btList .lv-c[data-id="8002"]'); return r ? ((r.querySelector(".ai-seal") || {}).textContent || "") : "satır yok"; };
    const o = [q()]; window.__f = { 8002: 0.70 }; await IDL.load(1, true); o.push(q()); window.__f = { 8002: 0.90 }; await IDL.load(1, true); o.push(q());
    BT.q = ""; document.querySelector('nav.tabs button[data-v="canli"]').click(); return o; });
  ok(nb[0] && nb[1] === "" && /%90$/.test(nb[2]), `bülten satırı nabız yenilemesinde yerinde güncellenir ${JSON.stringify(nb)}`);
  await p.waitForTimeout(300);
  // (d) 76. dk
  S.b.min = DK + 1; await p.evaluate(() => { window.__f = { 8002: 0.95 }; }); await reload();
  const D = await row(8002);
  ok(D && !D.seal && !D.on && D.late && /Son dakikalarda/.test(D.late), `(d) ${DK + 1}. dk: rozet yok, not "${D && D.late}"`);
  await p.evaluate(() => document.querySelector('#v-canli .lv-c[data-id="8002"]').scrollIntoView({ block: "center" }));
  await p.screenshot({ path: path.join(SHOTS, "isaret_04_76dk.png") });
  const msD = await p.evaluate(async () => { openMatch(IDL.byId[1][8002]); await new Promise(r => setTimeout(r, 500)); const el = $("msheet"); const r = { seal: !!el.querySelector(".ai-ms .ai-seal"), late: (el.querySelector(".ai-ms .ai-x") || {}).textContent || "" }; closeMatch(); return r; });
  ok(!msD.seal && /Son dakikalarda/.test(msD.late), `(d) ${DK + 1}. dk pencerede rozet yok, not görünür`);
  // karne satırı
  const kr = await p.evaluate(() => window.aiKarne());
  ok(/Canlı altın işaret/.test(kr) && /(Veri birikiyor|işaretli maç)/.test(kr), `karne satırı: ${kr.replace(/<[^>]+>/g, "").slice(0, 90)}…`);
  // yasak kelime (yeni metinler)
  const txt = await p.evaluate(() => [...document.querySelectorAll(".ai-l,.ai-ms,.ai-note")].map(e => e.textContent).join(" ") + " " + window.aiKarne().replace(/<[^>]+>/g, " "));
  ok(!YASAK.test(txt + " " + tst.t), "yeni metinlerde yasak kelime yok");
  ok(errs.length === 0, `sayfa hatası 0 ${JSON.stringify(errs.slice(0, 3))}`);
  await b.close();
  console.log(`\nSONUÇ: ${pass} geçti, ${fail} kaldı · ekran görüntüleri: ${SHOTS}`); process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
