#!/usr/bin/env python3
"""🔁 OXX sürekli öğrenme döngüsü (gece, otonom-ekip iş akışında; koruyucudan SONRA).

1) Sinyal → deney kuyruğu (data/deney_kuyrugu.json): OXX'un kilitli kupon karnesi (data/oxx_karne.json + gün dosyaları),
   kilitli tahmin günlükleri (predlog, pazar karnesinin canlı bölümü, bk_predlog, at karnesi) içinde OXX'un beklentisi ile
   gerçek arasındaki SİSTEMATİK farklar (|z| ≥ 1,5; öncelik |z|) otomatik deney adayı olur: strateji eşiği, pazar düzeltmesi (Platt),
   lig dışlama, basket σ ölçeği, at olasılık üssü (τ). Sinyal yoksa sıradaki keşif adayı (eşik ±0,02) eklenir.
2) Gece sınaması: kuyruktan en fazla N (OXX_N, varsayılan 3) aday; bu yılın geçmiş maçlarında İLERİYE DÖNÜK sanal oynatma
   (her gün yalnız o günden önce bilinenle: maç öncesi oran, önceki aylarla öğrenilmiş kalibratör / önceki maçlarla basket
   modeli / sızıntısız at yeniden oynatması). Günler ikiye bölünür: seçim dilimi (ilk 2/3) ve sınama dilimi (son 1/3).
3) KAPI (hepsi gerekli):
   a) seçim diliminde aday tabandan iyi;
   b) sınama diliminde eşleştirilmiş gün bootstrap'ının (B=2000) tek yanlı alt sınırı > 0, güven düzeyi deneme sayısıyla
      katılaşır: α = 0,05 / m (Bonferroni; m = bu yılın verisiyle o alanda bugüne kadar yapılan TÜM sınamalar, bu dahil);
   c) koruma: Altın bacak isabeti ve güçlü (≥%70) bacak isabeti sınamada düşmez; kupon sayısı tabanın %70'inden aşağı inmez;
   d) koruyucu (lab/guardian.py) geri alma aktifse ya da bu anahtar OXX geri alma süresindeyse kabul DONDURULUR.
4) Geçen değişiklik yalnız data/oxx_ayar.json'a küçük, geri alınabilir bir parametre olarak yazılır (motorun model.json ayarlarına
   dokunulmaz: onları saatlik motor yeniden öğrenir ve koruyucu izler — çakışma olmasın). Kupon robotu izlenen değişiklik için
   önceki ayarla "gölge" kupon da kilitler.
5) 14 gün sonra yeniden sınama: yalnız kabulden SONRAKİ günlerle (sanal oynatma) + canlı gölge kuponlarla. Kötüleşirse otomatik
   geri alınır; data/oxx_rollback.json (rollback.json kalıbı: aktif, baslangic, bitis, neden, params) 14 gün o anahtarı dondurur.
Her karar data/ogrenme_gunlugu.json'a yazılır (ne denendi, rakamlar, kabul/ret ve nedeni).

  python lab/oxx_ogren.py            # gece döngüsü
  python lab/oxx_ogren.py --kuru     # dosya yazmadan (deneme)
Ortam: OXX_N (gecelik aday), OXX_BUDGET (sn, varsayılan 300).
"""
import argparse, collections, copy, json, math, os, sys, time
from datetime import date, datetime, timedelta, timezone

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import oxx_kupon as K  # noqa: E402

KUYRUK = os.path.join(DATA, "deney_kuyrugu.json")
GUNLUK = os.path.join(DATA, "ogrenme_gunlugu.json")
OXX_RB = os.path.join(DATA, "oxx_rollback.json")
N_GECE = int(os.environ.get("OXX_N", "3"))
BUDGET = float(os.environ.get("OXX_BUDGET", "300"))
ALFA, B_BOOT, Z_SINYAL, BEKLEME, IZLEME = 0.05, 2000, 1.5, 14, 14
ESIK = {"fb_altin": ("p_min", .70, .90), "fb_70": ("p_bacak", .62, .85), "fb_3lu": ("p_min", .52, .80), "fb_deger": ("p_min", .30, .60),
        "fb_guvenli": ("p_min", .72, .92), "bk_en_olasi": ("p_min", .55, .80)}
T0 = time.time()
RNG = np.random.default_rng(20261026)


def r4(x): return None if x is None else round(float(x), 4)


def kalan(): return BUDGET - (time.time() - T0)


# ------------------------------------------------------------------ yardımcı: ayar yolu
def al(params, yol, vars_=None):
    cur = params
    for k in yol:
        if not isinstance(cur, dict) or k not in cur: return vars_
        cur = cur[k]
    return cur


def koy(params, yol, deger):
    cur = params
    for k in yol[:-1]: cur = cur.setdefault(k, {})
    if deger == "__yok__": cur.pop(yol[-1], None)
    else: cur[yol[-1]] = deger


def aday_ayar(J, yol, deger):
    G = copy.deepcopy(J); koy(G.setdefault("params", {}), yol, deger); return G


# ------------------------------------------------------------------ 1) sinyaller
def _z(h, e, v): return (h - e) / math.sqrt(v) if v > 0 else 0.0


