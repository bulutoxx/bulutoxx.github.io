#!/usr/bin/env python3
"""🔗 YH-34 laboratuvarı: Dixon–Coles düşük skor düzeltmeli ortak piyasa çıkarımı (YH-33 devamı) — 1X2 beraberlik.

YH-33'te bağımsız Poisson beraberliği eksik ölçtüğü için harman ağırlığı her katta 0 çıktı. Burada aynı ortak uyum
Dixon–Coles τ(ρ) ile yapılır (0-0, 1-0, 0-1, 1-1 hücreleri; τ toplam olasılığı korur, 2,5 Üst olasılığını değiştirmez ama
ortak uyumu değiştirir). Soru: 2,5 A/Ü fiyatı DC iskeletiyle 1X2'ye (özellikle beraberliğe) bilgi ekliyor mu?

Veri: derin arşiv (data/derin/*, football-data bitmiş sezonlar; yalnız türetilmiş satırlar), beş oranı da olan maçlar.

Önceden kayıtlı tasarım (her seçim yalnız eğitim katında):
  • ρ ızgarası {−0,20, −0,15, −0,10, −0,05, 0, +0,05}; her ρ için YH-33 ile aynı (μ, s) ızgarası ve çapraz entropi uyumu.
  • Lig grubu = lig; her katta her lig için ρ, eğitim katında DC 1X2'nin kendi log kaybını en aza indiren değer
    (eğitimde < 300 maçı olan lig → tüm ligler ortak ρ).
  • Aday 1X2: log Q = (1−w)·log p + w·log q_DC; tek w ∈ [0, 1] adım 0,02 (lig ρ'ları sabitken eğitimde seçilir).
    Aday 2,5: logit Q = (1−v)·logit r + v·logit q_Ü (ilgili ρ uyumundan); bilgi amaçlı, karar 1X2 üzerinden.
  • Taban: power marj ayırma. Katlar: 1 Temmuz sınırlı yıllık, YH-33 ile aynı; bloklar lig×gün.
Kapı (SK): sınamada ΔLL lig×gün blok bootstrap B = 2000 %95 GA üst < 0 · iki zaman yarısında ΔLL < 0 · ΔBrier ≤ 0 ·
tek yanlı p ≤ α_t (alfa yatırımı fb_model-<yıl>).

  python3 lab/dc_tutarlilik_lab.py      → data/dc_tutarlilik_lab.json
"""
import glob, json, math, os, sys
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))

from motivasyon_lab import power, ll3, br3, ll2, br2, blok_boot  # ortak ölçüm yardımcıları
from tutarlilik_lab import IZ_W, MU, SH, GMAX, harman3, harman2, uydur

RHO = [-0.20, -0.15, -0.10, -0.05, 0.0, 0.05]
MIN_LIG = 300


def tablo_dc(rho):
    """Izgara hücresi başına (P1, PX, P2, PÜst) — Dixon–Coles τ(ρ) düzeltmeli Poisson."""
    m, s = np.meshgrid(MU, SH, indexing="ij"); m = m.ravel(); s = s.ravel()
    lh, la = m * s, m * (1 - s)
    g = np.arange(GMAX); f = np.array([math.factorial(k) for k in g], float)
    ph = np.exp(-lh)[:, None] * lh[:, None] ** g / f; pa = np.exp(-la)[:, None] * la[:, None] ** g / f
    J = ph[:, :, None] * pa[:, None, :]
    J[:, 0, 0] *= 1 - lh * la * rho; J[:, 0, 1] *= 1 + lh * rho; J[:, 1, 0] *= 1 + la * rho; J[:, 1, 1] *= 1 - rho
    J = np.clip(J, 0, None)
    i, j = np.meshgrid(g, g, indexing="ij")
    p1 = (J * (i > j)).sum((1, 2)); px = (J * (i == j)).sum((1, 2)); p2 = (J * (i < j)).sum((1, 2))
    pu = (J * ((i + j) > 2)).sum((1, 2)); top = p1 + px + p2
    T = np.c_[p1 / top, px / top, p2 / top, pu / top]
    return np.clip(T, 1e-9, 1 - 1e-9).astype(np.float32)


