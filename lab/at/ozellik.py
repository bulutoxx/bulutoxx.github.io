# BULUTOXX at yarışı laboratuvarı — sızıntısız özellikler.
# Kural: bir koşunun özellikleri yalnız o GÜNDEN ÖNCEKİ sonuçlarla hesaplanır. Günler sırayla işlenir:
# önce o günün bütün koşuları için özellik çıkarılır, sonra durum o günün sonuçlarıyla güncellenir.
# Aynanın memory/*.json özetleri geleceği de içerdiği için KULLANILMAZ.
#
# v2 (2026-10-25): sabah (oransız) tahminini güçlendirmek için yeni gruplar —
#   piyasa_hafiza : atın geçmiş koşulardaki piyasa değerlendirmesi (EWMA, sıra, favori/yenilen favori,
#                   piyasaya göre fazla/eksik performans) + "piyasa reytingi" (rakiplere göre aktarılan)
#   reyting       : Plackett-Luce çevrimiçi reyting (at + jokey + antrenör), tam bitiş sırasından
#   sinif2        : sınıf türü (maiden/şartlı/handikap/KV/G/satış), alanın reyting düzeyi, handikap kilosu
#   hiz           : hız puanı = derece, hipodrom×pist×mesafe standardına ve gün/pist değişkenine göre
#   fark2         : zaman ağırlıklı (sönümlü) form ve kazanana uzaklık
import math
import re
from collections import deque, defaultdict
from datetime import date

import numpy as np

from veri import piyasa_q, zemin_sira
import jokey as _jk   # 🏇 jokey ve ahır uzmanı (lab/at/jokey.py): attan arındırılmış jokey/antrenör özellikleri

TUM_OZELLIKLER = [
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
    # --- v2 adayları
    ("pz_ewma", "piyasa_hafiza"), ("pz_en_iyi5", "piyasa_hafiza"), ("p_sira_son", "piyasa_hafiza"),
    ("p_sira3", "piyasa_hafiza"), ("fav_son", "piyasa_hafiza"), ("yenilen_fav", "piyasa_hafiza"),
    ("piyasa_ustu", "piyasa_hafiza"), ("piyasa_reyting", "piyasa_hafiza"), ("piyasa_yok", "piyasa_hafiza"),
    ("r_at", "reyting"), ("r_jokey", "reyting"), ("r_antrenor", "reyting"), ("r_at_belirsiz", "reyting"),
    ("r_at_alan", "reyting"),
    ("handikap", "sinif2"), ("maiden", "sinif2"), ("kilo_hnd", "sinif2"), ("sinif_r", "sinif2"),
    ("sinif_r_degisim", "sinif2"), ("at_ustu_sinif", "sinif2"),
    ("hiz_son", "hiz"), ("hiz_en_iyi", "hiz"), ("hiz_ort3", "hiz"), ("hiz_yok", "hiz"), ("hiz_pist", "hiz"),
    ("skor_sonum", "fark2"), ("geri_sonum", "fark2"), ("geri_en_iyi5", "fark2"),
    ("jokey_pz60", "jokey2"), ("antrenor_pz60", "jokey2"), ("jokey_r_degisim", "jokey2"), ("ekuri", "jokey2"),
    # --- v3 adayları
    ("zemin_ord", "zemin"), ("zemin_yok", "zemin"), ("zemin_uyum", "zemin"), ("zemin_x_kilo", "zemin"),
    ("zemin_x_skor", "zemin"),
    ("hz_son", "hiz3"), ("hz_en_iyi3", "hiz3"), ("hz_ort3", "hiz3"), ("hz_trend", "hiz3"), ("hz_yok", "hiz3"),
    ("hz_alan", "hiz3"),
    # --- v4 adayları
    # hp: handikap reytingi vekili (handikapçı kiloyu HP'den verir; kilo = sınıf düzeyi + HP farkı)
    ("hp_once", "hp"), ("hp_yok", "hp"), ("hp_bugun", "hp"), ("hp_degisim", "hp"), ("hp_alan", "hp"),
    ("kilo_sira_h", "hp"), ("kilo_min_h", "hp"), ("kilo_x_sinif", "hp"),
    # degisim: koşudan koşuya değişim sinyalleri
    ("mesafe_deg_y", "degisim"), ("pist_degisti", "degisim"), ("pist_ilk", "degisim"), ("jokey_r_fark", "degisim"),
    ("ara_10", "degisim"), ("ara_60_120", "degisim"), ("ara_120_240", "degisim"), ("ara_240p", "degisim"),
    ("donus_2", "degisim"), ("yas2_mesafe", "degisim"), ("sinif_dus", "degisim"), ("sinif_cik", "degisim"),
] + _jk.JK_OZELLIKLER   # jokey/ahır adayları (jk_* grupları) — mevcut sütunların sırası değişmez
TUM_ADLAR = [o[0] for o in TUM_OZELLIKLER]
GRUP = dict(TUM_OZELLIKLER)

# Yayındaki özellik listesi (deneylerle seçildi; bkz. lab/at/deney.py ve RAPOR.md)
# hiz ve jokey2 hesaplanır ama kapıdan geçemedi (log-loss'u az düşürdü, ilk-seçim isabetini düşürdü) → kullanılmıyor.
V1_GRUPLAR = ["form", "fark", "piyasa_gecmisi", "dinlenme", "pist_mesafe_hipodrom", "sinif", "kilo", "yas",
              "jokey", "antrenor", "jokey_at", "alan"]
