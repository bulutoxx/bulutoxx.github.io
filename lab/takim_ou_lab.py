#!/usr/bin/env python3
"""🎯 YH-36 laboratuvarı: takım düzeyi 2,5 A/Ü piyasa artığı — piyasa takımın gol eğilimine aşırı / eksik tepki veriyor mu?
Zaman sıralı (sızıntısız) sınama.

Soru: Bir takımın son maçlarında "üst" sonucu piyasanın verdiği olasılıktan sistematik olarak sık / seyrek çıkıyorsa
(r = y_üst − p_piyasa), bu artık bir sonraki maçta piyasa üstü bilgi taşır mı? Wheatcroft (2020) piyasanın son A/Ü
sonuçlarına AŞIRI tepki verdiğini bulur (η < 0 beklenir); eksik tepki η > 0 olurdu. İşaret veriden öğrenilir.

Veri: derin arşiv (data/derin/*, football-data bitmiş sezonlar) + data/season.json (yalnız d ≥ 2026-07-01).
Yalnız türetilmiş satırlar; ham veri yazılmaz.

Önceden kayıtlı tasarım:
  • Takım anahtarı (lig, takım); sezonlar arası taşınır. Her maç için artık r = y_üst − p_piyasa (power marj ayırma).
  • Üstel ağırlık λ = 0,5^(1/8) (8 maçlık yarı ömür); R_takım = Σ λ^k r_k / (Σ λ^k + k0), k0 = 5 (az maçlı takım 0'a büzülür).
  • Özellik s = R_ev + R_dep, YALNIZ önceki günlerin maçlarından (aynı gün maçları sonra işlenir).
  • Aday logit q = logit p_piyasa + η·s. Taban: power marj ayırma (üst/alt).
  • Yürüyen pencere: 1 Temmuz sınırlı yıllık katlar; η yalnız kendinden önceki maçlarla ızgarada (−1 … 1, adım 0,02).
    Sınama 2023-07-01 → bugün.
Kapı (SK): ΔLL lig×gün blok bootstrap B = 2000 %95 GA üst < 0 · iki zaman yarısında ΔLL < 0 · ΔBrier ≤ 0 ·
tek yanlı p ≤ α_t (alfa yatırımı fb_model-<yıl>, sinyalli aday).

  python3 lab/takim_ou_lab.py      → data/takim_ou_lab.json
"""
import json, os, sys
from collections import defaultdict
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))
from sezon_basi_lab import yukle, power2, qou, ll2, br2   # aynı veri yükleyici ve ölçüm yardımcıları

RNG = np.random.default_rng(36)
B_BOOT = 2000
YARI_OMUR = 8.0
LAM = 0.5 ** (1 / YARI_OMUR)
K0 = 5.0
SINAMA_BAS = "2023-07-01"
IZ_E = np.round(np.arange(-1.0, 1.001, 0.02), 3)


def satirlar(S):
    """Tüm maçlar tarih sırasıyla; her gün önce özellik (yalnız önceki günler), sonra durum güncellemesi."""
    M = []
    for (lg, sz), v in S.items():
        for m in v: M.append((m[0], lg) + tuple(m[1:]))
    M.sort(key=lambda m: m[0])
    num = defaultdict(float); den = defaultdict(float)     # (lg, takım) → Σλ^k r, Σλ^k
    out = []; i = 0
    while i < len(M):
        gun = M[i][0]; j = i
        while j < len(M) and M[j][0] == gun: j += 1
        bugun = []
        for d, lg, h, a, hg, ag, ou in M[i:j]:
            if not ou: continue
            p = power2(ou); y = int(hg + ag > 2)
            kh, ka = (lg, h), (lg, a)
            Rh = num[kh] / (den[kh] + K0); Ra = num[ka] / (den[ka] + K0)
            out.append((gun, lg, Rh + Ra, p, y, den[kh] > 0 and den[ka] > 0))
            bugun.append((kh, ka, y - p))
        for kh, ka, r in bugun:
            for k in (kh, ka):
                num[k] = LAM * num[k] + r; den[k] = LAM * den[k] + 1.0
        i = j
    return out


def blok_boot(delta, blok, B=B_BOOT):
    u, inv = np.unique(blok, return_inverse=True)
    s = np.bincount(inv, delta, len(u)); n = np.bincount(inv, None, len(u))
    idx = RNG.integers(0, len(u), (B, len(u)))
    bs = s[idx].sum(1) / n[idx].sum(1)
    return {"fark": round(float(delta.mean()), 6), "ga95": [round(float(np.quantile(bs, .025)), 6), round(float(np.quantile(bs, .975)), 6)],
            "p_tek": round(float((bs >= 0).mean()), 4), "n": int(len(delta)), "blok": int(len(u))}


