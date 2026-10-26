#!/usr/bin/env python3
"""🌐 Açık veri toplayıcı (sıfır maliyet, anahtarsız, ağ yoksa sessizce atlar).

Kaynaklar (yalnız türetilmiş özellik yazılır; ham kaynak dosyası depoya girmez):
  1) Club Elo — http://api.clubelo.com/<GGGG-AA-GG> (herkese açık CSV API'si, anahtar yok; atıf: clubelo.com).
     Avrupa kulüplerinin günlük Elo puanı: ligler arası (kupa) güç ölçeği için.
  2) openfootball/champions-league — CC0 (kamu malı) UEFA kupa sonuçları (Şampiyonlar / Avrupa / Konferans Ligi).
     Yalnız laboratuvar sınaması için geçmiş kupa maçları (lab/acik_lab.py); üretimde ESPN kupaları zaten var.

Üretim bağlantısı (bayraklı, geri alınabilir): data/acik/elo_kupa.json
  {"aktif": true|false, "w": .., "beta": .., ...}  — lab/acik_lab.py yazar, yalnız kapıyı geçerse aktif=true.
  aktif ise model.json → cup.teams (uygulamanın kupa/ligler arası yolu, index.html absRating) Elo'ya doğru büzülür:
     r_t = ln(hücum) − ln(savunma);  r̂_t = beta·(Elo_t − Ē)/100;  δ_t = w·(r̂_t − (r_t − r̄))
     hücum' = hücum·e^(δ/2),  savunma' = savunma·e^(−δ/2)   (toplam gol beklentisi korunur; yalnız güç farkı değişir)
  Geri alma: data/acik/elo_kupa.json içinde "aktif": false (ya da ACIK_ELO=0 ortam değişkeni) → bir sonraki çalışmada
  update.py'nin ham kupa güçleri olduğu gibi kalır. Koruyucu geri alma aktifken (data/rollback.json, elo_kupa anahtarı yoksa)
  uygulanmaz.
Çıktı: data/acik/elo.json (yalnız kupa takımlarımızın adı → Elo, tarih), model.json cup.elo (uygulama izi).
"""
import csv, difflib, hashlib, io, json, os, re, sys, tempfile, time, urllib.request
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data"); ACIK = os.path.join(DATA, "acik")
ONBELLEK = os.environ.get("ACIK_ONBELLEK") or os.path.join(tempfile.gettempdir(), "bulutoxx_acik")
UA = {"User-Agent": "Mozilla/5.0 (BULUTOXX acik-veri; +https://bulutoxx.github.io)"}
ELO_API = "http://api.clubelo.com/"
OF_RAW = "https://raw.githubusercontent.com/openfootball/champions-league/master/"
ATIF = {"clubelo": "Club Elo puanları: clubelo.com (api.clubelo.com)",
        "openfootball": "UEFA kupa sonuçları: github.com/openfootball/champions-league (CC0 1.0)"}

# lig anahtarımız → Club Elo ülke kodu
CE_ULKE = {"en": "ENG", "en2": "ENG", "en3": "ENG", "en4": "ENG", "es": "ESP", "es2": "ESP", "de": "GER", "de2": "GER",
           "it": "ITA", "it2": "ITA", "fr": "FRA", "fr2": "FRA", "nl": "NED", "pt": "POR", "be": "BEL", "tr1": "TUR",
           "gr": "GRE", "sc": "SCO", "sc2": "SCO", "at": "AUT", "ch": "SUI", "dk": "DEN", "no": "NOR", "se": "SWE",
           "pl": "POL", "ro": "ROM", "ru": "RUS", "fi": "FIN", "ie": "IRL"}
# openfootball (FIFA kodu) → Club Elo ülke kodu (farklı olanlar)
OF_ULKE = {"ROU": "ROM", "SVK": "SLK", "MDA": "MOL", "LVA": "LAT", "BIH": "BHZ", "MKD": "MAC", "FRO": "FAR", "LTU": "LIT",
           "MNE": "MNT", "KOS": "KOS"}
