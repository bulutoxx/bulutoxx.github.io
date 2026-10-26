"""🔧 Futbol isabet geliştirme laboratuvarı (yalnız repodaki veriyle; ağ kullanmaz).

1) Zayıf noktalar: uygulamanın SUNDUĞU olasılıklar (piyasa yolu: power marj → gol tablosu → iki yarı Dixon-Coles →
   calT/gscale/dk; scripts/collector.py served_pick ile aynı) pazar (MS, 2,5 A/Ü, KG, İY), lig ve olasılık kovası bazında.
   Kaynaklar: kilitli iddaa arşivi (data/archive), kilitli model tahmin günlüğü (data/predlog.json), derin arşiv + sezon.
2) Adaylar: en fazla 3 iyileştirme, YALNIZ ileriye dönük (her sınama dilimi için yalnız ondan önceki veriyle öğrenilir).
   Kapı: eşleştirilmiş gün-blok bootstrap ile Δlog-kayıp %95 GA üst sınırı < 0, güçlü (≥%70) ve Altın isabeti düşmüyor,
   İKİ ayrı zaman diliminin ikisinde de.
Çıktı: data/fb_gelistir.json (yalnız toplu istatistik; takım adı / ham kaynak verisi yazılmaz)."""
import json, os, sys, glob, math, collections, time
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import update as U

EPS = 1e-6
def jl(p):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return None

def params():
    return (jl(os.path.join(DATA, "model.json")) or {}).get("params", {})

# ------------------------------------------------------------------ sunulan olasılıklar (tüm pazarlar)
def served_full(odds, ous, P, chunk=4000):
    """odds: [[o1,oX,o2]], ous: [[ü,a] | None]. Dönen dict: q (MS, kalibre), O (2,5 üst), B (KG var), I (İY 1X2)."""
    rho = P.get("rho", -0.06); g = P.get("gscale", 1.0); h1 = P.get("h1", .4442); T = P.get("calT", 1.0); dk = P.get("dk", 1.0)
    out = {k: [] for k in "qOBI"}
    i, j = np.meshgrid(np.arange(15), np.arange(15), indexing="ij")
    a8, b8 = np.meshgrid(np.arange(8), np.arange(8), indexing="ij")
    for s in range(0, len(odds), chunk):
        lam = U.ui_market_lam(odds[s:s + chunk], ous[s:s + chunk], rho)
        lh = np.clip(lam[:, 0], .15, 4.5) * g; la = np.clip(lam[:, 1], .1, 4) * g
        g1 = U._dc_grid(lh * h1, la * h1, rho, 7); g2 = U._dc_grid(lh * (1 - h1), la * (1 - h1), rho * .6, 7)
        ft = np.zeros((len(lh), 15, 15))
        for a in range(8):
            for b in range(8): ft[:, a:a + 8, b:b + 8] += g1[:, a, b, None, None] * g2
        p = np.stack([(ft * (i > j)).sum((1, 2)), (ft * (i == j)).sum((1, 2)), (ft * (i < j)).sum((1, 2))], 1)
        out["q"].append(U._cal3(p, T, dk)); out["O"].append((ft * ((i + j) > 2)).sum((1, 2)))
        out["B"].append(ft[:, 1:, 1:].sum((1, 2)))
        out["I"].append(np.stack([(g1 * (a8 > b8)).sum((1, 2)), (g1 * (a8 == b8)).sum((1, 2)), (g1 * (a8 < b8)).sum((1, 2))], 1))
    return {k: np.concatenate(v) for k, v in out.items()}

# ------------------------------------------------------------------ veri
def load_archive():
    """Kilitli iddaa arşivi: puanlanmış kayıtlar (gün, kayıt) zaman sırasıyla."""
    out = []
    for f in sorted(glob.glob(os.path.join(DATA, "archive", "2*.json"))):
        d = os.path.basename(f)[:10]
        for k, r in (jl(f) or {}).items():
            if r.get("ok") is None or r.get("hs") is None or not r.get("ms"): continue
            out.append(dict(r, _d=d))
    out.sort(key=lambda r: r.get("ts", 0))
    return out

