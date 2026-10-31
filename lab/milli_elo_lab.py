#!/usr/bin/env python3
"""🌍 YH-20 laboratuvarı: milli takım Elo'su zaman sıralı (sızıntısız) sınama.

Taban ("lig ortalaması"): geçmiş 12 yılın 1X2 sıklığı, ev sahibi / tarafsız saha ayrı.
Aday: Dünya Futbol Elo usulü puan (scripts/milli_elo.py) + sıralı lojit 1X2 eşlemesi.
Sızıntı yok: Elo her maçtan önce okunur (çevrimiçi); eşleme ve taban her sınama yılında yalnız önceki yıllarla öğrenilir;
H / R0 / K çarpanı yalnız SECIM dilimi (2008–2015) ile seçilir, sınama 2016-01-01 → bugün.
Yalnız FIFA içi yarışmalar sınanır (CONIFA, ada oyunları vb. puanlanır ama sınanmaz).

Kapı (SK): sınamada ΔLL (aday − taban) gün-blok bootstrap %95 GA üst < 0 · iki zaman yarısında ΔLL < 0 · ΔBrier ≤ 0 ·
tek yanlı p ≤ α_t (alfa yatırımı fb_model-<yıl>, sinyalli aday). Oranlı alt küme için piyasa karşılaştırması
CC0'da yok → yalnız kilitli gölge kayıttan rapor (data/milli_elo_golge.json; ≥ 60 sonuçlu kayıtta).

  python3 lab/milli_elo_lab.py            → data/milli_elo_lab.json (+ data/milli_elo.json → params, kapi)
"""
import json, math, os, sys
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import milli_elo as ME  # noqa: E402

RNG = np.random.default_rng(20)
B_BOOT = 2000
SECIM = ("2008-01-01", "2016-01-01")
SINAMA = "2016-01-01"
PENCERE = 12   # yıl


def ll3(P, y): return -np.log(np.clip(P[np.arange(len(y)), y], 1e-9, 1))
def br3(P, y): return ((P - np.eye(3)[y]) ** 2).sum(1)


def blok_boot(delta, blok, B=B_BOOT):
    u, inv = np.unique(blok, return_inverse=True)
    s = np.bincount(inv, delta, len(u)); n = np.bincount(inv, None, len(u))
    idx = RNG.integers(0, len(u), (B, len(u)))
    bs = s[idx].sum(1) / n[idx].sum(1)
    return {"fark": round(float(delta.mean()), 5), "ga95": [round(float(np.quantile(bs, .025)), 5), round(float(np.quantile(bs, .975)), 5)],
            "p_tek": round(float((bs >= 0).mean()), 4), "n": int(len(delta)), "blok": int(len(u))}


def hazirla(oyn):
    d = np.array([m[0] for m in oyn]); yil = np.array([int(m[0][:4]) for m in oyn])
    y = np.array([0 if m[3] > m[4] else (1 if m[3] == m[4] else 2) for m in oyn])
    ntr = np.array([m[6] for m in oyn]); fifa = np.array([not ME.FIFA_DISI.search(m[5]) for m in oyn])
    hz = np.array([m[5] == "Friendly" for m in oyn])
    return d, yil, y, ntr, fifa, hz


def ileri(oyn, P, bas, bit, D):
    """[bas, bit) yıllarında yıl yıl: eşleme + taban yalnız önceki PENCERE yılla. Dönüş: maske, P_aday, P_taban."""
    d, yil, y, ntr, fifa, hz = D
    drs = np.zeros(len(oyn))
    def kay(i, dr): drs[i] = dr
    ME.puanla(oyn, P, kay)
    Pa = np.full((len(oyn), 3), np.nan); Pt = np.full((len(oyn), 3), np.nan)
    for Y in range(bas, bit):
        te = fifa & (yil == Y)
        if not te.any(): continue
        tr = fifa & (yil >= Y - PENCERE) & (yil < Y)
        M = ME.sirali_lojit(drs[tr] / 400.0, y[tr])
        z = drs[te] / 400.0
        pa = 1 / (1 + np.exp(-(M["t1"] - M["b"] * z))); pax = 1 / (1 + np.exp(-(M["t2"] - M["b"] * z)))
        Pa[te] = np.clip(np.c_[1 - pax, pax - pa, pa], 1e-4, 1)
        for nt in (False, True):
            m_tr = tr & (ntr == nt); m_te = te & (ntr == nt)
            f = np.bincount(y[m_tr], minlength=3) + 1.0
            Pt[m_te] = f / f.sum()
    Pa /= Pa.sum(1, keepdims=True)
    return Pa, Pt


