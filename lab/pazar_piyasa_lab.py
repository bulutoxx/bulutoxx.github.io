"""🧮 YH-57 · Pazar motoru ek pazarlarına (1,5 / 3,5 A/Ü, İY, İY A/Ü, 2Y, daha gollü yarı) iddaa oranının katılması — zaman sıralı laboratuvar.
Üretimi değiştirmez.

YH-55/56 KG oranının ızgara + Platt KG'sinden daha bilgili olduğunu gösterdi. Pazar motorunun diğer ek pazarları da yalnız 1X2 + 2,5
oranından kurulan ızgaradan geliyor; iddaa bu pazarların kendi oranlarını da veriyor (fixtures.json `po`, 2026-11-05'ten beri).

ÖNCEDEN KAYITLI TASARIM (2026-11-09; sonuç görülmeden yazıldı, değiştirilmez):
  Veri    : git geçmişindeki data/fixtures.json anlık görüntüleri; her maç için BAŞLAMA SAATİNDEN ÖNCEKİ son görüntü (pzy "p", pz + po).
            Sonuç: data/archive/*.json (iid → hs/as, İY h1/a1). Ham oran depoya yazılmaz; çıktı yalnız özet.
  Taban   : o görüntüde sunulan pz (PZ.full).
  Gruplar : U15, U35, IYU05, IYU15 (ikili) · IY, 2Y, YARI (üçlü). q = grubun iddaa oranlarının oransal payı (tüm seçenekler varsa).
  Aday    : ikili p' = σ(w·logit q + (1 − w)·logit p); üçlü p' ∝ q^w · p^(1 − w). w ∈ {0,0 … 1,0}.
  Seçim   : başlama gününe göre ileri yürüyüş — her sınama günü için w yalnız ÖNCEKİ günlerin maçlarıyla (≥ 300 maç) seçilir.
  KAPI (grup başına, hepsi gerekli): (1) sınamada n ≥ 500; (2) ΔLL lig×gün blok bootstrap (B 4000) iki yanlı GA, Bonferroni
            1 − 0,05/7, üst sınır < 0; (3) her sınama gününde Δ < 0 (≥ 2 gün); (4) ΔBrier ≤ 0; (5) en olası seçenek isabeti düşmez;
            (6) ECE (10 kova, seçenek başına) büyümez.
Çıktı: data/pazar_piyasa_lab.json
"""
import json, os, subprocess, sys, glob
from collections import defaultdict
from datetime import datetime, timezone
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import pazar as PZ  # noqa: E402

GRUPLAR = {"U15": ["U15", "A15"], "U35": ["U35", "A35"], "IYU05": ["IYU05", "IYA05"], "IYU15": ["IYU15", "IYA15"],
           "IY": ["IY1", "IYX", "IY2"], "2Y": ["2Y1", "2YX", "2Y2"], "YARI": ["DGY1", "DGYE", "DGY2"]}
WS = [round(0.1 * i, 1) for i in range(11)]
MIN_EGITIM, MIN_SINAMA, B, SINCE = 300, 500, 4000, "2026-11-04"
ALFA = 0.05 / len(GRUPLAR)
RNG = np.random.default_rng(57)


def anlik():
    """Her maç için başlamadan önceki son fixtures görüntüsü → {iid: f}."""
    revs = subprocess.run(["git", "-C", ROOT, "log", f"--since={SINCE}", "--format=%H %cI", "--", "data/fixtures.json"],
                          capture_output=True, text=True).stdout.split("\n")
    son = {}
    for line in reversed([r for r in revs if r.strip()]):
        h, t = line.split(); ct = datetime.fromisoformat(t)
        try: L = json.loads(subprocess.run(["git", "-C", ROOT, "show", h + ":data/fixtures.json"], capture_output=True, text=True).stdout)
        except Exception: continue
        for f in L:
            if f.get("pzy") != "p" or not f.get("pz") or not f.get("po") or not f.get("iid"): continue
            try: ko = datetime.fromisoformat(f["d"] + "T" + (f.get("t") or "00:00") + ":00+03:00")
            except Exception: continue
            if ct < ko: son[str(f["iid"])] = f
    return son


def sonuclar():
    A = {}
    for p in glob.glob(os.path.join(DATA, "archive", "*.json")):
        try: D = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        for k, r in (D.items() if isinstance(D, dict) else []):
            if isinstance(r, dict) and isinstance(r.get("hs"), int) and isinstance(r.get("as"), int):
                ht = [r["h1"], r["a1"]] if isinstance(r.get("h1"), int) and isinstance(r.get("a1"), int) else None
                A[str(k)] = ([r["hs"], r["as"]], ht)
    return A


def lgt(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))


def aday(p, q, w):
    if p.shape[1] == 2:
        v = 1 / (1 + np.exp(-(w * lgt(q[:, 0]) + (1 - w) * lgt(p[:, 0])))); return np.stack([v, 1 - v], 1)
    z = np.exp(w * np.log(np.clip(q, 1e-9, 1)) + (1 - w) * np.log(np.clip(p, 1e-9, 1))); return z / z.sum(1, keepdims=True)


def ll(P, y): return -np.log(np.clip(P[np.arange(len(y)), y], 1e-9, 1))
def brier(P, y): return ((P - np.eye(P.shape[1])[y]) ** 2).sum(1)


