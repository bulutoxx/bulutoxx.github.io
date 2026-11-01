#!/usr/bin/env python3
"""🏁 YH-31 laboratuvarı: Venn–Abers kalibrasyonu (kilitli iddaa arşivi, sunulan öneri olasılığı) — zaman sıralı sınama.

Soru: Uygulamanın gösterdiği öneri olasılığı (kilitli `sp`, sonuç `sok`; recOf / collector.served_pick: MS 1/X/2 ve 2,5 Ü/A içinden
en yüksek) üstüne ikili Venn–Abers (IVAP; Vovk & Petej 2014) kalibrasyonu log-kaybı düşürüyor mu?
  IVAP: test olasılığı s için kalibrasyon kümesine (s, 0) ve (s, 1) eklenerek iki izotonik regresyon kurulur → p0, p1;
  tek sayı p = p1 / (1 − p0 + p1).
Önceden kayıtlı tasarım:
  • Veri: data/archive (+ eski/) kilitli kayıtları; sonucu işlenmiş ve `sp`/`sok` dolu. İkincil (bilgi): model önerisi `rp`/`ok`.
  • Yürüyen pencere (gün sıralı, genişleyen): her sınama günü yalnız ÖNCEKİ günlerin satırlarıyla kalibre edilir
    (aynı gün içi sızıntı yok). İlk sınama günü: önceki satır ≥ MIN_EGITIM.
  • Taban (üretim) = kimlik (sunulan olasılık aynen).
Kapı (SK + ml90): arşiv ≥ 14 gün ve sınama ≥ 7 gün (yoksa "veri bekliyor", gölgede) · ΔLL gün-blok bootstrap B = 2000 %95 GA üst < 0
  (lig×gün blok da < 0) · iki zaman yarısında ΔLL < 0 · ΔBrier ≤ 0 · Altın isabeti düşmüyor · tek yanlı p ≤ α_t (alfa yatırımı
  fb_model-<yıl>, yalnız veri yeterliyken harcanır).

  python3 lab/venn_abers_lab.py      → data/venn_abers_lab.json (yalnız toplu ölçüm; takım adı / ham veri yok)
"""
import json, os, sys
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))  # scripts/arsiv.py, lab/arsiv.py'den önce

B_BOOT = 2000
MIN_GUN, MIN_SINAMA_GUN, MIN_EGITIM = 14, 7, 400
BANTLAR = ((.5, .6), (.6, .7), (.7, .78), (.78, .85), (.85, 1.01))
RNG = np.random.default_rng(31)


# ---------------------------------------------------------------- izotonik (PAV) ve IVAP
def pav(y, w):
    """Ağırlıklı havuzlu bitişik ihlal (artan). y, w: sıralı x'e göre. Dönüş: uydurulmuş değerler."""
    v, ww, ln = [], [], []
    for yi, wi in zip(y, w):
        v.append(yi); ww.append(wi); ln.append(1)
        while len(v) > 1 and v[-2] > v[-1]:
            W = ww[-2] + ww[-1]; v[-2] = (v[-2] * ww[-2] + v[-1] * ww[-1]) / W; ww[-2] = W; ln[-2] += ln[-1]
            v.pop(); ww.pop(); ln.pop()
    return np.repeat(v, ln)


def ivap(s_cal, y_cal, s_test):
    """Inductive Venn–Abers: her farklı test değeri için (s,0) ve (s,1) eklenmiş izotonik uydurma. Dönüş p, p0, p1."""
    xs, inv = np.unique(np.round(s_cal, 4), return_inverse=True)
    cnt = np.bincount(inv).astype(float); pos = np.bincount(inv, y_cal.astype(float))
    st = np.round(s_test, 4); out = {}
    for s in np.unique(st):
        k = np.searchsorted(xs, s); var = k < len(xs) and xs[k] == s
        r = []
        for lab in (0.0, 1.0):
            if var:
                c = cnt.copy(); p_ = pos.copy(); c[k] += 1; p_[k] += lab; x = xs
            else:
                x = np.insert(xs, k, s); c = np.insert(cnt, k, 1.0); p_ = np.insert(pos, k, lab)
            f = pav(p_ / c, c); r.append(float(f[k]))
        p0, p1 = r; out[s] = (p1 / (1 - p0 + p1), p0, p1)
    P = np.array([out[s][0] for s in st]); P0 = np.array([out[s][1] for s in st]); P1 = np.array([out[s][2] for s in st])
    return P, P0, P1


