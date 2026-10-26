"""OXXai v107 · Canlı maç istatistik ayarı (sunucu tarafı ortak matematik + ESPN anlık görüntüsü).

Uygulamadaki <script id="canli-gt-v107"> ile BİREBİR aynı formül: skor/zaman modelinin kalan süre gol beklentileri
(LH, LA) canlı istatistiklerle ölçülü biçimde eğilir.

  e      = λev / (λev + λdep)                       maç öncesi beklenen gol payı (takım gücü zaten λ'da → yalnız "sürpriz" ölçülür)
  pay(x,y)= (x+1)/(x+y+2)                           Laplace düzeltmeli pay
  ds     = pay(isabetli şut) − e   (son 8–20 dk'lık fark varsa 0,6·toplam + 0,4·son dönem)
  dh     = pay(şut) − e
  dp     = topa sahip olma payı − (0,5 + 0,5·(e − 0,5))
  w      = bilgi/(bilgi+6), bilgi = isabetli şut toplamı + 0,35·şut toplamı      (az veri → küçük etki)
  wt     = min(1, dakika/30)                                                    (ilk dakikalar gürültülü)
  tl     = sınırla(ln((şut/dk)/0,27), ±0,7)  (dakika ≥ 20)                      (tempo: iki takımın da gol hızı)
  s      = κ·w·wt·(0,6·ds + 0,3·dh + 0,1·dp) ;  g = κ·wt·0,12·tl
  ln mEv = sınırla(s + g, ±ln 1,25) ; ln mDep = sınırla(−s + g, ±ln 1,25)      → her takımda en çok ±%25

Varsayılan κ = 0,5 (küçük). Katsayılar data/canli_istat.json'dan yalnız "kabul": true ise okunur (lab/canli_istat_lab.py kapısı).
Kaynaklar (katsayıların yönü ve göreli büyüklüğü):
  • Fan & Wang (2024), Social Science Quarterly, doi:10.1111/ssqu.13364 — 98.849 maç: isabetli şut gol üretiminin en güçlü canlı
    göstergesi; şut ve korner de artırır; etki ikinci yarıda daha büyük → b_sot > b_sh, wt ile zamanla artan ağırlık.
  • Collet (2013), J. Sports Sciences 31(2):123-136 — maç düzeyinde topa sahip olma takım kalitesi ve saha avantajı
    kontrol edilince zayıf (hatta ters) yordayıcı → b_pos çok küçük (0,1).
  • Lago (2009), J. Sports Sciences 27(13) — geride olan takım topa daha çok sahip olur (skor durumu karıştırıcısı) → b_pos küçük.
  • Robberechts, Van Haaren & Davis (2021), KDD — oyun içi kazanma olasılığında bağlamsal (şut/fırsat, son dakikalardaki
    hücum) özellikler skor+zaman modeline ölçülü katkı yapar; kırmızı kartın etkisi zamanla azalır.
  • Dixon & Robinson (1998), The Statistician 47(3) — skor durumuna bağlı gol hızları (mevcut ±%10 skor etkisi).
  • Titman, Costain, Ridall & Gould (2015), JRSS A 178(3) — kırmızı kartın gol hızına etkisi (mevcut 0,72 / 1,25 çarpanı).
"""
import json, math, os, re, unicodedata
import urllib.request

DEF = {"kappa": 0.5, "b_sot": 0.6, "b_sh": 0.3, "b_pos": 0.1, "b_tempo": 0.12, "cap": math.log(1.25),
       "k_info": 6.0, "t_full": 30.0, "tempo_ref": 0.27}

# Uygulamadaki ESPN haritasıyla aynı (index.html → const ESPN)
ESPN = {"tr1": "tur.1", "en": "eng.1", "es": "esp.1", "it": "ita.1", "de": "ger.1", "fr": "fra.1", "ucl": "uefa.champions",
        "uel": "uefa.europa", "uecl": "uefa.europa.conf", "nl": "ned.1", "pt": "por.1", "be": "bel.1", "sc": "sco.1", "gr": "gre.1",
        "en2": "eng.2", "de2": "ger.2", "it2": "ita.2", "es2": "esp.2", "fr2": "fra.2", "br": "bra.1", "ar": "arg.1", "us": "usa.1",
        "mx": "mex.1", "jp": "jpn.1", "at": "aut.1", "ch": "sui.1", "dk": "den.1", "no": "nor.1", "se": "swe.1"}