def sinyaller(bugun, A):
    C = []
    T = K.tum_kuponlar()
    kup = collections.defaultdict(list); leg = collections.defaultdict(list); sleg = collections.defaultdict(list)
    for g, sp, Kp, geri in T:
        if Kp.get("durum") not in ("tuttu", "tutmadi"): continue
        kup[Kp["strateji"]].append((float(Kp["p"] or 0), bool(Kp["tuttu"])))
        if not Kp["strateji"].startswith("at_altili_"):
            sleg[Kp["strateji"]] += [(float(b["p"]), bool(b["tuttu"])) for b in Kp["bacaklar"] if b.get("tuttu") is not None and b.get("p") is not None]
        if sp == "futbol":
            for b in Kp["bacaklar"]:
                if b.get("tuttu") is not None: leg[b["kod"]].append((float(b["p"]), bool(b["tuttu"])))
    def ozet(L):
        p = np.array([x[0] for x in L]); y = np.array([x[1] for x in L], float)
        return len(L), float(y.sum()), float(p.sum()), float((p * (1 - p)).sum())
    # a) strateji kalibrasyonu → eşik / at τ
    for s, L0 in kup.items():
        L = L0 if len(L0) >= 15 else sleg.get(s, [])   # az kupon varsa bacak düzeyi (tek tek tahminler)
        if len(L) < 15: continue
        n, h, e, v = ozet(L); z = _z(h, e, v)
        if abs(z) < Z_SINYAL: continue
        sig = {"n": n, "tutan": int(h), "beklenen": round(e, 2), "z": round(z, 2), "kaynak": "oxx_karne (kilitli OXX kuponları)"}
        if s in ESIK:
            par, lo, hi = ESIK[s]; cur = A[s][par]; yeni = round(min(hi, cur + .02) if z < 0 else max(lo, cur - .02), 2)
            if yeni != cur:
                C.append({"anahtar": f"esik:{s}:{par}:{yeni}", "tur": "esik", "alan": "basket" if s.startswith("bk") else "futbol",
                          "yol": [s, par], "deger": yeni, "stratejiler": [s], "sinyal": sig,
                          "aciklama": f"{s} {'beklentinin altında' if z < 0 else 'beklentinin üstünde'} tuttu → {par} {cur} → {yeni}"})
        if s in ("at_ikili", "at_sirali_ikili", "at_cifte"):
            cur = A[s].get("tau", 1.0); yeni = round(cur * (0.9 if z < 0 else 1.1), 3)
            C.append({"anahtar": f"at_tau:{s}:{yeni}", "tur": "at_tau", "alan": "at", "yol": [s, "tau"], "deger": yeni, "stratejiler": [s],
                      "sinyal": sig, "aciklama": f"{s} olasılıkları {'fazla' if z < 0 else 'az'} güvenli → τ {cur} → {yeni}"})
    # b) futbol pazar düzeyi (OXX bacakları + pazar karnesinin kilitli predlog bölümü) → pazar düzeltmesi
    PK = K.jl(os.path.join(DATA, "pazar_karne.json"), {}) or {}
    cz = {}
    for c, L in leg.items():
        if len(L) >= 30:
            n, h, e, v = ozet(L); cz[c] = (n, h, e, v, "OXX bacakları")
    for c, v_ in ((PK.get("canli") or {}).get("pazarlar") or {}).items():
        n = v_.get("n", 0); pt, gt = v_.get("ort_tahmin"), v_.get("ort_gercek")
        if n >= 30 and pt is not None and gt is not None and (c not in cz or n > cz[c][0]):
            cz[c] = (n, gt * n, pt * n, n * pt * (1 - pt), "pazar_karne.canli (kilitli predlog)")
    for c, (n, h, e, v, kay) in cz.items():
        z = _z(h, e, v)
        if abs(z) >= Z_SINYAL and c not in (A.get("duzeltme") or {}).get("pazar", {}):
            C.append({"anahtar": f"pazar:{c}", "tur": "pazar", "alan": "futbol", "yol": ["duzeltme", "pazar", c], "deger": None,
                      "stratejiler": [s for s in K.STRATEJI if s.startswith("fb_")],
                      "sinyal": {"n": n, "tutan": round(h, 1), "beklenen": round(e, 2), "z": round(z, 2), "kaynak": kay},
                      "aciklama": f"{c}: OXX olasılığı sistemli {'yüksek' if z < 0 else 'düşük'} → Platt düzeltmesi (seçim diliminde öğrenilir)"})
    # c) lig: predlog (kilitli maç öncesi) en olası MS sonucu
    lgL = collections.defaultdict(list)
    for e in K.jl(os.path.join(DATA, "predlog.json"), []) or []:
        r = e.get("r")
        if not isinstance(r, list): continue
        p = e.get("mp") or e.get("p"); i = int(np.argmax(p)); res = 0 if r[0] > r[1] else 1 if r[0] == r[1] else 2
        lgL[e["lg"]].append((float(p[i]), i == res))
    for lg, L in lgL.items():
        if len(L) < 40 or lg in (A.get("lig_dis") or []): continue
        n, h, e, v = ozet(L); z = _z(h, e, v)
        if z <= -2.5:
            C.append({"anahtar": f"lig:{lg}", "tur": "lig", "alan": "futbol", "yol": ["lig_dis"], "deger": sorted(set((A.get("lig_dis") or []) + [lg])),
                      "stratejiler": [s for s in K.STRATEJI if s.startswith("fb_")], "sinyal": {"n": n, "tutan": int(h), "beklenen": round(e, 2), "z": round(z, 2),
                      "kaynak": "predlog (kilitli maç öncesi tahmin)"}, "aciklama": f"{lg}: en olası sonuç beklentinin belirgin altında → OXX kuponlarından çıkar"})
    # d) basket σ
    BJ = K.jl(os.path.join(DATA, "basket.json"), {}) or {}
    L = []
    for e in K.jl(os.path.join(DATA, "bk_predlog.json"), []) or []:
        if not e.get("r") or e.get("ph") is None: continue
        sm = (BJ.get("leagues", {}).get(e["lg"]) or {}).get("sm") or 12.0
        p1 = K._phi((e["ph"] - e["pa"]) / (sm * A["bk_en_olasi"].get("olcek", 1.0)))
        L.append((max(p1, 1 - p1), (e["r"][0] > e["r"][1]) == (p1 >= .5)))
    if len(L) >= 30:
        n, h, e, v = ozet(L); z = _z(h, e, v)
        if abs(z) >= Z_SINYAL:
            cur = A["bk_en_olasi"].get("olcek", 1.0); yeni = round(cur * (1.1 if z < 0 else 0.9), 3)
            C.append({"anahtar": f"bk_olcek:{yeni}", "tur": "bk_olcek", "alan": "basket", "yol": ["bk_en_olasi", "olcek"], "deger": yeni, "stratejiler": ["bk_en_olasi"],
                      "sinyal": {"n": n, "tutan": int(h), "beklenen": round(e, 2), "z": round(z, 2), "kaynak": "bk_predlog (kilitli basket tahmini)"},
                      "aciklama": f"basket favori olasılığı {'fazla' if z < 0 else 'az'} güvenli → σ ölçeği {cur} → {yeni}"})
    # e) at: gece robotunun kilitli karnesi (favori kalibrasyonu) → τ (ikili/sıralı ikili/çifte)
    AK = K.jl(os.path.join(DATA, "at", "karne.json"), {}) or {}
    L = []
    for x in AK.get("kosular", []):
        if not x.get("kosudan_once", True) or not x.get("pw"): continue
        p, y = max(x["pw"], key=lambda t: t[0]); L.append((float(p), bool(y)))
    if len(L) >= 30:
        n, h, e, v = ozet(L); z = _z(h, e, v)
        if abs(z) >= Z_SINYAL:
            for s in ("at_ikili", "at_sirali_ikili", "at_cifte"):
                cur = A[s].get("tau", 1.0); yeni = round(cur * (0.9 if z < 0 else 1.1), 3)
                C.append({"anahtar": f"at_tau:{s}:{yeni}", "tur": "at_tau", "alan": "at", "yol": [s, "tau"], "deger": yeni, "stratejiler": [s],
                          "sinyal": {"n": n, "tutan": int(h), "beklenen": round(e, 2), "z": round(z, 2), "kaynak": "data/at/karne.json (kilitli at tahmini)"},
                          "aciklama": f"at favorileri {'fazla' if z < 0 else 'az'} güvenli → {s} τ {cur} → {yeni}"})
    return C


