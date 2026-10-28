// v144 · YH-10 · Canlı piyasa harmanı: uygulama (js/katmanlar.js → canli-piyasa-v144 + canli-gt-v107 core kancası + core.js idlOdds)
// ↔ sunucu (scripts/canli_guc.py piyasa() / harman() / over()) birebir testi. Tarayıcı gerekmez (node vm). Kullanım: node lab/canli_piyasa_test.cjs
const fs = require("fs"), path = require("path"), vm = require("vm"), cp = require("child_process");
const ROOT = path.resolve(__dirname, "..");
const K = require("./_kaynak.cjs");
const srcGt = K.blok("canli-gt-v107"), srcPz = K.blok("canli-piyasa-v144");
const core = fs.readFileSync(path.join(ROOT, "js", "core.js"), "utf8");
const srcOdds = /function idlOdds\(e, sp\)\{[\s\S]*?\n\}\n/.exec(core)[0];
const cg = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "canli_guc.json"), "utf8"));
let pass = 0, fail = 0; const ok = (c, m) => { c ? pass++ : fail++; console.log(c ? "  ✓" : "  ✗", m); };
let rnd = 11; const R = () => (rnd = (rnd * 16807) % 2147483647) / 2147483647;
const DL = ["0", "30", "60", "75"];
const W = {}; for (const m of ["ms", "ou", "ng"]) { W[m] = {}; for (const d of DL) W[m][d] = [+(R() * 1.2).toFixed(4), +(R() * 1.4).toFixed(4)]; }

function run(pzFlag) {
  const ctx = {
    console, Math, JSON, Object, Array, Map, Set, Number, String, isFinite, Promise, Date, setTimeout,
    sessionStorage: { getItem: () => null, setItem: () => {} },
    fetch: u => Promise.resolve({ ok: true, json: () => Promise.resolve(/canli_guc/.test(u) ? Object.assign({}, cg, { kullan: true }) : /canli_piyasa/.test(u) ? pzFlag : null) }),
    poisV: (l, K) => { const o = []; let p = Math.exp(-l); for (let k = 0; k <= K; k++) { o.push(p); p *= l / (k + 1); } return o; },
    poisCdf: (k, l) => { if (k < 0) return 0; let p = Math.exp(-l), c = p; for (let i = 1; i <= k; i++) { p *= l / i; c += p; } return Math.min(1, c); },
    IDL: { lam: {} }, idlSecs: m => m.min * 60, idlPred: () => null, fbRemShare: () => .5, liveCal: p => ({ p }),
    msRender: () => {}, openMatch: () => {}, FIXTURES: [],
  };
  ctx.window = ctx; ctx.CDR = { pdOf: c => (c.pd != null ? c.pd : null) };
  vm.createContext(ctx); vm.runInContext(srcOdds + "\nwindow.idlOdds=idlOdds;", ctx); vm.runInContext(srcGt, ctx); vm.runInContext(srcPz, ctx);
  return ctx;
}
const od = () => +(1.02 + R() * 6).toFixed(2);
function olay() {   // iddaa sportsbook canlı etkinliği (yalnız test için yapay)
  const m = [], lk = () => (R() < .12 ? 2 : 1);
  if (R() < .9) m.push({ t: 4, st: R() < .5 ? 1 : 4, s: lk(), o: [{ n: "1", odd: od() }, { n: "0", odd: od() }, { n: "2", odd: od() }] });
  if (R() < .2) m.push({ t: 4, st: 4, s: 1, o: [{ n: "1", odd: od() }, { n: "0", odd: od() }, { n: "2", odd: od() }] });  // ikinci MS pazarı (ilk alınır)
  const nl = Math.floor(R() * 4);
  for (let i = 0; i < nl; i++) m.push({ t: 4, st: R() < .5 ? 14 : 101, s: lk(), sov: String(.5 + Math.floor(R() * 6)), o: [{ n: "Alt", odd: od() }, { n: "Üst", odd: od() }] });
  if (R() < .7) m.push({ t: 4, st: 34, s: lk(), sov: "1", o: [{ n: "1", odd: od() }, { n: "Olmaz", odd: od() }, { n: "2", odd: od() }] });
  if (R() < .3) m.push({ t: 1, st: 1, s: 1, o: [{ n: "1", odd: 2 }, { n: "0", odd: 3 }, { n: "2", odd: 4 }] });                 // maç öncesi pazar: yok sayılır
  return { s: 1, m };
}

