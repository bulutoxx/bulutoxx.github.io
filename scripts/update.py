#!/usr/bin/env python3
"""BULUTOXX veri güncelleme ve otonom öğrenme motoru.

GitHub Actions bu betiği her gün çalıştırır:
  1. football-data.co.uk'tan 6 ligin bu ve geçen sezon sonuçlarını (MS, İY, oranlar) indirir.
  2. data/season.json içindeki maçlarla birleştirir (aynı sezon + aynı ev/deplasman çifti = aynı maç).
  3. Modelin ayarlarını (zaman ağırlığı, ortalamaya çekme, Dixon-Coles rho, form ağırlığı,
     piyasa ağırlığı) geriye dönük testle yeniden ayarlar: her maç yalnızca o haftadan ÖNCEKİ
     maçlarla eğitilmiş modelle tahmin edilir, en düşük hata veren ayarlar seçilir.
  4. data/model.json'a ayarları ve test sonuçlarını, data/history.json'a öğrenme geçmişini yazar.

Ağ yoksa veya kaynak cevap vermezse mevcut veriyle devam eder, hiçbir veriyi silmez.
Sadece Python standart kütüphanesi ve numpy gerekir.
"""
import csv, io, json, math, os, re, sys, unicodedata, urllib.request, difflib
from datetime import datetime, date, timezone, timedelta
import collections
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
# key: (kaynak türü, football-data kodu, Türkçe ad)
# "main" = sezon dosyaları (MS + İY + oranlar), "new" = tek dosya, takvim yılı sezonları (MS + oranlar)
LEAGUES = {
 "tr1": ("main","T1","Süper Lig"), "en": ("main","E0","Premier League"), "es": ("main","SP1","La Liga"),
 "it": ("main","I1","Serie A"), "de": ("main","D1","Bundesliga"), "fr": ("main","F1","Ligue 1"),
 "nl": ("main","N1","Eredivisie"), "pt": ("main","P1","Liga Portugal"), "be": ("main","B1","Belçika Pro League"),
 "gr": ("main","G1","Yunanistan Süper Lig"), "sc": ("main","SC0","İskoçya Premiership"),
 "en2": ("main","E1","İngiltere Championship"), "en3": ("main","E2","İngiltere League One"), "en4": ("main","E3","İngiltere League Two"),
 "en5": ("main","EC","İngiltere National League"), "sc2": ("main","SC1","İskoçya Championship"), "sc3": ("main","SC2","İskoçya League One"),
 "sc4": ("main","SC3","İskoçya League Two"), "de2": ("main","D2","2. Bundesliga"), "it2": ("main","I2","Serie B"),
 "es2": ("main","SP2","La Liga 2"), "fr2": ("main","F2","Ligue 2"),
 "ar": ("new","ARG","Arjantin Primera División"), "at": ("new","AUT","Avusturya Bundesliga"), "br": ("new","BRA","Brezilya Serie A"),
 "cn": ("new","CHN","Çin Süper Lig"), "dk": ("new","DNK","Danimarka Superliga"), "fi": ("new","FIN","Finlandiya Veikkausliiga"),
 "ie": ("new","IRL","İrlanda Premier Division"), "jp": ("new","JPN","Japonya J1 League"), "mx": ("new","MEX","Meksika Liga MX"),
 "no": ("new","NOR","Norveç Eliteserien"), "pl": ("new","POL","Polonya Ekstraklasa"), "ro": ("new","ROU","Romanya Liga 1"),
 "ru": ("new","RUS","Rusya Premier Lig"), "se": ("new","SWE","İsveç Allsvenskan"), "ch": ("new","SWZ","İsviçre Super League"),
 "us": ("new","USA","ABD MLS"),
}
KEEP_DAYS = 450  # yaklaşık iki sezon

# Avrupa kupaları (TheSportsDB ücretsiz API) — lig gücü katsayıları bunlardan öğrenilir
CUPS = {"ucl": (4480, "Şampiyonlar Ligi"), "uel": (4481, "Avrupa Ligi"), "uecl": (5071, "Konferans Ligi")}
UEFA = {"tr1","en","es","it","de","fr","nl","pt","be","gr","sc","at","ch","dk","no","se","pl","ro","ru","fi","ie",
        "en2","de2","it2","es2","fr2","sc2"}
# Lig gücü ön bilgisi (log ölçek, Premier League = 0). Kupa sonuçları geldikçe veriden güncellenir.
STRENGTH_PRIOR = {"en":0.0,"es":-0.05,"it":-0.08,"de":-0.1,"fr":-0.18,"pt":-0.25,"nl":-0.28,"be":-0.33,"tr1":-0.33,
  "gr":-0.38,"at":-0.4,"ch":-0.4,"sc":-0.42,"dk":-0.42,"ru":-0.4,"no":-0.45,"se":-0.5,"pl":-0.5,"ro":-0.55,
  "en2":-0.35,"de2":-0.45,"it2":-0.55,"es2":-0.5,"fr2":-0.6,"sc2":-0.75,"fi":-0.7,"ie":-0.75}
UNKNOWN_PRIOR = -0.5
CUP_MAP = {"Inter Milan":"Inter","AC Milan":"Milan","Bayern Munich":"Bayern München","Paris SG":"Paris Saint-Germain",
  "Atletico Madrid":"Atlético Madrid","Sporting CP":"Sporting CP","Sporting Lisbon":"Sporting CP","Galatasaray SK":"Galatasaray",
  "Fenerbahce SK":"Fenerbahçe","Besiktas JK":"Beşiktaş","Istanbul Basaksehir":"Başakşehir"}

# football-data.co.uk kısaltmaları -> uygulamadaki adlar
MAP = {
 "Man City":"Manchester City","Man United":"Manchester United","Newcastle":"Newcastle United","Nott'm Forest":"Nottingham Forest",
 "Wolves":"Wolverhampton","Leeds":"Leeds United","Leicester":"Leicester City","Ipswich":"Ipswich Town","Coventry":"Coventry City",
 "Hull":"Hull City","Sheffield United":"Sheffield United","Spurs":"Tottenham",
 "Ath Bilbao":"Athletic Bilbao","Ath Madrid":"Atlético Madrid","Betis":"Real Betis","Sociedad":"Real Sociedad","Celta":"Celta Vigo",
 "Vallecano":"Rayo Vallecano","Alaves":"Alavés","Espanol":"Espanyol","La Coruna":"Deportivo La Coruña","Malaga":"Málaga",
 "Santander":"Racing Santander","Oviedo":"Real Oviedo","Leganes":"Leganés",
 "Bayern Munich":"Bayern München","Dortmund":"Borussia Dortmund","Leverkusen":"Bayer Leverkusen","Ein Frankfurt":"Eintracht Frankfurt",
 "Stuttgart":"VfB Stuttgart","Freiburg":"SC Freiburg","M'gladbach":"Borussia Mönchengladbach","Mainz":"Mainz 05","Augsburg":"FC Augsburg",
 "St Pauli":"St. Pauli","Hamburg":"Hamburger SV","FC Koln":"1. FC Köln","Paderborn":"SC Paderborn","Elversberg":"SV Elversberg",
 "Schalke 04":"Schalke 04","Werder Bremen":"Werder Bremen",
 "Paris SG":"Paris Saint-Germain","St Etienne":"Saint-Étienne",
 "Buyuksehyr":"Başakşehir","Rizespor":"Çaykur Rizespor","Gaziantep":"Gaziantep FK","Karagumruk":"Fatih Karagümrük",
 "Genclerbirligi":"Gençlerbirliği","Goztepe":"Göztepe","Eyupspor":"Eyüpspor","Kasimpasa":"Kasımpaşa","Besiktas":"Beşiktaş",
 "Fenerbahce":"Fenerbahçe","Ad. Demirspor":"Adana Demirspor","Ankaragucu":"Ankaragücü","Corum":"Çorum FK","Erzurum":"Erzurumspor",
 "Erzurum BB":"Erzurumspor","Istanbulspor":"İstanbulspor",
}
STOP = {"fc","sc","sv","ac","as","afc","cf","rc","ssc","1","fk","sk","club","de","cd","ud","sd","bk","calcio"}

def norm(s):
    s = unicodedata.normalize("NFKD", s.replace("ı","i").replace("İ","I")).encode("ascii","ignore").decode().lower()
    return " ".join(w for w in re.split(r"[^a-z0-9]+", s) if w and w not in STOP)

