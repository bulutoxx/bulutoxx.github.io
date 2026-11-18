"""YH-82 laboratuvarı: bozuk football-data 1X2 oranlarının (Σ1/o ∉ [0,98; 1,35]) ve onlardan türetilmiş piyasa xG'sinin
atılmasının zaman sıralı etkisi. A = bugünkü season.json, B = oran_temizle uygulanmış kopya. Aynı motor `backtest`
(her hafta yalnız önceki maçlarla eğitim, model.json parametreleri). Sınama = etkilenen liglerde ilk bozuk günden sonraki maçlar.
Kullanım: python3 lab/oran_temiz_lab.py [season.json]  → data/oran_temiz_lab.json (yalnız toplu metrik)."""
import json, os, sys, copy, collections
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import update as U

# YH-82 aday tanımı (dal yh82, scripts/update.py) burada kopya: main'de üretim kodu değişmedi.
def oran_akli(o):
    try: return bool(o) and len(o) == 3 and all(o) and 0.98 <= sum(1 / x for x in o) <= 1.35
    except (TypeError, ZeroDivisionError): return False

def oran_temizle(ms):
    n = 0
    for m in ms:
        if ("odds" in m and not oran_akli(m["odds"])) or ("xg_o" in m and not oran_akli(m["xg_o"])):
            for k in ("odds", "xg", "xg_o", "xg_m"): m.pop(k, None)
            n += 1
    return n

def main():
    sp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "season.json")
    SA = json.load(open(sp, encoding="utf-8"))
    P = json.load(open(os.path.join(ROOT, "data", "model.json"), encoding="utf-8"))["params"]
    P = {k: P[k] for k in ("decay", "prior", "rho", "formW", "mkt")}
    ilk = {}
    for lg, d in SA.items():
        if d.get("cup"): continue
        for m in d["matches"]:
            if (m.get("odds") and not oran_akli(m["odds"])) or (m.get("xg_o") and not oran_akli(m["xg_o"])):
                ilk[lg] = min(ilk.get(lg, "9999"), m["d"])
    SB = copy.deepcopy({lg: SA[lg] for lg in ilk})
    nsil = sum(oran_temizle(SB[lg]["matches"]) for lg in SB)
    A = U.backtest({lg: SA[lg]["matches"] for lg in ilk}, P); B = U.backtest({lg: SB[lg]["matches"] for lg in ilk}, P)
    def tablo(bt):
        out = {}
        for i, (lg, m, _, _) in enumerate(bt["rows"]):
            if m["d"] < ilk[lg]: continue
            y = bt["res"][i]; p = bt["p"][i]; po = bt["pO"][i]; o = 1 if sum(m["ft"]) > 2 else 0
            out[(lg, m["d"], m["h"], m["a"])] = (-np.log(max(p[y], 1e-9)), float(((p - np.eye(3)[y]) ** 2).sum()), int(np.argmax(p) == y),
                                                 -np.log(max(po if o else 1 - po, 1e-9)))
        return out
    ta, tb = tablo(A), tablo(B)
    ks = sorted(set(ta) & set(tb), key=lambda k: k[1])
    d = np.array([[tb[k][j] - ta[k][j] for j in range(4)] for k in ks])
    gun = collections.defaultdict(list)
    for i, k in enumerate(ks): gun[(k[0], k[1])].append(i)
    bl = list(gun.values()); rng = np.random.default_rng(7); bs = []
    for _ in range(2000):
        ix = np.concatenate([bl[j] for j in rng.integers(0, len(bl), len(bl))]); bs.append(d[ix, 0].mean())
    h = len(ks) // 2
    r = {"n": len(ks), "silinen": nsil, "ligler": ilk, "dLL": round(float(d[:, 0].mean()), 5),
         "ga95": [round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)],
         "yarilar": [round(float(d[:h, 0].mean()), 5), round(float(d[h:, 0].mean()), 5)],
         "dBrier": round(float(d[:, 1].mean()), 5), "isabet": [round(float(np.mean([ta[k][2] for k in ks])), 4), round(float(np.mean([tb[k][2] for k in ks])), 4)],
         "dLL_ou25": round(float(d[:, 3].mean()), 5),
         "lig": {lg: round(float(np.mean([d[i, 0] for i, k in enumerate(ks) if k[0] == lg])), 5) for lg in ilk}}
    r["kapi"] = bool(r["ga95"][1] < 0 and max(r["yarilar"]) < 0 and r["dBrier"] <= 0 and r["isabet"][1] >= r["isabet"][0])
    json.dump(r, open(os.path.join(ROOT, "data", "oran_temiz_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(r, ensure_ascii=False))

if __name__ == "__main__": main()
