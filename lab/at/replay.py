# OXXai at yarışı laboratuvarı — gün gün YENİDEN OYNATMA (replay) sınaması.
# "Geçmiş koşuları hiç oynanmamış gibi yeniden yarıştır": dönemin her yarış günü için tahmin, yayındaki sistemin o
# sabah üreteceği gibi üretilir:
#   - katsayılar: yayındaki gibi `--yenileme` günde bir (varsayılan 7, gece.py YENILEME_GUN) yeniden eğitilir; her
#     yenilemede YALNIZ o günden önceki sonuçlar kullanılır (son KAL_GUN gün kalibrasyon/harman, öncesi zaman
#     ağırlıklı eğitim — model.uretim_modeli ile aynı tarif, aynı λ ızgarası, aynı Henery üsleri),
#   - özellikler: o günden önceki sonuçlarla (ozellik.tablo_kur günü günü işler; gün içi sonuç kullanılmaz),
#   - p_sabah: yalnız model (oransız sabah bilgisi); p_oran: aynı model + nihai ganyan oranı harmanı ("oran bilinir");
#     favori: yalnız nihai oran (marjı ayrılmış q).
# Her koşu puanlanır; gün gün, hipodrom/pist/alan/sınıf kırılımları, kalibrasyon kovaları ve "Altın at" kural
# taraması (seçim ilk 2/3 gün, rapor son 1/3 gün — sınama dilimine bakılmadan) data/at/replay.json'a yazılır.
# Seçilen Altın kural `--kural-yaz` ile data/at/model.json "altin_kural" alanına yazılır (gece.py korur).
# Ham veri yazılmaz; yalnız türetilmiş özetler. tjk.org'a istek atılmaz.
#   AT_KAYNAK=/yol/tjk-data python lab/at/replay.py [--bas 2026-03-16] [--yenileme 7] [--kural-yaz]
import argparse, json, math, os, sys, time
from datetime import date, datetime, timedelta, timezone

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import veri, ozellik as O, model as M  # noqa: E402

KOK = os.path.abspath(os.path.join(BURA, "..", ".."))
CIKTI = os.path.join(KOK, "data", "at", "replay.json")
MODEL_JSON = os.path.join(KOK, "data", "at", "model.json")
KOSU_CIKTI = os.path.join(KOK, "data", "at", "replay_kosular.json")   # at bazında olasılıklar (6'lı ganyan geri testi için)
BAS = "2026-03-16"
# Yayındaki arayüz kuralı (index.html goldOfDay): sabah p ≥ .35, 2. ata fark ≥ .12, günde en çok 3, sıra p + fark
MEVCUT_ALTIN = {"p_min": 0.35, "fark_min": 0.12, "gunluk_max": 3}
P_IZGARA = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55]
F_IZGARA = [0.05, 0.10, 0.15, 0.20, 0.25]
G_IZGARA = [1, 2, 3]
MIN_GUNDE = 0.7    # seçim diliminde gün başına ortalama Altın sayısı alt sınırı
MIN_N = 150        # tam döneme oranlanmış en az seçim sayısı (seçim diliminde ≥ MIN_N · 2/3)
SENARYO = ("sabah", "oran", "favori")


def _g(t):
    return date.fromisoformat(t).toordinal()


def _t(g):
    return date.fromordinal(int(g)).isoformat()


def alan_kovasi(n):
    return "2-6" if n <= 6 else "7-9" if n <= 9 else "10-12" if n <= 12 else "13+"


SINIF_AD = {"M": "maiden", "S": "şartlı", "H": "handikap", "KV": "kısa vade", "G": "grup/kv-g", "SAT": "satış", "?": "diğer"}


def kosu_puanla(p, sira, gam=1.0):
    """Tek koşu: (log-loss, ilk seçim kazandı, ilk seçim ilk 3, ikili sıralı, ikili sırasız, p1, p2, ilk seçim indeksi)."""
    o = np.argsort(-p)
    w = int(np.flatnonzero(sira == 1)[0])
    ll = float(-math.log(max(p[w], 1e-12)))
    ilk = int(sira[o[0]] == 1)
    ilk3 = int(sira[o[0]] <= 3)
    ik_sir = ik_siz = 0
    if len(p) >= 2:
        E = M.sirali_olasiliklar(p, gam, ilk3=False)["ikili"]
        i, j = np.unravel_index(np.argmax(E), E.shape)
        ik_sir = int(sira[i] == 1 and sira[j] == 2)
        ik_siz = int({int(sira[o[0]]), int(sira[o[1]])} == {1, 2})
    return [round(ll, 5), ilk, ilk3, ik_sir, ik_siz, round(float(p[o[0]]), 5),
            round(float(p[o[1]]) if len(p) > 1 else 0.0, 5)]


