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
from datetime import datetime, date, timezone
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
        if kn.startswith(n) or n.startswith(kn): return k
    best = difflib.get_close_matches(n, [norm(k) for k in known], n=1, cutoff=0.75)
    if best:
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
    idx = {}
    for m in old:
        m.setdefault("season", season_of(m["d"])); idx[(m["season"], m["h"], m["a"])] = m
    for m in new:
        k = (m["season"], m["h"], m["a"])
        if k in idx:
            o = idx[k]
            if m.get("ht") is None and o.get("ht"): m["ht"] = o["ht"]
            for f in ("odds", "ou"):
                if f not in m and f in o: m[f] = o[f]
        idx[k] = m
    return sorted(idx.values(), key=lambda m: (m["d"], m["h"]))

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

def fit(ms, ref_day, P, init=None, iters=25):
    """Ağırlıklı Poisson (Maher) modeli; uygulamadaki fitLeague ile aynı matematik."""
    teams = sorted({m["h"] for m in ms} | {m["a"] for m in ms})
    ti = {t: i for i, t in enumerate(teams)}
    hi = np.array([ti[m["h"]] for m in ms]); ai = np.array([ti[m["a"]] for m in ms])
    hg = np.array([m["ft"][0] for m in ms], float); ag = np.array([m["ft"][1] for m in ms], float)
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
    by = {}
    for i, r in enumerate(rows):
        b = by.setdefault(r[0], [0, 0]); b[0] += 1; b[1] += int(p[i].argmax() == res[i])
    out["by_league"] = {k: {"n": v[0], "r1x2": round(v[1] / v[0], 4)} for k, v in by.items()}
    return out

def tune(all_ms, P0):
    """Koordinat iniş: her ayarı sırayla dene, geriye dönük log-loss'u düşüreni tut."""
    grid = {"decay": [0.001, 0.002, 0.004, 0.007, 0.012], "prior": [1.0, 2.5, 4.0, 6.0],
            "rho": [-0.15, -0.1, -0.06, -0.02, 0.0], "formW": [0.0, 0.15, 0.3, 0.45]}
    P = dict(P0); cur = backtest(all_ms, P)
    if not cur: return P, None
    if cur["n"] < 300:
        print(f"  test örneği az ({cur['n']} maç), ayarlar korunuyor", flush=True)
        return P, cur
    best = cur["logloss"]
    for _ in range(2):
        changed = False
        for key, vals in grid.items():
            for v in vals:
                if v == P[key]: continue
                Q = dict(P); Q[key] = v
                bt = backtest(all_ms, Q) if key != "rho" else None
                if key == "rho":
                    p, *_ = outcome_probs(np.array([r[2] for r in cur["rows"]]), np.array([r[3] for r in cur["rows"]]), v)
                    ll = -np.log(np.maximum(p[np.arange(len(cur["rows"])), cur["res"]], 1e-9)).mean()
                else:
                    ll = bt["logloss"]
                if ll < best - 1e-5:
                    best = ll; P = Q; changed = True
                    print(f"  {key}={v}  logloss={ll:.4f}", flush=True)
        if not changed: break
    return P, backtest(all_ms, P)

def h1_share(all_ms):
    g1 = g = 0
    for ms in all_ms.values():
        for m in ms:
            if m.get("ht"): g1 += sum(m["ht"]); g += sum(m["ft"])
    return round(min(max((g1 + 0.44 * 40) / (g + 40), 0.36), 0.52), 4)

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

def main():
    offline = "--offline" in sys.argv
    sp = os.path.join(DATA, "season.json")
    season = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {}
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

    mp = os.path.join(DATA, "model.json")
    model = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    P0 = {"decay": 0.004, "prior": 2.5, "rho": -0.06, "formW": 0.3}
    P0.update({k: v for k, v in model.get("params", {}).items() if k in P0})
    all_ms = {lg: d["matches"] for lg, d in season.items() if not d.get("cup")}
    # Ayarlar az veriyle seçildiyse (ilk kurulum) veya haftanın ilk günüyse tam öğrenme
    full = "--tune" in sys.argv or today.weekday() == 0 or model.get("tuned_n", 0) < 1000
    if full:
        print("Ayar aranıyor (haftalık tam öğrenme)…", flush=True)
        P, bt = tune(all_ms, P0)
    else:
        print("Günlük test (ayarlar korunuyor)…", flush=True)
        P, bt = dict(P0), backtest(all_ms, P0)
    P["h1"] = h1_share(all_ms)
    mw, mstats = tune_market(bt) if bt else (0.6, None)
    P["marketW"] = mw
    cup = learn_strength(season, P, today)
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mt = metrics(bt, P) if bt else {}
    model = {"cup": cup, "updated": now, "tuned": now if full else model.get("tuned", now),
             "tuned_n": (bt["n"] if bt else 0) if full else model.get("tuned_n", 0), "params": P, "backtest": mt, "market": mstats, "sources": log,
             "leagues": {lg: {"name": d.get("name", LEAGUES.get(lg, ("", "", lg))[2]), "asOf": d["asOf"],
                              "n": len([m for m in d["matches"] if m["season"] == d.get("season")]), "n_all": len(d["matches"]),
                              "avg": round(sum(sum(m["ft"]) for m in d["matches"] if m["season"] == d.get("season")) / max(1, len([m for m in d["matches"] if m["season"] == d.get("season")])), 2)}
                         for lg, d in season.items()}}
    json.dump(model, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    hp = os.path.join(DATA, "history.json")
    hist = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else []
    if mt:
        hist.append({"t": now, "n": mt["n"], "logloss": mt["logloss"], "brier": mt["brier"], "r1x2": mt["r1x2"]})
        hist = hist[-200:]
    json.dump(hist, open(hp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("Bitti:", json.dumps({k: v for k, v in mt.items() if k != "by_league"}, ensure_ascii=False), "params", P)

if __name__ == "__main__":
    main()
