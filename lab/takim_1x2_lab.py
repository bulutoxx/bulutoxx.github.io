#!/usr/bin/env python3
"""🎯 YH-37 laboratuvarı: takım düzeyi 1X2 piyasa artığı — piyasa takımın puan / sonuç eğilimine aşırı / eksik tepki veriyor mu?
Zaman sıralı (sızıntısız) sınama. YH-36'nın (lab/takim_ou_lab.py) maç sonucu karşılığı.

Soru: Bir takım son maçlarında piyasanın beklediğinden sistematik olarak fazla / az puan topluyorsa
(r = puan − piyasa beklenen puanı), bu artık bir sonraki maçta piyasa üstü bilgi taşır mı? Wheatcroft (2020),
Vlastakis vd. (2009). η < 0 → aşırı tepki (artığa karşı dön), η > 0 → eksik tepki (artığı izle). İşaret veriden öğrenilir.

Veri: derin arşiv (data/derin/*, football-data bitmiş sezonlar) + data/season.json (yalnız d ≥ 2026-07-01).
Yalnız türetilmiş satırlar; ham veri yazılmaz.

Önceden kayıtlı tasarım (YH-36 ile aynı):
  • Takım anahtarı (lig, takım); sezonlar arası taşınır. Her maç için ev artığı r_ev = puan_ev − (3·p_ev + p_x),
    deplasman artığı r_dep = puan_dep − (3·p_dep + p_x); p power marj ayırma (1X2).
  • Üstel ağırlık λ = 0,5^(1/8) (8 maçlık yarı ömür); R = Σ λ^k r_k / (Σ λ^k + k0), k0 = 5.
  • Özellik s = R_ev − R_dep, YALNIZ önceki günlerin maçlarından (aynı gün maçları sonra işlenir).
  • Aday: sıralı logit kayması — eşikler τ1 = logit p_dep, τ2 = logit (p_dep + p_x); P(dep) = σ(τ1 − η·s),
    P(dep ∪ x) = σ(τ2 − η·s). η = 0 tabanı birebir verir. Taban: power marj ayırma.
  • Yürüyen pencere: 1 Temmuz sınırlı yıllık katlar; η yalnız kendinden önceki maçlarla ızgarada (−1 … 1, adım 0,02).
    Sınama 2023-07-01 → bugün.
Kapı (SK): ΔLL lig×gün blok bootstrap B = 2000 %95 GA üst < 0 · iki zaman yarısında ΔLL < 0 · ΔBrier ≤ 0 ·
isabet düşmüyor · tek yanlı p ≤ α_t (alfa yatırımı fb_model-<yıl>, sinyalli aday).

  python3 lab/takim_1x2_lab.py      → data/takim_1x2_lab.json
"""
import glob, json, os, sys
from collections import defaultdict
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))

RNG = np.random.default_rng(37)
B_BOOT = 2000
YARI_OMUR = 8.0
LAM = 0.5 ** (1 / YARI_OMUR)
K0 = 5.0
SINAMA_BAS = "2023-07-01"
IZ_E = np.round(np.arange(-1.0, 1.001, 0.02), 3)


def power3(o):
    q = 1 / np.asarray(o, float); lo, hi = 0.5, 3.0
    for _ in range(60):
        k = (lo + hi) / 2
        if (q ** k).sum() > 1: lo = k
        else: hi = k
    p = q ** k; return p / p.sum()


def gecerli(o):
    return o is not None and len(o) == 3 and all(x and x > 1 for x in o)


def yukle():
    """[(tarih, lg, ev, dep, hg, ag, o1x2|None)] tarih sıralı; derin arşiv + season.json (d ≥ 2026-07-01, tekrar yok)."""
    M, gor = [], set()
    for f in sorted(glob.glob(os.path.join(DATA, "derin", "*-20*.json"))):
        D = json.load(open(f, encoding="utf-8"))
        if not D.get("tam", True): continue
        for d, h, a, hg, ag, o1, ox, o2, ou, ol in D["m"]:
            if hg is None or ag is None: continue
            gor.add((d, D["lg"], h, a))
            o = [o1, ox, o2]
            M.append((d, D["lg"], h, a, hg, ag, o if gecerli(o) else None))
    try: J = json.load(open(os.path.join(DATA, "season.json"), encoding="utf-8"))
    except Exception: J = {}
    for lg, v in J.items():
        for m in (v or {}).get("matches", []):
            if not m.get("ft") or m["d"] < "2026-07-01" or (m["d"], lg, m.get("h"), m.get("a")) in gor: continue
            hg, ag = m["ft"]; o = m.get("odds")
            M.append((m["d"], lg, m.get("h"), m.get("a"), hg, ag, list(o) if gecerli(o) else None))
    M.sort(key=lambda m: m[0])
    return M


