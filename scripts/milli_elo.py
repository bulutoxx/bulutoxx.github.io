#!/usr/bin/env python3
"""🌍 Milli takım Elo (YH-20; Dünya Futbol Elo usulü) — CC0 açık geçmişten türetilmiş puan.

Kaynak: martj42/international_results (CC0, 1872 → bugün) results.csv. Ham CSV depoya YAZILMAZ: yalnız
actions/cache klasöründe (.milli_elo_onbellek/) tutulur; depoya yalnız türetilmiş puan ve parametre (data/milli_elo.json) gider.

Puan: R' = R + K·G·(W − We), We = 1 / (10^(−dr/400) + 1), dr = R_ev − R_dep + H (tarafsız sahada H = 0).
  K: Dünya Kupası finalleri 60 · kıta şampiyonası finalleri + Konfederasyonlar 50 · eleme ve Uluslar Ligi 40 ·
     diğer turnuvalar 30 · hazırlık maçı 20.
  G: gol farkı ≤ 1 → 1 · 2 → 1,5 · N ≥ 3 → (11 + N) / 8.
1X2 olasılığı: dr/400 üzerinde sıralı lojit (θ1, θ2, b), yalnız geçmiş maçlarla öğrenilir.

Gölge kayıt (yalnız ölçüm, üretimi değiştirmez): fixtures.json'da iki takımı da milli takım sözlüğünde olan maçlar
başlamadan önce data/milli_elo_golge.json'a bir kez yazılır (Elo 1X2 + piyasa 1X2); kayıt sonradan değişmez,
yalnız sonuç alanı CC0 sonuçtan eklenir. Konsey adaylığı kararı bu kayıtlardan verilir (lab/milli_elo_lab.py golge).

  python3 scripts/milli_elo.py            # indir (önbellek), puanla, data/milli_elo.json + gölge kayıt
"""
import csv, io, json, math, os, re, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ONBELLEK = os.path.join(ROOT, ".milli_elo_onbellek")
URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
CIKTI = os.path.join(DATA, "milli_elo.json")
GOLGE = os.path.join(DATA, "milli_elo_golge.json")

# Varsayılan parametreler (lab/milli_elo_lab.py yalnız 2016 öncesiyle seçer; data/milli_elo.json → params yazarsa o kullanılır)
P0 = {"H": 100.0, "R0": 1500.0, "K_carp": 1.0}

FINAL60 = {"FIFA World Cup"}
FINAL50 = {"UEFA Euro", "Copa América", "African Cup of Nations", "AFC Asian Cup", "Gold Cup", "CONCACAF Championship",
           "Oceania Nations Cup", "Confederations Cup"}
# FIFA dışı / yarı resmî yarışmalar: puanlanır ama sınama ve kalibrasyon kümesine girmez
FIFA_DISI = re.compile(r"(CONIFA|Island Games|Viva World|Inter Games|Muratti|ELF Cup|FIFI Wild|Tynwald|Niamh|"
                       r"Peoples, Cultures|Coupe de l'Outre|Games$|Mini Games|UAFA|Wild Cup)", re.I)


def K_tur(t):
    if t in FINAL60: return 60.0
    if t in FINAL50: return 50.0
    if "qualification" in t or "Nations League" in t: return 40.0
    if t == "Friendly": return 20.0
    return 30.0


def G_carp(n):
    n = abs(n)
    return 1.0 if n <= 1 else (1.5 if n == 2 else (11.0 + n) / 8.0)


