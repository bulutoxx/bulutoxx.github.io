#!/usr/bin/env python3
"""🏁 YH-35 laboratuvarı: sezon başı gol ortamı — 2,5 A/Ü piyasa üstü bilgi var mı? Zaman sıralı (sızıntısız) sınama.

Soru: Sezonun ilk haftalarında piyasa geçen sezonun gol ortamına yaslanıyor mu? Bu sezon (yalnız önceki günler) gol
ortalaması geçen sezondan sapıyorsa piyasa bu sapmayı geç mi fiyatlıyor? (Forrest, Goddard & Simmons 2005.)

Veri: derin arşiv (data/derin/*, football-data bitmiş sezonlar) + data/season.json (yalnız d ≥ 2026-07-01 → 2026 sezonu;
derinde olan maç bir kez). Yalnız türetilmiş satırlar; ham veri yazılmaz.

Önceden kayıtlı tasarım:
  • ḡ_önceki = aynı ligin geçen sezon maç başı gol ortalaması (bitmiş sezon; yoksa satır özelliksiz = 0).
  • ḡ_bu = (G + m0·ḡ_önceki) / (n + m0), G/n = bu sezon YALNIZ ÖNCEKİ GÜNLERDEKİ gol / maç; m0 = 30 maç büzme.
  • h = tamamlanan hafta = ⌊2·n / takım_sayısı⌋; sönüm w = max(0, 1 − h/5) (ilk 5 hafta).
  • Özellik s = w · (ḡ_bu − ḡ_önceki); aday logit q = logit p_piyasa + η·s. Taban: power marj ayırma (üst/alt).
  • Yürüyen pencere: 1 Temmuz sınırlı yıllık katlar; η yalnız kendinden önceki (s ≠ 0) maçlarla ızgarada seçilir.
    Sınama 2023-07-01 → (ilk eğitilebilir kat: 2022 sezonu özellikli satırlar). Karar TÜM sınama üzerinden
    (özelliksiz maçlarda Δ = 0), sezon başı alt kümesi ayrıca raporlanır.
Kapı (SK): ΔLL lig×gün blok bootstrap B = 2000 %95 GA üst < 0 · iki zaman yarısında ΔLL < 0 · ΔBrier ≤ 0 ·
tek yanlı p ≤ α_t (alfa yatırımı fb_model-<yıl>, sinyalli aday).

  python3 lab/sezon_basi_lab.py      → data/sezon_basi_lab.json
"""
import glob, json, os, sys
from collections import defaultdict
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))

RNG = np.random.default_rng(35)
B_BOOT = 2000
M0 = 30.0
HAFTA = 5
SINAMA_BAS = "2023-07-01"
IZ_E = np.round(np.arange(-0.6, 0.601, 0.02), 3)


def power2(o):
    q = 1 / np.asarray(o, float); lo, hi = 0.5, 3.0
    for _ in range(50):
        k = (lo + hi) / 2
        if (q ** k).sum() > 1: lo = k
        else: hi = k
    p = q ** k; return float(p[0] / p.sum())


def yukle():
    """{(lg, sezon): [(tarih, ev, dep, hg, ag, ou|None)]}"""
    S, gor = defaultdict(list), set()
    for f in sorted(glob.glob(os.path.join(DATA, "derin", "*-20*.json"))):
        D = json.load(open(f, encoding="utf-8"))
        if not D.get("tam", True): continue
        for d, h, a, hg, ag, o1, ox, o2, ou, ol in D["m"]:
            if hg is None or ag is None: continue
            gor.add((d, D["lg"], h, a))
            S[(D["lg"], int(D["sezon"]))].append((d, h, a, hg, ag, [ou, ol] if ou and ol and min(ou, ol) > 1 else None))
    try: J = json.load(open(os.path.join(DATA, "season.json"), encoding="utf-8"))
    except Exception: J = {}
    for lg, v in J.items():
        for m in (v or {}).get("matches", []):
            if not m.get("ft") or m["d"] < "2026-07-01" or (m["d"], lg, m.get("h"), m.get("a")) in gor: continue
            hg, ag = m["ft"]; ou = m.get("ou")
            S[(lg, 2026)].append((m["d"], m.get("h"), m.get("a"), hg, ag, ou if ou and len(ou) == 2 and min(ou) > 1 else None))
    return S