(async () => {
  const on = run({ kullan: true, W }); await new Promise(r => setTimeout(r, 20));
  ok(on.CGT.G.on && on.CPH.H.on, "bayraklar okundu: CG açık, piyasa harmanı açık");
  const cases = [];
  for (let n = 0; n < 400; n++) {
    const min = Math.floor(R() * 97), hs = Math.floor(R() * 4), as = Math.floor(R() * 3), pd = min < 45 ? 1 : 2, rc = [R() < .1 ? 1 : 0, R() < .1 ? 1 : 0];
    cases.push({ min, hs, as, pd, rc, e: olay(), lam: [+(0.6 + R() * 1.6).toFixed(3), +(0.5 + R() * 1.4).toFixed(3)] });
  }
  const J = cases.map(c => { on.IDL.lam["9"] = c.lam; const m = { sp: 1, id: 9, min: c.min, pd: c.pd, hs: c.hs, as: c.as, rc: c.rc, odds: on.idlOdds(c.e, 1) };
    const P = on.CGT.core(m, 1, 1); return [P.H, P.D, P.A, P.nextH, P.none, P.nextA, P.pOver, P.line, P.harman ? 1 : 0]; });
  const py = JSON.parse(cp.execFileSync("python3", ["-c", `
import sys,json; sys.path.insert(0,"scripts"); import canli_guc as CG, canli_altin as CA
I=json.loads(sys.stdin.read()); P=dict(CG.DEF); P.update({k:float(v) for k,v in I["p"].items() if k in P})
W={m:{d:tuple(v) for d,v in I["W"][m].items()} for m in I["W"]}; out=[]
for c in I["c"]:
    t=float(c["min"]); hs,as_=c["hs"],c["as"]
    Pr=CG.probs(c["lam"][0],c["lam"][1],hs,as_,t,c["rc"],c["pd"],P); mk=CG.piyasa(c["e"]); R=CG.harman(Pr,mk,t,W,hs+as_)
    cand=dict((k,p) for k,p,o in CA.uygulama_adaylari(c["e"],R,hs,as_)); line=[k for k in cand if k[0]=="U"][0][1:]
    out.append([R["H"],R["D"],R["A"],R["nh"],R["none"],R["na"],cand["U"+line],float(line),1 if mk else 0])
print(json.dumps(out))`], { cwd: ROOT, input: JSON.stringify({ p: cg.params, W, c: cases }) }).toString());
  let d = 0, nh = 0; J.forEach((r, i) => { nh += r[8]; for (let j = 0; j < 9; j++) d = Math.max(d, Math.abs(r[j] - py[i][j])); });
  ok(d < 1e-12, `harmanlı olasılıklar JS ↔ Python birebir (${cases.length} durum, ${nh} piyasalı; en büyük fark ${d.toExponential(1)})`);
  ok(J.every(r => Math.abs(r[0] + r[1] + r[2] - 1) < 1e-9 && Math.abs(r[3] + r[4] + r[5] - 1) < 1e-9 && r.slice(0, 7).every(x => x >= 0 && x <= 1 + 1e-12)), "olasılıklar geçerli (üçlüler toplamı 1)");
  // piyasa olasılığı (marjı ayrılmış) JS ↔ Python
  const mkJ = cases.map(c => { const x = on.CPH.piyasa(on.idlOdds(c.e, 1)); return [x.ms || null, x.ou || null, x.ng || null]; });
  const mkP = JSON.parse(cp.execFileSync("python3", ["-c", `
import sys,json; sys.path.insert(0,"scripts"); import canli_guc as CG
print(json.dumps([[CG.piyasa(c["e"]).get(k) for k in ("ms","ou","ng")] for c in json.loads(sys.stdin.read())]))`], { cwd: ROOT, input: JSON.stringify(cases) }).toString());
  let dm = 0, bad = 0; mkJ.forEach((r, i) => r.forEach((x, j) => { const y = mkP[i][j]; if ((x == null) !== (y == null)) bad++; else if (x) x.forEach((v, k) => dm = Math.max(dm, Math.abs(v - y[k]))); }));
  ok(!bad && dm < 1e-12, `marjı ayrılmış piyasa olasılığı JS ↔ Python birebir (eksik pazar uyumsuzluğu ${bad}, en büyük fark ${dm.toExponential(1)})`);
  ok(mkJ.every(r => (!r[0] || Math.abs(r[0][0] + r[0][1] + r[0][2] - 1) < 1e-12) && (!r[2] || Math.abs(r[2].reduce((a, b) => a + b, 0) - 1) < 1e-12)), "piyasa olasılıkları toplamı 1 (marj ayrıldı)");
  // kapalı bayrak: CG aynen (harman yok, sonuçlar kancasız çalışmayla aynı)
  const off = run({ kullan: false, W }); await new Promise(r => setTimeout(r, 20));
  const offPy = JSON.parse(cp.execFileSync("python3", ["-c", `
import sys,json; sys.path.insert(0,"scripts"); import canli_guc as CG
I=json.loads(sys.stdin.read()); P=dict(CG.DEF); P.update({k:float(v) for k,v in I["p"].items() if k in P}); out=[]
for c in I["c"]:
    Pr=CG.probs(c["lam"][0],c["lam"][1],c["hs"],c["as"],float(c["min"]),c["rc"],c["pd"],P); out.append([Pr["H"],Pr["D"],Pr["A"],Pr["nh"],Pr["none"],Pr["na"]])
print(json.dumps(out))`], { cwd: ROOT, input: JSON.stringify({ p: cg.params, c: cases }) }).toString());
  let d0 = 0, anyH = false; cases.forEach((c, i) => { off.IDL.lam["9"] = c.lam; const P = off.CGT.core({ sp: 1, id: 9, min: c.min, pd: c.pd, hs: c.hs, as: c.as, rc: c.rc, odds: off.idlOdds(c.e, 1) }, 1, 1);
    anyH = anyH || !!P.harman; [P.H, P.D, P.A, P.nextH, P.none, P.nextA].forEach((x, j) => d0 = Math.max(d0, Math.abs(x - offPy[i][j]))); });
  const ch = J.filter((r, i) => Math.abs(r[0] - offPy[i][0]) > 1e-4 || Math.abs(r[4] - offPy[i][4]) > 1e-4).length;
  ok(ch > cases.length / 2, `harman açıkken olasılıklar gerçekten değişiyor (${ch}/${cases.length} durumda)`);
  ok(!off.CPH.H.on && !anyH && d0 < 1e-12, `kullan=false → harman yok, CG aynen (en büyük fark ${d0.toExponential(1)})`);
  // geçersiz ağırlık → kapalı
  const bad1 = run({ kullan: true, W: Object.assign({}, W, { ms: { "0": [5, 1] } }) }); await new Promise(r => setTimeout(r, 20));
  ok(!bad1.CPH.H.on, "geçersiz ağırlık → harman kapalı");
  // sunucu bayrağı: depodaki data/canli_piyasa.json ile Python harman_ayar ve JS aynı kararı verir
  const flag = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "canli_piyasa.json"), "utf8"));
  const fj = run(flag); await new Promise(r => setTimeout(r, 20));
  const pyOn = cp.execFileSync("python3", ["-c", `import sys; sys.path.insert(0,"scripts"); import canli_guc as CG; print(1 if CG.harman_ayar("data") else 0, 1 if CG.harman_ayar("data", golge=True) else 0)`], { cwd: ROOT }).toString().trim().split(" ");
  ok((fj.CPH.H.on ? "1" : "0") === pyOn[0] && pyOn[1] === "1", `depo bayrağı: kullan=${flag.kullan} → JS ${fj.CPH.H.on}, Python ${pyOn[0] === "1"}; gölge ağırlık hazır`);
  // kayıt biçimi: yalnız 3 haneli olasılık, ham oran yok
  const rec = JSON.parse(cp.execFileSync("python3", ["-c", `
import sys,json; sys.path.insert(0,"scripts"); import canli_guc as CG
print(json.dumps(CG.mk_kayit(CG.piyasa(json.loads(sys.stdin.read())))))`], { cwd: ROOT, input: JSON.stringify(cases.find(c => c.e.m.length > 2).e) }).toString());
  const vals = [].concat(rec.ms || [], rec.ng || [], rec.ou ? [rec.ou[1]] : []);
  ok(vals.length > 0 && vals.every(x => x >= 0 && x <= 1 && Math.abs(x * 1000 - Math.round(x * 1000)) < 1e-6), "canlı kayıt biçimi: 3 haneli olasılık (ham oran yok)");
  console.log(`\n${pass} geçti, ${fail} kaldı`); process.exit(fail ? 1 : 0);
})();
