#!/usr/bin/env python3
"""🧪 scripts/kadro.py sahte veri sınaması (ağ yok, anahtar yok). Geçici dizinde çalışır, depo dosyalarına dokunmaz.
Denetlenenler: bütçe tavanı, eşleme, öncelik (Altın aday önce), ilk 11 birikimi → kilit oyuncu, türetilmiş özette oyuncu kimliği/adı
olmaması, API hata gövdesinde durma, predlog_isle'nin yalnız başlamamış maça yazması.
  python3 lab/kadro_test.py"""
import json, os, sys, tempfile
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def main():
    tmp = tempfile.mkdtemp(prefix="kadro_test_")
    os.environ["KADRO_ONBELLEK"] = os.path.join(tmp, "onbellek")
    import kadro as K
    K.CIKTI = os.path.join(tmp, "kadro.json"); K.ARALIK_SN = 0
    an = datetime(2026, 10, 27, 16, 30, tzinfo=timezone.utc)
    gun = an.date().isoformat(); yarin = (an + timedelta(days=1)).date().isoformat()
    # bizim fikstür: biri Altın aday (yüksek güven), biri oransız (kp), biri başka gün
    fx = [{"lg": "en", "d": gun, "t": "18:00", "h": "Arsenal", "a": "Burnley", "odds": [1.2, 7.0, 14.0]},       # Londra 18:00 = 17:00 UTC
          {"lg": "col", "d": gun, "t": "18:45", "h": "Atlético Nacional", "a": "Deportivo Pasto", "kp": [0.5, 0.3, 0.2], "kpy": "guc"},
          {"lg": "es", "d": yarin, "t": "20:00", "h": "Sevilla", "a": "Getafe", "odds": [2.0, 3.2, 4.0]}]
    ts = lambda h, m=0, d=0: int((an.replace(hour=h, minute=m) + timedelta(days=d)).timestamp())
    api_fx = {gun: [{"fixture": {"id": 101, "timestamp": ts(17), "date": f"{gun}T17:00:00+00:00"}, "teams": {"home": {"id": 1, "name": "Arsenal FC"}, "away": {"id": 2, "name": "Burnley"}}},
                    {"fixture": {"id": 102, "timestamp": ts(17, 45), "date": f"{gun}T17:45:00+00:00"}, "teams": {"home": {"id": 3, "name": "Atletico Nacional"}, "away": {"id": 4, "name": "Deportivo Pasto"}}},
                    {"fixture": {"id": 999, "timestamp": ts(12), "date": f"{gun}T12:00:00+00:00"}, "teams": {"home": {"id": 8, "name": "Başka"}, "away": {"id": 9, "name": "Takım"}}}],
              yarin: [{"fixture": {"id": 103, "timestamp": ts(19, 0, 1), "date": f"{yarin}T19:00:00+00:00"}, "teams": {"home": {"id": 5, "name": "Sevilla FC"}, "away": {"id": 6, "name": "Getafe CF"}}}]}
    # takım 1'in geçmişi: oyuncu 10 her maç ilk 11'de (kilit), oyuncu 11 yarısında
    gecmis = []
    for k in range(6):
        gecmis.append({"fixture": {"id": 500 + k, "date": "2026-10-1%d" % k, "status": {"short": "FT"}},
                       "lineups": [{"team": {"id": 1}, "startXI": [{"player": {"id": 10, "name": "Gizli Ad"}}] + ([{"player": {"id": 11}}] if k % 2 else [])},
                                   {"team": {"id": 2}, "startXI": [{"player": {"id": 20}}]}]})
    istekler = []

    class Sahte(K.Istemci):
        def al(self, yol, **prm):
            if self.kalan() <= 0: raise K.Durdur("bütçe")
            self.calisma += 1; self.D["istek_bugun"] += 1; istekler.append((yol, prm))
            if yol == "fixtures" and "date" in prm: return {"response": api_fx.get(prm["date"], [])}
            if yol == "injuries":
                if prm["date"] != gun: return {"response": []}
                return {"response": [{"player": {"id": 10, "name": "Gizli Ad", "type": "Missing Fixture"}, "team": {"id": 1}, "fixture": {"id": 101}},
                                     {"player": {"id": 30, "type": "Questionable"}, "team": {"id": 2}, "fixture": {"id": 101}}]}
            if yol == "fixtures" and "ids" in prm:
                ids = prm["ids"].split("-")
                out = [g for g in gecmis if str(g["fixture"]["id"]) in ids]
                if "102" in ids:
                    out.append({"fixture": {"id": 102, "date": gun, "status": {"short": "NS"}},
                                "lineups": [{"team": {"id": 3}, "startXI": [{"player": {"id": 40}}]}, {"team": {"id": 4}, "startXI": [{"player": {"id": 41}}]}]})
                return {"response": out}
            return {"response": []}

    D = {"gun": gun, "istek_bugun": 0}
    I = Sahte("sahte", D)
    # önce kilit oyuncu birikimi (geçmiş maçlar önbelleğe işlenir)
    OB = {"islenen": {}}
    K.ilk11_isle(OB, gecmis)
    os.makedirs(os.environ["KADRO_ONBELLEK"], exist_ok=True)
    json.dump(OB, open(os.path.join(os.environ["KADRO_ONBELLEK"], "durum.json"), "w"))
    K.calis(istemci=I, fx=fx, an=an)
    C = json.load(open(K.CIKTI))
    hata = []
    ars = C["mac"].get(f"en|{gun}|Arsenal|Burnley")
    if not ars: hata.append("Arsenal maçı özeti yok")
    elif ars["ev"] != [1, 1, round(1.0 * K.KAYIP_KATSAYI, 4)]: hata.append(f"Arsenal ev özeti beklenmedik: {ars['ev']}")
    if ars and ars["dep"][0] != 0: hata.append("Questionable eksik sayılmamalı")
    metin = json.dumps(C, ensure_ascii=False)
    if "Gizli Ad" in metin or '"10"' in metin: hata.append("türetilmiş özette oyuncu adı/kimliği var")
    if istekler[0] != ("fixtures", {"date": gun, "timezone": "UTC"}): hata.append(f"ilk istek eşleme değil: {istekler[0]}")
    if not any(y == "fixtures" and "ids" in p and "102" in p["ids"] for y, p in istekler): hata.append("başlamaya yakın oransız maçın ilk 11'i istenmedi")
    # bütçe tavanı: ikinci çalışmada eşleme ve sakat istekleri tekrarlanmamalı
    n1 = len(istekler); K.calis(istemci=Sahte("sahte", D), fx=fx, an=an + timedelta(minutes=30))
    if len(istekler) - n1 > 1: hata.append(f"ikinci çalışmada gereksiz istek: {istekler[n1:]}")
    obp = os.path.join(os.environ["KADRO_ONBELLEK"], "durum.json"); OBx = json.load(open(obp))
    OBx["butce"]["istek_bugun"] = K.GUNLUK_TAVAN; OBx["sakat"] = {}          # sakat isteği gereksin ama tavan dolu
    json.dump(OBx, open(obp, "w"))
    n2 = len(istekler); K.calis(istemci=Sahte("sahte", D), fx=fx, an=an + timedelta(hours=3))
    if len(istekler) != n2: hata.append("günlük tavan aşıldı")
    # API hata gövdesi: gerçek istemcide durmalı (urlopen yerine sahte yanıt)
    class Y:
        headers = {}
        def __init__(s, b): s.b = b
        def read(s): return s.b
        def __enter__(s): return s
        def __exit__(s, *a): return False
    import urllib.request
    eski = urllib.request.urlopen
    urllib.request.urlopen = lambda req, timeout=0: Y(json.dumps({"errors": {"plan": "Free plans do not have access to this season"}, "response": []}).encode())
    try:
        D2 = {"gun": gun, "istek_bugun": 0}; I2 = K.Istemci("x", D2)
        try: I2.al("fixtures", date=gun); hata.append("hata gövdesinde durmadı")
        except K.Durdur: pass
        if "plan" not in (D2.get("son_hata") or ""): hata.append("son_hata yazılmadı")
    finally:
        urllib.request.urlopen = eski
    # predlog_isle: yalnız başlamamış maç
    plog = [{"id": f"en|{gun}|Arsenal|Burnley", "d": gun, "r": None}, {"id": f"en|{gun}|Arsenal|Burnley", "d": gun, "r": [1, 0]}]
    n = K.predlog_isle(plog, now=an - timedelta(hours=1))
    if n != 1 or len(plog[0].get("kd", [])) != 7: hata.append(f"predlog_isle beklenmedik: {n} {plog[0]}")
    if K.predlog_isle([{"id": f"en|{gun}|Arsenal|Burnley", "d": gun, "r": None}], now=an + timedelta(hours=1)) != 0:
        hata.append("başlamış maça kadro yazıldı")
    print(json.dumps({"istek_sayisi": len(istekler), "istekler": [y + (" " + ",".join(f"{k}={v}" for k, v in p.items())) for y, p in istekler],
                      "ozet": C["mac"], "durum": C["durum"]}, ensure_ascii=False, indent=1))
    if hata:
        print("HATA:", *hata, sep="\n  "); return 1
    print("kadro sınaması: tamam"); return 0


if __name__ == "__main__":
    sys.exit(main())
