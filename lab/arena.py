"""🤖 Robot arenası (robot ordusu + öğrenen konsey).
Birbirinden bağımsız düşünen tahmin robotları her maçı yalnızca o güne kadarki bilgiyle tahmin eder:
  R1 Piyasa      — iddaa/bahis oranları (marj 'power' yöntemiyle ayrılır)
  R2 Poisson     — BULUTOXX motoru (takım hücum/savunma gücü, piyasa beklenen golüyle eğitilmiş)
  R3 Elo         — gol farkına duyarlı Elo derecesi
  R4 Form        — son 6 maçın attığı/yediği gol ortalaması (ev/deplasman ayrı)
  R5 Momentum    — piyasa beklentisine göre son maçlarda fazla/eksik gol (sürpriz eğilimi)
Konsey: robotların olasılıklarını ağırlıklandıran öğrenen birleştirici (çok sınıflı lojistik, log-olasılıklar üzerinde).
Konsey bir sezonda öğrenir, diğer sezonda sınanır (çapraz). İki yönde de piyasayı geçerse 'kabul'.
Ayrıca 'oy birliği analizi': robotların kaçı aynı sonucu gösteriyorsa isabet nasıl değişiyor.
Pazarlar: maç sonucu (1X2) ve 2,5 alt/üst. Çıktı: data/arena.json."""
import json, math, os, sys, collections, time
from datetime import date, timedelta
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import update as U
T0 = time.time(); BUDGET = float(os.environ.get("ARENA_BUDGET", "1500"))

def pois_probs(lh, la, line=2.5):
    p, pO, _, _ = U.outcome_probs(np.array([lh]), np.array([la]), -0.06); return p[0], float(pO[0])

def softmax(z): z = z - z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)

def fit_stacker(X, y, k, l2=1.0, it=400, lr=0.5):
    """Çok sınıflı lojistik regresyon (gradyan inişi). X: (n, f), y: sınıf. Robot log-olasılıkları + sabit."""
    n, f = X.shape; W = np.zeros((f, k))
    for _ in range(it):
        P = softmax(X @ W); G = X.T @ (P - np.eye(k)[y]) / n + l2 * W / n
        W -= lr * G
    return W