def season_code(d):
    y = d.year if d.month >= 7 else d.year - 1
    return f"{y%100:02d}{(y+1)%100:02d}", y

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 BULUTOXX-updater"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8-sig", errors="replace")

def parse_date(s):
    for f in ("%d/%m/%Y", "%d/%m/%y"):
        try: return datetime.strptime(s.strip(), f).date().isoformat()
        except ValueError: pass
    return None

def fnum(x):
    try:
        v = float(x); return v if v > 1.0 else None
    except (TypeError, ValueError): return None

def resolve(name, known):
    """football-data adını mevcut adlarla eşleştir."""
    if name in MAP: return MAP[name]
    n = norm(name)
    for k in known:
        if norm(k) == n: return k
    for k in known:
        kn = norm(k)
        if min(len(kn), len(n)) >= 5 and (kn.startswith(n + " ") or n.startswith(kn + " ")): return k
    # bulanık eşleme yalnızca çok yakın ve aynı başlangıçlı adlarda (Antalyaspor ≠ Alanyaspor, Sheffield Weds ≠ Sheffield United)
    best = difflib.get_close_matches(n, [norm(k) for k in known], n=1, cutoff=0.9)
    if best and best[0][:4] == n[:4]:
        for k in known:
            if norm(k) == best[0]: return k
    return name

def download_new(lg, known, since):
    """Takvim yılı ligleri: tek dosyada tüm sezonlar (İY skoru yok)."""
    text = fetch(f"https://www.football-data.co.uk/new/{LEAGUES[lg][1]}.csv")
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            d = parse_date(row.get("Date", ""))
            if not d or d < since or row.get("HG", "") == "": continue
            sy = int(re.match(r"\d{4}", row.get("Season", "")).group(0))
            m = {"d": d, "h": resolve(row["Home"].strip(), known), "a": resolve(row["Away"].strip(), known),
                 "ft": [int(float(row["HG"])), int(float(row["AG"]))], "ht": None, "season": sy}
            o = [fnum(row.get(k)) for k in ("AvgCH", "AvgCD", "AvgCA")]
            if not all(o): o = [fnum(row.get(k)) for k in ("PSCH", "PSCD", "PSCA")]
            if all(o): m["odds"] = [round(x, 2) for x in o]
            out.append(m)
        except (ValueError, KeyError, AttributeError):
            continue
    return out

def download(lg, code, start_year, known):
    url = f"https://www.football-data.co.uk/mmz4281/{code}/{LEAGUES[lg][1]}.csv"
    text = fetch(url)
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            d = parse_date(row.get("Date", ""))
            h, a = row.get("HomeTeam", "").strip(), row.get("AwayTeam", "").strip()
            if not d or not h or not a or row.get("FTHG", "") == "": continue
            m = {"d": d, "h": resolve(h, known), "a": resolve(a, known), "ft": [int(row["FTHG"]), int(row["FTAG"])],
                 "ht": [int(row["HTHG"]), int(row["HTAG"])] if row.get("HTHG", "") not in ("", None) else None,
                 "season": start_year}
            o = [fnum(row.get(k)) for k in ("AvgH", "AvgD", "AvgA")]
            if not all(o): o = [fnum(row.get(k)) for k in ("B365H", "B365D", "B365A")]
            if all(o): m["odds"] = [round(x, 2) for x in o]
            ou = [fnum(row.get("Avg>2.5")), fnum(row.get("Avg<2.5"))]
            if all(ou): m["ou"] = [round(x, 2) for x in ou]
            out.append(m)
        except (ValueError, KeyError):
            continue
    return out

TSDB_KEYS = ["123", "3"]  # ücretsiz anahtarlar (biri değişirse diğeri denenir)
def tsdb(path):
    last = None
    for k in TSDB_KEYS:
        try:
            d = json.loads(fetch(f"https://www.thesportsdb.com/api/v1/json/{k}/" + path))
            if d and any(v for v in d.values()): return d
            last = d
        except Exception as e:
            last = e
    if isinstance(last, Exception): raise last
    return last or {}

def download_cup(cid, cy):
    """Bir kupanın bu ve geçen sezon maçlarını birkaç uç noktadan topla (ücretsiz anahtar sınırlı sonuç döndürür)."""
    evs = {}
    def add(lst):
        for e in (lst or []):
            if e.get("intHomeScore") in (None, "") or e.get("intAwayScore") in (None, ""): continue
            evs[e["idEvent"]] = e
    for sy in (cy - 1, cy):
        sname = f"{sy}-{sy+1}"
        try: add(tsdb(f"eventsseason.php?id={cid}&s={sname}").get("events"))
        except Exception: pass
        for r in list(range(1, 9)) + [32, 125, 150, 160, 170, 200]:
            try: add(tsdb(f"eventsround.php?id={cid}&r={r}&s={sname}").get("events"))
            except Exception: pass
    try: add(tsdb(f"eventspastleague.php?id={cid}").get("events"))
    except Exception as e: print(f"  kupa {cid} son maçlar: {e.__class__.__name__}", flush=True)
    print(f"  kupa {cid}: {len(evs)} maç bulundu", flush=True)
    return list(evs.values())

def season_of(d):
    dd = date.fromisoformat(d); return dd.year if dd.month >= 7 else dd.year - 1

def merge(old, new):
    """Aynı sezon + ev + deplasman = aynı maç. Yeni kaynak eskiyi günceller; eskide olan İY/oran korunur."""
    pairs = {}
    def find(m):
        for o in pairs.get((m["h"], m["a"]), []):
            if abs((date.fromisoformat(o["d"]) - date.fromisoformat(m["d"])).days) <= 3: return o
        return None
    for m in old:
        if m["h"] == m["a"]: continue
        m.setdefault("season", season_of(m["d"]))
        if not find(m): pairs.setdefault((m["h"], m["a"]), []).append(m)
    for m in new:
        if m["h"] == m["a"]: continue                     # hatalı isim eşlemesi: aynı takım iki tarafta
        o = find(m)
        if o:
            if m.get("ht") is None and o.get("ht"): m["ht"] = o["ht"]
            for f in ("odds", "ou"):
                if f not in m and f in o: m[f] = o[f]
            lst = pairs[(m["h"], m["a"])]; lst[lst.index(o)] = m
        else:
            pairs.setdefault((m["h"], m["a"]), []).append(m)
    return sorted((m for lst in pairs.values() for m in lst), key=lambda m: (m["d"], m["h"]))

# ------------------------------------------------------------------ model
def pois_vec(lam, kmax=10):
    k = np.arange(kmax + 1)
    lg = -lam[:, None] + k[None, :] * np.log(np.maximum(lam[:, None], 1e-9)) - np.array([math.lgamma(i + 1) for i in k])[None, :]
    return np.exp(lg)

def outcome_probs(lh, la, rho):
    """1X2 ve 2.5 üst olasılıkları (Dixon-Coles düzeltmeli)."""
    ph, pa = pois_vec(lh), pois_vec(la)
    g = ph[:, :, None] * pa[:, None, :]
    g[:, 0, 0] *= np.maximum(1 - lh * la * rho, 0); g[:, 0, 1] *= 1 + lh * rho
    g[:, 1, 0] *= 1 + la * rho; g[:, 1, 1] *= 1 - rho
    g /= g.sum(axis=(1, 2), keepdims=True)
    i = np.arange(g.shape[1])
    H = np.tril(np.ones((len(i), len(i))), -1); D = np.eye(len(i))
    pH = (g * H).sum(axis=(1, 2)); pD = (g * D).sum(axis=(1, 2)); pA = 1 - pH - pD
    tot = i[:, None] + i[None, :]
    pO = (g * (tot > 2)).sum(axis=(1, 2))
    pB = g[:, 1:, 1:].sum(axis=(1, 2))
    return np.stack([pH, pD, pA], 1), pO, pB, g

