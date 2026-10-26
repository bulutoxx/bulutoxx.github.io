#!/usr/bin/env python3
"""🎟️ OXX kupon robotu (oxx1, 2026-10-26) — OXX'un kendi kuponlarını maçtan ÖNCE kurar, KİLİTLER, sonuçla puanlar.

Hobi amaçlı ölçüm: para tutarı, bahis bağlantısı yok. Kupon = aynı gün farklı maçlardan seçilen tahminler;
"tutma olasılığı" = bacak olasılıklarının çarpımı (farklı maçlar bağımsız varsayılır).

Akış (her çalıştırmada, idempotent):
  1) Kilit: günün (İstanbul saatiyle) ilk çalıştırmasında, henüz BAŞLAMAMIŞ maçlardan strateji kurallarıyla kuponlar kurulur;
     kilit zaman damgası + motor/ayar sürümü yazılır. Kilitli bölüm bir daha DEĞİŞMEZ (yalnız sonuç alanları dolar).
  2) Puan: futbol arşivden (data/archive, iddaa sonuçları; yoksa season.json / predlog), basket bk_predlog/bk_games'ten,
     at data/at/canli/<gün>.json sonuçlarından ve 6'lı dosyasından (lab/at/altili.py) puanlanır.
  3) Karne: data/oxx_karne.json (strateji başına kupon/bacak isabeti, beklenen, kalibrasyon, son 7/30 gün, seri).

Yazarlar (tek yazar kuralı, git çakışması olmasın):
  data/oxx_kupon/<gün>.json      futbol + basket (update.yml, saatlik) — at bölümü at dosyasından kopyalanır (salt okunur)
  data/oxx_kupon/at/<gün>.json   at (at-canli.yml, 30 dk)
  data/oxx_karne.json            update.yml (saatlik)
Stratejilerin ayarları data/oxx_ayar.json'dan (öğrenme döngüsü lab/oxx_ogren.py yazar); dosya yoksa VARSAYILAN.
Şema: lab/OXX_KUPON.md.

Kullanım:
  python scripts/oxx_kupon.py                 # futbol + basket kilit/puan + karne (update.yml)
  python scripts/oxx_kupon.py --at            # at kilit/puan (at-canli.yml)
  python scripts/oxx_kupon.py --geriye 30     # son 30 gün için geriye dönük (yalnız o günden önce bilinenle) kupon + karne
  --simdi 2026-10-26T09:00:00+00:00           # saati sabitle (deneme)
"""
import argparse, collections, copy, glob, itertools, json, math, os, sys, time
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BURA)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, BURA)
KDIR = os.path.join(DATA, "oxx_kupon")
ATDIR = os.path.join(KDIR, "at")
KARNE = os.path.join(DATA, "oxx_karne.json")
AYAR = os.path.join(DATA, "oxx_ayar.json")
TR, UK = ZoneInfo("Europe/Istanbul"), ZoneInfo("Europe/London")
OXX_V = "oxx1"
UYARI = "Hobi amaçlı olasılık ölçümü; garanti değildir, para tutarı yoktur · 18+"

# ------------------------------------------------------------------ stratejiler (kimlikler KARARLIDIR; arayüz bunlarla eşler)
STRATEJI = {
    "fb_altin": ("futbol", "Altın kupon",
                 "Uygulamadaki öneri (MS 1/X/2, 2,5 A/Ü; oranı olan seçenekler içinde OXX'un en yüksek olasılığı). Olasılık ≥ p_min, "
                 "oran omin–omax, günde en fazla 'gunde' maç; hepsi tek kuponda."),
    "fb_70": ("futbol", "%70+ kupon",
              "Olasılığı ≥ p_bacak ve oranı ≥ omin öneriler (en olası 'aday' tanesi) içinden, birlikte tutma olasılığı ≥ p_kupon kalan "
              "2–en_cok maçlık kombinasyonların toplam oranı en yüksek olanı (uygulamadaki Power Now %70+ kuponuyla aynı kural)."),
    "fb_3lu": ("futbol", "3 maçlık en olası",
               "Günün en yüksek olasılıklı 3 önerisi (olasılık ≥ p_min, oran ≥ omin; farklı maçlar)."),
    "fb_deger": ("futbol", "Değerli kupon",
                 "Her maçta oranı olan seçenekler (MS 1/X/2, 2,5 A/Ü) içinde OXX olasılığı × oran en yüksek seçenek (olasılık ≥ p_min); "
                 "değer katsayısı en yüksek 'bacak' maç."),
    "fb_guvenli": ("futbol", "Güvenli kupon (yeni pazarlar)",
                   "Pazar karnesinde oneriye_uygun=true olan yeni pazarlar (Çifte şans, 1,5/3,5 A/Ü, KG, İY/2Y, birleşik…) içinde her maçın "
                   "en olası seçeneği; olasılık ≥ p_min ve iddaa oranı (yoksa adil oran 1/p) ≥ adil_min; en olası 'bacak' maç."),
    "bk_en_olasi": ("basket", "Basket: günün en olası seçimleri",
                    "Kilitli basket tahmininden kazanma olasılığı Φ(fark/σ·ölçek); olasılığı ≥ p_min en olası 3 maç "
                    "(3.'nün olasılığı p3_min altındaysa 2 maç)."),
    "at_altin": ("at", "Altın atlar",
                 "Gece robotunun Altın kuralı (data/at/model.json altin_kural): kazanma olasılığı ≥ p_min ve ikinciden fark ≥ fark_min; "
                 "günde en fazla gunluk_max at; her at ayrı ganyan kuponu."),
    "at_sirali_ikili": ("at", "OXX sıralı ikili",
                        "Her koşuda (en az 4 at) indirimli Harville ile en olası sıralı ilk iki (1. ve 2. at, sırasıyla)."),
    "at_ikili": ("at", "OXX ikili",
                 "Her koşuda (en az 7 at) en olası sırasız ilk iki."),
    "at_cifte": ("at", "OXX çifte",
                 "Her hipodromda ardışık iki koşunun favorilerinin birlikte kazanma olasılığı en yüksek çifti (tek kombinasyon)."),
    "at_altili_dar": ("at", "6'lı Dar (64)", "lab/at/altili.py dar seviye kuponu (ilk ayaktan önce kilitli)."),
    "at_altili_orta": ("at", "6'lı Orta (192)", "lab/at/altili.py orta seviye kuponu (ilk ayaktan önce kilitli)."),
    "at_altili_genis": ("at", "6'lı Geniş (576)", "lab/at/altili.py geniş seviye kuponu (ilk ayaktan önce kilitli)."),
}
VARSAYILAN = {
    "fb_altin": {"p_min": 0.78, "omin": 1.15, "omax": 2.00, "gunde": 3},
    "fb_70": {"p_bacak": 0.70, "p_kupon": 0.70, "omin": 1.05, "en_cok": 4, "aday": 12},
    "fb_3lu": {"p_min": 0.58, "omin": 1.15, "bacak": 3},
    "fb_deger": {"p_min": 0.40, "bacak": 2},
    "fb_guvenli": {"p_min": 0.80, "adil_min": 1.15, "bacak": 3},
    "bk_en_olasi": {"p_min": 0.60, "p3_min": 0.70, "olcek": 1.0},
    "at_sirali_ikili": {"en_az_at": 4, "tau": 1.0},
    "at_ikili": {"en_az_at": 7, "tau": 1.0},
    "at_cifte": {"tau": 1.0},
    "duzeltme": {"pazar": {}},     # öğrenme döngüsü: kod -> {"a","b"} (OXX kuponlarında bacak olasılığı σ(a + b·logit p))
    "lig_dis": [],                 # öğrenme döngüsü: OXX kuponlarına alınmayan ligler
}
ESKI = ["1", "X", "2", "U25", "A25"]
MIN_FB_MAC, MIN_BK_MAC = 10, 2


