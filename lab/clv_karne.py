"""📈 Öneri CLV karnesi (YH-01) — kapanış çizgisi değeri. Yalnız ölçüm; hiçbir tahmini değiştirmez.

Kilit:  data/archive/GGGG-AA-GG.json kaydı (iddaa kimliği): kilitlendiği andaki oranlar ms (1X2) / ou (2,5 üst, alt) ve öneri sk (yoksa rk).
Kapanış: data/tazeveri.json aynı iddaa kimliği (iid): maç başlamadan önce son görülen oran o1 / u1 (medyan ≈ başlamadan 15 dk önce).
clv = ln(p_kapanış / p_kilit), öneri tarafı, marjı oransal ayrılmış olasılık. > 0: piyasa kilitten sonra önerinin yönüne kaydı.

Doğrulama (karneye girme koşulu): corr(clv, y − p_kilit) > 0, gün blok bootstrap %95 GA alt sınırı > 0
(kapanışa doğru kayan öneriler kilit fiyatının ima ettiğinden daha sık tutuyor mu?). Ek: kapanış piyasası kilitten daha
iyi mi? ΔLL = LL(kapanış) − LL(kilit), sonuçlu maçlarda (3 yollu 1X2 ve 2,5 alt/üst), aynı GA.
Kapanış kilidi (kapanis_kilidi bloğu): data/predlog.json mp (açılış) → mpc (maça ≤ 75 dk kala, scripts/kilit.py); model yönü argmax(p − mp).
Çıktı: data/clv.json. Kullanım: python3 lab/clv_karne.py [--kuru]
"""
import glob, json, math, os, random, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CIKTI = os.path.join(DATA, "clv.json")
B = 2000
EN_AZ_GUN = 5
EN_AZ_N = 300