def coef(data_dir=None):
    """Varsayılan katsayılar; data/canli_istat.json yalnız kapıdan geçmişse (kabul) κ'yı değiştirir."""
    C = dict(DEF)
    try:
        j = json.load(open(os.path.join(data_dir, "canli_istat.json"), encoding="utf-8")) if data_dir else None
        if j and j.get("kabul"):
            k = float(j.get("kappa"))
            if 0 <= k <= 1.5: C["kappa"] = k
    except Exception:
        pass
    return C


# ---------------------------------------------------------------- v117 · kalan süre modeli (uzatma dakikası + artan gol yoğunluğu)
# Uygulamadaki <script id="canli-dr-v117"> → remShare() ile BİREBİR aynı. Parametreler tek kaynaktan gelir: data/daily.json → canli.zaman
# (toplayıcının zaman sıralı kapısı kabul ettiyse). Kabul yoksa eski doğrusal model (90+ hatası düzeltilmiş hâli) kullanılır.
#   • Devre süresi 45 + e (beklenen uzatma: 1. yarı e1, 2. yarı e2 dk). Uzatma başladıysa kalan uzatma = max(e − geçen, rmin).
#   • Yarı içinde gol yoğunluğu doğrusal artar: λ(u) ∝ 1 + ξ(u − ½), u = yarı içinde geçen pay (Dixon & Robinson 1998,
#     The Statistician 47(3): gol hızı maç ilerledikçe artar). Kalan pay = 1 − F(u), F(u) = u + ξ(u² − u)/2.
#   • Yarıların toplam payı h1 / 1 − h1 (uzatmalar dahil, model.json → params.h1) değişmez.
#   • iddaa durum kodu: s=2 → 1. yarı (dakika 45'i geçebilir: 45+X), s=3 → 2. yarı (90+X), s=49 → devre arası.
#     Normal sürede asla uzatma devresi (120) formülüne geçilmez.
ZDEF = {"v": 117, "e1": 3.0, "e2": 3.0, "xi": 1.0, "rmin": 1.0}   # zamanca ilk yarıda Platt sonrası Brier ile seçildi (lab/canli_dr_lab.py)


def period_of(s):
    """iddaa canlı durum kodu → devre: 1 (ilk yarı), 2 (ikinci yarı), 0 (devre arası), None (bilinmiyor)."""
    return {2: 1, 3: 2, 49: 0}.get(s)


def zaman(data_dir=None, daily=None):
    """Kabul edilmiş kalan süre parametreleri (daily.json → canli.zaman) ya da None (eski model)."""
    try:
        D = daily if daily is not None else json.load(open(os.path.join(data_dir, "daily.json"), encoding="utf-8"))
        z = (D.get("canli") or {}).get("zaman") or {}
        if not z.get("kabul"): return None
        Z = dict(ZDEF)
        for k in ("e1", "e2", "xi", "rmin"):
            v = z.get(k)
            if isinstance(v, (int, float)) and math.isfinite(v): Z[k] = float(v)
        return Z
    except Exception:
        return None


def _F(u, xi): return u + xi * (u * u - u) / 2


def rem_share(t, h1=0.4428, pd=None, Z=None):
    """Kalan sürede beklenen gol payı (maç toplamına göre). Z=None → eski doğrusal model; Z → v117 modeli."""
    if pd == 0: return 1 - h1                                      # devre arası: ikinci yarının tamamı kaldı
    if Z is None:                                                  # eski model (yalnız 90+ → 120 hatası düzeltildi)
        if t < 45: return (45 - t) / 45 * h1 + (1 - h1)
        return max(.012, (90 - t) / 45 * (1 - h1))
    if pd is None: pd = 1 if t < 45 else 2
    e1, e2, xi, rmin = Z["e1"], Z["e2"], Z["xi"], Z["rmin"]
    if pd == 1:
        a = max(0.0, t); r = (45 - t) + e1 if t < 45 else max(e1 - (t - 45), rmin)
        return (1 - _F(a / (a + r), xi)) * h1 + (1 - h1)
    a = max(0.0, t - 45); r = (90 - t) + e2 if t < 90 else max(e2 - (t - 90), rmin)
    return max(.004, (1 - _F(a / (a + r), xi)) * (1 - h1))