# v3: hiz3 kapıdan geçti; zemin elendi. v4 (iki katlı kapı, lab/at/deney4.py): degisim ve hp geçti.
SECILI_GRUPLAR = V1_GRUPLAR + ["piyasa_hafiza", "reyting", "sinif2", "fark2", "hiz3", "degisim", "hp"]
SECILI_GRUPLAR = SECILI_GRUPLAR + [g for g in _jk.JK_SECILI if g not in SECILI_GRUPLAR]   # jokey turu (deney_jokey.py)
OZELLIKLER = [o for o in TUM_OZELLIKLER if o[1] in SECILI_GRUPLAR]
ADLAR = [o[0] for o in OZELLIKLER]
GRUPLAR = sorted({o[1] for o in OZELLIKLER})

ONSEL_GAL = 0.10   # Bayes küçültmede genel kazanma oranı önseli
K_KUCULT = 30.0    # jokey/antrenör için önsel ağırlığı (sanal binicilik sayısı)
K_UYUM = 3.0       # at uyumları için önsel ağırlığı

# Plackett-Luce çevrimiçi reyting öğrenme hızları ve piyasa reytingi
PL_HIZ = {"at": 0.10, "jokey": 0.02, "antrenor": 0.01}
PL_KADEME = 4          # bitiş sırasının ilk kaç kademesi kullanılır (arkalar gürültülü)
PM_HIZ = 0.25          # piyasa reytingi öğrenme hızı
EWMA_A = 0.4           # geçmiş koşu ağırlığı (son koşu 0.4, öncesi 0.6 ile birleşir)
SONUM_GUN = 120.0      # zaman sönümlü formun yarı ömrü (gün)
HP_K = 3          # atın HP vekili: son kaç handikap değerinin medyanı
HP_TAVAN = 4.0    # apranti (jokey) kilo indirimi vekili üst sınırı (kg)
HZ_YONTEM = "projeksiyon"   # hız figürü gün değişkeni: "projeksiyon" (atların önceki figürleri) ya da "sinif" (par + sınıf ofseti)


def gun_no(t):
    return date.fromisoformat(t).toordinal()


def sinif_turu(rc):
    """raceClass -> (tür, numara). Ör. 'Handikap 16 /H1' -> ('H', 16); 'G 3' -> ('G', 3)."""
    s = re.sub(r"\s*/.*", "", str(rc or "")).strip().upper()
    n = re.findall(r"\d+", s)
    no = int(n[0]) if n else 0
    if "MAIDEN" in s:
        return "M", 0
    if "HANDIKAP" in s or "HANDİKAP" in s:
        return ("G" if s.startswith("G") else "H"), no
    if s.startswith("KV") or "KISA VADE" in s:
        return "KV", no
    if s.startswith("G"):
        return "G", no
    if "ŞARTLI" in s or "SARTLI" in s:
        return "S", no
    if "SATIŞ" in s or "SATIS" in s:
        return "SAT", no
    return "?", no


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


class _Ort:
    """Kayan zaman penceresinde değer ortalaması (küçültmeli)."""
    __slots__ = ("g", "n", "s", "gun")

    def __init__(self, gun):
        self.g, self.n, self.s, self.gun = deque(), 0, 0.0, gun

    def ekle(self, d, v):
        self.g.append((d, v)); self.n += 1; self.s += v

    def ort(self, bugun, k=20.0):
        while self.g and self.g[0][0] < bugun - self.gun:
            _, v = self.g.popleft(); self.n -= 1; self.s -= v
        return self.s / (self.n + k)


