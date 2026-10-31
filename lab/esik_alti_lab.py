#!/usr/bin/env python3
"""🧪 YH-21 · Eşik altı maçlar için hiyerarşik Bayes güç önseli — oransız ligler (season.json src=espn).

Soru: üretimin model yolu (update.fit / guc.tahmin) ligde < 45 (yürüyen pencere) maç varken ya da takımlardan biri < 3 maç
oynamışken tahmin yazmaz ("eşik altı"). YH-25'in ampirik Bayes `hb_fit`'i (lig τ², ligler arası önsel) bu maçlarda,
yalnız geçmişle, bir tabana karşı bilgi ekliyor mu?

Önceden kayıtlı tasarım (aşırı uyum yok: hiper parametreler YH-25'te başka maçlarda seçildi, burada ızgara yok):
  • Küme: lig içinde 450 günlük pencerede ≥ 10 ve FL.uygun_ve_hafta'nın uygun SAYMADIĞI maçlar (lig < 45 maç ya da takım < 3 maç).
  • Aday: hb_fit(τ²_0 = 0,03, n0 = 5, tavansız, decay 0,003); hiç görülmemiş takım = update.NEW_TEAM.
  • Taban: o güne kadarki TÜM oransız lig maçlarının havuzlanmış 1X2 ve 2,5 üst sıklığı (sızıntısız).
  • Ek kıyas (bilgi): tek önselli üretim Poisson'u (decay/prior fb_guc.json poisson_oransiz) aynı maçlarda.
  • Kapı (SK, tabana karşı): ΔLL lig×gün blok %95 GA üst < 0, iki zaman yarısında ΔLL < 0, ΔBrier ≤ 0; ayrıca Poisson'a karşı ΔLL ≤ 0.

  python3 lab/esik_alti_lab.py  → data/esik_alti_lab.json
"""
import collections, json, os, sys, time
from datetime import date, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import update as U  # noqa: E402
import fb_guc_lab as FL  # noqa: E402
from hb_guc_lab import hb_fit  # noqa: E402

T0 = time.time()
def log(*a): print(f"[{time.time() - T0:6.0f} sn]", *a, flush=True)

TAU0, N0, PENCERE, MIN_TRAIN = 0.03, 5, 450, 10