def load_hist():
    """Derin arşiv (bitmiş sezonlar) + season.json (lig maçları, oranlı). Çakışma: derin yalnız season'daki en eski maçtan önce."""
    S = jl(os.path.join(DATA, "season.json")) or {}
    out = []; first = {}
    for lg, d in S.items():
        if d.get("cup"): continue
        ms = [m for m in d["matches"] if m.get("ft") and m.get("odds") and all(m["odds"])]
        if ms: first[lg] = min(m["d"] for m in d["matches"])
        for m in ms:
            out.append({"d": m["d"], "lg": lg, "ft": m["ft"], "ht": m.get("ht"), "odds": m["odds"], "ou": m.get("ou") if m.get("ou") and all(m["ou"]) else None})
    for f in sorted(glob.glob(os.path.join(DATA, "derin", "*-*.json"))):
        D = jl(f) or {}; lg = D.get("lg"); cut = first.get(lg, "9999")
        for r in D.get("m", []):
            if r[0] < cut and r[5] and r[6] and r[7] and r[3] is not None:
                out.append({"d": r[0], "lg": lg, "ft": [r[3], r[4]], "ht": None, "odds": [r[5], r[6], r[7]], "ou": [r[8], r[9]] if r[8] and r[9] else None})
    out.sort(key=lambda m: m["d"])
    return out

# ------------------------------------------------------------------ ölçüler
def bll(p, y):
    p = np.clip(p, EPS, 1 - EPS); return -(y * np.log(p) + (1 - y) * np.log(1 - p))

def cal_row(p, y):
    p = np.asarray(p, float); y = np.asarray(y, float)
    if not len(p): return None
    return {"n": int(len(p)), "beklenen": round(float(p.mean()), 4), "gercek": round(float(y.mean()), 4),
            "fark": round(float(y.mean() - p.mean()), 4), "brier": round(float(np.mean((p - y) ** 2)), 5), "ll": round(float(bll(p, y).mean()), 5)}

KOVA = [(.5, .55), (.55, .6), (.6, .65), (.65, .7), (.7, .75), (.75, .8), (.8, .85), (.85, 1.01)]

def picks_of(q, O, ms, ou, res, ov):
    """Uygulama öneri kuralı (recOf): oranlı seçenekler (MS 1/X/2, 2,5 Ü/A) içinde en yüksek olasılık."""
    n = len(q); has = np.array([x is not None for x in ou])
    C = np.column_stack([q, np.where(has, O, -1), np.where(has, 1 - O, -1)])
    k = C.argmax(1); pp = C[np.arange(n), k]
    MS = np.array(ms, float); OU = np.array([x if x else [0, 0] for x in ou], float)
    od = np.where(k < 3, MS[np.arange(n), np.minimum(k, 2)], OU[np.arange(n), np.clip(k - 3, 0, 1)])
    y = np.where(k < 3, res == k, np.where(k == 3, ov, ~ov)).astype(float)
    return k, pp, od, y

def gold_mask(days, pp, od):
    m = np.zeros(len(pp), bool); by = collections.defaultdict(list)
    for i in np.where((pp >= .78) & (od >= 1.15) & (od <= 2.0))[0]: by[days[i]].append(i)
    for L in by.values():
        for i in sorted(L, key=lambda i: -pp[i])[:3]: m[i] = True
    return m

KN = ["MS 1", "MS X", "MS 2", "2,5 Üst", "2,5 Alt"]

