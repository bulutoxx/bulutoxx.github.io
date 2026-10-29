#!/usr/bin/env python3
"""📏 YH-26 · Uyumlu (conformal) tahmin aralıkları — basket toplam sayı ve sayı farkı (ağsız, yalnız yerel veri).

Tahmin: üretim ridge'i (basket.fit), haftalık ileri yürüyüş (lab/bk_elo_lab.backtest ile aynı; her maç yalnız önceki maçlarla).
Hedef: %80 aralık. Her hafta, yalnız O HAFTADAN ÖNCE sonuçlanmış maçların artıklarından (lig başına, son PENCERE maç):
  T0 sabit      : seçim diliminin sonunda donmuş lig başına |artık| %80 niceliği (sabit genişlik; yol haritası tabanı)
  T1 normal     : ±1,2816·σ (σ = önceki artıkların std'si; üretimdeki σ varsayımı)
  C1 conformal  : bölünmüş conformal, |artık| ⌈(n+1)·0,8⌉/n niceliği (simetrik)
  C2 asimetrik  : işaretli artıkların %10 / %90 nicelikleri (yanlılığı da taşır)
  C3 uyarlamalı : C1 + uyarlamalı conformal (Gibbs & Candès 2021): α_t ← α_t + γ(α − hata_t), maç maç, lig başına
Seçim dilimi: her ligin puanlanabilen satırlarının ilk yarısı (zaman sıralı) — yöntem ve γ yalnız burada seçilir.
Sınama dilimi: ikinci yarı; tarih ortancasıyla iki alt dilim.
Kapı (yol haritası YH-26): sınamada gerçekleşen kapsama %80 ± 2 puan İKİ alt dilimde de; ortalama genişlik ≤ T0 (sabit) genişliği.
Lig grubu (pro / avrupa / kolej) ve hedef (toplam / fark) başına ayrı karar; arayüz yalnız geçen grup×hedefi gösterir.
Çıktı: data/aralik_lab.json (türetilmiş özet; ham maç verisi yok) ve geçen gruplar için data/bk_aralik.json (yayın bayrağı + güncel
lig başına aralık yarı genişlikleri/nicelikleri).
Kullanım: python3 lab/aralik_lab.py   (data/bk_games.json gerekir: actions/cache ya da `python3 lab/arsiv.py indir data/bk_games.json`)"""
import json, math, os, sys
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import bk_gelistir as G     # noqa: E402
from bk_elo_lab import backtest, GRUP  # noqa: E402

DATA = os.path.join(ROOT, "data")
HEDEF, Z80 = 0.80, 1.2816
PENCERE, MIN_KAL = 400, 60
TOL = 0.02
LIG_MIN_N, LIG_TOL = 100, 0.04      # yayın için lig tek başına: sınamada ≥ 100 maç ve kapsama %80 ± 4 puan
GAMMA = (0.002, 0.005, 0.01)


def nicelik_abs(r, a):
    """|artık| için conformal nicelik: ⌈(n+1)(1−a)⌉/n (n küçükse sonsuz yerine en büyük)."""
    n = len(r)
    if n == 0: return float("nan")
    k = min(n, int(math.ceil((n + 1) * (1 - a))))
    return float(np.sort(np.abs(r))[k - 1])


def aralik_satirlari(rows, hedef):
    """Lig içi, zaman sıralı: her satır için geçmiş artık penceresinden yöntem aralıkları. Çıktı: liste (gün, y, tahmin, {yöntem: (alt, üst)})."""
    rows = sorted(rows, key=lambda r: (r[3], r[0]["dt"]))
    y = np.array([(g["hs"] + g["as_"]) if hedef == "toplam" else (g["hs"] - g["as_"]) for g, *_ in rows], float)
    m = np.array([(mh + ma) if hedef == "toplam" else (mh - ma) for _, mh, ma, _ in rows], float)
    wk = [r[3] for r in rows]
    out, gecmis = [], []
    i = 0
    while i < len(rows):
        j = i
        while j < len(rows) and wk[j] == wk[i]: j += 1
        R = np.array(gecmis[-PENCERE:], float)
        if len(R) >= MIN_KAL:
            s = float(np.std(R))
            q1 = nicelik_abs(R, 1 - HEDEF)
            lo2, hi2 = float(np.quantile(R, 0.10)), float(np.quantile(R, 0.90))
            for t in range(i, j):
                out.append({"d": rows[t][0]["dt"][:10], "y": y[t], "m": m[t], "R": R, "s": s, "q1": q1, "a2": (lo2, hi2)})
        gecmis.extend((y[i:j] - m[i:j]).tolist())
        i = j
    return out