def kesif(bugun, A, var):
    """Sinyal yoksa da öğrenme dursun diye sırayla bir eşik keşfi (deneme sayacına dahil, aynı kapıdan geçer)."""
    L = []
    for s, (par, lo, hi) in ESIK.items():
        for dlt in (+.02, -.02):
            yeni = round(min(hi, max(lo, A[s][par] + dlt)), 2)
            if yeni != A[s][par]: L.append((s, par, yeni))
    if not L: return None
    for j in range(len(L)):
        s, par, yeni = L[(bugun.toordinal() + j) % len(L)]
        k = f"esik:{s}:{par}:{yeni}"
        if k not in var:
            return {"anahtar": k, "tur": "esik", "alan": "basket" if s.startswith("bk") else "futbol", "yol": [s, par], "deger": yeni, "stratejiler": [s],
                    "sinyal": {"kaynak": "keşif (sinyal yok)"}, "aciklama": f"keşif: {s} {par} {A[s][par]} → {yeni}"}
    return None


# ------------------------------------------------------------------ 2) sanal oynatma verisi
class Veri:
    def __init__(self, bugun):
        self.bugun = bugun; self.yil = bugun.year; self._fb = self._bk = self._at = None

    def fb(self):
        if self._fb is None:
            S = K.jl(os.path.join(DATA, "season.json"), {}) or {}
            P = (K.jl(os.path.join(DATA, "model.json"), {}) or {}).get("params", {})
            PK = K.jl(os.path.join(DATA, "pazar_karne.json"), {}) or {}
            R, PZ = K.gecmis_pz(S, P, PK, f"{self.yil}-01-01", self.bugun.isoformat(), aylik=True)
            gun = collections.defaultdict(list); son = {}
            for t, r in enumerate(R):
                key = f"{r['lg']}|{r['d']}|{r['h']}|{r['a']}|{t}"
                gun[r["d"]].append((key, r["lg"], {c: float(PZ[c][t]) for c in PZ}, r["odds"], r["ou"]))
                son[key] = (r["ft"], r["ht"])
            self._fb = (dict(sorted(gun.items())), son, K.uygun_pazarlar(PK), R, PZ)
        return self._fb

    def bk(self):
        if self._bk is None:
            import basket as BK
            store = K.jl(os.path.join(DATA, "bk_games.json"), {}) or {}; BJ = K.jl(os.path.join(DATA, "basket.json"), {}) or {}
            gun = collections.defaultdict(list); son = {}
            for lg, st in store.items():
                L = BJ.get("leagues", {}).get(lg)
                if not L: continue
                ks = L.get("kscale", 1.0)
                for g, ph, pa in BK.backtest(st.get("g", []), L["params"], 200 if lg in ("ncaa", "ncaaw") else 80):
                    if g["dt"][:4] != str(self.yil): continue
                    ph, pa = ((ph + pa) + ks * (ph - pa)) / 2, ((ph + pa) - ks * (ph - pa)) / 2
                    d = K.zaman(g["dt"]).astimezone(K.TR).date().isoformat()
                    gun[d].append((g["id"], lg, ph, pa, L.get("sm") or 12.0)); son[g["id"]] = (g["hs"], g["as_"])
            self._bk = (dict(sorted(gun.items())), son)
        return self._bk

    def at(self):
        if self._at is None:
            R = K.jl(os.path.join(DATA, "at", "replay_kosular.json"), {}) or {}
            by = collections.defaultdict(list)
            for k in R.get("kosular", []):
                if k["t"][:4] == str(self.yil): by[k["t"]].append(k)
            self._at = dict(sorted(by.items()))
        return self._at


def _bol(gunler):
    g = sorted(gunler); c = g[int(len(g) * 2 / 3)] if g else ""
    return [d for d in g if d < c], [d for d in g if d >= c]


