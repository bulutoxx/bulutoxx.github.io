#!/usr/bin/env python3
"""🎯 YH-39 laboratuvarı: beraberlik fiyatlaması — lig × denklik kovası artığı (1X2 beraberlik). Pope & Peel (1989).
Zaman sıralı (sızıntısız) sınama. Veri yükleyici ve ölçüm yardımcıları YH-37 (lab/takim_1x2_lab.py) ile ortak.

Önceden kayıtlı tasarım:
  • Taban: power marj ayırma (YH-34 Dixon–Coles adayı değil).
  • Denklik kovası g = |p_ev − p_dep|: denk g < 0,15 · orta 0,15 ≤ g < 0,40 · favorili g ≥ 0,40 (sabit eşikler).
  • Anahtar (lig, kova); sezonlar arası taşınır. Artık r = 1[beraberlik] − p_x.
    Üstel ağırlık λ = 0,5^(1/80); R = Σ λ^k r_k / (Σ λ^k + 40). Özellik R YALNIZ önceki günlerden.
  • Aday: logit p_x' = logit p_x + η·R; kalan 1 − p_x' ev/dep arasında oranla paylaşılır. η = 0 tabanı birebir verir.
  • η ızgara −10 … 10 (adım 0,1) yalnız önceki katlarda; 1 Temmuz yıllık katlar; sınama 2023-07-01 →.
Kapı (SK): ΔLL lig×gün blok bootstrap B = 2000 %95 GA üst < 0 · iki yarıda ΔLL < 0 · ΔBrier ≤ 0 · isabet düşmüyor · p ≤ α_t.

  python3 lab/beraberlik_lab.py      → data/beraberlik_lab.json
"""
import json, os, sys
from collections import defaultdict
from datetime import date
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))
import takim_1x2_lab as T

T.RNG = np.random.default_rng(39)
LAM = 0.5 ** (1 / 80.0); K0 = 40.0
ESIK = (0.15, 0.40); KOVA_AD = ("denk", "orta", "favorili")
SINAMA_BAS = "2023-07-01"
IZ_E = np.round(np.arange(-10.0, 10.001, 0.1), 2)


def kova(p): g = abs(p[0] - p[2]); return 0 if g < ESIK[0] else (1 if g < ESIK[1] else 2)


def satirlar(M):
    num = defaultdict(float); den = defaultdict(float); out = []; i = 0
    while i < len(M):
        gun = M[i][0]; j = i
        while j < len(M) and M[j][0] == gun: j += 1
        bugun = []
        for d, lg, h, a, hg, ag, o in M[i:j]:
            if not o: continue
            p = T.power3(o); y = 0 if hg > ag else (1 if hg == ag else 2); k = (lg, kova(p))
            out.append((gun, lg, num[k] / (den[k] + K0), p, y, k[1]))
            bugun.append((k, (1.0 if y == 1 else 0.0) - p[1]))
        for k, r in bugun:
            num[k] = LAM * num[k] + r; den[k] = LAM * den[k] + 1.0
        i = j
    return out


def qx(P, s, et):
    px = T.sig(T.logit(P[:, 1]) + et * s)
    kalan = (1 - px) / np.clip(P[:, 0] + P[:, 2], 1e-9, None)
    return np.clip(np.stack([P[:, 0] * kalan, px, P[:, 2] * kalan], 1), 1e-9, 1)