def main():
    S = json.load(open(os.path.join(DATA, "season.json"), encoding="utf-8"))
    M = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8")); P = dict(M["params"])
    A = json.load(open(os.path.join(DATA, "fb_guc.json"), encoding="utf-8"))
    po = A.get("poisson_oransiz") or {}; decay, prior = float(po.get("decay", .003)), float(po.get("prior", 10.0))
    PP = dict(P, decay=decay, prior=prior); rho = P.get("rho", -0.06)
    Lg = FL.lig_maclari("espn", S); del S
    # havuz taban: tüm liglerin maçları tarih sırasıyla
    hepsi = sorted((m["d"], FL.sonuc(m["ft"]), m["ft"][0] + m["ft"][1] > 2) for ms in Lg.values() for m in ms)
    hd = np.array([x[0] for x in hepsi]); hy = np.array([x[1] for x in hepsi]); ho = np.array([x[2] for x in hepsi], float)
    cy = np.vstack([np.zeros(3), np.cumsum(np.eye(3)[hy], 0)]); co = np.concatenate([[0], np.cumsum(ho)])

    def taban(d):
        k = int(np.searchsorted(hd, d, "left"))
        q = (cy[k] + 1) / (k + 3); o = (co[k] + 1) / (k + 2)     # Laplace
        return q, o

    R = collections.defaultdict(list); neden = collections.Counter()
    for lg, ms in Lg.items():
        hafta, uy = FL.uygun_ve_hafta(ms, PENCERE)
        for wk, idx in hafta.items():
            hedef = [i for i in idx if not uy[i]]
            if not hedef: continue
            lo = (wk - timedelta(days=PENCERE)).isoformat(); cut = wk.isoformat()
            train = [m for m in ms if lo <= m["d"] < cut]
            if len(train) < MIN_TRAIN: continue
            cnt = collections.Counter([m["h"] for m in train] + [m["a"] for m in train])
            Fh = hb_fit(train, wk, decay, TAU0, N0, None)
            Fp = U.fit(train, wk, PP, None, iters=30)
            for i in hedef:
                m = ms[i]
                lam = []
                for F in (Fh, Fp):
                    (ah, dh), (aa, da) = F["t"].get(m["h"], U.NEW_TEAM), F["t"].get(m["a"], U.NEW_TEAM)
                    lam.append((F["mu"] * F["gamma"] * ah * da, F["mu"] * aa * dh))
                q, o = taban(m["d"])
                R["lh"].append(lam[0]); R["lp"].append(lam[1]); R["tq"].append(q); R["to"].append(o)
                R["y"].append(FL.sonuc(m["ft"])); R["yo"].append(float(m["ft"][0] + m["ft"][1] > 2))
                R["d"].append(m["d"]); R["lg"].append(lg)
                nd = "lig<45" if len(train) < 45 else "takim<3"
                R["neden"].append(nd); neden[nd] += 1
        log(lg, "eşik altı", sum(1 for x in R["lg"] if x == lg))
    y = np.array(R["y"]); yo = np.array(R["yo"]); d = np.array(R["d"]); lgs = np.array(R["lg"]); nd = np.array(R["neden"])
    lh = np.array(R["lh"]); lp = np.array(R["lp"]); tq = np.array(R["tq"]); to = np.array(R["to"])
    ph, oh, _, _ = U.outcome_probs(lh[:, 0], lh[:, 1], rho); pp, op, _, _ = U.outcome_probs(lp[:, 0], lp[:, 1], rho)
    blok = np.array([f"{a}|{b}" for a, b in zip(lgs, d)])
    s2 = sorted(d)[len(d) // 2]; h2 = d >= s2
    dl = FL.ll3(ph, y) - FL.ll3(tq, y); db = FL.br3(ph, y) - FL.br3(tq, y)
    dlp = FL.ll3(ph, y) - FL.ll3(pp, y)
    do = FL.ll2(oh, yo) - FL.ll2(to, yo); dbo = FL.br2(oh, yo) - FL.br2(to, yo)
    alt = {}
    for k in ("lig<45", "takim<3"):
        s = nd == k
        if s.any(): alt[k] = {"n": int(s.sum()), "dll_taban": round(float(dl[s].mean()), 5), "dll_poisson": round(float(dlp[s].mean()), 5)}
    K = {"madde": "YH-21", "tarih": date.today().isoformat(), "tasarim": {"tau0": TAU0, "n0": N0, "tavan": None, "decay": decay,
         "pencere_gun": PENCERE, "min_egitim": MIN_TRAIN, "uretim_prior": prior},
         "n": int(len(y)), "lig_sayisi": int(len(set(R["lg"]))), "donem": [min(d), max(d)], "yarilar_siniri": s2, "neden": dict(neden),
         "hb": FL.ozet(ph, y, oh, yo), "taban": FL.ozet(tq, y, to, yo), "poisson_tek_onsel": FL.ozet(pp, y, op, yo),
         "kiyas_1x2_taban": {"ll": FL.blok_boot(dl, blok), "brier": FL.blok_boot(db, blok),
                             "ll_yari1": round(float(dl[~h2].mean()), 5), "ll_yari2": round(float(dl[h2].mean()), 5)},
         "kiyas_1x2_poisson": FL.blok_boot(dlp, blok),
         "kiyas_ou_taban": {"ll": FL.blok_boot(do, blok), "brier": FL.blok_boot(dbo, blok),
                            "ll_yari1": round(float(do[~h2].mean()), 5), "ll_yari2": round(float(do[h2].mean()), 5)},
         "alt_kume": alt}
    k1 = K["kiyas_1x2_taban"]
    K["kapi"] = {"1x2": bool(k1["ll"]["ga95"][1] < 0 and k1["ll_yari1"] < 0 and k1["ll_yari2"] < 0 and k1["brier"]["fark"] <= 0
                            and K["kiyas_1x2_poisson"]["fark"] <= 0)}
    ko = K["kiyas_ou_taban"]
    K["kapi"]["ou"] = bool(ko["ll"]["ga95"][1] < 0 and ko["ll_yari1"] < 0 and ko["ll_yari2"] < 0 and ko["brier"]["fark"] <= 0)
    log(json.dumps(K, ensure_ascii=False))
    json.dump(K, open(os.path.join(DATA, "esik_alti_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    main()