def main():
    try: onceki = json.load(open(os.path.join(DATA, "takim_ou_lab.json"), encoding="utf-8"))
    except Exception: onceki = {}
    rows = satirlar(yukle())
    d_ = np.array([r[0] for r in rows]); lg = np.array([r[1] for r in rows]); s = np.array([r[2] for r in rows])
    p = np.array([r[3] for r in rows]); y = np.array([r[4] for r in rows]); gec = np.array([r[5] for r in rows])
    print("A/Ü maç", len(rows), "| iki takım da geçmişli", int(gec.sum()), "| s std", round(float(s.std()), 4))
    cuts = [f"{Y}-07-01" for Y in range(int(SINAMA_BAS[:4]), int(d_[-1][:4]) + 1)] + ["9999"]
    Q = p.copy(); katlar = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        tr = d_ < a; te = (d_ >= a) & (d_ < b)
        if not te.any(): continue
        et = float(min(IZ_E, key=lambda e: ll2(qou(p[tr], s[tr], e), y[tr]).sum()))
        Q[te] = qou(p[te], s[te], et)
        katlar.append({"kat": a, "n_sinama": int(te.sum()), "n_egitim": int(tr.sum()), "eta": et})
        print(katlar[-1])
    m = d_ >= cuts[0]
    dl = (ll2(Q, y) - ll2(p, y))[m]; db = (br2(Q, y) - br2(p, y))[m]
    blok = np.array([f"{l}|{x}" for l, x in zip(lg, d_)])[m]
    dt = d_[m]; s2 = sorted(dt)[len(dt) // 2]; h2 = dt >= s2
    r = blok_boot(dl, blok); rb = blok_boot(db, blok)
    r["yari1"] = round(float(dl[~h2].mean()), 6); r["yari2"] = round(float(dl[h2].mean()), 6)
    # betimsel (karar değil): sınamada özellik beşte birlik kovaları — gerçek üst − piyasa
    sm, ym, pm = s[m], y[m], p[m]; qs = np.quantile(sm, [0, .2, .4, .6, .8, 1])
    kova = []
    for k in range(5):
        mk = (sm >= qs[k]) & (sm <= qs[k + 1] if k == 4 else sm < qs[k + 1])
        if mk.any(): kova.append({"s_ort": round(float(sm[mk].mean()), 4), "n": int(mk.sum()),
                                  "ust_gercek": round(float(ym[mk].mean()), 4), "ust_piyasa": round(float(pm[mk].mean()), 4)})
    import oxx_ogren as O
    yol_fb = os.path.join(DATA, "fb_guc.json")
    try: A = json.load(open(yol_fb, encoding="utf-8"))
    except Exception: A = {}
    alan_k = f"fb_model-{date.today().year}"
    alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "literatür (Wheatcroft 2020)"}})) if A else 0.0
    gecti = bool(r["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and rb["fark"] <= 0 and r["p_tek"] <= alfa)
    sonuc = {"ou25": {"dll": r, "dbrier": rb, "kovalar": kova, "yarilar_siniri": s2, "alfa_t": round(alfa, 5), "kapi_gecti": gecti}}
    print(json.dumps(sonuc, ensure_ascii=False))
    karne = {"tarih": date.today().isoformat(), "madde": "YH-36", "kaynak": "derin arşiv + season.json 2026 (türetilmiş)",
             "tasarim": {"yari_omur_mac": YARI_OMUR, "k0": K0, "sinama_bas": SINAMA_BAS, "izgara_eta": [float(IZ_E[0]), float(IZ_E[-1]), 0.02]},
             "n_mac": len(rows), "n_gecmisli": int(gec.sum()), "katlar": katlar, "sonuc": sonuc,
             "karar": "gecti" if gecti else "reddedildi",
             "not": "Taban power marj ayırma; aday yalnız takım A/Ü piyasa artığı eğimi ekler. Artık yalnız önceki günlerden."}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and not karne["alfa_islendi"]:
        O.yatirim_guncelle(A, alan_k, alfa, gecti)
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "test": 1, "gecti": {"ou25": gecti}}
    json.dump(karne, open(os.path.join(DATA, "takim_ou_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", karne["karar"])


if __name__ == "__main__":
    main()
