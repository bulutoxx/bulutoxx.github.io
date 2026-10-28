// v107 · Canlı "↻ Güncel tahmin" + istatistik ayarı uçtan uca testi (Playwright; sahte iddaa canlı bülteni + sahte ESPN)
// Kullanım: python3 -m http.server 8766 (depo kökünde) → node lab/canli_gt_test.cjs [ekran_görüntüsü_klasörü]
//   BASE=http://localhost:8766 · BASE_HTML=_base_test.html (eski sürüm; maç öncesi pencerenin değişmediğini karşılaştırmak için)
const fs = require("fs"), path = require("path");
let chromium; try { ({ chromium } = require("playwright")); } catch (e) { ({ chromium } = require(path.join(process.env.HOME || "/root", ".npm-global/lib/node_modules/playwright"))); }
const ROOT = path.resolve(__dirname, "..");
const BASE = process.env.BASE || "http://localhost:8766";
const SHOTS = path.resolve(process.argv[2] || path.join(ROOT, "lab", "_shots"));
fs.mkdirSync(SHOTS, { recursive: true });
const T0 = Date.parse("2026-10-26T20:30:00+03:00");
let pass = 0, fail = 0; const FAILS = [];
const ok = (c, msg) => { if (c) { pass++; console.log("  ✓", msg); } else { fail++; FAILS.push(msg); console.log("  ✗", msg); } };

function fakeLive(now, min) {
  const ev = [
    { eventId: 7001, phase: 1, ci: 501, homeTeam: "Arsenal", awayTeam: "Chelsea", eventDate: Math.floor((now - (min + 17) * 60e3) / 1000) },
    { eventId: 7002, phase: 1, ci: 502, homeTeam: "Testspor", awayTeam: "Örnekspor", eventDate: Math.floor((now - 47 * 60e3) / 1000) }];
  const sc = {
    7001: { ht: { c: 2, ht: 1, co: 5, yc: 1, rc: 0 }, at: { c: 0, ht: 0, co: 3, yc: 2, rc: 0 }, min, sec: 0, s: 3, t: now },
    7002: { ht: { c: 0, ht: 0, co: 2, yc: 0, rc: 0 }, at: { c: 0, ht: 0, co: 1, yc: 1, rc: 0 }, min: 30, sec: 0, s: 2, t: now } };
  return { data: { events: ev, competitions: { 501: { n: "İngiltere Premier Lig", cid: "GB" }, 502: { n: "Test Ligi", cid: "TR" } }, sc } };
}
const fakeSb = { data: { events: [
  { i: 7001, s: 1, m: [{ t: 4, st: 1, s: 1, o: [{ n: "1", odd: 1.06 }, { n: "0", odd: 9 }, { n: "2", odd: 21 }] }, { t: 4, st: 14, s: 1, sov: 2.5, o: [{ n: "Alt", odd: 1.45 }, { n: "Üst", odd: 2.6 }] },
    { t: 4, st: 34, s: 1, sov: 3, o: [{ n: "1", odd: 2.6 }, { n: "Olmaz", odd: 1.9 }, { n: "2", odd: 3.2 }] }] },
  { i: 7002, s: 1, m: [{ t: 4, st: 1, s: 1, o: [{ n: "1", odd: 2.4 }, { n: "0", odd: 2.9 }, { n: "2", odd: 3.3 }] }] }] } };
const sb = (now) => ({ events: [{ id: "999101", date: new Date(now - 80 * 60e3).toISOString(), status: { displayClock: "63'", type: { state: "in", shortDetail: "63'" } },
  competitions: [{ competitors: [{ homeAway: "home", team: { id: "1", displayName: "Arsenal" }, score: "2" }, { homeAway: "away", team: { id: "2", displayName: "Chelsea" }, score: "0" }] }] }] });
const S = (h, a) => Object.entries({ shotsOnTarget: [h[0], a[0]], totalShots: [h[1], a[1]], possessionPct: [h[2], a[2]], wonCorners: [h[3], a[3]] });
const summary = (h, a) => ({ header: { competitions: [{ competitors: [{ homeAway: "home", team: { id: "1" } }, { homeAway: "away", team: { id: "2" } }] }] },
  boxscore: { teams: [{ team: { id: "2" }, statistics: S(h, a).map(([n, v]) => ({ name: n, displayValue: String(v[1]) })) }, { team: { id: "1" }, statistics: S(h, a).map(([n, v]) => ({ name: n, displayValue: String(v[0]) })) }] } });

