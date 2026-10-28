#!/usr/bin/env python3
"""YH-04 sınaması: dinlenme / arka arkaya maç / deplasman serisi / seyahat düzeltmesi (scripts/bk_dinlenme.py).

Yöntem (ağsız; data/bk_games.json — iş akışında lab/arsiv.py indir ile gelir):
  * Üretim modeli (basket.fit, ortak ev avantajı ligleri dahil) haftalık ileri yürüyüş: her maç yalnız önceki maçlarla.
  * Aday: aynı tahmin + Δfark = β·x; β lig grubu başına yalnız o haftadan ÖNCEKİ tahmin artıklarından (ridge, ön bilgi 0).
  * Olasılık Φ(fark/σ); σ her hafta yalnız önceki haftaların artıklarından (aday için düzeltilmiş artıklar).
  * Kapı (lab/bk_gelistir.gate): gün kümeli bootstrap B=2000; tüm + iki zaman dilimi: ΔLL GA üst < 0, ΔBrier < 0, isabet düşmez.
Çıktı: data/bk_dinlenme_lab.json (türetilmiş özet). --yaz: geçen gruplar için data/bk_dinlenme.json kullan[grup]=true ve β.
"""
import json, os, sys
from datetime import date, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import basket as B          # noqa: E402
import bk_gelistir as BG    # noqa: E402
import bk_dinlenme as D     # noqa: E402

OUT = os.path.join(ROOT, "data", "bk_dinlenme_lab.json")
VARYANT = {"b2b": [0], "b2b_dinlenme": [0, 1], "tam": [0, 1, 2, 3], "b2b_onbilgi": [0]}
# ön bilgi (yalnız literatür, bu veriden değil): FiveThirtyEight NBA — arka arkaya maç ≈ 46 Elo ≈ 1,6 sayı; kolejde b2b nadir ve etkisi bilinmiyor
ONBILGI = {"b2b_onbilgi": {"pro": [1.6, 0, 0, 0]}}


def backtest_uretim(games, P, mt):
    """basket.backtest ile aynı (üretim fit'i, ortak ev avantajı ligleri dahil); satıra hafta eklenir."""
    if len(games) < mt + 30: return []
    dts = [BG.d_of(g) for g in games]; wk, last = dts[mt], dts[-1]; rows = []
    while wk <= last:
        nxt = wk + timedelta(days=7)
        train = [g for g, d in zip(games, dts) if d < wk and (wk - d).days <= 400]
        test = [g for g, d in zip(games, dts) if wk <= d < nxt]
        if test and len(train) >= mt:
            F = B.fit(train, wk, P)
            for g in test:
                pm = B.pred_means(F, g["h"], g["a"], g.get("neutral", False), P.get("newp"))
                if pm: rows.append((g, pm[0], pm[1], wk))
        wk = nxt
    return rows


def duzelt(rows_by_lg, X, ozler, b0g=None):
    """Grup başına zaman sıralı β; dönüş: lig → düzeltilmiş satırlar, son β'lar."""
    out = {lg: [] for lg in rows_by_lg}; son = {}
    for g in sorted(set(D.GRUP.values())):
        R = sorted([(lg, r) for lg, rows in rows_by_lg.items() if D.GRUP.get(lg) == g for r in rows], key=lambda z: z[1][3])
        weeks = sorted({r[3] for _, r in R}); beta = [0.0] * len(D.OZ); b0 = (b0g or {}).get(g)
        for wk in weeks:
            prior = [r for _, r in R if r[3] < wk and r[0]["id"] in X]
            beta = D.beta_fit([X[r[0]["id"]] for r in prior], [(r[0]["hs"] - r[0]["as_"]) - (r[1] - r[2]) for r in prior], ozler=ozler, b0=b0)
            for lg, r in R:
                if r[3] != wk: continue
                dd = D.delta(X.get(r[0]["id"]), beta)
                out[lg].append((r[0], r[1] + dd / 2, r[2] - dd / 2, r[3]))
        son[g] = [round(b, 3) for b in beta]
    return out, son


