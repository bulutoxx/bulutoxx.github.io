# BULUTOXX at yarışı laboratuvarı — sızıntısız özellikler.
# Kural: bir koşunun özellikleri yalnız o GÜNDEN ÖNCEKİ sonuçlarla hesaplanır. Günler sırayla işlenir:
# önce o günün bütün koşuları için özellik çıkarılır, sonra durum o günün sonuçlarıyla güncellenir.
# Aynanın memory/*.json özetleri geleceği de içerdiği için KULLANILMAZ.
import math
from collections import deque, defaultdict
from datetime import date

import numpy as np

from veri import piyasa_q

OZELLIKLER = [
    ("yeni", "form"), ("n_kosu", "form"), ("skor_son", "form"), ("skor3", "form"), ("skor5", "form"),
    ("skor10", "form"), ("galibiyet10", "form"), ("ilk3_10", "form"),
    ("geri_son", "fark"), ("geri3", "fark"),
    ("piyasa_son", "piyasa_gecmisi"), ("piyasa3", "piyasa_gecmisi"),
    ("log_gun", "dinlenme"), ("uzun_ara", "dinlenme"),
    ("pist_uyum", "pist_mesafe_hipodrom"), ("pist_payi", "pist_mesafe_hipodrom"),
    ("mesafe_uyum", "pist_mesafe_hipodrom"), ("mesafe_degisim", "pist_mesafe_hipodrom"),
    ("hipodrom_uyum", "pist_mesafe_hipodrom"),
    ("sinif_degisim", "sinif"),
    ("kilo_fark", "kilo"), ("kilo_degisim", "kilo"),
    ("yas2", "yas"), ("yas3", "yas"), ("yas6p", "yas"),
    ("jokey_gal60", "jokey"), ("jokey_ae", "jokey"),
    ("antrenor_gal60", "antrenor"), ("antrenor_ae", "antrenor"),
    ("jokey_at_n", "jokey_at"), ("jokey_at_uyum", "jokey_at"), ("jokey_degisti", "jokey_at"),
    ("alan_x_form", "alan"),
]
ADLAR = [o[0] for o in OZELLIKLER]
GRUPLAR = sorted({o[1] for o in OZELLIKLER})

ONSEL_GAL = 0.10   # Bayes küçültmede genel kazanma oranı önseli
K_KUCULT = 30.0    # jokey/antrenör için önsel ağırlığı (sanal binicilik sayısı)
K_UYUM = 3.0       # at uyumları için önsel ağırlığı


def gun_no(t):
    return date.fromisoformat(t).toordinal()


class _Pencere:
    """Kayan zaman penceresi: (gün, kazandı, beklenen q) olaylarının toplamlarını tutar."""
    __slots__ = ("g", "n", "w", "e", "wq", "gun")

    def __init__(self, gun):
        self.g, self.n, self.w, self.e, self.wq, self.gun = deque(), 0, 0.0, 0.0, 0.0, gun

    def ekle(self, d, won, q):
        self.g.append((d, won, q)); self.n += 1; self.w += won
        if q is not None:
            self.e += q; self.wq += won

    def buda(self, bugun):
        while self.g and self.g[0][0] < bugun - self.gun:
            d, won, q = self.g.popleft(); self.n -= 1; self.w -= won
            if q is not None:
                self.e -= q; self.wq -= won


