// 🎨 Tasarımcı / kalite botu (her gün, GitHub Actions): yayındaki uygulamayı gerçek bir telefon ekranında açar,
// her sayfayı ve düğmeyi tıklar, JavaScript hatalarını, açılış süresini ve boş ekranları ölçer, ekran görüntüleri alır.
// Hata bulursa data/qa.json'a yazar; iş akışı GitHub'da uyarı kaydı (issue) açar.
import { chromium, devices } from "playwright";
import fs from "fs";
const URL = process.env.QA_URL || "https://bulutoxx.github.io/";
const out = { zaman: new Date().toISOString(), url: URL, hatalar: [], sayfalar: {}, dugme: { tiklanan: 0, hata: 0 }, acilis_ms: null };
fs.mkdirSync("data/qa", { recursive: true });
const b = await chromium.launch();
const ctx = await b.newContext({ ...devices["iPhone 13"], deviceScaleFactor: 1, serviceWorkers: "block" });
await ctx.addInitScript(() => { localStorage.setItem("bx-terms", JSON.stringify({ v: "1.0", at: Date.now() })); navigator.share = undefined; window.open = () => null; });
const p = await ctx.newPage();
const errs = []; p.on("pageerror", e => errs.push(String(e.message).slice(0, 300)));
p.on("dialog", d => d.dismiss());
const t0 = Date.now();
await p.goto(URL + "?qa=" + Date.now(), { waitUntil: "load", timeout: 60000 });
await p.waitForSelector(".ib-r, .panel.empty", { timeout: 30000 }).catch(() => out.hatalar.push("Bülten 30 sn içinde dolmadı"));
out.acilis_ms = Date.now() - t0;
await p.waitForTimeout(3000);
const views = [["bulten", 'nav.tabs button[data-v="bulten"]'], ["canli", 'nav.tabs button[data-v="canli"]'], ["power", "#navPow"], ["sonuclar", "#navRes"], ["menu", 'nav.tabs button[data-v="more"]']];
const DENY = /sil|sıfırla|temizle|paylaş|yükle|indir|install|bildirim|reset/i;
for (const [name, sel] of views) {
  errs.length = 0;
  try { await p.click(sel, { timeout: 5000 }); } catch (e) { out.hatalar.push(`${name}: menü düğmesi tıklanamadı`); continue; }
  await p.waitForTimeout(2500);
  const info = await p.evaluate(() => { const s = document.querySelector("section.view:not([hidden])"); return { id: s && s.id, metin: s ? s.innerText.length : 0 }; });
  await p.screenshot({ path: `data/qa/${name}.jpg`, type: "jpeg", quality: 55 });
  if (info.metin < 80) out.hatalar.push(`${name}: sayfa neredeyse boş (${info.metin} karakter)`);
  // görünür düğmeleri tek tek tıkla
  const n = await p.$$eval("section.view:not([hidden]) button:not([disabled])", x => x.filter(e => e.offsetParent).length);
  for (let i = 0; i < Math.min(n, 25); i++) {
    const t = await p.evaluate(i => { const el = [...document.querySelectorAll("section.view:not([hidden]) button:not([disabled])")].filter(e => e.offsetParent)[i]; if (!el) return null; el.setAttribute("data-qa", i); return (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 40); }, i);
    if (t == null || DENY.test(t)) continue;
    const before = errs.length;
    try { await p.click(`[data-qa="${i}"]`, { timeout: 2500 }); out.dugme.tiklanan++; } catch (e) { }
    await p.waitForTimeout(300);
    if (errs.length > before) { out.dugme.hata++; out.hatalar.push(`${name} › "${t}": ${errs[errs.length - 1]}`); }
    await p.keyboard.press("Escape");
    await p.evaluate(() => { const sh = document.getElementById("sheet"); if (sh && !sh.hidden) { sh.hidden = true; sh.innerHTML = ""; } const ms = document.getElementById("msheet"); if (ms && !ms.hidden && typeof closeMatch === "function") closeMatch(); const g = document.getElementById("gate"); if (g) g.remove(); document.querySelectorAll("[data-qa]").forEach(x => x.removeAttribute("data-qa")); });
    const cur = await p.evaluate(() => { const s = document.querySelector("section.view:not([hidden])"); return s && s.id; });
    if (cur !== info.id) { try { await p.click(sel, { timeout: 3000 }); await p.waitForTimeout(800); } catch (e) { } }
  }
  out.sayfalar[name] = { metin: info.metin, dugme: n };
}
if (errs.length) out.hatalar.push(...errs.map(e => "JS: " + e));
out.alarm = out.hatalar.length > 0;
fs.writeFileSync("data/qa.json", JSON.stringify(out, null, 1));
console.log(JSON.stringify(out, null, 1));
await b.close();
