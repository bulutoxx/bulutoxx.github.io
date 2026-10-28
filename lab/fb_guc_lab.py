#!/usr/bin/env python3
"""🧪 Güç puanları + topluluk laboratuvarı (oransız maçlar). Zaman sıralı ileri yürüyüş, lig×gün blok bootstrap'ı.

Alanlar:
  espn   Oranı hiç olmayan ligler (season.json src=espn; fikstürde oransız maçların neredeyse tamamı). Asıl hedef.
  derin  Oranlı ligler (derin arşiv 2021+ ve season.json). Model yolu (piyasa yok sayılarak) + piyasa ile yığınlama ölçümü.

Protokol (önceden kayıtlı):
  • Durumlar (Poisson haftalık yeniden eğitim, Elo, pi, GAS — YH-11 scripts/gas.py) yalnız maçtan önceki sonuçlarla ilerler.
  • Uygunluk: ligde eğitimde ≥45 maç, iki takımın da ≥3 önceki maçı (motorun backtest kuralı).
  • Seçim dilimi S: SINIR tarihinden önce (ayar ızgarası burada seçilir). Sınama dilimi T: SINIR ve sonrası (yalnız rapor).
  • Yığınlayıcı ağırlıkları aylık genişleyen pencereyle yalnız GEÇMİŞ aylarla öğrenilir.
  • Kapı (üretim): T'de ΔLL (aday − üretim) %95 GA üst sınırı < 0, T'nin iki yarısında da ΔLL < 0, ΔBrier ≤ 0;
    tek yanlı bootstrap p ≤ α_t (alfa yatırımı, lab/oxx_ogren.yatirim_alfa; alan "fb_model").
  • YH-11: C7 GAS, C8 topluluk+GAS; kiyas_c4 = mevcut topluluğa (C4) göre fark (gas_1x2 / gas_ou kapısının tabanı).
Çıktı: data/fb_guc_lab.json (karne) ve --uret ile data/fb_guc.json (yalnız kapıyı geçerse aktif=true).

  python3 lab/fb_guc_lab.py espn [--uret]
  python3 lab/fb_guc_lab.py derin
"""
import argparse, collections, json, math, os, sys, time
from datetime import date, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import update as U  # noqa: E402
import guc as G  # noqa: E402
import gas as GS  # noqa: E402

T0 = time.time()
RNG = np.random.default_rng(20261027)
B_BOOT = 2000


def log(*a): print(f"[{time.time() - T0:6.0f} sn]", *a, flush=True)


def sonuc(ft): return 0 if ft[0] > ft[1] else 1 if ft[0] == ft[1] else 2


# ------------------------------------------------------------------ veri
def lig_maclari(alan, S):
    out = {}
    if alan == "espn":
        for lg, d in S.items():
            if d.get("cup") or d.get("src") != "espn": continue
            ms = [dict(m) for m in d["matches"] if m.get("ft") and None not in m["ft"][:2]]
            out[lg] = sorted(ms, key=lambda m: (m["d"], m["h"]))
    else:
        import glob
        for lg, d in S.items():
            if d.get("cup") or d.get("src") == "espn": continue
            ms = [dict(m) for m in d["matches"] if m.get("ft") and None not in m["ft"][:2]]
            first = min(m["d"] for m in ms) if ms else "9999"
            for f in sorted(glob.glob(os.path.join(DATA, "derin", f"{lg}-*.json"))):
                D = json.load(open(f, encoding="utf-8"))
                for r in D.get("m", []):
                    if r[0] >= first or r[3] is None or r[4] is None: continue
                    m = {"d": r[0], "h": r[1], "a": r[2], "ft": [r[3], r[4]], "season": D.get("sezon")}
                    if r[5] and r[6] and r[7]: m["odds"] = [r[5], r[6], r[7]]
                    if r[8] and r[9]: m["ou"] = [r[8], r[9]]
                    ms.append(m)
            ms = sorted(ms, key=lambda m: (m["d"], m["h"]))
            U.market_xg([m for m in ms if m.get("odds")])
            out[lg] = ms
    return out


