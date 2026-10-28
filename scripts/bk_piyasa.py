#!/usr/bin/env python3
"""🏀📈 Basket piyasa çapası ve piyasa karnesi (denetim U8, 2026-10-27).

Ne yapar:
  1) Ölçüm. Kilitli basket tahminlerinde (data/bk_predlog.json) maç başlamadan önceki son piyasa anlık görüntüsü (`pz`) tutulur:
     iddaa MS (2 yollu, uzatma dahil), iddaa handikap (varsa), iddaa alt/üst ve ESPN çizgisi (spread, toplam). Marj ayrılır
     (Shin; karşılaştırma için power). Piyasa olasılığı model ile AYNI maçlarda, ileriye dönük karşılaştırılır: LL, Brier, isabet.
  2) Harman. Benter tarzı iki aşama, lig grubuna göre (pro / avrupa / kolej):
        logit p = a·logit p_model + b·logit p_piyasa
     a, b yalnız o günden ÖNCE sonuçlanmış maçlarla öğrenilir (zaman sıralı), ön bilgiye (A0, B0) doğru L2 küçültmeli.
     Skor dağılımı: handikap çizgisinden (yoksa MS olasılığından) beklenen sayı farkı, alt/üst çizgisinden beklenen toplam
     türetilir; model yolunun fark ve toplamı bunlara w_m, w_t ağırlığıyla çapalanır (ağırlıklar yine zaman sıralı öğrenilir).
  3) Kapı. Gün blokları bootstrap'ı (B=2000) ile %95 güven aralığı. Grup kapısı: n ≥ KAPI_N maç, ≥ KAPI_GUN gün,
     ΔLL (harman − model) GA üst sınırı < 0, ΔBrier < 0, isabet düşmez. Geçen grup yalnız ADAY olur: lab/oxx_ogren.py
     sinyali (tur "bk_piyasa") ve lab/surekli_deney.py gölge ölçümü (en az 3 gün) sonrası data/oxx_ayar.json
     params.bk_piyasa.<grup> = true yazılınca üretime girer. O zamana kadar harman yalnız gölgede ölçülür.
     Üretimde 14 gün izlenir (lab/oxx_ogren.yeniden_sina); kötüleşirse bayrak false olur ve bekleyen maçlardaki cp silinir.
     Alfa yatırımı servetinde piyasa çapası kendi ailesindedir ("bk_piyasa-<yıl>"): kör eşik keşifleri onu tüketemez.
  5) Gölge kaydı (2026-10-28). Her canlı (başlamamış, piyasalı) kilitli maçta harmansız / harmanlı / çapalı olasılık o anki
     ağırlıklarla e["pg"]'ye yazılır (maç başlayana dek tazelenir). Karne bunu "canli_golge" olarak ölçer; veri birikip
     kapı geçince harman kendiliğinden üretime girer.
  4) Karne. Her basket çalışmasında data/bk_piyasa.json yeniden yazılır (günlük satır tarihe göre güncellenir).
Ağ gerektirmez; yalnız yerel dosyalarla çalışır.
  python3 scripts/bk_piyasa.py           # karneyi yeniden üret
"""
import json, math, os, sys
from datetime import datetime, timezone, timedelta
from statistics import NormalDist

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
KARNE = os.path.join(DATA, "bk_piyasa.json")
AYAR = os.path.join(DATA, "oxx_ayar.json")
SURUM = "2026-10-28.1"
N = NormalDist()

GRUP = {"nba": "pro", "wnba": "pro", "gl": "pro", "nbl": "pro", "el": "avrupa", "ec": "avrupa", "ncaa": "kolej", "ncaaw": "kolej"}
GRUP_AD = {"pro": "NBA · WNBA · G League · NBL", "avrupa": "EuroLeague · EuroCup", "kolej": "NCAA erkek · kadın"}
# Benter ön bilgisi: literatürde kapanış çizgisi en güçlü tahminci (b büyük); veri azken harman buna yakın durur.
A0, B0, LAM_AB = 0.3, 0.7, 40.0            # λ: ön bilginin gücü (maç eşdeğeri, logit ölçeğinde)
W0_M, W0_T, LAM_W = 0.6, 0.6, 40.0         # fark / toplam çapa ağırlığı ön bilgisi
KAPI_N, KAPI_GUN, B_BOOT = 150, 20, 2000
URETIM_W = 0.5                              # istemcinin bugünkü ESPN karışımı (basket.json market.w varsayılanı)
RNG = np.random.default_rng(20261027)
TR = timezone(timedelta(hours=3))


