#!/usr/bin/env python3
"""🏀 YH-07 · Sayı farkı ağırlıklı Elo robotu + lojistik yığınlayıcı (ağsız, yalnız yerel veri).

Taban (üretim): basket.fit ağırlıklı ridge (kolej ligleri ortak ev avantajı + ön bilgi, üretimle aynı kod), haftalık ileri yürüyüş,
  p = Φ(fark / σ), σ yalnız ÖNCEKİ haftaların tahmin artıklarından (bk_gelistir 'std' ile aynı).
Elo robotu (FiveThirtyEight NBA Elo): K = 20, ev avantajı 100 Elo, sayı farkı çarpanı (MOV+3)^0,8 / (7,5 + 0,006·ΔElo_kazanan),
  sezon arası (≥ 45 gün boşluk) ortalamaya ¼ çekme, yeni takım 1500. Hafta başında DONDURULUR (ridge ile aynı bilgi: yalnız
  o haftadan önceki maçlar).
Yığınlayıcı (lig grubu başına: pro / avrupa / kolej): logit p = c + a·logit p_ridge + b·(ΔElo·ln10/400) + d·dinlenme farkı,
  her hafta yalnız önceki haftaların ileri yürüyüş satırlarıyla öğrenilir, (0, 1, 0, 0) ön bilgisine L2 ile çekilir (λ = LAM),
  en az MIN_N geçmiş satır yoksa taban kullanılır.
Kapı (yol haritası SK, grup başına ve tümü): ΔLL gün-blok bootstrap %95 GA üst < 0, iki zaman yarısında ΔLL < 0, ΔBrier ≤ 0,
  isabet düşmez, tek yanlı p ≤ α (α = 0,05 / 4: üç grup + tümü).
Çıktı: data/bk_elo_lab.json (türetilmiş özet; ham maç verisi yok).
Kullanım: python3 lab/bk_elo_lab.py   (data/bk_games.json gerekir: actions/cache ya da git yedeği)"""
import json, math, os, sys
from datetime import timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import basket as B          # noqa: E402
import bk_gelistir as G     # noqa: E402

DATA = os.path.join(ROOT, "data")
GRUP = {"nba": "pro", "wnba": "pro", "gl": "pro", "nbl": "pro", "el": "avrupa", "ec": "avrupa", "ncaa": "kolej", "ncaaw": "kolej"}
K_ELO, HCA_ELO, REVERT = 20.0, 100.0, 0.25
LAM, MIN_N = 300.0, 300
ALFA = 0.05 / 4
RNG = np.random.default_rng(20261028)


def elo_rows(games, wk0):
    """Her maç için hafta başında dondurulmuş Elo farkı (ev − dep + ev avantajı) ve dinlenme farkı (gün, 0…3)."""
    R, last, out = {}, {}, {}
    pend, cur_wk, prev_d = [], None, None
    def apply(g):
        h, a = g["h"], g["a"]; rh, ra = R.get(h, 1500.0), R.get(a, 1500.0)
        hh = 0.0 if g.get("neutral") else HCA_ELO
        e = 1 / (1 + 10 ** (-(rh + hh - ra) / 400)); mov = g["hs"] - g["as_"]; s = 1.0 if mov > 0 else 0.0
        dw = (rh + hh - ra) if mov > 0 else (ra - rh - hh)
        k = K_ELO * ((abs(mov) + 3) ** 0.8) / (7.5 + 0.006 * dw)
        R[h] = rh + k * (s - e); R[a] = ra - k * (s - e)
    for g in games:
        d = G.d_of(g)
        if prev_d is not None and (d - prev_d).days >= 45:      # sezon arası: bekleyenleri uygula, ortalamaya çek
            for x in pend: apply(x)
            pend = []
            for t in R: R[t] = (1 - REVERT) * R[t] + REVERT * 1500.0
        prev_d = d
        w = (d - wk0).days // 7 if d >= wk0 else None
        if w != cur_wk:
            for x in pend: apply(x)
            pend, cur_wk = [], w
        rh, ra = R.get(g["h"], 1500.0), R.get(g["a"], 1500.0)
        hh = 0.0 if g.get("neutral") else HCA_ELO
        rest = []
        for t in (g["h"], g["a"]):
            lt = last.get(t); rest.append(3.0 if lt is None else float(min(3, max(0, (d - lt).days - 1))))
            last[t] = d
        out[g["id"]] = ((rh + hh - ra) * math.log(10) / 400, rest[0] - rest[1])
        pend.append(g)
    return out


