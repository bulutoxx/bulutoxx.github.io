#!/usr/bin/env python3
"""OXXai Basketbol motoru.

Her çalıştırmada:
  1. NBA, WNBA, NCAA, NBL (ESPN) ve EuroLeague, EuroCup (resmî EuroLeague akışı) maçlarını ve çeyrek skorlarını indirir.
  2. Her lig için hücum/savunma gücü modelini (ağırlıklı ridge regresyon) kurar.
  3. Geçmiş maçları hafta hafta, hiç oynanmamış gibi tahmin edip gerçek skorla karşılaştırır (geriye dönük test)
     ve ayarlarını (zaman ağırlığı, düzenleme gücü) bu testte en az hatayı verecek şekilde kendisi seçer.
  4. Yaklaşan maçların tahminini maçtan önce kilitler, sonuçlanınca puanlar (gerçek ileriye dönük karne).
Çıktı: data/basket.json (uygulama), data/bk_games.json (geçmiş), data/bk_predlog.json (kilitli tahminler).
Ücretsiz kaynaklar, anahtar gerekmez. Claude'a bağlı değildir.
"""
import gzip, json, math, os, sys, time, urllib.request
from datetime import date, datetime, timedelta, timezone
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = "Mozilla/5.0 (BULUTOXX; +https://bulutoxx.github.io)"

# lig anahtarı: (kaynak, kod, görünen ad, çeyrek süresi dk, aylar)
LEAGUES = {
    "nba":  ("espn", "nba", "NBA", 12),
    "el":   ("euro", "E", "EuroLeague", 10),
    "ec":   ("euro", "U", "EuroCup", 10),
    "wnba": ("espn", "wnba", "WNBA", 10),
    "nbl":  ("espn", "nbl", "NBL Avustralya", 10),
    "ncaa": ("espn", "mens-college-basketball", "NCAA (ABD Üniversite)", 20),
    "ncaaw": ("espn", "womens-college-basketball", "NCAA Kadınlar", 10),
    "gl": ("espn", "nba-development", "NBA G League", 12),
}
HIST_DAYS = 560          # yaklaşık iki sezon
FIX_DAYS = 8
KS = {}
ENGINE_V = "2026-10-27.1"   # NCAAW ev avantajı ön bilgisi (HCA_K)
STORE_V = 2              # veri biçimi sürümü             # kaç gün sonrasına kadar fikstür

def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=30) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
                return json.loads(b.decode("utf-8"))
        except Exception as e:
            last = e; time.sleep(1.5 * (i + 1))
    raise last

# ---------------------------------------------------------------- indirme
def parse_espn_event(e, lg):
    c = e["competitions"][0]
    st = e.get("status", {}).get("type", {})
    stype = (e.get("season") or {}).get("type")
    if stype is not None and stype not in (2, 3): return None      # hazırlık, All-Star vb. maçlar sayılmaz
    cs = {t["homeAway"]: t for t in c["competitors"]}
    if "home" not in cs or "away" not in cs: return None
    def side(t):
        tm = t["team"]
        q = [float(x.get("value", 0) or 0) for x in (t.get("linescores") or [])]
        return {"n": tm.get("displayName") or tm.get("name"), "ab": tm.get("abbreviation", ""), "logo": tm.get("logo", ""),
                "s": int(float(t.get("score") or 0)), "q": [int(x) for x in q]}
    h, a = side(cs["home"]), side(cs["away"])
    g = {"id": "e" + str(e["id"]), "lg": lg, "dt": e["date"], "h": h["n"], "a": a["n"], "neutral": bool(c.get("neutralSite")),
         "state": st.get("state", "pre"), "hl": h["logo"], "al": a["logo"], "hab": h["ab"], "aab": a["ab"]}
    if "conferenceCompetition" in c: g["conf"] = bool(c.get("conferenceCompetition"))   # kolej: konferans içi maç (ileride ayrı ev avantajı için)
    if g["state"] == "post" and st.get("completed", True):
        if h["s"] + a["s"] == 0: return None
        g.update(hs=h["s"], as_=a["s"], hq=h["q"], aq=a["q"])
    elif g["state"] == "in":
        g.update(hs=h["s"], as_=a["s"], hq=h["q"], aq=a["q"], clock=e.get("status", {}).get("type", {}).get("shortDetail", ""))
    od = (c.get("odds") or [None])[0]
    if od:
        try:
            sp = od.get("spread"); ou = od.get("overUnder")
            g["odds"] = {"spread": float(sp) if sp is not None else None, "ou": float(ou) if ou is not None else None, "det": od.get("details", "")}
        except Exception: pass
    return g

def espn_month(slug, ym, lg):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{slug}/scoreboard?dates={ym}&limit=1000"
    if "college-basketball" in slug: url += "&groups=50"
    d = fetch(url)
    return [g for g in (parse_espn_event(e, lg) for e in d.get("events", [])) if g]

def espn_day(slug, ymd, lg):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{slug}/scoreboard?dates={ymd}&limit=500"
    if "college-basketball" in slug: url += "&groups=50"
    d = fetch(url)
    return [g for g in (parse_espn_event(e, lg) for e in d.get("events", [])) if g]

def euro_season(comp, code, lg):
    d = fetch(f"https://api-live.euroleague.net/v2/competitions/{comp}/seasons/{code}/games")
    out = []
    for x in d.get("data", []):
        try:
            L, R = x["local"], x["road"]
            if L["club"].get("isVirtual") or R["club"].get("isVirtual"): continue
            dt = x.get("utcDate") or x.get("date")
            if dt and not dt.endswith("Z"): dt = dt + "Z"
            g = {"id": "u" + x["identifier"], "lg": lg, "dt": dt, "h": L["club"]["name"], "a": R["club"]["name"],
                 "hl": (L["club"].get("images") or {}).get("crest", ""), "al": (R["club"].get("images") or {}).get("crest", ""),
                 "hab": L["club"].get("code", ""), "aab": R["club"].get("code", ""),
                 "neutral": bool(x.get("isNeutralVenue")), "state": "post" if x.get("played") else "pre",
                 "phase": (x.get("phaseType") or {}).get("name", ""), "round": x.get("roundName", "")}
            if x.get("played"):
                pq = lambda p: [int(p.get(f"partials{i}") or 0) for i in range(1, 5)] + [int(v or 0) for v in (p.get("extraPeriods") or {}).values()]
                g.update(hs=int(L["score"]), as_=int(R["score"]), hq=pq(L.get("partials") or {}), aq=pq(R.get("partials") or {}))
                if g["hs"] + g["as_"] == 0: continue
            out.append(g)
        except Exception:
            continue
    return out

