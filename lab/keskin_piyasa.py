"""🎯 YH-02 · Keskin piyasa önceliği laboratuvarı (yalnız ölçüm; hiçbir tahmini değiştirmez).

Soru: piyasa yolunda girdi/öğrenme hedefi olarak ortalama oran (Avg, üretim) yerine Pinnacle (PS) ya da ikisinin
log-uzlaşısı daha iyi kalibre olasılık verir mi?
Veri: football-data.co.uk (motorun zaten kullandığı ücretsiz kaynak; atıf), ana ligler son 5 bitmiş sezon + süren sezon.
  - "on" (maç öncesi): AvgH/D/A (üretim) · PSH/D/A · uzlaşı p ∝ Avg^(1−w)·PS^w — 1X2 ve 2,5 alt/üst (Avg>2.5 · P>2.5).
  - "kapanis": AvgCH (üretim; yeni ligler kapanışla öğrenir) · PSCH · uzlaşı.
Yöntem: power marj ayırma (üretimle aynı) → sıcaklık T (p^T, yeniden normalize). Yıllık yürüyen pencere: sınama sezonu s için
T ve w yalnız s'den önceki sezonlarda seçilir; s'de sınanır. Tüm adaylar aynı maç kümesinde (her iki oran da var).
Kapı (SK): ΔLL = LL(aday) − LL(Avg); lig×gün blok bootstrap (B=2000) %95 GA üst < 0 · iki zaman yarısında ΔLL < 0 ·
ΔBrier ≤ 0 · isabet düşmüyor · tek yanlı p ≤ 0,05 · katların çoğunda ΔLL < 0.
Çıktı: data/keskin_piyasa.json (yalnız toplu metrik; ham veri yazılmaz). Kullanım: python3 lab/keskin_piyasa.py [--sezon 5]
"""
import csv, io, json, math, os, random, sys, time, collections
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
CIKTI = os.path.join(DATA, "keskin_piyasa.json")
B = 2000
TS = [round(0.80 + 0.02 * i, 2) for i in range(21)]          # 0,80 … 1,20
WS = [round(0.1 * i, 1) for i in range(11)]                    # 0 … 1
EPS = 1e-12


def fnum(x):
    try:
        v = float(x); return v if v > 1.0 else None
    except (TypeError, ValueError):
        return None


def power_devig(o):
    q = [1.0 / x for x in o]
    lo, hi = 0.5, 5.0
    for _ in range(60):
        k = (lo + hi) / 2
        s = sum(x ** k for x in q)
        if s > 1: lo = k
        else: hi = k
    p = [x ** k for x in q]; s = sum(p)
    return [x / s for x in p]


def temp(p, T):
    r = [max(x, EPS) ** T for x in p]; s = sum(r)
    return [x / s for x in r]


def pool(a, b, w):
    r = [max(x, EPS) ** (1 - w) * max(y, EPS) ** w for x, y in zip(a, b)]; s = sum(r)
    return [x / s for x in r]


def ll(p, y): return -math.log(max(p[y], EPS))
def brier(p, y): return sum((p[i] - (1.0 if i == y else 0.0)) ** 2 for i in range(len(p)))
def hit(p, y): return 1.0 if max(range(len(p)), key=lambda i: p[i]) == y else 0.0


def oku(o, keys):
    v = [fnum(o.get(k)) for k in keys]
    return v if all(v) else None