_TABLE = None
def market_xg(matches):
    """Kapanış oranlarından maç başına piyasa beklenen golü (xg) çıkar; bir kez hesaplanır, saklanır."""
    global _TABLE
    todo = [m for m in matches if m.get("odds") and ("xg" not in m or m.get("xg_o") != m["odds"])]
    if not todo: return 0
    if _TABLE is None:
        lam = np.arange(0.15, 4.01, 0.05)
        LH, LA = np.meshgrid(lam, lam, indexing="ij"); LH = LH.ravel(); LA = LA.ravel()
        p, pO, _, _ = outcome_probs(LH, LA, -0.06)
        _TABLE = (LH, LA, p[:, 0], p[:, 2], pO)
    LH, LA, TH, TA, TO = _TABLE
    for i in range(0, len(todo), 1500):
        ch = todo[i:i + 1500]
        inv = np.array([[1 / o for o in m["odds"]] for m in ch]); inv /= inv.sum(1, keepdims=True)
        ou = np.array([(1 / m["ou"][0]) / (1 / m["ou"][0] + 1 / m["ou"][1]) if m.get("ou") else np.nan for m in ch])
        d = (TH[None, :] - inv[:, :1]) ** 2 + (TA[None, :] - inv[:, 2:3]) ** 2
        has = ~np.isnan(ou)
        if has.any(): d[has] += (TO[None, :] - ou[has, None]) ** 2
        k = d.argmin(1)
        for m, j in zip(ch, k): m["xg"] = [round(float(LH[j]), 2), round(float(LA[j]), 2)]; m["xg_o"] = list(m["odds"])
    return len(todo)

def targets(ms, P):
    """Eğitim hedefi: gerçek gol ile piyasa beklentisinin karışımı (mkt=0 yalnız gol, 1 yalnız piyasa)."""
    w = P.get("mkt", 0.0)
    hg = np.array([(1 - w) * m["ft"][0] + w * m["xg"][0] if m.get("xg") else m["ft"][0] for m in ms], float)
    ag = np.array([(1 - w) * m["ft"][1] + w * m["xg"][1] if m.get("xg") else m["ft"][1] for m in ms], float)
    return hg, ag

def fit(ms, ref_day, P, init=None, iters=25):
    """Ağırlıklı Poisson (Maher) modeli; uygulamadaki fitLeague ile aynı matematik."""
    teams = sorted({m["h"] for m in ms} | {m["a"] for m in ms})
    ti = {t: i for i, t in enumerate(teams)}
    hi = np.array([ti[m["h"]] for m in ms]); ai = np.array([ti[m["a"]] for m in ms])
    hg, ag = targets(ms, P)
    days = np.array([(ref_day - date.fromisoformat(m["d"])).days for m in ms], float)
    w = np.exp(-P["decay"] * days)
    n = len(teams)
    att = np.ones(n); de = np.ones(n)
    if init:
        for t, (a, d) in init.items():
            if t in ti: att[ti[t]] = a; de[ti[t]] = d
    mu = (w * ag).sum() / w.sum(); gamma = min(max((w * hg).sum() / max((w * ag).sum(), .1), 1.0), 1.6)
    K = P["prior"]
    for _ in range(iters):
        base = mu * math.sqrt(gamma)
        eh = mu * gamma * att[hi] * de[ai]; ea = mu * att[ai] * de[hi]
        gs = np.bincount(hi, w * hg, n) + np.bincount(ai, w * ag, n)
        es = np.bincount(hi, w * eh / att[hi], n) + np.bincount(ai, w * ea / att[ai], n)
        gc = np.bincount(ai, w * hg, n) + np.bincount(hi, w * ag, n)
        ec = np.bincount(ai, w * eh / de[ai], n) + np.bincount(hi, w * ea / de[hi], n)
        att = (gs + K * base) / (es + K * base); de = (gc + K * base) / (ec + K * base)
        att /= math.exp(np.log(att).mean()); de /= math.exp(np.log(de).mean())
        dh = (w * att[hi] * de[ai]).sum(); da = (w * att[ai] * de[hi]).sum()
        mu = (w * ag).sum() / da; gamma = min(max(((w * hg).sum() / dh) / mu, 1.0), 1.6)
    return {"t": {t: (float(att[ti[t]]), float(de[ti[t]])) for t in teams}, "mu": float(mu), "gamma": float(gamma)}

def form_ratio(ms, team, upto, L):
    own = [m for m in ms if (m["h"] == team or m["a"] == team) and m["d"] < upto][-5:][::-1]
    if not own: return 1.0, 1.0
    wts = [1, .85, .72, .61, .52]; k = 2.2
    gf = sum(wts[i] * (m["ft"][0] if m["h"] == team else m["ft"][1]) for i, m in enumerate(own))
    ga = sum(wts[i] * (m["ft"][1] if m["h"] == team else m["ft"][0]) for i, m in enumerate(own))
    ws = sum(wts[:len(own)])
    c = lambda x: min(max(x, .45), 2.2)
    return c(((gf + k * L) / (ws + k)) / L), c(((ga + k * L) / (ws + k)) / L)

def backtest(all_ms, P, collect=False):
    """Hafta hafta: her maçı yalnızca önceki maçlarla eğitilmiş modelle tahmin et."""
    rows = []
    for lg, ms in all_ms.items():
        ms = sorted(ms, key=lambda m: m["d"])
        if len(ms) < 40: continue
        weeks = sorted({date.fromisoformat(m["d"]).isocalendar()[:2] for m in ms})
        init = None
        for wk in weeks:
            test = [m for m in ms if date.fromisoformat(m["d"]).isocalendar()[:2] == wk]
            start = min(m["d"] for m in test)
            train = [m for m in ms if m["d"] < start]
            if len(train) < 45: continue
            f = fit(train, date.fromisoformat(start), P, init, iters=12 if init else 30)
            init = f["t"]
            cnt = {}
            for m in train: cnt[m["h"]] = cnt.get(m["h"], 0) + 1; cnt[m["a"]] = cnt.get(m["a"], 0) + 1
            L = f["mu"] * math.sqrt(f["gamma"])
            for m in test:
                if cnt.get(m["h"], 0) < 3 or cnt.get(m["a"], 0) < 3: continue
                (ah, dh), (aa, da) = f["t"][m["h"]], f["t"][m["a"]]
                if P["formW"] > 0:
                    fa_h, fd_h = form_ratio(train, m["h"], start, L); fa_a, fd_a = form_ratio(train, m["a"], start, L)
                    x = P["formW"]
                    ah, dh, aa, da = ah**(1-x)*fa_h**x, dh**(1-x)*fd_h**x, aa**(1-x)*fa_a**x, da**(1-x)*fd_a**x
                lh = f["mu"] * f["gamma"] * ah * da; la = f["mu"] * aa * dh
                rows.append((lg, m, lh, la))
    if not rows: return None
    lh = np.array([r[2] for r in rows]); la = np.array([r[3] for r in rows])
    p, pO, pB, g = outcome_probs(lh, la, P["rho"])
    res = np.array([0 if r[1]["ft"][0] > r[1]["ft"][1] else 1 if r[1]["ft"][0] == r[1]["ft"][1] else 2 for r in rows])
    ll = -np.log(np.maximum(p[np.arange(len(rows)), res], 1e-9)).mean()
    out = {"n": len(rows), "logloss": float(ll), "rows": rows, "p": p, "res": res, "pO": pO, "pB": pB, "g": g}
    return out

def tune_market(bt):
    """Kullanıcı oran girdiğinde model ile piyasa nasıl karıştırılsın? Geçmiş oranlarla öğren."""
    idx = [i for i, r in enumerate(bt["rows"]) if r[1].get("odds")]
    if len(idx) < 80: return 0.6, None
    p = bt["p"][idx]; res = bt["res"][idx]
    mk = np.array([[1 / o for o in bt["rows"][i][1]["odds"]] for i in idx]); mk /= mk.sum(1, keepdims=True)
    best = (9, 0.6)
    for w in np.linspace(0, 1, 11):
        q = np.exp((1 - w) * np.log(p) + w * np.log(mk)); q /= q.sum(1, keepdims=True)
        ll = -np.log(q[np.arange(len(idx)), res]).mean()
        if ll < best[0]: best = (float(ll), float(w))
    mll = -np.log(mk[np.arange(len(idx)), res]).mean()
    return round(best[1], 2), {"n": len(idx), "model_market_logloss": round(best[0], 4), "market_logloss": round(float(mll), 4)}

