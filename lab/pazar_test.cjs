// v104 · Pazar + Sonuçlar (OXX / Sen) uçtan uca testi — Playwright (yerel http.server ile çalışır)
// Kullanım: python3 -m http.server 8765  (depo kökünde)  →  node lab/pazar_test.cjs [ekran_görüntüsü_klasörü]
//   BASE=http://localhost:8765  ·  BASE_HTML=_base_test.html (isteğe bağlı: eski sürümle karşılaştırma; yoksa atlanır)
// Kapsam: GS–FB maç sayfası (tüm gruplar, 1&U25 = %33, kupona ekle/çıkar), KUPO (yeni kod adları, toplam oran + adil oran notu,
//   gruplu "seçim değiştir"), mkHit birim testleri (her kod, İY'li/İY'siz, bağımsız kahinle), at kuponu + eski futbol kuponu bozulmadı,
//   Sonuçlar (sahte biten maçlar + kilitli arşiv/predlog → OXX ✓/✗, kilitsiz maçta rozet yok, "Sen" rozeti, günlük özet), OXX sohbet.
//   Her ekranda yatay taşma ve pageerror sayılır.
const fs = require("fs"), path = require("path");
let chromium; try { ({ chromium } = require("playwright")); } catch (e) { ({ chromium } = require(path.join(process.env.HOME || "/root", ".npm-global/lib/node_modules/playwright"))); }
const ROOT = path.resolve(__dirname, "..");
const BASE = process.env.BASE || "http://localhost:8765";
const SHOTS = path.resolve(process.argv[2] || path.join(ROOT, "lab", "_shots"));
fs.mkdirSync(SHOTS, { recursive: true });
const NOW = new Date("2026-10-26T14:00:00+03:00");
const GSFB = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "fixtures.json"), "utf8")).find(f => f.h === "Galatasaray" && f.a === "Fenerbahçe");
const O1U = GSFB && GSFB.po && GSFB.po["1&U25"];
const O1Ut = O1U ? O1U.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "";
const DAY = "2026-10-25";
const J = f => JSON.parse(fs.readFileSync(path.join(ROOT, "data", f), "utf8"));
let pass = 0, fail = 0; const FAILS = [];
const ok = (c, msg) => { if (c) pass++; else { fail++; FAILS.push(msg); console.log("  ✗", msg); } };

// ---------------- bağımsız kahin (mkHit için) ----------------
function oracle(e, hs, as, h1, a1) {
  const iy = h1 != null && a1 != null && h1 <= hs && a1 <= as, t = hs + as;
  const r = (x, y) => x > y ? "1" : x < y ? "2" : "X";
  const h2 = iy ? hs - h1 : null, a2 = iy ? as - a1 : null;
  const T = { U15: t >= 2, A15: t <= 1, U25: t >= 3, A25: t <= 2, U35: t >= 4, A35: t <= 3, KGV: hs > 0 && as > 0, KGY: !(hs > 0 && as > 0),
    "1": hs > as, X: hs === as, "2": hs < as, "1X": hs >= as, "12": hs !== as, X2: hs <= as };
  if (e in T) return T[e];
  if (!iy) return null;
  const I = { IY1: h1 > a1, IYX: h1 === a1, IY2: h1 < a1, IYU05: h1 + a1 >= 1, IYA05: h1 + a1 === 0, IYU15: h1 + a1 >= 2, IYA15: h1 + a1 <= 1,
    "2Y1": h2 > a2, "2YX": h2 === a2, "2Y2": h2 < a2, "2YU05": h2 + a2 >= 1, "2YA05": h2 + a2 === 0, "2YU15": h2 + a2 >= 2, "2YA15": h2 + a2 <= 1,
    DGY1: h1 + a1 > h2 + a2, DGYE: h1 + a1 === h2 + a2, DGY2: h1 + a1 < h2 + a2 };
  if (e in I) return I[e];
  let m;
  if ((m = /^IYMS_(.)_(.)$/.exec(e))) return r(h1, a1) === m[1] && r(hs, as) === m[2];
  return undefined;
}
function oracleAll(e, hs, as, h1, a1) { // birleşikler İY gerektirmez
  const m = /^([1X2])&(U25|A25|KGV|KGY)$/.exec(e); if (m) return oracle(m[1], hs, as) && oracle(m[2], hs, as);
  return oracle(e, hs, as, h1, a1);
}
const CASES = [[2, 1, 1, 0], [0, 0, 0, 0], [1, 1, 1, 0], [3, 2, 0, 2], [1, 3, 1, 1], [4, 0, 2, 0], [0, 2, 0, 0], [2, 2, 2, 2], [5, 1, 3, 1],
  [2, 1, null, null], [0, 0, null, null], [3, 1, 4, 0] /* tutarsız İY → İY'siz sayılır */];

