#!/usr/bin/env python3
"""BULUTOXX basketbol isabet laboratuvarı (ağsız, yalnız repodaki veri).

Ölçer:
  * kilitli tahmin günlüğü (data/bk_predlog.json) sonuçlananlar: isabet, log-loss, Brier
  * ileriye dönük haftalık geriye dönük test (her maç yalnız ondan önceki maçlarla): pazar ve lig bazında
    MS (kazanan) isabet/log-loss/Brier/kalibrasyon kovaları, handikap (fark) ve toplam sayı hataları
Dener (en fazla 3 aday), kapı:
  * log-loss Δ ve Brier Δ < 0, log-loss Δ için gün kümeli eşleştirilmiş bootstrap %95 GA üst sınırı < 0
  * isabet düşmemeli; iki zaman diliminin (her ligin ilk / ikinci yarısı) ikisinde de
Çıktı: data/bk_gelistir.json (türetilmiş özet, ham maç verisi içermez).
Kullanım: python3 lab/bk_gelistir.py
"""
import json, math, os, sys
from datetime import date, datetime, timedelta
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import basket as B  # noqa: E402

DATA = os.path.join(ROOT, "data")
REF = date(2026, 10, 26)          # verinin anlık görüntü tarihi (All-Star süzgeci için)
MIN_PRIOR = 60                    # olasılık ölçeği için gereken önceki tahmin sayısı
RNG = np.random.default_rng(20261026)


def d_of(g):
    return datetime.fromisoformat(g["dt"].replace("Z", "+00:00")).date()


def load():
    store = json.load(open(os.path.join(DATA, "bk_games.json"), encoding="utf-8"))
    bj = json.load(open(os.path.join(DATA, "basket.json"), encoding="utf-8"))
    out = {}
    for lg, (src, *_r) in B.LEAGUES.items():
        games = store.get(lg, {}).get("g", [])
        cnt, lastd = {}, {}
        for g in games:
            for t in (g["h"], g["a"]):
                cnt[t] = cnt.get(t, 0) + 1; lastd[t] = g["dt"]
        if src == "espn":
            cut = (REF - timedelta(days=60)).isoformat()
            bad = {t for t, c in cnt.items() if c < 5 and lastd[t][:10] < cut}
            games = [g for g in games if g["h"] not in bad and g["a"] not in bad]
        if len(games) < 40 or lg not in bj.get("leagues", {}):
            continue
        out[lg] = (games, bj["leagues"][lg]["params"], bj["leagues"][lg])
    return out, bj