ALAN = ["ll", "ilk", "ilk3", "ik_sir", "ik_siz", "p1", "p2"]


def ozetle(satirlar, s):
    v = [r[s] for r in satirlar if r.get(s)]
    if not v:
        return None
    a = np.array([x[:5] for x in v], float)
    return {"kosu": len(v), "ilk_secim": round(float(a[:, 1].mean()), 4), "ilk3_icinde": round(float(a[:, 2].mean()), 4),
            "ikili_sirali": round(float(a[:, 3].mean()), 4), "ikili_sirasiz": round(float(a[:, 4].mean()), 4),
            "log_loss": round(float(a[:, 0].mean()), 4)}


def bootstrap(d, n=2000, tohum=7):
    d = np.asarray(d, float)
    if len(d) < 5:
        return None
    r = np.random.default_rng(tohum)
    ort = d[r.integers(0, len(d), size=(n, len(d)))].mean(1)
    return [round(float(np.percentile(ort, 2.5)), 4), round(float(np.percentile(ort, 97.5)), 4)]


def wilson(h, n, z=1.96):
    if not n:
        return None
    p = h / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    e = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - e, 4), round(c + e, 4)]


def kirilim(satirlar, anahtar):
    gr = {}
    for r in satirlar:
        gr.setdefault(anahtar(r), []).append(r)
    out = {}
    for k, L in sorted(gr.items(), key=lambda x: -len(x[1])):
        d = {"kosu": len(L)}
        for s in SENARYO:
            o = ozetle(L, s)
            if o:
                d[s] = {"ilk_secim": o["ilk_secim"], "ilk3_icinde": o["ilk3_icinde"], "log_loss": o["log_loss"]}
        both = [r for r in L if r.get("sabah") and r.get("favori")]
        if both:
            dd = np.array([r["sabah"][0] - r["favori"][0] for r in both])
            d["sabah_eksi_piyasa_ll"] = {"fark": round(float(dd.mean()), 4), "ga95": bootstrap(dd), "kosu": len(both)}
            di = np.array([r["sabah"][1] - r["favori"][1] for r in both], float)
            d["sabah_eksi_favori_ilk"] = {"fark": round(float(di.mean()), 4), "ga95": bootstrap(di)}
        out[k] = d
    return out


def altin_sec(satirlar, kural):
    """Günlük Altın seçimleri (arayüzle aynı: aday koşular p + fark büyükten küçüğe, günde en çok gunluk_max)."""
    gun = {}
    for r in satirlar:
        s = r["sabah"]
        fark = s[5] - s[6]
        if s[5] >= kural["p_min"] - 1e-12 and fark >= kural["fark_min"] - 1e-12:
            gun.setdefault(r["tarih"], []).append((s[5] + fark, s[1], s[2]))
    sec = []
    for t, L in gun.items():
        L.sort(key=lambda x: -x[0])
        sec += L[: kural["gunluk_max"]]
    return sec


def altin_olc(satirlar, kural, gun_sayisi):
    sec = altin_sec(satirlar, kural)
    n = len(sec)
    h = sum(x[1] for x in sec)
    return {"n": n, "isabet": round(h / n, 4) if n else None, "ilk3_isabet": round(sum(x[2] for x in sec) / n, 4) if n else None,
            "gunde_ort": round(n / gun_sayisi, 3) if gun_sayisi else 0.0, "isabet_ga95": wilson(h, n)}