function buildLR() {
  const arc = J(`archive/${DAY}.json`), plog = J("predlog.json");
  // not: Playwright'ta sonra eklenen route önce çalışır → genel 404 önce, sahte sonuç servisi sonra
  // sahte biten maçlar: arşivden kilitli kaydı olan 7 maç + yalnız predlog'da kilitli 1 maç + kilitsiz 1 maç
  const picks = Object.entries(arc).filter(([, r]) => r.hs != null && (r.sk || r.rk) && r.h1 != null).slice(0, 7);
  const pl = plog.find(x => x.d === DAY && x.ts && x.r && Array.isArray(x.p) && !Object.values(arc).some(r => r.h === x.h));
  const ev = [], sc = {}, comps = { 9001: { n: "Test Ligi", cid: "TR" } };
  for (const [id, r] of picks) { ev.push({ eventId: +id, phase: 2, ci: 9001, homeTeam: r.h, awayTeam: r.a, eventDate: r.ts }); sc[id] = { ht: { c: r.hs, ht: r.h1 }, at: { c: r.as, ht: r.a1 } }; }
  if (pl) { ev.push({ eventId: 999001, phase: 2, ci: 9001, homeTeam: pl.h, awayTeam: pl.a, eventDate: Math.floor(Date.parse(pl.ts) / 1000) + 7200 }); sc[999001] = { ht: { c: pl.r[0], ht: 0 }, at: { c: pl.r[1], ht: 0 } }; }
  ev.push({ eventId: 999002, phase: 2, ci: 9001, homeTeam: "Kilitsiz Ev FK", awayTeam: "Kilitsiz Dep SK", eventDate: Math.floor(Date.parse(DAY + "T20:00:00+03:00") / 1000) }); sc[999002] = { ht: { c: 1, ht: 0 }, at: { c: 0, ht: 0 } };
  const LR = { data: { events: ev, competitions: comps, sc } };
  return { arc, plog, picks, pl, LR };
}
async function run(vw, vh, tag) {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: 2, locale: "tr-TR", timezoneId: "Europe/Istanbul" });
  const { arc, plog, picks, pl, LR } = buildLR();
  // kullanıcı verisi (yalnız bu sahte telefonda): açık futbol kuponu (eski kodlar), eski kupon (biten maçlar), at kuponu
  const [i0, r0] = picks[0], [i1, r1] = picks[1];
  const dtOf = r => new Date(r.ts * 1000).toISOString();
  const T0 = Date.parse("2026-10-24T10:00:00Z");
  const seed = [
    { id: "kpA", ad: "Kupon 1", items: [], olusturma: T0, durum: "acik" },
    { id: "kpOld", ad: "Hafta sonu", olusturma: T0, durum: "bitti", bitti: T0 + 9e7, items: [
      { k: "i|" + r0.h + "|" + r0.a, lg: "i1", h: r0.h, a: r0.a, dt: dtOf(r0), mk: "U", odd: 1.8, p: .55, iid: +i0 },
      { k: "i|" + r1.h + "|" + r1.a, lg: "i1", h: r1.h, a: r1.a, dt: dtOf(r1), mk: "IYMS_1_1", odd: 4.1, p: .24, iid: +i1, fair: 1 }] },
    { id: "atk1", ad: "At Kuponu 1", spor: "at", items: [], at: [{ id: "r1", tur: "ganyan", d: "2026-10-26", kid: ["2026-10-26/Veliefendi/1"], hip: "Veliefendi", kosu: 1, saat: "18:30", t: Date.parse("2026-10-26T18:30:00+03:00"), sec: [[3]], ad: { 3: "Deneme At" }, komb: 1, p: .21, pk: "sabah", gd: [1, 1] }], olusturma: T0 + 1000, durum: "acik" }];
  await ctx.addInitScript(([seed]) => { localStorage.setItem("bx-terms", JSON.stringify({ v: "2.0", at: Date.now(), kvkk: true, inst: Date.now() })); localStorage.setItem("bx-oxxai-hos", "1"); localStorage.setItem("bx-oxxai-ikon", "1"); localStorage.setItem("bx-coach", "1");
    if (!sessionStorage.getItem("seeded")) { localStorage.setItem("bx-kuponlar", JSON.stringify(seed)); localStorage.setItem("bx-kupon-aktif", "kpA"); sessionStorage.setItem("seeded", "1"); } }, [seed]);
  const p = await ctx.newPage(); const errs = [];
  p.on("pageerror", e => errs.push(e.message)); p.on("console", m => { if (/v103|v104/.test(m.text())) console.log("   [konsol]", m.text()); }); p.on("framenavigated", f => { if (f === p.mainFrame()) console.log("   [nav]", f.url()); });
  await p.clock.setFixedTime(NOW);
  const sent = [];
  await p.route(/iddaa\.com|espn|jsdelivr|googleapis|gstatic|web3forms|api\./, r => { sent.push(r.request().url()); r.fulfill({ status: 404, body: "" }); });
  await p.route(/statisticsv2\.iddaa\.com\/live-results\?sportId=1&date=/, r => { const d = new URL(r.request().url()).searchParams.get("date"); r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(d === DAY ? LR : { data: { events: [], competitions: {}, sc: {} } }) }); });
  await p.goto(BASE + "/index.html");
  for (let i = 0; i < 60; i++) { const r = await p.evaluate(() => { try { PL_RESET(); return !!findMatchByTeams("Galatasaray", "Fenerbahçe") && FIXTURES.length > 0; } catch (e) { return false; } }); if (r) break; await p.waitForTimeout(500); }
  await p.waitForTimeout(800);
  const overflow = async (sel) => p.evaluate(s => { const vw = document.documentElement.clientWidth; let n = 0; const bad = [];
    const root = s ? document.querySelector(s) : document.body; if (!root) return { n: -1 };
    root.querySelectorAll("*").forEach(e => { const r = e.getBoundingClientRect(); if (!r.width || !r.height) return; const cs = getComputedStyle(e); if (cs.visibility === "hidden" || cs.display === "none") return;
      if (e.closest("svg") && e.tagName !== "svg") return; if (r.right > vw + 1 || r.left < -1) { if (e.closest(".msc-w,.ms-tabs,.bt-days,.bt-chips,.kx-chips,[style*='overflow']")) return; n++; if (bad.length < 5) bad.push(e.className + "@" + Math.round(r.right)); } });
    return { n, bad, sw: document.documentElement.scrollWidth, vw }; }, sel);
  const shot = async (name) => { await p.screenshot({ path: path.join(SHOTS, `${tag}_${name}.png`) }); };
  const OV = [];
  const ovc = async (name, sel) => { const o = await overflow(sel); OV.push([name, o.n]); ok(o.n === 0, `${tag} ${name}: yatay taşma ${o.n} ${JSON.stringify(o.bad || [])}`); ok(!(o.sw > o.vw + 1), `${tag} ${name}: sayfa genişliği ${o.sw} > ${o.vw}`); };

  // ---------- A) GS–FB maç sayfası ----------
  for (let i = 0; i < 60; i++) { const r = await p.evaluate(() => { try { PL_RESET(); } catch (e) {} const m = findMatchByTeams("Galatasaray", "Fenerbahçe"); if (!m) return { n: Pick.list().length, fx: FIXTURES.length, t: new Date().toISOString() }; openMatch(m); return true; }); if (r === true) break; if (i % 10 === 9) console.log("   bekleniyor", JSON.stringify(r)); await p.waitForTimeout(500); }
  await p.waitForTimeout(500);
  const tah = await p.evaluate(() => { const el = $("msheet"); const c = el.querySelector(".pz-tah"); return { card: c ? c.innerText : null, tab: el.querySelector('.ms-tabs button[data-t="oran"]').textContent }; });
  ok(tah.card && /2-1/.test(tah.card) && /MS 1 & 2,5 Üst/.test(tah.card) && /%33/.test(tah.card), `${tag} Tahmin sekmesinde skorla uyumlu kart (2-1 ⇒ MS 1 & 2,5 Üst %33): ${tah.card}`);
  ok(tah.tab === "Seçenekler", `${tag} sekme adı Seçenekler`);
  await shot("01_mac_tahmin"); await ovc("mac_tahmin", "#msheet");
  await p.evaluate(() => msGo("oran")); await p.waitForTimeout(300);
  await shot("02_mac_tum_tahminler_ust"); await ovc("mac_secenekler", "#msheet");
  // tüm grupları aç
  await p.evaluate(() => { document.querySelectorAll('#msheet .pz-gh[aria-expanded="false"]').forEach(b => b.click()); });
  await p.waitForTimeout(150);
  const G = await p.evaluate(() => { const el = $("msheet"); const gs = [...el.querySelectorAll("[data-pzg]")].map(g => ({ g: g.dataset.pzg, t: g.querySelector(".pz-gh b").textContent, n: g.querySelectorAll(".pz-r").length, open: !g.querySelector(".pz-gb").hidden }));
    const r = el.querySelector('[data-pzr="1&U25"]'); const cal = el.querySelectorAll(".pz-c").length, rows = el.querySelectorAll(".pz-r").length;
    return { gs, u: r ? r.innerText.replace(/\s+/g, " ") : null, cal, rows, fit: [...el.querySelectorAll(".pz-r.fit")].map(x => x.dataset.pzr), leg: !!el.querySelector(".mg-o .mo") }; });
  const NAMES = ["Maç sonucu", "Çifte şans", "Alt / Üst", "Karşılıklı gol", "İlk yarı", "İkinci yarı", "İY / MS", "MS + Alt/Üst", "MS + KG", "Daha gollü yarı"];
  ok(G.gs.length === 10 && NAMES.every((n, i) => G.gs[i] && G.gs[i].t === n), `${tag} 10 grup sırayla: ${G.gs.map(x => x.t).join(", ")}`);
  ok(G.gs.every(x => x.open && x.n > 0), `${tag} tüm gruplar açılır ve dolu`);
  ok(G.rows === 52, `${tag} 52 seçenek satırı (${G.rows})`);
  ok(G.u && /%33/.test(G.u) && G.u.includes(`oran ${O1Ut}`), `${tag} 1&U25 satırı %33 · oran ${O1Ut}: ${G.u}`);
  ok(G.cal >= 40, `${tag} kalibrasyon notları (${G.cal})`);
  ok(G.fit.includes("1&U25") && G.fit.includes("1&KGV") && !G.fit.includes("1"), `${tag} 2-1 ile uyumlu vurgusu yalnız birleşik/İY-MS: ${G.fit.join(",")}`);
  ok(!G.leg, `${tag} pz varken eski oran kutuları tekrar edilmiyor`);

  for (let y = 1; y <= 3; y++) { await p.evaluate(y => { const el = $("msheet"); el.scrollTop = Math.round(el.scrollHeight * y / 4); }, y); await p.waitForTimeout(80); await shot(`03_mac_tum_tahminler_${y}`); }
  await ovc("mac_tum_acik", "#msheet");
  // ekle / çıkar
  await p.evaluate(() => { const b = $("msheet").querySelector('[data-pzr="1&U25"] .pz-add'); b.click(); });
  await p.waitForTimeout(250);
  let st = await p.evaluate(() => { const it = CP.items.find(x => x.h === "Galatasaray"); const b = $("msheet").querySelector('[data-pzr="1&U25"] .pz-add'); return { it, pressed: b && b.getAttribute("aria-pressed"), txt: b && b.textContent, act: kxAct().ad }; });
  ok(st.it && st.it.mk === "1&U25" && Math.abs(st.it.odd - O1U) < 1e-9 && Math.abs(st.it.p - .331) < 1e-9 && !st.it.fair, `${tag} 1&U25 kupona eklendi (oran ${O1Ut}, p .331): ${JSON.stringify(st.it)}`);
  ok(st.pressed === "true" && /Kuponda/.test(st.txt), `${tag} düğme ✓ Kuponda`);
  await shot("04_mac_kuponda");
  await p.evaluate(() => { $("msheet").querySelector('[data-pzr="1&U25"] .pz-add').click(); }); await p.waitForTimeout(250);
  st = await p.evaluate(() => ({ n: CP.items.filter(x => x.h === "Galatasaray").length, pr: $("msheet").querySelector('[data-pzr="1&U25"] .pz-add').getAttribute("aria-pressed") }));
  ok(st.n === 0 && st.pr === "false", `${tag} tekrar dokun → çıkarıldı`);
  // KUPO için: GS–FB 1&U25 + iki maç daha (İY 0,5 Üst → oransız/adil; 2Y 1)
  const other = await p.evaluate(() => { const now = Date.now(); const L = FIXTURES.filter(f => f.pz && f.pz.IYU05 != null && f.pz["2Y1"] != null && !(f.po && f.po.IYU05) && Date.parse(f.d + "T" + f.t + ":00Z") > now + 3600e3 && f.h !== "Galatasaray").slice(0, 2); return L.map(f => [f.h, f.a]); });
  await p.evaluate(([o]) => { const C0 = pzCtx(findMatchByTeams("Galatasaray", "Fenerbahçe"), MS.f); pzToggle(C0, "1&U25"); closeMatch();
    const m1 = findMatchByTeams(o[0][0], o[0][1]), m2 = findMatchByTeams(o[1][0], o[1][1]);
    const f1 = FIXTURES.find(x => x.h === m1.h && x.a === m1.a), f2 = FIXTURES.find(x => x.h === m2.h && x.a === m2.a);
    pzToggle(pzCtx(m1, f1), "IYU05"); pzToggle(pzCtx(m2, f2), "2Y1"); }, [other]);
  await p.waitForTimeout(200);
  // ---------- B) KUPO ----------
  await p.evaluate(() => kxOpen("cp")); await p.waitForTimeout(600);
  const K = await p.evaluate(() => { const box = $("cpBox"); const names = [...box.querySelectorAll(".cprow .kx-mk")].map(b => b.childNodes[0].textContent.trim());
    const I = CP.items; const prod = I.reduce((a, x) => a * x.odd, 1); const tot = box.querySelector(".kx-sum .kp-odd b").textContent; const note = (box.querySelector(".pz-fair") || {}).textContent || "";
    return { names, prod, tot, note, items: I.map(x => [x.mk, x.odd, x.fair || 0, x.p]) }; });
  ok(JSON.stringify(K.names) === JSON.stringify(["MS 1 & 2,5 Üst", "İY 0,5 Üst", "2Y 1"]), `${tag} KUPO adları: ${K.names.join(" | ")}`);
  ok(K.tot === K.prod.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }), `${tag} toplam oran ${K.tot} = çarpım ${K.prod.toFixed(4)}`);
  const iyu = K.items.find(x => x[0] === "IO05");
  ok(iyu && iyu[2] === 1 && Math.abs(iyu[1] - +(1 / iyu[3]).toFixed(2)) < 1e-9, `${tag} İY 0,5 Üst uygulama kodu IO05, adil oran 1/p: ${JSON.stringify(iyu)}`);
  ok(/adil oran/.test(K.note), `${tag} toplam oranda adil oran notu: ${K.note}`);
  await shot("05_kupo_yeni_kodlar"); await ovc("kupo", "#v-kupon");
  // seçim değiştir (gruplu)
  await p.evaluate(() => { $("cpBox").querySelector('.cprow[data-cpi="0"] .kx-mk').click(); }); await p.waitForTimeout(300);
  const SW = await p.evaluate(() => { const k = $("cpBox").querySelector(".kx-opts"); return k ? { pz: k.classList.contains("pz-ko"), groups: [...k.querySelectorAll(".pz-kg")].map(g => (g.querySelector("small,summary") || {}).textContent), has: !!k.querySelector('[data-k="IYMS_1_1"]'), n: k.querySelectorAll("button[data-k]").length } : null; });
  ok(SW && SW.pz && SW.groups.length === 10 && SW.has && SW.n >= 52, `${tag} seçim değiştir: gruplu yeni pazarlar ${JSON.stringify(SW)}`);
  await shot("06_kupo_secim_degistir"); await ovc("kupo_secim", "#v-kupon");
  await p.evaluate(() => { const k = $("cpBox").querySelector(".kx-opts"); const d = k.querySelector('[data-k="IYMS_1_1"]'); const det = d.closest("details"); if (det) det.open = true; d.click(); }); await p.waitForTimeout(300);
  const sw2 = await p.evaluate(() => CP.items[0] && [CP.items[0].mk, CP.items[0].odd, CP.items[0].fair || 0]);
  ok(sw2 && sw2[0] === "IYMS_1_1" && sw2[2] === 1, `${tag} seçim İY/MS 1/1 olarak değişti (adil oran): ${JSON.stringify(sw2)}`);
  // ---------- C) mkHit birim testleri ----------
  const codes = await p.evaluate(() => [].concat(...PZ_CAT.map(c => c[2])));
  const R = await p.evaluate(([codes, cases]) => { const out = []; for (const e of codes) for (const [hs, as, h1, a1] of cases) {
      out.push([e, hs, as, h1, a1, mkHit(pzToApp(e), hs, as, h1, a1, null), /^(U15|U35)$/.test(e) ? "-" : mkHit(e, hs, as, h1, a1, null)]); } return out; }, [codes, CASES]);
  const TAB = {};
  for (const [e, hs, as, h1, a1, ga, ge] of R) { const exp = oracleAll(e, hs, as, h1, a1); const t = TAB[e] = TAB[e] || { n: 0, ok: 0, iy: 0, nul: 0 };
    t.n++; const good = ga === exp && (ge === "-" || ge === exp); if (good) t.ok++; else console.log("   mkHit", e, hs, as, h1, a1, "→", ga, ge, "beklenen", exp);
    if (h1 != null && h1 <= hs && a1 <= as) t.iy++; if (exp === null) t.nul++; ok(good, `${tag} mkHit ${e} ${hs}-${as} İY ${h1}-${a1}`); }
  // eski kodlar: anlamı değişmedi
  const LEG = ["1", "X", "2", "1X", "12", "X2", "U", "A", "O15", "U15", "O35", "U35", "KGV", "KGY", "IY1", "IYX", "IY2", "IO05", "IU05", "IO15", "IU15", "U2.5", "A2.5", "U1.5", "A3.5"];
  const LEX = { U: "U25", A: "A25", O15: "U15", U15: "A15", O35: "U35", U35: "A35", IO05: "IYU05", IU05: "IYA05", IO15: "IYU15", IU15: "IYA15", "U2.5": "U25", "A2.5": "A25", "U1.5": "U15", "A3.5": "A35" };
  const RL = await p.evaluate(([L, cases]) => L.map(k => cases.map(([hs, as, h1, a1]) => mkHit(k, hs, as, h1, a1, null))), [LEG, CASES.filter(c => !(c[2] != null && c[2] > c[0]))]);
  LEG.forEach((k, i) => CASES.filter(c => !(c[2] != null && c[2] > c[0])).forEach(([hs, as, h1, a1], j) => { const exp = oracleAll(LEX[k] || k, hs, as, h1, a1); ok(RL[i][j] === exp, `${tag} eski kod ${k} ${hs}-${as} İY ${h1}-${a1}: ${RL[i][j]} ≠ ${exp}`); }));
  const live = await p.evaluate(() => [mkHit("GG", 2, 1, null, null, "1-1"), mkHit("G0", 1, 1, null, null, "1-1"), mkHit("GG", 1, 1, null, null, "1-1")]);
  ok(JSON.stringify(live) === "[true,true,false]", `${tag} canlı GG/G0 korunur ${JSON.stringify(live)}`);
  // ---------- D) at kuponu + eski futbol kuponu ----------
  await p.evaluate(() => { const b = document.querySelector('#kxChips [data-kc="atk1"]'); if (b) b.click(); }); await p.waitForTimeout(500);
  const AT = await p.evaluate(() => ({ act: kxAct().ad, txt: ($("cpBox").innerText || "").replace(/\s+/g, " ").slice(0, 400), at: !!$("cpBox").querySelector(".atk-ic,[class*='atk']") }));
  ok(AT.act === "At Kuponu 1" && /Deneme At|Ganyan/.test(AT.txt), `${tag} at kuponu açılıyor: ${AT.txt.slice(0, 120)}`);
  await shot("07_kupo_at_kuponu");
  await p.evaluate(() => { try { kxGrade(); } catch (e) {} }); await p.waitForTimeout(1500);
  await p.evaluate(() => kxOpen("eski")); await p.waitForTimeout(500);
  await p.evaluate(() => { const h = document.querySelector('#kxOld .kx-oh[data-c="kpOld"]'); if (h && h.getAttribute("aria-expanded") !== "true") h.click(); }); await p.waitForTimeout(300);
  const OLD = await p.evaluate(() => ($("kxOld").innerText || "").replace(/\s+/g, " "));
  const OLDR = await p.evaluate(() => [...document.querySelectorAll("#kxOld .kx-od .cprow")].map(r => { const x = r.querySelector(".kx-res"); return x ? x.className.replace("kx-res", "").trim() : (r.querySelector(".kx-man") ? "need" : "?"); }));
  ok(/Hafta sonu/.test(OLD) && /2,5 Üst/.test(OLD) && /İY\/MS 1\/1/.test(OLD), `${tag} eski futbol kuponu adları (2,5 Üst, İY/MS 1/1)`);
  await shot("08_kupo_eski"); await ovc("kupo_eski", "#v-kupon");
  const atSnap = AT.txt;
  // ---------- E) Sonuçlar ----------
  await p.evaluate(() => { $("navRes").click(); }); await p.waitForTimeout(300);
  await p.evaluate(d => { RS.day = d; RS.load(d).then(renderRes); renderRes(); }, DAY);
  for (let i = 0; i < 20; i++) { const n = await p.evaluate(() => document.querySelectorAll("#rsList .rs-ox").length); if (n) break; await p.waitForTimeout(250); }
  await p.waitForTimeout(300);
  if (process.env.DBG) console.log(await p.evaluate(() => ({ rows: document.querySelectorAll("#rsList .rs-r").length, c: !!RS.cache.get(RS.day), day: RS.day, n: (RS.cache.get(RS.day) || {}).list, box: !!$("rsVsBox"), html: $("rsList").innerHTML.slice(0, 600), wrapped: String(renderRes).slice(0, 120) })));
  const SR = await p.evaluate(() => { const rows = [...document.querySelectorAll("#rsList .rs-r")]; return rows.map(r => ({ id: r.dataset.rsid, tm: (r.querySelector(".ib-tm") || {}).textContent, ox: (r.querySelector(".rs-ox") || {}).innerText || null, oxl: (r.querySelector(".rs-ox") || { getAttribute: () => null }).getAttribute("aria-label"), me: [...r.querySelectorAll(".rs-me")].map(x => x.innerText.replace(/\s+/g, " ")) })); });
  const strip = await p.evaluate(() => (($("rsVs") || {}).innerText || "").replace(/\s+/g, " "));
  // beklenen OXX: arşiv sk/sp (yoksa rk/rp) ve gerçek sonuç
  let expH = 0, expN = 0;
  for (const [id, r] of picks) { const row = SR.find(x => x.id === id); const k = r.sk || r.rk, pr = r.sk ? r.sp : r.rp;
    const exp = { "1": r.hs > r.as, X: r.hs === r.as, "2": r.hs < r.as, U: r.hs + r.as > 2.5, A: r.hs + r.as < 2.5 }[k]; expN++; if (exp) expH++;
    ok(row && row.oxl && row.oxl.includes(`yüzde ${Math.round(pr * 100)}`) && row.oxl.includes(exp ? ", tuttu" : ", tutmadı"), `${tag} OXX rozeti ${r.h}-${r.a} ${k} %${Math.round(pr * 100)} ${exp ? "✓" : "✗"}: ${row && row.oxl}`); }
  const plr = SR.find(x => x.id === "999001");
  if (pl) { const c = [["1", pl.p[0]], ["X", pl.p[1]], ["2", pl.p[2]], ["U", pl.o], ["A", 1 - pl.o]].sort((a, b) => b[1] - a[1])[0];
    const exp = { "1": pl.r[0] > pl.r[1], X: pl.r[0] === pl.r[1], "2": pl.r[0] < pl.r[1], U: pl.r[0] + pl.r[1] > 2.5, A: pl.r[0] + pl.r[1] < 2.5 }[c[0]]; expN++; if (exp) expH++;
    ok(plr && plr.oxl && plr.oxl.includes(`yüzde ${Math.round(c[1] * 100)}`) && plr.oxl.includes(exp ? ", tuttu" : ", tutmadı"), `${tag} predlog kilitli OXX rozeti: ${plr && plr.oxl}`); }
  const unl = SR.find(x => x.id === "999002");
  ok(unl && !unl.ox, `${tag} kilitli kaydı olmayan maçta OXX rozeti YOK`);
  const me0 = SR.find(x => x.id === String(picks[0][0])), me1 = SR.find(x => x.id === String(picks[1][0]));
  const u0 = r0.hs + r0.as > 2.5, iy1 = r1.h1 > r1.a1 && r1.hs > r1.as;
  ok(me0 && me0.me.length === 1 && me0.me[0].includes("Sen") && me0.me[0].includes("2,5 Üst") && me0.me[0].includes(u0 ? "✓" : "✗") && me0.me[0].includes("Hafta sonu"), `${tag} Sen rozeti (2,5 Üst ${u0 ? "✓" : "✗"}): ${me0 && me0.me}`);
  ok(me1 && me1.me[0] && me1.me[0].includes("İY/MS 1/1") && me1.me[0].includes(iy1 ? "✓" : "✗"), `${tag} Sen rozeti İY/MS 1/1 (İY skoruyla): ${me1 && me1.me}`);
  ok(SR.filter(x => x.me.length).length === 2, `${tag} Sen rozeti yalnız kupondaki 2 maçta`);
  const mH = (u0 ? 1 : 0) + (iy1 ? 1 : 0);
  ok(new RegExp(`OXX\\s*${expH}/${expN}`).test(strip) && new RegExp(`SEN\\s*${mH}/2`, "i").test(strip), `${tag} günlük özet "OXX ${expH}/${expN} · Sen ${mH}/2": ${strip}`);
  await shot("09_sonuclar"); await ovc("sonuclar", "#v-sonuclar");
  await p.evaluate(() => $("rsVs").click()); await p.waitForTimeout(200);
  const cmp = await p.evaluate(() => { const c = $("rsCmp"); return c && !c.hidden ? c.innerText.replace(/\s+/g, " ") : null; });
  ok(cmp && /Pazar OXX Sen/i.test(cmp) && /Toplam/.test(cmp) && /İY\/MS/.test(cmp), `${tag} karşılaştırma tablosu: ${cmp && cmp.slice(0, 160)}`);
  await shot("10_sonuclar_karsilastirma"); await ovc("sonuclar_cmp", "#v-sonuclar");
  await p.evaluate(id => { document.querySelector(`#rsList .rs-r[data-rsid="${id}"] .rs-me`).click(); }, String(picks[0][0])); await p.waitForTimeout(700);
  const go = await p.evaluate(() => { const v = $("v-kupon"); const h = document.querySelector('#kxOld .kx-oh[data-c="kpOld"]'); return { vis: v && !v.hidden, exp: h && h.getAttribute("aria-expanded") }; });
  ok(go.vis && go.exp === "true", `${tag} Sen rozetine dokun → KUPO'da o kupon açık ${JSON.stringify(go)}`);
  // ---------- F) OXX sohbet ----------
  await p.evaluate(() => { KX.aktif = "kpA"; kxSave(); try { CP.items.splice(0); cpSave(); } catch (e) {} BOT.ctx = null; });
  const Q = async q => p.evaluate(async q => { const R = await botAnswer(q); const d = document.createElement("div"); d.innerHTML = R.html || ""; return { t: d.innerText.replace(/\s+/g, " "), chips: R.chips || [] }; }, q);
  const b1 = await Q("galatasaray kazanır ve üst");
  ok(/MS 1 & 2,5 Üst/.test(b1.t) && /%33/.test(b1.t) && b1.chips[0] === "＋ Kupona ekle: MS 1 & 2,5 Üst", `${tag} sohbet "galatasaray kazanır ve üst": ${b1.t.slice(0, 200)} | ${b1.chips}`);
  const b2 = await Q("iy 0,5 üst"); ok(/İY 0,5 Üst/.test(b2.t) && /%77/.test(b2.t), `${tag} sohbet "iy 0,5 üst" (bağlam GS–FB): ${b2.t.slice(0, 160)}`);
  const b3 = await Q("ikinci yarı gol"); ok(/2Y 0,5 Üst/.test(b3.t) && /%86/.test(b3.t), `${tag} sohbet "ikinci yarı gol": ${b3.t.slice(0, 160)}`);
  const b4 = await Q("gs fb iy/ms"); ok(/İY\/MS 1\/1/.test(b4.t) && /%27/.test(b4.t), `${tag} sohbet "gs fb iy/ms": ${b4.t.slice(0, 200)}`);
  const b5 = await Q("galatasaray fenerbahçe kg var mı"); ok(/KG Var/.test(b5.t) && /%66/.test(b5.t) && (b5.t.match(/KG Var[^%]*%\d+/g) || []).length >= 1, `${tag} sohbet "kg var": ${b5.t.slice(0, 200)}`);
  const b6 = await Q("kg var ne demek"); ok(!/🧮/.test(b6.t) && /karşılıklı gol|iki takım/i.test(b6.t), `${tag} terim sorusu bozulmadı`);
  const b7 = await Q("fenerbahçe kazanır ve kg var"); ok(/MS 2 & KG Var/.test(b7.t) && /%19/.test(b7.t), `${tag} sohbet "fenerbahçe kazanır ve kg var": ${b7.t.slice(0, 200)}`);
  // UI: sohbetten çip ile kupona ekle
  await p.evaluate(() => { if (typeof closeMatch === "function") closeMatch(); botOpen(); }); await p.waitForTimeout(300);
  await p.fill("#botQ", "galatasaray kazanır ve üst"); await p.press("#botQ", "Enter");
  await p.waitForSelector('#botChips button[data-q^="＋ Kupona ekle"]', { timeout: 8000 }).catch(() => {});
  await p.waitForTimeout(300); await shot("11_oxx_sohbet"); await ovc("sohbet", null);
  await p.click('#botChips button[data-q^="＋ Kupona ekle"]'); await p.waitForTimeout(300);
  const bc = await p.evaluate(() => ({ it: CP.items.find(x => x.h === "Galatasaray"), chip: document.querySelector('#botChips button[data-q^="＋ Kupona ekle"]').textContent, log: document.querySelectorAll("#botLog .bt-msg").length }));
  ok(bc.it && bc.it.mk === "1&U25" && /Kuponda/.test(bc.chip), `${tag} sohbet çipi kupona ekledi ${JSON.stringify(bc.it && bc.it.mk)} · ${bc.chip}`);
  ok(errs.length === 0, `${tag} pageerror 0: ${errs.join(" | ")}`);
  const leak = sent.filter(u => /kupon|bx-|predlog/i.test(u));
  ok(leak.length === 0, `${tag} kullanıcı verisi dışarı gitmedi`);
  await b.close();
  return { TAB, OV, errs: errs.length, atSnap, oldSnap: OLD, oldRows: OLDR };
}

