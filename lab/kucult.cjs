#!/usr/bin/env node
// YH-69: yayın kopyasında js/*.js paketlerinin boşluk / yorum küçültmesi (yalnız yayın kopyası; depo kaynağı okunur kalır).
// Kullanım: OXX_KUCULT=<terser + acorn kurulu (node_modules) klasör> node lab/kucult.cjs <yayın_klasörü> js/a.js js/b.js …
// Güvenlik: yalnız terser compress:false + mangle:false (ad değiştirme yok, sözdizimi dönüştürme yok; boşluk / yorum / ; atılır). Her dosya için özgün ve küçültülmüş
// kodun acorn sözdizimi ağacı konum bilgisi dışında BİREBİR karşılaştırılır; fark, ayrıştırma hatası ya da küçülmeme → özgün kalır.
// Ağ isteği yapmaz; çıktı: JSON özet (stdout son satır).
"use strict";
const fs = require("fs"), path = require("path");
const { createRequire } = require("module");
const dir = process.env.OXX_KUCULT;
if (!dir) { console.log(JSON.stringify({ durum: "atlandi", neden: "OXX_KUCULT yok" })); process.exit(0); }
const req = createRequire(path.join(path.resolve(dir), "package.json"));
let terser, acorn;
try { terser = req("terser"); acorn = req("acorn"); }
catch (e) { console.log(JSON.stringify({ durum: "atlandi", neden: "terser/acorn yüklenemedi" })); process.exit(0); }

let ETIKETLI = true;
const ATLA = new Set(["start", "end", "loc", "range", "raw", "shorthand"]);   // {n} ≡ {n:n}
function esit(a, b, yol) {
  if (a === b) return null;
  if (typeof a !== typeof b) return yol;
  if (a === null || b === null || typeof a !== "object") {
    if (typeof a === "number" && Number.isNaN(a) && Number.isNaN(b)) return null;
    return yol;
  }
  if (a instanceof RegExp || b instanceof RegExp) return String(a) === String(b) ? null : yol;
  if (typeof a === "bigint") return a === b ? null : yol;
  if (Array.isArray(a) !== Array.isArray(b)) return yol;
  if (Array.isArray(a)) {                 // gövde listesindeki boş deyim (";") etkisizdir; terser atar
    const bos = x => x && x.type === "EmptyStatement";
    a = a.filter(x => !bos(x)); b = b.filter(x => !bos(x));
    if (a.length !== b.length) return yol + "[uzunluk]";
  }
  // Hesaplanmamış nesne anahtarı: {"1":…} ≡ {1:…} (anahtar her zaman dizeye çevrilir).
  if ((a.type === "Property" || a.type === "PropertyDefinition" || a.type === "MethodDefinition") && !a.computed && !b.computed &&
      a.key && b.key && a.key.type !== b.key.type && (a.key.type === "Literal" || b.key.type === "Literal")) {
    const ad = x => x.type === "Literal" ? String(x.value) : x.type === "Identifier" ? x.name : null;
    if (ad(a.key) === null || ad(a.key) !== ad(b.key)) return yol + ".key";
    a = Object.assign({}, a, { key: null }); b = Object.assign({}, b, { key: null });
  } else if ((a.type === "Property" || a.type === "PropertyDefinition" || a.type === "MethodDefinition") && !a.computed && !b.computed &&
      a.key && b.key && a.key.type === "Literal" && b.key.type === "Literal") {
    if (String(a.key.value) !== String(b.key.value)) return yol + ".key";
    a = Object.assign({}, a, { key: null }); b = Object.assign({}, b, { key: null });
  }
  const ka = Object.keys(a).filter(k => !ATLA.has(k)), kb = Object.keys(b).filter(k => !ATLA.has(k));
  if (ka.length !== kb.length || kb.some(k => !(k in a))) return yol + "{anahtar}";
  for (const k of ka) {
    // TemplateElement.value.raw String.raw için anlamlı: ayrıca karşılaştırılır.
    const r = esit(a[k], b[k], yol + "." + k);
    if (r) return r;
  }
  // Şablon metni: etiketsiz şablonda yalnız cooked anlamlı; dosyada etiketli şablon (String.raw vb.) varsa raw da birebir istenir.
  if (a.type === "TemplateElement" && ETIKETLI && a.value && b.value && a.value.raw !== b.value.raw) return yol + ".value.raw";
  if (a.type === "Literal" && a.regex && b.regex && (a.regex.pattern !== b.regex.pattern || a.regex.flags !== b.regex.flags)) return yol + ".regex";
  return null;
}
function agac(kod) {
  const o = { ecmaVersion: "latest", allowHashBang: true, allowReturnOutsideFunction: false };
  try { return acorn.parse(kod, Object.assign({ sourceType: "script" }, o)); }
  catch (e) { return acorn.parse(kod, Object.assign({ sourceType: "module" }, o)); }
}

(async () => {
const [kok, ...dosyalar] = process.argv.slice(2);
const sonuc = { durum: "tamam", once: 0, sonra: 0, kucultulen: [], ozgun_kalan: [] };
for (const y of dosyalar) {
  const p = path.join(kok, y);
  if (!/^js\/[A-Za-z0-9_\-]+\.js$/.test(y) || !fs.existsSync(p)) continue;
  const kod = fs.readFileSync(p, "utf8");
  let yeni, neden = null;
  try {
    const r = await terser.minify(kod, { compress: false, mangle: false, module: false, toplevel: false,
      format: { comments: false, ascii_only: false, beautify: false, semicolons: false } });
    yeni = r.code;
    const A0 = agac(kod);
    ETIKETLI = /"type":"TaggedTemplateExpression"/.test(JSON.stringify(A0));
    const d = esit(A0, agac(yeni), "Program");
    if (d) neden = "ağaç farkı " + d.slice(0, 120);
    else if (Buffer.byteLength(yeni) >= Buffer.byteLength(kod)) neden = "küçülmedi";
  } catch (e) { neden = "hata " + String(e && e.message || e).split("\n")[0].slice(0, 120); }
  const a = Buffer.byteLength(kod);
  sonuc.once += a;
  if (neden) { sonuc.ozgun_kalan.push({ y, neden }); sonuc.sonra += a; continue; }
  fs.writeFileSync(p, yeni);
  sonuc.sonra += Buffer.byteLength(yeni);
  sonuc.kucultulen.push(y);
}
console.log(JSON.stringify(sonuc));
})().catch(e => { console.log(JSON.stringify({ durum: "atlandi", neden: "hata " + String(e && e.message || e).slice(0, 120) })); });