def season_year(today):
    return today.year if today.month >= 7 else today.year - 1

def months_between(a, b):
    y, m = a.year, a.month
    while (y, m) <= (b.year, b.month):
        yield f"{y}{m:02d}"
        m += 1
        if m == 13: y, m = y + 1, 1

def download(lg, store, today, log):
    src, code, name, qlen = LEAGUES[lg]
    if store.get("v") != STORE_V: store = {}                         # veri biçimi değişti: baştan indir
    games = {g["id"]: g for g in store.get("g", [])}
    fixtures, live = [], []
    done = set(store.get("done", []))
    if src == "espn":
        start = today - timedelta(days=HIST_DAYS)
        n_new = 0
        for ym in months_between(start, today):
            y, m = int(ym[:4]), int(ym[4:])
            month_end = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
            if ym in done: continue
            try:
                if "college-basketball" in code:
                    # NCAA çok kalabalık: ayı haftalık parçalar yerine gün gün çek (yalnızca sezon ayları)
                    if m in (5, 6, 7, 8, 9, 10): done.add(ym); continue
                    got = []
                    d0 = date(y, m, 1)
                    while d0 <= min(month_end, today):
                        try: got += espn_day(code, d0.strftime("%Y%m%d"), lg)
                        except Exception: pass
                        d0 += timedelta(days=1)
                else:
                    got = espn_month(code, ym, lg)
            except Exception as e:
                log[f"{lg}-{ym}"] = f"hata: {e}"; continue
            for g in got:
                if g["state"] == "post" and "hs" in g: games[g["id"]] = g; n_new += 1
            if (today - month_end).days > 4: done.add(ym)
        log[lg] = n_new
        for k in range(-1, FIX_DAYS):
            dd = today + timedelta(days=k)
            try:
                for g in espn_day(code, dd.strftime("%Y%m%d"), lg):
                    if g["state"] == "post" and "hs" in g: games[g["id"]] = g
                    elif g["state"] == "in": live.append(g); fixtures.append(g)
                    else: fixtures.append(g)
            except Exception as e:
                log[f"{lg}-fx{k}"] = f"hata: {e}"
    else:
        sy = season_year(today)
        n_new = 0
        for yy in (sy - 1, sy):
            sc = f"{code}{yy}"
            if sc in done: continue
            try: got = euro_season(code, sc, lg)
            except Exception as e:
                log[f"{lg}-{sc}"] = f"hata: {e}"; continue
            for g in got:
                if g["state"] == "post": games[g["id"]] = g; n_new += 1
                else:
                    t = datetime.fromisoformat(g["dt"].replace("Z", "+00:00")).date()
                    if today - timedelta(days=1) <= t <= today + timedelta(days=FIX_DAYS): fixtures.append(g)
            if yy < sy and got and all(g["state"] == "post" for g in got): done.add(sc)
        log[lg] = n_new
    cut = (today - timedelta(days=HIST_DAYS)).isoformat()
    gl = sorted((g for g in games.values() if g["dt"][:10] >= cut), key=lambda g: g["dt"])
    for g in gl:
        for k in ("state", "clock", "odds"): g.pop(k, None)
    return {"v": STORE_V, "g": gl, "done": sorted(done), "asOf": gl[-1]["dt"][:10] if gl else ""}, fixtures

# ---------------------------------------------------------------- model
def days(g, ref):
    return (ref - datetime.fromisoformat(g["dt"].replace("Z", "+00:00")).date()).days

# Ev avantajı takım güçleriyle birlikte kestirilen ligler. Kolejde güçlü takımlar zayıflarını evde ağırlar;
# ham "ev sahibi ortalama farkı" bu yüzden ev avantajını şişirir. İleriye dönük testte (lab/bk_gelistir.py,
# data/bk_gelistir.json) log-loss ve Brier iki zaman diliminde de belirgin düştü, isabet arttı. Profesyonel
# liglerde etki yoktu, oralarda eski yol kalır. Geri almak için kümeyi boşaltmak yeter.
HCA_JOINT = {"ncaa", "ncaaw"}

# 🏠 Ev avantajı ön bilgisi (2026-10-27, denetim P1 "NCAA ev farkı sapması"). Ortak kestirimde ev avantajı cezasızdı; sezon
# başında güçlü takımlar zayıfları evinde ağırladığı için (dengesiz takvim) ridge'in küçülttüğü takım farkını ev avantajı
# emiyordu: tek sezonluk ileri yürüyüşte NCAA kestirimi 15 Kasım 14,3 → 10 Ocak 5,4 → sezon sonu 3,6 sayı; ocakta tahmin edilen
# ev farkı 5,4, gerçek 2,5. Çözüm: ev avantajını EV-DEPLASMAN EŞLEŞMELERİNDEN öğrenilen değere doğru küçült. A–B hem A'nın hem
# B'nin evinde oynadıysa iki maçın ev farkı ortalamasında takım gücü birbirini götürür (konferans maçları); zaman ağırlıklı
# (HCA_HD) ve tarafsız sahalar hariç. Eşleşme azsa (sezonun ilk haftaları, geçmiş sezon yoksa) HCA_PRIOR kullanılır.
# HCA_K: ön bilginin gücü (maç eşdeğeri). Seçim: haftalık ileri yürüyüş (her maç yalnız önceki maçlarla), κ DİĞER kolej liginde
# seçildi, bu ligin tüm sezonunda bk_gelistir kapısı (gün kümeli bootstrap; tüm + iki zaman dilimi; LL GA üst < 0, Brier < 0,
# isabet düşmez). NCAAW κ=6400: LL 0,4735 → 0,4713 (Δ −0,0023 [−0,0037, −0,0009]), iki dilimde de GA < 0, isabet +0,3 puan,
# ev farkı sapması −0,47 → +0,03 sayı → KABUL. NCAA κ=1e6: LL 0,5628 → 0,5546 (Δ −0,0082 [−0,0127, −0,0038]), sapma −1,62 → +0,57,
# ama ikinci dilimde Δ −0,0019 [−0,0055, +0,0017] ve isabet −0,4 puan → RET (yeni sezon verisiyle yeniden sınanmalı).
# Kasım–Aralık/Ocak–Nisan ayrı ev avantajı (dönem vekili) iki ligde de tek ön bilgiden kötü çıktı, eklenmedi.
HCA_K = {"ncaaw": 6400.0}
HCA_PRIOR = {"ncaa": 3.0, "ncaaw": 3.0}      # yalnız eşleşme verisi yokken (NCAA uzun dönem ev avantajı ≈3 sayı)
HCA_HD, HCA_MIN_PAIR = 0.0035, 100           # eşleşme zaman ağırlığı (yarı ömür ≈200 gün), en az eşleşme sayısı

