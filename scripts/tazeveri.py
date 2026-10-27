"""🌱 Taze veri (maça yakın bilgi) → maç öncesi futbol tahmini. Yalnız numpy; motor (update.py) ve kapı (lab/tazeveri_kapi.py) ortak kullanır.

Sinyaller (her biri ayrı aday, ayrı kapı; varsayılan KAPALI):
  kadro_1x2 / kadro_ou     data/kadro.json türetilmiş özeti (scripts/kadro.py): ev/dep = [eksik, kilit_eksik, tahmini_kayip].
                           Temel olasılıktan Poisson gol beklentisi çifti (λev, λdep) geri çözülür, güç farkı
                           x = k·(kayıp_dep − kayıp_ev) + ke·(eksik_dep − eksik_ev) kadar kaydırılır (log λev += x/2, log λdep −= x/2),
                           temel olasılık bu kaymanın Poisson oranıyla çarpılır (temelin kalibrasyonu korunur).
  hareket_1x2 / hareket_ou Oran hareketi: ilk görülen oran (açılış) → maç başlamadan önceki son oran. Marjı ayrılmış olasılıkların
                           log farkı m; p' = softmax(log p + b·m). 2,5 üst için logit farkı (bo).
  karisim_1x2 / karisim_ou Oranlı maçlarda piyasa yolu (sunulan) ile model yolu (Poisson; predict_fixtures) log-doğrusal karışımı (w, wo).
Temel (ayarsız) olasılık = uygulamanın gösterdiği: kp/ko varsa onlar, yoksa pz 1/X/2 ve U25 (pazar motoru).

Gölge kayıt: data/tazeveri.json  {"mac": {id: {...}}}  — her motor çalışmasında başlamamış maçların SON hali güncellenir,
başlayınca donar, sonuç gelince r yazılır. Alanlar (yalnız türetilmiş sayılar; ham API-Football verisi yok):
  bt başlama (unix), t0/t1 ilk/son görülme, o0/o1 1X2 oranı (açılış/son), u0/u1 2,5 üst/alt oranı, b/bo temel olasılık,
  pm/pmo model yolu, kd kadro özeti [eksik_ev, kilit_ev, kayip_ev, eksik_dep, kilit_dep, kayip_dep, ilk11],
  g = {aday: [p1, pX, p2] ya da p_ust} o anki parametrelerle ayarlı gölge tahmin, s = yayında uygulanan adaylar, r = [ev_gol, dep_gol].
Ayar ve kapı durumu: data/tazeveri_ayar.json (lab/tazeveri_kapi.py yazar). aktif adaylar yalnız fixtures.json ÇIKTISINA uygulanır
(kp/ko + tz alanı); bellekteki fikstür ve kilitli tahmin (predlog p) değişmez.
"""
import json, math, os
from datetime import date, datetime, timedelta, timezone

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
GOLGE = os.path.join(DATA, "tazeveri.json")
AYAR = os.path.join(DATA, "tazeveri_ayar.json")
KADRO = os.path.join(DATA, "kadro.json")
SAKLA_GUN = 120
RHO = -0.06
VARSAYILAN = {"kadro": {"k": 1.0, "ke": 0.01}, "hareket": {"b": 0.5, "bo": 0.5}, "karisim": {"w": 0.1, "wo": 0.1}}
ADAYLAR = ("kadro_1x2", "kadro_ou", "hareket_1x2", "hareket_ou", "karisim_1x2", "karisim_ou")


