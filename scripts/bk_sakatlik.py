#!/usr/bin/env python3
"""🏀🩹 Basket sakatlık raporu — dakika ağırlıklı kayıp (yol haritası YH-16, GÖLGE).

ESPN herkese açık sakatlık listesi (NBA / WNBA) → "oynamaz / şüpheli" oyuncular; oyuncunun bu (ya da önceki) sezon maç başı
dakika ve sayı ortalaması × durum ağırlığı → takım kaybı:
  dk = Σ w · min(dakika, 48) / 240      takımın oynanan dakikalarından eksik payı (0…1)
  pt = Σ w · sayı                        eksik oyuncuların maç başı sayı toplamı
Durum ağırlığı: Out 1 · Doubtful 0,75 · Questionable / Day-To-Day 0,5 · Probable 0,1.

Depoya yalnız TÜRETİLMİŞ takım değerleri yazılır (data/bk_sakatlik.json → "takim"); oyuncu adı / ham yanıt yazılmaz,
oyuncu ortalamaları yalnız iş akışı önbelleğinde (.bk_sakatlik_onbellek/, actions/cache) durur (futbol kadro.py ilkesi).

Gölge kaydı (scripts/basket.py lock_and_grade): kilitli kayıt DEĞİŞMEZ; maç başlayana dek e["skg"] = {x: [dk_fark, pt_fark],
d: önsel Δ, ts} tazelenir (skg0 = ilk görüntü). x ev lehine pozitiftir (dep kaybı − ev kaybı). Ölçüm maç öncesi son
görüntüyle; maç başladıktan sonra yazılmaz (sızıntı yok). Önsel Δfark = ONSEL_C · pt_fark (yedek oyuncu kaybın bir kısmını
karşılar) yalnız gölge LL raporu içindir; asıl katsayı kapı aşamasında geçmiş artıklardan öğrenilir.
Kapı (YH-16): ≥ 300 sonuçlanmış maç ve ≥ 80 sinyalli maç birikince tazeveri tipi kapı + SK. O zamana dek üretime etkisi yok.
"""
import gzip, json, os, re, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CIKTI = os.path.join(DATA, "bk_sakatlik.json")
ONBELLEK = os.path.join(ROOT, ".bk_sakatlik_onbellek")
LIG = {"nba": "nba", "wnba": "wnba"}
AGIRLIK = {"out": 1.0, "doubtful": 0.75, "questionable": 0.5, "day-to-day": 0.5, "probable": 0.1}
ONSEL_C = 0.5
OYUNCU_TTL = 20 * 3600       # oyuncu ortalaması önbellek ömrü
EN_COK_ISTEK = 160           # çalışma başına en çok oyuncu isteği
TAZE_SAAT = 3                # basket.py yalnız bu kadar taze takım sinyalini kullanır
UA = "Mozilla/5.0 (OXXai; +https://bulutoxx.github.io)"


def fetch(url, tries=2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=25) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
                return json.loads(b.decode("utf-8"))
        except Exception as e:
            last = e; time.sleep(1.0 * (i + 1))
    raise last


def agirlik(durum):
    s = str(durum or "").strip().lower()
    for k, w in AGIRLIK.items():
        if k in s: return w
    return 0.0


def _oyuncu_id(i):
    a = i.get("athlete") or {}
    if a.get("id"): return str(a["id"])
    for l in a.get("links") or []:
        m = re.search(r"/id/(\d+)", str(l.get("href", "")))
        if m: return m.group(1)
    return None


def raporu_ayristir(j):
    """ESPN /injuries yanıtı → {takım adı: [(oyuncu_id, ağırlık), ...]} (ağırlığı 0 olanlar atlanır)."""
    out = {}
    for t in (j or {}).get("injuries") or []:
        ad = t.get("displayName") or (t.get("team") or {}).get("displayName")
        if not ad: continue
        L = out.setdefault(ad, [])
        for i in t.get("injuries") or []:
            w = agirlik(i.get("status") or ((i.get("type") or {}).get("description")))
            pid = _oyuncu_id(i)
            if w > 0 and pid: L.append((pid, w))
    return out


def _sira(labels, names, *anahtar):
    for k in anahtar:
        for L in (labels or [], names or []):
            if k in L: return L.index(k)
    return None


