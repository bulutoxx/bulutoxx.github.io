#!/usr/bin/env python3
"""🏁 YH-29 laboratuvarı: sezon sonu "maç önemi" (motivasyon) — piyasa üstü bilgi var mı? Zaman sıralı (sızıntısız) sınama.

Soru: Matematiksel olarak hiçbir hedefi kalmamış ("ölü") takım — şampiyonluğa yetişemez VE ya kesin kurtulmuş ya kesin düşmüş —
piyasa olasılığının söylediğinden daha mı kötü oynuyor? (Goddard & Asimakopoulos 2004: maç önemi değişkenleri anlamlı,
sabit oranlı piyasada bu bilgi tam fiyatlanmıyor.)

Veri: derin arşiv (data/derin/*, football-data bitmiş sezonlar; yalnız türetilmiş satırlar). Puan tablosu her maçtan önce
yalnız o lig-sezonun DAHA ÖNCEKİ günlerdeki sonuçlarından kurulur (aynı gün maçlar görülmez). Sezon uzunluğu (takım sayısı,
takım başına maç) sezon öncesi bilinen fikstür bilgisidir.

Önceden kayıtlı tasarım (ızgara yalnız eğitim katında):
  • Lig-sezon kabulü: her takım eşit sayıda maç oynamış (tam fikstür); puan bölme / play-off / ortalama ile düşme olan ligler
    dışarıda (at, be, ro, ar, mx, us). Düşme sayısı: ≥ 18 takım → 3, değilse 2.
  • ölü(i) = şampiyonluğa yetişemez (puan + 3·kalan < lider) VE (kesin kurtulmuş: en az n_düşme rakip i'ye yetişemez
    YA DA kesin düşmüş: en az takım − n_düşme rakip i'nin erişemeyeceği puanda).
  • Aday 1X2: log q = log p_piyasa + [β·d, γ·b, −β·d] (d = ölü_dep − ölü_ev, b = ikisi de ölü), normalize.
    Aday 2,5 A/Ü: logit q = logit p_piyasa + η·(ölü_ev + ölü_dep).
  • Taban: power marj ayırma (sunulan piyasa yolunun ilk adımı; marj_lab ile aynı).
  • Yürüyen pencere: 1 Temmuz sınırlı yıllık katlar; her kat yalnız kendinden önceki maçlarla (β, γ, η) seçer.
Kapı (SK): sınamada ΔLL (aday − taban) lig×gün blok bootstrap B = 2000 %95 GA üst < 0 · iki zaman yarısında ΔLL < 0 ·
ΔBrier ≤ 0 · tek yanlı p ≤ α_t (alfa yatırımı fb_model-<yıl>, sinyalli aday). 1X2 ve 2,5 ayrı karar.

  python3 lab/motivasyon_lab.py      → data/motivasyon_lab.json
"""
import glob, json, os, sys
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))

RNG = np.random.default_rng(29)
B_BOOT = 2000
DISARIDA = {"at", "be", "ro", "ar", "mx", "us"}
IZ_B = np.round(np.arange(-0.6, 0.601, 0.02), 3)
IZ_G = np.round(np.arange(-0.4, 0.401, 0.04), 3)
IZ_E = np.round(np.arange(-0.4, 0.401, 0.02), 3)


def power(o):
    q = 1 / np.asarray(o, float); lo, hi = 0.5, 3.0
    for _ in range(50):
        k = (lo + hi) / 2
        if (q ** k).sum() > 1: lo = k
        else: hi = k
    p = q ** k; return p / p.sum()


def lig_sezon(D):
    """Tek lig-sezon: maç başına (tarih, lig, ölü_ev, ölü_dep, sonuç, p1x2, pO|None, toplam>2). Uygun değilse []."""
    M = sorted([m for m in D["m"] if m[3] is not None and m[4] is not None], key=lambda m: m[0])
    takim = sorted({m[1] for m in M} | {m[2] for m in M}); nt = len(takim)
    if nt < 8: return []
    say = {t: 0 for t in takim}
    for m in M: say[m[1]] += 1; say[m[2]] += 1
    G = set(say.values())
    if len(G) != 1: return []
    G = G.pop(); nrel = 3 if nt >= 18 else 2
    pts = {t: 0 for t in takim}; oyn = {t: 0 for t in takim}
    out = []; i = 0
    while i < len(M):
        gun = M[i][0]; j = i
        while j < len(M) and M[j][0] == gun: j += 1
        P = np.array([pts[t] for t in takim]); R = np.array([G - oyn[t] for t in takim]); maxp = P + 3 * R
        lider = P.max(); ix = {t: k for k, t in enumerate(takim)}
        def olu(t):
            k = ix[t]
            if maxp[k] >= lider: return 0
            yetisemez = int(((maxp < P[k]) & (np.arange(nt) != k)).sum())
            erisilmez = int(((P > maxp[k]) & (np.arange(nt) != k)).sum())
            return int(yetisemez >= nrel or erisilmez >= nt - nrel)
        for m in M[i:j]:
            h, a, hg, ag = m[1], m[2], m[3], m[4]
            if m[5] and m[6] and m[7]:
                pO = power([m[8], m[9]])[0] if m[8] and m[9] else None
                out.append((gun, D["lg"], olu(h), olu(a), 0 if hg > ag else (1 if hg == ag else 2),
                            power([m[5], m[6], m[7]]), pO, hg + ag > 2))
        for m in M[i:j]:
            h, a, hg, ag = m[1], m[2], m[3], m[4]
            oyn[h] += 1; oyn[a] += 1
            if hg > ag: pts[h] += 3
            elif hg == ag: pts[h] += 1; pts[a] += 1
            else: pts[a] += 3
        i = j
    return out