def altin_tarama(satirlar, gunler):
    kes = gunler[int(round(len(gunler) * 2 / 3))]
    sec_s = [r for r in satirlar if r["tarih"] < kes and r.get("sabah")]
    sin_s = [r for r in satirlar if r["tarih"] >= kes and r.get("sabah")]
    n_gs, n_gt = sum(1 for g in gunler if g < kes), sum(1 for g in gunler if g >= kes)
    min_n_sec = MIN_N * n_gs / len(gunler)
    tablo = []
    for pm in P_IZGARA:
        for fm in F_IZGARA:
            for gm in G_IZGARA:
                k = {"p_min": pm, "fark_min": fm, "gunluk_max": gm}
                a, b = altin_olc(sec_s, k, n_gs), altin_olc(sin_s, k, n_gt)
                uygun = a["n"] >= min_n_sec and a["gunde_ort"] >= MIN_GUNDE
                tablo.append({**k, "n": a["n"], "isabet": a["isabet"], "ilk3_isabet": a["ilk3_isabet"],
                              "gunde_ort": a["gunde_ort"], "uygun": uygun,
                              "sinama": {"n": b["n"], "isabet": b["isabet"], "ilk3_isabet": b["ilk3_isabet"],
                                         "gunde_ort": b["gunde_ort"]}})
    uy = [r for r in tablo if r["uygun"] and r["isabet"] is not None]
    # seçim YALNIZ seçim dilimine göre: en yüksek kazanma isabeti; eşitlikte daha çok seçim
    en = max(uy, key=lambda r: (r["isabet"], r["n"])) if uy else None
    mevcut = {**MEVCUT_ALTIN, "secim": altin_olc(sec_s, MEVCUT_ALTIN, n_gs), "sinama": altin_olc(sin_s, MEVCUT_ALTIN, n_gt)}
    secilen = None
    if en:
        k = {x: en[x] for x in ("p_min", "fark_min", "gunluk_max")}
        b = altin_olc(sin_s, k, n_gt)
        mi, bi = mevcut["sinama"]["isabet"] or 0.0, b["isabet"] or 0.0
        yener = k == MEVCUT_ALTIN or bi >= mi   # sınama diliminde mevcut kuraldan kötü değilse aday kabul
        secilen = {"aday": {**k, "secim": altin_olc(sec_s, k, n_gs), "sinama": b},
                   "mevcut": mevcut, "karar": ("aday kural" if yener and k != MEVCUT_ALTIN else
                                                "mevcut kural (aday sınama diliminde mevcut kuraldan kötü)" if not yener else "mevcut kural (zaten en iyi)")}
        son = k if yener else dict(MEVCUT_ALTIN)
        ol = b if yener else mevcut["sinama"]
        secilen["kural"] = {**son, "isabet_sinama": ol["isabet"], "n_sinama": ol["n"], "ilk3_isabet_sinama": ol["ilk3_isabet"],
                            "gunde_ort": ol["gunde_ort"], "isabet_ga95_sinama": ol["isabet_ga95"], "kaynak": "replay"}
    else:
        secilen = {"aday": None, "mevcut": mevcut, "karar": "uygun aday yok; mevcut kural",
                   "kural": {**MEVCUT_ALTIN, "isabet_sinama": mevcut["sinama"]["isabet"], "n_sinama": mevcut["sinama"]["n"],
                             "ilk3_isabet_sinama": mevcut["sinama"]["ilk3_isabet"], "gunde_ort": mevcut["sinama"]["gunde_ort"],
                             "isabet_ga95_sinama": mevcut["sinama"]["isabet_ga95"], "kaynak": "replay"}}
    secilen["bolum"] = {"secim": [gunler[0], _t(_g(kes) - 1)], "sinama": [kes, gunler[-1]], "gun_secim": n_gs, "gun_sinama": n_gt,
                        "kosul": f"gunde_ort ≥ {MIN_GUNDE} ve n ≥ {MIN_N} (tam döneme oranlanmış: seçim diliminde ≥ {min_n_sec:.0f})"}
    tablo.sort(key=lambda r: (not r["uygun"], -(r["isabet"] or 0), -r["n"]))
    return tablo, secilen