# ------------------------------------------------------------------ Poisson ileri yürüyüş
def uygun_ve_hafta(ms, pencere):
    """Her maç için (hafta başlangıcı, uygun mu). Uygunluk konfigürasyondan bağımsız."""
    hafta = collections.OrderedDict()
    for i, m in enumerate(ms):
        dd = date.fromisoformat(m["d"]); hafta.setdefault(dd - timedelta(days=dd.weekday()), []).append(i)
    uy = np.zeros(len(ms), bool)
    for wk, idx in hafta.items():
        lo = (wk - timedelta(days=pencere)).isoformat(); cut = wk.isoformat()
        train = [m for m in ms if lo <= m["d"] < cut]
        if len(train) < 45: continue
        cnt = collections.Counter([m["h"] for m in train] + [m["a"] for m in train])
        for i in idx:
            if cnt[ms[i]["h"]] >= 3 and cnt[ms[i]["a"]] >= 3: uy[i] = True
    return hafta, uy


def poisson_wf(ms, hafta, uy, P, pencere):
    lam = np.full((len(ms), 2), np.nan); init = None
    for wk, idx in hafta.items():
        if not uy[idx].any(): continue
        lo = (wk - timedelta(days=pencere)).isoformat(); cut = wk.isoformat()
        train = [m for m in ms if lo <= m["d"] < cut]
        F = U.fit(train, wk, P, init, iters=12 if init else 30); init = F["t"]
        for i in idx:
            if not uy[i]: continue
            (ah, dh), (aa, da) = F["t"][ms[i]["h"]], F["t"][ms[i]["a"]]
            lam[i] = (F["mu"] * F["gamma"] * ah * da, F["mu"] * aa * dh)
    return lam


# ------------------------------------------------------------------ ölçüt ve bootstrap
def ll3(P, y): return -np.log(np.clip(P[np.arange(len(y)), y], 1e-9, 1))
def br3(P, y): return ((P - np.eye(3)[y]) ** 2).sum(1)
def ll2(p, y): p = np.clip(p, 1e-6, 1 - 1e-6); return -(y * np.log(p) + (1 - y) * np.log(1 - p))
def br2(p, y): return (p - y) ** 2


def blok_boot(delta, blok, B=B_BOOT):
    """lig×gün blokları üzerinde eşleştirilmiş bootstrap. Dönüş: ortalama, %95 GA, tek yanlı p (Δ ≥ 0)."""
    u, inv = np.unique(blok, return_inverse=True)
    s = np.bincount(inv, delta, len(u)); n = np.bincount(inv, None, len(u))
    idx = RNG.integers(0, len(u), (B, len(u)))
    bs = s[idx].sum(1) / n[idx].sum(1)
    return {"fark": round(float(delta.mean()), 5), "ga95": [round(float(np.quantile(bs, .025)), 5), round(float(np.quantile(bs, .975)), 5)],
            "p_tek": round(float((bs >= 0).mean()), 4), "n": int(len(delta)), "blok": int(len(u))}


def ozet(P, y, o=None, yo=None):
    r = {"n": int(len(y)), "ll": round(float(ll3(P, y).mean()), 5), "brier": round(float(br3(P, y).mean()), 5),
         "isabet": round(float((P.argmax(1) == y).mean()), 4)}
    if o is not None:
        r.update(ou_ll=round(float(ll2(o, yo).mean()), 5), ou_brier=round(float(br2(o, yo).mean()), 5),
                 ou_isabet=round(float(((o >= .5) == yo).mean()), 4))
    return r