def indir(zorla=False, maks_yas_saat=20):
    """CSV metni: önbellek tazeyse oradan, değilse indir. Ağ yoksa eski önbellek."""
    os.makedirs(ONBELLEK, exist_ok=True)
    yol = os.path.join(ONBELLEK, "results.csv")
    taze = os.path.exists(yol) and (time.time() - os.path.getmtime(yol)) < maks_yas_saat * 3600
    if not taze or zorla:
        try:
            r = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "OXXai-milli-elo"}), timeout=60)
            b = r.read()
            if len(b) > 1_000_000 and b[:4] == b"date":
                open(yol, "wb").write(b)
        except Exception as e:
            print("indirme hatası (önbellek kullanılacak):", e, file=sys.stderr)
    if not os.path.exists(yol): raise SystemExit("CC0 sonuç dosyası yok (ağ + önbellek)")
    return open(yol, encoding="utf-8").read()


def satirlar(metin):
    """Oynanmış maçlar (tarih sıralı) + oynanmamış (NA) maçlar."""
    oyn, gel = [], []
    for r in csv.DictReader(io.StringIO(metin)):
        try:
            hs, as_ = int(r["home_score"]), int(r["away_score"])
        except (ValueError, TypeError):
            gel.append(r); continue
        oyn.append((r["date"], r["home_team"], r["away_team"], hs, as_, r["tournament"], r["neutral"].upper() == "TRUE"))
    oyn.sort(key=lambda x: x[0])
    return oyn, gel


def puanla(oyn, P=P0, kayit=None):
    """Çevrimiçi Elo. kayit(i, dr) her maçtan ÖNCE çağrılır (sızıntısız). Dönüş: R sözlüğü, son maç tarihi."""
    R, son = {}, {}
    H, R0, kc = P["H"], P["R0"], P.get("K_carp", 1.0)
    for i, (d, h, a, hs, as_, t, ntr) in enumerate(oyn):
        rh, ra = R.get(h, R0), R.get(a, R0)
        dr = rh - ra + (0.0 if ntr else H)
        if kayit is not None: kayit(i, dr)
        we = 1.0 / (10 ** (-dr / 400.0) + 1.0)
        w = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
        dlt = kc * K_tur(t) * G_carp(hs - as_) * (w - we)
        R[h] = rh + dlt; R[a] = ra - dlt; son[h] = d; son[a] = d
    return R, son


def _sig(x): return 1.0 / (1.0 + math.exp(-x))


def p1x2(dr, M):
    """Sıralı lojit: P(dep) = σ(θ1 − b z), P(dep ∪ X) = σ(θ2 − b z), z = dr/400."""
    z = dr / 400.0
    pa = _sig(M["t1"] - M["b"] * z); pax = _sig(M["t2"] - M["b"] * z)
    pa = min(max(pa, 1e-4), 1 - 2e-4); pd = min(max(pax - pa, 1e-4), 1 - pa - 1e-4)
    return [1.0 - pa - pd, pd, pa]


def sirali_lojit(z, y, w=None):
    """θ1, θ2, b en çok olabilirlik (y: 0 ev, 1 X, 2 dep)."""
    import numpy as np
    from scipy.optimize import minimize
    z = np.asarray(z, float); y = np.asarray(y); w = np.ones_like(z) if w is None else np.asarray(w, float)
    def nll(p):
        t1, dt, b = p; t2 = t1 + math.exp(dt)
        pa = 1 / (1 + np.exp(-(t1 - b * z))); pax = 1 / (1 + np.exp(-(t2 - b * z)))
        pr = np.where(y == 2, pa, np.where(y == 1, pax - pa, 1 - pax))
        return -(w * np.log(np.clip(pr, 1e-9, 1))).sum() / w.sum()
    r = minimize(nll, [-0.9, 0.0, 2.2], method="Nelder-Mead", options={"xatol": 1e-5, "fatol": 1e-8, "maxiter": 4000})
    t1, dt, b = r.x
    return {"t1": round(float(t1), 5), "t2": round(float(t1 + math.exp(dt)), 5), "b": round(float(b), 5)}


