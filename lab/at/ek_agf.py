# OXXai at lab — v6b: Ek kaynak A'nın zaman damgalı AGF görüntüleri piyasa harmanına bilgi katıyor mu?
# SIZINTI KURALI: AGF yalnız koşu saatinden en az ESIK_DK önce yakalanmış görüntüden alınır (harman koşuya ≤15 dk kala
# devreye girer; o andan sonraki görüntü kullanılmaz). Sabah kilidi yalnız modeldir (lab/at/kilit.py) — AGF sabah
# modeline GİRMEZ. Taban: replay_kosular.json'daki sızıntısız p_oran (model + piyasa harmanı).
# Değerlendirme: gün dışarıda bırakmalı (leave-one-day-out) koşullu logit [log p_oran, log agf], koşu-bootstrap %95 GA.
#   AT_EK_YOL=<yerel ek kaynak> python lab/at/ek_agf.py <ayna> <replay_kosular.json> [eşik_dk=15]
import csv, glob, gzip, json, math, os, sys, collections, datetime as dt
import numpy as np

EK, AYNA, REPLAY = os.environ["AT_EK_YOL"], sys.argv[1], sys.argv[2]
ESIK_DK = float(sys.argv[3]) if len(sys.argv) > 3 else 15
HIP = {"istanbul": "İstanbul", "izmir": "İzmir", "adana": "Adana", "bursa": "Bursa", "ankara": "Ankara",
       "sanliurfa": "Şanlıurfa", "antalya": "Antalya", "elazig": "Elazığ", "kocaeli": "Kocaeli", "diyarbakir": "Diyarbakır"}


def dk(s):
    h, m = s.split(":")[:2]
    return int(h) * 60 + int(m)


saat = {}
for f in glob.glob(os.path.join(AYNA, "data/daily/2026-10-*.json")):
    for r in json.load(open(f, encoding="utf-8")):
        if r.get("time"):
            saat[(r["date"], r["venue"], int(r["raceNo"]))] = dk(r["time"])
agf = collections.defaultdict(dict)   # (t,h,k) -> {no: (yakalama dk, agf)}  en son UYGUN görüntü
for f in sorted(glob.glob(os.path.join(EK, "data/agf_zaman/*.csv.gz"))):
    t = os.path.basename(f)[:10]
    for r in csv.DictReader(gzip.open(f, "rt", encoding="utf-8")):
        h = HIP.get(r["hipodrom"])
        k = (t, h, int(r["kosu"]))
        if k not in saat:
            continue
        y = dk(r["saat"])
        if y > saat[k] - ESIK_DK:      # koşuya ESIK_DK'dan az kala ya da sonra yakalanmış: KULLANILMAZ
            continue
        try:
            v = float(r["agf"])
        except ValueError:
            continue
        eski = agf[k].get(r["no"])
        if eski is None or y >= eski[0]:
            agf[k][r["no"]] = (y, v)
R = json.load(open(REPLAY, encoding="utf-8"))["kosular"]
satir = []
for kr in R:
    k = (kr["t"], kr["h"], kr["k"])
    if k not in agf:
        continue
    a = kr["a"]
    if any(x[2] is None for x in a):
        continue
    g = [agf[k].get(str(x[0])) for x in a]
    if sum(1 for x in g if x) < max(2, math.ceil(0.8 * len(a))):
        continue
    u = np.array([max(x[1], 0.1) if x else 0.5 for x in g]); u /= u.sum()
    y = np.array([1.0 if x[3] == 1 else 0.0 for x in a])
    if y.sum() != 1:
        continue
    satir.append({"gun": kr["t"], "po": np.array([x[2] for x in a]), "u": u, "y": y,
                  "once": np.mean([saat[k] - x[0] for x in g if x])})
print("koşu:", len(satir), "gün:", len({s["gun"] for s in satir}), "AGF yakalama, koşudan ort. dk önce:",
      round(float(np.mean([s["once"] for s in satir])), 1) if satir else None)


def sm(z):
    z = z - z.max(); e = np.exp(z); return e / e.sum()


def ll(p, y):
    return -math.log(max(float(p[y > 0][0]), 1e-12))


def X(s):
    return np.c_[np.log(np.clip(s["po"], 1e-9, 1)), np.log(s["u"])]


def uydur(S, lam=1.0):
    w = np.array([1.0, 0.0])
    for _ in range(40):
        g = -lam * (w - [1, 0]); H = lam * np.eye(2)
        for s in S:
            x = X(s); p = sm(x @ w); mu = p @ x
            g += x.T @ (s["y"] - p); H += (x * p[:, None]).T @ x - np.outer(mu, mu)
        st = np.linalg.solve(H, g); w += st
        if abs(st).max() < 1e-7:
            break
    return w


d, di, ws = [], [], []
for gun in sorted({s["gun"] for s in satir}):
    w = uydur([s for s in satir if s["gun"] != gun]); ws.append(w)
    for s in [s for s in satir if s["gun"] == gun]:
        p = sm(X(s) @ w)
        d.append(ll(p, s["y"]) - ll(s["po"], s["y"]))
        di.append(s["y"][np.argmax(p)] - s["y"][np.argmax(s["po"])])
out = {"ad": f"AGF (≥{ESIK_DK:g} dk önce yakalanan) p_oran'a ek", "kosu": len(d)}
if d:
    d = np.array(d); rng = np.random.default_rng(7)
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
    ga = np.percentile(bs, [2.5, 97.5])
    out.update({"dll": round(float(d.mean()), 4), "ga95": [round(float(ga[0]), 4), round(float(ga[1]), 4)],
                "d_ilk": round(float(np.mean(di)), 4), "w_ort": [round(float(x), 3) for x in np.mean(ws, 0)],
                "ll_p_oran": round(float(np.mean([ll(s["po"], s["y"]) for s in satir])), 4),
                "ll_agf": round(float(np.mean([ll(s["u"], s["y"]) for s in satir])), 4),
                "gecti": bool(ga[1] < 0 and np.mean(di) >= 0)})
print(json.dumps(out, ensure_ascii=False))