def pick_scores(g, p, pO):
    """Tutarlı skor: tahmin edilen sonuç (1/X/2) ve 2.5 alt/üst yönüyle uyumlu en olası skor (düz mod hep 1-1 der)."""
    n, K = g.shape[0], g.shape[1]; ii, jj = np.meshgrid(np.arange(K), np.arange(K), indexing="ij")
    om = [(ii > jj), (ii == jj), (ii < jj)]; pr = p.argmax(1); out = []
    for t in range(n):
        gg = g[t] * (om[pr[t]] & (((ii + jj) > 2) if pO[t] >= .5 else ((ii + jj) <= 2)))
        if gg.sum() == 0: gg = g[t] * om[pr[t]]
        out.append(divmod(int(gg.argmax()), K))
    return out

def pick_ht(g1, p1, pr_ft, th=0.05):
    """İlk yarı: sonuca koşullu mod; İY beraberlik zayıf öndeyse maç sonu favorisinin önde olduğu skoru seç."""
    K = g1.shape[1]; ii, jj = np.meshgrid(np.arange(K), np.arange(K), indexing="ij"); om = [(ii > jj), (ii == jj), (ii < jj)]
    out = []
    for t in range(g1.shape[0]):
        o = int(p1[t].argmax())
        if o == 1 and pr_ft[t] != 1:
            side = 0 if pr_ft[t] == 0 else 2
            if p1[t][1] - p1[t][side] <= th: o = side
        out.append(divmod(int((g1[t] * om[o]).argmax()), K))
    return out

RISK_RULES = [
    {"id": "en_yuksek", "ad": "En yüksek oran", "omin": 2.5, "omax": 99, "only": ["1", "X", "2"], "pick": "maxodds"},
    {"id": "akilli", "ad": "Akıllı sürpriz", "omin": 2.5, "omax": 3.6, "only": ["1", "X", "2", "Ü2.5", "A2.5"], "pick": "likely"},
    {"id": "akilli_genis", "ad": "Akıllı sürpriz (geniş)", "omin": 2.5, "omax": 4.5, "only": ["1", "X", "2"], "pick": "likely"},
    {"id": "beraberlik", "ad": "Beraberlik avcısı", "omin": 2.8, "omax": 5.0, "only": ["X"], "pick": "likely"},
]

def risk_pick(sel, rule):
    """sel: [(ad, oran, olasılık, tuttu_mu)] -> kurala göre seçilen yüksek oranlı tahmin."""
    c = [x for x in sel if x[0] in rule["only"] and rule["omin"] <= x[1] <= rule["omax"]]
    if not c: return None
    return max(c, key=lambda x: x[1]) if rule["pick"] == "maxodds" else max(c, key=lambda x: x[2])

def risk_test(bt):
    """Yüksek kazanç kutusu: kuralları gerçek kapanış oranlarıyla test et; ilk %70'te seç, son %30'da doğrula."""
    rows = bt["rows"]; items = []
    for i, r in enumerate(rows):
        m = r[1]
        if not m.get("odds"): continue
        ft = m["ft"]; res = 0 if ft[0] > ft[1] else 1 if ft[0] == ft[1] else 2
        inv = [1 / o for o in m["odds"]]; s_ = sum(inv); mk = [x / s_ for x in inv]
        sel = [("1", m["odds"][0], mk[0], res == 0), ("X", m["odds"][1], mk[1], res == 1), ("2", m["odds"][2], mk[2], res == 2)]
        if m.get("ou"):
            io = [1 / m["ou"][0], 1 / m["ou"][1]]; so = sum(io); o = sum(ft) > 2
            sel += [("Ü2.5", m["ou"][0], io[0] / so, o), ("A2.5", m["ou"][1], io[1] / so, not o)]
        items.append((m["d"], sel))
    if len(items) < 400: return None
    items.sort(key=lambda x: x[0]); split = items[int(len(items) * .7)][0]
    def st(its, rule):
        b = [risk_pick(sel, rule) for _, sel in its]; b = [x for x in b if x]
        if not b: return None
        n = len(b); hit = sum(x[3] for x in b); prof = sum((x[1] - 1) if x[3] else -1 for x in b)
        return {"n": n, "kapsam": round(n / len(its), 3), "tutma": round(hit / n, 4), "ort_oran": round(sum(x[1] for x in b) / n, 2), "getiri": round(prof / n, 4)}
    out = []
    for rule in RISK_RULES:
        e = st([x for x in items if x[0] < split], rule); l = st([x for x in items if x[0] >= split], rule)
        if e and l: out.append(dict(rule, ilk70=e, son30=l))
    if not out: return None
    best = max(out, key=lambda x: x["ilk70"]["getiri"])     # seçim yalnızca ilk %70'te; son %30 dürüst doğrulamadır
    return {"secilen": best["id"], "kural": {k: best[k] for k in ("id", "ad", "omin", "omax", "only", "pick")}, "kurallar": out}

def calibrate(bt, rho=-0.06):
    """Olasılık kalibrasyonu: keskinleştirme (T), gol ölçeği (g), beraberlik katsayısı (dk).
    İlk %70 maçta seçilir, son %30'da doğrulanır; geçemezse etkisiz (1, 1, 1). Laboratuvarda 3 sezonda doğrulandı."""
    rows = bt["rows"]; n = len(rows)
    if n < 500: return {"T": 1.0, "g": 1.0, "dk": 1.0, "kabul": False}
    split = sorted(r[1]["d"] for r in rows)[int(n * .7)]
    late = np.array([r[1]["d"] >= split for r in rows])
    lh = np.array([r[2] for r in rows]); la = np.array([r[3] for r in rows]); res = bt["res"]
    tot = np.array([sum(r[1]["ft"]) for r in rows])
    cache = {}
    def ev(T, g, dk, mask):
        if g not in cache: cache[g] = outcome_probs(lh * g, la * g, rho)[:2]
        p, pO = cache[g]; q = p ** T; q /= q.sum(1, keepdims=True); q[:, 1] *= dk; q /= q.sum(1, keepdims=True)
        idx = np.where(mask)[0]
        l1 = -np.log(np.maximum(q[idx, res[idx]], 1e-9)).mean()
        l2 = -np.mean(np.where(tot[idx] > 2, np.log(np.maximum(pO[idx], 1e-9)), np.log(np.maximum(1 - pO[idx], 1e-9))))
        return l1 + .5 * l2
    grid = [(T, g, dk) for T in (1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3) for g in (0.98, 1.0, 1.01, 1.02, 1.03, 1.04, 1.05) for dk in (0.97, 1.0, 1.03, 1.06, 1.1, 1.14)]
    best = min(grid, key=lambda x: ev(*x, ~late))
    b_late, n_late = ev(1.0, 1.0, 1.0, late), ev(*best, late)
    ok = n_late < b_late - 1e-5
    out = {"T": best[0] if ok else 1.0, "g": best[1] if ok else 1.0, "dk": best[2] if ok else 1.0, "kabul": bool(ok),
           "son30_once": round(float(b_late), 5), "son30_sonra": round(float(n_late), 5), "aday": list(best)}
    print("Kalibrasyon:", out, flush=True)
    return out

def apply_cal(p, P):
    T, dk = P.get("calT", 1.0), P.get("dk", 1.0)
    if T == 1.0 and dk == 1.0: return p
    q = p ** T; q /= q.sum(1, keepdims=True); q[:, 1] *= dk; q /= q.sum(1, keepdims=True)
    return q

