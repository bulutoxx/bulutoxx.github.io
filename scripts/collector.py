"""BULUTOXX veri toplayıcı (kendini geliştirme modülü) — her saat çalışır.

1) Resmi iddaa bülteninden maç başlamadan önceki son oranları ve BULUTOXX önerisini kaydeder (maç başlayınca kilitlenir).
2) Biten maçların sonucunu iddaa sonuç servisinden alıp kayda ekler ve öneriyi puanlar (tuttu / tutmadı).
3) Günlük özet (data/daily.json): "Dün önerilerin %X'i tuttu", güven dilimine ve lige göre isabet.
4) Arşiv (data/archive/GGGG-AA-GG.json): tüm liglerden oran + sonuç verisi; motorun öneri kalibrasyonu ve
   haftalık laboratuvar bu kendi verimizle zamanla daha da isabetli hale gelir.
"""
import json, math, os, sys, glob, collections
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iddaa as ID
import update as U

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data"); ARC = os.path.join(DATA, "archive")
TR = ZoneInfo("Europe/Istanbul")
KEEP_DAYS = 120

def rec_for(ms, ou, rho):
    """Uygulamadaki öneriyle aynı kural: MS 1/X/2 ve 2,5 Alt/Üst içinden en yüksek olasılık."""
    tmp = [dict({"odds": ms}, **({"ou": ou} if ou else {}))]
    U.market_xg(tmp)
    lh, la = tmp[0]["xg"]
    p, pO, pB, _ = U.outcome_probs(np.array([lh]), np.array([la]), rho)
    p = p[0]; pO = float(pO[0])
    c = [("1", float(p[0]), ms[0]), ("X", float(p[1]), ms[1]), ("2", float(p[2]), ms[2])]
    if ou: c += [("U", pO, ou[0]), ("A", 1 - pO, ou[1])]   # alt/üst oranı yoksa gol beklentisi belirsiz: alt/üst önerilmez
    # en olası seçenek önerilir; oranı düşük olsa bile (eski kural oran <1,15 ise favoriyi atlayıp %7'lik seçeneği öneriyordu)
    k, pp, o = max(c, key=lambda x: x[1])
    return {"lam": [lh, la], "p": [round(float(x), 4) for x in p], "o25": round(pO, 4), "kg": round(float(pB[0]), 4), "rk": k, "rp": round(pp, 4), "ro": o}

def hit(rk, hs, as_):
    if rk == "1": return hs > as_
    if rk == "X": return hs == as_
    if rk == "2": return hs < as_
    if rk == "U": return hs + as_ > 2
    if rk == "A": return hs + as_ < 3
    return None

def load_day(d):
    p = os.path.join(ARC, f"{d}.json")
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return {}