def backtest(games, P, min_train):
    """basket.backtest ile aynı (üretim fit'i); satır: (maç, ev bekl., dep bekl., hafta)."""
    dts = [G.d_of(g) for g in games]
    wk, last = dts[min_train], dts[-1]; rows = []
    while wk <= last:
        nxt = wk + timedelta(days=7)
        train = [g for g, d in zip(games, dts) if d < wk and (wk - d).days <= 400]
        test = [g for g, d in zip(games, dts) if wk <= d < nxt]
        if test and len(train) >= min_train:
            F = B.fit(train, wk, P)
            for g in test:
                pm = B.pred_means(F, g["h"], g["a"], g.get("neutral", False), P.get("newp"))
                if pm: rows.append((g, pm[0], pm[1], wk))
        wk = nxt
    return rows, dts[min_train]


def logit(p): return math.log(p / (1 - p))


def fit_logit(X, y, prior, lam):
    """L2'li (prior'a çekilmiş) lojistik regresyon, Newton."""
    w = prior.copy()
    for _ in range(30):
        z = X @ w; p = 1 / (1 + np.exp(-z))
        g = X.T @ (p - y) + lam * (w - prior)
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(len(w))
        st = np.linalg.solve(H, g); w -= st
        if np.max(np.abs(st)) < 1e-8: break
    return w


def rec(p, y, day):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return {"p": p, "y": y, "ll": -(y * math.log(p) + (1 - y) * math.log(1 - p)), "br": (p - y) ** 2,
            "acc": 1.0 if (p >= .5) == (y == 1.0) else 0.0, "day": day, "em": 0.0, "et": 0.0}


def boot(base, cand, ids, B_=2000):
    r = G.boot(base, cand, ids, B_)
    # tek yanlı p: gün-blok bootstrap'ta ΔLL ≥ 0 oranı
    days = {}
    for i in ids: days.setdefault(base[i]["day"], []).append(i)
    arr = np.array([(sum(cand[i]["ll"] - base[i]["ll"] for i in v), len(v)) for v in days.values()])
    n = len(arr); sims = []
    for _ in range(B_):
        s = arr[RNG.integers(0, n, n)].sum(0); sims.append(s[0] / s[1])
    r["p_tek"] = round(float(np.mean(np.array(sims) >= 0)), 4)
    return r


