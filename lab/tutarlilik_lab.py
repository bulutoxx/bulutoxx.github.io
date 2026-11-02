#!/usr/bin/env python3
"""🔗 YH-33 laboratuvarı: pazarlar arası tutarlılık — 1X2 ve 2,5 A/Ü piyasalarından ortak Poisson (λ_ev, λ_dep) çıkarımı.

Soru: 2,5 A/Ü fiyatı 1X2 olasılığına (ve 1X2 fiyatı 2,5 olasılığına) bilgi ekliyor mu? Her maç için iki pazarın marjı ayrılmış
olasılıklarına (power) aynı anda en iyi uyan bağımsız Poisson (λ_ev, λ_dep) bulunur (3 kısıt, 2 serbestlik: çapraz bilgi
yalnız bu fazlalıktan gelir). Aday = taban ile Poisson'un log-doğrusal harmanı; ağırlık yalnız eğitim katında seçilir.

Veri: derin arşiv (data/derin/*, football-data bitmiş sezonlar; yalnız türetilmiş satırlar), beş oranı da olan maçlar.

Önceden kayıtlı tasarım (ızgara yalnız eğitim katında):
  • Uyum: λ = μ·s, μ·(1−s); μ ∈ [0,6 ; 5,0] adım 0,02, s ∈ [0,10 ; 0,90] adım 0,005 ızgarası; amaç
    −Σ_k p_k log q_k(λ) − [r log q_Ü + (1−r) log q_A] (çapraz entropi, iki pazar eşit ağırlık).
  • Aday 1X2: log Q = (1−w)·log p + w·log q_pois, normalize; w ∈ [0, 1] adım 0,02.
    Aday 2,5: logit Q = (1−v)·logit r + v·logit q_Ü; v ∈ [0, 1] adım 0,02.
  • Taban: power marj ayırma (sunulan piyasa yolunun ilk adımı; marj_lab / motivasyon_lab ile aynı).
  • Yürüyen pencere: 1 Temmuz sınırlı yıllık katlar; her kat yalnız kendinden önceki maçlarla (w, v) seçer.
Kapı (SK): sınamada ΔLL lig×gün blok bootstrap B = 2000 %95 GA üst < 0 · iki zaman yarısında ΔLL < 0 · ΔBrier ≤ 0 ·
tek yanlı p ≤ α_t (alfa yatırımı fb_model-<yıl>). 1X2 ve 2,5 ayrı karar.

  python3 lab/tutarlilik_lab.py      → data/tutarlilik_lab.json
"""
import glob, json, math, os, sys
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))

from motivasyon_lab import power, ll3, br3, ll2, br2, blok_boot  # ortak ölçüm yardımcıları

IZ_W = np.round(np.arange(0, 1.0001, 0.02), 3)
MU = np.arange(0.6, 5.0001, 0.02)
SH = np.arange(0.10, 0.9001, 0.005)
GMAX = 11


def tablo():
    """Izgara hücresi başına (P1, PX, P2, PÜst) — bağımsız Poisson."""
    m, s = np.meshgrid(MU, SH, indexing="ij"); m = m.ravel(); s = s.ravel()
    lh, la = m * s, m * (1 - s)
    g = np.arange(GMAX); f = np.array([math.factorial(k) for k in g], float)
    ph = np.exp(-lh)[:, None] * lh[:, None] ** g / f; pa = np.exp(-la)[:, None] * la[:, None] ** g / f
    J = ph[:, :, None] * pa[:, None, :]
    i, j = np.meshgrid(g, g, indexing="ij")
    p1 = (J * (i > j)).sum((1, 2)); px = (J * (i == j)).sum((1, 2)); p2 = (J * (i < j)).sum((1, 2))
    pu = (J * ((i + j) > 2)).sum((1, 2)); top = p1 + px + p2
    T = np.c_[p1 / top, px / top, p2 / top, pu / top]
    return np.clip(T, 1e-9, 1 - 1e-9).astype(np.float32), m, s


def uydur(P, r, T):
    L = np.log(T[:, :3]); LU = np.log(T[:, 3]); LA = np.log(1 - T[:, 3])
    out = np.empty(len(P), int)
    for a in range(0, len(P), 400):
        b = a + 400
        ce = -(P[a:b].astype(np.float32) @ L.T) - (r[a:b, None] * LU[None] + (1 - r[a:b, None]) * LA[None])
        out[a:b] = ce.argmin(1)
    return out


