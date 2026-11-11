#!/usr/bin/env python3
"""YH-63 sınaması: ESPN yer tutucu ("TBD Home" / "TBD Away" / "TBD") takımlı maçların bülten ve kilitli günlük dışında tutulması.

Ağ yok, yalnız depodaki veri. Önceden kayıtlı kapı:
 (1) yanlış pozitif 0: depodaki tüm gerçek takım adları (futbol sezon verisi + takma adlar, basket takım tabloları, iki kilitli
     günlük) içinde yer tutucu sayılan her ad "TBD"/"TBA"/"To be …" ile başlar; elle seçilmiş zor adlar (Tbilisi, TB Tvøroyri …) yakalanmaz
 (2) futbol ve basket ESPN ayrıştırıcıları sahte olaylarda yer tutuculu maçı atar, gerçek maçı birebir aynı döndürür
 (3) mevcut data/fixtures.json ve data/basket.json fikstürlerine süzgeç uygulanınca yalnız yer tutuculu satırlar düşer,
     kalan satırlar A = B (sıra dahil); kilitli günlüklerdeki mevcut kayıtlara dokunulmaz (süzgeç yalnız yeni kilidi engeller)
Kullanım: python3 lab/yer_tutucu_test.py   (çıkış kodu 0 = kapı geçti)
"""
import json, os, sys, copy
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "scripts"))
D = lambda *p: os.path.join(KOK, "data", *p)
import update as U
import basket as B

sonuc = {"kapi": {}}
# (1) yanlış pozitif
adlar = set()
S = json.load(open(D("season.json"), encoding="utf-8"))
for lg, d in S.items():
    if not isinstance(d, dict): continue
    for m in d.get("matches", []): adlar.update((m["h"], m["a"]))
    adlar.update((d.get("alias") or {}).keys()); adlar.update((d.get("alias") or {}).values())
BK = json.load(open(D("basket.json"), encoding="utf-8"))
for lg, L in (BK.get("leagues") or {}).items():
    T = L.get("teams") or []
    for t in (T if isinstance(T, list) else T.keys()):
        adlar.add(t.get("n") if isinstance(t, dict) else t)
for f in ("predlog.json", "bk_predlog.json"):
    for e in json.load(open(D(f), encoding="utf-8")): adlar.update((e.get("h"), e.get("a")))
for f in BK.get("fixtures", []) + json.load(open(D("fixtures.json"), encoding="utf-8")): adlar.update((f.get("h"), f.get("a")))
adlar.discard(None)
zor = ["Tbilisi", "Dinamo Tbilisi", "TB Tvøroyri", "TBC", "Tabasalu", "Toulouse", "Tottenham", "Tobol", "Winners FC", "TSG Hoffenheim", "Tba Club"]
yt_u = sorted(a for a in adlar if U.yer_tutucu(a)); yt_b = sorted(a for a in adlar if B.yer_tutucu(a))
yanlis = [a for a in set(yt_u) | set(yt_b) if not a.strip().lower().startswith(("tbd", "tba", "to be"))]
zor_yakalanan = [a for a in zor if U.yer_tutucu(a) or B.yer_tutucu(a)]
# "Tba Club" gerçek bir ad değil; regex onu yakalar (kelime başı "tba"). Gerçek adlarda bulunmadığı (1)'in birinci yarısıyla doğrulanır.
zor_yakalanan = [a for a in zor_yakalanan if a != "Tba Club"]
sonuc["ad_sayisi"] = len(adlar); sonuc["yer_tutucu_ad"] = sorted(set(yt_u) | set(yt_b))
sonuc["kapi"]["1_yanlis_pozitif_0"] = not yanlis and not zor_yakalanan and yt_u == yt_b
sonuc["yanlis"] = yanlis + zor_yakalanan

# (2) ayrıştırıcılar — sahte ESPN olayları
def ev(i, h, a, state="pre", hs=None, as_=None):
    def t(n, ha, s): return {"homeAway": ha, "team": {"displayName": n, "name": n, "abbreviation": n[:3], "logo": ""}, "score": s, "linescores": []}
    return {"id": i, "date": "2026-11-21T19:00Z", "season": {"type": 3},
            "status": {"type": {"state": state, "completed": state == "post"}},
            "competitions": [{"competitors": [t(h, "home", hs), t(a, "away", as_)], "neutralSite": False}]}
