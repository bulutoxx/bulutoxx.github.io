#!/usr/bin/env python3
"""OXXai veri güncelleme ve otonom öğrenme motoru.

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
import csv, io, json, math, os, re, sys, time, unicodedata, urllib.request, difflib
from datetime import datetime, date, timezone, timedelta
import collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
  "Atletico Madrid":"Atlético Madrid","Sporting CP":"Sp Lisbon","Sporting Lisbon":"Sp Lisbon","Galatasaray SK":"Galatasaray",
  "Fenerbahce SK":"Fenerbahçe","Besiktas JK":"Beşiktaş","Istanbul Basaksehir":"Başakşehir",
  # ESPN kupa adları -> lig adları
  "Fenerbahce":"Fenerbahçe","Besiktas":"Beşiktaş","Internazionale":"Inter","AEK Athens":"AEK","AGF":"Aarhus","Braga":"Sp Braga",
  "F.C. København":"FC Copenhagen","FC Copenhagen":"FC Copenhagen","Heart of Midlothian":"Hearts","KAA Gent":"Gent","LASK Linz":"LASK",
  "Lausanne Sports":"Lausanne","Mjällby AIF":"Mjallby","NEC Nijmegen":"Nijmegen","RB Salzburg":"Salzburg","Red Bull Salzburg":"Salzburg",
  "Racing Genk":"Genk","KRC Genk":"Genk","Rapid Vienna":"SK Rapid","Sint-Truidense":"St Truiden","Stade Rennais":"Rennes",
  "TSG Hoffenheim":"Hoffenheim","Union St.-Gilloise":"St. Gilloise","Union Saint-Gilloise":"St. Gilloise","Legia Warsaw":"Legia",
  "Jagiellonia Bialystok":"Jagiellonia","Ajax Amsterdam":"Ajax","KuPS Kuopio":"KuPS","CSU Craiova":"Univ. Craiova",
  "Universitatea Craiova":"Univ. Craiova","PSV Eindhoven":"PSV Eindhoven","Olympiacos":"Olympiakos","PAOK Salonika":"PAOK",
  "Club Brugge":"Club Brugge","Celtic":"Celtic","Rangers":"Rangers","FC Midtjylland":"Midtjylland",
  "Malmo FF":"Malmo FF","FCSB":"FCSB",
  
  "Tottenham Hotspur":"Tottenham","Aston Villa":"Aston Villa",
  "Crystal Palace":"Crystal Palace","Olympique Lyonnais":"Lyon","Olympique de Marseille":"Marseille","AS Monaco":"Monaco",
  "Lille":"Lille","OGC Nice":"Nice",
  "Villarreal":"Villarreal","AS Roma":"Roma","SS Lazio":"Lazio","Napoli":"Napoli","Atalanta":"Atalanta","Fiorentina":"Fiorentina",
  "Bologna":"Bologna","Juventus":"Juventus","Benfica":"Benfica","FC Porto":"Porto","Feyenoord Rotterdam":"Feyenoord","AZ Alkmaar":"AZ Alkmaar",
  "FC Twente":"Twente","FC Utrecht":"Utrecht","Young Boys":"Young Boys","FC Basel":"Basel","Servette":"Servette","Sturm Graz":"Sturm Graz",
  "Trabzonspor":"Trabzonspor","Samsunspor":"Samsunspor","Galatasaray":"Galatasaray"}

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

T_START = time.time()
TIME_BUDGET = 1800   # sn: kaynaklar takılırsa iş 45 dk sınırına çarpmasın, eldekiyle devam etsin

def fetch(url):
    if time.time() - T_START > TIME_BUDGET: raise TimeoutError("süre bütçesi doldu")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 BULUTOXX-updater"})
    with urllib.request.urlopen(req, timeout=25) as r:
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
            # korner, kart ve şut (varsa): korner/kart tahmin modeli için
            try:
                if row.get("HC", "") not in ("", None) and row.get("AC", "") not in ("", None): m["c"] = [int(float(row["HC"])), int(float(row["AC"]))]
                if row.get("HY", "") not in ("", None) and row.get("AY", "") not in ("", None):
                    m["k"] = [int(float(row["HY"])) + int(float(row.get("HR") or 0)), int(float(row["AY"])) + int(float(row.get("AR") or 0))]
                if row.get("HST", "") not in ("", None) and row.get("AST", "") not in ("", None): m["st"] = [int(float(row["HST"])), int(float(row["AST"]))]
            except (TypeError, ValueError):
                pass
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
            for f in ("odds", "ou", "c", "k", "st"):
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
def power_devig(o):
    """Bahis marjını 'power' yöntemiyle ayır: p_i = (1/o_i)^k, toplam 1 olacak k bulunur (favori-sürpriz yanlılığını düzeltir)."""
    q = 1 / np.asarray(o, float); lo, hi = 1.0, 3.0
    for _ in range(40):
        k = (lo + hi) / 2
        if (q ** k).sum() > 1: lo = k
        else: hi = k
    p = q ** k; return p / p.sum()

def _rollback():
    """🛡️ Koruyucu bot bir değişikliği geri aldıysa (data/rollback.json) süresi boyunca önceki yapılandırma kullanılır."""
    try:
        R = json.load(open(os.path.join(DATA, "rollback.json"), encoding="utf-8"))
        if R.get("aktif") and R.get("bitis", "") >= date.today().isoformat(): return R
    except Exception: pass
    return None

def _devig_method():
    """Araştırmacı bot (lab/research.py) kendi arşivimizde daha iyi bir marj ayırma yöntemi kanıtladıysa onu kullan."""
    RB = _rollback()
    if RB: return RB.get("devig", "power")
    try:
        R = json.load(open(os.path.join(DATA, "research.json"), encoding="utf-8"))
        if R.get("devig_kabul") and R.get("devig") in ("power", "prop", "shin", "hibrit"): return R["devig"]
    except Exception: pass
    return "power"

HYB_MARGIN = 0.12
def devig(o, m):
    if m == "power": return power_devig(o)
    q = 1 / np.asarray(o, float)
    if m == "hibrit":
        # Marja duyarlı ayırma (2026-10-25 teşhisi): geçmişte (%8 marj, 15.080 maç) power en iyi (LL 1,0040 vs oransal 1,0048);
        # kilitli iddaa arşivinde (%18 marj, 468 maç) oransal iki zaman yarısında da power'dan iyi (1X2 LL 1,0047→1,0034 / 1,0599→1,0443).
        # Yalnız araştırmacı bot arşivde (≥1.500 maç, iki yarı) kanıtlarsa devreye girer.
        return power_devig(o) if q.sum() - 1 < HYB_MARGIN else q / q.sum()
    if m == "prop": return q / q.sum()
    B = q.sum(); lo, hi = 0.0, 0.4
    for _ in range(50):
        z = (lo + hi) / 2; p = (np.sqrt(z * z + 4 * (1 - z) * q * q / B) - z) / (2 * (1 - z))
        if p.sum() > 1: lo = z
        else: hi = z
    return p / p.sum()

def market_xg(matches):
    """Kapanış oranlarından maç başına piyasa beklenen golü (xg) çıkar; bir kez hesaplanır, saklanır."""
    global _TABLE
    DM = _devig_method(); tag = {"power": "pow"}.get(DM, DM)
    todo = [m for m in matches if m.get("odds") and ("xg" not in m or m.get("xg_o") != m["odds"] or m.get("xg_m") != tag)]
    if not todo: return 0
    if _TABLE is None:
        lam = np.arange(0.15, 4.01, 0.05)
        LH, LA = np.meshgrid(lam, lam, indexing="ij"); LH = LH.ravel(); LA = LA.ravel()
        p, pO, _, _ = outcome_probs(LH, LA, -0.06)
        _TABLE = (LH, LA, p[:, 0], p[:, 2], pO)
    LH, LA, TH, TA, TO = _TABLE
    for i in range(0, len(todo), 1500):
        ch = todo[i:i + 1500]
        inv = np.array([devig(m["odds"], DM) for m in ch])      # marj ayırma: varsayılan 'power' (2025 ve 2026'da oransaldan iyi), araştırmacı bot değiştirebilir
        ou = np.array([devig(m["ou"], DM)[0] if m.get("ou") else np.nan for m in ch])
        d = (TH[None, :] - inv[:, :1]) ** 2 + (TA[None, :] - inv[:, 2:3]) ** 2
        has = ~np.isnan(ou)
        if has.any(): d[has] += (TO[None, :] - ou[has, None]) ** 2
        k = d.argmin(1)
        for m, j in zip(ch, k): m["xg"] = [round(float(LH[j]), 2), round(float(LA[j]), 2)]; m["xg_o"] = list(m["odds"]); m["xg_m"] = tag
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
    G0, G1 = P.get("gmin", 1.0), P.get("gmax", 1.6)
    mu = (w * ag).sum() / w.sum(); gamma = min(max((w * hg).sum() / max((w * ag).sum(), .1), G0), G1)
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
        mu = (w * ag).sum() / da; gamma = min(max(((w * hg).sum() / dh) / mu, G0), G1)
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

GOLLU_T = 0.50   # 3,5 Üst olasılığı bu eşiği geçerse skor 4+ gollü seçilir

def pick_scores(g, p, pO):
    """Tutarlı skor: tahmin edilen sonuç (1/X/2) ve 2.5 alt/üst yönüyle uyumlu en olası skor (düz mod hep 1-1 der)."""
    n, K = g.shape[0], g.shape[1]; ii, jj = np.meshgrid(np.arange(K), np.arange(K), indexing="ij")
    om = [(ii > jj), (ii == jj), (ii < jj)]; pr = p.argmax(1); out = []
    for t in range(n):
        # Gollü maç: 3,5 Üst olasılığı ≥ GOLLU_T ise 4+ gollü, sonuçla uyumlu en olası skor (25 bin maç testi:
        # eşik .42'de bu maçların %51'inde gerçekten 4+ gol çıktı (genel %31), eşik .50'de %60; tam skor isabeti değişmedi)
        o35 = float((g[t] * ((ii + jj) > 3)).sum()) / max(1e-12, float(g[t].sum()))
        if o35 >= GOLLU_T: gg = g[t] * (om[pr[t]] & ((ii + jj) > 3))
        else: gg = g[t] * (om[pr[t]] & (((ii + jj) > 2) if pO[t] >= .5 else ((ii + jj) <= 2)))
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

# ------------------------------------------------------------------ 🎯 sunulan yol kalibrasyonu (2026-10-25, ml70)
# Teşhis: calT/gscale/dk motorun MODEL backtest'inde öğreniliyordu, ama uygulama (index.html dist()) bunları oranlı maçta
# PİYASA yoluna uyguluyor (marketW=1 → olasılık tamamen piyasadan). 11.426 maçlık aylık yürüyen sınamada eski ayarlar
# piyasa yolunu kötüleştiriyordu (1X2 log-loss 1,00249 → 1,00273; Altın isabeti %80,1 → %77,2). Burada kalibrasyon
# uygulamanın gerçekten sunduğu yolda (power marj ayırma → gol beklentisi tablosu → yarı yarıya Dixon-Coles → T/dk) öğrenilir.
_UI_TAB = {}
def _dc_grid(l1, l2, rho, K):
    k = np.arange(K + 1); lf = np.array([math.lgamma(i + 1) for i in k])
    a = np.exp(-l1[:, None] + k[None] * np.log(np.maximum(l1[:, None], 1e-9)) - lf); b = np.exp(-l2[:, None] + k[None] * np.log(np.maximum(l2[:, None], 1e-9)) - lf)
    g = a[:, :, None] * b[:, None, :]
    g[:, 0, 0] *= np.maximum(1 - l1 * l2 * rho, 0); g[:, 0, 1] *= 1 + l1 * rho; g[:, 1, 0] *= 1 + l2 * rho; g[:, 1, 1] *= 1 - rho
    g = np.maximum(g, 0); return g / g.sum((1, 2), keepdims=True)

def ui_market_lam(odds, ous, rho, dv="power"):
    """index.html fitMarket()'in aynısı: power marj ayırma, (0,25–3,8)×(0,2–3,4) tablo, 1X2 (+2,5 üst) en yakın nokta.
    dv: yalnız laboratuvar kıyası için başka marj ayırma (uygulama bugün yalnız power kullanır)."""
    key = round(float(rho), 4)
    if key not in _UI_TAB:
        LH, LA = np.meshgrid(np.arange(0.25, 3.8001, 0.05), np.arange(0.2, 3.4001, 0.05), indexing="ij"); LH = LH.ravel(); LA = LA.ravel()
        G = _dc_grid(LH, LA, rho, 10); ii, jj = np.meshgrid(np.arange(11), np.arange(11), indexing="ij")
        _UI_TAB[key] = (LH, LA, (G * (ii > jj)).sum((1, 2)), (G * (ii == jj)).sum((1, 2)), (G * (ii < jj)).sum((1, 2)), (G * ((ii + jj) > 2)).sum((1, 2)))
    LH, LA, TH, TD, TA, TO = _UI_TAB[key]
    dvf = power_devig if dv == "power" else (lambda o: devig(o, dv))
    p = np.array([dvf(o) for o in odds]); po = np.array([dvf(o)[0] if o else np.nan for o in ous])
    out = np.zeros((len(p), 2))
    for s in range(0, len(p), 400):
        pp, oo = p[s:s + 400], po[s:s + 400]
        e = (TH[None] - pp[:, :1]) ** 2 + (TD[None] - pp[:, 1:2]) ** 2 + (TA[None] - pp[:, 2:3]) ** 2
        has = ~np.isnan(oo)
        if has.any(): e[has] += (TO[None] - oo[has, None]) ** 2
        k = e.argmin(1); out[s:s + 400, 0] = LH[k]; out[s:s + 400, 1] = LA[k]
    return out

def served_probs(lh, la, g, rho, h1):
    """index.html dist()'in aynısı (kalibrasyonsuz kısım): kıstırma, gol ölçeği g, iki yarı ayrı Dixon-Coles, maç sonu = birleşim."""
    lh = np.clip(lh, .15, 4.5) * g; la = np.clip(la, .1, 4) * g
    g1 = _dc_grid(lh * h1, la * h1, rho, 7); g2 = _dc_grid(lh * (1 - h1), la * (1 - h1), rho * .6, 7)
    ft = np.zeros((len(lh), 15, 15))
    for a in range(8):
        for b in range(8): ft[:, a:a + 8, b:b + 8] += g1[:, a, b, None, None] * g2
    i, j = np.meshgrid(np.arange(15), np.arange(15), indexing="ij")
    return np.stack([(ft * (i > j)).sum((1, 2)), (ft * (i == j)).sum((1, 2)), (ft * (i < j)).sum((1, 2))], 1), (ft * ((i + j) > 2)).sum((1, 2))

def _cal3(p, T, dk):
    q = p ** T; q /= q.sum(1, keepdims=True); q[:, 1] *= dk; return q / q.sum(1, keepdims=True)

