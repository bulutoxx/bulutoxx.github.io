#!/usr/bin/env python3
"""BULUTOXX uzun vade araştırması: maçları 90 gün önceden tahmin et, hatalardan öğren, tekrar test et.

Protokol
  1. Taban: geçen sezonun (2025-26 / 2025) her maçını, yalnızca maçtan 90 gün ÖNCESİNE kadar oynanmış maçlarla
     eğitilen mevcut motorla tahmin et. Sonuçla karşılaştır.
  2. Hata analizi: kalibrasyon, yükselen (veride olmayan) takımlar, sezon başı, lig, favori gücü, beraberlik, gol seviyesi.
  3. Yeni yetenekler (aday): ortalamaya çekme, yeni takım önseli, alt lig verisinden taşıma, zaman ağırlığı,
     beraberlik düzeltmesi (rho), olasılık sıcaklığı. Yalnız geçen sezonda ayarlanır.
  4. Doğrulama: bu sezonun (2026-27 / 2026) maçlarında, AYAR DEĞİŞTİRMEDEN aynı test.
  5. Ayrıca kısa vade (1 hafta önce) testinde de bozulma olmadığını kontrol et.
Çıktı: research/r90.json, research/r90.log
"""
import csv, io, json, math, os, sys, time
from datetime import date, timedelta
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update as U

OUT = os.path.join(U.ROOT, "research"); os.makedirs(OUT, exist_ok=True)
CACHE = os.path.join(OUT, "cache"); os.makedirs(CACHE, exist_ok=True)
LOG = open(os.path.join(OUT, "r90.log"), "w", encoding="utf-8")
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n"); LOG.flush()

# Alt lig → üst lig (yükselen takımın alt lig gücünü taşımak için)
LOWER = {"en": "en2", "en2": "en3", "en3": "en4", "en4": "en5", "de": "de2", "it": "it2", "es": "es2", "fr": "fr2",
         "sc": "sc2", "sc2": "sc3", "sc3": "sc4"}

# ------------------------------------------------------------------ veri
def load_all():
    p = os.path.join(CACHE, "all.json")
    if os.path.exists(p): return json.load(open(p, encoding="utf-8"))
    allm = {}
    for lg, (kind, code, name) in U.LEAGUES.items():
        ms = []
        try:
            if kind == "new":
                ms = U.download_new(lg, [], "2022-01-01")
            else:
                known = []
                for c, sy in (("2223", 2022), ("2324", 2023), ("2425", 2024), ("2526", 2025), ("2627", 2026)):
                    try:
                        got = U.download(lg, c, sy, known)
                        known = sorted(set(known) | {m["h"] for m in got} | {m["a"] for m in got}); ms += got
                    except Exception as e:
                        log("  indirme yok", lg, c, e)
        except Exception as e:
            log("HATA", lg, e)
        ms = U.merge([], ms)
        U.market_xg(ms)
        allm[lg] = ms
        log(f"{lg}: {len(ms)} maç, sezonlar {sorted({m['season'] for m in ms})}")
    json.dump(allm, open(p, "w", encoding="utf-8"), separators=(",", ":"))
    return allm

# ------------------------------------------------------------------ tahmin çekirdeği
FIT_CACHE = {}
def get_fit(lg, ms, cut, P):
    key = (lg, cut, P["decay"], P["prior"], P["mkt"])
    if key in FIT_CACHE: return FIT_CACHE[key]
    lo = (date.fromisoformat(cut) - timedelta(days=730)).isoformat()
    train = [m for m in ms if lo <= m["d"] < cut]
    f = None
    if len(train) >= 60:
        f = U.fit(train, date.fromisoformat(cut), P, iters=30)
        last = {}
        for m in train: last[m["h"]] = m["d"]; last[m["a"]] = m["d"]
        f["last"] = last
        f["n"] = len(train)
    FIT_CACHE[key] = f
    return f

def monday(d):
    dd = date.fromisoformat(d); return (dd - timedelta(days=dd.weekday())).isoformat()

