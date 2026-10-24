"""📊 Analist botu (her gün, GitHub Actions).
Kilitli öneri arşivinden (data/archive) lig ve pazar bazında gerçek isabeti ölçer.
Bir ligde öneriler beklenenden sistemli olarak kötü/iyi tutuyorsa o lig için 'güven katsayısı' öğrenir.
Katsayılar arşivin ilk yarısında öğrenilip ikinci yarısında sınanır; tahmini iyileştirmiyorsa uygulanmaz.
Çıktı: data/analyst.json (uygulama okur; öneri yüzdeleri ve Power Now buna göre düzeltilir)."""
import json, os, glob, collections, math
from datetime import date
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARC = os.path.join(ROOT, "data", "archive")
MIN_N, SHRINK = 60, 80
YONTEM = "eb"   # "eb": ampirik Bayes logit küçültme (2026-10-25'ten beri), "carpim": eski çarpımsal k

def factors(recs):
    by = collections.defaultdict(list)
    for r in recs: by[r.get("c") or "?"].append(r)
    out = {}
    for c, rs in by.items():
        n = len(rs); act = sum(r["ok"] for r in rs) / n; exp = sum(r["rp"] for r in rs) / n
        k = (n * (act / max(exp, 1e-6)) + SHRINK) / (n + SHRINK)          # az veride 1'e çekilir
        out[c] = {"n": n, "gercek": round(act, 4), "beklenen": round(exp, 4), "k": round(min(max(k, 0.7), 1.25), 4)}
    return out

def factors_eb(recs):
    """Ampirik Bayes lig katsayısı (2026-10-25): lig sapması logit ölçeğinde ölçülür, ligler arası GERÇEK sapma varyansı (tau²)
    DerSimonian-Laird ile veriden tahmin edilir ve her lig ona göre küçültülür. Ligler arası fark gürültüden ibaretse tau²→0 ve
    tüm katsayılar 1'e iner (zarar vermez). Sınama (season.json, 2025→2026 ve yürüyen ay): eski çarpımsal yöntem Brier'i
    kötüleştiriyordu (0,23580→0,23621), bu yöntem ham ile aynı kalıyor. Çıktı biçimi factors() ile aynı ('k' alanı uygulamaya gider)."""
    by = collections.defaultdict(list)
    for r in recs: by[r.get("c") or "?"].append(r)
    st = {}
    for c, rs in by.items():
        res = sum(r["ok"] - r["rp"] for r in rs); v = sum(r["rp"] * (1 - r["rp"]) for r in rs)
        st[c] = (len(rs), res, max(v, 1e-6), sum(r["ok"] for r in rs) / len(rs), sum(r["rp"] for r in rs) / len(rs))
    ok_ = [(res / v, v) for n, res, v, _, _ in st.values() if v >= 2]
    tau2 = 0.0
    if len(ok_) >= 3:
        W = sum(w for _, w in ok_); dbar = sum(d * w for d, w in ok_) / W
        Q = sum(w * (d - dbar) ** 2 for d, w in ok_); C = W - sum(w * w for _, w in ok_) / W
        tau2 = max(0.0, (Q - (len(ok_) - 1)) / C) if C > 0 else 0.0
    out = {}
    for c, (n, res, v, act, exp) in st.items():
        d = res / (v + 1 / tau2) if tau2 > 0 else 0.0
        e = min(max(exp, 1e-4), 1 - 1e-4); pe = 1 / (1 + math.exp(-(math.log(e / (1 - e)) + d)))
        out[c] = {"n": n, "gercek": round(act, 4), "beklenen": round(exp, 4), "k": round(min(max(pe / e, 0.7), 1.25), 4), "kaydirma": round(d, 4)}
    global LAST_TAU
    LAST_TAU = round(math.sqrt(tau2), 4)
    return out
LAST_TAU = None

def brier(recs, F):
    def adj(r):
        f = F.get(r.get("c") or "?")
        return min(max(r["rp"] * (f["k"] if f and f["n"] >= MIN_N else 1), 0.02), 0.98)
    return (sum((r["rp"] - r["ok"]) ** 2 for r in recs) / len(recs), sum((adj(r) - r["ok"]) ** 2 for r in recs) / len(recs))

