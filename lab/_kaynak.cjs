// 🧩 Uygulama kaynağı okuyucu (testler ve lab araçları için ortak yardımcı; v143).
// index.html artık ince bir kabuk: satır içi katmanlar js/*.js paketlerinde, her biri `/* id: <eski-id> */` işaretiyle.
// Paket biçimi (sırası index.html'deki <script src> sırası):
//   /* id: <id> */ try {<blok>} catch (e) { … } /* /id: <id> */      ← katman (hata yalnız o katmanı durdurur)
//   /* id: ana */<blok>                                                ← çekirdek (js/core.js, "use strict" dosya başında)
// Kullanım:
//   const K = require("./_kaynak.cjs");
//   K.blok("canli-v70")        → bloğun kaynak metni (eskiden <script id="canli-v70">…</script> içi)
//   K.bloklar()                → [{id, tur:"script"|"style", ic, dosya}] index.html sırasıyla (satır içi + paketler)
//   K.tumKaynak()              → index.html + tüm paketler (metin araması / sözlük çıkarma için tek metin)
//   K.paketler()               → index.html'in yüklediği js/ ve css/ dosyaları (sırayla)
// İsteğe bağlı ilk argüman: index.html yolu (varsayılan depo kökündeki). Paketler o dosyanın klasörüne göre çözülür,
// orada yoksa depo köküne düşülür (BOT_COACH_INDEX gibi başka bir index.html sınanırken).
const fs = require("fs"), path = require("path");
const ROOT = path.resolve(__dirname, "..");

function oku(indexYol) {
  const yol = indexYol ? path.resolve(indexYol) : path.join(ROOT, "index.html");
  return { yol, dir: path.dirname(yol), html: fs.readFileSync(yol, "utf8") };
}
function dosyaYolu(dir, rel) {
  const a = path.join(dir, rel); if (fs.existsSync(a)) return a;
  return path.join(ROOT, rel);
}
const ETIKET = /<script\b([^>]*)>([\s\S]*?)<\/script>|<style\b([^>]*)>([\s\S]*?)<\/style>|<link\b([^>]*rel="stylesheet"[^>]*)>/g;
const SARMA = /\/\* id: ([\w.\-]+) \*\/ try \{([\s\S]*?)\} catch \(e\) \{[^\n]*?\/\* \/id: \1 \*\/\n/g;

function paketBloklari(metin, dosya) {
  const out = [];
  if (/^\/\* id: ([\w.\-]+) \*\/(?! try \{)/.test(metin)) {           // sarılmamış tek blok (js/core.js)
    const m = /^\/\* id: ([\w.\-]+) \*\//.exec(metin);
    out.push({ id: m[1], tur: "script", ic: metin.slice(m[0].length), dosya });
    return out;
  }
  let m; SARMA.lastIndex = 0;
  while ((m = SARMA.exec(metin))) out.push({ id: m[1], tur: "script", ic: m[2], dosya });
  return out;
}

function bloklar(indexYol) {
  const { dir, html } = oku(indexYol);
  const out = []; let m; ETIKET.lastIndex = 0;
  while ((m = ETIKET.exec(html))) {
    if (m[1] !== undefined) {
      const src = /\bsrc="([^"?]+)/.exec(m[1]);
      if (src) {
        const f = dosyaYolu(dir, src[1]);
        if (/^js\//.test(src[1]) && fs.existsSync(f)) out.push(...paketBloklari(fs.readFileSync(f, "utf8"), src[1]));
      } else {
        const id = (/\bid="([^"]+)"/.exec(m[1]) || [, "ana"])[1];
        out.push({ id, tur: "script", ic: m[2], dosya: "index.html" });
      }
    } else if (m[3] !== undefined) {
      out.push({ id: (/\bid="([^"]+)"/.exec(m[3]) || [, ""])[1], tur: "style", ic: m[4], dosya: "index.html" });
    } else {
      const href = /\bhref="([^"?]+)/.exec(m[5]), id = (/\bid="([^"]+)"/.exec(m[5]) || [, ""])[1];
      if (href && /^css\//.test(href[1])) { const f = dosyaYolu(dir, href[1]); if (fs.existsSync(f)) out.push({ id, tur: "style", ic: fs.readFileSync(f, "utf8"), dosya: href[1] }); }
    }
  }
  return out;
}

function blok(id, indexYol) {
  const b = bloklar(indexYol).find(x => x.id === id && x.tur === "script");
  if (!b) throw new Error(`blok bulunamadı: ${id} (index.html satır içi ya da js/*.js içinde /* id: ${id} */)`);
  return b.ic;
}

function paketler(indexYol) {
  const { html } = oku(indexYol);
  return [...html.matchAll(/(?:src|href)="((?:js|css)\/[^"?]+)/g)].map(m => m[1]);
}

function tumKaynak(indexYol) {
  const { dir, html } = oku(indexYol);
  return [html, ...paketler(indexYol).map(f => { const y = dosyaYolu(dir, f); return fs.existsSync(y) ? fs.readFileSync(y, "utf8") : ""; })].join("\n");
}

module.exports = { ROOT, blok, bloklar, paketler, tumKaynak };