def build(allm, test_season, horizon, P):
    """Her test maçı için (ham) model girdilerini topla. Ölçek dönüşümleri sonra ucuzca uygulanır."""
    rows = []
    for lg, ms in allm.items():
        test = [m for m in ms if m["season"] == test_season]
        if len(test) < 30: continue
        for m in test:
            cut = monday((date.fromisoformat(m["d"]) - timedelta(days=horizon)).isoformat())
            f = get_fit(lg, ms, cut, P)
            if not f: continue
            # alt lig verisi (yükselen takım için)
            fl = get_fit(LOWER[lg], allm.get(LOWER[lg], []), cut, P) if lg in LOWER and LOWER[lg] in allm else None
            def team(t):
                if t in f["t"]:
                    age = (date.fromisoformat(cut) - date.fromisoformat(f["last"][t])).days
                    return ("known", f["t"][t], age)
                if fl and t in fl["t"]:
                    return ("lower", fl["t"][t], 0)
                return ("new", (1.0, 1.0), 0)
            th, ta = team(m["h"]), team(m["a"])
            dd = date.fromisoformat(m["d"])
            # sezon içi sıra: sezonun ilk 6 haftası mı?
            rows.append({"lg": lg, "m": m, "mu": f["mu"], "gamma": f["gamma"], "h": th, "a": ta,
                         "flmu": fl["mu"] if fl else None, "early": None, "d": m["d"]})
    # sezon başı işareti
    first = {}
    for r in rows: first[r["lg"]] = min(first.get(r["lg"], r["d"]), r["d"])
    for r in rows: r["early"] = (date.fromisoformat(r["d"]) - date.fromisoformat(first[r["lg"]])).days < 42
    return rows

def lambdas(rows, Q):
    """Ölçek dönüşümleri: ortalamaya çekme (s), yeni takım önseli (pa,pd), alt lig taşıma faktörü (lf)."""
    lh = np.empty(len(rows)); la = np.empty(len(rows))
    s = Q["shrink"]
    for i, r in enumerate(rows):
        def tr(x):
            kind, (a, d), age = x
            if kind == "known":
                return a ** s, d ** s
            if kind == "lower":
                if Q["lower"] <= 0: return Q["pa"], Q["pd"]
                # alt lig gücü + lig farkı: alt ligde ortalama takım üst ligde pa/pd seviyesinde başlar
                return (Q["pa"] * a ** (s * Q["lower"]), Q["pd"] * d ** (s * Q["lower"]))
            return Q["pa"], Q["pd"]
        ah, dh = tr(r["h"]); aa, da = tr(r["a"])
        lh[i] = r["mu"] * r["gamma"] * ah * da; la[i] = r["mu"] * aa * dh
    return lh, la

def evaluate(rows, Q, detail=False):
    lh, la = lambdas(rows, Q)
    p, pO, pB, g = U.outcome_probs(lh, la, Q["rho"])
    if Q.get("temp", 1.0) != 1.0:
        p = p ** Q["temp"]; p /= p.sum(1, keepdims=True)
    if Q.get("draw", 0.0):
        p[:, 1] *= (1 + Q["draw"]); p /= p.sum(1, keepdims=True)
    res = np.array([0 if r["m"]["ft"][0] > r["m"]["ft"][1] else 1 if r["m"]["ft"][0] == r["m"]["ft"][1] else 2 for r in rows])
    tot = np.array([sum(r["m"]["ft"]) for r in rows]); bt = np.array([r["m"]["ft"][0] > 0 and r["m"]["ft"][1] > 0 for r in rows])
    n = len(rows)
    ll = float(-np.log(np.maximum(p[np.arange(n), res], 1e-9)).mean())
    llo = float(-np.mean(np.where(tot > 2, np.log(np.maximum(pO, 1e-9)), np.log(np.maximum(1 - pO, 1e-9)))))
    out = {"n": n, "logloss": round(ll, 4), "ll_ou": round(llo, 4),
           "brier": round(float(((p - np.eye(3)[res]) ** 2).sum(1).mean()), 4),
           "r1x2": round(float((p.argmax(1) == res).mean()), 4),
           "ou25": round(float(((pO >= .5) == (tot > 2)).mean()), 4),
           "btts": round(float(((pB >= .5) == bt).mean()), 4)}
    if detail:
        C = U.pick_scores(g, p, pO)
        out["exact"] = round(float(np.mean([C[i] == tuple(r["m"]["ft"]) for i, r in enumerate(rows)])), 4)
        out["_p"], out["_pO"], out["_res"], out["_tot"], out["_lh"], out["_la"] = p, pO, res, tot, lh, la
    return out