def degerlendir(sat, yontem, sabit_q=None, gamma=None):
    """Satırlar zaman sıralı (lig içi). Döner: kapsama dizisi, genişlik dizisi."""
    kap, gen = [], []
    a_t = 1 - HEDEF
    for x in sat:
        if yontem == "T0": lo, hi = x["m"] - sabit_q, x["m"] + sabit_q
        elif yontem == "T1": lo, hi = x["m"] - Z80 * x["s"], x["m"] + Z80 * x["s"]
        elif yontem == "C1": lo, hi = x["m"] - x["q1"], x["m"] + x["q1"]
        elif yontem == "C2": lo, hi = x["m"] + x["a2"][0], x["m"] + x["a2"][1]
        elif yontem == "C3":
            a_e = min(max(a_t, 0.005), 0.995); q = nicelik_abs(x["R"], a_e); lo, hi = x["m"] - q, x["m"] + q
        ic = 1.0 if lo <= x["y"] <= hi else 0.0
        kap.append(ic); gen.append(hi - lo)
        if yontem == "C3": a_t = a_t + gamma * ((1 - HEDEF) - (1 - ic))
    degerlendir.son_alfa = a_t
    return np.array(kap), np.array(gen)


def main():
    data, _bj = G.load()
    satir = {}            # (lig, hedef) -> satırlar
    for lg, (games, P, _L) in data.items():
        games.sort(key=lambda g: g["dt"])
        for g in games: g.setdefault("lg", lg)
        mt = 200 if lg in ("ncaa", "ncaaw") else 80
        rows, _wk0 = backtest(games, P, mt)
        for h in ("toplam", "fark"):
            satir[(lg, h)] = aralik_satirlari(rows, h)
        print(lg, len(rows), len(satir[(lg, "toplam")]), flush=True)

    R = {"tarih": date.today().isoformat(), "madde": "YH-26", "hedef_kapsama": HEDEF, "tolerans": TOL, "pencere": PENCERE,
         "min_kalibrasyon": MIN_KAL,
         "yontem": "Haftalık ileri yürüyüş (üretim ridge'i). Aralıklar yalnız önceki haftaların artıklarından (lig başına son "
                   f"{PENCERE} maç). Yöntem/γ seçimi her ligin ilk yarısında; karar ikinci yarıda, tarih ortancasıyla iki alt dilimde: "
                   "kapsama %80 ± 2 puan ikisinde de ve ortalama genişlik ≤ sabit genişlik (T0).",
         "kapi": "kapsama |k − 0,80| ≤ 0,02 her iki sınama yarısında; genişlik ≤ T0", "gruplar": {}}
    yayin = {}
    for grp in ("pro", "avrupa", "kolej"):
        for h in ("toplam", "fark"):
            ligler = [lg for lg in data if GRUP.get(lg) == grp and len(satir[(lg, h)]) >= 2 * MIN_KAL]
            if not ligler: continue
            sec_k, tes = {}, {}
            # lig başına seçim / sınama bölmesi ve T0 sabit genişliği (seçim diliminin |artık| niceliği)
            parca = {}
            for lg in ligler:
                s = satir[(lg, h)]; k = len(s) // 2
                sel, te = s[:k], s[k:]
                res_sel = np.array([x["y"] - x["m"] for x in sel])
                parca[lg] = (sel, te, nicelik_abs(res_sel, 1 - HEDEF))
            adaylar = [("T0", None), ("T1", None), ("C1", None), ("C2", None)] + [("C3", g) for g in GAMMA]
            for ad, gm in adaylar:
                ks, gs, kt, gt, dt = [], [], [], [], []
                lig_kap, son_alfa = {}, {}
                for lg in ligler:
                    sel, te, q0 = parca[lg]
                    # C3: α_t seçim diliminden sınamaya kesintisiz akar (yalnız geçmiş hatalarla güncellenir)
                    k_all, g_all = degerlendir(sel + te, ad, q0, gm)
                    if ad == "T0":
                        k_all = np.concatenate([np.full(len(sel), np.nan), k_all[len(sel):]])
                        g_all = np.concatenate([np.full(len(sel), np.nan), g_all[len(sel):]])
                    ks.append(k_all[:len(sel)]); gs.append(g_all[:len(sel)])
                    kt.append(k_all[len(sel):]); gt.append(g_all[len(sel):]); dt += [x["d"] for x in te]
                    lig_kap[lg] = {"n": len(te), "kapsama": round(float(k_all[len(sel):].mean()), 4)}
                    son_alfa[lg] = round(float(min(max(degerlendir.son_alfa, 0.005), 0.995)), 4)
                ks, gs = np.concatenate(ks), np.concatenate(gs)
                kt, gt, dt = np.concatenate(kt), np.concatenate(gt), np.array(dt)
                key = ad + (f"_g{gm}" if gm else "")
                sec_k[key] = {"kapsama": None if ad == "T0" else round(float(np.nanmean(ks)), 4),
                              "genislik": None if ad == "T0" else round(float(np.nanmean(gs)), 2)}
                med = np.sort(dt)[len(dt) // 2]
                yar = []
                for nm, mk in (("T1", dt < med), ("T2", dt >= med)):
                    yar.append({"ad": nm, "n": int(mk.sum()), "kapsama": round(float(kt[mk].mean()), 4), "genislik": round(float(gt[mk].mean()), 2)})
                tes[key] = {"n": int(len(kt)), "kapsama": round(float(kt.mean()), 4), "genislik": round(float(gt.mean()), 2), "yarilar": yar,
                            "ligler": lig_kap, "son_alfa": son_alfa if ad == "C3" else None}
            # seçim: kapsaması hedefe ±TOL içinde olanlar arasında en dar; yoksa hedefe en yakın (T0 seçimde ölçülemez → aday değil)
            uygun = [k for k, v in sec_k.items() if v["kapsama"] is not None and abs(v["kapsama"] - HEDEF) <= TOL]
            secilen = (min(uygun, key=lambda k: sec_k[k]["genislik"]) if uygun
                       else min((k for k in sec_k if sec_k[k]["kapsama"] is not None), key=lambda k: abs(sec_k[k]["kapsama"] - HEDEF)))
            t0g = tes["T0"]["genislik"]; c = tes[secilen]
            kap_ok = all(abs(y["kapsama"] - HEDEF) <= TOL for y in c["yarilar"])
            gen_ok = c["genislik"] <= t0g
            gecti = bool(kap_ok and gen_ok)
            R["gruplar"].setdefault(grp, {})[h] = {"ligler": ligler, "secim": sec_k, "secilen": secilen, "sinama": tes,
                                                   "kapsama_ok": kap_ok, "genislik_ok": gen_ok, "gecti": gecti}
            print(grp, h, secilen, c, "T0", t0g, "GEÇTİ" if gecti else "geçmedi", flush=True)
            if gecti:
                # yayın parametreleri: her lig için güncel (tüm geçmiş artıklardan, son PENCERE) yarı genişlik / nicelikler
                ad = secilen.split("_")[0]
                for lg in ligler:
                    lk = c["ligler"][lg]
                    if lk["n"] < LIG_MIN_N or abs(lk["kapsama"] - HEDEF) > LIG_TOL: continue   # lig tek başına da makul olmalı
                    a_son = (c["son_alfa"] or {}).get(lg, 1 - HEDEF)
                    s = satir[(lg, h)]
                    res = np.array([x["y"] - x["m"] for x in s])[-PENCERE:]
                    if ad in ("C1", "C3"):
                        q = nicelik_abs(res, a_son if ad == "C3" else 1 - HEDEF)
                        prm = {"alt": -round(q, 1), "ust": round(q, 1)}
                    elif ad == "C2":
                        prm = {"alt": round(float(np.quantile(res, .10)), 1), "ust": round(float(np.quantile(res, .90)), 1)}
                    else:
                        continue
                    yayin.setdefault(lg, {})[h] = dict(prm, n=int(len(res)), yontem=secilen)
    R["yayin_ligleri"] = sorted(yayin)
    json.dump(R, open(os.path.join(DATA, "aralik_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, allow_nan=False)
    bayrak = {"aktif": bool(yayin), "tarih": R["tarih"], "hedef": HEDEF, "ligler": yayin,
              "kanit": "data/aralik_lab.json", "aciklama": "YH-26: yalnız kapsaması sınamada kanıtlanan lig×hedef için %80 aralık "
              "(tahmin + alt … tahmin + üst). Geri alma: aktif=false."}
    json.dump(bayrak, open(os.path.join(DATA, "bk_aralik.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, allow_nan=False)
    print("yayın:", sorted(yayin))


if __name__ == "__main__":
    main()
