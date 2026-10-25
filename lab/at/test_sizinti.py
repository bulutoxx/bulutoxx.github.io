# BULUTOXX at yarışı laboratuvarı — sızıntı testi (elle ya da CI'da çalıştırılır).
# 1) Gün içi sıra testi: seçilen günlerin koşuları ters sırada özelliklendirilse de satırlar birebir aynı olmalı
#    (aynı gün içindeki başka koşunun sonucu özelliğe sızmıyor).
# 2) Aynı (at, gün) testi: bir at aynı gün birden çok satırda görünürse (veri tekrarı), atın geçmişine dayalı
#    sütunlar aynı olmalı.
# 3) Kapalı-sol pencere (kesme) testi: rastgele seçilen D günleri için durum YALNIZ D'den önceki koşulardan
#    yeniden kurulur; D'nin özellikleri tam tablodakiyle aynı olmalı (gelecek veri hiçbir özelliğe girmez).
#   AT_KAYNAK=/yol/tjk-data python lab/at/test_sizinti.py
import os, sys, time
from collections import defaultdict

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import veri, ozellik as O  # noqa: E402

AT_SUTUNLARI = ["yeni", "n_kosu", "skor_son", "skor3", "skor5", "skor10", "galibiyet10", "ilk3_10", "geri_son", "geri3",
                "piyasa_son", "piyasa3", "pz_ewma", "pz_en_iyi5", "piyasa_reyting", "r_at", "r_at_belirsiz",
                "skor_sonum", "geri_en_iyi5", "hz_son", "hz_en_iyi3", "hz_ort3", "hz_trend", "hz_yok", "hp_once", "hp_yok"]


def esit(A, B):
    return np.allclose(A, B, rtol=1e-9, atol=1e-9, equal_nan=True)


def main():
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    adlar = O.TUM_ADLAR
    T, _ = O.tablo_kur(kosular, adlar=adlar)
    hata = []
    # 2) aynı (at, gün)
    grup = defaultdict(list)
    r = 0
    for k in kosular:
        for a in k["atlar"]:
            grup[(k["tarih"], a["ad"])].append(r); r += 1
    sut = [adlar.index(a) for a in AT_SUTUNLARI]
    coklu = [v for v in grup.values() if len(v) > 1]
    bozuk = [v for v in coklu if not all(esit(T["X"][v[0], sut], T["X"][x, sut]) for x in v[1:])]
    print(f"2) aynı (at, gün) çoklu satır grubu: {len(coklu)}, tutarsız {len(bozuk)}", flush=True)
    if bozuk:
        hata.append(f"aynı (at, gün) tutarsız: {len(bozuk)} grup")
    # 3) kapalı-sol kesme testi
    gunler = sorted({k["tarih"] for k in kosular})
    rng = np.random.default_rng(3)
    secim = sorted(rng.choice(gunler[60:], size=3, replace=False))
    for D in secim:
        once = [k for k in kosular if k["tarih"] < D]
        bugun = [k for k in kosular if k["tarih"] == D]
        _, durum = O.tablo_kur(once, adlar=adlar)
        Xd = np.vstack([durum.ozellik(k, adlar) for k in bugun])
        bas = sum(len(k["atlar"]) for k in once)
        Xt = T["X"][bas: bas + len(Xd)]
        ok = esit(Xd, Xt)
        Xr = np.vstack([durum.ozellik(k, adlar) for k in reversed(bugun)])
        Xr = np.vstack(list(reversed(np.split(Xr, np.cumsum([len(k["atlar"]) for k in reversed(bugun)])[:-1]))))
        ok_ters = esit(Xd, Xr)
        print(f"3) kesme testi {D}: {len(Xd)} satır, {'AYNI' if ok else 'FARKLI'}; gün içi ters sıra: "
              f"{'AYNI' if ok_ters else 'FARKLI'}", flush=True)
        if not ok_ters:
            hata.append(f"gün içi sıra bağımlılığı {D}")
        if not ok:
            j = np.where(~np.isclose(Xd, Xt, equal_nan=True))
            hata.append(f"kesme testi {D}: farklı sütunlar {sorted({adlar[c] for c in j[1]})[:8]}")
    print(f"bitti {time.time() - t0:.0f} sn")
    if hata:
        print("SIZINTI ŞÜPHESİ:", *hata, sep="\n- ")
        sys.exit(1)
    print("SIZINTI YOK: tüm testler geçti")


if __name__ == "__main__":
    main()
