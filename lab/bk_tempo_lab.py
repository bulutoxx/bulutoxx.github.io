#!/usr/bin/env python3
"""YH-14 · Basket tempo (hücum sayısı) tabanlı toplam sayı modeli — yalnız ölçüm laboratuvarı.

Aday: toplam = tempo × (verim_ev + verim_dep) / 100
  * hücum sayısı (maç başına, iki takım ortalaması) = FGA − OREB + TOV + 0,44·FTA (OREB/TOV yoksa FGA + 0,44·FTA; lig içinde tek formül)
  * tempo ve 100 hücum başına verim, üretimdeki ağırlıklı ridge (scripts/basket.py fit) ile ayrı ayrı öğrenilir
Taban: üretim modeli (basket.fit, aynı parametreler) toplamı.
Adaylar: "tempo" (yalnız tempo toplamı) ve "harman" (tempo ile üretimin ağırlığı her hafta yalnız ÖNCEKİ haftaların hatasından seçilir).

Zaman sıralı, sızıntısız: haftalık ileri yürüyüş, her hafta yalnız o haftadan önceki maçlarla eğitim (basket.backtest ile aynı pencere).
Alt/üst: çizgi = ⌊taban toplamı⌋ + 0,5 (iki model aynı çizgide), P(üst) = 1 − Φ((çizgi − μ)/σ), σ = o haftadan önceki tahmin hatalarının std'si.
Kapı (SK): toplam MAE Δ ve alt/üst log-loss Δ için gün kümeli bootstrap (B = 2000) %95 GA üst sınırı < 0 — tümde ve iki zaman diliminde,
ΔBrier ≤ 0, tek yanlı p ≤ α/aday sayısı.

Veri: data/bk_games.json (iş akışında actions/cache) + ESPN herkese açık skor tablosundaki takım istatistikleri (yalnız bellekte;
hiçbir ham değer yazılmaz). Çıktı: data/bk_tempo_lab.json (toplu metrik). EuroLeague/EuroCup kapsam dışı (kutu skoru biçimi farklı).
Kullanım: python3 lab/bk_tempo_lab.py
"""
import json, math, os, sys, time
from datetime import date, datetime, timedelta, timezone
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import basket as B  # noqa: E402

DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "bk_tempo_lab.json")
MIN_TRAIN = 120
MIN_PRIOR = 60
ALFA = 0.05
NB = 2000
RNG = np.random.default_rng(20261029)
ESPN_LG = [lg for lg, v in B.LEAGUES.items() if v[0] == "espn"]


def d_of(g):
    return datetime.fromisoformat(g["dt"].replace("Z", "+00:00")).date()


# ------------------------------------------------------------- takım istatistikleri (yalnız bellekte)
def _stat(t):
    out = {}
    for s in t.get("statistics") or []:
        try:
            out[s.get("name")] = float(s.get("displayValue") if s.get("value") is None else s.get("value"))
        except Exception:
            pass
    return out


def stats_from_board(d):
    res = {}
    for e in d.get("events", []):
        try:
            c = e["competitions"][0]
            cs = {t["homeAway"]: _stat(t) for t in c["competitors"]}
            if "home" in cs and "away" in cs:
                res["e" + str(e["id"])] = (cs["home"], cs["away"])
        except Exception:
            continue
    return res


