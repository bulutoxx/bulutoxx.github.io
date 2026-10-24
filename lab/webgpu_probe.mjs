// Gerçek WebLLM + Qwen3.5 modelini uygulamanın içinde, WebGPU'lu Chrome ile dener (yazılımsal GPU: yavaş ama gerçek)
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const root = path.resolve("lab/site"); const out = { adim: [] }; const log = (...a) => { console.log(...a); out.adim.push(a.join(" ")); };
const types = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".png": "image/png", ".webmanifest": "application/json" };
http.createServer((q, r) => { let f = path.join(root, decodeURIComponent(q.url.split("?")[0])); if (f.endsWith("/")) f += "index.html";
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { "content-type": types[path.extname(f)] || "application/octet-stream" }); r.end(d); }); }).listen(8777);
const model = process.argv[2] || "hafif";
const b = await chromium.launch({ headless: true, args: ["--enable-unsafe-webgpu", "--enable-features=Vulkan", "--use-angle=vulkan", "--use-vulkan=swiftshader", "--use-webgpu-adapter=swiftshader", "--ignore-gpu-blocklist"] });
const ctx = await b.newContext({ serviceWorkers: "block" });
await ctx.addInitScript(() => { localStorage.setItem("bx-terms", JSON.stringify({ v: "1.0", at: Date.now() })); });
const p = await ctx.newPage(); p.on("console", m => { const t = m.text(); if (/webllm|WebGPU|error|Error/i.test(t)) log("konsol:", t.slice(0, 200)); }); p.on("pageerror", e => log("sayfa hatası:", e.message));
await p.goto("http://localhost:8777/", { waitUntil: "load" }); await p.waitForTimeout(4000);
const gpu = await p.evaluate(async () => { if (!navigator.gpu) return "navigator.gpu yok"; const a = await navigator.gpu.requestAdapter(); if (!a) return "adapter yok"; return "adapter var; f16=" + a.features.has("shader-f16") + " maxBuf=" + a.limits.maxBufferSize; });
log("WebGPU:", gpu); out.gpu = gpu;
if (/adapter var/.test(gpu)) {
  const t0 = Date.now();
  await p.evaluate(m => { botOpen(); return brainLoad(m); }, model);
  const st = await p.evaluate(() => ({ st: BRAIN.st, err: BRAIN.err, id: BRAIN.id }));
  log("yükleme:", JSON.stringify(st), Math.round((Date.now() - t0) / 1000) + " sn"); out.yukleme = st; out.yukleme_sn = Math.round((Date.now() - t0) / 1000);
  if (st.st === "ready") {
    out.cevaplar = [];
    for (const q of ["bugün hava nasıl", "aslanların maçında karşılıklı gol çıkar mı", "en iyi forvet kim", "bana yarın için 3 maçlık kombine düşün", "kuponum yattı moralim bozuk"]) {
      const t1 = Date.now(); const j = await p.evaluate(q => brainAsk(q), q);
      log("soru:", q, "→", JSON.stringify(j), Math.round((Date.now() - t1) / 1000) + " sn"); out.cevaplar.push({ q, j, sn: Math.round((Date.now() - t1) / 1000) });
    }
  }
}
fs.writeFileSync("lab/webgpu_probe_" + model + ".json", JSON.stringify(out, null, 1)); await b.close(); process.exit(0);