# openfootball ülke kodu → bizim lig (yalnız birinci lig; kupa takımının iç lig gücü için)
OF_LIG = {"ENG": "en", "ESP": "es", "GER": "de", "ITA": "it", "FRA": "fr", "NED": "nl", "POR": "pt", "BEL": "be", "TUR": "tr1",
          "GRE": "gr", "SCO": "sc", "AUT": "at", "SUI": "ch", "DEN": "dk", "NOR": "no", "SWE": "se", "POL": "pl", "ROU": "ro",
          "RUS": "ru", "FIN": "fi", "IRL": "ie"}
# bizim / ESPN / openfootball adı → Club Elo adı (genel eşleyicinin bulamadıkları)
ALIAS_CE = {
    "Manchester City": "Man City", "Manchester United": "Man United", "Newcastle United": "Newcastle", "Nottingham Forest": "Forest",
    "Brighton & Hove Albion": "Brighton", "Brighton & Hove Albion FC": "Brighton", "Wolverhampton": "Wolves", "Tottenham Hotspur": "Tottenham",
    "Atlético Madrid": "Atletico", "Club Atlético de Madrid": "Atletico", "Athletic Bilbao": "Bilbao", "Athletic Club": "Bilbao",
    "Real Betis": "Betis", "Real Betis Balompié": "Betis", "Real Sociedad": "Sociedad", "Celta Vigo": "Celta", "RC Celta de Vigo": "Celta",
    "Bayern München": "Bayern", "FC Bayern München": "Bayern", "Borussia Dortmund": "Dortmund", "Bayer Leverkusen": "Leverkusen",
    "Bayer 04 Leverkusen": "Leverkusen", "Eintracht Frankfurt": "Frankfurt", "SC Freiburg": "Freiburg", "VfB Stuttgart": "Stuttgart",
    "Mainz 05": "Mainz", "Borussia Mönchengladbach": "Gladbach", "1899 Hoffenheim": "Hoffenheim", "TSG 1899 Hoffenheim": "Hoffenheim",
    "1. FC Heidenheim 1846": "Heidenheim", "1. FC Union Berlin": "Union Berlin", "VfL Wolfsburg": "Wolfsburg",
    "Paris Saint-Germain": "Paris SG", "Paris Saint-Germain FC": "Paris SG", "Stade Brestois 29": "Brest", "Olympique Lyonnais": "Lyon",
    "Olympique Marseille": "Marseille", "LOSC Lille": "Lille", "Lille OSC": "Lille", "Stade Rennais FC": "Rennes",
    "Inter": "Inter", "FC Internazionale Milano": "Inter", "Internazionale": "Inter", "Lazio Roma": "Lazio", "SS Lazio": "Lazio",
    "Juventus FC": "Juventus", "AC Milan": "Milan", "SSC Napoli": "Napoli", "Atalanta BC": "Atalanta", "Bologna FC 1909": "Bologna",
    "Sp Lisbon": "Sporting", "Sporting Clube de Portugal": "Sporting", "Sporting CP": "Sporting", "Sp Braga": "Braga",
    "Sporting Braga": "Braga", "SC Braga": "Braga", "Vitória Guimarães": "Guimaraes", "Vitória SC": "Guimaraes",
    "Beşiktaş": "Besiktas", "Fenerbahçe": "Fenerbahce", "Başakşehir": "Bueyueksehir", "İstanbul Başakşehir": "Bueyueksehir",
    "AZ Alkmaar": "Alkmaar", "PSV Eindhoven": "PSV", "PSV": "PSV", "AFC Ajax": "Ajax", "Nijmegen": "Nijmegen", "NEC Nijmegen": "Nijmegen",
    "Club Brugge": "Brugge", "Club Brugge KV": "Brugge", "Cercle Brugge": "Cercle Brugge", "St. Gilloise": "St Gillis",
    "Union Saint-Gilloise": "St Gillis", "Royale Union Saint-Gilloise": "St Gillis", "St Truiden": "St Truiden", "KRC Genk": "Genk",
    "Royal Antwerp FC": "Antwerp", "FC Copenhagen": "FC Kobenhavn", "FC København": "FC Kobenhavn", "Bodo/Glimt": "Bodoe Glimt",
    "FK Bodø/Glimt": "Bodoe Glimt", "Malmo FF": "Malmoe", "Malmö FF": "Malmoe", "Mjallby": "Mjaellby", "Mjällby AIF": "Mjaellby",
    "Hacken": "Haecken", "BK Häcken": "Haecken", "IF Elfsborg": "Elfsborg", "Djurgårdens IF": "Djurgarden", "SK Rapid": "Rapid Wien",
    "Rapid Wien": "Rapid Wien", "SK Rapid Wien": "Rapid Wien", "SK Sturm Graz": "Sturm Graz", "FC Red Bull Salzburg": "Salzburg",
    "Red Bull Salzburg": "Salzburg", "LASK Linz": "LASK", "Univ. Craiova": "Craiova", "Universitatea Craiova": "Craiova",
    "CS Universitatea Craiova": "Craiova", "FCSB": "Steaua", "Lech Poznan": "Lech", "Lech Poznań": "Lech", "Legia Warszawa": "Legia",
    "Legia Warsaw": "Legia", "Jagiellonia Białystok": "Jagiellonia", "KuPS": "Kuopio", "KuPS Kuopio": "Kuopio", "OFI Crete": "OFI",
    "Shamrock Rovers": "Shamrock", "Olympiakos": "Olympiakos", "Olympiakos Piraeus": "Olympiakos", "PAOK Saloniki": "PAOK",
    "AEK Athens": "AEK", "Panathinaikos": "Panathinaikos", "Heart of Midlothian": "Hearts", "Rangers FC": "Rangers",
    "Celtic FC": "Celtic", "Red Star Belgrade": "Crvena Zvezda", "Crvena Zvezda": "Crvena Zvezda", "FK Crvena Zvezda": "Crvena Zvezda",
    "FK Qarabag": "Karabakh Agdam", "Qarabağ FK": "Karabakh Agdam", "Slavia Prague": "Slavia Praha", "Sparta Prague": "Sparta Praha",
    "AC Sparta Praha": "Sparta Praha", "SK Slavia Praha": "Slavia Praha", "Maccabi Tel-Aviv": "M Tel Aviv", "Maccabi Tel Aviv": "M Tel Aviv",
    "Hapoel Be'er": "Beer-Sheva", "Hapoel Beer Sheva": "Beer-Sheva", "Maccabi Haifa": "Maccabi Haifa", "Ludogorets Razgrad": "Razgrad",
    "PFC Ludogorets Razgrad": "Razgrad", "Omonia Nicosia": "Omonia", "Pafos": "Paphos", "Pafos FC": "Paphos", "AEK Larnaca": "Larnaca",
    "APOEL Nicosia": "APOEL", "Raków Czestochowa": "Rakow", "Raków Częstochowa": "Rakow", "Kairat Almaty": "Kairat",
    "FC Astana": "FK Astana", "Riga FC": "FK Riga", "KF Shkëndija": "Shkendija", "Drita Gjilan": "Drita", "Hamrun Spartans": "Hamrun",
    "Lincoln Red Imps": "Lincoln", "Inter D'Escaldes": "Escaldes", "Ararat-Armenia": "Ararat", "Hajduk Split": "Hajduk",
    "HNK Hajduk Split": "Hajduk", "GNK Dinamo Zagreb": "Dinamo Zagreb", "HNK Rijeka": "Rijeka", "Shakhtar Donetsk": "Shakhtar",
    "Dynamo Kyiv": "Dynamo Kyiv", "Dinamo Kiev": "Dynamo Kyiv", "Sabah FK": "Sabah", "FC Noah": "Noah", "NK Celje": "Celje",
    "NK Olimpija Ljubljana": "Olimpija Ljubljana", "Iberia 1999": "Saburtalo", "Levski Sofia": "Levski", "CSKA Sofia": "CSKA Sofia",
    "Ferencvárosi TC": "Ferencvaros", "Ferencvaros": "Ferencvaros", "Viktoria Plzeň": "Viktoria Plzen", "FC Viktoria Plzeň": "Viktoria Plzen",
    "Young Boys": "Young Boys", "BSC Young Boys": "Young Boys", "FC Basel 1893": "Basel", "FC Lugano": "Lugano", "Servette FC": "Servette",
    "FC Zürich": "Zuerich", "FC St. Gallen 1879": "StGallen", "Molde FK": "Molde", "Rosenborg BK": "Rosenborg",
    "FC Midtjylland": "Midtjylland", "FC Nordsjælland": "Nordsjaelland", "Brøndby IF": "Brondby", "Sheriff Tiraspol": "Sheriff Tiraspol",
    "Slovan Bratislava": "Slovan Bratislava", "ŠK Slovan Bratislava": "Slovan Bratislava", "Zrinjski Mostar": "Zrinjski Mostar",
    "HŠK Zrinjski Mostar": "Zrinjski Mostar", "Borac Banja Luka": "Borac Banja Luka", "FK Borac Banja Luka": "Borac Banja Luka",
    "The New Saints": "The New Saints", "Manchester City FC": "Man City", "Manchester United FC": "Man United",
    "Qarabağ Ağdam FK": "Karabakh Agdam", "Stade Rennais": "Rennes", "Sporting Clube de Braga": "Braga", "Torreense": "Torreense", "Galatasaray": "Galatasaray", "Trabzonspor": "Trabzonspor",
}
STOP2 = {"fc", "sc", "sv", "ac", "as", "afc", "cf", "rc", "ssc", "fk", "sk", "club", "de", "cd", "ud", "sd", "bk", "calcio", "acf",
         "ogc", "rsc", "pfc", "nk", "hnk", "gnk", "kv", "krc", "if", "aif", "sl", "cp", "osc", "bc", "tc", "jk", "spor", "kf",
         "the", "1", "fk", "royal", "royale", "1893", "1909", "1899", "1846", "1879", "1900", "04", "05", "29"}