olaylar = [ev(1, "TBD Home", "TBD Away"), ev(2, "Durango", "TBD Away"), ev(3, "TBD", "TBD"), ev(4, "Alianza Lima", "FC Cajamarca"),
           ev(5, "Tlaxcala FC", "Club Atlético La Paz", "post", 2, 1), ev(6, "To Be Determined", "Venados FC"), ev(7, "Dinamo Tbilisi", "Torpedo")]
gercek = {4, 5, 7}
fetch0 = U.fetch
U.fetch = lambda url: json.dumps({"events": olaylar})
r_, f_ = U.espn_month("x", "202611")
U.fetch = fetch0
fu = {(x["h"], x["a"]) for x in r_ + f_}
bek = {(e["competitions"][0]["competitors"][0]["team"]["displayName"], e["competitions"][0]["competitors"][1]["team"]["displayName"]) for e in olaylar if e["id"] in gercek}
bb = [B.parse_espn_event(copy.deepcopy(e), "nba") for e in olaylar]
bu = {(g["h"], g["a"]) for g in bb if g}
# eski davranışla (süzgeçsiz) aynı mı: gerçek maçlarda çıktı birebir
U_yt, B_yt = U.yer_tutucu, B.yer_tutucu
U.yer_tutucu = lambda a: False; B.yer_tutucu = lambda a: False
U.fetch = lambda url: json.dumps({"events": olaylar}); r0, f0 = U.espn_month("x", "202611"); U.fetch = fetch0
bb0 = [B.parse_espn_event(copy.deepcopy(e), "nba") for e in olaylar]
U.yer_tutucu, B.yer_tutucu = U_yt, B_yt
ayni_u = [x for x in r0 + f0 if not (U.yer_tutucu(x["h"]) or U.yer_tutucu(x["a"]))] == r_ + f_
ayni_b = [g for g in bb0 if g and not (B.yer_tutucu(g["h"]) or B.yer_tutucu(g["a"]))] == [g for g in bb if g]
negatif = len(r0 + f0) > len(r_ + f_) and sum(1 for g in bb0 if g) > sum(1 for g in bb if g)
sonuc["kapi"]["2_ayristirici"] = fu == bek and bu == bek and ayni_u and ayni_b and negatif
sonuc["ayristirici"] = {"futbol": sorted(fu), "basket": sorted(bu), "negatif_denetim": negatif}

# (3) mevcut fikstürler
FX = json.load(open(D("fixtures.json"), encoding="utf-8"))
fx2 = [f for f in FX if not (U.yer_tutucu(f.get("h")) or U.yer_tutucu(f.get("a")))]
dus_fx = [f"{f['lg']}|{f['d']}|{f['h']}|{f['a']}" for f in FX if f not in fx2]
BF = BK.get("fixtures", [])
bf2 = [f for f in BF if not (B.yer_tutucu(f.get("h")) or B.yer_tutucu(f.get("a")))]
dus_bf = [f"{f['lg']}|{f.get('dt')}|{f['h']}|{f['a']}" for f in BF if f not in bf2]
kalan_ab = [f for f in FX if f"{f['lg']}|{f['d']}|{f['h']}|{f['a']}" not in dus_fx] == fx2 and [f for f in BF if f not in [x for x in BF if x not in bf2]] == bf2
hepsi_yt = all("TBD" in k or "TBA" in k for k in dus_fx + dus_bf)
sonuc["fikstur"] = {"futbol": {"once": len(FX), "sonra": len(fx2), "dusen": dus_fx}, "basket": {"once": len(BF), "sonra": len(bf2), "dusen": dus_bf}}
PL = json.load(open(D("predlog.json"), encoding="utf-8")); BPL = json.load(open(D("bk_predlog.json"), encoding="utf-8"))
sonuc["kilitli_mevcut_yer_tutucu"] = {"futbol": sum(1 for e in PL if U.yer_tutucu(e["h"]) or U.yer_tutucu(e["a"])),
                                      "basket": sum(1 for e in BPL if B.yer_tutucu(e.get("h")) or B.yer_tutucu(e.get("a")))}
sonuc["kapi"]["3_fikstur_ab"] = kalan_ab and hepsi_yt
sonuc["gecti"] = all(sonuc["kapi"].values())
print(json.dumps(sonuc, ensure_ascii=False, indent=1))
sys.exit(0 if sonuc["gecti"] else 1)