def ortalama_ayristir(j):
    """ESPN oyuncu istatistik yanıtı → (dakika, sayı, maç) ya da None. Önce maç sayısı ≥ 5 olan en son sezon, yoksa en son satır."""
    adaylar = []
    for c in (j or {}).get("categories") or []:
        if str(c.get("name", "")).lower() not in ("averages", "avg", "") and "aver" not in str(c.get("displayName", "")).lower(): continue
        lb, nm = c.get("labels") or [], c.get("names") or []
        im, ip, ig = _sira(lb, nm, "MIN", "avgMinutes"), _sira(lb, nm, "PTS", "avgPoints"), _sira(lb, nm, "GP", "gamesPlayed")
        if im is None or ip is None: continue
        for s in c.get("statistics") or []:
            st = s.get("stats") or []
            yil = (s.get("season") or {}).get("year") or 0
            adaylar.append((yil, st, im, ip, ig))
    st0 = (j or {}).get("statistics") or {}
    if not adaylar and isinstance(st0, dict):
        lb, nm = st0.get("labels") or [], st0.get("names") or []
        im, ip, ig = _sira(lb, nm, "MIN", "avgMinutes"), _sira(lb, nm, "PTS", "avgPoints"), _sira(lb, nm, "GP", "gamesPlayed")
        if im is not None and ip is not None:
            for k, s in enumerate(st0.get("splits") or []):
                if "regular" in str(s.get("displayName", "")).lower() or k == 0:
                    adaylar.append((9999 - k, s.get("stats") or [], im, ip, ig))

    def sayi(v):
        try: return float(str(v).replace(",", "."))
        except Exception: return None
    satir = []
    for yil, st, im, ip, ig in adaylar:
        if max(im, ip) >= len(st): continue
        m, p = sayi(st[im]), sayi(st[ip]); g = sayi(st[ig]) if (ig is not None and ig < len(st)) else None
        if m is None or p is None: continue
        satir.append((yil, m, p, g))
    if not satir: return None
    satir.sort(key=lambda r: r[0], reverse=True)
    for yil, m, p, g in satir:
        if g is None or g >= 5: return (m, p, g)
    return satir[0][1:]


def _onbellek_oku():
    try: return json.load(open(os.path.join(ONBELLEK, "oyuncu.json"), encoding="utf-8"))
    except Exception: return {}


def _onbellek_yaz(C):
    os.makedirs(ONBELLEK, exist_ok=True)
    tmp = os.path.join(ONBELLEK, "oyuncu.json.tmp")
    json.dump(C, open(tmp, "w", encoding="utf-8")); os.replace(tmp, os.path.join(ONBELLEK, "oyuncu.json"))