# ---- iddaa (Türkçe) → CC0 adı. Yalnız tam ad eşleşmesi; U21/kadın/olimpik takımlar ayrıca elenir.
TR_EN = {
 "Türkiye": "Turkey", "Almanya": "Germany", "Fransa": "France", "İspanya": "Spain", "İtalya": "Italy", "İngiltere": "England",
 "Hollanda": "Netherlands", "Belçika": "Belgium", "Portekiz": "Portugal", "İsviçre": "Switzerland", "Avusturya": "Austria",
 "Hırvatistan": "Croatia", "Sırbistan": "Serbia", "Danimarka": "Denmark", "İsveç": "Sweden", "Norveç": "Norway",
 "Finlandiya": "Finland", "İzlanda": "Iceland", "Polonya": "Poland", "Çekya": "Czech Republic", "Çek Cumhuriyeti": "Czech Republic",
 "Slovakya": "Slovakia", "Slovenya": "Slovenia", "Macaristan": "Hungary", "Romanya": "Romania", "Bulgaristan": "Bulgaria",
 "Yunanistan": "Greece", "Arnavutluk": "Albania", "Kuzey Makedonya": "North Macedonia", "Karadağ": "Montenegro",
 "Bosna Hersek": "Bosnia and Herzegovina", "Bosna-Hersek": "Bosnia and Herzegovina", "Kosova": "Kosovo", "Ukrayna": "Ukraine",
 "Rusya": "Russia", "Belarus": "Belarus", "Beyaz Rusya": "Belarus", "Moldova": "Moldova", "Gürcistan": "Georgia",
 "Ermenistan": "Armenia", "Azerbaycan": "Azerbaijan", "Kazakistan": "Kazakhstan", "İskoçya": "Scotland", "Galler": "Wales",
 "Kuzey İrlanda": "Northern Ireland", "İrlanda": "Republic of Ireland", "İrlanda Cumhuriyeti": "Republic of Ireland",
 "Estonya": "Estonia", "Letonya": "Latvia", "Litvanya": "Lithuania", "Lüksemburg": "Luxembourg", "Malta": "Malta",
 "Kıbrıs": "Cyprus", "GKRY": "Cyprus", "Güney Kıbrıs": "Cyprus", "Andorra": "Andorra", "San Marino": "San Marino",
 "Lihtenştayn": "Liechtenstein", "Faroe Adaları": "Faroe Islands", "Cebelitarık": "Gibraltar", "İsrail": "Israel",
 "Brezilya": "Brazil", "Arjantin": "Argentina", "Uruguay": "Uruguay", "Kolombiya": "Colombia", "Şili": "Chile",
 "Peru": "Peru", "Ekvador": "Ecuador", "Paraguay": "Paraguay", "Bolivya": "Bolivia", "Venezuela": "Venezuela",
 "Meksika": "Mexico", "ABD": "United States", "Amerika Birleşik Devletleri": "United States", "Kanada": "Canada",
 "Kosta Rika": "Costa Rica", "Panama": "Panama", "Honduras": "Honduras", "Jamaika": "Jamaica", "El Salvador": "El Salvador",
 "Guatemala": "Guatemala", "Haiti": "Haiti", "Küba": "Cuba", "Trinidad ve Tobago": "Trinidad and Tobago",
 "Nikaragua": "Nicaragua", "Curaçao": "Curaçao", "Curacao": "Curaçao", "Surinam": "Suriname",
 "Japonya": "Japan", "Güney Kore": "South Korea", "Kuzey Kore": "North Korea", "Çin": "China", "Avustralya": "Australia",
 "Yeni Zelanda": "New Zealand", "İran": "Iran", "Suudi Arabistan": "Saudi Arabia", "Katar": "Qatar", "Irak": "Iraq",
 "Birleşik Arap Emirlikleri": "United Arab Emirates", "BAE": "United Arab Emirates", "Ürdün": "Jordan", "Umman": "Oman",
 "Bahreyn": "Bahrain", "Kuveyt": "Kuwait", "Suriye": "Syria", "Lübnan": "Lebanon", "Filistin": "Palestine",
 "Özbekistan": "Uzbekistan", "Tacikistan": "Tajikistan", "Kırgızistan": "Kyrgyzstan", "Türkmenistan": "Turkmenistan",
 "Tayland": "Thailand", "Vietnam": "Vietnam", "Endonezya": "Indonesia", "Malezya": "Malaysia", "Hindistan": "India",
 "Filipinler": "Philippines", "Singapur": "Singapore", "Hong Kong": "Hong Kong", "Yemen": "Yemen",
 "Fas": "Morocco", "Cezayir": "Algeria", "Tunus": "Tunisia", "Mısır": "Egypt", "Libya": "Libya", "Nijerya": "Nigeria",
 "Senegal": "Senegal", "Gana": "Ghana", "Kamerun": "Cameroon", "Fildişi Sahili": "Ivory Coast", "Mali": "Mali",
 "Burkina Faso": "Burkina Faso", "Güney Afrika": "South Africa", "Demokratik Kongo Cumhuriyeti": "DR Congo", "DK Kongo": "DR Congo",
 "Kongo": "Congo", "Gine": "Guinea", "Gabon": "Gabon", "Zambiya": "Zambia", "Zimbabve": "Zimbabwe", "Uganda": "Uganda",
 "Kenya": "Kenya", "Tanzanya": "Tanzania", "Angola": "Angola", "Benin": "Benin", "Togo": "Togo", "Yeşil Burun Adaları": "Cape Verde",
 "Ekvator Ginesi": "Equatorial Guinea", "Mozambik": "Mozambique", "Namibya": "Namibia", "Madagaskar": "Madagascar",
 "Moritanya": "Mauritania", "Nijer": "Niger", "Sudan": "Sudan", "Etiyopya": "Ethiopia", "Ruanda": "Rwanda",
 "Gambiya": "Gambia", "Sierra Leone": "Sierra Leone", "Liberya": "Liberia", "Malavi": "Malawi", "Botsvana": "Botswana",
 "Gine-Bissau": "Guinea-Bissau", "Komorlar": "Comoros", "Burundi": "Burundi", "Lesotho": "Lesotho", "Esvatini": "Eswatini",
}
GENC = re.compile(r"(\bU-?\d{2}\b|\(K\)|kadın|women|olimpik|\bB\b$)", re.I)
MILLI_CN = re.compile(r"(dünya kupası|uluslar|hazırlık|elemeleri|avrupa şampiyonası|copa am|afrika uluslar|asya kupası|"
                      r"gold cup|konfederasyon|world cup|nations|friendl|qualif)", re.I)