def jl(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def r4(x):
    return None if x is None or not np.isfinite(x) else round(float(x), 4)


def phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def logit(p):
    p = min(max(p, 1e-4), 1 - 1e-4); return math.log(p / (1 - p))


def sig(z): return 1 / (1 + math.exp(-z))


# ------------------------------------------------------------------ marj ayırma
def devig_power(odds):
    """Power yöntemi: Σ (1/o_i)^k = 1."""
    q = [1 / o for o in odds if o and o > 1]
    if len(q) != len(odds): return None
    lo, hi = 0.5, 3.0
    for _ in range(60):
        k = (lo + hi) / 2
        if sum(x ** k for x in q) > 1: lo = k
        else: hi = k
    p = [x ** ((lo + hi) / 2) for x in q]; s = sum(p)
    return [x / s for x in p]


def devig_shin(odds):
    """Shin (1993), iki ve çok yollu: p_i = (√(z² + 4(1−z) q_i²/S) − z) / (2(1−z)), Σp = 1 olacak z."""
    q = [1 / o for o in odds if o and o > 1]
    if len(q) != len(odds): return None
    S = sum(q)
    if S <= 1: return [x / S for x in q]
    def pz(z): return [(math.sqrt(z * z + 4 * (1 - z) * x * x / S) - z) / (2 * (1 - z)) for x in q]
    lo, hi = 0.0, 0.4
    for _ in range(80):
        z = (lo + hi) / 2
        if sum(pz(z)) > 1: lo = z
        else: hi = z
    p = pz((lo + hi) / 2); s = sum(p)
    return [x / s for x in p]


DEVIG = {"shin": devig_shin, "power": devig_power}


# ------------------------------------------------------------------ piyasa anlık görüntüsü
def pz_al(f):
    """Fikstürden piyasa anlık görüntüsü (yalnız var olan alanlar)."""
    o = {}
    if f.get("io") and len(f["io"]) == 2: o["io"] = [float(x) for x in f["io"]]
    if f.get("itot") and len(f["itot"]) == 3: o["itot"] = [float(x) for x in f["itot"]]
    if f.get("ihnd") and len(f["ihnd"]) == 3: o["ihnd"] = [float(x) for x in f["ihnd"]]
    od = f.get("odds") if f.get("src") != "iddaa" else None
    if od and (od.get("spread") is not None or od.get("ou")):
        o["espn"] = {"spread": od.get("spread"), "ou": od.get("ou")}
    return o


def piyasa(pz, sm, st, yontem="shin"):
    """Piyasa → {p: ev kazanır, m: beklenen fark (ev − dep), t: beklenen toplam, kaynak}. Yoksa None."""
    if not pz: return None
    dv = DEVIG[yontem]; out = {"kaynak": []}
    if pz.get("io"):
        pp = dv(pz["io"])
        if pp: out["p"] = pp[0]; out["kaynak"].append("iddaa_ms")
    es = pz.get("espn") or {}
    m_ms = sm * N.inv_cdf(min(max(out["p"], 0.01), 0.99)) if "p" in out else None
    if pz.get("ihnd"):        # [çizgi, oran1, oran2]; işaret iddaa'da belirsiz → MS ile tutarlı olan seçilir
        h, o1, o2 = pz["ihnd"]; pp = dv([o1, o2])
        if pp:
            c = [s * abs(h) + sm * N.inv_cdf(min(max(pp[0], 0.01), 0.99)) for s in (1, -1)]
            ref = m_ms if m_ms is not None else (-es["spread"] if es.get("spread") is not None else None)
            mh = min(c, key=lambda x: abs(x - ref)) if ref is not None else None
            if mh is not None and abs(mh - ref) <= max(6.0, 0.5 * abs(ref)): out["m"] = mh; out["kaynak"].append("iddaa_hnd")
    if "m" not in out and es.get("spread") is not None: out["m"] = -float(es["spread"]); out["kaynak"].append("espn_spread")
    if "m" not in out and m_ms is not None: out["m"] = m_ms
    if "p" not in out and "m" in out: out["p"] = phi(out["m"] / sm)
    if pz.get("itot"):
        ln, ov, un = pz["itot"]; pp = dv([ov, un])
        if pp: out["t"] = ln + st * N.inv_cdf(min(max(pp[0], 0.01), 0.99)); out["kaynak"].append("iddaa_au")
    if "t" not in out and es.get("ou"): out["t"] = float(es["ou"]); out["kaynak"].append("espn_ou")
    return out if "p" in out else None


# ------------------------------------------------------------------ zaman sıralı öğrenme
def benter_fit(X, a0=A0, b0=B0, lam=LAM_AB):
    """X: [(logit p_model, logit p_piyasa, y)] → (a, b); L2 küçültme (a0, b0)'a doğru, Newton."""
    th = np.array([a0, b0], float)
    if not X: return float(th[0]), float(th[1])
    Z = np.array([[x[0], x[1]] for x in X]); y = np.array([x[2] for x in X], float)
    P0 = np.array([a0, b0])
    for _ in range(25):
        p = 1 / (1 + np.exp(-(Z @ th)))
        g = Z.T @ (p - y) + lam * (th - P0)
        H = (Z * (p * (1 - p))[:, None]).T @ Z + lam * np.eye(2)
        st = np.linalg.solve(H, g); th -= st
        if np.abs(st).max() < 1e-7: break
    return float(th[0]), float(th[1])


def w_fit(L, w0, lam=LAM_W):
    """L: [(model, piyasa, gerçek)] → w ∈ [0,1]: argmin Σ(y − m − w(k − m))² + λ·s²·(w − w0)², s² = ort (k − m)²."""
    if not L: return w0
    d = np.array([x[1] - x[0] for x in L]); e = np.array([x[2] - x[0] for x in L])
    s2 = max(1.0, float(np.mean(d * d)))
    return float(min(1.0, max(0.0, (np.sum(d * e) + lam * s2 * w0) / (np.sum(d * d) + lam * s2))))


def satirlar(plog, ligler):
    """Sonuçlanmış, piyasası olan kilitli tahminler → değerlendirme satırları (tarih sıralı)."""
    out = []
    for e in plog:
        r = e.get("r"); pz = e.get("pz") or ({"espn": e["odds"]} if e.get("odds") else None)
        if not r or e.get("ph") is None or not pz or r[0] == r[1]: continue
        L = ligler.get(e["lg"]) or {}
        sm, st = L.get("sm") or 12.0, L.get("st") or 18.0
        mk = piyasa(pz, sm, st, "shin")
        if not mk: continue
        mkp = piyasa(pz, sm, st, "power")
        mm, tm = e["ph"] - e["pa"], e["ph"] + e["pa"]
        es = pz.get("espn") or {}
        mu = (1 - URETIM_W) * mm + URETIM_W * (-es["spread"]) if es.get("spread") is not None and es.get("ou") else mm   # istemcinin bugünkü yolu
        out.append({"id": e["id"], "lg": e["lg"], "g": GRUP.get(e["lg"], "diger"), "gun": gun_tr(e), "y": int(r[0] > r[1]),
                    "ym": r[0] - r[1], "yt": r[0] + r[1], "sm": sm, "pm": phi(mm / sm), "pk": mk["p"], "pk_pow": mkp["p"] if mkp else mk["p"],
                    "pu": phi(mu / sm), "mm": mm, "tm": tm, "mk": mk.get("m"), "tk": mk.get("t"), "kaynak": mk["kaynak"]})
    return sorted(out, key=lambda x: (x["gun"], x["id"]))


def gun_tr(e):
    try:
        if e.get("dt"): return datetime.fromisoformat(e["dt"].replace("Z", "+00:00")).astimezone(TR).date().isoformat()
    except Exception: pass
    return e.get("d") or ""


def ileri_yuru(S):
    """Her gün yalnız ÖNCEKİ günlerin sonuçlarıyla (grup başına) a, b, w_m, w_t öğrenilir; o günün maçları harmanlanır."""
    gecmis = {}; agirlik = {}
    for d in sorted({x["gun"] for x in S}):
        bugun = [x for x in S if x["gun"] == d]
        for g in {x["g"] for x in bugun}:
            G = gecmis.get(g, [])
            a, b = benter_fit([(logit(x["pm"]), logit(x["pk"]), x["y"]) for x in G])
            wm = w_fit([(x["mm"], x["mk"], x["ym"]) for x in G if x["mk"] is not None], W0_M)
            wt = w_fit([(x["tm"], x["tk"], x["yt"]) for x in G if x["tk"] is not None], W0_T)
            agirlik[g] = {"a": a, "b": b, "w_m": wm, "w_t": wt, "n_ogrenme": len(G)}
            for x in bugun:
                if x["g"] != g: continue
                x["ph_"] = sig(a * logit(x["pm"]) + b * logit(x["pk"]))
                x["mc"] = x["mm"] + wm * (x["mk"] - x["mm"]) if x["mk"] is not None else x["mm"]
                x["tc"] = x["tm"] + wt * (x["tk"] - x["tm"]) if x["tk"] is not None else x["tm"]
                x["pc"] = phi(x["mc"] / x["sm"])       # çapalı skor dağılımından ev olasılığı
        for x in bugun: gecmis.setdefault(x["g"], []).append(x)
    return S, agirlik


# ------------------------------------------------------------------ ölçüt ve bootstrap
def _ll(p, y): return -math.log(max(p if y else 1 - p, 1e-9))


YOLLAR = {"model": "pm", "piyasa": "pk", "piyasa_power": "pk_pow", "harman": "ph_", "capali": "pc", "uretim": "pu"}


def olc(S, k):
    if not S: return None
    return {"n": len(S), "ll": r4(np.mean([_ll(x[k], x["y"]) for x in S])), "brier": r4(np.mean([(x[k] - x["y"]) ** 2 for x in S])),
            "isabet": r4(np.mean([(x[k] >= .5) == bool(x["y"]) for x in S]))}


def boot(S, f):
    """Gün blokları bootstrap'ı: f(alt küme) → değer. Dönüş (nokta, [%2,5, %97,5])."""
    gl = sorted({x["gun"] for x in S}); by = {d: [x for x in S if x["gun"] == d] for d in gl}
    nokta = f(S)
    if len(gl) < 5: return r4(nokta), None
    v = []
    for _ in range(B_BOOT):
        ix = RNG.integers(0, len(gl), len(gl)); T = [x for i in ix for x in by[gl[i]]]
        v.append(f(T))
    v = np.array(v); v = v[np.isfinite(v)]
    return r4(nokta), [r4(np.quantile(v, .025)), r4(np.quantile(v, .975))]


def fark(S, k1, k0="pm"):
    dll = boot(S, lambda T: np.mean([_ll(x[k1], x["y"]) - _ll(x[k0], x["y"]) for x in T]))
    dbr = boot(S, lambda T: np.mean([(x[k1] - x["y"]) ** 2 - (x[k0] - x["y"]) ** 2 for x in T]))
    dis = np.mean([((x[k1] >= .5) == bool(x["y"])) - ((x[k0] >= .5) == bool(x["y"])) for x in S])
    return {"ll": dll[0], "ll_ga": dll[1], "brier": dbr[0], "brier_ga": dbr[1], "isabet": r4(dis)}


def skor_olc(S):
    A = [x for x in S if x["mk"] is not None]; B = [x for x in S if x["tk"] is not None]
    o = {}
    if A:
        o["fark_mse"] = {"model": r4(np.mean([(x["ym"] - x["mm"]) ** 2 for x in A])), "piyasa": r4(np.mean([(x["ym"] - x["mk"]) ** 2 for x in A])),
                         "capali": r4(np.mean([(x["ym"] - x["mc"]) ** 2 for x in A])), "n": len(A)}
        o["fark_mse"]["capali_eksi_model"] = boot(A, lambda T: np.mean([(x["ym"] - x["mc"]) ** 2 - (x["ym"] - x["mm"]) ** 2 for x in T]))
    if B:
        o["toplam_mae"] = {"model": r4(np.mean([abs(x["yt"] - x["tm"]) for x in B])), "piyasa": r4(np.mean([abs(x["yt"] - x["tk"]) for x in B])),
                           "capali": r4(np.mean([abs(x["yt"] - x["tc"]) for x in B])), "n": len(B)}
        o["toplam_mae"]["capali_eksi_model"] = boot(B, lambda T: np.mean([abs(x["yt"] - x["tc"]) - abs(x["yt"] - x["tm"]) for x in T]))
    return o


def kapi(S, fk):
    n, gun = len(S), len({x["gun"] for x in S})
    neden = []
    if n < KAPI_N: neden.append(f"maç az ({n} < {KAPI_N})")
    if gun < KAPI_GUN: neden.append(f"gün az ({gun} < {KAPI_GUN})")
    ga = fk.get("ll_ga")
    if ga is None or ga[1] is None or ga[1] >= 0: neden.append(f"ΔLL GA üst sınırı ≥ 0 ({ga})")
    if fk.get("brier") is None or fk["brier"] >= 0: neden.append(f"ΔBrier ≥ 0 ({fk.get('brier')})")
    if fk.get("isabet") is not None and fk["isabet"] < 0: neden.append(f"isabet düştü ({fk['isabet']})")
    return {"durum": "gecti" if not neden else ("veri_az" if n < KAPI_N or gun < KAPI_GUN else "golge"),
            "neden": "; ".join(neden) if neden else "harman kapıyı geçti → OXXai gölge ölçümüne aday"}


def izleme():
    """oxx_ayar.json izlenen + gecmis içindeki bk_piyasa kayıtları (karne için)."""
    J = jl(AYAR, {}) or {}
    iz = [{k: i.get(k) for k in ("anahtar", "kabul_tarihi", "yeniden_sinama", "uzatma")} for i in J.get("izlenen", []) if i.get("tur") == "bk_piyasa"]
    gc = [g for g in J.get("gecmis", []) if str(g.get("anahtar", "")).startswith("bk_piyasa:")][-10:]
    return {"izlenen": iz, "gecmis": gc}


def golge_ve_capa(plog, ligler, PK, now_iso):
    """Başlamamış her piyasalı kilitli maç: gölge kaydı e["pg"] (harmansız pm, harmanlı ph, çapalı pc, piyasa pk) daima;
    çapalı üretim tahmini e["cp"] yalnız üretimdeki grupta. Üretimden çıkmış (geri alınmış) grupta bekleyen cp silinir.
    Dönüş: {id: cp} (basket.json fikstürüne)."""
    U = PK.get("uretimde") or {}; AG = PK.get("agirlik") or {}; cp_fx = {}
    for e in plog:
        if e.get("r") is not None or e.get("ph") is None or e.get("dt", e.get("d", ""))[:16] <= now_iso: continue
        g = GRUP.get(e["lg"]); L = ligler.get(e["lg"]) or {}
        if not U.get(g): e.pop("cp", None)
        if not e.get("pz") or not g or not AG.get(g): continue
        cp = capala(e["ph"], e["pa"], e["pz"], L, AG[g])
        if not cp: continue
        sm = L.get("sm") or 12.0; mk = piyasa(e["pz"], sm, L.get("st") or 18.0)
        e["pg"] = {"pm": round(phi((e["ph"] - e["pa"]) / sm), 4), "ph": cp["p"], "pc": round(phi((cp["ph"] - cp["pa"]) / sm), 4),
                   "pk": round(mk["p"], 4), "n": AG[g].get("n_ogrenme"), "u": bool(U.get(g)), "ts": now_iso + "Z"}
        if U.get(g): e["cp"] = cp; cp_fx[e["id"]] = cp
    return cp_fx


def canli_golge(plog):
    """Gölge kaydı olan sonuçlanmış maçlar: kayıt anındaki ağırlıklarla harmansız / harmanlı / çapalı ölçüm."""
    out = {}
    R = [e for e in plog if e.get("r") and e.get("pg") and e["r"][0] != e["r"][1]]
    for g in ["tum"] + sorted({GRUP.get(e["lg"], "diger") for e in R}):
        G = [e for e in R if g == "tum" or GRUP.get(e["lg"], "diger") == g]
        if not G: continue
        o = {"n": len(G), "gun": len({gun_tr(e) for e in G})}
        for k in ("pm", "ph", "pc", "pk"):
            ys = [(e["pg"][k], int(e["r"][0] > e["r"][1])) for e in G]
            o[k] = {"ll": r4(np.mean([_ll(p, y) for p, y in ys])), "isabet": r4(np.mean([(p >= .5) == bool(y) for p, y in ys]))}
        out[g] = o
    return out


def uretimde():
    """oxx_ayar.json params.bk_piyasa: {grup: true} (yalnız oxx_ogren / surekli_deney kapısı + gölge sonrası yazılır)."""
    P = ((jl(AYAR, {}) or {}).get("params") or {}).get("bk_piyasa") or {}
    return {g: bool(v) for g, v in P.items() if isinstance(v, bool)}


# ------------------------------------------------------------------ üretim: fikstüre çapa
def capala(ph, pa, pz, L, ag):
    """Model yolu (ph, pa) + piyasa → çapalı (ph, pa, p). ag: grup ağırlıkları."""
    sm, st = L.get("sm") or 12.0, L.get("st") or 18.0
    mk = piyasa(pz, sm, st)
    if not mk or not ag: return None
    mm, tm = ph - pa, ph + pa
    mc = mm + ag["w_m"] * (mk["m"] - mm) if mk.get("m") is not None else mm
    tc = tm + ag["w_t"] * (mk["t"] - tm) if mk.get("t") is not None else tm
    p = sig(ag["a"] * logit(phi(mm / sm)) + ag["b"] * logit(mk["p"]))
    return {"ph": round((tc + mc) / 2, 1), "pa": round((tc - mc) / 2, 1), "p": round(p, 4), "kaynak": "+".join(mk["kaynak"])}


# ------------------------------------------------------------------ karne
def kapsam(plog, fixtures, ligler=None):
    """Hangi ligde piyasa oranı var / yok. Sentetik iddaa yarışmaları: oran var, model ve sonuç kaynağı yok (ölçülemez)."""
    k = {}
    for e in plog:
        x = k.setdefault(e["lg"], {"kilitli": 0, "oranli": 0, "sonuclu_oranli": 0, "iddaa_ms": 0, "iddaa_hnd": 0, "iddaa_au": 0, "espn": 0})
        x["kilitli"] += 1; pz = e.get("pz") or ({"espn": e["odds"]} if e.get("odds") else {})
        if pz: x["oranli"] += 1
        if pz and e.get("r"): x["sonuclu_oranli"] += 1
        for a, b in (("io", "iddaa_ms"), ("ihnd", "iddaa_hnd"), ("itot", "iddaa_au"), ("espn", "espn")):
            if pz.get(a): x[b] += 1
    syn = {}
    for f in fixtures or []:
        if str(f.get("lg", "")).startswith("i"):
            ad = ((ligler or {}).get(f["lg"]) or {}).get("name") or f["lg"]; syn[ad] = syn.get(ad, 0) + 1
    return k, syn


def karne(plog=None, ligler=None, fixtures=None, yaz=True):
    BJ = jl(os.path.join(DATA, "basket.json"), {}) or {}
    plog = plog if plog is not None else (jl(os.path.join(DATA, "bk_predlog.json"), []) or [])
    ligler = ligler if ligler is not None else BJ.get("leagues", {})
    fixtures = fixtures if fixtures is not None else BJ.get("fixtures", [])
    S, ag = ileri_yuru(satirlar(plog, ligler))
    # üretim için ağırlıklar: TÜM sonuçlanmış maçlarla (bir sonraki maçlar için "önceki günler")
    son_ag = {}
    for g in set(GRUP.values()):
        G = [x for x in S if x["g"] == g]
        a, b = benter_fit([(logit(x["pm"]), logit(x["pk"]), x["y"]) for x in G])
        son_ag[g] = {"a": round(a, 4), "b": round(b, 4), "w_m": round(w_fit([(x["mm"], x["mk"], x["ym"]) for x in G if x["mk"] is not None], W0_M), 4),
                     "w_t": round(w_fit([(x["tm"], x["tk"], x["yt"]) for x in G if x["tk"] is not None], W0_T), 4), "n_ogrenme": len(G)}
    U = uretimde()
    gruplar = {}
    for g in sorted({x["g"] for x in S}):
        G = [x for x in S if x["g"] == g]
        fk = fark(G, "ph_")
        gruplar[g] = {"ad": GRUP_AD.get(g, g), "n": len(G), "gun": len({x["gun"] for x in G}), "ligler": sorted({x["lg"] for x in G}),
                      **{k: olc(G, v) for k, v in YOLLAR.items()},
                      "fark_harman_model": fk, "fark_piyasa_model": fark(G, "pk"), "fark_capali_model": fark(G, "pc"),
                      "fark_uretim_model": fark(G, "pu"), "skor": skor_olc(G), "agirlik": son_ag.get(g), "kapi": kapi(G, fk), "uretimde": U.get(g, False)}
    K = jl(KARNE, {}) or {}
    gunluk = {r["gun"]: r for r in K.get("gunluk", [])}
    for d in sorted({x["gun"] for x in S}):
        D = [x for x in S if x["gun"] == d]
        gunluk[d] = {"gun": d, "n": len(D), **{k: r4(np.mean([_ll(x[v], x["y"]) for x in D])) for k, v in (("ll_model", "pm"), ("ll_piyasa", "pk"), ("ll_harman", "ph_"))}}
    kp, syn = kapsam(plog, fixtures, ligler)
    simdi = datetime.now(TR).strftime("%Y-%m-%d %H:%M")
    out = {"surum": SURUM, "guncelleme": simdi,
           "aciklama": ("Basket piyasa karnesi: kilitli model tahmini ile maç öncesi son piyasa oranı (marjı Shin ile ayrılmış) aynı maçlarda. "
                        "Harman = Benter iki aşama (lig grubu, zaman sıralı ağırlık). Çapalı = model fark/toplamının handikap ve alt/üst "
                        "çizgisine çekilmesi. GA: gün blokları bootstrap %95. Üretime yalnız OXXai kapısı + gölge sonrası girer."),
           "kurallar": {"kapi": f"n ≥ {KAPI_N}, gün ≥ {KAPI_GUN}, ΔLL GA üst < 0, ΔBrier < 0, isabet düşmez",
                        "onbilgi": {"a": A0, "b": B0, "lam": LAM_AB, "w_m": W0_M, "w_t": W0_T, "lam_w": LAM_W},
                        "uretim": "data/oxx_ayar.json params.bk_piyasa.<grup> = true (oxx_ogren kapısı + surekli_deney gölgesi)",
                        "izleme": "üretimde 14 gün: kabulden sonraki maçlarda harman log-kaybı model + 0,002'yi aşarsa (n ≥ 30) otomatik geri alma",
                        "golge": "başlamamış her piyasalı maçta pg = {pm harmansız, ph harmanlı, pc çapalı, pk piyasa} bk_predlog'a yazılır"},
           "toplam": {"n": len(S), "gun": len({x["gun"] for x in S}), **{k: olc(S, v) for k, v in YOLLAR.items()}},
           "gruplar": gruplar, "agirlik": son_ag, "uretimde": U, "izleme": izleme(), "canli_golge": canli_golge(plog), "kapsam": kp, "sentetik_yarismalar": syn,
           "gunluk": [gunluk[d] for d in sorted(gunluk)][-120:]}
    if yaz:
        tmp = KARNE + ".tmp"
        json.dump(out, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1, allow_nan=False)
        os.replace(tmp, KARNE)
    return out, S


def gunluk_ll(plog=None, ligler=None):
    """oxx_ogren kapısı için: gün → [(LL model, LL harman, grup)] (ileri yürüyüş)."""
    BJ = jl(os.path.join(DATA, "basket.json"), {}) or {}
    plog = plog if plog is not None else (jl(os.path.join(DATA, "bk_predlog.json"), []) or [])
    S, _ = ileri_yuru(satirlar(plog, ligler if ligler is not None else BJ.get("leagues", {})))
    out = {}
    for x in S: out.setdefault(x["gun"], []).append((_ll(x["pm"], x["y"]), _ll(x["ph_"], x["y"]), x["g"]))
    return dict(sorted(out.items()))


if __name__ == "__main__":
    o, S = karne(yaz="--kuru" not in sys.argv)
    print(json.dumps({"toplam": o["toplam"], "gruplar": {g: {k: v for k, v in G.items() if k in ("n", "gun", "model", "piyasa", "harman", "fark_harman_model", "kapi")}
                                                          for g, G in o["gruplar"].items()}}, ensure_ascii=False, indent=1))