def hca_pairs(games, ref, hd=HCA_HD):
    """Ev-deplasman eşleşmelerinden yalın ev avantajı: (kestirim, eşleşme sayısı)."""
    by = {}
    for g in games:
        if g.get("neutral"): continue
        w = math.exp(-hd * max(0, days(g, ref))); a = by.setdefault((g["h"], g["a"]), [0.0, 0.0])
        a[0] += w * (g["hs"] - g["as_"]); a[1] += w
    num = den = 0.0; npair = 0
    for (h, a), (s1, w1) in by.items():
        if h < a and (a, h) in by:
            s2, w2 = by[(a, h)]; ww = 2.0 / (1.0 / w1 + 1.0 / w2)
            num += ww * (s1 / w1 + s2 / w2) / 2.0; den += ww; npair += 1
    return (num / den if den > 0 else None), npair

def hca_prior(games, ref, lg):
    h, npair = hca_pairs(games, ref)
    if h is None or npair < HCA_MIN_PAIR: return HCA_PRIOR.get(lg, 3.0), npair, "varsayilan"
    return h, npair, "eslesme"

def fit(games, ref, P, joint=None):
    """Ağırlıklı ridge: ev sayısı = mu + hca + hücum(ev) + savunma(dep), dep sayısı = mu + hücum(dep) + savunma(ev)."""
    if len(games) < 20: return None
    if joint is None: joint = games[0].get("lg") in HCA_JOINT
    teams = sorted({g["h"] for g in games} | {g["a"] for g in games}); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
    w = np.array([math.exp(-P["decay"] * max(0, days(g, ref))) for g in games])
    hs = np.array([g["hs"] for g in games], float); as_ = np.array([g["as_"] for g in games], float)
    neu = np.array([g.get("neutral", False) for g in games])
    mu = float(np.sum(w * (hs + as_)) / (2 * np.sum(w)))
    hi = np.array([ix[g["h"]] for g in games]); ai = np.array([ix[g["a"]] for g in games])
    if joint:   # bilinmeyenler: hücum(n), savunma(n), ev avantajı(1); ev avantajına yok denecek kadar küçük ceza (HCA_K ligleri: ön bilgi)
        K = 2 * n + 1; M = np.zeros((K, K)); b = np.zeros(K); c = np.where(neu, 0.0, 0.5)
        for (o, d, y, s) in ((hi, ai, hs - mu, c), (ai, hi, as_ - mu, -c)):
            oi, di = o, n + d; hh = np.full(len(o), 2 * n)
            for (r1, r2, v) in ((oi, oi, w), (di, di, w), (oi, di, w), (di, oi, w),
                                (oi, hh, w * s), (hh, oi, w * s), (di, hh, w * s), (hh, di, w * s), (hh, hh, w * s * s)):
                np.add.at(M, (r1, r2), v)
            np.add.at(b, oi, w * y); np.add.at(b, di, w * y); np.add.at(b, hh, w * s * y)
        M[np.diag_indices(2 * n)] += P["lam"]; M[2 * n, 2 * n] += 1e-3
        lg = games[0].get("lg"); hk = HCA_K.get(lg, 0.0); hp = None
        if hk > 0:   # ön bilgi: ½·hk·(hca − h0)²  (bir tarafsız olmayan maç ev avantajı denklemine 0,5·w katar)
            h0, npair, src = hca_prior(games, ref, lg); M[2 * n, 2 * n] += 0.5 * hk; b[2 * n] += 0.5 * hk * h0
            hp = {"h0": round(float(h0), 2), "eslesme": npair, "kaynak": src, "k": hk}
        x = np.linalg.solve(M, b)
        return {"teams": teams, "ix": ix, "off": x[:n], "def": x[n:2 * n], "mu": mu, "hca": float(x[2 * n]), "hca_prior": hp}
    hca = float(np.sum(w[~neu] * (hs - as_)[~neu]) / max(1e-9, np.sum(w[~neu]))) if (~neu).any() else 0.0
    hcaH = np.where(neu, 0, hca / 2); hcaA = np.where(neu, 0, -hca / 2)
    yh = hs - mu - hcaH; ya = as_ - mu - hcaA
    M = np.zeros((2 * n, 2 * n)); b = np.zeros(2 * n)
    # ev denklemi: off[h] + def[a]
    for (o, d, y) in ((hi, ai, yh), (ai, hi, ya)):
        oi, di = o, n + d
        np.add.at(M, (oi, oi), w); np.add.at(M, (di, di), w); np.add.at(M, (oi, di), w); np.add.at(M, (di, oi), w)
        np.add.at(b, oi, w * y); np.add.at(b, di, w * y)
    M[np.diag_indices(2 * n)] += P["lam"]
    x = np.linalg.solve(M, b)
    off, dfn = x[:n], x[n:]
    return {"teams": teams, "ix": ix, "off": off, "def": dfn, "mu": mu, "hca": hca}

def pred_means(F, h, a, neutral=False, newp=None):
    """Lige yeni gelen takım: öğrenilmiş ön bilgi (hücum, savunma) kullanılır; yoksa tahmin yapılmaz."""
    if F is None: return None
    def rt(t):
        if t in F["ix"]: i = F["ix"][t]; return F["off"][i], F["def"][i]
        return tuple(newp) if newp is not None else None
    rh, ra = rt(h), rt(a)
    if rh is None or ra is None: return None
    hh = 0 if neutral else F["hca"] / 2
    return F["mu"] + hh + rh[0] + ra[1], F["mu"] - hh + ra[0] + rh[1]

def backtest(games, P, min_train=120, H=0):
    """Hafta hafta: o haftaya kadarki maçlarla eğit, o haftanın maçlarını tahmin et."""
    if len(games) < min_train + 30: return []
    rows = []
    d0 = datetime.fromisoformat(games[min_train]["dt"].replace("Z", "+00:00")).date()
    last = datetime.fromisoformat(games[-1]["dt"].replace("Z", "+00:00")).date()
    wk = d0
    gi = 0
    dts = [datetime.fromisoformat(g["dt"].replace("Z", "+00:00")).date() for g in games]
    while wk <= last:
        nxt = wk + timedelta(days=7)
        cut = wk - timedelta(days=H)
        train = [g for g, d in zip(games, dts) if d < cut and (cut - d).days <= 400]
        test = [g for g, d in zip(games, dts) if wk <= d < nxt]
        if test and len(train) >= min_train:
            F = fit(train, cut, P)
            for g in test:
                pm = pred_means(F, g["h"], g["a"], g.get("neutral", False), P.get("newp"))
                if pm: rows.append((g, pm[0], pm[1]))
        wk = nxt
    return rows

