"""🧮 YH-56 · Pazar motoru KG Var / KG Yok ve MS&KG birleşiklerine iddaa KG oranının katılması — zaman sıralı laboratuvar. Üretimi değiştirmez.

YH-55 uygulamanın KG olasılığını (dist → btts) KG oranıyla harmanladı; pazar motorunun KGV'si (scripts/pazar.py apply_cal: ızgara KGV +
Platt kalibratörü) ve ondan IPF ile türeyen 1&KGV / X&KGV / 2&KGV hâlâ KG oranını kullanmıyor (YH-55 lab bilgisi: Platt'lı KGV 0,6916,
saf piyasa 0,6867). Bu madde aynı bilgiyi pazar motoruna taşır; KUPO paneli ve oran sekmesi `pz` okur.

ÖNCEDEN KAYITLI TASARIM (2026-11-08; sonuç görülmeden yazıldı, değiştirilmez):
  Veri    : lab/kg_piyasa_lab.kayitlar() — kilitli bülten arşivi (3 MS + 2 KG oranı + sonuç).
  Üretim  : pazar.raw_marginals(ui_market_lam(1X2, 2,5), h1 = model.json h1) → apply_cal(kal = pazar_karne.json kalibrator) → KGV,
            MS&KG (rake). Not: kalibratör bugünkü karneden (lig maçları; bülten arşivi değil) — üretim lehine hafif iyimser, adayı zorlaştırır.
  Aday    : KGV' = σ(w·logit q + (1 − w)·logit KGV_üretim), q = KG oranının oransal payı; w ∈ {0,0 … 1,0} her sınama günü yalnız
            ÖNCEKİ günlerle (≥ 5 gün, ≥ 1.500 maç). MS&KG birleşikleri aynı rake ile yeni KGV marjinaline.
  KAPI    : (1) KGV Δ gün-blok bootstrap (B 2000) %95 GA üst < 0; (2) iki zaman yarısında Δ < 0; (3) ΔBrier ≤ 0; (4) en olası KG seçeneği
            isabeti düşmez; (5) ECE büyümez; (6) MS×KG 6'lı log-kayıp ortalaması artmaz.
Çıktı: data/kg_pazar_lab.json
"""
import json, os, random, sys
from collections import defaultdict
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import update as U          # noqa: E402
import pazar as PZ          # noqa: E402
import kg_piyasa_lab as KL  # noqa: E402

WS = [round(0.1 * i, 1) for i in range(11)]
MIN_GUN, MIN_MAC, B = 5, 1500, 2000


def lg(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))


def ll(p, y): p = np.clip(p, 1e-9, 1 - 1e-9); return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def uretim(R, P, kal):
    lam = U.ui_market_lam([r["ms"] for r in R], [r["ou"] for r in R], P.get("rho", -0.06))
    M = PZ.raw_marginals(lam[:, 0], lam[:, 1], P.get("h1", .4442), P)
    O = PZ.apply_cal(M, P, kal)
    q3 = np.stack([O["1"], O["X"], O["2"]], 1)
    return M, O, q3


def mskg(M, q3, kgv):
    K = PZ._rake(M["mskg"], q3, np.stack([1 - kgv, kgv], 1))   # (n, 3, [Yok, Var])
    return K


