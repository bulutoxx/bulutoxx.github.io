"""⚖️ YH-23 · Marj ayırma yöntemleri laboratuvarı (gölge ölçüm; hiçbir tahmini değiştirmez).

Soru: uygulamanın sunduğu piyasa olasılığında (js/core.js implied(), update.py power_devig) power yerine Shin,
odds-ratio (Cheung 2015), oransal ya da toplamsal marj ayırma daha iyi kalibre olasılık verir mi?
Veri (aynı yöntemle iki arşiv, zaman sıralı):
  - "derin": data/derin/*.json (football-data, 2021→) + data/season.json (süren sezon; aynı maç bir kez) — düşük marj (~%7).
  - "iddaa": kilitli öneri arşivi (scripts/arsiv.py; kilit anındaki iddaa oranı + sonuç) — yüksek marj (~%18), uygulamanın gerçekten gösterdiği oran.
1X2 ve 2,5 alt/üst ayrı. Yöntemler parametresiz (öğrenme yok) → sızıntı yok; zaman sırası yalnız yarı ayrımı ve izleme için.
Kapı (SK): ΔLL = LL(aday) − LL(power); lig×gün blok bootstrap (B=2000) %95 GA üst < 0 · iki zaman yarısında ΔLL < 0 · ΔBrier ≤ 0.
Bir yöntem iddaa arşivinde hem 1X2 hem A/Ü'de geçerse "aday" yazılır; üretime geçiş elle (Python + JS tek fonksiyon, bayrak).
Çıktı: data/marj_lab.json (yalnız toplu metrik). Kullanım: python3 lab/marj_lab.py
"""
import glob, json, os, sys
from datetime import date
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import arsiv  # noqa: E402

CIKTI = os.path.join(DATA, "marj_lab.json")
B = 2000
URETIM = "power"


def power(q):
    lo, hi = 1.0, 3.0
    for _ in range(40):
        k = (lo + hi) / 2
        if (q ** k).sum() > 1: lo = k
        else: hi = k
    p = q ** k; return p / p.sum()


def prop(q): return q / q.sum()


def shin(q):
    """Shin (1993): p_i = (√(z² + 4(1−z) q_i²/S) − z) / (2(1−z)), Σp = 1 olacak z (update.py devig 'shin' ile aynı)."""
    S = q.sum(); lo, hi = 0.0, 0.4
    for _ in range(50):
        z = (lo + hi) / 2; p = (np.sqrt(z * z + 4 * (1 - z) * q * q / S) - z) / (2 * (1 - z))
        if p.sum() > 1: lo = z
        else: hi = z
    return p / p.sum()


def odds_ratio(q):
    """Cheung (2015): p/(1−p) = (q/(1−q)) / c, Σp = 1 olacak c."""
    lo, hi = 1.0, 5.0
    for _ in range(50):
        c = (lo + hi) / 2; p = q / (c + q - c * q)
        if p.sum() > 1: lo = c
        else: hi = c
    return p / p.sum()


def additive(q):
    p = np.clip(q - (q.sum() - 1) / len(q), 1e-4, None); return p / p.sum()


YONTEM = {"power": power, "shin": shin, "odds_ratio": odds_ratio, "prop": prop, "additive": additive}


def _sonuc(hg, ag): return 0 if hg > ag else 1 if hg == ag else 2


def yukle_derin():
    X1, X2, gor = [], [], set()
    for f in sorted(glob.glob(os.path.join(DATA, "derin", "*-20*.json"))):
        D = json.load(open(f, encoding="utf-8")); lg = D["lg"]
        for d, h, a, hg, ag, o1, ox, o2, ou, ol in D["m"]:
            if hg is None or ag is None: continue
            gor.add((d, lg, h, a))
            if o1 and ox and o2 and min(o1, ox, o2) > 1: X1.append((d, lg, [o1, ox, o2], _sonuc(hg, ag)))
            if ou and ol and min(ou, ol) > 1: X2.append((d, lg, [ou, ol], 0 if hg + ag > 2 else 1))
    try: S = json.load(open(os.path.join(DATA, "season.json"), encoding="utf-8"))
    except Exception: S = {}
    for lg, v in S.items():
        for m in (v or {}).get("matches", []):
            if not m.get("ft") or (m["d"], lg, m.get("h"), m.get("a")) in gor: continue
            hg, ag = m["ft"]
            if m.get("odds") and len(m["odds"]) == 3 and min(m["odds"]) > 1: X1.append((m["d"], lg, m["odds"], _sonuc(hg, ag)))
            if m.get("ou") and len(m["ou"]) == 2 and min(m["ou"]) > 1: X2.append((m["d"], lg, m["ou"], 0 if hg + ag > 2 else 1))  # ou = [üst, alt]
    return X1, X2