def satirlar(M):
    num = defaultdict(float); den = defaultdict(float)
    out = []; i = 0
    while i < len(M):
        gun = M[i][0]; j = i
        while j < len(M) and M[j][0] == gun: j += 1
        bugun = []
        for d, lg, h, a, hg, ag, o in M[i:j]:
            if not o: continue           # oransız maç artık üretmez (piyasa beklentisi yok)
            p = power3(o); y = 0 if hg > ag else (1 if hg == ag else 2)
            kh, ka = (lg, h), (lg, a)
            Rh = num[kh] / (den[kh] + K0); Ra = num[ka] / (den[ka] + K0)
            out.append((gun, lg, Rh - Ra, p, y, den[kh] > 0 and den[ka] > 0))
            ph = 3 if y == 0 else (1 if y == 1 else 0); pa = 3 if y == 2 else (1 if y == 1 else 0)
            bugun.append((kh, ph - (3 * p[0] + p[1])))
            bugun.append((ka, pa - (3 * p[2] + p[1])))
        for k, r in bugun:
            num[k] = LAM * num[k] + r; den[k] = LAM * den[k] + 1.0
        i = j
    return out


def logit(x): x = np.clip(x, 1e-9, 1 - 1e-9); return np.log(x) - np.log(1 - x)
def sig(x): return 1 / (1 + np.exp(-x))


def q1x2(P, s, et):
    """P: (n,3) ev/x/dep; sıralı logit kayması η·s (s > 0 ve η > 0 → ev lehine)."""
    t1 = logit(P[:, 2]); t2 = logit(P[:, 2] + P[:, 1])
    a = sig(t1 - et * s); b = sig(t2 - et * s)
    Q = np.stack([1 - b, b - a, a], 1)
    return np.clip(Q, 1e-9, 1)


def ll3(Q, y): return -np.log(Q[np.arange(len(y)), y])
def br3(Q, y):
    Y = np.zeros_like(Q); Y[np.arange(len(y)), y] = 1
    return ((Q - Y) ** 2).sum(1)


def blok_boot(delta, blok, B=B_BOOT):
    u, inv = np.unique(blok, return_inverse=True)
    s = np.bincount(inv, delta, len(u)); n = np.bincount(inv, None, len(u))
    idx = RNG.integers(0, len(u), (B, len(u)))
    bs = s[idx].sum(1) / n[idx].sum(1)
    return {"fark": round(float(delta.mean()), 6), "ga95": [round(float(np.quantile(bs, .025)), 6), round(float(np.quantile(bs, .975)), 6)],
            "p_tek": round(float((bs >= 0).mean()), 4), "n": int(len(delta)), "blok": int(len(u))}