def weak_tables(S, days, ms, ou, res, ov, btts, has_kg, ires, has_ht, grp):
    """S: served_full çıktısı. Pazar / seçim / kova / grup (lig) tabloları."""
    q, O, B, I = S["q"], S["O"], S["B"], S["I"]; n = len(q)
    T = {}
    # pazar düzeyi (tam dağılım log-kaybı + seçilen tarafın kalibrasyonu)
    mk = {}
    mk["MS"] = {"n": n, "ll": round(float(-np.log(np.clip(q[np.arange(n), res], EPS, 1)).mean()), 5),
                "isabet_argmax": round(float((q.argmax(1) == res).mean()), 4)}
    h = np.array([x is not None for x in ou])
    mk["2,5 A/Ü"] = {"n": int(h.sum()), "ll": round(float(bll(O[h], ov[h]).mean()), 5), "isabet_argmax": round(float(((O[h] >= .5) == ov[h]).mean()), 4),
                     "beklenen_ust": round(float(O[h].mean()), 4), "gercek_ust": round(float(ov[h].mean()), 4)}
    mk["KG"] = {"n": int(has_kg.sum()), "ll": round(float(bll(B[has_kg], btts[has_kg]).mean()), 5), "isabet_argmax": round(float(((B[has_kg] >= .5) == btts[has_kg]).mean()), 4),
                "beklenen_var": round(float(B[has_kg].mean()), 4), "gercek_var": round(float(btts[has_kg].mean()), 4)}
    if has_ht.any():
        ih = has_ht
        mk["İY"] = {"n": int(ih.sum()), "ll": round(float(-np.log(np.clip(I[ih][np.arange(ih.sum()), ires[ih]], EPS, 1)).mean()), 5),
                    "isabet_argmax": round(float((I[ih].argmax(1) == ires[ih]).mean()), 4),
                    "beklenen_x": round(float(I[ih][:, 1].mean()), 4), "gercek_x": round(float((ires[ih] == 1).mean()), 4)}
    # her sonuç olasılığının kendi kalibrasyonu (tüm maçlar, ikili)
    sides = {}
    for j, nm in enumerate(("MS 1", "MS X", "MS 2")): sides[nm] = cal_row(q[:, j], (res == j).astype(float))
    sides["2,5 Üst"] = cal_row(O[h], ov[h].astype(float)); sides["KG Var"] = cal_row(B[has_kg], btts[has_kg].astype(float))
    if has_ht.any():
        for j, nm in enumerate(("İY 1", "İY X", "İY 2")): sides[nm] = cal_row(I[has_ht][:, j], (ires[has_ht] == j).astype(float))
    T["pazar"] = mk; T["olasilik_kalibrasyonu"] = sides
    k, pp, od, y = picks_of(q, O, ms, ou, res, ov)
    T["oneri"] = {"genel": cal_row(pp, y)}
    T["oneri_pazar"] = {KN[j]: cal_row(pp[k == j], y[k == j]) for j in range(5) if (k == j).any()}
    T["oneri_kova"] = {f"{a:.2f}-{b:.2f}": cal_row(pp[(pp >= a) & (pp < b)], y[(pp >= a) & (pp < b)]) for a, b in KOVA if ((pp >= a) & (pp < b)).any()}
    T["oneri_oran"] = {nm: cal_row(pp[m], y[m]) for nm, m in (("<1,20", od < 1.2), ("1,20-1,50", (od >= 1.2) & (od < 1.5)), ("1,50-2,00", (od >= 1.5) & (od <= 2)), (">2,00", od > 2)) if m.any()}
    g = gold_mask(days, pp, od); m70 = pp >= .7
    T["guclu"] = cal_row(pp[m70], y[m70]); T["altin"] = cal_row(pp[g], y[g])
    if grp is not None:
        G = collections.defaultdict(list)
        for i, c in enumerate(grp): G[c].append(i)
        rows = []
        for c, ix in G.items():
            if len(ix) < 25: continue
            ix = np.array(ix); r = cal_row(pp[ix], y[ix]); r["grup"] = c
            r["ms_ll"] = round(float(-np.log(np.clip(q[ix, res[ix]], EPS, 1)).mean()), 5); rows.append(r)
        rows.sort(key=lambda r: r["fark"])
        T["grup_en_zayif"] = rows[:8]; T["grup_en_iyi"] = rows[-4:][::-1]; T["grup_sayisi"] = len(rows)
    return T, (k, pp, od, y)

def arrays_arc(A):
    ms = [r["ms"] for r in A]; ou = [r["ou"] if r.get("ou") and all(r["ou"]) else None for r in A]
    hs = np.array([r["hs"] for r in A]); as_ = np.array([r["as"] for r in A])
    res = np.where(hs > as_, 0, np.where(hs == as_, 1, 2)); ov = (hs + as_) > 2; btts = (hs > 0) & (as_ > 0)
    has_kg = np.array([bool(r.get("kgo")) for r in A]); has_ht = np.array([r.get("h1") is not None for r in A])
    h1 = np.array([r.get("h1") or 0 for r in A]); a1 = np.array([r.get("a1") or 0 for r in A])
    ires = np.where(h1 > a1, 0, np.where(h1 == a1, 1, 2))
    return ms, ou, res, ov, btts, has_kg, ires, has_ht