def main():
    P = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"]
    kal = (json.load(open(os.path.join(DATA, "pazar_karne.json"), encoding="utf-8")).get("kalibrator") or {})
    R = KL.kayitlar()
    M, O, q3 = uretim(R, P, kal)
    p0 = np.asarray(O["KGV"], float)
    inv = np.array([[1 / r["kgo"][0], 1 / r["kgo"][1]] for r in R]); q = inv[:, 0] / inv.sum(1)
    y = np.array([r["y"] for r in R], float)
    # MS sonucu: kayitlar() skorunu taşımıyor → arşivden yeniden okunur (yalnız hs/as)
    ms_y = msy(R)
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
    pos = defaultdict(list)
    for k, i in enumerate(T): pos[R[i]["d"]].append(k)
    D = {d: dl[pos[d]] for d in tg}
    rnd = random.Random(17); bs = sorted(float(np.mean(np.concatenate([D[rnd.choice(tg)] for _ in tg]))) for _ in range(B))
    ga = [bs[int(.025 * B)], bs[int(.975 * B) - 1]]
    h = len(tg) // 2; y1 = float(np.mean(np.concatenate([D[d] for d in tg[:h]]))); y2 = float(np.mean(np.concatenate([D[d] for d in tg[h:]])))
    dB = float(np.mean((pa[T] - y[T]) ** 2 - (p0[T] - y[T]) ** 2))
    is0 = float(np.mean((p0[T] >= .5) == (y[T] == 1))); isa = float(np.mean((pa[T] >= .5) == (y[T] == 1)))
    e0, ea = KL.ece(p0[T], y[T]), KL.ece(pa[T], y[T])
    # MS×KG 6'lı
    K0 = mskg({k: v[T] for k, v in M.items()}, q3[T], p0[T]); K1 = mskg({k: v[T] for k, v in M.items()}, q3[T], pa[T])
    yi = ms_y[T]; yk = y[T].astype(int); m6 = yi >= 0
    l6_0 = -np.log(np.maximum(K0[np.arange(len(T)), yi.clip(0), yk], 1e-9))[m6]
    l6_1 = -np.log(np.maximum(K1[np.arange(len(T)), yi.clip(0), yk], 1e-9))[m6]
    d6 = float(np.mean(l6_1 - l6_0))
    kapi = {"ga_ust_negatif": bool(ga[1] < 0), "iki_yari_negatif": bool(y1 < 0 and y2 < 0), "brier_kotulesmedi": bool(dB <= 0),
            "isabet_dusmedi": bool(isa >= is0), "ece_buyumedi": bool(ea <= e0), "mskg_kotulesmedi": bool(d6 <= 0)}
    out = {"v": 1, "madde": "YH-56", "tarih": gun[-1], "n_kayit": len(R), "gunler": [gun[0], gun[-1]], "n_sinama": int(len(T)),
           "sinama_gunleri": len(tg), "kalibrator_KGV": kal.get("KGV"), "secilen_gunluk": sec, "son_w": sec[max(sec)] if sec else None,
           "ll_uretim": round(float(L0[T].mean()), 5), "ll_aday": round(float(La.mean()), 5), "ll_saf_piyasa": round(float(ll(q[T], y[T]).mean()), 5),
           "delta_ll": round(float(dl.mean()), 5), "ga95": [round(x, 5) for x in ga], "yarilar": [round(y1, 5), round(y2, 5)],
           "delta_brier": round(dB, 5), "isabet": {"uretim": round(is0, 4), "aday": round(isa, 4)}, "ece": {"uretim": round(e0, 4), "aday": round(ea, 4)},
           "mskg6": {"n": int(m6.sum()), "ll_uretim": round(float(l6_0.mean()), 5), "ll_aday": round(float(l6_1.mean()), 5), "delta": round(d6, 5)},
           "kapi": kapi, "karar": "gecti" if all(kapi.values()) else "reddedildi"}
    out["kabul"] = out["karar"] == "gecti"
    json.dump(out, open(os.path.join(DATA, "kg_pazar_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "secilen_gunluk"}, ensure_ascii=False, indent=1)); print(sec)


def msy(R):
    """MS sonucu (0 ev, 1 beraberlik, 2 deplasman) — arşivdeki hs/as; bulunamazsa −1."""
    import glob
    S = {}
    for f in sorted(glob.glob(os.path.join(DATA, "archive", "*.json"))) + sorted(glob.glob(os.path.join(DATA, "archive", "eski", "*.json"))):
        g = os.path.basename(f)[:10]
        try: Dd = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        for k, r in (Dd.items() if isinstance(Dd, dict) else []):
            if isinstance(r, dict) and isinstance(r.get("hs"), int) and isinstance(r.get("as"), int):
                S[(g, k)] = 0 if r["hs"] > r["as"] else (1 if r["hs"] == r["as"] else 2)
    return np.array([S.get((r["d"], r["k"]), -1) for r in R])


if __name__ == "__main__":
    main()
