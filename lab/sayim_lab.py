#!/usr/bin/env python3
"""🧪 YH-18 · Gol sayısı dağılımında aşırı/eksik yayılım (model yolu, oransız ligler). Yalnız ölçüm; üretimi değiştirmez.

Soru: Model yolundaki Poisson marjinalleri (aynı λ, aynı Dixon-Coles) yerine yayılımı ayrı parametreyle öğrenen bir sayım
dağılımı gol pazarlarını iyileştiriyor mu?
  NB   negatif binom (aşırı yayılım; r → ∞ Poisson)
  CMP  Conway–Maxwell–Poisson (ν > 1 eksik, ν < 1 aşırı yayılım; ν = 1 Poisson)
  WB   Weibull sayım (Weibull bekleme süreli yenileme süreci; c = 1 Poisson) — Boshnakov, Kharrat, McHale (2017)
Her aday ortalamayı korur (λ aynı, yalnız şekil değişir): ortalama eşlemeli tablo + doğrusal ara değer.

Protokol (önceden kayıtlı):
  • λ: üretimdeki oransız Poisson (fb_guc.json poisson_oransiz decay/prior) ile haftalık ileri yürüyüş (lab/fb_guc_lab.py ile aynı).
  • Ortak ızgara: λ·gscale, Dixon-Coles ρ (model.json), 0..10 gol. Taban = aynı ızgarada Poisson marjinaller.
  • Şekil parametresi her ay için yalnız ÖNCEKİ ayların sonuçlarıyla (genişleyen pencere, en az 1500 maç) skor LL'si en küçük
    ızgara değeri olarak seçilir. Sınama dilimi: SINIR ve sonrası.
  • Kapı (SK, birincil pazar 2,5 A/Ü): ΔLL %95 GA üst < 0 (lig×gün blok bootstrap B = 2000), iki yarıda ΔLL < 0, ΔBrier ≤ 0,
    tek yanlı p ≤ α_t (alfa yatırımı "fb_model-<yıl>", sinyalli aday payı). Ek koşul: net skor LL ve 1X2 LL kötüleşmiyor (fark ≤ 0).
Çıktı: data/sayim_lab.json

  python3 lab/sayim_lab.py [--sinir 2026-04-01]            # karar alanı (oransız)
  python3 lab/sayim_lab.py --alan derin --sinir 2025-07-01  # sağlamlık (oranlı ligler, model yolu)
"""
import argparse, collections, json, math, os, sys, time
from datetime import date

import numpy as np
from scipy.signal import fftconvolve as _fc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import update as U  # noqa: E402
import fb_guc_lab as FL  # noqa: E402

T0 = time.time()
K = 10
KK = np.arange(K + 1)
LF = np.array([math.lgamma(i + 1) for i in KK])


def log(*a): print(f"[{time.time() - T0:6.0f} sn]", *a, flush=True)


# ------------------------------------------------------------------ sayım dağılımları (ortalama eşlemeli tablolar)
def pois_pmf(mu):
    return np.exp(-mu[:, None] + KK[None] * np.log(np.maximum(mu[:, None], 1e-12)) - LF[None])


def nb_pmf(mu, r):
    if r is None: return pois_pmf(mu)
    lg = (np.array([math.lgamma(r + k) for k in KK])[None] - math.lgamma(r) - LF[None]
          + r * np.log(r / (r + mu[:, None])) + KK[None] * np.log(np.maximum(mu[:, None], 1e-12) / (r + mu[:, None])))
    return np.exp(lg)


def _tablo(fn, mus):
    """fn(μ ızgarası) → (ortalama, pmf[0..K]); ortalama monoton → λ ile ara değer."""
    P = fn(mus); P = P / P.sum(1, keepdims=True)
    return (P * KK[None]).sum(1), P


def cmp_tablo(nu):
    mus = np.exp(np.linspace(np.log(0.01), np.log(60.0), 1500))
    def fn(m):
        j = np.arange(60); lg = j[None] * np.log(m[:, None]) - nu * np.array([math.lgamma(i + 1) for i in j])[None]
        lg -= lg.max(1, keepdims=True); p = np.exp(lg); p /= p.sum(1, keepdims=True)
        return p[:, :K + 1]
    return _tablo(fn, mus)


