#!/usr/bin/env python3
"""YH-06 · Beta kalibrasyonu laboratuvarı (pazar motoru ikili ek pazarları).

Kull, Silva Filho, Flach (2017): logit q = c + a·ln p − b·ln(1−p)  (a = b ⇒ Platt; a = b = 1, c = 0 ⇒ kimlik).
Protokol pazar.karne ile aynı: aylık ileriye dönük — her sınama ayı için kalibratör yalnız ÖNCEKİ aylarla öğrenilir,
olasılıklar kapanış oranlarından (uygulamanın sunduğu yol). Üretim = karnenin bugünkü kabul düzeni (Platt kabul edilen
pazarlarda Platt, diğerlerinde ham). Aday = beta. Kapı (pazar başına, SK): lig×gün blok bootstrap (B = 2000) ΔLL %95 GA
üst < 0, iki zaman yarısında ΔLL < 0, ΔBrier ≤ 0, tek yanlı p ≤ α (7 pazar için Bonferroni: 0,05/7).

Çalıştırma:  python3 lab/beta_kal_lab.py   → data/beta_kal_lab.json (yalnız toplu ölçüm; takım adı / ham veri yok)
"""
import json, os, sys, time
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
DATA = os.path.join(ROOT, "data")
import pazar as PZ  # noqa: E402

ALFA = 0.05 / 7
B_BOOT = 2000


def fit_beta(p, y, lam=30.0, it=40):
    """Ridge (kimlik yönüne) çekilen beta kalibrasyonu, Newton. Dönüş {a, b, c}."""
    p = np.clip(p, 1e-6, 1 - 1e-6); X = np.stack([np.ones_like(p), np.log(p), -np.log(1 - p)], 1)
    y = y.astype(float); w0 = np.array([0.0, 1.0, 1.0]); w = w0.copy()
    for _ in range(it):
        q = PZ._sig(X @ w); r = q * (1 - q)
        g = X.T @ (q - y) + lam * (w - w0)
        H = (X * r[:, None]).T @ X + lam * np.eye(3)
        st = np.linalg.solve(H, g); w = w - st
        if np.abs(st).max() < 1e-9: break
    return {"a": round(float(w[1]), 4), "b": round(float(w[2]), 4), "c": round(float(w[0]), 4)}


def beta_apply(p, k):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return PZ._sig(k["c"] + k["a"] * np.log(p) - k["b"] * np.log(1 - p))


def ll_vec(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6); return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def boot(d, blok, rnd):
    ub, inv = np.unique(blok, return_inverse=True)
    s = np.bincount(inv, weights=d); n = np.bincount(inv).astype(float)
    k = len(ub); out = np.empty(B_BOOT)
    for i in range(B_BOOT):
        j = rnd.integers(0, k, k); out[i] = s[j].sum() / n[j].sum()
    return out


