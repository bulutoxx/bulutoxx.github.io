// 🎨 Tasarımcı / kalite botu (Playwright, ücretsiz). Uygulamayı gerçek bir telefon ekranında açar, ana ekranları gezer ve ölçer:
//   Bülten, Canlı, Sonuçlar, Menü, POWER NOW, KUPO, OXXai sohbeti, At (Bugün, Program, Türler, Sonuç, KUPO, arama).
//   Her ekranda: ekran açıldı mı / dolu mu, pageerror sayısı, yatay taşma, görünür metinde yasak kelime.
//   Performans bütçesi: index.html boyutu, ilk ekranın veri boyutu, en uzun ana iş parçacığı görevi.
// Sonuç QA_CIKTI dosyasına (varsayılan data/qa.json) yazılır. Alarm varsa çıkış kodu 1 olur: lab/adim.py bunu sağlık kaydına
// "hata" olarak yazar, kurtarıcı (lab/kurtarici.py) hem bu kaydı hem data/qa*.json alarmını görür. Issue/mail/bildirim AÇMAZ.
//
// Ortam değişkenleri:
//   QA_URL      test edilecek adres (varsayılan https://bulutoxx.github.io/; yerel kopya: http://127.0.0.1:PORT/)
//   QA_MOD      tam (varsayılan; düğmeleri tek tek dener, ekran görüntüsü alır) | hizli (yayın kapısı: yalnız ekranlar, birkaç dakika)
//   QA_CIKTI    sonuç dosyası (varsayılan data/qa.json)
//   QA_EKRAN    ekran görüntüsü klasörü (tam modda varsayılan data/qa; boş = alma)
//   QA_DIS      engelle | izin  — dış alan adlarına istek (yerel adreste varsayılan engelle). tjk.org ve atyarisi.com HER ZAMAN engellenir.
//   QA_BUTCE_INDEX_KB, QA_BUTCE_VERI_KB, QA_BUTCE_GOREV_MS   bütçe sınırları (aşılırsa alarm)
import { chromium, devices } from "playwright";
import fs from "fs";
import path from "path";

const URL0 = process.env.QA_URL || "https://bulutoxx.github.io/";
const URL = URL0.endsWith("/") ? URL0 : URL0 + "/";
const MOD = (process.env.QA_MOD || "tam") === "hizli" ? "hizli" : "tam";
const CIKTI = process.env.QA_CIKTI || "data/qa.json";
const EKRAN = process.env.QA_EKRAN != null ? process.env.QA_EKRAN : (MOD === "tam" ? "data/qa" : "");
const YEREL = /^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(URL);
const DIS = (process.env.QA_DIS || (YEREL ? "engelle" : "izin")) === "engelle";
const BUTCE = {   // alarm sınırları (gerileme kapısı). "hedef" değerleri yalnız bilgi (denetim_mimari §4 hedefleri)
  index_kb: +(process.env.QA_BUTCE_INDEX_KB || 1500),
  veri_kb: +(process.env.QA_BUTCE_VERI_KB || 6000),
  gorev_ms: +(process.env.QA_BUTCE_GOREV_MS || 15000),
};
const SON_AN = Date.now() + 1000 * +(process.env.QA_SURE_SN || (MOD === "hizli" ? 420 : 900));   // bu süreden sonra kalan ekranlar atlanır
const ARDISIK_SINIR = MOD === "hizli" ? 3 : 6;   // art arda bu kadar ekran açılamazsa kalanlar atlanır (uygulama zaten bozuk)
const HEDEF = { index_kb: 1300, veri_aktarim_kb: 900, gorev_ms: 2000 };
const YASAK = [/\b(bahis\w*|ganyan\w*|banko|kupon\w*)\b/gi, /bulut/gi];
const YASAK_ALAN = /(^|\.)(tjk\.org|atyarisi\.com)$/i;

