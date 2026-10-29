#!/usr/bin/env python3
"""🧪 YH-25 · Hiyerarşik (ampirik) Bayes güç modeli laboratuvarı — oransız ligler (season.json src=espn).

Üretim Poisson'u (scripts/update.fit) tüm takımlara TEK önsel kullanır: att, def ~ Gamma(α, α), α = prior × taban (fb_guc.json
poisson_oransiz.prior; şu an 10). Aday (Baio & Blangiardo 2010 hiyerarşisinin ampirik Bayes / eşlenik Gamma yaklaşımı):
  • Her lig ve her hafta, YALNIZ o haftadan önceki maçlarla, takım log-güçlerinin gerçek varyansı τ² moment yöntemiyle
    kestirilir: τ²_lig = var(log güç_ham) − ort(örnekleme varyansı ≈ 1 / beklenen gol). Hücum ve savunma ayrı.
  • Ligler arası önsel: τ² = (J·τ²_lig + n0·τ²_0) / (J + n0)  (J = takım sayısı) — az takımlı / az maçlı ligler ortak değere çekilir.
  • Önsel gücü α = 1 / τ²  (hücum ve savunma ayrı) → Gamma eşlenik güncellemesiyle aynı Maher yinelemesi.
  • İsteğe bağlı "karışım" (büyük skor tek başına gücü uçurmasın): eğitimde maç başına gol en çok `tavan` sayılır.
Izgara (τ²_0, n0, tavan) yalnız seçim diliminde (SINIR öncesi) seçilir.

Kıyas (önceden kayıtlı): üretimdeki model yolu = topluluk C4 (Poisson + Elo + pi, aylık genişleyen yığınlama). Aday = aynı topluluk,
Poisson girdisi hiyerarşik Bayes'ten. Sınama dilimi (SINIR ve sonrası) — standart kapı: ΔLL %95 GA (lig×gün blok, B=2000) üst < 0,
iki zaman yarısında ΔLL < 0, ΔBrier ≤ 0, isabet düşmüyor, tek yanlı p ≤ α_t (alfa yatırımı, fb_model-<yıl>); ek kapı: sezonun ilk
8 haftasındaki maçlarda ΔLL < 0. A/Ü (2,5) ayrı rapor.

  python3 lab/hb_guc_lab.py [--sinir 2026-04-01] [--kapi]   → data/hb_guc_lab.json
"""
import argparse, collections, json, math, os, sys, time
from datetime import date, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import update as U  # noqa: E402
import guc as G  # noqa: E402
import fb_guc_lab as FL  # noqa: E402

T0 = time.time()
def log(*a): print(f"[{time.time() - T0:6.0f} sn]", *a, flush=True)


