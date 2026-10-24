"""Konsey uygulayıcı (motorun parçası): Robot arenası (lab/arena.py) bir pazarda piyasayı iki sezonda da geçtiyse
o pazar için robotların birleşik tahmini yaklaşan maçlara otomatik eklenir (fixtures.json: kp = [1, X, 2], ko = 2,5 üst).
Onay beklemez; Koruyucu bot sonrasını izler ve isabet düşerse geri alır."""
import json, math, os, collections
from datetime import date, timedelta
import numpy as np
import update as U

def _pp(lh, la, rho):
    p, pO, _, _ = U.outcome_probs(np.array([lh]), np.array([la]), rho); return p[0], float(pO[0])

def apply(fx, season, P, today):
    try: A = json.load(open(os.path.join(U.DATA, "arena.json"), encoding="utf-8")).get("uygula") or {}
    except Exception: return 0
    w1, w2, We = A.get("1x2"), A.get("ou"), A.get("elo_W")
    if not (w1 or w2) or not We: return 0
    We = np.array(We); rho = P.get("rho", -0.06); n = 0
    by = collections.defaultdict(list)
    for f in fx:
        if f.get("odds") and f.get("lg") in season and not season[f["lg"]].get("cup"): by[f["lg"]].append(f)
    for lg, fl in by.items():
        ms = sorted([m for m in season[lg]["matches"] if m.get("ft")], key=lambda m: m["d"])
        if len(ms) < 120: continue
        elo = collections.defaultdict(lambda: 1500.0); hist = collections.defaultdict(list); mom = collections.defaultdict(list)
        for m in ms:
            a, b = m["ft"]; de = elo[m["h"]] + 60 - elo[m["a"]]; ex = 1 / (1 + 10 ** (-de / 400)); sc = 1 if a > b else .5 if a == b else 0
            k = 20 * (1 + abs(a - b)) ** .5; elo[m["h"]] += k * (sc - ex); elo[m["a"]] -= k * (sc - ex)
            hist[m["h"]].append((a, b)); hist[m["a"]].append((b, a))
            if m.get("xg"): mom[m["h"]].append(a - m["xg"][0]); mom[m["a"]].append(b - m["xg"][1])
        train = [m for m in ms if m["d"] >= (today - timedelta(days=540)).isoformat()]
        if len(train) < 80: continue
        F = U.fit(train, today, P, iters=20)
        for f in fl:
            if f["h"] not in F["t"] or f["a"] not in F["t"] or len(hist[f["h"]]) < 3 or len(hist[f["a"]]) < 3: continue
            U.market_xg([f])
            pm = U.devig(f["odds"], U._devig_method()); om = float(U.devig(f["ou"], U._devig_method())[0]) if f.get("ou") else None
            (ah, dh), (aa, da) = F["t"][f["h"]], F["t"][f["a"]]
            pP, oP = _pp(F["mu"] * F["gamma"] * ah * da, F["mu"] * aa * dh, rho)
            hh, ha = hist[f["h"]][-6:], hist[f["a"]][-6:]
            fh = (np.mean([x[0] for x in hh]) + np.mean([x[1] for x in ha])) / 2; fa = (np.mean([x[0] for x in ha]) + np.mean([x[1] for x in hh])) / 2
            pF, oF = _pp(max(fh, .2), max(fa, .2), rho)
            xg = f.get("xg") or [1.4, 1.1]; mh = np.mean(mom[f["h"]][-6:]) if mom[f["h"]] else 0; ma = np.mean(mom[f["a"]][-6:]) if mom[f["a"]] else 0
            pM, oM = _pp(max(xg[0] * math.exp(.25 * mh), .2), max(xg[1] * math.exp(.25 * ma), .2), rho)
            e = (elo[f["h"]] + 60 - elo[f["a"]]) / 400; z = np.array([1, e, e * e]) @ We; pE = np.exp(z - z.max()); pE /= pE.sum()
            if w1:
                L = sum(w1[k] * np.log(np.maximum(v, 1e-6)) for k, v in (("Piyasa", pm), ("Poisson", pP), ("Form", pF), ("Momentum", pM), ("Elo", pE)))
                q = np.exp(L - L.max()); q /= q.sum(); f["kp"] = [round(float(x), 4) for x in q]; n += 1
            if w2 and om is not None:
                lg_ = lambda p: math.log(max(p, 1e-6)) - math.log(max(1 - p, 1e-6))
                z2 = sum(w2[k] * lg_(v) for k, v in (("Piyasa", om), ("Poisson", oP), ("Form", oF), ("Momentum", oM)))
                f["ko"] = round(1 / (1 + math.exp(-z2)), 4)
    return n