def yeniden_oynat(kosular, T, bas, bit=None, yenileme=7, gunluk_iz=False, sutun_adlar=None, log=print):
    """Ana döngü. Döner: (satırlar, yenileme kayıtları, at düzeyi olasılıklar). Satır: koşu başına puanlar
    (sabah/oran/favori, her biri ALAN sırasıyla). At düzeyi: [(p_sabah, p_oran|None, kazandı)] kalibrasyon kovaları için."""
    adlar = list(sutun_adlar or O.ADLAR)
    sut = np.array([T["adlar"].index(a) for a in adlar])
    K = M.kume_kur(T)
    tarih, gunler, tam, idx, ilk = M._pencereler(kosular)
    bit = bit or tarih[-1]
    donem = (tarih >= bas) & (tarih <= bit)
    gun_list = sorted(set(tarih[donem]))
    if not gun_list:
        return [], [], []
    g_bas = _g(gun_list[0])
    yen_kayit, satirlar, at_p = [], [], []
    g_son = _g(gun_list[-1])
    r = g_bas
    while r <= g_son:
        r2 = r + yenileme
        hedef = donem & (gunler >= r) & (gunler < r2)
        if not hedef.any():
            r = r2
            continue
        t0 = time.time()
        kal_bas = r - M.KAL_GUN
        Kf = M._ozel(K, (idx >= ilk) & (gunler < kal_bas))
        Kh = M._ozel(K, (gunler >= kal_bas) & (gunler < r) & tam)
        ag = 0.5 ** ((kal_bas - gunler[Kf.kosu_no[Kf.bas]]) / M.YARI_OMUR) if M.YARI_OMUR else None
        m, _ = M.egit(Kf, Kh, T["adlar"], sutun=sut, agirlik=ag, gbm=True, henery=True)
        Ka = M._ozel(K, hedef)
        Xa = Ka.X[:, sut]
        pm = m.p_model(Xa, Ka)
        with np.errstate(invalid="ignore"):
            ph_tum = m.p_harman(Xa, Ka, Ka.q)   # oranı eksik koşularda NaN (koşu içinde kalır, kullanılmaz)
        tamr = np.add.reduceat(np.isfinite(Ka.q).astype(int), Ka.bas) == Ka.n
        for k in range(Ka.R):
            a, b = Ka.bas[k], Ka.bas[k] + Ka.n[k]
            ko = kosular[Ka.kosu_no[a]]
            sira = Ka.sira[a:b]
            if np.sum(sira == 1) != 1:
                continue
            sat = {"tarih": ko["tarih"], "hipodrom": ko["hipodrom"], "kosu": ko["kosu"], "pist": ko["pist"] or "?",
                   "alan": int(Ka.n[k]), "sinif": O.sinif_turu(ko["sinif"])[0]}
            sat["sabah"] = kosu_puanla(pm[a:b], sira, m.gam_m)
            ph = None
            if tamr[k]:
                ph = ph_tum[a:b]
                sat["oran"] = kosu_puanla(ph, sira, m.gam)
                sat["favori"] = kosu_puanla(Ka.q[a:b], sira, 1.0)
            satirlar.append(sat)
            at_p.append((pm[a:b].copy(), None if ph is None else ph.copy(), (sira == 1).astype(float)))
            sat["_a"] = [[str(at["no"]), round(float(pm[a + j]), 4),
                          (round(float(ph[j]), 4) if ph is not None else None),
                          (int(sira[j]) if sira[j] < 99 else None)] for j, at in enumerate(ko["atlar"])]
        yen_kayit.append({"tarih": _t(r), "egitim_kosu": int(Kf.R), "kal_kosu": int(Kh.R), "tahmin_kosu": int(Ka.R),
                          "lambda": m.lam, "alfa": round(m.alfa, 3), "beta": round(m.beta, 3), "c_gbm": round(float(m.cg), 3),
                          "sure_sn": round(time.time() - t0, 1)})
        log(f"yenileme {_t(r)}: eğitim {Kf.R} kal {Kh.R} tahmin {Ka.R} koşu, {time.time() - t0:.0f} sn", flush=True)
        r = r2
    return satirlar, yen_kayit, at_p