def save_day(d, recs):
    os.makedirs(ARC, exist_ok=True)
    json.dump({k: recs[k] for k in sorted(recs)}, open(os.path.join(ARC, f"{d}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# ---------------------------------------------------------------- canlı seçim kaydı (Power Now'un kendi isabetinden öğrenmesi)
LIVE = os.path.join(ARC, "live")

def _pois_cdf(k, l):
    if k < 0: return 0.0
    p = math.exp(-l); c = p
    for i in range(1, k + 1): p *= l / i; c += p
    return min(1.0, c)

def live_pred(lh, la, hs, as_, t, rc, h1=0.4428):
    """Uygulamadaki canlı tahminin aynısı: kalan süre payı + skor durumu + kırmızı kart."""
    rem = ((45 - t) / 45 * h1 + (1 - h1)) if t < 45 else max(.012, (90 - t) / 45 * (1 - h1)) if t <= 90 else max(.012, (120 - t) / 45 * (1 - h1))
    d = hs - as_; st = t >= 15; up, dn = math.exp(.1), math.exp(-.1)
    LH = lh * rem * ((up if d < 0 else dn) if st else 1); LA = la * rem * ((up if d > 0 else dn) if st else 1)
    LH *= .72 ** rc[0] * 1.25 ** rc[1]; LA *= .72 ** rc[1] * 1.25 ** rc[0]
    ph = [math.exp(-LH) * LH ** i / math.factorial(i) for i in range(9)]; pa = [math.exp(-LA) * LA ** j / math.factorial(j) for j in range(9)]
    H = D = A = 0.0
    for i in range(9):
        for j in range(9):
            q = ph[i] * pa[j]
            if hs + i > as_ + j: H += q
            elif hs + i == as_ + j: D += q
            else: A += q
    z = H + D + A; p0 = math.exp(-(LH + LA))
    return {"H": H / z, "D": D / z, "A": A / z, "LT": LH + LA, "none": p0, "nh": (1 - p0) * LH / max(LH + LA, 1e-9), "na": (1 - p0) * LA / max(LH + LA, 1e-9)}

def live_snapshot():
    """O an oynanan maçlarda en yüksek olasılıklı açık oranlı seçimi kaydet (maç dakikası ve skoruyla, kilitli)."""
    import urllib.request
    now = datetime.now(timezone.utc); d = now.astimezone(TR).date().isoformat()
    lam = {}
    for back in (0, 1):
        dd = (now.astimezone(TR).date() - timedelta(days=back)).isoformat()
        for k, r in load_day(dd).items():
            if r.get("lam"): lam[k] = r["lam"]
    try: lam.update({k: v[:2] for k, v in json.load(open(os.path.join(DATA, "iddaa.json"), encoding="utf-8")).get("lam", {}).items() if k not in lam})
    except Exception: pass
    try: h1 = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"].get("h1", .4428)
    except Exception: h1 = .4428
    get = lambda u: json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=ID.UA), timeout=40).read().decode("utf-8")).get("data") or {}
    lr = get("https://statisticsv2.iddaa.com/live-results?sportId=1"); ev = get("https://sportsbookv2.iddaa.com/sportsbook/events?st=1&type=1&version=0")
    sc = lr.get("sc") or {}
    os.makedirs(LIVE, exist_ok=True); fp = os.path.join(LIVE, f"{d}.json")
    try: log = json.load(open(fp, encoding="utf-8"))
    except Exception: log = {}
    n = 0
    for e in (ev.get("events") or []):
        if e.get("s") != 1: continue
        k = str(e["i"]); s = sc.get(k); L = lam.get(k)
        if not s or not L or s.get("min") is None or s.get("s") not in (2, 3): continue
        t = s["min"] + (s.get("sec") or 0) / 60; hs, as_ = int(s["ht"].get("c") or 0), int(s["at"].get("c") or 0)
        rc = [int(s["ht"].get("rc") or 0), int(s["at"].get("rc") or 0)]
        P = live_pred(L[0], L[1], hs, as_, t, rc, h1)
        cands = []
        for m in e.get("m") or []:
            if m.get("s") != 1 or m.get("t") != 4: continue     # yalnız canlı pazarlar
            v = {o.get("n"): o.get("odd") for o in m.get("o") or [] if o.get("odd") and o["odd"] > 1.01}
            if m.get("st") in (4, 1) and all(x in v for x in ("1", "0", "2")):
                cands += [("1", P["H"], v["1"], None), ("X", P["D"], v["0"], None), ("2", P["A"], v["2"], None)]
            elif m.get("st") in (14, 101) and m.get("sov") and "Alt" in v and "Üst" in v:
                line = float(m["sov"]); po = 1 - _pois_cdf(int(math.floor(line)) - (hs + as_), P["LT"])
                cands += [("U" + str(line), po, v["Üst"], line), ("A" + str(line), 1 - po, v["Alt"], line)]
            elif m.get("st") == 34 and all(x in v for x in ("1", "Olmaz", "2")):
                cands += [("G1", P["nh"], v["1"], None), ("G0", P["none"], v["Olmaz"], None), ("G2", P["na"], v["2"], None)]
        cands = [c for c in cands if c[2] >= 1.03]
        if not cands: continue
        b = max(cands, key=lambda c: c[1])
        key = f"{k}-{int(t)}"
        if key in log: continue
        log[key] = {"id": k, "t": round(t, 1), "hs": hs, "as": as_, "rk": b[0], "p": round(b[1], 4), "o": b[2], "c": e.get("ci"), "h": e.get("hn"), "a": e.get("an"),
                    "ts": int(now.timestamp())}   # kayıt anı: canlı kalibrasyonun zaman sıralı sınaması için
        n += 1
    json.dump(log, open(fp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"Canlı kayıt: {n} yeni seçim ({len(log)} bugün)", flush=True)

LIVE_PLATT_LAM, LIVE_PLATT_MIN = 5.0, 300

def _platt_fit(p, y, lam=LIVE_PLATT_LAM, prior=(0.0, 1.0)):
    """Logit doğrusal kalibrasyon q = σ(a + b·logit p); (a, b) önsel (0, 1)'e L2 ile küçültülür (az veride kimliğe yakın kalır)."""
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4); y = np.asarray(y, float); x = np.log(p / (1 - p))
    a, b = prior
    for _ in range(30):
        q = 1 / (1 + np.exp(-(a + b * x))); r = q - y; s = q * (1 - q)
        g = np.array([r.sum() + lam * (a - prior[0]), (r * x).sum() + lam * (b - prior[1])])
        H = np.array([[s.sum() + lam, (s * x).sum()], [(s * x).sum(), (s * x * x).sum() + lam]])
        d = np.linalg.solve(H, g); a -= d[0]; b -= d[1]
        if abs(d).max() < 1e-9: break
    return float(a), float(b)