def oyuncu_ortalama(lg, pid, C, sayac):
    k = f"{lg}:{pid}"; v = C.get(k); now = time.time()
    if v and now - v.get("t", 0) < OYUNCU_TTL: return v.get("o")
    if sayac[0] >= EN_COK_ISTEK: return v.get("o") if v else None
    sayac[0] += 1
    o = None
    for url in (f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/{lg}/athletes/{pid}/stats",
                f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/{lg}/athletes/{pid}/overview"):
        try:
            o = ortalama_ayristir(fetch(url))
        except Exception:
            o = None
        if o: break
    C[k] = {"t": now, "o": list(o) if o else None}
    time.sleep(0.15)
    return C[k]["o"]


def takim_kaybi(L, ort):
    """L: [(pid, w)], ort: pid → (dakika, sayı, maç) | None. Dönüş: (dk payı, sayı, sayılan oyuncu, bilinmeyen oyuncu)."""
    dk = pt = 0.0; n = bil = 0
    for pid, w in L:
        o = ort.get(pid)
        if not o: bil += 1; continue
        dk += w * min(max(o[0], 0.0), 48.0) / 240.0; pt += w * max(o[1], 0.0); n += 1
    return round(min(dk, 1.0), 4), round(pt, 2), n, bil


def oku():
    try: return json.load(open(CIKTI, encoding="utf-8"))
    except Exception: return {}


def kaydet(A):
    tmp = CIKTI + ".tmp"
    json.dump(A, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1, allow_nan=False); os.replace(tmp, CIKTI)


def topla():
    A = oku(); C = _onbellek_oku(); sayac = [0]; takim = {}; tani = {}
    for lg, slug in LIG.items():
        try:
            R = raporu_ayristir(fetch(f"https://site.api.espn.com/apis/site/v2/sports/basketball/{slug}/injuries"))
        except Exception as e:
            tani[lg] = {"hata": e.__class__.__name__}; continue
        ort = {}
        for L in R.values():
            for pid, _ in L:
                if pid not in ort: ort[pid] = oyuncu_ortalama(slug, pid, C, sayac)
        for ad, L in R.items():
            dk, pt, n, bil = takim_kaybi(L, ort)
            takim[ad] = {"lg": lg, "dk": dk, "pt": pt, "n": n, "bil": bil}
        tani[lg] = {"takim": len(R), "oyuncu": sum(len(L) for L in R.values()), "ortalama_bulunan": sum(1 for v in ort.values() if v)}
    _onbellek_yaz(C)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    if takim or not A.get("takim"):
        A["takim"] = takim; A["ts"] = now
    A["tani"] = dict(tani, istek=sayac[0], guncelleme=now)
    A.setdefault("aciklama", "YH-16 gölge: ESPN sakatlık listesi → takım başına dakika payı (dk) ve maç başı sayı (pt) kaybı; "
                 "yalnız türetilmiş takım değerleri. Kilitli tahmine etkisi yok; kapı ≥ 300 maç / ≥ 80 sinyalli maçta.")
    A["onsel_c"] = ONSEL_C
    kaydet(A)
    print(f"🩹 basket sakatlık: {json.dumps(A['tani'], ensure_ascii=False)}", flush=True)
    return A


# ------------------------------------------------------------------ basket.py yardımcıları
def sinyal_hazir(A=None, simdi=None):
    """Taze takım sinyali (≤ TAZE_SAAT saat) yoksa {} döner."""
    A = A if A is not None else oku(); simdi = simdi or datetime.now(timezone.utc)
    try:
        ts = datetime.strptime(A.get("ts", ""), "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    except Exception:
        return {}
    if simdi - ts > timedelta(hours=TAZE_SAAT): return {}
    return {"ts": A["ts"], "takim": A.get("takim") or {}}


def mac_sinyali(S, e):
    """S: sinyal_hazir() çıktısı; e: kilitli kayıt (lg, h, a). Dönüş: {x, d, ts} ya da None."""
    if not S or e.get("lg") not in LIG: return None
    T = S["takim"]; z = {"dk": 0.0, "pt": 0.0}
    h, a = T.get(e["h"], z), T.get(e["a"], z)
    x = [round(a["dk"] - h["dk"], 4), round(a["pt"] - h["pt"], 2)]
    return {"x": x, "d": round(ONSEL_C * x[1], 2), "ts": S["ts"]}


def golge_ozet(plog, ligler):
    """Sonuçlanmış maçlarda önsel Δ ile LL farkı (düzeltmeli − düzeltmesiz); son maç öncesi görüntü (skg)."""
    import math
    def phi(v): return 0.5 * (1 + math.erf(v / math.sqrt(2)))
    out = {}
    for e in plog:
        s = e.get("skg")
        if e.get("lg") not in LIG or not e.get("r") or not s or e["r"][0] == e["r"][1]: continue
        sm = (ligler.get(e["lg"]) or {}).get("sm") or 12.0; y = 1 if e["r"][0] > e["r"][1] else 0
        m = e["ph"] - e["pa"]
        p0 = min(max(phi(m / sm), 1e-6), 1 - 1e-6); p1 = min(max(phi((m + s["d"]) / sm), 1e-6), 1 - 1e-6)
        l = lambda p: -(y * math.log(p) + (1 - y) * math.log(1 - p))
        o = out.setdefault(e["lg"], [0, 0, 0.0]); o[0] += 1; o[1] += 1 if any(abs(v) > 1e-9 for v in s["x"]) else 0; o[2] += l(p1) - l(p0)
    return {lg: {"n": n, "sinyalli": k, "d_ll_onsel": round(t / n, 5)} for lg, (n, k, t) in out.items()}


if __name__ == "__main__":
    try:
        topla()
    except Exception as e:
        print("basket sakatlık toplanamadı:", e.__class__.__name__, str(e)[:160], flush=True); sys.exit(0)