def main():
    try: onceki = json.load(open(os.path.join(DATA, "dc_tutarlilik_lab.json"), encoding="utf-8"))
    except Exception: onceki = {}
    rows = []
    for f in sorted(glob.glob(os.path.join(DATA, "derin", "*-*.json"))):
        D = json.load(open(f, encoding="utf-8"))
        for m in D["m"]:
            if m[3] is None or m[4] is None or not all(m[5:10]): continue
            rows.append((m[0], D["lg"], 0 if m[3] > m[4] else (1 if m[3] == m[4] else 2), m[3] + m[4] > 2,
                         power(m[5:8]), power(m[8:10])[0]))
    rows.sort(key=lambda r: r[0])
    d_ = np.array([r[0] for r in rows]); lg = np.array([r[1] for r in rows])
    y = np.array([r[2] for r in rows]); yo = np.array([r[3] for r in rows])
    P = np.array([r[4] for r in rows]); r_ = np.array([r[5] for r in rows])
    print("maç", len(rows), "lig", len(set(lg)), d_[0], "→", d_[-1])
    QP, QU, uy = {}, {}, {}
    for rho in RHO:
        T = tablo_dc(rho); k = uydur(P, r_, T); del T
        T = tablo_dc(rho)[k]  # yalnız seçilen hücreler
        q = T[:, :3].astype(float); q /= q.sum(1, keepdims=True); QP[rho] = q; QU[rho] = T[:, 3].astype(float)
        uy[str(rho)] = {"poisson_X_ort": round(float(q[:, 1].mean()), 4), "ort_abs_1x2": round(float(np.abs(q - P).mean()), 5),
                        "ort_abs_ust": round(float(np.abs(QU[rho] - r_).mean()), 5)}
        print("ρ", rho, uy[str(rho)])
    uy["piyasa_X_ort"] = round(float(P[:, 1].mean()), 4)
    ligler = sorted(set(lg))
    y0, y1 = 2022, int(d_[-1][:4])
    cuts = [f"{Y}-07-01" for Y in range(y0, y1 + 1)] + ["9999"]
    Q = P.copy(); QO = r_.copy(); katlar = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        tr = d_ < a; te = (d_ >= a) & (d_ < b)
        if not te.any(): continue
        rho_g = min(RHO, key=lambda h: ll3(QP[h][tr], y[tr]).sum())
        rho_l = {}
        for L in ligler:
            mL = tr & (lg == L)
            rho_l[L] = min(RHO, key=lambda h: ll3(QP[h][mL], y[mL]).sum()) if mL.sum() >= MIN_LIG else rho_g
        rsec = np.array([rho_l[L] for L in lg])
        Qd = np.zeros_like(P); Qu = np.zeros_like(r_)
        for h in RHO:
            mm = rsec == h; Qd[mm] = QP[h][mm]; Qu[mm] = QU[h][mm]
        w = float(min(IZ_W, key=lambda w: ll3(harman3(P[tr], Qd[tr], w), y[tr]).sum()))
        v = float(min(IZ_W, key=lambda v: ll2(harman2(r_[tr], Qu[tr], v), yo[tr]).sum()))
        Q[te] = harman3(P[te], Qd[te], w); QO[te] = harman2(r_[te], Qu[te], v)
        dag = {str(h): int(sum(1 for L in ligler if rho_l[L] == h)) for h in RHO}
        katlar.append({"kat": a, "n_egitim": int(tr.sum()), "n_sinama": int(te.sum()), "rho_ortak": rho_g,
                       "rho_lig_dagilim": dag, "w_1x2": w, "v_ou25": v}); print(katlar[-1])
    te_all = d_ >= cuts[0]
    blok = np.array([f"{l}|{x}" for l, x in zip(lg, d_)])
    import oxx_ogren as O
    yol_fb = os.path.join(DATA, "fb_guc.json")
    try: A = json.load(open(yol_fb, encoding="utf-8"))
    except Exception: A = {}
    alan_k = f"fb_model-{date.today().year}"
    sonuc = {}
    for pazar in ("1x2", "ou25"):
        m = te_all
        if pazar == "1x2": dl = (ll3(Q, y) - ll3(P, y))[m]; db = (br3(Q, y) - br3(P, y))[m]
        else: dl = (ll2(QO, yo) - ll2(r_, yo))[m]; db = (br2(QO, yo) - br2(r_, yo))[m]
        dt = d_[m]; s2 = sorted(dt)[len(dt) // 2]; h2 = dt >= s2
        r = blok_boot(dl, blok[m]); rb = blok_boot(db, blok[m])
        r["yari1"] = round(float(dl[~h2].mean()), 6); r["yari2"] = round(float(dl[h2].mean()), 6)
        alfa = 0.0
        if A and pazar == "1x2":
            alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "Dixon–Coles ortak piyasa çıkarımı (1X2)"}}))
        gecti = bool(r["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and rb["fark"] <= 0 and r["p_tek"] <= alfa)
        sonuc[pazar] = {"dll": r, "dbrier": rb, "yarilar_siniri": s2, "alfa_t": round(alfa, 5), "kapi_gecti": gecti,
                        "rol": "karar" if pazar == "1x2" else "bilgi"}
        print(pazar, json.dumps(sonuc[pazar], ensure_ascii=False))
    # beraberlik betimi (sınama): sunulan X ortalaması vs gerçekleşen
    xm = te_all
    ber = {"gercek_X": round(float((y[xm] == 1).mean()), 4), "taban_X": round(float(P[xm, 1].mean()), 4),
           "aday_X": round(float(Q[xm, 1].mean()), 4)}
    karne = {"tarih": date.today().isoformat(), "madde": "YH-34", "kaynak": "derin arşiv (football-data, türetilmiş)",
             "n_mac": len(rows), "n_lig": len(ligler), "n_sinama": int(te_all.sum()), "rho_izgara": RHO, "uyum": uy,
             "beraberlik": ber, "katlar": katlar, "sonuc": sonuc,
             "karar": "gecti" if sonuc["1x2"]["kapi_gecti"] else "reddedildi",
             "not": "Taban power marj ayırma; aday iki pazara ortak uyan Dixon–Coles (lig ρ, yalnız geçmiş katlardan) ile log-doğrusal harman. Karar 1X2; 2,5 bilgi."}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and not karne["alfa_islendi"]:
        O.yatirim_guncelle(A, alan_k, sonuc["1x2"]["alfa_t"], sonuc["1x2"]["kapi_gecti"])
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "test": 1, "gecti": {"1x2": sonuc["1x2"]["kapi_gecti"]}}
    json.dump(karne, open(os.path.join(DATA, "dc_tutarlilik_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", karne["karar"])


if __name__ == "__main__":
    main()