def _platt(p, ab):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4); return 1 / (1 + np.exp(-(ab[0] + ab[1] * np.log(p / (1 - p)))))

def _bins_cal(p, B, nmin=30, s=50):
    """Uygulamadaki liveCal (index.html) ile aynı: kova isabetine 50'lik küçültme, n≥30."""
    q = np.array(p, float)
    for lo, hi, n, h in B:
        if n >= nmin and h is not None:
            m = (q >= lo) & (q < hi); q[m] = (h * n + q[m] * s) / (n + s)
    return np.minimum(q, .99)

def live_platt(stats, edges):
    """Canlı kalibrasyon adayı: havuz Platt. ZAMAN SIRALI genişleyen pencere: maçlar ilk kayıt anına göre 6 dilime ayrılır,
    k. dilim yalnız önceki dilimlerle öğrenilip sınanır (aynı maçın anlık seçimleri aynı dilimde → sızıntı yok).
    Kabul: birleşik sınamada Brier hem ham hem mevcut kova yönteminden iyi ve dilimlerin çoğunda kova yönteminden iyi.
    Kanıt (2026-10-25, 584 seçim/116 maç, git kayıt saatleriyle): Brier ham 0,2463 · kova 0,2421 · Platt 0,2365; 5/5 dilimde iyi."""
    if len(stats) < LIVE_PLATT_MIN: return {"kabul": False, "n": len(stats), "aciklama": f"en az {LIVE_PLATT_MIN} puanlanmış canlı seçim gerekli"}
    first = {}
    for r in stats:
        o = (r.get("_d", ""), r.get("ts") or 0, str(r["id"]))
        if r["id"] not in first or o < first[r["id"]]: first[r["id"]] = o
    ids = sorted(first, key=first.get); fold = {m: min(5, j * 6 // len(ids)) for j, m in enumerate(ids)}
    def bins_of(rs):
        out = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            s_ = [r for r in rs if lo <= r["p"] < hi]
            out.append([lo, hi, len(s_), sum(r["ok"] for r in s_) / len(s_) if s_ else None])
        return out
    tot = {"ham": [], "kova": [], "platt": []}; ys = []; win = 0; nf = 0
    for k in range(1, 6):
        tr = [r for r in stats if fold[r["id"]] < k]; te = [r for r in stats if fold[r["id"]] == k]
        if len(tr) < 50 or not te: continue
        p = np.array([r["p"] for r in te]); y = np.array([float(r["ok"]) for r in te])
        ab = _platt_fit([r["p"] for r in tr], [float(r["ok"]) for r in tr])
        qk, qp = _bins_cal(p, bins_of(tr)), np.minimum(_platt(p, ab), .99)
        tot["ham"].append(np.minimum(p, .99)); tot["kova"].append(qk); tot["platt"].append(qp); ys.append(y)
        nf += 1; win += float(np.mean((qp - y) ** 2)) < float(np.mean((qk - y) ** 2))
    if not nf: return {"kabul": False, "n": len(stats), "aciklama": "sınama dilimi oluşmadı"}
    y = np.concatenate(ys); B = {k: round(float(np.mean((np.concatenate(v) - y) ** 2)), 5) for k, v in tot.items()}
    ok = B["platt"] < B["kova"] - 1e-4 and B["platt"] < B["ham"] - 1e-4 and win * 2 > nf
    a, b = _platt_fit([r["p"] for r in stats], [float(r["ok"]) for r in stats])
    return {"a": round(a, 4), "b": round(b, 4), "kabul": bool(ok), "n": len(stats), "yontem": "havuz Platt (logit doğrusal, L2 λ=5)",
            "dogrulama": {"sinama_n": int(len(y)), "dilim": nf, "kazanilan_dilim": int(win), "brier_ham": B["ham"], "brier_kova": B["kova"], "brier_platt": B["platt"]},
            "aciklama": "p' = 1/(1+exp(-(a + b·ln(p/(1-p)))))  — kabul ise canlı yüzde bununla düzeltilir (kova yöntemi yerine)"}

def live_grade():
    """Biten maçlarla canlı seçimleri puanla; olasılık dilimine göre gerçek isabet (Power Now kalibrasyonu)."""
    import urllib.request
    now = datetime.now(timezone.utc); stats = []
    for f in sorted(glob.glob(os.path.join(LIVE, "*.json")))[-30:]:
        d = os.path.basename(f)[:10]; log = json.load(open(f, encoding="utf-8")); changed = False
        need = [r for r in log.values() if "ok" not in r]
        if need and d >= (now.astimezone(TR).date() - timedelta(days=2)).isoformat():
            fin = {}
            for back in (0, 1):
                dd = (date.fromisoformat(d) + timedelta(days=back)).isoformat()
                try:
                    data = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://statisticsv2.iddaa.com/live-results?sportId=1&date={dd}", headers=ID.UA), timeout=40).read().decode("utf-8")).get("data") or {}
                except Exception: continue
                ph = {str(e["eventId"]): e.get("phase") for e in data.get("events") or []}
                for k, s_ in (data.get("sc") or {}).items():
                    if ph.get(k) == 2 and s_.get("ht") and s_["ht"].get("c") is not None: fin[k] = (int(s_["ht"]["c"]), int(s_["at"]["c"]))
            for r in need:
                if r["id"] not in fin: continue
                fh, fa = fin[r["id"]]; k = r["rk"]; ok = None
                if k == "1": ok = fh > fa
                elif k == "X": ok = fh == fa
                elif k == "2": ok = fh < fa
                elif k[0] in "UA" and k[1:]: line = float(k[1:]); ok = (fh + fa > line) if k[0] == "U" else (fh + fa < line)
                elif k == "G0": ok = (fh + fa) == (r["hs"] + r["as"])
                elif k in ("G1", "G2"):
                    dh, da = fh - r["hs"], fa - r["as"]
                    if dh + da == 0: ok = False
                    elif dh > 0 and da == 0: ok = k == "G1"
                    elif da > 0 and dh == 0: ok = k == "G2"
                    else: ok = None     # iki takım da attı: ilk golü kimin attığı bilinmiyor
                r["ok"] = ok; changed = True
            if changed: json.dump(log, open(f, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        stats += [dict(r, _d=d) for r in log.values() if r.get("ok") is not None]
    edges = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.01]; bins = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s_ = [r for r in stats if lo <= r["p"] < hi]
        bins.append([lo, hi, len(s_), round(sum(r["ok"] for r in s_) / len(s_), 4) if s_ else None])
    out = {"n": len(stats), "hit": round(sum(r["ok"] for r in stats) / len(stats), 4) if stats else None, "bins": bins}
    # 🎯 Canlı Platt kalibrasyonu (yeni alan, 'bins' biçimi değişmedi): zaman sıralı sınamayı geçerse kabul=true
    try:
        pl = live_platt(stats, edges)
        if pl.get("kabul") and _rollback_frozen("canli_platt"): pl["kabul"] = False; pl["aciklama"] = "Koruyucu geri alma süresince dondurulmuş"
        out["platt"] = pl
    except Exception as ex:
        print("canlı Platt atlandı:", ex.__class__.__name__, ex, flush=True)
    return out

def _rollback_frozen(key):
    """🛡️ Koruyucu geri alma aktifse ve önceki yapılandırmada bu özellik kapalıysa → dondur."""
    try:
        RB = json.load(open(os.path.join(DATA, "rollback.json"), encoding="utf-8"))
        return bool(RB.get("aktif")) and not RB.get(key)
    except Exception: return False

def main():
    now = datetime.now(timezone.utc); nts = now.timestamp()
    try: rho = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"].get("rho", -0.06)
    except Exception: rho = -0.06
    # 1) maç öncesi kayıt (başlamamış maçlar güncellenir; başlayınca son hali kilitli kalır)
    days = {}
    def day_of(ts): return datetime.fromtimestamp(ts, timezone.utc).astimezone(TR).date().isoformat()
    n_pre = 0
    try:
        evs = ID.fetch(1, days=2)
        for e in evs:
            if e["ts"] <= nts: continue
            d = day_of(e["ts"]); recs = days.setdefault(d, load_day(d)); k = str(e["iid"])
            r = recs.get(k, {})
            if r.get("hs") is not None: continue
            try: rr = rec_for(e["mk"]["ms"], e["mk"].get("ou"), rho)
            except Exception: continue
            r.update({"ts": e["ts"], "c": e["comp"], "cc": e["cc"], "h": e["h"], "a": e["a"], "ms": e["mk"]["ms"], "ou": e["mk"].get("ou"),
                      "kgo": e["mk"].get("kg"), "mbs": e.get("mbc")}, **rr)
            recs[k] = r; n_pre += 1
    except Exception as ex:
        print("bülten alınamadı:", ex.__class__.__name__, ex, flush=True)
    # 2) sonuçlar: dün ve bugün
    n_res = 0
    for back in (2, 1, 0):
        d = (now.astimezone(TR).date() - timedelta(days=back)).isoformat()
        try:
            import urllib.request
            req = urllib.request.Request(f"https://statisticsv2.iddaa.com/live-results?sportId=1&date={d}", headers=ID.UA)
            j = json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8")); data = j.get("data") or {}
        except Exception as ex:
            print("sonuç alınamadı", d, ex.__class__.__name__, flush=True); continue
        recs = days.setdefault(d, load_day(d)); sc = data.get("sc") or {}
        for ev in data.get("events") or []:
            if ev.get("phase") != 2: continue
            k = str(ev["eventId"]); r = recs.get(k)
            s = sc.get(k)
            if not r or not s or not s.get("ht") or s["ht"].get("c") is None: continue
            if r.get("hs") is not None: continue
            r["hs"], r["as"] = int(s["ht"]["c"]), int(s["at"]["c"])
            if s["ht"].get("ht") is not None: r["h1"], r["a1"] = s["ht"]["ht"], s["at"]["ht"]
            r["ok"] = hit(r.get("rk"), r["hs"], r["as"]); n_res += 1
    for d, recs in days.items(): save_day(d, recs)
    # eski arşivleri temizle
    cut = (now.astimezone(TR).date() - timedelta(days=KEEP_DAYS)).isoformat()
    for f in glob.glob(os.path.join(ARC, "*.json")):
        if os.path.basename(f)[:10] < cut: os.remove(f)
    # 3) günlük özet
    summ = []
    for f in sorted(glob.glob(os.path.join(ARC, "*.json")))[-30:]:
        d = os.path.basename(f)[:10]; recs = json.load(open(f, encoding="utf-8"))
        g = [r for r in recs.values() if r.get("ok") is not None]
        if not g: summ.append({"d": d, "n": 0, "kayit": len(recs)}); continue
        tiers = {"guclu": [r for r in g if r["rp"] >= .70], "oneri": [r for r in g if .58 <= r["rp"] < .70], "riskli": [r for r in g if r["rp"] < .58]}
        top = sorted([r for r in tiers["guclu"] if r["ok"]], key=lambda r: -r["rp"])[:5]
        NM = {"1": "MS 1", "X": "MS X", "2": "MS 2", "U": "2,5 Üst", "A": "2,5 Alt"}
        summ.append({"d": d, "n": len(g), "kayit": len(recs), "hit": round(sum(r["ok"] for r in g) / len(g), 4),
                     **{k: {"n": len(v), "hit": round(sum(r["ok"] for r in v) / len(v), 4) if v else None} for k, v in tiers.items()},
                     "ornek": [{"h": r["h"], "a": r["a"], "s": f"{r['hs']}-{r['as']}", "o": NM.get(r["rk"], r["rk"]), "p": r["rp"], "odd": r.get("ro")} for r in top]})
    allg = [r for f in glob.glob(os.path.join(ARC, "*.json")) for r in json.load(open(f, encoding="utf-8")).values() if r.get("ok") is not None]
    out = {"updated": now.strftime("%Y-%m-%dT%H:%MZ"), "gunler": summ,
           "toplam": {"n": len(allg), "hit": round(sum(r["ok"] for r in allg) / len(allg), 4) if allg else None,
                      "guclu_n": sum(1 for r in allg if r["rp"] >= .7), "guclu_hit": (round(sum(r["ok"] for r in allg if r["rp"] >= .7) / max(1, sum(1 for r in allg if r["rp"] >= .7)), 4))}}
    try: live_snapshot()
    except Exception as ex: print("canlı kayıt atlandı:", ex.__class__.__name__, ex, flush=True)
    try: out["canli"] = live_grade()
    except Exception as ex: print("canlı puanlama atlandı:", ex.__class__.__name__, ex, flush=True)
    json.dump(out, open(os.path.join(DATA, "daily.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"Toplayıcı: {n_pre} maç öncesi kayıt, {n_res} sonuç işlendi; arşivde {len(allg)} puanlanmış öneri", flush=True)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "live":      # 15 dakikada bir: yalnız canlı seçim kaydı
        try: live_snapshot()
        except Exception as e: print("canlı kayıt hata:", e)
        sys.exit(0)
    try: main()
    except Exception as e:
        import traceback; traceback.print_exc(); print("toplayıcı hata verdi, sonraki saatte tekrar denenecek")