def main():
    data, bj = BG.load()
    rows, X = {}, {}
    for lg, (games, P, L) in data.items():
        mt = 200 if lg in ("ncaa", "ncaaw") else 80
        rows[lg] = backtest_uretim(games, P, mt)
        X.update(D.ozellikler(games))
        print(lg, len(rows[lg]), flush=True)
    # özellik dağılımı (tanı)
    tani = {}
    for lg in data:
        xs = np.array([X[r[0]["id"]] for r in rows[lg]]) if rows[lg] else np.zeros((0, 4))
        if len(xs): tani[lg] = {"n": len(xs), "b2b_fark_sifirdan_farkli": round(float(np.mean(xs[:, 0] != 0)), 3),
                                "dinlenme_fark_ort_mutlak": round(float(np.mean(np.abs(xs[:, 1]))), 2),
                                "seri_fark_ort_mutlak": round(float(np.mean(np.abs(xs[:, 2]))), 2), "yol_fark_ort_mutlak_bin_km": round(float(np.mean(np.abs(xs[:, 3]))), 3)}
    base_pg = {}
    for lg in data: base_pg.update(BG.per_game(rows[lg], BG.probs(rows[lg], "std")))
    lg_of = {r[0]["id"]: lg for lg in data for r in rows[lg]}
    rep = {"tarih": date.today().isoformat(), "kaynak": "data/bk_games.json (arşiv) · " + ", ".join(f"{lg} {len(rows[lg])}" for lg in data),
           "yontem": "haftalık ileri yürüyüş (üretim fit'i); β grup başına yalnız önceki haftaların artıklarından; σ önceki haftalardan",
           "kapi": "gün kümeli bootstrap B=2000; tüm + iki zaman dilimi: ΔLL GA üst < 0, ΔBrier < 0, isabet Δ ≥ 0",
           "mevcut": BG.summary(base_pg), "tani": tani, "adaylar": {}}
    for v, oz in VARYANT.items():
        cr, son = duzelt(rows, X, oz, ONBILGI.get(v))
        pg = {}
        for lg in data: pg.update(BG.per_game(cr[lg], BG.probs(cr[lg], "std")))
        gt = BG.gate(base_pg, pg, rows); gt["ozet"] = BG.summary({i: x for i, x in pg.items() if i in base_pg}); gt["son_beta"] = son
        gt["grup"] = {}
        for g in sorted(set(D.GRUP.values())):
            ids = {i for i in base_pg if D.GRUP.get(lg_of.get(i)) == g and i in pg}
            if not ids: continue
            rg = {lg: rr for lg, rr in rows.items() if D.GRUP.get(lg) == g}
            sub_b = {i: base_pg[i] for i in ids}; sub_c = {i: pg[i] for i in ids}
            gg = BG.gate(sub_b, sub_c, rg)
            gt["grup"][g] = {k: gg[k] for k in ("tum", "dilim1", "dilim2", "gecti")}
            gt["grup"][g]["mevcut"] = BG.summary(sub_b); gt["grup"][g]["aday"] = BG.summary(sub_c)
        gt["lig"] = {lg: BG.boot(base_pg, pg, {i for i in base_pg if lg_of.get(i) == lg and i in pg}, 500) for lg in data if any(lg_of.get(i) == lg for i in pg)}
        rep["adaylar"][v] = gt
        print(v, json.dumps({k: gt[k] for k in ("tum", "dilim1", "dilim2", "gecti")}, ensure_ascii=False), {g: x["gecti"] for g, x in gt["grup"].items()}, son, flush=True)
    # karar: grup başına, geçen varyantlardan tüm ΔLL'si en düşük olan
    karar = {}
    for g in sorted(set(D.GRUP.values())):
        ok = [(rep["adaylar"][v]["grup"][g]["tum"]["d_ll"], v) for v in VARYANT if g in rep["adaylar"][v]["grup"] and rep["adaylar"][v]["grup"][g]["gecti"]]
        karar[g] = {"gecti": bool(ok), "varyant": min(ok)[1] if ok else None}
    rep["karar"] = karar
    json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar", karar)
    if "--yaz" in sys.argv:
        A = D.ayar(); A.setdefault("kullan", {})
        sinir = (date.today() - timedelta(days=30)).isoformat()
        A["kapi"] = {"tarih": date.today().isoformat(), "karar": karar, "dosya": "data/bk_dinlenme_lab.json",
                     "ozet": {v: {g: {k: x["tum"][k] for k in ("n", "d_ll", "d_ll_ga", "d_isabet")} for g, x in a["grup"].items()} for v, a in rep["adaylar"].items()}}
        for g, k in karar.items():
            geri = any(x.get("grup") == g and x.get("olay") == "geri_alindi" and x.get("tarih", "") >= sinir for x in A.get("gecmis", []))
            if k["gecti"] and not A["kullan"].get(g) and not geri:
                A["kullan"][g] = True; A.setdefault("izleme", {})[g] = {"kabul_tarihi": date.today().isoformat()}
                A.setdefault("ozler_grup", {})[g] = VARYANT[k["varyant"]]
                A.setdefault("gecmis", []).append({"tarih": date.today().isoformat(), "grup": g, "olay": "kabul", "varyant": k["varyant"],
                                                   "kanit": rep["adaylar"][k["varyant"]]["grup"][g]["tum"]})
        D.kaydet(A)


if __name__ == "__main__":
    main()