def en_ad(tr):
    tr = (tr or "").strip()
    if not tr or GENC.search(tr): return None
    return TR_EN.get(tr)


def milli_mi(f):
    h, a = en_ad(f.get("h")), en_ad(f.get("a"))
    if not h or not a: return None
    cn = (f.get("cn") or f.get("ln") or "")
    if cn and GENC.search(cn): return None
    if str(f.get("lg", "")).startswith("i") or MILLI_CN.search(cn): return h, a
    return None


def _yaz(yol, obj):
    tmp = yol + ".tmp"
    json.dump(obj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, yol)


def golge(R, M, P, oyn):
    """Kilitli gölge kayıt: başlamamış milli maçlara Elo + piyasa 1X2 (bir kez). Sonuç CC0'dan eklenir."""
    try: G = json.load(open(GOLGE, encoding="utf-8"))
    except Exception: G = {"aciklama": "YH-20 gölge: milli maçlarda Elo 1X2 ve piyasa 1X2, maçtan önce kilitli", "kayit": []}
    try: fx = json.load(open(os.path.join(DATA, "fixtures.json"), encoding="utf-8"))
    except Exception: fx = []
    simdi = datetime.now(timezone(timedelta(hours=3)))
    var = {(k["d"], k["h"], k["a"]) for k in G["kayit"]}
    yeni = 0
    for f in fx:
        mm = milli_mi(f)
        if not mm: continue
        anah = (f.get("d"), f.get("h"), f.get("a"))
        if anah in var: continue
        try: bas = datetime.strptime(f"{f['d']} {f.get('t') or '00:00'}", "%Y-%m-%d %H:%M").replace(tzinfo=simdi.tzinfo)
        except Exception: continue
        if bas <= simdi: continue
        h, a = mm
        if h not in R or a not in R: continue
        dr = R[h] - R[a] + P["H"]          # tarafsız saha bilgisi bültende yok → ev avantajı varsayılır (kayda işlenir)
        pe = p1x2(dr, M)
        pz = f.get("pz") or {}
        pm = [pz.get("1"), pz.get("X"), pz.get("2")] if f.get("pzy") == "p" else None
        G["kayit"].append({"d": f["d"], "t": f.get("t"), "h": f["h"], "a": f["a"], "en": [h, a], "cn": f.get("cn"),
                           "dr": round(dr, 1), "elo": [round(x, 4) for x in pe], "piyasa": pm,
                           "kilit": simdi.strftime("%Y-%m-%dT%H:%M")})
        var.add(anah); yeni += 1
    # sonuç: CC0 kaydı (tarih ± 1 gün, aynı takımlar, ev/dep sırası bağımsız)
    son = {}
    for d, h, a, hs, as_, t, ntr in oyn[-3000:]:
        son[(d, h, a)] = (hs, as_); son[(d, a, h)] = (as_, hs)
    for k in G["kayit"]:
        if k.get("sonuc"): continue
        d0 = datetime.strptime(k["d"], "%Y-%m-%d")
        for g in (0, -1, 1):
            dd = (d0 + timedelta(days=g)).strftime("%Y-%m-%d")
            s = son.get((dd, k["en"][0], k["en"][1]))
            if s: k["sonuc"] = list(s); break
    G["guncelleme"] = simdi.strftime("%Y-%m-%dT%H:%M")
    _yaz(GOLGE, G)
    return yeni, len(G["kayit"])


