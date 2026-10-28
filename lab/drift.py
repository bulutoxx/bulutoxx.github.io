"""📉 Drift alarmı (futbol): lig ve pazar bazında model − piyasa log-kayıp farkı izlenir; model bozulursa o ligde model ağırlığı düşer.

Neden: koruyucu (lab/guardian.py) yalnız bir değişiklikten sonraki 14 günü izler; değişiklik olmadan modelin bir ligde kötüleşmesi
(kadro değişimi, sezon başı, veri kayması) görünmüyordu.

Ölçü (maç başına): Δ = LL(model) − LL(piyasa); 1X2 ve 2,5 Alt/Üst ayrı. Oransız maçta (piyasa yok) Δ = LL(model) − LL(temel yol)
(g0/g0o = aynı anda kilitlenen eski Poisson üretim yolu; pazar adı 1x2_t / ou_t; ağırlık lig pazarının en küçüğü). Kaynak: kilitli tahmin günlüğü (data/predlog.json),
kapanış kilidi varsa onu (pc/mpc, pco/mpco), yoksa açılışı (p/mp, o/mo) kullanır. Piyasa = oran payı.
  • yürüyen 7 gün ortalama Δ (n7)
  • tek yönlü CUSUM: S ← max(0, S + (Δ − μ0)/σ − k); μ0/σ = taban fark (canlı veride ≥300 maç varsa canlı havuz, yoksa geçmiş arşiv).
Alarm: S > h VE n7 ≥ N7_MIN VE 7 gün ortalaması tabandan kötü. Alarmda o lig-pazarın model ağırlığı a = 0 (oranlı maç: yalnız piyasa;
oransız maç: topluluk tahmini → Poisson), S sıfırlanır. Düzelme: her gün 7 gün ortalaması tabana dönmüşse (n7 ≥ N7_MIN) a += 0,25;
veri yoksa alarmdan 14 gün sonra kademeli döner. Durum her çalışmada tüm canlı veriden baştan yeniden üretilir (deterministik; durum kaybolmaz).

Eşik seçimi (geçmiş arşiv, günde bir kez): motorun geriye dönük testi (her maç yalnız önceki maçlarla) football-data oranlarıyla;
(k, h) ızgarasında yanlış alarm oranı (arşivde bilinen drift yok → her alarm yanlış sayılır, üst sınır) ≤ 1/hafta olanlar içinden
yapay kayma enjeksiyonunda (+0,15 Δ, 14 gün) 7 günde yakalama oranı en yüksek olan seçilir.

Çıktı: data/drift.json (motor scripts/update.py drift_ayar() ile okur). Yalnız numpy; ağ yok; ücretsiz.
  python3 lab/drift.py            # ölç + yaz
  python3 lab/drift.py --kuru     # yazmaz
"""
import collections, json, math, os, sys
from datetime import date, datetime, timedelta, timezone
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
CIKTI = os.path.join(DATA, "drift.json")
N7_MIN, ADIM, VERISIZ_GUN, CANLI_TABAN_MIN, TEMEL_TABAN_MIN = 8, 0.25, 14, 300, 100
KS = (0.05, 0.1, 0.25, 0.5)
HS = (2, 3, 4, 5, 6, 8, 10, 12, 15, 20)
VARSAYILAN = {"k": 0.25, "h": 8.0}
ENJ_D, ENJ_GUN, ENJ_YAKALAMA = 0.15, 14, 7


def bugun(): return (datetime.now(timezone.utc) + timedelta(hours=3)).date()
def jl(p, d=None):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d
def R(x, k=5): return None if x is None else round(float(x), k)
def _ll3(q, y): return -math.log(max(q[y], 1e-9))
def _ll2(p, y): return -math.log(max(p if y else 1 - p, 1e-9))
def _pay(o):
    inv = 1 / np.asarray(o, float); return inv / inv.sum(-1, keepdims=True)