def norm(s):
    import unicodedata
    s = str(s).replace("ı", "i").replace("İ", "I").replace("ø", "oe").replace("Ø", "Oe").replace("ß", "ss").replace("æ", "ae")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return " ".join(w for w in re.split(r"[^a-z0-9]+", s) if w and w not in STOP2)


def eslestir(ad, adaylar, ipucu=None):
    """ad → adaylardan biri (yoksa None). adaylar: {ad: ülke}. ipucu: Club Elo ülke kodu (varsa önce o ülkede aranır)."""
    if ad in ALIAS_CE and ALIAS_CE[ad] in adaylar:
        return ALIAS_CE[ad]
    havuz = [a for a, c in adaylar.items() if not ipucu or c == ipucu] or list(adaylar)
    n = norm(ad); nt = set(n.split())
    if not nt:
        return None
    for a in havuz:
        if norm(a) == n:
            return a
    alt = [a for a in havuz if (set(norm(a).split()) and (set(norm(a).split()) <= nt or nt <= set(norm(a).split())))]
    if len(alt) == 1:
        return alt[0]
    b = difflib.get_close_matches(n, [norm(a) for a in havuz], n=2, cutoff=0.82)
    if b and (len(b) == 1 or difflib.SequenceMatcher(None, n, b[0]).ratio() - difflib.SequenceMatcher(None, n, b[1]).ratio() > .05):
        for a in havuz:
            if norm(a) == b[0]:
                return a
    return None