# ---------------------------------------------------------------- veri
def satirlar(pk="sp", ok="sok", key="sk"):
    import arsiv
    R = []
    for d, r in arsiv.kayitlar(DATA, puanli=True):
        if r.get(pk) is None or r.get(ok) is None: continue
        k = r.get(key); od = None
        if k in ("1", "X", "2") and r.get("ms"): od = r["ms"]["1X2".index(k)]
        elif k in ("U", "A") and r.get("ou"): od = r["ou"][0 if k == "U" else 1]
        R.append((d, r.get("ts") or 0, r.get("c") or "?", float(r[pk]), float(bool(r[ok])), od or 0.0))
    R.sort(key=lambda x: (x[0], x[1]))
    return R


def ll(p, y): p = np.clip(p, 1e-4, 1 - 1e-4); return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def boot(delta, blok):
    u, inv = np.unique(blok, return_inverse=True)
    s = np.bincount(inv, delta, len(u)); n = np.bincount(inv, None, len(u))
    idx = RNG.integers(0, len(u), (B_BOOT, len(u))); bs = s[idx].sum(1) / n[idx].sum(1)
    return {"fark": round(float(delta.mean()), 6), "ga95": [round(float(np.quantile(bs, .025)), 6), round(float(np.quantile(bs, .975)), 6)],
            "p_tek": round(float((bs >= 0).mean()), 4), "n": int(len(delta)), "blok": int(len(u))}


def altin(day, p, od, cap=3):
    by = {}
    for i in range(len(p)):
        if p[i] >= .78 and 1.15 <= od[i] <= 2.0: by.setdefault(day[i], []).append(i)
    return [i for L in by.values() for i in sorted(L, key=lambda i: -p[i])[:cap]]


def bantlar(p, y):
    out = []
    for a, b in BANTLAR:
        m = (p >= a) & (p < b)
        if m.any(): out.append({"bant": f"{a:.2f}-{min(b, 1):.2f}", "n": int(m.sum()), "tahmin": round(float(p[m].mean()), 4), "gercek": round(float(y[m].mean()), 4)})
    return out