def arrays_hist(H):
    ms = [m["odds"] for m in H]; ou = [m["ou"] for m in H]
    hs = np.array([m["ft"][0] for m in H]); as_ = np.array([m["ft"][1] for m in H])
    res = np.where(hs > as_, 0, np.where(hs == as_, 1, 2)); ov = (hs + as_) > 2; btts = (hs > 0) & (as_ > 0)
    has_ht = np.array([bool(m.get("ht")) for m in H]); h1 = np.array([(m.get("ht") or [0, 0])[0] for m in H]); a1 = np.array([(m.get("ht") or [0, 0])[1] for m in H])
    ires = np.where(h1 > a1, 0, np.where(h1 == a1, 1, 2))
    return ms, ou, res, ov, btts, np.ones(len(H), bool), ires, has_ht

def predlog_tables():
    L = [e for e in (jl(os.path.join(DATA, "predlog.json")) or []) if e.get("r")]
    if not L: return None
    res = np.array([0 if e["r"][0] > e["r"][1] else 1 if e["r"][0] == e["r"][1] else 2 for e in L])
    p = np.array([e["p"] for e in L]); o = np.array([e["o"] for e in L]); ov = np.array([sum(e["r"]) > 2 for e in L])
    out = {"n": len(L), "model_ms_ll": round(float(-np.log(np.clip(p[np.arange(len(L)), res], EPS, 1)).mean()), 5),
           "model_ms_isabet": round(float((p.argmax(1) == res).mean()), 4), "model_ou_ll": round(float(bll(o, ov).mean()), 5),
           "model_ou_isabet": round(float(((o >= .5) == ov).mean()), 4)}
    mi = [i for i, e in enumerate(L) if e.get("mp")]
    if mi:
        mp = np.array([L[i]["mp"] for i in mi]); r = res[mi]
        out["piyasa_ms_ll_ayni_maclar"] = round(float(-np.log(np.clip(mp[np.arange(len(mi)), r], EPS, 1)).mean()), 5)
        out["model_ms_ll_ayni_maclar"] = round(float(-np.log(np.clip(p[mi][np.arange(len(mi)), r], EPS, 1)).mean()), 5)
        out["ayni_mac_n"] = len(mi)
    G = collections.defaultdict(list)
    for i, e in enumerate(L): G[e["lg"]].append(i)
    rows = []
    for lg, ix in G.items():
        if len(ix) < 12: continue
        ix = np.array(ix); rows.append({"lig": lg, "n": len(ix), "ms_ll": round(float(-np.log(np.clip(p[ix, res[ix]], EPS, 1)).mean()), 4),
                                        "ms_isabet": round(float((p[ix].argmax(1) == res[ix]).mean()), 4)})
    rows.sort(key=lambda r: -r["ms_ll"]); out["lig_en_zayif"] = rows[:6]
    return out

# ------------------------------------------------------------------ küçük, numpy-yalın uydurucu
def softmax_fit(F, y, base=None, th0=None, lam=1.0, iters=30, w=None):
    """z_ik = base_ik + F_ik·θ ; çok sınıflı log-kayıp + λ/2·|θ−θ0|² (Newton). F: (n,K,d), y: (n,) sınıf."""
    n, K, d = F.shape; th0 = np.zeros(d) if th0 is None else np.asarray(th0, float); th = th0.copy()
    base = np.zeros((n, K)) if base is None else base; w = np.ones(n) if w is None else w
    Y = np.eye(K)[y]
    for _ in range(iters):
        z = base + F @ th; z -= z.max(1, keepdims=True); p = np.exp(z); p /= p.sum(1, keepdims=True)
        g = np.einsum("i,ik,ikd->d", w, p - Y, F) + lam * (th - th0)
        mf = np.einsum("ik,ikd->id", p, F)
        Hm = np.einsum("i,ik,ikd,ike->de", w, p, F, F) - np.einsum("i,id,ie->de", w, mf, mf) + lam * np.eye(d)
        step = np.linalg.solve(Hm, g); th -= step
        if np.abs(step).max() < 1e-7: break
    return th

def logit(p): p = np.clip(p, EPS, 1 - EPS); return np.log(p) - np.log(1 - p)
def sig(z): return 1 / (1 + np.exp(-z))

# ------------------------------------------------------------------ adaylar (her biri: fit(eğitim) → apply(sınama))
def platt_ou_fit(O, ov, lam=20.0):
    """C1 — 2,5 Alt/Üst olasılığına Platt (logit doğrusal), kimliğe doğru L2."""
    l = logit(O); F = np.zeros((len(O), 2, 2)); F[:, 0, 0] = l; F[:, 0, 1] = 1
    a = softmax_fit(F, np.where(ov, 0, 1), th0=[1.0, 0.0], lam=lam)
    return {"b": float(a[0]), "a": float(a[1])}