def main():
    data, _bj = G.load()
    feats, base_rows, ylab = {}, {}, {}
    rows_by_lg = {}
    for lg, (games, P, _L) in data.items():
        games.sort(key=lambda g: g["dt"])
        for g in games: g.setdefault("lg", lg)
        mt = 200 if lg in ("ncaa", "ncaaw") else 80
        rows, wk0 = backtest(games, P, mt)
        pm = G.probs(rows, "std")
        E = elo_rows(games, wk0)
        rows = [r for r in rows if r[0]["id"] in pm]
        rows_by_lg[lg] = rows
        for g, mh, ma, wk in rows:
            feats[g["id"]] = (lg, wk, logit(min(max(pm[g["id"]], 1e-6), 1 - 1e-6)), E[g["id"]][0], E[g["id"]][1], g["dt"][:10])
            ylab[g["id"]] = 1.0 if g["hs"] > g["as_"] else 0.0
        print(lg, len(rows), flush=True)
    # yığınlayıcı: grup başına, hafta hafta yalnız önceki haftalarla
    base, cand, cand_elo = {}, {}, {}
    coefs = {}
    for grp in ("pro", "avrupa", "kolej"):
        ids = [i for i, f in feats.items() if GRUP[f[0]] == grp]
        weeks = sorted({feats[i][1] for i in ids})
        for wk in weeks:
            tr = [i for i in ids if feats[i][1] < wk]; te = [i for i in ids if feats[i][1] == wk]
            w = wE = None
            if len(tr) >= MIN_N:
                X = np.array([[1.0, feats[i][2], feats[i][3], feats[i][4]] for i in tr]); y = np.array([ylab[i] for i in tr])
                w = fit_logit(X, y, np.array([0.0, 1.0, 0.0, 0.0]), LAM)
                wE = fit_logit(X[:, [0, 2]], y, np.array([0.0, 1.0]), LAM)     # yalnız Elo (karşılaştırma)
                coefs[grp] = {"n": len(tr), "w": [round(float(v), 4) for v in w]}
            for i in te:
                f = feats[i]; base[i] = rec(1 / (1 + math.exp(-f[2])), ylab[i], f[5])
                cand[i] = rec(1 / (1 + math.exp(-float(np.dot(w, [1, f[2], f[3], f[4]])))) if w is not None else base[i]["p"], ylab[i], f[5])
                cand_elo[i] = rec(1 / (1 + math.exp(-float(np.dot(wE, [1, f[3]])))) if wE is not None else base[i]["p"], ylab[i], f[5])
    rep = {"tarih": "2026-10-28", "madde": "YH-07",
           "yontem": "haftalık ileri yürüyüş (üretim ridge'i), Elo hafta başında dondurulmuş, yığınlayıcı grup başına yalnız önceki haftalarla (L2 ön bilgi (0,1,0,0), λ=%g, en az %d satır)" % (LAM, MIN_N),
           "elo": {"K": K_ELO, "ev": HCA_ELO, "ortalama_cekme": REVERT, "mov": "(MOV+3)^0,8/(7,5+0,006·ΔElo)"},
           "kapi": "ΔLL GA üst < 0, iki yarı ΔLL < 0, ΔBrier ≤ 0, isabet düşmez, tek yanlı p ≤ %.4f" % ALFA, "gruplar": {}}
    def judge(ids):
        s1, s2 = G.slices(rows_by_lg, set(ids))
        t = boot(base, cand, set(ids)); a = boot(base, cand, s1); b = boot(base, cand, s2)
        ok = t["d_ll_ga"][1] < 0 and a["d_ll"] < 0 and b["d_ll"] < 0 and t["d_brier"] <= 0 and t["d_isabet"] >= 0 and t["p_tek"] <= ALFA
        ll = lambda D: round(float(np.mean([D[i]["ll"] for i in ids])), 5)
        acc = lambda D: round(float(np.mean([D[i]["acc"] for i in ids])), 4)
        return {"n": len(ids), "ll_taban": ll(base), "ll_aday": ll(cand), "ll_yalniz_elo": ll(cand_elo),
                "isabet_taban": acc(base), "isabet_aday": acc(cand), "tum": t, "yari1": a, "yari2": b, "gecti": bool(ok)}
    for grp in ("pro", "avrupa", "kolej"):
        ids = [i for i in base if GRUP[feats[i][0]] == grp]
        if ids:
            rep["gruplar"][grp] = judge(ids); rep["gruplar"][grp]["son_katsayi"] = coefs.get(grp)
            print(grp, json.dumps({k: rep["gruplar"][grp][k] for k in ("n", "ll_taban", "ll_aday", "ll_yalniz_elo", "gecti")}),
                  rep["gruplar"][grp]["tum"]["d_ll_ga"], rep["gruplar"][grp]["yari1"]["d_ll"], rep["gruplar"][grp]["yari2"]["d_ll"],
                  rep["gruplar"][grp]["tum"]["p_tek"], flush=True)
    rep["tumu"] = judge(list(base))
    print("tumu", json.dumps({k: rep["tumu"][k] for k in ("n", "ll_taban", "ll_aday", "gecti")}), rep["tumu"]["tum"]["d_ll_ga"])
    json.dump(rep, open(os.path.join(DATA, "bk_elo_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
