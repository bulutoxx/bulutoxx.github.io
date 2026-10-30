#!/usr/bin/env python3
"""YH-16 basket sakatlık gölgesi — ağsız birim sınaması (ayrıştırıcı, takım kaybı, sızıntısız gölge kaydı, kilit değişmezliği)."""
import json, os, sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import bk_sakatlik as BS
import basket as B

ok = 0
def kontrol(k, m):
    global ok
    if not k: print("HATA:", m); sys.exit(1)
    ok += 1

# 1) rapor ayrıştırma (iki id biçimi, ağırlık 0 olanlar atlanır)
R = BS.raporu_ayristir({"injuries": [
    {"displayName": "Boston Celtics", "injuries": [
        {"status": "Out", "athlete": {"id": "11"}},
        {"status": "Day-To-Day", "athlete": {"links": [{"href": "https://x/nba/player/_/id/12/ad"}]}},
        {"status": "Active", "athlete": {"id": "13"}}]},
    {"displayName": "Miami Heat", "injuries": [{"status": "Questionable", "athlete": {"id": "21"}}]}]})
kontrol(R["Boston Celtics"] == [("11", 1.0), ("12", 0.5)], "rapor ayrıştırma")
kontrol(R["Miami Heat"] == [("21", 0.5)], "rapor ayrıştırma 2")

# 2) oyuncu ortalaması: en son sezon GP ≥ 5; az maçlıysa önceki sezon
j = {"categories": [{"name": "averages", "labels": ["GP", "GS", "MIN", "PTS"], "statistics": [
    {"season": {"year": 2026}, "stats": ["30", "30", "34.5", "25.1"]},
    {"season": {"year": 2027}, "stats": ["2", "2", "20.0", "8.0"]}]}]}
kontrol(BS.ortalama_ayristir(j) == (34.5, 25.1, 30.0), "ortalama seçimi")
j2 = {"statistics": {"labels": ["GP", "MIN", "PTS"], "splits": [{"displayName": "Regular Season", "stats": ["9", "28.0", "14.0"]}]}}
kontrol(BS.ortalama_ayristir(j2) == (28.0, 14.0, 9.0), "overview yedeği")
kontrol(BS.ortalama_ayristir({}) is None, "boş yanıt")

# 3) takım kaybı
dk, pt, n, bil = BS.takim_kaybi([("11", 1.0), ("12", 0.5), ("99", 1.0)], {"11": (36.0, 20.0, 30), "12": (24.0, 10.0, 30), "99": None})
kontrol((dk, pt, n, bil) == (0.2, 25.0, 2, 1), f"takım kaybı {dk, pt, n, bil}")

# 4) sinyal tazeliği + maç sinyali (ev lehine pozitif)
simdi = datetime.now(timezone.utc)
A = {"ts": simdi.strftime("%Y-%m-%dT%H:%MZ"), "takim": {"Boston Celtics": {"dk": 0.2, "pt": 25.0}, "Miami Heat": {"dk": 0.05, "pt": 5.0}}}
S = BS.sinyal_hazir(A, simdi)
kontrol(BS.sinyal_hazir(dict(A, ts=(simdi - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%MZ")), simdi) == {}, "bayat sinyal kullanılmaz")
s = BS.mac_sinyali(S, {"lg": "nba", "h": "Miami Heat", "a": "Boston Celtics"})
kontrol(s["x"] == [0.15, 20.0] and s["d"] == 10.0, f"maç sinyali {s}")
kontrol(BS.mac_sinyali(S, {"lg": "ncaa", "h": "Miami Heat", "a": "Boston Celtics"}) is None, "yalnız NBA/WNBA")

# 5) basket.py kilit: yeni kayıtta skg/skg0; başlamış maça yazılmaz; ph/pa değişmez
BS.sinyal_hazir = lambda *a, **k: S
gelecek = (simdi + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%MZ")
gecmis = (simdi - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%MZ")
fx = [{"id": "g1", "lg": "nba", "dt": gelecek, "h": "Miami Heat", "a": "Boston Celtics"},
      {"id": "g2", "lg": "nba", "dt": gecmis, "h": "Miami Heat", "a": "Boston Celtics", "state": "in"}]
plog = [{"id": "g2", "lg": "nba", "d": gecmis[:10], "dt": gecmis, "h": "Miami Heat", "a": "Boston Celtics", "ph": 110.0, "pa": 108.0}]
F = {"nba": object()}
B.pred_means = lambda *a, **k: (112.0, 109.0)
out = B.lock_and_grade(plog, fx, F, {}, {}, date.today(), {})
g1 = next(e for e in out if e["id"] == "g1"); g2 = next(e for e in out if e["id"] == "g2")
kontrol(g1.get("skg") == s and g1.get("skg0") == s, "yeni kayıtta gölge sinyali")
kontrol(g1["ph"] > g1["pa"], "kilit")
kontrol("skg" not in g2 and g2["ph"] == 110.0, "başlamış maça yazılmaz (sızıntı yok)")
# tazeleme: sinyal değişince skg güncellenir, skg0 ve ph/pa sabit
ph0, pa0 = g1["ph"], g1["pa"]
S2 = {"ts": S["ts"], "takim": {"Boston Celtics": {"dk": 0.0, "pt": 0.0}}}
BS.sinyal_hazir = lambda *a, **k: S2
out = B.lock_and_grade(out, fx, F, {}, {}, date.today(), {})
g1 = next(e for e in out if e["id"] == "g1")
kontrol(g1["skg"]["x"] == [0.0, 0.0] and g1["skg0"] == s and (g1["ph"], g1["pa"]) == (ph0, pa0), "tazeleme / kilit değişmez")

# 6) gölge özeti
g1["r"] = [100, 90]; g1["skg"] = s
oz = BS.golge_ozet(out, {"nba": {"sm": 12.0}})
kontrol(oz["nba"]["n"] == 1 and oz["nba"]["sinyalli"] == 1 and oz["nba"]["d_ll_onsel"] < 0, f"gölge özeti {oz}")
print(f"bk_sakatlik_test: {ok}/{ok} geçti")