async function run(vw, vh, tag) {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: 2, locale: "tr-TR", timezoneId: "Europe/Istanbul" });
  await ctx.addInitScript(() => { localStorage.setItem("bx-terms", JSON.stringify({ v: "2.0", at: Date.now(), kvkk: true, inst: Date.now() })); localStorage.setItem("bx-oxxai-hos", "1"); localStorage.setItem("bx-oxxai-ikon", "1"); localStorage.setItem("bx-coach", "1"); });
  const p = await ctx.newPage(); const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  p.on("console", m => { if (/canli-gt/.test(m.text())) console.log("   [konsol]", m.text()); });
  let now = T0, min = 63, stats = summary([2, 7, 47, 5], [5, 12, 53, 3]);
  await p.clock.setFixedTime(new Date(now));
  const req = { sum: 0, sb: 0, idl: 0 };
  await p.route(/iddaa\.com|espn|jsdelivr|googleapis|gstatic|web3forms|abacus|api\./, r => r.fulfill({ status: 404, body: "" }));
  await p.route(/statisticsv2\.iddaa\.com\/live-results\?sportId=1$/, r => { req.idl++; r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fakeLive(now, min)) }); });
  await p.route(/sportsbookv2\.iddaa\.com\/sportsbook\/events\?st=1/, r => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fakeSb) }));
  await p.route(/site\.api\.espn\.com\/apis\/site\/v2\/sports\/soccer\/[^/]+\/scoreboard/, r => { req.sb++; r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(/eng\.1\//.test(r.request().url()) ? sb(now) : { events: [] }) }); });
  await p.route(/site\.api\.espn\.com\/apis\/site\/v2\/sports\/soccer\/eng\.1\/summary\?event=999101/, async r => { req.sum++; await new Promise(z => setTimeout(z, 150)); r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(stats) }); });
  await p.goto(BASE + "/index.html");
  for (let i = 0; i < 60; i++) { const r = await p.evaluate(() => { try { return FIXTURES.length > 0 && typeof window.liveProbs === "function" && !!(DAILY && DAILY.canli); } catch (e) { return false; } }); if (r) break; await p.waitForTimeout(500); }
  await p.evaluate(async () => { IDL.lam["7001"] = [1.9, 0.95]; await IDL.load(1, true); });
  await p.waitForTimeout(400);
  const shot = async n => p.screenshot({ path: path.join(SHOTS, `${tag}_${n}.png`) });
  const overflow = async () => p.evaluate(() => { const vw = document.documentElement.clientWidth; let n = 0; const bad = []; const root = document.querySelector("#msheet"); if (!root) return { n: -1 };
    root.querySelectorAll("*").forEach(e => { const r = e.getBoundingClientRect(); if (!r.width || !r.height) return; const cs = getComputedStyle(e); if (cs.visibility === "hidden" || cs.display === "none") return;
      if (e.closest("svg") && e.tagName !== "svg") return; if (r.right > vw + 1 || r.left < -1) { if (e.closest(".msc-w,.ms-tabs,[style*='overflow']")) return; n++; if (bad.length < 5) bad.push(e.className + "@" + Math.round(r.right)); } });
    return { n, bad, sw: document.documentElement.scrollWidth, vw }; });
  const ovc = async n => { const o = await overflow(); ok(o.n === 0 && !(o.sw > o.vw + 1), `${tag} ${n}: yatay taşma yok (${o.n} ${JSON.stringify(o.bad || [])}, ${o.sw}/${o.vw})`); };

  // 1) maç öncesi maç: düğme / etiket yok
  const pre = await p.evaluate(() => { try { PL_RESET(); } catch (e) {} const m = Pick.list().find(x => !x.live && !x.started && x.dt.getTime() > Date.now() + 3600e3 && x.src === "fx"); if (!m) return null; openMatch(m);
    const el = $("msheet"); return { cgt: !!el.querySelector(".cgt"), prel: !!el.querySelector(".cgt-pre"), h: m.h, a: m.a, txt: el.querySelector(".ms-body").innerText.length }; });
  ok(pre && !pre.cgt && !pre.prel, `${tag} maç öncesi maçta düğme ve etiket yok (${pre && pre.h} – ${pre && pre.a})`);
  await p.evaluate(() => closeMatch());

  // 2) canlı maç: düğme görünür, sonuç yok; değerler henüz istatistiksiz
  await p.evaluate(() => openMatch(IDL.byId[1][7001]));
  await p.waitForTimeout(600);   // açılış animasyonu bitsin (ölçüm ölçekli kutudan yapılmasın)
  let st = await p.evaluate(() => { const el = $("msheet"), b = el.querySelector(".cgt-btn"); const r = b && b.getBoundingClientRect();
    return { btn: !!b, vis: !!(r && r.width > 40 && r.height >= 40), res: !!el.querySelector(".cgt-res"), at: (el.querySelector(".cgt-at") || {}).textContent, adj: !!liveProbs(IDL.byId[1][7001]).adj }; });
  ok(st.btn && st.vis && !st.res && !st.adj, `${tag} canlı maçta "Güncel tahmin" düğmesi görünür (${st.at}) ${JSON.stringify([st.btn, st.vis, st.res, st.adj])}`);
  await shot("01_canli_once"); await ovc("canli_once");

  // 3) bas (çift dokunuş → tek ESPN özet isteği)
  const r0 = { ...req };
  await p.evaluate(() => { const b = $("msheet").querySelector(".cgt-btn"); b.click(); b.click(); window.cgtRefresh(); });
  await p.waitForFunction(() => !!document.querySelector("#msheet .cgt-res"), null, { timeout: 8000 });
  await p.waitForTimeout(200);
  st = await p.evaluate(() => { const el = $("msheet"), m = IDL.byId[1][7001], P = liveProbs(m), B = liveProbsBase(m);
    return { rows: el.querySelectorAll(".cgt-r").length, arrows: [...el.querySelectorAll(".cgt-v i")].map(x => x.textContent).join(""), txt: el.querySelector(".cgt-res").innerText,
      adj: P.adj && { mH: P.adj.mH, mA: P.adj.mA }, H: P.H, H0: B.H, LH: P.LH, LH0: P.LH0, at: el.querySelector(".cgt-at").textContent }; });
  ok(req.sum - r0.sum === 1, `${tag} çift dokunuşta tek ESPN özet isteği (${req.sum - r0.sum})`);
  ok(st.rows === 9 && /[▲▼=]/.test(st.arrows), `${tag} 9 satır önceki → şimdi (${st.arrows})`);
  ok(st.adj && st.adj.mA > 1 && st.adj.mH < 1 && st.adj.mA <= 1.25 + 1e-9 && st.adj.mH >= 0.8 - 1e-9, `${tag} istatistik ayarı deplasman lehine ve ±%25 sınırında (mH ${st.adj && st.adj.mH.toFixed(3)}, mA ${st.adj && st.adj.mA.toFixed(3)})`);
  ok(st.H < st.H0 && Math.abs(st.H - st.H0) < 0.05, `${tag} MS 1 olasılığı ölçülü düştü (${st.H0.toFixed(4)} → ${st.H.toFixed(4)})`);
  ok(/İstatistik: isabetli şut 2-5/.test(st.txt) && /Kaynak: iddaa/.test(st.txt), `${tag} gerekçe ve kaynak notu`);
  ok(/Son güncelleme/.test(st.at), `${tag} son güncelleme saati: ${st.at}`);
  await shot("02_canli_guncel"); await ovc("canli_guncel");
  await p.evaluate(() => { const el = $("msheet"); el.scrollTop = el.querySelector(".cgt").offsetTop - 20; }); await p.waitForTimeout(100); await shot("03_canli_guncel_kart");

  // 4) 12 dk sonra: deplasman 4 isabetli şut daha → "son 12 dk'da" gerekçesi
  now += 12 * 60e3; min = 75; stats = summary([2, 8, 44, 5], [9, 18, 56, 6]);
  await p.clock.setFixedTime(new Date(now));
  await p.evaluate(() => window.cgtRefresh());
  await p.waitForTimeout(500);
  st = await p.evaluate(() => { const el = $("msheet"); return { txt: el.querySelector(".cgt-res").innerText, at: el.querySelector(".cgt-at").textContent }; });
  ok(/Chelsea son 12 dk'da 4 isabetli şut \(rakip 0\), baskı arttı/.test(st.txt), `${tag} son dönem baskı gerekçesi: ${(st.txt.match(/Chelsea son[^·.]*/) || [""])[0]}`);
  ok(/75/.test(st.at), `${tag} dakika güncellendi: ${st.at}`);
  await shot("04_canli_ikinci_guncelleme");

  // 4b) sunucu (scripts/canli_istat.py) ile uygulama formülü birebir aynı mı?
  const IN = { st: { sot: [2, 9], sh: [8, 18], pos: [44, 56] }, prev: { sot: [2, 5] }, L: [1.9, 0.95], t: 75 };
  const js = await p.evaluate(I => { const F = CGT.feats(I.st, I.prev, I.L, I.t), M = CGT.multOf(F); return [F.ds, F.dh, F.dp, F.w, F.wt, F.tl, M.mH, M.mA]; }, IN);
  const py = JSON.parse(require("child_process").execFileSync("python3", ["-c", `import sys,json; sys.path.insert(0,"scripts"); import canli_istat as C; I=json.loads(sys.argv[1]); F=C.feats(I["st"],I["prev"],I["L"],I["t"]); m=C.mult(F); print(json.dumps([F["ds"],F["dh"],F["dp"],F["w"],F["wt"],F["tl"],m[0],m[1]]))`, JSON.stringify(IN)], { cwd: ROOT }).toString());
  ok(js.every((x, i) => Math.abs(x - py[i]) < 1e-12), `${tag} JS ↔ Python istatistik formülü aynı (mH ${js[6].toFixed(4)}, mA ${js[7].toFixed(4)})`);
  st = await p.evaluate(() => $("msheet").querySelector(".cgt-res").innerText);
  ok(/12 dk geçti, gol yok/.test(st), `${tag} MS gerekçesinde süre etkisi`);

  // 4c) v117 kalan süre modeli: uygulama (canli-dr-v117) ↔ sunucu (canli_istat.rem_share + collector.live_pred) birebir
  const DR = await p.evaluate(() => { const h1 = (MODEL && MODEL.params && MODEL.params.h1) || .4428, Z = CDR.ZDEF, R = [];
    const T = [0, 10, 30, 44.5, 45, 46, 47, 48.5, 50, 60, 75, 85, 89.9, 90, 91, 93, 95, 97, 100];
    for (const z of [null, Z]) for (const pd of [null, 0, 1, 2]) for (const t of T) R.push({ t, pd, z: !!z, v: CDR.remShare(t, pd, z) });
    const C = []; const save = DAILY.canli.zaman; const gOn = CGT.G && CGT.G.on; if (CGT.G) CGT.G.on = false;   // eski yol paritesi (CG ayrı sınanır: lab/canli_guc_test.cjs)
    const cases = [[30, 2, 0, 0, [0, 0]], [47, 2, 1, 0, [0, 0]], [45, 49, 1, 1, [0, 0]], [63, 3, 2, 0, [0, 1]], [88, 3, 1, 1, [0, 0]], [93, 3, 0, 1, [1, 0]], [96, 3, 2, 2, [0, 0]]];
    for (const kab of [false, true]) { DAILY.canli.zaman = Object.assign({}, Z, { kabul: kab });
      for (const [min, stc, hs, as, rc] of cases) { IDL.lam["7999"] = [1.6, 1.1]; const m = { sp: 1, id: 7999, hs, as, rc, min, st: stc, odds: {} };
        const P = CGT.core(m, 1, 1); C.push({ min, st: stc, hs, as, rc, kab, H: P.H, D: P.D, A: P.A, LT: P.LH + P.LA, none: P.none, nh: P.nextH }); } }
    DAILY.canli.zaman = save; delete IDL.lam["7999"]; if (CGT.G) CGT.G.on = gOn;
    return { h1, Z, R, C, cur: CDR.zaman(), m93: fbMinute("90'+3'"), m45: fbMinute("45'+2'"), m63: fbMinute("63'") }; });
  const pyDR = JSON.parse(require("child_process").execFileSync("python3", ["-c", `
import sys,json; sys.path.insert(0,"scripts"); import canli_istat as CI, collector as CO
I=json.loads(sys.stdin.read()); h1=I["h1"]; Z=dict(CI.ZDEF)
R=[CI.rem_share(r["t"],h1,r["pd"],Z if r["z"] else None) for r in I["R"]]
C=[]
for c in I["C"]:
    pd=CI.period_of(c["st"]); t=45.0 if pd==0 else float(c["min"]); P=CO.live_pred(1.6,1.1,c["hs"],c["as"],t,c["rc"],h1,pd,Z if c["kab"] else None)
    C.append([P["H"],P["D"],P["A"],P["LT"],P["none"],P["nh"]])
print(json.dumps({"R":R,"C":C,"Z":{k:CI.ZDEF[k] for k in ("e1","e2","xi","rmin")}}))`], { cwd: ROOT, input: JSON.stringify(DR) }).toString());
  const dR = Math.max(...DR.R.map((r, i) => Math.abs(r.v - pyDR.R[i]))), dC = Math.max(...DR.C.map((c, i) => Math.max(...[c.H, c.D, c.A, c.LT, c.none, c.nh].map((x, j) => Math.abs(x - pyDR.C[i][j])))));
  ok(["e1", "e2", "xi", "rmin"].every(k => DR.Z[k] === pyDR.Z[k]), `${tag} v117 ZDEF JS = Python (${JSON.stringify(pyDR.Z)})`);
  ok(dR < 1e-12, `${tag} kalan süre payı JS ↔ Python birebir (${DR.R.length} durum, en büyük fark ${dR.toExponential(1)})`);
  ok(dC < 1e-12, `${tag} canlı olasılık (core ↔ collector.live_pred) birebir (${DR.C.length} durum, eski+v117, en büyük fark ${dC.toExponential(1)})`);
  const g = (t, pd, z) => DR.R.find(r => r.t === t && r.pd === pd && r.z === z).v, h1 = DR.h1;
  ok(g(93, 2, false) <= .012 + 1e-12 && g(93, null, false) <= .012 + 1e-12 && g(93, 2, true) < g(90, 2, true) && g(93, 2, true) < .05,
    `${tag} 90+X uzatma devresine (120) düşmüyor (eski 93' ${g(93, 2, false).toFixed(4)}, v117 90' ${g(90, 2, true).toFixed(4)} → 93' ${g(93, 2, true).toFixed(4)})`);
  ok(g(45, 0, false) === 1 - h1 && g(45, 0, true) === 1 - h1 && g(47, 0, true) === 1 - h1, `${tag} devre arası: kalan pay = 1 − h1 (${(1 - h1).toFixed(4)})`);
  ok(g(47, 1, true) > 1 - h1 && g(47, 1, true) < g(44.5, 1, true) && g(47, 2, true) < 1 - h1, `${tag} v117 ilk yarı uzatması (45+2) ikinci yarı sanılmıyor (${g(47, 1, true).toFixed(4)} > ${(1 - h1).toFixed(4)})`);
  ok(DR.R.filter(r => r.z && (r.pd === 1 || r.pd === 2)).every((r, i, a) => i === 0 || a[i - 1].pd !== r.pd || a[i - 1].v >= r.v - 1e-15), `${tag} v117 kalan pay dakikayla artmıyor (monoton)`);
  ok(DR.m93 === 93 && DR.m45 === 45 && DR.m63 === 63, `${tag} ESPN saati 90'+3' → ${DR.m93}, 45'+2' → ${DR.m45}`);
  console.log(`   (yayındaki kalan süre modeli: ${DR.cur ? "v117 " + JSON.stringify(DR.cur) : "eski doğrusal — daily.json canli.zaman kapısı kabul etmedi"})`);

  // 5) tek doğruluk kaynağı: pencere öneri kartı = Power Now = KUPO "OXX şimdi" = liveShown
  const C = await p.evaluate(async () => { const m = IDL.byId[1][7001], P = liveProbs(m), K = idlPick(m, P), k = K.best.k;
    const shown = Math.round(liveShown(m, k) * 100);
    const rb = (($("msheet").querySelector(".recbig .rb-p em") || {}).textContent || "").replace(/\D/g, "");
    const box = [...$("msheet").querySelectorAll(".ms-body .mo")].find(b => b.dataset.mk === k); const boxP = box ? Math.round(+box.dataset.p * 100) : null;
    const pw = pwLiveCands().find(x => x.m.id === 7001); const pwP = pw ? Math.round(pw.p * 100) : null;
    closeMatch();
    cpToggle({ lg: "i" + m.ci, h: m.h, a: m.a, dt: new Date(m.ts) }, k, K.best.o, liveShown(m, k));
    const m2 = IDL.byId[1][7002]; const x2 = Math.round(liveShown(m2, "X") * 100);
    cpToggle({ lg: "i" + m2.ci, h: m2.h, a: m2.a, dt: new Date(m2.ts) }, "X", 2.9, liveShown(m2, "X"));
    kxOpen("cp"); await new Promise(r => setTimeout(r, 700)); try { kxLiveDeco(); } catch (e) {}
    const kx = [...document.querySelectorAll("#cpBox .kx-lv .n b")].map(x => x.textContent.replace(/\D/g, ""));
    document.querySelector('nav.tabs button[data-v="power"]') && document.querySelector('nav.tabs button[data-v="power"]').click();
    await new Promise(r => setTimeout(r, 400)); try { renderPower(); } catch (e) {}
    const pwRow = [...document.querySelectorAll("#v-power .pw-r")].find(r => /Arsenal/.test(r.textContent)); const pwTxt = pwRow ? (pwRow.querySelector(".pw-s b") || {}).textContent : null;
    const yasak = typeof LGF !== "undefined" && m.min != null && +m.min >= LGF.dkmax;   // v135/v136: dkmax ve sonrası Power Now tavsiyesi yok
    return { x2, k, shown, rb, boxP, pwP, kx, pwTxt: pwTxt ? pwTxt.replace(/\D/g, "") : null, adj: !!P.adj, yasak, dk: m.min }; });
  await shot("05_power_now");
  ok(C.adj && String(C.shown) === C.rb && C.boxP === C.shown && (C.yasak ? C.pwP === null && C.pwTxt === null : C.pwP === C.shown && C.pwTxt === String(C.shown)) && C.kx.includes(String(C.shown)),
    `${tag} aynı olasılık her yerde (${C.k}): pencere %${C.rb}, kutu %${C.boxP}, Power Now %${C.pwP}/${C.pwTxt}${C.yasak ? ` (${C.dk}'. dk ≥ son dakika sınırı: tavsiye yok, beklenen)` : ""}, KUPO %${C.kx.join(",")}, liveShown %${C.shown}`);
  ok(C.kx.includes(String(C.x2)), `${tag} KUPO'da en olası olmayan seçim (MS X) de aynı kaynaktan: %${C.x2} (${C.kx.join(",")})`);
  await p.evaluate(() => kxOpen("cp")); await p.waitForTimeout(500); await shot("06_kupo_canli");

  // 6) Seçenekler sekmesi canlıda: CANLI etiketi + bilgi satırları
  await p.evaluate(() => { openMatch(IDL.byId[1][7001]); msGo("oran"); }); await p.waitForTimeout(250);
  st = await p.evaluate(() => { const el = $("msheet"); return { lv: (el.querySelector(".cgt-lv") || {}).textContent || "", info: el.querySelectorAll(".cgt-info .cgt-r").length, pz: !!el.querySelector(".pz") }; });
  ok(/CANLI/.test(st.lv) && /istatistik/.test(st.lv) && st.info === 5 && !st.pz, `${tag} Seçenekler canlıda etiketli, maç öncesi panel yok (${st.lv.slice(0, 60)}…)`);
  await shot("07_canli_secenekler"); await ovc("canli_secenekler");
  await p.evaluate(() => closeMatch());

  // 7) istatistik yok → skor/zaman modeline zarif düşüş
  await p.evaluate(() => openMatch(IDL.byId[1][7002])); await p.waitForTimeout(150);
  const b0 = await p.evaluate(() => { const m = IDL.byId[1][7002]; return [liveProbs(m).H, liveProbsBase(m).H]; });
  await p.evaluate(() => window.cgtRefresh()); await p.waitForTimeout(600);
  st = await p.evaluate(() => { const el = $("msheet"), m = IDL.byId[1][7002]; return { note: (el.querySelector(".cgt-note.warn") || {}).textContent || "", adj: !!liveProbs(m).adj, rows: el.querySelectorAll(".cgt-r").length }; });
  ok(/İstatistik yok/.test(st.note) && !st.adj && st.rows === 9 && b0[0] === b0[1], `${tag} istatistik yoksa not + skor/zaman modeli: ${st.note}`);
  const sums = await p.evaluate(() => { const R = []; for (const m of IDL.live[1]) { const s3 = ["1", "X", "2"].reduce((a, k) => a + liveShown(m, k), 0), sg = ["G1", "G0", "G2"].reduce((a, k) => a + liveShown(m, k), 0), P = liveProbs(m);
      R.push([s3, sg, liveShown(m, "U" + P.line) + liveShown(m, "A" + P.line), liveShown(m, "KGV") + liveShown(m, "KGY")]); } return R; });
  ok(sums.every(r => r.every(x => Math.abs(x - 1) < 1e-9)), `${tag} gösterilen yüzdeler grup içinde %100 (1/X/2, sıradaki gol, Alt/Üst, KG): ${JSON.stringify(sums.map(r => r.map(x => +x.toFixed(4))))}`);
  await shot("08_istatistik_yok"); await ovc("istatistik_yok");
  await p.evaluate(() => closeMatch());

  // 8) başlamış ama canlı bülteni olmayan maç: "MAÇ ÖNCESİ" etiketi
  st = await p.evaluate(() => { const f = FIXTURES.find(x => x.lg === "en") || FIXTURES[0]; openMatch({ src: "fx", lg: f.lg, h: f.h, a: f.a, dt: new Date(Date.now() - 30 * 60e3), started: true, live: false });
    const el = $("msheet"); return { pre: (el.querySelector(".cgt-pre") || {}).textContent || "", btn: !!el.querySelector(".cgt-btn") }; });
  ok(/MAÇ ÖNCESİ/.test(st.pre) && !st.btn, `${tag} başlamış/canlı verisiz maçta maç öncesi etiketi, düğme yok`);
  await shot("09_mac_oncesi_etiket");
  await p.evaluate(() => closeMatch());
  ok(errs.length === 0, `${tag} pageerror 0 ${JSON.stringify(errs.slice(0, 3))}`);
  await b.close();
}

// maç öncesi pencere eski sürümle birebir aynı mı?
async function same(vw, vh) {
  const bh = process.env.BASE_HTML; if (!bh || !fs.existsSync(path.join(ROOT, bh))) { console.log("  (BASE_HTML yok: karşılaştırma atlandı)"); return; }
  const grab = async (file) => { const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: vw, height: vh }, locale: "tr-TR", timezoneId: "Europe/Istanbul" });
    await ctx.addInitScript(() => { localStorage.setItem("bx-terms", JSON.stringify({ v: "2.0", at: Date.now(), kvkk: true, inst: Date.now() })); localStorage.setItem("bx-oxxai-hos", "1"); localStorage.setItem("bx-oxxai-ikon", "1"); localStorage.setItem("bx-coach", "1"); });
    const p = await ctx.newPage(); await p.clock.setFixedTime(new Date(T0)); await p.route(/iddaa\.com|espn|jsdelivr|googleapis|gstatic|web3forms|abacus|api\./, r => r.fulfill({ status: 404, body: "" }));
    await p.goto(BASE + "/" + file);
    for (let i = 0; i < 60; i++) { const r = await p.evaluate(() => { try { try { PL_RESET(); } catch (e) {} return FIXTURES.length > 0 && Pick.list().length > 0; } catch (e) { return false; } }); if (r) break; await p.waitForTimeout(500); }
    await p.waitForTimeout(1500);
    const out = await p.evaluate(() => { try { PL_RESET(); } catch (e) {} const L = Pick.list().filter(x => x.src === "fx" && x.dt.getTime() > Date.now() + 3600e3).slice(0, 4); const R = [];
      for (const m of L) for (const t of ["tahmin", "oran"]) { openMatch(m, t); R.push($("msheet").innerHTML.replace(/\d{2}:\d{2}:\d{2}/g, "")); closeMatch(); } return R; });
    await b.close(); return out; };
  const A = await grab(bh), B = await grab("index.html");
  ok(A.length > 0 && A.length === B.length && A.every((x, i) => x === B[i]), `maç öncesi pencereler eski sürümle birebir aynı (${A.length} görünüm)`);
}

(async () => {
  console.log("390 px"); await run(390, 844, "390");
  console.log("360 px"); await run(360, 740, "360");
  await same(390, 844);
  console.log(`\nSONUÇ: ${pass} geçti, ${fail} kaldı`); if (fail) { console.log(FAILS.join("\n")); process.exit(1); }
})();