def score(e): return e["logloss"] + 0.5 * e["ll_ou"]

def market_ref(rows):
    mk = [(i, r) for i, r in enumerate(rows) if r["m"].get("odds")]
    if not mk: return None
    res = np.array([0 if r["m"]["ft"][0] > r["m"]["ft"][1] else 1 if r["m"]["ft"][0] == r["m"]["ft"][1] else 2 for _, r in mk])
    inv = np.array([[1 / o for o in r["m"]["odds"]] for _, r in mk]); inv /= inv.sum(1, keepdims=True)
    return {"n": len(mk), "logloss": round(float(-np.log(inv[np.arange(len(mk)), res]).mean()), 4),
            "r1x2": round(float((inv.argmax(1) == res).mean()), 4), "idx": [i for i, _ in mk]}

# ------------------------------------------------------------------ hata analizi
def analysis(rows, e):
    p, pO, res, tot, lh, la = e["_p"], e["_pO"], e["_res"], e["_tot"], e["_lh"], e["_la"]
    n = len(rows); A = {}
    def grp(mask, name):
        if mask.sum() < 30: return
        ll = float(-np.log(np.maximum(p[mask][np.arange(mask.sum()), res[mask]], 1e-9)).mean())
        A[name] = {"n": int(mask.sum()), "logloss": round(ll, 4), "r1x2": round(float((p[mask].argmax(1) == res[mask]).mean()), 4),
                   "draw_pred": round(float(p[mask][:, 1].mean()), 4), "draw_real": round(float((res[mask] == 1).mean()), 4),
                   "goals_pred": round(float((lh + la)[mask].mean()), 3), "goals_real": round(float(tot[mask].mean()), 3),
                   "home_pred": round(float(p[mask][:, 0].mean()), 4), "home_real": round(float((res[mask] == 0).mean()), 4)}
    kinds = np.array([(r["h"][0], r["a"][0]) for r in rows])
    grp(np.ones(n, bool), "tümü")
    grp((kinds[:, 0] == "known") & (kinds[:, 1] == "known"), "iki takım da biliniyor")
    grp((kinds[:, 0] != "known") | (kinds[:, 1] != "known"), "yükselen/yeni takım var")
    grp(np.array([r["early"] for r in rows]), "sezonun ilk 6 haftası")
    grp(~np.array([r["early"] for r in rows]), "sezonun geri kalanı")
    fav = p.max(1)
    for lo, hi in ((0, .45), (.45, .55), (.55, .65), (.65, .75), (.75, 1.01)):
        m = (fav >= lo) & (fav < hi)
        if m.sum() >= 30:
            A[f"favori %{int(lo*100)}-{int(min(hi,1)*100)}"] = {"n": int(m.sum()), "tahmin": round(float(fav[m].mean()), 4),
                                                                 "gerçek": round(float((p[m].argmax(1) == res[m]).mean()), 4)}
    by = {}
    for i, r in enumerate(rows): by.setdefault(r["lg"], []).append(i)
    L = {}
    for lg, ix in by.items():
        ix = np.array(ix)
        L[lg] = {"n": len(ix), "r1x2": round(float((p[ix].argmax(1) == res[ix]).mean()), 4),
                 "logloss": round(float(-np.log(np.maximum(p[ix, res[ix]], 1e-9)).mean()), 4),
                 "goal_bias": round(float((lh + la)[ix].mean() - tot[ix].mean()), 3),
                 "draw_bias": round(float(p[ix, 1].mean() - (res[ix] == 1).mean()), 4)}
    A["ligler"] = L
    return A

