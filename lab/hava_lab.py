#!/usr/bin/env python3
"""🌧️ YH-32 laboratuvarı: maç günü havası (yağış / rüzgâr) 2,5 A/Ü piyasa olasılığına bilgi ekliyor mu? Zaman sıralı sınama.

Yalnız ölçüm; üretimi değiştirmez. GitHub Actions'ta çalışır (bu iki kaynağa geliştirme ortamından erişilemiyor).
Kaynaklar (ücretsiz, anahtarsız):
  • Wikidata (CC0): takım adı → kulüp öğesi → iç saha stadı (P115) → koordinat (P625); stat yoksa kulübün kendi koordinatı.
    Yalnız türetilmiş tablo yazılır: data/stadyum_koord.json {"<lig>|<takım>": [enlem, boylam, kaynak]}.
  • Open-Meteo geçmiş hava API'si (CC BY 4.0, atıf: https://open-meteo.com/): saatlik yağış, 10 m rüzgâr, 2 m sıcaklık.
    Ham değerler yalnız iş akışı önbelleğinde (.hava_onbellek/, actions/cache); depoya ve siteye girmez.
Önceden kayıtlı tasarım:
  • Veri: data/season.json, 2,5 A/Ü oranı ve sonucu olan lig maçları; ev sahibinin stadı = maç yeri.
  • Başlama saati arşivde yok → yerel 12:00–21:59 saatlerinin ortalaması / toplamı (sabit pencere; önceden seçildi).
  • Özellikler: x1 = log(1 + pencere yağış toplamı mm), x2 = max(0, ortalama rüzgâr − 20 km/sa) / 10.
  • Aday: logit q = logit p_piyasa(üst) + a·x1 + b·x2;  taban: power marj ayırma (YH-29/30 ile aynı).
  • Yürüyen pencere: 2026-01'den aylık genişleyen katlar; (a, b) yalnız katın öncesindeki havalı maçlarla seçilir (≥ 300).
Kapı (SK): kapsam (havası bilinen sınama maçı) ≥ %80 ve ≥ 1.500 maç, yoksa "veri bekliyor" · ΔLL lig×gün blok bootstrap
B = 2000 %95 GA üst < 0 · iki zaman yarısında ΔLL < 0 · ΔBrier ≤ 0 · tek yanlı p ≤ α_t (alfa yatırımı fb_model-<yıl>,
yalnız kapsam yeterliyken harcanır). Betimsel (karar değil): yağışlı (≥ 5 mm) ve rüzgârlı (≥ 30 km/sa) alt kümeler.
Open-Meteo kotası (saatte ~5.000 ağırlıklı çağrı) yüzünden veri birkaç gecede tamamlanır; her çalışma bütçe kadar çeker.

  python3 lab/hava_lab.py          → data/hava_lab.json (+ data/stadyum_koord.json)
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import date, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))
from motivasyon_lab import power, ll2, br2, blok_boot  # noqa: E402

UA = {"User-Agent": "OXXai-lab/1.0 (https://bulutoxx.github.io/; yalniz olcum)"}
WD = "https://www.wikidata.org/w/api.php"
OM = "https://archive-api.open-meteo.com/v1/archive"
ONB = os.path.join(ROOT, ".hava_onbellek")
KOORD = os.path.join(DATA, "stadyum_koord.json")
BUTCE_SN = float(os.environ.get("HAVA_BUDGET", "2700"))
MAKS_CAGRI = int(os.environ.get("HAVA_MAKS_CAGRI", "4200"))   # konum-gün (Open-Meteo ağırlığı)
ARALIK = 1.0                     # sn / Open-Meteo isteği
IZ = np.round(np.arange(-0.4, 0.401, 0.02), 3)
MIN_KAPSAM, MIN_N = 0.80, 1500
KULUP = {"Q476028", "Q103229495", "Q15944511", "Q847017", "Q12973014"}
T0 = time.time()


def al(url, deneme=2):
    for i in range(deneme):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            print("ağ:", e.code, url.split("?")[0])
            if e.code == 429: return "KOTA"
            if e.code < 500: return None
        except Exception as e:
            print("ağ:", type(e).__name__, str(e)[:100])
        time.sleep(4 * (i + 1))
    return None


def avrupa(la, lo): return 27 <= la <= 72 and -32 <= lo <= 46


# ---------------------------------------------------------------- koordinatlar (Wikidata, CC0)
def _p625(cl):
    for c in cl.get("P625", []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if v: return float(v["latitude"]), float(v["longitude"])
    return None


def _idler(cl, p):
    return [c["mainsnak"]["datavalue"]["value"]["id"] for c in cl.get(p, []) if c.get("mainsnak", {}).get("datavalue")]


def varliklar(ids):
    out = {}
    for i in range(0, len(ids), 50):
        r = al(f"{WD}?action=wbgetentities&format=json&props=claims&ids={'|'.join(ids[i:i + 50])}")
        if isinstance(r, dict): out.update(r.get("entities", {}))
    return out


ULKE = {"en": {"Q145", "Q21", "Q25"}, "sc": {"Q145", "Q22"}, "es": {"Q29", "Q228"}, "it": {"Q38", "Q238"}, "de": {"Q183"},
        "fr": {"Q142", "Q235"}, "nl": {"Q55"}, "pt": {"Q45"}, "be": {"Q31"}, "gr": {"Q41"}, "tr": {"Q43"}}


def _aday(lg, ids):
    E = varliklar(ids); izin = ULKE.get(lg.rstrip("0123456789"), set())
    for i in ids:
        cl = E.get(i, {}).get("claims", {})
        if not (set(_idler(cl, "P31")) & KULUP or "Q2736" in _idler(cl, "P641")): continue
        ul = set(_idler(cl, "P17"))
        if ul and izin and not (ul & izin): continue
        for st in _idler(cl, "P115")[:2]:
            k = _p625(varliklar([st]).get(st, {}).get("claims", {}))
            if k and avrupa(*k): return [round(k[0], 3), round(k[1], 3), "stat"]
        k = _p625(cl)
        if k and avrupa(*k): return [round(k[0], 3), round(k[1], 3), "kulup"]
    return None


def koordinat_bul(lg, ad):
    # 1) tam metin arama, yalnız futbol kulübü öğeleri (haswbstatement); 2) ad araması (eski yol)
    for q in (f"{ad} haswbstatement:P31=Q476028", f"{ad.replace('.', ' ')} haswbstatement:P31=Q476028"):
        r = al(f"{WD}?action=query&list=search&format=json&srlimit=6&srsearch={urllib.parse.quote(q)}")
        ids = [x["title"] for x in (r.get("query", {}).get("search", []) if isinstance(r, dict) else []) if x.get("title", "").startswith("Q")]
        if ids:
            k = _aday(lg, ids)
            if k: return k
    for q in (ad, ad + " FC"):
        r = al(f"{WD}?action=wbsearchentities&format=json&language=en&type=item&limit=7&search={urllib.parse.quote(q)}")
        ids = [x["id"] for x in r.get("search", [])] if isinstance(r, dict) else []
        if ids:
            k = _aday(lg, ids)
            if k: return k
    return None


def koordinatlar(takimlar):
    try: K = json.load(open(KOORD, encoding="utf-8"))
    except Exception: K = {}
    tablo = K.get("tablo", {}); dene = K.get("bulunamadi", {}) if K.get("surum") == 2 else {}
    yeni = 0
    for t in sorted(takimlar):
        if t in tablo or dene.get(t, "") >= (date.today() - timedelta(days=30)).isoformat(): continue
        if time.time() - T0 > 900: break
        k = koordinat_bul(*t.split("|", 1))
        if k: tablo[t] = k; dene.pop(t, None); yeni += 1
        else: dene[t] = date.today().isoformat()
    K = {"surum": 2, "kaynak": "Wikidata (CC0) — kulüp → iç saha stadı (P115) → koordinat (P625); yalnız türetilmiş tablo",
         "guncelleme": date.today().isoformat(), "n": len(tablo), "tablo": dict(sorted(tablo.items())),
         "bulunamadi": dict(sorted(dene.items()))}
    json.dump(K, open(KOORD, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"koordinat: {len(tablo)} takım ({yeni} yeni), bulunamayan {len(dene)}")
    return tablo


# ---------------------------------------------------------------- hava (Open-Meteo, CC BY 4.0) — ham değer yalnız önbellekte
def hava_topla(istek):
    """istek: {(la, lo): set(tarih)} → önbellek {"la,lo": {tarih: [yagis_top, ruzgar_ort, sicaklik_ort] | None}}.
    Gün başına TEK istek, o gün maçı olan tüm konumlar birlikte (≤ 40 konum / istek): ağırlık = konum-gün sayısı, gecikme az."""
    os.makedirs(ONB, exist_ok=True)
    yol = os.path.join(ONB, "hava.json")
    try: C = json.load(open(yol, encoding="utf-8"))
    except Exception: C = {}
    son = (date.today() - timedelta(days=6)).isoformat()
    gun_yer = {}
    for (la, lo), gunler in istek.items():
        var = C.setdefault(f"{la},{lo}", {})
        for g in gunler:
            if g not in var and g <= son: gun_yer.setdefault(g, []).append((la, lo))
    cagri = agirlik = 0; durum = "tamam"
    for g in sorted(gun_yer, reverse=True):          # önce yeni günler (sınama dilimi)
        L = sorted(gun_yer[g])
        for i in range(0, len(L), 40):
            if agirlik >= MAKS_CAGRI or time.time() - T0 > BUTCE_SN: durum = "butce"; break
            P = L[i:i + 40]; t1 = time.time()
            r = al(f"{OM}?latitude={','.join(str(a) for a, _ in P)}&longitude={','.join(str(b) for _, b in P)}"
                   f"&start_date={g}&end_date={g}&hourly=precipitation,wind_speed_10m,temperature_2m&timezone=auto")
            cagri += 1; agirlik += len(P)
            if r == "KOTA": durum = "kota"; break
            if isinstance(r, dict): r = [r]
            for (la, lo), x in zip(P, r if isinstance(r, list) else [None] * len(P)):
                v = None
                if isinstance(x, dict) and "hourly" in x:
                    H = x["hourly"]
                    a = [(p, w, s) for t, p, w, s in zip(H["time"], H["precipitation"], H["wind_speed_10m"], H["temperature_2m"])
                         if t[:10] == g and 12 <= int(t[11:13]) <= 21 and None not in (p, w, s)]
                    if a:
                        a = np.array(a); v = [round(float(a[:, 0].sum()), 2), round(float(a[:, 1].mean()), 1), round(float(a[:, 2].mean()), 1)]
                if v is not None or isinstance(r, list): C[f"{la},{lo}"][g] = v
            time.sleep(max(0.0, ARALIK - (time.time() - t1)))
            if cagri % 25 == 0: json.dump(C, open(yol, "w", encoding="utf-8"))
        if durum != "tamam": break
    json.dump(C, open(yol, "w", encoding="utf-8"))
    print(f"hava: {cagri} istek, {agirlik} konum-gün, durum {durum}")
    return C, agirlik, durum


# ---------------------------------------------------------------- deney
def main():
    try: onceki = json.load(open(os.path.join(DATA, "hava_lab.json"), encoding="utf-8"))
    except Exception: onceki = {}
    S = json.load(open(os.path.join(DATA, "season.json"), encoding="utf-8"))
    rows = []
    for lg, v in S.items():
        for m in v.get("matches", []):
            ou, ft = m.get("ou"), m.get("ft")
            if not ft or ft[0] is None or not ou or len(ou) != 2 or not all(ou) or min(ou) <= 1: continue
            rows.append((m["d"][:10], lg, f"{lg}|{m['h']}", float(power(ou)[0]), sum(ft) > 2))
    rows.sort()
    takimlar = {r[2] for r in rows}
    erisim = {"wikidata": isinstance(al(f"{WD}?action=wbgetentities&format=json&ids=Q9617&props=info"), dict),
              "open_meteo": isinstance(al(f"{OM}?latitude=41&longitude=29&start_date=2025-09-01&end_date=2025-09-01&daily=precipitation_sum"), dict)}
    print("erişim:", erisim)
    tablo = koordinatlar(takimlar) if erisim["wikidata"] else (json.load(open(KOORD, encoding="utf-8")).get("tablo", {}) if os.path.exists(KOORD) else {})
    istek = {}
    for d, lg, t, _, _ in rows:
        if t in tablo: istek.setdefault((tablo[t][0], tablo[t][1]), set()).add(d)
    C, cagri, durum = hava_topla(istek) if erisim["open_meteo"] else ({}, 0, "erisim_yok")

    def hv(d, t):
        if t not in tablo: return None
        return (C.get(f"{tablo[t][0]},{tablo[t][1]}") or {}).get(d)
    H = [hv(r[0], r[2]) for r in rows]
    d_ = np.array([r[0] for r in rows]); lg = np.array([r[1] for r in rows])
    p = np.array([r[3] for r in rows]); y = np.array([r[4] for r in rows])
    has = np.array([h is not None for h in H])
    yag = np.array([h[0] if h else 0.0 for h in H]); ruz = np.array([h[1] if h else 0.0 for h in H])
    x1 = np.log1p(yag); x2 = np.maximum(0, ruz - 20) / 10
    Lp = np.log(np.clip(p, 1e-9, 1)) - np.log(np.clip(1 - p, 1e-9, 1))

    def q(m, a, b): return 1 / (1 + np.exp(-(Lp[m] + a * x1[m] + b * x2[m])))
    cuts = [f"2026-{M:02d}-01" for M in range(1, 13)] + ["9999"]
    Q = p.copy(); katlar = []
    for a_, b_ in zip(cuts[:-1], cuts[1:]):
        tr = (d_ < a_) & has; te = (d_ >= a_) & (d_ < b_)
        if not te.any(): continue
        best = (0.0, 0.0)
        if tr.sum() >= 300:
            A = IZ[:, None, None]; B = IZ[None, :, None]
            z = Lp[tr][None, None, :] + A * x1[tr][None, None, :] + B * x2[tr][None, None, :]
            qq = 1 / (1 + np.exp(-z)); yy = y[tr][None, None, :]
            L = -np.where(yy, np.log(np.clip(qq, 1e-9, 1)), np.log(np.clip(1 - qq, 1e-9, 1))).sum(2)
            i, j = np.unravel_index(np.argmin(L), L.shape); best = (float(IZ[i]), float(IZ[j]))
        mm = te & has; Q[mm] = q(mm, *best)
        katlar.append({"kat": a_, "n_sinama": int(te.sum()), "n_sinama_havali": int(mm.sum()), "n_egitim_havali": int(tr.sum()),
                       "a_yagis": best[0], "b_ruzgar": best[1]})
        print(katlar[-1])
    te_all = d_ >= cuts[0]
    kapsam = float(has[te_all].mean()) if te_all.any() else 0.0
    m = te_all & has
    blok = np.array([f"{l}|{x}" for l, x in zip(lg, d_)])
    sonuc = None; gecti = False; yeterli = bool(kapsam >= MIN_KAPSAM and m.sum() >= MIN_N)
    alan_k = f"fb_model-{date.today().year}"; yol_fb = os.path.join(DATA, "fb_guc.json")
    try: A = json.load(open(yol_fb, encoding="utf-8"))
    except Exception: A = {}
    if m.sum() >= 200:
        dl = (ll2(Q, y) - ll2(p, y))[m]; db = (br2(Q, y) - br2(p, y))[m]
        dt = d_[m]; s2 = sorted(dt)[len(dt) // 2]; h2 = dt >= s2
        r = blok_boot(dl, blok[m]); rb = blok_boot(db, blok[m])
        r["yari1"] = round(float(dl[~h2].mean()), 6); r["yari2"] = round(float(dl[h2].mean()), 6)
        import oxx_ogren as O
        alfa = float(O.yatirim_alfa(A, alan_k, {"sinyal": {"kaynak": "literatür (yağış/rüzgâr gol sayısını düşürür)"}})) if A and yeterli else 0.0
        gecti = bool(yeterli and r["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and rb["fark"] <= 0 and r["p_tek"] <= alfa)

        def alt(msk):
            mm = m & msk
            return {"n": int(mm.sum()), "dll": round(float((ll2(Q, y) - ll2(p, y))[mm].mean()), 5) if mm.any() else None,
                    "ust_gercek": round(float(y[mm].mean()), 4) if mm.any() else None,
                    "ust_piyasa": round(float(p[mm].mean()), 4) if mm.any() else None}
        sonuc = {"dll": r, "dbrier": rb, "yarilar_siniri": s2, "alfa_t": round(alfa, 5),
                 "alt_kume": {"yagisli_5mm": alt(yag >= 5), "ruzgarli_30": alt(ruz >= 30), "kuru_sakin": alt((yag < 0.5) & (ruz < 20))}}
        print(json.dumps(sonuc, ensure_ascii=False))
    karar = "gecti" if gecti else ("reddedildi" if yeterli else ("beklemede (erişim yok)" if not all(erisim.values()) else "veri bekliyor"))
    karne = {"tarih": date.today().isoformat(), "madde": "YH-32", "erisim": erisim, "karar": karar, "kapi_gecti": gecti,
             "n_mac": len(rows), "n_takim": len(takimlar), "n_takim_koordinatli": sum(1 for t in takimlar if t in tablo),
             "n_havali": int(has.sum()), "sinama_kapsam": round(kapsam, 4), "n_sinama_havali": int(m.sum()),
             "hava_cagri": cagri, "hava_durum": durum, "katlar": katlar, "sonuc": sonuc,
             "tasarim": "logit q = logit p_power(üst) + a·log1p(yağış 12–22 mm) + b·max(0, rüzgâr−20)/10; aylık genişleyen katlar",
             "atif": "Hava verisi: Open-Meteo.com (CC BY 4.0); stat koordinatları: Wikidata (CC0)"}
    karne["alfa_islendi"] = onceki.get("alfa_islendi")
    if A and yeterli and sonuc and not karne["alfa_islendi"]:
        O.yatirim_guncelle(A, alan_k, sonuc["alfa_t"], gecti)
        json.dump(A, open(yol_fb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        karne["alfa_islendi"] = {"tarih": karne["tarih"], "alan": alan_k, "test": 1, "gecti": gecti}
    json.dump(karne, open(os.path.join(DATA, "hava_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", karar, "| kapsam", round(kapsam, 3))


if __name__ == "__main__":
    main()