def _gold_stats(q, O, items, idx):
    """Öneri (recOf: oranlı seçenekler içinde en yüksek olasılık) düzeyi ölçüm: ikili log-loss/Brier, ≥%70 ve Altın
    (≥%78, oran 1,20–2,00, günde en fazla 3) isabeti."""
    picks = []
    for t in idx:
        d, odds, ou, r, ov = items[t]
        c = [(q[t, 0], odds[0], r == 0), (q[t, 1], odds[1], r == 1), (q[t, 2], odds[2], r == 2)]
        if ou: c += [(O[t], ou[0], ov), (1 - O[t], ou[1], not ov)]
        b = max(c, key=lambda x: x[0]); picks.append((d, float(b[0]), b[1], bool(b[2])))
    if not picks: return {}
    pp = np.array([x[1] for x in picks]); yy = np.array([x[3] for x in picks], float); pc = np.clip(pp, 1e-4, 1 - 1e-4)
    m70 = pp >= .70; byd = collections.defaultdict(list)
    for x in picks:
        if x[1] >= .78 and 1.15 <= x[2] <= 2.00: byd[x[0]].append(x)   # Altın alt oran sınırı 1,15 (2026-10-25)
    gold = [x for L in byd.values() for x in sorted(L, key=lambda x: -x[1])[:3]]
    return {"oneri_ll": round(float(-np.mean(yy * np.log(pc) + (1 - yy) * np.log(1 - pc))), 5), "oneri_brier": round(float(np.mean((pp - yy) ** 2)), 5),
            "n70": int(m70.sum()), "hit70": round(float(yy[m70].mean()), 4) if m70.any() else None,
            "altin_n": len(gold), "altin_hit": round(float(np.mean([x[3] for x in gold])), 4) if gold else None}

def load_deep(season):
    """🗄️ Derin arşiv (lab/derin.py: football-data'nın bitmiş eski sezonları). Yalnız season.json'daki en eski maçtan önceki,
    oranlı maçlar döner (çakışma yok). Dosya yoksa boş liste."""
    out = []
    first = {lg: min(m["d"] for m in d["matches"]) for lg, d in season.items() if d.get("matches") and not d.get("cup")}
    for f in sorted(__import__("glob").glob(os.path.join(DATA, "derin", "*-*.json"))):
        try: D = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        lg = D.get("lg"); cut = first.get(lg, "9999")
        for r in D.get("m", []):
            if r[0] < cut and r[5] and r[6] and r[7]:
                out.append({"d": r[0], "ft": [r[3], r[4]], "odds": [r[5], r[6], r[7]], "ou": [r[8], r[9]] if r[8] and r[9] else None})
    return out

def _odds_share():
    """Uygulamadaki tahminlerin ne kadarı oranlı (piyasa yolu)? Son fikstür dosyasından; yoksa 0,7."""
    try:
        F = json.load(open(os.path.join(DATA, "fixtures.json"), encoding="utf-8"))
        if len(F) >= 50: return min(max(sum(1 for f in F if f.get("odds")) / len(F), 0.5), 0.95)
    except Exception: pass
    return 0.7

def calibrate_served(bt, P, legacy=None, deep=None, w_srv=None):
    """calT/gscale/dk'yı uygulamanın sunduğu yolda öğren. Amaç = w·(oranlı maç, piyasa yolu) + (1−w)·(oransız maç, model yolu);
    w = fikstürde oranlı maç payı. İlk %70'te (öncesi + derin arşiv) seçilir, son %30'da sınanır.
    Kabul: son %30'da amaç şu anki (model-yolu) kalibrasyondan iyi VE Altın isabeti ondan düşük değil."""
    rows = bt["rows"]; n = len(rows); res = bt["res"]; rho = P["rho"]; h1 = P.get("h1", .44); mw = P.get("marketW", .6)
    if n < 500: return {"kabul": False, "neden": "az veri"}
    w = _odds_share() if w_srv is None else w_srv
    tot = np.array([sum(r[1]["ft"]) for r in rows]); dts = [r[1]["d"] for r in rows]
    split = sorted(dts)[int(n * .7)]; late_m = np.array([d >= split for d in dts])
    lhm = np.array([r[2] for r in rows]); lam = np.array([r[3] for r in rows])
    oi = [i for i, r in enumerate(rows) if r[1].get("odds")]
    items = [(rows[i][1]["d"], rows[i][1]["odds"], rows[i][1].get("ou"), int(res[i]), tot[i] > 2) for i in oi]
    deep = (deep or []) if mw >= 0.9 else []          # derin arşivde model tahmini yok: yalnız piyasa ağırlıklıyken kullanılır
    for m in deep:
        a, b = m["ft"]; items.append((m["d"], m["odds"], m["ou"], 0 if a > b else 1 if a == b else 2, a + b > 2))
    if len(oi) < 300: return {"kabul": False, "neden": "oranlı maç az"}
    mk = ui_market_lam([x[1] for x in items], [x[2] for x in items], rho)
    sl = mk.copy()
    if mw < 1:
        sl[:len(oi), 0] = np.exp((1 - mw) * np.log(lhm[oi]) + mw * np.log(mk[:len(oi), 0]))
        sl[:len(oi), 1] = np.exp((1 - mw) * np.log(lam[oi]) + mw * np.log(mk[:len(oi), 1]))
    rs = np.array([x[3] for x in items]); ovs = np.array([x[4] for x in items]); hou = np.array([bool(x[2]) for x in items])
    late_s = np.array([x[0] >= split for x in items]); late_s[len(oi):] = False
    GS = (0.98, 1.0, 1.01, 1.02, 1.03, 1.04, 1.05); TS = (0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3); DK = (0.97, 1.0, 1.03, 1.06, 1.1, 1.14, 1.18, 1.22)
    cs = {g: served_probs(sl[:, 0], sl[:, 1], g, rho, h1) for g in GS}
    cm = {g: served_probs(lhm, lam, g, rho, h1) for g in GS}   # ml80: model yolu da uygulamanın dist()'i (iki yarı DC) ile
    def part(p, pO, r, ov, hasou, idx, T, dk):
        q = _cal3(p[idx], T, dk); l1 = -np.log(np.maximum(q[np.arange(len(idx)), r[idx]], 1e-9)).mean()
        j = idx[hasou[idx]]; o = np.clip(pO[j], 1e-9, 1 - 1e-9)
        l2 = -np.mean(np.where(ov[j], np.log(o), np.log(1 - o))) if len(j) else 0.0
        return float(l1), float(l2)
    es, ls = np.where(~late_s & (np.arange(len(items)) >= 0))[0], np.where(late_s)[0]
    em, lm = np.where(~late_m)[0], np.where(late_m)[0]
    ones = np.ones(n, bool)
    def obj(T, g, dk, si, mi):
        a1, a2 = part(*cs[g], rs, ovs, hou, si, T, dk); b1, b2 = part(*cm[g], res, tot > 2, ones, mi, T, dk)
        return w * (a1 + .5 * a2) + (1 - w) * (b1 + .5 * b2)
    best = min(((T, g, dk) for T in TS for g in GS for dk in DK), key=lambda x: obj(*x, es, em))
    def rep(T, g, dk):
        p, O = cs[g]; q = _cal3(p, T, dk); a1, a2 = part(p, O, rs, ovs, hou, ls, T, dk); b1, b2 = part(*cm[g], res, tot > 2, ones, lm, T, dk)
        return dict({"amac": round(obj(T, g, dk, ls, lm), 5), "piyasa_ll_1x2": round(a1, 5), "piyasa_ll_ou": round(a2, 5), "model_ll_1x2": round(b1, 5), "model_ll_ou": round(b2, 5)},
                    **_gold_stats(q, O, items, ls))
    R = {"kimlik": rep(1.0, 1.0, 1.0), "aday": rep(*best)}
    if legacy: R["eski_model_yolu"] = rep(legacy.get("T", 1.0), legacy.get("g", 1.0) if legacy.get("g", 1.0) in cs else 1.0, legacy.get("dk", 1.0))
    # Kıyas: şu an kullanılan yapılandırma (eski model-yolu kalibrasyonu; yoksa kimlik). Aday hem amaçta iyi olmalı
    # hem de Altın isabetini düşürmemeli (iki tarafta da ≥20 Altın seçim varsa ölçülür).
    ki, ad = R.get("eski_model_yolu") or R["kimlik"], R["aday"]
    gold_ok = (ad.get("altin_n", 0) < 20 or ki.get("altin_n", 0) < 20) or (ad.get("altin_hit") or 0) >= (ki.get("altin_hit") or 0) - 1e-9
    ok = ad["amac"] < ki["amac"] - 1e-5 and gold_ok
    out = {"T": best[0], "g": best[1], "dk": best[2], "kabul": bool(ok), "yol": "sunulan", "w_oranli": round(w, 3), "ayrim": split,
           "n_piyasa": len(items), "n_derin": len(deep), "son30": R}
    # 🎯 ml80: tek "son %30" sınaması gürültülüydü (65–92 Altın seçim; CI'da %77,2 → %76,6 farkıyla reddedildi).
    # Yürüyen pencere (her yaz 1 Temmuz'dan bölünen yıllık katlar, derin arşiv + sezon ≈53 bin oranlı maç sınama) ile karar verilir.
    try:
        wf = _served_walkforward(items, cs, cm, res, tot, dts, rs, ovs, hou, w, legacy, TS, GS, DK, n_oi=len(oi), part=part)
        out["wf"] = wf
        if wf.get("karar") is not None:
            out["kabul_son30"] = out["kabul"]; out["kabul"] = bool(wf["karar"])
            if wf["karar"]: out["T"], out["g"], out["dk"] = wf["secilen"]
    except Exception as e:
        print("yürüyen pencere atlandı:", e.__class__.__name__, e, flush=True)
    print("Sunulan yol kalibrasyonu:", json.dumps(out, ensure_ascii=False), flush=True)
    return out

WF_MIN_TEST, WF_MIN_TRAIN = 1500, 5000
def _served_walkforward(items, cs, cm, res, tot, dts, rs, ovs, hou, w, legacy, TS, GS, DK, n_oi, part):
    """ml80 — sunulan yol kalibrasyonunun yürüyen pencere sınaması.
    Katlar: 1 Temmuz sınırlarıyla yıllık; k. kat yalnız kendinden ÖNCEKİ maçlarla (derin arşiv + sezon; model yolu satırları
    varsa (1−w) ağırlıkla) T/g/dk seçer, kendi yılında sınanır. Sınama tahminleri birleştirilip şu an kullanılan yapılandırmayla
    (eski model-yolu kalibrasyonu) karşılaştırılır. Kabul (hepsi):
      1) birleşik sınamada piyasa amacı (1X2 + ½·2,5 log-kayıp) daha düşük ve katların çoğunda daha düşük,
      2) öneri Brier'i daha düşük, 3) Altın isabeti (≥%78, oran 1,20–2,00, günde ≤3) düşmüyor (her iki tarafta ≥100 Altın),
      4) model (oransız) yolu: son katın model satırlarında amaç en fazla 0,002 kötüleşebilir.
    Kabul edilirse uygulanan değer TÜM veride aynı amaçla seçilen T/g/dk'dır (yöntem sınandı, son veriyle yeniden öğrenilir)."""
    n = len(items); idt = np.array([x[0] for x in items]); mdt = np.array(dts)
    if n < WF_MIN_TRAIN + WF_MIN_TEST: return {"karar": None, "neden": "az veri"}
    y0, y1 = int(min(idt)[:4]) + 1, int(max(idt)[:4])
    cuts = [f"{y}-07-01" for y in range(y0, y1 + 1)]
    folds = []
    for i, a in enumerate(cuts):
        b = cuts[i + 1] if i + 1 < len(cuts) else "9999"
        nt = int(((idt >= a) & (idt < b)).sum()); ntr = int((idt < a).sum())
        if nt >= WF_MIN_TEST and ntr >= WF_MIN_TRAIN: folds.append((a, b))
        elif folds and nt: folds[-1] = (folds[-1][0], b)   # küçük son dilim önceki kata eklenir
    if len(folds) < 2: return {"karar": None, "neden": "kat oluşmadı"}
    grid = [(T, g, dk) for T in TS for g in GS for dk in DK]
    allm = np.ones(len(mdt), bool)
    def obj(c, si, mi):
        T, g, dk = c; a1, a2 = part(*cs[g], rs, ovs, hou, si, T, dk); mk_ = a1 + .5 * a2
        if len(mi) < 300: return mk_
        b1, b2 = part(*cm[g], res, tot > 2, allm, mi, T, dk); return w * mk_ + (1 - w) * (b1 + .5 * b2)
    def mkt(c, si):
        T, g, dk = c; a1, a2 = part(*cs[g], rs, ovs, hou, si, T, dk); return a1 + .5 * a2
    def mdl(c, mi):
        T, g, dk = c; b1, b2 = part(*cm[g], res, tot > 2, allm, mi, T, dk); return b1 + .5 * b2
    cur = (legacy.get("T", 1.0), legacy.get("g", 1.0) if legacy.get("g", 1.0) in cs else 1.0, legacy.get("dk", 1.0)) if legacy else (1.0, 1.0, 1.0)
    # öneri düzeyi (recOf): her maçta oranlı seçenekler içinde en yüksek olasılık
    O1 = np.array([x[1] for x in items], float); OU = np.array([x[2] if x[2] else [0, 0] for x in items], float)
    def picks(c, idx):
        T, g, dk = c; p, O = cs[g]; q = _cal3(p[idx], T, dk); Oi = O[idx]
        C5 = np.column_stack([q, np.where(hou[idx], Oi, -1), np.where(hou[idx], 1 - Oi, -1)])
        k = C5.argmax(1); j = np.arange(len(idx)); pp = C5[j, k]
        od = np.where(k < 3, O1[idx][j, np.minimum(k, 2)], OU[idx][j, np.clip(k - 3, 0, 1)])
        r = rs[idx]; ov = ovs[idx]
        y = np.where(k < 3, r == k, np.where(k == 3, ov, ~ov)).astype(float)
        return pp, od, y
    def gold(dd, pp, od):
        m = np.zeros(len(pp), bool); by = collections.defaultdict(list)
        for i in np.where((pp >= .78) & (od >= 1.15) & (od <= 2.0))[0]: by[dd[i]].append(i)   # Altın: oran 1,15–2,00
        for L in by.values():
            for i in sorted(L, key=lambda i: -pp[i])[:3]: m[i] = True
        return m
    rows = []; SEL = {"p": [], "od": [], "y": [], "d": []}; CUR = {"p": [], "od": [], "y": []}; win = 0
    for a, b in folds:
        si_tr = np.where(idt < a)[0]; si_te = np.where((idt >= a) & (idt < b))[0]
        mi_tr = np.where(mdt < a)[0]; mi_te = np.where((mdt >= a) & (mdt < b))[0]
        c = min(grid, key=lambda x: obj(x, si_tr, mi_tr))
        o_new, o_cur = mkt(c, si_te), mkt(cur, si_te); win += o_new < o_cur
        r = {"kat": a, "secilen": list(c), "n": len(si_te), "piyasa_amac": round(o_new, 5), "piyasa_amac_mevcut": round(o_cur, 5)}
        if len(mi_te) >= 300: r["model_amac"] = round(mdl(c, mi_te), 5); r["model_amac_mevcut"] = round(mdl(cur, mi_te), 5)
        rows.append(r)
        for D, cc in ((SEL, c), (CUR, cur)):
            pp, od, y = picks(cc, si_te); D["p"].append(pp); D["od"].append(od); D["y"].append(y)
        SEL["d"] += [items[i][0] for i in si_te]
    dd = SEL["d"]
    def summ(D):
        pp, od, y = (np.concatenate(D[k]) for k in ("p", "od", "y")); g = gold(dd, pp, od); m70 = pp >= .7; pc = np.clip(pp, 1e-4, 1 - 1e-4)
        return {"n": len(pp), "oneri_brier": round(float(np.mean((pp - y) ** 2)), 5), "oneri_ll": round(float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))), 5),
                "n70": int(m70.sum()), "hit70": round(float(y[m70].mean()), 4) if m70.any() else None,
                "altin_n": int(g.sum()), "altin_hit": round(float(y[g].mean()), 4) if g.any() else None}, (pp, od, y, g)
    S_new, A = summ(SEL); S_cur, B = summ(CUR)
    sinama = np.concatenate([np.where((idt >= a) & (idt < b))[0] for a, b in folds])
    S_new["piyasa_amac"] = round(float(np.average([r["piyasa_amac"] for r in rows], weights=[r["n"] for r in rows])), 5)
    S_cur["piyasa_amac"] = round(float(np.average([r["piyasa_amac_mevcut"] for r in rows], weights=[r["n"] for r in rows])), 5)
    # gün blok bootstrap (%95): Δ = aday − mevcut
    ci = {}
    try:
        rng = np.random.default_rng(80); ud = sorted(set(dd)); di = collections.defaultdict(list)
        for i, d_ in enumerate(dd): di[d_].append(i)
        di = [np.array(di[d_]) for d_ in ud]; dg, dh, db = [], [], []
        for _ in range(300):
            idx = np.concatenate([di[j] for j in rng.integers(0, len(ud), len(ud))])
            ga, gb = A[3][idx], B[3][idx]
            if ga.any() and gb.any(): dg.append(A[2][idx][ga].mean() - B[2][idx][gb].mean())
            ma, mb = A[0][idx] >= .7, B[0][idx] >= .7
            if ma.any() and mb.any(): dh.append(A[2][idx][ma].mean() - B[2][idx][mb].mean())
            db.append(np.mean((A[0][idx] - A[2][idx]) ** 2) - np.mean((B[0][idx] - B[2][idx]) ** 2))
        q = lambda v: [round(float(np.percentile(v, 2.5)), 5), round(float(np.percentile(v, 97.5)), 5)] if v else None
        ci = {"altin_hit": q(dg), "hit70": q(dh), "oneri_brier": q(db)}
    except Exception: pass
    last = rows[-1]
    model_ok = "model_amac" not in last or last["model_amac"] <= last["model_amac_mevcut"] + 0.002
    gold_ok = S_new["altin_n"] >= 100 and S_cur["altin_n"] >= 100 and S_new["altin_hit"] >= S_cur["altin_hit"] - 1e-9
    ok = (S_new["piyasa_amac"] < S_cur["piyasa_amac"] - 1e-5 and win * 2 > len(folds) and S_new["oneri_brier"] <= S_cur["oneri_brier"]
          and gold_ok and model_ok)
    allsi = np.arange(n); fin = min(grid, key=lambda x: obj(x, allsi, np.arange(len(mdt))))
    neden = [] if ok else [t for t, c_ in (("piyasa amacı", S_new["piyasa_amac"] < S_cur["piyasa_amac"] - 1e-5), ("katların çoğu", win * 2 > len(folds)),
                                           ("öneri Brier", S_new["oneri_brier"] <= S_cur["oneri_brier"]), ("Altın isabeti", gold_ok), ("model yolu", model_ok)) if not c_]
    return {"karar": bool(ok), "secilen": list(fin), "mevcut": list(cur), "kat_sayisi": len(folds), "kazanilan_kat": int(win),
            "n_sinama": int(len(sinama)), "aday": S_new, "mevcut_sonuc": S_cur, "fark_ci95": ci, "katlar": rows,
            "neden": "geçti" if ok else "geçemedi: " + ", ".join(neden)}