# ------------------------------------------------------------------ ayar arama
def search(rows_by_P, base_Q):
    """Koordinat iniş. Fit ayarları (decay/prior) satır kümesini değiştirir; diğerleri ucuz dönüşümler."""
    grid = {"shrink": [1.0, .95, .9, .85, .8, .75, .7, .6],
            "pa": [1.0, .95, .9, .85, .8, .75, .7], "pd": [1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.4],
            "lower": [0.0, .3, .5, .7, 1.0], "rho": [0.0, -.03, -.06, -.09, -.12, -.15],
            "temp": [1.1, 1.0, .95, .9, .85, .8, .75], "draw": [0.0, .03, .06, .1, .15]}
    best_key, Q = None, dict(base_Q)
    best = None
    for key, rows in rows_by_P.items():
        s = score(evaluate(rows, Q))
        if best is None or s < best: best, best_key = s, key
    for it in range(3):
        changed = False
        for k, vals in grid.items():
            for v in vals:
                Q2 = dict(Q, **{k: v}); s = score(evaluate(rows_by_P[best_key], Q2))
                if s < best - 1e-5: best, Q, changed = s, Q2, True
        for key, rows in rows_by_P.items():
            s = score(evaluate(rows, Q))
            if s < best - 1e-5: best, best_key, changed = s, key, True
        log(f"  tur {it+1}: puan {best:.4f}, fit {best_key}, ayar {Q}")
        if not changed: break
    return best_key, Q

def strip(e): return {k: v for k, v in e.items() if not k.startswith("_")}

