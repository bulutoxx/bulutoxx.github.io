#!/usr/bin/env python3
"""🏁 YH-30 laboratuvarı: hafta ortası maç yükü (son ≤ 4 günde resmi maç) — piyasa üstü bilgi var mı? Zaman sıralı sınama.

Soru: Son 72–96 saatte (tarih farkı ≤ 4 gün) resmi maç oynamış takım, piyasa olasılığının söylediğinden daha mı kötü oynuyor?
(Scoppa 2015: turnuva verisinde dinlenme etkisi küçük; piyasa kısmen fiyatlıyor.)

Veri: data/season.json (ESPN; lig maçları + Şampiyonlar / Avrupa / Konferans Ligi; kupa takımları `hl/al` ile lig kimliğine bağlı,
ad eşleme %100). Ulusal kupalar arşivde yok → kupa sonrası yük eksik ölçülür (etki küçülür, yanlış pozitif üretmez).
Önceden kayıtlı tasarım (ızgara yalnız eğitim katında):
  • yük(i) = takımın bu maçtan ÖNCEKİ son resmi maçı (lig ya da Avrupa) ≤ 4 gün önce. Takımın arşivdeki ilk maçı yüksüz sayılır.
  • Aday 1X2: log q = log p_piyasa + [β·d, γ·b, −β·d] (d = yük_dep − yük_ev, b = ikisi de yüklü), normalize.
    Aday 2,5 A/Ü: logit q = logit p_piyasa + η·(yük_ev + yük_dep).
  • Taban: power marj ayırma (YH-29 ile aynı).
  • Yürüyen pencere: 2026-01'den başlayan aylık genişleyen katlar; her kat yalnız kendinden önceki maçlarla (β, γ, η) seçer.
Kapı (SK): sınamada ≥ 1.500 yüklü maç (yoksa "veri yetersiz", gölgede) · ΔLL lig×gün blok bootstrap B = 2000 %95 GA üst < 0 ·
iki zaman yarısında ΔLL < 0 · ΔBrier ≤ 0 · tek yanlı p ≤ α_t (alfa yatırımı fb_model-<yıl>, sinyalli aday). 1X2 ve 2,5 ayrı.
Betimsel (karar değil): Avrupa kaynaklı yük ve Avrupa deplasmanı sonrası alt kümeler.

  python3 lab/yuk_lab.py      → data/yuk_lab.json
"""
import json, os, sys
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))
from motivasyon_lab import power, q1x2, qou, ll3, br3, ll2, br2, blok_boot, IZ_B, IZ_G, IZ_E  # noqa: E402

AVRUPA = ("ucl", "uel", "uecl")
ESIK_GUN = 4
MIN_YUKLU = 1500


def gun(s): return date.fromisoformat(s[:10]).toordinal()


def satirlar(S):
    """Her takım (lig kimliği|ad) için resmi maç takvimi; sonra oranlı lig maçlarına yük göstergeleri."""
    tk = {}  # anahtar → [(gün, avrupa?, deplasman?)]
    for lg, v in S.items():
        for m in v.get("matches", []):
            if not m.get("ft") or not m.get("d"): continue
            g = gun(m["d"])
            if lg in AVRUPA:
                if m.get("hl"): tk.setdefault(f"{m['hl']}|{m['h']}", []).append((g, 1, 0))
                if m.get("al"): tk.setdefault(f"{m['al']}|{m['a']}", []).append((g, 1, 1))
            else:
                tk.setdefault(f"{lg}|{m['h']}", []).append((g, 0, 0))
                tk.setdefault(f"{lg}|{m['a']}", []).append((g, 0, 1))
    for k in tk: tk[k].sort()

    def onceki(k, g):
        L = tk.get(k, []); son = None
        for x in L:
            if x[0] < g: son = x
            else: break
        if son is None or g - son[0] > ESIK_GUN: return 0, 0, 0
        return 1, son[1], int(son[1] and son[2])

    out = []
    for lg, v in S.items():
        if lg in AVRUPA: continue
        for m in v.get("matches", []):
            o = m.get("odds"); ft = m.get("ft")
            if not ft or not o or len(o) != 3 or not all(o) or ft[0] is None: continue
            g = gun(m["d"])
            yh, eh, th = onceki(f"{lg}|{m['h']}", g); ya, ea, ta = onceki(f"{lg}|{m['a']}", g)
            ou = m.get("ou"); pO = power(ou)[0] if ou and len(ou) == 2 and all(ou) else None
            hg, ag = ft
            out.append((m["d"][:10], lg, yh, ya, eh, ea, th, ta, 0 if hg > ag else (1 if hg == ag else 2), power(o), pO, hg + ag > 2))
    out.sort(key=lambda r: r[0])
    return out


