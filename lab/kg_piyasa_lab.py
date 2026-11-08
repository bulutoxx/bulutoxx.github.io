"""⚽ YH-55 · KG (karşılıklı gol) olasılığına iddaa KG oranının katılması — zaman sıralı laboratuvar. Üretimi değiştirmez.

Teşhis (lab/isabet_teshis.py, 2026-11-08, kilitli bülten arşivi n 4.893): uygulamanın KG Var olasılığı yalnız 1X2 + 2,5 oranlarına
uydurulan gol beklentisinden (dist → btts) geliyor; KG oranının kendisi kullanılmıyor. Ham yol LL 0,6852 / ECE 0,039, KG oran payı
LL 0,6825 / ECE 0,018. Daha önce denenenlerden farkı: YH-06 (beta kalibrasyonu, KGV) yalnız modelin kendi olasılığını yeniden ölçekledi;
YH-33/34 ortak Poisson'u 1X2 + 2,5'ten kurdu, KG oranını hiç kullanmadı. Burada KG pazarının KENDİ oranı bilgiye katılır.

ÖNCEDEN KAYITLI TASARIM (2026-11-08; sonuç görülmeden yazıldı, değiştirilmez):
  Veri    : data/archive/*.json (+ eski/) — sonucu olan, 3 MS oranı ve 2 KG oranı (> 1) olan kilitli bülten kayıtları.
  Üretim  : uygulamanın dist()'i — ui_market_lam (power; 1X2 + varsa 2,5) → gscale (model.json) → iki yarı Dixon–Coles → btts.
  Piyasa  : KG oranının oransal (marj bölüştürmeli) payı q = (1/o_var) / (1/o_var + 1/o_yok).
  Aday    : logit p = w · logit q + (1 − w) · logit p_üretim; w ∈ {0,0; 0,1; …; 1,0}; her sınama günü d için w yalnız d'den ÖNCEKİ
            günlerde ortalama LL'yi en küçük yapan değer (en az 5 eğitim günü ve 1.500 maç).
  Ölçüt   : maç başına Δ = LL_aday − LL_üretim (KG Var/Yok ikili).
  KAPI    : (1) Δ gün-blok bootstrap (B 2000) %95 GA üst sınırı < 0; (2) sınama günlerinin iki zaman yarısında ortalama Δ < 0;
            (3) ΔBrier ≤ 0; (4) "en olası KG seçeneği" isabeti düşmez; (5) ECE büyümez. Hepsi → "gecti", yoksa "reddedildi".
Çıktı: data/kg_piyasa_lab.json
"""
import glob, json, math, os, random, sys
from collections import defaultdict
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import update as U   # noqa: E402

WS = [round(0.1 * i, 1) for i in range(11)]
MIN_GUN, MIN_MAC, B = 5, 1500, 2000


def ok_(o, n): return isinstance(o, list) and len(o) == n and all(isinstance(x, (int, float)) and x > 1 for x in o)


def kayitlar():
    R = []
    for f in sorted(glob.glob(os.path.join(DATA, "archive", "*.json"))) + sorted(glob.glob(os.path.join(DATA, "archive", "eski", "*.json"))):
        g = os.path.basename(f)[:10]
        try: D = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        for k, r in (D.items() if isinstance(D, dict) else []):
            if not isinstance(r, dict) or not isinstance(r.get("hs"), int) or not isinstance(r.get("as"), int): continue
            if not ok_(r.get("ms"), 3) or not ok_(r.get("kgo"), 2): continue
            R.append({"d": g, "k": k, "ms": r["ms"], "ou": r["ou"] if ok_(r.get("ou"), 2) else None, "kgo": r["kgo"],
                      "y": int(r["hs"] > 0 and r["as"] > 0)})
    R.sort(key=lambda r: (r["d"], r["k"]))
    return R


def uretim_btts(R):
    """index.html dist(): kıstırma → gscale → iki yarı DC (rho, rho·0,6) → maç sonu ızgarası → iki takım da ≥1."""
    P = {}
    try: P = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"]
    except Exception: pass
    rho, h1, g = P.get("rho", -0.06), P.get("h1", .4442), P.get("gscale", 1.0)
    lam = U.ui_market_lam([r["ms"] for r in R], [r["ou"] for r in R], rho)
    lh = np.clip(lam[:, 0], .15, 4.5) * g; la = np.clip(lam[:, 1], .1, 4) * g
    out = np.zeros(len(R))
    for s in range(0, len(R), 500):
        a, b = lh[s:s + 500], la[s:s + 500]
        g1 = U._dc_grid(a * h1, b * h1, rho, 7); g2 = U._dc_grid(a * (1 - h1), b * (1 - h1), rho * .6, 7)
        ft = np.zeros((len(a), 15, 15))
        for x in range(8):
            for y in range(8): ft[:, x:x + 8, y:y + 8] += g1[:, x, y, None, None] * g2
        out[s:s + 500] = ft[:, 1:, 1:].sum((1, 2))
    return out, {"rho": rho, "h1": h1, "gscale": g}


