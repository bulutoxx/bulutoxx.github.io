"""OXXai · YH-84 · Canlı olasılığın üst kuyruk (p > 0,90) kalibrasyonu laboratuvarı (ağ kullanmaz; yalnız numpy).

  python3 lab/canli_kuyruk_lab.py            ölç → data/canli_kuyruk_lab.json

SORU: Canlı güç modeli (CG, kal = null) %90 üstü dediği seçimlerde aşırı güvenli mi? (data/canli_guc.json gec.secim p90_ustu:
75+ n 124 %93,6 tuttu / ort. tahmin %98,3; 75− n 87 %92,0 / %98,0.)

ÖNCEDEN KAYITLI TASARIM (2026-11-18, ölçümden önce):
  Veri: lab/canli_altin_lab.py ile aynı — kayıtlı canlı seçimler (data/archive/live), her gün D için CG yalnız D başlamadan sonucu
  kesin maçlarla öğrenilir (gün önbelleği data/canli_altin_cg.json) ve seçim olasılığı bu modelle yeniden hesaplanır; dakika < dkmax,
  oran ≥ 1,05, gösterim tavanı 0,99. Düzeltme (ölçümden önce, yalnız kayıt SAYISI görülerek): dakika sınırı (dkmax 75) kaldırıldı —
  75. dk öncesinde yalnız 87 kuyruk kaydı vardı (< 100 eğitim şartı); gösterim her dakikada aynı eşlemeyi kullanır.
  Aday: x = logit p, x0 = logit 0,90; x > x0 ise x' = x0 + c·(x − x0) (yalnız üst kuyruk; p ≤ 0,90 değişmez, sıra değişmez,
  %80 / %85 altın ve işaret eşiklerindeki seçimler değişmez). c ızgarası 0,20 … 1,00 (0,05 adım); her sınama günü D için c yalnız
  D'den önceki günlerin kuyruk kayıtlarında log-kaybı en küçükleyen değer (≥ 100 kuyruk kaydı yoksa c = 1 → o gün sınamaya girmez).
  Sınama birimi: kuyruk kaydı (p > 0,90). Ek rapor: maç × seçim başına ilk kuyruk görünüşü.
  KAPI (SK): ΔLL = LL(aday) − LL(üretim) gün-blok bootstrap (B 2000) %95 GA üst < 0 · sınamanın iki zaman yarısında ΔLL < 0 ·
  ΔBrier ≤ 0 · tek yanlı p ≤ α = 0,0158 (yeni "canli-2026" ailesi: W0 = 0,05·0,95, sinyalli aday W/3) · ilk görünüş alt kümesinde
  de ΔLL < 0. İsabet tanım gereği değişmez (eşleme sıra koruyan).
"""
import json, math, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
OUT = os.path.join(ROOT, "data", "canli_kuyruk_lab.json")
P0 = 0.90; X0 = math.log(P0 / (1 - P0)); GRID = [round(0.20 + 0.05 * i, 2) for i in range(17)]
MIN_TR, B, ALFA = 100, 2000, 0.0158
EPS = 1e-6


def esle(p, c):
    p = np.clip(np.asarray(p, dtype=np.float64), EPS, 1 - EPS); x = np.log(p / (1 - p))
    x2 = np.where(x > X0, X0 + c * (x - X0), x); return 1 / (1 + np.exp(-x2))


def ll(p, y):
    p = np.clip(p, EPS, 1 - EPS); return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def kayitlar():
    import canli_altin_lab as LAB
    import canli_altin as CA, canli_guc_lab as L, canli_guc as CG
    # canli_altin_lab.olc() ile birebir aynı kayıt üretimi (seçim olasılığı = o gün öncesiyle öğrenilmiş CG)
    F = CA.ayar(LAB.DATA); dkmax = F["dkmax"]; h1 = CG.DEF["h1"]
    fin, snaps = L.load(); days = sorted({r["d"] for r in snaps}); R = []; OB = LAB._ob_oku()
    for D in days[1:]:
        t0 = L.day_start(D); tr = {k for k, M in fin.items() if M["ts"] + 2.5 * 3600 < t0}
        if len({r["id"] for r in snaps if r["id"] in tr}) < 30: continue
        X = L.rows_of(snaps, fin, tr, extra=True); P = LAB._cg_fit(OB, D, X, dict(CG.DEF, h1=h1), L.fit)
        for r in snaps:
            if r["d"] != D or r.get("ok") is None or not (r.get("o") and r["o"] >= 1.05): continue
            p = L.cg_pick_p(r, P)
            if p is None: continue
            R.append({"d": D, "id": r["id"], "k": r["rk"], "p": min(.99, p), "dk": r["t"], "ts": r.get("ts") or 0, "ok": int(bool(r["ok"]))})
    LAB._ob_yaz(OB, days)
    return R, dkmax