def main():
    t0 = time.time()
    import update as U
    season = json.load(open(os.path.join(DATA, "season.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"]
    PK = json.load(open(os.path.join(DATA, "pazar_karne.json"), encoding="utf-8"))
    uretim_platt = {k for k, v in (PK.get("kalibrator") or {}).items() if "a" in v and "c" not in v}
    rows = PZ.hist_rows(season); del season
    rho = P.get("rho", -0.06); lam = np.zeros((len(rows), 2))
    for s_ in range(0, len(rows), 3000):
        ch = rows[s_:s_ + 3000]; lam[s_:s_ + len(ch)] = U.ui_market_lam([r["odds"] for r in ch], [r["ou"] for r in ch], rho)
    s = PZ.h1_forward(rows, P.get("h1", .4442))
    M = PZ.raw_marginals(lam[:, 0], lam[:, 1], s, P); Y = PZ.labels(rows)
    months = np.array([r["d"][:7] for r in rows]); um = sorted(set(months))
    test_m = [m_ for m_ in um if (months < m_).sum() >= 2500]
    tidx = np.where(np.isin(months, test_m))[0]
    half = sorted(rows[t]["d"] for t in tidx)[len(tidx) // 2]
    dates = np.array([r["d"] for r in rows]); blok_all = np.array([f"{r['lg']}|{r['d']}" for r in rows])
    rnd = np.random.default_rng(20261028)
    ikili = [nm for nm, (tp, _) in PZ.CALS.items() if tp == "ikili"] + ["U25"]
    sonuc = {}
    for nm in ikili:
        code = nm; src = M[code]; y = Y[code]
        ham = src.copy(); pl = src.copy(); be = src.copy(); kal_son = None
        for m_ in test_m:
            tr = (months < m_) & ~np.isnan(y); ix = months == m_
            if tr.sum() < 800: continue
            kp = PZ.fit_platt(src[tr], y[tr]); kb = fit_beta(src[tr], y[tr])
            pl[ix] = PZ._sig(kp["a"] + kp["b"] * PZ._logit(src[ix])); be[ix] = beta_apply(src[ix], kb); kal_son = kb
        ur = pl if nm in uretim_platt else ham
        m = ~np.isnan(y[tidx]); ti = tidx[m]; yy = y[ti]
        L = {"ham": ll_vec(ham[ti], yy), "platt": ll_vec(pl[ti], yy), "beta": ll_vec(be[ti], yy), "uretim": ll_vec(ur[ti], yy)}
        Bq = {"ham": (ham[ti] - yy) ** 2, "platt": (pl[ti] - yy) ** 2, "beta": (be[ti] - yy) ** 2, "uretim": (ur[ti] - yy) ** 2}
        d = L["beta"] - L["uretim"]; bl = blok_all[ti]; bs = boot(d, bl, rnd)
        A_ = dates[ti] < half
        r = {"n": int(len(ti)), "uretim_yolu": "platt" if nm in uretim_platt else "ham",
             "ll": {k: round(float(v.mean()), 5) for k, v in L.items()}, "brier": {k: round(float(v.mean()), 5) for k, v in Bq.items()},
             "dLL": round(float(d.mean()), 5), "ga95": [round(float(np.quantile(bs, .025)), 5), round(float(np.quantile(bs, .975)), 5)],
             "p_tek": round(float((bs >= 0).mean()), 4), "yari1": round(float(d[A_].mean()), 5), "yari2": round(float(d[~A_].mean()), 5),
             "dBrier": round(float((Bq["beta"] - Bq["uretim"]).mean()), 6),
             "beta_vs_platt": round(float((L["beta"] - L["platt"]).mean()), 5), "son_beta": kal_son}
        r["gecti"] = bool(nm != "U25" and r["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and r["dBrier"] <= 0 and r["p_tek"] <= ALFA)
        sonuc[nm] = r
        print(f"{nm:6s} n={r['n']} üretim={r['uretim_yolu']:5s} ΔLL={r['dLL']:+.5f} GA{r['ga95']} y1={r['yari1']:+.5f} y2={r['yari2']:+.5f} "
              f"ΔBr={r['dBrier']:+.6f} p={r['p_tek']} β−platt={r['beta_vs_platt']:+.5f} → {'GEÇTİ' if r['gecti'] else 'geçmedi'}", flush=True)
    out = {"madde": "YH-06", "tarih": time.strftime("%Y-%m-%d"), "donem": f"{rows[tidx[0]]['d']}…{rows[tidx[-1]]['d']}", "n_mac": int(len(tidx)),
           "yontem": "aylık ileriye dönük (yalnız önceki aylarla öğrenme), lig×gün blok bootstrap B=2000, α=0,05/7 (Bonferroni); "
                     "U25 yalnız bilgi (üretimde konsey yolu, kalibratör adayı değil)",
           "kabul": sorted(k for k, v in sonuc.items() if v["gecti"]), "pazarlar": sonuc, "sure_sn": round(time.time() - t0, 1)}
    json.dump(out, open(os.path.join(DATA, "beta_kal_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("kabul:", out["kabul"], out["sure_sn"], "sn")


if __name__ == "__main__":
    main()