def rapor_kur(satirlar, yen_kayit, bas, yenileme, sure, kova):
    gunler = sorted({r["tarih"] for r in satirlar})
    gunluk = []
    for t in gunler:
        L = [r for r in satirlar if r["tarih"] == t]
        d = {"tarih": t, "kosu": len(L)}
        for s in SENARYO:
            v = [r[s][1] for r in L if r.get(s)]
            d[s + "_ilk"] = round(float(np.mean(v)), 3) if v else None
        d["sabah_isabet"] = int(sum(r["sabah"][1] for r in L))
        gunluk.append(d)
    tarama, secilen = altin_tarama(satirlar, gunler)
    ort = [r for r in satirlar if r.get("favori")]
    fark = {}
    for s in ("sabah", "oran"):
        dd = np.array([r[s][0] - r["favori"][0] for r in ort])
        di = np.array([r[s][1] - r["favori"][1] for r in ort], float)
        fark[s + "_eksi_piyasa"] = {"ll_fark": round(float(dd.mean()), 4), "ga95": bootstrap(dd),
                                    "ilk_fark": round(float(di.mean()), 4), "ilk_ga95": bootstrap(di), "kosu": len(ort)}
    out = {
        "olusturma": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "aciklama": ("Gün gün yeniden oynatma: her yarış günü için tahmin, yayındaki sistemin o sabah üreteceği gibi — "
                     f"katsayılar {yenileme} günde bir yalnız o günden önceki sonuçlarla yeniden eğitilir (son {M.KAL_GUN} gün "
                     "kalibrasyon), özellikler o günden önceki sonuçlarla. sabah = yalnız model (oransız); oran = model + nihai "
                     "ganyan oranı harmanı; favori = yalnız nihai oran. Oran/favori yalnız tam oranlı koşularda."),
        "donem": [gunler[0], gunler[-1]] if gunler else [bas, None], "kosu": len(satirlar), "gun": len(gunler),
        "tam_oranli_kosu": len(ort), "yenileme_gun": yenileme, "yenileme_sayisi": len(yen_kayit), "sure_sn": round(sure),
        "ozet": {s: ozetle(satirlar, s) for s in SENARYO},
        "ozet_ortak": {s: ozetle(ort, s) for s in SENARYO},
        "fark": fark,
        "gunluk": gunluk,
        "kirilim": {"hipodrom": kirilim(satirlar, lambda r: r["hipodrom"]),
                    "pist": kirilim(satirlar, lambda r: r["pist"]),
                    "alan_buyuklugu": kirilim(satirlar, lambda r: alan_kovasi(r["alan"])),
                    "sinif": kirilim(satirlar, lambda r: SINIF_AD.get(r["sinif"], r["sinif"]))},
        "altin_tarama": tarama,
        "secilen_altin": secilen,
        "kalibrasyon": kova,
        "yenilemeler": yen_kayit,
        "uyari": "Hobi amaçlıdır; tahmin garanti değildir · 18+",
    }
    return out


def ganyan_baslangic(kaynak=None):
    """(tarih, hipodrom, koşu no) -> isGanyanStart (aynanın günlük program dosyalarından; yoksa anahtar yok).
    Yan ürün: EKURI[(tarih, hipodrom, koşu no)] = ekürili at no grupları (6'lı ayağında tek grup sayılır)."""
    d = os.path.join(kaynak or veri.KAYNAK, "data", "daily")
    out = {}
    EKURI.clear()
    if not os.path.isdir(d):
        return out
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"):
            continue
        try:
            js = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except Exception:
            continue
        for r in js if isinstance(js, list) else []:
            if r.get("venue") not in veri.YERLI:
                continue
            an = (r.get("date") or f[:10], r.get("venue"), int(r.get("raceNo") or 0))
            if "isGanyanStart" in r:
                out[an] = None if r["isGanyanStart"] is None else bool(r["isGanyanStart"])
            eg = [[str(x) for x in g] for g in (r.get("ekuriGroups") or []) if isinstance(g, list) and len(g) > 1]
            if eg:
                EKURI[an] = eg
    return out


EKURI = {}


def kosu_dosyasi(satirlar, yol):
    """Koşu başına at olasılıkları (türetilmiş tahmin + sonuç sırası; ham veri değil), kısa anahtarlarla sıkıştırılmış."""
    gs = ganyan_baslangic()
    ks = [{"id": f'{r["tarih"]}/{r["hipodrom"]}/{r["kosu"]}', "t": r["tarih"], "h": r["hipodrom"], "k": r["kosu"],
           "gs": gs.get((r["tarih"], r["hipodrom"], r["kosu"])), "e": EKURI.get((r["tarih"], r["hipodrom"], r["kosu"]), []),
           "a": r["_a"]} for r in satirlar]
    out = {"v": 1, "aciklama": "id: tarih/hipodrom/koşu no; t: tarih; h: hipodrom; k: koşu no; gs: isGanyanStart (6'lı ganyan "
                              "başlangıcı; günlük program aynada yoksa — 2026-04 öncesi — null); e: ekürili at no grupları; "
                              "a: koşan atlar [at no, p_sabah, p_oran|null (oran eksikse), bitiş sırası|null]. Koşmayan atlar yok. "
                              "Olasılıklar replay.py'nin gün gün yeniden oynatmasından (sızıntısız). Yalnız tek kazananlı koşular.",
           "kosu": len(ks), "kosular": ks}
    tmp = yol + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, yol)
    return sum(1 for k in ks if k["gs"] is not None)