def main():
    R, dkmax = kayitlar()
    T = [r for r in R if r["p"] > P0]; days = sorted({r["d"] for r in T})
    rows, cs = [], {}
    for D in days:
        tr = [r for r in T if r["d"] < D]
        if len(tr) < MIN_TR: continue
        pt = np.array([r["p"] for r in tr]); yt = np.array([r["ok"] for r in tr], dtype=float)
        c = min(GRID, key=lambda c: (float(ll(esle(pt, c), yt).mean()), -c)); cs[D] = c
        for r in T:
            if r["d"] == D: rows.append(dict(r, c=c, q=float(esle([r["p"]], c)[0])))
    if not rows:
        json.dump({"karar": "veri_yetersiz"}, open(OUT, "w")); print("veri yetersiz"); return
    sd = sorted({r["d"] for r in rows}); di = {d: i for i, d in enumerate(sd)}
    p = np.array([r["p"] for r in rows]); q = np.array([r["q"] for r in rows]); y = np.array([r["ok"] for r in rows], dtype=float)
    g = np.array([di[r["d"]] for r in rows])
    dl = ll(q, y) - ll(p, y); db = (q - y) ** 2 - (p - y) ** 2
    G = len(sd); sum_d = np.bincount(g, dl, G); sum_b = np.bincount(g, db, G); cnt = np.bincount(g, minlength=G).astype(float)
    rng = np.random.default_rng(20261118); bs = []
    for _ in range(B):
        ix = rng.integers(0, G, G); bs.append(sum_d[ix].sum() / max(1.0, cnt[ix].sum()))
    bs = np.array(bs); ga = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]; p_tek = float((bs >= 0).mean())
    h = G // 2; m1 = g < h; m2 = ~m1
    # ilk görünüş (maç × seçim başına ilk kuyruk kaydı)
    seen, ix1 = set(), []
    for i, r in sorted(enumerate(rows), key=lambda t: (t[1]["ts"], t[1]["dk"])):
        k = (r["id"], r["k"])
        if k not in seen: seen.add(k); ix1.append(i)
    ix1 = np.array(sorted(ix1))
    def oz(m):
        return {"n": int(m.sum()), "gercek": round(float(y[m].mean()), 4), "ort_p_uretim": round(float(p[m].mean()), 4),
                "ort_p_aday": round(float(q[m].mean()), 4), "dLL": round(float(dl[m].mean()), 5), "dBrier": round(float(db[m].mean()), 5)}
    tum = np.ones(len(rows), bool); ilk = np.zeros(len(rows), bool); ilk[ix1] = True
    S = {"tum": oz(tum), "yari1": oz(m1), "yari2": oz(m2), "ilk_gorunus": oz(ilk),
         "dk75_ustu": oz(np.array([r["dk"] >= 75 for r in rows])), "dk75_alti": oz(np.array([r["dk"] < 75 for r in rows]))}
    dLL = float(dl.mean())
    k = {"ga95_ust<0": ga[1] < 0, "yarilar<0": S["yari1"]["dLL"] < 0 and S["yari2"]["dLL"] < 0, "dBrier<=0": S["tum"]["dBrier"] <= 0,
         "p<=alfa": p_tek <= ALFA, "ilk_gorunus_dLL<0": S["ilk_gorunus"]["dLL"] < 0}
    gecti = all(k.values())
    out = {"madde": "YH-84", "zaman": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
           "tasarim": {"p0": P0, "grid": [GRID[0], GRID[-1], 0.05], "min_egitim": MIN_TR, "B": B, "alfa": ALFA, "dkmax": dkmax,
                       "birim": "kuyruk kaydı (p > 0,90), gün-blok bootstrap"},
           "kayit": len(R), "kuyruk_kayit": len(T), "sinama_gunleri": [sd[0], sd[-1], G], "c_gun": cs,
           "dLL": round(dLL, 5), "ga95": [round(ga[0], 5), round(ga[1], 5)], "p_tek": round(p_tek, 4), "ozet": S,
           "kapi": k, "gecti": gecti, "karar": "gecti" if gecti else "reddedildi"}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