def main():
    try: onceki = json.load(open(os.path.join(DATA, "yuk_lab.json"), encoding="utf-8"))
    except Exception: onceki = {}
    S = json.load(open(os.path.join(DATA, "season.json"), encoding="utf-8"))
    rows = satirlar(S)
    d_ = np.array([r[0] for r in rows]); lg = np.array([r[1] for r in rows])
    yh, ya, eh, ea, th, ta = (np.array([r[k] for r in rows]) for k in range(2, 8))
    y = np.array([r[8] for r in rows]); P = np.array([r[9] for r in rows])
    hasO = np.array([r[10] is not None for r in rows]); pO = np.array([r[10] if r[10] is not None else .5 for r in rows])
    yo = np.array([r[11] for r in rows])
    dd = (ya - yh).astype(float); bb = (yh & ya).astype(float); ss = (yh + ya).astype(float); yuk = (yh + ya) > 0
    print("maç", len(rows), "| yüklü taraflı", int(yuk.sum()), "| Avrupa kaynaklı", int(((eh + ea) > 0).sum()))
    cuts = [f"{Y}-{M:02d}-01" for Y in (2026,) for M in range(1, 13)] + ["9999"]
    Q = P.copy(); QO = pO.copy(); katlar = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        tr = d_ < a; te = (d_ >= a) & (d_ < b)
        if not te.any(): continue
        trm = tr & yuk; best = (0.0, 0.0); bl = None
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
        katlar.append({"kat": a, "n_sinama": int(te.sum()), "n_egitim_yuklu": int(trm.sum()), "beta": best[0], "gamma": best[1],
                       "eta": et, "n_sinama_yuklu": int((te & yuk).sum())})
        print(katlar[-1])
    te_all = d_ >= cuts[0]
    blok = np.array([f"{l}|{x}" for l, x in zip(lg, d_)])
    import oxx_ogren as O
    yol_fb = os.path.join(DATA, "fb_guc.json")
    try: A = json.load(open(yol_fb, encoding="utf-8"))
    except Exception: A = {}
    alan_k = f"fb_model-{date.today().year}"
    sonuc = {}
    for pazar in ("1x2", "ou25"):
        m = te_all if pazar == "1x2" else te_all & hasO
        if pazar == "1x2": dl = (ll3(Q, y) - ll3(P, y))[m]; db = (br3(Q, y) - br3(P, y))[m]
        else: dl = (ll2(QO, yo) - ll2(pO, yo))[m]; db = (br2(QO, yo) - br2(pO, yo))[m]
        dt = d_[m]; s2 = sorted(dt)[len(dt) // 2]; h2 = dt >= s2
        r = blok_boot(dl, blok[m]); rb = blok_boot(db, blok[m])
        r["yari1"] = round(float(dl[~h2].mean()), 6); r["yari2"] = round(float(dl[h2].mean()), 6)
        n_yuk = int(yuk[m].sum())
        def alt(msk): return {"n": int(msk.sum()), "dll": round(float(dl[msk].mean()), 5) if msk.any() else None}
        A_ = {"yuklu_tarafli": alt(yuk[m]), "avrupa_kaynakli": alt(((eh + ea) > 0)[m]), "avrupa_deplasmani": alt(((th + ta) > 0)[m])}
        if pazar == "1x2":
            for nm, msk, k in (("ev_yuklu_rakip_dinlenik", (yh == 1) & (ya == 0), 0), ("dep_yuklu_rakip_dinlenik", (ya == 1) & (yh == 0), 2),
                               ("ev_avrupa_rakip_dinlenik", (eh == 1) & (ya == 0), 0), ("dep_avrupa_rakip_dinlenik", (ea == 1) & (yh == 0), 2)):
                mm = m & msk
                if mm.any(): A_[nm] = {"n": int(mm.sum()), "yuklu_kazanir_gercek": round(float((y[mm] == k).mean()), 4),
                                       "yuklu_kazanir_piyasa": round(float(P[mm, k].mean()), 4)}
        yeterli = n_yuk >= MIN_YUKLU
        alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "literatür (Scoppa 2015)"}})) if A and yeterli else 0.0
        gecti = bool(yeterli and r["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and rb["fark"] <= 0 and r["p_tek"] <= alfa)
        sonuc[pazar] = {"dll": r, "dbrier": rb, "alt_kume": A_, "n_yuklu": n_yuk, "veri_yeterli": yeterli,
                        "yarilar_siniri": s2, "alfa_t": round(alfa, 5), "kapi_gecti": gecti}
        print(pazar, json.dumps(sonuc[pazar], ensure_ascii=False))
    yeter = all(v["veri_yeterli"] for v in sonuc.values())
    karne = {"tarih": date.today().isoformat(), "madde": "YH-30", "kaynak": "data/season.json (ESPN lig + Avrupa kupaları)",
             "esik_gun": ESIK_GUN, "n_mac": len(rows), "n_yuklu_tarafli": int(yuk.sum()),
             "n_avrupa_kaynakli": int(((eh + ea) > 0).sum()), "katlar": katlar, "sonuc": sonuc,
             "karar": "gecti" if any(v["kapi_gecti"] for v in sonuc.values()) else ("reddedildi" if yeter else "veri yetersiz"),
             "not": "Taban power marj ayırma; aday piyasa olasılığına yalnız 'son ≤4 günde maç' eğimi ekler. Ulusal kupalar arşivde yok."}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and yeter and not karne["alfa_islendi"]:
        for pazar, v in sonuc.items(): O.yatirim_guncelle(A, alan_k, v["alfa_t"], v["kapi_gecti"])
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "test": len(sonuc),
                                 "gecti": {k: v["kapi_gecti"] for k, v in sonuc.items()}}
    json.dump(karne, open(os.path.join(DATA, "yuk_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", karne["karar"])


if __name__ == "__main__":
    main()
