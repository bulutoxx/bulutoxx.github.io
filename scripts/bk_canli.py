#!/usr/bin/env python3
"""🏀🔴 Basket canlı kazanma olasılığı: anlık görüntü kaydı + Brown hareketi modeli + kapı (yol haritası YH-05).

Model (Stern 1994, JASA): ev − dep sayı farkı sürüklenmeli Brown hareketi. Kalan süre oranı r (0…1), anlık fark d:
    P(ev kazanır) = Φ( (d + w·μ·r) / max(1,5; k·σ·r^(0,5+γ)) )
    σ = σ_lig · sqrt(toplam / (2·mu_lig))     maç başı sayı farkı oynaklığı, beklenen toplamla (tempo) ölçeklenir
    μ = σ · Φ⁻¹(p0)                            sürüklenme: maç öncesi gösterilen olasılıktan (piyasa çapası / model) türetilir
  (k, w, γ) kayıt biriktikçe en çok olabilirlikle öğrenilir; başlangıç değerleri geçmiş çeyrek sonu skorlarından
  (lab/bk_canli_lab.py → data/bk_canli_lab.json). Eski formül (uygulamada bugüne dek): Φ((d + fark·r) / max(1,5; sm·sqrt(r))).
  Formül uygulamadaki bkLivePred ile birebir aynıdır (index.html).

Kayıt (live-log.yml, 5 dk arayla): ESPN canlı skor tablosundan (NBA, WNBA, NBL, G League, NCAA) devam eden maçlar →
  data/archive/bk_live/<İstanbul günü>.json  {maç id: {lg, h, a, p0, mar, sm, tot, mu2, s: [{t, q, c, r, hs, as, pe, pn}], r?: [ev, dep]}}
  Maç öncesi değerler uygulamanın bkPredict'iyle aynı yoldan (data/basket.json fikstürü, takım güçleri, piyasa harmanı, çapa) hesaplanır.
  Maç bitince sonuç yazılır (ESPN; olmazsa bk_predlog / bk_games).
Kapı (gece, basket.py içinden günde bir): ≥ 300 sonuçlu anlık görüntü ve ≥ 40 maç; gün sıralı (D günü yalnız D'den önceki maçlarla
  öğrenilmiş parametre); maç-blok bootstrap B=2000 ΔLL (yeni − eski) %95 üst sınırı < 0, iki zaman yarısında ΔLL < 0, ΔBrier ≤ 0,
  isabet düşmez → data/bk_canli.json kullan=true (uygulama yeni formülü kullanır). 14 gün izleme: kabulden sonraki maçlarda
  ΔLL > +0,002 (≥ 20 maç) → kullan=false (geri alma, gecmis'e yazılır).
  python3 scripts/bk_canli.py kayit      # tek tur anlık görüntü
  python3 scripts/bk_canli.py dongu N SN # N tur, SN saniye arayla (live-log arka plan adımı)
  python3 scripts/bk_canli.py gece       # puanla + kapı (normalde basket.py çağırır)
"""
import glob, gzip, json, math, os, sys, time, urllib.request
from datetime import datetime, timedelta, timezone, date
from statistics import NormalDist

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIZIN = os.path.join(DATA, "archive", "bk_live")
AYAR = os.path.join(DATA, "bk_canli.json")
UA = "Mozilla/5.0 (OXXai; +https://bulutoxx.github.io)"
ESPN = {"nba": "nba", "wnba": "wnba", "nbl": "nbl", "ncaa": "mens-college-basketball", "ncaaw": "womens-college-basketball", "gl": "nba-development"}
N = NormalDist()
VARSAYILAN = {"k": 1.0, "w": 1.0, "g": 0.0}
KAPI_SNAP, KAPI_MAC, IZLE_GUN, IZLE_MAC, IZLE_ESIK = 300, 40, 14, 20, 0.002
try:
    from zoneinfo import ZoneInfo
    TR = ZoneInfo("Europe/Istanbul")
except Exception:
    TR = timezone(timedelta(hours=3))


def phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ------------------------------------------------------------------ formüller (index.html bkLivePred ile aynı)
def p_eski(d, r, mar, sm):
    sd = max(1.5, sm * math.sqrt(max(r, .003)))
    return phi((d + mar * r) / sd)


