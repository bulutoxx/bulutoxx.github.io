// YH-92 sondası: bültendeki her takım için "<takım> maçı" sorusu + büyük kulüp kontrol soruları; cevap sorulan takımın maçına mı gidiyor?
// doğru = cevap metni takımın bültendeki adını içeriyor, genel liste ("Önümüzdeki …") değil, "bulamadım" değil.
// Kullanım: node lab/bot_tek_takim_sonda.mjs <çıktı.json>   (BOT_COACH_TIME ile saat sabitlenir; kök = bu dosyanın deposu)
import fs from "fs"; import path from "path"; import http from "http"; import { createRequire } from "module"; import { fileURLToPath } from "url";
const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = process.argv[2] || "sonda.json";
const NOW = new Date(process.env.BOT_COACH_TIME || Date.now());
const { chromium } = require("playwright");
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp" };
const srv = await new Promise(res => { const s = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split("?")[0]); if (p === "/") p = "/index.html";
  const f = path.join(ROOT, path.normalize(p).replace(/^(\.\.[/\\])+/, "")); fs.readFile(f, (e, b) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" }); r.end(b); }); });
  s.listen(0, "127.0.0.1", () => res(s)); });
const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: "block" });
await ctx.addInitScript(() => { localStorage.setItem("bx-terms", JSON.stringify({ v: "2.0", at: Date.now(), kvkk: true, inst: Date.now() })); localStorage.setItem("bx-oxxai-hos", "1"); localStorage.setItem("bx-oxxai-ikon", "1"); });
const p = await ctx.newPage(); const errs = []; p.on("pageerror", e => errs.push(String(e.message || e).slice(0, 200)));
await p.clock.setFixedTime(NOW);
await p.route(/iddaa\.com|espn|jasoncameron|jsdelivr|api-sports|huggingface|googleapis|gstatic/, r => r.fulfill({ status: 404, body: "" }));
await p.goto(`http://127.0.0.1:${srv.address().port}/index.html`, { timeout: 90000 }); await p.waitForTimeout(3000);
for (let i = 0; i < 45; i++) { const ok = await p.evaluate(() => { try { if (FIXTURES.length && window.PL_RESET) PL_RESET(); return FIXTURES.length && Pick.list().length && !!DAILY; } catch (e) { return false; } }); if (ok) break; if (i % 5 === 4) await p.evaluate(() => { try { dailyLoad(); } catch (e) { } }); await p.waitForTimeout(1000); }
try { await p.waitForLoadState("networkidle", { timeout: 20000 }); } catch (e) { }
await p.waitForTimeout(2500); await p.evaluate(async () => { try { PL_RESET(); } catch (e) { } try { await (window.BOT70 && BOT70.ready); } catch (e) { } });
const teams = await p.evaluate(() => { const now = Date.now(), S = new Set(); for (const m of Pick.list()) { const t = m.dt.getTime(); if (t < now || t > now + 8 * 864e5 || m.live) continue; S.add(m.h); S.add(m.a); } return [...S].sort(); });
const KONTROL = ["real madrid", "atletico madrid", "manchester united", "manchester city", "inter", "milan", "sporting", "porto", "benfica", "real madrid maçı", "atletico madrid maçı", "manchester united maçı", "manchester city maçı", "inter maçı", "milan maçı", "sporting maçı", "porto maçı", "benfica maçı", "stuttgart", "stuttgart maçı", "sporting lizbon maçı"];
const rows = [];
const Q = teams.map(t => ({ t, q: t + " maçı" })).concat(KONTROL.map(q => ({ t: null, q })));
for (const { t, q } of Q) {
  const r = await p.evaluate(async q => { BOT.ctx = null; BOT.hist = []; if (window.BOT70) { BOT70.resetSession(); BOT70.testMode(true); }
    let R; try { R = await botAnswer(q); } catch (e) { R = { html: "" }; } const d = document.createElement("div"); d.innerHTML = R.html || ""; return d.textContent.replace(/\s+/g, " ").trim(); }, q);
  const genel = /^(Önümüzdeki saatlerde|Önümüzdeki günlerde)/.test(r), bulamadi = /bulamadım/.test(r);
  rows.push({ takim: t, soru: q, kontrol: !t, dogru: t ? (!genel && !bulamadi && r.toLowerCase().includes(t.toLowerCase())) : null, genel, text: r.slice(0, 300) });
}
fs.writeFileSync(OUT, JSON.stringify({ saat: NOW.toISOString(), n: rows.length, pageerror: errs, rows }, null, 1));
const tk = rows.filter(x => !x.kontrol);
console.log(`[sonda] ${tk.length} takım · doğru ${tk.filter(x => x.dogru).length} · yanlış/genel ${tk.filter(x => !x.dogru).length} · kontrol ${rows.length - tk.length} · pageerror ${errs.length}`);
await b.close(); srv.close();