def metrics(bt, P):
    rows, p, res = bt["rows"], bt["p"], bt["res"]
    n = len(rows)
    out = {"n": n, "logloss": round(bt["logloss"], 4),
           "brier": round(float(((p - np.eye(3)[res]) ** 2).sum(1).mean()), 4),
           "r1x2": round(float((p.argmax(1) == res).mean()), 4)}
    tot = np.array([r[1]["ft"][0] + r[1]["ft"][1] for r in rows]); btts = np.array([r[1]["ft"][0] > 0 and r[1]["ft"][1] > 0 for r in rows])
    out["ou25"] = round(float(((bt["pO"] >= .5) == (tot > 2)).mean()), 4)
    out["btts"] = round(float(((bt["pB"] >= .5) == btts).mean()), 4)
    g = bt["g"]; flat = g.reshape(n, -1).argmax(1); kk = g.shape[1]
    out["ft_exact"] = round(float(np.mean([flat[i] // kk == r[1]["ft"][0] and flat[i] % kk == r[1]["ft"][1] for i, r in enumerate(rows)])), 4)
    # ilk yarı / ikinci yarı net skor
    hts = [(i, r) for i, r in enumerate(rows) if r[1].get("ht")]
    if hts:
        s = P["h1"]
        lh = np.array([rows[i][2] for i, _ in hts]); la = np.array([rows[i][3] for i, _ in hts])
        _, _, _, g1 = outcome_probs(lh * s, la * s, P["rho"]); _, _, _, g2 = outcome_probs(lh * (1 - s), la * (1 - s), P["rho"] * .6)
        f1 = g1.reshape(len(hts), -1).argmax(1); f2 = g2.reshape(len(hts), -1).argmax(1); k1 = g1.shape[1]
        out["nh"] = len(hts)
        out["ht_exact"] = round(float(np.mean([f1[j] // k1 == r[1]["ht"][0] and f1[j] % k1 == r[1]["ht"][1] for j, (_, r) in enumerate(hts)])), 4)
        out["h2_exact"] = round(float(np.mean([f2[j] // k1 == r[1]["ft"][0] - r[1]["ht"][0] and f2[j] % k1 == r[1]["ft"][1] - r[1]["ht"][1] for j, (_, r) in enumerate(hts)])), 4)
        p1, _, _, _ = outcome_probs(lh * s, la * s, P["rho"])
        HC = pick_ht(g1, p1, p.argmax(1)[[i for i, _ in hts]])
        hres = [0 if r[1]["ht"][0] > r[1]["ht"][1] else 1 if r[1]["ht"][0] == r[1]["ht"][1] else 2 for _, r in hts]
        out["ht_exact_c"] = round(float(np.mean([HC[j] == tuple(r[1]["ht"]) for j, (_, r) in enumerate(hts)])), 4)
        out["ht_res_c"] = round(float(np.mean([(0 if a > b else 1 if a == b else 2) == hres[j] for j, (a, b) in enumerate(HC)])), 4)
        out["ht_res_mode"] = round(float(np.mean([(0 if f1[j] // k1 > f1[j] % k1 else 1 if f1[j] // k1 == f1[j] % k1 else 2) == hres[j] for j in range(len(hts))])), 4)
        out["ht_top_c"] = collections.Counter(f"{a}-{b}" for a, b in HC).most_common(5)
    # Skor seçim testi: düz mod ile tutarlı seçimi aynı geçmiş maçlarda karşılaştır, iyi olanı kullan
    C = pick_scores(g, p, bt["pO"]); act = [tuple(r[1]["ft"]) for r in rows]
    A = [divmod(int(f), kk) for f in flat]
    def ev(S):
        return {"exact": round(float(np.mean([S[t] == act[t] for t in range(n)])), 4),
                "res": round(float(np.mean([(0 if a > b else 1 if a == b else 2) == res[t] for t, (a, b) in enumerate(S)])), 4),
                "ou": round(float(np.mean([((a + b) > 2) == (tot[t] > 2) for t, (a, b) in enumerate(S)])), 4),
                "distinct": len(set(S)), "top": collections.Counter(f"{a}-{b}" for a, b in S).most_common(5)}
    eA, eC = ev(A), ev(C)
    # Kural: tutarlı seçim net skorda en fazla 2.5 puan kaybediyor ve sonuç + alt/üst uyumunda kazanıyorsa onu kullan
    mode = "tutarli" if (eA["exact"] - eC["exact"] <= .025 and eC["res"] + eC["ou"] > eA["res"] + eA["ou"]) else "mod"
    out["score_test"] = {"mod": eA, "tutarli": eC, "secilen": mode}
    out["ft_exact_c"] = eC["exact"]
    by = {}
    for i, r in enumerate(rows):
        b = by.setdefault(r[0], [0, 0]); b[0] += 1; b[1] += int(p[i].argmax() == res[i])
    out["by_league"] = {k: {"n": v[0], "r1x2": round(v[1] / v[0], 4)} for k, v in by.items()}
    return out

def tune(all_ms, P0):
    """Koordinat iniş: her ayarı sırayla dene, geriye dönük log-loss'u düşüreni tut."""
    grid = {"mkt": [0.0, 0.3, 0.5, 0.7, 0.85, 1.0],
            "decay": [0.001, 0.002, 0.004, 0.007, 0.012, 0.018, 0.026, 0.035], "prior": [0.3, 0.6, 1.0, 2.5, 4.0, 6.0, 9.0],
            "formW": [0.0, 0.1, 0.2, 0.35], "rho": [-0.2, -0.15, -0.1, -0.06, -0.02, 0.0, 0.04]}
    P = dict(P0); cur = backtest(all_ms, P)
    if not cur: return P, None
    split = sorted(r[1]["d"] for r in cur["rows"])[int(len(cur["rows"]) * .7)]
    def part(bt, late):
        idx = [i for i, r in enumerate(bt["rows"]) if (r[1]["d"] >= split) == late]
        return float(-np.log(np.maximum(bt["p"][idx, bt["res"][idx]], 1e-9)).mean()) if idx else 9.0
    base_late = part(cur, True)
    if cur["n"] < 300:
        print(f"  test örneği az ({cur['n']} maç), ayarlar korunuyor", flush=True)
        return P, cur
    best = part(cur, False)
    for _ in range(3):
        changed = False
        for key, vals in grid.items():
            for v in vals:
                if v == P[key]: continue
                Q = dict(P); Q[key] = v
                bt = backtest(all_ms, Q) if key != "rho" else None
                if key == "rho":
                    p, *_ = outcome_probs(np.array([r[2] for r in cur["rows"]]), np.array([r[3] for r in cur["rows"]]), v)
                    ll = part({"rows": cur["rows"], "p": p, "res": cur["res"]}, False)
                else:
                    ll = part(bt, False)
                if ll < best - 1e-5:
                    best = ll; P = Q; changed = True
                    if bt: cur = bt
                    print(f"  {key}={v}  logloss={ll:.4f}", flush=True)
        if not changed: break
    fin = backtest(all_ms, P); late = part(fin, True)
    global GUARD
    GUARD = {"split": split, "eski_son30": round(base_late, 4), "yeni_son30": round(late, 4), "kabul": bool(late <= base_late + 1e-4)}
    if not GUARD["kabul"]:
        print(f"  ayar değişikliği doğrulamadan geçemedi ({late:.4f} > {base_late:.4f}), eski ayarlar korunuyor", flush=True)
        return dict(P0), backtest(all_ms, P0)
    print(f"  doğrulama: son %30 maçta {base_late:.4f} -> {late:.4f}", flush=True)
    return P, fin

GUARD = None
ENGINE_V = "2026-10-24.3"
DATA_V = 2   # 2: aynı eşleşmenin sezonda birden çok oynanması + sıkı isim eşleme   # motor kodu değişince bir kez tam eğitim yapılır
CAL_INFO = {}
NEW_TEAM = (0.95, 1.05)   # 3 ay önceden testte (3 sezon) en iyi çıkan: lige yeni gelen takım ortalamaya yakın, hafif zayıf

def horizon_test(all_ms, P, H=90, decays=(None, 0.01)):
    """Uzun vade sağlık testi: son 1 yıldaki her maçı, maçtan H gün önceki veriyle tahmin et."""
    out = {}
    end = max(m["d"] for ms in all_ms.values() for m in ms)
    start = (date.fromisoformat(end) - timedelta(days=330)).isoformat()
    for dc in decays:
        Q = dict(P) if dc is None else dict(P, decay=dc)
        rows = []; skipped = 0
        for lg, ms in all_ms.items():
            ms = sorted(ms, key=lambda m: m["d"]); test = [m for m in ms if m["d"] >= start]
            if len(test) < 20: continue
            weeks = {}
            for m in test:
                d = date.fromisoformat(m["d"]); weeks.setdefault(d - timedelta(days=d.weekday()), []).append(m)
            for wk, tm in weeks.items():
                cut = (wk - timedelta(days=H)).isoformat(); train = [m for m in ms if m["d"] < cut]
                if len(train) < 40: skipped += len(tm); continue
                f = fit(train, date.fromisoformat(cut), Q, iters=20)
                for m in tm:
                    h = f["t"].get(m["h"], NEW_TEAM); a = f["t"].get(m["a"], NEW_TEAM)
                    rows.append((m, f["mu"] * f["gamma"] * h[0] * a[1], f["mu"] * a[0] * h[1]))
        if not rows: continue
        lh = np.array([r[1] for r in rows]); la = np.array([r[2] for r in rows])
        p, pO, _, _ = outcome_probs(lh, la, Q["rho"])
        res = np.array([0 if r[0]["ft"][0] > r[0]["ft"][1] else 1 if r[0]["ft"][0] == r[0]["ft"][1] else 2 for r in rows])
        tot = np.array([sum(r[0]["ft"]) for r in rows])
        out["mevcut" if dc is None else f"decay_{dc}"] = {"n": len(rows), "kapsam": round(len(rows) / (len(rows) + skipped), 3),
            "r1x2": round(float((p.argmax(1) == res).mean()), 4), "logloss": round(float(-np.log(np.maximum(p[np.arange(len(rows)), res], 1e-9)).mean()), 4),
            "ou25": round(float(((pO >= .5) == (tot > 2)).mean()), 4), "decay": Q["decay"]}
    if out:
        best = min(out.values(), key=lambda x: x["logloss"]); out["uzun_vade_decay"] = best["decay"]
    return out

def h1_share(all_ms):
    g1 = g = 0
    for ms in all_ms.values():
        for m in ms:
            if m.get("ht"): g1 += sum(m["ht"]); g += sum(m["ft"])
    return round(min(max((g1 + 0.44 * 40) / (g + 40), 0.36), 0.52), 4)

ESPN = {"tr1":"tur.1","en":"eng.1","es":"esp.1","it":"ita.1","de":"ger.1","fr":"fra.1","nl":"ned.1","pt":"por.1","be":"bel.1",
  "sc":"sco.1","gr":"gre.1","en2":"eng.2","en3":"eng.3","en4":"eng.4","de2":"ger.2","it2":"ita.2","es2":"esp.2","fr2":"fra.2",
  "br":"bra.1","ar":"arg.1","us":"usa.1","mx":"mex.1","jp":"jpn.1","at":"aut.1","ch":"sui.1","dk":"den.1","no":"nor.1","se":"swe.1",
  "pl":"pol.1","ro":"rou.1","ie":"irl.1","fi":"fin.1","cn":"chn.1","ru":"rus.1",
  "ucl":"uefa.champions","uel":"uefa.europa","uecl":"uefa.europa.conf"}

def fetch_logos(season):
    """Her ligin takım logolarını ESPN'den indir ve uygulamadaki takım adlarıyla eşle."""
    lp = os.path.join(DATA, "logos.json")
    logos = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else {}
    got = 0
    for lg, d in season.items():
        code = ESPN.get(lg)
        if not code: continue
        names = sorted({m["h"] for m in d["matches"]} | {m["a"] for m in d["matches"]})
        if all(n in logos for n in names): continue
        try:
            j = json.loads(fetch(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/teams"))
            teams = [t["team"] for t in j["sports"][0]["leagues"][0]["teams"]]
        except Exception as e:
            print(f"  logo {lg}: {e.__class__.__name__}", flush=True); continue
        idx = {}
        for t in teams:
            href = (t.get("logos") or [{}])[0].get("href")
            if not href: continue
            for k in ("displayName", "shortDisplayName", "name", "nickname", "location"):
                if t.get(k): idx.setdefault(norm(t[k]), href)
        keys = list(idx)
        for n in names:
            if n in logos: continue
            q = norm(n); url = idx.get(q)
            if not url:
                for k in keys:
                    if k and (k.startswith(q) or q.startswith(k) or (len(q) > 4 and q in k) or (len(k) > 4 and k in q)): url = idx[k]; break
            if not url:
                b = difflib.get_close_matches(q, keys, n=1, cutoff=0.72)
                if b: url = idx[b[0]]
            if url: logos[n] = url; got += 1
    json.dump(logos, open(lp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"Logolar: {len(logos)} takım ({got} yeni)", flush=True)

def learn_strength(season, P, today):
    """Lig gücü katsayılarını ve kupa takım güçlerini Avrupa kupası sonuçlarından öğren."""
    dom = {}
    for lg, d in season.items():
        if d.get("cup"): continue
        cur = [m for m in d["matches"] if m["season"] == d.get("season")]
        if len(cur) < 20: continue
        f = fit(d["matches"], today, P)
        for t, (a, de) in f["t"].items():
            if any(m["h"] == t or m["a"] == t for m in cur): dom[t] = (lg, a, de)
    cm = [m for d in season.values() if d.get("cup") for m in d["matches"]]
    k = {lg: STRENGTH_PRIOR.get(lg, UNKNOWN_PRIOR) for lg in {v[0] for v in dom.values()}}
    teams = sorted({m["h"] for m in cm} | {m["a"] for m in cm})
    ext = {t: [UNKNOWN_PRIOR, 0.0, 0.0] for t in teams if t not in dom}  # bilinmeyen takım: [güç, hücum, savunma] log
    mu, gam = 1.35, 1.2
    def rating(t):
        if t in dom:
            lg, a, de = dom[t]; return math.log(a) + k[lg], math.log(de) - k[lg]
        e = ext[t]; return e[0] + e[1], -e[0] + e[2]
    if cm:
        lr = 0.05
        for _ in range(300):
            gk = {lg: 0.0 for lg in k}; ge = {t: [0.0, 0.0, 0.0] for t in ext}; sh = sa = eh_s = ea_s = 0.0
            for m in cm:
                (ah, dh), (aa, da) = rating(m["h"]), rating(m["a"])
                lh = mu * gam * math.exp(ah + da); la = mu * math.exp(aa + dh)
                rh, ra = m["ft"][0] - lh, m["ft"][1] - la
                sh += m["ft"][0]; sa += m["ft"][1]; eh_s += lh; ea_s += la
                for t, r_for, r_ag in ((m["h"], rh, ra), (m["a"], ra, rh)):
                    if t in dom: gk[dom[t][0]] += r_for - r_ag
                    else:
                        g = ge[t]; g[0] += r_for - r_ag; g[1] += r_for; g[2] += r_ag
            for lg in k:
                k[lg] += lr * (gk[lg] / 10 - 0.5 * (k[lg] - STRENGTH_PRIOR.get(lg, UNKNOWN_PRIOR)))
            for t, g in ge.items():
                e = ext[t]
                e[0] += lr * (g[0] / 10 - 0.5 * (e[0] - UNKNOWN_PRIOR)); e[1] += lr * (g[1] / 10 - 1.0 * e[1]); e[2] += lr * (g[2] / 10 - 1.0 * e[2])
            mu *= (sa / max(ea_s, 1e-6)) ** 0.2; gam *= ((sh / max(eh_s, 1e-6)) / (sa / max(ea_s, 1e-6))) ** 0.2
            gam = min(max(gam, 1.0), 1.6)
    base = {lg: round(v, 3) for lg, v in k.items()}
    for lg, v in STRENGTH_PRIOR.items(): base.setdefault(lg, v)
    cup_teams = {}
    for t in teams:
        a, de = rating(t); cup_teams[t] = [round(math.exp(a), 3), round(math.exp(de), 3), dom[t][0] if t in dom else None]
    return {"mu": round(mu, 3), "gamma": round(gam, 3), "n": len(cm), "strength": base, "unknown": UNKNOWN_PRIOR, "teams": cup_teams}

# ------------------------------------------------------------------ gelecek maçlar + canlı karne
NEW_COUNTRY = {"Argentina":"ar","Austria":"at","Brazil":"br","China":"cn","Denmark":"dk","Finland":"fi","Ireland":"ie","Japan":"jp",
               "Mexico":"mx","Norway":"no","Poland":"pl","Romania":"ro","Russia":"ru","Sweden":"se","Switzerland":"ch","USA":"us"}
def _odds(row, sets):
    for ks in sets:
        o = [fnum(row.get(k)) for k in ks]
        if all(o): return [round(x, 2) for x in o]
    return None
def download_fixtures(season, today):
    """football-data.co.uk yaklaşan maçlar ve ortalama bahis oranları."""
    code2lg = {v[1]: k for k, v in LEAGUES.items() if v[0] == "main"}
    known = {lg: sorted({m["h"] for m in d["matches"]} | {m["a"] for m in d["matches"]}) for lg, d in season.items() if not d.get("cup")}
    out = []
    for url, kind in (("https://www.football-data.co.uk/fixtures.csv", "main"), ("https://www.football-data.co.uk/new_league_fixtures.csv", "new")):
        try: text = fetch(url)
        except Exception as e: print(f"  fikstür {kind}: {e.__class__.__name__}", flush=True); continue
        for row in csv.DictReader(io.StringIO(text)):
            try:
                lg = code2lg.get((row.get("Div") or "").strip()) if kind == "main" else NEW_COUNTRY.get((row.get("Country") or "").strip())
                if not lg: continue
                d = parse_date(row.get("Date", ""))
                if not d or d < today.isoformat(): continue
                h = (row.get("HomeTeam") or row.get("Home") or "").strip(); a = (row.get("AwayTeam") or row.get("Away") or "").strip()
                if not h or not a: continue
                kn = known.get(lg, [])
                f = {"d": d, "t": (row.get("Time") or "").strip(), "lg": lg, "h": resolve(h, kn), "a": resolve(a, kn)}
                o = _odds(row, [("AvgH","AvgD","AvgA"),("B365H","B365D","B365A"),("PSH","PSD","PSA"),("AvgCH","AvgCD","AvgCA"),("MaxH","MaxD","MaxA")])
                if o: f["odds"] = o
                ou = _odds(row, [("Avg>2.5","Avg<2.5"),("B365>2.5","B365<2.5"),("P>2.5","P<2.5")])
                if ou: f["ou"] = ou
                out.append(f)
            except Exception:
                continue
    out.sort(key=lambda f: (f["d"], f["t"]))
    print(f"Yaklaşan maç: {len(out)} ({sum(1 for f in out if f.get('odds'))} oranlı)", flush=True)
    return out

def predict_fixtures(fx, all_ms, P, today):
    """Her yaklaşan maç için model ve piyasa tahminini önceden kaydet (gerçek ileriye dönük test için)."""
    fits = {}
    for lg, ms in all_ms.items():
        if len(ms) >= 40:
            try: fits[lg] = fit(ms, today, P)
            except Exception: pass
    market_xg(fx)
    rows = []
    for f in fx:
        F = fits.get(f["lg"])
        if not F: continue
        (ah, dh), (aa, da) = F["t"].get(f["h"], NEW_TEAM), F["t"].get(f["a"], NEW_TEAM)
        rows.append((f, F["mu"] * F["gamma"] * ah * da, F["mu"] * aa * dh))
    if not rows: return []
    lh = np.array([r[1] for r in rows]); la = np.array([r[2] for r in rows])
    gs_ = P.get("gscale", 1.0)
    p, pO, pB, g = outcome_probs(lh * gs_, la * gs_, P["rho"]); kk = g.shape[1]
    p = apply_cal(p, P)
    CS = pick_scores(g, p, pO) if P.get("scoreMode", "tutarli") == "tutarli" else None
    out = []
    for i, (f, a, b) in enumerate(rows):
        k = int(g[i].reshape(-1).argmax())
        if CS: k = CS[i][0] * kk + CS[i][1]
        e = {"id": f"{f['lg']}|{f['d']}|{f['h']}|{f['a']}", "d": f["d"], "lg": f["lg"], "h": f["h"], "a": f["a"],
             "p": [round(float(x), 4) for x in p[i]], "o": round(float(pO[i]), 4), "ft": f"{k // kk}-{k % kk}"}
        if f.get("odds"):
            inv = [1 / x for x in f["odds"]]; s_ = sum(inv); e["mp"] = [round(x / s_, 4) for x in inv]
        out.append(e)
    return out

def grade_predlog(log, all_ms, today):
    idx = {}
    for lg, ms in all_ms.items():
        for m in ms: idx.setdefault((lg, m["h"], m["a"]), []).append(m)
    for e in log:
        if e.get("r") is not None or e["d"] >= today.isoformat(): continue
        cands = [m for m in idx.get((e["lg"], e["h"], e["a"]), []) if abs((date.fromisoformat(m["d"]) - date.fromisoformat(e["d"])).days) <= 3]
        if cands:
            m = cands[0]; e["r"] = m["ft"]
        elif (today - date.fromisoformat(e["d"])).days > 10:
            e["r"] = False   # ertelendi / bulunamadı
    keep = [e for e in log if (today - date.fromisoformat(e["d"])).days <= 120]
    return keep

def live_report(log, today):
    def stats(es):
        es = [e for e in es if e.get("r")]
        if not es: return None
        res = [0 if e["r"][0] > e["r"][1] else 1 if e["r"][0] == e["r"][1] else 2 for e in es]
        hit = sum(int(np.argmax(e["p"]) == r) for e, r in zip(es, res))
        ll = -np.mean([math.log(max(e["p"][r], 1e-9)) for e, r in zip(es, res)])
        ou = sum(int((e["o"] >= .5) == (sum(e["r"]) > 2)) for e in es)
        ex = sum(int(e["ft"] == f"{e['r'][0]}-{e['r'][1]}") for e in es)
        mk = [(e, r) for e, r in zip(es, res) if e.get("mp")]
        out = {"n": len(es), "r1x2": round(hit / len(es), 4), "logloss": round(float(ll), 4), "ou25": round(ou / len(es), 4), "ft_exact": round(ex / len(es), 4)}
        if mk:
            out["market_r1x2"] = round(sum(int(np.argmax(e["mp"]) == r) for e, r in mk) / len(mk), 4)
            out["market_logloss"] = round(float(-np.mean([math.log(max(e["mp"][r], 1e-9)) for e, r in mk])), 4)
            out["market_n"] = len(mk)
        return out
    cut = (today.toordinal() - 30)
    return {"all": stats(log), "d30": stats([e for e in log if date.fromisoformat(e["d"]).toordinal() >= cut]),
            "pending": sum(1 for e in log if e.get("r") is None)}

def main():
    offline = "--offline" in sys.argv
    sp = os.path.join(DATA, "season.json")
    season = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {}
    mp0 = os.path.join(DATA, "model.json")
    if not offline and (json.load(open(mp0, encoding="utf-8")) if os.path.exists(mp0) else {}).get("data_v") != DATA_V:
        print("Veri kuralları değişti: sezon verisi baştan kuruluyor", flush=True); season = {}
    today = date.today()
    code, y = season_code(today)
    prev_code, py = f"{(y-1)%100:02d}{y%100:02d}", y - 1
    log = {}
    since = date.fromordinal(today.toordinal() - KEEP_DAYS).isoformat()
    for lg, (kind, fcode, lname) in LEAGUES.items():
        cur = season.get(lg, {"matches": []})
        old = cur.get("matches", [])
        known = sorted({m["h"] for m in old} | {m["a"] for m in old})
        new = []
        if not offline:
            try:
                if kind == "new":
                    new = download_new(lg, known, since); log[lg] = len(new)
                else:
                    for c, sy in ((prev_code, py), (code, y)):
                        try:
                            got = download(lg, c, sy, known)
                            known = sorted(set(known) | {m["h"] for m in got} | {m["a"] for m in got})
                            new += got; log[f"{lg}-{c}"] = len(got)
                        except Exception as e:
                            log[f"{lg}-{c}"] = f"hata: {e.__class__.__name__}"
            except Exception as e:
                log[lg] = f"hata: {e.__class__.__name__}"
        ms = [m for m in merge(old, new) if m["d"] >= since]
        if not ms: continue
        last_season = max(m["season"] for m in ms)
        cur_ms = [m for m in ms if m["season"] == last_season]
        season[lg] = {"name": lname, "asOf": max(m["d"] for m in cur_ms), "season": last_season, "matches": ms}
    print("İndirme:", json.dumps(log, ensure_ascii=False), flush=True)
    json.dump(season, open(sp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # --- Avrupa kupaları
    dom_names = {}
    for lg, d in season.items():
        if d.get("cup") or lg not in UEFA: continue
        for m in d["matches"]:
            if m["season"] == d.get("season"): dom_names[m["h"]] = lg; dom_names[m["a"]] = lg
    all_dom = sorted(dom_names)
    for ck, (cid, cname) in CUPS.items():
        old = season.get(ck, {}).get("matches", [])
        new = []
        if not offline:
            try:
                for e in download_cup(cid, y):
                    d = (e.get("dateEvent") or "")[:10]
                    if not d or d < since: continue
                    h = CUP_MAP.get(e["strHomeTeam"]) or resolve(e["strHomeTeam"], all_dom)
                    a = CUP_MAP.get(e["strAwayTeam"]) or resolve(e["strAwayTeam"], all_dom)
                    new.append({"d": d, "h": h, "a": a, "ft": [int(e["intHomeScore"]), int(e["intAwayScore"])], "ht": None,
                                "season": season_of(d), "id": e["idEvent"]})
                log[ck] = len(new)
            except Exception as ex:
                log[ck] = f"hata: {ex.__class__.__name__}"
        byid = {m.get("id") or (m["d"], m["h"], m["a"]): m for m in old if m["d"] >= since}
        for m in new: byid[m["id"]] = m
        ms = sorted(byid.values(), key=lambda m: (m["d"], m["h"]))
        for m in ms: m["hl"] = dom_names.get(m["h"]); m["al"] = dom_names.get(m["a"])
        if ms:
            season[ck] = {"name": cname, "cup": True, "asOf": ms[-1]["d"], "season": max(m["season"] for m in ms), "matches": ms}
    print("Kupalar:", {k: log.get(k) for k in CUPS}, flush=True)
    json.dump(season, open(sp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    if not offline:
        try: fetch_logos(season)
        except Exception as e: print("Logo hatası:", e, flush=True)

    mp = os.path.join(DATA, "model.json")
    model = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    P0 = {"decay": 0.004, "prior": 2.5, "rho": -0.06, "formW": 0.3, "mkt": 0.5}
    P0.update({k: v for k, v in model.get("params", {}).items() if k in P0})
    nx = sum(market_xg(d["matches"]) for d in season.values() if not d.get("cup"))
    print(f"Piyasa beklenen golü hesaplanan yeni maç: {nx}", flush=True)
    json.dump(season, open(sp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    all_ms = {lg: d["matches"] for lg, d in season.items() if not d.get("cup")}
    # Ayarlar az veriyle seçildiyse (ilk kurulum) veya haftanın ilk günüyse tam öğrenme
    # Sürekli öğrenme: her çalıştırmada ayarlar yeni veriyle baştan aranır (yaklaşık 1-2 dakika, ücretsiz)
    # Akıllı nöbet: motor saatte bir uyanır; yeni maç sonucu yoksa yeniden eğitmez (aynı veri = aynı model),
    # yalnızca oranları, fikstürü ve tahmin karnesini tazeler. Yeni sonuç gelince tam öğrenme yapar.
    import hashlib
    fp = hashlib.sha1(json.dumps(sorted((lg, [(m["d"], m["h"], m["a"], m["ft"], m.get("ht"), m.get("odds"), m.get("ou")) for m in ms])
                                         for lg, ms in all_ms.items())).encode()).hexdigest()[:16]
    quick = (model.get("fp") == fp and model.get("engine") == ENGINE_V and bool(model.get("backtest")) and "--force" not in sys.argv)
    full = "--no-tune" not in sys.argv and not quick
    if quick:
        print("Yeni maç sonucu yok: eğitim atlandı, yalnızca oranlar ve fikstür tazeleniyor", flush=True)
        P, bt = dict(model["params"]), None
    elif full:
        print("Yeni sonuç var: ayar aranıyor (tam öğrenme)…", flush=True)
        P, bt = tune(all_ms, P0)
    else:
        print("Günlük test (ayarlar korunuyor)…", flush=True)
        P, bt = dict(P0), backtest(all_ms, P0)
    if not quick and bt:
        cal = calibrate(bt, P["rho"]); P["calT"], P["gscale"], P["dk"] = cal["T"], cal["g"], cal["dk"]
        CAL_INFO.clear(); CAL_INFO.update(cal)
    if not quick:
        P["h1"] = h1_share(all_ms)
        mw, mstats = tune_market(bt) if bt else (0.6, None)
        P["marketW"] = mw
    else:
        mstats = model.get("market")
    cup = learn_strength(season, P, today)
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mt = metrics(bt, P) if bt else dict(model.get("backtest", {}))
    if GUARD: mt["dogrulama"] = GUARD
    if CAL_INFO: mt["kalibrasyon"] = dict(CAL_INFO)
    try:
        rk = risk_test(bt) if bt else mt.get("risk")
        if rk: mt["risk"] = rk; P["risk"] = rk["kural"]
        print("Yüksek kazanç kuralı:", rk and rk["secilen"], flush=True)
    except Exception as e:
        print("risk testi atlandı:", e, flush=True)
    try:
        hz = horizon_test(all_ms, P) if (full or not model.get("backtest", {}).get("uzun_vade")) and not quick else model.get("backtest", {}).get("uzun_vade")
        if hz: mt["uzun_vade"] = hz; P["decay90"] = hz.get("uzun_vade_decay", P["decay"])
        print("Uzun vade testi:", json.dumps(hz, ensure_ascii=False), flush=True)
    except Exception as e:
        print("uzun vade testi atlandı:", e, flush=True)
    if mt.get("score_test"): P["scoreMode"] = mt["score_test"]["secilen"]
    # Yaklaşan maçlar: oranları kaydet, tahminleri önceden arşivle, geçmiş tahminleri gerçek sonuçla puanla
    fxp = os.path.join(DATA, "fixtures.json"); plp = os.path.join(DATA, "predlog.json")
    fx = [] if offline else download_fixtures(season, today)
    if not fx and os.path.exists(fxp):
        fx = [f for f in json.load(open(fxp, encoding="utf-8")) if f["d"] >= today.isoformat()]
    json.dump([{k: v for k, v in f.items() if k != "xg"} for f in fx], open(fxp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    plog = json.load(open(plp, encoding="utf-8")) if os.path.exists(plp) else []
    have = {e["id"] for e in plog}
    played = {(lg, m["h"], m["a"], m["d"]) for lg, ms in all_ms.items() for m in ms}
    now_utc = datetime.now(timezone.utc)
    def kickoff(f):
        try:
            from zoneinfo import ZoneInfo
            hh, mm = (f.get("t") or "23:59").split(":")[:2]
            return datetime.fromisoformat(f["d"]).replace(hour=int(hh), minute=int(mm), tzinfo=ZoneInfo("Europe/London"))
        except Exception:
            return datetime.fromisoformat(f["d"] + "T23:59:00+00:00")
    fx_lock = [f for f in fx if kickoff(f) > now_utc and (f["lg"], f["h"], f["a"], f["d"]) not in played]
    for e in predict_fixtures(fx_lock, all_ms, P, today):
        if e["id"] not in have:                           # maçtan önceki ilk tahmin kilitlenir, sonradan değiştirilmez
            e["v"] = ENGINE_V; e["ts"] = now_utc.strftime("%Y-%m-%dT%H:%MZ"); plog.append(e)
    plog = grade_predlog(plog, all_ms, today)
    json.dump(plog, open(plp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    live = live_report(plog, today)
    print("Canlı karne:", json.dumps(live, ensure_ascii=False), flush=True)
    model = {"live": live, "cup": cup, "updated": now, "tuned": now if not quick else model.get("tuned", now), "fp": fp, "engine": ENGINE_V, "data_v": DATA_V,
             "checks": (model.get("checks", 0) + 1), "trainings": model.get("trainings", 0) + (0 if quick else 1),
             "tuned_n": (bt["n"] if bt else 0) if not quick else model.get("tuned_n", 0), "params": P, "backtest": mt, "market": mstats, "sources": log,
             "leagues": {lg: {"name": d.get("name", LEAGUES.get(lg, ("", "", lg))[2]), "asOf": d["asOf"],
                              "n": len([m for m in d["matches"] if m["season"] == d.get("season")]), "n_all": len(d["matches"]),
                              "avg": round(sum(sum(m["ft"]) for m in d["matches"] if m["season"] == d.get("season")) / max(1, len([m for m in d["matches"] if m["season"] == d.get("season")])), 2)}
                         for lg, d in season.items()}}
    json.dump(model, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1, allow_nan=False)
    hp = os.path.join(DATA, "history.json")
    hist = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else []
    if mt and not quick:
        hist.append({"t": now, "n": mt["n"], "logloss": mt["logloss"], "brier": mt["brier"], "r1x2": mt["r1x2"]})
        hist = hist[-200:]
    json.dump(hist, open(hp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("Bitti:", json.dumps({k: v for k, v in mt.items() if k != "by_league"}, ensure_ascii=False), "params", P)

if __name__ == "__main__":
    main()