def main():
    recs = []
    for f in sorted(glob.glob(os.path.join(ARC, "*.json"))):
        d = os.path.basename(f)[:10]
        for r in json.load(open(f, encoding="utf-8")).values():
            if r.get("ok") is not None and r.get("rp"): recs.append(dict(r, _d=d))
    out = {"tarih": date.today().isoformat(), "n": len(recs), "ligler": {}, "pazar": {}, "kabul": False, "aciklama": ""}
    # pazar bazında isabet (MS 1/X/2, 2,5 Alt/Üst)
    pm = collections.defaultdict(list)
    for r in recs: pm[r["rk"]].append(r)
    out["pazar"] = {k: {"n": len(v), "gercek": round(sum(x["ok"] for x in v) / len(v), 4), "beklenen": round(sum(x["rp"] for x in v) / len(v), 4)} for k, v in pm.items()}
    # 🩺 teşhis (yalnız ölçüm, hiçbir şeyi değiştirmez): pazar Brier'i ve oran bandına göre sapma (ör. <1,20 ağır favorilerde aşırı güven)
    def _s(v): return {"n": len(v), "gercek": round(sum(x["ok"] for x in v) / len(v), 4), "beklenen": round(sum(x["rp"] for x in v) / len(v), 4),
                       "brier": round(sum((x["rp"] - x["ok"]) ** 2 for x in v) / len(v), 5)} if v else {"n": 0}
    bands = [("<1.20", 0, 1.2), ("1.20-1.50", 1.2, 1.5), ("1.50-2.00", 1.5, 2.0001), (">2.00", 2.0001, 99)]
    out["teshis"] = {"pazar": {k: _s(v) for k, v in pm.items()},
                     "oran_bandi": {nm: _s([r for r in recs if r.get("ro") and lo <= r["ro"] < hi]) for nm, lo, hi in bands}}
    if len(recs) < 1500:
        out["aciklama"] = f"Arşivde {len(recs)} puanlanmış öneri var; lig katsayıları için en az 1.500 gerekli. Veri birikiyor."
    else:
        recs.sort(key=lambda r: r["_d"]); mid = recs[len(recs) // 2]["_d"]
        tr = [r for r in recs if r["_d"] < mid]; te = [r for r in recs if r["_d"] >= mid]
        FACT = factors_eb if YONTEM == "eb" else factors
        F_tr = FACT(tr); b0, b1 = brier(te, F_tr); tau = LAST_TAU
        _, b_eski = brier(te, factors(tr))
        out["dogrulama"] = {"ayrim": mid, "brier_ham": round(b0, 5), "brier_katsayili": round(b1, 5), "test_n": len(te),
                            "yontem": YONTEM, "tau": tau, "brier_eski_yontem": round(b_eski, 5)}
        out["kabul"] = b1 < b0 - 1e-5
        F = FACT(recs)
        out["ligler"] = {c: v for c, v in F.items() if v["n"] >= MIN_N} if out["kabul"] else {}
        zayif = sorted([(c, v) for c, v in F.items() if v["n"] >= MIN_N], key=lambda x: x[1]["gercek"] - x[1]["beklenen"])[:5]
        out["zayif_ligler"] = [{"lig": c, **v} for c, v in zayif]
        out["aciklama"] = (f"Lig güven katsayıları ikinci yarıda tahmini iyileştirdi (Brier {b0:.4f} → {b1:.4f}); uygulanıyor." if out["kabul"]
                           else f"Lig katsayıları ikinci yarıda tahmini iyileştirmedi (Brier {b0:.4f} → {b1:.4f}); uygulanmıyor.")
    try:
        RB = json.load(open(os.path.join(ROOT, "data", "rollback.json"), encoding="utf-8"))
        if RB.get("aktif") and not RB.get("analist"): out["kabul"] = False; out["ligler"] = {}; out["aciklama"] += " (Koruyucu geri alma süresince katsayılar dondurulmuş.)"
    except Exception: pass
    json.dump(out, open(os.path.join(ROOT, "data", "analyst.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out["aciklama"])

if __name__ == "__main__":
    main()
