"""🧮 YH-88 · 3,5 A/Ü ve 2. yarı 1X2'ye iddaa oranının katılması — YENİ, önceden kayıtlı, yalnız görülmemiş maçlarla sınama.
Üretimi değiştirmez.

Neden: YH-57'de (aynı aday) U35 ve 2Y yön olarak tutarlı olumluydu (2026-11-20 son ölçüm: U35 ΔLL −0,0102, 2Y −0,0040) ama o maddenin
"her sınama gününde Δ < 0" ölçütü 12 günde karşılanamadı → reddedildi. O veriler görüldüğü için yeniden kullanılamaz; bu madde yalnız
kayıt tarihinden SONRA başlayan maçlarla sınanır.

ÖNCEDEN KAYITLI TASARIM (2026-11-20 02:40 UTC; 2026-11-21 ve sonrası maçlar görülmeden yazıldı, değiştirilmez):
  Veri / taban / aday: lab/pazar_piyasa_lab.py ile birebir (başlamadan önceki son fixtures görüntüsü, sunulan pz, iddaa po oransal payı;
            ikili p' = σ(w·logit q + (1 − w)·logit p), üçlü p' ∝ q^w·p^(1 − w), w ∈ {0,0 … 1,0}).
  Gruplar : U35 (3,5 Alt / Üst), 2Y (2. yarı 1 / X / 2). Yalnız bu ikisi.
  Seçim   : her sınama günü w yalnız ÖNCEKİ günlerin maçlarıyla (2026-11-04'ten beri, ≥ 300 maç).
  Sınama  : yalnız başlama günü ≥ 2026-11-21 olan maçlar.
  KAPI (grup başına, hepsi gerekli): (1) sınamada n ≥ 500; (2) ΔLL lig×gün blok bootstrap (B 4000) iki yanlı GA, Bonferroni 1 − 0,05/2,
            üst sınır < 0; (3) sınama tarih sırasıyla iki yarıya bölünür, iki yarıda da ΔLL < 0; (4) ΔBrier ≤ 0; (5) en olası seçenek
            isabeti düşmez; (6) ECE (10 kova) büyümez.
  Tek ölçüm: n < 500 iken yalnız n raporlanır (metrik hesaplanmaz, gözetleme yok). Grup n ≥ 500'e ulaşınca bir kez ölçülür ve karar
            kesinleşir (geçti / reddedildi); sonradan kapı gevşetilmez. 2026-12-31'e kadar n ≥ 500 olmazsa veri yetersiz → reddedildi.
  Geçerse: yalnız o grup için pazar motorunda w (son tüm veri seçimi) bayrakla açılır; ayrı madde güncellemesi ve 14 gün izleme.
Çıktı: data/u35_2y_piyasa_lab.json
"""
import json, os, sys
from datetime import datetime, timezone
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pazar_piyasa_lab as M  # noqa: E402

GRUPLAR = {"U35": M.GRUPLAR["U35"], "2Y": M.GRUPLAR["2Y"]}
SINAMA_BAS, MIN_SINAMA, SON_GUN = "2026-11-21", 500, "2026-12-31"
ALFA = 0.05 / len(GRUPLAR)
CIKTI = os.path.join(M.DATA, "u35_2y_piyasa_lab.json")


def satirlar(kodlar, S, A):
    rows = []
    for iid, f in S.items():
        if iid not in A: continue
        po = f["po"]
        if not all(isinstance(po.get(c), (int, float)) and po[c] > 1 for c in kodlar): continue
        ft, ht = A[iid]; oc = [M.PZ.outcome(c, ft, ht) for c in kodlar]
        if any(o is None for o in oc) or sum(oc) != 1: continue
        pf = M.PZ.full(f["pz"]); p = np.array([pf.get(c, np.nan) for c in kodlar], float)
        if np.isnan(p).any(): continue
        p = np.clip(p, 1e-6, 1); p = p / p.sum()
        inv = np.array([1 / po[c] for c in kodlar]); rows.append((f["d"], f["lg"], p, inv / inv.sum(), oc.index(True)))
    rows.sort(key=lambda r: r[0]); return rows