// ---------- eski sürümle karşılaştırma (at kuponu + eski futbol kuponu metni aynı) ----------
async function baseSnap(vw, vh) {
  const bh = process.env.BASE_HTML; if (!bh || !fs.existsSync(path.join(ROOT, bh))) return null;
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: vw, height: vh }, locale: "tr-TR", timezoneId: "Europe/Istanbul" });
  const T0 = Date.parse("2026-10-24T10:00:00Z"), arc = J(`archive/${DAY}.json`);
  const picks = Object.entries(arc).filter(([, r]) => r.hs != null && (r.sk || r.rk) && r.h1 != null).slice(0, 2); const dtOf = r => new Date(r.ts * 1000).toISOString();
  const [[i0, r0], [i1, r1]] = picks;
  const seed = [{ id: "kpA", ad: "Kupon 1", items: [], olusturma: T0, durum: "acik" },
    { id: "kpOld", ad: "Hafta sonu", olusturma: T0, durum: "bitti", bitti: T0 + 9e7, items: [
      { k: "i|" + r0.h + "|" + r0.a, lg: "i1", h: r0.h, a: r0.a, dt: dtOf(r0), mk: "U", odd: 1.8, p: .55, iid: +i0 },
      { k: "i|" + r1.h + "|" + r1.a, lg: "i1", h: r1.h, a: r1.a, dt: dtOf(r1), mk: "IYMS_1_1", odd: 4.1, p: .24, iid: +i1, fair: 1 }] },
    { id: "atk1", ad: "At Kuponu 1", spor: "at", items: [], at: [{ id: "r1", tur: "ganyan", d: "2026-10-26", kid: ["2026-10-26/Veliefendi/1"], hip: "Veliefendi", kosu: 1, saat: "18:30", t: Date.parse("2026-10-26T18:30:00+03:00"), sec: [[3]], ad: { 3: "Deneme At" }, komb: 1, p: .21, pk: "sabah", gd: [1, 1] }], olusturma: T0 + 1000, durum: "acik" }];
  await ctx.addInitScript(([seed]) => { localStorage.setItem("bx-terms", JSON.stringify({ v: "2.0", at: Date.now(), kvkk: true, inst: Date.now() })); localStorage.setItem("bx-oxxai-hos", "1"); localStorage.setItem("bx-oxxai-ikon", "1"); localStorage.setItem("bx-coach", "1"); localStorage.setItem("bx-kuponlar", JSON.stringify(seed)); localStorage.setItem("bx-kupon-aktif", "atk1"); }, [seed]);
  const p = await ctx.newPage(); await p.clock.setFixedTime(NOW); const { LR } = buildLR();
  await p.route(/iddaa\.com|espn|jsdelivr|googleapis|gstatic|web3forms|api\./, r => r.fulfill({ status: 404, body: "" }));
  await p.route(/statisticsv2\.iddaa\.com\/live-results\?sportId=1&date=/, r => { const d = new URL(r.request().url()).searchParams.get("date"); r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(d === DAY ? LR : { data: { events: [], competitions: {}, sc: {} } }) }); });
  await p.goto(BASE + "/" + bh); await p.waitForTimeout(5000);
  await p.evaluate(() => kxOpen("cp")); await p.waitForTimeout(600);
  const at = await p.evaluate(() => ($("cpBox").innerText || "").replace(/\s+/g, " ").slice(0, 400));
  await p.evaluate(() => { try { kxGrade(); } catch (e) {} }); await p.waitForTimeout(1500);
  await p.evaluate(() => kxOpen("eski")); await p.waitForTimeout(500);
  await p.evaluate(() => { const h = document.querySelector('#kxOld .kx-oh[data-c="kpOld"]'); if (h) h.click(); }); await p.waitForTimeout(300);
  const old = await p.evaluate(() => [...document.querySelectorAll("#kxOld .kx-od .cprow")].map(r => { const x = r.querySelector(".kx-res"); return x ? x.className.replace("kx-res", "").trim() : (r.querySelector(".kx-man") ? "need" : "?"); }));
  await b.close(); return { at, old };
}