# ------------------------------------------------------------- model çeşitleri
def fit_v(games, ref, P, hca_joint=False, carry=None):
    """basket.fit ile aynı; seçenekler:
    hca_joint: ev avantajı takım güçleriyle birlikte (ridge içinde) kestirilir
    carry: sezon arası: önceki sezon maçlarının yaşı tatil süresi kadar kısaltılır ve ağırlık carry ile çarpılır"""
    if carry is None and not hca_joint:
        return B.fit(games, ref, P, joint=False)          # üretimdeki eski yol (ham ev avantajı)
    if carry is None and hca_joint:
        return B.fit(games, ref, P, joint=True)           # üretime bağlanan yol (aynı kod)
    if len(games) < 20:
        return None
    teams = sorted({g["h"] for g in games} | {g["a"] for g in games}); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
    ages = np.array([max(0, B.days(g, ref)) for g in games], float)
    mult = np.ones(len(games))
    if carry is not None:
        ds = [d_of(g) for g in games]
        start, gap = None, 0
        for i in range(1, len(ds)):
            gg = (ds[i] - ds[i - 1]).days
            if gg >= 45: start, gap = ds[i], gg
        if start is not None:
            prev = np.array([d < start for d in ds])
            ages = np.where(prev, np.maximum(0, ages - gap), ages)
            mult = np.where(prev, carry, 1.0)
    w = mult * np.exp(-P["decay"] * ages)
    hs = np.array([g["hs"] for g in games], float); as_ = np.array([g["as_"] for g in games], float)
    neu = np.array([g.get("neutral", False) for g in games])
    mu = float(np.sum(w * (hs + as_)) / (2 * np.sum(w)))
    hi = np.array([ix[g["h"]] for g in games]); ai = np.array([ix[g["a"]] for g in games])
    if not hca_joint:
        hca = float(np.sum(w[~neu] * (hs - as_)[~neu]) / max(1e-9, np.sum(w[~neu]))) if (~neu).any() else 0.0
        hcaH = np.where(neu, 0, hca / 2); hcaA = np.where(neu, 0, -hca / 2)
        yh = hs - mu - hcaH; ya = as_ - mu - hcaA
        M = np.zeros((2 * n, 2 * n)); b = np.zeros(2 * n)
        for (o, d, y) in ((hi, ai, yh), (ai, hi, ya)):
            oi, di = o, n + d
            np.add.at(M, (oi, oi), w); np.add.at(M, (di, di), w); np.add.at(M, (oi, di), w); np.add.at(M, (di, oi), w)
            np.add.at(b, oi, w * y); np.add.at(b, di, w * y)
        M[np.diag_indices(2 * n)] += P["lam"]
        x = np.linalg.solve(M, b)
        return {"teams": teams, "ix": ix, "off": x[:n], "def": x[n:2 * n], "mu": mu, "hca": hca}
    # ortak kestirim: bilinmeyenler off(n), def(n), hca (1); hca'ya çok küçük ceza
    K = 2 * n + 1; M = np.zeros((K, K)); b = np.zeros(K)
    c = np.where(neu, 0.0, 0.5)
    for (o, d, y, s) in ((hi, ai, hs - mu, c), (ai, hi, as_ - mu, -c)):
        oi, di = o, n + d; hh = np.full(len(o), 2 * n)
        for (r1, r2, v) in ((oi, oi, w), (di, di, w), (oi, di, w), (di, oi, w),
                            (oi, hh, w * s), (hh, oi, w * s), (di, hh, w * s), (hh, di, w * s), (hh, hh, w * s * s)):
            np.add.at(M, (r1, r2), v)
        np.add.at(b, oi, w * y); np.add.at(b, di, w * y); np.add.at(b, hh, w * s * y)
    M[np.diag_indices(2 * n)] += P["lam"]; M[2 * n, 2 * n] += 1e-3
    x = np.linalg.solve(M, b)
    return {"teams": teams, "ix": ix, "off": x[:n], "def": x[n:2 * n], "mu": mu, "hca": float(x[2 * n])}


def backtest_v(games, P, min_train, **kw):
    """basket.backtest ile aynı haftalık ileri yürüyüş; satır: (maç, ev bekl., dep bekl., hafta)."""
    if len(games) < min_train + 30:
        return []
    dts = [d_of(g) for g in games]
    wk, last = dts[min_train], dts[-1]
    rows = []
    while wk <= last:
        nxt = wk + timedelta(days=7)
        train = [g for g, d in zip(games, dts) if d < wk and (wk - d).days <= 400]
        test = [g for g, d in zip(games, dts) if wk <= d < nxt]
        if test and len(train) >= min_train:
            F = fit_v(train, wk, P, **kw)
            for g in test:
                pm = B.pred_means(F, g["h"], g["a"], g.get("neutral", False), P.get("newp"))
                if pm:
                    rows.append((g, pm[0], pm[1], wk))
        wk = nxt
    return rows


# ------------------------------------------------------------- olasılık ve ölçüler
try:
    from scipy.special import ndtr as phi_v          # hızlı; yoksa math.erf ile aynı sonuç
except Exception:
    def phi_v(x):
        return 0.5 * (1 + np.vectorize(math.erf)(np.asarray(x, float) / math.sqrt(2)))


def sigma_ll(m, y):
    """Φ(m/σ) için log-loss'u en küçük yapan σ (ızgara)."""
    best, bs = None, 12.0
    for s in np.arange(6.0, 30.01, 0.1):
        p = np.clip(phi_v(m / s), 1e-6, 1 - 1e-6)
        ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        if best is None or ll < best:
            best, bs = ll, float(s)
    return bs


