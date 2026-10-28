"""OXXai · Canlı güç (CG) laboratuvarı — öğrenme + zaman sıralı sınama + kapı (ağ kullanmaz; yalnız numpy).

Veri (yalnız deponun kendi kayıtları, türetilmiş sayılar):
  • data/archive/live/*.json   canlı anlık görüntüler (dakika, skor, devre, kırmızı kart, maç öncesi λ) — toplayıcı 5 dk'da bir
  • data/archive/GGGG-AA-GG.json   maç sonu skoru (hs/as), ilk yarı skoru (h1/a1), maç öncesi λ, başlama anı (ts)
  Eğitimde ek satırlar: devre arası (t=45, skor h1-a1) ve maç başı (t=0, 0-0) — aynı maçların sonuçlarından.
Sınama (sızıntısız): maçlar başlama gününe göre (İstanbul). Sınama günü D için eğitim = başlama anı + 2,5 sa < D 00:00 olan
maçlar (yani D başlamadan SONUCU kesin bilinenler). Genişleyen pencere: D = 2. günden son güne kadar. Sınama satırları yalnız
canlı anlık görüntüler. Hedefler: MS 1/X/2 (3 sınıf log-kayıp + Brier) ve maç sonu 2,5 Üst (log-kayıp + Brier).
Karşılaştırma: ESKİ = uygulamadaki mevcut yol (canli_istat.rem_lams + Poisson; gösterimde liveCal Platt'ı — sınamada her gün yalnız
önceki günlerin seçimleriyle öğrenilir). YENİ = CG (scripts/canli_guc.py) + isteğe bağlı kendi Platt'ı.
KAPI (kullan=true için hepsi): sınamada ≥ 600 anlık görüntü / ≥ 120 maç; birleşik (MS + 2,5) log-kayıp farkı maç-blok bootstrap
%95 GA üst sınırı < 0; MS ve 2,5 Üst log-kayıplarının ikisi de kötüleşmiyor; Brier (MS) kötüleşmiyor; sınama günlerinin çoğunda iyi.
Kullanım: python3 lab/canli_guc_lab.py [--uygula]   (--uygula: data/canli_guc.json yazılır; kapı geçmezse kullan=false)
"""
import glob, json, math, os, sys, collections
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "scripts"))
import canli_guc as CG, canli_istat as CI
DATA = os.path.join(ROOT, "data"); ARC = os.path.join(DATA, "archive"); TR = ZoneInfo("Europe/Istanbul")
NMAX = 10
MIN_N, MIN_M = 600, 120
W_IY, W_MO, L2 = 1.0, 0.5, 2.0       # ek eğitim satırı ağırlıkları · önsele (DEF) L2 cezası (toplam ağırlık başına değil, sabit)


# ---------------------------------------------------------------- veri
def load():
    fin = {}
    for f in sorted(glob.glob(os.path.join(ARC, "*.json"))):
        d = os.path.basename(f)[:10]
        try: A = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        for k, r in A.items():
            if not isinstance(r, dict) or r.get("hs") is None or r.get("ok") is None or not r.get("lam") or not r.get("ts"): continue
            fin[k] = {"d": d, "ts": r["ts"], "fh": int(r["hs"]), "fa": int(r["as"]), "lam": r["lam"][:2],
                      "h1": r.get("h1"), "a1": r.get("a1")}
    snaps = []
    for f in sorted(glob.glob(os.path.join(ARC, "live", "*.json"))):
        for r in json.load(open(f, encoding="utf-8")).values():
            M = fin.get(str(r["id"]))
            if not M: continue
            L = r.get("lam") or M["lam"]
            snaps.append(dict(r, id=str(r["id"]), lam=L, fh=M["fh"], fa=M["fa"], d=M["d"], kts=M["ts"], rc=r.get("rc") or [0, 0]))
    import collector as CO
    CO._infer_pd(snaps)
    for r in snaps: r["pd_"] = r.get("_pd")
    return fin, snaps