# ------------------------------------------------------------------ oynatıcılar: gün -> istatistik
def oyna_fb(V, A, stratejiler, gunler=None):
    import pazar as PZM
    G, son, uyg, _, _ = V.fb()
    out = {}
    for d, L in G.items():
        if gunler is not None and d not in gunler: continue
        M = [K.fb_mac(k, lg, lg, "", "", d + "T12:00Z", pz, od, ou, None, None, A) for k, lg, pz, od, ou in L]
        KK = K.fb_kuponlar(M, A, uyg, yalniz=stratejiler)
        st = {"k": collections.defaultdict(list), "b": collections.defaultdict(list), "guclu": []}
        for s, KL in KK.items():
            for Kp in KL:
                hs = [PZM.outcome(b["kod"], *son[b["mac"]]) for b in Kp["bacaklar"]]
                if any(h is None for h in hs): continue
                st["k"][s].append((Kp["p"], all(hs)))
                for b, h in zip(Kp["bacaklar"], hs): st["b"][s].append((b["p"], h))
        for m in M:   # güçlü (≥%70) öneri isabeti: koruma ölçütü
            if m["lg"] in set(A.get("lig_dis") or []): continue
            r = K.rec(m)
            if r and r["p"] >= .70:
                h = PZM.outcome(r["kod"], *son[m["mac"]])
                if h is not None: st["guclu"].append((r["p"], h))
        out[d] = st
    return out


def oyna_bk(V, A, gunler=None):
    G, son = V.bk(); out = {}; o = A["bk_en_olasi"].get("olcek", 1.0)
    for d, L in G.items():
        if gunler is not None and d not in gunler: continue
        M = [K.bk_mac(i, lg, lg, "", "", d + "T12:00Z", ph, pa, sm, o) for i, lg, ph, pa, sm in L]
        st = {"k": collections.defaultdict(list), "b": collections.defaultdict(list), "guclu": [], "ll": []}
        for m in M:
            r = son[m["mac"]]; h = (r[0] > r[1]) if m["kod"] == "1" else (r[1] > r[0])
            st["ll"].append(-math.log(max(m["p"] if h else 1 - m["p"], 1e-9)))
        for Kp in K.bk_kuponlar(M, A)["bk_en_olasi"]:
            hs = [(son[b["mac"]][0] > son[b["mac"]][1]) if b["kod"] == "1" else (son[b["mac"]][1] > son[b["mac"]][0]) for b in Kp["bacaklar"]]
            st["k"]["bk_en_olasi"].append((Kp["p"], all(hs)))
            for b, h in zip(Kp["bacaklar"], hs): st["b"]["bk_en_olasi"].append((b["p"], h))
        out[d] = st
    return out


def oyna_at(V, A, stratejiler, gunler=None):
    out = {}
    for d, L in V.at().items():
        if gunler is not None and d not in gunler: continue
        ks = [{"kosu_id": k["id"], "hipodrom": k["h"], "kosu": k["k"], "saat": None, "bas_utc": None, "atlar": [(a[0], "", a[1]) for a in k["a"]]} for k in L]
        son = {}
        for k in L:
            pos = sorted([a for a in k["a"] if a[3] is not None], key=lambda a: a[3])
            son[k["id"]] = {"sira": [a[0] for a in pos[:4]], "derece": [a[3] for a in pos[:4]], "ekuri": k.get("e") or []}
        KK = K.at_kuponlar(ks, A, oran_mi=False)
        st = {"k": collections.defaultdict(list), "b": collections.defaultdict(list), "guclu": []}
        for s in stratejiler + ["at_altin"]:
            for Kp in KK.get(s, []):
                hs = [K.at_bacak_tuttu(b, son.get(b["kosu_id"])) for b in Kp["bacaklar"]]
                if any(h is None for h in hs): continue
                if s == "at_altin": st["guclu"].append((Kp["p"], all(hs)))
                else: st["k"][s].append((Kp["p"], all(hs)))
        out[d] = st
    return out


# ------------------------------------------------------------------ ölçüt ve bootstrap
def _topla(S, gunler, ss, alan="k"):
    """gün -> (tutan, n, Σp, Σ(p−y)²) seçilen stratejiler için."""
    out = {}
    for d in gunler:
        st = S.get(d)
        L = [x for s in ss for x in st[alan].get(s, [])] if st else []
        out[d] = (sum(1 for x in L if x[1]), len(L), sum(x[0] for x in L), sum((x[0] - x[1]) ** 2 for x in L))
    return out


def boot_alt(gunler, f, alfa):
    """f(gün indeks dizisi) -> fark (iyileşme > 0). Dönüş: (nokta, alt sınır, B)."""
    g = np.arange(len(gunler))
    if len(g) < 5: return None, None, 0
    nokta = f(g)
    vals = np.array([f(RNG.choice(g, len(g), replace=True)) for _ in range(B_BOOT)])
    vals = vals[np.isfinite(vals)]
    if len(vals) < B_BOOT // 2: return nokta, None, len(vals)
    if alfa * len(vals) >= 5: lo = float(np.quantile(vals, alfa))
    else:
        from statistics import NormalDist
        lo = float(vals.mean() - NormalDist().inv_cdf(1 - alfa) * vals.std(ddof=1))
    return nokta, lo, len(vals)


def oran_farki(Tb, Tc, gunler):
    """İsabet oranı farkı (aday − taban), gün bootstrap'ı için."""
    hb = np.array([Tb[d][0] for d in gunler], float); nb = np.array([Tb[d][1] for d in gunler], float)
    hc = np.array([Tc[d][0] for d in gunler], float); nc = np.array([Tc[d][1] for d in gunler], float)
    def f(ix):
        a, b = nc[ix].sum(), nb[ix].sum()
        return (hc[ix].sum() / a - hb[ix].sum() / b) if a > 0 and b > 0 else np.nan
    return f


def brier_farki(Tb, Tc, gunler):
    """Brier iyileşmesi (taban − aday) / bacak, gün bootstrap'ı."""
    bb = np.array([Tb[d][3] for d in gunler]); nb = np.array([Tb[d][1] for d in gunler], float)
    bc = np.array([Tc[d][3] for d in gunler]); nc = np.array([Tc[d][1] for d in gunler], float)
    def f(ix):
        a, b = nc[ix].sum(), nb[ix].sum()
        return (bb[ix].sum() / b - bc[ix].sum() / a) if a > 0 and b > 0 else np.nan
    return f