def score_rows(rows, late=None, split=None):
    if split is not None: rows = [r for r in rows if (r[0]["dt"] >= split) == late]
    if not rows: return None
    eh = np.array([r[0]["hs"] - r[1] for r in rows]); ea = np.array([r[0]["as_"] - r[2] for r in rows])
    return float(np.mean(eh ** 2 + ea ** 2))

def tune(games, lg, prev=None):
    """Ayarları ilk %70 maçta öğren, son %30 maçta doğrula. Doğrulamada kötüleşen değişiklik kabul edilmez (ezber koruması)."""
    grid_d = [0.0, 0.004, 0.008, 0.015, 0.03]; grid_l = [1.0, 3.0, 8.0, 20.0, 50.0]
    grid_n = [[0.0, 0.0], [-3.0, 3.0], [-6.0, 6.0]]
    P0 = {"decay": 0.008, "lam": 8.0, "newp": [0.0, 0.0]}
    if prev: P0.update({k: v for k, v in prev.items() if k in P0})
    if P0.get("newp") is None: P0["newp"] = [0.0, 0.0]
    mt = 200 if lg in ("ncaa", "ncaaw") else 80
    rows0 = backtest(games, P0, mt)
    if not rows0: return P0, None, None
    split = sorted(r[0]["dt"] for r in rows0)[int(len(rows0) * .7)]
    P = dict(P0); best = score_rows(rows0, False, split)
    for _ in range(2):
        for k, grid in (("decay", grid_d), ("lam", grid_l), ("newp", grid_n)):
            for v in grid:
                if v == P.get(k): continue
                Q = dict(P, **{k: v}); s = score_rows(backtest(games, Q, mt), False, split)
                if s is not None and s < best - 1e-9: best, P = s, Q
    # doğrulama: yalnızca eski ayarın da tahmin ettiği maçlarda karşılaştır (adil kıyas)
    ids0 = {r[0]["id"] for r in rows0}
    late0 = score_rows(rows0, True, split); rows1 = backtest(games, P, mt)
    late1 = score_rows([r for r in rows1 if r[0]["id"] in ids0], True, split)
    ok = late1 is not None and late0 is not None and late1 <= late0 + 1e-6
    guard = {"son30_eski": round(late0, 2) if late0 else None, "son30_yeni": round(late1, 2) if late1 else None, "kabul": bool(ok)}
    return (P if ok else P0), guard, split

def reg_quarters(q, halves):
    """Normal süre periyotlarını 4 çeyreğe çevir (NCAA iki devre oynar: her devre ikiye bölünür)."""
    q = q or []
    if halves:
        if len(q) < 2: return None
        return [q[0] / 2, q[0] / 2, q[1] / 2, q[1] / 2]
    return [float(x) for x in q[:4]] if len(q) >= 4 else None

def quarter_shares(games, halves=False):
    sh = np.zeros(4); n = 0
    for g in games:
        for q in (reg_quarters(g.get("hq"), halves), reg_quarters(g.get("aq"), halves)):
            if q and sum(q) > 0:
                sh += np.array(q, float) / sum(q); n += 1
    return [round(float(x), 4) for x in (sh / n if n else np.array([.25, .25, .25, .25]))]

def phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def metrics(rows, sm, st, shares, halves=False):
    if not rows: return None
    n = len(rows)
    win = np.mean([((r[1] > r[2]) == (r[0]["hs"] > r[0]["as_"])) for r in rows])
    mar = np.array([(r[0]["hs"] - r[0]["as_"]) - (r[1] - r[2]) for r in rows])
    tot = np.array([(r[0]["hs"] + r[0]["as_"]) - (r[1] + r[2]) for r in rows])
    home = np.mean([r[0]["hs"] > r[0]["as_"] for r in rows])
    # olasılık kalibrasyonu (log-loss): kazanma olasılığı Φ(fark/σ)
    ll = np.mean([-math.log(max(1e-6, phi((r[1] - r[2]) / sm) if r[0]["hs"] > r[0]["as_"] else 1 - phi((r[1] - r[2]) / sm))) for r in rows])
    h1 = []
    for r in rows:
        qh, qa = reg_quarters(r[0].get("hq"), halves), reg_quarters(r[0].get("aq"), halves)
        if qh and qa: h1.append((r, qh[0] + qh[1], qa[0] + qa[1]))
    s2 = shares[0] + shares[1]
    hv = [((r[1] - r[2]) * s2 > 0) == (hh > aa) for r, hh, aa in h1 if hh != aa]
    h1w = np.mean(hv) if hv else None
    conf = [r for r in rows if abs(phi((r[1] - r[2]) / sm) - .5) >= .25]
    return {"n": n, "win": round(float(win), 4), "home_base": round(float(home), 4), "logloss": round(float(ll), 4),
            "mae_margin": round(float(np.mean(np.abs(mar))), 2), "mae_total": round(float(np.mean(np.abs(tot))), 2),
            "tot10": round(float(np.mean(np.abs(tot) <= 10)), 4), "mar5": round(float(np.mean(np.abs(mar) <= 5)), 4),
            "h1_win": round(float(h1w), 4) if h1w is not None else None,
            "conf_n": len(conf), "conf_win": round(float(np.mean([((r[1] > r[2]) == (r[0]["hs"] > r[0]["as_"])) for r in conf])), 4) if conf else None}

# ---------------------------------------------------------------- yardımcılar
def current_season(games, today):
    """Bu sezon: son 60+ günlük aradan sonraki maçlar."""
    if not games: return []
    dts = [datetime.fromisoformat(g["dt"].replace("Z", "+00:00")).date() for g in games]
    start = dts[0]
    for i in range(1, len(dts)):
        if (dts[i] - dts[i - 1]).days >= 45: start = dts[i]
    return [g for g, d in zip(games, dts) if d >= start]

