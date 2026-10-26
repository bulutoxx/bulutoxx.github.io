"""OXXai otomatik laboratuvar (haftalık, GitHub Actions).
Açık kaynak penaltyblog (MIT) modellerini kendi motorumuzla aynı veride, hafta hafta ileriye dönük (oynanmamış gibi) yarıştırır.
Ölçüt: maç sonucu log-loss. Karşılaştırılanlar: piyasa (oran, marj 'power' yöntemiyle ayrılır), bizim model, penaltyblog Dixon-Coles,
ve bunların piyasa ile karışımları. Bir aday yalnızca SON İKİ SEZONUN İKİSİNDE de mevcut sistemi geçerse 'kabul' önerilir.
Sonuç data/auto_lab.json'a yazılır; Motor sayfasında görünür."""
import json, math, os, sys, time, collections, warnings
from datetime import date, timedelta
import numpy as np
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import update as U
LEAGUES = [l for l in (os.environ.get("LAB_LEAGUES") or "en,es,it,de,fr,tr1,pt,nl,en2,de2").split(",")]
BUDGET = float(os.environ.get("LAB_BUDGET", "2400"))
T0 = time.time()

def power_devig(o):
    q = 1 / np.asarray(o, float); lo, hi = 1.0, 3.0
    for _ in range(40):
        k = (lo + hi) / 2
        if (q ** k).sum() > 1: lo = k
        else: hi = k
    p = q ** k; return p / p.sum()

def main():
    S = json.load(open(os.path.join(ROOT, "data", "season.json"), encoding="utf-8"))
    M = json.load(open(os.path.join(ROOT, "data", "model.json"), encoding="utf-8"))
    P = dict(M["params"]); rho = P.get("rho", -0.06)
    try:
        import penaltyblog as pb
        have_pb = True
    except Exception as e:
        print("penaltyblog yok:", e); have_pb = False
    rows = []   # (sezon, sonuç, p_piyasa, p_bizim, p_pbDC)
    for lg in LEAGUES:
        d = S.get(lg)
        if not d: continue
        ms = sorted([m for m in d["matches"] if m.get("ft")], key=lambda m: m["d"])
        U.market_xg([m for m in ms if m.get("odds")])
        seasons = sorted({m["season"] for m in ms})[-2:]
        test = [m for m in ms if m["season"] in seasons and m.get("odds")]
        weeks = collections.OrderedDict()
        for m in test:
            dd = date.fromisoformat(m["d"]); weeks.setdefault(dd - timedelta(days=dd.weekday()), []).append(m)
        for wk, tm in weeks.items():
            if time.time() - T0 > BUDGET: break
            cut = wk.isoformat(); lo = (wk - timedelta(days=540)).isoformat()
            train = [m for m in ms if lo <= m["d"] < cut]
            if len(train) < 80: continue
            F = U.fit(train, wk, P, iters=20)
            cnt = collections.Counter([m["h"] for m in train] + [m["a"] for m in train])
            pbm = None
            if have_pb:
                try:
                    days = np.array([(wk - date.fromisoformat(m["d"])).days for m in train], float)
                    w = np.exp(-0.0065 * days)    # penaltyblog belgelerindeki tipik zaman ağırlığı (xi ≈ 0.0018/gün * 3.6)
                    pbm = pb.models.DixonColesGoalModel([m["ft"][0] for m in train], [m["ft"][1] for m in train],
                                                        [m["h"] for m in train], [m["a"] for m in train], w)
                    pbm.fit()
                except Exception as e:
                    pbm = None
            for m in tm:
                if cnt[m["h"]] < 3 or cnt[m["a"]] < 3: continue
                (ah, dh), (aa, da) = F["t"][m["h"]], F["t"][m["a"]]
                lh = F["mu"] * F["gamma"] * ah * da; la = F["mu"] * aa * dh
                p_our, _, _, _ = U.outcome_probs(np.array([lh]), np.array([la]), rho)
                p_pb = None
                if pbm is not None:
                    try: p_pb = np.array(pbm.predict(m["h"], m["a"]).home_draw_away, float)
                    except Exception: p_pb = None
                r = 0 if m["ft"][0] > m["ft"][1] else 1 if m["ft"][0] == m["ft"][1] else 2
                rows.append((m["season"], r, power_devig(m["odds"]), p_our[0], p_pb))
        print(f"{lg}: toplam {len(rows)} satır, {time.time()-T0:.0f} sn", flush=True)
    if not rows: return
    seasons = sorted({r[0] for r in rows})
    def ll(ps, rs): return float(-np.mean([math.log(max(p[r], 1e-9)) for p, r in zip(ps, rs)]))
    def mix(a, b, w):
        q = np.exp((1 - w) * np.log(np.maximum(a, 1e-9)) + w * np.log(np.maximum(b, 1e-9))); return q / q.sum()
    cands = {"piyasa (mevcut)": lambda r: r[2], "bizim model": lambda r: r[3]}
    for w in (0.1, 0.2, 0.3): cands[f"piyasa + bizim %{int(w*100)}"] = (lambda w: lambda r: mix(r[2], r[3], w))(w)
    if any(r[4] is not None for r in rows):
        cands["penaltyblog Dixon-Coles"] = lambda r: r[4] if r[4] is not None else r[3]
        for w in (0.1, 0.2, 0.3): cands[f"piyasa + penaltyblog %{int(w*100)}"] = (lambda w: lambda r: mix(r[2], r[4] if r[4] is not None else r[2], w))(w)
    out = {"tarih": date.today().isoformat(), "ligler": LEAGUES, "n": len(rows), "sezonlar": seasons, "sonuc": {}}
    base = {}
    for name, fn in cands.items():
        res = {}
        for s in seasons:
            sub = [r for r in rows if r[0] == s]
            ps = [fn(r) for r in sub]; rs = [r[1] for r in sub]
            res[str(s)] = {"n": len(sub), "logloss": round(ll(ps, rs), 5), "isabet": round(float(np.mean([np.argmax(p) == r for p, r in zip(ps, rs)])), 4)}
        out["sonuc"][name] = res
        if name == "piyasa (mevcut)": base = res
    best = None
    for name, res in out["sonuc"].items():
        if name == "piyasa (mevcut)": continue
        gains = [base[s]["logloss"] - res[s]["logloss"] for s in res]
        if all(g > 0.0005 for g in gains) and (best is None or sum(gains) > best[1]): best = (name, sum(gains))
    out["karar"] = {"kabul": best[0] if best else None, "aciklama": (f"'{best[0]}' iki sezonda da piyasayı geçti (toplam log-loss kazancı {best[1]:.4f})." if best
                    else "Hiçbir aday iki sezonun ikisinde de mevcut sistemi (piyasa olasılığı) geçemedi; mevcut sistem korunur.")}
    json.dump(out, open(os.path.join(ROOT, "data", "auto_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