# ------------------------------------------------------------------ indirme (önbellekli, savunmacı)
def _get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8-sig", errors="replace")


def _onbellek(ad, url, yas_gun=None):
    """Geçici klasörde önbellek (repoya girmez). yas_gun: bu kadar günden eskiyse yeniden indir (None: hiç)."""
    os.makedirs(ONBELLEK, exist_ok=True)
    p = os.path.join(ONBELLEK, ad)
    if os.path.exists(p) and (yas_gun is None or time.time() - os.path.getmtime(p) < yas_gun * 86400):
        return open(p, encoding="utf-8").read()
    t = _get(url)
    open(p, "w", encoding="utf-8").write(t)
    return t


def clubelo_gun(g):
    """g tarihindeki tüm kulüplerin Elo'su: {kulüp: (ülke, elo)}. Ağ yoksa / boşsa {}."""
    g = g if isinstance(g, str) else g.isoformat()
    try:
        t = _onbellek(f"clubelo_{g}.csv", ELO_API + g, yas_gun=None if g < date.today().isoformat() else 0.2)
    except Exception:
        return {}
    out = {}
    for r in csv.DictReader(io.StringIO(t)):
        try:
            out[r["Club"]] = (r["Country"], float(r["Elo"]))
        except (KeyError, TypeError, ValueError):
            continue
    return out