def main():
    try: onceki = json.load(open(os.path.join(DATA, "beraberlik_lab.json"), encoding="utf-8"))
    except Exception: onceki = {}
    rows = satirlar(T.yukle())
    d_ = np.array([r[0] for r in rows]); lg = np.array([r[1] for r in rows]); s = np.array([r[2] for r in rows])
    P = np.array([r[3] for r in rows]); y = np.array([r[4] for r in rows]); kv = np.array([r[5] for r in rows])
    print("1X2 maç", len(rows), "| R std", round(float(s.std()), 4), "| ilk", d_[0])
    cuts = [f"{Y}-07-01" for Y in range(int(SINAMA_BAS[:4]), int(d_[-1][:4]) + 1)] + ["9999"]
    Q = P.copy(); katlar = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        tr = d_ < a; te = (d_ >= a) & (d_ < b)
        if not te.any() or not tr.any(): continue
        et = float(min(IZ_E, key=lambda e: T.ll3(qx(P[tr], s[tr], e), y[tr]).sum()))
        Q[te] = qx(P[te], s[te], et)
        katlar.append({"kat": a, "n_sinama": int(te.sum()), "n_egitim": int(tr.sum()), "eta": et}); print(katlar[-1])
    m = d_ >= SINAMA_BAS
    dl = (T.ll3(Q, y) - T.ll3(P, y))[m]; db = (T.br3(Q, y) - T.br3(P, y))[m]
    blok = np.array([f"{l}|{x}" for l, x in zip(lg, d_)])[m]
    dt = d_[m]; s2 = sorted(dt)[len(dt) // 2]; h2 = dt >= s2
    r = T.blok_boot(dl, blok); rb = T.blok_boot(db, blok)
    r["yari1"] = round(float(dl[~h2].mean()), 6); r["yari2"] = round(float(dl[h2].mean()), 6)
    ym = y[m]
    isabet = {"taban": round(float((P[m].argmax(1) == ym).mean()), 5), "aday": round(float((Q[m].argmax(1) == ym).mean()), 5)}
    # betimsel (karar değil): sınamada kova başına gerçek / piyasa beraberlik oranı
    betim = []
    for k in range(3):
        mk = m & (kv == k)
        if mk.any(): betim.append({"kova": KOVA_AD[k], "n": int(mk.sum()), "x_gercek": round(float((y[mk] == 1).mean()), 4),
                                   "x_piyasa": round(float(P[mk, 1].mean()), 4),
                                   "dll": round(float((T.ll3(Q, y) - T.ll3(P, y))[mk].mean()), 6)})
    import oxx_ogren as O
    yol_fb = os.path.join(DATA, "fb_guc.json")
    try: A = json.load(open(yol_fb, encoding="utf-8"))
    except Exception: A = {}
    alan_k = f"fb_model-{date.today().year}"
    alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "literatür (Pope & Peel 1989)"}})) if A else 0.0
    gecti = bool(r["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and rb["fark"] <= 0
                 and isabet["aday"] >= isabet["taban"] and r["p_tek"] <= alfa)
    sonuc = {"x12": {"dll": r, "dbrier": rb, "isabet": isabet, "kovalar": betim, "yarilar_siniri": s2,
                     "alfa_t": round(alfa, 5), "kapi_gecti": gecti}}
    print(json.dumps(sonuc, ensure_ascii=False))
    karne = {"tarih": date.today().isoformat(), "madde": "YH-39", "kaynak": "derin arşiv + season.json 2026 (türetilmiş)",
             "tasarim": {"yari_omur_mac": 80, "k0": K0, "esik": list(ESIK), "sinama_bas": SINAMA_BAS,
                         "izgara_eta": [float(IZ_E[0]), float(IZ_E[-1]), 0.1], "aday": "logit p_x + η·R(lig, kova)"},
             "n_mac": len(rows), "katlar": katlar, "sonuc": sonuc, "karar": "gecti" if gecti else "reddedildi",
             "not": "Taban power marj ayırma (1X2); aday yalnız lig×denklik beraberlik artığı eğimi ekler. Artık yalnız önceki günlerden."}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and not karne["alfa_islendi"]:
        O.yatirim_guncelle(A, alan_k, alfa, gecti)
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "test": 1, "gecti": {"x12": gecti}}
    json.dump(karne, open(os.path.join(DATA, "beraberlik_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", karne["karar"])


if __name__ == "__main__":
    main()