def rem_lams(lh, la, hs, as_, t, rc, h1=0.4428, pd=None, Z=None):
    """Uygulamadaki skor/zaman/kırmızı kart modeli: kalan süre gol beklentileri (istatistiksiz)."""
    rem = rem_share(t, h1, pd, Z); d = hs - as_; st = t >= 15; up, dn = math.exp(.1), math.exp(-.1)
    LH = lh * rem * ((up if d < 0 else dn) if st else 1) * .72 ** rc[0] * 1.25 ** rc[1]
    LA = la * rem * ((up if d > 0 else dn) if st else 1) * .72 ** rc[1] * 1.25 ** rc[0]
    return LH, LA


def _pcdf(k, l):
    if k < 0: return 0.0
    p = math.exp(-l); c = p
    for i in range(1, k + 1): p *= l / i; c += p
    return min(1.0, c)


def probs(LH, LA, hs, as_):
    """MS 1/X/2, kalan sürede gol (0,5 Üst), 1,5 Üst, KG Var — 9x9 Poisson ızgarası (uygulamayla aynı)."""
    ph = [math.exp(-LH) * LH ** i / math.factorial(i) for i in range(9)]
    pa = [math.exp(-LA) * LA ** j / math.factorial(j) for j in range(9)]
    H = D = A = K = 0.0
    for i in range(9):
        for j in range(9):
            q = ph[i] * pa[j]; fh, fa = hs + i, as_ + j
            if fh > fa: H += q
            elif fh == fa: D += q
            else: A += q
            if fh > 0 and fa > 0: K += q
    z = H + D + A
    return {"H": H / z, "D": D / z, "A": A / z, "r05": 1 - math.exp(-(LH + LA)), "r15": 1 - _pcdf(1, LH + LA), "kg": K / z}


def _pay(x, y): return (x + 1) / (x + y + 2)


def feats(st, prev, lam, t, C=DEF):
    """İstatistik özellikleri (uygulamadaki feats() ile aynı). st/prev: {"sot":[h,a],"sh":[h,a],"pos":[h,a]}."""
    e = lam[0] / (lam[0] + lam[1]); ds = dh = dp = None; info = 0.0; rate = None
    sot, sh, pos = st.get("sot"), st.get("sh"), st.get("pos")
    if sot: ds = _pay(sot[0], sot[1]) - e; info += sot[0] + sot[1]
    if prev and sot and prev.get("sot"):
        a, b = sot[0] - prev["sot"][0], sot[1] - prev["sot"][1]
        if a >= 0 and b >= 0 and a + b >= 2:
            dr = _pay(a, b) - e; ds = dr if ds is None else .6 * ds + .4 * dr
    if sh:
        dh = _pay(sh[0], sh[1]) - e; info += .35 * (sh[0] + sh[1])
        if t >= 20: rate = (sh[0] + sh[1]) / max(t, 1)
    if pos and pos[0] + pos[1] > 0: dp = pos[0] / (pos[0] + pos[1]) - (.5 + .5 * (e - .5))
    w = info / (info + C["k_info"]); wt = min(1.0, t / C["t_full"])
    tl = max(-.7, min(.7, math.log(max(rate, 1e-3) / C["tempo_ref"]))) if rate is not None else 0.0
    return {"ds": ds, "dh": dh, "dp": dp, "w": w, "wt": wt, "tl": tl}


def mult(F, C=DEF, kappa=None):
    k = C["kappa"] if kappa is None else kappa
    s = k * F["w"] * F["wt"] * (C["b_sot"] * (F["ds"] or 0) + C["b_sh"] * (F["dh"] or 0) + C["b_pos"] * (F["dp"] or 0))
    g = k * F["wt"] * C["b_tempo"] * F["tl"]
    cl = lambda x: max(-C["cap"], min(C["cap"], x))
    return math.exp(cl(s + g)), math.exp(cl(-s + g))