def q1x2(P, d, b, be, ga):
    z = np.log(np.clip(P, 1e-9, 1)) + np.c_[be * d, ga * b, -be * d]
    z = np.exp(z - z.max(1, keepdims=True)); return z / z.sum(1, keepdims=True)


def qou(p, s, et):
    l = np.log(np.clip(p, 1e-9, 1)) - np.log(np.clip(1 - p, 1e-9, 1)) + et * s
    return 1 / (1 + np.exp(-l))


def ll3(Q, y): return -np.log(np.clip(Q[np.arange(len(y)), y], 1e-9, 1))
def br3(Q, y): return ((Q - np.eye(3)[y]) ** 2).sum(1)
def ll2(q, y): return -np.where(y, np.log(np.clip(q, 1e-9, 1)), np.log(np.clip(1 - q, 1e-9, 1)))
def br2(q, y): return (q - y) ** 2


def blok_boot(delta, blok, B=B_BOOT):
    u, inv = np.unique(blok, return_inverse=True)
    s = np.bincount(inv, delta, len(u)); n = np.bincount(inv, None, len(u))
    idx = RNG.integers(0, len(u), (B, len(u)))
    bs = s[idx].sum(1) / n[idx].sum(1)
    return {"fark": round(float(delta.mean()), 6), "ga95": [round(float(np.quantile(bs, .025)), 6), round(float(np.quantile(bs, .975)), 6)],
            "p_tek": round(float((bs >= 0).mean()), 4), "n": int(len(delta)), "blok": int(len(u))}