(async () => {
  const A = await run(390, 844, "390");
  const B = await run(360, 740, "360");
  const base = await baseSnap(390, 844);
  if (base) {
    ok(base.at === A.atSnap, `at kuponu metni eski sürümle aynı\n   eski: ${base.at.slice(0, 160)}\n   yeni: ${A.atSnap.slice(0, 160)}`);
    // eski sürüm: 2,5 Üst aynı sonucu alır; İY/MS 1/1'i puanlayamaz ("sonuç eksik", elle işaretle) → yeni sürüm İY skoruyla puanlar
    ok(base.old[0] === A.oldRows[0] && /^[gx]$/.test(A.oldRows[0]), `eski kod (2,5 Üst) eski sürümle aynı puanlandı: ${base.old[0]} / ${A.oldRows[0]}`);
    ok(/need|w/.test(base.old[1]) && /^[gx]$/.test(A.oldRows[1]), `İY/MS 1/1: eski sürüm puanlayamıyordu (${base.old[1]}), yeni sürüm puanladı (${A.oldRows[1]})`);
  } else console.log("  (eski sürüm karşılaştırması atlandı: BASE_HTML yok)");
  console.log("\nmkHit birim test tablosu (kod · durum · geçen/toplam · İY'li vaka · İY yok → null):");
  for (const [e, t] of Object.entries(A.TAB)) console.log(`  ${e.padEnd(9)} ${t.ok === t.n ? "✓" : "✗"} ${t.ok}/${t.n}  İY'li ${t.iy}  null ${t.nul}`);
  console.log("\nTaşma:", JSON.stringify(A.OV), JSON.stringify(B.OV));
  console.log(`\nSONUÇ: ${pass} geçti, ${fail} kaldı · pageerror ${A.errs + B.errs} · ekran görüntüleri: ${SHOTS}`);
  if (fail) { console.log(FAILS.slice(0, 40).join("\n")); process.exit(1); }
})().catch(e => { console.error(e); process.exit(2); });