def wb_tablo(c, h=1 / 4000):
    """Weibull bekleme süreli yenileme sürecinde N(1) dağılımı: S_x = x bekleme süresinin toplamı, P(N ≥ x) = P(S_x ≤ 1)."""
    n = int(round(1 / h)); t = np.arange(n + 1) * h
    scales = np.exp(np.linspace(np.log(0.02), np.log(30.0), 500))      # birim zamanda beklenen olay ~ ölçek
    rows = []
    for s in scales:
        # bekleme süresi Weibull(c, ölçek θ); E[T] = θ Γ(1+1/c) ≈ 1/s
        th = 1 / (s * math.gamma(1 + 1 / c))
        F = 1 - np.exp(-(t / th) ** c); f = np.diff(F)               # [0,1] ızgarasında kütle (1'in ötesi önemsiz)
        cdf = [np.ones(1)]; cur = f.copy(); cdfs = [1.0]
        for _ in range(K + 1):
            cdfs.append(float(cur.sum()))                             # P(S_x ≤ 1)
            cur = _fc(cur, f)[:n]
        ge = np.array(cdfs[:K + 2])                                   # P(N ≥ x), x = 0..K+1
        p = np.maximum(ge[:-1] - ge[1:], 0); p[-1] = max(0.0, ge[K]); rows.append(p)
    P = np.array(rows); P = P / P.sum(1, keepdims=True)
    return (P * KK[None]).sum(1), P


def ara(tab, lam):
    mean, P = tab
    o = np.argsort(mean); mean, P = mean[o], P[o]
    out = np.stack([np.interp(lam, mean, P[:, k]) for k in range(K + 1)], 1)
    return out / out.sum(1, keepdims=True)


def dc_izgara(a, b, l1, l2, rho):
    g = a[:, :, None] * b[:, None, :]
    g[:, 0, 0] *= np.maximum(1 - l1 * l2 * rho, 0); g[:, 0, 1] *= 1 + l1 * rho; g[:, 1, 0] *= 1 + l2 * rho; g[:, 1, 1] *= 1 - rho
    g = np.maximum(g, 0); return g / g.sum((1, 2), keepdims=True)


I, J = np.meshgrid(KK, KK, indexing="ij")