def yukle_iddaa():
    X1, X2 = [], []
    for d, r in arsiv.kayitlar(DATA, puanli=False):
        if r.get("hs") is None or r.get("as") is None: continue
        hg, ag, lg = r["hs"], r["as"], r.get("c", "")
        if r.get("ms") and len(r["ms"]) == 3 and min(r["ms"]) > 1: X1.append((d, lg, r["ms"], _sonuc(hg, ag)))
        if r.get("ou") and len(r["ou"]) == 2 and min(r["ou"]) > 1: X2.append((d, lg, r["ou"], 0 if hg + ag > 2 else 1))  # ou = [üst, alt]
    return X1, X2


def degerlendir(X, seed=23):
    X = sorted(X, key=lambda x: x[0]); n = len(X)
    if n < 200: return {"n": n, "not": "veri az"}
    y = np.array([x[3] for x in X]); L, Br = {}, {}
    for m, f in YONTEM.items():
        P = np.array([f(1 / np.asarray(x[2], float)) for x in X]); Y = np.eye(P.shape[1])[y]
        L[m] = -np.log(np.clip(P[np.arange(n), y], 1e-12, 1)); Br[m] = ((P - Y) ** 2).sum(1)
    blk = np.unique([f"{x[1]}|{x[0]}" for x in X], return_inverse=True)[1]; nb = int(blk.max()) + 1
    rng = np.random.default_rng(seed)
    W = np.stack([np.bincount(rng.integers(0, nb, nb), minlength=nb)[blk] for _ in range(B)]).astype(float)
    h = n // 2; out = {}
    for m in YONTEM:
        dl = L[m] - L[URETIM]; db = Br[m] - Br[URETIM]; bs = (W @ dl) / W.sum(1)
        lo, hi = np.percentile(bs, [2.5, 97.5]); y1, y2 = dl[:h].mean(), dl[h:].mean()
        out[m] = {"LL": round(float(L[m].mean()), 5), "Brier": round(float(Br[m].mean()), 5), "dLL": round(float(dl.mean()), 5),
                  "ga": [round(float(lo), 5), round(float(hi), 5)], "yari": [round(float(y1), 5), round(float(y2), 5)],
                  "dBrier": round(float(db.mean()), 6),
                  "gecti": bool(m != URETIM and hi < 0 and y1 < 0 and y2 < 0 and db.mean() <= 0)}
    return {"n": n, "marj": round(float(np.mean([sum(1 / np.asarray(x[2])) - 1 for x in X])), 4),
            "bas": X[0][0], "son": X[-1][0], "yari_ayrim": X[h][0], "yontem": out}


def main():
    R = {"tarih": date.today().isoformat(), "uretim": URETIM, "B": B, "arsiv": {}}
    for ad, f in (("derin", yukle_derin), ("iddaa", yukle_iddaa)):
        X1, X2 = f(); R["arsiv"][ad] = {"1x2": degerlendir(X1), "au25": degerlendir(X2)}
    I = R["arsiv"]["iddaa"]
    aday = [m for m in YONTEM if m != URETIM and all(I[k].get("yontem", {}).get(m, {}).get("gecti") for k in ("1x2", "au25"))]
    R["aday"] = aday
    R["karar"] = (f"aday: {', '.join(aday)} (iddaa arşivinde 1X2 ve A/Ü kapısını geçti; üretime geçiş elle)" if aday
                  else "gölgede: hiçbir yöntem power'ı standart kapıda geçmedi")
    json.dump(R, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for ad, v in R["arsiv"].items():
        for k, e in v.items():
            print(f"== {ad} {k} n={e['n']} marj={e.get('marj')} {e.get('bas')}..{e.get('son')}")
            for m, r in e.get("yontem", {}).items():
                print(f"  {m:10s} LL={r['LL']:.5f} Br={r['Brier']:.5f} ΔLL={r['dLL']:+.5f} {r['ga']} yarılar={r['yari']} geçti={r['gecti']}")
    print(R["karar"])


if __name__ == "__main__":
    main()