# ---------------------------------------------------------------- ESPN (yalnız türetilmiş sayılar kaydedilir)
def _fold(s):
    s = unicodedata.normalize("NFKD", str(s or "").lower().replace("ı", "i"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return [w for w in re.sub(r"[^a-z0-9 ]", " ", s).split() if w not in {"fc", "cf", "sc", "afc", "ac", "fk", "sk", "club", "de", "cd", "ud", "sd", "the", "if", "bk", "as", "ss", "us"}]


def tm_eq(x, y):
    a, b = _fold(x), _fold(y)
    if not a or not b: return False
    if a == b: return True
    s1, s2 = (a, b) if len(a) <= len(b) else (b, a)
    if all(w in s2 for w in s1): return True
    return any(len(w) >= 5 and (w in b or any(v.startswith(w) or w.startswith(v) for v in b if len(v) >= 5)) for w in a)


def tm_score(x, y):
    """Eşleşme gücü (0 = eşleşmez): ortak kelime oranı; 'Manchester United' ↔ 'Manchester City' gibi yalnız şehir adı ortak
    olanları ayırmak için en güçlü aday seçilir (bkz. best_match)."""
    if not tm_eq(x, y): return 0.0
    a, b = set(_fold(x)), set(_fold(y))
    return len(a & b) / max(1, len(a | b)) + (1.0 if a == b else 0.0)


def best_match(E, h, a):
    """ESPN listesinde iki takım adı da eşleşen, toplam benzerliği en yüksek maç; eşitlikte belirsiz → None."""
    sc = sorted(((tm_score(x["h"], h) + tm_score(x["a"], a), i) for i, x in enumerate(E) if x.get("st") and tm_score(x["h"], h) > 0 and tm_score(x["a"], a) > 0), reverse=True)
    if not sc or (len(sc) > 1 and abs(sc[0][0] - sc[1][0]) < 1e-9): return None
    return E[sc[0][1]]


def _num(v):
    try: return float(str(v).replace(",", ".").replace("%", ""))
    except Exception: return None


def comp_stats(H, A):
    """ESPN rakip istatistik listelerinden {"sot","sh","pos","co"} — eksikler atlanır; isabetli şut veya şut yoksa None."""
    def m(c): return {s.get("name"): _num(s.get("displayValue", s.get("value"))) for s in (c.get("statistics") or []) if isinstance(s, dict)}
    h, a = m(H), m(A); out = {}
    for k, n in (("sot", "shotsOnTarget"), ("sh", "totalShots"), ("pos", "possessionPct"), ("co", "wonCorners")):
        if h.get(n) is not None and a.get(n) is not None: out[k] = [round(h[n], 1) if k == "pos" else int(h[n]), round(a[n], 1) if k == "pos" else int(a[n])]
    return out if ("sot" in out or "sh" in out) else None


def _get(url, timeout=8):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (BULUTOXX; canli)", "Accept": "application/json"}), timeout=timeout).read().decode("utf-8"))


def espn_live(budget=40):
    """Takip edilen liglerin ESPN skor tablosundaki oynanan maçlar + istatistikleri. Ağ yoksa boş liste (sessiz)."""
    import time
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.time(); out = []

    def one(slug):
        if time.time() - t0 > budget: return []
        try: j = _get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard")
        except Exception: return None
        r = []
        for ev in j.get("events") or []:
            c = (ev.get("competitions") or [{}])[0]; st = ((ev.get("status") or {}).get("type") or {}).get("state")
            if st != "in": continue
            cs = c.get("competitors") or []
            H = next((x for x in cs if x.get("homeAway") == "home"), None); A = next((x for x in cs if x.get("homeAway") == "away"), None)
            if not H or not A: continue
            s = comp_stats(H, A)
            r.append({"e": str(ev.get("id")), "lg": slug, "h": (H.get("team") or {}).get("displayName", ""), "a": (A.get("team") or {}).get("displayName", ""), "st": s})
        return r

    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(one, ESPN.values()))
    if all(x is None for x in res): return None          # ağ yok / erişim yok
    for x in res: out += x or []
    return out