def _logit(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


class Durum:
    def __init__(self):
        self.at = defaultdict(list)  # at -> geçmiş koşular (sözlük)
        self.j60 = defaultdict(lambda: _Pencere(60)); self.j365 = defaultdict(lambda: _Pencere(365))
        self.t60 = defaultdict(lambda: _Pencere(60)); self.t365 = defaultdict(lambda: _Pencere(365))
        self.ja = defaultdict(lambda: [0, 0.0])  # (jokey, at) -> [binme, skor toplamı]
        self.sinif = defaultdict(lambda: [0, 0.0])  # sınıf -> [koşu, alan kalitesi toplamı]
        self.genel_sinif = [0, 0.0]

    # --- sınıf düzeyi: o sınıfta koşan atların geçmiş galibiyet sayısının (log) kayan ortalaması
    def sinif_duzeyi(self, k):
        n, s = self.sinif[k]
        gn, gs = self.genel_sinif
        g = gs / gn if gn else 0.0
        return (s + 5 * g) / (n + 5)

    def _alan_kalitesi(self, kosu):
        v = [math.log1p(sum(h["kazandi"] for h in self.at[a["ad"]])) for a in kosu["atlar"]]
        return sum(v) / len(v)

    def ozellik(self, kosu):
        """Bir koşu için (N x d) özellik matrisi; yalnız mevcut durumdan (geçmişten)."""
        bugun = gun_no(kosu["tarih"])
        N = len(kosu["atlar"])
        kilolar = [a["kilo"] for a in kosu["atlar"] if a["kilo"]]
        kilo_ort = sum(kilolar) / len(kilolar) if kilolar else 0.0
        sd_now = self.sinif_duzeyi(kosu["sinif_k"])
        satirlar = []
        for a in kosu["atlar"]:
            g = self.at.get(a["ad"], [])
            son = g[-10:]
            n = len(g)
            f = dict.fromkeys(ADLAR, 0.0)
            f["yeni"] = 1.0 if n == 0 else 0.0
            f["n_kosu"] = math.log1p(n)
            ort_skor = 0.5
            if n:
                sk = [h["skor"] for h in son]
                f["skor_son"] = sk[-1] - 0.5
                f["skor3"] = sum(sk[-3:]) / len(sk[-3:]) - 0.5
                f["skor5"] = sum(sk[-5:]) / len(sk[-5:]) - 0.5
                f["skor10"] = sum(sk) / len(sk) - 0.5
                f["galibiyet10"] = (sum(h["kazandi"] for h in son) + 1 * ONSEL_GAL) / (len(son) + 1)
                f["ilk3_10"] = (sum(h["ilk3"] for h in son) + 1 * 0.3) / (len(son) + 1)
                gr = [h["geri"] for h in son if h["geri"] is not None]
                f["geri_son"] = (son[-1]["geri"] if son[-1]["geri"] is not None else 4.0) - 4.0
                f["geri3"] = (sum(gr[-3:]) / len(gr[-3:]) if gr else 4.0) - 4.0
                pm = [h["piyasa"] for h in son if h["piyasa"] is not None]
                f["piyasa_son"] = son[-1]["piyasa"] if son[-1]["piyasa"] is not None else 0.0
                f["piyasa3"] = sum(pm[-3:]) / len(pm[-3:]) if pm else 0.0
                ara = max(bugun - g[-1]["gun"], 1)
                f["log_gun"] = math.log(ara) - math.log(28)
                f["uzun_ara"] = 1.0 if ara > 90 else 0.0
                tum = sum(h["skor"] for h in g)
                ort_skor = (tum + K_UYUM * 0.5) / (n + K_UYUM)

                def uyum(kosul):
                    s = [h["skor"] for h in g if kosul(h)]
                    return (sum(s) + K_UYUM * ort_skor) / (len(s) + K_UYUM) - ort_skor, len(s)
                pu, pn = uyum(lambda h: h["pist"] == kosu["pist"])
                f["pist_uyum"] = pu; f["pist_payi"] = pn / n
                f["mesafe_uyum"] = uyum(lambda h: abs(h["mesafe"] - kosu["mesafe"]) <= 200)[0]
                if g[-1]["mesafe"] and kosu["mesafe"]:
                    f["mesafe_degisim"] = abs(math.log(kosu["mesafe"] / g[-1]["mesafe"]))
                f["hipodrom_uyum"] = uyum(lambda h: h["hipodrom"] == kosu["hipodrom"])[0]
                f["sinif_degisim"] = sd_now - self.sinif_duzeyi(g[-1]["sinif_k"])
                if a["kilo"] and g[-1]["kilo"]:
                    f["kilo_degisim"] = a["kilo"] - g[-1]["kilo"]
                f["jokey_degisti"] = 1.0 if g[-1]["jokey"] != a["jokey"] else 0.0
            else:
                f["geri_son"] = f["geri3"] = 0.0
            if a["kilo"] and kilo_ort:
                f["kilo_fark"] = a["kilo"] - kilo_ort
            yas = a["yas"] or 0
            f["yas2"] = 1.0 if yas == 2 else 0.0
            f["yas3"] = 1.0 if yas == 3 else 0.0
            f["yas6p"] = 1.0 if yas >= 6 else 0.0
            for (p60, p365, ad_, k1, k2) in ((self.j60, self.j365, a["jokey"], "jokey_gal60", "jokey_ae"),
                                             (self.t60, self.t365, a["antrenor"], "antrenor_gal60", "antrenor_ae")):
                w60 = p60.get(ad_); w365 = p365.get(ad_)
                if w60 is not None:
                    w60.buda(bugun)
                if w365 is not None:
                    w365.buda(bugun)
                n60, g60 = (w60.n, w60.w) if w60 else (0, 0)
                f[k1] = _logit((g60 + K_KUCULT * ONSEL_GAL) / (n60 + K_KUCULT)) - _logit(ONSEL_GAL)
                if w365 is not None and w365.e > 0:
                    # gerçekleşen / piyasanın beklediği galibiyet (365 gün) — 3 sanal galibiyetle küçültülmüş log oranı
                    f[k2] = math.log((w365.wq + 3.0) / (w365.e + 3.0))
            ja = self.ja.get((a["jokey"], a["ad"]))
            if ja and ja[0]:
                f["jokey_at_n"] = math.log1p(ja[0])
                f["jokey_at_uyum"] = (ja[1] + K_UYUM * ort_skor) / (ja[0] + K_UYUM) - ort_skor
            f["alan_x_form"] = (math.log(N) - math.log(10)) * f["skor5"]
            satirlar.append([f[k] for k in ADLAR])
        return np.asarray(satirlar, dtype=np.float64)

    def guncelle(self, kosu):
        """Koşu sonucu durumu günceller (yalnız o gün bittikten sonra çağrılır)."""
        bugun = gun_no(kosu["tarih"])
        atlar = kosu["atlar"]
        N = len(atlar)
        q = piyasa_q([a["oran"] for a in atlar])
        kaz_sure = next((a["sure"] for a in atlar if a["sira"] == 1), None)
        kal = self._alan_kalitesi(kosu)
        s = self.sinif[kosu["sinif_k"]]; s[0] += 1; s[1] += kal
        self.genel_sinif[0] += 1; self.genel_sinif[1] += kal
        for i, a in enumerate(atlar):
            sira = a["sira"] or N
            skor = 1.0 - (min(sira, N) - 1) / max(N - 1, 1)
            geri = None
            if kaz_sure and a["sure"] and kosu["mesafe"]:
                geri = min(max((a["sure"] - kaz_sure) / (kosu["mesafe"] / 1000.0), 0.0), 15.0)
            qi = q[i] if q else None
            self.at[a["ad"]].append({
                "gun": bugun, "skor": skor, "kazandi": 1 if sira == 1 else 0, "ilk3": 1 if sira <= 3 else 0,
                "geri": geri, "piyasa": (math.log(qi * N) if qi else None), "pist": kosu["pist"],
                "mesafe": kosu["mesafe"], "hipodrom": kosu["hipodrom"], "sinif_k": kosu["sinif_k"],
                "kilo": a["kilo"], "jokey": a["jokey"]})
            won = 1 if sira == 1 else 0
            for p, k in ((self.j60, a["jokey"]), (self.j365, a["jokey"]), (self.t60, a["antrenor"]), (self.t365, a["antrenor"])):
                if k:
                    p[k].ekle(bugun, won, qi)
            ja = self.ja[(a["jokey"], a["ad"])]; ja[0] += 1; ja[1] += skor


def tablo_kur(kosular, durum=None):
    """Zaman sıralı koşulardan sızıntısız koşan tablosu kurar. Günü günü işler."""
    durum = durum or Durum()
    X, kid, y, q, sira = [], [], [], [], []
    i = 0
    while i < len(kosular):
        t = kosular[i]["tarih"]
        j = i
        while j < len(kosular) and kosular[j]["tarih"] == t:
            j += 1
        gunluk = kosular[i:j]
        for r, k in enumerate(gunluk):
            F = durum.ozellik(k)
            X.append(F)
            kid.extend([i + r] * len(k["atlar"]))
            y.extend([1.0 if a["sira"] == 1 else 0.0 for a in k["atlar"]])
            sira.extend([a["sira"] or 99 for a in k["atlar"]])
            qq = piyasa_q([a["oran"] for a in k["atlar"]])
            q.extend(qq if qq else [np.nan] * len(k["atlar"]))
        for k in gunluk:
            durum.guncelle(k)
        i = j
    return {"X": np.vstack(X), "kid": np.asarray(kid), "y": np.asarray(y), "q": np.asarray(q),
            "sira": np.asarray(sira), "adlar": list(ADLAR)}, durum