def _logit(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _pl_gradyan(s, sira, kademe):
    """Plackett-Luce log-olabilirliğinin güçlere göre gradyanı (ilk `kademe` sıra)."""
    N = len(s)
    o = sorted(range(N), key=lambda i: sira[i])
    g = [0.0] * N
    kalan = list(o)
    for k in range(min(kademe, N - 1)):
        mx = max(s[i] for i in kalan)
        e = [math.exp(s[i] - mx) for i in kalan]
        z = sum(e)
        for i, ei in zip(kalan, e):
            g[i] -= ei / z
        g[o[k]] += 1.0
        kalan.remove(o[k])
    return g


class Durum:
    def __init__(self):
        self.at = defaultdict(list)  # at -> geçmiş koşular (sözlük)
        self.j60 = defaultdict(lambda: _Pencere(60)); self.j365 = defaultdict(lambda: _Pencere(365))
        self.t60 = defaultdict(lambda: _Pencere(60)); self.t365 = defaultdict(lambda: _Pencere(365))
        self.ja = defaultdict(lambda: [0, 0.0])  # (jokey, at) -> [binme, skor toplamı]
        self.sinif = defaultdict(lambda: [0, 0.0])  # sınıf -> [koşu, alan kalitesi toplamı]
        self.genel_sinif = [0, 0.0]
        # v2
        self.r = {"at": defaultdict(float), "jokey": defaultdict(float), "antrenor": defaultdict(float)}
        self.rn = defaultdict(int)                       # at -> reyting güncelleme sayısı
        self.pr = defaultdict(float)                     # piyasa reytingi
        self.sinif_r = defaultdict(lambda: [0, 0.0])     # sınıf -> [koşu, alan ort. reytingi toplamı]
        self.std = defaultdict(lambda: deque(maxlen=60))  # (hipodrom, pist, mesafe) -> kazanan derece/km
        self.gun_bekleyen = []                           # aynı günün koşuları (gün değişkeni için)
        self.jpz = defaultdict(lambda: _Ort(60)); self.tpz = defaultdict(lambda: _Ort(60))
        # v3: Beyer tarzı hız figürü (bkz. _hz_* ve gun_sonu)
        self.hz_taban = defaultdict(lambda: np.zeros(5))   # pist -> [n, Σx, Σy, Σxx, Σxy]  (x = log mesafe, y = log sn/m)
        self.hz_par = defaultdict(lambda: [0, 0.0])        # (hipodrom, pist, mesafe) -> [n, Σ artık]
        self.hz_sinif = defaultdict(lambda: [0, 0.0])      # sınıf anahtarı -> [n, Σ artık]
        self.hz_bekleyen = []                              # bu günün koşuları (gün değişkeni gün sonunda)
        # v4: handikap reytingi vekili (kg biriminde)
        self.hp_at = defaultdict(lambda: deque(maxlen=6))  # at -> örtük HP değerleri (handikap koşularından)
        self.hp_sinif = defaultdict(lambda: [0, 0.0])      # handikap sınıf anahtarı -> [n, Σ düzey gözlemi]
        self.hp_jokey = defaultdict(lambda: deque(maxlen=40))  # jokey -> kilo indirimi kalıntıları
        self.hp_bekleyen = []                              # günün handikap koşuları (gün sonunda işlenir)
        self.jk = _jk.JokeyDurum()                         # jokey/ahır: Bayes PL becerisi + kalıntı istatistikleri

    # --- sınıf düzeyi: o sınıfta koşan atların geçmiş galibiyet sayısının (log) kayan ortalaması
    def sinif_duzeyi(self, k):
        n, s = self.sinif[k]
        gn, gs = self.genel_sinif
        g = gs / gn if gn else 0.0
        return (s + 5 * g) / (n + 5)

    def sinif_reyting(self, k):
        n, s = self.sinif_r[k]
        return s / (n + 5)   # önsel 0 (genel ortalama)

    # --- v4: handikap reytingi vekili. Handikapta kiloyu handikapçı HP'den verir: kilo ≈ taban(sınıf) + k·HP.
    # Örtük HP (kg biriminde) = L(sınıf) + (kilo + jokey indirimi − koşu medyanı). L(sınıf), sınıflar arasında
    # geçiş yapan atların önceki HP'lerinden çevrimiçi öğrenilir; jokey (apranti) indirimi bilinmediği için
    # jokeyin kalıntılarının medyanıyla (0–4 kg, küçültmeli) tahmin edilir. Atın HP'si son 3 değerin medyanı.
    @staticmethod
    def _handikap_mi(kosu):
        return sinif_turu(kosu["sinif"])[0] == "H"

    def _hp_indirim(self, jokey):
        d = self.hp_jokey.get(jokey)
        if not d:
            return 0.0
        return min(max(float(np.median(d)) * len(d) / (len(d) + 5.0), 0.0), HP_TAVAN)

    def _hp_at(self, ad_):
        d = self.hp_at.get(ad_)
        return float(np.median(list(d)[-HP_K:])) if d else None

    def _hp_duzey(self, k):
        n, t = self.hp_sinif.get(k, (0, 0.0))
        return t / (n + 0.5) if n else 0.0

    def _hp_ofset(self, kosu):
        """Handikap koşusunda her atın (kilo + indirim − medyan) değeri; kilosu olmayan at None."""
        ad = [(a["kilo"] + self._hp_indirim(a["jokey"])) if a["kilo"] else None for a in kosu["atlar"]]
        v = [x for x in ad if x is not None]
        if len(v) < 2:
            return None
        md = float(np.median(v))
        return [None if x is None else x - md for x in ad]

    def _alan_kalitesi(self, kosu):
        v = [math.log1p(sum(h["kazandi"] for h in self.at[a["ad"]])) for a in kosu["atlar"]]
        return sum(v) / len(v)

    def ozellik(self, kosu, adlar=None):
        """Bir koşu için (N x d) özellik matrisi; yalnız mevcut durumdan (geçmişten)."""
        adlar = ADLAR if adlar is None else adlar
        bugun = gun_no(kosu["tarih"])
        N = len(kosu["atlar"])
        kilolar = [a["kilo"] for a in kosu["atlar"] if a["kilo"]]
        kilo_ort = sum(kilolar) / len(kilolar) if kilolar else 0.0
        sd_now = self.sinif_duzeyi(kosu["sinif_k"])
        tur, _ = sinif_turu(kosu["sinif"])
        sr_now = self.sinif_reyting(kosu["sinif_k"])
        r_at_list = [self.r["at"].get(a["ad"], 0.0) for a in kosu["atlar"]]
        r_alan = sum(r_at_list) / N
        ant_say = defaultdict(int)
        for a in kosu["atlar"]:
            ant_say[a["antrenor"]] += 1
        # v3: pist durumu (bugün) ve hız figürleri (alan düzeyi için önce hepsi)
        z_bugun = zemin_sira(kosu.get("zemin"))
        hz_l = []
        for a in kosu["atlar"]:
            v = [h["hz"] for h in self.at.get(a["ad"], [])[-6:] if h.get("hz") is not None][-3:]
            hz_l.append(v)
        eniyi = [max(v) for v in hz_l if v]
        hz_alan_ort = sum(eniyi) / len(eniyi) if eniyi else 0.0
        hz_alan_min = min(eniyi) if eniyi else 0.0
        # v4: handikap vekili (koşu düzeyi)
        hnd = self._handikap_mi(kosu)
        hp_o = [self._hp_at(a["ad"]) for a in kosu["atlar"]]
        hp_b = list(hp_o)
        kl = [a["kilo"] for a in kosu["atlar"] if a["kilo"]]
        _, sno = sinif_turu(kosu["sinif"])
        if hnd:
            of = self._hp_ofset(kosu)
            if of is not None:
                L = self._hp_duzey(kosu["sinif_k"])
                hp_b = [hp_o[i] if of[i] is None else L + of[i] for i in range(N)]
        hv = [x for x in hp_b if x is not None]
        hp_dol = [x if x is not None else (min(hv) if hv else 0.0) for x in hp_b]
        hp_alan_ort = sum(hp_dol) / N
        kl_sira = {}
        if hnd and len(kl) >= 2:
            ss = sorted(kl)
            for a in kosu["atlar"]:
                if a["kilo"]:
                    lo = ss.index(a["kilo"]); hi = len(ss) - 1 - ss[::-1].index(a["kilo"])
                    kl_sira[id(a)] = (lo + hi) / 2.0 / (len(ss) - 1)
        kl_min = min(kl) if kl else 0.0
        kl_med = float(np.median(kl)) if kl else 0.0
        jk_sat = self.jk.satirlar(kosu) if any(x in _jk.JK_ADLAR for x in adlar) else None
        satirlar = []
        for ai, a in enumerate(kosu["atlar"]):
            g = self.at.get(a["ad"], [])
            son = g[-10:]
            n = len(g)
            f = dict.fromkeys(TUM_ADLAR, 0.0)
            f["yeni"] = 1.0 if n == 0 else 0.0
            f["n_kosu"] = math.log1p(n)
            ort_skor = 0.5
            f["piyasa_yok"] = 1.0
            f["hiz_yok"] = 1.0
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
                # --- v2: piyasa hafızası
                if pm:
                    f["piyasa_yok"] = 0.0
                    e = None
                    for h in son:
                        if h["piyasa"] is not None:
                            e = h["piyasa"] if e is None else EWMA_A * h["piyasa"] + (1 - EWMA_A) * e
                    f["pz_ewma"] = e
                    f["pz_en_iyi5"] = max(pm[-5:])
                    ps = [h["p_sira"] for h in son if h.get("p_sira") is not None]
                    f["p_sira_son"] = ps[-1] if ps else 0.0
                    f["p_sira3"] = sum(ps[-3:]) / len(ps[-3:]) if ps else 0.0
                    sonp = next((h for h in reversed(son) if h["piyasa"] is not None), None)
                    f["fav_son"] = 1.0 if sonp and sonp.get("p_sira") == 0.0 else 0.0
                    f["yenilen_fav"] = 1.0 if f["fav_son"] and not sonp["kazandi"] else 0.0
                    ust = [h["kazandi"] - h["q"] for h in son if h.get("q") is not None]
                    f["piyasa_ustu"] = sum(ust) / (len(ust) + 2.0)
                f["piyasa_reyting"] = self.pr.get(a["ad"], 0.0)
                # --- v2: hız puanı
                hz = [h["hiz"] for h in son if h.get("hiz") is not None]
                if hz:
                    f["hiz_yok"] = 0.0
                    f["hiz_son"] = hz[-1]
                    f["hiz_en_iyi"] = max(hz[-5:])
                    f["hiz_ort3"] = sum(hz[-3:]) / len(hz[-3:])
                    hp = [h["hiz"] for h in son if h.get("hiz") is not None and h["pist"] == kosu["pist"]]
                    f["hiz_pist"] = (sum(hp) / len(hp) - f["hiz_ort3"]) * len(hp) / (len(hp) + 2.0) if hp else 0.0
                # --- v2: zaman sönümlü form ve fark
                wsum = sk_ = gr_ = gw = 0.0
                for h in son:
                    w = 0.5 ** ((bugun - h["gun"]) / SONUM_GUN)
                    wsum += w; sk_ += w * h["skor"]
                    if h["geri"] is not None:
                        gw += w; gr_ += w * h["geri"]
                f["skor_sonum"] = (sk_ + 0.5 * 0.5) / (wsum + 0.5) - 0.5
                f["geri_sonum"] = (gr_ + 1.0 * 4.0) / (gw + 1.0) - 4.0
                gr5 = [h["geri"] for h in son[-5:] if h["geri"] is not None]
                f["geri_en_iyi5"] = (min(gr5) if gr5 else 4.0) - 4.0
                if g[-1].get("sinif_r") is not None:
                    f["sinif_r_degisim"] = sr_now - self.sinif_reyting(g[-1]["sinif_k"])
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
            # --- v2: reytingler ve sınıf
            f["r_at"] = r_at_list[ai]
            f["r_jokey"] = self.r["jokey"].get(a["jokey"], 0.0)
            f["r_antrenor"] = self.r["antrenor"].get(a["antrenor"], 0.0)
            f["r_at_belirsiz"] = 1.0 / math.sqrt(1.0 + self.rn.get(a["ad"], 0))
            f["r_at_alan"] = r_at_list[ai] - r_alan
            f["handikap"] = 1.0 if tur == "H" else 0.0
            f["maiden"] = 1.0 if tur == "M" else 0.0
            f["kilo_hnd"] = f["kilo_fark"] if tur in ("H", "G") else 0.0
            f["sinif_r"] = sr_now
            f["at_ustu_sinif"] = r_at_list[ai] - sr_now
            # --- v2: jokey/antrenörün binişlerine piyasanın verdiği değer, jokey yükseltmesi, ekuri
            jp = self.jpz.get(a["jokey"]); tp = self.tpz.get(a["antrenor"])
            f["jokey_pz60"] = jp.ort(bugun) if jp else 0.0
            f["antrenor_pz60"] = tp.ort(bugun) if tp else 0.0
            if n:
                f["jokey_r_degisim"] = f["r_jokey"] - self.r["jokey"].get(g[-1]["jokey"], 0.0)
            f["ekuri"] = float(ant_say[a["antrenor"]] - 1) if a["antrenor"] else 0.0
            # --- v3: pist durumu
            zo = z_bugun if z_bugun is not None else 0
            f["zemin_ord"] = float(zo)
            f["zemin_yok"] = 1.0 if z_bugun is None else 0.0
            f["zemin_x_kilo"] = zo * f["kilo_fark"]
            f["zemin_x_skor"] = zo * f["skor5"]
            if n and zo >= 1:
                s = [h["skor"] for h in g if (h.get("zemin_s") or 0) >= 1]
                f["zemin_uyum"] = (sum(s) + K_UYUM * ort_skor) / (len(s) + K_UYUM) - ort_skor
            # --- v3: hız figürü (son 3 figürlü koşu)
            v = hz_l[ai]
            if v:
                f["hz_son"] = v[-1]
                f["hz_en_iyi3"] = max(v)
                f["hz_ort3"] = sum(v) / len(v)
                f["hz_trend"] = (v[-1] - sum(v[:-1]) / len(v[:-1])) if len(v) >= 2 else 0.0
                f["hz_alan"] = max(v) - hz_alan_ort
            else:
                f["hz_yok"] = 1.0
                f["hz_son"] = f["hz_en_iyi3"] = f["hz_ort3"] = hz_alan_min
                f["hz_alan"] = hz_alan_min - hz_alan_ort
            # --- v4: handikap reytingi vekili
            f["hp_yok"] = 1.0 if hp_o[ai] is None else 0.0
            f["hp_once"] = hp_o[ai] if hp_o[ai] is not None else 0.0
            f["hp_bugun"] = hp_dol[ai]
            f["hp_alan"] = hp_dol[ai] - hp_alan_ort
            if hnd and hp_o[ai] is not None and hp_b[ai] is not None:
                f["hp_degisim"] = hp_b[ai] - hp_o[ai]
            if hnd and a["kilo"]:
                f["kilo_sira_h"] = kl_sira.get(id(a), 0.5) - 0.5
                f["kilo_min_h"] = a["kilo"] - kl_min
                f["kilo_x_sinif"] = (a["kilo"] - kl_med) * sno / 20.0
            # --- v4: değişim sinyalleri
            if n:
                h0 = g[-1]
                if h0["mesafe"] and kosu["mesafe"]:
                    f["mesafe_deg_y"] = math.log(kosu["mesafe"] / h0["mesafe"])
                f["pist_degisti"] = 1.0 if h0["pist"] != kosu["pist"] else 0.0
                f["pist_ilk"] = 1.0 if not any(h["pist"] == kosu["pist"] for h in g) else 0.0
                f["jokey_r_fark"] = self.r["jokey"].get(a["jokey"], 0.0) - self.r["jokey"].get(h0["jokey"], 0.0)
                ara = max(bugun - h0["gun"], 1)
                f["ara_10"] = 1.0 if ara <= 10 else 0.0
                f["ara_60_120"] = 1.0 if 60 < ara <= 120 else 0.0
                f["ara_120_240"] = 1.0 if 120 < ara <= 240 else 0.0
                f["ara_240p"] = 1.0 if ara > 240 else 0.0
                if n >= 2 and h0["gun"] - g[-2]["gun"] > 90 and ara <= 60:
                    f["donus_2"] = 1.0
                sd = f["sinif_r_degisim"]
                f["sinif_dus"] = 1.0 if sd < -0.15 else 0.0
                f["sinif_cik"] = 1.0 if sd > 0.15 else 0.0
            if (a["yas"] or 0) == 2 and kosu["mesafe"]:
                f["yas2_mesafe"] = math.log(kosu["mesafe"] / 1200.0)
            if jk_sat is not None:
                f.update(jk_sat[ai])
            satirlar.append([f[k] for k in adlar])
        return np.asarray(satirlar, dtype=np.float64)

    # ---------------------------------------------------------------- v3 hız figürü (sıfırdan, Beyer tarzı)
    # Model: y = log(derece / mesafe) = T_pist(log mesafe) + P(hipodrom, pist, mesafe) + C(sınıf) + V(gün, hipodrom, pist) + ε
    #   T: pist başına log-mesafe doğrusu (geçmiş kazananlardan en küçük kareler)
    #   P: hipodrom×pist×mesafe "par" artığı (küçültmeli ortalama, k=5)
    #   C: sınıf ofseti (küçültmeli, k=20) — yalnız gün değişkenini doğru ayırmak için; figüre katılmaz
    #   V: aynı gün + hipodrom + pist değişkeni (kırpılmış artıkların küçültmeli ortalaması, k=1.5). Varsayılan
    #      "projeksiyon": koşudaki (ön sıradaki) atların ham figürü − kendi önceki figürleri, koşu medyanı (Beyer usulü;
    #      cins/sınıf karışımına dayanıklı). Yedek "sinif": kazanan derecesi − par − sınıf ofseti.
    # Figür = −1000·(y − T − P) − V: par'a göre binde kaç hızlı. Tamamen geçmişten: T/P/C gün sonunda, o günün
    # figürleri hesaplandıktan SONRA güncellenir; figürler yalnız ertesi günlerin özelliklerine girer.
    HZ_KIRP = 0.04

    @staticmethod
    def _hz_sinif_k(rc):
        tur, no = sinif_turu(rc)
        return f"{tur}{min(no // 4, 6) if tur in ('H', 'KV', 'G', 'S') else ''}"

    def _hz_taban(self, pist, x):
        a = self.hz_taban.get(pist)
        if a is None or a[0] < 30:
            a = sum((v for v in self.hz_taban.values()), np.zeros(5))
            if a[0] < 30:
                return None
        n, sx, sy, sxx, sxy = a
        vx = sxx / n - (sx / n) ** 2
        b = (sxy / n - sx / n * sy / n) / vx if vx > 1e-9 else 0.0
        return sy / n + b * (x - sx / n)

    def _hz_beklenen(self, kosu):
        """(T + P, C) ya da None."""
        if not kosu["mesafe"]:
            return None
        t = self._hz_taban(kosu["pist"], math.log(kosu["mesafe"]))
        if t is None:
            return None
        pn, ps = self.hz_par.get((kosu["hipodrom"], kosu["pist"], kosu["mesafe"]), (0, 0.0))
        cn, cs = self.hz_sinif.get(self._hz_sinif_k(kosu["sinif"]), (0, 0.0))
        return t + ps / (pn + 5.0), cs / (cn + 20.0)

    def _hz_gun_sonu(self):
        K = self.HZ_KIRP
        grup = defaultdict(list)
        for kosu, ys in self.hz_bekleyen:
            grup[(kosu["hipodrom"], kosu["pist"])].append((kosu, ys))
        for _, liste in grup.items():
            bek = [self._hz_beklenen(kosu) for kosu, _ in liste]
            # gün değişkeni V (figür biriminde, + = hızlı gün)
            art = []
            for (kosu, ys), b in zip(liste, bek):
                if b is None:
                    continue
                if HZ_YONTEM == "projeksiyon":
                    # Beyer projeksiyonu: atların bu günkü ham figürü − kendi önceki figür ortalaması (ön sıradakiler);
                    # koşu medyanı → cins/sınıf karışımından bağımsız gün değişkeni
                    N = len(kosu["atlar"])
                    d = [(-1000.0 * (ys[a["ad"]] - b[0])) - ys["_on"][a["ad"]] for a in kosu["atlar"]
                         if a["ad"] in ys and ys["_on"].get(a["ad"]) is not None and (a["sira"] or 99) <= max(3, N // 2)]
                    if len(d) >= 2:
                        art.append(min(max(float(np.median(d)), -1000 * K), 1000 * K))
                else:
                    yw = ys.get("_kazanan")
                    if yw is not None:
                        art.append(-1000.0 * min(max(yw - b[0] - b[1], -K), K))
            V = sum(art) / (len(art) + 1.5) if art else 0.0
            for (kosu, ys), b in zip(liste, bek):
                if b is not None:
                    yw = ys.get("_kazanan")
                    fw = -1000.0 * (yw - b[0]) - V if yw is not None else None
                    for a in kosu["atlar"]:
                        y = ys.get(a["ad"])
                        h = self.at[a["ad"]][-1]
                        if y is None or h.get("gun") != gun_no(kosu["tarih"]):
                            continue
                        f = -1000.0 * (y - b[0]) - V
                        if fw is not None:
                            f = max(f, fw - 50.0)    # geride bırakılmış/eğilmiş atlar: en fazla %5 kazananın gerisi
                        h["hz"] = min(max(f, -150.0), 150.0)
                # öğrenme (bu günün figürlerinden SONRA): taban, par, sınıf — gün değişkeni ayıklanmış kazanan derecesiyle
                yw = ys.get("_kazanan")
                if yw is None or not kosu["mesafe"]:
                    continue
                x = math.log(kosu["mesafe"])
                yv = yw + V / 1000.0
                a = self.hz_taban[kosu["pist"]]
                a += np.array([1.0, x, yv, x * x, x * yv])
                if b is not None:
                    p = self.hz_par[(kosu["hipodrom"], kosu["pist"], kosu["mesafe"])]
                    t = self._hz_taban(kosu["pist"], x)
                    p[0] += 1; p[1] += min(max(yv - t - b[1], -2 * K), 2 * K)
                    c = self.hz_sinif[self._hz_sinif_k(kosu["sinif"])]
                    c[0] += 1; c[1] += min(max(yv - b[0], -2 * K), 2 * K)
        self.hz_bekleyen = []

    def _std_derece(self, kosu):
        """(hipodrom, pist, mesafe) için geçmiş kazanan derecelerinin medyanı (sn/km); az örnekte None."""
        d = self.std.get((kosu["hipodrom"], kosu["pist"], kosu["mesafe"]))
        if not d or len(d) < 5:
            return None
        v = sorted(d)
        return v[len(v) // 2]

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
        # piyasa sırası (0 = favori, 1 = en az ilgi)
        p_sira = None
        if q:
            o = sorted(range(N), key=lambda i: -q[i])
            p_sira = [0.0] * N
            for rnk, i in enumerate(o):
                p_sira[i] = rnk / max(N - 1, 1)
        # sınıf reyting düzeyi (güncellemeden önceki at reytingleriyle)
        ra = [self.r["at"].get(a["ad"], 0.0) for a in atlar]
        sr = self.sinif_r[kosu["sinif_k"]]; sr[0] += 1; sr[1] += sum(ra) / N
        # hız: kazanan derecesi standarda göre (gün değişkeni gün sonunda hesaplanır)
        std = self._std_derece(kosu)
        km = kosu["mesafe"] / 1000.0 if kosu["mesafe"] else None
        for i, a in enumerate(atlar):
            sira = a["sira"] or N
            skor = 1.0 - (min(sira, N) - 1) / max(N - 1, 1)
            geri = None
            if kaz_sure and a["sure"] and kosu["mesafe"]:
                geri = min(max((a["sure"] - kaz_sure) / (kosu["mesafe"] / 1000.0), 0.0), 15.0)
            qi = q[i] if q else None
            ham_hiz = None
            if std is not None and a["sure"] and km:
                ham_hiz = std - min(a["sure"] / km, std + 15.0)   # + = standarttan hızlı (sn/km)
            self.at[a["ad"]].append({
                "gun": bugun, "skor": skor, "kazandi": 1 if sira == 1 else 0, "ilk3": 1 if sira <= 3 else 0,
                "geri": geri, "piyasa": (math.log(qi * N) if qi else None), "pist": kosu["pist"],
                "mesafe": kosu["mesafe"], "hipodrom": kosu["hipodrom"], "sinif_k": kosu["sinif_k"],
                "kilo": a["kilo"], "jokey": a["jokey"],
                "q": qi, "p_sira": (p_sira[i] if p_sira else None), "sinif_r": 1.0,
                "ham_hiz": ham_hiz, "hiz": ham_hiz, "hz": None, "zemin_s": zemin_sira(kosu.get("zemin"))})
            won = 1 if sira == 1 else 0
            for p, k in ((self.j60, a["jokey"]), (self.j365, a["jokey"]), (self.t60, a["antrenor"]), (self.t365, a["antrenor"])):
                if k:
                    p[k].ekle(bugun, won, qi)
            ja = self.ja[(a["jokey"], a["ad"])]; ja[0] += 1; ja[1] += skor
            if qi:
                if a["jokey"]:
                    self.jpz[a["jokey"]].ekle(bugun, math.log(qi * N))
                if a["antrenor"]:
                    self.tpz[a["antrenor"]].ekle(bugun, math.log(qi * N))
        # Plackett-Luce reyting güncellemesi (at + jokey + antrenör güçlerinin toplamı)
        guc = [self.r["at"][a["ad"]] + self.r["jokey"][a["jokey"]] + self.r["antrenor"][a["antrenor"]] for a in atlar]
        gr = _pl_gradyan(guc, [a["sira"] or N for a in atlar], PL_KADEME)
        for i, a in enumerate(atlar):
            self.r["at"][a["ad"]] += PL_HIZ["at"] * gr[i]
            self.r["jokey"][a["jokey"]] += PL_HIZ["jokey"] * gr[i]
            self.r["antrenor"][a["antrenor"]] += PL_HIZ["antrenor"] * gr[i]
            self.rn[a["ad"]] += 1
        # piyasa reytingi: piyasanın (q) koşu içi dağılımına çapraz-entropi adımı
        if q:
            pr = [self.pr[a["ad"]] for a in atlar]
            mx = max(pr)
            e = [math.exp(v - mx) for v in pr]
            z = sum(e)
            for i, a in enumerate(atlar):
                self.pr[a["ad"]] += PM_HIZ * N * (q[i] - e[i] / z)
        # standart derece: kazanan derecesini ekle (sonraki koşular için)
        if kaz_sure and km:
            self.std[(kosu["hipodrom"], kosu["pist"], kosu["mesafe"])].append(kaz_sure / km)
        if std is not None and kaz_sure and km:
            self.gun_bekleyen.append((kosu, std - kaz_sure / km))
        self.jk.guncelle(kosu)
        # v4 handikap vekili: gün sonunda (aynı günün başka koşusuna sızmasın diye)
        if self._handikap_mi(kosu):
            self.hp_bekleyen.append(kosu)
        # v3 hız figürü: o günün log(sn/m) değerleri gün sonunda figüre çevrilir
        if kosu["mesafe"]:
            ys = {}
            for a in atlar:
                if a["sure"] and a["sure"] > 0:
                    ys[a["ad"]] = math.log(a["sure"] / kosu["mesafe"])
            if kaz_sure:
                ys["_kazanan"] = math.log(kaz_sure / kosu["mesafe"])
            on = {}
            for a in atlar:   # atın bu koşudan ÖNCEKİ figür ortalaması (son 3) — projeksiyon için
                v = [h["hz"] for h in self.at[a["ad"]][:-1][-6:] if h.get("hz") is not None][-3:]
                on[a["ad"]] = sum(v) / len(v) if v else None
            ys["_on"] = on
            self.hz_bekleyen.append((kosu, ys))

    def gun_sonu(self):
        """Gün bitti: hipodrom×pist gün değişkenini (kazananların standarda göre ortalama farkı, küçültülmüş)
        hesaplayıp o günkü hız puanlarını düzeltir. Yalnız ertesi günlerin özelliklerine yansır."""
        grup = defaultdict(list)
        for kosu, fark in self.gun_bekleyen:
            grup[(kosu["hipodrom"], kosu["pist"])].append((kosu, fark))
        for _, liste in grup.items():
            deg = sum(f for _, f in liste) / (len(liste) + 1.0)
            for kosu, _ in liste:
                for a in kosu["atlar"]:
                    h = self.at[a["ad"]][-1]
                    if h.get("ham_hiz") is not None:
                        h["hiz"] = h["ham_hiz"] - deg
        self.gun_bekleyen = []
        self._hz_gun_sonu()
        self._hp_gun_sonu()
        self.jk.gun_sonu()

    def _hp_gun_sonu(self):
        """Günün handikap koşularından: sınıf düzeyi, jokey indirimi ve atların örtük HP değerleri güncellenir.
        Tüm hesap günün başındaki durumla yapılır (gün içi sıra bağımsız), güncellemeler sonra uygulanır."""
        hesap = []
        for kosu in self.hp_bekleyen:
            of = self._hp_ofset(kosu)
            if of is None:
                continue
            onc = [self._hp_at(a["ad"]) for a in kosu["atlar"]]
            gz = [onc[i] - of[i] for i in range(len(of)) if onc[i] is not None and of[i] is not None]
            # jokey indirimi kalıntısı: beklenen ofset (atın HP'si − sınıf düzeyi) − ham ofset (indirimsiz)
            kl = [a["kilo"] for a in kosu["atlar"] if a["kilo"]]
            md_ham = float(np.median(kl))
            L0 = self._hp_duzey(kosu["sinif_k"])
            jk = [(a["jokey"], (onc[i] - L0) - (a["kilo"] - md_ham)) for i, a in enumerate(kosu["atlar"])
                  if onc[i] is not None and a["kilo"] and a["jokey"]]
            hesap.append((kosu, of, gz, jk))
        for kosu, of, gz, jk in hesap:
            if len(gz) >= 2:
                c = self.hp_sinif[kosu["sinif_k"]]
                c[0] += 1; c[1] += float(np.median(gz))
            for j, r in jk:
                self.hp_jokey[j].append(min(max(r, -3.0), 6.0))
        for kosu, of, gz, jk in hesap:
            L = self._hp_duzey(kosu["sinif_k"])
            for i, a in enumerate(kosu["atlar"]):
                if of[i] is not None:
                    self.hp_at[a["ad"]].append(L + of[i])
        self.hp_bekleyen = []


def tablo_kur(kosular, durum=None, adlar=None):
    """Zaman sıralı koşulardan sızıntısız koşan tablosu kurar. Günü günü işler."""
    durum = durum or Durum()
    adlar = ADLAR if adlar is None else list(adlar)
    X, kid, y, q, sira = [], [], [], [], []
    i = 0
    while i < len(kosular):
        t = kosular[i]["tarih"]
        j = i
        while j < len(kosular) and kosular[j]["tarih"] == t:
            j += 1
        gunluk = kosular[i:j]
        for r, k in enumerate(gunluk):
            F = durum.ozellik(k, adlar)
            X.append(F)
            kid.extend([i + r] * len(k["atlar"]))
            y.extend([1.0 if a["sira"] == 1 else 0.0 for a in k["atlar"]])
            sira.extend([a["sira"] or 99 for a in k["atlar"]])
            qq = piyasa_q([a["oran"] for a in k["atlar"]])
            q.extend(qq if qq else [np.nan] * len(k["atlar"]))
        for k in gunluk:
            durum.guncelle(k)
        durum.gun_sonu()
        i = j
    return {"X": np.vstack(X), "kid": np.asarray(kid), "y": np.asarray(y), "q": np.asarray(q),
            "sira": np.asarray(sira), "adlar": list(adlar)}, durum
