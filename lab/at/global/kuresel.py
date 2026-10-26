# BULUTOXX at yarışı laboratuvarı — KÜRESEL katkılar (yabancı literatür / kamu düzenleyici tablolarından aktarılan önseller
# ve yöntemler). Gece akışına doğrudan bağlı DEĞİL; kapıdan geçenler oncul.json → GLOBAL_SECILI üzerinden bağlanır.
#
# Adaylar (deney masası: lab/at/deney_global.py, deney4 iki katlı kapı):
#   gl_wfa       : yaşa göre kilo (Weight-For-Age) önseli. Kaynak: ARCI-010-020 (Association of Racing Commissioners
#                  International, model kurallar, Section D, Table 1 "Scale of Weights for Age"). ABD de Türkiye gibi
#                  1 Ocak doğum günü kullanır → ay×mesafe×yaş tablosu doğrudan aktarılır. Özellik: atın fizyolojik WFA
#                  avantajı (kg, alan ortalamasına göre) ve "etkin kilo" = (kilo − alan ort.) + (WFA avantajı − alan ort.).
#                  Yalnız bugünkü programdaki alanlara (yaş, kilo, ay, mesafe) dayanır → geçmiş/sonuç bilgisi yok.
#   gl_piyasa    : piyasa olasılığının kayırma–uzun atış (favourite-longshot) düzeltmeli dönüşümü (Shin 1992/93;
#                  odds-ratio, Cheung 2015; Clarke vd. 2017). Yöntem harman öncesi dönemde (sınama dışı) seçilir;
#                  harmanda log q yerine kullanılır (yalnız-model değişmez).
#   gl_lambdarank: GBM katmanının amacı koşu-içi softmax yerine LambdaMART/LambdaRank (Burges 2010; LightGBM
#                  'lambdarank'), etiket = ilk 3 sıralaması. Doğrusal katman ve kalibrasyon aynı.
import math

import numpy as np

# ---------------------------------------------------------------- WFA (ARCI-010-020, Section D, Table 1 — kamuya açık model kural metni)
# Mesafeler: ½ mil, 6 f, 1 mil, 1¼ mil, 1½ mil, 2 mil  → metre
WFA_M = [804.7, 1207.0, 1609.3, 2011.7, 2414.0, 3218.7]
# 3 yaş (lb), ay 1..12
WFA3 = [[117, 114, 107, 101, 98, 96], [117, 114, 107, 101, 98, 96], [119, 117, 111, 107, 104, 102],
        [119, 117, 111, 107, 104, 102], [121, 119, 113, 111, 108, 106], [123, 121, 115, 113, 111, 109],
        [125, 123, 117, 116, 114, 112], [126, 125, 119, 118, 117, 114], [127, 126, 121, 120, 119, 117],
        [128, 127, 122, 121, 121, 119], [129, 128, 123, 122, 122, 120], [129, 128, 123, 122, 122, 120]]
_ORTAK = [[130, 130, 128, 127, 126, 126], [130, 130, 128, 127, 126, 126],                    # Mar, Nis
          [130, 130, 127, 127, 126, 126],                                                      # May
          [130, 130, 126, 126, 126, 126], [130, 130, 126, 126, 126, 126],                    # Haz, Tem
          [130, 130, 126, 126, 126, 125], [130, 130, 126, 126, 126, 125],                    # Ağu, Eyl
          [130, 130, 126, 126, 126, 124], [130, 130, 126, 126, 126, 124], [130, 130, 126, 126, 126, 124]]  # Eki–Ara
# 4 yaş (lb): Ocak–Şubat farklı, Mart'tan itibaren 5+ ile aynı
WFA4 = [[130, 130, 127, 125, 124, 124], [130, 130, 127, 125, 124, 124]] + _ORTAK
# 5+ yaş (lb)
WFA5 = [[130, 130, 128, 127, 126, 126], [130, 130, 128, 127, 126, 126]] + _ORTAK
assert len(WFA3) == len(WFA4) == len(WFA5) == 12
# 2 yaş (lb), yalnız Ağustos–Aralık, ½ mil–1 mil (daha uzunlar için tablo yok → en yakın sütun)
WFA2 = {8: [105, 102, None], 9: [108, 105, 96], 10: [111, 108, 99], 11: [114, 111, 102], 12: [114, 111, 102]}
LB_KG = 0.45359237


def _ara(m, satir):
    """log-mesafe doğrusal ara değerleme (uçlarda sabit)."""
    xs = [math.log(x) for x in WFA_M[:len(satir)]]
    ys = list(satir)
    while ys and ys[-1] is None:
        xs.pop(); ys.pop()
    return float(np.interp(math.log(max(m, 1.0)), xs, ys))


def wfa_avantaj_kg(yas, ay, mesafe):
    """Atın 5+ yaşa göre fizyolojik kilo avantajı (kg, ≥ 0). Bilinmeyen yaş → 0."""
    try:
        yas = int(yas)
    except (TypeError, ValueError):
        return 0.0
    if yas >= 5 or not (1 <= ay <= 12) or not mesafe:
        return 0.0
    tam = _ara(mesafe, WFA5[ay - 1])
    if yas == 4:
        w = _ara(mesafe, WFA4[ay - 1])
    elif yas == 3:
        w = _ara(mesafe, WFA3[ay - 1])
    elif yas <= 2:
        satir = WFA2.get(ay) or WFA2[8]           # tablo dışı ay: en erken sütun (en büyük avantaj)
        w = _ara(mesafe, satir)
    else:
        return 0.0
    return max(tam - w, 0.0) * LB_KG


GL_WFA_ADLAR = ["gl_wfa_av", "gl_etkin_kilo", "gl_wfa_x_mes"]