AY = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
SATIR = re.compile(r"^\s*(?:\d{1,2}[:.]\d{2}\s+)?(.+?)\s+\(([A-Z]{3})\)\s+v\s+(.+?)\s+\(([A-Z]{3})\)\s+(\d+)-(\d+)(.*)$")
TARIH = re.compile(r"^\s*(?:\[)?(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\s+([A-Z][a-z]{2})/?\s*(\d{1,2})(?:\s+(\d{4}))?")


def openfootball_kupa(sezon, kod):
    """sezon '2024-25', kod 'cl'|'el'|'conf' → [{d, h, hc, a, ac, ft (90 dk), ht}] ; ağ yoksa []."""
    try:
        t = _onbellek(f"of_{sezon}_{kod}.txt", f"{OF_RAW}{sezon}/{kod}.txt")
    except Exception:
        return []
    y0 = int(sezon[:4]); gun = None; out = []
    for ln in t.splitlines():
        m = TARIH.match(ln)
        if m and " v " not in ln:
            mo = AY.get(m.group(1)); dd = int(m.group(2))
            yy = int(m.group(3)) if m.group(3) else (y0 if mo >= 7 else y0 + 1)
            gun = date(yy, mo, dd).isoformat(); continue
        m = SATIR.match(ln)
        if not m or not gun:
            continue
        h, hc, a, ac, g1, g2, rest = m.groups()
        ft = [int(g1), int(g2)]; ht = None
        par = re.findall(r"\((\d+)-(\d+)(?:,\s*(\d+)-(\d+))?\)", rest)
        if "a.e.t" in rest or "pen" in rest:
            # "4-2 pen. 1-0 a.e.t. (1-0, 1-0)" ya da "1-2 a.e.t. (1-1, 0-1)": parantezin ilki 90 dk skoru
            if not par:
                continue
            ft = [int(par[0][0]), int(par[0][1])]
            ht = [int(par[0][2]), int(par[0][3])] if par[0][2] else None
        elif par:
            ht = [int(par[0][0]), int(par[0][1])]
        out.append({"d": gun, "h": h.strip(), "hc": hc, "a": a.strip(), "ac": ac, "ft": ft, "ht": ht, "kupa": kod})
    return out


# ------------------------------------------------------------------ üretim: kupa güçlerine Elo büzülmesi
def elo_ayar(r_t, elo_t, w, beta):
    """r_t: {takım: r}, elo_t: {takım: elo} (yalnız ikisinde de olanlar kullanılır) → {takım: δ}."""
    ort = [t for t in r_t if t in elo_t]
    if len(ort) < 8 or not w:
        return {}
    rb = sum(r_t[t] for t in ort) / len(ort); eb = sum(elo_t[t] for t in ort) / len(ort)
    return {t: w * (beta * (elo_t[t] - eb) / 100.0 - (r_t[t] - rb)) for t in ort}