def probs(rows, mode):
    """Her hafta için σ yalnız o haftadan ÖNCE sonuçlanmış tahminlerden.
    mode 'std': üretimdeki gibi fark hatasının std'si; 'll': log-loss'u en iyi yapan σ."""
    out = {}
    weeks = sorted({r[3] for r in rows})
    for wk in weeks:
        prior = [r for r in rows if r[3] < wk]
        if len(prior) < MIN_PRIOR:
            continue
        m = np.array([r[1] - r[2] for r in prior]); real = np.array([r[0]["hs"] - r[0]["as_"] for r in prior], float)
        if mode == "std":
            s = float(np.std(real - m))
        else:
            s = sigma_ll(m, (real > 0).astype(float))
        for r in rows:
            if r[3] == wk:
                out[r[0]["id"]] = float(phi_v((r[1] - r[2]) / s))
    return out


def per_game(rows, pmap):
    """id -> (p, y, doğru, gün, mae_fark, mae_toplam)"""
    res = {}
    for g, mh, ma, wk in rows:
        if g["id"] not in pmap:
            continue
        p = min(max(pmap[g["id"]], 1e-6), 1 - 1e-6); y = 1.0 if g["hs"] > g["as_"] else 0.0
        res[g["id"]] = {"p": p, "y": y, "ll": -(y * math.log(p) + (1 - y) * math.log(1 - p)), "br": (p - y) ** 2,
                        "acc": 1.0 if (mh > ma) == (y == 1.0) else 0.0, "day": g["dt"][:10],
                        "em": abs((g["hs"] - g["as_"]) - (mh - ma)), "et": abs((g["hs"] + g["as_"]) - (mh + ma))}
    return res


def summary(pg):
    if not pg:
        return None
    a = list(pg.values())
    f = lambda k: float(np.mean([x[k] for x in a]))
    return {"n": len(a), "isabet": round(f("acc"), 4), "logloss": round(f("ll"), 4), "brier": round(f("br"), 4),
            "mae_fark": round(f("em"), 2), "mae_toplam": round(f("et"), 2)}


def buckets(pg):
    """Favori olasılığı kovaları: ortalama tahmin vs gerçekleşen."""
    edges = [.5, .6, .7, .8, .9, 1.0001]
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        xs = [(max(x["p"], 1 - x["p"]), x["y"] if x["p"] >= .5 else 1 - x["y"]) for x in pg.values() if lo <= max(x["p"], 1 - x["p"]) < hi]
        if xs:
            out.append({"kova": f"{int(lo*100)}-{min(100,int(hi*100))}", "n": len(xs),
                        "tahmin": round(float(np.mean([p for p, _ in xs])), 3), "gercek": round(float(np.mean([o for _, o in xs])), 3)})
    return out


def boot(base, cand, ids, B_=2000):
    """Gün kümeli eşleştirilmiş bootstrap: Δ = aday - mevcut."""
    days = {}
    for i in ids:
        days.setdefault(base[i]["day"], []).append(i)
    keys = list(days)
    D = {k: (np.array([cand[i]["ll"] - base[i]["ll"] for i in days[k]]).sum(),
             np.array([cand[i]["br"] - base[i]["br"] for i in days[k]]).sum(),
             np.array([cand[i]["acc"] - base[i]["acc"] for i in days[k]]).sum(), len(days[k])) for k in keys}
    arr = np.array([D[k] for k in keys])
    n = len(keys)
    pt = arr.sum(0); pt = pt[:3] / pt[3]
    sims = []
    for _ in range(B_):
        s = arr[RNG.integers(0, n, n)].sum(0)
        sims.append(s[:3] / s[3])
    sims = np.array(sims)
    lo, hi = np.percentile(sims, [2.5, 97.5], axis=0)
    r = lambda v: round(float(v), 5)
    return {"n": len(ids), "d_ll": r(pt[0]), "d_ll_ga": [r(lo[0]), r(hi[0])], "d_brier": r(pt[1]), "d_brier_ga": [r(lo[1]), r(hi[1])],
            "d_isabet": r(pt[2]), "d_isabet_ga": [r(lo[2]), r(hi[2])]}