def _oz(T, gunler):
    h = sum(T[d][0] for d in gunler); n = sum(T[d][1] for d in gunler); e = sum(T[d][2] for d in gunler)
    return {"n": n, "tutan": h, "isabet": r4(h / n) if n else None, "beklenen": round(e, 2), "brier": r4(sum(T[d][3] for d in gunler) / n) if n else None}


# ------------------------------------------------------------------ 3) kapı
def sina(c, V, J, A, m_deneme, gunler_filtre=None):
    """Aday c'yi taban ayarla karşılaştır. Dönüş: kayıt sözlüğü (karar alanı dahil)."""
    alfa = ALFA / max(1, m_deneme)
    Ab = A
    # pazar düzeltmesi: Platt seçim diliminde öğrenilir (yalnız o koddaki tüm maçlarla)
    if c["tur"] == "pazar":
        import pazar as PZM
        G, son, uyg, R, PZ = V.fb()
        secim, _ = _bol(G.keys())
        kod = c["yol"][-1]
        ix = [t for t, r in enumerate(R) if r["d"] in set(secim)]
        y = np.array([np.nan if (v := PZM.outcome(kod, R[t]["ft"], R[t]["ht"])) is None else float(v) for t in ix])
        p = np.array([PZ[kod][t] for t in ix]); ok = ~np.isnan(y) & np.isfinite(p)
        if ok.sum() < 300:
            return {"karar": "veri_yetersiz", "neden": f"seçim diliminde {int(ok.sum())} maç (<300)"}
        c["deger"] = PZM.fit_platt(p[ok], y[ok])
    Jc = aday_ayar(J, c["yol"], c["deger"]); Ac = K.ayar_yukle(Jc)
    ss = c["stratejiler"]
    if c["alan"] == "futbol":   # Altın her zaman oynatılır (koruma ölçütü)
        ss_o = sorted(set(ss) | {"fb_altin"})
        Sb, Sc = oyna_fb(V, Ab, ss_o, gunler_filtre), oyna_fb(V, Ac, ss_o, gunler_filtre)
    elif c["alan"] == "basket":
        Sb, Sc = oyna_bk(V, Ab, gunler_filtre), oyna_bk(V, Ac, gunler_filtre)
    else:
        Sb, Sc = oyna_at(V, Ab, ss, gunler_filtre), oyna_at(V, Ac, ss, gunler_filtre)
    gun = sorted(set(Sb) | set(Sc))
    for d in gun:
        Sb.setdefault(d, None); Sc.setdefault(d, None)
    secim, sinama = (_bol(gun) if gunler_filtre is None else ([], gun))
    kb, kc = _topla(Sb, gun, ss), _topla(Sc, gun, ss)
    bb, bc = _topla(Sb, gun, ss, "b"), _topla(Sc, gun, ss, "b")
    alt_b = _topla(Sb, gun, ["fb_altin"], "b") if c["alan"] == "futbol" else None
    alt_c = _topla(Sc, gun, ["fb_altin"], "b") if c["alan"] == "futbol" else None
    def _g(S_, d):
        L = (S_[d] or {}).get("guclu", [])
        return (sum(1 for x in L if x[1]), len(L), sum(x[0] for x in L), sum((x[0] - x[1]) ** 2 for x in L))
    gb = {d: _g(Sb, d) for d in gun}; gc = {d: _g(Sc, d) for d in gun}
    kalibre = c["tur"] in ("pazar", "bk_olcek", "at_tau")
    # ölçüt: eşik/lig → kupon isabet oranı; kalibrasyon türleri → bacak (basket: tüm maçlar log-kaybı) Brier/LL
    if c["alan"] == "basket" and c["tur"] == "bk_olcek":
        lb = {d: (0, len((Sb[d] or {}).get("ll", [])), 0, sum((Sb[d] or {}).get("ll", []))) for d in gun}
        lc = {d: (0, len((Sc[d] or {}).get("ll", [])), 0, sum((Sc[d] or {}).get("ll", []))) for d in gun}
        Ob, Oc, fn, ad = lb, lc, brier_farki, "log-kaybı iyileşmesi (tüm maçlar)"
    elif kalibre:
        Ob, Oc, fn, ad = (kb, kc, brier_farki, "kupon Brier iyileşmesi") if c["alan"] == "at" else (bb, bc, brier_farki, "bacak Brier iyileşmesi")
    else:
        Ob, Oc, fn, ad = kb, kc, oran_farki, "kupon isabet oranı farkı"
    sec_n = fn(Ob, Oc, secim)(np.arange(len(secim))) if secim else None
    nokta, alt, B = boot_alt(sinama, fn(Ob, Oc, sinama), alfa)
    rap = {"olcut": ad, "alfa": r4(alfa), "deneme_no": m_deneme,
           "secim": {"gun": [secim[0], secim[-1]] if secim else None, "fark": r4(sec_n) if sec_n is not None and np.isfinite(sec_n) else None,
                     "taban": _oz(kb, secim), "aday": _oz(kc, secim)},
           "sinama": {"gun": [sinama[0], sinama[-1]] if sinama else None, "fark": r4(nokta) if nokta is not None and np.isfinite(nokta) else None,
                      "alt_sinir": r4(alt), "bootstrap_B": B, "taban": _oz(kb, sinama), "aday": _oz(kc, sinama),
                      "bacak_taban": _oz(bb, sinama), "bacak_aday": _oz(bc, sinama)}}
    kor = {}
    if alt_b:
        kor["altin_taban"], kor["altin_aday"] = _oz(alt_b, sinama), _oz(alt_c, sinama)
    if any(gb[d][1] for d in sinama):
        kor["guclu_taban"], kor["guclu_aday"] = _oz(gb, sinama), _oz(gc, sinama)
    rap["koruma"] = kor
    neden = []
    nb_, nc_ = sum(kb[d][1] for d in sinama), sum(kc[d][1] for d in sinama)
    if gunler_filtre is None and (sec_n is None or not np.isfinite(sec_n) or sec_n <= 0): neden.append("seçim diliminde iyileşme yok")
    if nb_ < 20: neden.append(f"sınamada taban kupon sayısı az ({nb_})")
    if nc_ < 0.7 * nb_: neden.append(f"kupon sayısı %70'in altına indi ({nc_}/{nb_})")
    if alt is None or not np.isfinite(alt) or alt <= 0: neden.append(f"sınama alt sınırı ≤ 0 (α={alfa:.4f})")
    for k_ in ("altin", "guclu"):
        tb, ta = kor.get(k_ + "_taban"), kor.get(k_ + "_aday")
        if tb and ta and tb["n"] >= 20 and ta["isabet"] is not None and tb["isabet"] is not None and ta["isabet"] < tb["isabet"] - 1e-9:
            neden.append(f"{'Altın' if k_ == 'altin' else 'güçlü'} isabeti düştü ({tb['isabet']} → {ta['isabet']})")
    rap["karar"] = "kabul" if not neden else "ret"
    rap["neden"] = "; ".join(neden) if neden else "tüm kapılar geçildi"
    return rap


