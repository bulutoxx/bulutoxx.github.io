#!/usr/bin/env python3
"""🧪 scripts/tazeveri.py + lab/tazeveri_kapi.py sahte veri sınaması (ağ yok). Geçici dizinde çalışır, depo dosyalarına dokunmaz.
Denetlenen: kadro kayması yönü, açılış oranının korunması / son oranın tazelenmesi, başlamış maçın donması, sonuç işleme,
kapalıyken fixtures çıktısının değişmemesi, aktifken yalnız kopyaya kp/ko/tz yazılması, kapının veri azken kapalı kalması.
  python3 lab/tazeveri_test.py"""
import json, os, sys, tempfile
from datetime import datetime, timedelta, timezone

LAB = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(LAB)
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(ROOT, "scripts"))


def main():
    tmp = tempfile.mkdtemp(prefix="taze_test_")
    import tazeveri as T
    T.GOLGE = os.path.join(tmp, "tazeveri.json"); T.AYAR = os.path.join(tmp, "ayar.json"); T.KADRO = os.path.join(tmp, "kadro.json")
    T.DATA = tmp
    hata = []
    an = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc); bt = an.timestamp() + 5 * 3600
    gun = "2026-10-27"
    f = {"lg": "en", "d": gun, "t": "17:00", "h": "A", "a": "B", "odds": [2.0, 3.4, 3.9], "ou": [1.9, 1.9],
         "pz": {"1": .48, "X": .27, "2": .25, "U25": .5}}
    ko = lambda x: bt
    json.dump({"mac": {f"en|{gun}|A|B": {"ev": [3, 2, 0.08], "dep": [1, 0, 0.0], "ilk11": 1, "t": "x", "bt": int(bt)}}}, open(T.KADRO, "w"))
    G = {}
    T.golge_guncelle([f], ko, model={f"en|{gun}|A|B": ([.5, .25, .25], .55)}, now=an, A={}, G=G, yaz=False)
    e = G["mac"][f"en|{gun}|A|B"]
    if e["g"]["kadro_1x2"][0] >= e["b"][0]: hata.append(f"ev kilit eksik → ev olasılığı düşmeli: {e['g']['kadro_1x2']} vs {e['b']}")
    if len(e.get("kd", [])) != 7: hata.append(f"kd eksik: {e.get('kd')}")
    f2 = dict(f, odds=[1.8, 3.5, 4.4])
    T.golge_guncelle([f2], ko, now=an + timedelta(hours=2), A={}, G=G, yaz=False)
    if e["o0"] != [2.0, 3.4, 3.9] or e["o1"] != [1.8, 3.5, 4.4]: hata.append(f"açılış/son oran yanlış: {e['o0']} {e['o1']}")
    if e["g"]["hareket_1x2"][0] <= e["b"][0]: hata.append("ev lehine oran hareketi ev olasılığını artırmalı (b>0)")
    T.golge_guncelle([dict(f, odds=[1.5, 4, 6])], ko, now=an + timedelta(hours=6), A={}, G=G, yaz=False)
    if e["o1"] != [1.8, 3.5, 4.4]: hata.append("başlamış maç güncellendi")
    n = T.sonuc_isle(G, {"en": [{"d": gun, "h": "A", "a": "B", "ft": [2, 1]}]}, arsiv_dizin=tmp, now=an + timedelta(hours=9), yaz=False)
    if n != 1 or e.get("r") != [2, 1]: hata.append(f"sonuç işlenmedi: {n} {e.get('r')}")
    out, nz = T.cikti_uygula([f], {}, G)
    if nz or out[0] is not f: hata.append("kapalıyken çıktı değişti")
    A = {"adaylar": {"kadro_1x2": {"durum": "aktif"}}}
    out, nz = T.cikti_uygula([f], A, G)
    if nz != 1 or out[0].get("tz") != ["kadro_1x2"] or "kp" in f: hata.append(f"aktifken çıktı yanlış: {nz} {out[0].get('tz')} {'kp' in f}")
    import tazeveri_kapi as K
    K.GELISIM = os.path.join(tmp, "gelisim.json")
    A2 = K.karar_ver(A={"v": 1}, G=G, kuru=True, guardian=False, O=None)
    if any(v.get("durum") in ("aktif", "kalici") for v in A2["adaylar"].values()): hata.append("tek satırla kapı açıldı")
    if hata:
        print("TAZE VERİ SINAMASI BAŞARISIZ:\n  " + "\n  ".join(hata)); return 1
    print("taze veri sınaması: tamam"); return 0


if __name__ == "__main__":
    sys.exit(main())