def main():
    try: onceki = json.load(open(os.path.join(DATA, "motivasyon_lab.json"), encoding="utf-8"))
    except Exception: onceki = {}
    rows = []; kabul, red = [], []
    for f in sorted(glob.glob(os.path.join(DATA, "derin", "*-*.json"))):
        D = json.load(open(f, encoding="utf-8"))
        ad = f"{D.get('lg')}-{D.get('sezon')}"
        if D.get("lg") in DISARIDA or not D.get("tam", True): red.append(ad); continue
        r = lig_sezon(D)
        (kabul if r else red).append(ad); rows += r
    rows.sort(key=lambda r: r[0])
    d_ = np.array([r[0] for r in rows]); lg = np.array([r[1] for r in rows])
    oh = np.array([r[2] for r in rows]); oa = np.array([r[3] for r in rows]); y = np.array([r[4] for r in rows])
    P = np.array([r[5] for r in rows]); hasO = np.array([r[6] is not None for r in rows])
    pO = np.array([r[6] if r[6] is not None else .5 for r in rows]); yo = np.array([r[7] for r in rows])
    dd = (oa - oh).astype(float); bb = (oh & oa).astype(float); ss = (oh + oa).astype(float)
    print("lig-sezon kabul", len(kabul), "dışarıda", len(red), "| maç", len(rows), "| ölü taraflı maç", int(((oh + oa) > 0).sum()))
    y0, y1 = int(d_[0][:4]) + 1, int(d_[-1][:4])
    cuts = [f"{Y}-07-01" for Y in range(y0, y1 + 1)] + ["9999"]
    Q = P.copy(); QO = pO.copy(); katlar = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        tr = d_ < a; te = (d_ >= a) & (d_ < b)
        if not te.any(): continue
        # 1X2: β, γ ayrı ızgara (yalnız eğitim katı)
        trm = tr & ((oh + oa) > 0)
        best = (0.0, 0.0); bl = None
        if trm.sum() >= 50:
            for be in IZ_B:
                for ga in IZ_G:
                    l = ll3(q1x2(P[trm], dd[trm], bb[trm], be, ga), y[trm]).sum()
                    if bl is None or l < bl: bl, best = l, (float(be), float(ga))
        Q[te] = q1x2(P[te], dd[te], bb[te], *best)
        tro = tr & hasO & (ss > 0); et = 0.0
        if tro.sum() >= 50:
            et = float(min(IZ_E, key=lambda e: ll2(qou(pO[tro], ss[tro], e), yo[tro]).sum()))
        teo = te & hasO; QO[teo] = qou(pO[teo], ss[teo], et)
        katlar.append({"kat": a, "n_sinama": int(te.sum()), "n_egitim_olu": int(trm.sum()), "beta": best[0], "gamma": best[1], "eta": et,
                       "n_sinama_olu": int((te & ((oh + oa) > 0)).sum())})
        print(katlar[-1])
    te_all = d_ >= cuts[0]
    blok = np.array([f"{l}|{x}" for l, x in zip(lg, d_)])
    sonuc = {}
    import oxx_ogren as O
    yol_fb = os.path.join(DATA, "fb_guc.json")
    try: A = json.load(open(yol_fb, encoding="utf-8"))
    except Exception: A = {}
    alan_k = f"fb_model-{date.today().year}"
    for pazar in ("1x2", "ou25"):
        m = te_all if pazar == "1x2" else te_all & hasO
        if pazar == "1x2": dl = (ll3(Q, y) - ll3(P, y))[m]; db = (br3(Q, y) - br3(P, y))[m]
        else: dl = (ll2(QO, yo) - ll2(pO, yo))[m]; db = (br2(QO, yo) - br2(pO, yo))[m]
        dt = d_[m]; s2 = sorted(dt)[len(dt) // 2]; h2 = dt >= s2
        r = blok_boot(dl, blok[m]); rb = blok_boot(db, blok[m])
        r["yari1"] = round(float(dl[~h2].mean()), 6); r["yari2"] = round(float(dl[h2].mean()), 6)
        mo = ((oh + oa) > 0)[m]
        alt = {"olu_tarafli": {"n": int(mo.sum()), "dll": round(float(dl[mo].mean()), 5) if mo.any() else None},
               "olu_ev": round(float(dl[(oh[m] == 1)].mean()), 5) if (oh[m] == 1).any() else None,
               "olu_dep": round(float(dl[(oa[m] == 1)].mean()), 5) if (oa[m] == 1).any() else None}
        if pazar == "1x2":
            # betimsel (karar değil): ölü takımın gerçek kazanma oranı − piyasanın beklediği
            for nm, msk, k in (("ev_olu_rakip_canli", (oh == 1) & (oa == 0), 0), ("dep_olu_rakip_canli", (oa == 1) & (oh == 0), 2)):
                mm = m & msk
                if mm.any(): alt[nm] = {"n": int(mm.sum()), "olu_kazanir_gercek": round(float((y[mm] == k).mean()), 4),
                                        "olu_kazanir_piyasa": round(float(P[mm, k].mean()), 4)}
        alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "literatür (Goddard & Asimakopoulos 2004)"}})) if A else 0.0
        gecti = bool(r["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and rb["fark"] <= 0 and r["p_tek"] <= alfa)
        sonuc[pazar] = {"dll": r, "dbrier": rb, "alt_kume": alt, "yarilar_siniri": s2, "alfa_t": round(alfa, 5), "kapi_gecti": gecti}
        print(pazar, json.dumps(sonuc[pazar], ensure_ascii=False))
    karne = {"tarih": date.today().isoformat(), "madde": "YH-29", "kaynak": "derin arşiv (football-data, türetilmiş)",
             "lig_sezon_kabul": len(kabul), "lig_sezon_disarida": sorted(red), "n_mac": len(rows),
             "n_olu_tarafli": int(((oh + oa) > 0).sum()), "katlar": katlar, "sonuc": sonuc,
             "karar": "gecti" if any(v["kapi_gecti"] for v in sonuc.values()) else "reddedildi",
             "not": "Taban power marj ayırma; aday piyasa olasılığına yalnız 'ölü takım' eğimi ekler. Puan tablosu yalnız önceki günlerden."}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and not karne["alfa_islendi"]:
        for pazar, v in sonuc.items(): O.yatirim_guncelle(A, alan_k, v["alfa_t"], v["kapi_gecti"])
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "test": len(sonuc),
                                 "gecti": {k: v["kapi_gecti"] for k, v in sonuc.items()}}
    json.dump(karne, open(os.path.join(DATA, "motivasyon_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", karne["karar"])


if __name__ == "__main__":
    main()
