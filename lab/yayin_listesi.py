#!/usr/bin/env python3
"""📦 Yayın listesi: GitHub Pages'e yalnız uygulamanın gerçekten istediği dosyalar çıkar (denetim P1 #8).

Eskiden deploy işi tüm depoyu (`path: .`) yüklüyordu: lab/, scripts/, data/derin/, robot iç verisi de yayındaydı.
Bu betik listeyi otomatik çıkarır:
  1) Kök uygulama dosyaları: index.html, sw.js, manifest.webmanifest, brain-worker.js, yayin.json (yayın kapısı kaydı).
  2) index.html, sw.js (SHELL), manifest.webmanifest ve brain-worker.js içindeki yol dizeleri: "data/…", "icons/…", "ses/…".
     - Düz yol ("data/ratings.json?t=" → data/ratings.json) olduğu gibi alınır.
     - Klasör önekli dinamik yol ("data/at/canli/"+gün+".json") → o klasördeki *.json (alt klasöre inmez).
     - Şablon (`data/archive/${d}.json`) → data/archive/*.json.
  3) Bilinen dinamik yollar (BILINEN): betikte tarama kaçırsa bile hep eklenir. Her .webp görselin .png yedeği de eklenir.
  4) ses/ klasörü varsa tamamı (alt klasörler dahil).
Robot iç verisi (DISLA) eşleşse bile yayınlanmaz.

Kullanım:
  python3 lab/yayin_listesi.py liste [--json]          → yayınlanacak dosyalar (depo köküne göre)
  python3 lab/yayin_listesi.py kur _site               → listeyi _site/ klasörüne kopyalar (klasör önce temizlenir)
  python3 lab/yayin_listesi.py ozet                    → yayınlanan / yayınlanmayan boyut özeti
Seçenek: --kok DİZİN (varsayılan depo kökü). Yalnız standart kütüphane; ağ isteği yapmaz.

Güvenlik payı: listeden eksik kalan bir dosya uygulamayı kırar. lab/qa.mjs aynı kaynaktan 404 alan her isteği
hata sayar (yayın kapısı reddeder); tarihli dosyalar (ör. data/at/canli/2026-10-28.json) depoda da yoksa 404 normaldir.
"""
import argparse, fnmatch, json, os, re, shutil, sys

KOK0 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = ["index.html", "sw.js", "manifest.webmanifest", "brain-worker.js"]
KOK_DOSYA = ["index.html", "sw.js", "manifest.webmanifest", "brain-worker.js", "yayin.json"]
# Taramanın kaçırabileceği ya da başka bloklarda kurulan dinamik yollar (glob, depo köküne göre).
BILINEN = [
    "data/version.json", "data/ratings.json", "data/fixtures.json", "data/logos.json", "data/season.json",
    "data/basket.json", "data/iddaa.json", "data/daily.json", "data/model.json", "data/qa.json",
    "data/archive/*.json",                 # günlük arşiv (data/archive/<gün>.json)
    "data/oxx_kupon/*.json", "data/oxx_kupon/at/*.json",
    "data/at/*.json",                      # at: dizin, jokeyler, kariyer, karne, model, altili_karne, kupon_karne …
    "data/at/canli/*.json", "data/at/oran_izi/*.json", "data/at/tahmin/*.json", "data/at/altili/*.json",
    "icons/oxxai-og.png",                  # paylaşım önizlemesi (og:image)
]
# Eşleşse bile yayınlanmaz: robot iç verisi / deney / büyük ham tablolar
DISLA = [
    "data/derin/*", "data/bk_games.json", "data/bot_tests.json", "data/deney/*", "data/deney_*", "data/acik/*",
    "data/archive/live/*", "data/archive/live_stats/*", "data/archive/eski/*", "data/archive/*.gz",
    "data/at/deneyler*.json", "data/at/arastirma.json", "data/at/replay.json", "data/at/ek_ozellik/*",
    "data/at/oran_izi_v*.json", "data/saglik/*", "data/qa/*",
]
YOL_RE = re.compile(r"(?<![A-Za-z0-9_\-])(?:\./|/)?((?:data|icons|ses)/[A-Za-z0-9_\-./${}]*)")