# ------------------------------------------------------------------ 🔒 kilitli arşiv kalibrasyonu (2026-10-27, ml90)
# Teşhis (denetim P1): calibrate_served T/g/dk'yı football-data'nın düşük marjlı (≈%5) ortalama/kapanış oranlarıyla öğreniyor;
# uygulama ise maçtan saatler önce kilitlenen ≈%18 marjlı iddaa oranını sunuyor. Bu dağılım farkı yüzünden kilitli 1.216 maçta
# favori olasılıkları şişik (1,0–1,3 oran bandında power %80,5 / gerçek %77,6; 1,6–2,0 bandında %49,9 / %43,2), beraberlik eksik.
# Burada T/g/dk uygulamanın GERÇEKTEN sunduğu dağılımda öğrenilir: kilitli arşiv (iddaa kilit oranı + sonuç), aynı sunulan yol
# (power marj → gol tablosu → iki yarı Dixon-Coles → T/dk). Kapı: zaman sıralı genişleyen pencere (ilk %40 öğren, kalan 4 dilimde
# yalnız geçmişle seçilip sınanır), lig×gün küme bootstrap %95; kabul edilirse sunulan yolun kalibrasyonunun yerine geçer.
KL_MIN, KL_MIN_GUN, KL_TEST0, KL_FOLDS, KL_BOOT = 800, 14, 0.4, 4, 2000
# KL_MIN_GUN: ilk ölçümde (24–27 Ekim, 3 gün) gün etkisi baskındı (beraberlik %28,7 / %27,6 / %15,8; 0,78+ öneri isabeti
# %69 / %83 / %91). Gün içi maçlar bağımsız değil: karar yalnız ≥14 günlük arşivde ve GÜN-blok bootstrap ile verilir.
KL_TS = (0.80, 0.84, 0.88, 0.91, 0.94, 0.97, 1.0, 1.05, 1.1)
KL_GS = (0.98, 1.0, 1.01, 1.02, 1.04)
KL_DK = (1.0, 1.04, 1.08, 1.12, 1.14, 1.16, 1.2, 1.24, 1.28, 1.32)
KL_BANDS = ((.5, .6), (.6, .7), (.7, .78), (.78, .85), (.85, 1.01))

def kilitli_veri(data_dir=None):
    """Kilitli arşivden sonucu belli, 1X2 iddaa oranı tam maçlar; başlama zamanına (ts) göre sıralı."""
    import arsiv
    out = []
    for d, r in arsiv.kayitlar(data_dir or DATA, puanli=False):
        if r.get("hs") is None or r.get("as") is None or not r.get("ms") or len(r["ms"]) != 3 or not all(r["ms"]): continue
        ou = r.get("ou") if r.get("ou") and len(r["ou"]) == 2 and all(r["ou"]) else None
        hs, as_ = r["hs"], r["as"]
        out.append({"ts": r.get("ts") or 0, "d": d, "c": r.get("c") or "?", "ms": list(r["ms"]), "ou": ou,
                    "res": 0 if hs > as_ else 1 if hs == as_ else 2, "ov": hs + as_ > 2})
    out.sort(key=lambda x: (x["ts"], x["d"]))
    return out

class _KL:
    """Kilitli veride sunulan yol olasılıkları (g başına önbellekli) ve maç başına kayıp."""
    def __init__(self, V, rho, h1, dv="power"):
        self.V, self.rho, self.h1 = V, rho, h1; self.n = len(V)
        self.lam = ui_market_lam([v["ms"] for v in V], [v["ou"] for v in V], rho, dv)
        self.res = np.array([v["res"] for v in V]); self.ov = np.array([v["ov"] for v in V]); self.hou = np.array([v["ou"] is not None for v in V])
        self.O1 = np.array([v["ms"] for v in V], float); self.OU = np.array([v["ou"] or [0, 0] for v in V], float)
        self.day = [v["d"] for v in V]; self.cl = np.unique([f'{v["c"]}|{v["d"]}' for v in V], return_inverse=True)[1]
        self._c = {}
    def probs(self, g):
        if g not in self._c: self._c[g] = served_probs(self.lam[:, 0], self.lam[:, 1], g, self.rho, self.h1)
        return self._c[g]
    def loss(self, c):
        """Maç başına amaç: 1X2 log-kayıp + ½·2,5 log-kayıp (calibrate_served ile aynı ağırlık); ayrıca q, O."""
        T, g, dk = c; p, O = self.probs(g); return _kl_loss_from(self, _cal3(p, T, dk), O)
    def picks(self, q, O):
        """Uygulamadaki öneri (recOf / collector.served_pick): MS 1/X/2 ve 2,5 Üst/Alt içinden en yüksek olasılık."""
        C = np.column_stack([q, np.where(self.hou, O, -1), np.where(self.hou, 1 - O, -1)]); k = C.argmax(1); j = np.arange(self.n)
        pp = C[j, k]; od = np.where(k < 3, self.O1[j, np.minimum(k, 2)], self.OU[j, np.clip(k - 3, 0, 1)])
        y = np.where(k < 3, self.res == k, np.where(k == 3, self.ov, ~self.ov)).astype(float)
        return k, pp, od, y

def _wilson(h, n):
    if not n: return [None, None]
    p = h / n; z = 1.96; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den; w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(c - w, 3), round(c + w, 3)]

def _kl_gold(day, pp, od, idx, cap=3):
    """Altın kuralı (p ≥ 0,78, oran 1,15–2,00, günde en fazla 3); cap=None: günlük sınır yok (uygulamadaki Altın karnesi gibi)."""
    by = collections.defaultdict(list)
    for i in idx:
        if pp[i] >= .78 and 1.15 <= od[i] <= 2.0: by[day[i]].append(i)
    return [i for L in by.values() for i in (sorted(L, key=lambda i: -pp[i])[:cap] if cap else L)]

def _kl_report(K, q, O, idx):
    l1, l2, q, O = _kl_loss_from(K, q, O); k, pp, od, y = K.picks(q, O); i = np.asarray(idx); E = np.eye(3)[K.res[i]]
    hi = i[K.hou[i]]; pc = np.clip(pp[i], 1e-4, 1 - 1e-4)
    bands = []
    for a, b in KL_BANDS:
        m = i[(pp[i] >= a) & (pp[i] < b)]
        if len(m): bands.append({"bant": f"{a:.2f}-{min(b, 1):.2f}", "n": int(len(m)), "tahmin": round(float(pp[m].mean()), 4),
                                 "gercek": round(float(y[m].mean()), 4), "ci95": _wilson(int(y[m].sum()), len(m))})
    g3 = _kl_gold(K.day, pp, od, i, 3); ga = _kl_gold(K.day, pp, od, i, None)
    return {"n": int(len(i)), "amac": round(float((l1[i] + .5 * l2[i]).mean()), 5), "ll_1x2": round(float(l1[i].mean()), 5),
            "ll_ou": round(float(l2[hi].mean()), 5) if len(hi) else None, "brier_1x2": round(float(((q[i] - E) ** 2).sum(1).mean()), 5),
            "beraberlik_tahmin": round(float(q[i, 1].mean()), 4), "beraberlik_gercek": round(float((K.res[i] == 1).mean()), 4),
            "oneri_ort": round(float(pp[i].mean()), 4), "oneri_gercek": round(float(y[i].mean()), 4),
            "oneri_brier": round(float(np.mean((pp[i] - y[i]) ** 2)), 5), "oneri_ll": round(float(-np.mean(y[i] * np.log(pc) + (1 - y[i]) * np.log(1 - pc))), 5),
            "bantlar": bands,
            "altin": {"n": len(g3), "tutan": int(y[g3].sum()) if g3 else 0, "isabet": round(float(y[g3].mean()), 4) if g3 else None,
                      "tahmin": round(float(pp[g3].mean()), 4) if g3 else None, "ci95": _wilson(int(y[g3].sum()), len(g3)) if g3 else None},
            "altin_gunluk_sinirsiz": {"n": len(ga), "isabet": round(float(y[ga].mean()), 4) if ga else None,
                                      "tahmin": round(float(pp[ga].mean()), 4) if ga else None, "ci95": _wilson(int(y[ga].sum()), len(ga)) if ga else None}}

def _kl_boot(K, d, idx, B, seed, gun=False):
    """Küme bootstrap (lig×gün; gun=True: gün blokları): Δ ortalamasının %95 aralığı."""
    idx = np.asarray(idx); cl = np.asarray(K.day)[idx] if gun else K.cl[idx]; u, inv = np.unique(cl, return_inverse=True)
    s = np.bincount(inv, weights=d[idx]); c = np.bincount(inv).astype(float); rng = np.random.default_rng(seed)
    bs = []
    for _ in range(B):
        w = np.bincount(rng.integers(0, len(u), len(u)), minlength=len(u)); bs.append((w * s).sum() / max((w * c).sum(), 1))
    return [round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)]

