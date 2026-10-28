#!/usr/bin/env python3
"""🏀😴 Basket dinlenme / arka arkaya maç / deplasman serisi / seyahat düzeltmesi (yol haritası YH-04).

Her maç için iki takımın TAKVİMDEN (sonuç değil, yalnız tarih ve saha) türetilen yorgunluk özellikleri:
  x1 = b2b(dep) − b2b(ev)                arka arkaya maç (önceki maçtan < 36 saat)
  x2 = dinlenme(ev) − dinlenme(dep)      maçsız gün sayısı (0…3; sezon başı / uzun ara = 3)
  x3 = seri(dep) − seri(ev)              üst üste deplasman (dep: bu maça kadar süren deplasman serisi; ev: yeni döndüğü seri), 0…4
  x4 = (yol(dep) − yol(ev)) / 1000 km    önceki maçın sahasından bu sahaya kuş uçuşu (yalnız koordinatı bilinen NBA / WNBA)
Ridge güç modelinin beklenen sayı farkına öğrenilen toplamsal düzeltme eklenir: Δfark = β·x (ev − dep; toplam değişmez).
β lig grubu başına (pro / avrupa / kolej) yalnız GEÇMİŞ tahmin artıklarından (gerçek fark − model farkı) ridge ile öğrenilir;
sabit terim (ev avantajı sapması) öğrenilir ama uygulanmaz (yalnız yorgunluk etkisi).

Bayrak: data/bk_dinlenme.json {"kullan": {grup: bool}, "beta": {grup: [...]}, "izleme": ..., "gecmis": [...]}.
  · kullan[grup] true → basket.py kilitli tahmine ve fikstüre (yd) düzeltmeyi uygular; uygulama (bkPredict) f.yd'yi ekler.
  · false → yalnız gölge: e["ydg"] = Δ kilitli kayda yazılır, ölçülür, uygulanmaz.
  · Üretimde 14 gün izlenir: kabulden sonra kilitlenip sonuçlanan maçlarda düzeltmeli LL − düzeltmesiz LL > +0,002 (n ≥ 30)
    ise bayrak kendiliğinden false olur (gecmis'e yazılır). Kapı kanıtı: lab/bk_dinlenme_lab.py → data/bk_dinlenme_lab.json.
Ağ gerektirmez."""
import json, math, os
from datetime import datetime, timezone, date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
AYAR = os.path.join(DATA, "bk_dinlenme.json")
GRUP = {"nba": "pro", "wnba": "pro", "gl": "pro", "nbl": "pro", "el": "avrupa", "ec": "avrupa", "ncaa": "kolej", "ncaaw": "kolej"}
OZ = ["b2b", "dinlenme", "seri", "yol"]
LAM = 200.0                 # β ön bilgisi 0'a doğru küçültme (maç eşdeğeri)
MIN_N = 300                 # β öğrenmek için en az geçmiş tahmin
IZLE_GUN, IZLE_N, IZLE_ESIK = 14, 30, 0.002

# Salon koordinatları (enlem, boylam) — kamuya açık genel bilgi; yalnız seyahat mesafesi için
KOORD = {
    "Atlanta Hawks": (33.757, -84.396), "Boston Celtics": (42.366, -71.062), "Brooklyn Nets": (40.683, -73.976),
    "Charlotte Hornets": (35.225, -80.839), "Chicago Bulls": (41.881, -87.674), "Cleveland Cavaliers": (41.497, -81.688),
    "Dallas Mavericks": (32.790, -96.810), "Denver Nuggets": (39.749, -105.008), "Detroit Pistons": (42.341, -83.055),
    "Golden State Warriors": (37.768, -122.388), "Houston Rockets": (29.751, -95.362), "Indiana Pacers": (39.764, -86.155),
    "LA Clippers": (33.945, -118.341), "Los Angeles Lakers": (34.043, -118.267), "Memphis Grizzlies": (35.138, -90.051),
    "Miami Heat": (25.781, -80.188), "Milwaukee Bucks": (43.045, -87.917), "Minnesota Timberwolves": (44.979, -93.276),
    "New Orleans Pelicans": (29.949, -90.082), "New York Knicks": (40.751, -73.993), "Oklahoma City Thunder": (35.463, -97.515),
    "Orlando Magic": (28.539, -81.384), "Philadelphia 76ers": (39.901, -75.172), "Phoenix Suns": (33.446, -112.071),
    "Portland Trail Blazers": (45.532, -122.667), "Sacramento Kings": (38.580, -121.500), "San Antonio Spurs": (29.427, -98.437),
    "Toronto Raptors": (43.643, -79.379), "Utah Jazz": (40.768, -111.901), "Washington Wizards": (38.898, -77.021),
    "Atlanta Dream": (33.650, -84.450), "Chicago Sky": (41.870, -87.620), "Connecticut Sun": (41.490, -72.090),
    "Dallas Wings": (32.730, -97.110), "Golden State Valkyries": (37.768, -122.388), "Indiana Fever": (39.764, -86.155),
    "Las Vegas Aces": (36.090, -115.180), "Los Angeles Sparks": (34.043, -118.267), "Minnesota Lynx": (44.979, -93.276),
    "New York Liberty": (40.683, -73.976), "Phoenix Mercury": (33.446, -112.071), "Portland Fire": (45.532, -122.667),
    "Seattle Storm": (47.622, -122.354), "Toronto Tempo": (43.643, -79.379), "Washington Mystics": (38.870, -76.990),
}