def hb_fit(ms, ref_day, decay, tau0, n0, tavan=None, G0=1.0, G1=1.6, iters=30):
    """Ampirik Bayes Maher-Poisson. Dönüş update.fit ile aynı biçim + {"tau": (τ²_hücum, τ²_savunma)}."""
    teams = sorted({m["h"] for m in ms} | {m["a"] for m in ms}); ti = {t: i for i, t in enumerate(teams)}; n = len(teams)
    hi = np.array([ti[m["h"]] for m in ms]); ai = np.array([ti[m["a"]] for m in ms])
    hg = np.array([m["ft"][0] for m in ms], float); ag = np.array([m["ft"][1] for m in ms], float)
    if tavan:
        hg = np.minimum(hg, tavan); ag = np.minimum(ag, tavan)
    days = np.array([(ref_day - date.fromisoformat(m["d"])).days for m in ms], float)
    w = np.exp(-decay * days)
    mu = (w * ag).sum() / w.sum(); gamma = min(max((w * hg).sum() / max((w * ag).sum(), .1), G0), G1)

    def dongu(Ka, Kd, att, de, mu, gamma, it):
        for _ in range(it):
            eh = mu * gamma * att[hi] * de[ai]; ea = mu * att[ai] * de[hi]
            gs = np.bincount(hi, w * hg, n) + np.bincount(ai, w * ag, n)
            es = np.bincount(hi, w * eh / att[hi], n) + np.bincount(ai, w * ea / att[ai], n)
            gc = np.bincount(ai, w * hg, n) + np.bincount(hi, w * ag, n)
            ec = np.bincount(ai, w * eh / de[ai], n) + np.bincount(hi, w * ea / de[hi], n)
            att = (gs + Ka) / (es + Ka); de = (gc + Kd) / (ec + Kd)
            att /= math.exp(np.log(att).mean()); de /= math.exp(np.log(de).mean())
            dh = (w * att[hi] * de[ai]).sum(); da = (w * att[ai] * de[hi]).sum()
            mu = (w * ag).sum() / da; gamma = min(max(((w * hg).sum() / dh) / mu, G0), G1)
        return att, de, mu, gamma, es * att, ec * de

    # 1) zayıf önselle ham güçler + beklenen gol (örnekleme varyansı ≈ 1 / beklenen gol)
    att, de, mu1, g1, ega, egd = dongu(0.5, 0.5, np.ones(n), np.ones(n), mu, gamma, 20)
    va = float(np.var(np.log(att))) - float(np.mean(1 / np.maximum(ega, .5)))
    vd = float(np.var(np.log(de))) - float(np.mean(1 / np.maximum(egd, .5)))
    ta_lig = max(va, 1e-3); td_lig = max(vd, 1e-3)
    ta = (n * ta_lig + n0 * tau0) / (n + n0); td = (n * td_lig + n0 * tau0) / (n + n0)
    # 2) hiyerarşik önselle yeniden (α = 1/τ²)
    att, de, mu, gamma, _, _ = dongu(1 / ta, 1 / td, np.ones(n), np.ones(n), mu, gamma, iters)
    return {"t": {t: (float(att[ti[t]]), float(de[ti[t]])) for t in teams}, "mu": float(mu), "gamma": float(gamma), "tau": (ta, td)}