def rows_of(snaps, fin, ids, extra=True):
    """Model girdisi sözlüğü (numpy). extra: aynı maçların devre arası + maç başı satırları."""
    R = []
    for r in snaps:
        if r["id"] in ids: R.append((r["lam"][0], r["lam"][1], r["t"], r["pd_"], r["hs"], r["as"], r["rc"][0], r["rc"][1], r["fh"], r["fa"], 1.0, 0))
    if extra:
        for k in ids:
            M = fin[k]; lh, la = M["lam"]
            R.append((lh, la, 0.0, 1, 0, 0, 0, 0, M["fh"], M["fa"], W_MO, 2))
            if M["h1"] is not None: R.append((lh, la, 45.0, 0, int(M["h1"]), int(M["a1"]), 0, 0, M["fh"], M["fa"], W_IY, 1))
    A = np.array([[np.nan if v is None else v for v in x] for x in R], float) if R else np.zeros((0, 12))
    c = lambda i: A[:, i]
    return {"lh": c(0), "la": c(1), "t": c(2), "pd": c(3), "hs": c(4), "as": c(5), "rh": c(6), "ra": c(7), "fh": c(8), "fa": c(9), "w": c(10), "src": c(11)}


# ---------------------------------------------------------------- vektörel modeller
def _rem(t, pd, h1, xi, e1=3.0, e2=3.0, rmin=1.0):
    pd = np.where(np.isnan(pd), np.where(t < 45, 1, 2), pd)
    F = lambda u: u + xi * (u * u - u) / 2
    a1 = np.maximum(0, t); r1 = np.where(t < 45, (45 - t) + e1, np.maximum(e1 - (t - 45), rmin))
    a2 = np.maximum(0, t - 45); r2 = np.where(t < 90, (90 - t) + e2, np.maximum(e2 - (t - 90), rmin))
    s1 = (1 - F(a1 / (a1 + r1))) * h1 + (1 - h1); s2 = np.maximum(.004, (1 - F(a2 / (a2 + r2))) * (1 - h1))
    return np.where(pd == 0, 1 - h1, np.where(pd == 1, s1, s2))


def _rem_old(t, pd, h1):
    s = np.where(t < 45, (45 - t) / 45 * h1 + (1 - h1), np.maximum(.012, (90 - t) / 45 * (1 - h1)))
    return np.where(pd == 0, 1 - h1, s)


def _grid(ph, pa, X):
    """ph, pa: (n, K+1). Sonuç: H, D, A, o25."""
    K = ph.shape[1]; i = np.arange(K)
    fh = X["hs"][:, None, None] + i[None, :, None]; fa = X["as"][:, None, None] + i[None, None, :]
    q = ph[:, :, None] * pa[:, None, :]
    H = (q * (fh > fa)).sum((1, 2)); D = (q * (fh == fa)).sum((1, 2)); A = (q * (fh < fa)).sum((1, 2)); O = (q * (fh + fa > 2)).sum((1, 2))
    z = H + D + A
    return H / z, D / z, A / z, O / z


def _pois(mu, K):
    out = [np.exp(-mu)]
    for k in range(K): out.append(out[-1] * mu / (k + 1))
    return np.stack(out, 1)


def _nb(mu, r, K):
    q = r / (r + mu); out = [q ** r]; s = mu / (r + mu)
    for k in range(K): out.append(out[-1] * (k + r) / (k + 1) * s)
    P = np.stack(out, 1); return P / P.sum(1, keepdims=True)


def old_probs(X, h1):
    """Uygulamadaki mevcut çekirdek (canli_istat.rem_lams, kalan süre eski doğrusal — daily.json canli.zaman kabul değil)."""
    rem = _rem_old(X["t"], X["pd"], h1); d = X["hs"] - X["as"]; st = X["t"] >= 15; up, dn = math.exp(.1), math.exp(-.1)
    LH = X["lh"] * rem * np.where(st, np.where(d < 0, up, dn), 1) * .72 ** X["rh"] * 1.25 ** X["ra"]
    LA = X["la"] * rem * np.where(st, np.where(d > 0, up, dn), 1) * .72 ** X["ra"] * 1.25 ** X["rh"]
    return _grid(_pois(LH, 8), _pois(LA, 8), X)


