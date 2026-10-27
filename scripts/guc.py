"""⚖️ Güç puanları ve topluluk (oransız maçların model yolu). Yalnız numpy; motor (update.py) ve laboratuvar (lab/fb_guc_lab.py) ortak kullanır.

Robotlar (her biri maçı yalnız o güne kadarki sonuçlarla tahmin eder):
  Poisson  — motorun Maher-Poisson'u (update.fit); oransız liglerde hedef yalnız gol olduğu için ayrı decay/prior ile.
  Elo      — gol farkı ağırlıklı Elo (Dünya Futbol Elo çarpanı), lig bazlı ev avantajı çevrimiçi öğrenilir, sezon başı ortalamaya çekilir.
  pi       — pi-rating (Constantinou & Fenton 2013): her takımın ayrı ev / deplasman puanı, beklenen gol farkı.
Topluluk (yığınlama): çok sınıflı lojistik regresyon; girdiler Poisson log-olasılıkları + Elo farkı + pi gol farkı.
Ağırlıklar yalnız geçmiş maçlarla öğrenilir (laboratuvarda aylık genişleyen pencere; üretimde kapıdan geçen ağırlıklar).
2,5 alt/üst: Poisson üst olasılığının logiti + pi beklenen farkın büyüklüğü + lig gol ortalaması üzerinde lojistik.

Üretim bağlantısı (bayraklı, geri alınabilir): data/fb_guc.json  {"aktif": bool, "W": .., "Wo": .., "prm": ..}
  aktif ise update.py oranı OLMAYAN yaklaşan maçlara kp (1X2) ve ko (2,5 üst) yazar; uygulamanın öneri yolu (recOf) bunları kullanır.
  Koruyucu geri alma (data/rollback.json) ya da OXXai geri alma (data/oxx_rollback.json donmus["fb_guc"]) aktifse uygulanmaz.
"""
import collections, json, math, os
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
AYAR = os.path.join(DATA, "fb_guc.json")

# Laboratuvarda seçim diliminde bulunan varsayılanlar (lab/fb_guc_lab.py yazar; burada yalnız güvenli başlangıç)
ELO_VARSAYILAN = {"K": 20.0, "H0": 60.0, "eta": 1.0, "rev": 0.25, "yeni": 50.0}
PI_VARSAYILAN = {"lam": 0.06, "gam": 0.6, "c": 3.0}


# ------------------------------------------------------------------ Elo
def _sonuc(a, b): return 1.0 if a > b else 0.5 if a == b else 0.0


def elo_seq(ms, prm=None):
    """ms: tarih sıralı maçlar (ft dolu). Dönüş: (her maç için maç öncesi elo farkı (ev avantajı dahil) listesi, durum).
    durum = {"r": {takım: puan}, "H": lig ev avantajı, "sezon": son sezon}"""
    p = dict(ELO_VARSAYILAN, **(prm or {}))
    r = {}; H = p["H0"]; out = []; cur_season = None
    for m in ms:
        s = m.get("season")
        if cur_season is not None and s != cur_season and r:
            mu = float(np.mean(list(r.values())))
            for t in r: r[t] = mu + (1 - p["rev"]) * (r[t] - mu)
        cur_season = s
        for t in (m["h"], m["a"]):
            if t not in r: r[t] = (float(np.mean(list(r.values()))) if r else 1500.0) - (p["yeni"] if r else 0.0)
        d = r[m["h"]] + H - r[m["a"]]
        out.append(d)
        a, b = m["ft"][0], m["ft"][1]
        S = _sonuc(a, b); E = 1 / (1 + 10 ** (-d / 400))
        gd = abs(a - b)
        mult = 1.0 if gd <= 1 else 1.5 if gd == 2 else (11 + gd) / 8      # Dünya Futbol Elo gol farkı çarpanı (eloratings.net)
        dk = p["K"] * mult * (S - E)
        r[m["h"]] += dk; r[m["a"]] -= dk
        H += p["eta"] * (S - E)
    return out, {"r": r, "H": H, "sezon": cur_season}


def elo_fark(st, h, a, prm=None):
    p = dict(ELO_VARSAYILAN, **(prm or {}))
    r = st["r"]; mu = float(np.mean(list(r.values()))) if r else 1500.0
    return r.get(h, mu - p["yeni"]) + st["H"] - r.get(a, mu - p["yeni"])


# ------------------------------------------------------------------ pi-rating (Constantinou & Fenton 2013)
def _pi_g(x, c): return math.copysign(10 ** (abs(x) / c) - 1, x)


