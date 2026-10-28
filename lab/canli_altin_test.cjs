// v136 · Canlı altın kuralı: uygulama (index.html → canli-v70 build) ↔ toplayıcı (scripts/canli_altin.py sec) birebir testi.
// Tarayıcı gerekmez: betik küçük taslaklarla node vm içinde çalıştırılır. Kullanım: node lab/canli_altin_test.cjs
const fs = require("fs"), path = require("path"), vm = require("vm"), cp = require("child_process");
const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const src = html.match(/<script id="canli-v70">([\s\S]*?)<\/script>/)[1];
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
console.log(`\n${pass} geçti, ${fail} kaldı`); process.exit(fail ? 1 : 0);