# ------------------------------------------------------------------ ana akış
def main():
    t0 = time.time()
    allm = load_all()
    M = json.load(open(os.path.join(U.DATA, "model.json"), encoding="utf-8")); P0 = dict(M["params"])
    log("Mevcut motor ayarları:", P0)
    BASE_Q = {"shrink": 1.0, "pa": 1.0, "pd": 1.0, "lower": 0.0, "rho": P0["rho"], "temp": 1.0, "draw": 0.0}
    H = 90
    R = {"protocol": "Her maç, yalnızca maç tarihinden 90 gün önceye kadar oynanmış maçlarla eğitilen modelle tahmin edildi.",
         "horizon": H}

    # 1) TABAN: geçen sezon, mevcut motor
    log("\n=== 1) TABAN: geçen sezon (2025) 90 gün önceden, mevcut motor ===")
    rows = build(allm, 2025, H, P0)
    base = evaluate(rows, BASE_Q, detail=True)
    mk = market_ref(rows)
    R["base_last"] = strip(base); R["market_last"] = {k: v for k, v in (mk or {}).items() if k != "idx"}
    log("Taban:", strip(base)); log("Piyasa (maç günü kapanış oranı, üst sınır):", R["market_last"])

    # 2) HATA ANALİZİ
    log("\n=== 2) HATA ANALİZİ ===")
    A = analysis(rows, base); R["analysis_base"] = A
    for k, v in A.items():
        if k != "ligler": log(f"  {k}: {v}")
    worst = sorted(A["ligler"].items(), key=lambda kv: -kv[1]["logloss"])[:6]
    log("  En zor ligler:", worst)

    # 3) YENİ YETENEKLER: fit ayarları (zaman ağırlığı, önsel) × dönüşümler
    log("\n=== 3) YENİ YETENEKLER: ayar arama (yalnız geçen sezonda) ===")
    rows_by_P = {}
    for dec in (0.004, 0.008, 0.012, P0["decay"]):
        for pr in (P0["prior"], 1.0, 3.0):
            P = dict(P0, decay=dec, prior=pr); key = f"decay={dec},prior={pr}"
            rows_by_P[key] = build(allm, 2025, H, P)
    best_key, Q = search(rows_by_P, BASE_Q)
    dec = float(best_key.split(",")[0].split("=")[1]); pr = float(best_key.split(",")[1].split("=")[1])
    P1 = dict(P0, decay=dec, prior=pr)
    new_last = evaluate(rows_by_P[best_key], Q, detail=True)
    R["new_params"] = {"fit": {"decay": dec, "prior": pr}, "Q": Q}
    R["new_last"] = strip(new_last); R["analysis_new"] = analysis(rows_by_P[best_key], new_last)
    log("Yeni (geçen sezon):", strip(new_last))
    # her yeteneğin tek başına katkısı (ablation)
    abl = {}
    for k in ("shrink", "pa", "pd", "lower", "rho", "temp", "draw"):
        Qk = dict(Q, **{k: BASE_Q[k]}); e = evaluate(rows_by_P[best_key], Qk)
        abl[k] = round(e["logloss"] - new_last["logloss"], 4)
    e = evaluate(rows_by_P[f"decay={P0['decay']},prior={P0['prior']}"], Q); abl["decay/prior"] = round(e["logloss"] - new_last["logloss"], 4)
    R["ablation"] = abl; log("Yetenek çıkarılınca log-loss artışı (büyük = önemli):", abl)

    # 4) DOĞRULAMA: bu sezon, ayar değiştirmeden
    log("\n=== 4) DOĞRULAMA: bu sezon (2026), ayar değiştirmeden ===")
    rows26b = build(allm, 2026, H, P0); rows26n = build(allm, 2026, H, P1)
    b26 = evaluate(rows26b, BASE_Q, detail=True); n26 = evaluate(rows26n, Q, detail=True)
    mk26 = market_ref(rows26b)
    R["base_this"] = strip(b26); R["new_this"] = strip(n26); R["market_this"] = {k: v for k, v in (mk26 or {}).items() if k != "idx"}
    log("Taban (bu sezon):", strip(b26)); log("Yeni (bu sezon):", strip(n26)); log("Piyasa:", R["market_this"])

    # 5) KISA VADE kontrolü (7 gün önce): yeni yetenekler yakın maçları bozmuyor mu?
    log("\n=== 5) KISA VADE (7 gün) kontrolü, bu sezon ===")
    FIT_CACHE.clear()
    s7b = evaluate(build(allm, 2026, 7, P0), BASE_Q, detail=True)
    s7n = evaluate(build(allm, 2026, 7, P1), Q, detail=True)
    # kısa vadede yalnız yeni takım önseli + rho + sıcaklık (ortalamaya çekme uzun vadeye özgü olabilir)
    Qs = dict(Q, shrink=1.0)
    s7m = evaluate(build(allm, 2026, 7, P0), dict(Qs), detail=True)
    R["short_base"] = strip(s7b); R["short_new"] = strip(s7n); R["short_mixed"] = strip(s7m)
    log("7 gün taban:", strip(s7b)); log("7 gün yeni (tüm yetenekler):", strip(s7n)); log("7 gün karma (çekme yok, eski zaman ağırlığı):", strip(s7m))

    # karar
    ok_long = n26["logloss"] < b26["logloss"]
    cand = {"full": s7n["logloss"], "mixed": s7m["logloss"], "base": s7b["logloss"]}
    short_choice = min(cand, key=cand.get)
    R["decision"] = {"long_horizon_improves_this_season": bool(ok_long), "short_choice": short_choice,
                     "long_params": {"decay": dec, "prior": pr, **Q}, "short_params": ({"decay": dec, "prior": pr, **Q} if short_choice == "full" else
                                                                                       {"decay": P0["decay"], "prior": P0["prior"], **Qs} if short_choice == "mixed" else
                                                                                       {"decay": P0["decay"], "prior": P0["prior"], **BASE_Q})}
    log("\nKARAR:", R["decision"])
    R["seconds"] = round(time.time() - t0)
    json.dump(R, open(os.path.join(OUT, "r90.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"Bitti, {R['seconds']} sn")

if __name__ == "__main__":
    main()