def pi_seq(ms, prm=None):
    """Dönüş: (her maç için maç öncesi beklenen gol farkı (ev − dep), durum {"H": {takım: ev puanı}, "A": {takım: dep puanı}})."""
    p = dict(PI_VARSAYILAN, **(prm or {}))
    lam, gam, c = p["lam"], p["gam"], p["c"]
    RH = collections.defaultdict(float); RA = collections.defaultdict(float); out = []
    for m in ms:
        h, a = m["h"], m["a"]
        pred = _pi_g(RH[h], c) - _pi_g(RA[a], c)
        out.append(pred)
        e = (m["ft"][0] - m["ft"][1]) - pred
        psi = math.copysign(c * math.log10(1 + abs(e)), e)
        dh = lam * psi
        RH[h] += dh; RA[h] += gam * dh
        RA[a] -= dh; RH[a] -= gam * dh
    return out, {"H": dict(RH), "A": dict(RA), "c": c}


def pi_fark(st, h, a):
    return _pi_g(st["H"].get(h, 0.0), st["c"]) - _pi_g(st["A"].get(a, 0.0), st["c"])


# ------------------------------------------------------------------ yığınlayıcı
def _softmax(z):
    z = z - z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)


def ozellik_1x2(pp, elo_d, pi_gd, kullan=("pois", "elo", "pi")):
    """pp: (n,3) Poisson olasılıkları; elo_d: (n,) elo farkı; pi_gd: (n,) pi beklenen gol farkı."""
    n = len(pp); cols = [np.ones(n)]
    if "pois" in kullan:
        lp = np.log(np.clip(pp, 1e-6, 1))
        cols += [lp[:, 0] - lp[:, 2], lp[:, 1] - (lp[:, 0] + lp[:, 2]) / 2]
    if "elo" in kullan:
        e = np.asarray(elo_d, float) / 400; cols += [e, np.abs(e)]
    if "pi" in kullan:
        g = np.clip(np.asarray(pi_gd, float), -4, 4); cols += [g, np.abs(g)]
    return np.stack(cols, 1)


def mlogit_fit(X, y, l2=1.0, it=60, W0=None):
    """Çok sınıflı lojistik (Newton, blok köşegen yaklaşımı yerine tam Hessian; özellik sayısı küçük). Sabite ceza yok."""
    n, f = X.shape; k = 3
    W = np.zeros((f, k)) if W0 is None else np.array(W0, float)
    Y = np.eye(k)[y]; R = np.eye(f) * l2; R[0, 0] = 1e-6
    for _ in range(it):
        Pm = _softmax(X @ W)
        G = X.T @ (Pm - Y) + R @ W
        # tam Hessian (f*k x f*k)
        Hs = np.zeros((f * k, f * k))
        for i in range(k):
            for j in range(k):
                wij = Pm[:, i] * ((i == j) - Pm[:, j])
                Hs[i * f:(i + 1) * f, j * f:(j + 1) * f] = (X * wij[:, None]).T @ X + (R if i == j else 0)
        Hs += np.eye(f * k) * 1e-6
        step = np.linalg.solve(Hs, G.T.reshape(-1)).reshape(k, f).T
        W -= step
        if np.abs(step).max() < 1e-7: break
    W -= W[:, 1:2]          # beraberlik sınıfı referans (özdeşlik)
    return W


def mlogit_pred(X, W): return _softmax(X @ np.asarray(W, float))


def ozellik_ou(pO, pi_gd, ort_gol):
    lo = np.log(np.clip(pO, 1e-4, 1 - 1e-4)) - np.log(np.clip(1 - pO, 1e-4, 1))
    return np.stack([np.ones(len(lo)), lo, np.abs(np.clip(np.asarray(pi_gd, float), -4, 4)), np.log(np.maximum(ort_gol, .5))], 1)


def logit_fit(X, y, l2=1.0, it=50):
    w = np.zeros(X.shape[1]); R = np.eye(X.shape[1]) * l2; R[0, 0] = 1e-6
    for _ in range(it):
        p = 1 / (1 + np.exp(-(X @ w)))
        G = X.T @ (p - y) + R @ w; Hs = (X * (p * (1 - p))[:, None]).T @ X + R
        st = np.linalg.solve(Hs, G); w -= st
        if np.abs(st).max() < 1e-8: break
    return w


def logit_pred(X, w): return 1 / (1 + np.exp(-(X @ np.asarray(w, float))))


# ------------------------------------------------------------------ üretim
def ayar():
    try:
        return json.load(open(AYAR, encoding="utf-8"))
    except Exception:
        return None


def _geri_alma_aktif():
    try:
        R = json.load(open(os.path.join(DATA, "rollback.json"), encoding="utf-8"))
        if R.get("aktif") and R.get("bitis", "") >= date.today().isoformat() and "fb_guc" not in (R.get("haric") or []): return True
    except Exception: pass
    try:
        R = json.load(open(os.path.join(DATA, "oxx_rollback.json"), encoding="utf-8"))
        if (R.get("donmus") or {}).get("fb_guc", "") >= date.today().isoformat(): return True
    except Exception: pass
    return False