def slices(rows_by_lg, ids):
    """İki zaman dilimi: her ligin ileriye dönük maçlarının kronolojik ilk ve ikinci yarısı."""
    s1, s2 = set(), set()
    for lg, rows in rows_by_lg.items():
        rr = sorted([r for r in rows if r[0]["id"] in ids], key=lambda r: r[0]["dt"])
        h = len(rr) // 2
        s1 |= {r[0]["id"] for r in rr[:h]}; s2 |= {r[0]["id"] for r in rr[h:]}
    return s1, s2


def gate(base, cand, rows_by_lg):
    ids = set(base) & set(cand)
    s1, s2 = slices(rows_by_lg, ids)
    out = {"tum": boot(base, cand, ids), "dilim1": boot(base, cand, s1), "dilim2": boot(base, cand, s2)}
    ok = all(out[k]["d_ll_ga"][1] < 0 and out[k]["d_brier"] < 0 and out[k]["d_isabet"] >= 0 for k in ("dilim1", "dilim2", "tum"))
    out["gecti"] = bool(ok)
    return out


# ------------------------------------------------------------- kilitli günlük
def predlog_report(bj):
    pl = json.load(open(os.path.join(DATA, "bk_predlog.json"), encoding="utf-8"))
    done = [e for e in pl if e.get("r")]
    res = {"toplam": len(pl), "sonuclanan": len(done), "bekleyen": len(pl) - len(done), "lig": {}}
    def st(es):
        if not es:
            return None
        acc, ll, br, mt, mm = [], [], [], [], []
        for e in es:
            L = bj["leagues"].get(e["lg"], {}); sm = L.get("sm", 12.0)
            p = min(max(float(phi_v((e["ph"] - e["pa"]) / sm)), 1e-6), 1 - 1e-6); y = 1.0 if e["r"][0] > e["r"][1] else 0.0
            acc.append((e["ph"] > e["pa"]) == (y == 1)); ll.append(-(y * math.log(p) + (1 - y) * math.log(1 - p))); br.append((p - y) ** 2)
            mt.append(abs(sum(e["r"]) - (e["ph"] + e["pa"]))); mm.append(abs((e["r"][0] - e["r"][1]) - (e["ph"] - e["pa"])))
        accs = np.array(acc, float)
        bs = [accs[RNG.integers(0, len(accs), len(accs))].mean() for _ in range(2000)]
        return {"n": len(es), "isabet": round(float(accs.mean()), 4), "isabet_ga": [round(float(x), 3) for x in np.percentile(bs, [2.5, 97.5])],
                "logloss": round(float(np.mean(ll)), 4), "brier": round(float(np.mean(br)), 4),
                "mae_fark": round(float(np.mean(mm)), 2), "mae_toplam": round(float(np.mean(mt)), 2)}
    res["tum"] = st(done)
    for lg in sorted({e["lg"] for e in done}):
        res["lig"][lg] = st([e for e in done if e["lg"] == lg])
    od = [e for e in done if e.get("odds") and e["odds"].get("spread") is not None and e["odds"].get("ou")]
    if od:
        pa = np.mean([((e["ph"] > e["pa"]) == (e["r"][0] > e["r"][1])) for e in od])
        ma = np.mean([((-e["odds"]["spread"]) > 0) == (e["r"][0] > e["r"][1]) for e in od if e["odds"]["spread"] != 0])
        res["oranli"] = {"n": len(od), "model_isabet": round(float(pa), 4), "piyasa_isabet": round(float(ma), 4),
                         "model_mae_toplam": round(float(np.mean([abs(sum(e["r"]) - e["ph"] - e["pa"]) for e in od])), 2),
                         "piyasa_mae_toplam": round(float(np.mean([abs(sum(e["r"]) - e["odds"]["ou"]) for e in od])), 2)}
    return res


