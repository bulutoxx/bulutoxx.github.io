// v180 · Canlı maç SAHA grafiği uçtan uca testi (Playwright, iPhone 13 boyutu; ESPN yanıtları KURGU fixture)
// Kullanım: python3 -m http.server 8767 (depo kökünde ya da yayın kopyasında) → NODE_PATH=/opt/npm-tools/node_modules node lab/saha_test.cjs [ekran_klasörü]
//   (a) konumlu eng.1 senaryosu: Saha sekmesi, işaretler doğru tarafta (ev sağa hücum), şut çizgileri, nabız, dokununca bilgi,
//       son 5 olay, olay tabanlı baskı grafiği · (b) konumsuz tur.1 senaryosu: saha çizilmez, "İstatistikten tahmini" baskı
//   (c) 403 / erişim yok: uyarı, hata yok · (d) bayrak saha:false → sekme yok
//   Her senaryoda: yorum metni (text) hiçbir yerde görünmez/saklanmaz, sayfa hatası 0, yatay taşma yok, yasak kelime yok.
const fs = require("fs"), path = require("path");
let pw; try { pw = require("playwright"); } catch (e) { pw = require(path.join(process.env.HOME || "/root", ".npm-global/lib/node_modules/playwright")); }
const { chromium, devices } = pw;
const ROOT = path.resolve(__dirname, "..");
const BASE = process.env.BASE || "http://localhost:8767";
const SHOTS = path.resolve(process.argv[2] || path.join(ROOT, "lab", "_shots"));
fs.mkdirSync(SHOTS, { recursive: true });
let pass = 0, fail = 0;
const ok = (c, msg) => { c ? pass++ : fail++; console.log(c ? "  ✓" : "  ✗", msg); };
const YASAK = /bahis|ganyan|banko|bulut|kupon/i;
const GIZLI = "GIZLI_YORUM_METNI";

// ---- kurgu ESPN özeti ----
const TEAMS = { en: [{ id: "359", n: "Arsenal" }, { id: "363", n: "Chelsea" }], tr1: [{ id: "432", n: "Galatasaray" }, { id: "436", n: "Fenerbahce" }] };
function rnd(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }
function ozet(lg, dk, opt) {
  const [H, A] = TEAMS[lg], r = rnd(lg === "en" ? 7 : 11);
  const comp = { status: { displayClock: dk + "'", period: dk > 45 ? 2 : 1, type: { state: opt.state || "in" } },
    competitors: [{ homeAway: "home", score: "1", team: { id: H.id, displayName: H.n } }, { homeAway: "away", score: "0", team: { id: A.id, displayName: A.n } }] };
  const box = { teams: [{ homeAway: "home", team: { id: H.id }, statistics: [{ name: "totalShots", displayValue: String(opt.st[0]) }, { name: "shotsOnTarget", displayValue: String(opt.st[1]) }, { name: "wonCorners", displayValue: String(opt.st[2]) }] },
    { homeAway: "away", team: { id: A.id }, statistics: [{ name: "totalShots", displayValue: String(opt.st[3]) }, { name: "shotsOnTarget", displayValue: String(opt.st[4]) }, { name: "wonCorners", displayValue: String(opt.st[5]) }] }] };
  const commentary = [];
  if (opt.konum) {
    const TY = ["shot-on-target", "shot-off-target", "shot-blocked", "corner-awarded", "foul", "offside", "yellow-card", "shot-hit-woodwork"];
    let id = 1;
    for (let m = 1; m <= dk; m++) {
      const n = m % 3 === 0 ? 2 : 1;
      for (let k = 0; k < n; k++) {
        const ev = (m * 7 + k) % 5 < 3 ? H : A, ty = TY[Math.floor(r() * TY.length)];
        let x, y = 15 + r() * 70, x2 = null, y2 = null;
        if (/shot/.test(ty)) { x = 76 + r() * 16; x2 = 100; y2 = 45 + r() * 10; }
        else if (ty === "corner-awarded") { x = 99; y = r() < .5 ? 1 : 99; }
        else if (ty === "foul") x = 20 + r() * 60;
        else x = 40 + r() * 50;
        const play = { id: String(id++), type: { type: ty, text: "Tür" }, text: GIZLI + " " + ty, clock: { value: m * 60 - 30, displayValue: m + "'" }, period: { number: m > 45 ? 2 : 1 },
          team: { displayName: ev.n }, fieldPositionX: +x.toFixed(1), fieldPositionY: +y.toFixed(1) };
        if (x2 != null) { play.fieldPosition2X = x2; play.fieldPosition2Y = +y2.toFixed(1); }
        if (m % 11 === 0 && k === 0) { delete play.fieldPositionX; delete play.fieldPositionY; play.type.type = "substitution"; }
        commentary.push({ sequence: id, text: GIZLI + " uzun yorum", play });
      }
    }
    commentary.push({ text: GIZLI, play: { id: "g1", type: { type: "goal", text: "Goal" }, text: GIZLI, clock: { value: 70 * 60 - 10, displayValue: "70'" }, period: { number: 2 }, team: { displayName: H.n }, fieldPositionX: 91, fieldPositionY: 48, fieldPosition2X: 100, fieldPosition2Y: 50 } });
    commentary.push({ text: GIZLI, play: { id: "z1", type: { type: "shot-on-target", text: "Shot" }, text: GIZLI, clock: { value: dk * 60 - 5, displayValue: dk + "'" }, period: { number: 2 }, team: { displayName: A.n }, fieldPositionX: 88, fieldPositionY: 40, fieldPosition2X: 100, fieldPosition2Y: 52 } });
    commentary.reverse();   // ESPN: en yeni önce
  }
  const keyEvents = opt.konum ? [] : [{ id: "k1", type: { type: "goal" }, text: GIZLI, clock: { value: 1500, displayValue: "25'" }, period: { number: 1 }, team: { displayName: H.n } },
    { id: "k2", type: { type: "yellow-card" }, text: GIZLI, clock: { value: 3300, displayValue: "55'" }, period: { number: 2 }, team: { displayName: A.n } }];
  return { header: { competitions: [comp] }, boxscore: box, commentary, keyEvents };
}

