#!/usr/bin/env python3
"""YH-27 · Basket Dean Oliver dört faktör modeli — yalnız ölçüm laboratuvarı (üretimi değiştirmez).

Girdi: takım başına maç kutu skoru → dört faktör (hücum; rakibe yapılan = savunma):
  eFG% = (FGM + 0,5·3PM) / FGA · FTr = FTM / FGA · TOV% = TOV / (FGA + 0,44·FTA + TOV) · ORB% = ORB / (ORB + rakip DRB)
  Profesyonel ligler (NBA, WNBA, G League, NBL): ESPN maç özeti (summary) kutu skoru → dört faktörün tamamı ("tam").
  Kolej (NCAA, NCAAW): ESPN skor tablosu (OREB/TOV yok) → eFG%, FTr ve ribaund payı REB/(REB+rakip REB) ("kismi").
Aşama 1: her faktör için üretimdeki ağırlıklı ridge (scripts/basket.py fit, aynı decay/lam) → takımın hücum faktörü ve rakibe
  izin verdiği faktör; maç için beklenen faktör farkları d_f = f(ev) − f(dep).
Aşama 2 (yığma): fark = β0 + β1·taban_fark + Σ γ_f·d_f, ridge; yalnız ÖNCEKİ haftaların örneklem dışı satırlarıyla öğrenilir.
Taban: aynı aşama 2 yalnız taban_fark ile (yeniden ölçekleme kazancı faktörlere yazılmasın diye). P(ev kazanır) = Φ(μ/σ),
  σ = önceki haftaların aşama 2 artıklarının std'si (her model kendi σ'sı).
Zaman sıralı, sızıntısız: haftalık ileri yürüyüş, her hafta yalnız o haftadan önceki maçlarla (≤ 400 gün) eğitim.
Kapı (SK): kazanma LL Δ gün kümeli bootstrap (B = 2000) %95 GA üst < 0 — tümde ve iki zaman diliminde (lig içi tarih yarıları),
  ΔBrier ≤ 0, tek yanlı p ≤ α = 0,05. Fark MAE de raporlanır. NBA / WNBA / diğer pro / kolej ayrı rapor (grup kapısı aynı ölçüt).
Veri: data/bk_games.json (iş akışında actions/cache) + ESPN herkese açık kutu skorları (yalnız bellekte; hiçbir ham değer yazılmaz).
Çıktı: data/bk_dortfaktor_lab.json (toplu metrik). EuroLeague/EuroCup kapsam dışı.
Kullanım: python3 lab/bk_dortfaktor_lab.py [--lig nba,wnba]
"""
import json, math, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "lab"))
import basket as B  # noqa: E402
import bk_tempo_lab as T  # noqa: E402  (skor tablosu istatistikleri, gün kümeli yardımcılar)

DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "bk_dortfaktor_lab.json")
MIN_TRAIN = 120
MIN_PRIOR = 150
ALFA = 0.05
NB = 2000
LAM2 = 1.0
RNG = np.random.default_rng(20261029)
PRO = ("nba", "wnba", "gl", "nbl")
GRUP = {"nba": "nba", "wnba": "wnba", "gl": "diger_pro", "nbl": "diger_pro", "ncaa": "kolej", "ncaaw": "kolej"}
FAKTOR = {"tam": ("efg", "ftr", "tov", "orb"), "kismi": ("efg", "ftr", "reb")}


# ------------------------------------------------------------- kutu skoru (yalnız bellekte)
def _num(v):
    try:
        return float(v)
    except Exception:
        return None


def parse_box_team(stats):
    """ESPN summary boxscore.teams[i].statistics → düz sözlük ("a-b" çiftleri açılır)."""
    out = {}
    for s in stats or []:
        nm, dv = s.get("name") or "", s.get("displayValue")
        if "-" in nm and isinstance(dv, str) and "-" in dv:
            ks, vs = nm.split("-"), dv.split("-")
            if len(ks) == len(vs):
                for k, v in zip(ks, vs):
                    x = _num(v)
                    if x is not None:
                        out[k] = x
            continue
        x = _num(s.get("value")) if s.get("value") is not None else _num(dv)
        if x is not None:
            out[nm] = x
    return out