def indir(sezon_say):
    import update as U
    _, y = U.season_code(date.today())
    rows = []; log = {}
    for lg, (kind, code, _n) in U.LEAGUES.items():
        try:
            if kind == "main":
                for s in range(y - sezon_say, y + 1):
                    try:
                        txt = U.fetch(f"https://www.football-data.co.uk/mmz4281/{s % 100:02d}{(s + 1) % 100:02d}/{code}.csv")
                    except Exception as e:
                        log[f"{lg}-{s}"] = e.__class__.__name__; continue
                    n = 0
                    for r in csv.DictReader(io.StringIO(txt)):
                        d = U.parse_date(r.get("Date", "") or "")
                        if not d or (r.get("FTHG") or "") == "": continue
                        try: hg, ag = int(float(r["FTHG"])), int(float(r["FTAG"]))
                        except Exception: continue
                        rows.append({"lg": lg, "d": d, "s": s, "y": 0 if hg > ag else (1 if hg == ag else 2), "ou": 1 if hg + ag > 2 else 0,
                                     "avg": oku(r, ("AvgH", "AvgD", "AvgA")), "ps": oku(r, ("PSH", "PSD", "PSA")),
                                     "avgc": oku(r, ("AvgCH", "AvgCD", "AvgCA")), "psc": oku(r, ("PSCH", "PSCD", "PSCA")),
                                     "avgou": oku(r, ("Avg>2.5", "Avg<2.5")), "psou": oku(r, ("P>2.5", "P<2.5"))})
                        n += 1
                    log[f"{lg}-{s}"] = n
            else:
                txt = U.fetch(f"https://www.football-data.co.uk/new/{code}.csv"); n = 0
                for r in csv.DictReader(io.StringIO(txt)):
                    d = U.parse_date(r.get("Date", "") or "")
                    if not d or (r.get("HG") or "") == "" or d < f"{y - sezon_say}-01-01": continue
                    try: hg, ag = int(float(r["HG"])), int(float(r["AG"]))
                    except Exception: continue
                    s = int(d[:4]) if int(d[5:7]) >= 7 else int(d[:4]) - 1   # yıllık kat sınırı 1 Temmuz (üretimle aynı)
                    rows.append({"lg": lg, "d": d, "s": s, "y": 0 if hg > ag else (1 if hg == ag else 2), "ou": 1 if hg + ag > 2 else 0,
                                 "avg": None, "ps": None, "avgc": oku(r, ("AvgCH", "AvgCD", "AvgCA")), "psc": oku(r, ("PSCH", "PSCD", "PSCA")),
                                 "avgou": None, "psou": None})
                    n += 1
                log[lg] = n
        except Exception as e:
            log[lg] = e.__class__.__name__
    return rows, log, y