def main():
    metin = ME.indir()
    oyn, _ = ME.satirlar(metin)
    D = hazirla(oyn); d, yil, y, ntr, fifa, hz = D
    print("maç", len(oyn), "son", oyn[-1][0])
    # 1) seçim: yalnız 2008–2015
    y0, y1 = int(SECIM[0][:4]), int(SECIM[1][:4])
    ms = fifa & (yil >= y0) & (yil < y1)
    izgara = []
    for H in (60.0, 80.0, 100.0, 120.0):
        for R0 in (1300.0, 1400.0, 1500.0):
            for kc in (0.8, 1.0, 1.25):
                P = {"H": H, "R0": R0, "K_carp": kc}
                Pa, _ = ileri(oyn, P, y0, y1, D)
                izgara.append((float(ll3(Pa[ms], y[ms]).mean()), P))
    izgara.sort(key=lambda t: t[0])
    Pbest = izgara[0][1]
    print("seçim", Pbest, "LL", round(izgara[0][0], 5), "| varsayılan", next(round(l, 5) for l, p in izgara if p == ME.P0))
    # 2) sınama 2016 → bugün
    Pa, Pt = ileri(oyn, Pbest, int(SINAMA[:4]), int(date.today().year) + 1, D)
    ok = fifa & (d >= SINAMA) & ~np.isnan(Pa[:, 0]) & ~np.isnan(Pt[:, 0])
    dll = (ll3(Pa, y) - ll3(Pt, y))[ok]; dbr = (br3(Pa, y) - br3(Pt, y))[ok]
    dT = d[ok]; s2 = sorted(dT)[len(dT) // 2]; h2 = dT >= s2
    blok = d[ok]
    r_ll = blok_boot(dll, blok); r_br = blok_boot(dbr, blok)
    r_ll["yari1"] = round(float(dll[~h2].mean()), 5); r_ll["yari2"] = round(float(dll[h2].mean()), 5)
    def oz(P, m): return {"n": int(m.sum()), "ll": round(float(ll3(P[m], y[m]).mean()), 5), "brier": round(float(br3(P[m], y[m]).mean()), 5),
                          "isabet": round(float((P[m].argmax(1) == y[m]).mean()), 4)}
    alt = {}
    for ad, m in (("hazirlik", ok & hz), ("resmi", ok & ~hz), ("tarafsiz", ok & ntr), ("ev_sahipli", ok & ~ntr)):
        alt[ad] = {"aday": oz(Pa, m), "taban": oz(Pt, m), "dll": round(float((ll3(Pa, y) - ll3(Pt, y))[m].mean()), 5)}
    # kalibrasyon (aday, ev kazanır olasılığı 10 kovada)
    kal = []
    ph = Pa[ok, 0]; yh = (y[ok] == 0)
    for lo in np.arange(0, 1, 0.1):
        m = (ph >= lo) & (ph < lo + 0.1)
        if m.sum() >= 30: kal.append([round(float(lo), 1), int(m.sum()), round(float(ph[m].mean()), 3), round(float(yh[m].mean()), 3)])
    import oxx_ogren as O
    yol_fb = os.path.join(DATA, "fb_guc.json")
    try: A = json.load(open(yol_fb, encoding="utf-8"))
    except Exception: A = {}
    alan_k = f"fb_model-{date.today().year}"
    alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "literatür (Hvattum & Arntzen 2010; Lasek 2013)"}}))
    gecti = bool(r_ll["ga95"][1] < 0 and r_ll["yari1"] < 0 and r_ll["yari2"] < 0 and r_br["fark"] <= 0 and r_ll["p_tek"] <= alfa)
    # gölge (piyasa karşılaştırması; yalnız rapor)
    try: G = json.load(open(ME.GOLGE, encoding="utf-8"))["kayit"]
    except Exception: G = []
    gs = [k for k in G if k.get("sonuc") and k.get("piyasa") and None not in k["piyasa"]]
    golge = {"n_kayit": len(G), "n_sonuclu_piyasali": len(gs), "esik": 60}
    if gs:
        yy = np.array([0 if k["sonuc"][0] > k["sonuc"][1] else (1 if k["sonuc"][0] == k["sonuc"][1] else 2) for k in gs])
        PE = np.array([k["elo"] for k in gs]); PM = np.array([k["piyasa"] for k in gs]); PM = PM / PM.sum(1, keepdims=True)
        golge.update({"elo_ll": round(float(ll3(PE, yy).mean()), 5), "piyasa_ll": round(float(ll3(PM, yy).mean()), 5)})
    karne = {"tarih": date.today().isoformat(), "madde": "YH-20", "kaynak": "martj42/international_results (CC0)",
             "n_mac": len(oyn), "son_mac": oyn[-1][0], "secim_dilimi": SECIM, "sinama_baslangic": SINAMA, "yarilar_siniri": s2,
             "secilen": Pbest, "izgara_ilk5": [[round(l, 5), p] for l, p in izgara[:5]],
             "aday": oz(Pa, ok), "taban": oz(Pt, ok), "dll": r_ll, "dbrier": r_br, "alt_kume": alt, "kalibrasyon_ev": kal,
             "alfa_t": round(alfa, 5), "kapi_gecti": gecti, "karar": "gecti" if gecti else "reddedildi", "golge_piyasa": golge,
             "not": "Taban = geçmiş 12 yılın 1X2 sıklığı (ev / tarafsız ayrı). Piyasaya karşı ölçüm yalnız kilitli gölge kayıttan."}
    json.dump(karne, open(os.path.join(DATA, "milli_elo_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # alfa yatırımı yalnız ilk kararda işlenir (haftalık yeniden ölçüm serveti tekrar tekrar değiştirmez)
    try: onceki = json.load(open(os.path.join(DATA, "milli_elo_lab.json"), encoding="utf-8"))
    except Exception: onceki = {}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and not karne["alfa_islendi"]:
        O.yatirim_guncelle(A, alan_k, alfa, gecti)
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "alfa": round(alfa, 5), "gecti": gecti}
    json.dump(karne, open(os.path.join(DATA, "milli_elo_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # üretim puan dosyasına seçilen parametre + kapı özeti
    try: E = json.load(open(ME.CIKTI, encoding="utf-8"))
    except Exception: E = {}
    E["params"] = Pbest
    E["kapi"] = {"tarih": karne["tarih"], "gecti": gecti, "dll": r_ll["fark"], "ga95": r_ll["ga95"], "n": r_ll["n"]}
    ME._yaz(ME.CIKTI, E)
    print(f"sınama n {r_ll['n']} | aday LL {karne['aday']['ll']} taban {karne['taban']['ll']} | ΔLL {r_ll['fark']} GA {r_ll['ga95']} "
          f"yarılar {r_ll['yari1']}/{r_ll['yari2']} p {r_ll['p_tek']} α {alfa:.5f} | ΔBrier {r_br['fark']} | isabet "
          f"{karne['aday']['isabet']} vs {karne['taban']['isabet']} → {'GEÇTİ' if gecti else 'geçmedi'}")
    for k, v in alt.items(): print(" ", k, v)


if __name__ == "__main__":
    main()
