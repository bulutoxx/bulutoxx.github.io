#!/usr/bin/env node
// YH-70: yayın kopyasında CSS'in boşluk / yorum küçültmesi (css/*.css paketleri + index.html içindeki <style> blokları; depo kaynağı okunur kalır).
// Kullanım: OXX_KUCULT=<css-tree kurulu (node_modules) klasör> node lab/kucult_css.cjs <yayın_klasörü> css/a.css … [index.html]
// Güvenlik: css-tree ayrıştır → üret (dönüştürme yok: değer kısaltma, kural birleştirme, sıralama YOK; yalnız boşluk / yorum atılır).
// Bildirim değerleri ve @kural önekleri ayrıştırılmaz (parseValue/parseAtrulePrelude: false) → metinleri olduğu gibi (yalnız baş/son boşluk) yazılır;
// tam değer ayrıştırması `140% at` → `140%at` gibi boşluk silip tarayıcı CSSOM metnini değiştirdiği için kapatıldı (YH-70 ölçümü).
// Her CSS parçasının özgün ve küçültülmüş sözdizimi ağacı konum bilgisi dışında BİREBİR karşılaştırılır; fark, hata, küçülmeme ya da
// "</style" içeren çıktı → o parça özgün kalır. Ağ isteği yapmaz; çıktı: JSON özet (stdout son satır).
"use strict";
const fs = require("fs"), path = require("path");
const { createRequire } = require("module");
const dir = process.env.OXX_KUCULT;
if (!dir) { console.log(JSON.stringify({ durum: "atlandi", neden: "OXX_KUCULT yok" })); process.exit(0); }
let ct;
try { ct = createRequire(path.join(path.resolve(dir), "package.json"))("css-tree"); }
catch (e) { console.log(JSON.stringify({ durum: "atlandi", neden: "css-tree yüklenemedi" })); process.exit(0); }

const duz = a => JSON.stringify(ct.toPlainObject(a), (k, v) => k === "loc" ? undefined : v);
function kucuk(css) {              // → [yeni, null] ya da [null, neden]
  let hata = null;
  const o = { positions: false, parseValue: false, parseAtrulePrelude: false, parseRulePrelude: true, onParseError: e => { hata = hata || e; } };
  const A = ct.parse(css, o);
  if (hata) return [null, "ayrıştırma uyarısı " + String(hata.message || hata).slice(0, 80)];
  const yeni = ct.generate(A);
  const B = ct.parse(yeni, o);
  if (hata) return [null, "yeniden ayrıştırma uyarısı"];
  if (duz(A) !== duz(B)) return [null, "ağaç farkı"];
  if (/<\/style/i.test(yeni)) return [null, "</style içeriyor"];
  if (Buffer.byteLength(yeni) >= Buffer.byteLength(css)) return [null, "küçülmedi"];
  return [yeni, null];
}

const [kok, ...dosyalar] = process.argv.slice(2);
const sonuc = { durum: "tamam", once: 0, sonra: 0, kucultulen: [], ozgun_kalan: [] };
try {
  for (const y of dosyalar) {
    const p = path.join(kok, y);
    if (!fs.existsSync(p)) continue;
    const kod = fs.readFileSync(p, "utf8");
    if (/^css\/[A-Za-z0-9_\-]+\.css$/.test(y)) {
      let yeni = null, neden;
      try { [yeni, neden] = kucuk(kod); } catch (e) { neden = "hata " + String(e && e.message || e).slice(0, 80); }
      sonuc.once += Buffer.byteLength(kod);
      if (!yeni) { sonuc.ozgun_kalan.push({ y, neden }); sonuc.sonra += Buffer.byteLength(kod); continue; }
      fs.writeFileSync(p, yeni); sonuc.sonra += Buffer.byteLength(yeni); sonuc.kucultulen.push(y);
    } else if (y === "index.html") {
      let i = 0, degisti = false;
      const html = kod.replace(/(<style\b[^>]*>)([\s\S]*?)(<\/style>)/gi, (m, a, css, b) => {
        const ad = y + "#" + ((a.match(/id="([^"]+)"/) || [])[1] || "style" + i); i++;
        let yeni = null, neden;
        try { [yeni, neden] = kucuk(css); } catch (e) { neden = "hata " + String(e && e.message || e).slice(0, 80); }
        sonuc.once += Buffer.byteLength(css);
        if (!yeni) { sonuc.ozgun_kalan.push({ y: ad, neden }); sonuc.sonra += Buffer.byteLength(css); return m; }
        sonuc.sonra += Buffer.byteLength(yeni); sonuc.kucultulen.push(ad); degisti = true;
        return a + yeni + b;
      });
      if (degisti) fs.writeFileSync(p, html);
    }
  }
} catch (e) { console.log(JSON.stringify({ durum: "atlandi", neden: "hata " + String(e && e.message || e).slice(0, 120) })); process.exit(0); }
console.log(JSON.stringify(sonuc));