def fetch_stats(lg, games):
    """ESPN skor tablosu (aylık; kolejde günlük) → {maç id: (ev ist., dep ist.)}."""
    code = B.LEAGUES[lg][1]
    out, err = {}, 0
    if "college-basketball" in code:
        keys = sorted({g["dt"][:10].replace("-", "") for g in games})
        # ESPN tarihleri ABD saatine göre: UTC gününün bir öncesi de denenir
        ext = set(keys)
        for k in keys:
            ext.add((datetime.strptime(k, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d"))
        urls = [f"https://site.api.espn.com/apis/site/v2/sports/basketball/{code}/scoreboard?dates={k}&limit=500&groups=50" for k in sorted(ext)]
    else:
        keys = sorted({g["dt"][:7].replace("-", "") for g in games})
        urls = [f"https://site.api.espn.com/apis/site/v2/sports/basketball/{code}/scoreboard?dates={k}&limit=1000" for k in keys]
    for u in urls:
        try:
            out.update(stats_from_board(B.fetch(u)))
        except Exception:
            err += 1
        time.sleep(0.15)
    return out, len(urls), err


def poss_of(st):
    """İki takımın hücum sayısı tahmini (ortalama); yoksa None. Dönüş: (hücum, 'tam'|'yaklasik')."""
    h, a = st
    def one(t):
        fga, fta = t.get("fieldGoalsAttempted"), t.get("freeThrowsAttempted")
        if not fga or fta is None:
            return None, None
        orb, tov = t.get("offensiveRebounds"), t.get("turnovers", t.get("totalTurnovers"))
        if orb is not None and tov is not None:
            return fga - orb + tov + 0.44 * fta, "tam"
        return fga + 0.44 * fta, "yaklasik"
    ph, kh = one(h); pa, ka = one(a)
    if ph is None or pa is None or ph <= 20 or pa <= 20:
        return None, None
    return (ph + pa) / 2, ("tam" if kh == ka == "tam" else "yaklasik")


# ------------------------------------------------------------- modeller
def tempo_fit(train, ref, P, kind):
    """Tempo ve verim ridge'leri (basket.fit). Yalnız istatistiği olan maçlar; tek formül türü (kind)."""
    tg = [g for g in train if g.get("_p") and g.get("_k") == kind]
    if len(tg) < MIN_TRAIN:
        return None
    pace_games = [dict(g, hs=g["_p"], as_=g["_p"], neutral=True) for g in tg]
    eff_games = [dict(g, hs=100.0 * g["hs"] / g["_p"], as_=100.0 * g["as_"] / g["_p"]) for g in tg]
    FP = B.fit(pace_games, ref, P, joint=False)
    FE = B.fit(eff_games, ref, P)
    return (FP, FE) if FP and FE else None


def tempo_total(T, g, P):
    if T is None:
        return None
    FP, FE = T
    pp = B.pred_means(FP, g["h"], g["a"], True, [0.0, 0.0])
    pe = B.pred_means(FE, g["h"], g["a"], g.get("neutral", False), [0.0, 0.0])
    if not pp or not pe:
        return None
    pace = (pp[0] + pp[1]) / 2
    return pace * (pe[0] + pe[1]) / 100.0


def walk(games, P, kind):
    """(maç, taban toplam, tempo toplam, hafta) satırları."""
    if len(games) < MIN_TRAIN + 30:
        return []
    dts = [d_of(g) for g in games]
    wk, last = dts[MIN_TRAIN], dts[-1]
    rows = []
    while wk <= last:
        nxt = wk + timedelta(days=7)
        train = [g for g, d in zip(games, dts) if d < wk and (wk - d).days <= 400]
        test = [g for g, d in zip(games, dts) if wk <= d < nxt]
        if test and len(train) >= MIN_TRAIN:
            F = B.fit(train, wk, P)
            T = tempo_fit(train, wk, P, kind)
            for g in test:
                pm = B.pred_means(F, g["h"], g["a"], g.get("neutral", False), P.get("newp"))
                tt = tempo_total(T, g, P)
                if pm and tt is not None and math.isfinite(tt):
                    rows.append((g, pm[0] + pm[1], tt, wk))
        wk = nxt
    return rows


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def score(rows):
    """Aday başına maç düzeyi ölçüler: {id: {mae, ll, br, day}}; σ ve harman ağırlığı yalnız önceki haftalardan."""
    out = {"taban": {}, "tempo": {}, "harman": {}}
    wts = []
    weeks = sorted({r[3] for r in rows})
    for wk in weeks:
        prior = [r for r in rows if r[3] < wk]
        if len(prior) < MIN_PRIOR:
            continue
        y = np.array([r[0]["hs"] + r[0]["as_"] for r in prior], float)
        b = np.array([r[1] for r in prior]); t = np.array([r[2] for r in prior])
        dlt = t - b; den = float(np.dot(dlt, dlt))
        w = float(np.clip(np.dot(dlt, y - b) / den, 0, 1)) if den > 1e-9 else 0.0
        wts.append(w)
        preds = {"taban": b, "tempo": t, "harman": b + w * dlt}
        sig = {k: max(1.0, float(np.std(y - v))) for k, v in preds.items()}
        for r in rows:
            if r[3] != wk:
                continue
            g = r[0]; real = g["hs"] + g["as_"]
            line = math.floor(r[1]) + 0.5; ov = 1.0 if real > line else 0.0
            for k, mu in (("taban", r[1]), ("tempo", r[2]), ("harman", r[1] + w * (r[2] - r[1]))):
                p = min(max(1 - phi((line - mu) / sig[k]), 1e-6), 1 - 1e-6)
                out[k][g["id"]] = {"mae": abs(real - mu), "ll": -(ov * math.log(p) + (1 - ov) * math.log(1 - p)),
                                   "br": (p - ov) ** 2, "day": g["dt"][:10], "lg": g["lg"], "dt": g["dt"]}
    return out, (round(float(np.mean(wts)), 3) if wts else None)


def boot(base, cand, ids):
    days = {}
    for i in ids:
        days.setdefault(base[i]["day"], []).append(i)
    keys = list(days)
    if len(keys) < 5:
        return None
    arr = np.array([[sum(cand[i][m] - base[i][m] for i in days[k]) for m in ("mae", "ll", "br")] + [len(days[k])] for k in keys])
    pt = arr.sum(0); pt = pt[:3] / pt[3]
    n = len(keys)
    sims = np.array([(lambda s: s[:3] / s[3])(arr[RNG.integers(0, n, n)].sum(0)) for _ in range(NB)])
    lo, hi = np.percentile(sims, [2.5, 97.5], axis=0)
    r = lambda v: round(float(v), 5)
    return {"n": len(ids), "d_mae": r(pt[0]), "d_mae_ga": [r(lo[0]), r(hi[0])], "d_ll": r(pt[1]), "d_ll_ga": [r(lo[1]), r(hi[1])],
            "d_brier": r(pt[2]), "d_brier_ga": [r(lo[2]), r(hi[2])], "p_ll": r(float(np.mean(sims[:, 1] >= 0))),
            "p_mae": r(float(np.mean(sims[:, 0] >= 0)))}


def summ(sc, ids):
    if not ids:
        return None
    f = lambda m: round(float(np.mean([sc[i][m] for i in ids])), 4)
    return {"n": len(ids), "mae_toplam": f("mae"), "au_ll": f("ll"), "au_brier": f("br")}


def gate(base, cand, ids, alfa):
    ids = sorted(ids, key=lambda i: base[i]["dt"])
    by = {}
    for i in ids:
        by.setdefault(base[i]["lg"], []).append(i)
    s1, s2 = [], []
    for lg, xs in by.items():
        h = len(xs) // 2; s1 += xs[:h]; s2 += xs[h:]
    out = {"tum": boot(base, cand, ids), "dilim1": boot(base, cand, s1), "dilim2": boot(base, cand, s2)}
    ok = all(out[k] and out[k]["d_mae_ga"][1] < 0 and out[k]["d_ll_ga"][1] < 0 and out[k]["d_brier"] <= 0
             for k in ("tum", "dilim1", "dilim2")) and out["tum"]["p_ll"] <= alfa and out["tum"]["p_mae"] <= alfa
    out["alfa"] = alfa
    out["gecti"] = bool(ok)
    return out


# ------------------------------------------------------------- ana akış
def load_games():
    store = json.load(open(os.path.join(DATA, "bk_games.json"), encoding="utf-8"))
    bj = json.load(open(os.path.join(DATA, "basket.json"), encoding="utf-8"))
    out = {}
    for lg in ESPN_LG:
        games = store.get(lg, {}).get("g", [])
        P = (bj.get("leagues", {}).get(lg) or {}).get("params")
        if len(games) >= MIN_TRAIN + 30 and P:
            out[lg] = (sorted(games, key=lambda g: g["dt"]), P)
    return out


def main(fetcher=fetch_stats):
    t0 = time.time()
    lgs = load_games()
    res = {"zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "madde": "YH-14",
           "yontem": "haftalık ileri yürüyüş; tempo ve 100 hücum verimi ayrı ridge (basket.fit); alt/üst çizgisi ⌊taban⌋+0,5; "
                     "gün kümeli bootstrap B=2000; kapı: MAE ve A/Ü LL GA üst < 0 (tüm + iki dilim), ΔBrier ≤ 0, p ≤ α/2",
           "lig": {}, "kapsam": {}}
    allsc = {"taban": {}, "tempo": {}, "harman": {}}
    for lg, (games, P) in lgs.items():
        st, nurl, nerr = fetcher(lg, games)
        kinds = {}
        for g in games:
            s = st.get(g["id"])
            p, k = poss_of(s) if s else (None, None)
            if p:
                g["_p"], g["_k"] = p, k; kinds[k] = kinds.get(k, 0) + 1
        kind = max(kinds, key=kinds.get) if kinds else None
        nst = sum(kinds.values())
        res["kapsam"][lg] = {"mac": len(games), "istatistikli": nst, "oran": round(nst / max(1, len(games)), 3),
                             "formul": kind, "istek": nurl, "hata": nerr}
        if not kind or nst < MIN_TRAIN + 30:
            continue
        mean_p = float(np.mean([g["_p"] for g in games if g.get("_k") == kind]))
        rows = walk(games, P, kind)
        sc, w = score(rows)
        ids = set(sc["taban"])
        res["lig"][lg] = {"n": len(ids), "ort_hucum": round(mean_p, 1), "harman_w_ort": w,
                          **{k: summ(sc[k], ids) for k in sc}}
        for k in sc:
            allsc[k].update(sc[k])
        print(lg, res["kapsam"][lg], res["lig"][lg], flush=True)
    ids = set(allsc["taban"])
    res["tum"] = {k: summ(allsc[k], ids) for k in allsc}
    res["kapi"] = {k: gate(allsc["taban"], allsc[k], ids, ALFA / 2) for k in ("tempo", "harman")} if ids else {}
    res["gecti"] = [k for k, v in res["kapi"].items() if v.get("gecti")]
    res["sure_sn"] = round(time.time() - t0)
    for g in (g for lg in lgs.values() for g in lg[0]):
        g.pop("_p", None); g.pop("_k", None)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"tum": res["tum"], "gecti": res["gecti"],
                      "kapi_tum": {k: v.get("tum") for k, v in res["kapi"].items()}}, ensure_ascii=False))
    return res


if __name__ == "__main__":
    main()
