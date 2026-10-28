// v136 · Canlı altın kuralı: uygulama (index.html → canli-v70 build) ↔ toplayıcı (scripts/canli_altin.py sec) birebir testi.
// Tarayıcı gerekmez: betik küçük taslaklarla node vm içinde çalıştırılır. Kullanım: node lab/canli_altin_test.cjs
const fs = require("fs"), path = require("path"), vm = require("vm"), cp = require("child_process");
const ROOT = path.resolve(__dirname, "..");
const K = require("./_kaynak.cjs");   // v143: bloklar js/*.js paketlerinde (/* id: … */)
const src = K.blok("canli-v70");
let pass = 0, fail = 0; const ok = (c, m) => { c ? pass++ : fail++; console.log(c ? "  ✓" : "  ✗", m); };
let rnd = 7; const R = () => (rnd = (rnd * 16807) % 2147483647) / 2147483647;
const cases = [];
for (let n = 0; n < 300; n++) {
  const k = 1 + Math.floor(R() * 9), L = [];
  for (let i = 0; i < k; i++) L.push({ id: "m" + Math.floor(R() * 12), k: ["1", "X", "2", "A2.5", "G0"][Math.floor(R() * 5)], p: Math.min(.99, .8 + R() * .2), o: +(1.01 + R() * .5).toFixed(2), dk: Math.floor(R() * 95) });
  const F = { tekli: [.8, .85, .9, .95][Math.floor(R() * 4)], kombine: [.75, .8, .85, .9][Math.floor(R() * 4)], aday: .8, dkmax: [75, 80][Math.floor(R() * 2)] };
  cases.push({ L: L.sort((a, b) => b.p - a.p), F });
}
const js = cases.map(({ L, F }) => {
  const ctx = { console, Math, JSON, Object, Array, Set, String, Number, isFinite, document: { querySelector: () => null, querySelectorAll: () => [] },
    $: () => null, LGF: Object.assign({ durum: null }, F), pwLiveCands: () => L.map(x => ({ m: { id: x.id, min: x.dk }, k: x.k, p: x.p, o: x.o })), IDL: { ok: {} } };
  ctx.window = ctx; vm.createContext(ctx); vm.runInContext(src.replace(/\bconst LGF\b/, "var _x"), ctx);
  const K = ctx.lgBuild(); return K ? { sel: K.sel.map(x => x.m.id + ":" + x.k), p: K.p, o: K.o } : null;
});
const py = JSON.parse(cp.execFileSync("python3", ["-c", `
import sys,json; sys.path.insert(0,"scripts"); import canli_altin as CA
out=[]
for c in json.loads(sys.stdin.read()):
    K=CA.sec(c["L"], c["F"]); out.append({"sel":[x["id"]+":"+x["k"] for x in K["sel"]],"p":K["p"],"o":K["o"]} if K else None)
print(json.dumps(out))`], { cwd: ROOT, input: JSON.stringify(cases) }).toString());
let bad = 0, nk = 0, nt = 0;
js.forEach((a, i) => { const b = py[i]; if (a && a.sel.length > 1) nk++; if (a && a.sel.length === 1) nt++;
  const same = (!a && !b) || (a && b && a.sel.join() === b.sel.join() && Math.abs(a.p - b.p) < 1e-12 && Math.abs(a.o - b.o) < 1e-9); if (!same) { bad++; if (bad < 4) console.log("   fark", i, JSON.stringify(a), JSON.stringify(b)); } });
ok(bad === 0, `altın seçimi JS ↔ Python birebir (${cases.length} durum: ${nk} kombine, ${nt} tekli, ${cases.length - nk - nt} yok)`);

