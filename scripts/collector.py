"""OXXai veri toplayıcı (kendini geliştirme modülü) — her saat çalışır.

1) Resmi iddaa bülteninden maç başlamadan önceki son oranları ve OXXai önerisini kaydeder (maç başlayınca kilitlenir).
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
import arsiv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data"); ARC = os.path.join(DATA, "archive")
TR = ZoneInfo("Europe/Istanbul")
KEEP_DAYS = 120

def rec_for(ms, ou, rho):
    """Uygulamadaki öneriyle aynı kural: MS 1/X/2 ve 2,5 Alt/Üst içinden en yüksek olasılık.
    Not (ml70): arşivdeki 'rp' bilerek kalibrasyonsuz (ham piyasa) tutulur; kilitli 605 iddaa önerisinde calT/gscale/dk
    uygulamak log-loss'u kötüleştirdi (0,6719 → 0,6755). Koruyucu ve analist bu ham ölçeği izler."""
    tmp = [dict({"odds": ms}, **({"ou": ou} if ou else {}))]
    U.market_xg(tmp)
    lh, la = tmp[0]["xg"]
    p, pO, pB, _ = U.outcome_probs(np.array([lh]), np.array([la]), rho)
    p = p[0]; pO = float(pO[0])
    c = [("1", float(p[0]), ms[0]), ("X", float(p[1]), ms[1]), ("2", float(p[2]), ms[2])]
    if ou: c += [("U", pO, ou[0]), ("A", 1 - pO, ou[1])]   # alt/üst oranı yoksa gol beklentisi belirsiz: alt/üst önerilmez
    # en olası seçenek önerilir; oranı düşük olsa bile (eski kural oran <1,15 ise favoriyi atlayıp %7'lik seçeneği öneriyordu)
    k, pp, o = max(c, key=lambda x: x[1])
    out = {"lam": [lh, la], "p": [round(float(x), 4) for x in p], "o25": round(pO, 4), "kg": round(float(pB[0]), 4), "rk": k, "rp": round(pp, 4), "ro": o}
    try: out.update(served_pick(ms, ou))
    except Exception: pass
    return out

_SRV_P = None
def served_pick(ms, ou):
    """ml80: uygulamanın GÖSTERDİĞİ öneri (piyasa yolu: power marj → gol tablosu → iki yarı Dixon-Coles → calT/gscale/dk,
    model.json'daki o anki ayarlarla). 'sk' seçenek, 'sp' olasılık; sonuçta 'sok' puanlanır. 'rp' (ham ölçek) değişmeden kalır;
    koruyucu kalibrasyon değişikliklerini artık 'sp' ile izleyebilir (rp bu ayarlardan etkilenmiyordu)."""
    global _SRV_P
    if _SRV_P is None:
        try: _SRV_P = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"]
        except Exception: _SRV_P = {}
    P = _SRV_P; rho = P.get("rho", -0.06)
    lam = U.ui_market_lam([ms], [ou], rho)
    p, O = U.served_probs(lam[:, 0], lam[:, 1], P.get("gscale", 1.0), rho, P.get("h1", .4442))
    q = U._cal3(p, P.get("calT", 1.0), P.get("dk", 1.0))[0]; O = float(O[0])
    c = [("1", q[0]), ("X", q[1]), ("2", q[2])] + ([("U", O), ("A", 1 - O)] if ou else [])
    k, pp = max(c, key=lambda x: x[1])
    return {"sk": k, "sp": round(float(pp), 4)}

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