def kova_topla(satirlar_p):
    """satirlar_p: [(p_sabah dizisi, p_oran dizisi|None, y dizisi)] → kalibrasyon kovaları (at düzeyi)."""
    ps, ys, po, yo = [], [], [], []
    for a, b, y in satirlar_p:
        ps.append(a); ys.append(y)
        if b is not None:
            po.append(b); yo.append(y)
    out = {"sabah": M.kovalar(np.concatenate(ps), np.concatenate(ys)) if ps else []}
    out["oran"] = M.kovalar(np.concatenate(po), np.concatenate(yo)) if po else []
    return out


# ---------------------------------------------------------------- replay zayıflıklarına göre kapılı deneyler
# Kapı v4'ünkiyle aynı (deney4.gecer): iki katlı aylık walk-forward, katların ortalama yalnız-model log-loss'u
# düşmeli, ortalama ilk-seçim isabeti düşmemeli, B katı kötüleşmemeli, harman 0,001'den fazla bozulmamalı.
HIP_SIRA = sorted(veri.YERLI)


def baglam_sutunlari(T, kosular):
    """Koşu bağlamı (koşu içinde sabit): alan, pist, mesafe, hipodrom. Doğrusal koşullu logitte etkisizdir
    (koşu içinde sabit), GBM ise bunlarla diğer özelliklerin hipodrom/pist/alan'a göre değişen etkisini öğrenebilir."""
    kid = T["kid"]
    n = np.bincount(kid, minlength=len(kosular))[kid].astype(float)
    pist = np.array([kosular[i]["pist"] for i in kid])
    mes = np.array([kosular[i]["mesafe"] / 1000.0 for i in kid])
    hip = np.array([kosular[i]["hipodrom"] for i in kid])
    cols = {"b_alan": n, "b_cim": (pist == "Çim").astype(float), "b_kum": (pist == "Kum").astype(float), "b_mesafe": mes}
    for h in HIP_SIRA:
        cols["b_hip_" + h] = (hip == h).astype(float)
    return cols


def tablo_ekle(T, cols):
    T2 = dict(T)
    T2["X"] = np.c_[T["X"], np.column_stack(list(cols.values()))]
    T2["adlar"] = list(T["adlar"]) + list(cols)
    return T2


def deney_kapisi(kosular, T, adaylar, log=print):
    """adaylar: [(ad, ek sütunlar sözlüğü, eklenecek özellik adları)] — her biri v4 tabanına karşı tek tek."""
    import deney4 as D
    sonuc = []
    ek_tum = {}
    for _, c, _ in adaylar:
        ek_tum.update(c)
    T2 = tablo_ekle(T, ek_tum) if ek_tum else T
    masa = D.Masa(kosular, T2)
    t0 = time.time()
    E0 = masa.egit(list(O.ADLAR))
    r0, v0 = masa.ozet(*masa.tahmin(E0)[:2])
    log(f"taban: {r0['model']} harman {r0['harman']} ({time.time() - t0:.0f} sn)", flush=True)
    sonuc.append({"deney": "taban (v4 yayın tarifi)", "gecti": None, "model": r0["model"], "harman": r0["harman"],
                  "katlar": {k: {"model": r0["katlar"][k]["model"], "kosu": r0["katlar"][k]["kosu"]} for k in D.KATLAR}})
    for ad, _, adlar in adaylar:
        t1 = time.time()
        E = masa.egit(list(O.ADLAR) + list(adlar))
        r, v = masa.ozet(*masa.tahmin(E)[:2])
        ok = D.gecer(r, r0)
        fm, fh = masa.fark(v, v0, "model"), masa.fark(v, v0, "harman")
        sonuc.append({"deney": ad, "gecti": bool(ok), "model": r["model"], "harman": r["harman"],
                      "katlar": {k: {"model": r["katlar"][k]["model"], "kosu": r["katlar"][k]["kosu"]} for k in D.KATLAR},
                      "fark_model": fm, "fark_harman": fh, "sure_sn": round(time.time() - t1)})
        log(f"{ad}: {'GEÇTİ' if ok else 'elendi'} {r['model']} ΔLL {fm['dll']} {fm['ga95']} ilk {fm['d_ilk']} "
            f"({time.time() - t1:.0f} sn)", flush=True)
    return sonuc