def degerlendir(R):
    d = np.array([r[0] for r in R]); lg = np.array([r[2] for r in R]); s = np.array([r[3] for r in R]); y = np.array([r[4] for r in R])
    od = np.array([r[5] for r in R]); gunler = sorted(set(d))
    q = np.full(len(R), np.nan); wid = np.full(len(R), np.nan); katlar = []
    for g in gunler:
        tr = d < g; te = d == g
        if tr.sum() < MIN_EGITIM: continue
        P, P0, P1 = ivap(s[tr], y[tr], s[te]); q[te] = P; wid[te] = P1 - P0
        katlar.append({"gun": g, "egitim_n": int(tr.sum()), "sinama_n": int(te.sum()),
                       "dll": round(float((ll(P, y[te]) - ll(s[te], y[te])).mean()), 5)})
    m = ~np.isnan(q); sg = sorted(set(d[m]))
    res = {"n": int(len(R)), "gun": len(gunler), "ilk": gunler[0] if gunler else None, "son": gunler[-1] if gunler else None,
           "n_sinama": int(m.sum()), "gun_sinama": len(sg), "katlar": katlar}
    if not m.any(): return res
    dl = (ll(q, y) - ll(s, y))[m]; db = ((q - y) ** 2 - (s - y) ** 2)[m]; dm = d[m]
    yari = sg[len(sg) // 2] if len(sg) > 1 else sg[0]; h2 = dm >= yari
    g0 = altin(dm, s[m], od[m]); g1 = altin(dm, q[m], od[m]); ym = y[m]
    res.update({"dll_gun": boot(dl, dm), "dll_lig_gun": boot(dl, np.char.add(np.char.add(lg[m], "|"), dm)), "dbrier": boot(db, dm),
                "yari_siniri": yari, "yari1": round(float(dl[~h2].mean()), 6) if (~h2).any() else None, "yari2": round(float(dl[h2].mean()), 6),
                "ll_once": round(float(ll(s, y)[m].mean()), 5), "ll_sonra": round(float(ll(q, y)[m].mean()), 5),
                "aralik_genisligi_ort": round(float(np.nanmean(wid[m])), 4),
                "altin_once": {"n": len(g0), "isabet": round(float(ym[g0].mean()), 4) if g0 else None, "tahmin": round(float(s[m][g0].mean()), 4) if g0 else None},
                "altin_sonra": {"n": len(g1), "isabet": round(float(ym[g1].mean()), 4) if g1 else None, "tahmin": round(float(q[m][g1].mean()), 4) if g1 else None},
                "bantlar_once": bantlar(s[m], ym), "bantlar_sonra": bantlar(q[m], ym),
                "orneklem_ici_bantlar": bantlar(s, y)})
    return res


def main():
    try: onceki = json.load(open(os.path.join(DATA, "venn_abers_lab.json"), encoding="utf-8"))
    except Exception: onceki = {}
    S = degerlendir(satirlar("sp", "sok", "sk"))
    M = degerlendir(satirlar("rp", "ok", "rk"))
    yeterli = S.get("gun", 0) >= MIN_GUN and S.get("gun_sinama", 0) >= MIN_SINAMA_GUN
    A, alan_k, alfa = {}, f"fb_model-{date.today().year}", 0.0
    yol_fb = os.path.join(DATA, "fb_guc.json")
    if yeterli:
        import oxx_ogren as O
        try: A = json.load(open(yol_fb, encoding="utf-8"))
        except Exception: A = {}
        alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "literatür (Vovk & Petej 2014)"}})) if A else 0.0
    gecti = False
    if yeterli and "dll_gun" in S:
        a1, a0 = S["altin_sonra"], S["altin_once"]
        altin_ok = a1["isabet"] is None or a0["isabet"] is None or a1["isabet"] >= a0["isabet"]
        gecti = bool(S["dll_gun"]["ga95"][1] < 0 and S["dll_lig_gun"]["ga95"][1] < 0 and (S["yari1"] or 0) < 0 and S["yari2"] < 0
                     and S["dbrier"]["fark"] <= 0 and altin_ok and S["dll_gun"]["p_tek"] <= alfa)
    karar = "gecti" if gecti else ("reddedildi" if yeterli else "veri bekliyor")
    karne = {"tarih": date.today().isoformat(), "madde": "YH-31", "kaynak": "kilitli arşiv (data/archive; sunulan öneri sp/sok)",
             "kapi": {"min_gun": MIN_GUN, "min_sinama_gun": MIN_SINAMA_GUN, "min_egitim": MIN_EGITIM, "B": B_BOOT},
             "sunulan": S, "model_onerisi_bilgi": M, "veri_yeterli": yeterli, "alfa_t": round(alfa, 5), "karar": karar,
             "kabul": gecti, "not": "Taban kimlik (sunulan olasılık). Aday IVAP; yalnız önceki günlerle. Üretim bu dosyanın kabul bayrağı olmadan değişmez."}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and yeterli and not karne["alfa_islendi"]:
        import oxx_ogren as O
        O.yatirim_guncelle(A, alan_k, alfa, gecti)
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "test": 1, "gecti": gecti}
    json.dump(karne, open(os.path.join(DATA, "venn_abers_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    oz = {k: S.get(k) for k in ("n", "gun", "n_sinama", "gun_sinama", "dll_gun", "dll_lig_gun", "yari1", "yari2", "dbrier", "altin_once", "altin_sonra")}
    print(json.dumps(oz, ensure_ascii=False)); print("karar:", karar)


if __name__ == "__main__":
    main()