def wfa_satirlar(kosu):
    """Koşu programından (yaş, kilo, ay, mesafe) gl_wfa özellikleri. Sonuç/geçmiş kullanmaz."""
    ay = int(kosu["tarih"][5:7])
    mes = kosu["mesafe"] or 1400
    av = [wfa_avantaj_kg(a.get("yas"), ay, mes) for a in kosu["atlar"]]
    kilolar = [a["kilo"] for a in kosu["atlar"] if a["kilo"]]
    kort = sum(kilolar) / len(kilolar) if kilolar else None
    aort = sum(av) / len(av)
    out = []
    for a, v in zip(kosu["atlar"], av):
        kf = (a["kilo"] - kort) if (a["kilo"] and kort) else 0.0
        d = v - aort
        out.append([d, kf + d, d * math.log(mes / 1400.0)])
    return np.asarray(out, float)


def wfa_tablosu(kosular):
    """tablo_kur ile aynı satır sırası (koşu sırası × at sırası)."""
    return np.vstack([wfa_satirlar(k) for k in kosular])


# ---------------------------------------------------------------- piyasa dönüşümleri (kayırma–uzun atış)
def _orantili(pi):
    return pi / pi.sum()


def _shin(pi):
    S = pi.sum()
    if S <= 1.0 + 1e-9:
        return pi / S

    def top(z):
        return np.sum((np.sqrt(z * z + 4 * (1 - z) * pi * pi / S) - z) / (2 * (1 - z)))
    lo, hi = 0.0, 0.999
    for _ in range(60):
        z = 0.5 * (lo + hi)
        if top(z) > 1.0:
            lo = z
        else:
            hi = z
    z = 0.5 * (lo + hi)
    p = (np.sqrt(z * z + 4 * (1 - z) * pi * pi / S) - z) / (2 * (1 - z))
    return p / p.sum()


def _odds_ratio(pi):
    S = pi.sum()
    if S <= 1.0 + 1e-9:
        return pi / S
    lo, hi = 1.0, 100.0

    def top(c):
        return np.sum(pi / (c + pi - c * pi))
    for _ in range(80):
        c = math.sqrt(lo * hi)
        if top(c) > 1.0:
            lo = c
        else:
            hi = c
    c = math.sqrt(lo * hi)
    p = pi / (c + pi - c * pi)
    return p / p.sum()


PIYASA_YONTEM = {"orantili": _orantili, "shin": _shin, "odds_ratio": _odds_ratio}


def piyasa_q(oranlar, yontem="shin"):
    """veri.piyasa_q ile aynı arayüz; eksik oran varsa None."""
    if not oranlar or any(o is None for o in oranlar):
        return None
    return list(PIYASA_YONTEM[yontem](1.0 / np.asarray(oranlar, float)))


def q_tablosu(kosular, yontem):
    q = []
    for k in kosular:
        qq = piyasa_q([a["oran"] for a in k["atlar"]], yontem)
        q.extend(qq if qq else [np.nan] * len(k["atlar"]))
    return np.asarray(q, float)


# ---------------------------------------------------------------- LambdaRank GBM amacı
def gbm_egit_lambdarank(M, lgb):
    """model.gbm_egit ile aynı imza; amaç LightGBM 'lambdarank' (etiket: 1.→3, 2.→2, 3.→1, diğer 0)."""
    import os

    def egit(X, K, agirlik=None, ayar=None, init=None, tohum=1):
        a = dict(M.GBM_AYAR, **(ayar or {}))
        sw = (np.ones(K.R) if agirlik is None else np.asarray(agirlik, float))[K.seg]
        lab = np.clip(4 - np.asarray(K.sira, float), 0, 3).astype(int)
        lab[np.asarray(K.sira) >= 99] = 0
        par = {"objective": "lambdarank", "learning_rate": a["ogrenme"], "num_leaves": a["yaprak"],
               "min_data_in_leaf": a["min_yaprak"], "feature_fraction": a["oznitelik_payi"], "bagging_fraction": 0.8,
               "bagging_freq": 1, "lambda_l2": a["l2"], "verbose": -1, "seed": tohum, "deterministic": True,
               "lambdarank_truncation_level": 3, "eval_at": [3],
               "num_threads": min(4, os.cpu_count() or 1)}
        ds = lgb.Dataset(X, label=lab, group=np.asarray(K.n), weight=sw, free_raw_data=False)
        return lgb.train(par, ds, num_boost_round=a["n_agac"])
    return egit


# ---------------------------------------------------------------- bağlama (yalnız oncul.json üzerinden)
def _oncul():
    import json, os
    try:
        return json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "oncul.json"), encoding="utf-8"))
    except Exception:
        return {}


GLOBAL_SECILI = list(_oncul().get("GLOBAL_SECILI", []))          # deney_global.py kapısından geçenler
GLOBAL_SECILI_GRUPLAR = [g for g in GLOBAL_SECILI if g in ("gl_wfa",)]   # ozellik.SECILI_GRUPLAR'a eklenecek gruplar
GL_OZELLIKLER = [(a, "gl_wfa") for a in GL_WFA_ADLAR]

IFADE = {   # gerekçe ifadeleri (değer koşu ortalamasından YÜKSEKSE, DÜŞÜKSE)
    "gl_wfa_av": ("yaşına göre kilo avantajı olmalı (WFA)", "yaşı gereği kilo avantajı yok (WFA)"),
    "gl_etkin_kilo": ("yaşına göre etkin kilosu ağır", "yaşına göre etkin kilosu hafif"),
    "gl_wfa_x_mes": ("uzun mesafede yaş avantajı", "uzun mesafede yaş dezavantajı"),
}
