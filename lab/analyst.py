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

def factors(recs):
    by = collections.defaultdict(list)
    for r in recs: by[r.get("c") or "?"].append(r)
    out = {}
    for c, rs in by.items():
        n = len(rs); act = sum(r["ok"] for r in rs) / n; exp = sum(r["rp"] for r in rs) / n
        k = (n * (act / max(exp, 1e-6)) + SHRINK) / (n + SHRINK)          # az veride 1'e çekilir
        out[c] = {"n": n, "gercek": round(act, 4), "beklenen": round(exp, 4), "k": round(min(max(k, 0.7), 1.25), 4)}
    return out

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
    if len(recs) < 1500:
        out["aciklama"] = f"Arşivde {len(recs)} puanlanmış öneri var; lig katsayıları için en az 1.500 gerekli. Veri birikiyor."
    else:
        recs.sort(key=lambda r: r["_d"]); mid = recs[len(recs) // 2]["_d"]
        tr = [r for r in recs if r["_d"] < mid]; te = [r for r in recs if r["_d"] >= mid]
        F_tr = factors(tr); b0, b1 = brier(te, F_tr)
        out["dogrulama"] = {"ayrim": mid, "brier_ham": round(b0, 5), "brier_katsayili": round(b1, 5), "test_n": len(te)}
        out["kabul"] = b1 < b0 - 1e-5
        F = factors(recs)
        out["ligler"] = {c: v for c, v in F.items() if v["n"] >= MIN_N} if out["kabul"] else {}
        zayif = sorted([(c, v) for c, v in F.items() if v["n"] >= MIN_N], key=lambda x: x[1]["gercek"] - x[1]["beklenen"])[:5]
        out["zayif_ligler"] = [{"lig": c, **v} for c, v in zayif]
        out["aciklama"] = (f"Lig güven katsayıları ikinci yarıda tahmini iyileştirdi (Brier {b0:.4f} → {b1:.4f}); uygulanıyor." if out["kabul"]
                           else f"Lig katsayıları ikinci yarıda tahmini iyileştirmedi (Brier {b0:.4f} → {b1:.4f}); uygulanmıyor.")
    json.dump(out, open(os.path.join(ROOT, "data", "analyst.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out["aciklama"])

if __name__ == "__main__":
    main()
