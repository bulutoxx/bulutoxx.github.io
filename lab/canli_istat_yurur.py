"""OXXai YH-103 · Canlı istatistik ayarı κ'nın yürüyen pencereyle (zaman sıralı, sızıntısız) sınanması.

Her sınama günü κ yalnız önceki günlerin sonuçlu kayıtlarıyla seçilir (birleşik MS + kalan gol log kaybı);
üretimdeki κ (data/canli_istat.json kabul yoksa varsayılan 0,5) ile karşılaştırılır. Kapı lab/YOL_HARITASI.md YH-103'te
ölçümden önce kaydedildi. --uygula: kapı geçerse data/canli_istat.json'a tüm veriyle seçilen κ + kabul yazılır.
Kullanım: python3 lab/canli_istat_yurur.py [--uygula]
"""
import json, math, os, random, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import canli_istat as CI
from canli_istat_lab import load, GRID

ILK_GUN, MIN_N, MIN_M, B, MAX_GOL = 5, 1000, 150, 2000, 0.0005


def kayip(r, k, C):
    F = {x: r["f"].get(x) for x in ("ds", "dh", "dp", "w", "wt", "tl")}
    if F["w"] is None or F["wt"] is None: return None
    F["tl"] = F["tl"] or 0.0
    mH, mA = CI.mult(F, C, k)
    P = CI.probs(r["L0"][0] * mH, r["L0"][1] * mA, r["hs"], r["as"])
    fh, fa = r["fh"], r["fa"]; y = "H" if fh > fa else "A" if fh < fa else "D"
    more = (fh + fa) > (r["hs"] + r["as"])
    br = sum((P[c] - (1.0 if c == y else 0.0)) ** 2 for c in ("H", "D", "A"))
    return -math.log(max(1e-6, P[y])), -math.log(max(1e-6, P["r05"] if more else 1 - P["r05"])), br


def main(argv):
    C = CI.coef(os.path.join(ROOT, "data")); uretim = C["kappa"]
    R = load(os.path.join(ROOT, "data", "archive", "live_stats"))
    # her kayıt × κ için kayıplar (bir kez)
    T = []
    for r in R:
        v = {k: kayip(r, k, C) for k in GRID}
        if all(v.values()): T.append((r["_d"], r["id"], v))
    gunler = sorted({t[0] for t in T})
    sec = {}; S = []
    for i, d in enumerate(gunler):
        if i < ILK_GUN: continue
        egit = [t for t in T if t[0] < d]
        k = min(GRID, key=lambda g: sum(t[2][g][0] + t[2][g][1] for t in egit))
        sec[d] = k
        for t in T:
            if t[0] == d:
                a, u = t[2][k], t[2][uretim]
                S.append({"d": d, "id": t[1], "dll": (a[0] + a[1]) - (u[0] + u[1]), "dms": a[0] - u[0], "dgol": a[1] - u[1], "dbr": a[2] - u[2]})
    n = len(S); maclar = sorted({s["id"] for s in S})
    ort = lambda xs: sum(xs) / len(xs) if xs else 0.0
    dll = ort([s["dll"] for s in S])
    yarim = sorted({s["d"] for s in S}); orta = yarim[len(yarim) // 2] if yarim else None
    y1 = ort([s["dll"] for s in S if s["d"] < orta]); y2 = ort([s["dll"] for s in S if s["d"] >= orta])
    per = {}
    for s in S: p = per.setdefault(s["id"], [0.0, 0]); p[0] += s["dll"]; p[1] += 1
    rnd = random.Random(103); bs = []
    for _ in range(B):
        sm = [rnd.choice(maclar) for _ in maclar]
        bs.append(sum(per[m][0] for m in sm) / sum(per[m][1] for m in sm))
    bs.sort(); ga = [bs[int(.025 * B)], bs[int(.975 * B) - 1]]
    tum = min(GRID, key=lambda g: sum(t[2][g][0] + t[2][g][1] for t in T))
    son5 = [sec[d] for d in yarim[-5:]]
    dbr, dgol, dms = ort([s["dbr"] for s in S]), ort([s["dgol"] for s in S]), ort([s["dms"] for s in S])
    k1 = n >= MIN_N and len(maclar) >= MIN_M; k2 = ga[1] < 0; k3 = y1 < 0 and y2 < 0; k4 = dbr <= 0 and dgol <= MAX_GOL
    k5 = all(k == tum for k in son5)
    gecti = k1 and k2 and k3 and k4 and k5 and tum != uretim
    rep = {"madde": "YH-103", "zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "uretim_kappa": uretim,
           "kayit": len(T), "gun": len(gunler), "ilk_gun": gunler[0] if gunler else None, "son_gun": gunler[-1] if gunler else None,
           "sinama": {"kayit": n, "mac": len(maclar), "gun": len(yarim), "dLL": round(dll, 5), "GA95": [round(x, 5) for x in ga],
                      "yarilar": [round(y1, 5), round(y2, 5)], "dLL_ms": round(dms, 5), "dLL_gol": round(dgol, 5), "dBrier_ms": round(dbr, 5)},
           "secilen_gunluk": sec, "tum_veri_kappa": tum, "kosullar": {"1_n": k1, "2_GA": k2, "3_yarilar": k3, "4_brier_gol": k4, "5_kararlilik": k5},
           "gecti": bool(gecti), "karar": "kapıdan geçti" if gecti else "kapıdan geçmedi — üretim değişmez",
           "not": "Taban L0 eski skor/zaman modelinden (CG değil); çarpan uygulamada CG tabanına da aynı biçimde uygulanır."}
    if gecti and "--uygula" in argv:
        p = os.path.join(ROOT, "data", "canli_istat.json"); j = json.load(open(p, encoding="utf-8"))
        j.update({"kappa": tum, "kabul": True, "kaynak": "YH-103", "tarih": rep["zaman"], "onceki_kappa": uretim,
                  "dogrulama": rep["sinama"], "kanit": "data/canli_istat_yurur.json",
                  "geri_alma": "kabul false (uygulama ve toplayıcı varsayılan κ 0,5'e döner)"})
        json.dump(j, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1); rep["yazildi"] = "data/canli_istat.json"
    json.dump(rep, open(os.path.join(ROOT, "data", "canli_istat_yurur.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "secilen_gunluk"}, ensure_ascii=False, indent=1))
    return rep


if __name__ == "__main__":
    main(sys.argv[1:])