def live_pred(lh, la, hs, as_, t, rc, h1=0.4428, pd=None, Z=None):
    """Uygulamadaki canlı tahminin aynısı (canli-gt-v107 core + canli-dr-v117 remShare): kalan süre payı + skor durumu + kırmızı kart.
    Kalan süre tek kaynaktan: canli_istat.rem_lams (pd: devre 1/2/0=devre arası; Z: daily.json → canli.zaman, None → eski model)."""
    import canli_istat as CI
    LH, LA = CI.rem_lams(lh, la, hs, as_, t, rc, h1, pd, Z)
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
    import canli_istat as CI
    Z = CI.zaman(DATA)                                   # v117: kabul edilmiş kalan süre modeli (yoksa eski model)
    get = lambda u: json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=ID.UA), timeout=40).read().decode("utf-8")).get("data") or {}
    lr = get("https://statisticsv2.iddaa.com/live-results?sportId=1"); ev = get("https://sportsbookv2.iddaa.com/sportsbook/events?st=1&type=1&version=0")
    sc = lr.get("sc") or {}
    os.makedirs(LIVE, exist_ok=True); fp = os.path.join(LIVE, f"{d}.json")
    try: log = json.load(open(fp, encoding="utf-8"))
    except Exception: log = {}
    n = 0; st_c = []
    for e in (ev.get("events") or []):
        if e.get("s") != 1: continue
        k = str(e["i"]); s = sc.get(k); L = lam.get(k)
        if not s or not L or s.get("min") is None or s.get("s") not in (2, 3, 49): continue      # 49 = devre arası
        pd = CI.period_of(s.get("s"))
        t = 45.0 if pd == 0 else s["min"] + (s.get("sec") or 0) / 60; hs, as_ = int(s["ht"].get("c") or 0), int(s["at"].get("c") or 0)
        rc = [int(s["ht"].get("rc") or 0), int(s["at"].get("rc") or 0)]
        P = live_pred(L[0], L[1], hs, as_, t, rc, h1, pd, Z)
        st_c.append({"id": k, "t": t, "pd": pd, "hs": hs, "as": as_, "rc": rc, "lam": [float(L[0]), float(L[1])], "h": e.get("hn") or "", "a": e.get("an") or ""})
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
                    "ts": int(now.timestamp()),    # kayıt anı: canlı kalibrasyonun zaman sıralı sınaması için
                    "pd": pd, "rc": rc, "lam": [round(float(L[0]), 4), round(float(L[1]), 4)], "mv": 117 if Z else 0}   # v117: yeniden hesap için   # kayıt anı: canlı kalibrasyonun zaman sıralı sınaması için
        n += 1
    json.dump(log, open(fp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"Canlı kayıt: {n} yeni seçim ({len(log)} bugün)", flush=True)
    try: live_stats_snapshot(st_c, h1, now, Z=Z)
    except Exception as ex: print("canlı istatistik atlandı:", ex.__class__.__name__, flush=True)

# ---------------------------------------------------------------- v107 · canlı istatistik anlık görüntüsü (gelecekte kalibrasyon için)
LIVE_ST = os.path.join(ARC, "live_stats")
LIVE_ST_MAX, LIVE_ST_KEEP = 800, 90          # gün başına en çok kayıt · tutulan gün sayısı

def live_stats_snapshot(cands, h1, now, espn=None, Z=None):
    """ESPN'den erişilebiliyorsa oynanan maçların istatistik anlık görüntüsü + ayarsız (p0) ve ayarlı (p1) olasılık.
    Yalnız türetilmiş sayılar yazılır (ham API yanıtı yok). Ağ yoksa ya da eşleşme yoksa sessizce atlar."""
    import canli_istat as CI
    if not cands: return 0
    E = CI.espn_live() if espn is None else espn
    if not E: return 0                                    # ağ yok / ESPN erişilemedi → sessiz
    C = CI.coef(DATA); d = now.astimezone(TR).date().isoformat()
    os.makedirs(LIVE_ST, exist_ok=True); fp = os.path.join(LIVE_ST, f"{d}.json")
    try: log = json.load(open(fp, encoding="utf-8"))
    except Exception: log = {}
    n = 0; r4 = lambda x: round(x, 4)
    for c in cands:
        if len(log) >= LIVE_ST_MAX: break
        m = CI.best_match(E, c["h"], c["a"])
        if not m: continue
        key = f"{c['id']}-{int(c['t'])}"
        if key in log: continue
        prev = None                                          # aynı maçın 8–20 dk önceki kaydı (son dönem isabetli şut farkı)
        for r in log.values():
            if r.get("id") == c["id"] and 8 <= c["t"] - r.get("t", -99) <= 20 and (prev is None or r["t"] < prev["t"]): prev = r
        F = CI.feats(m["st"], prev and prev.get("st"), c["lam"], c["t"], C)
        mH, mA = CI.mult(F, C)
        LH, LA = CI.rem_lams(c["lam"][0], c["lam"][1], c["hs"], c["as"], c["t"], c["rc"], h1, c.get("pd"), Z)
        p0, p1 = CI.probs(LH, LA, c["hs"], c["as"]), CI.probs(LH * mH, LA * mA, c["hs"], c["as"])
        K = ("H", "D", "A", "r05", "kg")
        log[key] = {"id": c["id"], "e": m["e"], "lg": m["lg"], "ts": int(now.timestamp()), "t": round(c["t"], 1), "pd": c.get("pd"), "mv": 117 if Z else 0, "hs": c["hs"], "as": c["as"], "rc": c["rc"],
                    "lam": [r4(c["lam"][0]), r4(c["lam"][1])], "L0": [r4(LH), r4(LA)], "st": m["st"],
                    "f": {k: (None if v is None else r4(v)) for k, v in F.items()}, "k": C["kappa"], "m": [r4(mH), r4(mA)],
                    "p0": [r4(p0[k]) for k in K], "p1": [r4(p1[k]) for k in K]}
        n += 1
    if n:
        json.dump(log, open(fp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        for old in sorted(glob.glob(os.path.join(LIVE_ST, "*.json")))[:-LIVE_ST_KEEP]: os.remove(old)
    print(f"Canlı istatistik: {n} yeni anlık görüntü ({len(log)} bugün)", flush=True)
    return n

def live_stats_grade():
    """Biten maçların son skorunu (fh, fa) istatistik kayıtlarına ekle — lab/canli_istat_lab.py ileriye dönük sınar."""
    import urllib.request
    now = datetime.now(timezone.utc); n = 0
    for f in sorted(glob.glob(os.path.join(LIVE_ST, "*.json")))[-3:]:
        d = os.path.basename(f)[:10]
        try: log = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        need = [r for r in log.values() if "fh" not in r]
        if not need or d < (now.astimezone(TR).date() - timedelta(days=2)).isoformat(): continue
        fin = {}
        for back in (0, 1):
            dd = (date.fromisoformat(d) + timedelta(days=back)).isoformat()
            try:
                data = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://statisticsv2.iddaa.com/live-results?sportId=1&date={dd}", headers=ID.UA), timeout=40).read().decode("utf-8")).get("data") or {}
            except Exception: continue
            ph = {str(e["eventId"]): e.get("phase") for e in data.get("events") or []}
            for k, s_ in (data.get("sc") or {}).items():
                if ph.get(k) == 2 and s_.get("ht") and s_["ht"].get("c") is not None: fin[k] = (int(s_["ht"]["c"]), int(s_["at"]["c"]))
        k0 = n
        for r in need:
            if r["id"] in fin: r["fh"], r["fa"] = fin[r["id"]]; n += 1
        if n > k0: json.dump(log, open(f, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return n

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

# ---------------------------------------------------------------- v117 · canlı kalan süre modeli kapısı (eski doğrusal ↔ uzatma + artan yoğunluk)
def _live_lam_map():
    """Canlı kayıtların maç öncesi gol beklentileri (arşiv günleri + iddaa.json); yeni kayıtlar lam'ı kendisi taşır."""
    lam = {}
    for f in sorted(glob.glob(os.path.join(ARC, "*.json"))):
        try:
            for k, r in json.load(open(f, encoding="utf-8")).items():
                if isinstance(r, dict) and r.get("lam"): lam[k] = r["lam"]
        except Exception: pass
    try: lam.update({k: v[:2] for k, v in json.load(open(os.path.join(DATA, "iddaa.json"), encoding="utf-8")).get("lam", {}).items() if k not in lam})
    except Exception: pass
    return lam

def _infer_pd(stats):
    """Eski kayıtlarda devre (pd) yok: 45–50. dakikalar ilk yarı uzatması mı ikinci yarı başı mı? Aynı maçın kesin kayıtlarından
    başlama anı kestirilir (ilk yarı: ts − t·60; ikinci yarı referansı aynı ölçüyle ≈ +17 dk). Kestirilemezse None (≥45 → 2. yarı)."""
    by = collections.defaultdict(list)
    for r in stats: by[r["id"]].append(r)
    for rs in by.values():
        k1 = sorted(r["ts"] - r["t"] * 60 for r in rs if r.get("ts") and r["t"] < 40)
        k2 = sorted(r["ts"] - r["t"] * 60 for r in rs if r.get("ts") and 50 < r["t"] <= 90)
        for r in rs:
            if "pd" in r and r["pd"] is not None: r["_pd"] = r["pd"]; continue
            if r["t"] < 45: r["_pd"] = 1; continue
            if r["t"] >= 50 or not r.get("ts"): r["_pd"] = 2 if r["t"] >= 50 else None; continue
            if k1: r["_pd"] = 1 if r["ts"] - k1[len(k1) // 2] < (r["t"] + 8) * 60 else 2
            elif k2: r["_pd"] = 1 if r["ts"] - k2[len(k2) // 2] < (r["t"] - 8) * 60 else 2
            else: r["_pd"] = None

def live_p_of(r, lam, h1, Z):
    """Kayıtlı seçimin (rk) olasılığını verilen kalan süre modeliyle yeniden hesapla (uygulama formülü)."""
    P = live_pred(lam[0], lam[1], r["hs"], r["as"], r["t"], r.get("rc") or [0, 0], h1, r.get("_pd", r.get("pd")), Z); k = r["rk"]
    if k == "1": return P["H"]
    if k == "X": return P["D"]
    if k == "2": return P["A"]
    if k[0] in "UA" and k[1:]:
        po = 1 - _pois_cdf(int(math.floor(float(k[1:]))) - (r["hs"] + r["as"]), P["LT"]); return po if k[0] == "U" else 1 - po
    if k == "G1": return P["nh"]
    if k == "G2": return P["na"]
    if k == "G0": return P["none"]
    return None

def _match_folds(stats, nf=6):
    first = {}
    for r in stats:
        o = (r.get("_d", ""), r.get("ts") or 0, str(r["id"]))
        if r["id"] not in first or o < first[r["id"]]: first[r["id"]] = o
    ids = sorted(first, key=first.get)
    return {m: min(nf - 1, j * nf // len(ids)) for j, m in enumerate(ids)}

def _app_cal(tr, p):
    """Uygulamadaki liveCal'ın aynısı, yalnız eğitim kayıtlarıyla: live_platt kabul ederse Platt, etmezse kova (n≥30, 50'lik küçültme)."""
    edges = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.01]
    pl = live_platt(tr, edges) if len(tr) >= LIVE_PLATT_MIN else {"kabul": False}
    if pl.get("kabul"): return np.minimum(_platt(p, (pl["a"], pl["b"])), .99), "platt"
    B = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s_ = [r for r in tr if lo <= r["p"] < hi]; B.append([lo, hi, len(s_), sum(r["ok"] for r in s_) / len(s_) if s_ else None])
    return _bins_cal(p, B), "kova"

def live_model_gate(stats, h1, Z=None, nboot=1000, seed=7, test_from=1):
    """Kapı: eski doğrusal model + kendi Platt'ı ↔ v117 modeli + kendi Platt'ı. Aynı kilitli seçimler, olasılık iki modelle yeniden
    hesaplanır. ZAMAN SIRALI genişleyen pencere (maçlar ilk kayıt anına göre 6 dilim; k. dilimin Platt'ı yalnız önceki dilimlerle
    öğrenilir). Fark maç-blok bootstrap ile; kabul: ΔBrier %95 GA üst sınırı < 0 ve ΔLL < 0."""
    Z = Z or dict(__import__("canli_istat").ZDEF)
    lam = _live_lam_map(); rs = [r for r in stats if (r.get("lam") or lam.get(str(r["id"])))]
    if len(rs) < LIVE_PLATT_MIN: return {"kabul": False, "n": len(rs), "aciklama": f"en az {LIVE_PLATT_MIN} eşleşen canlı seçim gerekli"}
    _infer_pd(rs)
    for r in rs:
        L = r.get("lam") or lam[str(r["id"])]
        r["_p0"] = live_p_of(r, L, h1, None); r["_p1"] = live_p_of(r, L, h1, Z)
    rs = [r for r in rs if r["_p0"] is not None and r["_p1"] is not None]
    fold = _match_folds(rs); y_all = np.array([float(r["ok"]) for r in rs])
    out = {m: [] for m in ("ham0", "ham1", "q0", "q1")}; te_ix = []; fw = 0; nfo = 0; secim = []
    for k in range(test_from, 6):
        tr = [i for i, r in enumerate(rs) if fold[r["id"]] < k]; te = [i for i, r in enumerate(rs) if fold[r["id"]] == k]
        if len(tr) < 50 or not te: continue
        nfo += 1; te_ix += te; yt = y_all[te]; bb = []; sc = []
        for j, key in ((0, "_p0"), (1, "_p1")):
            pt = np.array([rs[i][key] for i in te]); q, nm = _app_cal([dict(rs[i], p=rs[i][key]) for i in tr], pt)
            out[f"ham{j}"].append(np.minimum(pt, .99)); out[f"q{j}"].append(q); bb.append(float(np.mean((q - yt) ** 2))); sc.append(nm)
        fw += bb[1] < bb[0]; secim.append(sc)
    if not nfo: return {"kabul": False, "n": len(rs), "aciklama": "sınama dilimi oluşmadı"}
    te_ix = np.array(te_ix); y = y_all[te_ix]; A = {k: np.concatenate(v) for k, v in out.items()}
    br = lambda p: (p - y) ** 2
    ll = lambda p: -(y * np.log(np.clip(p, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1)))
    dB = br(A["q1"]) - br(A["q0"]); dL = ll(A["q1"]) - ll(A["q0"]); dH = br(A["ham1"]) - br(A["q0"])   # dH: yalnız bilgi
    ids = np.array([str(rs[i]["id"]) for i in te_ix]); uid = sorted(set(ids)); ix = {u: np.where(ids == u)[0] for u in uid}
    rng = np.random.default_rng(seed); bsB = []; bsL = []; bsH = []
    for _ in range(nboot):
        sm = np.concatenate([ix[u] for u in rng.choice(uid, len(uid))]); bsB.append(dB[sm].mean()); bsL.append(dL[sm].mean()); bsH.append(dH[sm].mean())
    ciB = [float(np.percentile(bsB, 2.5)), float(np.percentile(bsB, 97.5))]; ciL = [float(np.percentile(bsL, 2.5)), float(np.percentile(bsL, 97.5))]
    def band(p):
        o = []
        for lo, hi in ((0, .6), (.6, .7), (.7, .8), (.8, .9), (.9, 1.01)):
            m = (p >= lo) & (p < hi)
            if m.any(): o.append([lo, hi, int(m.sum()), round(float(p[m].mean()), 4), round(float(y[m].mean()), 4), round(float(y[m].mean() - p[m].mean()), 4)])
        return o
    R = lambda x: round(float(x), 5)
    tab = {k: {"brier": R(br(v).mean()), "ll": R(ll(v).mean()), "ort_p": round(float(v.mean()), 4), "bant": band(v)} for k, v in A.items()}
    ok = ciB[1] < 0 and float(dL.mean()) < 0
    return {"kabul": bool(ok), "n": len(rs), "mac": len({r["id"] for r in rs}), "sinama_n": int(len(y)), "sinama_mac": len(uid), "gercek": round(float(y.mean()), 4),
            "dilim": nfo, "kazanilan_dilim": int(fw), "kalibrasyon_secimi": secim, "d_brier": R(dB.mean()), "d_brier_ga95": [R(ciB[0]), R(ciB[1])],
            "d_ll": R(dL.mean()), "d_ll_ga95": [R(ciL[0]), R(ciL[1])], "tablo": tab,
            "bilgi_v117_ham_vs_eski_kal": {"d_brier": R(dH.mean()), "ga95": [R(np.percentile(bsH, 2.5)), R(np.percentile(bsH, 97.5))]},
            "aciklama": "ham0/q0: eski doğrusal model (ham / uygulamanın kalibrasyonu), ham1/q1: v117 uzatma + artan yoğunluk. Kalibrasyon her dilimde yalnız önceki dilimlerle, uygulamadaki kuralla seçilir (Platt kabul ise Platt, değilse kova). bant: [alt, üst, n, ort tahmin, gerçek, fark]"}, rs

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
    return live_cal_block(stats)

def live_cal_block(stats, h1=None):
    """Canlı kalibrasyon bloğu (daily.json → canli). Ağ kullanmaz. v117: önce kalan süre modeli kapısı (canli.zaman); kabul ise
    kova ve Platt, kayıtlı seçimlerin v117 modeliyle YENİDEN hesaplanan olasılığı üzerinden öğrenilir (uygulama ile aynı ölçek)."""
    import canli_istat as CI
    if h1 is None:
        try: h1 = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"].get("h1", .4428)
        except Exception: h1 = .4428
    zm = {"v": 117, **{k: v for k, v in CI.ZDEF.items() if k != "v"}, "kabul": False}
    try:
        G = live_model_gate([dict(r) for r in stats], h1)
        if isinstance(G, tuple):
            G, rs = G
            if G.get("kabul") and _rollback_frozen("canli_zaman"): G["kabul"] = False; G["aciklama"] = "Koruyucu geri alma süresince dondurulmuş"
            if G.get("kabul"): stats = [dict(r, p=round(r["_p1"], 4)) for r in rs]      # yeni ölçekte kova + Platt
        zm.update(kabul=bool(G.get("kabul")), kapi=G)
    except Exception as ex:
        print("canlı zaman kapısı atlandı:", ex.__class__.__name__, ex, flush=True)
    edges = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.01]; bins = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s_ = [r for r in stats if lo <= r["p"] < hi]
        bins.append([lo, hi, len(s_), round(sum(r["ok"] for r in s_) / len(s_), 4) if s_ else None])
    out = {"n": len(stats), "hit": round(sum(r["ok"] for r in stats) / len(stats), 4) if stats else None, "bins": bins, "zaman": zm}
    # 🎯 Canlı Platt kalibrasyonu (yeni alan, 'bins' biçimi değişmedi): zaman sıralı sınamayı geçerse kabul=true
    try:
        pl = live_platt(stats, edges)
        if pl.get("kabul") and _rollback_frozen("canli_platt"): pl["kabul"] = False; pl["aciklama"] = "Koruyucu geri alma süresince dondurulmuş"
        pl["model"] = "v117" if zm["kabul"] else "eski"
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
            if r.get("sk"): r["sok"] = hit(r["sk"], r["hs"], r["as"])   # ml80: uygulamanın gösterdiği önerinin sonucu
    for d, recs in days.items(): save_day(d, recs)
    # eski arşivler artık SİLİNMEZ: 120 günden eski günler data/archive/eski/ katmanına sıkıştırılarak taşınır (veritabanı büyür)
    try:
        nz = arsiv.sikistir(DATA, KEEP_DAYS, now.astimezone(TR).date())
        if nz: print(f"Arşiv: {nz} eski gün kalıcı katmana taşındı", flush=True)
    except Exception as ex: print("arşiv sıkıştırma atlandı:", ex.__class__.__name__, ex, flush=True)
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
    allg = [r for _, r in arsiv.kayitlar(DATA, puanli=False) if r.get("ok") is not None]
    out = {"updated": now.strftime("%Y-%m-%dT%H:%MZ"), "gunler": summ,
           "toplam": {"n": len(allg), "hit": round(sum(r["ok"] for r in allg) / len(allg), 4) if allg else None,
                      "guclu_n": sum(1 for r in allg if r["rp"] >= .7), "guclu_hit": (round(sum(r["ok"] for r in allg if r["rp"] >= .7) / max(1, sum(1 for r in allg if r["rp"] >= .7)), 4))}}
    try: out["veritabani"] = arsiv.ozet(DATA)   # yeni alan: {gun, kayit, puanli, ilk, eski_gun}
    except Exception: pass
    try: live_snapshot()
    except Exception as ex: print("canlı kayıt atlandı:", ex.__class__.__name__, ex, flush=True)
    try: out["canli"] = live_grade()
    except Exception as ex: print("canlı puanlama atlandı:", ex.__class__.__name__, ex, flush=True)
    try: live_stats_grade()
    except Exception as ex: print("canlı istatistik puanlama atlandı:", ex.__class__.__name__, flush=True)
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