def lg(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))


def ll(p, y): p = np.clip(p, 1e-9, 1 - 1e-9); return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def ece(p, y, k=10):
    b = np.minimum((p * k).astype(int), k - 1)
    return float(sum(abs(p[b == i].sum() - y[b == i].sum()) for i in range(k)) / len(p))


def main():
    R = kayitlar(); p0, prm = uretim_btts(R)
    inv = np.array([[1 / r["kgo"][0], 1 / r["kgo"][1]] for r in R]); q = inv[:, 0] / inv.sum(1)
    y = np.array([r["y"] for r in R], float)
    gun = sorted({r["d"] for r in R}); ix = defaultdict(list)
    for i, r in enumerate(R): ix[r["d"]].append(i)
    cand = {w: 1 / (1 + np.exp(-(w * lg(q) + (1 - w) * lg(p0)))) for w in WS}
    Lw = {w: ll(cand[w], y) for w in WS}; L0 = ll(p0, y)
    pa = np.full(len(R), np.nan); sec = {}
    for j, d in enumerate(gun):
        I0 = [i for dd in gun[:j] for i in ix[dd]]
        if j < MIN_GUN or len(I0) < MIN_MAC: continue
        w = min(WS, key=lambda w: Lw[w][I0].mean()); sec[d] = w; pa[ix[d]] = cand[w][ix[d]]
    T = np.where(~np.isnan(pa))[0]; tg = sorted({R[i]["d"] for i in T})
    La = ll(pa[T], y[T]); dl = La - L0[T]
    D = {d: dl[[k for k, i in enumerate(T) if R[i]["d"] == d]] for d in tg}
    rnd = random.Random(13); bs = sorted(float(np.mean(np.concatenate([D[rnd.choice(tg)] for _ in tg]))) for _ in range(B))
    ga = [bs[int(.025 * B)], bs[int(.975 * B) - 1]]
    h = len(tg) // 2; y1 = float(np.mean(np.concatenate([D[d] for d in tg[:h]]))); y2 = float(np.mean(np.concatenate([D[d] for d in tg[h:]])))
    dB = float(np.mean((pa[T] - y[T]) ** 2 - (p0[T] - y[T]) ** 2))
    is0 = float(np.mean((p0[T] >= .5) == (y[T] == 1))); isa = float(np.mean((pa[T] >= .5) == (y[T] == 1)))
    e0, ea = ece(p0[T], y[T]), ece(pa[T], y[T])
    # bilgi: güvenli taraf (en olası KG seçeneği ≥ 0,58) isabeti
    def guv(p):
        m = np.maximum(p, 1 - p) >= .58; t = (p >= .5) == (y == 1)
        return {"n": int(m[T].sum()), "isabet": round(float(t[T][m[T]].mean()), 4) if m[T].any() else None,
                "soylenen": round(float(np.maximum(p, 1 - p)[T][m[T]].mean()), 4) if m[T].any() else None}
    kapi = {"ga_ust_negatif": bool(ga[1] < 0), "iki_yari_negatif": bool(y1 < 0 and y2 < 0), "brier_kotulesmedi": bool(dB <= 0),
            "isabet_dusmedi": bool(isa >= is0), "ece_buyumedi": bool(ea <= e0)}
    son_w = sec[max(sec)] if sec else None
    w_tum = min(WS, key=lambda w: Lw[w].mean())
    out = {"v": 1, "madde": "YH-55", "tarih": gun[-1], "n_kayit": len(R), "gunler": [gun[0], gun[-1]], "n_sinama": int(len(T)), "sinama_gunleri": len(tg),
           "uretim_param": prm, "devig": "oransal", "secilen_gunluk": sec, "son_w": son_w, "w_tum_veri": w_tum,
           "ll_uretim": round(float(L0[T].mean()), 5), "ll_aday": round(float(La.mean()), 5), "ll_saf_piyasa": round(float(ll(q[T], y[T]).mean()), 5),
           "delta_ll": round(float(dl.mean()), 5), "ga95": [round(x, 5) for x in ga], "yarilar": [round(y1, 5), round(y2, 5)],
           "delta_brier": round(dB, 5), "isabet": {"uretim": round(is0, 4), "aday": round(isa, 4)}, "ece": {"uretim": round(e0, 4), "aday": round(ea, 4)},
           "guvenli_058": {"uretim": guv(p0), "aday": guv(np.where(np.isnan(pa), p0, pa))},
           "kapi": kapi, "karar": "gecti" if all(kapi.values()) else "reddedildi"}
    out["kabul"] = out["karar"] == "gecti"
    json.dump(out, open(os.path.join(DATA, "kg_piyasa_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "secilen_gunluk"}, ensure_ascii=False, indent=1)); print(sec)


if __name__ == "__main__":
    main()