def fetch_summary(code, gid):
    u = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{code}/summary?event={gid[1:]}"
    try:
        d = B.fetch(u)
        tm = {t.get("homeAway"): parse_box_team(t.get("statistics")) for t in (d.get("boxscore") or {}).get("teams", [])}
        if "home" in tm and "away" in tm:
            return gid, (tm["home"], tm["away"])
    except Exception:
        pass
    return gid, None


def fetch_box(lg, games, adlar):
    """→ ({maç id: (ev, dep)}, istek, hata). Pro: summary (4 işçi); kolej: skor tablosu (bk_tempo_lab.fetch_stats)."""
    if lg not in PRO:
        return T.fetch_stats(lg, games)
    code = B.LEAGUES[lg][1]
    out, err = {}, 0
    with ThreadPoolExecutor(4) as ex:
        for gid, st in ex.map(lambda g: fetch_summary(code, g["id"]), games):
            if st:
                out[gid] = st
                for t in st:
                    adlar.update(t.keys())
            else:
                err += 1
    return out, len(games), err


def tov_of(t):
    for k in ("totalTurnovers", "turnovers"):
        if t.get(k) is not None:
            return t[k]
    return None


def factors(st):
    """(ev, dep) istatistik → {'tam': (fh, fa) | None, 'kismi': (fh, fa) | None}; f = {faktör: değer×100}."""
    h, a = st

    def base(t):
        fga, fgm, tpm = t.get("fieldGoalsAttempted"), t.get("fieldGoalsMade"), t.get("threePointFieldGoalsMade")
        ftm, fta = t.get("freeThrowsMade"), t.get("freeThrowsAttempted")
        if not fga or fga < 20 or fgm is None or tpm is None or ftm is None:
            return None
        return {"efg": 100 * (fgm + 0.5 * tpm) / fga, "ftr": 100 * ftm / fga, "_fga": fga, "_fta": fta or 0.0}

    bh, ba = base(h), base(a)
    if not bh or not ba:
        return {"tam": None, "kismi": None}
    res = {"tam": None, "kismi": None}
    rh, ra = h.get("rebounds", h.get("totalRebounds")), a.get("rebounds", a.get("totalRebounds"))
    if rh is not None and ra is not None and rh + ra > 0:
        res["kismi"] = (dict(bh, reb=100 * rh / (rh + ra)), dict(ba, reb=100 * ra / (rh + ra)))
    th, ta = tov_of(h), tov_of(a)
    oh, oa = h.get("offensiveRebounds"), a.get("offensiveRebounds")
    dh, da = h.get("defensiveRebounds"), a.get("defensiveRebounds")
    if None not in (th, ta, oh, oa, dh, da) and oh + da > 0 and oa + dh > 0:
        fh = dict(bh, tov=100 * th / (bh["_fga"] + 0.44 * bh["_fta"] + th), orb=100 * oh / (oh + da))
        fa = dict(ba, tov=100 * ta / (ba["_fga"] + 0.44 * ba["_fta"] + ta), orb=100 * oa / (oa + dh))
        res["tam"] = (fh, fa)
    return res


# ------------------------------------------------------------- ileri yürüyüş
def walk(games, P, kind):
    """(maç, taban fark, [d_f...], hafta) satırları; aşama 1 yalnız o haftadan önceki maçlarla."""
    fs = FAKTOR[kind]
    dts = [T.d_of(g) for g in games]
    wk, last = dts[MIN_TRAIN], dts[-1]
    rows = []
    while wk <= last:
        nxt = wk + timedelta(days=7)
        train = [g for g, d in zip(games, dts) if d < wk and (wk - d).days <= 400]
        test = [g for g, d in zip(games, dts) if wk <= d < nxt]
        ftrain = [g for g in train if g.get("_f")]
        if test and len(train) >= MIN_TRAIN and len(ftrain) >= MIN_TRAIN:
            F = B.fit(train, wk, P)
            FF = {f: B.fit([dict(g, hs=g["_f"][0][f], as_=g["_f"][1][f]) for g in ftrain], wk, P, joint=False) for f in fs}
            for g in test:
                pm = B.pred_means(F, g["h"], g["a"], g.get("neutral", False), P.get("newp"))
                if not pm:
                    continue
                d = []
                for f in fs:
                    pf = B.pred_means(FF[f], g["h"], g["a"], g.get("neutral", False), [0.0, 0.0])
                    d.append(pf[0] - pf[1] if pf else 0.0)
                rows.append((g, pm[0] - pm[1], d, wk))
        wk = nxt
    return rows


