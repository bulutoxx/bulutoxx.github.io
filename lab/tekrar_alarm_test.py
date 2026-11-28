#!/usr/bin/env python3
"""YH-102 birim sınaması: lab/adim.py hata_gunleri + lab/kurtarici.py hata_gun_say / adim_kayitlari tekrar alanı."""
import json, os, sys, tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lab"))
import adim, kurtarici as K  # noqa: E402

an = datetime(2026, 11, 28, 10, 0, tzinfo=timezone.utc)
ok = 0; hata = []


def t(ad, kosul):
    global ok
    if kosul: ok += 1
    else: hata.append(ad)


# 1) tekilleşme + bugün eklenir
t("tekil", adim.hata_gunleri(["2026-11-27", "2026-11-27"], None, 1, an) == ["2026-11-27", "2026-11-28"])
# 2) 7 günden eski düşer (sınır 11-22 dahil)
t("eski_duser", adim.hata_gunleri(["2026-11-20", "2026-11-21", "2026-11-22"], None, 0, an) == ["2026-11-22"])
# 3) eski kayıt (hata_gun yok) hata_24s'ten tohumlanır
t("tohum", adim.hata_gunleri(None, ["2026-11-27T11:32:21Z"], 0, an) == ["2026-11-27"])
t("tohum_bos", adim.hata_gunleri([], ["2026-11-27T11:32:21Z"], 0, an) == [])
# 4) kurtarıcı sayacı: hata_gun yoksa hata_24s
t("say_eski", K.hata_gun_say({"hata_24s": ["2026-11-28T01:00:00Z"]}, an) == 1)
t("say_yeni", K.hata_gun_say({"hata_gun": ["2026-11-21", "2026-11-23", "2026-11-25", "2026-11-27"]}, an) == 3)


def kayit(adimlar, run="r9"):
    d = tempfile.mkdtemp()
    json.dump({"run": run, "is_akisi": "x.yml", "adimlar": adimlar}, open(os.path.join(d, "x.json"), "w"))
    eski = K.SAGLIK_DIZIN; K.SAGLIK_DIZIN = d
    try: return K.adim_kayitlari(an)["x.yml"]["x.json"]
    finally: K.SAGLIK_DIZIN = eski


gun3 = ["2026-11-24", "2026-11-26", "2026-11-28"]
# 5) son çalışma başarısız + 3 gün → tekrar; sinif geçici (A ile aynı)
o = kayit({"s": {"rc": 124, "run": "r9", "onem": "bilgi", "hata_24s": ["2026-11-28T03:00:00Z"], "hata_gun": gun3}})
b = o["bilgi_hata"][0]
t("tekrar_var", b["tekrar"] is True and b["sinif"] == "gecici" and b["hata_gun7"] == 3)
# 6) son çalışma başarılı → kayıt yok
o = kayit({"s": {"rc": 0, "run": "r9", "hata_gun": gun3}})
t("basarili_yok", o["basarisiz"] == [] and o["bilgi_hata"] == [])
# 7) 24 saatte kalıcı → tekrar değil (iki listeye birden girmez)
o = kayit({"s": {"rc": 1, "run": "r9", "hata_24s": ["2026-11-28T01:00:00Z", "2026-11-28T02:00:00Z", "2026-11-28T03:00:00Z"], "hata_gun": gun3}})
b = o["basarisiz"][0]
t("kalici_tekrar_degil", b["sinif"] == "kalici" and b["tekrar"] is False)
# 8) 2 gün → tekrar değil; eski kayıt alanı yok → çalışır
o = kayit({"s": {"rc": 1, "run": "r9", "hata_24s": ["2026-11-28T01:00:00Z"]}})
t("eski_kayit", o["basarisiz"][0]["tekrar"] is False and o["basarisiz"][0]["sinif"] == "gecici")
# 9) sinif kararı A ile birebir: alanlar dışında aynı
o = kayit({"s": {"rc": 1, "run": "r9", "hata_24s": ["2026-11-28T01:00:00Z"], "hata_gun": gun3}})
t("sinif_ayni", o["basarisiz"][0]["sinif"] == "gecici")

print(f"{ok} / {ok + len(hata)} geçti" + (f"; kalan: {hata}" if hata else ""))
sys.exit(1 if hata else 0)
