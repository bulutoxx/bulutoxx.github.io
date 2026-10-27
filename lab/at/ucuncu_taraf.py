# OXXai at lab — v6: aynadaki üçüncü taraf tahmin günlüğü (memory/predictions, git'te ilk sabah sürümü) yığma testi.
# python lab/at/ucuncu_taraf.py <blobless ayna klonu> pred_ilk.txt data/at/replay_kosular.json
# Aynadaki üçüncü taraf tahmin günlüğü (memory/predictions, git'te İLK sürüm, sabah) sabah modelimize bilgi katıyor mu?
import json, sys, subprocess, math, collections, datetime as dt
import numpy as np
REPO, ILK, REPLAY = sys.argv[1:4]
R = {f"{k['t']}|{k['h']}|{k['k']}": k for k in json.load(open(REPLAY))["kosular"]}
satir = []; zam = collections.Counter()
for ln in open(ILK):
    t, ct, oid = ln.split(); ct = int(ct)
    if t <= "2026-06-12": continue
    d = json.loads(subprocess.check_output(["git", "-C", REPO, "cat-file", "-p", oid]))
    saat = (dt.datetime.fromtimestamp(ct, dt.timezone.utc) + dt.timedelta(hours=3))
    zam[saat.hour] += 1
    for r in d.get("racePredictions") or []:
        k = f"{t}|{r['venue']}|{r['raceNo']}"
        if k not in R or not r.get("time"): continue
        post = dt.datetime.fromisoformat(f"{t}T{r['time']}:00+03:00").timestamp()
        if ct > post - 30 * 60: continue
        c = {x["no"]: x["probability"] / 100 for x in r.get("contenders") or []}
        a = R[k]["a"]
        y = np.array([1.0 if x[3] == 1 else 0.0 for x in a])
        if y.sum() != 1 or not c: continue
        kalan = max(1e-3, 1 - sum(c.values())); nk = sum(1 for x in a if x[0] not in c)
        u = np.array([c.get(x[0], kalan / max(nk, 1)) for x in a]); u = np.clip(u, 1e-3, 1); u /= u.sum()
        satir.append({"ay": t[:7], "ps": np.array([x[1] for x in a]), "u": u, "y": y,
                      "po": np.array([x[2] if x[2] else x[1] for x in a]), "top": np.array([1.0 if x[0] in c else 0.0 for x in a])})
print("saat dağılımı", sorted(zam.items()), "koşu", len(satir))
def sm(z): z = z - z.max(); e = np.exp(z); return e / e.sum()
def ll(p, y): return -math.log(max(float(p[y > 0][0]), 1e-12))
def X(s): return np.c_[np.log(s["ps"]), np.log(s["u"]), s["top"]]
def uydur(S, lam=1.0):
    w = np.array([1.0, 0.0, 0.0])
    for _ in range(30):
        g = -lam * (w - [1, 0, 0]); H = lam * np.eye(3)
        for s in S:
            x = X(s); p = sm(x @ w); mu = p @ x
            g += x.T @ (s["y"] - p); H += (x * p[:, None]).T @ x - np.outer(mu, mu)
        st = np.linalg.solve(H, g); w += st
        if abs(st).max() < 1e-7: break
    return w
aylar = sorted({s["ay"] for s in satir}); d = []; ilk = []
for ay in aylar[1:]:
    w = uydur([s for s in satir if s["ay"] < ay])
    for s in [s for s in satir if s["ay"] == ay]:
        p = sm(X(s) @ w); d.append(ll(p, s["y"]) - ll(s["ps"], s["y"])); ilk.append(s["y"][np.argmax(p)] - s["y"][np.argmax(s["ps"])])
d = np.array(d); rng = np.random.default_rng(7)
print("ΔLL sabah+ucuncu − sabah", round(d.mean(), 4), np.round(np.percentile([d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)], [2.5, 97.5]), 4), "Δilk", round(np.mean(ilk), 4), "w", np.round(w, 3))
print("LL sabah", round(np.mean([ll(s['ps'], s['y']) for s in satir]), 4), "üçüncü", round(np.mean([ll(s['u'], s['y']) for s in satir]), 4),
      "ilk sabah", round(np.mean([s['y'][np.argmax(s['ps'])] for s in satir]), 4), "ilk üçüncü", round(np.mean([s['y'][np.argmax(s['u'])] for s in satir]), 4))
