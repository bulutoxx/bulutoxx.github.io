"""BULUTOXX v107 · Canlı istatistik ayarı değerlendiricisi (ileriye dönük sınama + kapı).

data/archive/live_stats/*.json kayıtları (toplayıcı 15 dk'da bir yazar; maç bitince fh/fa eklenir) biriktikçe
istatistik ağırlığı κ'yı zaman sıralı olarak sınar:
  • eğitim = ilk %70 gün, sınama = son %30 gün (geleceği görmeden)
  • κ ızgarası eğitimde seçilir; sınamada ayarsız (κ=0) ve mevcut κ ile log kaybı karşılaştırılır
    hedefler: maç sonucu (1/X/2) ve kalan sürede gol (0,5 Üst)
  • KAPI: sınamada ≥400 kayıt ve ≥150 farklı maç; birleşik log kaybı κ=0'a göre ≥0,001 iyi ve mevcut κ'dan kötü değil;
    hiçbir hedef 0,0005'ten fazla kötüleşmiyor; maç bazlı 300 bootstrap'ta iyileşme olasılığı ≥ %90.
Varsayılan: yalnız rapor (stdout). --uygula: kapıdan geçerse data/canli_istat.json'a yeni κ + kabul=true yazar;
geçmezse hiçbir şeyi değiştirmez. β katsayıları (literatür) sabit tutulur, yalnız genel ölçek κ öğrenilir.
Kullanım: python3 lab/canli_istat_lab.py [--uygula] [--dir data/archive/live_stats]
"""
import glob, json, math, os, random, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import canli_istat as CI

GRID = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
MIN_N, MIN_M, MIN_GAIN, MAX_LOSS, MIN_BOOT = 400, 150, 0.001, 0.0005, 0.90


def load(d):
    R = []
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        day = os.path.basename(f)[:10]
        try: log = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        for r in log.values():
            if r.get("fh") is None or not r.get("f") or not r.get("L0"): continue
            r = dict(r, _d=day); R.append(r)
    return R


def ll(r, kappa, C):
    """Bir kaydın (MS, kalan gol) log kaybı, verilen κ ile yeniden hesaplanmış olasılıktan."""
    F = {k: r["f"].get(k) for k in ("ds", "dh", "dp", "w", "wt", "tl")}
    if F["w"] is None or F["wt"] is None: return None
    F["tl"] = F["tl"] or 0.0
    mH, mA = CI.mult(F, C, kappa)
    P = CI.probs(r["L0"][0] * mH, r["L0"][1] * mA, r["hs"], r["as"])
    fh, fa = r["fh"], r["fa"]
    y = "H" if fh > fa else "A" if fh < fa else "D"
    e = 1e-6
    l_ms = -math.log(max(e, P[y]))
    more = (fh + fa) > (r["hs"] + r["as"])
    l_g = -math.log(max(e, P["r05"] if more else 1 - P["r05"]))
    return l_ms, l_g


def score(R, kappa, C):
    a = b = 0.0; n = 0; per = {}
    for r in R:
        x = ll(r, kappa, C)
        if not x: continue
        a += x[0]; b += x[1]; n += 1
        p = per.setdefault(r["id"], [0.0, 0.0, 0]); p[0] += x[0]; p[1] += x[1]; p[2] += 1
    return (a / n if n else None, b / n if n else None, n, per)


def main(argv):
    d = os.path.join(ROOT, "data", "archive", "live_stats")
    if "--dir" in argv: d = argv[argv.index("--dir") + 1]
    C = CI.coef(os.path.join(ROOT, "data")); cur = C["kappa"]
    R = load(d); days = sorted({r["_d"] for r in R})
    rep = {"zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "kayit": len(R), "gun": len(days), "mevcut_kappa": cur,
           "kapi": {"min_kayit": MIN_N, "min_mac": MIN_M, "min_kazanc": MIN_GAIN, "max_kayip": MAX_LOSS, "bootstrap": MIN_BOOT}}
    if len(days) < 3 or len(R) < 50:
        rep.update(karar="yetersiz veri", gecti=False); print(json.dumps(rep, ensure_ascii=False, indent=1)); return rep
    cut = days[max(1, int(len(days) * .7)) - 1]
    tr = [r for r in R if r["_d"] <= cut]; te = [r for r in R if r["_d"] > cut]
    tr_s = {k: score(tr, k, C) for k in GRID}
    best = min(GRID, key=lambda k: (tr_s[k][0] or 9) + (tr_s[k][1] or 9))
    s0, sb, sc = score(te, 0.0, C), score(te, best, C), score(te, cur, C)
    n, mac = sb[2], len(sb[3])
    gain = ((s0[0] or 0) + (s0[1] or 0)) - ((sb[0] or 0) + (sb[1] or 0)) if n else 0
    vs_cur = ((sc[0] or 0) + (sc[1] or 0)) - ((sb[0] or 0) + (sb[1] or 0)) if n else 0
    worst = max(((sb[0] or 0) - (s0[0] or 0)), ((sb[1] or 0) - (s0[1] or 0))) if n else 9
    # maç bazlı bootstrap (aynı maçın kayıtları birlikte)
    ids = list(sb[3]); rnd = random.Random(107); win = 0; B = 300
    for _ in range(B):
        smp = [rnd.choice(ids) for _ in ids]
        a0 = sum(s0[3][i][0] + s0[3][i][1] for i in smp); a1 = sum(sb[3][i][0] + sb[3][i][1] for i in smp)
        win += a1 < a0
    pb = win / B if ids else 0
    ok = n >= MIN_N and mac >= MIN_M and gain >= MIN_GAIN and vs_cur >= 0 and worst <= MAX_LOSS and pb >= MIN_BOOT and best > 0
    rep.update({"egitim_gun": [days[0], cut], "sinama_kayit": n, "sinama_mac": mac, "secilen_kappa": best,
                "sinama": {"ms_ll_ayarsiz": s0[0], "gol_ll_ayarsiz": s0[1], "ms_ll_ayarli": sb[0], "gol_ll_ayarli": sb[1],
                           "kazanc": round(gain, 5), "mevcuda_gore": round(vs_cur, 5), "en_kotu_hedef": round(worst, 5), "bootstrap_iyi": round(pb, 3)},
                "gecti": bool(ok), "karar": "kapıdan geçti" if ok else "kapıdan geçmedi — katsayı değişmez"})
    if ok and "--uygula" in argv:
        p = os.path.join(ROOT, "data", "canli_istat.json")
        try: j = json.load(open(p, encoding="utf-8"))
        except Exception: j = {}
        j.update({"kappa": best, "kabul": True, "kaynak": "lab", "tarih": rep["zaman"], "dogrulama": rep["sinama"], "sinama_kayit": n})
        json.dump(j, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        rep["yazildi"] = p
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return rep


if __name__ == "__main__":
    main(sys.argv[1:])