def kupa_uygula(cup, elo_t, w, beta):
    """model.json 'cup' sözlüğüne Elo büzülmesini uygular (yerinde). Taban: update.py'nin ham değerleri."""
    import math
    teams = cup.get("teams") or {}
    iz = cup.get("elo") or {}
    imza = hashlib.sha1(json.dumps(teams, sort_keys=True).encode()).hexdigest()[:16]
    ham = iz.get("ham") if iz.get("imza") == imza and iz.get("ham") else {t: v[:2] for t, v in teams.items()}
    r = {t: math.log(max(v[0], 1e-6)) - math.log(max(v[1], 1e-6)) for t, v in ham.items()}
    d = elo_ayar(r, elo_t, w, beta)
    yeni = {}
    for t, v in teams.items():
        a, de = ham.get(t, v[:2]); k = d.get(t, 0.0)
        yeni[t] = [round(a * math.exp(k / 2), 3), round(de * math.exp(-k / 2), 3)] + list(v[2:])
    cup["teams"] = yeni
    cup["elo"] = {"ham": ham, "imza": hashlib.sha1(json.dumps(yeni, sort_keys=True).encode()).hexdigest()[:16],
                  "w": w, "beta": beta, "eslesen": len(d), "takim": len(teams), "kaynak": ATIF["clubelo"]}
    return len(d)


def kupa_geri_al(cup):
    """Elo izi varsa ham değerlere döndürür (bayrak kapatılınca)."""
    iz = cup.get("elo") or {}
    teams = cup.get("teams") or {}
    if iz.get("ham") and iz.get("imza") == hashlib.sha1(json.dumps(teams, sort_keys=True).encode()).hexdigest()[:16]:
        cup["teams"] = {t: list(iz["ham"].get(t, v[:2])) + list(v[2:]) for t, v in teams.items()}
    cup.pop("elo", None)


def _jl(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def _dondur():
    RB = _jl(os.path.join(DATA, "rollback.json"), {}) or {}
    return bool(RB.get("aktif")) and not RB.get("elo_kupa")


def main():
    t0 = time.time()
    ayar = _jl(os.path.join(ACIK, "elo_kupa.json"), {}) or {}
    mp = os.path.join(DATA, "model.json"); M = _jl(mp)
    if not M or not M.get("cup"):
        print("açık veri: model.json/cup yok, atlandı"); return
    aktif = bool(ayar.get("aktif")) and os.environ.get("ACIK_ELO", "1") != "0" and not _dondur()
    cup = M["cup"]
    if not aktif:
        if cup.get("elo"):
            kupa_geri_al(cup); json.dump(M, open(mp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            print("açık veri: Elo bayrağı kapalı → kupa güçleri ham hale döndürüldü")
        else:
            print("açık veri: Elo bayrağı kapalı (data/acik/elo_kupa.json aktif=false); değişiklik yok")
        return
    bugun = date.today()
    E = {}
    for geri in range(0, 4):            # bugün boşsa birkaç gün geriye bak
        E = clubelo_gun(bugun - timedelta(days=geri))
        if E:
            break
    eski = _jl(os.path.join(ACIK, "elo.json"), {}) or {}
    adaylar = {k: v[0] for k, v in E.items()}
    elo_t = {}
    if E:
        for t, v in (cup.get("teams") or {}).items():
            k = eslestir(t, adaylar, CE_ULKE.get(v[2]) if len(v) > 2 and v[2] else None)
            if k:
                elo_t[t] = round(E[k][1], 1)
    elif eski.get("takimlar") and (bugun - date.fromisoformat(eski.get("tarih", "2000-01-01"))).days <= 10:
        elo_t = eski["takimlar"]; print("açık veri: Club Elo'ya ulaşılamadı; son kayıt kullanılıyor", eski.get("tarih"))
    if not elo_t:
        print("açık veri: Club Elo yok (ağ?), kupa güçleri değişmedi"); return
    n = kupa_uygula(cup, elo_t, float(ayar.get("w", 0)), float(ayar.get("beta", 0.25)))
    json.dump(M, open(mp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    os.makedirs(ACIK, exist_ok=True)
    if E:
        json.dump({"tarih": bugun.isoformat(), "kaynak": ATIF["clubelo"], "takimlar": dict(sorted(elo_t.items()))},
                  open(os.path.join(ACIK, "elo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"açık veri: Club Elo {len(elo_t)}/{len(cup.get('teams') or {})} kupa takımında eşlendi, {n} takıma uygulandı "
          f"(w={ayar.get('w')}, beta={ayar.get('beta')}) {time.time() - t0:.1f} sn")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback; traceback.print_exc(); print("açık veri atlandı:", e)