def sigma_mac(sm, tot, mu2):
    if tot and mu2 and tot > 0 and mu2 > 0: return sm * math.sqrt(tot / mu2)
    return sm


def p_yeni(d, r, p0, sg, prm=None):
    prm = prm or VARSAYILAN
    r = max(r, .003); p0 = min(max(p0, .01), .99)
    mu = sg * N.inv_cdf(p0)
    sd = max(1.5, prm["k"] * sg * r ** (0.5 + prm["g"]))
    return phi((d + prm["w"] * mu * r) / sd)


try:
    from scipy.special import ndtr, ndtri
except Exception:                       # scipy yoksa: Abramowitz–Stegun 7.1.26 (uygulamadaki bkPhi ile aynı, hata < 1,5e-7)
    _inv = np.vectorize(N.inv_cdf)
    def ndtr(x):
        x = np.asarray(x, float); t = 1 / (1 + 0.3275911 * np.abs(x) / math.sqrt(2))
        y = 1 - ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-x * x / 2)
        return np.where(x >= 0, (1 + y) / 2, (1 - y) / 2)
    def ndtri(p): return _inv(np.asarray(p, float))


def p_yeni_v(d, r, p0, sg, k, w, g, mu=None):
    """Vektör sürüm (öğrenme ve sınama). mu verilirse Φ⁻¹ yeniden hesaplanmaz."""
    r = np.maximum(r, .003)
    if mu is None: mu = sg * ndtri(np.clip(p0, .01, .99))
    sd = np.maximum(1.5, k * sg * r ** (0.5 + g))
    return ndtr((d + w * mu * r) / sd)


def p_eski_v(d, r, mar, sm):
    return ndtr((d + mar * r) / np.maximum(1.5, sm * np.sqrt(np.maximum(r, .003))))


def ll_v(p, y):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


IZGARA = {"k": np.round(np.arange(0.6, 1.401, 0.05), 3), "w": np.round(np.arange(0.4, 1.601, 0.1), 3), "g": np.round(np.arange(-0.2, 0.201, 0.05), 3)}


def ogren(S, onbilgi=None, lam=0.0):
    """S: dict dizileri d, r, p0, sg, y, (ağırlık wt). En çok olabilirlik ızgarası; lam>0 ise ön bilgiye L2 (anlık görüntü eşdeğeri)."""
    onb = onbilgi or VARSAYILAN
    if len(S["y"]) == 0: return dict(onb)
    wt = S.get("wt"); wt = np.ones(len(S["y"])) if wt is None else wt
    best, bp = None, dict(onb)
    mu = S["sg"] * ndtri(np.clip(S["p0"], .01, .99)); r = np.maximum(S["r"], .003)
    for k in IZGARA["k"]:
        for g in IZGARA["g"]:
            sd = np.maximum(1.5, k * S["sg"] * r ** (0.5 + g))
            for w in IZGARA["w"]:
                L = float(np.sum(wt * ll_v(ndtr((S["d"] + w * mu * r) / sd), S["y"])))
                L += lam * ((k - onb["k"]) ** 2 + (w - onb["w"]) ** 2 + (g - onb["g"]) ** 2)
                if best is None or L < best: best, bp = L, {"k": float(k), "w": float(w), "g": float(g)}
    return bp


def blok_boot(dl, db, da, blok, B=2000, seed=20261028):
    """Maç-blok bootstrap: Δ dizileri (anlık görüntü başına), blok = maç kimliği. Dönüş: ortalama, %95 GA."""
    rng = np.random.default_rng(seed)
    keys = sorted(set(blok)); ix = {k: i for i, k in enumerate(keys)}; bi = np.array([ix[b] for b in blok])
    S = np.zeros((len(keys), 4))
    np.add.at(S, bi, np.column_stack([dl, db, da, np.ones(len(dl))]))
    pt = S.sum(0); pt = pt[:3] / pt[3]
    sims = []
    for _ in range(B):
        s = S[rng.integers(0, len(keys), len(keys))].sum(0); sims.append(s[:3] / s[3])
    lo, hi = np.percentile(np.array(sims), [2.5, 97.5], axis=0)
    r5 = lambda v: round(float(v), 5)
    return {"n": len(dl), "mac": len(keys), "d_ll": r5(pt[0]), "d_ll_ga": [r5(lo[0]), r5(hi[0])], "d_brier": r5(pt[1]), "d_brier_ga": [r5(lo[1]), r5(hi[1])],
            "d_isabet": r5(pt[2]), "d_isabet_ga": [r5(lo[2]), r5(hi[2])]}