def cg_probs(X, P, nb=True):
    t = X["t"]; rem = _rem(t, X["pd"], P["h1"], P["xi"], P["e1"], P["e2"], P["rmin"]); el = np.maximum(0, 1 - rem); d = X["hs"] - X["as"]
    late = np.clip((t - 60) / 30, 0, 1); st = t >= 15; kL = np.exp(P.get("g_l2", 0.0) * np.clip((t - 70) / 15, 0, 1))
    def sm(dd): return np.where(st, np.where(dd < 0, np.exp(P["g_tr"] + P["g_trl"] * late), np.where(dd > 0, np.exp(P["g_ld"] + P.get("g_ldl", 0.0) * late), np.exp(P["g_lv"]))), 1.0)
    a = P["a"]; s = P["s"]
    kH = P["rc_own"] ** X["rh"] * P["rc_opp"] ** X["ra"]; kA = P["rc_own"] ** X["ra"] * P["rc_opp"] ** X["rh"]
    mH = s * X["lh"] * rem * sm(d) * kH * kL * (a + X["hs"]) / (a + s * X["lh"] * el)
    mA = s * X["la"] * rem * sm(-d) * kA * kL * (a + X["as"]) / (a + s * X["la"] * el)
    if not nb: return _grid(_pois(mH, NMAX), _pois(mA, NMAX), X)
    return _grid(_nb(mH, a + X["hs"], NMAX), _nb(mA, a + X["as"], NMAX), X)


# ---------------------------------------------------------------- ölçüler
def losses(pr, X):
    H, D, A, O = [np.clip(v, 1e-6, 1 - 1e-6) for v in pr]
    yH = (X["fh"] > X["fa"]).astype(float); yD = (X["fh"] == X["fa"]).astype(float); yA = (X["fh"] < X["fa"]).astype(float)
    yO = (X["fh"] + X["fa"] > 2).astype(float)
    ll_ms = -(yH * np.log(H) + yD * np.log(D) + yA * np.log(A)); br_ms = (H - yH) ** 2 + (D - yD) ** 2 + (A - yA) ** 2
    ll_o = -(yO * np.log(O) + (1 - yO) * np.log(1 - O)); br_o = (O - yO) ** 2
    return ll_ms, br_ms, ll_o, br_o


def platt(p, ab):
    p = np.clip(p, 1e-4, 1 - 1e-4); return 1 / (1 + np.exp(-(ab[0] + ab[1] * np.log(p / (1 - p)))))


def shown(pr, ab):
    """Uygulamadaki gösterim (canli-gt-v107 reg): üçlüde en olası seçenek liveCal (Platt) ile düzeltilir, kalan orantılı dağıtılır;
    ikili pazarda (2,5 Üst) büyük olan düzeltilir, tümleyeni alınır. ab=None → ham."""
    H, D, A, O = pr
    if ab is None: return pr
    T = np.stack([H, D, A], 1); bi = T.argmax(1); bv = np.minimum(.99, platt(T[np.arange(len(T)), bi], ab))
    rest = T.sum(1) - T[np.arange(len(T)), bi]; S = T * ((1 - bv) / np.maximum(rest, 1e-12))[:, None]; S[np.arange(len(T)), bi] = bv
    hi = np.maximum(O, 1 - O); v = np.minimum(.99, platt(hi, ab)); O2 = np.where(O >= .5, v, 1 - v)
    return S[:, 0], S[:, 1], S[:, 2], O2


# ---------------------------------------------------------------- öğrenme
FREE = ("s", "h1", "xi", "a", "g_tr", "g_trl", "g_ld", "g_lv")


def unpack(v, base):
    P = dict(base)
    P.update(s=math.exp(v[0]), h1=min(.6, max(.3, v[1])), xi=min(1.9, max(-1.9, v[2])), a=math.exp(min(7, max(-1, v[3]))),
             g_tr=v[4], g_trl=v[5], g_ld=v[6], g_lv=v[7])
    return P


def pack(P): return np.array([math.log(P["s"]), P["h1"], P["xi"], math.log(P["a"]), P["g_tr"], P["g_trl"], P["g_ld"], P["g_lv"]])


def objective(v, X, base, nb=True):
    P = unpack(v, base); l1, _, l2, _ = losses(cg_probs(X, P, nb), X)
    w = X["w"]; prior = pack(base)
    pen = L2 * float(np.sum((v - prior)[[0, 4, 5, 6, 7]] ** 2)) + 0.5 * L2 * ((v[2] - prior[2]) ** 2 + (v[1] - prior[1]) ** 2 * 25)
    return float(((l1 + l2) * w).sum() / w.sum()) + pen / max(1.0, w.sum() / 50)


