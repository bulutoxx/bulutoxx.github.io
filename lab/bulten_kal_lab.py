"""🎯 YH-54 · Bülten (iddaa) maçlarına özgü sunulan yol kalibrasyonu (T / g / dk) — zaman sıralı laboratuvar. Üretimi değiştirmez.

Teşhis (lab/isabet_teshis.py, 2026-11-08): kilitli bülten arşivinde uygulamanın gösterdiği öneri olasılığı (sp) sistemli şişkin:
0,70–0,78 bandında söylenen %73,7 / gerçek %67,0 (n 466); ≥0,78 %85,9 / %81,3 (n 418); "Üst" %60,9 / %58,2, "Alt" %57,7 / %60,8.
ml80 ayarları (calT 1,05, gscale 1,01, dk 1,14) football-data'nın büyük liglerinde (derin arşiv, 50 bin maç) öğrenildi; bülten ise
çoğu küçük lig. YH-31 (Venn–Abers, öneri olasılığına parametresiz) reddedildi; bu madde FARKLI: tam dağılımın parametrik T/g/dk'sı,
bülten kayıtlarında yeniden seçilir (ızgara, yalnız önceki günler).

ÖNCEDEN KAYITLI TASARIM (2026-11-08, sonuçlar görülmeden yazıldı; değiştirilmez):
  Veri     : data/archive/*.json (+ eski/) — sonucu olan, 3 MS oranı > 1 olan kilitli bülten kayıtları; OU oranı varsa 2,5 de puanlanır.
  Yol      : scripts/update.py ui_market_lam (power, uygulamanın fitMarket'i) → served_probs(g) → _cal3(T, dk) — uygulamanın dist()'i.
  Üretim   : T = 1,05, g = 1,01, dk = 1,14 (model.json params).
  Aday     : her sınama günü d için (T, g, dk) ızgarası T ∈ {0,90 … 1,10; 0,025}, g ∈ {0,97 … 1,04; 0,01}, dk ∈ {1,00 … 1,20; 0,02}
             yalnız d'den ÖNCEKİ günlerde amaç = ortalama [LL_1X2 + LL_2,5] en küçük olan seçilir; en az 5 eğitim günü ve 1.500 maç.
  Ölçüt    : maç başına Δ = (LL_1X2 + LL_2,5)_aday − (…)_üretim (2,5 oranı yoksa yalnız 1X2).
  KAPI     : (1) Δ gün-blok bootstrap (B = 2000) %95 GA üst sınırı < 0; (2) sınama günlerinin iki zaman yarısında da ortalama Δ < 0;
             (3) ΔBrier (1X2 + 2,5) ≤ 0; (4) öneri isabeti (uygulama kuralı: MS 1/X/2 ve 2,5 A/Ü içinde en yüksek olasılık, ≥ 0,58)
             düşmez; (5) ≥0,70 öneri kovasının |söylenen − gerçek| farkı büyümez. Hepsi geçerse "gecti", yoksa "reddedildi".
  Bilgi    : lig grubu kırılımı (motorun lig maçı mı, yalnız bülten mi), kova tablosu önce / sonra.
Çıktı: data/bulten_kal_lab.json
"""
import glob, json, math, os, random, sys
from collections import defaultdict
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import update as U   # noqa: E402

URETIM = (1.05, 1.01, 1.14)
TS = [round(0.90 + 0.025 * i, 3) for i in range(9)]
GS = [round(0.97 + 0.01 * i, 2) for i in range(8)]
DKS = [round(1.00 + 0.02 * i, 2) for i in range(11)]
MIN_GUN, MIN_MAC, B = 5, 1500, 2000


def kayitlar():
    R = []
    for f in sorted(glob.glob(os.path.join(DATA, "archive", "*.json"))) + sorted(glob.glob(os.path.join(DATA, "archive", "eski", "*.json"))):
        g = os.path.basename(f)[:10]
        try: D = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        for k, r in (D.items() if isinstance(D, dict) else []):
            if not isinstance(r, dict) or not isinstance(r.get("hs"), int) or not isinstance(r.get("as"), int): continue
            ms = r.get("ms")
            if not (isinstance(ms, list) and len(ms) == 3 and all(isinstance(x, (int, float)) and x > 1 for x in ms)): continue
            ou = r.get("ou") if isinstance(r.get("ou"), list) and len(r["ou"]) == 2 and all(isinstance(x, (int, float)) and x > 1 for x in r["ou"]) else None
            R.append({"d": g, "k": k, "ms": ms, "ou": ou, "y": 0 if r["hs"] > r["as"] else 1 if r["hs"] == r["as"] else 2,
                      "ov": r["hs"] + r["as"] > 2, "c": r.get("c"), "h": r.get("h"), "a": r.get("a")})
    return R