def team_table(games, cur, F, logos):
    tb = {}
    for g in cur:
        for t, s, o, w in ((g["h"], g["hs"], g["as_"], g["hs"] > g["as_"]), (g["a"], g["as_"], g["hs"], g["as_"] > g["hs"])):
            r = tb.setdefault(t, {"w": 0, "l": 0, "pf": 0, "pa": 0})
            r["w" if w else "l"] += 1; r["pf"] += s; r["pa"] += o
    out = {}
    for t in (F["teams"] if F else sorted(tb)):
        i = F["ix"][t] if F else None
        form = []
        for g in reversed(games):
            if g["h"] == t or g["a"] == t:
                me, op = (g["hs"], g["as_"]) if g["h"] == t else (g["as_"], g["hs"])
                form.append({"d": g["dt"][:10], "o": g["a"] if g["h"] == t else g["h"], "s": f"{me}-{op}", "r": "G" if me > op else "M", "ev": g["h"] == t})
                if len(form) == 5: break
        r = tb.get(t, {"w": 0, "l": 0, "pf": 0, "pa": 0}); gp = r["w"] + r["l"]
        out[t] = {"w": r["w"], "l": r["l"], "ppg": round(r["pf"] / gp, 1) if gp else None, "oppg": round(r["pa"] / gp, 1) if gp else None,
                  "off": round(float(F["off"][i]), 2) if F else 0, "def": round(float(F["def"][i]), 2) if F else 0,
                  "logo": logos.get(t, {}).get("l", ""), "ab": logos.get(t, {}).get("ab", ""), "form": form}
    return out

def pick_score(mh, ma, shares):
    """Tutarlı tahmini skor: MS, İY, 2Y ve çeyrekler birbirine eşit toplanır; beraberlik olmaz."""
    H, A = int(round(mh)), int(round(ma))
    if H == A:
        if mh >= ma: H += 1
        else: A += 1
    s1 = shares[0] + shares[1]
    h1, a1 = int(round(mh * s1)), int(round(ma * s1))
    if h1 == a1:
        if mh >= ma: h1 += 1
        else: a1 += 1
    q1h, q1a = int(round(mh * shares[0])), int(round(ma * shares[0]))
    q3h, q3a = int(round(mh * shares[2])), int(round(ma * shares[2]))
    return {"ms": [H, A], "iy": [h1, a1], "y2": [H - h1, A - a1], "q": [[q1h, q1a], [h1 - q1h, a1 - q1a], [q3h, q3a], [H - h1 - q3h, A - a1 - q3a]]}

# ---------------------------------------------------------------- tahmin günlüğü
def dinlenme_hazirla(fixtures, store_games):
    """YH-04: fikstür → (Δfark, uygulanıyor mu). Takvim = arşivdeki maçlar + fikstürler (yalnız tarih/saha; sonuç kullanılmaz)."""
    try:
        import bk_dinlenme as BD
        A = BD.ayar(); beta = A.get("beta") or {}; K = A.get("kullan") or {}
        tak = [g for st in store_games.values() for g in st.get("g", [])] + [f for f in fixtures if f.get("lg") in LEAGUES]
        X = BD.ozellikler(tak); out = {}
        for f in fixtures:
            g = BD.GRUP.get(f.get("lg"))
            if g and beta.get(g) and f["id"] in X:
                out[f["id"]] = (round(BD.delta(X[f["id"]], beta[g]), 2), bool(K.get(g)))
        return out
    except Exception as e:
        print("dinlenme düzeltmesi atlandı:", e.__class__.__name__, str(e)[:120], flush=True); return {}


def lock_and_grade(plog, fixtures, fits, Ps, store_games, today, YD=None):
    import bk_piyasa as BP
    YD = YD or {}
    try:   # 🩹 YH-16 gölge: taze sakatlık sinyali (kilitli tahmini değiştirmez; maç başlayana dek skg tazelenir)
        import bk_sakatlik as BS; SK = BS.sinyal_hazir()
    except Exception as ex:
        BS = None; SK = {}; print("sakatlık sinyali atlandı:", ex.__class__.__name__, str(ex)[:120], flush=True)
    def _sk(e):
        s = BS.mac_sinyali(SK, e) if (BS and SK) else None
        if s: e["skg"] = s; e.setdefault("skg0", s)
    have = {e["id"] for e in plog}
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    fx = {f["id"]: f for f in fixtures}
    # 📈 piyasa anlık görüntüsü (denetim U8): kilitli tahmin değişmez; piyasa oranı maç başlayana dek tazelenir (pz = son,
    # pz0 = kilit anı). Ölçüm maç öncesi SON görüntüyle yapılır; maç başladıktan sonra hiç yazılmaz (sızıntı yok).
    for e in plog:
        f = fx.get(e["id"])
        if e.get("r") is not None or not f or f.get("state") in ("in", "post") or f.get("live") or f["dt"][:16] <= now_iso: continue
        pz = BP.pz_al(f)
        if pz: e["pz"] = dict(pz, ts=now_iso + "Z"); e.setdefault("pz0", e["pz"])
        e.setdefault("dt", f["dt"])
        _sk(e)
    for f in fixtures:
        if f["id"] in have or f.get("state") in ("in", "post") or f.get("live") or f["dt"][:16] <= now_iso: continue
        F = fits.get(f["lg"]); pm = pred_means(F, f["h"], f["a"], f.get("neutral", False), Ps.get(f["lg"], {}).get("newp")) if F else None
        if not pm: continue
        k_ = KS.get(f["lg"], 1.0); pm = (((pm[0] + pm[1]) + k_ * (pm[0] - pm[1])) / 2, ((pm[0] + pm[1]) - k_ * (pm[0] - pm[1])) / 2)
        yd, yon = YD.get(f["id"], (None, False))
        if yd is not None and yon: pm = (pm[0] + yd / 2, pm[1] - yd / 2)      # 😴 YH-04 üretimde: dinlenme düzeltmesi kilide girer
        e = {"id": f["id"], "lg": f["lg"], "d": f["dt"][:10], "dt": f["dt"], "h": f["h"], "a": f["a"], "ph": round(pm[0], 1), "pa": round(pm[1], 1),
             "v": ENGINE_V, "ts": now_iso + "Z"}
        if yd is not None: e["yd" if yon else "ydg"] = yd                    # yd: uygulandı · ydg: yalnız gölge ölçümü
        if f.get("odds"): e["odds"] = f["odds"]
        pz = BP.pz_al(f)
        if pz: e["pz"] = dict(pz, ts=now_iso + "Z"); e["pz0"] = e["pz"]
        _sk(e)
        plog.append(e); have.add(f["id"])
    res = {}
    for lg, st in store_games.items():
        for g in st["g"]: res[g["id"]] = g
    for e in plog:
        if e.get("r") is None and e["id"] in res:
            g = res[e["id"]]; e["r"] = [g["hs"], g["as_"]]
    cut = (today - timedelta(days=200)).isoformat()
    return [e for e in plog if e["d"] >= cut]