async function senaryo(b, ad, lg, sumFn, ozellik) {
  console.log(`\n— ${ad}`);
  const ctx = await b.newContext({ ...devices["iPhone 13"], locale: "tr-TR", timezoneId: "Europe/Istanbul" });
  await ctx.addInitScript(() => { localStorage.setItem("bx-terms", JSON.stringify({ v: "2.0", at: Date.now(), kvkk: true, inst: Date.now() })); localStorage.setItem("bx-oxxai-hos", "1"); localStorage.setItem("bx-oxxai-ikon", "1"); localStorage.setItem("bx-coach", "1"); });
  const S = { dk: 74, st: [12, 5, 6, 7, 2, 3], konum: lg === "en", n: 0 };
  await ctx.route(/iddaa\.com|jsdelivr|googleapis|gstatic|web3forms|abacus/, r => r.fulfill({ status: 404, body: "" }));
  await ctx.route(/espn\.com\//, r => {
    const u = r.request().url();
    if (/\/summary\?/.test(u)) { S.n++; return sumFn(r, S); }
    return r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ events: [] }) });
  });
  if (ozellik) await ctx.route(/data\/ozellik\.json/, r => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(ozellik) }));
  const p = await ctx.newPage(); const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  await p.goto(BASE + "/index.html");
  for (let i = 0; i < 60; i++) { const r = await p.evaluate(() => { try { return FIXTURES.length > 0 && !!window.sahaV180 && window.sahaV180.FL.bilinen && typeof openMatch === "function"; } catch (e) { return false; } }); if (r) break; await p.waitForTimeout(500); }
  const [H, A] = TEAMS[lg];
  await p.evaluate(({ lg, H, A }) => {
    const d = new Date(Date.now() - 80 * 60e3).toISOString();
    Pick.extra["901" + lg] = { id: "901" + lg, lg, date: d, state: "in", clock: "74'", detail: "74'", h: H.n, a: A.n, hl: "", al: "", hs: 1, as: 0 };
    openMatch({ src: "espn", id: "901" + lg, lg, dt: new Date(d), live: true, clock: "74'", h: H.n, a: A.n, hs: 1, as: 0 });
  }, { lg, H, A });
  await p.waitForTimeout(400);
  return { ctx, p, errs, S };
}
const sekme = p => p.evaluate(() => !!document.querySelector('#msheet .ms-tabs button[data-t="saha"]'));
async function sahaAc(p) { await p.click('#msheet .ms-tabs button[data-t="saha"]'); for (let i = 0; i < 40; i++) { const d = await p.evaluate(() => { const s = window.sahaV180.durum(); return s && s.at && !document.querySelector("#msheet .sh-sp"); }); if (d) break; await p.waitForTimeout(150); } await p.waitForTimeout(200); }
async function ortak(p, errs, tag) {
  const o = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, vw: document.documentElement.clientWidth,
    ms: (() => { const m = document.getElementById("msheet"); return m ? { sw: m.scrollWidth, cw: m.clientWidth } : null; })() }));
  ok(o.sw <= o.vw + 1 && (!o.ms || o.ms.sw <= o.ms.cw + 1), `${tag}: yatay taşma yok (sayfa ${o.sw}/${o.vw}, pencere ${o.ms && o.ms.sw}/${o.ms && o.ms.cw})`);
  const g = await p.evaluate(G => { const s = []; try { for (let i = 0; i < localStorage.length; i++) s.push(localStorage.getItem(localStorage.key(i))); for (let i = 0; i < sessionStorage.length; i++) s.push(sessionStorage.getItem(sessionStorage.key(i))); } catch (e) {}
    const D = JSON.stringify([...window.sahaV180.D.values()].map(x => x.P));
    return { ekran: document.documentElement.outerHTML.includes(G), depo: s.join("").includes(G), bellek: D.includes(G) }; }, GIZLI);
  ok(!g.ekran && !g.depo && !g.bellek, `${tag}: yorum metni ekranda/depoda/katman belleğinde yok ${JSON.stringify(g)}`);
  const txt = await p.evaluate(() => (document.querySelector("#msheet .sh-wrap") || {}).textContent || "");
  ok(!YASAK.test(txt), `${tag}: saha bölümünde yasak kelime yok`);
  ok(errs.length === 0, `${tag}: sayfa hatası 0 ${JSON.stringify(errs.slice(0, 3))}`);
}