def deney_main(ar):
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    b = baglam_sutunlari(T, kosular)
    hip = {k: v for k, v in b.items() if k.startswith("b_hip_")}
    adaylar = [("D1: koşu bağlamı GBM'ye (alan, pist, mesafe, hipodrom; doğrusal katmanda etkisiz)", b, list(b))]
    if "D2" in ar.deney:
        adaylar.append(("D2: yalnız alan + pist + mesafe bağlamı (hipodromsuz)",
                        {k: v for k, v in b.items() if k not in hip}, [k for k in b if k not in hip]))
    dn = deney_kapisi(kosular, T, adaylar)
    try:
        rj = json.load(open(ar.cikti, encoding="utf-8"))
    except Exception:
        rj = {}
    rj["deneyler"] = {"tarih": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                      "kapi": "deney4.gecer: iki kat (A/B) aylık walk-forward; ort. yalnız-model LL düşmeli (>1e-4), ort. ilk seçim "
                              "düşmemeli, B katı LL kötüleşmemeli, harman +0,001'den fazla bozulmamalı",
                      "adimlar": dn}
    json.dump(rj, open(ar.cikti, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bas", default=BAS)
    ap.add_argument("--bit", default=None)
    ap.add_argument("--yenileme", type=int, default=7, help="katsayı yenileme aralığı (gün); yayında 7")
    ap.add_argument("--kural-yaz", action="store_true", help="seçilen Altın kuralı data/at/model.json'a yaz")
    ap.add_argument("--cikti", default=CIKTI)
    ap.add_argument("--kosu-cikti", default=KOSU_CIKTI)
    ap.add_argument("--iz", default=None, help="koşu başına izi bu yola yaz (yalnız yerel deney için; depoya girmez)")
    ap.add_argument("--deney", default=None, help="replay zayıflıklarına göre kapılı deneyler (ör. D1 ya da D1,D2)")
    ar = ap.parse_args()
    if ar.deney:
        return deney_main(ar)
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    print(f"tablo {T['X'].shape}, {time.time() - t0:.0f} sn", flush=True)
    satirlar, yen, at_p = yeniden_oynat(kosular, T, ar.bas, ar.bit, ar.yenileme)
    kova = kova_topla(at_p)
    sure = time.time() - t0
    n_gs = kosu_dosyasi(satirlar, ar.kosu_cikti)
    print(f"koşu dosyası: {len(satirlar)} koşu ({n_gs} koşuda ganyan başlangıç bayrağı)")
    for r in satirlar:
        r.pop("_a", None)
    out = rapor_kur(satirlar, yen, ar.bas, ar.yenileme, sure, kova)
    try:   # kapılı deney sonuçları (--deney) ve idman araştırması notu yeniden oynatmada korunur
        eski = json.load(open(ar.cikti, encoding="utf-8"))
        for k in ("deneyler", "idman_verisi"):   # elle/deneyle üretilen alanlar
            if eski.get(k):
                out[k] = eski[k]
    except Exception:
        pass
    os.makedirs(os.path.dirname(ar.cikti), exist_ok=True)
    tmp = ar.cikti + ".tmp"
    json.dump(out, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, ar.cikti)
    if ar.iz:
        json.dump(satirlar, open(ar.iz, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    if ar.kural_yaz and not out["secilen_altin"]["karar"].startswith(("aday kural", "mevcut kural (zaten")):
        print("altin_kural YAZILMADI:", out["secilen_altin"]["karar"])
    elif ar.kural_yaz:
        try:
            mj = json.load(open(MODEL_JSON, encoding="utf-8"))
            k = dict(out["secilen_altin"]["kural"])
            k["donem"] = out["donem"]; k["tarih"] = out["olusturma"][:10]
            mj["altin_kural"] = k
            json.dump(mj, open(MODEL_JSON + ".tmp", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            os.replace(MODEL_JSON + ".tmp", MODEL_JSON)
            print("altin_kural yazıldı:", k)
        except Exception as e:
            print("altin_kural yazılamadı:", e)
    o = out["ozet"]
    print(f"bitti: {out['kosu']} koşu, {out['gun']} gün, {sure:.0f} sn")
    for s in SENARYO:
        print(s, o[s])
    print("altın:", out["secilen_altin"]["karar"], out["secilen_altin"]["kural"])


if __name__ == "__main__":
    main()
