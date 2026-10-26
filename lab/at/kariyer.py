# OXXai at yarışı laboratuvarı — AT KARİYERİ (arayüzün At profili kartı).
# Yalnız o günün (ve yarının) programındaki koşucular için, aynanın sonuç arşivinden (data/results) türetilmiş
# KOMPAKT bir özet yazar: data/at/kariyer.json. Ham ayna verisi (memory/horses.json dahil) depoya kopyalanmaz.
# Sızıntı yok: bir atın özeti yalnız koştuğu günden ÖNCEKİ sonuçlardan kurulur. tjk.org / atyarisi.com'a istek YOK.
#
# Biçim (at adı -> özet):
#   n: koşu sayısı · d: [1., 2., 3. sayısı] · son: son 10 derece (en yeni önce; 0 = derece bilgisi yok)
#   pist: {pist: [koşu, birincilik, ilk 3]} · mes: {mesafe grubu: [koşu, birincilik, ilk 3]} · hip: {hipodrom: [koşu, birincilik]}
#   jk: [bugünkü jokeyiyle koşu, birincilik] · ilk / sonT: ilk ve son koşu tarihi · g: hangi günün programı
#
# Kullanım: AT_KAYNAK=<ayna> python3 lab/at/kariyer.py [--gun YYYY-MM-DD]   (varsayılan: İstanbul saatiyle bugün + yarın)
# gece.py her gece kariyer.yaz(kosular, [bugun, yarin]) ile çağırır (sonuçlar zaten yüklü; ek okuma yok).
import argparse, json, os, sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

BURA = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.abspath(os.path.join(BURA, "..", ".."))
sys.path.insert(0, BURA)
os.environ.setdefault("AT_KAYNAK", os.path.join(KOK, "_tjk-data"))
import veri  # noqa: E402

DOSYA = os.path.join(KOK, "data", "at", "kariyer.json")
GRUPLAR = [(1400, "1000–1400"), (1700, "1500–1700"), (2100, "1800–2100"), (99999, "2200+")]


def mesafe_grubu(m):
    try:
        m = int(m or 0)
    except (TypeError, ValueError):
        return None
    if m <= 0:
        return None
    for ust, ad in GRUPLAR:
        if m <= ust:
            return ad
    return None


def _tsi():
    return datetime.now(timezone.utc) + timedelta(hours=3)


def ozet_kur(kosular, gunler, kaynak=None):
    """kosular: veri.sonuclari_yukle çıktısı (zaman sıralı). gunler: program günleri. -> {ad: özet}."""
    kosucular = {}   # ad -> (gün, jokey); aynı at iki gün koşuyorsa ilk gün
    for g in sorted(gunler):
        for k in veri.program_yukle(g, kaynak):
            for a in k["atlar"]:
                if a["ad"] and a["ad"] not in kosucular:
                    kosucular[a["ad"]] = (g, a.get("jokey") or "")
    if not kosucular:
        return {}
    gecmis = defaultdict(list)   # ad -> [(tarih, hipodrom, mesafe, pist, sira, jokey)]
    for k in kosular:
        for a in k["atlar"]:
            ad_ = a["ad"]
            if ad_ in kosucular and k["tarih"] < kosucular[ad_][0]:
                gecmis[ad_].append((k["tarih"], k["hipodrom"], k["mesafe"], k["pist"], a.get("sira"), a.get("jokey") or ""))
    out = {}
    for ad_, (g, jk) in sorted(kosucular.items()):
        L = sorted(gecmis.get(ad_, []), key=lambda x: x[0])
        z = {"g": g, "n": len(L)}
        if not L:
            out[ad_] = z
            continue
        d = [0, 0, 0]
        pist, mes, hip = defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0])
        jn = [0, 0]
        for (t, h, m, p, s, j) in L:
            s = s if isinstance(s, int) and s > 0 else None
            if s and s <= 3:
                d[s - 1] += 1
            w, i3 = int(s == 1), int(bool(s) and s <= 3)
            if p:
                x = pist[p]; x[0] += 1; x[1] += w; x[2] += i3
            mg = mesafe_grubu(m)
            if mg:
                x = mes[mg]; x[0] += 1; x[1] += w; x[2] += i3
            if h:
                x = hip[h]; x[0] += 1; x[1] += w
            if jk and j == jk:
                jn[0] += 1; jn[1] += w
        z.update({"d": d, "son": [x[4] if isinstance(x[4], int) and x[4] > 0 else 0 for x in reversed(L[-10:])],
                  "pist": dict(pist), "mes": {k: mes[k] for _, k in GRUPLAR if k in mes}, "hip": dict(hip),
                  "ilk": L[0][0], "sonT": L[-1][0]})
        if jk:
            z["jk"] = jn
        out[ad_] = z
    return out


def yaz(kosular, gunler, kaynak=None, yol=DOSYA):
    """Özeti yazar; dönen değer: yazılan at sayısı (program yoksa 0, dosyaya dokunmaz)."""
    atlar = ozet_kur(kosular, gunler, kaynak)
    if not atlar:
        return 0
    js = {"surum": 1, "guncelleme_tsi": _tsi().strftime("%Y-%m-%d %H:%M"), "gunler": sorted(gunler),
          "son_sonuc": kosular[-1]["tarih"] if kosular else None,
          "kaynak": "açık TJK sonuç arşivi (github.com/cenkozgur/tjk-data); yalnız türetilmiş özet",
          "aciklama": "n koşu · d [1.,2.,3.] · son: son 10 derece (en yeni önce, 0 = bilinmiyor) · pist/mes: [koşu, 1., ilk 3] · "
                      "hip: [koşu, 1.] · jk: bugünkü jokeyiyle [koşu, 1.] · yalnız günden önceki sonuçlar",
          "atlar": atlar}
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    tmp = yol + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, yol)
    return len(atlar)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gun", default=None, help="YYYY-MM-DD (varsayılan: İstanbul saatiyle bugün; yarın da eklenir)")
    ar = ap.parse_args()
    bugun = ar.gun or _tsi().date().isoformat()
    gunler = [bugun, (date.fromisoformat(bugun) + timedelta(days=1)).isoformat()]
    kosular, _ = veri.sonuclari_yukle()
    n = yaz(kosular, gunler)
    print(f"kariyer: {n} at · günler {gunler} · {DOSYA if n else 'program yok, yazılmadı'}")


if __name__ == "__main__":
    main()