def satirlar(S):
    ort = {k: np.mean([m[3] + m[4] for m in v]) for k, v in S.items() if len(v) >= 50}
    out = []
    for (lg, sz), M in S.items():
        M = sorted(M, key=lambda m: m[0]); nt = max(len({m[1] for m in M} | {m[2] for m in M}), 2)
        gp = ort.get((lg, sz - 1)); G = n = 0; i = 0
        while i < len(M):
            gun = M[i][0]; j = i
            while j < len(M) and M[j][0] == gun: j += 1
            h = int(2 * n // nt); w = max(0.0, 1 - h / HAFTA)
            s = w * ((G + M0 * gp) / (n + M0) - gp) if gp is not None else 0.0
            for m in M[i:j]:
                if m[5]: out.append((gun, lg, s, h, power2(m[5]), int(m[3] + m[4] > 2), gp is not None and w > 0))
            for m in M[i:j]: G += m[3] + m[4]; n += 1
            i = j
    out.sort(key=lambda r: r[0]); return out


def qou(p, s, et):
    l = np.log(np.clip(p, 1e-9, 1)) - np.log(np.clip(1 - p, 1e-9, 1)) + et * s
    return 1 / (1 + np.exp(-l))


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
    try: onceki = json.load(open(os.path.join(DATA, "sezon_basi_lab.json"), encoding="utf-8"))
    except Exception: onceki = {}
    rows = satirlar(yukle())
    d_ = np.array([r[0] for r in rows]); lg = np.array([r[1] for r in rows]); s = np.array([r[2] for r in rows])
    p = np.array([r[4] for r in rows]); y = np.array([r[5] for r in rows]); erken = np.array([r[6] for r in rows])
    print("A/Ü maç", len(rows), "| sezon başı (özellikli)", int(erken.sum()), "| s ≠ 0", int((s != 0).sum()))
    cuts = [f"{Y}-07-01" for Y in range(int(SINAMA_BAS[:4]), int(d_[-1][:4]) + 1)] + ["9999"]
    Q = p.copy(); katlar = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        tr = (d_ < a) & (s != 0); te = (d_ >= a) & (d_ < b)
        if not te.any(): continue
        et = float(min(IZ_E, key=lambda e: ll2(qou(p[tr], s[tr], e), y[tr]).sum())) if tr.sum() >= 50 else 0.0
        Q[te] = qou(p[te], s[te], et)
        katlar.append({"kat": a, "n_sinama": int(te.sum()), "n_sinama_erken": int((te & erken).sum()), "n_egitim": int(tr.sum()), "eta": et})
        print(katlar[-1])
    m = d_ >= cuts[0]
    dl = (ll2(Q, y) - ll2(p, y))[m]; db = (br2(Q, y) - br2(p, y))[m]
    blok = np.array([f"{l}|{x}" for l, x in zip(lg, d_)])[m]
    dt = d_[m]; s2 = sorted(dt)[len(dt) // 2]; h2 = dt >= s2
    r = blok_boot(dl, blok); rb = blok_boot(db, blok)
    r["yari1"] = round(float(dl[~h2].mean()), 6); r["yari2"] = round(float(dl[h2].mean()), 6)
    em = erken[m]
    alt = {"sezon_basi": {"n": int(em.sum()), "dll": round(float(dl[em].mean()), 5) if em.any() else None,
                          "dbrier": round(float(db[em].mean()), 6) if em.any() else None},
           "betimsel": {}}
    # betimsel (karar değil): bu sezon önceki-günler gol ortamı yukarıdaysa gerçek üst oranı − piyasa
    for nm, msk in (("s_pozitif", (s > 0.05)), ("s_negatif", (s < -0.05))):
        mm = (d_ >= cuts[0]) & msk
        if mm.any(): alt["betimsel"][nm] = {"n": int(mm.sum()), "ust_gercek": round(float(y[mm].mean()), 4), "ust_piyasa": round(float(p[mm].mean()), 4)}
    import oxx_ogren as O
    yol_fb = os.path.join(DATA, "fb_guc.json")
    try: A = json.load(open(yol_fb, encoding="utf-8"))
    except Exception: A = {}
    alan_k = f"fb_model-{date.today().year}"
    alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "literatür (Forrest, Goddard & Simmons 2005)"}})) if A else 0.0
    gecti = bool(r["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and rb["fark"] <= 0 and r["p_tek"] <= alfa)
    sonuc = {"ou25": {"dll": r, "dbrier": rb, "alt_kume": alt, "yarilar_siniri": s2, "alfa_t": round(alfa, 5), "kapi_gecti": gecti}}
    print(json.dumps(sonuc, ensure_ascii=False))
    karne = {"tarih": date.today().isoformat(), "madde": "YH-35", "kaynak": "derin arşiv + season.json 2026 (türetilmiş)",
             "tasarim": {"m0": M0, "hafta": HAFTA, "sinama_bas": SINAMA_BAS, "izgara_eta": [float(IZ_E[0]), float(IZ_E[-1]), 0.02]},
             "n_mac": len(rows), "n_sezon_basi": int(erken.sum()), "katlar": katlar, "sonuc": sonuc,
             "karar": "gecti" if gecti else "reddedildi",
             "not": "Taban power marj ayırma; aday yalnız sezon başı gol ortamı farkı eğimi ekler. Gol ortamı yalnız önceki günlerden."}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and not karne["alfa_islendi"]:
        O.yatirim_guncelle(A, alan_k, alfa, gecti)
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "test": 1, "gecti": {"ou25": gecti}}
    json.dump(karne, open(os.path.join(DATA, "sezon_basi_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", karne["karar"])


if __name__ == "__main__":
    main()
