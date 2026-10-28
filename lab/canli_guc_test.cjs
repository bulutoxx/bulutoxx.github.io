// Canlı güç (CG) · uygulama çekirdeği (index.html → canli-gt-v107 core, CG açık) ↔ sunucu (scripts/canli_guc.py) birebir testi.
// Tarayıcı gerekmez: canli-gt-v107 betiği küçük taslaklarla (stub) node vm içinde çalıştırılır. Kullanım: node lab/canli_guc_test.cjs
const fs = require("fs"), path = require("path"), vm = require("vm"), cp = require("child_process");
const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const src = html.match(/<script id="canli-gt-v107">([\s\S]*?)<\/script>/)[1];
const flag = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "canli_guc.json"), "utf8"));
let pass = 0, fail = 0; const ok = (c, m) => { c ? pass++ : fail++; console.log(c ? "  ✓" : "  ✗", m); };

function run(flagJson) {
  const ctx = {
    console, Math, JSON, Object, Array, Map, Number, String, isFinite, Promise, Date, setTimeout,
    sessionStorage: { getItem: () => null, setItem: () => {} },
    fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve(flagJson) }),
    poisV: (l, K) => { const o = []; let p = Math.exp(-l); for (let k = 0; k <= K; k++) { o.push(p); p *= l / (k + 1); } return o; },
    poisCdf: (k, l) => { if (k < 0) return 0; let p = Math.exp(-l), c = p; for (let i = 1; i <= k; i++) { p *= l / i; c += p; } return Math.min(1, c); },
    IDL: { lam: {} }, idlSecs: m => m.min * 60, idlPred: () => null, fbRemShare: () => .5, liveCal: p => ({ p: p * .9 }),
    msRender: () => {}, openMatch: () => {}, FIXTURES: [],
  };
  ctx.window = ctx; ctx.CDR = { pdOf: c => (c.pd != null ? c.pd : c.st === 2 ? 1 : c.st === 3 ? 2 : c.st === 49 ? 0 : null) };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  return ctx;
}

(async () => {
  const ctx = run(flag); await new Promise(r => setTimeout(r, 20));
  ok(ctx.CGT.G.on === !!flag.kullan, `bayrak okundu: kullan=${flag.kullan} → G.on=${ctx.CGT.G.on}`);
  const on = run(Object.assign({}, flag, { kullan: true })); await new Promise(r => setTimeout(r, 20));
  const cases = [[0, 1, 0, 0, [0, 0]], [12, 1, 1, 0, [0, 0]], [30, 1, 0, 0, [0, 0]], [46, 1, 1, 1, [0, 0]], [45, 0, 2, 0, [0, 0]], [55, 2, 0, 1, [0, 0]],
    [63, 2, 2, 0, [0, 1]], [75, 2, 1, 1, [1, 0]], [88, 2, 0, 0, [0, 0]], [93, 2, 1, 2, [0, 0]], [97, 2, 3, 3, [1, 1]], [30, null, 0, 2, [0, 0]]];
  const parity = async (params, tag) => {
  const on = run(Object.assign({}, flag, { kullan: true, params })); await new Promise(r => setTimeout(r, 20));
  const J = cases.map(([min, pd, hs, as, rc]) => { on.IDL.lam["9"] = [1.6, 1.1]; const P = on.CGT.core({ sp: 1, id: 9, min, pd, hs, as, rc, odds: { ou: { l: hs + as + 1.5 } } }, 1, 1);
    return [P.H, P.D, P.A, P.o25, P.none, P.nextH, P.nextA, P.pOver, P.r15, P.LH, P.LA, P.model === "cg" ? 1 : 0]; });
  const py = JSON.parse(cp.execFileSync("python3", ["-c", `
import sys,json; sys.path.insert(0,"scripts"); import canli_guc as CG
I=json.loads(sys.stdin.read()); P=dict(CG.DEF); P.update({k:float(v) for k,v in I["p"].items() if k in P}); out=[]
for min_,pd,hs,as_,rc in I["c"]:
    t=float(min_); R=CG.probs(1.6,1.1,hs,as_,t,rc,pd,P)
    out.append([R["H"],R["D"],R["A"],R["o25"],R["none"],R["nh"],R["na"],CG.over(R,hs+as_+1.5,hs+as_),max(0.0,1-sum(R["tot"][:2])),R["LH"],R["LA"],1])
print(json.dumps(out))`], { cwd: ROOT, input: JSON.stringify({ p: params, c: cases }) }).toString());
  const d = Math.max(...J.map((r, i) => Math.max(...r.map((x, j) => Math.abs(x - py[i][j])))));
  ok(d < 1e-12, `CG olasılıkları JS ↔ Python birebir — ${tag} (${cases.length} durum, en büyük fark ${d.toExponential(1)})`);
  ok(J.every(r => Math.abs(r[0] + r[1] + r[2] - 1) < 1e-9 && r.slice(0, 9).every(x => x >= 0 && x <= 1)), `olasılıklar geçerli (1/X/2 toplamı 1) — ${tag}`);
  return J; };
  const J0 = await parity(flag.params, "bayrak");
  // v136: geç dakika parametreleri (e2, rmin, g_l2, g_ldl) nötr değilken de birebir; nötrken eski CG ile aynı
  const J1 = await parity(Object.assign({}, flag.params, { e2: 4.2, rmin: 1.6, g_l2: .25, g_ldl: .18 }), "geç dakika parametreleri");
  const Jn = await parity(Object.assign({}, flag.params, { e2: 3, rmin: 1, g_l2: 0, g_ldl: 0 }), "nötr");
  const late = cases.map((c, i) => c[0] >= 70 ? Math.abs(J1[i][9] - Jn[i][9]) : 0);
  ok(Math.max(...late) > 1e-3 && cases.every((c, i) => c[0] >= 60 || Math.abs(J1[i][9] - Jn[i][9]) < 1e-12 || c[1] === 2), "geç parametreler yalnız 2. yarı / geç dakikaları etkiler");
  // kapalı bayrak: eski yol aynen (Poisson, model "eski")
  const off = run(Object.assign({}, flag, { kullan: false })); await new Promise(r => setTimeout(r, 20)); off.IDL.lam["9"] = [1.6, 1.1];
  const Po = off.CGT.core({ sp: 1, id: 9, min: 60, pd: 2, hs: 1, as: 0, rc: [0, 0], odds: {} }, 1, 1);
  ok(Po.model === "eski" && !off.CGT.G.on, "kullan=false → eski yol");
  // gösterim: CG açıkken liveCal eski Platt'ı uygulamaz (kal=null → olduğu gibi)
  ok(Math.abs(on.liveCal(.7234567).p - (flag.kal ? on.liveCal(.7234567).p : .7234567)) < 1e-12 && Math.abs(off.liveCal(.7234567).p - .7234567 * .9) < 1e-12, "liveCal: CG açık → kendi kalibrasyonu, kapalı → eski");
  console.log(`\n${pass} geçti, ${fail} kaldı`); process.exit(fail ? 1 : 0);
})();