def pazarlar(g, fh, fa):
    n = len(g); r = np.arange(n)
    p3 = np.stack([(g * (I > J)).sum((1, 2)), (g * (I == J)).sum((1, 2)), (g * (I < J)).sum((1, 2))], 1)
    tot = I + J
    return {"skor": g[r, np.minimum(fh, K), np.minimum(fa, K)], "p3": p3,
            "o15": (g * (tot > 1)).sum((1, 2)), "o25": (g * (tot > 2)).sum((1, 2)), "o35": (g * (tot > 3)).sum((1, 2)),
            "kg": g[:, 1:, 1:].sum((1, 2))}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sinir", default="2026-04-01"); ap.add_argument("--cikti", default=None); ap.add_argument("--alan", default="espn", choices=["espn", "derin"])
    ar = ap.parse_args()
    S = json.load(open(os.path.join(DATA, "season.json"), encoding="utf-8"))
    M = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8")); P = dict(M["params"])
    FG = json.load(open(os.path.join(DATA, "fb_guc.json"), encoding="utf-8"))
    po = FG.get("poisson_oransiz") or {}
    if po.get("aktif"): P.update(decay=float(po["decay"]), prior=float(po["prior"]))
    rho = float(P.get("rho", -0.06)); gsc = float(P.get("gscale", 1.0))
    Lg = FL.lig_maclari(ar.alan, S); del S
    pen = 450 if ar.alan == "espn" else 540
    if ar.alan == "derin": P.update(decay=float(M["params"]["decay"]), prior=float(M["params"]["prior"]))   # oranlı ligde üretim model yolu
    log("ligler", len(Lg), "maç", sum(len(v) for v in Lg.values()), "decay/prior", P["decay"], P["prior"])
    R = collections.defaultdict(list)
    for lg, ms in Lg.items():
        hafta, uy = FL.uygun_ve_hafta(ms, pen)
        if uy.sum() < 20: continue
        lam = FL.poisson_wf(ms, hafta, uy, P, pen)
        for i in np.where(uy)[0]:
            m = ms[i]
            R["lg"].append(lg); R["d"].append(m["d"]); R["fh"].append(int(m["ft"][0])); R["fa"].append(int(m["ft"][1]))
            R["l1"].append(lam[i, 0]); R["l2"].append(lam[i, 1])
        log(lg, "uygun", int(uy.sum()))
    d = np.array(R["d"]); lgs = np.array(R["lg"]); fh = np.array(R["fh"]); fa = np.array(R["fa"])
    l1 = np.clip(np.array(R["l1"]), .15, 4.5) * gsc; l2 = np.clip(np.array(R["l2"]), .1, 4) * gsc
    n = len(d); log("satır", n)
    y3 = np.where(fh > fa, 0, np.where(fh == fa, 1, 2)); tot = fh + fa
    blok = np.array([f"{a}|{b}" for a, b in zip(lgs, d)])

    log("tablolar kuruluyor")
    AILE = {"NB": [(r, ("nb", r)) for r in (3.0, 6.0, 12.0, 25.0, 50.0, 100.0)],
            "CMP": [(v, ("cmp", v)) for v in (0.8, 0.9, 0.95, 1.05, 1.1, 1.2, 1.3)],
            "WB": [(c, ("wb", c)) for c in (0.85, 0.92, 1.08, 1.15, 1.25)]}
    MK = {}
    def marj(key, lam):
        if key is None: return pois_pmf(lam)
        t, v = key
        if t == "nb": return nb_pmf(lam, v)
        if key not in MK: MK[key] = cmp_tablo(v) if t == "cmp" else wb_tablo(v)
        return ara(MK[key], lam)
    # doğruluk denetimi: c = 1 Weibull ve ν = 1 CMP Poisson'a eşit olmalı
    tst = np.array([0.4, 1.3, 2.7])
    e_wb = float(np.abs(ara(wb_tablo(1.0), tst) - pois_pmf(tst) / pois_pmf(tst).sum(1, keepdims=True)).max())
    e_cmp = float(np.abs(ara(cmp_tablo(1.0), tst) - pois_pmf(tst) / pois_pmf(tst).sum(1, keepdims=True)).max())
    log("denetim |WB(c=1) − Poisson|", round(e_wb, 5), "|CMP(ν=1) − Poisson|", round(e_cmp, 5))

    def pz(key):
        return pazarlar(dc_izgara(marj(key, l1), marj(key, l2), l1, l2, rho), fh, fa)
    base = pz(None)
    cand = {(a, v): pz(k) for a, L in AILE.items() for v, k in L}
    sk_ll = lambda Z: -np.log(np.clip(Z["skor"], 1e-9, 1))
    l_base = sk_ll(base)
    # aylık genişleyen seçim (yalnız geçmiş)
    aylar = sorted({x[:7] for x in d})
    sec = {a: np.full(n, np.nan) for a in AILE}; secd = {a: {} for a in AILE}
    for ay in aylar:
        tr = d < ay + "-01"; te = np.array([x[:7] == ay for x in d])
        if tr.sum() < 1500: continue
        for a, L in AILE.items():
            sc = {v: float(sk_ll(cand[(a, v)])[tr].mean()) for v, _ in L}; sc[None] = float(l_base[tr].mean())
            b = min(sc, key=sc.get); secd[a][ay] = b
            sec[a][te] = np.nan if b is None else b
            sec[a][te & np.isnan(sec[a])] = -1                       # -1 = Poisson seçildi
    ok = (d >= ar.sinir)
    for a in AILE: ok &= ~np.isnan(sec[a])
    dT = d[ok]; s2 = sorted(dT)[len(dT) // 2]; h2 = dT >= s2
    log("sınama satırı", int(ok.sum()), "yarı sınırı", s2)

    def birles(a):
        """her satırda o ay seçilen parametrenin pazarları"""
        out = {k: (v.copy()) for k, v in base.items()}
        for v, _ in AILE[a]:
            m = sec[a] == v
            for k in out: out[k][m] = cand[(a, v)][k][m]
        return out
    yo = {"o15": (tot > 1).astype(float), "o25": (tot > 2).astype(float), "o35": (tot > 3).astype(float),
          "kg": ((fh > 0) & (fa > 0)).astype(float)}
    def metr(Z):
        r = {"skor_ll": -np.log(np.clip(Z["skor"], 1e-9, 1)), "1x2_ll": FL.ll3(Z["p3"], y3), "1x2_brier": FL.br3(Z["p3"], y3)}
        for k, yy in yo.items(): r[k + "_ll"] = FL.ll2(Z[k], yy); r[k + "_brier"] = FL.br2(Z[k], yy)
        return r
    mb = metr(base)
    karne = {"tarih": date.today().isoformat(), "madde": "YH-18", "alan": ar.alan + (" (oransız ligler, model yolu)" if ar.alan == "espn" else " (oranlı ligler, piyasa yok sayılarak model yolu; yalnız sağlamlık)"), "sinir": ar.sinir,
             "yarilar_siniri": s2, "n_satir": int(n), "n_sinama": int(ok.sum()), "blok": int(len(set(blok[ok]))),
             "parametre": {"decay": P["decay"], "prior": P["prior"], "rho": rho, "gscale": gsc},
             "denetim": {"wb_c1_poisson_maks_fark": round(e_wb, 6), "cmp_nu1_poisson_maks_fark": round(e_cmp, 6)},
             "taban_poisson": {k: round(float(v[ok].mean()), 5) for k, v in mb.items()},
             "gozlenen": {"gol_ort": round(float(tot[ok].mean()), 4), "lam_ort": round(float((l1 + l2)[ok].mean()), 4),
                          "ev_var_ort": round(float(fh[ok].var() / max(fh[ok].mean(), 1e-9)), 4),
                          "dep_var_ort": round(float(fa[ok].var() / max(fa[ok].mean(), 1e-9)), 4),
                          "artik_yayilim_ev": round(float(np.mean((fh[ok] - l1[ok]) ** 2 / l1[ok])), 4),
                          "artik_yayilim_dep": round(float(np.mean((fa[ok] - l2[ok]) ** 2 / l2[ok])), 4)},
             "adaylar": {}, "secim_gecmisi": {a: {k: v for k, v in secd[a].items()} for a in AILE}}
    import oxx_ogren as O
    try: A = json.load(open(os.path.join(DATA, "fb_guc.json"), encoding="utf-8"))
    except Exception: A = {}
    alan_k = f"fb_model-{date.today().year}"
    alfa = O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "literatür (Boshnakov 2017)"}})
    karne["alfa_t"] = round(float(alfa), 5)
    for a in AILE:
        Z = birles(a); mz = metr(Z); r = {"secilen_son": secd[a][max(secd[a])] if secd[a] else None, "fark": {}}
        for k in mb:
            dl = (mz[k] - mb[k])[ok]
            r["fark"][k] = dict(FL.blok_boot(dl, blok[ok]), yari1=round(float(dl[~h2].mean()), 6), yari2=round(float(dl[h2].mean()), 6))
        f = r["fark"]
        g = (f["o25_ll"]["ga95"][1] < 0 and f["o25_ll"]["yari1"] < 0 and f["o25_ll"]["yari2"] < 0 and f["o25_brier"]["fark"] <= 0
             and f["o25_ll"]["p_tek"] <= alfa and f["skor_ll"]["fark"] <= 0 and f["1x2_ll"]["fark"] <= 0)
        r["kapi_gecti"] = bool(g)
        karne["adaylar"][a] = r
        log(f"{a:4s} son seçim {r['secilen_son']} | 2,5 ΔLL {f['o25_ll']['fark']:+.5f} {f['o25_ll']['ga95']} p {f['o25_ll']['p_tek']}"
            f" yarılar {f['o25_ll']['yari1']:+.5f}/{f['o25_ll']['yari2']:+.5f} | skor ΔLL {f['skor_ll']['fark']:+.5f} {f['skor_ll']['ga95']}"
            f" | 1X2 {f['1x2_ll']['fark']:+.5f} | 1,5 {f['o15_ll']['fark']:+.5f} 3,5 {f['o35_ll']['fark']:+.5f} KG {f['kg_ll']['fark']:+.5f}"
            f" → {'GEÇTİ' if g else 'geçmedi'}")
    karne["karar"] = "gecti" if any(v["kapi_gecti"] for v in karne["adaylar"].values()) else "reddedildi"
    log("gözlenen", karne["gozlenen"]); log("karar", karne["karar"])
    cik = ar.cikti or os.path.join(DATA, "sayim_lab.json" if ar.alan == "espn" else "sayim_lab_derin.json")
    json.dump(karne, open(cik, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("yazıldı", cik)


if __name__ == "__main__":
    main()