# ------------------------------------------------------------------ ana akış
def calistir(alan, sinir, uret=False):
    S = json.load(open(os.path.join(DATA, "season.json"), encoding="utf-8"))
    M = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8")); P = dict(M["params"])
    Lg = lig_maclari(alan, S); del S
    pencere = 450 if alan == "espn" else 540
    log(alan, "ligler", len(Lg), "maç", sum(len(v) for v in Lg.values()))
    # Poisson ayar ızgarası (oransız: hedef yalnız gol; derin: üretim hedefi xg karışımı)
    if alan == "espn":
        IZ = [(dc, pr) for dc in (0.003, 0.006, 0.01, 0.018) for pr in (0.3, 2.5, 5.0, 10.0, 20.0)]
    else:
        IZ = [(0.018, 0.3), (0.006, 1.5), (0.003, 4.0)]
    # Üretimdeki (decay, prior) ızgarada yoksa B0 ölçümü için ayrıca hesaplanır; C1 seçimine KATILMAZ (seçim ızgarası önceden kayıtlı).
    b0 = (float(P["decay"]), float(P["prior"]))
    IZ_EK = [] if b0 in IZ else [b0]
    if IZ_EK: log("üretim decay/prior ızgarada yok → B0 için ayrıca hesaplanıyor:", b0)
    ELO = [(K, eta) for K in (20, 30, 40, 55, 75) for eta in (0.0, 1.0, 2.0)]
    PI = [(lm, gm) for lm in (0.035, 0.06, 0.1, 0.15, 0.22) for gm in (0.5, 0.7, 0.9)]
    GAZ = [(A_, B_) for A_ in (0.006, 0.01, 0.015, 0.025, 0.04) for B_ in (0.99, 0.995, 0.998, 1.0)]     # YH-11 GAS (adım, kalıcılık)
    R = collections.defaultdict(list)    # sütun → liste
    for lg, ms in Lg.items():
        hafta, uy = uygun_ve_hafta(ms, pencere)
        if uy.sum() < 20: continue
        lams = {}
        for dc, pr in IZ + IZ_EK:
            PP = dict(P, decay=dc, prior=pr)
            lams[(dc, pr)] = poisson_wf(ms, hafta, uy, PP, pencere)
        elos = {k: np.array(G.elo_seq(ms, {"K": k[0], "eta": k[1]})[0]) for k in ELO}
        pis = {k: np.array(G.pi_seq(ms, {"lam": k[0], "gam": k[1]})[0]) for k in PI}
        gass = {k: np.array(GS.gas_seq(ms, {"A": k[0], "B": k[1]})[0]) for k in GAZ}
        # lig gol ortalaması (son 300 maç, yalnız geçmiş)
        tot = np.array([m["ft"][0] + m["ft"][1] for m in ms], float); cs = np.concatenate([[0], np.cumsum(tot)])
        og = np.array([(cs[i] - cs[max(0, i - 300)]) / max(1, i - max(0, i - 300)) if i else 2.6 for i in range(len(ms))])
        ii = np.where(uy)[0]
        for i in ii:
            m = ms[i]
            R["lg"].append(lg); R["d"].append(m["d"]); R["y"].append(sonuc(m["ft"])); R["tot"].append(m["ft"][0] + m["ft"][1])
            R["og"].append(og[i])
            R["odds"].append(m.get("odds")); R["ou"].append(m.get("ou"))
        for k, v in lams.items(): R[("lam",) + k].append(v[ii])
        for k, v in elos.items(): R[("elo",) + k].append(v[ii])
        for k, v in pis.items(): R[("pi",) + k].append(v[ii])
        for k, v in gass.items(): R[("gas",) + k].append(v[ii])
        log(lg, "uygun", int(uy.sum()))
    y = np.array(R["y"]); d = np.array(R["d"]); lgs = np.array(R["lg"]); n = len(y)
    yo = (np.array(R["tot"]) > 2).astype(float); og = np.array(R["og"])
    blok = np.array([f"{a}|{b}" for a, b in zip(lgs, d)])
    for k in list(R):
        if isinstance(k, tuple): R[k] = np.concatenate(R[k])
    Ssel = d < sinir; Tm = ~Ssel
    log("satır", n, "seçim", int(Ssel.sum()), "sınama", int(Tm.sum()))
    rho = P.get("rho", -0.06)

    # --- B0 üretim yolu: decay/prior/kalibrasyon model.json'dan; uygulamanın dist() yolu (gscale, iki yarı DC, calT/dk)
    b0k = ("lam",) + b0
    if b0k not in R:
        raise SystemExit("üretim decay/prior hesaplanamadı (uygun maç yok)")
    L0 = R[b0k]
    p0, o0 = U.served_probs(L0[:, 0], L0[:, 1], P.get("gscale", 1.0), rho, P.get("h1", .4437))
    p0 = U._cal3(p0, P.get("calT", 1.0), P.get("dk", 1.0))

    # --- C1 Poisson yeniden ayarlı (seçim diliminde en iyi decay/prior; kalibrasyonsuz)
    def pois(k):
        L = R[("lam",) + k]; p, pO, _, _ = U.outcome_probs(L[:, 0], L[:, 1], rho); return p, pO
    izsk = {}
    for k in IZ:
        p, pO = pois(k); izsk[k] = float(ll3(p[Ssel], y[Ssel]).mean())
    k1 = min(izsk, key=izsk.get); p1, o1 = pois(k1)
    log("Poisson ızgarası (seçim LL):", {f"{a}/{b}": round(v, 4) for (a, b), v in izsk.items()}, "→", k1)

    # --- Elo ve pi ayarı: seçim diliminde tek başına lojistik eşlemeyle
    def tek(feat_cols, mask):
        X = np.stack([np.ones(n)] + feat_cols, 1); W = G.mlogit_fit(X[mask], y[mask], l2=1.0)
        return float(ll3(G.mlogit_pred(X[mask], W), y[mask]).mean())
    esk = {k: tek([R[("elo",) + k] / 400, np.abs(R[("elo",) + k] / 400)], Ssel) for k in ELO}
    ke = min(esk, key=esk.get)
    psk = {k: tek([np.clip(R[("pi",) + k], -4, 4), np.abs(np.clip(R[("pi",) + k], -4, 4))], Ssel) for k in PI}
    kp = min(psk, key=psk.get)
    log("Elo ızgarası:", {f"{a}/{b}": round(v, 4) for (a, b), v in esk.items()}, "→", ke)
    log("pi ızgarası:", {f"{a}/{b}": round(v, 4) for (a, b), v in psk.items()}, "→", kp)
    E = R[("elo",) + ke]; PIg = R[("pi",) + kp]
    # --- YH-11 GAS: λ → Dixon-Coles olasılıkları; seçim diliminde tek başına lojistik eşlemeyle ayar
    gpr = {}
    for k in GAZ:
        L = R[("gas",) + k]; q, qO, _, _ = U.outcome_probs(L[:, 0], L[:, 1], rho); gpr[k] = (q, qO)
    gsk = {k: tek(list(G.ozellik_1x2(None, None, None, ("gas",), gpr[k][0])[:, 1:].T), Ssel) for k in GAZ}
    kg = min(gsk, key=gsk.get); GP, GO = gpr[kg]
    log("GAS ızgarası:", {f"{a}/{b}": round(v, 4) for (a, b), v in gsk.items()}, "→", kg)

    # --- aylık genişleyen yığınlama
    aylar = sorted({x[:7] for x in d})
    def yigin(kullan, ou=False, min_n=800, l2=1.0, Xou=None):
        out = np.full((n, 3), np.nan) if not ou else np.full(n, np.nan); W = None
        X = G.ozellik_1x2(p1, E, PIg, kullan, GP) if not ou else (G.ozellik_ou(o1, PIg, og) if Xou is None else Xou)
        for ay in aylar:
            tr = d < ay + "-01"; te = np.array([x[:7] == ay for x in d])
            if tr.sum() < min_n: continue
            if ou: W = G.logit_fit(X[tr], yo[tr], l2=l2); out[te] = G.logit_pred(X[te], W)
            else: W = G.mlogit_fit(X[tr], y[tr], l2=l2); out[te] = G.mlogit_pred(X[te], W)
        return out, W
    adaylar = {}
    # referans: taban oranları (geçmiş ayların 1/X/2 ve 2,5 üst sıklığı)
    tb = np.full((n, 3), np.nan); tbo = np.full(n, np.nan)
    for ay in aylar:
        tr = d < ay + "-01"; te = np.array([x[:7] == ay for x in d])
        if tr.sum() < 300: continue
        tb[te] = np.bincount(y[tr], None, 3) / tr.sum(); tbo[te] = yo[tr].mean()
    adaylar["R0 taban oranları (referans)"] = (tb, tbo)
    adaylar["C1 Poisson yeniden ayarlı"] = (p1, o1)
    # C1s: aynı Poisson, uygulamanın dist() yolundan (gscale, iki yarı DC, calT/dk) — ratings.json'a yazılırsa istemcinin göstereceği
    L1 = R[("lam",) + k1]
    p1s, o1s = U.served_probs(L1[:, 0], L1[:, 1], P.get("gscale", 1.0), rho, P.get("h1", .4437))
    p1s = U._cal3(p1s, P.get("calT", 1.0), P.get("dk", 1.0))
    adaylar["C1s Poisson yeniden ayarlı (uygulama yolu)"] = (p1s, o1s)
    for ad, ku in (("C1k Poisson + yığın kalibrasyonu", ("pois",)), ("C2 Elo", ("elo",)), ("C3 pi-rating", ("pi",)),
                   ("C4 Topluluk (Poisson+Elo+pi)", ("pois", "elo", "pi")), ("C5 Poisson+pi", ("pois", "pi")), ("C6 Poisson+Elo", ("pois", "elo"))):
        q, W = yigin(ku); adaylar[ad] = (q, None); adaylar[ad + "|W"] = W
    qo, Wo = yigin(None, ou=True)
    # YH-11: GAS adayları (C7 tek başına, C8 mevcut topluluk + GAS); A/Ü: topluluk girdilerine GAS üst logiti eklenir
    Xog = G.ozellik_ou(o1, PIg, og, GO)
    for ad, ku in (("C7 GAS", ("gas",)), ("C8 Topluluk+GAS (Poisson+Elo+pi+GAS)", ("pois", "elo", "pi", "gas"))):
        q, W = yigin(ku); adaylar[ad] = (q, None); adaylar[ad + "|W"] = W
    qog, Wog = yigin(None, ou=True, Xou=Xog)
    qo7, _ = yigin(None, ou=True, Xou=Xog[:, [0, 4, 3]])
    OU_ADAY = {"C4": qo, "C7 GAS": qo7, "C8 Topluluk+GAS (Poisson+Elo+pi+GAS)": qog}
    # yalnız yığınlayıcının tanımlı olduğu ve sınama dilimindeki satırlar
    ok = (Tm & ~np.isnan(adaylar["C4 Topluluk (Poisson+Elo+pi)"][0][:, 0]) & ~np.isnan(qo) & ~np.isnan(tb[:, 0])
          & ~np.isnan(adaylar["C8 Topluluk+GAS (Poisson+Elo+pi+GAS)"][0][:, 0]) & ~np.isnan(qog))
    log("değerlendirme satırı", int(ok.sum()))
    yarim = np.median(np.where(ok)[0]) if ok.any() else 0
    dT = d[ok]; sinir2 = sorted(dT)[len(dT) // 2] if len(dT) else sinir
    karne = {"alan": alan, "tarih": date.today().isoformat(), "sinir": sinir, "yarilar_siniri": sinir2,
             "n_satir": int(n), "n_secim": int(Ssel.sum()), "n_sinama": int(ok.sum()), "lig": sorted(set(lgs.tolist())),
             "secilen": {"poisson": {"decay": k1[0], "prior": k1[1]}, "elo": {"K": ke[0], "eta": ke[1]}, "pi": {"lam": kp[0], "gam": kp[1]}, "gas": {"A": kg[0], "B": kg[1]}},
             "izgara": {"poisson": {f"{a}/{b}": round(v, 5) for (a, b), v in izsk.items()},
                        "elo": {f"{a}/{b}": round(v, 5) for (a, b), v in esk.items()}, "pi": {f"{a}/{b}": round(v, 5) for (a, b), v in psk.items()},
                        "gas": {f"{a}/{b}": round(v, 5) for (a, b), v in gsk.items()}},
             "modeller": {}, "kiyas": {}}
    karne["modeller"]["B0 üretim (model yolu)"] = ozet(p0[ok], y[ok], o0[ok], yo[ok])
    l0 = ll3(p0[ok], y[ok]); b0 = br3(p0[ok], y[ok]); lo0 = ll2(o0[ok], yo[ok]); bo0 = br2(o0[ok], yo[ok])
    h2 = dT >= sinir2
    for ad, v in adaylar.items():
        if ad.endswith("|W"): continue
        q, oo = v
        oo = qo if ad.startswith("C4") else OU_ADAY.get(ad, oo)
        karne["modeller"][ad] = ozet(q[ok], y[ok], oo[ok] if oo is not None else None, yo[ok] if oo is not None else None)
        dl = ll3(q[ok], y[ok]) - l0; db = br3(q[ok], y[ok]) - b0
        k = {"ll": blok_boot(dl, blok[ok]), "brier": blok_boot(db, blok[ok]),
             "ll_yari1": round(float(dl[~h2].mean()), 5), "ll_yari2": round(float(dl[h2].mean()), 5)}
        if oo is not None:
            k["ou_ll"] = blok_boot(ll2(oo[ok], yo[ok]) - lo0, blok[ok]); k["ou_brier"] = blok_boot(br2(oo[ok], yo[ok]) - bo0, blok[ok])
            do = ll2(oo[ok], yo[ok]) - lo0; k["ou_ll_yari1"] = round(float(do[~h2].mean()), 5); k["ou_ll_yari2"] = round(float(do[h2].mean()), 5)
        karne["kiyas"][ad] = k
        log(f"{ad:38s} LL {karne['modeller'][ad]['ll']:.4f} ΔLL {k['ll']['fark']:+.5f} {k['ll']['ga95']} yarılar {k['ll_yari1']:+.4f}/{k['ll_yari2']:+.4f}"
            + (f" | A/Ü ΔLL {k['ou_ll']['fark']:+.5f} {k['ou_ll']['ga95']}" if oo is not None else ""))
    log("B0", karne["modeller"]["B0 üretim (model yolu)"])
    # lig bazında (C4 − B0)
    c4 = adaylar["C4 Topluluk (Poisson+Elo+pi)"][0]
    dl4 = ll3(c4[ok], y[ok]) - l0
    # --- YH-11: GAS adaylarının MEVCUT TOPLULUK (C4) karşısındaki farkı (gas_1x2 / gas_ou kapısının tabanı)
    lc4 = ll3(c4[ok], y[ok]); bc4 = br3(c4[ok], y[ok]); loc4 = ll2(qo[ok], yo[ok]); boc4 = br2(qo[ok], yo[ok])
    karne["kiyas_c4"] = {}
    for ad in ("C7 GAS", "C8 Topluluk+GAS (Poisson+Elo+pi+GAS)"):
        q = adaylar[ad][0][ok]; oo = OU_ADAY[ad][ok]
        dl = ll3(q, y[ok]) - lc4; do = ll2(oo, yo[ok]) - loc4
        karne["kiyas_c4"][ad] = {"ll": blok_boot(dl, blok[ok]), "brier": blok_boot(br3(q, y[ok]) - bc4, blok[ok]),
                                 "ll_yari1": round(float(dl[~h2].mean()), 5), "ll_yari2": round(float(dl[h2].mean()), 5),
                                 "isabet_fark": round(float((q.argmax(1) == y[ok]).mean() - (c4[ok].argmax(1) == y[ok]).mean()), 4),
                                 "ou_ll": blok_boot(do, blok[ok]), "ou_brier": blok_boot(br2(oo, yo[ok]) - boc4, blok[ok]),
                                 "ou_ll_yari1": round(float(do[~h2].mean()), 5), "ou_ll_yari2": round(float(do[h2].mean()), 5)}
        kk = karne["kiyas_c4"][ad]
        log(f"[C4 tabanı] {ad:36s} ΔLL {kk['ll']['fark']:+.5f} {kk['ll']['ga95']} yarılar {kk['ll_yari1']:+.4f}/{kk['ll_yari2']:+.4f} ΔBr {kk['brier']['fark']:+.5f}"
            f" | A/Ü ΔLL {kk['ou_ll']['fark']:+.5f} {kk['ou_ll']['ga95']} yarılar {kk['ou_ll_yari1']:+.4f}/{kk['ou_ll_yari2']:+.4f} ΔBr {kk['ou_brier']['fark']:+.5f}")
    karne["lig_bazinda"] = {lg: {"n": int((lgs[ok] == lg).sum()), "dLL": round(float(dl4[lgs[ok] == lg].mean()), 4)} for lg in sorted(set(lgs[ok].tolist()))}

    # --- derin alan: piyasa kıyası (yalnız ölçüm)
    if alan == "derin":
        hasO = np.array([o is not None for o in R["odds"]]) & ok
        pm = np.array([U.power_devig(o) if o is not None else [np.nan] * 3 for o in R["odds"]])
        X4 = G.ozellik_1x2(p1, E, PIg)
        Xm = np.concatenate([X4, np.log(np.clip(pm, 1e-6, 1))[:, [0]] - np.log(np.clip(pm, 1e-6, 1))[:, [2]],
                             np.log(np.clip(pm, 1e-6, 1))[:, [1]] - (np.log(np.clip(pm, 1e-6, 1))[:, [0]] + np.log(np.clip(pm, 1e-6, 1))[:, [2]]) / 2], 1)
        qm = np.full((n, 3), np.nan); qmo = np.full((n, 3), np.nan)
        Xmo = Xm[:, [0, 7, 8]]
        hasAll = np.array([o is not None for o in R["odds"]])
        for ay in aylar:
            tr = (d < ay + "-01") & hasAll; te = np.array([x[:7] == ay for x in d]) & hasAll
            if tr.sum() < 2000 or not te.any(): continue
            W = G.mlogit_fit(Xm[tr], y[tr]); qm[te] = G.mlogit_pred(Xm[te], W)
            W2 = G.mlogit_fit(Xmo[tr], y[tr]); qmo[te] = G.mlogit_pred(Xmo[te], W2)
        okm = hasO & ~np.isnan(qm[:, 0])
        lm = ll3(pm[okm], y[okm])
        karne["piyasa"] = {"n": int(okm.sum()), "piyasa": ozet(pm[okm], y[okm]), "piyasa_kalibre (yalnız piyasa yığını)": ozet(qmo[okm], y[okm]),
                           "piyasa+topluluk yığını": ozet(qm[okm], y[okm]), "topluluk (piyasasız)": ozet(c4[okm], y[okm]),
                           "fark_yigin_piyasa": blok_boot(ll3(qm[okm], y[okm]) - lm, blok[okm]),
                           "fark_yigin_piyasakal": blok_boot(ll3(qm[okm], y[okm]) - ll3(qmo[okm], y[okm]), blok[okm]),
                           "fark_topluluk_piyasa": blok_boot(ll3(c4[okm], y[okm]) - lm, blok[okm])}
        log("piyasa kıyası:", json.dumps(karne["piyasa"], ensure_ascii=False))

    # --- kapı (önceden kayıtlı) — yalnız espn alanında üretim adayı
    kapi = {}
    for ad, k in karne["kiyas"].items():
        g = (k["ll"]["ga95"][1] < 0 and k["ll_yari1"] < 0 and k["ll_yari2"] < 0 and k["brier"]["fark"] <= 0)
        kapi[ad] = {"gecti_ham": bool(g), "p_tek": k["ll"]["p_tek"]}
    karne["kapi_ham"] = kapi
    # üretim ağırlıkları: kapı ileri yürüyüşle ölçüldü; yayına giden ağırlık tüm uygun satırlarla (yalnız geçmiş) öğrenilir
    Xall = G.ozellik_1x2(p1, E, PIg); W_tum = G.mlogit_fit(Xall, y); Wo_tum = G.logit_fit(G.ozellik_ou(o1, PIg, og), yo)
    Xg = G.ozellik_1x2(p1, E, PIg, ("pois", "elo", "pi", "gas"), GP)
    son = {"W": adaylar["C4 Topluluk (Poisson+Elo+pi)|W"], "Wo": Wo, "k1": k1, "ke": ke, "kp": kp, "W_tum": W_tum, "Wo_tum": Wo_tum,
           "kg": kg, "W_gas": adaylar["C8 Topluluk+GAS (Poisson+Elo+pi+GAS)|W"], "Wo_gas": Wog,
           "W_gas_tum": G.mlogit_fit(Xg, y), "Wo_gas_tum": G.logit_fit(Xog, yo),
           "son_tarih": max(d.tolist())}
    return karne, son


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("alan", choices=["espn", "derin"])
    ap.add_argument("--sinir", default=None)
    ap.add_argument("--cikti", default=None)
    ar = ap.parse_args()
    sinir = ar.sinir or ("2026-04-01" if ar.alan == "espn" else "2025-07-01")
    karne, son = calistir(ar.alan, sinir)
    cik = ar.cikti or os.path.join(DATA, f"fb_guc_lab_{ar.alan}.json")
    karne["son_agirlik"] = {"W": np.asarray(son["W"]).round(5).tolist() if son["W"] is not None else None,
                            "Wo": np.asarray(son["Wo"]).round(5).tolist() if son["Wo"] is not None else None}
    json.dump(karne, open(cik, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("yazıldı", cik)


if __name__ == "__main__":
    main()