# ------------------------------------------------------------------ 4–5) uygulama, izleme, geri alma
def uygula(J, c, bugun):
    yol = c["yol"]; once = al(J.get("params", {}), yol, "__yok__")
    koy(J.setdefault("params", {}), yol, c["deger"])
    n = len(J.get("gecmis", [])) + 1
    J["surum"] = f"{bugun.isoformat()}.{n}"
    J.setdefault("izlenen", []).append({"anahtar": c["anahtar"], "anahtar_yol": yol, "onceki": once, "yeni": c["deger"], "stratejiler": c["stratejiler"],
                                        "alan": c["alan"], "tur": c["tur"], "kabul_tarihi": bugun.isoformat(),
                                        "yeniden_sinama": (bugun + timedelta(days=IZLEME)).isoformat()})
    J.setdefault("gecmis", []).append({"tarih": bugun.isoformat(), "olay": "kabul", "anahtar": c["anahtar"], "yol": yol, "onceki": once, "yeni": c["deger"]})


def golge_karsilastir(iz):
    """Canlı gölge kuponlar: kabulden sonraki günlerde aynı strateji için gerçek (yeni ayar) ve gölge (önceki ayar) kuponları."""
    gb, gc = [0, 0, 0.0], [0, 0, 0.0]
    for f in sorted(os.listdir(K.KDIR)) if os.path.isdir(K.KDIR) else []:
        if not f.endswith(".json") or f[:10] < iz["kabul_tarihi"]: continue
        D = K.jl(os.path.join(K.KDIR, f), {}) or {}
        if D.get("geriye_donuk"): continue
        for sp in ("futbol", "basket"):
            for Kp in (D.get(sp) or {}).get("kuponlar", []):
                if Kp["strateji"] in iz["stratejiler"] and Kp.get("durum") in ("tuttu", "tutmadi"):
                    gc[0] += int(Kp["tuttu"]); gc[1] += 1; gc[2] += (Kp["p"] - Kp["tuttu"]) ** 2
            for Kp in ((D.get("golge") or {}).get(sp) or {}).get("kuponlar", []):
                if Kp["strateji"] in iz["stratejiler"] and Kp.get("durum") in ("tuttu", "tutmadi"):
                    gb[0] += int(Kp["tuttu"]); gb[1] += 1; gb[2] += (Kp["p"] - Kp["tuttu"]) ** 2
    return {"yeni": {"n": gc[1], "tutan": gc[0], "brier": r4(gc[2] / gc[1]) if gc[1] else None},
            "golge_onceki": {"n": gb[1], "tutan": gb[0], "brier": r4(gb[2] / gb[1]) if gb[1] else None}}