def ridge(X, y, lam=LAM2):
    """Kesişim cezasız ridge (sütunlar ölçeklenir)."""
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    A = np.c_[np.ones(len(Z)), Z]
    R = lam * np.eye(A.shape[1]); R[0, 0] = 0
    w = np.linalg.solve(A.T @ A + R, A.T @ y)
    return lambda Xn: np.c_[np.ones(len(Xn)), (Xn - mu) / sd] @ w, w[1:] / sd


def score(rows):
    """Model başına maç düzeyi ölçüler (aşama 2 ve σ yalnız önceki haftalardan)."""
    out = {"taban": {}, "dortfaktor": {}}
    katsayi = []
    for wk in sorted({r[3] for r in rows}):
        prior = [r for r in rows if r[3] < wk]
        cur = [r for r in rows if r[3] == wk]
        if len(prior) < MIN_PRIOR or not cur:
            continue
        y = np.array([r[0]["hs"] - r[0]["as_"] for r in prior], float)
        Xb = np.array([[r[1]] for r in prior]); Xf = np.array([[r[1]] + r[2] for r in prior])
        fb, _ = ridge(Xb, y); ff, cf = ridge(Xf, y)
        katsayi.append(cf)
        sb = max(1.0, float(np.std(y - fb(Xb)))); sf = max(1.0, float(np.std(y - ff(Xf))))
        mb = fb(np.array([[r[1]] for r in cur])); mf = ff(np.array([[r[1]] + r[2] for r in cur]))
        for r, ub, uf in zip(cur, mb, mf):
            g = r[0]; mar = g["hs"] - g["as_"]; yw = 1.0 if mar > 0 else 0.0
            for k, mu, s in (("taban", ub, sb), ("dortfaktor", uf, sf)):
                p = min(max(T.phi(mu / s), 1e-6), 1 - 1e-6)
                out[k][g["id"]] = {"mae": abs(mar - mu), "ll": -(yw * math.log(p) + (1 - yw) * math.log(1 - p)),
                                   "br": (p - yw) ** 2, "isabet": float((mu > 0) == (mar > 0)),
                                   "day": g["dt"][:10], "lg": g["lg"], "dt": g["dt"]}
    kat = np.mean(katsayi, 0).round(4).tolist() if katsayi else None
    return out, kat


def boot(base, cand, ids):
    days = {}
    for i in ids:
        days.setdefault(base[i]["day"], []).append(i)
    keys = list(days)
    if len(keys) < 5:
        return None
    ms = ("ll", "br", "mae", "isabet")
    arr = np.array([[sum(cand[i][m] - base[i][m] for i in days[k]) for m in ms] + [len(days[k])] for k in keys])
    pt = arr.sum(0); pt = pt[:4] / pt[4]
    n = len(keys)
    sims = np.array([(lambda s: s[:4] / s[4])(arr[RNG.integers(0, n, n)].sum(0)) for _ in range(NB)])
    lo, hi = np.percentile(sims, [2.5, 97.5], axis=0)
    r = lambda v: round(float(v), 5)
    return {"n": len(ids), "gun": n, "d_ll": r(pt[0]), "d_ll_ga": [r(lo[0]), r(hi[0])], "d_brier": r(pt[1]),
            "d_brier_ga": [r(lo[1]), r(hi[1])], "d_mae": r(pt[2]), "d_mae_ga": [r(lo[2]), r(hi[2])],
            "d_isabet": r(pt[3]), "p_ll": r(float(np.mean(sims[:, 0] >= 0)))}


def summ(sc, ids):
    if not ids:
        return None
    f = lambda m: round(float(np.mean([sc[i][m] for i in ids])), 4)
    return {"n": len(ids), "ll": f("ll"), "brier": f("br"), "mae_fark": f("mae"), "isabet": f("isabet")}


