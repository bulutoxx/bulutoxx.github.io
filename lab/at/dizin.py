# BULUTOXX at yarışı laboratuvarı — ARAMA DİZİNİ (arayüzün 🔍 arama ekranı ve OXX "X bugün koşuyor mu?" cevapları).
# Aynanın sonuç arşivinden (data/results) türetilmiş KOMPAKT bir dizin yazar: data/at/dizin.json.
# Ham ayna verisi depoya kopyalanmaz; yalnız ad + birkaç sayı. tjk.org / atyarisi.com'a istek YOK.
#
# Biçim (dizi satırları, boyut için):
#   gun0: tarih tabanı (YYYY-MM-DD); tüm "g" alanları gun0'dan beri gün sayısıdır
#   hip:  hipodrom adları · jk: jokey adları · an: antrenör adları (satırlar bu dizilere indeksle bağlanır)
#   atlar: [ad, son koşu g, koşu sayısı (arşivdeki tüm koşuları), son derece (0 = bilinmiyor), son hipodrom i, son antrenör i, son jokey i]
#          yalnız son PENCERE günde (varsayılan 365) koşmuş atlar
#   jokeyler / antrenorler: [ad i, son koşu g, 90 gün koşu, 90 gün birincilik, 90 gün ilk 3, son hipodrom i, pencere koşu sayısı]
#
# Kullanım: AT_KAYNAK=<ayna> python3 lab/at/dizin.py   ·   gece.py her gece dizin.yaz(kosular) ile çağırır (sonuçlar zaten yüklü).
import argparse, json, os, sys
from datetime import date, datetime, timedelta, timezone

BURA = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.abspath(os.path.join(BURA, "..", ".."))
sys.path.insert(0, BURA)
os.environ.setdefault("AT_KAYNAK", os.path.join(KOK, "_tjk-data"))
import veri  # noqa: E402

DOSYA = os.path.join(KOK, "data", "at", "dizin.json")
PENCERE = 365
OZET_GUN = 90
SINIR = 420 * 1024   # bayt; aşılırsa pencere daraltılır


def _tsi():
    return datetime.now(timezone.utc) + timedelta(hours=3)


def kur(kosular, pencere=PENCERE):
    if not kosular:
        return None
    son = kosular[-1]["tarih"]
    son_d = date.fromisoformat(son)
    alt = (son_d - timedelta(days=pencere)).isoformat()
    alt90 = (son_d - timedelta(days=OZET_GUN)).isoformat()
    gun0 = date.fromisoformat(alt)
    g = lambda t: (date.fromisoformat(t) - gun0).days

    sayi = {}      # at -> tüm arşivdeki koşu sayısı
    at_son = {}    # at -> (tarih, sira, hipodrom, antrenor, jokey) son koşu (pencere içinde)
    kisi = {"jokey": {}, "antrenor": {}}   # ad -> [son tarih, n90, w90, i3_90, son hip, n_pencere]
    for k in kosular:
        t = k["tarih"]
        for a in k["atlar"]:
            ad = a["ad"]
            if not ad:
                continue
            sayi[ad] = sayi.get(ad, 0) + 1
            if t < alt:
                continue
            s = a.get("sira") if isinstance(a.get("sira"), int) and a.get("sira") > 0 else 0
            at_son[ad] = (t, s, k["hipodrom"], a.get("antrenor") or "", a.get("jokey") or "")
            for tur in ("jokey", "antrenor"):
                kad = a.get(tur) or ""
                if not kad:
                    continue
                z = kisi[tur].setdefault(kad, [t, 0, 0, 0, k["hipodrom"], 0])
                z[0], z[4] = t, k["hipodrom"]
                z[5] += 1
                if t >= alt90:
                    z[1] += 1
                    z[2] += int(s == 1)
                    z[3] += int(0 < s <= 3)
    hip = sorted({v[2] for v in at_son.values()} | {z[4] for tur in kisi for z in kisi[tur].values()})
    hi = {h: i for i, h in enumerate(hip)}
    # sıra: son 90 günde çok koşan önce (arayüzde eşit eşleşmede öne çıkar)
    jk = sorted(kisi["jokey"], key=lambda x: (-kisi["jokey"][x][1], -kisi["jokey"][x][5], x))
    an = sorted(kisi["antrenor"], key=lambda x: (-kisi["antrenor"][x][1], -kisi["antrenor"][x][5], x))
    ji, ai = {x: i for i, x in enumerate(jk)}, {x: i for i, x in enumerate(an)}
    atlar = []
    for ad, (t, s, h, ant, jok) in sorted(at_son.items(), key=lambda x: (x[1][0], x[0]), reverse=True):
        atlar.append([ad, g(t), sayi.get(ad, 0), s, hi.get(h, -1), ai.get(ant, -1), ji.get(jok, -1)])
    kis = lambda tur, L, idx: [[idx[x], g(kisi[tur][x][0])] + kisi[tur][x][1:4] + [hi.get(kisi[tur][x][4], -1), kisi[tur][x][5]] for x in L]
    return {"surum": 1, "guncelleme_tsi": _tsi().strftime("%Y-%m-%d %H:%M"), "son_sonuc": son, "gun0": gun0.isoformat(),
            "pencere_gun": pencere, "ozet_gun": OZET_GUN,
            "kaynak": "açık TJK sonuç arşivi (github.com/cenkozgur/tjk-data); yalnız türetilmiş dizin",
            "aciklama": "g: gun0'dan beri gün · atlar [ad, son koşu g, koşu sayısı, son derece (0 = bilinmiyor), hip i, antrenör i, jokey i] · "
                        "jokeyler/antrenorler [ad i, son koşu g, 90g koşu, 90g 1., 90g ilk 3, hip i, pencere koşu]",
            "hip": hip, "jk": jk, "an": an, "atlar": atlar,
            "jokeyler": kis("jokey", jk, ji), "antrenorler": kis("antrenor", an, ai)}


def yaz(kosular, yol=DOSYA):
    """Dizini yazar; dönen değer (at sayısı, bayt). Sonuç yoksa dosyaya dokunmaz."""
    pencere = PENCERE
    while True:
        js = kur(kosular, pencere)
        if not js:
            return 0, 0
        metin = json.dumps(js, ensure_ascii=False, separators=(",", ":"))
        b = len(metin.encode("utf-8"))
        if b <= SINIR or pencere <= 120:
            break
        pencere -= 45
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    tmp = yol + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(metin)
    os.replace(tmp, yol)
    return len(js["atlar"]), b


def main():
    argparse.ArgumentParser(description="data/at/dizin.json üretir").parse_args()
    kosular, _ = veri.sonuclari_yukle()
    n, b = yaz(kosular)
    print(f"dizin: {n} at · {b / 1024:.0f} KB · {DOSYA if n else 'sonuç yok, yazılmadı'}")


if __name__ == "__main__":
    main()