def lig_grubu(R):
    """Motorun lig maçı (predlog'da aynı gün ± 1, aynı takım adı) mı? Yalnız bilgi kırılımı için; ad eşleşmesi kaba."""
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts")); from predlog_tekil import tekillestir
        log, _ = tekillestir(json.load(open(os.path.join(DATA, "predlog.json"), encoding="utf-8")))
    except Exception: log = []
    ad = lambda s: (s or "").lower().replace(" ", "")[:6]
    S = {(e["d"], ad(e["h"])) for e in log if e.get("mp")}
    for r in R: r["grup"] = "motor_ligi" if (r["d"], ad(r["h"])) in S else "yalniz_bulten"


def olasiliklar(R):
    rho, h1 = -0.06, 0.4442
    try:
        P = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"]; rho, h1 = P.get("rho", rho), P.get("h1", h1)
    except Exception: pass
    lam = U.ui_market_lam([r["ms"] for r in R], [r["ou"] for r in R], rho)
    out = {}
    for g in sorted(set(GS) | {URETIM[1]}):
        p, O = U.served_probs(lam[:, 0], lam[:, 1], g, rho, h1); out[g] = (p, O)
    return out


def metrik(R, PO, T, g, dk):
    p, O = PO[g]; q = U._cal3(p.copy(), T, dk)
    y = np.array([r["y"] for r in R]); ov = np.array([r["ov"] for r in R]); has = np.array([r["ou"] is not None for r in R])
    l1 = -np.log(np.maximum(q[np.arange(len(R)), y], 1e-9))
    l2 = np.where(has, -np.log(np.maximum(np.where(ov, O, 1 - O), 1e-9)), 0.0)
    b1 = ((q - np.eye(3)[y]) ** 2).sum(1); b2 = np.where(has, (O - ov) ** 2, 0.0)
    return q, O, l1 + l2, b1 + b2


def oneriler(R, q, O):
    """Uygulama kuralı: MS 1/X/2 (+ 2,5 A/Ü oranı varsa) içinde en yüksek olasılık. Dönüş: [(p, tuttu)]."""
    out = []
    for i, r in enumerate(R):
        c = [(q[i, 0], r["y"] == 0), (q[i, 1], r["y"] == 1), (q[i, 2], r["y"] == 2)]
        if r["ou"]: c += [(O[i], r["ov"]), (1 - O[i], not r["ov"])]
        out.append(max(c, key=lambda x: x[0]))
    return out


def kova(ps):
    K = defaultdict(list)
    for p, t in ps:
        k = "<0,58" if p < .58 else "0,58-0,70" if p < .70 else "0,70-0,78" if p < .78 else "≥0,78"; K[k].append((p, t))
    return {k: {"n": len(v), "soylenen": round(float(np.mean([p for p, _ in v])), 4), "gercek": round(float(np.mean([t for _, t in v])), 4)} for k, v in sorted(K.items())}