def ece(P, y, k=10):
    e = []
    for j in range(P.shape[1]):
        p = P[:, j]; t = (y == j).astype(float); b = np.minimum((p * k).astype(int), k - 1)
        e.append(sum(abs(p[b == i].mean() - t[b == i].mean()) * (b == i).sum() for i in range(k) if (b == i).any()) / len(p))
    return float(np.mean(e))


def boot(delta, blok):
    u, inv = np.unique(blok, return_inverse=True)
    s = np.bincount(inv, delta, len(u)); n = np.bincount(inv, None, len(u))
    idx = RNG.integers(0, len(u), (B, len(u))); bs = s[idx].sum(1) / n[idx].sum(1)
    return [round(float(np.quantile(bs, ALFA / 2)), 5), round(float(np.quantile(bs, 1 - ALFA / 2)), 5)], int(len(u))


def grup(G, kodlar, S, A):
    rows = []
    for iid, f in S.items():
        if iid not in A: continue
        po = f["po"]
        if not all(isinstance(po.get(c), (int, float)) and po[c] > 1 for c in kodlar): continue
        ft, ht = A[iid]; oc = [PZ.outcome(c, ft, ht) for c in kodlar]
        if any(o is None for o in oc) or sum(oc) != 1: continue
        pf = PZ.full(f["pz"]); p = np.array([pf.get(c, np.nan) for c in kodlar], float)
        if np.isnan(p).any(): continue
        p = np.clip(p, 1e-6, 1); p = p / p.sum()
        inv = np.array([1 / po[c] for c in kodlar]); rows.append((f["d"], f["lg"], p, inv / inv.sum(), oc.index(True)))
    rows.sort(key=lambda r: r[0])
    if not rows: return {"n": 0, "karar": "veri_yok"}
    d = np.array([r[0] for r in rows]); lg = np.array([r[1] for r in rows])
    P = np.stack([r[2] for r in rows]); Q = np.stack([r[3] for r in rows]); y = np.array([r[4] for r in rows])
    C = {w: aday(P, Q, w) for w in WS}; L = {w: ll(C[w], y) for w in WS}; L0 = ll(P, y)
    Pa = np.full_like(P, np.nan); sec = {}
    for g in sorted(set(d)):
        tr = d < g
        if tr.sum() < MIN_EGITIM: continue
        w = min(WS, key=lambda w: L[w][tr].mean()); sec[g] = w; Pa[d == g] = C[w][d == g]
    T = ~np.isnan(Pa[:, 0]); n = int(T.sum())
    out = {"n_toplam": len(rows), "n_sinama": n, "secilen_gunluk": sec, "son_w_tum_veri": min(WS, key=lambda w: L[w].mean())}
    if n == 0: out["karar"] = "veri_bekliyor"; return out
    dl = ll(Pa[T], y[T]) - L0[T]; blok = np.array([a + "|" + b for a, b in zip(lg[T], d[T])])
    ga, nb = boot(dl, blok)
    gunluk = {g: round(float(dl[d[T] == g].mean()), 5) for g in sorted(set(d[T]))}
    dB = float((brier(Pa[T], y[T]) - brier(P[T], y[T])).mean())
    i0 = float((P[T].argmax(1) == y[T]).mean()); ia = float((Pa[T].argmax(1) == y[T]).mean())
    e0, ea = ece(P[T], y[T]), ece(Pa[T], y[T])
    kapi = {"n_yeterli": n >= MIN_SINAMA, "ga_ust_negatif": ga[1] < 0, "her_gun_negatif": len(gunluk) >= 2 and all(v < 0 for v in gunluk.values()),
            "brier_kotulesmedi": dB <= 0, "isabet_dusmedi": ia >= i0, "ece_buyumedi": ea <= e0}
    out.update({"ll_uretim": round(float(L0[T].mean()), 5), "ll_aday": round(float(ll(Pa[T], y[T]).mean()), 5),
                "ll_saf_piyasa": round(float(ll(Q[T], y[T]).mean()), 5), "delta_ll": round(float(dl.mean()), 5),
                "ga": ga, "ga_duzey": round(1 - ALFA, 4), "blok": nb, "gunluk_delta": gunluk, "delta_brier": round(dB, 5),
                "isabet": {"uretim": round(i0, 4), "aday": round(ia, 4)}, "ece": {"uretim": round(e0, 4), "aday": round(ea, 4)},
                "kapi": {k: bool(v) for k, v in kapi.items()}})
    out["karar"] = "gecti" if all(kapi.values()) else ("veri_bekliyor" if not kapi["n_yeterli"] else "reddedildi")
    return out


def main():
    S = anlik(); A = sonuclar()
    R = {G: grup(G, k, S, A) for G, k in GRUPLAR.items()}
    out = {"v": 1, "madde": "YH-57", "tarih": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "n_anlik_mac": len(S),
           "tasarim": "lab/pazar_piyasa_lab.py başlığı (önceden kayıtlı)", "gruplar": R,
           "gecen": [G for G, r in R.items() if r.get("karar") == "gecti"]}
    json.dump(out, open(os.path.join(DATA, "pazar_piyasa_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for G, r in R.items():
        print(G, {k: v for k, v in r.items() if k != "secilen_gunluk"})


if __name__ == "__main__":
    main()