def live_report(plog, today, sm=None):
    def st(es):
        es = [e for e in es if e.get("r")]
        if not es: return None
        win = np.mean([((e["ph"] > e["pa"]) == (e["r"][0] > e["r"][1])) for e in es])
        mt = np.mean([abs((e["r"][0] + e["r"][1]) - (e["ph"] + e["pa"])) for e in es])
        out = {"n": len(es), "win": round(float(win), 4), "mae_total": round(float(mt), 2)}
        oo = [e for e in es if e.get("odds") and e["odds"].get("ou")]
        if oo:
            out["ou_n"] = len(oo)
            vv = [((e["ph"] + e["pa"]) > e["odds"]["ou"]) == ((e["r"][0] + e["r"][1]) > e["odds"]["ou"]) for e in oo if (e["r"][0] + e["r"][1]) != e["odds"]["ou"]]
            out["ou"] = round(float(np.mean(vv)), 4) if vv else None
        return out
    cut = (today - timedelta(days=30)).isoformat()
    out = {"all": st(plog), "d30": st([e for e in plog if e["d"] >= cut]), "pending": sum(1 for e in plog if e.get("r") is None)}
    try: import guvenilirlik as GV; out["guvenilirlik"] = GV.karne_basket(plog, sm)   # YH-09: Brier ayrışımı + ECE (kilitli, sonuçlanmış)
    except Exception as ex: print("güvenilirlik atlandı:", ex.__class__.__name__, ex, flush=True)
    return out

def learn_market(plog):
    """Oranı olan geçmiş maçlarda model ile piyasa çizgisinin en iyi karışımını öğren (yeterli veri olunca)."""
    es = [e for e in plog if e.get("r") and e.get("odds") and e["odds"].get("spread") is not None and e["odds"].get("ou")]
    if len(es) < 60: return None, len(es)
    best, bw = None, 0.5
    for w in (0, .25, .5, .75, 1):
        err = 0
        for e in es:
            mm = e["ph"] - e["pa"]; tm = e["ph"] + e["pa"]
            mk_m = -e["odds"]["spread"]; mk_t = e["odds"]["ou"]
            pmar = (1 - w) * mm + w * mk_m; ptot = (1 - w) * tm + w * mk_t
            err += ((e["r"][0] - e["r"][1]) - pmar) ** 2 + ((e["r"][0] + e["r"][1]) - ptot) ** 2
        if best is None or err < best: best, bw = err, w
    return bw, len(es)

# ---------------------------------------------------------------- ana akış
def iddaa_bk(fixtures, out_lg):
    """Resmi iddaa basketbol bülteni: ESPN maçlarına iddaa oranı eklenir; bizde olmayan maçlar
    (Türkiye BSL dahil) yarışma başına sentetik bir 'piyasa ligi' ile bültene girer. Tahmin tamamen orandan:
    MS oranından beklenen fark, alt/üst çizgisinden beklenen toplam."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import iddaa as ID
    from statistics import NormalDist
    N = NormalDist()
    evs = ID.fetch(2)
    def ts(f):
        try: return datetime.fromisoformat(f["dt"].replace("Z", "+00:00")).timestamp()
        except Exception: return None
    fk = [(f, ts(f)) for f in fixtures]
    used = set(); extra = []; syn = {}; nm = 0
    comp_tot = {}
    for e in evs:
        if e["mk"].get("tot"): comp_tot.setdefault(e["ci"], []).append(e["mk"]["tot"][0])
    for e in evs:
        best, bs = None, 0
        for j, (f, t) in enumerate(fk):
            if j in used or t is None or abs(t - e["ts"]) > 3 * 3600: continue
            sh, sa = ID.sim(e["h"], f["h"]), ID.sim(e["a"], f["a"])
            if min(sh, sa) < 0.5 or sh + sa < 1.4: continue
            if sh + sa > bs: best, bs = j, sh + sa
        mk = e["mk"]; o1, o2 = mk["ms"]
        p = (1 / o1) / (1 / o1 + 1 / o2)
        tot = mk["tot"][0] if mk.get("tot") else (float(np.median(comp_tot[e["ci"]])) if comp_tot.get(e["ci"]) else None)
        if best is not None:
            used.add(best); f = fk[best][0]; nm += 1
            f["io"] = mk["ms"]; f["iid"] = e["iid"]
            if mk.get("tot"): f["itot"] = mk["tot"]
            if mk.get("hnd"): f["ihnd"] = mk["hnd"]
            continue
        if tot is None: tot = 160.0
        sm = max(8.0, 0.075 * tot)                          # fark belirsizliği toplamla ölçeklenir (NBA ~15, Avrupa ~12)
        mar = sm * N.inv_cdf(min(max(p, 0.02), 0.98))
        lg = f"i{e['ci']}"
        if lg not in syn:
            syn[lg] = {"name": e["comp"], "syn": True, "cc": e["cc"], "qlen": 10, "halves": False, "mu": round(tot / 2, 1), "hca": 0.0,
                       "sm": round(sm, 2), "st": round(max(10.0, 0.1 * tot), 2), "shares": [0.25, 0.25, 0.25, 0.25], "newp": [0.0, 0.0], "teams": {}}
        extra.append({"id": f"i{e['iid']}", "lg": lg, "dt": datetime.fromtimestamp(e["ts"], timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                      "h": e["h"], "a": e["a"], "neutral": False, "odds": {"spread": round(-mar, 1), "ou": tot}, "io": mk["ms"], "iid": e["iid"], "src": "iddaa"})
    print(f"iddaa basketbol: {len(evs)} maç · {nm} eşleşti · {len(extra)} yeni · {len(syn)} yarışma", flush=True)
    return extra, syn

def gece_isi():
    """Günde bir (İstanbul 03:00'ten sonra ilk çalışma): YH-04 dinlenme kapısı yeniden sınaması ve YH-05 canlı kayıt puanlama + kapı."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Europe/Istanbul"))
    except Exception:
        now = datetime.now(timezone(timedelta(hours=3)))
    if now.hour < 3 and "--gece" not in sys.argv: return
    try:
        import bk_canli as BC
        if (BC.ayar().get("gece_tarih") == now.date().isoformat()) and "--gece" not in sys.argv: return
        A = BC.gece(now.date())
        print("🏀🔴 canlı kapı:", json.dumps({k: A.get(k) for k in ("kullan", "prm", "veri", "karar")}, ensure_ascii=False), flush=True)
    except Exception as e:
        print("canlı kapı atlandı:", e.__class__.__name__, str(e)[:160], flush=True)
    try:
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(ROOT, "lab", "bk_dinlenme_lab.py"), "--yaz"], capture_output=True, text=True, timeout=900)
        print("😴 dinlenme kapısı:", (r.stdout.strip().splitlines() or ["?"])[-1][:300], flush=True)
    except Exception as e:
        print("dinlenme kapısı atlandı:", e.__class__.__name__, str(e)[:160], flush=True)