def grup(kodlar, S, A, onceki=None):
    if onceki and onceki.get("karar") in ("gecti", "reddedildi"): return onceki          # karar kesin: yeniden ölçülmez
    rows = satirlar(kodlar, S, A)
    d = np.array([r[0] for r in rows]); T = d >= SINAMA_BAS; n = int(T.sum())
    out = {"n_toplam": len(rows), "n_sinama": n}
    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if n < MIN_SINAMA:
        out["karar"] = "reddedildi" if bugun > SON_GUN else "veri_bekliyor"
        if out["karar"] == "reddedildi": out["neden"] = f"{SON_GUN} sonuna kadar n < {MIN_SINAMA}"
        return out
    lg = np.array([r[1] for r in rows]); P = np.stack([r[2] for r in rows]); Q = np.stack([r[3] for r in rows]); y = np.array([r[4] for r in rows])
    C = {w: M.aday(P, Q, w) for w in M.WS}; L = {w: M.ll(C[w], y) for w in M.WS}; L0 = M.ll(P, y)
    Pa = np.full_like(P, np.nan); sec = {}
    for g in sorted(set(d[T])):
        tr = d < g
        if tr.sum() < M.MIN_EGITIM: continue
        w = min(M.WS, key=lambda w: L[w][tr].mean()); sec[str(g)] = w; Pa[d == g] = C[w][d == g]
    T = T & ~np.isnan(Pa[:, 0]); n = int(T.sum()); out["n_sinama"] = n
    dl = M.ll(Pa[T], y[T]) - L0[T]; blok = np.array([a + "|" + b for a, b in zip(lg[T], d[T])])
    M.ALFA = ALFA; ga, nb = M.boot(dl, blok)
    h = n // 2; yari = [round(float(dl[:h].mean()), 5), round(float(dl[h:].mean()), 5)]   # satırlar tarih sıralı
    dB = float((M.brier(Pa[T], y[T]) - M.brier(P[T], y[T])).mean())
    i0 = float((P[T].argmax(1) == y[T]).mean()); ia = float((Pa[T].argmax(1) == y[T]).mean())
    e0, ea = M.ece(P[T], y[T]), M.ece(Pa[T], y[T])
    kapi = {"n_yeterli": n >= MIN_SINAMA, "ga_ust_negatif": ga[1] < 0, "iki_yari_negatif": yari[0] < 0 and yari[1] < 0,
            "brier_kotulesmedi": dB <= 0, "isabet_dusmedi": ia >= i0, "ece_buyumedi": ea <= e0}
    out.update({"olcum_tarihi": bugun, "secilen_gunluk": sec, "son_w_tum_veri": min(M.WS, key=lambda w: L[w].mean()),
                "ll_uretim": round(float(L0[T].mean()), 5), "ll_aday": round(float(M.ll(Pa[T], y[T]).mean()), 5),
                "delta_ll": round(float(dl.mean()), 5), "ga": ga, "ga_duzey": round(1 - ALFA, 4), "blok": nb, "yarilar": yari,
                "delta_brier": round(dB, 5), "isabet": {"uretim": round(i0, 4), "aday": round(ia, 4)},
                "ece": {"uretim": round(e0, 4), "aday": round(ea, 4)}, "kapi": {k: bool(v) for k, v in kapi.items()}})
    out["karar"] = "gecti" if all(kapi.values()) else "reddedildi"
    return out


def main():
    try: eski = json.load(open(CIKTI, encoding="utf-8")).get("gruplar", {})
    except Exception: eski = {}
    S = M.anlik(); A = M.sonuclar()
    R = {G: grup(k, S, A, eski.get(G)) for G, k in GRUPLAR.items()}
    out = {"v": 1, "madde": "YH-88", "tarih": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "sinama_baslangic": SINAMA_BAS,
           "tasarim": "lab/u35_2y_piyasa_lab.py başlığı (önceden kayıtlı 2026-11-20)", "gruplar": R,
           "gecen": [G for G, r in R.items() if r.get("karar") == "gecti"]}
    json.dump(out, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for G, r in R.items(): print(G, {k: v for k, v in r.items() if k != "secilen_gunluk"})


if __name__ == "__main__":
    main()