# ------------------------------------------------------------- ana akış
def main():
    data, bj = load()
    rep = {"tarih": REF.isoformat(), "yontem": "haftalık ileri yürüyüş; her maç yalnız önceki maçlarla; σ yalnız önceki haftaların tahminlerinden",
           "kapi": "log-loss Δ GA üst < 0, Brier Δ < 0, isabet Δ ≥ 0; tüm + iki zaman dilimi", "predlog": predlog_report(bj)}
    variants = {"mevcut": {}, "B_ortak_hca": {"hca_joint": True}}
    for c in (0.25, 0.5, 1.0):
        variants[f"C_sezon_tasima_{c}"] = {"carry": c}
    rows = {v: {} for v in variants}
    for lg, (games, P, L) in data.items():
        mt = 200 if lg in ("ncaa", "ncaaw") else 80
        for v, kw in variants.items():
            rows[v][lg] = backtest_v(games, P, mt, **kw)
        print(lg, {v: len(rows[v][lg]) for v in variants}, flush=True)
    pg = {}
    for v in variants:
        pg[v] = {}
        for lg in data:
            pg[v].update(per_game(rows[v][lg], probs(rows[v][lg], "std")))
    # bağlanan biçim: ortak ev avantajı yalnız kolej liglerinde (dengesiz iç saha takvimi); diğer ligler aynen mevcut
    pg["B_ortak_hca_kolej"] = {}
    for lg in data:
        src = "B_ortak_hca" if lg in B.HCA_JOINT else "mevcut"
        pg["B_ortak_hca_kolej"].update(per_game(rows[src][lg], probs(rows[src][lg], "std")))
    pg["A_sigma_logloss"] = {}
    for lg in data:
        pg["A_sigma_logloss"].update(per_game(rows["mevcut"][lg], probs(rows["mevcut"][lg], "ll")))

    lg_of = {g[0]["id"]: lg for lg in data for g in rows["mevcut"][lg]}
    def by_lg(p):
        return {lg: summary({i: x for i, x in p.items() if lg_of.get(i) == lg}) for lg in data}
    rep["mevcut"] = {"tum": summary(pg["mevcut"]), "lig": by_lg(pg["mevcut"]), "kalibrasyon": buckets(pg["mevcut"]),
                     "kalibrasyon_lig": {lg: buckets({i: x for i, x in pg["mevcut"].items() if lg_of.get(i) == lg}) for lg in data},
                     "uretim_sm": {lg: L["sm"] for lg, (_, _, L) in data.items()}}
    rep["adaylar"] = {}
    for v in pg:
        if v == "mevcut":
            continue
        gt = gate(pg["mevcut"], pg[v], rows["mevcut"])
        gt["ozet"] = summary({i: x for i, x in pg[v].items() if i in pg["mevcut"]})
        gt["lig"] = {}
        for lg in data:
            ids = {i for i in pg["mevcut"] if lg_of.get(i) == lg and i in pg[v]}
            if ids:
                gt["lig"][lg] = boot(pg["mevcut"], pg[v], ids, 500)
        if v == "A_sigma_logloss":
            gt["kalibrasyon"] = buckets(pg[v])
            gt["sm_ll_tum"] = {lg: round(sigma_ll(np.array([r[1] - r[2] for r in rows["mevcut"][lg]]),
                                                  np.array([float(r[0]["hs"] > r[0]["as_"]) for r in rows["mevcut"][lg]])), 2) for lg in data}
        rep["adaylar"][v] = gt
        print(v, json.dumps({k: gt[k] for k in ("tum", "dilim1", "dilim2", "gecti")}, ensure_ascii=False), flush=True)
    json.dump(rep, open(os.path.join(DATA, "bk_gelistir.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(rep["mevcut"]["tum"], ensure_ascii=False))


if __name__ == "__main__":
    main()