# ------------------------------------------------------------------ seriler
def canli_seri(plog):
    """[(lig, gün, pazar, Δ)] kilitli tahmin günlüğünden (sonuçlu, piyasası olan)."""
    out = []
    for e in plog:
        r = e.get("r")
        if not isinstance(r, list) or len(r) != 2: continue
        y = 0 if r[0] > r[1] else 1 if r[0] == r[1] else 2; ov = sum(r) > 2
        m, q = (e.get("pc"), e.get("mpc")) if e.get("pc") and e.get("mpc") else (e.get("p"), e.get("mp"))
        if isinstance(m, list) and isinstance(q, list) and len(m) == 3 and len(q) == 3:
            out.append((e["lg"], e["d"], "1x2", _ll3(m, y) - _ll3(q, y)))
        mo, qo = (e.get("pco"), e.get("mpco")) if e.get("mpco") is not None and e.get("pco") is not None else (e.get("o"), e.get("mo"))
        if isinstance(mo, (int, float)) and isinstance(qo, (int, float)):
            out.append((e["lg"], e["d"], "ou", _ll2(mo, ov) - _ll2(qo, ov)))
        # oransız maç: model (kilitli p; topluluk / yeni Poisson) − temel yol (g0 = eski Poisson üretim yolu, aynı anda kilitli)
        if not e.get("mp") and isinstance(e.get("g0"), list) and len(e["g0"]) == 3 and isinstance(e.get("p"), list):
            out.append((e["lg"], e["d"], "1x2_t", _ll3(e["p"], y) - _ll3(e["g0"], y)))
            if isinstance(e.get("g0o"), (int, float)) and isinstance(e.get("o"), (int, float)) and abs(e["o"] - e["g0o"]) > 1e-9:
                out.append((e["lg"], e["d"], "ou_t", _ll2(e["o"], ov) - _ll2(e["g0o"], ov)))
    return out


def gecmis_seri(U, season, P):
    """Geçmiş arşiv: motorun geriye dönük testi (her maç yalnız önceki maçlarla), oranlı maçlar. Model = predict_fixtures ile aynı yol."""
    core = {lg: d["matches"] for lg, d in season.items() if not d.get("cup") and d.get("src") != "espn"}
    bt = U.backtest(core, P)
    rows = bt["rows"]; lh = np.array([r[2] for r in rows]); la = np.array([r[3] for r in rows]); gs = P.get("gscale", 1.0)
    p, pO, _, _ = U.outcome_probs(lh * gs, la * gs, P["rho"]); p = U.apply_cal(p, P)
    out = []
    for i, (lg, m, _, _) in enumerate(rows):
        y = 0 if m["ft"][0] > m["ft"][1] else 1 if m["ft"][0] == m["ft"][1] else 2; ov = sum(m["ft"]) > 2
        if m.get("odds") and all(m["odds"]):
            out.append((lg, m["d"], "1x2", _ll3(p[i], y) - _ll3(_pay(m["odds"]), y)))
        if m.get("ou") and all(m["ou"]):
            out.append((lg, m["d"], "ou", _ll2(float(pO[i]), ov) - _ll2(float(_pay(m["ou"])[0]), ov)))
    return out


# ------------------------------------------------------------------ tekrar oynatma (deterministik durum)
def oynat(seri, k, h, mu, sig, son_gun=None, olay=False):
    """seri: [(lig, gün, pazar, Δ)]. Dönüş: {(lig, pazar): durum}, olaylar, alarm sayısı."""
    by = collections.defaultdict(list)
    for lg, d, pz, x in seri: by[(lg, pz)].append((d, x))
    D = {}; olaylar = []; n_alarm = 0
    for (lg, pz), L in by.items():
        L.sort(); gunluk = collections.defaultdict(list)
        for d, x in L: gunluk[d].append(x)
        g0 = date.fromisoformat(L[0][0]); g1 = date.fromisoformat(son_gun or L[-1][0])
        S, a, son_alarm, w = 0.0, 1.0, None, collections.deque()
        g = g0
        while g <= g1:
            gs = g.isoformat()
            for x in gunluk.get(gs, ()):
                S = max(0.0, S + (x - mu[pz]) / sig[pz] - k); w.append((g, x))
            while w and (g - w[0][0]).days >= 7: w.popleft()
            n7 = len(w); m7 = sum(x for _, x in w) / n7 if n7 else None
            if S > h and n7 >= N7_MIN and m7 > mu[pz]:
                n_alarm += 1; S = 0.0; son_alarm = g
                if olay: olaylar.append({"tarih": gs, "lig": lg, "pazar": pz, "tur": "alarm", "w7": R(m7, 4), "n7": n7})
                a = 0.0
            elif a < 1 and son_alarm and g > son_alarm:
                if (n7 >= N7_MIN and m7 <= mu[pz]) or (n7 == 0 and (g - son_alarm).days >= VERISIZ_GUN):
                    a = min(1.0, a + ADIM)
                    if olay and a >= 1: olaylar.append({"tarih": gs, "lig": lg, "pazar": pz, "tur": "duzeldi"})
            g += timedelta(days=1)
        D[(lg, pz)] = {"a": a, "S": round(S, 3), "n7": n7, "w7": R(m7, 4), "son_alarm": son_alarm.isoformat() if son_alarm else None, "n": len(L)}
    return D, olaylar, n_alarm