def main():
    R = kayitlar(); R.sort(key=lambda r: (r["d"], r["k"])); lig_grubu(R)
    gunler = sorted({r["d"] for r in R}); PO = olasiliklar(R)
    ix = defaultdict(list)
    for i, r in enumerate(R): ix[r["d"]].append(i)
    # her ızgara noktasının gün bazında toplam amacı (hızlı seçim için)
    A = {}
    y = np.array([r["y"] for r in R])
    for g in GS:
        for T in TS:
            for dk in DKS:
                _, _, L, _ = metrik(R, PO, T, g, dk)
                A[(T, g, dk)] = np.array([L[ix[d]].sum() for d in gunler])
    nd = np.array([len(ix[d]) for d in gunler])
    _, _, L0, B0 = metrik(R, PO, *URETIM); q0, O0, _, _ = metrik(R, PO, *URETIM)
    La = np.full(len(R), np.nan); Ba = np.full(len(R), np.nan); qa = np.zeros((len(R), 3)); Oa = np.zeros(len(R)); sec = {}
    for j, d in enumerate(gunler):
        if j < MIN_GUN or nd[:j].sum() < MIN_MAC: continue
        best = min(A, key=lambda k: A[k][:j].sum() / nd[:j].sum())
        sec[d] = best
        q, O, L, Bq = metrik(R, PO, *best); I = ix[d]
        La[I] = L[I]; Ba[I] = Bq[I]; qa[I] = q[I]; Oa[I] = O[I]
    test = [i for i in range(len(R)) if not np.isnan(La[i])]
    tg = sorted({R[i]["d"] for i in test})
    D = {d: [La[i] - L0[i] for i in ix[d]] for d in tg}
    delta = float(np.mean([x for d in tg for x in D[d]]))
    rnd = random.Random(11); bs = []
    for _ in range(B):
        s = [x for _ in tg for x in D[rnd.choice(tg)]]; bs.append(np.mean(s))
    bs.sort(); ga = [float(bs[int(.025 * B)]), float(bs[int(.975 * B) - 1])]
    h = len(tg) // 2; yari = [float(np.mean([x for d in tg[:h] for x in D[d]])), float(np.mean([x for d in tg[h:] for x in D[d]]))]
    dB = float(np.mean([Ba[i] - B0[i] for i in test]))
    Rt = [R[i] for i in test]
    o0 = oneriler(Rt, q0[test], O0[test]); oa = oneriler(Rt, qa[test], Oa[test])
    is0 = [t for p, t in o0 if p >= .58]; isa = [t for p, t in oa if p >= .58]
    k0, ka = kova(o0), kova(oa)
    def sap(k, kk): return abs(k[kk]["soylenen"] - k[kk]["gercek"]) if kk in k else None
    s70_0 = [(p, t) for p, t in o0 if p >= .70]; s70_a = [(p, t) for p, t in oa if p >= .70]
    gap0 = abs(np.mean([p for p, _ in s70_0]) - np.mean([t for _, t in s70_0])) if s70_0 else 0
    gapa = abs(np.mean([p for p, _ in s70_a]) - np.mean([t for _, t in s70_a])) if s70_a else 0
    kapi = {"ga_ust_negatif": ga[1] < 0, "iki_yari_negatif": yari[0] < 0 and yari[1] < 0, "brier_kotulesmedi": dB <= 0,
            "oneri_isabeti_dusmedi": (np.mean(isa) if isa else 0) >= (np.mean(is0) if is0 else 0),
            "yuksek_kova_sapmasi_buyumedi": gapa <= gap0}
    kapi = {k: bool(v) for k, v in kapi.items()}
    grup = {}
    for gname in ("motor_ligi", "yalniz_bulten"):
        I = [i for i in test if R[i]["grup"] == gname]
        if I: grup[gname] = {"n": len(I), "delta": round(float(np.mean([La[i] - L0[i] for i in I])), 5)}
    son = sec[max(sec)] if sec else None
    out = {"v": 1, "madde": "YH-54", "tarih": gunler[-1] if gunler else None, "n_kayit": len(R), "gunler": [gunler[0], gunler[-1]] if gunler else None,
           "n_sinama": len(test), "sinama_gunleri": len(tg), "uretim": dict(zip(("T", "g", "dk"), URETIM)),
           "secilen_gunluk": {d: dict(zip(("T", "g", "dk"), v)) for d, v in sec.items()}, "son_secilen": dict(zip(("T", "g", "dk"), son)) if son else None,
           "delta_ll": round(delta, 5), "ga95": [round(x, 5) for x in ga], "yarilar": [round(x, 5) for x in yari], "delta_brier": round(dB, 5),
           "ll_uretim": round(float(np.mean([L0[i] for i in test])), 5), "ll_aday": round(float(np.mean([La[i] for i in test])), 5),
           "oneri": {"uretim": {"n": len(is0), "isabet": round(float(np.mean(is0)), 4) if is0 else None, "n_70": len(s70_0), "sapma_70": round(float(gap0), 4)},
                     "aday": {"n": len(isa), "isabet": round(float(np.mean(isa)), 4) if isa else None, "n_70": len(s70_a), "sapma_70": round(float(gapa), 4)}},
           "kova_uretim": k0, "kova_aday": ka, "grup": grup, "kapi": kapi, "karar": "gecti" if all(kapi.values()) else "reddedildi"}
    out["kabul"] = out["karar"] == "gecti"
    json.dump(out, open(os.path.join(DATA, "bulten_kal_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("n_kayit", "n_sinama", "sinama_gunleri", "son_secilen", "delta_ll", "ga95", "yarilar", "delta_brier", "oneri", "grup", "kapi", "karar")}, ensure_ascii=False, indent=1))
    print(json.dumps({"uretim": k0, "aday": ka}, ensure_ascii=False))


if __name__ == "__main__":
    main()