def _t(g):
    return datetime.fromisoformat(g["dt"].replace("Z", "+00:00")).timestamp()


def _km(a, b):
    if not a or not b: return 0.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def ozellikler(takvim):
    """takvim: bir ya da birçok ligin maçları (id, lg, dt, h, a, neutral; sonuçsuz fikstür olabilir).
    Dönüş: id → [x1, x2, x3, x4] (ev − dep yönünde; pozitif = ev lehine yorgunluk farkı)."""
    out = {}
    by = {}
    for g in takvim: by.setdefault(g.get("lg"), {})[g["id"]] = g
    for lg, gs in by.items():
        son = {}   # takım → (zaman, saha koordinatı, deplasman serisi, ev mi)
        for g in sorted(gs.values(), key=_t):
            t = _t(g); saha = None if g.get("neutral") else KOORD.get(g["h"])
            f = {}
            for tm, ev in ((g["h"], True), (g["a"], False)):
                s = son.get(tm)
                if s is None or (t - s[0]) > 20 * 86400:        # sezon başı / uzun ara: dinlenmiş, seri sıfır
                    f[tm] = (0, 3, 0, 0.0)
                else:
                    gap = (t - s[0]) / 3600.0
                    b2b = 1 if gap < 36 else 0
                    din = max(0, min(3, int(round(gap / 24.0)) - 1))
                    seri = min(4, s[2])                          # bu maçtan önce üst üste kaç deplasman
                    yol = _km(s[1], saha) if (saha and s[1] and KOORD.get(tm)) else 0.0
                    f[tm] = (b2b, din, seri, yol)
            fh, fa = f[g["h"]], f[g["a"]]
            out[g["id"]] = [float(fa[0] - fh[0]), float(fh[1] - fa[1]), float(fa[2] - fh[2]), (fa[3] - fh[3]) / 1000.0]
            for tm, ev in ((g["h"], True), (g["a"], False)):
                s = son.get(tm); prev = s[2] if (s and (t - s[0]) <= 20 * 86400) else 0
                son[tm] = (t, saha, 0 if ev else prev + 1, ev)
    return out


def beta_fit(X, r, lam=LAM, ozler=None, b0=None):
    """Ridge: r ≈ c + X·β (c cezasız, β ön bilgisi b0; yoksa 0). ozler: kullanılacak sütun indeksleri. Dönüş: tam uzunlukta β.
    Veri MIN_N'den azsa ön bilgi aynen döner."""
    k = len(OZ); b0 = list(b0) if b0 else [0.0] * k
    idx = list(range(k)) if ozler is None else list(ozler)
    if len(r) < MIN_N: return [b0[i] if i in idx else 0.0 for i in range(k)]
    X = np.asarray(X, float); r = np.asarray(r, float)
    Z = np.column_stack([np.ones(len(r)), X[:, idx]])
    P = np.eye(Z.shape[1]) * lam; P[0, 0] = 1e-6
    pr = np.array([0.0] + [b0[i] for i in idx])
    b = np.linalg.solve(Z.T @ Z + P, Z.T @ r + P @ pr)
    out = [0.0] * k
    for j, i in enumerate(idx): out[i] = float(b[j + 1])
    return out


def delta(x, beta):
    if not x or not beta: return 0.0
    return float(sum(a * b for a, b in zip(x, beta)))


# ------------------------------------------------------------------ ayar / izleme
def ayar():
    try: return json.load(open(AYAR, encoding="utf-8"))
    except Exception: return {"kullan": {}, "beta": {}, "gecmis": []}


