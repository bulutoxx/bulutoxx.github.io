# BULUTOXX at yarışı — hazırlık keşif robotu (yalnız okur, hiçbir şey yayınlamaz).
# TJK sayfalarını nazikçe (istekler arası 1,5 sn) dolaşır; robots.txt'e uyar; hangi verinin nerede, hangi biçimde
# bulunduğunu ve kullanım koşullarını raporlar. Ham sayfalar yalnız iş akışı eki (artifact) olarak 7 gün saklanır.
import json, re, time, urllib.request, urllib.robotparser, html, os, sys
from urllib.parse import urljoin, urlparse
UA = "Mozilla/5.0 (compatible; BULUTOXX-kesif/0.1; hobi amacli veri kesfi)"
OUT = "kesif_out"; os.makedirs(OUT, exist_ok=True)
rep = {"robots": {}, "sayfalar": [], "baglantilar": {}, "kosullar": []}
rps = {}
def allowed(u):
    h = urlparse(u).scheme + "://" + urlparse(u).netloc
    if h not in rps:
        rp = urllib.robotparser.RobotFileParser(); rp.set_url(h + "/robots.txt")
        try:
            txt = get(h + "/robots.txt", check=False)[1]
            rep["robots"][h] = txt[:4000]; rp.parse(txt.splitlines())
        except Exception as e:
            rep["robots"][h] = "alinamadi: %s" % e; rp = None
        rps[h] = rp
    return rps[h] is None or rps[h].can_fetch(UA, u)
def get(u, check=True):
    if check and not allowed(u): return (None, "robots.txt izin vermiyor", {})
    time.sleep(1.5)
    r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "tr-TR,tr"}), timeout=30)
    b = r.read(3_000_000)
    return (r.status, b.decode(r.headers.get_content_charset() or "utf-8", "replace"), dict(r.headers))
def save(name, txt): open(os.path.join(OUT, name), "w", encoding="utf-8").write(txt)
KEY = re.compile(r"program|sonuc|agf|idman|galop|istatistik|kullan|yasal|gizlilik|kvkk|csv|xls|pdf|sorgu|at-?bilgi|jokey|antren|yabanc|handikap|hipodrom|derece|pedigri|kosmaz|degisiklik|bulten", re.I)
def probe(name, u):
    t0 = time.time()
    try:
        st, txt, hd = get(u)
        title = re.search(r"<title[^>]*>(.*?)</title>", txt or "", re.S | re.I)
        links = sorted({urljoin(u, html.unescape(m)) for m in re.findall(r'href=["\']([^"\'#]+)', txt or "")})
        kl = [l for l in links if KEY.search(l)]
        tables = len(re.findall(r"<table", txt or "", re.I))
        rep["sayfalar"].append({"ad": name, "url": u, "durum": st, "boyut": len(txt or ""), "baslik": (title.group(1).strip()[:150] if title else None),
                                "tablo": tables, "tur": hd.get("Content-Type"), "sure": round(time.time() - t0, 2), "anahtar_baglanti": kl[:120]})
        if txt: save(re.sub(r"\W+", "_", name) + ".html", txt[:600000])
        for l in kl: rep["baglantilar"][l] = rep["baglantilar"].get(l, 0) + 1
        return txt
    except Exception as e:
        rep["sayfalar"].append({"ad": name, "url": u, "hata": str(e)[:300]}); return None
T = sys.argv[1] if len(sys.argv) > 1 else "25/10/2026"
B = "https://www.tjk.org"
probe("anasayfa", B + "/")
for n, p in [("gunluk_program", "/TR/YarisSever/Info/Page/GunlukYarisProgrami"),
             ("gunluk_sonuc", "/TR/YarisSever/Info/Page/GunlukYarisSonuclari"),
             ("program_tarihli", "/TR/YarisSever/Info/Page/GunlukYarisProgrami?QueryParameter_Tarih=" + T),
             ("sonuc_tarihli", "/TR/YarisSever/Info/Page/GunlukYarisSonuclari?QueryParameter_Tarih=" + T),
             ("agf", "/TR/YarisSever/Info/Page/AGF"),
             ("idman", "/TR/YarisSever/Info/Page/IdmanBilgileri"),
             ("galop", "/TR/YarisSever/Info/Page/GalopBilgileri"),
             ("yillik_program", "/TR/YarisSever/Query/Page/YillikYarisProgrami"),
             ("at_sorgu", "/TR/YarisSever/Query/Page/Atlar"),
             ("istatistik", "/TR/YarisSever/Query/Page/Istatistikler")]:
    probe(n, B + p)
# Ana sayfa ve program sayfasında bulunan, kullanım koşulu / yasal içerikli bağlantılar
for l in list(rep["baglantilar"]):
    if re.search(r"kullan|yasal|gizlilik|kvkk|telif|sartlar|kosullar", l, re.I) and urlparse(l).netloc.endswith("tjk.org"):
        txt = probe("kosul:" + l[-60:], l)
        if txt:
            body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", txt, flags=re.S | re.I)
            body = re.sub(r"<[^>]+>", " ", body); body = re.sub(r"\s+", " ", html.unescape(body))
            for m in re.finditer(r"[^.]{0,250}(kopyal|çoğalt|izinsiz|ticari|otomatik|robot|veri|telif|fikri)[^.]{0,250}\.", body, re.I):
                rep["kosullar"].append({"url": l, "cumle": m.group(0).strip()[:500]})
# indirilebilir dosya (csv/xls/pdf) bağlantıları
rep["dosya_baglantilari"] = sorted(l for l in rep["baglantilar"] if re.search(r"\.(csv|xls|xlsx|pdf|json|xml)(\?|$)", l, re.I))[:200]
json.dump(rep, open(os.path.join(OUT, "kesif.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"sayfa": len(rep["sayfalar"]), "basarili": sum(1 for s in rep["sayfalar"] if s.get("durum") == 200),
                  "dosya": len(rep["dosya_baglantilari"]), "kosul_cumlesi": len(rep["kosullar"])}, ensure_ascii=False))