def kapi(pe, pn, y, blok, sira):
    """sira: zaman anahtarı (iki yarı). Dönüş: tum / yari1 / yari2 + gecti."""
    pe, pn, y = np.asarray(pe), np.asarray(pn), np.asarray(y, float)
    dl = ll_v(pn, y) - ll_v(pe, y); db = (pn - y) ** 2 - (pe - y) ** 2
    da = ((pn >= .5) == (y == 1)).astype(float) - ((pe >= .5) == (y == 1)).astype(float)
    blok = list(blok); sira = list(sira)
    mk = sorted(set(blok), key=lambda b: min(s for s, bb in zip(sira, blok) if bb == b))
    h = set(mk[: len(mk) // 2])
    m1 = np.array([b in h for b in blok])
    out = {"tum": blok_boot(dl, db, da, blok)}
    if m1.any() and (~m1).any():
        out["yari1"] = blok_boot(dl[m1], db[m1], da[m1], [b for b, m in zip(blok, m1) if m], 500)
        out["yari2"] = blok_boot(dl[~m1], db[~m1], da[~m1], [b for b, m in zip(blok, m1) if not m], 500)
    t = out["tum"]
    out["gecti"] = bool(t["d_ll_ga"][1] < 0 and t["d_brier"] <= 0 and t["d_isabet"] >= 0
                        and all(out.get(k, {"d_ll": 1})["d_ll"] < 0 for k in ("yari1", "yari2")))
    out["ll_eski"] = round(float(np.mean(ll_v(pe, y))), 4); out["ll_yeni"] = round(float(np.mean(ll_v(pn, y))), 4)
    out["isabet_eski"] = round(float(np.mean((pe >= .5) == (y == 1))), 4); out["isabet_yeni"] = round(float(np.mean((pn >= .5) == (y == 1))), 4)
    out["brier_eski"] = round(float(np.mean((pe - y) ** 2)), 4); out["brier_yeni"] = round(float(np.mean((pn - y) ** 2)), 4)
    return out


# ------------------------------------------------------------------ ayar
def jl(p, d=None):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d


def ayar():
    return jl(AYAR, None) or {"kullan": False, "prm": dict(VARSAYILAN), "onbilgi": dict(VARSAYILAN), "gecmis": []}


def kaydet_json(p, o, indent=1):
    os.makedirs(os.path.dirname(p), exist_ok=True); tmp = p + ".tmp"
    json.dump(o, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=indent, separators=None if indent else (",", ":"), allow_nan=False)
    os.replace(tmp, p)


# ------------------------------------------------------------------ maç öncesi (bkPredict'in Python karşılığı)
def on_tahmin(f, D):
    L = (D.get("leagues") or {}).get(f["lg"])
    if not L: return None
    newp = L.get("newp"); NP = {"off": newp[0], "def": newp[1]} if newp else None
    T = L.get("teams") or {}; H = T.get(f["h"]) or NP; A = T.get(f["a"]) or NP
    if not H or not A: return None
    hh = 0 if f.get("neutral") else L["hca"] / 2
    mh = L["mu"] + hh + H["off"] + A["def"]; ma = L["mu"] - hh + A["off"] + H["def"]
    k = L.get("kscale") or 1
    if k != 1: t, dd = mh + ma, (mh - ma) * k; mh, ma = (t + dd) / 2, (t - dd) / 2
    if f.get("yd"): mh += f["yd"] / 2; ma -= f["yd"] / 2          # YH-04 dinlenme düzeltmesi (yalnız üretimdeki grupta gelir)
    od = f.get("odds") or {}
    if od.get("spread") is not None and od.get("ou"):
        w = ((D.get("market") or {}).get("w"));  w = .5 if w is None else w
        mar = (1 - w) * (mh - ma) + w * (-od["spread"]); tot = (1 - w) * (mh + ma) + w * od["ou"]; mh, ma = (tot + mar) / 2, (tot - mar) / 2
    cp = f.get("cp") or {}
    if cp.get("ph") is not None and cp.get("pa") is not None: mh, ma = float(cp["ph"]), float(cp["pa"])
    sm = L.get("sm") or 12; mar = mh - ma
    p0 = float(cp["p"]) if cp.get("p") is not None else phi(mar / sm)
    return {"p0": round(p0, 4), "mar": round(mar, 2), "sm": sm, "tot": round(mh + ma, 1), "mu2": round(2 * L["mu"], 2),
            "qlen": L.get("qlen") or 12, "halves": bool(L.get("halves"))}


def kalan(per, clock_s, qlen, halves):
    """ESPN period + displayClock → kalan normal süre oranı (bkParseClock ile aynı mantık; uzatmada kalan uzatma dk / toplam)."""
    nper = 2 if halves else 4; plen = 20 if halves else qlen; total = nper * plen
    try:
        mm, ss = (clock_s or "0:00").split(":") if ":" in (clock_s or "") else (0, clock_s or 0)
        left = float(mm) + float(ss) / 60.0
    except Exception:
        return None
    if not per: return None
    if per > nper: return max(.01, left / total)
    return max(0.0, ((nper - per) * plen + left) / total)


# ------------------------------------------------------------------ kayıt
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=25) as r:
        b = r.read()
        if r.headers.get("Content-Encoding") == "gzip" or b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
        return json.loads(b.decode("utf-8"))


def gun_dosyasi(gun): return os.path.join(DIZIN, f"{gun}.json")


def kayit(simdi=None, cek=None):
    """Tek tur. cek(lg, ymd) → ESPN scoreboard sözlüğü (sınamada sahte veri). Dönüş: (canlı maç, yeni anlık görüntü, sonuçlanan)."""
    simdi = simdi or datetime.now(timezone.utc); cek = cek or (lambda lg, ymd: fetch(
        f"https://site.api.espn.com/apis/site/v2/sports/basketball/{ESPN[lg]}/scoreboard?dates={ymd}"
        + ("&groups=50&limit=400" if lg in ("ncaa", "ncaaw") else "")))
    D = jl(os.path.join(DATA, "basket.json"), {}) or {}
    fx = {(f["lg"], f["h"], f["a"]): f for f in D.get("fixtures", [])}
    lgs = sorted({f["lg"] for f in D.get("fixtures", []) if f["lg"] in ESPN})
    if not lgs: return 0, 0, 0
    gun = simdi.astimezone(TR).date().isoformat()
    # ESPN günleri ABD saatiyle: bugün ve dün (gece yarısını geçen maçlar)
    us = simdi - timedelta(hours=6); gunler = sorted({us.strftime("%Y%m%d"), (us - timedelta(days=1)).strftime("%Y%m%d")})
    dosyalar = {}
    def dosya(g):
        if g not in dosyalar: dosyalar[g] = jl(gun_dosyasi(g), {}) or {}
        return dosyalar[g]
    # açık maçlar (son 2 günün dosyalarında sonucu olmayan)
    acik = {}
    for g in ((simdi.astimezone(TR).date() - timedelta(days=i)).isoformat() for i in (0, 1)):
        for k, v in dosya(g).items():
            if v.get("r") is None: acik[k] = g
    ts = simdi.strftime("%Y-%m-%dT%H:%MZ"); n_live = n_snap = n_done = 0
    A = ayar(); prm = A.get("prm") or VARSAYILAN
    gorulen = set()
    for lg in lgs:
        for ymd in gunler:
            try: J = cek(lg, ymd)
            except Exception as e:
                print(f"bk canlı: {lg} {ymd} alınamadı: {e.__class__.__name__}", flush=True); continue
            for e in (J or {}).get("events", []):
                try:
                    c = e["competitions"][0]; cs = {t["homeAway"]: t for t in c["competitors"]}
                    h, a = cs["home"]["team"].get("displayName"), cs["away"]["team"].get("displayName")
                    st = e.get("status") or {}; ty = st.get("type") or {}; state = ty.get("state")
                    gid = "e" + str(e["id"]); hs, as_ = int(float(cs["home"].get("score") or 0)), int(float(cs["away"].get("score") or 0))
                except Exception:
                    continue
                if gid in gorulen: continue
                gorulen.add(gid)
                if state == "post" and ty.get("completed", True) and gid in acik:
                    dosya(acik[gid])[gid]["r"] = [hs, as_]; n_done += 1; continue
                if state != "in": continue
                f = fx.get((lg, h, a))
                if not f: continue
                n_live += 1
                gk = acik.get(gid, gun); G = dosya(gk)
                if gid not in G:
                    pt = on_tahmin(f, D)
                    if not pt: continue
                    G[gid] = {"lg": lg, "h": h, "a": a, "dt": f.get("dt"), **{k: pt[k] for k in ("p0", "mar", "sm", "tot", "mu2", "qlen", "halves")}, "s": []}
                    acik[gid] = gk
                m = G[gid]
                per = int(st.get("period") or 0); clk = st.get("displayClock") or ""
                r = kalan(per, clk, m["qlen"], m["halves"])
                if r is None: continue
                if m["s"] and m["s"][-1]["q"] == per and m["s"][-1]["c"] == clk and m["s"][-1]["hs"] == hs and m["s"][-1]["as"] == as_: continue
                d = hs - as_; sg = sigma_mac(m["sm"], m["tot"], m["mu2"])
                m["s"].append({"t": ts, "q": per, "c": clk, "r": round(r, 4), "hs": hs, "as": as_,
                               "pe": round(p_eski(d, r, m["mar"], m["sm"]), 4), "pn": round(p_yeni(d, r, m["p0"], sg, prm), 4)})
                n_snap += 1
    for g, o in dosyalar.items():
        if o: kaydet_json(gun_dosyasi(g), o, indent=None)
    return n_live, n_snap, n_done


def puanla(gunler=4):
    """ESPN'de kaçırılan sonuçları bk_predlog / bk_games'ten tamamla."""
    res = {}
    for e in jl(os.path.join(DATA, "bk_predlog.json"), []) or []:
        if e.get("r"): res[e["id"]] = e["r"]
    for st in (jl(os.path.join(DATA, "bk_games.json"), {}) or {}).values():
        if isinstance(st, dict):
            for g in st.get("g", []): res.setdefault(g["id"], [g["hs"], g["as_"]])
    n = 0
    for p in sorted(glob.glob(os.path.join(DIZIN, "*.json")))[-gunler:]:
        o = jl(p, {}) or {}; ch = False
        for k, v in o.items():
            if v.get("r") is None and k in res: v["r"] = list(res[k]); ch = True; n += 1
        if ch: kaydet_json(p, o, indent=None)
    return n


def yukle_kayitlar(gun_sayisi=180):
    """Sonuçlu anlık görüntüler: diziler + maç/gün anahtarları (beraberlik sonuçları yok sayılır)."""
    rows = []
    for p in sorted(glob.glob(os.path.join(DIZIN, "*.json")))[-gun_sayisi:]:
        gun = os.path.basename(p)[:10]
        for k, m in (jl(p, {}) or {}).items():
            if not m.get("r") or m["r"][0] == m["r"][1]: continue
            y = 1.0 if m["r"][0] > m["r"][1] else 0.0; sg = sigma_mac(m["sm"], m["tot"], m["mu2"])
            for s in m.get("s", []):
                rows.append((gun, k, s["t"], s["hs"] - s["as"], s["r"], m["p0"], sg, m["mar"], m["sm"], y))
    return rows


def dizi(rows):
    a = list(zip(*rows)) if rows else [[]] * 10
    f = lambda i: np.array(a[i], float)
    return {"gun": list(a[0]), "mac": list(a[1]), "t": list(a[2]), "d": f(3), "r": f(4), "p0": f(5), "sg": f(6), "mar": f(7), "sm": f(8), "y": f(9)}


def gece(bugun=None, yaz=True):
    """Puanla + gün sıralı sınama + kapı + izleme. Dönüş: ayar sözlüğü."""
    bugun = bugun or datetime.now(TR).date()
    puanla()
    A = ayar(); onb = A.get("onbilgi") or dict(VARSAYILAN)
    rows = yukle_kayitlar()
    S = dizi(rows); n = len(S["y"]); macs = sorted(set(S["mac"]))
    A["veri"] = {"anlik": n, "mac": len(macs), "gun": len(set(S["gun"])), "esik": {"anlik": KAPI_SNAP, "mac": KAPI_MAC}}
    if n:
        # gün sıralı: D günü için parametre yalnız D'den önceki günlerin maçlarıyla (ön bilgiye çekilmiş)
        g_arr = np.array(S["gun"]); pn = np.zeros(n)
        hafta = np.array([(date.fromisoformat(x) - timedelta(days=date.fromisoformat(x).weekday())).isoformat() for x in S["gun"]])
        for D in sorted(set(hafta)):         # haftalık yeniden öğrenme: D haftası yalnız D'den önceki günlerle
            tr = g_arr < D; te = hafta == D
            prm = ogren({k: S[k][tr] for k in ("d", "r", "p0", "sg", "y")}, onb, lam=50.0) if tr.sum() >= 50 else dict(onb)
            pn[te] = p_yeni_v(S["d"][te], S["r"][te], S["p0"][te], S["sg"][te], prm["k"], prm["w"], prm["g"])
        pe = p_eski_v(S["d"], S["r"], S["mar"], S["sm"])
        K = kapi(pe, pn, S["y"], S["mac"], S["t"])
        A["sinama"] = {"tarih": bugun.isoformat(), **K}
        if len(macs) >= KAPI_MAC:
            A["prm"] = ogren({k: S[k] for k in ("d", "r", "p0", "sg", "y")}, onb, lam=50.0)
        yeter = n >= KAPI_SNAP and len(macs) >= KAPI_MAC
        geri = [g for g in A.get("gecmis", []) if g.get("olay") == "geri_alindi" and g.get("tarih", "") >= (bugun - timedelta(days=30)).isoformat()]
        if not A.get("kullan") and yeter and K["gecti"] and not geri:
            A["kullan"] = True; A["izleme"] = {"kabul_tarihi": bugun.isoformat()}
            A.setdefault("gecmis", []).append({"tarih": bugun.isoformat(), "olay": "kabul", "kanit": K["tum"], "prm": A["prm"]})
        A["karar"] = ("yeni formül üretimde" if A.get("kullan") else
                      ("veri birikiyor" if not yeter else ("kapı geçmedi → eski formül" if not K["gecti"] else "geri alındı, 30 gün bekleme")))
        # 14 gün izleme
        if A.get("kullan") and (A.get("izleme") or {}).get("kabul_tarihi"):
            kt = A["izleme"]["kabul_tarihi"]; m = g_arr >= kt
            if m.any():
                dl = ll_v(pn[m], S["y"][m]) - ll_v(pe[m], S["y"][m]); nm = len(set(np.array(S["mac"])[m]))
                A["izleme"].update({"anlik": int(m.sum()), "mac": nm, "d_ll": round(float(dl.mean()), 5),
                                    "gun": (bugun - date.fromisoformat(kt)).days})
                if nm >= IZLE_MAC and float(dl.mean()) > IZLE_ESIK:
                    A["kullan"] = False; A["karar"] = "izlemede kötüleşti → geri alındı"
                    A.setdefault("gecmis", []).append({"tarih": bugun.isoformat(), "olay": "geri_alindi", "mac": nm, "d_ll": round(float(dl.mean()), 5)})
                elif A["izleme"]["gun"] >= IZLE_GUN and not A["izleme"].get("tamam"):
                    A["izleme"]["tamam"] = True
                    A.setdefault("gecmis", []).append({"tarih": bugun.isoformat(), "olay": "izleme_bitti", "mac": nm, "d_ll": A["izleme"]["d_ll"]})
    else:
        A["karar"] = "veri birikiyor"
    A["gece_tarih"] = bugun.isoformat()
    A["gecmis"] = (A.get("gecmis") or [])[-30:]
    if yaz: kaydet_json(AYAR, A)
    return A


if __name__ == "__main__":
    kom = sys.argv[1] if len(sys.argv) > 1 else "kayit"
    if kom == "kayit":
        print("bk canlı kayıt:", kayit(), flush=True)
    elif kom == "dongu":
        tur = int(sys.argv[2]) if len(sys.argv) > 2 else 6; ara = int(sys.argv[3]) if len(sys.argv) > 3 else 300
        for i in range(tur):
            t0 = time.time()
            try: print(time.strftime("%H:%M"), "bk canlı kayıt (canlı, yeni görüntü, biten):", kayit(), flush=True)
            except Exception as e: print("bk canlı kayıt hatası:", e.__class__.__name__, str(e)[:160], flush=True)
            if i < tur - 1: time.sleep(max(0, ara - (time.time() - t0)))
    elif kom == "gece":
        A = gece(); print(json.dumps({k: A.get(k) for k in ("kullan", "prm", "veri", "karar")}, ensure_ascii=False), flush=True)