def _hafta(seri):
    ds = sorted({d for _, d, _, _ in seri}); return max(1.0, (date.fromisoformat(ds[-1]) - date.fromisoformat(ds[0])).days / 7) if ds else 1.0


def esik_sec(seri, mu, sig, seed=5, n_enj=150):
    """(k, h) ızgarası: yanlış alarm/hafta (geçmiş arşiv) ve yapay kayma yakalama oranı."""
    hafta = _hafta(seri); rng = np.random.default_rng(seed)
    by = collections.defaultdict(list)
    for t in seri: by[(t[0], t[2])].append(t)
    anahtar = [k_ for k_, L in by.items() if len(L) >= 150]
    enj = []
    for _ in range(n_enj if anahtar else 0):
        k_ = anahtar[rng.integers(len(anahtar))]; L = sorted(by[k_], key=lambda t: t[1]); i0 = int(rng.integers(len(L) // 4, len(L) - 30))
        enj.append((k_, L[i0][1]))
    tablo = []
    for k in KS:
        for h in HS:
            _, _, na = oynat(seri, k, h, mu, sig); fa = na / hafta
            yak = None
            if enj and fa <= 1.0:
                ok = 0
                for (lg, pz), d0 in enj:
                    d1 = (date.fromisoformat(d0) + timedelta(days=ENJ_GUN)).isoformat()
                    L = [(l, d, p, x + (ENJ_D if d0 <= d < d1 else 0)) for (l, d, p, x) in by[(lg, pz)] if d < d1]
                    D, ol, _ = oynat(L, k, h, mu, sig, olay=True)
                    lim = (date.fromisoformat(d0) + timedelta(days=ENJ_YAKALAMA)).isoformat()
                    ok += any(o["tur"] == "alarm" and d0 <= o["tarih"] <= lim for o in ol)
                yak = round(ok / len(enj), 4)
            tablo.append({"k": k, "h": h, "alarm": na, "yanlis_alarm_hafta": round(fa, 3), "yakalama_7g": yak})
    uygun = [t for t in tablo if t["yanlis_alarm_hafta"] <= 1.0 and t["yakalama_7g"] is not None]
    sec = max(uygun, key=lambda t: (t["yakalama_7g"], -t["yanlis_alarm_hafta"])) if uygun else None
    return sec, tablo, round(hafta, 1)


PAZAR = ("1x2", "ou", "1x2_t", "ou_t")   # _t = oransız: model − temel yol (Poisson); diğerleri model − piyasa


def taban(seri, n_min=50):
    mu, sig = {}, {}
    for pz in PAZAR:
        x = np.array([t[3] for t in seri if t[2] == pz])
        mu[pz], sig[pz] = (float(x.mean()), float(max(x.std(), 0.05))) if len(x) >= n_min else ((0.0, 0.25) if pz in ("1x2", "ou") else (0.0, 0.15))
    return mu, sig


def calis(kuru=False):
    import update as U
    gs = bugun().isoformat(); E = jl(CIKTI, {}) or {}
    M = jl(os.path.join(DATA, "model.json"), {}) or {}; P = dict(M.get("params") or {})
    G = E.get("gecmis_olcum") or {}
    if G.get("tarih") != gs or G.get("fp") != M.get("fp"):
        try:
            season = jl(os.path.join(DATA, "season.json"), {}) or {}
            hs = gecmis_seri(U, season, P); mu_g, sig_g = taban(hs)
            sec, tablo, hafta = esik_sec(hs, mu_g, sig_g)
            G = {"tarih": gs, "fp": M.get("fp"), "n": len(hs), "hafta": hafta, "ilk": min(t[1] for t in hs), "son": max(t[1] for t in hs),
                 "mu": {k: R(v) for k, v in mu_g.items()}, "sigma": {k: R(v) for k, v in sig_g.items()}, "secilen": sec, "tablo": tablo,
                 "aciklama": "Geçmiş arşivde bilinen drift yok: her alarm yanlış sayılır (üst sınır). yakalama_7g = yapay +0,15 Δ kaymanın 7 günde yakalanma oranı."}
        except Exception as e:
            print("drift geçmiş ölçümü atlandı:", e.__class__.__name__, e, flush=True); G = dict(G, hata=f"{e.__class__.__name__}: {e}"[:200])
    sec = G.get("secilen") or VARSAYILAN; k, h = sec["k"], sec["h"]
    cs = canli_seri(jl(os.path.join(DATA, "predlog.json"), []) or [])
    mu, sig = {}, {}
    mu_c, sig_c = taban(cs)
    for pz in PAZAR:
        n_c = sum(1 for t in cs if t[2] == pz)
        if n_c >= CANLI_TABAN_MIN: mu[pz], sig[pz] = mu_c[pz], sig_c[pz]
        elif pz.endswith("_t"): mu[pz], sig[pz] = (mu_c[pz], sig_c[pz]) if n_c >= TEMEL_TABAN_MIN else (0.0, 0.15)   # geçmiş arşivde temel yol yok
        else: mu[pz], sig[pz] = (G.get("mu") or {}).get(pz, 0.0) or 0.0, (G.get("sigma") or {}).get(pz, 0.25) or 0.25
    D, olaylar, na = oynat(cs, k, h, mu, sig, son_gun=gs, olay=True)
    ligler = {}
    for (lg, pz), st in sorted(D.items()):
        L = ligler.setdefault(lg, {"agirlik_1x2": 1.0, "agirlik_ou": 1.0})
        ana = pz.replace("_t", ""); L[f"agirlik_{ana}"] = min(L[f"agirlik_{ana}"], st["a"]); L[pz] = st
    for L in ligler.values():
        L["durum"] = "alarm" if min(L["agirlik_1x2"], L["agirlik_ou"]) == 0 else ("toparlaniyor" if min(L["agirlik_1x2"], L["agirlik_ou"]) < 1 else "normal")
    out = {"v": 1, "guncelleme": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
           "prm": {"k": k, "h": h, "n7_min": N7_MIN, "adim": ADIM, "verisiz_gun": VERISIZ_GUN, "mu": {p: R(v) for p, v in mu.items()},
                   "sigma": {p: R(v) for p, v in sig.items()}, "taban_kaynak": {p: ("canli" if sum(1 for t in cs if t[2] == p) >= (TEMEL_TABAN_MIN if p.endswith("_t") else CANLI_TABAN_MIN) else ("varsayilan" if p.endswith("_t") else "gecmis")) for p in PAZAR}},
           "canli": {"n": len(cs), **{f"n_{p}": sum(1 for t in cs if t[2] == p) for p in PAZAR}, "alarm": na,
                     "alarm_hafta": R(na / _hafta(cs), 3) if cs else None,
                     "fark_1x2": R(mu_c["1x2"]) if any(t[2] == "1x2" for t in cs) else None, "fark_ou": R(mu_c["ou"]) if any(t[2] == "ou" for t in cs) else None},
           "ligler": ligler, "olaylar": olaylar[-60:],
           "dusuk_agirlik": sorted(lg for lg, L in ligler.items() if L["durum"] != "normal"),
           "gecmis_olcum": G,
           "aciklama": "Lig × pazar model − piyasa log-kayıp farkı (yürüyen 7 gün + CUSUM). agirlik_* < 1 olan ligde motor model ağırlığını düşürür "
                       "(oranlı maç: yalnız piyasa; oransız maç: topluluk tahmini Poisson'a doğru). Düzelince günde 0,25 geri gelir."}
    if not kuru:
        tmp = CIKTI + ".tmp"; json.dump(out, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, CIKTI)
    print(json.dumps({"prm": out["prm"], "canli": out["canli"], "dusuk_agirlik": out["dusuk_agirlik"],
                      "gecmis": {k_: G.get(k_) for k_ in ("n", "hafta", "secilen")}}, ensure_ascii=False))
    return out


if __name__ == "__main__":
    try: calis(kuru="--kuru" in sys.argv)
    except Exception as e:
        import traceback; traceback.print_exc(); print("drift atlandı:", e.__class__.__name__, e); sys.exit(1)