def gate(base, cand, ids, alfa=ALFA):
    ids = sorted(ids, key=lambda i: base[i]["dt"])
    by = {}
    for i in ids:
        by.setdefault(base[i]["lg"], []).append(i)
    s1, s2 = [], []
    for xs in by.values():
        h = len(xs) // 2; s1 += xs[:h]; s2 += xs[h:]
    out = {"tum": boot(base, cand, ids), "dilim1": boot(base, cand, s1), "dilim2": boot(base, cand, s2)}
    ok = all(out[k] and out[k]["d_ll"] < 0 for k in ("dilim1", "dilim2")) and bool(out["tum"]) \
        and out["tum"]["d_ll_ga"][1] < 0 and out["tum"]["d_brier"] <= 0 and out["tum"]["p_ll"] <= alfa \
        and all(out[k]["d_ll_ga"][1] < 0 for k in ("dilim1", "dilim2"))
    out["gecti"] = bool(ok)
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--lig", default="")
    a = ap.parse_args(argv)
    t0 = time.time()
    lgs = T.load_games()
    if a.lig:
        lgs = {k: v for k, v in lgs.items() if k in a.lig.split(",")}
    res = {"zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "madde": "YH-27",
           "yontem": "haftalık ileri yürüyüş; aşama 1: faktör başına ridge (basket.fit), aşama 2: önceki haftaların örneklem dışı "
                     "satırlarıyla ridge yığma (taban da aynı aşama 2, yalnız taban farkı); P = Φ(μ/σ); gün kümeli bootstrap B=2000; "
                     "kapı: kazanma LL GA üst < 0 (tüm + iki dilim), ΔBrier ≤ 0, p ≤ 0,05",
           "lig": {}, "kapsam": {}, "grup": {}}
    allsc = {"taban": {}, "dortfaktor": {}}
    adlar = set()
    for lg, (games, P) in lgs.items():
        st, nurl, nerr = fetch_box(lg, games, adlar)
        cnt = {"tam": 0, "kismi": 0}
        fx = {}
        for g in games:
            s = st.get(g["id"])
            if s:
                fx[g["id"]] = factors(s)
                for k in cnt:
                    cnt[k] += fx[g["id"]][k] is not None
        kind = "tam" if cnt["tam"] >= 0.8 * max(1, len(games)) else ("kismi" if cnt["kismi"] >= MIN_TRAIN + 30 else None)
        res["kapsam"][lg] = {"mac": len(games), "tam": cnt["tam"], "kismi": cnt["kismi"], "tur": kind, "istek": nurl, "hata": nerr}
        print(lg, res["kapsam"][lg], flush=True)
        if not kind:
            continue
        for g in games:
            v = fx.get(g["id"])
            if v and v[kind]:
                g["_f"] = v[kind]
        rows = walk(games, P, kind)
        sc, kat = score(rows)
        ids = set(sc["taban"])
        res["lig"][lg] = {"n": len(ids), "tur": kind, "faktorler": list(FAKTOR[kind]),
                          "katsayi_fark_ve_faktorler": kat, **{k: summ(sc[k], ids) for k in sc}}
        for k in sc:
            allsc[k].update(sc[k])
        print(lg, json.dumps(res["lig"][lg], ensure_ascii=False), flush=True)
        for g in games:
            g.pop("_f", None)
    ids = set(allsc["taban"])
    res["tum"] = {k: summ(allsc[k], ids) for k in allsc}
    res["kapi"] = gate(allsc["taban"], allsc["dortfaktor"], ids) if ids else {}
    for gr in sorted(set(GRUP.values())):
        gi = {i for i in ids if GRUP.get(allsc["taban"][i]["lg"]) == gr}
        if gi:
            res["grup"][gr] = {"ozet": {k: summ(allsc[k], gi) for k in allsc}, "kapi": gate(allsc["taban"], allsc["dortfaktor"], gi)}
    res["gecti"] = bool(res["kapi"].get("gecti"))
    res["gecen_gruplar"] = [g for g, v in res["grup"].items() if v["kapi"].get("gecti")]
    res["istatistik_adlari_ornek"] = sorted(adlar)[:60]
    res["sure_sn"] = round(time.time() - t0)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"tum": res["tum"], "kapi": res["kapi"], "gecen_gruplar": res["gecen_gruplar"],
                      "grup": {g: v["kapi"].get("tum") for g, v in res["grup"].items()}}, ensure_ascii=False))
    return res


if __name__ == "__main__":
    main()