def main():
    try: onceki = json.load(open(os.path.join(DATA, "takim_1x2_lab.json"), encoding="utf-8"))
    except Exception: onceki = {}
    rows = satirlar(yukle())
    d_ = np.array([r[0] for r in rows]); lg = np.array([r[1] for r in rows]); s = np.array([r[2] for r in rows])
    P = np.array([r[3] for r in rows]); y = np.array([r[4] for r in rows]); gec = np.array([r[5] for r in rows])
    print("1X2 maç", len(rows), "| iki takım da geçmişli", int(gec.sum()), "| s std", round(float(s.std()), 4))
    cuts = [f"{Y}-07-01" for Y in range(int(SINAMA_BAS[:4]), int(d_[-1][:4]) + 1)] + ["9999"]
    Q = P.copy(); katlar = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        tr = d_ < a; te = (d_ >= a) & (d_ < b)
        if not te.any(): continue
        et = float(min(IZ_E, key=lambda e: ll3(q1x2(P[tr], s[tr], e), y[tr]).sum()))
        Q[te] = q1x2(P[te], s[te], et)
        katlar.append({"kat": a, "n_sinama": int(te.sum()), "n_egitim": int(tr.sum()), "eta": et})
        print(katlar[-1])
    m = d_ >= cuts[0]
    dl = (ll3(Q, y) - ll3(P, y))[m]; db = (br3(Q, y) - br3(P, y))[m]
    blok = np.array([f"{l}|{x}" for l, x in zip(lg, d_)])[m]
    dt = d_[m]; s2 = sorted(dt)[len(dt) // 2]; h2 = dt >= s2
    r = blok_boot(dl, blok); rb = blok_boot(db, blok)
    r["yari1"] = round(float(dl[~h2].mean()), 6); r["yari2"] = round(float(dl[h2].mean()), 6)
    ym = y[m]
    isabet = {"taban": round(float((P[m].argmax(1) == ym).mean()), 5), "aday": round(float((Q[m].argmax(1) == ym).mean()), 5)}
    # betimsel (karar değil): sınamada s beşte birlik kovaları — ev gerçek puan − piyasa beklenen
    sm, Pm = s[m], P[m]; qs = np.quantile(sm, [0, .2, .4, .6, .8, 1]); kova = []
    ev_puan = np.where(ym == 0, 3, np.where(ym == 1, 1, 0)); ev_bek = 3 * Pm[:, 0] + Pm[:, 1]
    for k in range(5):
        mk = (sm >= qs[k]) & (sm <= qs[k + 1] if k == 4 else sm < qs[k + 1])
        if mk.any(): kova.append({"s_ort": round(float(sm[mk].mean()), 4), "n": int(mk.sum()),
                                  "ev_puan_gercek": round(float(ev_puan[mk].mean()), 4), "ev_puan_piyasa": round(float(ev_bek[mk].mean()), 4),
                                  "ev_gercek": round(float((ym[mk] == 0).mean()), 4), "ev_piyasa": round(float(Pm[mk, 0].mean()), 4)})
    import oxx_ogren as O
    yol_fb = os.path.join(DATA, "fb_guc.json")
    try: A = json.load(open(yol_fb, encoding="utf-8"))
    except Exception: A = {}
    alan_k = f"fb_model-{date.today().year}"
    alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "literatür (Wheatcroft 2020; Vlastakis vd. 2009)"}})) if A else 0.0
    gecti = bool(r["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and rb["fark"] <= 0
                 and isabet["aday"] >= isabet["taban"] and r["p_tek"] <= alfa)
    sonuc = {"x12": {"dll": r, "dbrier": rb, "isabet": isabet, "kovalar": kova, "yarilar_siniri": s2,
                     "alfa_t": round(alfa, 5), "kapi_gecti": gecti}}
    print(json.dumps(sonuc, ensure_ascii=False))
    karne = {"tarih": date.today().isoformat(), "madde": "YH-37", "kaynak": "derin arşiv + season.json 2026 (türetilmiş)",
             "tasarim": {"yari_omur_mac": YARI_OMUR, "k0": K0, "sinama_bas": SINAMA_BAS, "izgara_eta": [float(IZ_E[0]), float(IZ_E[-1]), 0.02],
                         "aday": "sıralı logit kayması η·(R_ev − R_dep)"},
             "n_mac": len(rows), "n_gecmisli": int(gec.sum()), "katlar": katlar, "sonuc": sonuc,
             "karar": "gecti" if gecti else "reddedildi",
             "not": "Taban power marj ayırma (1X2); aday yalnız takım puan artığı farkı eğimi ekler. Artık yalnız önceki günlerden."}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and not karne["alfa_islendi"]:
        O.yatirim_guncelle(A, alan_k, alfa, gecti)
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "test": 1, "gecti": {"x12": gecti}}
    json.dump(karne, open(os.path.join(DATA, "takim_1x2_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", karne["karar"])


if __name__ == "__main__":
    main()