def main():
    offline = "--offline" in sys.argv
    today = date.today()
    gp = os.path.join(DATA, "bk_games.json"); op = os.path.join(DATA, "basket.json"); pp = os.path.join(DATA, "bk_predlog.json")
    store = json.load(open(gp, encoding="utf-8")) if os.path.exists(gp) else {}
    old = json.load(open(op, encoding="utf-8")) if os.path.exists(op) else {}
    log, fixtures = {}, []
    for lg in LEAGUES:
        if offline:
            fixtures += [f for f in old.get("fixtures", []) if f["lg"] == lg]; continue
        try:
            st, fx = download(lg, store.get(lg, {}), today, log)
            store[lg] = st; fixtures += fx
        except Exception as e:
            log[lg] = f"hata: {e}"
            fixtures += [f for f in old.get("fixtures", []) if f["lg"] == lg and f["dt"][:10] >= today.isoformat()]
        print(lg, log.get(lg), len(store.get(lg, {}).get("g", [])), flush=True)
    json.dump(store, open(gp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # Akıllı nöbet: yeni maç sonucu yoksa yeniden eğitme, yalnızca fikstür ve canlı bilgiyi tazele
    import hashlib
    fp = hashlib.sha1(json.dumps(sorted((lg, len(st.get("g", [])), (st.get("g") or [{}])[-1].get("id", "")) for lg, st in store.items())).encode()).hexdigest()[:16]
    quick = old.get("fp") == fp and old.get("engine") == ENGINE_V and bool(old.get("leagues")) and "--force" not in sys.argv
    if quick: print("Basketbol: yeni sonuç yok, eğitim atlandı", flush=True)
    out_lg, fits, Ps, bt_all, rows_lg = {}, {}, {}, [], {}
    for lg, (src, code, name, qlen) in LEAGUES.items():
        games = store.get(lg, {}).get("g", [])
        cnt_ = {}
        for g in games: cnt_[g["h"]] = cnt_.get(g["h"], 0) + 1; cnt_[g["a"]] = cnt_.get(g["a"], 0) + 1
        if src == "espn":   # All-Star/gösteri takımları: az maçlı VE son maçı 60 günden eski
            lastd = {}
            for g in games: lastd[g["h"]] = g["dt"]; lastd[g["a"]] = g["dt"]
            old_cut = (today - timedelta(days=60)).isoformat()
            bad = {t for t, c in cnt_.items() if c < 5 and lastd[t][:10] < old_cut}
            games = [g for g in games if g["h"] not in bad and g["a"] not in bad]
        if len(games) < 40: continue
        if quick and lg in old["leagues"]:
            P = old["leagues"][lg]["params"]; fits[lg] = fit(games, today, P); Ps[lg] = P; out_lg[lg] = old["leagues"][lg]; continue
        t0 = time.time()
        P, guard, _ = tune(games, lg, (old.get("leagues", {}).get(lg) or {}).get("params"))
        mt = 200 if lg in ("ncaa", "ncaaw") else 80
        rows = backtest(games, P, mt)
        ks = 1.0; kinfo = None
        if rows and len(rows) >= 150:
            split = sorted(r[0]["dt"] for r in rows)[int(len(rows) * .7)]
            def kerr(k, late):
                e = [((r[0]["hs"] - r[0]["as_"]) - k * (r[1] - r[2])) ** 2 for r in rows if (r[0]["dt"] >= split) == late]
                return sum(e) / max(1, len(e))
            kc = min((.7, .8, .9, 1.0, 1.1, 1.2), key=lambda k: kerr(k, False))
            ok = kerr(kc, True) < kerr(1.0, True) - .3
            ks = kc if ok else 1.0
            kinfo = {"aday": kc, "kabul": bool(ok), "son30_once": round(kerr(1.0, True), 2), "son30_sonra": round(kerr(kc, True), 2)}
            if ks != 1.0:   # tahminleri ölçekle (fark küçülür/büyür, toplam aynı kalır)
                rows = [(r[0], ((r[1] + r[2]) + ks * (r[1] - r[2])) / 2, ((r[1] + r[2]) - ks * (r[1] - r[2])) / 2) for r in rows]
        if rows:
            sm = float(np.std([(r[0]["hs"] - r[0]["as_"]) - (r[1] - r[2]) for r in rows]))
            stt = float(np.std([(r[0]["hs"] + r[0]["as_"]) - (r[1] + r[2]) for r in rows]))
        else:
            sm, stt = 12.0, 18.0
        halves = qlen == 20
        shares = quarter_shares(games[-1500:], halves)
        try: hz = metrics(backtest(games, P, mt, H=90), sm, stt, shares, halves)    # uzun vade: 3 ay önceden tahmin
        except Exception: hz = None
        F = fit(games, today, P); fits[lg] = F; Ps[lg] = P
        if rows: rows_lg[lg] = rows
        logos = {}
        for g in games:
            if g.get("hl"): logos[g["h"]] = {"l": g["hl"], "ab": g.get("hab", "")}
            if g.get("al"): logos[g["a"]] = {"l": g["al"], "ab": g.get("aab", "")}
        cur = current_season(games, today)
        m = metrics(rows, sm, stt, shares, halves)
        bt_all += rows
        out_lg[lg] = {"name": name, "qlen": qlen, "halves": halves, "n": len(games), "n_cur": len(cur), "asOf": store[lg].get("asOf", ""),
                      "mu": round(F["mu"], 2), "hca": round(F["hca"], 2), "hca_prior": F.get("hca_prior"), "sm": round(sm, 2), "st": round(stt, 2), "shares": shares,
                      "params": P, "backtest": m, "dogrulama": guard, "kscale": ks, "kscale_test": kinfo, "uzun_vade": hz, "newp": P.get("newp"), "teams": team_table(games, cur, F, logos),
                      "recent": [{"dt": g["dt"], "h": g["h"], "a": g["a"], "s": [g["hs"], g["as_"]], "hq": g.get("hq"), "aq": g.get("aq")} for g in games[-60:]][::-1]}
        print(f"{lg}: {len(games)} maç, ayar {P}, test {m}, {time.time()-t0:.0f} sn", flush=True)

    # iddaa oranları KİLİTTEN ÖNCE eşlensin: kilitli kayda maç öncesi piyasa görüntüsü (MS, handikap, alt/üst) yazılır
    if not offline:
        try:
            bx, syn = iddaa_bk([f for f in fixtures if f.get("state") != "post"], out_lg)
            for k, v in syn.items(): out_lg.setdefault(k, v)
            fixtures = fixtures + bx
        except Exception as e:
            print("iddaa basketbol alınamadı:", e.__class__.__name__, str(e)[:120], flush=True)
    else:   # çevrimdışı: önceki çıktının sentetik iddaa yarışmaları korunur (fikstürleri zaten old["fixtures"]'tan gelir)
        for lg, L in old.get("leagues", {}).items():
            if L.get("syn"): out_lg.setdefault(lg, L)
        fixtures = fixtures + [f for f in old.get("fixtures", []) if str(f.get("lg", "")).startswith("i")]
    plog = json.load(open(pp, encoding="utf-8")) if os.path.exists(pp) else []
    KS.clear(); KS.update({lg: L.get("kscale", 1.0) for lg, L in out_lg.items()})
    # 😴 YH-04: tam eğitimde β (lig grubu, ileri yürüyüş artıkları) tazelenir; düzeltme gölgede ya da bayraklı üretimde
    try:
        import bk_dinlenme as BD
        if rows_lg:
            BD.kaydet(BD.ogren(rows_lg, [g for st in store.values() for g in st.get("g", [])]))
    except Exception as e:
        print("dinlenme β öğrenilemedi:", e.__class__.__name__, str(e)[:120], flush=True)
    YD = dinlenme_hazirla(fixtures, store)
    plog = lock_and_grade(plog, fixtures, fits, Ps, store, today, YD)
    try:
        import bk_dinlenme as BD
        A_ = BD.izle(plog, out_lg); A_["golge"] = BD.golge_ozet(plog, out_lg); A_["guncelleme"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        BD.kaydet(A_)
    except Exception as e:
        print("dinlenme izleme atlandı:", e.__class__.__name__, str(e)[:120], flush=True)
    try:   # 🩹 YH-16 gölge özeti (önsel Δ ile LL farkı; kapı ≥ 300 maç / ≥ 80 sinyalli)
        import bk_sakatlik as BS
        A_ = BS.oku()
        if A_: A_["golge"] = BS.golge_ozet(plog, out_lg); BS.kaydet(A_)
    except Exception as e:
        print("sakatlık gölge özeti atlandı:", e.__class__.__name__, str(e)[:120], flush=True)
    # 📈 piyasa karnesi (data/bk_piyasa.json) + yalnız kapıdan ve gölgeden geçmiş gruplarda çapalı tahmin (cp)
    cp_fx = {}
    try:
        import bk_piyasa as BP
        PK, _ = BP.karne(plog, out_lg, fixtures)
        U = PK.get("uretimde") or {}
        # gölge kaydı (pg: harmansız / harmanlı / çapalı) her piyasalı maçta; cp yalnız üretimdeki grupta (geri alınınca silinir)
        cp_fx = BP.golge_ve_capa(plog, out_lg, PK, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"))
        t_ = PK.get("toplam") or {}
        print(f"Basket piyasa karnesi: {t_.get('n')} maç · model LL {(t_.get('model') or {}).get('ll')} · piyasa {(t_.get('piyasa') or {}).get('ll')} "
              f"· harman {(t_.get('harman') or {}).get('ll')} · üretimde {sorted(g for g, v in U.items() if v)}", flush=True)
    except Exception as e:
        print("basket piyasa karnesi atlandı:", e.__class__.__name__, str(e)[:160], flush=True)
    json.dump(plog, open(pp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    mw, mn = learn_market(plog)
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tot = old.get("backtest") if quick else None
    if bt_all:
        tot = {"n": len(bt_all), "win": round(float(np.mean([((r[1] > r[2]) == (r[0]["hs"] > r[0]["as_"])) for r in bt_all])), 4),
               "mae_total": round(float(np.mean([abs((r[0]["hs"] + r[0]["as_"]) - (r[1] + r[2])) for r in bt_all])), 2),
               "mae_margin": round(float(np.mean([abs((r[0]["hs"] - r[0]["as_"]) - (r[1] - r[2])) for r in bt_all])), 2)}
    hist = old.get("history", [])
    if tot and not quick: hist = (hist + [{"t": now, "win": tot["win"], "n": tot["n"], "mae_total": tot["mae_total"]}])[-60:]
    fx_out = []; seen_fx = set()
    for f in sorted(fixtures, key=lambda x: x["dt"]):
        if f["lg"] not in out_lg or f["id"] in seen_fx: continue
        seen_fx.add(f["id"])
        x = {k: f[k] for k in ("id", "lg", "dt", "h", "a", "hl", "al", "neutral") if k in f}
        for k in ("odds", "phase", "round", "clock", "io", "iid", "itot", "ihnd", "src"):
            if f.get(k): x[k] = f[k]
        if cp_fx.get(f["id"]): x["cp"] = cp_fx[f["id"]]          # çapalı tahmin (yalnız üretime alınmış gruplar; istemci henüz okumuyor)
        if YD.get(f["id"], (None, False))[1]: x["yd"] = YD[f["id"]][0]   # 😴 YH-04 dinlenme düzeltmesi (yalnız üretimdeki grup; bkPredict ekler)
        if f.get("state") == "in": x["live"] = True; x["hs"] = f.get("hs"); x["as"] = f.get("as_")
        fx_out.append(x)
    res = {"updated": now, "tuned": old.get("tuned", now) if quick else now, "fp": fp, "engine": ENGINE_V, "leagues": out_lg, "fixtures": fx_out, "backtest": tot, "history": hist,
           "live": live_report(plog, today, {k_: v_.get("sm") for k_, v_ in out_lg.items()}), "market": {"w": mw if mw is not None else 0.5, "n": mn, "learned": mw is not None}, "sources": log}
    def _cn(o):
        if isinstance(o, float): return o if math.isfinite(o) else None
        if isinstance(o, dict): return {k: _cn(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [_cn(v) for v in o]
        return o
    json.dump(_cn(res), open(op, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if not offline: gece_isi()
    print("Bitti:", json.dumps(tot, ensure_ascii=False), "fikstür", len(fx_out), flush=True)

if __name__ == "__main__":
    main()