def yeniden_sina(J, iz, V, bugun, rb):
    """Kabulden sonraki günler: sanal oynatma (önceki ↔ yeni) + canlı gölge. Kötüleşme → geri al."""
    Ay = K.ayar_yukle(J); Jo = aday_ayar(J, iz["anahtar_yol"], iz["onceki"]); Ao = K.ayar_yukle(Jo)
    yeni_gun = None
    if iz["alan"] == "futbol": G = V.fb()[0]
    elif iz["alan"] == "basket": G = V.bk()[0]
    else: G = V.at()
    yeni_gun = [d for d in G if d >= iz["kabul_tarihi"]]
    ss = iz["stratejiler"]
    if iz["alan"] == "futbol": Sb, Sc = oyna_fb(V, Ao, ss, set(yeni_gun)), oyna_fb(V, Ay, ss, set(yeni_gun))
    elif iz["alan"] == "basket": Sb, Sc = oyna_bk(V, Ao, set(yeni_gun)), oyna_bk(V, Ay, set(yeni_gun))
    else: Sb, Sc = oyna_at(V, Ao, ss, set(yeni_gun)), oyna_at(V, Ay, ss, set(yeni_gun))
    gun = sorted(set(Sb) | set(Sc))
    for d in gun: Sb.setdefault(d, None); Sc.setdefault(d, None)
    kb, kc = _topla(Sb, gun, ss), _topla(Sc, gun, ss)
    ob, oc = _oz(kb, gun), _oz(kc, gun)
    canli = golge_karsilastir(iz)
    kotu = []
    if ob["n"] >= 15 and oc["n"] and ob["isabet"] is not None and oc["isabet"] is not None:
        if iz["tur"] in ("pazar", "bk_olcek", "at_tau"):
            if oc["brier"] > ob["brier"] + 0.002: kotu.append(f"sanal oynatma Brier {ob['brier']} → {oc['brier']}")
        elif oc["isabet"] < ob["isabet"] - 0.02: kotu.append(f"sanal oynatma isabet {ob['isabet']} → {oc['isabet']}")
    cy, cg = canli["yeni"], canli["golge_onceki"]
    if cy["n"] >= 10 and cg["n"] >= 10 and cy["tutan"] / cy["n"] < cg["tutan"] / cg["n"] - 0.05 and (cy["brier"] or 0) > (cg["brier"] or 0):
        kotu.append(f"canlı gölge: yeni {cy['tutan']}/{cy['n']} < önceki {cg['tutan']}/{cg['n']}")
    kayit = {"tarih": bugun.isoformat(), "anahtar": iz["anahtar"], "tur": "yeniden_sinama", "kabulden_sonra_gun": len(gun),
             "sanal": {"onceki": ob, "yeni": oc}, "canli_golge": canli}
    yeterli = ob["n"] >= 15 or (cy["n"] >= 10 and cg["n"] >= 10)
    if kotu:
        koy(J["params"], iz["anahtar_yol"], iz["onceki"])
        J["surum"] = f"{bugun.isoformat()}.geri{len(J.get('gecmis', [])) + 1}"
        J.setdefault("gecmis", []).append({"tarih": bugun.isoformat(), "olay": "geri_alindi", "anahtar": iz["anahtar"], "yol": iz["anahtar_yol"],
                                          "onceki": iz["yeni"], "yeni": iz["onceki"], "neden": "; ".join(kotu)})
        rb["aktif"] = True; rb["baslangic"] = bugun.isoformat(); rb["bitis"] = (bugun + timedelta(days=BEKLEME)).isoformat()
        rb["neden"] = f"{iz['kabul_tarihi']} tarihli OXX değişikliği ({iz['anahtar']}) sonrası kötüleşme: " + "; ".join(kotu)
        rb["params"] = {"/".join(iz["anahtar_yol"]): iz["onceki"]}
        rb.setdefault("donmus", {})[iz["anahtar"]] = rb["bitis"]
        rb["gecmis"] = (rb.get("gecmis") or [])[-10:] + [iz["anahtar"]]
        kayit["karar"] = "GERİ ALINDI"; kayit["neden"] = "; ".join(kotu); return "geri", kayit
    if not yeterli and iz.get("uzatma", 0) < 2:
        iz["uzatma"] = iz.get("uzatma", 0) + 1; iz["yeniden_sinama"] = (bugun + timedelta(days=7)).isoformat()
        kayit["karar"] = "uzatıldı"; kayit["neden"] = "kabulden sonra yeterli veri yok, 7 gün daha izlenecek"; return "uzat", kayit
    J.setdefault("gecmis", []).append({"tarih": bugun.isoformat(), "olay": "kalici", "anahtar": iz["anahtar"]})
    kayit["karar"] = "kalıcı"; kayit["neden"] = "kötüleşme yok" if yeterli else "yeterli veri yok, kabul"
    return "kalici", kayit