// v140 · Canlı altın İŞARET (tek maç rozeti): index.html → canli-isaret-v140 aiRule ↔ scripts/canli_altin.py isaret, 300 rastgele durum
{
  const src2 = K.blok("canli-isaret-v140");
  const ctx = { console, Math, JSON, Object, Array, Map, Set, String, Number, isFinite, document: { querySelector: () => null, querySelectorAll: () => [], addEventListener() {} },
    $: () => null, esc: s => String(s), toast() {}, LGF: { isaret: { esik: .8, kapanis: .77, dkmax: 75, durum: "deneme" } }, IDL: { byId: {}, live: {}, load: async () => {} },
    idlRow: () => "", idlBoxHtml: () => "", msRender() {}, idlPick: () => null, idlPred: () => null, IDLV: { sp: 1 } };
  ctx.window = ctx; vm.createContext(ctx); vm.runInContext(src2, ctx);
  const KEYS = ["1", "X", "2", "A2.5", "U2.5", "G1", "G0", "G2"], C2 = [];
  for (let n = 0; n < 300; n++) {
    const all = KEYS.map(k => ({ k, p: R() < .08 ? null : +(R() < .5 ? .5 + R() * .5 : R()).toFixed(4), o: R() < .2 ? null : +(1 + R() * .4).toFixed(2) }));
    const I = { esik: [.8, .85][Math.floor(R() * 2)], kapanis: 0, dkmax: [75, 80][Math.floor(R() * 2)], durum: R() < .05 ? "durduruldu" : "deneme" }; I.kapanis = +(I.esik - .03).toFixed(2);
    const dk = R() < .1 ? null : Math.floor(R() * 95), was = R() < .5, cal = R() < .5 ? null : { a: +(R() * .4 - .2).toFixed(3), b: +(.8 + R() * .4).toFixed(3) };
    C2.push({ all, I, dk, was, cal });
  }
  const js2 = C2.map(({ all, I, dk, was, cal }) => { const f = cal ? (p => (0 < p && p < 1) ? 1 / (1 + Math.exp(-(cal.a + cal.b * Math.log(p / (1 - p))))) : p) : null;
    const r = ctx.aiRule(all, dk, I, was, f); return r ? { k: r.k, p: r.p } : null; });
  const py2 = JSON.parse(cp.execFileSync("python3", ["-c", `
import sys,json; sys.path.insert(0,"scripts"); import canli_altin as CA
out=[]
for c in json.loads(sys.stdin.read()):
    r=CA.isaret([(x["k"],x["p"],x["o"]) for x in c["all"]], c["dk"], c["I"], c["cal"], c["was"]); out.append({"k":r["k"],"p":r["p"]} if r else None)
print(json.dumps(out))`], { cwd: ROOT, input: JSON.stringify(C2) }).toString());
  let bad2 = 0, on2 = 0, hy = 0;
  js2.forEach((a, i) => { const b = py2[i]; if (a) on2++; if (a && C2[i].was && a.p < C2[i].I.esik) hy++;
    const same = (!a && !b) || (a && b && a.k === b.k && Math.abs(a.p - b.p) < 1e-12); if (!same) { bad2++; if (bad2 < 4) console.log("   fark", i, JSON.stringify(a), JSON.stringify(b)); } });
  ok(bad2 === 0, `canlı altın işaret JS ↔ Python birebir (${C2.length} durum: ${on2} işaretli, ${hy} histerezisle açık kalan)`);
  const I0 = { esik: .8, kapanis: .77, dkmax: 75, durum: "deneme" }, A = p => [{ k: "1", n: "MS 1", p, o: 1.2 }];
  ok(!ctx.aiRule(A(.79), 30, I0, false) && !!ctx.aiRule(A(.8), 30, I0, false), "eşik: %79 işaret yok, %80 işaret var");
  ok(!!ctx.aiRule(A(.78), 30, I0, true) && !ctx.aiRule(A(.76), 30, I0, true) && !ctx.aiRule(A(.78), 30, I0, false), "histerezis: açıkken %78 kalır, %76 kalkar; kapalıyken %78 açılmaz");
  ok(!ctx.aiRule(A(.95), 75, I0, true) && !!ctx.aiRule(A(.95), 74, I0, false) && !!ctx.aiRule(A(.95), 45, I0, false), "75. dk ve sonrası işaret yok; devre arası (45) işaret kalabilir");
  ok(!ctx.aiRule([{ k: "1", n: "MS 1", p: .95, o: 1.04 }], 30, I0, false), "oran < 1,05 → işaret yok (canlı altın aday kuralı)");
}
console.log(`\n${pass} geçti, ${fail} kaldı`); process.exit(fail ? 1 : 0);