const out = {
  zaman: new Date().toISOString(), url: URL, mod: MOD, hatalar: [], uyarilar: [], sayfalar: {},
  dugme: { tiklanan: 0, hata: 0 }, acilis_ms: null, pageerror: 0, tasma: 0, yasak_kelime: [], butce: null, sure_sn: null, alarm: true,
  aciklama: "Kalite botu (lab/qa.mjs). alarm=true → hatalar listesine bakın; adım sağlık kaydında hata olarak görünür.",
};
const T0 = Date.now();
const errs = [];            // tüm pageerror'lar (ekran adıyla)
let ekran = "acilis";
const hata = m => { if (!out.hatalar.includes(m)) out.hatalar.push(m); };
const uyari = m => { if (!out.uyarilar.includes(m)) out.uyarilar.push(m); };
const bekle = ms => new Promise(r => setTimeout(r, ms));
const maskele = s => s.replace(/(bahis|ganyan|banko|kupon|bulut)/gi, w => w[0] + "•" + w.slice(2));   // yayımlanan raporda kelimenin kendisi geçmesin

let b, p, ardisik = 0;
try {
  if (EKRAN) fs.mkdirSync(EKRAN, { recursive: true });
  b = await chromium.launch({ args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const ctx = await b.newContext({ ...devices["iPhone 13"], deviceScaleFactor: 1, serviceWorkers: "block", locale: "tr-TR", timezoneId: "Europe/Istanbul" });
  ctx.setDefaultTimeout(240000);
  await ctx.route("**/*", r => {
    let h = ""; try { h = new globalThis.URL(r.request().url()).hostname; } catch (e) { }
    if (YASAK_ALAN.test(h)) return r.abort();
    if (DIS && h && !URL.includes("//" + h)) return r.abort();
    return r.continue();
  });
  await ctx.addInitScript(() => {
    try {
      localStorage.setItem("bx-terms", JSON.stringify({ v: "2.0", at: Date.now(), kvkk: true }));
      localStorage.setItem("bx-coach", "1"); localStorage.setItem("bx-oxxai-hos", "1"); localStorage.setItem("bx-oxxai-ikon", "1");
    } catch (e) { }
    try { navigator.share = undefined; } catch (e) { }
    window.open = () => null;
    window.__qa = { lt: [] };
    try { new PerformanceObserver(l => { for (const e of l.getEntries()) window.__qa.lt.push([Math.round(e.startTime), Math.round(e.duration)]); }).observe({ type: "longtask", buffered: true }); } catch (e) { }
  });
  p = await ctx.newPage();
  p.setDefaultTimeout(240000); p.setDefaultNavigationTimeout(240000);
  p.on("pageerror", e => { const m = String(e.message || e).slice(0, 240); errs.push([ekran, m]); });
  p.on("dialog", d => d.dismiss().catch(() => { }));

  // ---------------------------------------------------------------- yardımcılar
  const gorunurView = () => p.evaluate(() => { const s = document.querySelector("main section.view:not([hidden])") || document.querySelector("section.view:not([hidden])"); return s ? s.id : null; });
  const temizle = async () => {      // beklenmeyen katmanlar: onay, yükleme koçu, karşılama kartı, alt sayfa
    const r = await p.evaluate(() => {
      const not = [];
      const g = document.getElementById("gate");
      if (g) { const c = document.getElementById("gAll"), go = document.getElementById("gGo"); if (c && go) { c.checked = true; c.dispatchEvent(new Event("change")); go.disabled = false; go.click(); } else g.remove(); not.push("onay ekranı"); }
      document.querySelectorAll("#instGate,#g2doc,#coach,#ez,.iarrow").forEach(x => { x.remove(); not.push(x.id || x.className); });
      const sh = document.getElementById("sheet"); if (sh && !sh.hidden) { sh.hidden = true; sh.innerHTML = ""; not.push("alt sayfa"); }
      const ms = document.getElementById("msheet"); if (ms && !ms.hidden && typeof closeMatch === "function") { try { closeMatch(); } catch (e) { } }
      const bs = document.getElementById("botSheet"); if (bs && !bs.hidden && typeof botClose === "function") { try { botClose(); } catch (e) { } }
      // genel: alt menüyü ya da üst çubuğu örten sabit katman (yerel alt sayfalar, modallar) → gizle
      for (let k = 0; k < 4; k++) {
        const nav = document.querySelector("nav.tabs"); if (!nav) break;
        const r = nav.getBoundingClientRect(); const el = document.elementFromPoint(innerWidth / 2, Math.min(innerHeight - 2, r.top + r.height / 2));
        if (!el || nav.contains(el)) break;
        let top = el; while (top.parentElement && top.parentElement !== document.body) top = top.parentElement;
        if (!top || top === document.body || top.tagName === "MAIN" || top.tagName === "HEADER" || top.contains(nav)) break;
        top.style.display = "none"; top.setAttribute("data-qa-gizlendi", "1"); not.push("#" + (top.id || top.className || top.tagName));
      }
      return not;
    }).catch(() => []);
    return r;
  };
  const metinOlc = () => p.evaluate(() => {
    const s = document.querySelector("main section.view:not([hidden])");
    const de = document.documentElement;
    return { id: s && s.id, metin: s ? s.innerText.trim().length : 0, tasma: Math.max(de.scrollWidth, document.body.scrollWidth) - de.clientWidth };
  });
  // yasak kelime istisnaları: jokey / antrenör / at adları (at verisindeki büyük harfli adlar), site adresi
  const istisna = new Set();
  for (const f of ["data/at/dizin.json", "data/at/jokeyler.json"]) {
    try {
      const r = await ctx.request.get(URL + f, { timeout: 60000 }); if (!r.ok()) continue;
      const topla = x => { if (typeof x === "string") { if (/^[A-ZÇĞİÖŞÜÂÎÛ .'()-]{3,}$/.test(x)) x.split(/[\s.'()-]+/).forEach(w => w && istisna.add(w.toLocaleLowerCase("tr"))); } else if (Array.isArray(x)) x.forEach(topla); else if (x && typeof x === "object") Object.values(x).forEach(topla); };
      topla(await r.json());
    } catch (e) { }
  }
  const yasakTara = async ad => {
    const t = await p.evaluate(() => document.body.innerText).catch(() => "");
    const temiz = t.replace(/\S*bulutoxx\.github\.io\S*/gi, " ");
    for (const re of YASAK) {
      re.lastIndex = 0; let m;
      while ((m = re.exec(temiz))) {
        let s = m.index, e = m.index + m[0].length;
        while (s > 0 && /[\p{L}\p{N}]/u.test(temiz[s - 1])) s--;
        while (e < temiz.length && /[\p{L}\p{N}]/u.test(temiz[e])) e++;
        const kelime = temiz.slice(s, e);
        if (istisna.has(kelime.toLocaleLowerCase("tr"))) continue;
        const kayit = `${ad}: "${maskele(kelime)}" (…${maskele(temiz.slice(Math.max(0, s - 30), e + 30).replace(/\s+/g, " "))}…)`;
        if (!out.yasak_kelime.some(x => x.startsWith(`${ad}: "${maskele(kelime)}"`))) out.yasak_kelime.push(kayit);
      }
    }
  };
  const tikla = async (sel, ad) => {
    const el = p.locator(sel + " >> visible=true").first();
    await el.waitFor({ state: "visible", timeout: MOD === "hizli" ? 30000 : 60000 });
    await el.click({ timeout: 30000 });
  };
  const fotograf = async ad => { if (EKRAN) await p.screenshot({ path: path.join(EKRAN, `${ad}.jpg`), type: "jpeg", quality: 55 }).catch(() => { }); };
  const DENY = /sil|sıfırla|temizle|paylaş|yükle|indir|install|bildirim|reset|kaldır|çıkış|yenile|ses/i;
  const dugmeleriDene = async (ad, geriSel) => {   // yalnız tam mod: görünür düğmeleri tek tek tıkla
    const id0 = await gorunurView();
    const n = await p.$$eval("main section.view:not([hidden]) button:not([disabled])", x => x.filter(e => e.offsetParent).length).catch(() => 0);
    for (let i = 0; i < Math.min(n, 25); i++) {
      const t = await p.evaluate(i => { document.querySelectorAll("[data-qa]").forEach(x => x.removeAttribute("data-qa")); const el = [...document.querySelectorAll("main section.view:not([hidden]) button:not([disabled])")].filter(e => e.offsetParent)[i]; if (!el) return null; el.setAttribute("data-qa", i); return (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 40); }, i).catch(() => null);
      if (t == null || DENY.test(t)) continue;
      const once = errs.length;
      try { await p.click(`[data-qa="${i}"]`, { timeout: 4000 }); out.dugme.tiklanan++; } catch (e) { continue; }
      await bekle(350);
      if (errs.length > once) { out.dugme.hata++; hata(`${ad} › "${maskele(t)}": ${errs[errs.length - 1][1]}`); }
      await p.keyboard.press("Escape").catch(() => { });
      await temizle();
      if ((await gorunurView()) !== id0) { try { await tikla(geriSel); await bekle(800); } catch (e) { } }
    }
    return n;
  };
  // bir ekranı aç → bekle → ölç
  const atla = ad => {
    if (ardisik >= ARDISIK_SINIR) { out.sayfalar[ad] = { ok: false, atlandi: true }; hata(`${ad}: atlandı (art arda ${ardisik} ekran açılamadı)`); return true; }
    if (Date.now() > SON_AN) { out.sayfalar[ad] = { ok: false, atlandi: true }; hata(`${ad}: atlandı (süre bütçesi doldu)`); return true; }
    return false;
  };
  const kontrol = async (ad, ac, { bekleSel = null, enAz = 60, geriSel = null, dene = true } = {}) => {
    if (atla(ad)) return;
    ekran = ad; const t1 = Date.now(); const e0 = errs.length;
    const S = out.sayfalar[ad] = { ok: false };
    try {
      await temizle();
      await ac();
      if (bekleSel) await p.waitForSelector(bekleSel, { state: "visible", timeout: 90000 });
      // içerik dolana kadar (yavaş makine) en çok 60 sn bekle
      let m = await metinOlc(); const son = Date.now() + 60000;
      while (m.metin < enAz && Date.now() < son) { await bekle(1000); m = await metinOlc(); }
      await bekle(MOD === "tam" ? 1200 : 600);
      m = await metinOlc();
      Object.assign(S, { view: m.id, metin: m.metin, tasma_px: m.tasma });
      if (m.metin < enAz) hata(`${ad}: ekran boş ya da dolmadı (${m.metin} karakter)`);
      if (m.tasma > 1) { out.tasma++; hata(`${ad}: yatay taşma ${m.tasma} px`); }
      await yasakTara(ad);
      await fotograf(ad);
      if (MOD === "tam" && dene && geriSel) S.dugme = await dugmeleriDene(ad, geriSel);
      S.ok = m.metin >= enAz;
    } catch (e) {
      hata(`${ad}: ekran açılamadı (${String(e.message || e).split("\n")[0].slice(0, 160)})`);
      try { const m = await metinOlc(); S.tasma_px = m.tasma; if (m.tasma > 1) { out.tasma++; hata(`${ad}: yatay taşma ${m.tasma} px`); } } catch (e2) { }
      await fotograf(ad + "-hata");
    }
    S.ms = Date.now() - t1;
    S.pageerror = errs.length - e0;
    ardisik = S.ok ? 0 : ardisik + 1;
  };

  // ---------------------------------------------------------------- performans: index.html boyutu
  const butce = out.butce = { sinir: BUTCE, hedef: HEDEF };
  try {
    const r = await ctx.request.get(URL + "index.html?qa=" + Date.now(), { timeout: 120000 });
    butce.index_kb = Math.round((await r.body()).length / 1024);
  } catch (e) { uyari("index.html boyutu ölçülemedi: " + String(e.message).slice(0, 100)); }

  // ---------------------------------------------------------------- açılış
  ekran = "acilis";
  const t0 = Date.now(); const ACILIS_MS = MOD === "hizli" ? 150000 : 240000;
  await p.goto(URL + "?qa=" + Date.now(), { waitUntil: "load", timeout: 240000 });
  try {
    await p.waitForFunction(() => { const s = document.getElementById("v-bulten"); return document.getElementById("gate") || (s && !s.hidden && s.innerText.trim().length > 200); }, null, { timeout: ACILIS_MS, polling: 500 });
  } catch (e) { hata(`açılış: Bülten ${ACILIS_MS / 1000} sn içinde dolmadı`); ardisik++; }
  out.acilis_ms = Date.now() - t0;
  // açılış görseli (splash) kendiliğinden kaybolsun; en çok 20 sn
  await p.waitForFunction(() => { const s = document.getElementById("splash"); if (!s) return true; const r = s.getBoundingClientRect(), c = getComputedStyle(s); return s.hidden || c.display === "none" || c.visibility === "hidden" || +c.opacity === 0 || r.height === 0; }, null, { timeout: 20000, polling: 250 }).catch(() => uyari("açılış görseli 20 sn'de kapanmadı"));
  const ilk = await temizle(); if (ilk.length) uyari("açılışta beklenmeyen katman kapatıldı: " + ilk.join(", "));
  await bekle(1500);
  // ilk ekran veri boyutu (aynı kaynaktan gelen tüm dosyalar; ham = açılmış, aktarım = ağdan geçen, yerelde gzip yok)
  const veri = await p.evaluate(() => { const o = location.origin; let ham = 0, akt = 0, n = 0, dis = 0;
    for (const e of performance.getEntriesByType("resource")) { if (e.name.startsWith(o)) { ham += e.decodedBodySize || 0; akt += e.encodedBodySize || 0; n++; } else dis++; }
    const nav = performance.getEntriesByType("navigation")[0]; if (nav) { ham += nav.decodedBodySize || 0; akt += nav.encodedBodySize || 0; n++; }
    return { ham, akt, n, dis }; });
  Object.assign(butce, { ilk_veri_kb: Math.round(veri.ham / 1024), ilk_aktarim_kb: Math.round(veri.akt / 1024), ilk_istek: veri.n, ilk_dis_istek: veri.dis });

  // ---------------------------------------------------------------- ekranlar
  const NAV = v => `nav.tabs button[data-v="${v}"]`;
  await kontrol("bulten", () => tikla(NAV("bulten")), { bekleSel: "#v-bulten", enAz: 200, geriSel: NAV("bulten") });
  await kontrol("canli", () => tikla(NAV("canli")), { bekleSel: "#v-canli", enAz: 30, geriSel: NAV("canli") });
  await kontrol("sonuclar", () => tikla("#navRes"), { enAz: 60, geriSel: "#navRes" });
  await kontrol("menu", () => tikla(NAV("more")), { bekleSel: "#v-more", enAz: 60, geriSel: NAV("more") });
  await kontrol("power", () => tikla("#navPow"), { enAz: 60, geriSel: "#navPow" });
  await kontrol("kupo", () => tikla("#hdrKup"), { bekleSel: "#v-kupon", enAz: 30, geriSel: "#hdrKup" });

  // OXXai sohbeti: aç, hazır soru gönder, yanıt gelsin, kapat
  ekran = "sohbet";
  if (!atla("sohbet")) {
    const t1 = Date.now(), e0 = errs.length; const S = out.sayfalar.sohbet = { ok: false };
    try {
      await temizle();
      await tikla(NAV("bulten")); await bekle(500);
      await tikla("#hdrBot");
      await p.waitForSelector("#botSheet", { state: "visible", timeout: 60000 });
      const n0 = await p.locator("#botLog .bt-msg.bot").count();
      await p.fill("#botQ", "Sıradaki maçı öner");
      await p.press("#botQ", "Enter");
      await p.waitForFunction(n0 => { const L = [...document.querySelectorAll("#botLog .bt-msg.bot")]; const s = L[L.length - 1]; return L.length > n0 && s && !s.querySelector(".bt-dots") && s.innerText.trim().length > 15; }, n0, { timeout: 120000, polling: 500 });
      S.yanit = await p.evaluate(() => { const L = [...document.querySelectorAll("#botLog .bt-msg.bot")]; return L[L.length - 1].innerText.trim().length; });
      const tas = await metinOlc(); S.tasma_px = tas.tasma; if (tas.tasma > 1) { out.tasma++; hata(`sohbet: yatay taşma ${tas.tasma} px`); }
      await yasakTara("sohbet");
      await fotograf("sohbet");
      await p.click("#botX", { timeout: 15000 }).catch(() => p.evaluate(() => typeof botClose === "function" && botClose()));
      S.ok = true;
    } catch (e) { hata(`sohbet: OXXai yanıt vermedi ya da açılmadı (${String(e.message || e).split("\n")[0].slice(0, 140)})`); await fotograf("sohbet-hata"); }
    S.ms = Date.now() - t1; S.pageerror = errs.length - e0;
    ardisik = S.ok ? 0 : ardisik + 1;
  }

  // At yarışı: spor seçici → sekmeler → arama
  const AT_SEKME = [["at_bugun", "bugun"], ["at_program", "program"], ["at_turler", "turler"], ["at_sonuc", "sonuc"], ["at_kupo", "kupon"]];
  await kontrol("at_bugun", async () => {
    await tikla(NAV("bulten")); await bekle(400);
    await tikla('.sport-sw button[data-s="at"]');
    await p.waitForSelector("#v-at", { state: "visible", timeout: 90000 });
    await p.waitForSelector('#at2Nav a[data-tab="bugun"]', { state: "visible", timeout: 90000 });
    await tikla('#at2Nav a[data-tab="bugun"]');
  }, { enAz: 60, dene: false });
  for (const [ad, tab] of AT_SEKME.slice(1)) {
    await kontrol(ad, async () => {
      await tikla(`#at2Nav a[data-tab="${tab}"]`);
      await p.waitForSelector(`#at2Nav a[data-tab="${tab}"][aria-current="page"]`, { timeout: 60000 });
    }, { enAz: 40, geriSel: `#at2Nav a[data-tab="${tab}"]`, dene: false });
  }
  await kontrol("at_arama", async () => {
    await tikla('#at2Nav a[data-tab="bugun"]'); await bekle(400);
    await tikla("a.a5-sb");
    await p.waitForSelector("#a5q", { state: "visible", timeout: 60000 });
    await p.fill("#a5q", "ahmet");      // yaygın jokey/antrenör adı; sonuç listesi dolmalı
    await p.waitForSelector("#a5res .a5-r", { state: "visible", timeout: 90000 });
  }, { enAz: 40, dene: false });
  ekran = "son";
  if (MOD === "tam") { try { await tikla(NAV("bulten")); } catch (e) { } }

  // ---------------------------------------------------------------- toplam ölçümler
  const lt = await p.evaluate(() => (window.__qa && window.__qa.lt) || []).catch(() => []);
  butce.en_uzun_gorev_ms = lt.reduce((m, x) => Math.max(m, x[1]), 0);
  butce.uzun_gorev_sayisi = lt.length;
  if (butce.index_kb != null && butce.index_kb > BUTCE.index_kb) hata(`bütçe: index.html ${butce.index_kb} KB > ${BUTCE.index_kb} KB`);
  if (butce.ilk_veri_kb > BUTCE.veri_kb) hata(`bütçe: ilk ekran verisi ${butce.ilk_veri_kb} KB > ${BUTCE.veri_kb} KB`);
  if (butce.en_uzun_gorev_ms > BUTCE.gorev_ms) hata(`bütçe: en uzun görev ${butce.en_uzun_gorev_ms} ms > ${BUTCE.gorev_ms} ms`);
  butce.hedefte = { index: (butce.index_kb ?? 1e9) <= HEDEF.index_kb, gorev: butce.en_uzun_gorev_ms <= HEDEF.gorev_ms };
  if (MOD === "tam" && out.dugme.tiklanan === 0) hata("hiçbir düğme denenemedi (seçiciler eskimiş olabilir)");
} catch (e) {
  hata(`betik yarıda kaldı (${ekran}): ${String(e.message || e).split("\n")[0].slice(0, 200)}`);
} finally {
  out.pageerror = errs.length;
  for (const [ad, m] of errs.slice(0, 12)) hata(`JS (${ad}): ${maskele(m)}`);
  if (out.yasak_kelime.length) hata(`yasak kelime: ${out.yasak_kelime.length} yerde (${out.yasak_kelime.slice(0, 3).join(" · ")})`);
  out.sure_sn = Math.round((Date.now() - T0) / 1000);
  out.alarm = out.hatalar.length > 0;
  try { fs.mkdirSync(path.dirname(CIKTI) || ".", { recursive: true }); fs.writeFileSync(CIKTI, JSON.stringify(out, null, 1) + "\n"); } catch (e) { console.error("sonuç yazılamadı:", e.message); }
  console.log(JSON.stringify(out, null, 1));
  try { if (b) await b.close(); } catch (e) { }
  process.exit(out.alarm ? 1 : 0);
}