# ------------------------------------------------------------------ ana
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--kuru", action="store_true"); ap.add_argument("--bugun", default=None)
    ar = ap.parse_args()
    bugun = date.fromisoformat(ar.bugun) if ar.bugun else datetime.now(K.TR).date()
    J = K.jl(K.AYAR, None) or {"v": 1, "surum": "varsayilan", "aciklama": "OXX kupon stratejilerinin öğrenilmiş ayarları (yalnız varsayılandan farklı olanlar). "
                                "Yazar: lab/oxx_ogren.py. Okur: scripts/oxx_kupon.py. Motorun model.json ayarlarına dokunulmaz.",
                                "params": {}, "izlenen": [], "gecmis": []}
    A = K.ayar_yukle(J)
    Q = K.jl(KUYRUK, {}) or {"adaylar": []}
    GL = K.jl(GUNLUK, {}) or {"v": 1, "sayac": {}, "kayitlar": []}
    rb = K.jl(OXX_RB, {}) or {"aktif": False, "gecmis": []}
    if rb.get("aktif") and rb.get("bitis", "") < bugun.isoformat(): rb = {"aktif": False, "gecmis": rb.get("gecmis", []), "donmus": rb.get("donmus", {})}
    rb["donmus"] = {k: v for k, v in (rb.get("donmus") or {}).items() if v >= bugun.isoformat()}
    grb = K.jl(os.path.join(DATA, "rollback.json"), {}) or {}
    donuk = bool(grb.get("aktif"))
    V = Veri(bugun)
    kayitlar = []
    # 5) yeniden sınama (öncelikli)
    kalan_iz = []
    for iz in J.get("izlenen", []):
        if iz["yeniden_sinama"] <= bugun.isoformat() and kalan() > 60:
            try:
                s, kay = yeniden_sina(J, iz, V, bugun, rb); kayitlar.append(kay)
                if s == "uzat": kalan_iz.append(iz)
            except Exception as e:
                kalan_iz.append(iz); kayitlar.append({"tarih": bugun.isoformat(), "anahtar": iz["anahtar"], "tur": "yeniden_sinama", "karar": "hata", "neden": repr(e)[:200]})
        else:
            kalan_iz.append(iz)
    J["izlenen"] = kalan_iz
    A = K.ayar_yukle(J)
    # 1) sinyaller → kuyruk
    var = {a["anahtar"]: a for a in Q.get("adaylar", [])}
    son_ret = {k["anahtar"]: k["tarih"] for k in GL.get("kayitlar", []) if k.get("karar") in ("ret", "veri_yetersiz")}
    yeni = 0
    for c in sinyaller(bugun, A):
        r = son_ret.get(c["anahtar"]); o = var.get(c["anahtar"])
        if (o and o["durum"] == "bekliyor") or (r and (bugun - date.fromisoformat(r)).days < BEKLEME): continue
        if o and o.get("sonuc") == "kabul" and al((J.get("params") or {}), c["yol"]) == c.get("deger"): continue
        c.update({"eklenme": bugun.isoformat(), "durum": "bekliyor", "oncelik": round(abs(c["sinyal"].get("z") or 0), 2)})
        var[c["anahtar"]] = c; yeni += 1
    bek = [a for a in var.values() if a["durum"] == "bekliyor"]
    if len(bek) < N_GECE:
        k_ = kesif(bugun, A, {k for k, a in var.items() if a["durum"] == "bekliyor"} | {k for k, t in son_ret.items() if (bugun - date.fromisoformat(t)).days < BEKLEME})
        if k_:
            k_.update({"eklenme": bugun.isoformat(), "durum": "bekliyor", "oncelik": 0.0}); var[k_["anahtar"]] = k_; yeni += 1
    # 2–3) gecelik sınama: en fazla N aday, öncelik sırasıyla
    sira = sorted([a for a in var.values() if a["durum"] == "bekliyor"], key=lambda a: (-a["oncelik"], a["eklenme"]))
    # gecelik sınır: iş akışı günde iki kez çalışsa da aynı gün en fazla N aday sınanır (aynı veriyle sınırsız deneme yok)
    hak = N_GECE - sum(1 for k in GL.get("kayitlar", []) if k.get("tarih") == bugun.isoformat() and k.get("tur") != "yeniden_sinama"
                       and k.get("karar") in ("kabul", "ret", "dondurulmus", "veri_yetersiz"))
    denenen = 0
    for c in sira:
        if denenen >= hak or kalan() < 45: break
        alan_k = f"{c['alan']}-{bugun.year}"
        m = GL["sayac"].get(alan_k, 0) + 1
        t1 = time.time()
        try:
            rap = sina(c, V, J, A, m)
        except Exception as e:
            rap = {"karar": "hata", "neden": repr(e)[:300]}
        if rap.get("karar") in ("kabul", "ret"): GL["sayac"][alan_k] = m
        if rap.get("karar") == "kabul":
            if donuk: rap["karar"], rap["neden"] = "dondurulmus", "koruyucu geri alma aktif (data/rollback.json); kabul edilmedi"
            elif c["anahtar"] in (rb.get("donmus") or {}): rap["karar"], rap["neden"] = "dondurulmus", "bu anahtar OXX geri alma süresinde"
        uyg = rap.get("karar") == "kabul"
        if uyg: uygula(J, c, bugun); A = K.ayar_yukle(J)
        kayitlar.append(dict({"tarih": bugun.isoformat(), "anahtar": c["anahtar"], "tur": c["tur"], "alan": c["alan"], "aciklama": c.get("aciklama"),
                              "sinyal": c.get("sinyal"), "deger": c.get("deger"), "uygulandi": uyg, "sure_sn": round(time.time() - t1, 1)}, **rap))
        c["durum"] = "denendi"; c["son_deneme"] = bugun.isoformat(); c["sonuc"] = rap.get("karar"); denenen += 1
        print(f"OXX öğrenme: {c['anahtar']} → {rap.get('karar')} ({rap.get('neden')})", flush=True)
    Q["adaylar"] = sorted(var.values(), key=lambda a: (a["durum"] != "bekliyor", -a.get("oncelik", 0)))[-200:]
    Q["guncelleme"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    Q["aciklama"] = ("OXX öğrenme döngüsünün deney adayları: kilitli kupon/tahmin günlüklerinde beklenti ile gerçek arasındaki sistematik "
                     "farklardan (|z| ≥ 1,5; öncelik |z|) otomatik üretilir; her gece en fazla " + str(N_GECE) + " aday sınanır.")
    GL["kayitlar"] = (GL.get("kayitlar", []) + kayitlar)[-300:]
    GL["guncelleme"] = Q["guncelleme"]
    GL["kurallar"] = {"gecelik_aday": N_GECE, "secim_sinama": "günler 2/3 seçim, 1/3 sınama (ileriye dönük sanal oynatma, bu yılın maçları)",
                      "bootstrap": f"eşleştirilmiş gün bootstrap B={B_BOOT}, tek yanlı alt sınır > 0", "alfa": "0,05 / m (m = o alanda bu yıl yapılan sınama sayısı; Bonferroni)",
                      "koruma": "Altın ve güçlü (≥%70) bacak isabeti düşmez; kupon sayısı ≥ tabanın %70'i",
                      "yeniden_sinama": f"{IZLEME} gün sonra kabulden sonraki günlerle + canlı gölge kuponlarla; kötüleşirse geri alınır, anahtar {BEKLEME} gün dondurulur",
                      "dondurma": "koruyucu (data/rollback.json) aktifken kabul yok"}
    GL["ozet"] = {"bu_gece": collections.Counter(k.get("karar") for k in kayitlar), "kuyruk_bekleyen": sum(1 for a in Q["adaylar"] if a["durum"] == "bekliyor"),
                  "ayar_surum": J.get("surum"), "izlenen": [i["anahtar"] for i in J.get("izlenen", [])], "sure_sn": round(time.time() - T0, 1)}
    print(f"OXX öğrenme: {yeni} yeni aday, {denenen} sınandı, {round(time.time() - T0, 1)} sn; ayar {J.get('surum')}", flush=True)
    if ar.kuru:
        print(json.dumps(kayitlar, ensure_ascii=False, indent=1)[:4000]); return
    J.setdefault("aciklama", "OXX kupon stratejilerinin öğrenilmiş ayarları"); K.jw_degisince(K.AYAR, J, haric=(), indent=1)
    K.jw(KUYRUK, Q); K.jw(GUNLUK, GL)
    rb.setdefault("aciklama", "OXX öğrenme döngüsünün geri alma kaydı (rollback.json kalıbı); aktifken 'donmus' anahtarlar yeniden kabul edilmez.")
    K.jw(OXX_RB, rb)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback; traceback.print_exc(); print("OXX öğrenme döngüsü bu gece atlandı")