def boot(d, bl, rnd):
    """Blok bootstrap ortalamaları (numpy varsa vektörel)."""
    bsum = [sum(d[i] for i in g) for g in bl]; bcnt = [len(g) for g in bl]
    try:
        import numpy as np
        S = np.array(bsum); C = np.array(bcnt, dtype=float); g = np.random.default_rng(20261028); out = []
        for _ in range(B // 100):
            ix = g.integers(0, len(bl), size=(100, len(bl)))
            out.extend((S[ix].sum(1) / C[ix].sum(1)).tolist())
        return out
    except ImportError:
        out = []
        for _ in range(B):
            tot = cnt = 0.0
            for _k in range(len(bl)):
                j = rnd.randrange(len(bl)); tot += bsum[j]; cnt += bcnt[j]
            out.append(tot / cnt)
        return out


def deney(rows, a_key, b_key, yk, ad):
    """a = üretim kaynağı, b = keskin. Yürüyen pencere; aday: 'ps' (yalnız b) ve 'uzlasi' (log havuz, w öğrenilir)."""
    M = []
    for r in rows:
        a, b = r.get(a_key), r.get(b_key)
        if not a or not b: continue
        M.append((r["s"], r["d"], r["lg"], power_devig(a), power_devig(b), r[yk]))
    if len(M) < 2000: return {"ad": ad, "n": len(M), "not": "yetersiz veri"}
    M.sort(key=lambda m: m[1])
    sezonlar = sorted({m[0] for m in M})
    katlar = [s for s in sezonlar if sum(1 for m in M if m[0] < s) >= 3000]
    if not katlar: return {"ad": ad, "n": len(M), "not": "kat yok"}
    test = []; kat_ozet = []
    for s in katlar:
        tr = [m for m in M if m[0] < s]; te = [m for m in M if m[0] == s]
        if not te: continue
        # her aday kendi T'sini (ve w'sini) yalnız geçmişte seçer
        Ta = min(TS, key=lambda T: sum(ll(temp(m[3], T), m[5]) for m in tr))
        Tb = min(TS, key=lambda T: sum(ll(temp(m[4], T), m[5]) for m in tr))
        best = None
        for w in WS:
            pw = [pool(m[3], m[4], w) for m in tr]
            for T in TS[::2]:
                v = sum(ll(temp(p, T), m[5]) for p, m in zip(pw, tr))
                if best is None or v < best[0]: best = (v, w, T)
        _, w, Tu = best
        dl_b = dl_u = 0.0
        for m in te:
            pa = temp(m[3], Ta); pb = temp(m[4], Tb); pu = temp(pool(m[3], m[4], w), Tu)
            y = m[5]
            rec = (m[1], m[2], ll(pa, y), ll(pb, y), ll(pu, y), brier(pa, y), brier(pb, y), brier(pu, y), hit(pa, y), hit(pb, y), hit(pu, y))
            test.append(rec); dl_b += rec[3] - rec[2]; dl_u += rec[4] - rec[2]
        kat_ozet.append({"sezon": s, "n_ogren": len(tr), "n_sinama": len(te), "T_avg": Ta, "T_ps": Tb, "w_ps": w, "T_uzlasi": Tu,
                         "dLL_ps": round(dl_b / len(te), 5), "dLL_uzlasi": round(dl_u / len(te), 5)})
    test.sort(key=lambda r: r[0])
    out = {"ad": ad, "n": len(test), "katlar": kat_ozet, "adaylar": {}}
    bloklar = collections.defaultdict(list)
    for i, r in enumerate(test): bloklar[(r[1], r[0])].append(i)
    bl = list(bloklar.values()); rnd = random.Random(20261028)
    for ci, (aday, li, bi, hi) in enumerate((("ps", 3, 6, 9), ("uzlasi", 4, 7, 10))):
        d = [r[li] - r[2] for r in test]
        dB = sum(r[bi] - r[5] for r in test) / len(test)
        dH = sum(r[hi] - r[8] for r in test) / len(test)
        mean = sum(d) / len(d)
        h = len(d) // 2
        y1, y2 = sum(d[:h]) / h, sum(d[h:]) / (len(d) - h)
        bs = boot(d, bl, rnd)
        bs.sort()
        lo, hi_ = bs[int(0.025 * B)], bs[int(0.975 * B) - 1]
        p = sum(1 for v in bs if v >= 0) / B
        kat_cogu = sum(1 for k in out["katlar"] if k["dLL_" + aday] < 0) > len(out["katlar"]) / 2
        gecti = hi_ < 0 and y1 < 0 and y2 < 0 and dB <= 0 and dH >= 0 and p <= 0.05 and kat_cogu
        out["adaylar"][aday] = {"dLL": round(mean, 5), "GA95": [round(lo, 5), round(hi_, 5)], "yarilar": [round(y1, 5), round(y2, 5)],
                                "dBrier": round(dB, 5), "dIsabet": round(dH, 4), "p_tek": round(p, 4), "katlarin_cogu": kat_cogu, "kapi": gecti}
    out["LL_avg"] = round(sum(r[2] for r in test) / len(test), 5)
    return out


def main():
    sezon = 5
    if "--sezon" in sys.argv: sezon = int(sys.argv[sys.argv.index("--sezon") + 1])
    t0 = time.time()
    rows, log, y = indir(sezon)
    print(f"satır: {len(rows)} · indirme {time.time() - t0:.0f} sn", flush=True)
    sonuc = {"zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "madde": "YH-02", "kaynak": "football-data.co.uk",
             "satir": len(rows), "indirme_hata": {k: v for k, v in log.items() if isinstance(v, str)}, "deneyler": []}
    for a, b, yk, ad in (("avg", "ps", "y", "1x2_on"), ("avgou", "psou", "ou", "ou25_on"), ("avgc", "psc", "y", "1x2_kapanis")):
        t1 = time.time()
        r = deney(rows, a, b, yk, ad); r["sure_sn"] = round(time.time() - t1)
        sonuc["deneyler"].append(r)
        print(json.dumps({k: v for k, v in r.items() if k != "katlar"}, ensure_ascii=False), flush=True)
    sonuc["kapi"] = {d["ad"]: {k: v.get("kapi") for k, v in d.get("adaylar", {}).items()} for d in sonuc["deneyler"]}
    json.dump(sonuc, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("SONUC " + json.dumps(sonuc, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