def jl(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def jw(p, o):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(o, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, p)


def r4(x): return round(float(x), 4)


# ------------------------------------------------------------------ Poisson (Dixon-Coles) ızgarası ve ters çözüm
_K = np.arange(11)
_LF = np.array([math.lgamma(k + 1) for k in _K])


def olas(lh, la, rho=RHO):
    """Vektörel: (n,) λ çiftlerinden (n,3) 1X2 ve (n,) 2,5 üst."""
    lh = np.atleast_1d(np.asarray(lh, float)); la = np.atleast_1d(np.asarray(la, float))
    ph = np.exp(_K[None, :] * np.log(lh[:, None]) - lh[:, None] - _LF[None, :])
    pa = np.exp(_K[None, :] * np.log(la[:, None]) - la[:, None] - _LF[None, :])
    g = ph[:, :, None] * pa[:, None, :]
    g[:, 0, 0] *= 1 - lh * la * rho; g[:, 0, 1] *= 1 + lh * rho; g[:, 1, 0] *= 1 + la * rho; g[:, 1, 1] *= 1 - rho
    g /= g.sum((1, 2), keepdims=True)
    i, j = np.meshgrid(_K, _K, indexing="ij")
    p = np.stack([(g * (i > j)).sum((1, 2)), (g * (i == j)).sum((1, 2)), (g * (i < j)).sum((1, 2))], 1)
    return p, (g * ((i + j) > 2)).sum((1, 2))


_TAB = None


def _tablo():
    global _TAB
    if _TAB is None:
        v = np.arange(0.15, 4.51, 0.025)
        LH, LA = np.meshgrid(v, v, indexing="ij"); LH, LA = LH.ravel(), LA.ravel()
        p, o = olas(LH, LA)
        _TAB = (LH, LA, p[:, 0] - p[:, 2], o)
    return _TAB


def ters(p, o=None):
    """1X2 (ve varsa 2,5 üst) olasılığından Poisson λ çifti. 2,5 üst yoksa toplam gol 2,6 varsayılır."""
    LH, LA, d, ov = _tablo()
    hedef_d = p[0] - p[2]
    if o is None:
        e = (d - hedef_d) ** 2 + 0.05 * ((LH + LA) - 2.6) ** 2
    else:
        e = (d - hedef_d) ** 2 + (ov - o) ** 2
    i = int(np.argmin(e)); return float(LH[i]), float(LA[i])


# ------------------------------------------------------------------ dönüşümler
def _norm(p): p = np.clip(np.asarray(p, float), 1e-6, 1); return p / p.sum()
def _lg(x): x = min(max(float(x), 1e-4), 1 - 1e-4); return math.log(x / (1 - x))
def _sg(z): return 1 / (1 + math.exp(-z))


def dv(od):
    """Oransal marj ayırma (1X2 ya da üst/alt)."""
    if not od or any((not isinstance(x, (int, float))) or x <= 1 for x in od): return None
    q = [1 / x for x in od]; s = sum(q); return [x / s for x in q]


def kadro_kayma(kd, prm):
    if not kd or len(kd) < 6: return 0.0
    return prm.get("k", 0) * (kd[5] - kd[2]) + prm.get("ke", 0) * (kd[3] - kd[0])


def kadro_ayarla(p, o, kd, prm):
    """Dönüş: (p', o')."""
    x = kadro_kayma(kd, prm)
    if not x: return list(p), o
    lh, la = ters(p, o)
    q, qo = olas([lh, lh * math.exp(x / 2)], [la, la * math.exp(-x / 2)])
    p2 = _norm(np.asarray(p) * q[1] / np.maximum(q[0], 1e-6))
    o2 = None if o is None else _sg(_lg(o) + _lg(qo[1]) - _lg(qo[0]))
    return [r4(v) for v in p2], (None if o2 is None else r4(o2))


def hareket_ayarla(p, o, o0, o1, u0, u1, prm):
    a, b = dv(o0), dv(o1); p2 = list(p)
    if a and b and len(a) == 3:
        z = np.log(_norm(p)) + prm.get("b", 0) * (np.log(_norm(b)) - np.log(_norm(a)))
        p2 = [r4(v) for v in _norm(np.exp(z - z.max()))]
    o2 = o
    ua, ub = dv(u0), dv(u1)
    if o is not None and ua and ub:
        o2 = r4(_sg(_lg(o) + prm.get("bo", 0) * (_lg(ub[0]) - _lg(ua[0]))))
    return p2, o2


def karisim_ayarla(p, o, pm, pmo, prm):
    p2 = list(p); o2 = o
    if pm and len(pm) == 3:
        w = prm.get("w", 0); z = (1 - w) * np.log(_norm(p)) + w * np.log(_norm(pm))
        p2 = [r4(v) for v in _norm(np.exp(z - z.max()))]
    if o is not None and pmo is not None:
        w = prm.get("wo", 0); o2 = r4(_sg((1 - w) * _lg(o) + w * _lg(pmo)))
    return p2, o2


def ayarla(e, aday, prm):
    """Gölge kayıt satırı e için tek adayın ayarlı tahmini: 1x2 → [3], ou → float ya da None (uygulanamazsa)."""
    sin, paz = aday.split("_")
    p, o = e.get("b"), e.get("bo")
    if not p: return None
    if sin == "kadro":
        if not e.get("kd"): return None
        p2, o2 = kadro_ayarla(p, o, e["kd"], prm)
    elif sin == "hareket":
        if not e.get("o0") or not e.get("o1"): return None
        p2, o2 = hareket_ayarla(p, o, e.get("o0"), e.get("o1"), e.get("u0"), e.get("u1"), prm)
    else:
        if not e.get("o1") or not e.get("pm"): return None      # karışım yalnız oranlı maçlarda (piyasa yolu + model yolu)
        p2, o2 = karisim_ayarla(p, o, e.get("pm"), e.get("pmo"), prm)
    return p2 if paz == "1x2" else o2


# ------------------------------------------------------------------ ayar ve geri alma
def ayar():
    return jl(AYAR, None) or {}


def parametre(A, sin):
    return dict(VARSAYILAN[sin], **(((A or {}).get("prm") or {}).get(sin) or {}))


def _geri_alma_aktif():
    bugun = date.today().isoformat()
    R = jl(os.path.join(DATA, "rollback.json"), {}) or {}
    if R.get("aktif") and R.get("bitis", "") >= bugun and "tazeveri" not in (R.get("haric") or []): return True
    R = jl(os.path.join(DATA, "oxx_rollback.json"), {}) or {}
    return (R.get("donmus") or {}).get("tazeveri", "") >= bugun


def aktifler(A=None):
    A = A if A is not None else ayar()
    if _geri_alma_aktif(): return []
    return [a for a in ADAYLAR if ((A.get("adaylar") or {}).get(a) or {}).get("durum") in ("aktif", "kalici")]


# ------------------------------------------------------------------ motor bağlantısı
def anahtar(f): return f"{f['lg']}|{f['d']}|{f['h']}|{f['a']}"


def temel(f):
    """Uygulamanın gösterdiği (ayarsız) olasılık: kp/ko varsa onlar, yoksa pazar motoru pz."""
    pz = f.get("pz") or {}
    p = f["kp"] if isinstance(f.get("kp"), list) and len(f["kp"]) == 3 else (
        [pz["1"], pz["X"], pz["2"]] if all(isinstance(pz.get(k), (int, float)) for k in ("1", "X", "2")) else None)
    o = f["ko"] if isinstance(f.get("ko"), (int, float)) else (pz["U25"] if isinstance(pz.get("U25"), (int, float)) else None)
    od, ou = _oran(f)
    if p is None and od: p = dv(od)                     # pazar motoru yoksa: son oranın marjı ayrılmış hali (piyasa yolu)
    if o is None and ou and dv(ou): o = dv(ou)[0]
    if p is not None:
        s = sum(p)
        if s <= 0: return None, None
        p = [r4(x / s) for x in p]
    return p, (None if o is None else r4(o))


def _oran(f):
    o = f.get("odds") if isinstance(f.get("odds"), list) and len(f["odds"]) == 3 else None
    u = f.get("ou") if isinstance(f.get("ou"), list) and len(f["ou"]) == 2 else (f.get("iou") if isinstance(f.get("iou"), list) else None)
    return o, u


def golge_guncelle(fx, kickoff_ts, model=None, now=None, A=None, G=None, yaz=True):
    """Başlamamış her maç için gölge kaydı tazeler. model: {id: (p[3], o)} model yolu (predict_fixtures). Dönüş: güncellenen sayı."""
    now = now or datetime.now(timezone.utc); nts = now.timestamp(); tz = now.strftime("%Y-%m-%dT%H:%MZ")
    A = A if A is not None else ayar()
    G = G if G is not None else (jl(GOLGE, None) or {})
    M = G.setdefault("mac", {})
    K = (jl(KADRO, {}) or {}).get("mac") or {}
    akt = aktifler(A)
    n = 0
    for f in fx:
        try:
            bt = kickoff_ts(f)
        except Exception:
            bt = None
        if not bt or bt <= nts or bt - nts > 9 * 86400: continue
        k = anahtar(f)
        e = M.get(k)
        if e is None:
            e = M[k] = {"lg": f["lg"], "d": f["d"], "t0": tz}
        e["bt"] = int(bt); e["t1"] = tz
        b, bo = temel(f)
        if b: e["b"] = b
        if bo is not None: e["bo"] = bo
        o, u = _oran(f)
        if o:
            e.setdefault("o0", [round(float(x), 2) for x in o]); e["o1"] = [round(float(x), 2) for x in o]
        if u:
            e.setdefault("u0", [round(float(x), 2) for x in u]); e["u1"] = [round(float(x), 2) for x in u]
        if f.get("iid"): e["iid"] = f["iid"]
        mm = (model or {}).get(k)
        if mm:
            e["pm"] = [r4(x) for x in mm[0]]
            if mm[1] is not None: e["pmo"] = r4(mm[1])
        kk = K.get(k)
        if kk and kk.get("bt", 0) > nts - 600:
            e["kd"] = list(kk["ev"]) + list(kk["dep"]) + [kk.get("ilk11", 0)]; e["kdt"] = kk.get("t")
        g = {}
        for a in ADAYLAR:
            v = ayarla(e, a, parametre(A, a.split("_")[0]))
            if v is not None: g[a] = v
        if g: e["g"] = g
        else: e.pop("g", None)
        s = [a for a in akt if a in g]
        if s: e["s"] = s
        else: e.pop("s", None)
        n += 1
    if yaz: _yaz(G, now)
    return n


def sonuc_isle(G, all_ms, arsiv_dizin=None, now=None, yaz=True):
    """Başlamış ve sonucu bilinen maçlara r yazar. all_ms: {lg: [maç]} (motorun sezon verisi); arşiv iddaa kimliğiyle (hs/as)."""
    M = (G or {}).get("mac") or {}
    nts = (now or datetime.now(timezone.utc)).timestamp()
    bek = [(k, e) for k, e in M.items() if e.get("r") is None and e.get("bt", 9e12) < nts - 2 * 3600]
    if not bek: return 0
    sk = {}
    for lg, ms in (all_ms or {}).items():
        for m in ms:
            if m.get("ft") and None not in m["ft"][:2]: sk[f"{lg}|{m['d']}|{m['h']}|{m['a']}"] = [int(m["ft"][0]), int(m["ft"][1])]
    ar = {}
    ad = arsiv_dizin or os.path.join(DATA, "archive")
    gunler = sorted({e["d"] for _, e in bek})
    for g in {x for d in gunler for x in (d, (date.fromisoformat(d) - timedelta(days=1)).isoformat(), (date.fromisoformat(d) + timedelta(days=1)).isoformat())}:
        for iid, r in ((jl(os.path.join(ad, g + ".json"), {}) or {}).items()):
            if isinstance(r, dict) and r.get("hs") is not None and r.get("as") is not None: ar[str(iid)] = [int(r["hs"]), int(r["as"])]
    n = 0
    for k, e in bek:
        r = sk.get(k) or (ar.get(str(e["iid"])) if e.get("iid") else None)
        if r: e["r"] = r; n += 1
    if yaz and n: _yaz(G)
    return n


def _yaz(G, now=None):
    now = now or datetime.now(timezone.utc)
    sinir = (now - timedelta(days=SAKLA_GUN)).date().isoformat()
    bayat = (now - timedelta(days=3)).timestamp()
    G["mac"] = {k: e for k, e in G.get("mac", {}).items() if e.get("d", "") >= sinir
                and not (e.get("r") is None and e.get("bt", 0) < bayat - 4 * 86400)}     # sonucu hiç gelmeyen eski maç atılır
    M = G["mac"]
    G["ozet"] = {"guncelleme": now.strftime("%Y-%m-%dT%H:%MZ"), "mac": len(M), "puanli": sum(1 for e in M.values() if e.get("r")),
                 "kadrolu": sum(1 for e in M.values() if e.get("kd")), "kadrolu_puanli": sum(1 for e in M.values() if e.get("kd") and e.get("r")),
                 "oranli_hareketli": sum(1 for e in M.values() if e.get("o0") and e.get("o1") and e["o0"] != e["o1"]),
                 "oranli_puanli": sum(1 for e in M.values() if e.get("o1") and e.get("r"))}
    G["aciklama"] = ("Taze veri gölge kaydı (scripts/tazeveri.py): maç başına temel tahmin (b/bo) ile kadro, oran hareketi ve "
                     "model karışımı ayarlı gölge tahminler (g). Yalnız türetilmiş sayılar. Kapı: lab/tazeveri_kapi.py.")
    jw(GOLGE, G)


def cikti_uygula(fx, A=None, G=None):
    """fixtures.json'a yazılacak KOPYALAR: aktif adayların ayarlı olasılığı kp/ko'ya, uygulanan adaylar tz'ye. Dönüş: (liste, sayı)."""
    A = A if A is not None else ayar()
    akt = aktifler(A)
    if not akt: return fx, 0
    M =((G if G is not None else jl(GOLGE, {})) or {}).get("mac") or {}
    out = []; n = 0
    for f in fx:
        e = M.get(anahtar(f)) if f.get("lg") else None
        g = (e or {}).get("g") or {}
        s = [a for a in akt if a in g]
        if not s: out.append(f); continue
        f2 = dict(f); p, o = e.get("b"), e.get("bo")
        # birden çok aday aktifse sırayla uygulanır (kadro → hareket → karışım), her biri öncekinin çıktısına
        for sin in ("kadro", "hareket", "karisim"):
            e2 = dict(e, b=p, bo=o)
            if f"{sin}_1x2" in s: p = ayarla(e2, f"{sin}_1x2", parametre(A, sin)) or p
            if f"{sin}_ou" in s:
                v = ayarla(e2, f"{sin}_ou", parametre(A, sin)); o = v if v is not None else o
        if any(a.endswith("_1x2") for a in s): f2["kp"] = p
        if any(a.endswith("_ou") for a in s) and o is not None: f2["ko"] = o
        f2["tz"] = s; out.append(f2); n += 1
    return out, n