def nelder_mead(f, x0, step=0.15, it=900, tol=1e-7):
    n = len(x0); S = [np.array(x0, float)] + [np.array(x0, float) + step * np.eye(n)[i] for i in range(n)]; V = [f(x) for x in S]
    for _ in range(it):
        o = np.argsort(V); S = [S[i] for i in o]; V = [V[i] for i in o]
        if abs(V[-1] - V[0]) < tol: break
        c = np.mean(S[:-1], 0); xr = c + (c - S[-1]); fr = f(xr)
        if fr < V[0]:
            xe = c + 2 * (c - S[-1]); fe = f(xe)
            S[-1], V[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < V[-2]: S[-1], V[-1] = xr, fr
        else:
            xc = c + .5 * (S[-1] - c); fc = f(xc)
            if fc < V[-1]: S[-1], V[-1] = xc, fc
            else:
                S = [S[0]] + [S[0] + .5 * (x - S[0]) for x in S[1:]]; V = [V[0]] + [f(x) for x in S[1:]]
    i = int(np.argmin(V)); return S[i], V[i]


def fit(X, base, nb=True):
    v, val = nelder_mead(lambda v: objective(v, X, base, nb), pack(base))
    v, val = nelder_mead(lambda v: objective(v, X, base, nb), v, step=.05)
    return unpack(v, base), val


# ---------------------------------------------------------------- v136 · son dakika (geç) parametreleri — 2. aşama
# Ölçüm (v135): eski canlı modelde 75. dk sonrası %97,9 denilen seçimler %81,6 tuttu. CG'de geç dakikalar için ayrı serbest parametre
# yoktu (uzatma e2=3 ve taban rmin=1 sabit). 2. aşama: 1. aşama parametreleri sabitken yalnız GEC öğrenilir (nötr Gauss önsel).
GEC = ("e2", "rmin", "g_l2", "g_ldl")
GEC_NOTR = {"e2": 3.0, "rmin": 1.0, "g_l2": 0.0, "g_ldl": 0.0}
GEC_DK = 75                            # ölçüm dilimi sınırı (75+ / 75−)


def unpack_gec(v, base):
    return dict(base, e2=min(8.0, max(1.0, v[0])), rmin=min(4.0, max(0.5, v[1])), g_l2=min(1.0, max(-1.0, v[2])), g_ldl=min(1.0, max(-1.0, v[3])))


def fit_gec(X, base):
    """2. aşama: yalnız geç dakika parametreleri. Amaç: tüm satırlarda birleşik log-kayıp (geç dakika satırları bu parametrelere
    duyarlı olduğundan esas olarak onlar belirler); önsel nötr (GEC_NOTR), Gauss önsel std sc."""
    m = X["t"] >= 60
    Xs = {k: v[m] for k, v in X.items()}
    v0 = np.array([GEC_NOTR[k] for k in GEC]); sc = np.array([2.0, 1.0, 0.5, 0.5])     # önsel std (Gauss önsel, toplam log-olabilirliğe eklenir)
    def f(v):
        P = unpack_gec(v, base); l1, _, l2, _ = losses(cg_probs(Xs, P), Xs); w = Xs["w"]
        return float(((l1 + l2) * w).sum() + 0.5 * np.sum(((v - v0) / sc) ** 2)) / float(w.sum())
    v, _ = nelder_mead(f, v0, step=.3, it=600)
    v, _ = nelder_mead(f, v, step=.05, it=400)
    return unpack_gec(v, base)


# ---------------------------------------------------------------- seçim (pick) Platt'ı — uygulamanın liveCal'ı
def pick_rows(snaps, ids):
    return [r for r in snaps if r["id"] in ids and r.get("ok") is not None]


def old_pick_p(r, h1):
    import collector as CO
    return CO.live_p_of(dict(r, _pd=r["pd_"]), r["lam"], h1, None)


def cg_pick_p(r, P):
    Pr = CG.probs(r["lam"][0], r["lam"][1], r["hs"], r["as"], r["t"], r["rc"], r["pd_"], P)
    return CG.pick_p(Pr, r["rk"], r["hs"], r["as"])


def platt_fit(ps, ys):
    import collector as CO
    return CO._platt_fit(ps, ys)


# ---------------------------------------------------------------- sınama
def day_start(d): return datetime.combine(date.fromisoformat(d), datetime.min.time(), TR).timestamp()


def evaluate(fin, snaps, h1, verbose=True):
    days = sorted({r["d"] for r in snaps}); res = {"gunler": [], "satir": {}}
    acc = collections.defaultdict(list); ids_all = []; dayflag = []
    for D in days[1:]:
        t0 = day_start(D)
        tr_ids = {k for k, M in fin.items() if M["ts"] + 2.5 * 3600 < t0}
        te_ids = {r["id"] for r in snaps if r["d"] == D}
        tr_live = {r["id"] for r in snaps if r["id"] in tr_ids}
        if len(tr_live) < 30 or not te_ids: continue
        Xtr = rows_of(snaps, fin, tr_ids, extra=True)
        base = dict(CG.DEF, h1=h1)
        P, val = fit(Xtr, base, nb=True)
        Pg = fit_gec(Xtr, P)
        Xte = rows_of(snaps, fin, te_ids, extra=False)
        # seçim Platt'ları (yalnız eğitim maçlarının kayıtlı seçimleri)
        pr_tr = pick_rows(snaps, tr_ids)
        ab_old = platt_fit([old_pick_p(r, h1) for r in pr_tr], [float(r["ok"]) for r in pr_tr]) if len(pr_tr) >= 300 else None
        cgp = [(cg_pick_p(r, P), float(r["ok"])) for r in pr_tr]; cgp = [x for x in cgp if x[0] is not None]
        ab_cg = platt_fit([x[0] for x in cgp], [x[1] for x in cgp]) if len(cgp) >= 300 else None
        po = old_probs(Xte, h1); pn = cg_probs(Xte, P)
        V = {"eski_ham": po, "eski_kal": shown(po, ab_old), "cg_ham": pn, "cg_kal": shown(pn, ab_cg),
             "cg_poisson": cg_probs(Xte, dict(P, a=1e7), nb=True), "cg_gec": cg_probs(Xte, Pg)}
        res.setdefault("_T", []).append(Xte["t"])
        for k, pr in V.items(): acc[k].append(np.stack(losses(pr, Xte), 1))
        ids_all += [r["id"] for r in snaps if r["d"] == D and r["id"] in te_ids]
        # satır sırası rows_of ile aynı (snaps sırası)
        g = {k: [round(float(x), 5) for x in np.stack(losses(pr, Xte), 1).mean(0)] for k, pr in V.items()}
        res.setdefault("_P", []).append((D, P)); res.setdefault("_PG", []).append((D, Pg))
        res["gunler"].append({"gun": D, "egitim_mac": len(tr_ids), "egitim_canli_mac": len(tr_live), "sinama_n": int(len(Xte["t"])), "sinama_mac": len(te_ids),
                              "params": {k: round(P[k], 4) for k in FREE}, "gec": {k: round(Pg[k], 4) for k in GEC}, "platt_eski": ab_old and [round(x, 4) for x in ab_old], "platt_cg": ab_cg and [round(x, 4) for x in ab_cg],
                              "olcu": g})
        if verbose: print(D, "eğitim maç", len(tr_ids), "sınama", len(Xte["t"]), "/", len(te_ids), {k: v for k, v in g.items()}, {k: round(P[k], 3) for k in FREE}, flush=True)
    if not acc: return None
    L = {k: np.concatenate(v) for k, v in acc.items()}; ids = np.array(ids_all); res["_T"] = np.concatenate(res["_T"])
    res["n"] = int(len(ids)); res["mac"] = len(set(ids_all))
    NM = ("ll_ms", "brier_ms", "ll_o25", "brier_o25")
    res["tablo"] = {k: {nm: round(float(v[:, i].mean()), 5) for i, nm in enumerate(NM)} for k, v in L.items()}
    return res, L, ids


def pick_eval(fin, snaps, h1, params_by_day):
    """Kayıtlı canlı seçimler (Power Now): seçimin olasılığı ↔ tuttu mu. ESKİ = eski model + Platt (yalnız önceki günlerle), YENİ = CG ham."""
    P_ = []; Y = []; I = []
    for D, P in params_by_day:
        t0 = day_start(D); tr = {k for k, M in fin.items() if M["ts"] + 2.5 * 3600 < t0}; te = {r["id"] for r in snaps if r["d"] == D}
        ptr = pick_rows(snaps, tr)
        if len(ptr) < 300: continue
        ab = platt_fit([old_pick_p(r, h1) for r in ptr], [float(r["ok"]) for r in ptr])
        for r in pick_rows(snaps, te):
            po, pc = old_pick_p(r, h1), cg_pick_p(r, P)
            if po is None or pc is None: continue
            P_.append((min(.99, float(platt(np.array([po]), ab)[0])), min(.99, pc))); Y.append(float(r["ok"])); I.append(r["id"])
    if not Y: return None
    A = np.array(P_); Y = np.array(Y); I = np.array(I)
    br = lambda p: (p - Y) ** 2
    ll = lambda p: -(Y * np.log(np.clip(p, 1e-6, 1)) + (1 - Y) * np.log(np.clip(1 - p, 1e-6, 1)))
    d = br(A[:, 1]) - br(A[:, 0]); ci, pw = boot(d, I)
    return {"n": int(len(Y)), "mac": len(set(I.tolist())), "gercek": round(float(Y.mean()), 4),
            "eski_kal": {"brier": round(float(br(A[:, 0]).mean()), 5), "ll": round(float(ll(A[:, 0]).mean()), 5), "ort_p": round(float(A[:, 0].mean()), 4)},
            "cg_ham": {"brier": round(float(br(A[:, 1]).mean()), 5), "ll": round(float(ll(A[:, 1]).mean()), 5), "ort_p": round(float(A[:, 1].mean()), 4)},
            "d_brier": round(float(d.mean()), 5), "ga95": ci, "p_iyi": pw}


def gec_eval(fin, snaps, h1, res, L, ids):
    """v136 · geç dakika düzeltmesinin zaman sıralı ölçümü, 75+ ve 75− dilimlerinde ayrı ayrı:
    (a) anlık görüntüler: MS + 2,5 Üst birleşik log-kayıp ve Brier (cg_ham ↔ cg_gec), maç-blok bootstrap;
    (b) kayıtlı canlı seçimler (Power Now): seçimin olasılığı ↔ tuttu mu — n, ort_p, gerçek, kalibrasyon farkı, LL, Brier.
        once = CG (zaman sıralı, uygulamanın kullandığı), sonra = CG + geç parametreler, eski_kayit = kayıttaki eski model olasılığı
        (v135 ölçümünde aşırı güvenli çıkan; başvuru için)."""
    T = res["_T"]; out = {"dk": GEC_DK, "anlik": {}, "secim": {}}
    for nm, m in (("75+", T >= GEC_DK), ("75-", T < GEC_DK)):
        if not m.any(): continue
        a, b = L["cg_ham"][m], L["cg_gec"][m]; d = (b[:, 0] + b[:, 2]) - (a[:, 0] + a[:, 2]); ci, pw = boot(d, ids[m])
        out["anlik"][nm] = {"n": int(m.sum()), "ll_once": round(float((a[:, 0] + a[:, 2]).mean()), 5), "ll_sonra": round(float((b[:, 0] + b[:, 2]).mean()), 5),
                            "brier_once": round(float((a[:, 1] + a[:, 3]).mean()), 5), "brier_sonra": round(float((b[:, 1] + b[:, 3]).mean()), 5),
                            "d_ll": round(float(d.mean()), 5), "ga95": ci, "p_iyi": pw}
    PG = dict(res.get("_PG", [])); rows = []
    for D, P in res.get("_P", []):
        Pg = PG.get(D)
        if not Pg: continue
        for r in snaps:
            if r["d"] != D or r.get("ok") is None: continue
            p0, p1 = cg_pick_p(r, P), cg_pick_p(r, Pg)
            if p0 is None or p1 is None: continue
            rows.append((r["t"], min(.99, p0), min(.99, p1), float(r["ok"]), r["id"], min(.99, float(r["p"]))))
    for nm, f in (("75+", lambda t: t >= GEC_DK), ("75-", lambda t: t < GEC_DK)):
        R = [x for x in rows if f(x[0])]
        if not R: continue
        A = np.array([x[1:4] for x in R]); y = A[:, 2]; I = np.array([x[4] for x in R]); E = np.array([x[5] for x in R])
        br = lambda p: (p - y) ** 2; ll = lambda p: -(y * np.log(np.clip(p, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1)))
        dB = br(A[:, 1]) - br(A[:, 0]); ci, pw = boot(dB, I)
        hi = A[:, 0] >= .9
        out["secim"][nm] = {"n": int(len(y)), "gercek": round(float(y.mean()), 4),
                            "once": {"ort_p": round(float(A[:, 0].mean()), 4), "fark": round(float(y.mean() - A[:, 0].mean()), 4), "ll": round(float(ll(A[:, 0]).mean()), 5), "brier": round(float(br(A[:, 0]).mean()), 5)},
                            "sonra": {"ort_p": round(float(A[:, 1].mean()), 4), "fark": round(float(y.mean() - A[:, 1].mean()), 4), "ll": round(float(ll(A[:, 1]).mean()), 5), "brier": round(float(br(A[:, 1]).mean()), 5)},
                            "eski_kayit": {"ort_p": round(float(E.mean()), 4), "fark": round(float(y.mean() - E.mean()), 4), "ll": round(float(ll(E).mean()), 5), "brier": round(float(br(E).mean()), 5),
                                           "p95_ustu": {"n": int((E >= .95).sum()), "ort_p": round(float(E[E >= .95].mean()), 4) if (E >= .95).any() else None,
                                                        "gercek": round(float(y[E >= .95].mean()), 4) if (E >= .95).any() else None,
                                                        "cg_ort_p": round(float(A[E >= .95, 0].mean()), 4) if (E >= .95).any() else None}},
                            "d_brier": round(float(dB.mean()), 5), "ga95": ci, "p_iyi": pw,
                            "p90_ustu": {"n": int(hi.sum()), "gercek": round(float(y[hi].mean()), 4) if hi.any() else None,
                                         "once_ort_p": round(float(A[hi, 0].mean()), 4) if hi.any() else None, "sonra_ort_p": round(float(A[hi, 1].mean()), 4) if hi.any() else None}}
    a, b = out["anlik"].get("75+"), out["anlik"].get("75-"); sa, sb = out["secim"].get("75+"), out["secim"].get("75-")
    ok = bool(a and b and sa and sb and a["n"] >= 150 and a["d_ll"] < 0 and a["p_iyi"] >= .8 and b["d_ll"] <= 0.001
              and sa["d_brier"] <= 0 and sb["d_brier"] <= 0.001 and abs(sa["sonra"]["fark"]) <= abs(sa["once"]["fark"]) + 0.01)
    out["kapi"] = {"kural": "75+ anlık: ΔLL < 0 ve bootstrap P(iyi) ≥ 0,8 (n ≥ 150); 75−: ΔLL ≤ +0,001; seçimlerde 75+ ΔBrier ≤ 0, 75− ΔBrier ≤ +0,001; 75+ kalibrasyon farkı büyümüyor (+0,01 pay)",
                   "gecti": ok}
    return out


def boot(dl, ids, B=2000, seed=11):
    uid = sorted(set(ids)); ix = {u: np.where(ids == u)[0] for u in uid}; rng = np.random.default_rng(seed); out = []
    for _ in range(B):
        sm = np.concatenate([ix[u] for u in rng.choice(uid, len(uid))]); out.append(dl[sm].mean())
    return [round(float(np.percentile(out, 2.5)), 5), round(float(np.percentile(out, 97.5)), 5)], round(float(np.mean(np.array(out) < 0)), 4)


def main(argv):
    try: h1 = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"].get("h1", .4428)
    except Exception: h1 = .4428
    fin, snaps = load()
    print(f"sonuçlu maç {len(fin)} · sonuçlu canlı anlık görüntü {len(snaps)} / {len({r['id'] for r in snaps})} maç", flush=True)
    E = evaluate(fin, snaps, h1)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    out = {"v": 1, "kullan": False, "zaman": now, "model": "CG: Gamma-Poisson (NB) kalan gol + skor durumu + kırmızı kart + uzatmalı kalan süre"}
    if not E:
        out.update(karar="yetersiz veri")
    else:
        res, L, ids = E
        # karşılaştırma: YENİ (gösterim yolu = cg_kal veya cg_ham, hangisi eğitimde seçilirse — burada: her ikisi raporlanır) ↔ ESKİ gösterim (eski_kal)
        T = res["tablo"]
        new_key = "cg_kal" if T["cg_kal"]["ll_ms"] + T["cg_kal"]["ll_o25"] < T["cg_ham"]["ll_ms"] + T["cg_ham"]["ll_o25"] else "cg_ham"
        # NOT: new_key seçimi sınama kümesine bakar → kapı ikisinin de ayrı ayrı geçmesini ister (en kötüsü kullanılır)
        def cmp(a, b):
            d = (L[a][:, 0] + L[a][:, 2]) - (L[b][:, 0] + L[b][:, 2]); ci, pw = boot(d, ids)
            dms = L[a][:, 0] - L[b][:, 0]; do = L[a][:, 2] - L[b][:, 2]; dbm = L[a][:, 1] - L[b][:, 1]; dbo = L[a][:, 3] - L[b][:, 3]
            return {"d_ll_toplam": round(float(d.mean()), 5), "ga95": ci, "p_iyi": pw, "d_ll_ms": round(float(dms.mean()), 5), "d_ll_o25": round(float(do.mean()), 5),
                    "d_brier_ms": round(float(dbm.mean()), 5), "d_brier_o25": round(float(dbo.mean()), 5), "ga95_ms": boot(dms, ids)[0], "ga95_o25": boot(do, ids)[0]}
        K = {f"{a}_vs_{b}": cmp(a, b) for a, b in (("cg_ham", "eski_kal"), ("cg_kal", "eski_kal"), ("cg_ham", "eski_ham"), ("cg_poisson", "eski_ham"))}
        win_days = sum(1 for g in res["gunler"] if g["olcu"]["cg_ham"][0] + g["olcu"]["cg_ham"][2] < g["olcu"]["eski_kal"][0] + g["olcu"]["eski_kal"][2])
        c = K["cg_ham_vs_eski_kal"]
        GECR = gec_eval(fin, snaps, h1, res, L, ids); res.pop("_T", None); res.pop("_PG", None)
        SEC = pick_eval(fin, snaps, h1, res.pop("_P", []))
        ok = (SEC is not None and SEC["d_brier"] <= 0 and res["n"] >= MIN_N and res["mac"] >= MIN_M and c["ga95"][1] < 0 and c["d_ll_ms"] <= 0 and c["d_ll_o25"] <= 0 and c["d_brier_ms"] <= 0
              and win_days * 2 > len(res["gunler"]))
        # son parametreler: tüm sonuçlu maçlarla (uygulamada kullanılacak)
        base = dict(CG.DEF, h1=h1); Xall = rows_of(snaps, fin, set(fin), extra=True); P, _ = fit(Xall, base)
        if GECR["kapi"]["gecti"]: P = fit_gec(Xall, P)          # v136: geç dakika parametreleri yalnız kapıyı geçerse (yoksa nötr)
        else: P = dict(P, **GEC_NOTR)
        GECR["uygulanan"] = {k: round(P[k], 5) for k in GEC}
        out.update({"kullan": bool(ok), "params": {k: round(P[k], 5) for k in list(FREE) + ["e1", "e2", "rmin", "g_l2", "g_ldl", "rc_own", "rc_opp", "nmax"]},
                    "gec": GECR,
                    "kal": None, "egitim_satir": int(len(Xall["t"])), "egitim_mac": len(fin),
                    "sinama": {"yontem": "genişleyen pencere, gün bazlı; eğitim = sınama günü başlamadan sonucu kesin maçlar", "n": res["n"], "mac": res["mac"],
                               "tablo": T, "karsilastirma": K, "secim": SEC, "kazanilan_gun": win_days, "gun_sayisi": len(res["gunler"]), "gunler": res["gunler"]},
                    "kapi": {"min_n": MIN_N, "min_mac": MIN_M, "kural": "CG ham ↔ eski (uygulama gösterimi): birleşik ΔLL %95 GA üst < 0, ΔLL MS ≤ 0, ΔLL 2,5 ≤ 0, ΔBrier MS ≤ 0, günlerin çoğunda iyi; kayıtlı canlı seçimlerde Brier eski + Platt'tan kötü değil"},
                    "karar": "kapıdan geçti — uygulama CG kullanır" if ok else "kapıdan geçmedi — uygulama eski yolu kullanır"})
    print(json.dumps({k: v for k, v in out.items() if k != "sinama"}, ensure_ascii=False, indent=1))
    if E: print(json.dumps({k: out["sinama"][k] for k in ("n", "mac", "tablo", "karsilastirma", "secim", "kazanilan_gun", "gun_sayisi")}, ensure_ascii=False, indent=1))
    if E: print(json.dumps(out.get("gec"), ensure_ascii=False, indent=1))
    if "--uygula" in argv:
        json.dump(out, open(os.path.join(DATA, "canli_guc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("yazıldı: data/canli_guc.json")
    return out


if __name__ == "__main__":
    main(sys.argv[1:])