def platt_ou_apply(O, c): return sig(c["a"] + c["b"] * logit(O))

def ms_temp_fit(q, res, lam=20.0):
    """C2 — MS için sıcaklık + beraberlik kaydırması: z_k = T·ln q_k + δ·[k=X]."""
    F = np.zeros((len(q), 3, 2)); F[:, :, 0] = np.log(np.clip(q, EPS, 1)); F[:, 1, 1] = 1
    t = softmax_fit(F, res, th0=[1.0, 0.0], lam=lam)
    return {"T": float(t[0]), "dX": float(t[1])}

def ms_temp_apply(q, c):
    z = c["T"] * np.log(np.clip(q, EPS, 1)); z[:, 1] += c["dX"]; z -= z.max(1, keepdims=True); p = np.exp(z); return p / p.sum(1, keepdims=True)

def lig_fit(q, res, grp, lam=60.0, nmin=150):
    """C3 — lig bazlı MS düzeltmesi: z_k = ln q_k + β_lig·[ev, beraberlik], kimliğe (0) doğru L2 (büzülme)."""
    out = {}
    G = collections.defaultdict(list)
    for i, g in enumerate(grp): G[g].append(i)
    for g, ix in G.items():
        if len(ix) < nmin: continue
        ix = np.array(ix); F = np.zeros((len(ix), 3, 2)); F[:, 0, 0] = 1; F[:, 1, 1] = 1
        b = softmax_fit(F, res[ix], base=np.log(np.clip(q[ix], EPS, 1)), lam=lam)
        out[g] = [round(float(b[0]), 4), round(float(b[1]), 4)]
    return out

def lig_apply(q, grp, c):
    z = np.log(np.clip(q, EPS, 1)).copy()
    for i, g in enumerate(grp):
        b = c.get(g)
        if b: z[i, 0] += b[0]; z[i, 1] += b[1]
    z -= z.max(1, keepdims=True); p = np.exp(z); return p / p.sum(1, keepdims=True)

# ------------------------------------------------------------------ kapı
def boot_ci(dl, blocks, B=2000, seed=7):
    """Eşleştirilmiş blok bootstrap: dl = aday − mevcut kayıp farkı (maç başına). Dönen (ortalama, %2,5, %97,5)."""
    rng = np.random.default_rng(seed); ub = {}
    for i, b in enumerate(blocks): ub.setdefault(b, []).append(i)
    S = np.array([dl[ix].sum() for ix in ub.values()]); N = np.array([len(ix) for ix in ub.values()])
    k = len(S); bs = []
    for _ in range(B):
        j = rng.integers(0, k, k); bs.append(S[j].sum() / N[j].sum())
    return float(dl.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))

def slice_eval(days, blocks, q0, O0, q1, O1, ms, ou, res, ov, primary):
    """Bir sınama dilimi: birincil kayıp (MS 3'lü veya 2,5 ikili) Δ + GA; öneri düzeyi LL; güçlü ve Altın isabeti (mevcut vs aday)."""
    h = np.array([x is not None for x in ou])
    if primary == "ou":
        l0 = bll(O0[h], ov[h]); l1 = bll(O1[h], ov[h]); bl = [b for b, x in zip(blocks, h) if x]
    else:
        l0 = -np.log(np.clip(q0[np.arange(len(res)), res], EPS, 1)); l1 = -np.log(np.clip(q1[np.arange(len(res)), res], EPS, 1)); bl = blocks
    m, lo, hi = boot_ci(l1 - l0, bl)
    R = {"n": int(len(l0)), "ll_mevcut": round(float(l0.mean()), 5), "ll_aday": round(float(l1.mean()), 5), "dll": round(m, 5), "ga95": [round(lo, 5), round(hi, 5)]}
    for nm, (q, O) in (("mevcut", (q0, O0)), ("aday", (q1, O1))):
        k, pp, od, y = picks_of(q, O, ms, ou, res, ov); g = gold_mask(days, pp, od); m70 = pp >= .7
        R[nm] = {"oneri_ll": round(float(bll(pp, y).mean()), 5), "oneri_isabet": round(float(y.mean()), 4),
                 "guclu_n": int(m70.sum()), "guclu_hit": round(float(y[m70].mean()), 4) if m70.any() else None,
                 "altin_n": int(g.sum()), "altin_hit": round(float(y[g].mean()), 4) if g.any() else None}
    a, c = R["aday"], R["mevcut"]
    R["gecti"] = bool(hi < 0 and (a["guclu_hit"] or 0) >= (c["guclu_hit"] or 0) - 1e-9
                      and (a["altin_hit"] is None or c["altin_hit"] is None or a["altin_hit"] >= c["altin_hit"] - 1e-9)
                      and a["oneri_ll"] <= c["oneri_ll"] + 1e-9)
    return R

