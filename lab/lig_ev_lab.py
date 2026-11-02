#!/usr/bin/env python3
"""🎯 YH-38 laboratuvarı: lig düzeyi ev sahibi avantajı kayması — piyasa ev avantajındaki değişime geç mi uyum sağlıyor?
Zaman sıralı (sızıntısız) sınama. Veri yükleyici, kaydırma ve ölçüm yardımcıları YH-37 (lab/takim_1x2_lab.py) ile ortak.

Önceden kayıtlı tasarım:
  • Lig anahtarı; sezonlar arası taşınır. Her oranlı maç için r = puan_ev − (3·p_ev + p_x), p power marj ayırma.
  • Üstel ağırlık λ = 0,5^(1/60); R_lig = Σ λ^k r_k / (Σ λ^k + 30). Özellik s = R_lig YALNIZ önceki günlerden.
  • Aday: sıralı logit kayması μ = η·s (takim_1x2_lab.q1x2). Taban power. η ızgara −2 … 2 (adım 0,02) yalnız önceki katlarda.
  • Sınama 2023-07-01 →; 1 Temmuz yıllık katlar. Seyircisiz dönem (2020-03-01 … 2021-06-30) ayrıca 2020-07-01 katından
    itibaren betimsel raporlanır (karar yalnız sınama diliminde).
Kapı (SK): ΔLL lig×gün blok bootstrap B = 2000 %95 GA üst < 0 · iki yarıda ΔLL < 0 · ΔBrier ≤ 0 · isabet düşmüyor · p ≤ α_t.

  python3 lab/lig_ev_lab.py      → data/lig_ev_lab.json
"""
import json, os, sys
from collections import defaultdict
from datetime import date
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))
import takim_1x2_lab as T

T.RNG = np.random.default_rng(38)
LAM = 0.5 ** (1 / 60.0); K0 = 30.0
SINAMA_BAS = "2023-07-01"
IZ_E = np.round(np.arange(-2.0, 2.001, 0.02), 3)


def satirlar(M):
    num = defaultdict(float); den = defaultdict(float); out = []; i = 0
    while i < len(M):
        gun = M[i][0]; j = i
        while j < len(M) and M[j][0] == gun: j += 1
        bugun = []
        for d, lg, h, a, hg, ag, o in M[i:j]:
            if not o: continue
            p = T.power3(o); y = 0 if hg > ag else (1 if hg == ag else 2)
            out.append((gun, lg, num[lg] / (den[lg] + K0), p, y))
            bugun.append((lg, (3 if y == 0 else (1 if y == 1 else 0)) - (3 * p[0] + p[1])))
        for k, r in bugun:
            num[k] = LAM * num[k] + r; den[k] = LAM * den[k] + 1.0
        i = j
    return out


def kat_uygula(d_, P, s, y, bas):
    cuts = [f"{Y}-07-01" for Y in range(int(bas[:4]), int(d_[-1][:4]) + 1)] + ["9999"]
    Q = P.copy(); katlar = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        tr = d_ < a; te = (d_ >= a) & (d_ < b)
        if not te.any() or not tr.any(): continue
        et = float(min(IZ_E, key=lambda e: T.ll3(T.q1x2(P[tr], s[tr], e), y[tr]).sum()))
        Q[te] = T.q1x2(P[te], s[te], et)
        katlar.append({"kat": a, "n_sinama": int(te.sum()), "n_egitim": int(tr.sum()), "eta": et})
    return Q, katlar


def main():
    try: onceki = json.load(open(os.path.join(DATA, "lig_ev_lab.json"), encoding="utf-8"))
    except Exception: onceki = {}
    rows = satirlar(T.yukle())
    d_ = np.array([r[0] for r in rows]); lg = np.array([r[1] for r in rows]); s = np.array([r[2] for r in rows])
    P = np.array([r[3] for r in rows]); y = np.array([r[4] for r in rows])
    print("1X2 maç", len(rows), "| s std", round(float(s.std()), 4), "| ilk tarih", d_[0])
    Q, katlar = kat_uygula(d_, P, s, y, SINAMA_BAS)
    for k in katlar: print(k)
    m = d_ >= SINAMA_BAS
    dl = (T.ll3(Q, y) - T.ll3(P, y))[m]; db = (T.br3(Q, y) - T.br3(P, y))[m]
    blok = np.array([f"{l}|{x}" for l, x in zip(lg, d_)])[m]
    dt = d_[m]; s2 = sorted(dt)[len(dt) // 2]; h2 = dt >= s2
    r = T.blok_boot(dl, blok); rb = T.blok_boot(db, blok)
    r["yari1"] = round(float(dl[~h2].mean()), 6); r["yari2"] = round(float(dl[h2].mean()), 6)
    ym = y[m]
    isabet = {"taban": round(float((P[m].argmax(1) == ym).mean()), 5), "aday": round(float((Q[m].argmax(1) == ym).mean()), 5)}
    # betimsel (karar değil): seyircisiz dönem — 2020-07-01 katından itibaren aynı yürüyen pencere
    covid = None
    if d_[0] < "2020-07-01":
        Qc, kc = kat_uygula(d_, P, s, y, "2020-07-01")
        mc = (d_ >= "2020-07-01") & (d_ <= "2021-06-30")
        if mc.any():
            covid = {"n": int(mc.sum()), "dll": round(float((T.ll3(Qc, y) - T.ll3(P, y))[mc].mean()), 6), "eta": kc[0]["eta"] if kc else None,
                     "ev_gercek": round(float((y[mc] == 0).mean()), 4), "ev_piyasa": round(float(P[mc, 0].mean()), 4)}
    import oxx_ogren as O
    yol_fb = os.path.join(DATA, "fb_guc.json")
    try: A = json.load(open(yol_fb, encoding="utf-8"))
    except Exception: A = {}
    alan_k = f"fb_model-{date.today().year}"
    alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "literatür (Winkelmann vd. 2021)"}})) if A else 0.0
    gecti = bool(r["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and rb["fark"] <= 0
                 and isabet["aday"] >= isabet["taban"] and r["p_tek"] <= alfa)
    sonuc = {"x12": {"dll": r, "dbrier": rb, "isabet": isabet, "seyircisiz_donem": covid, "yarilar_siniri": s2,
                     "alfa_t": round(alfa, 5), "kapi_gecti": gecti}}
    print(json.dumps(sonuc, ensure_ascii=False))
    karne = {"tarih": date.today().isoformat(), "madde": "YH-38", "kaynak": "derin arşiv + season.json 2026 (türetilmiş)",
             "tasarim": {"yari_omur_mac": 60, "k0": K0, "sinama_bas": SINAMA_BAS, "izgara_eta": [float(IZ_E[0]), float(IZ_E[-1]), 0.02],
                         "aday": "sıralı logit kayması η·R_lig"},
             "n_mac": len(rows), "katlar": katlar, "sonuc": sonuc, "karar": "gecti" if gecti else "reddedildi",
             "not": "Taban power marj ayırma (1X2); aday yalnız lig ev puanı artığı eğimi ekler. Artık yalnız önceki günlerden."}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and not karne["alfa_islendi"]:
        O.yatirim_guncelle(A, alan_k, alfa, gecti)
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "test": 1, "gecti": {"x12": gecti}}
    json.dump(karne, open(os.path.join(DATA, "lig_ev_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", karne["karar"])


if __name__ == "__main__":
    main()