def jl(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d


def jw(p, o, indent=1):
    """indent=None: sıkışık (gün dosyaları, karne — depo boyutu); küçük durum dosyaları okunur biçimde."""
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if indent is None: json.dump(o, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        else: json.dump(o, f, ensure_ascii=False, indent=indent, allow_nan=False)
    os.replace(tmp, p)


def jw_degisince(p, o, haric=("guncelleme_utc",), indent=None):
    eski = jl(p)
    yeni = json.loads(json.dumps(o, ensure_ascii=False))
    if eski is not None and {k: v for k, v in eski.items() if k not in haric} == {k: v for k, v in yeni.items() if k not in haric}:
        return False
    jw(p, o, indent)
    return True


def r4(x):
    return None if x is None else round(float(x), 4)


def ayar_yukle(ham=None):
    """data/oxx_ayar.json (öğrenme döngüsü) + VARSAYILAN; eksik anahtar varsayılandan gelir."""
    A = copy.deepcopy(VARSAYILAN)
    J = ham if ham is not None else (jl(AYAR, {}) or {})
    for k, v in (J.get("params") or {}).items():
        if isinstance(v, dict) and isinstance(A.get(k), dict):
            A[k].update(v)
        else:
            A[k] = v
    A["_surum"] = J.get("surum", "varsayilan")
    return A


def zaman(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(t):
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def tsi(t):
    return t.astimezone(TR).strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------------ futbol: maç kaydı ve olasılık
def _sig(z): return 1 / (1 + math.exp(-z))


def _logit(p): p = min(max(p, 1e-6), 1 - 1e-6); return math.log(p / (1 - p))


def duzelt(pz, A):
    """Öğrenme döngüsünün kabul ettiği pazar düzeltmeleri (yalnız OXX kuponlarında; uygulamanın gösterdiği olasılığa dokunmaz)."""
    D = (A.get("duzeltme") or {}).get("pazar") or {}
    if not D:
        return pz
    import pazar as PZM
    q = dict(pz)
    for c, ab in D.items():
        if c in q:
            q[c] = _sig(ab["a"] + ab["b"] * _logit(q[c]))
            es = PZM.TUMLEYEN.get(c) or next((k for k, v in PZM.TUMLEYEN.items() if v == c), None)
            if es and es in q:
                q[es] = 1 - q[c]
    if any(c in D for c in "1X2"):
        s = q["1"] + q["X"] + q["2"]
        for c in "1X2": q[c] /= s
    return q


def fb_mac(key, lg, lig, h, a, bas, pz, odds, ou, po=None, iid=None, A=None):
    """Strateji fonksiyonlarının okuduğu tek biçim (canlı fikstür, geçmiş sezon ve arşiv aynı yoldan)."""
    return {"mac": key, "lg": lg, "lig": lig, "h": h, "a": a, "bas_utc": bas, "iid": iid,
            "pz": duzelt(pz, A or VARSAYILAN), "odds": odds if odds and len(odds) == 3 else None,
            "ou": ou if ou and len(ou) == 2 and ou[0] and ou[1] else None, "po": po or {}}


def _ad(c):
    import pazar as PZM
    return PZM.NAME.get(c, c)


def _oran(m, c):
    if c in ("1", "X", "2") and m["odds"]: return m["odds"]["1X2".index(c)]
    if c == "U25" and m["ou"]: return m["ou"][0]
    if c == "A25" and m["ou"]: return m["ou"][1]
    return None


def rec(m):
    """Uygulamadaki recOf: oranı olan seçenekler (MS 1/X/2, 2,5 A/Ü) içinde en yüksek olasılık."""
    c = [k for k in ESKI if _oran(m, k) and m["pz"].get(k) is not None]
    if not c: return None
    k = max(c, key=lambda k: m["pz"][k])
    return {"kod": k, "p": float(m["pz"][k]), "oran": _oran(m, k)}


def _bacak(m, kod, p, oran):
    return {"mac": m["mac"], "lg": m["lg"], "lig": m["lig"], "h": m["h"], "a": m["a"], "bas_utc": m["bas_utc"], "iid": m["iid"],
            "kod": kod, "secim": _ad(kod), "p": r4(p), "oran": oran}


def _kupon(sid, bacaklar):
    p = math.prod(b["p"] for b in bacaklar)
    o = math.prod(b["oran"] for b in bacaklar) if all(b.get("oran") for b in bacaklar) else None
    return {"strateji": sid, "bacaklar": bacaklar, "p": r4(p), "oran": round(o, 2) if o else None}


def fb_kuponlar(maclar, A, uygun=(), yalniz=None):
    """Bir günün maçları -> {strateji: [kupon]}. yalniz: yalnız bu stratejiler (öğrenme sınaması)."""
    L = [m for m in maclar if m["lg"] not in set(A.get("lig_dis") or [])]
    R = [(m, rec(m)) for m in L]
    R = [(m, r) for m, r in R if r]
    out = {}
    want = lambda s: yalniz is None or s in yalniz
    if want("fb_altin"):
        a = A["fb_altin"]
        c = sorted([(m, r) for m, r in R if r["p"] >= a["p_min"] - 1e-12 and a["omin"] <= r["oran"] <= a["omax"]], key=lambda x: -x[1]["p"])[:int(a["gunde"])]
        out["fb_altin"] = [_kupon("fb_altin", [_bacak(m, r["kod"], r["p"], r["oran"]) for m, r in c])] if c else []
    if want("fb_70"):
        a = A["fb_70"]
        c = sorted([(m, r) for m, r in R if r["p"] >= a["p_bacak"] - 1e-12 and r["oran"] >= a["omin"]], key=lambda x: -x[1]["p"])[:int(a["aday"])]
        best = None
        for n in range(2, int(a["en_cok"]) + 1):
            for comb in itertools.combinations(c, n):
                jp = math.prod(r["p"] for _, r in comb)
                if jp < a["p_kupon"] - 1e-12: continue
                to = math.prod(r["oran"] for _, r in comb)
                if best is None or (to, jp) > (best[0], best[1]): best = (to, jp, comb)
        out["fb_70"] = [_kupon("fb_70", [_bacak(m, r["kod"], r["p"], r["oran"]) for m, r in best[2]])] if best else []
    if want("fb_3lu"):
        a = A["fb_3lu"]
        c = sorted([(m, r) for m, r in R if r["p"] >= a["p_min"] - 1e-12 and r["oran"] >= a["omin"]], key=lambda x: -x[1]["p"])[:int(a["bacak"])]
        out["fb_3lu"] = [_kupon("fb_3lu", [_bacak(m, r["kod"], r["p"], r["oran"]) for m, r in c])] if len(c) == int(a["bacak"]) else []
    if want("fb_deger"):
        a = A["fb_deger"]; c = []
        for m in L:
            op = [(k, m["pz"][k], _oran(m, k)) for k in ESKI if _oran(m, k) and m["pz"].get(k, 0) >= a["p_min"] - 1e-12]
            if op:
                k, p, o = max(op, key=lambda x: x[1] * x[2]); c.append((m, k, p, o))
        c = sorted(c, key=lambda x: -x[2] * x[3])[:int(a["bacak"])]
        if len(c) == int(a["bacak"]):
            K = _kupon("fb_deger", [_bacak(m, k, p, o) for m, k, p, o in c])
            for b, (_, _, p, o) in zip(K["bacaklar"], c): b["deger"] = round(p * o, 3)
            out["fb_deger"] = [K]
        else:
            out["fb_deger"] = []
    if want("fb_guvenli"):
        a = A["fb_guvenli"]; c = []
        for m in L:
            op = []
            for k in uygun:
                p = m["pz"].get(k)
                if p is None or p < a["p_min"] - 1e-12: continue
                o = m["po"].get(k)
                if (o and o >= a["adil_min"]) or (not o and 1 / max(p, 1e-9) >= a["adil_min"]): op.append((k, p, o))
            if op:
                k, p, o = max(op, key=lambda x: x[1]); c.append((m, k, p, o))
        c = sorted(c, key=lambda x: -x[2])[:int(a["bacak"])]
        out["fb_guvenli"] = [_kupon("fb_guvenli", [_bacak(m, k, p, o) for m, k, p, o in c])] if len(c) == int(a["bacak"]) else []
    return out


def uygun_pazarlar(PK):
    return sorted(c for c, v in ((PK or {}).get("pazarlar") or {}).items() if v.get("oneriye_uygun") and c not in ESKI)


def kickoff(f):
    try:
        hh, mm = (f.get("t") or "23:59").split(":")[:2]
        return datetime.fromisoformat(f["d"]).replace(hour=int(hh), minute=int(mm), tzinfo=UK).astimezone(timezone.utc)
    except Exception:
        return datetime.fromisoformat(f["d"] + "T23:59:00+00:00")


def fb_canli_maclar(gun, simdi, A):
    """fixtures.json: kickoff İstanbul günü == gun ve henüz başlamamış (5 dk pay), pazar olasılığı (pz) olan maçlar."""
    import pazar as PZM
    out = []
    for f in jl(os.path.join(DATA, "fixtures.json"), []) or []:
        if not f.get("pz"): continue
        ko = kickoff(f)
        if ko.astimezone(TR).date().isoformat() != gun or ko <= simdi + timedelta(minutes=5): continue
        key = f"{f['lg']}|{f['d']}|{f['h']}|{f['a']}"
        out.append(fb_mac(key, f["lg"], f.get("cn") or f["lg"], f["h"], f["a"], iso(ko), PZM.full(f["pz"]), f.get("odds"), f.get("ou"), f.get("po"), f.get("iid"), A))
    return out


# ------------------------------------------------------------------ futbol: geçmiş (geriye dönük ve öğrenme sınaması)
def gecmis_pz(season, P, PK, d0=None, d1=None, aylik=True, log=print):
    """season.json oranlı maçları için pazar olasılıkları (uygulamanın sunduğu yol). Kalibratörler (pazar karnesinin kabul
    ettikleri) YALNIZ o aydan önceki maçlarla öğrenilir; lig İY payı yalnız önceki maçlardan (pazar.h1_forward). Dönüş:
    (satırlar, {kod: dizi}) — satırlar d0 ≤ d < d1."""
    import pazar as PZM, update as U
    rows = PZM.hist_rows(season)
    if not rows: return [], {}
    rho = P.get("rho", -0.06)
    lam = np.zeros((len(rows), 2))
    for s_ in range(0, len(rows), 3000):
        ch = rows[s_:s_ + 3000]; lam[s_:s_ + len(ch)] = U.ui_market_lam([r["odds"] for r in ch], [r["ou"] for r in ch], rho)
    s = PZM.h1_forward(rows, P.get("h1", .4442))
    M = PZM.raw_marginals(lam[:, 0], lam[:, 1], s, P)
    Y = PZM.labels(rows)
    acc = set(((PK or {}).get("kalibrator") or {}).keys())
    months = np.array([r["d"][:7] for r in rows])
    sel = np.array([(d0 is None or r["d"] >= d0) and (d1 is None or r["d"] < d1) for r in rows])
    out = {c: np.full(len(rows), np.nan) for c in PZM.CODES}
    tm = sorted(set(months[sel]))
    for m_ in (tm if aylik else tm[:1]):
        ix = np.where(sel & ((months == m_) if aylik else sel))[0]
        cut = m_ if aylik else (d0 or "0000")[:7]
        kal = {k: v for k, v in PZM.fit_cals(M, Y, months < cut).items() if k in acc} if acc else {}
        Pm = PZM.apply_cal({k: v[ix] for k, v in M.items()}, P, kal)
        for c in PZM.CODES: out[c][ix] = Pm[c]
    idx = np.where(sel)[0]
    ad = hist_rows_adli(season)
    ad = ad if len(ad) == len(rows) else [{}] * len(rows)
    R = [dict(rows[t], _i=int(t), h=ad[t].get("h", ""), a=ad[t].get("a", "")) for t in idx]
    return R, {c: out[c][idx] for c in PZM.CODES}


def gecmis_gunler(R, PZ, A, adlar=None):
    """gecmis_pz çıktısı -> {gün: [maç]} (+ sonuç sözlüğü {maç: (ft, ht)}). adlar: {lig kodu: lig adı}."""
    gun, sonuc = collections.defaultdict(list), {}
    adlar = adlar or {}
    for t, r in enumerate(R):
        key = f"{r['lg']}|{r['d']}|{r.get('h', t)}|{r.get('a', '')}"
        pz = {c: float(PZ[c][t]) for c in PZ}
        gun[r["d"]].append(fb_mac(key, r["lg"], adlar.get(r["lg"], r["lg"]), r.get("h", ""), r.get("a", ""), r["d"] + "T12:00Z", pz, r["odds"], r["ou"], None, None, A))
        sonuc[key] = (r["ft"], r["ht"])
    return gun, sonuc


def hist_rows_adli(season):
    """pazar.hist_rows ile aynı süzgeç, takım adlarıyla (karne/arayüz için)."""
    rows = []
    for lg, d in season.items():
        if d.get("cup") or d.get("src") == "espn": continue
        for m in d.get("matches", []):
            ht = m.get("ht")
            if m.get("odds") and m.get("ou") and ht and len(ht) == 2 and ht[0] is not None and m["ft"][0] >= ht[0] and m["ft"][1] >= ht[1]:
                rows.append({"lg": lg, "d": m["d"], "h": m["h"], "a": m["a"]})
    rows.sort(key=lambda r: r["d"])
    return rows


def arsiv_maclari(gun, P, PK, A):
    """data/archive/<gün>.json (iddaa bülteni; kilitli oran + sonuç) -> maç listesi ve sonuçlar. Olasılık yalnız o maçın
    maç öncesi oranından (uygulamanın sunduğu yol, genel İY payı, pazar karnesinin kalibratörleri)."""
    import pazar as PZM, update as U, arsiv
    f = arsiv.gunler(DATA).get(gun)
    recs = jl(f, {}) if f else {}
    L = [(k, r) for k, r in recs.items() if r.get("ms") and len(r["ms"]) == 3 and r.get("hs") is not None]
    if not L: return [], {}
    rho = P.get("rho", -0.06)
    lam = U.ui_market_lam([r["ms"] for _, r in L], [r["ou"] if r.get("ou") and len(r["ou"]) == 2 else None for _, r in L], rho)
    M = PZM.raw_marginals(lam[:, 0], lam[:, 1], np.full(len(L), P.get("h1", .4442)), P)
    PZ = PZM.apply_cal(M, P, (PK or {}).get("kalibrator") or {})
    out, sonuc = [], {}
    for t, (k, r) in enumerate(L):
        po = {"1": r["ms"][0], "X": r["ms"][1], "2": r["ms"][2]}
        if r.get("ou"): po.update({"U25": r["ou"][0], "A25": r["ou"][1]})
        if r.get("kgo") and len(r["kgo"]) == 2: po.update({"KGV": r["kgo"][0], "KGY": r["kgo"][1]})
        key = f"iddaa|{k}"
        bas = iso(datetime.fromtimestamp(r["ts"], timezone.utc)) if r.get("ts") else gun + "T12:00Z"
        out.append(fb_mac(key, "iddaa:" + str(r.get("c") or "?"), r.get("c") or "", r.get("h", ""), r.get("a", ""), bas,
                          {c: float(PZ[c][t]) for c in PZ}, r["ms"], r.get("ou"), po, int(k) if str(k).isdigit() else None, A))
        ht = [r["h1"], r["a1"]] if r.get("h1") is not None and r.get("a1") is not None else None
        sonuc[key] = ([r["hs"], r["as"]], ht)
    return out, sonuc


# ------------------------------------------------------------------ futbol: sonuç bulma ve puanlama
class FbSonuc:
    def __init__(self):
        import arsiv
        self.gun = arsiv.gunler(DATA); self._a = {}
        S = jl(os.path.join(DATA, "season.json"), {}) or {}
        self.idx = collections.defaultdict(list)
        for lg, d in S.items():
            for m in d.get("matches", []):
                self.idx[(lg, m["h"], m["a"])].append(m)
        self.pl = {e["id"]: e for e in (jl(os.path.join(DATA, "predlog.json"), []) or []) if e.get("r")}

    def _arsiv(self, d):
        if d not in self._a:
            self._a[d] = jl(self.gun[d], {}) if d in self.gun else {}
        return self._a[d]

    def bul(self, b):
        """(ft, ht) ya da None."""
        bas = zaman(b["bas_utc"]); d = bas.astimezone(TR).date()
        if b.get("iid"):
            for k in (0, -1, 1):
                r = self._arsiv((d + timedelta(days=k)).isoformat()).get(str(b["iid"]))
                if r and r.get("hs") is not None:
                    return [r["hs"], r["as"]], ([r["h1"], r["a1"]] if r.get("h1") is not None and r.get("a1") is not None else None)
        if b["mac"].startswith("iddaa|"):
            k = b["mac"].split("|", 1)[1]
            for j in (0, -1, 1):
                r = self._arsiv((d + timedelta(days=j)).isoformat()).get(k)
                if r and r.get("hs") is not None:
                    return [r["hs"], r["as"]], ([r["h1"], r["a1"]] if r.get("h1") is not None and r.get("a1") is not None else None)
            return None
        for m in self.idx.get((b["lg"], b["h"], b["a"]), []):
            if abs((date.fromisoformat(m["d"]) - d).days) <= 1 and m.get("ft"):
                ht = m.get("ht") if m.get("ht") and len(m["ht"]) == 2 and m["ht"][0] is not None else None
                return m["ft"], ht
        e = self.pl.get(b["mac"])
        if e and isinstance(e.get("r"), list): return e["r"], e.get("rh")
        return None


def kupon_durum(K, simdi, gec_gun=4):
    """Bacak sonuçlarından kupon durumu: tuttu / tutmadi / bekliyor / gecersiz (sonuç bulunamadı, ertelendi)."""
    L = K["bacaklar"]
    if any(b.get("tuttu") is False for b in L): K["durum"], K["tuttu"] = "tutmadi", False
    elif all(b.get("tuttu") is True for b in L): K["durum"], K["tuttu"] = "tuttu", True
    else:
        eski = any(b.get("tuttu") is None and simdi - zaman(b["bas_utc"]) > timedelta(days=gec_gun) for b in L if b.get("bas_utc"))
        K["durum"], K["tuttu"] = ("gecersiz", None) if eski else ("bekliyor", None)
    return K


def fb_puanla(bolum, S, simdi):
    import pazar as PZM
    for K in bolum.get("kuponlar", []):
        for b in K["bacaklar"]:
            if b.get("tuttu") is not None: continue
            r = S.bul(b) if S else None
            if r:
                ft, ht = r; b["sonuc"] = f"{ft[0]}-{ft[1]}"
                if ht: b["iy"] = f"{ht[0]}-{ht[1]}"
                b["tuttu"] = PZM.outcome(b["kod"], ft, ht)
        kupon_durum(K, simdi)


# ------------------------------------------------------------------ basket
def _phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bk_kuponlar(maclar, A):
    a = A["bk_en_olasi"]
    c = sorted([m for m in maclar if m["p"] >= a["p_min"] - 1e-12], key=lambda m: -m["p"])
    if len(c) >= 3 and c[2]["p"] >= a["p3_min"] - 1e-12: c = c[:3]
    elif len(c) >= 2: c = c[:2]
    else: return {"bk_en_olasi": []}
    B = [{"mac": m["mac"], "lg": m["lg"], "lig": m["lig"], "h": m["h"], "a": m["a"], "bas_utc": m["bas_utc"], "kod": m["kod"],
          "secim": "MS 1 (ev)" if m["kod"] == "1" else "MS 2 (deplasman)", "p": r4(m["p"]), "oran": m.get("oran"),
          "tahmin": m.get("tahmin")} for m in c]
    return {"bk_en_olasi": [_kupon("bk_en_olasi", B)]}


def bk_mac(id_, lg, lig, h, a, bas, ph, pa, sm, olcek, io=None):
    p1 = _phi((ph - pa) / max(sm * olcek, 1e-6)); kod = "1" if p1 >= .5 else "2"
    o = (io[0] if kod == "1" else io[1]) if io and len(io) == 2 else None
    return {"mac": id_, "lg": lg, "lig": lig, "h": h, "a": a, "bas_utc": bas, "kod": kod, "p": max(p1, 1 - p1), "oran": o,
            "tahmin": f"{round(ph)}-{round(pa)}"}


def bk_canli_maclar(gun, simdi, A):
    BJ = jl(os.path.join(DATA, "basket.json"), {}) or {}
    FX = {f["id"]: f for f in BJ.get("fixtures", [])}
    LG = BJ.get("leagues", {})
    out = []
    for e in jl(os.path.join(DATA, "bk_predlog.json"), []) or []:
        f = FX.get(e["id"])
        if not f or e.get("r") or f.get("live") or e.get("ph") is None: continue
        bas = zaman(f["dt"])
        if bas.astimezone(TR).date().isoformat() != gun or bas <= simdi + timedelta(minutes=5): continue
        L = LG.get(e["lg"], {})
        out.append(bk_mac(e["id"], e["lg"], L.get("name", e["lg"]), e["h"], e["a"], iso(bas), e["ph"], e["pa"], L.get("sm") or 12.0,
                          A["bk_en_olasi"].get("olcek", 1.0), f.get("io")))
    return out


class BkSonuc:
    def __init__(self):
        self.r = {}
        for lg, st in (jl(os.path.join(DATA, "bk_games.json"), {}) or {}).items():
            for g in st.get("g", []): self.r[g["id"]] = [g["hs"], g["as_"]]
        for e in jl(os.path.join(DATA, "bk_predlog.json"), []) or []:
            if e.get("r"): self.r[e["id"]] = e["r"]

    def puanla(self, bolum, simdi):
        for K in bolum.get("kuponlar", []):
            for b in K["bacaklar"]:
                if b.get("tuttu") is not None: continue
                r = self.r.get(b["mac"])
                if r:
                    b["sonuc"] = f"{r[0]}-{r[1]}"; b["tuttu"] = (r[0] > r[1]) if b["kod"] == "1" else (r[1] > r[0])
            kupon_durum(K, simdi)


def bk_gecmis(gun_list, A, log=print):
    """Geriye dönük basket: her gün için o günden ÖNCEKİ maçlarla model kurulur (basket.fit), o günün maçları tahmin edilir."""
    import basket as BK
    store = jl(os.path.join(DATA, "bk_games.json"), {}) or {}
    BJ = jl(os.path.join(DATA, "basket.json"), {}) or {}
    out = collections.defaultdict(list); res = {}
    for lg, st in store.items():
        L = BJ.get("leagues", {}).get(lg)
        if not L: continue
        P = L["params"]; G = st.get("g", []); ks = L.get("kscale", 1.0)
        gd = [(zaman(g["dt"]).astimezone(TR).date().isoformat(), g) for g in G]
        for d in gun_list:
            test = [g for dd, g in gd if dd == d]
            if not test: continue
            ref = date.fromisoformat(d)
            train = [g for dd, g in gd if dd < d and (ref - date.fromisoformat(dd)).days <= 400]   # yalnız o günden önceki maçlar
            if len(train) < 80: continue
            F = BK.fit(train, ref, P)
            for g in test:
                pm = BK.pred_means(F, g["h"], g["a"], g.get("neutral", False), P.get("newp"))
                if not pm: continue
                pm = (((pm[0] + pm[1]) + ks * (pm[0] - pm[1])) / 2, ((pm[0] + pm[1]) - ks * (pm[0] - pm[1])) / 2)
                out[d].append(bk_mac(g["id"], lg, L.get("name", lg), g["h"], g["a"], g["dt"][:16] + "Z", pm[0], pm[1], L.get("sm") or 12.0,
                                     A["bk_en_olasi"].get("olcek", 1.0)))
                res[g["id"]] = [g["hs"], g["as_"]]
    return out, res


# ------------------------------------------------------------------ at
def _at_mod():
    p = os.path.join(ROOT, "lab", "at")
    if p not in sys.path: sys.path.insert(0, p)
    import kupon as KP
    return KP


def at_harville_us(oran_mi):
    H = (jl(os.path.join(DATA, "at", "kupon_karne.json"), {}) or {}).get("harville") or {}
    return (H.get("gamma_oran", .82), H.get("delta_oran", .66)) if oran_mi else (H.get("gamma", .82), H.get("delta", .68))


def at_altin_kural():
    k = (jl(os.path.join(DATA, "at", "model.json"), {}) or {}).get("altin_kural") or {}
    return {"p_min": k.get("p_min", .35), "fark_min": k.get("fark_min", .12), "gunluk_max": int(k.get("gunluk_max", 3))}


def _tau(p, tau):
    q = np.asarray(p, float) ** tau; return q / q.sum()


def at_kuponlar(kosular, A, oran_mi=True):
    """kosular: [{"kosu_id","hipodrom","kosu","saat","atlar":[(no, ad, p)]}] (p kazanma, koşu içinde) -> {strateji: [kupon]}."""
    KP = _at_mod()
    g, d = at_harville_us(oran_mi)
    AK = at_altin_kural()
    out = {k: [] for k in ("at_altin", "at_sirali_ikili", "at_ikili", "at_cifte")}
    alt = []
    for k in kosular:
        at = k["atlar"]
        if len(at) < 2: continue
        p = np.array([x[2] for x in at], float); p = p / p.sum()
        o = np.argsort(-p)
        if p[o[0]] >= AK["p_min"] - 1e-12 and p[o[0]] - p[o[1]] >= AK["fark_min"] - 1e-12:
            alt.append((float(p[o[0]]), k, at[o[0]], float(p[o[1]])))
        def leg(tur, secim, pp):
            return {"kosu_id": k["kosu_id"], "hipodrom": k["hipodrom"], "kosu": k["kosu"], "saat": k.get("saat"), "bas_utc": k.get("bas_utc"),
                    "tur": tur, "secim": [str(s) for s in secim], "adlar": [next((x[1] for x in at if str(x[0]) == str(s)), "") for s in secim], "p": r4(pp)}
        for sid, sir in (("at_sirali_ikili", True), ("at_ikili", False)):
            a = A[sid]
            if len(at) < a["en_az_at"]: continue
            H = KP.harville(_tau(p, a.get("tau", 1.0)), g, d, derin=2)
            if len(H) < 2: continue
            P12 = H[1] if sir else H[1] + H[1].T
            if not sir: P12 = np.triu(P12, 1)
            i, j = np.unravel_index(int(np.argmax(P12)), P12.shape)
            out[sid].append(_kupon(sid, [leg("sirali_ikili" if sir else "ikili", [at[i][0], at[j][0]], P12[i, j])]))
    for pp, k, x, p2 in sorted(alt, key=lambda z: -z[0])[:AK["gunluk_max"]]:
        b = {"kosu_id": k["kosu_id"], "hipodrom": k["hipodrom"], "kosu": k["kosu"], "saat": k.get("saat"), "bas_utc": k.get("bas_utc"),
             "tur": "ganyan", "secim": [str(x[0])], "adlar": [x[1]], "p": r4(pp), "fark": r4(pp - p2)}
        out["at_altin"].append(_kupon("at_altin", [b]))
    hip = collections.defaultdict(list)
    for k in kosular: hip[k["hipodrom"]].append(k)
    tc = A["at_cifte"].get("tau", 1.0)
    for h, L in sorted(hip.items()):
        by = {k["kosu"]: k for k in L if len(k["atlar"]) >= 2}; best = None
        for n in sorted(by):
            if n + 1 not in by: continue
            legs = []
            for k in (by[n], by[n + 1]):
                q = _tau([x[2] for x in k["atlar"]], tc); i = int(np.argmax(q)); legs.append((k, k["atlar"][i], float(q[i])))
            jp = legs[0][2] * legs[1][2]
            if best is None or jp > best[0]: best = (jp, legs)
        if best:
            B = [{"kosu_id": k["kosu_id"], "hipodrom": h, "kosu": k["kosu"], "saat": k.get("saat"), "bas_utc": k.get("bas_utc"), "tur": "ganyan",
                  "secim": [str(x[0])], "adlar": [x[1]], "p": r4(pp)} for k, x, pp in best[1]]
            K = _kupon("at_cifte", B); K["tur"] = "cifte"; out["at_cifte"].append(K)
    return out


def at_bacak_tuttu(b, s):
    """s: koşu sonucu {"sira": [no, ...], "kazanan", "ekuri": [[no,..]], "derece": [...]}."""
    if not s or not s.get("sira"): return None
    sira = [str(x) for x in s["sira"]]; der = s.get("derece") or []
    def ayni_birim(no, w):
        if str(no) == str(w): return True
        return any(str(no) in [str(x) for x in g] and str(w) in [str(x) for x in g] for g in s.get("ekuri") or [])
    if b["tur"] == "ganyan":
        if len(der) >= 2 and der[0] == der[1]:   # birincilikte eşit derece: iki at da birinci
            return any(ayni_birim(b["secim"][0], w) for w in sira[:2])
        return ayni_birim(b["secim"][0], sira[0])
    if len(sira) < 2 or (len(der) >= 3 and der[1] == der[2]) or (len(der) >= 2 and der[0] == der[1]): return None
    if b["tur"] == "sirali_ikili": return sira[:2] == b["secim"][:2]
    if b["tur"] == "ikili": return set(sira[:2]) == set(b["secim"][:2])
    return None


def at_canli_kosular(gun, simdi):
    """data/at/tahmin/<gün>.json (gece robotunun koşudan önce kilitlediği olasılık) -> henüz başlamamış koşular."""
    T = jl(os.path.join(DATA, "at", "tahmin", gun + ".json"))
    if not T: return None, None
    now = tsi(simdi); out = []
    for k in T.get("kosular", []):
        if not k.get("kosudan_once", True): continue
        if k.get("saat") and f"{gun} {k['saat']}" <= now: continue
        bas = iso(datetime.fromisoformat(f"{gun}T{k['saat']}").replace(tzinfo=TR)) if k.get("saat") else None
        out.append({"kosu_id": k["kosu_id"], "hipodrom": k["hipodrom"], "kosu": k["kosu"], "saat": k.get("saat"), "bas_utc": bas,
                    "mod": k.get("mod"), "atlar": [(a["no"], a.get("ad", ""), a["p_kazanma"]) for a in k["atlar"]]})
    return out, T


def at_altili_kuponlar(A_dosya, sadece_kilitli=True):
    out = []
    for X in (A_dosya or {}).get("altililar", []):
        if sadece_kilitli and not (X.get("kilitli") and X.get("kosudan_once")): continue
        for sev in ("dar", "orta", "genis"):
            L = (X.get("seviyeler") or {}).get(sev)
            if not L: continue
            out.append({"strateji": f"at_altili_{sev}", "altili_id": X["id"], "hipodrom": X["hipodrom"], "saat": X.get("saat"),
                        "bas_utc": iso(datetime.fromisoformat(f"{X['id'][:10]}T{X['saat']}").replace(tzinfo=TR)) if X.get("saat") else None,
                        "kombinasyon": L.get("kombinasyon"), "p": r4(L.get("p")), "oran": None,
                        "kilit_tsi": X.get("kilit_tsi"), "kosudan_once": bool(X.get("kosudan_once")),
                        "bacaklar": [{"kosu": a["kosu"], "saat": a.get("saat"), "tur": "ayak", "secim": a["secim"], "p": a.get("p_ayak")} for a in L["ayaklar"]]})
    return out


def at_puanla(bolum, gun, simdi):
    C = jl(os.path.join(DATA, "at", "canli", gun + ".json"), {}) or {}
    S = {k["kosu_id"]: k.get("sonuc") for k in C.get("kosular", [])}
    AL = {X["id"]: X for X in (jl(os.path.join(DATA, "at", "altili", gun + ".json"), {}) or {}).get("altililar", [])}
    for K in bolum.get("kuponlar", []):
        if K["strateji"].startswith("at_altili_"):
            X = AL.get(K["altili_id"]); sev = K["strateji"].rsplit("_", 1)[1]
            if X and X.get("sonuc"):
                at = X["sonuc"]["ayak_tuttu"].get(sev) or []
                for b, ok in zip(K["bacaklar"], at): b["tuttu"] = ok
                kz = X["sonuc"].get("kazananlar") or []
                for b, w in zip(K["bacaklar"], kz):
                    if w: b["kazanan"] = str(w)
            kupon_durum(K, simdi, gec_gun=3)
            continue
        for b in K["bacaklar"]:
            if b.get("tuttu") is not None: continue
            s = S.get(b["kosu_id"])
            if s:
                b["tuttu"] = at_bacak_tuttu(b, s); b["sonuc"] = s.get("sira")
        kupon_durum(K, simdi, gec_gun=3)


def at_gecmis(gun_list, A):
    """replay_kosular.json (sızıntısız gün gün yeniden oynatma, p_sabah = yalnız model) -> geriye dönük at kuponları + puan."""
    R = jl(os.path.join(DATA, "at", "replay_kosular.json"), {}) or {}
    by = collections.defaultdict(list)
    for k in R.get("kosular", []): by[k["t"]].append(k)
    KP = _at_mod()
    import altili as AL
    AK = (jl(os.path.join(DATA, "at", "altili_karne.json"), {}) or {}).get("geriye_donuk") or {}
    tau6, kural6 = AK.get("tau", 1.0), AK.get("altin_kural") or dict(AL.ALTIN_YOK)
    Alt = [X for X in AL._replay_altililar(R)[0] if X["t"] in set(gun_list)] if R else []
    out = {}
    for d in gun_list:
        L = sorted(by.get(d, []), key=lambda k: (k["h"], k["k"]))
        if not L: continue
        ks = [{"kosu_id": k["id"], "hipodrom": k["h"], "kosu": k["k"], "saat": None, "bas_utc": None,
               "atlar": [(a[0], "", a[1]) for a in k["a"]]} for k in L]
        K = at_kuponlar(ks, A, oran_mi=False)
        son = {}
        for k in L:
            pos = sorted([a for a in k["a"] if a[3] is not None], key=lambda a: a[3])
            son[k["id"]] = {"sira": [a[0] for a in pos[:4]], "derece": [a[3] for a in pos[:4]], "ekuri": k.get("e") or []}
        kup = [x for v in K.values() for x in v]
        for X in [x for x in Alt if x["t"] == d]:
            UB = [AL._ayak_birim(k, tau6) for k in X["ayak"]]
            kaz = [AL._kazanan_birim(U, k)[1] for U, k in zip(UB, X["ayak"])]
            for sev, B in AL.SEVIYE.items():
                n, alt, p, c = AL.kupon(UB, B, kural6)
                at = [kaz[i] is not None and kaz[i] < n[i] for i in range(6)]
                kup.append({"strateji": f"at_altili_{sev}", "altili_id": X["id"], "hipodrom": X["h"], "saat": None, "bas_utc": None,
                            "kombinasyon": c, "p": r4(p), "oran": None, "kosudan_once": True,
                            "bacaklar": [{"kosu": k["k"], "tur": "ayak", "secim": [no for u in UB[i][:n[i]] for no in u["nolar"]],
                                          "p": r4(sum(u["p"] for u in UB[i][:n[i]])), "tuttu": bool(at[i])} for i, k in enumerate(X["ayak"])]})
        for Kp in kup:
            if not Kp["strateji"].startswith("at_altili_"):
                for b in Kp["bacaklar"]:
                    s = son.get(b["kosu_id"]); b["tuttu"] = at_bacak_tuttu(b, s); b["sonuc"] = s and s["sira"]
            Kp["durum"] = "tuttu" if all(b.get("tuttu") for b in Kp["bacaklar"]) else ("tutmadi" if any(b.get("tuttu") is False for b in Kp["bacaklar"]) else "gecersiz")
            Kp["tuttu"] = True if Kp["durum"] == "tuttu" else (False if Kp["durum"] == "tutmadi" else None)
        out[d] = kup
    return out


# ------------------------------------------------------------------ dosya / kilit
def _numarala(gun, kup):
    say = collections.Counter()
    for K in kup:
        say[K["strateji"]] += 1; K["id"] = f"{gun}/{K['strateji']}/{say[K['strateji']]}"
    return kup


def motor_surumu():
    M = jl(os.path.join(DATA, "model.json"), {}) or {}
    PK = jl(os.path.join(DATA, "pazar_karne.json"), {}) or {}
    BJ = jl(os.path.join(DATA, "basket.json"), {}) or {}
    AM = jl(os.path.join(DATA, "at", "model.json"), {}) or {}
    return {"oxx": OXX_V, "futbol": M.get("engine"), "pazar_v": PK.get("v"), "basket": BJ.get("engine"), "at": AM.get("surum")}


def golge_ayar(Ayar):
    """İzlenen (14 gün) kabul edilmiş değişiklikler: önceki ayarla 'gölge' kupon da kurulur (yeniden sınama için)."""
    J = jl(AYAR, {}) or {}
    izl = [d for d in J.get("izlenen", []) if d.get("onceki") is not None]
    if not izl: return None, []
    G = copy.deepcopy(J)
    for d in izl:
        yol = d["anahtar_yol"]; cur = G.setdefault("params", {})
        for k in yol[:-1]: cur = cur.setdefault(k, {})
        if d["onceki"] == "__yok__": cur.pop(yol[-1], None)
        else: cur[yol[-1]] = d["onceki"]
    return ayar_yukle(G), sorted({s for d in izl for s in d.get("stratejiler", [])})


def fb_bk_kilitle(gun, simdi, A, log=print):
    yol = os.path.join(KDIR, gun + ".json")
    D = jl(yol) or {"tarih": gun, "oxx_v": OXX_V, "geriye_donuk": False, "uyari": UYARI}
    if D.get("geriye_donuk"): return D, yol     # geçmiş gün dosyası: canlı kilit yazılmaz
    PK = jl(os.path.join(DATA, "pazar_karne.json"), {}) or {}
    if "futbol" not in D:
        M = fb_canli_maclar(gun, simdi, A)
        if len(M) >= MIN_FB_MAC:
            K = fb_kuponlar(M, A, uygun_pazarlar(PK))
            D["futbol"] = {"kilit_utc": iso(simdi), "kilit_tsi": tsi(simdi), "motor": motor_surumu(), "ayar_surum": A["_surum"],
                           "aday_mac": len(M), "kuponlar": _numarala(gun, [x for s in STRATEJI if s in K for x in K[s]])}
            GA, gs = golge_ayar(A)
            if GA and any(s.startswith("fb_") for s in gs):
                KG = fb_kuponlar(fb_canli_maclar(gun, simdi, GA), GA, uygun_pazarlar(PK), yalniz=[s for s in gs if s.startswith("fb_")])
                D.setdefault("golge", {})["futbol"] = {"ayar_surum": "onceki", "kuponlar": _numarala(gun, [x for s in KG for x in KG[s]])}
            log(f"OXX futbol {gun}: {len(M)} aday maç, {len(D['futbol']['kuponlar'])} kupon kilitlendi")
        else:
            log(f"OXX futbol {gun}: aday maç {len(M)} < {MIN_FB_MAC}, kilit sonraki çalıştırmaya")
    if "basket" not in D:
        M = bk_canli_maclar(gun, simdi, A)
        if len(M) >= MIN_BK_MAC:
            K = bk_kuponlar(M, A)
            D["basket"] = {"kilit_utc": iso(simdi), "kilit_tsi": tsi(simdi), "motor": motor_surumu(), "ayar_surum": A["_surum"],
                           "aday_mac": len(M), "kuponlar": _numarala(gun, K["bk_en_olasi"])}
            log(f"OXX basket {gun}: {len(M)} aday maç, {len(D['basket']['kuponlar'])} kupon kilitlendi")
    return D, yol


def at_kilitle(gun, simdi, A, log=print):
    yol = os.path.join(ATDIR, gun + ".json")
    D = jl(yol) or {"tarih": gun, "oxx_v": OXX_V, "geriye_donuk": False, "uyari": UYARI, "kuponlar": []}
    if D.get("geriye_donuk"): return D, yol
    if not D.get("kilit_utc"):
        ks, T = at_canli_kosular(gun, simdi)
        if ks:
            K = at_kuponlar(ks, A, oran_mi=True)
            D.update({"kilit_utc": iso(simdi), "kilit_tsi": tsi(simdi), "motor": motor_surumu(), "ayar_surum": A["_surum"],
                      "tahmin_kilit_tsi": T.get("kilit_zamani_tsi"), "aday_kosu": len(ks)})
            D["kuponlar"] = _numarala(gun, [x for s in STRATEJI if s in K for x in K[s]])
            log(f"OXX at {gun}: {len(ks)} koşu, {len(D['kuponlar'])} kupon kilitlendi")
    # 6'lı: altili.py kuponu ilk ayaktan önce kurup ilk ayakta kilitler; OXX onu kilitlendiği haliyle benimser (bir kez)
    var = {K.get("altili_id") for K in D["kuponlar"] if K.get("altili_id")}
    yeni = [K for K in at_altili_kuponlar(jl(os.path.join(DATA, "at", "altili", gun + ".json"))) if K["altili_id"] not in var]
    if yeni:
        for K in yeni: K["oxx_kilit_utc"] = iso(simdi)
        D["kuponlar"] = _numarala(gun, D["kuponlar"] + yeni)
    return D, yol


# ------------------------------------------------------------------ karne
KOVA = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0001]


def _ozet(L):
    """L: [(gün, p, tuttu, bacak_n, bacak_tutan, bacak_p_toplam)]"""
    n = len(L)
    if not n: return {"n": 0, "tutan": 0, "isabet": None, "beklenen": 0.0}
    h = sum(x[2] for x in L); e = sum(x[1] for x in L); v = sum(x[1] * (1 - x[1]) for x in L)
    bn = sum(x[3] for x in L); bt = sum(x[4] for x in L); be = sum(x[5] for x in L)
    return {"n": n, "tutan": int(h), "isabet": r4(h / n), "beklenen": round(e, 2), "beklenen_oran": r4(e / n),
            "z": round((h - e) / math.sqrt(v), 2) if v > 0 else None,
            "bacak": {"n": bn, "tutan": bt, "isabet": r4(bt / bn) if bn else None, "beklenen": round(be, 2)}}


def _kova(L):
    out = []
    for lo, hi in zip(KOVA[:-1], KOVA[1:]):
        s = [x for x in L if lo <= x[1] < hi]
        if s: out.append({"aralik": f"{lo:.1f}-{min(hi, 1):.1f}", "n": len(s), "tahmin": r4(np.mean([x[1] for x in s])), "gercek": r4(np.mean([x[2] for x in s]))})
    return out


def _seri(L):
    if not L: return {"guncel": 0, "en_uzun_tutan": 0, "en_uzun_tutmayan": 0}
    son = L[-1][2]; k = 0
    for x in reversed(L):
        if x[2] != son: break
        k += 1
    eu = et = c = 0; prev = None
    for x in L:
        c = c + 1 if x[2] == prev else 1; prev = x[2]
        if x[2]: eu = max(eu, c)
        else: et = max(et, c)
    return {"guncel": k if son else -k, "en_uzun_tutan": eu, "en_uzun_tutmayan": et}


def tum_kuponlar():
    """[(gün, spor, kupon, geriye_donuk)] — futbol/basket gün dosyalarından, at at dosyalarından."""
    out = []
    for f in sorted(glob.glob(os.path.join(KDIR, "*.json"))):
        D = jl(f, {}) or {}; g = D.get("tarih") or os.path.basename(f)[:10]
        for sp in ("futbol", "basket"):
            for K in (D.get(sp) or {}).get("kuponlar", []): out.append((g, sp, K, bool(D.get("geriye_donuk"))))
    for f in sorted(glob.glob(os.path.join(ATDIR, "*.json"))):
        D = jl(f, {}) or {}; g = D.get("tarih") or os.path.basename(f)[:10]
        for K in D.get("kuponlar", []): out.append((g, "at", K, bool(D.get("geriye_donuk"))))
    return out


def karne_kur(bugun, log=print):
    T = tum_kuponlar()
    by = collections.defaultdict(list); bekleyen = collections.Counter()
    for g, sp, K, geri in T:
        if K.get("durum") == "bekliyor": bekleyen[K["strateji"]] += 1
        if K.get("durum") not in ("tuttu", "tutmadi"): continue
        if K["strateji"].startswith("at_altili_") and not K.get("kosudan_once", True): continue
        bl = [b for b in K["bacaklar"] if b.get("tuttu") is not None]
        by[K["strateji"]].append((g, float(K["p"] or 0), bool(K["tuttu"]), len(bl), sum(1 for b in bl if b["tuttu"]),
                                  sum(float(b.get("p") or 0) for b in bl), geri, K.get("bas_utc") or (K["bacaklar"][0].get("bas_utc") if K["bacaklar"] else "") or ""))
    d7 = (bugun - timedelta(days=7)).isoformat(); d30 = (bugun - timedelta(days=30)).isoformat()
    S = {}
    for sid, (sp, ad, kural) in STRATEJI.items():
        L = sorted(by.get(sid, []), key=lambda x: (x[0], x[7]))
        gun = collections.OrderedDict()
        for x in L:
            G = gun.setdefault(x[0], [0, 0, 0.0, x[6]]); G[0] += 1; G[1] += int(x[2]); G[2] += x[1]
        S[sid] = dict(_ozet(L), ad=ad, spor=sp, kural=kural, bekleyen=bekleyen.get(sid, 0),
                      kalibrasyon={"gercek_bolu_beklenen": r4(sum(x[2] for x in L) / sum(x[1] for x in L)) if L and sum(x[1] for x in L) > 0 else None,
                                   "kovalar": _kova(L)},
                      son7=_ozet([x for x in L if x[0] >= d7]), son30=_ozet([x for x in L if x[0] >= d30]), seri=_seri(L),
                      canli=_ozet([x for x in L if not x[6]]), geriye_donuk=_ozet([x for x in L if x[6]]),
                      gunluk=[{"d": d, "n": v[0], "tutan": v[1], "beklenen": round(v[2], 3), "geriye_donuk": v[3]} for d, v in list(gun.items())[-30:]])
    gd = sorted({g for g, _, _, geri in T if geri}); cd = sorted({g for g, _, _, geri in T if not geri})
    J = jl(AYAR, {}) or {}
    out = {"v": 1, "oxx_v": OXX_V, "guncelleme_utc": iso(datetime.now(timezone.utc)), "uyari": UYARI,
           "aciklama": "Strateji başına kilitli OXX kuponları: n = puanlanmış kupon, tutan, beklenen = kupon tutma olasılıkları toplamı "
                       "(iyi kalibre robotta tutan ≈ beklenen; z = (tutan − beklenen)/√Σp(1−p)). bacak = kupondaki tek tek tahminler. "
                       "geriye_donuk = kilit sistemi kurulmadan önceki günler için yalnız o günden önce bilinenle sonradan kurulan kuponlar; "
                       "canli = gerçekten maçtan önce kilitlenenler. Para tutarı yoktur.",
           "donem": {"geriye_donuk": [gd[0], gd[-1]] if gd else None, "canli": [cd[0], cd[-1]] if cd else None},
           "ayar_surum": J.get("surum", "varsayilan"), "motor": motor_surumu(), "stratejiler": S}
    jw_degisince(KARNE, out)
    return out


# ------------------------------------------------------------------ geriye dönük
def geriye(n_gun, bugun, log=print):
    """Son n_gun (bugün hariç) için kupon kur ve puanla; YALNIZ o günden önce bilinen bilgi: futbol olasılığı maçın kendi maç
    öncesi (kapanış) oranından, kalibratörler pencereden önceki maçlarla; basket modeli o günden önceki maçlarla; at
    olasılığı sızıntısız yeniden oynatmanın sabah (yalnız model) olasılığı. Mevcut canlı gün dosyalarına dokunmaz."""
    import pazar as PZM
    t0 = time.time()
    A = ayar_yukle({})            # geriye dönük karne VARSAYILAN kurallarla (öğrenilmiş ayar sızıntı olurdu)
    S = jl(os.path.join(DATA, "season.json"), {}) or {}
    MJ = jl(os.path.join(DATA, "model.json"), {}) or {}
    P = MJ.get("params", {})
    PK = jl(os.path.join(DATA, "pazar_karne.json"), {}) or {}
    gunler = [(bugun - timedelta(days=i)).isoformat() for i in range(n_gun, 0, -1)]
    d0, d1 = gunler[0], (bugun).isoformat()
    R, PZ = gecmis_pz(S, P, PK, d0, d1, aylik=False, log=log)
    G, SON = gecmis_gunler(R, PZ, A, {lg: d.get("name", lg) for lg, d in S.items()})
    uyg = uygun_pazarlar(PK)
    bk, bkr = bk_gecmis(gunler, A, log)
    atg = at_gecmis(gunler, A)
    simdi = datetime.now(timezone.utc)
    yaz = 0
    for g in gunler:
        yol = os.path.join(KDIR, g + ".json"); E = jl(yol)
        if E and not E.get("geriye_donuk"): continue
        am, ason = arsiv_maclari(g, P, PK, A)
        if len(am) >= MIN_FB_MAC and len(am) >= len(G.get(g, [])):
            M, SN, kay = am, ason, "arşiv (iddaa bülteni, kilitli oran + sonuç)"
        else:
            M, SN, kay = G.get(g, []), SON, "season.json (football-data kapanış oranı + sonuç)"
        D = {"tarih": g, "oxx_v": OXX_V, "geriye_donuk": True, "uyari": UYARI,
             "not": "GERİYE DÖNÜK: kilit sistemi bu gün için çalışmıyordu; kuponlar sonradan, yalnız o günden önce bilinen bilgiyle kuruldu "
                    "(maç öncesi oran, önceki maçlarla öğrenilmiş kalibrasyon/model). Varsayılan strateji kuralları.",
             "kilit_utc": iso(simdi), "bilgi_kesimi": g + "T00:00+03:00", "motor": motor_surumu()}
        if len(M) >= MIN_FB_MAC:
            K = fb_kuponlar(M, A, uyg)
            kup = _numarala(g, [x for s in STRATEJI if s in K for x in K[s]])
            for Kp in kup:
                for b in Kp["bacaklar"]:
                    ft, ht = SN[b["mac"]]; b["sonuc"] = f"{ft[0]}-{ft[1]}"
                    if ht: b["iy"] = f"{ht[0]}-{ht[1]}"
                    b["tuttu"] = PZM.outcome(b["kod"], ft, ht)
                kupon_durum(Kp, simdi)
            D["futbol"] = {"kaynak": kay, "aday_mac": len(M), "ayar_surum": "varsayilan", "kuponlar": kup}
        if len(bk.get(g, [])) >= MIN_BK_MAC:
            K = bk_kuponlar(bk[g], A)["bk_en_olasi"]
            for Kp in K:
                for b in Kp["bacaklar"]:
                    r = bkr.get(b["mac"]); b["sonuc"] = f"{r[0]}-{r[1]}"; b["tuttu"] = (r[0] > r[1]) if b["kod"] == "1" else (r[1] > r[0])
                kupon_durum(Kp, simdi)
            D["basket"] = {"kaynak": "bk_games.json (o günden önceki maçlarla basket.fit)", "aday_mac": len(bk[g]), "kuponlar": _numarala(g, K)}
        if "futbol" in D or "basket" in D:
            yaz += jw_degisince(yol, D)
        if g in atg:
            ya = os.path.join(ATDIR, g + ".json"); E = jl(ya)
            if not E or E.get("geriye_donuk"):
                jw_degisince(ya, {"tarih": g, "oxx_v": OXX_V, "geriye_donuk": True, "uyari": UYARI, "kilit_utc": iso(simdi),
                                  "not": "GERİYE DÖNÜK: data/at/replay_kosular.json (sızıntısız yeniden oynatma, p_sabah = yalnız model) ile sonradan kuruldu.",
                                  "kaynak": "replay_kosular.json", "motor": motor_surumu(), "kuponlar": _numarala(g, atg[g])})
    log(f"OXX geriye dönük: {len(gunler)} gün ({gunler[0]}…{gunler[-1]}), {yaz} gün dosyası yazıldı, {time.time() - t0:.1f} sn")


# ------------------------------------------------------------------ ana akış
def ana(simdi, log=print):
    t0 = time.time()
    A = ayar_yukle()
    bugun = simdi.astimezone(TR).date()
    D, yol = fb_bk_kilitle(bugun.isoformat(), simdi, A, log)
    os.makedirs(KDIR, exist_ok=True)
    jw_degisince(yol, D)
    S, B = FbSonuc(), BkSonuc()
    for f in sorted(glob.glob(os.path.join(KDIR, "*.json")))[-12:]:   # son günlerin sonuçları (geç gelen sonuçlar dahil)
        X = jl(f, {}) or {}
        if X.get("geriye_donuk"): continue
        if "futbol" in X: fb_puanla(X["futbol"], S, simdi)
        if "basket" in X: B.puanla(X["basket"], simdi)
        for sp in ("futbol",):
            if (X.get("golge") or {}).get(sp): fb_puanla(X["golge"][sp], S, simdi)
        AT = jl(os.path.join(ATDIR, os.path.basename(f)))
        if AT and not AT.get("geriye_donuk"):
            X["at"] = {k: AT.get(k) for k in ("kilit_utc", "kilit_tsi", "motor", "ayar_surum", "kuponlar")}
            X["at"]["kaynak"] = "data/oxx_kupon/at/" + os.path.basename(f)
        X["guncelleme_utc"] = iso(simdi)
        jw_degisince(f, X)
    K = karne_kur(bugun, log)
    oz = {s: (v["n"], v["tutan"]) for s, v in K["stratejiler"].items() if v["n"]}
    log(f"OXX karne: {oz} ({time.time() - t0:.1f} sn)")


def ana_at(simdi, log=print):
    t0 = time.time()
    A = ayar_yukle()
    bugun = simdi.astimezone(TR).date()
    gunler = [bugun.isoformat()]
    if simdi.astimezone(TR).hour < 6: gunler.insert(0, (bugun - timedelta(days=1)).isoformat())
    for g in gunler:
        D, yol = at_kilitle(g, simdi, A, log) if g == bugun.isoformat() else (jl(os.path.join(ATDIR, g + ".json")), os.path.join(ATDIR, g + ".json"))
        if not D or D.get("geriye_donuk"): continue
        at_puanla(D, g, simdi)
        D["guncelleme_utc"] = iso(simdi)
        if D.get("kilit_utc") or D.get("kuponlar"): jw_degisince(yol, D)
    for f in sorted(glob.glob(os.path.join(ATDIR, "*.json")))[-4:]:   # geç gelen sonuçlar
        g = os.path.basename(f)[:10]
        if g in gunler: continue
        D = jl(f, {}) or {}
        if D.get("geriye_donuk"): continue
        if any(K.get("durum") == "bekliyor" for K in D.get("kuponlar", [])):
            at_puanla(D, g, simdi); D["guncelleme_utc"] = iso(simdi); jw_degisince(f, D)
    log(f"OXX at tamam ({time.time() - t0:.1f} sn)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", action="store_true")
    ap.add_argument("--geriye", type=int, default=0)
    ap.add_argument("--simdi", default=None)
    ar = ap.parse_args()
    simdi = zaman(ar.simdi) if ar.simdi else datetime.now(timezone.utc)
    if ar.geriye:
        geriye(ar.geriye, simdi.astimezone(TR).date())
        karne_kur(simdi.astimezone(TR).date())
        return
    if ar.at: ana_at(simdi)
    else: ana(simdi)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback; traceback.print_exc(); print("OXX kupon robotu hata verdi; diğer adımlar etkilenmez")