def main():
    S = json.load(open(os.path.join(ROOT, "data", "season.json"), encoding="utf-8"))
    M = json.load(open(os.path.join(ROOT, "data", "model.json"), encoding="utf-8")); P = dict(M["params"])
    leagues = [lg for lg, d in S.items() if not d.get("cup") and d.get("src") != "espn"]
    rows = []
    for lg in leagues:
        if time.time() - T0 > BUDGET: break
        ms = sorted([m for m in S[lg]["matches"] if m.get("ft")], key=lambda m: m["d"])
        if len(ms) < 300: continue
        U.market_xg([m for m in ms if m.get("odds")])
        seasons = sorted({m["season"] for m in ms})[-2:]
        # Elo ve form durumları kronolojik ilerler (bilgi sızıntısı yok)
        elo = collections.defaultdict(lambda: 1500.0); hist = collections.defaultdict(list); mom = collections.defaultdict(list)
        weeks = collections.OrderedDict()
        for m in ms:
            dd = date.fromisoformat(m["d"]); weeks.setdefault(dd - timedelta(days=dd.weekday()), []).append(m)
        fitF = None
        for wk, tm in weeks.items():
            test = tm[0]["season"] in seasons
            if test and len([x for x in ms if x["d"] < wk.isoformat()]) >= 120:
                train = [x for x in ms if (wk - timedelta(days=540)).isoformat() <= x["d"] < wk.isoformat()]
                F = U.fit(train, wk, P, iters=15)
                cnt = collections.Counter([x["h"] for x in train] + [x["a"] for x in train])
                L = np.mean([sum(x["ft"]) for x in train[-400:]]) / 2
                for m in tm:
                    if not m.get("odds") or not m.get("ou") or cnt[m["h"]] < 5 or cnt[m["a"]] < 5: continue
                    (ah, dh), (aa, da) = F["t"][m["h"]], F["t"][m["a"]]
                    p2, o2 = pois_probs(F["mu"] * F["gamma"] * ah * da, F["mu"] * aa * dh)
                    p1 = U.power_devig(m["odds"]); o1 = float(U.power_devig(m["ou"])[0])
                    de = elo[m["h"]] + 60 - elo[m["a"]]
                    hh, aa_ = hist[m["h"]][-6:], hist[m["a"]][-6:]
                    if len(hh) < 3 or len(aa_) < 3: continue
                    fh = (np.mean([x[0] for x in hh]) + np.mean([x[1] for x in aa_])) / 2; fa = (np.mean([x[0] for x in aa_]) + np.mean([x[1] for x in hh])) / 2
                    p4, o4 = pois_probs(max(fh, .2), max(fa, .2))
                    mh = np.mean(mom[m["h"]][-6:]) if mom[m["h"]] else 0.0; ma = np.mean(mom[m["a"]][-6:]) if mom[m["a"]] else 0.0
                    xg = m.get("xg") or [1.4, 1.1]
                    p5, o5 = pois_probs(max(xg[0] * math.exp(.25 * mh), .2), max(xg[1] * math.exp(.25 * ma), .2))
                    a, b = m["ft"]; r = 0 if a > b else 1 if a == b else 2
                    rows.append({"s": m["season"], "lg": lg, "r": r, "ov": int(a + b > 2), "m": p1, "mo": o1, "p": p2, "po": o2, "e": de, "f": p4, "fo": o4, "mm": p5, "mmo": o5})
            for m in tm:   # sonuçla durumları güncelle
                a, b = m["ft"]; de = elo[m["h"]] + 60 - elo[m["a"]]; ex = 1 / (1 + 10 ** (-de / 400)); sc = 1 if a > b else .5 if a == b else 0
                k = 20 * (1 + abs(a - b)) ** .5; elo[m["h"]] += k * (sc - ex); elo[m["a"]] -= k * (sc - ex)
                hist[m["h"]].append((a, b)); hist[m["a"]].append((b, a))
                if m.get("xg"): mom[m["h"]].append((a - m["xg"][0])); mom[m["a"]].append((b - m["xg"][1]))
        print(f"{lg}: {len(rows)} satır, {time.time()-T0:.0f} sn", flush=True)
    if len(rows) < 2000: print("yetersiz veri"); return
    seasons = sorted({r["s"] for r in rows})
    # Elo → 1X2: her test sezonu için diğer sezonda öğrenilen sıralı lojistik yerine basit çok sınıflı lojistik
    def elo_feat(rs): e = np.array([r["e"] for r in rs]) / 400; return np.stack([np.ones_like(e), e, e * e], 1)
    y = lambda rs: np.array([r["r"] for r in rs])
    out = {"tarih": date.today().isoformat(), "n": len(rows), "sezonlar": seasons, "robotlar": {}, "konsey": {}, "oybirligi": {}}
    def ll3(P, yy): return float(-np.mean(np.log(np.maximum(P[np.arange(len(yy)), yy], 1e-9))))
    def ll2(p, yy): p = np.clip(p, 1e-6, 1 - 1e-6); return float(-np.mean(yy * np.log(p) + (1 - yy) * np.log(1 - p)))
    res = collections.defaultdict(dict)
    for s in seasons:
        te = [r for r in rows if r["s"] == s]; tr = [r for r in rows if r["s"] != s]
        We = fit_stacker(elo_feat(tr), y(tr), 3); pe_te = softmax(elo_feat(te) @ We); pe_tr = softmax(elo_feat(tr) @ We)
        R3 = {"Piyasa": ("m", "mo"), "Poisson (BULUTOXX)": ("p", "po"), "Form": ("f", "fo"), "Momentum": ("mm", "mmo")}
        yy = y(te); ov = np.array([r["ov"] for r in te])
        for nm, (k, ko) in R3.items():
            Pm = np.array([r[k] for r in te]); po = np.array([r[ko] for r in te])
            res[nm][str(s)] = {"n": len(te), "ll_1x2": round(ll3(Pm, yy), 5), "isabet_1x2": round(float((Pm.argmax(1) == yy).mean()), 4),
                               "ll_ou": round(ll2(po, ov), 5), "isabet_ou": round(float(((po >= .5) == ov).mean()), 4)}
        res["Elo"][str(s)] = {"n": len(te), "ll_1x2": round(ll3(pe_te, yy), 5), "isabet_1x2": round(float((pe_te.argmax(1) == yy).mean()), 4)}
        # Konsey: geometrik havuz q ∝ Π p_i^w_i (robot ağırlıkları eğitim sezonunda koordinat aramasıyla öğrenilir)
        def pool3(rs, pe, w):
            L = sum(w[i] * np.log(np.maximum(A, 1e-6)) for i, A in enumerate([np.array([r[k] for r in rs]) for k in ("m", "p", "f", "mm")] + [pe]))
            return softmax(L)
        def pool2(rs, w):
            z = sum(w[i] * (np.log(np.maximum(np.array([r[k] for r in rs]), 1e-6)) - np.log(np.maximum(1 - np.array([r[k] for r in rs]), 1e-6))) for i, k in enumerate(("mo", "po", "fo", "mmo")))
            return 1 / (1 + np.exp(-z))
        def search(f, n):
            w = [1.0] + [0.0] * (n - 1); best = f(w); grid = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.85, 1.0, 1.15]
            for _ in range(3):
                for i in range(n):
                    for v in grid:
                        q = list(w); q[i] = v; l = f(q)
                        if l < best - 1e-6: best, w = l, q
            return w
        ytr = y(tr); ovtr = np.array([r["ov"] for r in tr])
        w1 = search(lambda w: ll3(pool3(tr, pe_tr, w), ytr), 5); Pk = pool3(te, pe_te, w1)
        w2 = search(lambda w: ll2(pool2(tr, w), ovtr), 4); pk2 = pool2(te, w2)
        out.setdefault("agirliklar", {})[str(s)] = {"1x2": dict(zip(["Piyasa", "Poisson", "Form", "Momentum", "Elo"], w1)), "ou": dict(zip(["Piyasa", "Poisson", "Form", "Momentum"], w2))}
        res["Konsey"][str(s)] = {"n": len(te), "ll_1x2": round(ll3(Pk, yy), 5), "isabet_1x2": round(float((Pk.argmax(1) == yy).mean()), 4),
                                 "ll_ou": round(ll2(pk2, ov), 5), "isabet_ou": round(float(((pk2 >= .5) == ov).mean()), 4)}
        # oy birliği: favori sonucu kaç robot gösteriyor
        votes = np.stack([np.array([r[k] for r in te]).argmax(1) for k in ("m", "p", "f", "mm")] + [pe_te.argmax(1)], 1)
        mk = np.array([r["m"] for r in te]).argmax(1); agree = (votes == mk[:, None]).sum(1)
        for a in range(1, 6):
            sel = agree == a
            if sel.sum() >= 30: out["oybirligi"].setdefault(str(a), {})[str(s)] = {"n": int(sel.sum()), "isabet": round(float((mk[sel] == yy[sel]).mean()), 4),
                                                                                    "piyasa_beklenen": round(float(np.array([r["m"][r_] for r, r_ in zip(np.array(te)[sel], mk[sel])]).mean()), 4)}
    out["robotlar"] = dict(res)
    base = res["Piyasa"]; kon = res["Konsey"]
    g1 = [base[s]["ll_1x2"] - kon[s]["ll_1x2"] for s in base]; g2 = [base[s]["ll_ou"] - kon[s]["ll_ou"] for s in base]
    out["konsey"] = {"kabul_1x2": all(g > 0.0005 for g in g1), "kabul_ou": all(g > 0.0005 for g in g2),
                     "kazanc_1x2": [round(g, 5) for g in g1], "kazanc_ou": [round(g, 5) for g in g2]}
    out["karar"] = ("Konsey " + " ve ".join([x for x, ok in (("maç sonucunda", out["konsey"]["kabul_1x2"]), ("alt/üstte", out["konsey"]["kabul_ou"])) if ok]) + " iki sezonda da piyasayı geçti."
                    if out["konsey"]["kabul_1x2"] or out["konsey"]["kabul_ou"] else "Konsey iki sezonda da piyasayı geçemedi; mevcut sistem (piyasa + kalibrasyon) korunur.")
    json.dump(out, open(os.path.join(ROOT, "data", "arena.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("konsey", "karar", "agirliklar")}, ensure_ascii=False))
    for nm, v in res.items(): print(f"{nm:20s}", " | ".join(f"{s}: 1X2 ll {x['ll_1x2']} %{x['isabet_1x2']*100:.1f}" + (f" · A/Ü ll {x['ll_ou']} %{x['isabet_ou']*100:.1f}" if "ll_ou" in x else "") for s, x in v.items()))

if __name__ == "__main__":
    main()