def harman3(P, Qp, w):
    z = (1 - w) * np.log(np.clip(P, 1e-9, 1)) + w * np.log(np.clip(Qp, 1e-9, 1))
    z = np.exp(z - z.max(1, keepdims=True)); return z / z.sum(1, keepdims=True)


def logit(p): p = np.clip(p, 1e-9, 1 - 1e-9); return np.log(p) - np.log(1 - p)


def harman2(r, qu, v): return 1 / (1 + np.exp(-((1 - v) * logit(r) + v * logit(qu))))


def main():
    try: onceki = json.load(open(os.path.join(DATA, "tutarlilik_lab.json"), encoding="utf-8"))
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
    T, mu, sh = tablo()
    k = uydur(P, r_, T); Qp = T[k, :3].astype(float); Qp /= Qp.sum(1, keepdims=True); qu = T[k, 3].astype(float)
    sinir = int(((mu[k] <= MU[0] + 1e-9) | (mu[k] >= MU[-1] - 1e-9) | (sh[k] <= SH[0] + 1e-9) | (sh[k] >= SH[-1] - 1e-9)).sum())
    # betimsel uyumsuzluk: Poisson'un iki pazarı ne kadar tutarlı açıkladığı
    uy = {"ort_abs_1x2": round(float(np.abs(Qp - P).mean()), 5), "ort_abs_ust": round(float(np.abs(qu - r_).mean()), 5),
          "piyasa_X_ort": round(float(P[:, 1].mean()), 4), "poisson_X_ort": round(float(Qp[:, 1].mean()), 4),
          "izgara_sinirinda": sinir}
    print("uyum", uy)
    y0, y1 = 2022, int(d_[-1][:4])
    cuts = [f"{Y}-07-01" for Y in range(y0, y1 + 1)] + ["9999"]
    Q = P.copy(); QO = r_.copy(); katlar = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        tr = d_ < a; te = (d_ >= a) & (d_ < b)
        if not te.any(): continue
        w = float(min(IZ_W, key=lambda w: ll3(harman3(P[tr], Qp[tr], w), y[tr]).sum()))
        v = float(min(IZ_W, key=lambda v: ll2(harman2(r_[tr], qu[tr], v), yo[tr]).sum()))
        Q[te] = harman3(P[te], Qp[te], w); QO[te] = harman2(r_[te], qu[te], v)
        katlar.append({"kat": a, "n_egitim": int(tr.sum()), "n_sinama": int(te.sum()), "w_1x2": w, "v_ou25": v}); print(katlar[-1])
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
        alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "pazarlar arası tutarlılık (ortak Poisson)"}})) if A else 0.0
        gecti = bool(r["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and rb["fark"] <= 0 and r["p_tek"] <= alfa)
        sonuc[pazar] = {"dll": r, "dbrier": rb, "yarilar_siniri": s2, "alfa_t": round(alfa, 5), "kapi_gecti": gecti}
        print(pazar, json.dumps(sonuc[pazar], ensure_ascii=False))
    karne = {"tarih": date.today().isoformat(), "madde": "YH-33", "kaynak": "derin arşiv (football-data, türetilmiş)",
             "n_mac": len(rows), "n_lig": len(set(lg)), "n_sinama": int(te_all.sum()), "uyum": uy, "katlar": katlar, "sonuc": sonuc,
             "karar": "gecti" if any(v["kapi_gecti"] for v in sonuc.values()) else "reddedildi",
             "not": "Taban power marj ayırma; aday iki pazara ortak uyan bağımsız Poisson ile log-doğrusal harman (ağırlık yalnız geçmiş katlardan)."}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and not karne["alfa_islendi"]:
        for pazar, v in sonuc.items(): O.yatirim_guncelle(A, alan_k, v["alfa_t"], v["kapi_gecti"])
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "test": len(sonuc),
                                 "gecti": {k: v["kapi_gecti"] for k, v in sonuc.items()}}
    json.dump(karne, open(os.path.join(DATA, "tutarlilik_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", karne["karar"])


if __name__ == "__main__":
    main()