def tara(kok):
    """Kaynak dosyalardaki yol dizelerini (düz, klasör öneki, şablon) çıkarır → glob listesi."""
    desen = set()
    for f in KAYNAK:
        p = os.path.join(kok, f)
        if not os.path.isfile(p):
            continue
        metin = open(p, encoding="utf-8", errors="replace").read()
        for m in YOL_RE.finditer(metin):
            y = m.group(1)
            if "${" in y:                                 # `data/archive/${d}.json` → data/archive/*.json
                y = re.sub(r"\$\{[^}]*\}?", "*", y)
                y = y.split("$")[0]
            y = y.rstrip(".")
            parca = y.split("/")
            if y.endswith("/"):
                if len(parca) < 3:                       # "data/", "icons/" gibi kök önekleri (sw.js "/data/") → alma
                    continue
                y += "*.json" if parca[0] == "data" else "*"
            elif "." not in parca[-1]:                    # uzantısız parça (ör. "data/at" kelimesi) → alma
                continue
            desen.add(y)
    return desen


def eslesir(yol, desenler):
    # fnmatch'te * "/" ile de eşleşir; alt klasöre inmemek için parça sayısını da karşılaştır
    for d in desenler:
        if d.count("/") == yol.count("/") and fnmatch.fnmatchcase(yol, d):
            return True
    return False


def liste(kok=KOK0):
    desen = tara(kok) | set(BILINEN)
    sec = set(f for f in KOK_DOSYA if os.path.isfile(os.path.join(kok, f)))
    eksik = []
    for d in sorted(desen):
        if not any(c in d for c in "*?["):
            if os.path.isfile(os.path.join(kok, d)):
                sec.add(d)
            else:
                eksik.append(d)
            continue
        klasor = os.path.join(kok, os.path.dirname(d))
        if os.path.isdir(klasor):
            for f in os.listdir(klasor):
                y = os.path.dirname(d) + "/" + f
                if os.path.isfile(os.path.join(kok, y)) and eslesir(y, [d]):
                    sec.add(y)
    # görsel yedeği: uygulama .webp yüklenemezse aynı adlı .png'ye düşer (src.replace(/\.webp…/, ".png"))
    for y in list(sec):
        if y.endswith(".webp"):
            png = y[:-5] + ".png"
            if os.path.isfile(os.path.join(kok, png)):
                sec.add(png)
    ses = os.path.join(kok, "ses")
    if os.path.isdir(ses):
        for d, _, fs in os.walk(ses):
            for f in fs:
                sec.add(os.path.relpath(os.path.join(d, f), kok).replace(os.sep, "/"))
    sec = sorted(y for y in sec if not eslesir(y, DISLA) and not any(fnmatch.fnmatchcase(y, d) and d.endswith("/*") for d in DISLA))
    return sec, eksik


def boyut(kok, yollar):
    return sum(os.path.getsize(os.path.join(kok, y)) for y in yollar)


def depo_dosyalari(kok):
    out = []
    for d, ds, fs in os.walk(kok):
        ds[:] = [x for x in ds if x not in (".git", ".github", "node_modules", "_site")]
        for f in fs:
            out.append(os.path.relpath(os.path.join(d, f), kok).replace(os.sep, "/"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("komut", choices=["liste", "kur", "ozet"])
    ap.add_argument("hedef", nargs="?")
    ap.add_argument("--kok", default=KOK0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    kok = os.path.abspath(a.kok)
    sec, eksik = liste(kok)
    for y in ("index.html", "sw.js", "manifest.webmanifest"):
        if y not in sec:
            print(f"[yayın listesi] HATA: {y} yok", file=sys.stderr); return 2
    if a.komut == "liste":
        print(json.dumps({"dosyalar": sec, "bulunamayan": eksik}, ensure_ascii=False, indent=1) if a.json else "\n".join(sec))
        return 0
    if a.komut == "ozet":
        tum = depo_dosyalari(kok)
        print(json.dumps({"yayin_dosya": len(sec), "yayin_kb": round(boyut(kok, sec) / 1024),
                          "depo_dosya": len(tum), "depo_kb": round(boyut(kok, tum) / 1024),
                          "bulunamayan": eksik}, ensure_ascii=False, indent=1))
        return 0
    if not a.hedef:
        print("kullanım: yayin_listesi.py kur <hedef_klasor>", file=sys.stderr); return 2
    hedef = os.path.abspath(a.hedef)
    if hedef == kok or kok.startswith(hedef + os.sep):
        print("[yayın listesi] hedef depo kökü olamaz", file=sys.stderr); return 2
    if os.path.isdir(hedef):
        shutil.rmtree(hedef)
    for y in sec:
        h = os.path.join(hedef, y)
        os.makedirs(os.path.dirname(h), exist_ok=True)
        shutil.copy2(os.path.join(kok, y), h)
    print(f"[yayın listesi] {len(sec)} dosya, {round(boyut(kok, sec) / 1024)} KB → {hedef}")
    if eksik:
        print(f"[yayın listesi] kaynakta geçen ama depoda olmayan {len(eksik)} yol (dinamik olabilir): {', '.join(eksik[:12])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