def kaydet(A):
    tmp = AYAR + ".tmp"
    json.dump(A, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1, allow_nan=False); os.replace(tmp, AYAR)


def ogren(rows_by_lg, takvim, A=None):
    """Üretim β'sı: tam eğitimde basket.py'nin ileri yürüyüş satırlarından (r[0] maç, r[1], r[2] beklenen sayı)."""
    A = A or ayar(); X = ozellikler(takvim); beta = dict(A.get("beta") or {}); nn = {}
    for g in sorted(set(GRUP.values())):
        oz = (A.get("ozler_grup") or {}).get(g) or [0, 1, 2, 3]       # kapıyı geçen varyantın özellikleri; gölgede tam küme
        R = [r for lg, rows in rows_by_lg.items() if GRUP.get(lg) == g for r in rows if r[0]["id"] in X]
        if len(R) < MIN_N: continue
        beta[g] = [round(v, 4) for v in beta_fit([X[r[0]["id"]] for r in R], [(r[0]["hs"] - r[0]["as_"]) - (r[1] - r[2]) for r in R], ozler=oz)]
        nn[g] = len(R)
    A["beta"] = beta; A["beta_n"] = dict(A.get("beta_n") or {}, **nn)
    A["beta_tarih"] = date.today().isoformat()
    return A


def phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def izle(plog, ligler, A=None, bugun=None):
    """14 gün izleme + koruyucu geri alma. Kabulden sonra kilitlenmiş, düzeltmesi uygulanmış (yd) ve sonuçlanmış maçlar."""
    A = A or ayar(); bugun = bugun or date.today(); K = A.setdefault("kullan", {}); I = A.setdefault("izleme", {})
    for g, on in list(K.items()):
        if not on: continue
        kt = (I.get(g) or {}).get("kabul_tarihi")
        if not kt: I[g] = {"kabul_tarihi": bugun.isoformat()}; continue
        E = [e for e in plog if e.get("r") and e.get("yd") is not None and GRUP.get(e["lg"]) == g and e.get("d", "") >= kt and e["r"][0] != e["r"][1]]
        d = []
        for e in E:
            sm = (ligler.get(e["lg"]) or {}).get("sm") or 12.0; y = 1 if e["r"][0] > e["r"][1] else 0
            p1 = min(max(phi((e["ph"] - e["pa"]) / sm), 1e-6), 1 - 1e-6); p0 = min(max(phi((e["ph"] - e["pa"] - e["yd"]) / sm), 1e-6), 1 - 1e-6)
            l = lambda p: -(y * math.log(p) + (1 - y) * math.log(1 - p))
            d.append(l(p1) - l(p0))
        gun = (bugun - date.fromisoformat(kt)).days
        I[g].update({"n": len(d), "d_ll": round(float(np.mean(d)), 5) if d else None, "gun": gun})
        if len(d) >= IZLE_N and float(np.mean(d)) > IZLE_ESIK:
            K[g] = False
            A.setdefault("gecmis", []).append({"tarih": bugun.isoformat(), "grup": g, "olay": "geri_alindi", "n": len(d), "d_ll": round(float(np.mean(d)), 5)})
        elif gun >= IZLE_GUN and not I[g].get("tamam"):
            I[g]["tamam"] = True
            A.setdefault("gecmis", []).append({"tarih": bugun.isoformat(), "grup": g, "olay": "izleme_bitti", "n": len(d), "d_ll": I[g]["d_ll"]})
    return A


def golge_ozet(plog, ligler):
    """Gölgede (uygulanmamış) Δ: sonuçlanmış maçlarda LL farkı (düzeltmeli − düzeltmesiz)."""
    out = {}
    for e in plog:
        if not e.get("r") or e.get("ydg") is None or e["r"][0] == e["r"][1]: continue
        g = GRUP.get(e["lg"]); sm = (ligler.get(e["lg"]) or {}).get("sm") or 12.0; y = 1 if e["r"][0] > e["r"][1] else 0
        m = e["ph"] - e["pa"] - (e.get("yd") or 0.0)
        p0 = min(max(phi(m / sm), 1e-6), 1 - 1e-6); p1 = min(max(phi((m + e["ydg"]) / sm), 1e-6), 1 - 1e-6)
        l = lambda p: -(y * math.log(p) + (1 - y) * math.log(1 - p))
        o = out.setdefault(g, [0, 0.0]); o[0] += 1; o[1] += l(p1) - l(p0)
    return {g: {"n": n, "d_ll": round(s / n, 5)} for g, (n, s) in out.items()}