def calibrate_locked(P, V=None, dv="power", grid=None, cur=None, boot=KL_BOOT, seed=90, K=None):
    """T/g/dk'yı kilitli arşivde (uygulamanın sunduğu iddaa kilit oranı dağılımı) öğren ve kapıdan geçir.
    Zaman sıralı genişleyen pencere: ilk %40 yalnız öğrenme; kalan maçlar 4 ardışık dilim, her dilimde ayar yalnız ondan ÖNCEKİ
    maçlarla seçilir. Birleşik dilim-dışı tahminler şu an sunulan ayarla (cur) maç maç eşleştirilir. Kabul (hepsi):
      1) amaç (1X2 + ½·2,5 log-kayıp) farkının lig×gün küme bootstrap %95 üst sınırı < 0,
      2) sınama döneminin iki zaman yarısında da fark < 0,
      3) 1X2 Brier ve öneri Brier'i kötüleşmiyor.
    Kabul edilirse uygulanan değer TÜM kilitli veride aynı amaçla seçilen T/g/dk'dır."""
    V = kilitli_veri() if V is None else V; n = len(V)
    if n < KL_MIN: return {"kabul": False, "neden": f"az veri ({n} < {KL_MIN})", "n": n}
    rho, h1 = P.get("rho", -0.1), P.get("h1", .4437)
    K = K or _KL(V, rho, h1, dv)
    grid = grid or [(T, g, dk) for T in KL_TS for g in KL_GS for dk in KL_DK]
    cur = tuple(cur or (P.get("calT", 1.0), P.get("gscale", 1.0), P.get("dk", 1.0)))
    tot = {}
    def obj(c):
        if c not in tot: l1, l2, _, _ = K.loss(c); tot[c] = l1 + .5 * l2
        return tot[c]
    s0 = int(n * KL_TEST0); cuts = [s0 + (n - s0) * i // KL_FOLDS for i in range(KL_FOLDS + 1)]
    sel = np.zeros(n); oos = np.arange(s0, n); folds = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        c = min(grid, key=lambda x: obj(x)[:a].mean()); sel[a:b] = obj(c)[a:b]
        folds.append({"egitim_n": a, "sinama_n": b - a, "secilen": list(c), "fark": round(float((obj(c)[a:b] - obj(cur)[a:b]).mean()), 5)})
    d = sel - obj(cur); ci_lg = _kl_boot(K, d, oos, boot, seed); ci_gun = _kl_boot(K, d, oos, boot, seed, gun=True)
    n_gun, n_gun_s = len(set(K.day)), len(set(K.day[i] for i in oos)); ci = ci_gun
    h = (n - s0) // 2; d1, d2 = float(d[s0:s0 + h].mean()), float(d[s0 + h:].mean())
    fin = min(grid, key=lambda x: obj(x).mean())
    # birleşik dilim-dışı rapor: önce (cur) tek ayar; sonra (aday) dilim başına ayar → olasılıkları birleştirip raporla
    l1c, l2c, qc, Oc = K.loss(cur); Q = qc.copy(); OO = Oc.copy()
    for f, (a, b) in zip(folds, zip(cuts[:-1], cuts[1:])):
        _, _, q_, O_ = K.loss(tuple(f["secilen"])); Q[a:b] = q_[a:b]; OO[a:b] = O_[a:b]
    once = _kl_report(K, qc, Oc, oos); sonra = _kl_report(K, Q, OO, oos)
    # Brier farkları için bootstrap
    E = np.eye(3)[K.res]; db = ((Q - E) ** 2).sum(1) - ((qc - E) ** 2).sum(1)
    _, pp1, _, y1 = K.picks(Q, OO); _, pp0, _, y0 = K.picks(qc, Oc); dpb = (pp1 - y1) ** 2 - (pp0 - y0) ** 2
    ci_b = _kl_boot(K, db, oos, boot, seed + 1, gun=True); ci_pb = _kl_boot(K, dpb, oos, boot, seed + 2, gun=True)
    ok_ci, ok_half = ci_gun[1] < 0 and ci_lg[1] < 0, d1 < 0 and d2 < 0
    ok_b = float(db[oos].mean()) <= 0 and float(dpb[oos].mean()) <= 0; ok_g = n_gun >= KL_MIN_GUN
    ok = bool(ok_ci and ok_half and ok_b and ok_g)
    neden = [t for t, c_ in ((f"arşiv {n_gun} gün (< {KL_MIN_GUN})", ok_g), ("Δ amaç güven aralığı sıfırı dışlamıyor", ok_ci),
                             ("iki zaman yarısı aynı yönde değil", ok_half), ("Brier kötüleşiyor", ok_b)) if not c_]
    out = {"kabul": ok, "neden": "geçti" if ok else "geçemedi: " + ", ".join(neden), "yol": "kilitli", "devig": dv,
           "n": n, "n_sinama": int(len(oos)), "gun": n_gun, "gun_sinama": n_gun_s, "ilk": V[0]["d"], "son": V[-1]["d"], "mevcut": list(cur), "secilen": list(fin),
           "T": fin[0], "g": fin[1], "dk": fin[2], "katlar": folds,
           "fark": {"amac": round(float(d[oos].mean()), 5), "amac_ci95": ci_gun, "amac_ci95_lig_gun": ci_lg, "yari1": round(d1, 5), "yari2": round(d2, 5),
                    "brier_1x2": round(float(db[oos].mean()), 5), "brier_1x2_ci95": ci_b,
                    "oneri_brier": round(float(dpb[oos].mean()), 5), "oneri_brier_ci95": ci_pb},
           "once": once, "sonra": sonra,
           # dürüst ileriye dönük karne: şu an sunulan ayarla TÜM kilitli arşiv (bu ayar kilitli veriyle seçilmedi)
           "mevcut_tum_arsiv": _kl_report(K, qc, Oc, np.arange(n))}
    print("Kilitli arşiv kalibrasyonu:", json.dumps({k: out[k] for k in ("kabul", "neden", "n", "gun", "mevcut", "secilen", "fark")}, ensure_ascii=False), flush=True)
    return out

def _kl_loss_from(K, Q, OO):
    j = np.arange(K.n); l1 = -np.log(np.maximum(Q[j, K.res], 1e-9)); o = np.clip(OO, 1e-9, 1 - 1e-9)
    l2 = np.where(K.hou, -np.where(K.ov, np.log(o), np.log(1 - o)), 0.0)
    return l1, l2, Q, OO

def build_ck(season, today):
    """Korner ve kart: takım bazlı oran modeli (gol modeliyle aynı yapı). Laboratuvar: korner 9,5 çizgisinde
    lig ortalamasına göre +%1,5-2,8; kart 3,5 çizgisinde +%3-5 isabet (2024'te seçildi, 2025-26'da doğrulandı)."""
    out = {}
    for lg, d in season.items():
        if d.get("cup") or d.get("src") == "espn": continue
        lgo = {}
        for key, r in (("c", 10), ("k", 5)):
            ms = [dict(d=m["d"], h=m["h"], a=m["a"], ft=m[key]) for m in d["matches"] if key in m]
            if len(ms) < 120: continue
            try:
                F = fit(ms, today, {"decay": 0.004, "prior": 3.0, "mkt": 0.0, "gmin": 0.6, "gmax": 1.6}, iters=25)
            except Exception:
                continue
            lgo[key] = {"mu": round(F["mu"], 4), "g": round(F["gamma"], 4), "r": r,
                        "t": {t: [round(a, 3), round(dd, 3)] for t, (a, dd) in F["t"].items()},
                        "avg": round(float(np.mean([sum(m["ft"]) for m in ms[-300:]])), 2)}
        if lgo: out[lg] = lgo
    json.dump({"test": {"korner_9.5": "lig ort. %52-54 → model %54,5-56,4", "kart_3.5": "lig ort. %56-60 → model %60-62"}, "ligler": out},
              open(os.path.join(DATA, "ck.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return len(out)

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
ENGINE_V = "2026-10-25.ml80"   # ml80: sunulan yol kalibrasyonunda yürüyen pencere kararı (ml70: sunulan yol + derin arşiv)
DATA_V = 3   # 3: kupalar ESPN, takvim yılı sezonları, önek eşleme kaldırıldı; 2: aynı eşleşmenin sezonda birden çok oynanması + sıkı isim eşleme   # motor kodu değişince bir kez tam eğitim yapılır
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

# ESPN'den ek futbol ligleri (football-data'da olmayanlar). Sonuçlar aylık sorguyla, fikstür aynı sorgudan.
EXTRA = {
 "col": ("col.1", "Kolombiya Primera A"), "mx2": ("mex.2", "Meksika Expansion MX"), "nwsl": ("usa.nwsl", "ABD NWSL (Kadın)"),
 "chi": ("chi.1", "Şili Primera División"), "per": ("per.1", "Peru Liga 1"), "ecu": ("ecu.1", "Ekvador LigaPro"),
 "uru": ("uru.1", "Uruguay Primera"), "par": ("par.1", "Paraguay Primera"), "ven": ("ven.1", "Venezuela Primera"),
 "bol": ("bol.1", "Bolivya Primera"), "ar2": ("arg.2", "Arjantin Primera Nacional"), "br2": ("bra.2", "Brezilya Serie B"),
 "ksa": ("ksa.1", "Suudi Arabistan Pro Lig"), "aus": ("aus.1", "Avustralya A-League"), "ausw": ("aus.w.1", "Avustralya A-League Kadın"),
 "nl2": ("ned.2", "Hollanda Eerste Divisie"), "usl": ("usa.usl.1", "ABD USL Championship"), "hon": ("hon.1", "Honduras Liga Nacional"),
 "crc": ("crc.1", "Kosta Rika Primera"), "gua": ("gua.1", "Guatemala Liga Nacional"), "slv": ("slv.1", "El Salvador Primera"),
 "ind": ("ind.1", "Hindistan Süper Lig"), "rsa": ("rsa.1", "Güney Afrika Premiership"), "wsl": ("eng.w.1", "İngiltere WSL (Kadın)"),
 "esw": ("esp.w.1", "İspanya Liga F (Kadın)"), "frw": ("fra.w.1", "Fransa D1 (Kadın)"), "mxw": ("mex.w.1", "Meksika Liga MX Kadın"),
 "nlw": ("ned.w.1", "Hollanda Eredivisie Kadın"),
}
ESPN_UA = {"User-Agent": "Mozilla/5.0 (BULUTOXX)"}
WOMEN = {"nwsl", "wsl", "esw", "frw", "mxw", "nlw"}
CAL_YEAR = {"col", "chi", "per", "ecu", "uru", "par", "ven", "bol", "ar2", "br2", "nwsl", "usl"}   # sezon = takvim yılı
def season_for(lg, d):
    return int(d[:4]) if lg in CAL_YEAR else season_of(d)

def espn_month(slug, ym):
    j = json.loads(fetch(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={ym}&limit=900"))
    res, fx = [], []
    for e in j.get("events", []):
        try:
            c = e["competitions"][0]; cs = {t["homeAway"]: t for t in c["competitors"]}
            h, a = cs["home"]["team"]["displayName"], cs["away"]["team"]["displayName"]
            st = e.get("status", {}).get("type", {}); dt = datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
            try:
                from zoneinfo import ZoneInfo
                uk = dt.astimezone(ZoneInfo("Europe/London"))
            except Exception: uk = dt
            d, t = uk.strftime("%Y-%m-%d"), uk.strftime("%H:%M")
            if st.get("state") == "post" and st.get("completed", True) and cs["home"].get("score") not in (None, ""):
                res.append({"d": d, "h": h, "a": a, "ft": [int(float(cs["home"]["score"])), int(float(cs["away"]["score"]))], "ht": None, "season": season_of(d)})
            elif st.get("state") == "pre":
                fx.append({"d": d, "t": t, "h": h, "a": a})
        except Exception:
            continue
    return res, fx

def download_extra(season, today, log):
    """Ek ligler: son ~15 ayın sonuçları (biten aylar önbellekte), bu ve gelecek ayın fikstürü."""
    fixtures = []
    start = date.fromordinal(today.toordinal() - KEEP_DAYS)
    for lg, (slug, name) in EXTRA.items():
        cur = season.get(lg, {"matches": [], "done": []})
        done = set(cur.get("done", [])); new = []
        y, m = start.year, start.month
        months = []
        while (y, m) <= (today.year + (today.month == 12), today.month % 12 + 1):
            months.append(f"{y}{m:02d}"); m += 1
            if m == 13: y, m = y + 1, 1
        n_req = 0
        for ym in months:
            if ym in done: continue
            try:
                r, f = espn_month(slug, ym); n_req += 1
                new += r
                fixtures += [dict(x, lg=lg) for x in f if x["d"] >= today.isoformat()]
                yy, mm = int(ym[:4]), int(ym[4:])
                end = date(yy + (mm == 12), mm % 12 + 1, 1) - timedelta(days=1)
                if (today - end).days > 5: done.add(ym)
            except Exception as e:
                log[f"{lg}-{ym}"] = f"hata: {e.__class__.__name__}"
        # başka ligde aynı adlı takım varsa (ör. "Nacional") karışmasın: ada ülke eki. Atanan ad kalıcıdır (alias),
        # sonradan değişmez; böylece takım geçmişi ve kilitli tahmin kimlikleri bölünmez.
        alias = dict(cur.get("alias", {}))
        others = {n for k, d in season.items() if k != lg and not d.get("cup") for x in d["matches"] for n in (x["h"], x["a"])}
        def tag(n):
            if n not in alias: alias[n] = f"{n} ({lg.upper()})" if n in others else n
            return alias[n]
        new = [dict(x, h=tag(x["h"]), a=tag(x["a"]), season=season_for(lg, x["d"])) for x in new]
        fixtures = [dict(x, h=tag(x["h"]), a=tag(x["a"])) if x["lg"] == lg else x for x in fixtures]
        ms = [x for x in merge(cur.get("matches", []), new) if x["d"] >= start.isoformat()]
        for x in ms: x["season"] = season_for(lg, x["d"])
        log[lg] = f"{len(new)} yeni, {n_req} istek"
        if len(ms) < 10: continue
        last_season = max(x["season"] for x in ms)
        season[lg] = {"name": name, "espn": slug, "asOf": max(x["d"] for x in ms), "season": last_season, "matches": ms, "done": sorted(done), "src": "espn", "alias": alias}
    return fixtures

def fetch_logos(season):
    """Her ligin takım logolarını ESPN'den indir ve uygulamadaki takım adlarıyla eşle."""
    lp = os.path.join(DATA, "logos.json")
    logos = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else {}
    got = 0
    for lg, d in season.items():
        code = ESPN.get(lg) or d.get("espn")
        if not code: continue
        names = sorted({m["h"] for m in d["matches"]} | {m["a"] for m in d["matches"]})
        if all(n in logos for n in names): continue
        if logos.get("_tried_" + lg) == date.today().isoformat(): continue
        logos["_tried_" + lg] = date.today().isoformat()
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
    dom = {}; ncur = {}
    for lg, d in season.items():
        if d.get("cup") or lg in WOMEN: continue   # erkek kupaları kadın ligleriyle eşleşmesin (Ajax ↔ Ajax Kadın)
        cur = [m for m in d["matches"] if m["season"] == d.get("season")]
        if len(cur) < 20: continue
        f = fit(d["matches"], today, P)
        cnt = collections.Counter([m["h"] for m in cur] + [m["a"] for m in cur])
        for t, (a, de) in f["t"].items():
            if cnt[t] and cnt[t] > ncur.get(t, 0): dom[t] = (lg, a, de); ncur[t] = cnt[t]   # çakışmada bu sezon en çok oynadığı lig
    cm = [m for d in season.values() if d.get("cup") for m in d["matches"] if m.get("ft") and None not in m["ft"][:2]]
    k = {lg: STRENGTH_PRIOR.get(lg, UNKNOWN_PRIOR) for lg in {v[0] for v in dom.values()}}
    teams = sorted({m["h"] for m in cm} | {m["a"] for m in cm})
    ext = {t: [UNKNOWN_PRIOR, 0.0, 0.0] for t in teams if t not in dom}  # bilinmeyen takım: [güç, hücum, savunma] log
    mu, gam = 1.35, 1.2
    def rating(t):
        if t in dom:
            lg, a, de = dom[t]; return math.log(a) + k[lg], math.log(de) - k[lg]
        e = ext[t]; return e[0] + e[1], -e[0] + e[2]
    if cm:
        # Gradyanlar maç sayısına bölünür (ortalama kalıntı) ve değerler sınırlanır: kupa maçı sayısı arttıkça
        # toplam gradyan büyüyüp exp() taşmasına yol açıyordu.
        nk = collections.Counter(); ne = collections.Counter()
        for m in cm:
            for t in (m["h"], m["a"]):
                if t in dom: nk[dom[t][0]] += 1
                else: ne[t] += 1
        clip = lambda x, lo=-2.5, hi=2.5: min(max(x, lo), hi)
        lr = 0.3
        for _ in range(300):
            gk = {lg: 0.0 for lg in k}; ge = {t: [0.0, 0.0, 0.0] for t in ext}; sh = sa = eh_s = ea_s = 0.0
            for m in cm:
                (ah, dh), (aa, da) = rating(m["h"]), rating(m["a"])
                lh = mu * gam * math.exp(clip(ah + da, -4, 4)); la = mu * math.exp(clip(aa + dh, -4, 4))
                rh, ra = m["ft"][0] - lh, m["ft"][1] - la
                sh += m["ft"][0]; sa += m["ft"][1]; eh_s += lh; ea_s += la
                for t, r_for, r_ag in ((m["h"], rh, ra), (m["a"], ra, rh)):
                    if t in dom: gk[dom[t][0]] += r_for - r_ag
                    else:
                        g = ge[t]; g[0] += r_for - r_ag; g[1] += r_for; g[2] += r_ag
            for lg in k:
                pr = STRENGTH_PRIOR.get(lg, UNKNOWN_PRIOR)
                k[lg] = clip(k[lg] + lr * (gk[lg] / (nk[lg] + 10) - 0.05 * (k[lg] - pr)))
            for t, g in ge.items():
                e = ext[t]; c = ne[t] + 5
                e[0] = clip(e[0] + lr * (g[0] / c - 0.05 * (e[0] - UNKNOWN_PRIOR)))
                e[1] = clip(e[1] + lr * (g[1] / c - 0.1 * e[1]), -1, 1); e[2] = clip(e[2] + lr * (g[2] / c - 0.1 * e[2]), -1, 1)
            mu *= (sa / max(ea_s, 1e-6)) ** 0.2; gam *= ((sh / max(eh_s, 1e-6)) / (sa / max(ea_s, 1e-6))) ** 0.2
            mu = min(max(mu, 0.5), 3.0); gam = min(max(gam, 1.0), 1.6)
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

def pick_calib(season, rho):
    """Öneri kalibrasyonu: her maçta en yüksek olasılıklı seçenek (MS 1/X/2, 2,5 Alt/Üst; oran ≥1.15) geçmişte ne sıklıkla tuttu?
    Olasılık dilimlerine göre gerçek isabet; bir önceki sezonda öğrenilip son sezonda doğrulanır."""
    # Kendi arşivimiz (scripts/collector.py: tüm iddaa liglerinde kilitli öneri + sonuç) yeterince büyüdüyse onu kullan
    try:
        import arsiv   # güncel + kalıcı (eski/) arşiv katmanı
        ar = arsiv.kayitlar(DATA)
        if len(ar) >= 3000:
            edges = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 1.01]; mid = sorted(a[0] for a in ar)[len(ar) // 2]
            def tab2(rs):
                o = []
                for lo, hi in zip(edges[:-1], edges[1:]):
                    s_ = [r for r in rs if lo <= r["rp"] < hi]
                    o.append([lo, hi, len(s_), round(sum(r["ok"] for r in s_) / len(s_), 4) if s_ else None, round(float(np.mean([r["rp"] for r in s_])), 4) if s_ else None])
                return o
            tr, te = tab2([r for d_, r in ar if d_ < mid]), tab2([r for d_, r in ar if d_ >= mid])
            def br(rs, T):
                def cal(pp):
                    for lo, hi, n, h, e in T:
                        if lo <= pp < hi and n and h is not None: return (h * n + pp * 50) / (n + 50)
                    return pp
                return float(np.mean([(r["rp"] - r["ok"]) ** 2 for r in rs])), float(np.mean([(cal(r["rp"]) - r["ok"]) ** 2 for r in rs]))
            b0, b1 = br([r for d_, r in ar if d_ >= mid], tr)
            return {"bins": tab2([r for _, r in ar]), "min_odd": 1.15, "n": len(ar), "hit": round(sum(r["ok"] for _, r in ar) / len(ar), 4), "kaynak": "arşiv",
                    "dogrulama": {"sezon": mid, "ogrenme": tr, "test": te, "brier_ham": round(b0, 4), "brier_kalibre": round(b1, 4), "kabul": b1 <= b0}}
    except Exception as ex:
        print("arşiv kalibrasyonu atlandı:", ex, flush=True)
    ms = [m for lg, d in season.items() if not d.get("cup") and d.get("src") != "espn" for m in d["matches"] if m.get("odds") and m.get("ou")]
    if len(ms) < 2000: return None
    market_xg(ms)
    lh = np.array([m["xg"][0] for m in ms]); la = np.array([m["xg"][1] for m in ms])
    p, pO, _, _ = outcome_probs(lh, la, rho)
    rows = []
    for i, m in enumerate(ms):
        a, b = m["ft"]; r = 0 if a > b else 1 if a == b else 2; ov = a + b > 2
        c = [(p[i, 0], m["odds"][0], r == 0), (p[i, 1], m["odds"][1], r == 1), (p[i, 2], m["odds"][2], r == 2), (pO[i], m["ou"][0], ov), (1 - pO[i], m["ou"][1], not ov)]
        if c: bb = max(c, key=lambda x: x[0]); rows.append((m["season"], float(bb[0]), bool(bb[2])))
    edges = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 1.01]
    def tab(rs):
        out = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            s_ = [r for r in rs if lo <= r[1] < hi]
            out.append([lo, hi, len(s_), round(float(np.mean([r[2] for r in s_])), 4) if s_ else None, round(float(np.mean([r[1] for r in s_])), 4) if s_ else None])
        return out
    last = max(r[0] for r in rows)
    tr, te = tab([r for r in rows if r[0] < last]), tab([r for r in rows if r[0] == last])
    def brier(rs, T):
        def cal(pp):
            for lo, hi, n, h, e in T:
                if lo <= pp < hi and n and h is not None: return (h * n + pp * 50) / (n + 50)
            return pp
        return float(np.mean([(r[1] - r[2]) ** 2 for r in rs])), float(np.mean([(cal(r[1]) - r[2]) ** 2 for r in rs]))
    b0, b1 = brier([r for r in rows if r[0] == last], tr)
    return {"bins": tab(rows), "min_odd": 1.15, "n": len(rows), "hit": round(float(np.mean([r[2] for r in rows])), 4),
            "dogrulama": {"sezon": last, "ogrenme": tr, "test": te, "brier_ham": round(b0, 4), "brier_kalibre": round(b1, 4), "kabul": b1 <= b0}}

IDDAA_LIG = os.path.join(DATA, "iddaa_lig.json")
KADIN_RE = re.compile(r"(kad[ıi]n|women|\(k\))", re.I)
_EVRE = re.compile(r"^(a[cç][ıi]l[ıi][sş]|kapan[ıi][sş]|final|apertura|clausura|play.?off|normal sezon|1\. ?etap|2\. ?etap|ilk etap)$", re.I)

def _komp_ad(s):
    """iddaa yarışma adı → karşılaştırma anahtarı: küçük harf, ASCII; yalnız sezon evresi eki (", Açılış", ", Final") atılır."""
    s = (s or "").strip()
    if "," in s:
        bas, son = s.rsplit(",", 1)
        if _EVRE.match(son.strip()): s = bas
    s = unicodedata.normalize("NFKD", s.replace("ı", "i").replace("İ", "I")).encode("ascii", "ignore").decode().lower()
    return " ".join(re.split(r"[^a-z0-9]+", s)).strip()

def _lig_yaz(H, path):
    """Hafıza dosyası: her yarışma bir satır (git farkı okunur kalır)."""
    dm = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))
    bas = ",\n".join(f"{dm(k)}:{dm(v)}" for k, v in H.items() if k != "komp")
    kom = ",\n".join(f" {dm(k)}:{dm(v)}" for k, v in (H.get("komp") or {}).items())
    open(path, "w", encoding="utf-8").write("{" + bas + ',\n"komp":{\n' + kom + "\n}}\n")

def iddaa_lig_hafiza(evs, cl, known, today, path=None, yaz=True):
    """iddaa yarışma kimliği (ci) → bilinen lig kodu hafızası (data/iddaa_lig.json, veri güdümlü).
    · Bu turda maç eşleşmesiyle öğrenilen (cl) eşlemeler hafızaya yazılır/güncellenir (yeni kanıt eskisini ezer).
    · Eşleşmesi çıkmayan yarışma: önce ci, yoksa normalleştirilmiş ad + ülke ile hafızada aranır; aday lig ancak
      yarışmadaki takımların en az yarısı o ligin model takımlarıyla eşleşirse kabul edilir (yanlış ci / yeniden kullanılmış kimlik koruması).
    · Kadın yarışmaları ve kupalar bağlanmaz (hafızaya yalnız lig maçıyla eşleşmiş yarışmalar girer).
    Dönüş: (yeni cl, {ci: "mac"|"hafiza"|"ad"}). Eski i### kayıtları değişmez; eşlenemeyen yarışma yine i{ci} olarak kalır."""
    import iddaa as ID
    path = path or IDDAA_LIG
    try: H = json.load(open(path, encoding="utf-8"))
    except Exception: H = {}
    komp = H.setdefault("komp", {})
    gecerli = set(LEAGUES) | set(EXTRA)
    by_ci = collections.defaultdict(list)
    for e in evs: by_ci[e["ci"]].append(e)
    kadin = lambda es: any(KADIN_RE.search(x["comp"] or "") or "(K)" in x["h"] or "(K)" in x["a"] for x in es)
    bugun = today.isoformat(); out = dict(cl); kay = {ci: "mac" for ci in cl}
    for ci, lg in cl.items():   # öğren
        es = by_ci.get(ci) or []
        if not es or kadin(es): continue
        k = komp.get(str(ci)) or {}
        komp[str(ci)] = {"lg": lg, "ad": es[0]["comp"] or k.get("ad"), "cc": es[0].get("cc") or k.get("cc"),
                         "n": (k.get("n", 0) + 1) if k.get("lg") == lg else 1, "son": bugun}
    ad_idx = collections.defaultdict(set)
    for ci_, k in komp.items():
        if k.get("ad") and k.get("lg") in gecerli: ad_idx[(_komp_ad(k["ad"]), (k.get("cc") or "").upper()[:2])].add(k["lg"])
    for ci, es in by_ci.items():   # uygula
        if ci in out or kadin(es): continue
        k = komp.get(str(ci)); lg, yol = (k or {}).get("lg"), "hafiza"
        if not lg:
            c_ = ad_idx.get((_komp_ad(es[0]["comp"]), (es[0].get("cc") or "").upper()[:2])) or set()
            lg, yol = (next(iter(c_)) if len(c_) == 1 else None), "ad"
        if not lg or lg not in gecerli: continue
        kn = known.get(lg) or []
        if not kn: continue   # modelde takım listesi olmayan lige bağlanmaz
        tak = {t for x in es for t in (x["h"], x["a"])}
        tut = sum(1 for t in tak if ID.best_name(t, kn))
        if tut * 2 < len(tak): continue
        out[ci] = lg; kay[ci] = yol
        if yol == "ad": komp[str(ci)] = {"lg": lg, "ad": es[0]["comp"], "cc": es[0].get("cc"), "n": 0, "son": bugun, "yol": "ad"}
    if yaz:
        H["v"] = 1; H["guncelleme"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        H["aciklama"] = ("iddaa yarışma kimliği → lig kodu hafızası. scripts/update.py merge_iddaa her turda maç eşleşmesinden öğrenir; "
                         "eşleşme çıkmayan turda bu tablo kullanılır (takım adı doğrulamalı).")
        H["komp"] = dict(sorted(komp.items(), key=lambda kv: (kv[1].get("lg", ""), kv[0])))
        _lig_yaz(H, path)
    n_h = sum(1 for v in kay.values() if v != "mac")
    if n_h: print(f"iddaa lig hafızası: {n_h} yarışma bilinen lige bağlandı " + ", ".join(f"i{c}→{out[c]}" for c, v in kay.items() if v != "mac"), flush=True)
    return out, kay

def merge_iddaa(fx, season, today):
    """Resmi iddaa bülteni: Bilyoner'deki maçların tamamı. Bizdeki maçlara iddaa oranı eklenir,
    bizde olmayanlar ayrı lig başlığıyla bültene girer. Her maç için piyasa gol beklentisi (lh, la) data/iddaa.json'a yazılır."""
    import iddaa as ID
    from zoneinfo import ZoneInfo
    UK, TR = ZoneInfo("Europe/London"), ZoneInfo("Europe/Istanbul")
    evs = ID.fetch(1, eksik_ms=True)   # MS oranı kapalı dev favori maçları da bültende (oransız: güç modeliyle tahmin)
    known = {lg: sorted({m["h"] for m in d["matches"]} | {m["a"] for m in d["matches"]}) for lg, d in season.items() if not d.get("cup")}
    def ko(f):
        try:
            hh, mm = (f.get("t") or "12:00").split(":")[:2]
            return datetime.fromisoformat(f["d"]).replace(hour=int(hh), minute=int(mm), tzinfo=UK).timestamp()
        except Exception: return None
    fx_ko = [(f, ko(f)) for f in fx]
    used = set(); comp_lg = collections.defaultdict(collections.Counter); matched = {}
    for e in evs:
        best, bs = None, 0
        for j, (f, t) in enumerate(fx_ko):
            if j in used or t is None or abs(t - e["ts"]) > 3 * 3600: continue
            sh, sa = ID.sim(e["h"], f["h"]), ID.sim(e["a"], f["a"])
            if min(sh, sa) < 0.55 or sh + sa < 1.45: continue
            sc = sh + sa + (0.3 if abs(t - e["ts"]) <= 1800 else 0)
            if sc > bs: best, bs = j, sc
        if best is not None:
            used.add(best); matched[e["iid"]] = best; comp_lg[e["ci"]][fx_ko[best][0]["lg"]] += 1
    # lig eşlemesi: en az 2 maçı bizdeki ligle eşleşen yarışma; kadın yarışmaları erkek ligine bağlanmaz
    women = lambda e: "(K)" in e["h"] or "(K)" in e["a"] or re.search(r"kad[ıi]n", e["comp"], re.I)
    cl = {}
    for e in evs:
        c = comp_lg.get(e["ci"])
        if c and not women(e):
            lg_, n_ = c.most_common(1)[0]
            if n_ >= 2 or sum(c.values()) == n_ == sum(1 for x in evs if x["ci"] == e["ci"]): cl[e["ci"]] = lg_
    # v128 lig hafızası: bu turda eşleşecek fikstürü olmayan (football-data o ligin yeni haftasını henüz yayınlamamış) yarışma,
    # önceki turlarda öğrenilmiş eşlemeyle bilinen lig koduna bağlanır (i584 → tr1). Takım adları ligin takımlarıyla doğrulanır.
    try: cl, lig_kay = iddaa_lig_hafiza(evs, cl, known, today)
    except Exception as ex: lig_kay = {}; print("iddaa lig hafızası atlandı:", ex.__class__.__name__, ex, flush=True)
    # 2. tur: aynı lig + yakın saat + bir takım adı çok benzer (Amed Sportif Faaliyetler ~ Amedspor)
    for e in evs:
        if e["iid"] in matched or e["ci"] not in cl: continue
        best, bs = None, 0
        for j, (f, t) in enumerate(fx_ko):
            if j in used or t is None or f["lg"] != cl[e["ci"]] or abs(t - e["ts"]) > 3 * 3600: continue
            sh, sa = ID.sim(e["h"], f["h"]), ID.sim(e["a"], f["a"])
            if max(sh, sa) < 0.85 or min(sh, sa) < 0.25: continue
            if sh + sa > bs: best, bs = j, sh + sa
        if best is not None: used.add(best); matched[e["iid"]] = best
    out_fx = list(fx); extra = []; lam = {}
    def add_io(f, e):
        mk = e["mk"]; f["iid"] = e["iid"]; f["cn"] = e["comp"]
        if not mk.get("ms"):                       # MS kapalı: oransız maç gibi (oran alanları yazılmaz)
            if e.get("mbc"): f["mbs"] = e["mbc"]
            return
        f["io"] = mk["ms"]
        if e.get("mbc"): f["mbs"] = e["mbc"]
        if mk.get("ou"): f["iou"] = mk["ou"]
        if mk.get("kg"): f["ikg"] = mk["kg"]
        if not f.get("odds"): f["odds"] = mk["ms"]
        if not f.get("ou") and mk.get("ou"): f["ou"] = mk["ou"]
        # 🧮 pazar motoru: iddaa oranları pazar kodlarıyla (eski io/iou/ikg aynen kalır; po yalnız ek bilgi)
        try:
            po = {"1": mk["ms"][0], "X": mk["ms"][1], "2": mk["ms"][2]}
            if mk.get("ou"): po.update({"U25": mk["ou"][0], "A25": mk["ou"][1]})
            if mk.get("kg"): po.update({"KGV": mk["kg"][0], "KGY": mk["kg"][1]})
            for k_, v_ in (mk.get("px") or {}).items():
                if k_ not in po and isinstance(v_, (int, float)) and v_ > 1.01: po[k_] = round(float(v_), 2)
            f["po"] = po
        except Exception: pass
    for e in evs:
        if e["iid"] in matched:
            add_io(out_fx[matched[e["iid"]]], e); continue
        dt = datetime.fromtimestamp(e["ts"], timezone.utc).astimezone(UK)
        lg = cl.get(e["ci"])
        h, a = e["h"], e["a"]
        if lg and lg in known:
            h = ID.best_name(h, known[lg]) or h; a = ID.best_name(a, known[lg]) or a
        f = {"d": dt.date().isoformat(), "t": dt.strftime("%H:%M"), "lg": lg or f"i{e['ci']}", "h": h, "a": a, "src": "iddaa"}
        if not lg: f["ln"] = e["comp"]; f["cc"] = e["cc"]
        elif lig_kay.get(e["ci"]) in ("hafiza", "ad"): f["lgk"] = lig_kay[e["ci"]]   # lig kodu hafızadan (eski kod: i{ci})
        add_io(f, e); extra.append(f)
    out_fx += extra
    # piyasa gol beklentisi (canlı tahminin başlangıç noktası)
    tmp = [dict({"odds": e["mk"]["ms"], "iid": e["iid"]}, **({"ou": e["mk"]["ou"]} if e["mk"].get("ou") else {})) for e in evs if e["mk"].get("ms")]
    market_xg(tmp)
    # başlamış maçlar bültenden düşer; canlı tahmin ve Sonuçlar için maç öncesi beklenti 8 gün saklanır
    try:
        oldl = json.load(open(os.path.join(DATA, "iddaa.json"), encoding="utf-8")).get("lam", {})
        cut = datetime.now(timezone.utc).timestamp() - 8 * 86400   # Sonuçlar sayfası son 8 günü gösterir
        lam.update({k: v for k, v in oldl.items() if len(v) >= 3 and v[2] > cut})
    except Exception: pass
    tsd = {e["iid"]: e["ts"] for e in evs}
    for x in tmp:
        if x.get("xg"): lam[str(x["iid"])] = [x["xg"][0], x["xg"][1], tsd[x["iid"]]]
    json.dump({"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "lam": lam,
               "comp_lg": {str(k): v for k, v in cl.items()}, "comp_lg_kaynak": {str(k): v for k, v in lig_kay.items()}},
              open(os.path.join(DATA, "iddaa.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"iddaa bülteni: {len(evs)} maç · {len(matched)} bizdeki maçla eşleşti · {len(extra)} yeni maç eklendi", flush=True)
    try:   # teşhis: bültendeki pazar adları ve hangi koda ayrıştırıldığı (oran değeri yazılmaz)
        nm = ID.market_names(getattr(ID, "LAST_RAW", []) or [])
        npx = collections.Counter(k for e in evs for k in (e["mk"].get("px") or {}))
        json.dump({"guncelleme": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "pazar_tanimi": len(ID.market_config()),
                   "pazarlar": nm, "ayristirilan_kod": dict(npx.most_common())},
                  open(os.path.join(DATA, "iddaa_pazarlar.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(f"iddaa ek pazar: {sum(1 for e in evs if e['mk'].get('px'))} maçta, {len(npx)} kod", flush=True)
    except Exception as ex: print("iddaa pazar teşhisi atlandı:", ex.__class__.__name__, flush=True)
    return out_fx

def predict_fixtures(fx, all_ms, P, today, pzmap=None, PL=None, golge=None):
    """Her yaklaşan maç için model ve piyasa tahminini önceden kaydet (gerçek ileriye dönük test için).
    ⚖️ PL(lg) → lig ayarı (oransız liglerde kapıyı geçen Poisson ayarı); golge: guc.tahmin gölge çıktısı.
    Oransız maçta yeni yol yayındaysa eski üretim yolu g0/g0o olarak kilitlenir (14 günlük gölge A/B izlemesi, lab/fb_guc_kapi.py)."""
    PL = PL or (lambda lg: P)
    fits = {}; fits0 = {}
    for lg, ms in all_ms.items():
        if len(ms) >= 40:
            try:
                fits[lg] = fit(ms, today, PL(lg))
                if PL(lg) is not P: fits0[lg] = fit(ms, today, P)
            except Exception: pass
    market_xg(fx)
    rows = []; rows0 = {}
    for f in fx:
        F = fits.get(f["lg"])
        if not F: continue
        (ah, dh), (aa, da) = F["t"].get(f["h"], NEW_TEAM), F["t"].get(f["a"], NEW_TEAM)
        rows.append((f, F["mu"] * F["gamma"] * ah * da, F["mu"] * aa * dh))
        F0 = fits0.get(f["lg"])
        if F0:
            (ah, dh), (aa, da) = F0["t"].get(f["h"], NEW_TEAM), F0["t"].get(f["a"], NEW_TEAM)
            rows0[len(rows) - 1] = (F0["mu"] * F0["gamma"] * ah * da, F0["mu"] * aa * dh)
    if not rows: return []
    lh = np.array([r[1] for r in rows]); la = np.array([r[2] for r in rows])
    gs_ = P.get("gscale", 1.0)
    p, pO, pB, g = outcome_probs(lh * gs_, la * gs_, P["rho"]); kk = g.shape[1]
    p = apply_cal(p, P)
    g0 = {}
    if rows0:
        ix = sorted(rows0); l0 = np.array([rows0[i] for i in ix])
        q0, qO0, _, _ = outcome_probs(l0[:, 0] * gs_, l0[:, 1] * gs_, P["rho"]); q0 = apply_cal(q0, P)
        g0 = {i: (q0[j], float(qO0[j])) for j, i in enumerate(ix)}
    CS = pick_scores(g, p, pO) if P.get("scoreMode", "tutarli") == "tutarli" else None
    out = []
    for i, (f, a, b) in enumerate(rows):
        k = int(g[i].reshape(-1).argmax())
        if CS: k = CS[i][0] * kk + CS[i][1]
        e = {"id": f"{f['lg']}|{f['d']}|{f['h']}|{f['a']}", "d": f["d"], "lg": f["lg"], "h": f["h"], "a": f["a"],
             "p": [round(float(x), 4) for x in p[i]], "o": round(float(pO[i]), 4), "ft": f"{k // kk}-{k % kk}"}
        if f.get("odds"):
            inv = [1 / x for x in f["odds"]]; s_ = sum(inv); e["mp"] = [round(x / s_, 4) for x in inv]
        else:   # ⚖️ oransız maç: topluluk / yeni Poisson yayındaysa eski yol gölgede kilitlenir
            try:
                yeni_pois = i in g0
                if yeni_pois: e["pv"] = 1; e["pk"] = "pois"
                if f.get("kpy") == "guc" and isinstance(f.get("kp"), list):
                    e["gp"] = e["p"]; e["p"] = [round(float(x), 4) for x in f["kp"]]; e["pk"] = "guc"
                    if isinstance(f.get("ko"), (int, float)) and f.get("kpo") == "guc": e["o"] = round(float(f["ko"]), 4); e["ok_"] = "guc"
                    if isinstance(f.get("kpg"), list): e["gt"] = f["kpg"]; e["gtk"] = f.get("kpgy")       # YH-11 GAS'sız topluluk gölgesi
                    if isinstance(f.get("kog"), (int, float)) and e.get("ok_") == "guc": e["gto"] = f["kog"]
                if yeni_pois or e.get("pk") == "guc":
                    q, qo = g0[i] if yeni_pois else (p[i], float(pO[i]))
                    e["g0"] = [round(float(x), 4) for x in q]; e["g0o"] = round(float(qo), 4)
                z = (golge or {}).get((f["lg"], f["d"], f["h"], f["a"]))
                if z and e.get("pk") != "guc": e["gk"] = z["p"]; e["gko"] = z["o"]
            except Exception: pass
        try:   # 🧮 sunulan tüm pazar olasılıkları (binde, pazar.PZ_KAYIT sırası) + iddaa oranları; sonuçla puanlanır
            z = (pzmap or {}).get((f["lg"], f["d"], f["h"], f["a"]))
            if z:
                import pazar as PZM
                e["pz"] = PZM.pack(z); e["pzv"] = PZM.PAZAR_V
                po_ = {k: v for k, v in (f.get("po") or {}).items() if k not in PZM.ESKI and z.get(k, 0) >= .70}   # Altın kapısı için yeter
                if po_: e["po"] = po_
        except Exception: pass
        out.append(e)
    return out

# ------------------------------------------------------------------ 🔒 kapanış kilidi ve karne (2026-10-28)
# Kilitli ilk tahmin (p) maçtan ortanca 4,4 gün önce yazılıyordu; karne bayat tahmini ölçüyordu. p DEĞİŞMEZ; maça ≤ KAPANIS_DK
# kala ilk çalışmada bir kez ikinci kilit yazılır (pc/pco = aynı yol, kapanıştaki; mpc/mpco = piyasa kapanışı; psc/psco = uygulamanın
# oranlı maçta gösterdiği; pcts/pcdk = yazıldığı an ve maça kalan dakika). Saatlik iş :17'de çalışır; 75 dk pencere gecikmeye pay bırakır.
KAPANIS_DK = 75

def _oran_pay(o):
    try:
        inv = [1 / x for x in o]; s = sum(inv); return [round(x / s, 4) for x in inv]
    except Exception: return None

def sunulan_olasilik(odds_list, ou_list, P, lg_list=None):
    """Uygulamanın oranlı maçta gösterdiği MS 1X2 ve 2,5 Üst (index.html predict → dist, marketW=1; collector.served_pick ile aynı)."""
    if not odds_list: return []
    rho, h1 = P.get("rho", -0.06), P.get("h1", .4442)
    T, g, dk = P.get("calT", 1.0), P.get("gscale", 1.0), P.get("dk", 1.0)
    lam = ui_market_lam(odds_list, ou_list, rho)
    p, O = served_probs(lam[:, 0], lam[:, 1], g, rho, h1); q = _cal3(p, T, dk)
    return [([round(float(x), 4) for x in q[i]], round(float(O[i]), 4)) for i in range(len(q))]

def kapanis_kilidi(plog, tahmin, fx_id, kickoff, now_utc, P):
    """Kilitli kayda (p'ye dokunmadan) kapanış alanlarını bir kez yaz. Dönüş: yazılan kayıt sayısı."""
    hedef = []
    for e in plog:
        if "pc" in e or e.get("r") is not None: continue
        t, f = tahmin.get(e["id"]), fx_id.get(e["id"])
        if not t or not f: continue
        dk = (kickoff(f) - now_utc).total_seconds() / 60
        if 0 < dk <= KAPANIS_DK: hedef.append((e, t, f, dk))
    if not hedef: return 0
    ts = now_utc.strftime("%Y-%m-%dT%H:%MZ")
    od = [(e, f) for e, t, f, dk in hedef if f.get("odds") and len(f["odds"]) == 3]
    srv = {}
    try:
        for (e, f), (q, o) in zip(od, sunulan_olasilik([f["odds"] for _, f in od], [f.get("ou") if f.get("ou") and len(f["ou"]) == 2 else None for _, f in od], P)):
            srv[e["id"]] = (q, o if f.get("ou") else None)
    except Exception as ex: print("kapanış sunulan olasılık atlandı:", ex.__class__.__name__, ex, flush=True)
    for e, t, f, dk in hedef:
        e["pc"] = list(t["p"]); e["pco"] = t.get("o"); e["pcts"] = ts; e["pcdk"] = int(round(dk))
        if f.get("odds"):
            e["mpc"] = _oran_pay(f["odds"])
            if f.get("ou") and len(f["ou"]) == 2: e["mpco"] = _oran_pay(f["ou"])[0]
        if e["id"] in srv:
            e["psc"] = srv[e["id"]][0]
            if srv[e["id"]][1] is not None: e["psco"] = srv[e["id"]][1]
    return len(hedef)

def acilis_sunulan(yeni, fx_id, P):
    """Yeni kilitlenen oranlı maçlara açılıştaki uygulama olasılığı (ps/pso) ve piyasa 2,5 Üst payı (mo). p değişmez."""
    od = [(e, fx_id[e["id"]]) for e in yeni if e["id"] in fx_id and fx_id[e["id"]].get("odds") and len(fx_id[e["id"]]["odds"]) == 3]
    for e, f in od:
        if f.get("ou") and len(f["ou"]) == 2: e["mo"] = _oran_pay(f["ou"])[0]
    if not od: return 0
    for (e, f), (q, o) in zip(od, sunulan_olasilik([f["odds"] for _, f in od], [f.get("ou") if f.get("ou") and len(f["ou"]) == 2 else None for _, f in od], P)):
        e["ps"] = q
        if f.get("ou") and len(f["ou"]) == 2: e["pso"] = o
    return len(od)

from kilit import kilit_karne   # açılış / kapanış kilidi karnesi (scripts/kilit.py; collector ve oxx_kupon da kullanır)

# ------------------------------------------------------------------ 📉 drift bayrağı (lab/drift.py → data/drift.json)
def drift_ayar():
    """{lig: {"1x2": a, "ou": a}} (a < 1 olan ligler; a = model ağırlığı çarpanı). Koruyucu geri alması aktifken de uygulanır (yalnız temkin yönü)."""
    try:
        D = json.load(open(os.path.join(DATA, "drift.json"), encoding="utf-8"))
        out = {}
        for lg, v in (D.get("ligler") or {}).items():
            a1, ao = float(v.get("agirlik_1x2", 1.0)), float(v.get("agirlik_ou", 1.0))
            if a1 < 1 or ao < 1: out[lg] = {"1x2": round(max(0.0, min(1.0, a1)), 3), "ou": round(max(0.0, min(1.0, ao)), 3)}
        return out
    except Exception: return {}

def drift_oranli(fx, P, DR):
    """Drift alarmındaki ligde oranlı maçın model katkılı olasılığı (konsey kp/ko) uygulamanın saf piyasa yoluna çekilir:
    kp ← a·kp + (1−a)·piyasa (a = 0 → piyasa ağırlığı 1). Dönüş: değişen maç sayısı."""
    L = [f for f in fx if f["lg"] in DR and f.get("odds") and len(f["odds"]) == 3 and f.get("kpy") != "guc"
         and (isinstance(f.get("kp"), list) or isinstance(f.get("ko"), (int, float)))]
    if not L: return 0
    S = sunulan_olasilik([f["odds"] for f in L], [f.get("ou") if f.get("ou") and len(f["ou"]) == 2 else None for f in L], P)
    for f, (q, o) in zip(L, S):
        a1, ao = DR[f["lg"]]["1x2"], DR[f["lg"]]["ou"]
        if isinstance(f.get("kp"), list) and len(f["kp"]) == 3:
            z = [a1 * f["kp"][k] + (1 - a1) * q[k] for k in range(3)]; t = sum(z); f["kp"] = [round(x / t, 4) for x in z]
        if isinstance(f.get("ko"), (int, float)) and f.get("ou"): f["ko"] = round(ao * f["ko"] + (1 - ao) * o, 4)
        f["drf"] = [a1, ao]
    return len(L)

def drift_uygula(fx, all_ms, P, PL, today, DR):
    """Drift alarmındaki ligde oransız maçların topluluk tahmini (kp/ko) Poisson yoluna doğru çekilir: kp ← a·kp + (1−a)·Poisson.
    a = 0 → tamamen Poisson (uygulamanın kendi yolu); a kademeli 1'e döndükçe topluluk geri gelir. Dönüş: değişen maç sayısı."""
    hedef = [f for f in fx if f["lg"] in DR and f.get("kpy") == "guc" and (isinstance(f.get("kp"), list) or isinstance(f.get("ko"), (int, float)))]
    if not hedef: return 0
    n = 0; gs_ = P.get("gscale", 1.0)
    for lg in sorted({f["lg"] for f in hedef}):
        if len(all_ms.get(lg, [])) < 40: continue
        F = fit(all_ms[lg], today, PL(lg)); L = [f for f in hedef if f["lg"] == lg]
        lh = np.array([F["mu"] * F["gamma"] * F["t"].get(f["h"], NEW_TEAM)[0] * F["t"].get(f["a"], NEW_TEAM)[1] for f in L])
        la = np.array([F["mu"] * F["t"].get(f["a"], NEW_TEAM)[0] * F["t"].get(f["h"], NEW_TEAM)[1] for f in L])
        p, pO, _, _ = outcome_probs(lh * gs_, la * gs_, P["rho"]); p = apply_cal(p, P)
        a1, ao = DR[lg]["1x2"], DR[lg]["ou"]
        for i, f in enumerate(L):
            if isinstance(f.get("kp"), list) and len(f["kp"]) == 3:
                q = [a1 * f["kp"][k] + (1 - a1) * float(p[i, k]) for k in range(3)]; s = sum(q); f["kp"] = [round(x / s, 4) for x in q]
            if isinstance(f.get("ko"), (int, float)): f["ko"] = round(ao * f["ko"] + (1 - ao) * float(pO[i]), 4)
            f["drf"] = [a1, ao]; n += 1
    return n

def grade_predlog(log, all_ms, today):
    idx = {}
    for lg, ms in all_ms.items():
        for m in ms: idx.setdefault((lg, m["h"], m["a"]), []).append(m)
    for e in log:
        if e.get("r") is not None or e["d"] >= today.isoformat(): continue
        cands = [m for m in idx.get((e["lg"], e["h"], e["a"]), []) if abs((date.fromisoformat(m["d"]) - date.fromisoformat(e["d"])).days) <= 3]
        if cands:
            m = cands[0]; e["r"] = m["ft"]
            if m.get("ht") and len(m["ht"]) == 2 and m["ht"][0] is not None: e["rh"] = m["ht"]
        elif (today - date.fromisoformat(e["d"])).days > 10:
            e["r"] = False   # ertelendi / bulunamadı
    keep = [e for e in log if (today - date.fromisoformat(e["d"])).days <= 400]   # ml70: 120 → 400 gün (veritabanı büyür)
    for e in keep:   # 🧮 pazar olasılıkları 180 gün tutulur (boyut sınırı); puanlanmış özet pazar_karne.json'da
        if "pz" in e and (today - date.fromisoformat(e["d"])).days > 180: e.pop("pz", None); e.pop("po", None)
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
    extra_fx = []
    if not offline:
        try: extra_fx = download_extra(season, today, log)
        except Exception as e: log["extra"] = f"hata: {e}"
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
        cdone = set(season.get(ck, {}).get("done", []))
        if not offline:
            # Kupalar ESPN aylık sorgusundan (TheSportsDB ücretsiz anahtarı güncel sezonu vermiyordu)
            try:
                sd = date.fromisoformat(since); yy, mm = sd.year, sd.month
                while (yy, mm) <= (today.year, today.month):
                    ym = f"{yy}{mm:02d}"
                    if ym not in cdone:
                        try:
                            res, _ = espn_month(ESPN[ck], ym)
                            for e in res:
                                h = CUP_MAP.get(e["h"]) or resolve(e["h"], all_dom); a = CUP_MAP.get(e["a"]) or resolve(e["a"], all_dom)
                                new.append({"d": e["d"], "h": h, "a": a, "ft": e["ft"], "ht": None, "season": season_of(e["d"]), "id": f"{e['d']}|{h}|{a}"})
                            end = date(yy + (mm == 12), mm % 12 + 1, 1) - timedelta(days=1)
                            if (today - end).days > 5: cdone.add(ym)
                        except Exception as ex:
                            log[f"{ck}-{ym}"] = f"hata: {ex.__class__.__name__}"
                    mm += 1
                    if mm == 13: yy, mm = yy + 1, 1
                log[ck] = len(new)
            except Exception as ex:
                log[ck] = f"hata: {ex.__class__.__name__}"
        for m in old:   # eski kayıtlardaki adlar yeni eşleme kurallarıyla güncellenir
            m["h"] = CUP_MAP.get(m["h"]) or resolve(m["h"], all_dom); m["a"] = CUP_MAP.get(m["a"]) or resolve(m["a"], all_dom)
        byid = {f"{m['d']}|{m['h']}|{m['a']}": m for m in old if m["d"] >= since}
        for m in new: byid[m["id"]] = m
        ms = sorted(byid.values(), key=lambda m: (m["d"], m["h"]))
        for m in ms: m["hl"] = dom_names.get(m["h"]); m["al"] = dom_names.get(m["a"])
        if ms:
            season[ck] = {"name": cname, "cup": True, "asOf": ms[-1]["d"], "season": max(m["season"] for m in ms), "matches": ms, "done": sorted(cdone)}
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
    core_ms = {lg: ms for lg, ms in all_ms.items() if season[lg].get("src") != "espn"}   # ayar/kalibrasyon: oranlı ligler
    # Ayarlar az veriyle seçildiyse (ilk kurulum) veya haftanın ilk günüyse tam öğrenme
    # Sürekli öğrenme: her çalıştırmada ayarlar yeni veriyle baştan aranır (yaklaşık 1-2 dakika, ücretsiz)
    # Akıllı nöbet: motor saatte bir uyanır; yeni maç sonucu yoksa yeniden eğitmez (aynı veri = aynı model),
    # yalnızca oranları, fikstürü ve tahmin karnesini tazeler. Yeni sonuç gelince tam öğrenme yapar.
    import hashlib
    fp = hashlib.sha1(json.dumps(sorted((lg, [(m["d"], m["h"], m["a"], m["ft"], m.get("ht"), m.get("odds"), m.get("ou")) for m in ms])
                                         for lg, ms in all_ms.items())).encode()).hexdigest()[:16]
    quick = (model.get("fp") == fp and model.get("engine") == ENGINE_V and bool(model.get("backtest")) and "--force" not in sys.argv)
    full = "--no-tune" not in sys.argv and not quick
    RB = _rollback()
    if RB and RB.get("params"):
        # geri alma süresince ayar araması yapılmaz; değişiklikten önceki ayarlarla çalışılır
        P0.update({k: v for k, v in RB["params"].items() if v is not None and k in P0}); full = False
        print("Koruyucu geri alma aktif:", RB.get("neden"), "→", RB.get("bitis"), flush=True)
    if quick:
        print("Yeni maç sonucu yok: eğitim atlandı, yalnızca oranlar ve fikstür tazeleniyor", flush=True)
        P, bt = dict(model["params"]), None
    elif full:
        print("Yeni sonuç var: ayar aranıyor (tam öğrenme)…", flush=True)
        P, bt = tune(core_ms, P0)
    else:
        print("Günlük test (ayarlar korunuyor)…", flush=True)
        P, bt = dict(P0), backtest(core_ms, P0)
    if not quick or not os.path.exists(os.path.join(DATA, "ck.json")):
        try: print("Korner/kart modeli:", build_ck(season, today), "lig", flush=True)
        except Exception as e: print("korner/kart atlandı:", e, flush=True)
    if not quick:
        P["h1"] = h1_share(all_ms)
        mw, mstats = tune_market(bt) if bt else (0.6, None)
        P["marketW"] = mw
        # Haftalık otomatik laboratuvar (lab/auto_lab.py) iki sezonda kanıtlanmış bir karışım bulduysa onu uygula
        try:
            AL = json.load(open(os.path.join(DATA, "auto_lab.json"), encoding="utf-8"))
            kb = (AL.get("karar") or {}).get("kabul") or ""
            mm = re.match(r"piyasa \+ bizim %(\d+)", kb)
            if mm: P["marketW"] = round(1 - int(mm.group(1)) / 100, 2); P["auto_lab"] = kb
        except Exception: pass
        if RB and RB.get("params") and RB["params"].get("marketW") is not None: P["marketW"] = RB["params"]["marketW"]
    if not quick and bt:
        cal = calibrate(bt, P["rho"]); P["calT"], P["gscale"], P["dk"] = cal["T"], cal["g"], cal["dk"]; P["cal_yol"] = "model"
        CAL_INFO.clear(); CAL_INFO.update(cal)
        # 🎯 ml70: kalibrasyonu uygulamanın sunduğu yolda öğren (kabul edilirse eski model-yolu kalibrasyonunun yerine geçer).
        # Koruyucu geri alma aktifse ve önceki yapılandırmada bu özellik kapalıysa dondurulur (canli_platt ile aynı kalıp).
        try:
            if RB and RB.get("cal_yol") != "sunulan":
                CAL_INFO["sunulan"] = {"kabul": False, "neden": "Koruyucu geri alma süresince dondurulmuş"}
            else:
                deep = load_deep(season)
                srv = calibrate_served(bt, P, legacy=cal, deep=deep)
                CAL_INFO["sunulan"] = srv
                if srv.get("kabul"): P["calT"], P["gscale"], P["dk"], P["cal_yol"] = srv["T"], srv["g"], srv["dk"], "sunulan"
        except Exception as e:
            print("sunulan yol kalibrasyonu atlandı:", e.__class__.__name__, e, flush=True)
        # 🔒 ml90: uygulamanın gerçekten sunduğu dağılımda (kilitli iddaa oranı) kapı. Kabul edilirse sunulan yol ayarının yerine geçer.
        try:
            if RB:
                CAL_INFO["kilitli"] = {"kabul": False, "neden": "Koruyucu geri alma süresince dondurulmuş"}
            else:
                kl = calibrate_locked(P)
                CAL_INFO["kilitli"] = kl
                if kl.get("kabul"): P["calT"], P["gscale"], P["dk"], P["cal_yol"] = kl["T"], kl["g"], kl["dk"], "kilitli"
        except Exception as e:
            print("kilitli arşiv kalibrasyonu atlandı:", e.__class__.__name__, e, flush=True)
        CAL_INFO["kullanilan"] = {"yol": P["cal_yol"], "T": P["calT"], "g": P["gscale"], "dk": P["dk"]}
    if not quick:
        if RB and RB.get("params"):
            for k in ("marketW", "calT", "gscale", "dk"):
                if RB["params"].get(k) is not None: P[k] = RB["params"][k]
            P.pop("auto_lab", None)
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
    try: fx = [] if offline else download_fixtures(season, today)
    except Exception as e: print("fikstür indirilemedi:", e, flush=True); fx = []
    if not fx and os.path.exists(fxp):
        fx = [f for f in json.load(open(fxp, encoding="utf-8")) if f["d"] >= today.isoformat() and f["lg"] not in EXTRA]
    if extra_fx:
        fx += [f for f in extra_fx if f["d"] <= (today + timedelta(days=10)).isoformat()]
    # 6) tekilleştir
    seen_fx = set(); fx_u = []
    for f in fx:
        k = (f["lg"], f["d"], f["h"], f["a"])
        if k not in seen_fx: seen_fx.add(k); fx_u.append(f)
    fx = fx_u
    if not offline:
        try: fx = merge_iddaa([f for f in fx if f.get("src") != "iddaa"], season, today)
        except Exception as e: print("iddaa bülteni alınamadı:", e.__class__.__name__, str(e)[:120], flush=True)
    # Robot arenası konseyi bir pazarda kanıtlandıysa yaklaşan maçlara konsey olasılığı eklenir (onay beklemeden; koruyucu izler)
    try:
        import konsey
        nk = konsey.apply(fx, season, P, today)
        if nk: print(f"Konsey tahmini eklenen maç: {nk}", flush=True)
    except Exception as e: print("konsey atlandı:", e.__class__.__name__, e, flush=True)
    # ⚖️ Oransız maçlar: kapıyı geçen topluluk (Poisson + Elo + pi) → kp/ko (lab/fb_guc_kapi.py; bayrak data/fb_guc.json, geri alınabilir)
    PL, GOLGE_T = (lambda lg: P), {}
    try:
        import guc
        GA_ = guc.ayar()
        PL = lambda lg, _A=GA_: guc.lig_parametre(P, lg, season, _A)
        ng = guc.uygula(fx, season, P, today, sys.modules[__name__])
        if ng: print(f"Topluluk tahmini eklenen oransız maç: {ng}", flush=True)
        if GA_ and not GA_.get("aktif"):
            GOLGE_T = guc.tahmin([f for f in fx if f.get("src") != "iddaa"], season, P, today, sys.modules[__name__], GA_, golge=True)
    except Exception as e: print("topluluk atlandı:", e.__class__.__name__, e, flush=True)
    # 📉 Drift bayrağı (lab/drift.py → data/drift.json): alarmdaki ligde model ağırlığı düşer (oranlı: yalnız piyasa; oransız: topluluk → Poisson)
    P.pop("drift", None)
    DR = drift_ayar()
    if DR:
        try:
            P["drift"] = DR; nd_ = drift_uygula(fx, all_ms, P, PL, today, DR)
            nk_ = drift_oranli(fx, P, DR)
            print(f"Drift: {len(DR)} ligde model ağırlığı düşük ({json.dumps(DR, ensure_ascii=False)[:300]}); oransız {nd_}, oranlı {nk_} maç", flush=True)
        except Exception as e: print("drift bayrağı atlandı:", e.__class__.__name__, e, flush=True)
    # 🧮 Pazar motoru: tüm pazarlar tek skor ızgarasından (scripts/pazar.py). Karne tam öğrenmede (veya yoksa) yeniden kurulur.
    pzmap, PK = {}, None
    kp_ = os.path.join(DATA, "pazar_karne.json")
    try:
        import pazar as PZM
        try: PK = json.load(open(kp_, encoding="utf-8"))
        except Exception: PK = None
        if not quick or not PK or PK.get("v") != PZM.PAZAR_V or PK.get("engine") != ENGINE_V or "--pazar-karne" in sys.argv:
            PK = PZM.karne(season, P, sys.modules[__name__]) or PK
            if PK: PK["engine"] = ENGINE_V; PK["guncelleme"] = now
        need = {f["lg"] for f in fx if not f.get("odds") and f["lg"] in all_ms and len(all_ms[f["lg"]]) >= 40}
        fits_ = {}
        for lg_ in need:
            try: fits_[lg_] = fit(all_ms[lg_], today, PL(lg_))
            except Exception: pass
        pzmap = PZM.enrich(fx, season, P, PK, fits=fits_, today=today, U=sys.modules[__name__])
        print(f"Pazar olasılığı eklenen maç: {len(pzmap)} / {len(fx)}", flush=True)
    except Exception as e:
        print("pazar motoru atlandı:", e.__class__.__name__, e, flush=True)
        for f in fx: f.pop("pz", None); f.pop("pzy", None)
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
    # iddaa kaynaklı maç: lig hafızasıyla bilinen lige bağlandı ve iki takım da o ligin model takımıysa (ad çözülmüş) kilitlenir
    lg_tk = {lg: {t for m in ms for t in (m["h"], m["a"])} for lg, ms in all_ms.items()}
    ok_src = lambda f: f.get("src") != "iddaa" or (f.get("lgk") and f["h"] in lg_tk.get(f["lg"], ()) and f["a"] in lg_tk.get(f["lg"], ()))
    fx_lock = [f for f in fx if ok_src(f) and kickoff(f) > now_utc and (f["lg"], f["h"], f["a"], f["d"]) not in played]
    model_yolu = {}; tahmin_ = {}; yeni_ = []
    for e in predict_fixtures(fx_lock, all_ms, P, today, pzmap=pzmap, PL=PL, golge=GOLGE_T):
        model_yolu[e["id"]] = (e["p"], e.get("o"))       # model yolu (oranlı maçta piyasadan bağımsız Poisson)
        tahmin_[e["id"]] = e
        if e["id"] not in have:                           # maçtan önceki ilk tahmin kilitlenir, sonradan değiştirilmez
            e["v"] = ENGINE_V; e["ts"] = now_utc.strftime("%Y-%m-%dT%H:%MZ"); plog.append(e); have.add(e["id"]); yeni_.append(e)
    try:   # 🔒 açılışta uygulamanın gösterdiği (ps) + kapanış kilidi (maça ≤75 dk kala bir kez: pc/mpc/psc; p değişmez)
        fx_id_ = {f"{f['lg']}|{f['d']}|{f['h']}|{f['a']}": f for f in fx_lock}
        tahmin_ = {k: dict(v) for k, v in tahmin_.items()}   # yeni kayıtlara eklenen alanlar kapanış kopyasına sızmasın
        na_ = acilis_sunulan(yeni_, fx_id_, P); nc_ = kapanis_kilidi(plog, tahmin_, fx_id_, kickoff, now_utc, P)
        print(f"Kilit: {len(yeni_)} yeni açılış ({na_} oranlı), {nc_} kapanış kilidi", flush=True)
    except Exception as e: print("kapanış kilidi atlandı:", e.__class__.__name__, e, flush=True)
    try:   # 🌱 taze veri gölge kaydı (scripts/tazeveri.py): kadro / oran hareketi / karışım ayarlı ve ayarsız tahmin; kapı açıksa fixtures çıktısına
        import tazeveri as TZV
        TZA = TZV.ayar(); TZG = TZV.jl(TZV.GOLGE, None) or {}
        nt_ = TZV.golge_guncelle(fx, lambda f_: kickoff(f_).timestamp(), model=model_yolu, now=now_utc, A=TZA, G=TZG, yaz=False)
        nr_ = TZV.sonuc_isle(TZG, all_ms, now=now_utc, yaz=False)
        TZV._yaz(TZG, now_utc)
        fx_c, nz_ = TZV.cikti_uygula(fx, TZA, TZG)
        if nz_:
            json.dump([{k: v for k, v in f.items() if k != "xg"} for f in fx_c], open(fxp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(f"Taze veri gölge kaydı: {nt_} maç güncellendi, {nr_} sonuç, yayında ayarlı {nz_} maç", flush=True)
    except Exception as e: print("taze veri atlandı:", e.__class__.__name__, e, flush=True)
    try:   # 🩹 kadro özeti (scripts/kadro.py, türetilmiş): maç başlamadan önceki son hali kd alanına (p kilitli kalır)
        import kadro
        nk_ = kadro.predlog_isle(plog)
        if nk_: print(f"Kadro özeti eklenen kilitli tahmin: {nk_}", flush=True)
    except Exception as e: print("kadro özeti atlandı:", e.__class__.__name__, e, flush=True)
    plog = grade_predlog(plog, all_ms, today)
    try:   # 🧾 sezon verisinde sonucu gecikenler (hafta içi turları vb.) iddaa sonuçlarından: r/rh/rs (scripts/sonuc_esle.py; p değişmez)
        import sonuc_esle
        oz_ = sonuc_esle.tamamla(plog, today, DATA, cevrimici=not offline)
        print("iddaa sonuç eşleme:", json.dumps(oz_, ensure_ascii=False), flush=True)
    except Exception as e: print("iddaa sonuç eşleme atlandı:", e.__class__.__name__, e, flush=True)
    json.dump(plog, open(plp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    live = live_report(plog, today)
    try: live["kilit"] = kilit_karne(plog)   # yeni alan: açılış / kapanış kilidi karnesi (eski alanlar aynı)
    except Exception as e: print("kilit karnesi atlandı:", e.__class__.__name__, e, flush=True)
    print("Canlı karne:", json.dumps(live, ensure_ascii=False), flush=True)
    if PK:
        try:
            import pazar as PZM
            PK["canli"] = PZM.live_scores(plog, PK)
            gate = PK["canli"].get("altin_kapisi", {})
            for c_, v_ in PK.get("pazarlar", {}).items():
                v_["altina_uygun"] = bool(c_ in PZM.ESKI or (v_.get("oneriye_uygun") and gate.get(c_, {}).get("acik")))
            PK["boyut"] = {"fixtures_kb": round(os.path.getsize(fxp) / 1024, 1), "predlog_kb": round(os.path.getsize(plp) / 1024, 1)}
            json.dump(clean_nan(PK), open(kp_, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        except Exception as e: print("pazar karnesi yazılamadı:", e.__class__.__name__, e, flush=True)
    try:
        oneri = pick_calib(season, P["rho"]) if not quick or not model.get("oneri") else model.get("oneri")
        print("Öneri kalibrasyonu:", json.dumps(oneri and oneri["dogrulama"], ensure_ascii=False)[:600], flush=True)
    except Exception as e:
        print("öneri kalibrasyonu atlandı:", e, flush=True); oneri = model.get("oneri")
    model = {"oneri": oneri, "live": live, "cup": cup, "updated": now, "tuned": now if not quick else model.get("tuned", now), "fp": fp, "engine": ENGINE_V, "data_v": DATA_V,
             "checks": (model.get("checks", 0) + 1), "trainings": model.get("trainings", 0) + (0 if quick else 1),
             "tuned_n": (bt["n"] if bt else 0) if not quick else model.get("tuned_n", 0), "params": P, "backtest": mt, "market": mstats, "sources": log,
             "leagues": {lg: {"name": d.get("name", LEAGUES.get(lg, ("", "", lg))[2]), "asOf": d["asOf"],
                              "n": len([m for m in d["matches"] if m["season"] == d.get("season")]), "n_all": len(d["matches"]),
                              "avg": round(sum(sum(m["ft"]) for m in d["matches"] if m["season"] == d.get("season")) / max(1, len([m for m in d["matches"] if m["season"] == d.get("season")])), 2)}
                         for lg, d in season.items()}}
    # 🗄️ ml70: veritabanı büyüklüğü (uygulama için yeni alan; okumazsa zararsız)
    try:
        import arsiv
        dx = json.load(open(os.path.join(DATA, "derin", "index.json"), encoding="utf-8")) if os.path.exists(os.path.join(DATA, "derin", "index.json")) else {}
        model["veritabani"] = {"sezon_maci": sum(len(d["matches"]) for d in season.values()), "derin_maci": dx.get("toplam", 0),
                               "derin_dosya": dx.get("dosya", 0), "arsiv": arsiv.ozet(DATA)}
    except Exception as e: print("veritabanı özeti atlandı:", e, flush=True)
    json.dump(clean_nan(model), open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1, allow_nan=False)
    try:
        try:
            import guc
            _GA = guc.ayar(); _lp = lambda lg: guc.lig_parametre(clean_nan(model).get("params") or {}, lg, season, _GA)
        except Exception: _lp = None
        write_ratings(season, clean_nan(model).get("params") or {}, lig_param=_lp)
    except Exception as e: print("ratings.json atlandı:", e, flush=True)
    hp =os.path.join(DATA, "history.json")
    hist = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else []
    if mt and not quick:
        hist.append({"t": now, "n": mt["n"], "logloss": mt["logloss"], "brier": mt["brier"], "r1x2": mt["r1x2"]})
        hist = hist[-200:]
    json.dump(hist, open(hp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("Bitti:", json.dumps({k: v for k, v in mt.items() if k != "by_league"}, ensure_ascii=False), "params", P)

def fit_league_js(ms, MP):
    """index.html fitLeague()'in birebir karşılığı (v118): uygulama artık telefonda eğitmiyor, bu sonucu data/ratings.json'dan okuyor."""
    use = ms
    if len(use) < 12: return None
    last = date.fromisoformat(max(m["d"] for m in use))
    W = [math.exp(-MP("decay", 0.004) * (last - date.fromisoformat(m["d"])).days) for m in use]
    names = list(dict.fromkeys(x for m in use for x in (m["h"], m["a"])))
    att = {n: 1.0 for n in names}; dfn = {n: 1.0 for n in names}
    MK = MP("mkt", 0)
    T = [[(1 - MK) * m["ft"][0] + MK * m["xg"][0], (1 - MK) * m["ft"][1] + MK * m["xg"][1]] if isinstance(m.get("xg"), list) else m["ft"] for m in use]
    sw = sum(W); sh = sum(w * t[0] for w, t in zip(W, T)); sa = sum(w * t[1] for w, t in zip(W, T))
    cl = lambda x, a, b: max(a, min(b, x))
    gamma = cl(sh / max(sa, 0.1), 1.0, 1.6); mu = sa / sw
    K = MP("prior", 2.5)
    for _ in range(40):
        gs = dict.fromkeys(names, 0.0); es = dict.fromkeys(names, 0.0); gc = dict.fromkeys(names, 0.0); ec = dict.fromkeys(names, 0.0)
        for m, w, t in zip(use, W, T):
            h, a = m["h"], m["a"]
            eh = mu * gamma * att[h] * dfn[a]; ea = mu * att[a] * dfn[h]
            gs[h] += w * t[0]; es[h] += w * eh / att[h]; gc[a] += w * t[0]; ec[a] += w * eh / dfn[a]
            gs[a] += w * t[1]; es[a] += w * ea / att[a]; gc[h] += w * t[1]; ec[h] += w * ea / dfn[h]
        base = mu * math.sqrt(gamma)
        for n in names:
            att[n] = (gs[n] + K * base) / (es[n] + K * base); dfn[n] = (gc[n] + K * base) / (ec[n] + K * base)
        ga = math.exp(sum(math.log(att[n]) for n in names) / len(names)); gd = math.exp(sum(math.log(dfn[n]) for n in names) / len(names))
        for n in names: att[n] /= ga; dfn[n] /= gd
        nh = dh = na = da = 0.0
        for m, w, t in zip(use, W, T):
            nh += w * t[0]; dh += w * att[m["h"]] * dfn[m["a"]]; na += w * t[1]; da += w * att[m["a"]] * dfn[m["h"]]
        mu = na / da; gamma = cl((nh / dh) / mu, 1.0, 1.6)
    g1 = g = 0
    for m in use:
        if isinstance(m.get("ht"), list): g1 += m["ht"][0] + m["ht"][1]; g += m["ft"][0] + m["ft"][1]
    h1 = cl((g1 + MP("h1", 0.44) * 60) / (g + 60), 0.36, 0.52)
    cnt = collections.Counter(x for m in use for x in (m["h"], m["a"]))
    return {"mu": mu, "gamma": gamma, "h1": h1, "n": len(use), "t": {n: [round(att[n], 6), round(dfn[n], 6), cnt[n]] for n in names}}

def write_ratings(season, params, lig_param=None):
    """⚡ v118: data/ratings.json — uygulamanın açılışta ihtiyaç duyduğu küçük özet: lig güçleri (fitLeague sonucu) ve
    her takımın son 5 maçı. season.json (3,8 MB) artık yalnız puan durumu / aralarındaki maçlar gibi ekranlarda, gerekince yüklenir.
    Biçim: tm = takım adları; m = [tarih, ev no, dep no, ev gol, dep gol, sezon]; fit.a/fit.d/fit.c = tm sırasıyla hücum/savunma/maç;
    o = bu sezonun takımları (uygulamadaki sırayla)."""
    MP = lambda k, d: params[k] if params.get(k) is not None else d
    out = {"v": 1, "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
           "params": {k: params.get(k) for k in ("decay", "prior", "mkt", "h1")}, "leagues": {}}
    for lg, d in season.items():
        ms = sorted([m for m in d.get("matches", []) if m and isinstance(m.get("ft"), list) and len(m["ft"]) == 2], key=lambda m: m["d"])
        tm = list(dict.fromkeys(x for m in ms for x in (m["h"], m["a"]))); ix = {n: i for i, n in enumerate(tm)}
        last5 = collections.defaultdict(list)
        for i, m in enumerate(ms): last5[m["h"]].append(i); last5[m["a"]].append(i)
        keep = sorted({i for L in last5.values() for i in L[-5:]})
        L = {k: d[k] for k in ("name", "cup", "espn", "asOf", "season", "src") if d.get(k) is not None}
        L.update(n=len(ms), tm=tm, m=[[ms[i]["d"], ix[ms[i]["h"]], ix[ms[i]["a"]], ms[i]["ft"][0], ms[i]["ft"][1], ms[i].get("season")] for i in keep])
        if not d.get("cup"):
            lp = lig_param(lg) if lig_param else params      # ⚖️ oransız ligde kapıyı geçen Poisson ayarı (yoksa motor ayarı)
            f = fit_league_js(ms, (lambda k, dflt, _p=lp: _p[k] if _p.get(k) is not None else dflt) if lp is not params else MP)
            if f:
                last = max((m.get("season") or 0) for m in ms)
                cur = [m for m in ms if not m.get("season") or m.get("season") == last]
                L["o"] = [ix[n] for n in dict.fromkeys(x for m in cur for x in (m["h"], m["a"]))]   # uygulamanın takımları gezdiği sıra
                t = f.pop("t")
                f.update(avg=sum(m["ft"][0] + m["ft"][1] for m in cur) / len(cur) if cur else None,
                         a=[t[n][0] for n in tm], d=[t[n][1] for n in tm], c=[t[n][2] for n in tm])
                L["fit"] = f
        out["leagues"][lg] = L
    json.dump(clean_nan(out), open(os.path.join(DATA, "ratings.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

def clean_nan(o):
    """JSON'a NaN/sonsuz yazılmasın (tarayıcı okuyamaz): None'a çevir."""
    if isinstance(o, float): return o if math.isfinite(o) else None
    if isinstance(o, dict): return {k: clean_nan(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean_nan(v) for v in o]
    return o

if __name__ == "__main__":
    try:
        main()
        try: os.remove(os.path.join(DATA, "engine_error.txt"))
        except FileNotFoundError: pass
    except Exception:
        import traceback
        tb = traceback.format_exc(); print(tb, flush=True)
        open(os.path.join(DATA, "engine_error.txt"), "w", encoding="utf-8").write(datetime.now(timezone.utc).isoformat() + "\n" + tb)
        sys.exit(1)