def oransiz_ligler(season):
    return {lg for lg, d in season.items() if d.get("src") == "espn" and not d.get("cup")}


def lig_parametre(P, lg, season, A=None):
    """Kapıyı geçtiyse oransız liglerde Poisson decay/prior (yalnız gol hedefi); değilse motorun ayarı aynen."""
    A = A if A is not None else ayar()
    po = (A or {}).get("poisson_oransiz") or {}
    if not po.get("aktif") or lg not in oransiz_ligler(season) or _geri_alma_aktif(): return P
    return dict(P, decay=po["decay"], prior=po["prior"])


def durumlar(ms, A):
    """Bir ligin bitmiş maçlarından Elo ve pi durumları + lig gol ortalaması."""
    ms = sorted([m for m in ms if m.get("ft") and None not in m["ft"][:2]], key=lambda m: (m["d"], m["h"]))
    _, se = elo_seq(ms, A.get("elo"))
    _, sp = pi_seq(ms, A.get("pi"))
    son = ms[-300:]
    og = float(np.mean([m["ft"][0] + m["ft"][1] for m in son])) if son else 2.6
    return se, sp, og


def tahmin(fx_list, season, P, today, U, A=None, golge=False):
    """Oransız maçlar için topluluk tahmini. Dönüş: {(lg,d,h,a): {"p": [3], "o": float, "p_pois": [3]}}.
    A: fb_guc.json içeriği (W, Wo, prm). golge=True ise bayrak kapalı olsa da hesaplar (gölge kayıt için)."""
    A = A if A is not None else ayar()
    if not A or not A.get("W"): return {}
    if not golge and (not A.get("aktif") or _geri_alma_aktif()): return {}
    PP = dict(P); PP.update(A.get("poisson") or {})
    ligler = A.get("ligler")
    by = collections.defaultdict(list)
    for f in fx_list:
        if f.get("odds"): continue
        lg = f.get("lg")
        if lg not in season or season[lg].get("cup"): continue
        if ligler and lg not in ligler: continue
        by[lg].append(f)
    out = {}
    for lg, fl in by.items():
        ms = [m for m in season[lg]["matches"] if m.get("ft") and None not in m["ft"][:2]]
        if len(ms) < 60: continue
        try:
            F = U.fit(ms, today, PP)
        except Exception:
            continue
        se, sp, og = durumlar(ms, A.get("prm") or {})
        cnt = collections.Counter([m["h"] for m in ms] + [m["a"] for m in ms])
        rows = []
        for f in fl:
            if cnt[f["h"]] < 3 or cnt[f["a"]] < 3: continue
            (ah, dh), (aa, da) = F["t"].get(f["h"], U.NEW_TEAM), F["t"].get(f["a"], U.NEW_TEAM)
            rows.append((f, F["mu"] * F["gamma"] * ah * da, F["mu"] * aa * dh,
                         elo_fark(se, f["h"], f["a"], (A.get("prm") or {}).get("elo")), pi_fark(sp, f["h"], f["a"])))
        if not rows: continue
        lh = np.array([r[1] for r in rows]); la = np.array([r[2] for r in rows])     # laboratuvarla aynı: gscale/calT yok (yığınlayıcı kalibre eder)
        pp, pO, _, _ = U.outcome_probs(lh, la, PP.get("rho", -0.06))
        X = ozellik_1x2(pp, [r[3] for r in rows], [r[4] for r in rows], tuple(A.get("kullan") or ("pois", "elo", "pi")))
        q = mlogit_pred(X, A["W"])
        qo = logit_pred(ozellik_ou(pO, [r[4] for r in rows], np.full(len(rows), og)), A["Wo"]) if A.get("Wo") else pO
        for i, r in enumerate(rows):
            f = r[0]
            out[(lg, f["d"], f["h"], f["a"])] = {"p": [round(float(x), 4) for x in q[i]], "o": round(float(qo[i]), 4),
                                                 "p_pois": [round(float(x), 4) for x in pp[i]]}
    return out


def uygula(fx, season, P, today, U):
    """Bayrak açıksa oransız yaklaşan maçlara kp/ko/kpy yazar. Dönüş: yazılan maç sayısı."""
    A = ayar()
    if not A or not A.get("aktif") or _geri_alma_aktif(): return 0
    T = tahmin(fx, season, P, today, U, A)
    n = 0
    for f in fx:
        z = T.get((f.get("lg"), f.get("d"), f.get("h"), f.get("a")))
        if not z or f.get("odds"): continue
        f["kp"] = z["p"]; f["kpy"] = "guc"; n += 1
        if A.get("ko_aktif"): f["ko"] = z["o"]; f["kpo"] = "guc"     # 2,5 üst ayrı kapı
    return n