(async () => {
  const b = await chromium.launch();
  // (a) konumlu eng.1
  {
    const { ctx, p, errs, S } = await senaryo(b, "(a) eng.1 konumlu canlı maç", "en", (r, S) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(ozet("en", S.dk, S)) }));
    ok(await sekme(p), "(a) maç penceresinde Saha sekmesi var");
    await sahaAc(p);
    const R = await p.evaluate(() => { const el = document.querySelector("#msheet .sh-wrap"); if (!el) return null;
      const M = [...el.querySelectorAll(".sh-svg .sh-m")].map(g => ({ sd: g.dataset.sd, k: g.dataset.k, cx: +g.querySelector(".hit").getAttribute("cx"), yeni: g.classList.contains("yeni") }));
      return { M, tr: el.querySelectorAll(".sh-svg line.tr").length, st: el.querySelectorAll(".sh-svg polygon.st").length, pl: el.querySelectorAll(".sh-svg .pl").length,
        son: [...el.querySelectorAll(".sh-son li")].map(li => li.textContent.replace(/\s+/g, " ").trim()), bas: el.querySelectorAll(".sh-bsvg rect.bh").length, bas2: el.querySelectorAll(".sh-bsvg rect.ba").length,
        tag: (el.querySelector(".sh-bas .sh-tag") || {}).textContent || "", cn: (el.querySelector(".sh-cn") || {}).textContent || "", durum: window.sahaV180.durum() }; });
    ok(R && R.M.length > 5 && R.M.length <= 60, `(a) saha işaretleri çizildi: ${R && R.M.length} (≤ 60) · durum ${JSON.stringify(R && R.durum)}`);
    const sut = R.M.filter(m => /^(sot|off|blk|wood|goal)$/.test(m.k));
    const evS = sut.filter(m => m.sd === "h"), dpS = sut.filter(m => m.sd === "a");
    ok(evS.length > 0 && evS.every(m => m.cx > 75), `(a) ev sahibi şutları sağ (rakip) kalede: ${evS.length} şut, en küçük x ${Math.min(...evS.map(m => m.cx)).toFixed(1)} / 105`);
    ok(dpS.length > 0 && dpS.every(m => m.cx < 30), `(a) deplasman şutları sola çevrildi (x'=100−x): ${dpS.length} şut, en büyük x ${Math.max(...dpS.map(m => m.cx)).toFixed(1)} / 105`);
    const kor = R.M.filter(m => m.k === "cor");
    ok(kor.every(m => (m.sd === "h" ? m.cx > 100 : m.cx < 5)), `(a) kornerler doğru köşede (${kor.length})`);
    ok(R.tr > 0 && R.st >= 1, `(a) şut hedef çizgileri ${R.tr}, gol yıldızı ${R.st}`);
    ok(R.pl === 1 && R.M.filter(m => m.yeni).length === 1 && R.M[R.M.length - 1].yeni && R.M[R.M.length - 1].sd === "a", "(a) en yeni olay (74' deplasman şutu) nabız animasyonlu");
    ok(R.son.length === 5 && /^74'/.test(R.son[0]) && /İsabetli şut/.test(R.son[0]) && /Chelsea/.test(R.son[0]), `(a) son 5 olay listesi: ${JSON.stringify(R.son.slice(0, 2))}`);
    ok(R.bas > 10 && R.bas2 > 10 && /Olaylardan/.test(R.tag), `(a) olay tabanlı baskı grafiği: ev ${R.bas}, dep ${R.bas2} çubuk · "${R.tag}"`);
    ok(/CANLI 74'/.test(R.cn), `(a) durum rozeti "${R.cn}"`);
    await p.screenshot({ path: path.join(SHOTS, "saha_01_eng1.png"), fullPage: false });
    await p.evaluate(() => document.querySelector("#msheet .sh-bas").scrollIntoView({ block: "center" }));
    await p.screenshot({ path: path.join(SHOTS, "saha_02_eng1_baski.png") });
    // dokununca bilgi
    await p.evaluate(() => document.querySelector("#msheet .sh-pitch").scrollIntoView({ block: "center" }));
    await p.locator("#msheet .sh-svg .sh-m.yeni .hit").click({ force: true });
    const tip = await p.evaluate(() => document.querySelector("#msheet .sh-tip").textContent);
    await p.evaluate(() => msRender());
    const tip2 = await p.evaluate(() => document.querySelector("#msheet .sh-tip").textContent);
    ok(tip2 === tip, `(a) pencere yeniden çizilince seçili işaret bilgisi korunur`);
    ok(/74'/.test(tip) && /İsabetli şut/.test(tip) && /Chelsea/.test(tip) && /ceza sahası içi/.test(tip), `(a) işarete dokununca bilgi: "${tip}"`);
    await p.screenshot({ path: path.join(SHOTS, "saha_03_dokun.png") });
    // tüm maç
    await p.click('#msheet .sh-sec button[data-s="tum"]');
    const nT = await p.evaluate(() => document.querySelectorAll("#msheet .sh-svg .sh-m").length);
    ok(nT === 60, `(a) "Tüm maç" en çok 60 işaret: ${nT}`);
    // yenileme: 30 sn'de bir (saat ileri sarılarak), gizliyken istek yok
    await p.waitForTimeout(3200);   // ui-v92: aynı ESPN adresi 3 sn içinde birleşir
    const n0 = S.n; await p.evaluate(() => { istekV124.temizle(); }); S.dk = 76;
    await p.evaluate(async () => { await window.sahaV180.yukle(true); msRender(); });
    const d2 = await p.evaluate(() => window.sahaV180.durum());
    ok(S.n === n0 + 1 && d2.simdi === 76, `(a) yenileme yeni veriyi çizer (istek ${S.n - n0}, dakika ${d2.simdi})`);
    await p.evaluate(() => { Object.defineProperty(document, "hidden", { configurable: true, get: () => true }); istekV124.temizle(); });
    const n1 = S.n; await p.evaluate(async () => { try { await window.sahaV180.yukle(true); } catch (e) {} });
    ok(S.n === n1, "(a) sayfa gizliyken ESPN'e istek yok");
    await p.evaluate(() => { Object.defineProperty(document, "hidden", { configurable: true, get: () => false }); });
    // diğer sekmeler bozulmadı
    await p.click('#msheet .ms-tabs button[data-t="tahmin"]');
    const tb = await p.evaluate(() => ({ sh: !!document.querySelector("#msheet .sh-wrap"), tab: MS.tab, body: (document.querySelector("#msheet .ms-body") || {}).children.length }));
    ok(!tb.sh && tb.tab === "tahmin" && tb.body > 0, "(a) Tahmin sekmesine dönüş: saha bölümü kalkar, tahmin içeriği çizilir");
    await ortak(p, errs, "(a)");
    // masaüstü genişliği
    await p.setViewportSize({ width: 1280, height: 860 }); await p.click('#msheet .ms-tabs button[data-t="saha"]'); await p.waitForTimeout(300);
    const dm = await p.evaluate(() => { const s = document.querySelector("#msheet .sh-svg"); const r = s && s.getBoundingClientRect(); return r ? { w: Math.round(r.width), h: Math.round(r.height) } : null; });
    ok(dm && dm.w > 300 && dm.h <= 450, `(a) masaüstü: saha ${dm && dm.w}×${dm && dm.h}`);
    await p.screenshot({ path: path.join(SHOTS, "saha_04_masaustu.png") });
    const o = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, vw: document.documentElement.clientWidth }));
    ok(o.sw <= o.vw + 1, `(a) masaüstü yatay taşma yok (${o.sw}/${o.vw})`);
    await ctx.close();
  }
  // (b) konumsuz tur.1 → istatistikten tahmini baskı
  {
    const { ctx, p, errs, S } = await senaryo(b, "(b) tur.1 konumsuz canlı maç", "tr1", (r, S) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(ozet("tr1", S.dk, S)) }));
    ok(await sekme(p), "(b) Saha sekmesi var");
    await sahaAc(p);
    S.dk = 80; S.st = [15, 7, 8, 8, 2, 3]; await p.waitForTimeout(3200);
    await p.evaluate(async () => { istekV124.temizle(); await window.sahaV180.yukle(true); msRender(); });
    const R = await p.evaluate(() => { const el = document.querySelector("#msheet .sh-wrap"); return el ? { svg: !!el.querySelector(".sh-svg"), bsvg: !!el.querySelector(".sh-bsvg"), bh: el.querySelectorAll(".sh-bsvg rect.bh").length,
      tag: (el.querySelector(".sh-tag") || {}).textContent || "", not: (el.querySelector(".sh-bos") || {}).textContent || "", son: el.querySelectorAll(".sh-son li").length, d: window.sahaV180.durum() } : null; });
    ok(R && !R.svg, "(b) konum yok → saha çizilmedi");
    ok(R && R.bsvg && R.bh > 10 && /İstatistikten tahmini/.test(R.tag), `(b) baskı grafiği istatistikten: ${R && R.bh} çubuk · "${R && R.tag}" · ölçüm ${R && R.d && R.d.hist}`);
    ok(R && R.d && R.d.hist === 2 && R.d.simdi === 80, `(b) yenilemede ikinci istatistik ölçümü eklendi (${R && R.d && R.d.hist} ölçüm, ${R && R.d && R.d.simdi}. dk)`);
    ok(R && /konum verisi yayınlanmıyor/.test(R.not), `(b) açıklama: "${R && R.not.slice(0, 70)}…"`);
    ok(R && R.son === 2, `(b) kilit olaylar listesi (gol, kart): ${R && R.son}`);
    await p.screenshot({ path: path.join(SHOTS, "saha_05_tur1.png") });
    await ortak(p, errs, "(b)");
    await ctx.close();
  }
  // (c) 403 / erişim yok
  {
    const { ctx, p, errs } = await senaryo(b, "(c) ESPN 403", "en", r => r.fulfill({ status: 403, contentType: "text/html", body: "Access Denied" }));
    ok(await sekme(p), "(c) Saha sekmesi var");
    await sahaAc(p);
    const R = await p.evaluate(() => ({ w: (document.querySelector("#msheet .sh-bos.warn") || {}).textContent || "", svg: !!document.querySelector("#msheet .sh-svg") }));
    ok(/ulaşılamıyor/.test(R.w) && !R.svg, `(c) uyarı: "${R.w}"`);
    await p.screenshot({ path: path.join(SHOTS, "saha_06_403.png") });
    await ortak(p, errs, "(c)");
    await ctx.close();
  }
  // (d) bayrak kapalı
  {
    const { ctx, p, errs } = await senaryo(b, "(d) bayrak saha:false", "en", (r, S) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(ozet("en", S.dk, S)) }), { at: false, saha: false });
    ok(!(await sekme(p)), "(d) saha:false → Saha sekmesi çizilmez");
    ok(errs.length === 0, `(d) sayfa hatası 0 ${JSON.stringify(errs.slice(0, 3))}`);
    await ctx.close();
  }
  await b.close();
  console.log(`\nSONUÇ: ${pass} geçti, ${fail} kaldı · ekran görüntüleri: ${SHOTS}`); process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
