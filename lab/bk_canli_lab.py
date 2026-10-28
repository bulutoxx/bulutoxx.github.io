#!/usr/bin/env python3
"""YH-05 çevrimdışı sınama: basket canlı kazanma olasılığı, geçmiş maçların çeyrek / devre sonu skorlarıyla.

Canlı kayıt yeni başladığı için (data/archive/bk_live/) ilk kanıt arşivdeki çeyrek skorlarından gelir: her maç için
1., 2., 3. çeyrek sonu (NCAA erkek: devre arası) anlık görüntüsü; maç öncesi fark ve σ üretim modelinin haftalık ileri
yürüyüşünden (her maç yalnız önceki maçlarla, σ yalnız önceki haftaların artıklarından).
  eski  = Φ((d + fark·r) / max(1,5; sm·√r))                          (uygulamadaki bkLivePred)
  yeni  = Φ((d + w·μ·r) / max(1,5; k·σ·r^(0,5+γ))), σ = sm·√(toplam/2mu), μ = σ·Φ⁻¹(p0)   (scripts/bk_canli.py)
(k, w, γ) haftalık, yalnız ÖNCEKİ haftaların anlık görüntüleriyle en çok olabilirlik (ilk haftalar: k=w=1, γ=0).
Kapı: maç-blok bootstrap B=2000, ΔLL GA üst < 0, iki zaman yarısında ΔLL < 0, ΔBrier ≤ 0, isabet düşmez.
Çıktı: data/bk_canli_lab.json; --yaz: data/bk_canli.json onbilgi (tüm veriyle öğrenilmiş k, w, γ; kullan bayrağına dokunmaz).
"""
import json, os, sys
from datetime import date, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import bk_gelistir as BG        # noqa: E402
import bk_canli as C            # noqa: E402
from bk_dinlenme_lab import backtest_uretim   # noqa: E402

OUT = os.path.join(ROOT, "data", "bk_canli_lab.json")


def anliklar(data):
    rows = []
    for lg, (games, P, L) in data.items():
        mt = 200 if lg in ("ncaa", "ncaaw") else 80
        R = sorted(backtest_uretim(games, P, mt), key=lambda r: r[0]["dt"])
        halves = bool(L.get("halves"))
        weeks = sorted({r[3] for r in R})
        for wk in weeks:
            prior = [r for r in R if r[3] < wk]
            if len(prior) < BG.MIN_PRIOR: continue
            sm = float(np.std([(r[0]["hs"] - r[0]["as_"]) - (r[1] - r[2]) for r in prior]))
            mu2 = float(np.mean([r[0]["hs"] + r[0]["as_"] for r in prior[-1500:]]))
            for g, mh, ma, _ in (r for r in R if r[3] == wk):
                if g["hs"] == g["as_"]: continue
                hq, aq = g.get("hq") or [], g.get("aq") or []
                cuts = [1] if halves else [1, 2, 3]
                need = 2 if halves else 4
                if len(hq) < need or len(aq) < need: continue
                mar, tot = mh - ma, mh + ma; p0 = C.phi(mar / sm); y = 1.0 if g["hs"] > g["as_"] else 0.0
                for c in cuts:
                    d = sum(hq[:c]) - sum(aq[:c]); r = 1 - c / (2 if halves else 4)
                    rows.append({"lg": lg, "mac": g["id"], "gun": g["dt"][:10], "hafta": wk.isoformat(), "d": d, "r": r, "p0": p0,
                                 "sg": C.sigma_mac(sm, tot, mu2), "mar": mar, "sm": sm, "y": y, "c": c})
    return rows


def main():
    data, _ = BG.load()
    rows = anliklar(data)
    A = {k: np.array([x[k] for x in rows], float) for k in ("d", "r", "p0", "sg", "mar", "sm", "y")}
    hafta = np.array([x["hafta"] for x in rows]); mac = [x["mac"] for x in rows]; gun = [x["gun"] for x in rows]
    pe = C.p_eski_v(A["d"], A["r"], A["mar"], A["sm"]); pn = np.zeros(len(rows)); prm_iz = {}
    hl = sorted(set(hafta))
    for i, wk in enumerate(hl):
        tr = hafta < wk; te = hafta == wk
        prm = C.ogren({k: A[k][tr] for k in ("d", "r", "p0", "sg", "y")}) if tr.sum() >= 300 else dict(C.VARSAYILAN)
        if i % 8 == 0: prm_iz[wk] = prm
        pn[te] = C.p_yeni_v(A["d"][te], A["r"][te], A["p0"][te], A["sg"][te], prm["k"], prm["w"], prm["g"])
    # aynı formül, öğrenmesiz (k=w=1, γ=0): yalnız tempo ölçeği + piyasa/model olasılığından sürüklenme
    p1 = C.p_yeni_v(A["d"], A["r"], A["p0"], A["sg"], 1.0, 1.0, 0.0)
    K = C.kapi(pe, pn, A["y"], mac, gun)
    K1 = C.kapi(pe, p1, A["y"], mac, gun)
    lg_a = np.array([x["lg"] for x in rows]); c_a = np.array([x["c"] for x in rows])
    def alt(mask):
        if not mask.any(): return None
        y = A["y"][mask]
        return {"n": int(mask.sum()), "ll_eski": round(float(C.ll_v(pe[mask], y).mean()), 4), "ll_yeni": round(float(C.ll_v(pn[mask], y).mean()), 4),
                "isabet_eski": round(float(((pe[mask] >= .5) == (y == 1)).mean()), 4), "isabet_yeni": round(float(((pn[mask] >= .5) == (y == 1)).mean()), 4)}
    tum_prm = C.ogren({k: A[k] for k in ("d", "r", "p0", "sg", "y")})
    rep = {"tarih": date.today().isoformat(), "kaynak": "data/bk_games.json çeyrek / devre skorları (arşiv), üretim modeli haftalık ileri yürüyüş",
           "n_anlik": len(rows), "n_mac": len(set(mac)), "kapi_yeni": K, "kapi_ogrenmesiz": K1,
           "lig": {lg: alt(lg_a == lg) for lg in sorted(set(lg_a))},
           "an": {f"{c}. çeyrek / devre sonu": alt(c_a == c) for c in (1, 2, 3)},
           "prm_tum": tum_prm, "prm_iz": prm_iz}
    json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: rep[k] for k in ("n_anlik", "n_mac", "prm_tum")}, ensure_ascii=False))
    print("yeni:", json.dumps({k: K[k] for k in ("tum", "gecti", "ll_eski", "ll_yeni", "isabet_eski", "isabet_yeni")}, ensure_ascii=False))
    print("öğrenmesiz:", json.dumps({k: K1[k] for k in ("tum", "gecti", "ll_eski", "ll_yeni")}, ensure_ascii=False))
    print(json.dumps(rep["an"], ensure_ascii=False)); print(json.dumps(rep["lig"], ensure_ascii=False))
    if "--yaz" in sys.argv:
        S = C.ayar(); S["onbilgi"] = tum_prm
        if not S.get("kullan"): S["prm"] = tum_prm
        S["onbilgi_kaynak"] = {"tarih": rep["tarih"], "n_anlik": len(rows), "n_mac": len(set(mac)), "kapi": {k: K[k] for k in ("tum", "gecti")},
                               "dosya": "data/bk_canli_lab.json"}
        C.kaydet_json(C.AYAR, S)


if __name__ == "__main__":
    main()