def jl(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def dv(o):
    try:
        q = [1.0 / float(x) for x in o]
    except Exception:
        return None
    if any(x <= 0 for x in q): return None
    s = sum(q)
    return [x / s for x in q]


TARAF = {"1": ("ms", "o1", 0), "X": ("ms", "o1", 1), "2": ("ms", "o1", 2), "U": ("ou", "u1", 0), "A": ("ou", "u1", 1)}


def sonuc(r, e):
    if r.get("hs") is not None and r.get("as") is not None: return int(r["hs"]), int(r["as"])
    if e.get("r"): return int(e["r"][0]), int(e["r"][1])
    return None


def tuttu(k, s):
    h, a = s
    return {"1": h > a, "X": h == a, "2": h < a, "U": h + a > 2, "A": h + a < 3}[k]


def kayitlar():
    T = (jl(os.path.join(DATA, "tazeveri.json"), {}) or {}).get("mac") or {}
    byi = {str(e["iid"]): e for e in T.values() if e.get("iid")}
    R, L = [], []
    for f in sorted(glob.glob(os.path.join(DATA, "archive", "*.json")) + glob.glob(os.path.join(DATA, "archive", "eski", "*.json"))):
        gun = os.path.basename(f)[:10]
        for iid, r in (jl(f, {}) or {}).items():
            if not isinstance(r, dict): continue
            e = byi.get(str(iid))
            if not e: continue
            s = sonuc(r, e)
            # kapanış piyasası kilitten daha bilgili mi (sonuçlu her maç, öneri olsun olmasın)
            if s:
                for ka, kk, y in (("ms", "o1", 0 if s[0] > s[1] else 1 if s[0] == s[1] else 2), ("ou", "u1", 0 if sum(s) > 2 else 1)):
                    p0, p1 = dv(r.get(ka) or []), dv(e.get(kk) or [])
                    if p0 and p1 and len(p0) == len(p1):
                        L.append({"g": gun, "pz": "1x2" if ka == "ms" else "ou", "d": -math.log(max(p1[y], 1e-9)) + math.log(max(p0[y], 1e-9))})
            k = r.get("sk") or r.get("rk")
            if k not in TARAF: continue
            ka, kk, i = TARAF[k]
            p0, p1 = dv(r.get(ka) or []), dv(e.get(kk) or [])
            if not p0 or not p1 or len(p0) != len(p1): continue
            x = {"g": gun, "k": k, "lg": r.get("c", ""), "p0": p0[i], "p1": p1[i], "clv": math.log(p1[i] / p0[i])}
            if s: x["y"] = 1 if tuttu(k, s) else 0
            R.append(x)
    return R, L


def _corr(xs, ys):
    n = len(xs)
    if n < 3: return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sx = math.sqrt(sum((a - mx) ** 2 for a in xs)); sy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return sxy / (sx * sy) if sx > 0 and sy > 0 else None


def _ga(bloklar, stat, rnd):
    """Gün blok bootstrap %95 aralığı."""
    anah = list(bloklar)
    v = []
    for _ in range(B):
        sec = [x for _ in anah for x in bloklar[rnd.choice(anah)]]
        s = stat(sec)
        if s is not None: v.append(s)
    v.sort()
    if len(v) < 100: return None
    return [round(v[int(0.025 * len(v))], 4), round(v[int(0.975 * len(v)) - 1], 4)]


def hesapla(R, L, rnd=None):
    rnd = rnd or random.Random(20261028)
    out = {}
    if R:
        out["oneri"] = {"n": len(R), "ort_clv": round(sum(x["clv"] for x in R) / len(R), 4),
                        "gecti": round(sum(1 for x in R if x["clv"] > 1e-9) / len(R), 4),
                        "ayni": round(sum(1 for x in R if abs(x["clv"]) <= 1e-9) / len(R), 4)}
        pz = {}
        for x in R:
            pz.setdefault("1x2" if x["k"] in "1X2" else "ou", []).append(x)
        out["pazar"] = {k: {"n": len(v), "ort_clv": round(sum(x["clv"] for x in v) / len(v), 4),
                            "gecti": round(sum(1 for x in v if x["clv"] > 1e-9) / len(v), 4)} for k, v in sorted(pz.items())}
        gun = {}
        for x in R:
            gun.setdefault(x["g"], []).append(x)
        out["gunluk"] = [{"g": g, "n": len(v), "ort_clv": round(sum(x["clv"] for x in v) / len(v), 4),
                          "gecti": round(sum(1 for x in v if x["clv"] > 1e-9) / len(v), 4)} for g, v in sorted(gun.items())]
        out["oneri"]["ga_ort_clv"] = _ga(gun, lambda s: sum(x["clv"] for x in s) / len(s) if s else None, rnd)
    P = [x for x in R if "y" in x]
    d = {"n_sonuclu": len(P), "gun": len({x["g"] for x in P})}
    if P:
        bl = {}
        for x in P: bl.setdefault(x["g"], []).append(x)
        st = lambda s: _corr([x["clv"] for x in s], [x["y"] - x["p0"] for x in s])
        c = st(P)
        d["corr_clv_fazla"] = None if c is None else round(c, 4)
        d["ga"] = _ga(bl, st, rnd)
        art = [x for x in P if x["clv"] > 1e-9]; eks = [x for x in P if x["clv"] < -1e-9]
        for ad, s in (("clv_arti", art), ("clv_eksi", eks)):
            if s: d[ad] = {"n": len(s), "isabet": round(sum(x["y"] for x in s) / len(s), 4), "kilit_ima": round(sum(x["p0"] for x in s) / len(s), 4)}
    if L:
        bl = {}
        for x in L: bl.setdefault(x["g"], []).append(x)
        st = lambda s: sum(x["d"] for x in s) / len(s) if s else None
        d["kapanis_dLL"] = {"n": len(L), "dLL": round(st(L), 5), "ga": _ga(bl, st, rnd),
                            "aciklama": "LL(kapanış) − LL(kilit), sonuçlu maçlar; negatif = kapanış daha bilgili"}
    g = d.get("ga")
    d["kabul"] = bool(g and g[0] > 0 and d["n_sonuclu"] >= EN_AZ_N and d["gun"] >= EN_AZ_GUN)
    d["kosul"] = f"corr(clv, y − p_kilit) GA alt sınırı > 0, n ≥ {EN_AZ_N}, ≥ {EN_AZ_GUN} gün"
    out["dogrulama"] = d
    return out


def kapanis_kilidi(plog, rnd=None):
    """Kilitli tahmin günlüğünün kapanış kilidi (scripts/kilit.py alanları): mp = açılış piyasa payı, mpc = maça ≤ 75 dk kala piyasa payı
    (ikisi de marjı ayıklanmış). Model yönü k = argmax(p − mp) (modelin açılışta piyasadan ayrıldığı taraf); clv = ln(mpc[k] / mp[k]).
    Ek: sonuçlu maçlarda kapanış piyasası açılıştan daha bilgili mi (ΔLL = LL(mpc) − LL(mp)); model kapanışı (pc) − piyasa kapanışı (mpc)."""
    rnd = rnd or random.Random(20261029)
    R = []
    for e in plog:
        p, m0, m1 = e.get("p"), e.get("mp"), e.get("mpc")
        if not all(isinstance(x, list) and len(x) == 3 for x in (p, m0, m1)) or min(m0) <= 0 or min(m1) <= 0: continue
        k = max(range(3), key=lambda i: p[i] - m0[i])
        x = {"g": e.get("d", ""), "clv": math.log(m1[k] / m0[k]), "fark": p[k] - m0[k]}
        r = e.get("r")
        if isinstance(r, list) and len(r) == 2:
            y = 0 if r[0] > r[1] else 1 if r[0] == r[1] else 2
            x["dLL"] = -math.log(max(m1[y], 1e-9)) + math.log(max(m0[y], 1e-9))
            if isinstance(e.get("pc"), list) and len(e["pc"]) == 3: x["mkLL"] = -math.log(max(e["pc"][y], 1e-9)) + math.log(max(m1[y], 1e-9))
        R.append(x)
    out = {"n": len(R), "kaynak": "data/predlog.json (mp → mpc)"}
    if not R: return out
    bl = {}
    for x in R: bl.setdefault(x["g"], []).append(x)
    out.update(ort_clv=round(sum(x["clv"] for x in R) / len(R), 4), gecti=round(sum(1 for x in R if x["clv"] > 1e-9) / len(R), 4),
               ga_ort_clv=_ga(bl, lambda s: sum(x["clv"] for x in s) / len(s) if s else None, rnd),
               corr_fark_clv=(lambda c: None if c is None else round(c, 4))(_corr([x["fark"] for x in R], [x["clv"] for x in R])))
    S = [x for x in R if "dLL" in x]
    if S: out["kapanis_dLL"] = {"n": len(S), "dLL": round(sum(x["dLL"] for x in S) / len(S), 5)}
    M = [x for x in R if "mkLL" in x]
    if M: out["model_eksi_piyasa_kapanis_LL"] = {"n": len(M), "dLL": round(sum(x["mkLL"] for x in M) / len(M), 5)}
    return out


def main():
    R, L = kayitlar()
    out = hesapla(R, L)
    try: out["kapanis_kilidi"] = kapanis_kilidi(jl(os.path.join(DATA, "predlog.json"), []) or [])
    except Exception as e: print("kapanış kilidi CLV atlandı:", e)
    out["guncelleme"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    out["aciklama"] = ("Öneri CLV karnesi (lab/clv_karne.py, YH-01): clv = ln(p_kapanış / p_kilit), öneri tarafı, marjı ayrılmış piyasa; "
                       "kilit = arşivdeki kilitli oran, kapanış = başlamadan önce son görülen oran (tazeveri o1/u1). Yalnız ölçüm.")
    print(json.dumps({k: out[k] for k in ("oneri", "pazar", "dogrulama", "kapanis_kilidi") if k in out}, ensure_ascii=False, indent=1))
    if "--kuru" not in sys.argv:
        with open(CIKTI, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:   # hata sistemi durdurmaz
        print("clv_karne hata:", e)
        sys.exit(0)