def main():
    metin = indir()
    oyn, gel = satirlar(metin)
    try: eski = json.load(open(CIKTI, encoding="utf-8"))
    except Exception: eski = {}
    P = dict(P0, **(eski.get("params") or {}))
    # 1X2 eşlemesi: son 12 yılın FIFA içi maçları (yalnız maç öncesi dr ile)
    drs = [0.0] * len(oyn)
    def kay(i, dr): drs[i] = dr
    R, son = puanla(oyn, P, kay)
    sinir = (datetime.now(timezone.utc) - timedelta(days=365 * 12)).strftime("%Y-%m-%d")
    idx = [i for i, m in enumerate(oyn) if m[0] >= sinir and not FIFA_DISI.search(m[5])]
    y = [0 if oyn[i][3] > oyn[i][4] else (1 if oyn[i][3] == oyn[i][4] else 2) for i in idx]
    M = sirali_lojit([drs[i] / 400.0 for i in idx], y)
    akt = (datetime.now(timezone.utc) - timedelta(days=365 * 4)).strftime("%Y-%m-%d")
    puan = {t: round(r, 1) for t, r in sorted(R.items(), key=lambda kv: -kv[1]) if son.get(t, "") >= akt}
    cikti = {"madde": "YH-20", "kaynak": "martj42/international_results (CC0) — yalnız türetilmiş puan",
             "guncelleme": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "son_mac": oyn[-1][0], "n_mac": len(oyn),
             "params": P, "esleme": M, "esleme_n": len(idx), "kapi": eski.get("kapi"), "puan": puan}
    _yaz(CIKTI, cikti)
    yeni, top = golge(R, M, P, oyn)
    ilk = list(puan.items())[:5]
    print(f"milli Elo: {len(oyn)} maç, son {oyn[-1][0]}, aktif takım {len(puan)}, eşleme {M}; ilk 5 {ilk}; gölge +{yeni} (toplam {top})")


if __name__ == "__main__":
    main()