def hb_wf(ms, hafta, uy, decay, tau0, n0, tavan, pencere):
    lam = np.full((len(ms), 2), np.nan); taus = []
    for wk, idx in hafta.items():
        if not uy[idx].any(): continue
        lo = (wk - timedelta(days=pencere)).isoformat(); cut = wk.isoformat()
        train = [m for m in ms if lo <= m["d"] < cut]
        F = hb_fit(train, wk, decay, tau0, n0, tavan); taus.append(F["tau"])
        for i in idx:
            if not uy[i]: continue
            (ah, dh), (aa, da) = F["t"][ms[i]["h"]], F["t"][ms[i]["a"]]
            lam[i] = (F["mu"] * F["gamma"] * ah * da, F["mu"] * aa * dh)
    return lam, taus


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sinir", default="2026-04-01"); ap.add_argument("--kapi", action="store_true")
    ar = ap.parse_args(); sinir = ar.sinir
    S = json.load(open(os.path.join(DATA, "season.json"), encoding="utf-8"))
    M = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8")); P = dict(M["params"])
    A = json.load(open(os.path.join(DATA, "fb_guc.json"), encoding="utf-8"))
    po = A.get("poisson_oransiz") or {}; decay, prior = float(po.get("decay", .003)), float(po.get("prior", 10.0))
    prm = A.get("prm") or {}
    Lg = FL.lig_maclari("espn", S); del S
    pencere = 450
    IZ = [(t0, n0, tv) for t0 in (0.03, 0.06, 0.1) for n0 in (5, 20, 80) for tv in (None, 4)]
    log("ligler", len(Lg), "ızgara", len(IZ), "üretim decay/prior", decay, prior)
    R = collections.defaultdict(list); tau_ozet = collections.defaultdict(list)
    for lg, ms in Lg.items():
        hafta, uy = FL.uygun_ve_hafta(ms, pencere)
        if uy.sum() < 20: continue
        ii = np.where(uy)[0]
        l0 = FL.poisson_wf(ms, hafta, uy, dict(P, decay=decay, prior=prior), pencere)
        R["lam0"].append(l0[ii])
        for k in IZ:
            lk, taus = hb_wf(ms, hafta, uy, decay, *k, pencere); R[k].append(lk[ii])
            if k == (0.06, 20, None) and taus: tau_ozet[lg] = [round(float(np.median([t[0] for t in taus])), 4), round(float(np.median([t[1] for t in taus])), 4)]
        R["elo"].append(np.array(G.elo_seq(ms, prm.get("elo"))[0])[ii]); R["pi"].append(np.array(G.pi_seq(ms, prm.get("pi"))[0])[ii])
        tot = np.array([m["ft"][0] + m["ft"][1] for m in ms], float); cs = np.concatenate([[0], np.cumsum(tot)])
        og = np.array([(cs[i] - cs[max(0, i - 300)]) / max(1, i - max(0, i - 300)) if i else 2.6 for i in range(len(ms))])
        bas = {}
        for m in ms: bas.setdefault(m.get("season"), m["d"])
        for i in ii:
            m = ms[i]
            R["lg"].append(lg); R["d"].append(m["d"]); R["y"].append(FL.sonuc(m["ft"])); R["tot"].append(m["ft"][0] + m["ft"][1]); R["og"].append(og[i])
            R["erken"].append((date.fromisoformat(m["d"]) - date.fromisoformat(bas[m.get("season")])).days < 56)
        log(lg, "uygun", int(uy.sum()))
    for k in list(R):
        if k not in ("lg", "d", "y", "tot", "og", "erken"): R[k] = np.concatenate(R[k])
    y = np.array(R["y"]); d = np.array(R["d"]); lgs = np.array(R["lg"]); n = len(y); og = np.array(R["og"]); erken = np.array(R["erken"])
    yo = (np.array(R["tot"]) > 2).astype(float); blok = np.array([f"{a}|{b}" for a, b in zip(lgs, d)])
    Ssel = d < sinir; rho = P.get("rho", -0.06); E = R["elo"]; PIg = R["pi"]
    aylar = sorted({x[:7] for x in d})

    def pois(L): p, pO, _, _ = U.outcome_probs(L[:, 0], L[:, 1], rho); return p, pO

    def yigin(p, pO):
        q = np.full((n, 3), np.nan); o = np.full(n, np.nan)
        X = G.ozellik_1x2(p, E, PIg); Xo = G.ozellik_ou(pO, PIg, og)
        for ay in aylar:
            tr = d < ay + "-01"; te = np.array([x[:7] == ay for x in d])
            if tr.sum() < 800: continue
            q[te] = G.mlogit_pred(X[te], G.mlogit_fit(X[tr], y[tr])); o[te] = G.logit_pred(Xo[te], G.logit_fit(Xo[tr], yo[tr]))
        return q, o

    p0, o0 = pois(R["lam0"]); q0, qo0 = yigin(p0, o0)
    # seçim: yalnız S diliminde, topluluk (aday) LL'sine göre — yığınlayıcı tanımlı satırlar
    sk = {}; cache = {}
    for k in IZ:
        pk, ok_ = pois(R[k]); qk, qok = yigin(pk, ok_); cache[k] = (pk, ok_, qk, qok)
        msk = Ssel & ~np.isnan(qk[:, 0]) & ~np.isnan(q0[:, 0])
        sk[k] = float(FL.ll3(qk[msk], y[msk]).mean()) if msk.any() else float(FL.ll3(pk[Ssel], y[Ssel]).mean())
    msk = Ssel & ~np.isnan(q0[:, 0]); s0 = float(FL.ll3(q0[msk], y[msk]).mean())
    ks = min(sk, key=sk.get); pk, opk, qk, qok = cache[ks]
    log("seçim LL (üretim C4", round(s0, 5), "n", int(msk.sum()), "):", {str(k): round(v, 5) for k, v in sk.items()}, "→", ks)
    ok = (~Ssel) & ~np.isnan(q0[:, 0]) & ~np.isnan(qk[:, 0]) & ~np.isnan(qo0) & ~np.isnan(qok)
    dT = d[ok]; s2 = sorted(dT)[len(dT) // 2]; h2 = dT >= s2
    dl = FL.ll3(qk[ok], y[ok]) - FL.ll3(q0[ok], y[ok]); db = FL.br3(qk[ok], y[ok]) - FL.br3(q0[ok], y[ok])
    do = FL.ll2(qok[ok], yo[ok]) - FL.ll2(qo0[ok], yo[ok]); dbo = FL.br2(qok[ok], yo[ok]) - FL.br2(qo0[ok], yo[ok])
    dlp = FL.ll3(pk[ok], y[ok]) - FL.ll3(p0[ok], y[ok])      # yalnız Poisson (bilgi)
    er = erken[ok]
    K = {"madde": "YH-25", "tarih": date.today().isoformat(), "sinir": sinir, "yarilar_siniri": s2, "n_secim": int(msk.sum()),
         "n_sinama": int(ok.sum()), "uretim": {"decay": decay, "prior": prior, "elo": prm.get("elo"), "pi": prm.get("pi")},
         "secilen": {"tau0": ks[0], "n0": ks[1], "tavan": ks[2]}, "izgara_secim_ll": {str(k): round(v, 5) for k, v in sk.items()},
         "secim_ll_uretim": round(s0, 5), "tau_medyan_lig (0.06/20)": dict(tau_ozet),
         "uretim_c4": FL.ozet(q0[ok], y[ok], qo0[ok], yo[ok]), "aday_c4": FL.ozet(qk[ok], y[ok], qok[ok], yo[ok]),
         "kiyas_1x2": {"ll": FL.blok_boot(dl, blok[ok]), "brier": FL.blok_boot(db, blok[ok]),
                       "ll_yari1": round(float(dl[~h2].mean()), 5), "ll_yari2": round(float(dl[h2].mean()), 5),
                       "isabet_fark": round(float((qk[ok].argmax(1) == y[ok]).mean() - (q0[ok].argmax(1) == y[ok]).mean()), 4),
                       "erken8hafta": {"n": int(er.sum()), "ll": round(float(dl[er].mean()), 5) if er.any() else None}},
         "kiyas_ou": {"ll": FL.blok_boot(do, blok[ok]), "brier": FL.blok_boot(dbo, blok[ok]),
                      "ll_yari1": round(float(do[~h2].mean()), 5), "ll_yari2": round(float(do[h2].mean()), 5),
                      "erken8hafta": round(float(do[er].mean()), 5) if er.any() else None},
         "yalniz_poisson_1x2": FL.blok_boot(dlp, blok[ok])}
    k1 = K["kiyas_1x2"]
    sk_ = (k1["ll"]["ga95"][1] < 0 and k1["ll_yari1"] < 0 and k1["ll_yari2"] < 0 and k1["brier"]["fark"] <= 0 and k1["isabet_fark"] >= 0
           and (k1["erken8hafta"]["ll"] is None or k1["erken8hafta"]["ll"] < 0))
    ko = K["kiyas_ou"]
    sk_ou = ko["ll"]["ga95"][1] < 0 and ko["ll_yari1"] < 0 and ko["ll_yari2"] < 0 and ko["brier"]["fark"] <= 0
    K["kapi"] = {"1x2_ham": bool(sk_), "ou_ham": bool(sk_ou)}
    if ar.kapi:
        import oxx_ogren as O
        GLp = os.path.join(DATA, "fb_guc.json"); GL = json.load(open(GLp, encoding="utf-8"))
        alan_k = f"fb_model-{date.today().year}"
        for ad, ham, kk in (("1x2", sk_, k1), ("ou", sk_ou, ko)):
            alfa = O.yatirim_alfa(GL, alan_k, {}); gecti = bool(ham and kk["ll"]["p_tek"] <= alfa)
            O.yatirim_guncelle(GL, alan_k, alfa, gecti)
            K["kapi"][ad] = {"alfa": round(alfa, 5), "p_tek": kk["ll"]["p_tek"], "gecti": gecti}
        json.dump(GL, open(GLp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("1X2:", json.dumps(k1, ensure_ascii=False)); log("A/Ü:", json.dumps(ko, ensure_ascii=False))
    log("yalnız Poisson:", K["yalniz_poisson_1x2"]); log("kapı:", K["kapi"])
    json.dump(K, open(os.path.join(DATA, "hb_guc_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    main()