# ------------------------------------------------------------------ çalıştırıcı
HIST_DILIM = [("2024-07-01", "2025-07-01"), ("2025-07-01", "9999")]

def _sub(a, ix): return [a[i] for i in ix] if isinstance(a, list) else a[ix]

def altin_varyant(days, pp, od, y):
    out = []
    for pmin, olo, cap in ((.78, 1.15, 3), (.80, 1.15, 3), (.75, 1.15, 3), (.78, 1.20, 3), (.78, 1.10, 3), (.78, 1.15, 5)):
        m = np.zeros(len(pp), bool); by = collections.defaultdict(list)
        for i in np.where((pp >= pmin) & (od >= olo) & (od <= 2.0))[0]: by[days[i]].append(i)
        for L in by.values():
            for i in sorted(L, key=lambda i: -pp[i])[:cap]: m[i] = True
        out.append({"kural": f"p≥{pmin:.2f}, oran {olo:.2f}–2,00, günde ≤{cap}", "n": int(m.sum()),
                    "isabet": round(float(y[m].mean()), 4) if m.any() else None, "beklenen": round(float(pp[m].mean()), 4) if m.any() else None})
    return out

def main():
    t0 = time.time(); P = params()
    A = load_archive(); H = load_hist()
    SA = served_full([r["ms"] for r in A], [r["ou"] if r.get("ou") and all(r["ou"]) else None for r in A], P)
    SH = served_full([m["odds"] for m in H], [m["ou"] for m in H], P)
    print(f"veri: arşiv {len(A)} · geçmiş {len(H)} · {time.time() - t0:.0f} sn", flush=True)
    R = {"tarih": time.strftime("%Y-%m-%d"), "motor": (jl(os.path.join(DATA, "model.json")) or {}).get("engine"),
         "yontem": "Sunulan olasılık (piyasa yolu, model.json ayarları). Adaylar yalnız sınama diliminden ÖNCEKİ veriyle öğrenilir; "
                   "kapı: birincil log-kayıp Δ'sının eşleştirilmiş blok bootstrap %95 GA üst sınırı < 0, güçlü (≥%70) ve Altın isabeti ile "
                   "öneri log-kaybı kötüleşmiyor; iki ayrı zaman diliminin ikisinde de."}
    # 1) zayıf noktalar
    ams, aou, ares, aov, abt, akg, aires, aht = arrays_arc(A)
    R["zayif_arsiv"], (k2, pp2, od2, y2) = weak_tables(SA, [r["_d"] for r in A], ams, aou, ares, aov, abt, akg, aires, aht, [r.get("c") or r.get("cc") for r in A])
    hd = np.array([m["d"] for m in H]); hlg = [m["lg"] for m in H]
    hms, hou, hres, hov, hbt, hkg, hires, hht = arrays_hist(H)
    ix = np.where(hd >= HIST_DILIM[0][0])[0]
    R["zayif_gecmis"], (k1, pp1, od1, y1) = weak_tables({k: v[ix] for k, v in SH.items()}, list(hd[ix]), _sub(hms, ix), _sub(hou, ix), hres[ix], hov[ix],
                                                        hbt[ix], hkg[ix], hires[ix], hht[ix], _sub(hlg, ix))
    R["zayif_gecmis"]["kapsam"] = f"{HIST_DILIM[0][0]} sonrası lig maçları (derin arşiv + sezon)"
    R["predlog"] = predlog_tables()
    # 2) adaylar
    hh = np.array([x is not None for x in hou]); C = {}
    for name in ("C1", "C3"):
        C[name] = []
        for a, b in HIST_DILIM:
            tr = np.where(hd < a)[0]; te = np.where((hd >= a) & (hd < b))[0]
            q0, O0 = SH["q"][te], SH["O"][te]; q1, O1 = q0, O0
            if name == "C1":
                t2 = tr[hh[tr]]; c = platt_ou_fit(SH["O"][t2], hov[t2]); O1 = platt_ou_apply(O0, c); prim = "ou"
            else:
                t3 = tr[hd[tr] >= f"{int(a[:4]) - 3}{a[4:]}"]
                c = lig_fit(SH["q"][t3], hres[t3], _sub(hlg, t3)); q1 = lig_apply(q0, _sub(hlg, te), c); prim = "ms"; c = {"lig_sayisi": len(c)}
            r = slice_eval(list(hd[te]), list(hd[te]), q0, O0, q1, O1, _sub(hms, te), _sub(hou, te), hres[te], hov[te], prim)
            r.update(param={k: (round(v, 4) if isinstance(v, float) else v) for k, v in c.items()}, dilim=[a, b], n_egitim=int(len(tr))); C[name].append(r)
    # C2: kilitli iddaa arşivi (yüksek marj) — yalnız arşivin kendi geçmişiyle, zaman sıralı
    ad = np.array([r["_d"] for r in A]); ats = np.array([r.get("ts", 0) for r in A]); blk = list(ats // 3600)
    days = sorted(set(ad)); ah = np.array([x is not None for x in aou])
    d2 = days[1] if len(days) > 1 else days[0]; med = np.median(ats[ad == d2])
    S1 = np.where((ad == d2) & (ats < med))[0]; S2 = np.where((ad > d2) | ((ad == d2) & (ats >= med)))[0]
    C["C2"] = []
    for te in (S1, S2):
        tr = np.where(ats < ats[te].min())[0]
        cm = ms_temp_fit(SA["q"][tr], ares[tr]); t2 = tr[ah[tr]]; co = platt_ou_fit(SA["O"][t2], aov[t2])
        q0, O0 = SA["q"][te], SA["O"][te]; q1 = ms_temp_apply(q0, cm); O1 = platt_ou_apply(O0, co)
        r = slice_eval(list(ad[te]), _sub(blk, te), q0, O0, q1, O0, _sub(ams, te), _sub(aou, te), ares[te], aov[te], "ms")
        r_ou = slice_eval(list(ad[te]), _sub(blk, te), q0, O0, q1, O1, _sub(ams, te), _sub(aou, te), ares[te], aov[te], "ou")
        r["ou_birlikte"] = {k: r_ou[k] for k in ("n", "ll_mevcut", "ll_aday", "dll", "ga95", "aday", "gecti")}
        r["gecti"] = bool(r["gecti"] and r_ou["gecti"])
        r.update(param={"MS": {k: round(v, 4) for k, v in cm.items()}, "AU": {k: round(v, 4) for k, v in co.items()}},
                 dilim=[f"ts≥{int(ats[te].min())}"], n_egitim=int(len(tr))); C["C2"].append(r)
    AD = {"C1": "2,5 Alt/Üst için pazar bazlı Platt kalibrasyonu (tüm geçmiş, kimliğe L2)",
          "C2": "Yüksek marjlı iddaa oranında MS sıcaklık+beraberlik ve 2,5 A/Ü Platt (yalnız kilitli arşivin önceki kayıtları)",
          "C3": "Lig bazlı MS ev/beraberlik kaydırması (son 3 yıl, büzülmeli L2, lig başına ≥150 maç)"}
    R["adaylar"] = {k: {"ad": AD[k], "dilimler": v, "kabul": all(x["gecti"] for x in v)} for k, v in C.items()}
    R["baglanan"] = [k for k, v in R["adaylar"].items() if v["kabul"]]
    # 3) Altın kural (yalnız öneri; motor değiştirmez)
    R["altin_varyant"] = {"gecmis": altin_varyant(list(hd[ix]), pp1, od1, y1), "arsiv": altin_varyant([r["_d"] for r in A], pp2, od2, y2)}
    json.dump(R, open(os.path.join(DATA, "fb_gelistir.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, allow_nan=False)
    for k, v in R["adaylar"].items():
        print(k, "kabul" if v["kabul"] else "red", [(x["dll"], x["ga95"], x["gecti"]) for x in v["dilimler"]], flush=True)
    print(f"bitti {time.time() - t0:.0f} sn", flush=True)

if __name__ == "__main__":
    main()
