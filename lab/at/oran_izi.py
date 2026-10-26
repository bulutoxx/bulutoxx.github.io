# BULUTOXX at lab — v6: oran izi (erken oran → nihai) harmana bilgi katıyor mu? Walk-forward (aylık), koşu-bootstrap GA.
# python lab/at/oran_izi.py <ayna> iz.json data/at/replay_kosular.json [eşik_dk]
# Oran izi (erken oran -> nihai oran hareketi) harmana bilgi katıyor mu? replay_kosular.json (sızıntısız p_sabah, p_oran)
# + aynanın odds-snapshots (2026-04..06) + git geçmişi oran izi (2026-06..10). Walk-forward (aylık yeniden uydurma).
import json, os, sys, glob, math, collections, datetime as dt
import numpy as np
AYNA, IZ, REPLAY = sys.argv[1], sys.argv[2], sys.argv[3]
ESIK_DK = float(sys.argv[4]) if len(sys.argv) > 4 else 30
def post_ts(t, saat):
    return dt.datetime.fromisoformat(f"{t}T{saat}:00+03:00").timestamp()
# erken oranlar: anahtar -> (ad -> oran) ; ilk görüntü ve post'tan >= ESIK_DK önceki en son görüntü
erken = {}
for f in sorted(glob.glob(os.path.join(AYNA, "data/odds-snapshots/*.jsonl"))):
    per = collections.defaultdict(lambda: collections.defaultdict(dict))
    saat = {}
    for ln in open(f):
        r = json.loads(ln)
        k = f"{r['date']}|{r['venue']}|{r['raceNo']}"
        ts = dt.datetime.fromisoformat(r["ts"].replace("Z", "+00:00")).timestamp()
        per[k][ts][r["name"]] = r["odds"]; saat[k] = r.get("time")
    for k, s in per.items():
        if not saat.get(k): continue
        p = post_ts(k.split("|")[0], saat[k])
        on = [t for t in s if t <= p - ESIK_DK * 60]
        if on:
            erken[k] = ("jsonl", min(on), max(on), s[min(on)], s[max(on)], p)
iz = json.load(open(IZ))
for k, d in iz.items():
    if k in erken or not d.get("saat") or not d.get("t"): continue
    p = post_ts(k.split("|")[0], d["saat"])
    ts = [c for c, _ in d["t"] if c <= p - ESIK_DK * 60]
    if not ts: continue
    def an(c):
        return {a: v for a, l in d["o"].items() for (cc, v) in l if cc == c}
    erken[k] = ("git", min(ts), max(ts), an(min(ts)), an(max(ts)), p)
# sonuçlar: ad -> no, nihai oran
sonuc = {}
for f in glob.glob(os.path.join(AYNA, "data/results/2026-*.json")):
    for r in json.load(open(f)):
        k = f"{r['date']}|{r['venue']}|{r['raceNo']}"
        sonuc[k] = {str(h["no"]): (h["name"], h.get("odds")) for h in r["horses"] if not h.get("nonRunner")}
R = json.load(open(REPLAY))["kosular"]
satir = []
for kr in R:
    k = f"{kr['t']}|{kr['h']}|{kr['k']}"
    if k not in erken or k not in sonuc: continue
    kay, t0, t1, o0, o1, p = erken[k]
    a = kr["a"]
    if any(x[2] is None for x in a): continue
    no2 = sonuc[k]
    try:
        qf = np.array([1 / no2[x[0]][1] for x in a]); qf /= qf.sum()
        e1 = np.array([1 / o1[no2[x[0]][0]] for x in a]); e1 /= e1.sum()
        e0 = np.array([1 / o0[no2[x[0]][0]] for x in a]); e0 /= e0.sum()
    except (KeyError, TypeError, ZeroDivisionError):
        continue
    y = np.array([1.0 if x[3] == 1 else 0.0 for x in a])
    if y.sum() != 1: continue
    satir.append({"k": k, "ay": kr["t"][:7], "kay": kay, "dk": (p - t1) / 60, "ps": np.array([x[1] for x in a]),
                  "po": np.array([x[2] for x in a]), "qf": qf, "e0": e0, "e1": e1, "y": y})
print("koşu:", len(satir), collections.Counter(s["kay"] for s in satir), "ort. dk önce:", np.median([s["dk"] for s in satir]))
def ll(p, y): return -math.log(max(float(p[y > 0][0]), 1e-12))
def sm(z):
    z = z - z.max(); e = np.exp(z); return e / e.sum()
def ozellik(s, tur):
    lpo = np.log(np.clip(s["po"], 1e-12, 1)); lqf = np.log(s["qf"]); le = np.log(s["e1"])
    m = lqf - le
    if tur == "steam": return lpo, np.c_[m]
    if tur == "steam2": return lpo, np.c_[m, m * (lqf > np.log(0.25)), np.maximum(m, 0)]
    if tur == "erken_q": return lpo, np.c_[le - lqf]
    if tur == "sabah": return lpo, np.c_[np.log(np.clip(s["ps"], 1e-12, 1)) - lpo]
def uydur(S, tur, lam=1.0):
    d = ozellik(S[0], tur)[1].shape[1]; w = np.zeros(d)
    for it in range(30):
        g = np.zeros(d); H = lam * np.eye(d)
        for s in S:
            b, X = ozellik(s, tur); p = sm(b + X @ w)
            mu = p @ X; g += X.T @ (s["y"] - p)
            H += (X * p[:, None]).T @ X - np.outer(mu, mu)
        g -= lam * w
        st = np.linalg.solve(H, g); w += st
        if np.abs(st).max() < 1e-6: break
    return w
aylar = sorted({s["ay"] for s in satir})
for tur in ("steam", "steam2", "erken_q", "sabah"):
    d = []; ws = []
    for ay in aylar:
        egit = [s for s in satir if s["ay"] < ay]; test = [s for s in satir if s["ay"] == ay]
        if len(egit) < 200: continue
        w = uydur(egit, tur); ws.append(w)
        for s in test:
            b, X = ozellik(s, tur)
            d.append(ll(sm(b + X @ w), s["y"]) - ll(s["po"], s["y"]))
    d = np.array(d)
    rng = np.random.default_rng(7); bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
    print(tur, "n", len(d), "ΔLL", round(d.mean(), 4), "GA", np.round(np.percentile(bs, [2.5, 97.5]), 4), "w son", np.round(ws[-1], 3) if ws else None)
# referanslar
for ad, f in (("p_oran", "po"), ("q nihai", "qf"), ("q erken", "e1"), ("sabah", "ps")):
    print(ad, round(np.mean([ll(s[f], s["y"]) for s in satir]), 4), "ilk", round(np.mean([s["y"][np.argmax(s[f])] for s in satir]), 4))
