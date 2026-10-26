# OXXai at yarışı laboratuvarı — v5 at özellikleri (sınıf-ayarlı form, göreli kilo değişimi, dinlenme eğrisi).
#
# Aynadaki alanlarla (sonuç: sıra, derece, kilo, oran, sınıf, mesafe, pist; program: aynı + pist durumu) kurulabilenler.
# Aynada start/kulvar numarası ve koşu içi pozisyon (tempo, erken hız) YOK; bu yüzden kulvar yanlılığı ve koşu stili
# kurulamadı. Aynı gün pist yanlılığı (günün önceki koşularında önden gidenler) sabah kilidinde bilinemez ve gün içi
# sıra testini bozar → denenmedi.
#
# Gruplar (deney masası: lab/at/deney5.py, deney4 iki katlı kapı):
#   a5_sinif : sınıf-ayarlı form — atın son koşularındaki RAKİP ALAN düzeyi (alanın ortalama PL at reytingi, o koşudan
#              önce) bugünkü alana göre; ilk 3'e girdiği en güçlü alan; güçlü alanlarda ilk 3 payı
#   a5_kilo  : göreli kilo değişimi — bugünkü (kilo − alan ort.) − son koşudaki (kilo − alan ort.), kilo × mesafe,
#              galibiyet sonrası kilo cezası, iyi koştuğu (ilk 3) koşulardaki kiloya göre fark
#   a5_taze  : dinlenme eğrisi — atın uzun aradan (≥45 g) / sık (≤14 g) koşularındaki kişisel uyumu, antrenörün uzun
#              aradan (>60 g) dönen atlarındaki piyasaya göre kalıntısı, log(ara)², son 30 günde koşu sayısı
# Sızıntı yok: hepsi ozellik.Durum'un atın geçmişine (gün sonunda eklenen) ve bu modülün gün sonu durumuna dayanır.
import math
from collections import defaultdict

A5_OZELLIKLER = [
    ("a5_sr_ort5", "a5_sinif"), ("a5_sr_son", "a5_sinif"), ("a5_sr_ilk3_max", "a5_sinif"), ("a5_ust_ilk3", "a5_sinif"),
    ("a5_kilo_gdeg", "a5_kilo"), ("a5_kilo_x_mes", "a5_kilo"), ("a5_kilo_kaz", "a5_kilo"), ("a5_kilo_iyi", "a5_kilo"),
    ("a5_taze_uyum", "a5_taze"), ("a5_sik_uyum", "a5_taze"), ("a5_ant_donus", "a5_taze"), ("a5_ara_kare", "a5_taze"),
    ("a5_yogun30", "a5_taze"),
]
A5_ADLAR = [o[0] for o in A5_OZELLIKLER]
A5_GRUPLAR = list(dict.fromkeys(g for _, g in A5_OZELLIKLER))
# Kapıdan geçen gruplar (lab/at/deney5.py ile seçilir; yayın tarifine eklenir — bkz. ozellik.SECILI_GRUPLAR)
# v5 turu (deney4 iki katlı kapı, 26.10.2026): a5_sinif geçti (ΔLL yalnız model −0,0106 [−0,0140; −0,0075]);
# a5_kilo, a5_taze (yalnız ilk-seçim kuralına takıldı, tekrarda da) ve harman hm_alan elendi.
A5_SECILI = ["a5_sinif"]

IFADE = {   # gerekçe ifadeleri (değer koşu ortalamasından YÜKSEKSE, DÜŞÜKSE)
    "a5_sr_ort5": ("son koşularında daha güçlü rakiplerle koştu", "son koşularında daha zayıf rakiplerle koştu"),
    "a5_sr_son": ("son koşusu daha güçlü bir alandaydı", "son koşusu daha zayıf bir alandaydı"),
    "a5_sr_ilk3_max": ("bu düzeyde ya da üstünde ilk 3'e girmişliği var", "bu düzeyde ilk 3'e girmişliği yok"),
    "a5_ust_ilk3": ("güçlü alanlarda ilk 3 oranı yüksek", "güçlü alanlarda ilk 3 oranı düşük"),
}

K_UYUM = 3.0
ANT_K = 15.0     # antrenör dönüş kalıntısı küçültmesi (sanal biniş)


class A5Durum:
    """Antrenörün uzun aradan dönen atlarındaki (kazandı − q) kalıntısı. Atın geçmişi ozellik.Durum'da tutulur."""

    def __init__(self):
        self.ant = defaultdict(lambda: [0, 0.0])   # antrenör -> [n, Σ(kazandı − q)]
        self.bekleyen = []

    def satirlar(self, kosu, durum, r_alan, kilo_ort, bugun):
        out = []
        mes = kosu["mesafe"] or 1400
        for a in kosu["atlar"]:
            f = dict.fromkeys(A5_ADLAR, 0.0)
            g = durum.at.get(a["ad"], [])
            kf = (a["kilo"] - kilo_ort) if (a["kilo"] and kilo_ort) else 0.0
            f["a5_kilo_x_mes"] = kf * math.log(mes / 1400.0)
            n, r = self.ant.get(a["antrenor"], (0, 0.0))
            if g:
                h0 = g[-1]
                son = g[-10:]
                # --- sınıf-ayarlı form (alan_r: o koşunun alanının ortalama at reytingi, koşudan önce)
                ar = [h["alan_r"] for h in son[-5:] if h.get("alan_r") is not None]
                if ar:
                    f["a5_sr_ort5"] = sum(ar) / len(ar) - r_alan
                if h0.get("alan_r") is not None:
                    f["a5_sr_son"] = h0["alan_r"] - r_alan
                i3 = [h["alan_r"] for h in son if h.get("alan_r") is not None and h["ilk3"]]
                f["a5_sr_ilk3_max"] = (max(i3) - r_alan) if i3 else -0.5
                ust = [h["ilk3"] for h in son if h.get("alan_r") is not None and h["alan_r"] >= r_alan - 0.05]
                f["a5_ust_ilk3"] = (sum(ust) + 0.3) / (len(ust) + 1.0) - 0.3
                # --- göreli kilo değişimi
                if a["kilo"] and kilo_ort and h0.get("kilo_f") is not None:
                    f["a5_kilo_gdeg"] = kf - h0["kilo_f"]
                if a["kilo"] and h0["kilo"] and h0["kazandi"]:
                    f["a5_kilo_kaz"] = a["kilo"] - h0["kilo"]
                iyi = [h["kilo"] for h in son if h["ilk3"] and h["kilo"]]
                if iyi and a["kilo"]:
                    f["a5_kilo_iyi"] = a["kilo"] - max(iyi)
                # --- dinlenme eğrisi
                ara = max(bugun - h0["gun"], 1)
                ort = sum(h["skor"] for h in g) / len(g)
                if ara >= 45:
                    s = [h["skor"] for h in g if (h.get("ara") or 0) >= 45]
                    f["a5_taze_uyum"] = (sum(s) + K_UYUM * ort) / (len(s) + K_UYUM) - ort
                if ara > 60:
                    f["a5_ant_donus"] = r / (n + ANT_K)
                if ara <= 14:
                    s = [h["skor"] for h in g if h.get("ara") is not None and h["ara"] <= 14]
                    f["a5_sik_uyum"] = (sum(s) + K_UYUM * ort) / (len(s) + K_UYUM) - ort
                f["a5_ara_kare"] = (math.log(ara) - math.log(28)) ** 2
                f["a5_yogun30"] = math.log1p(sum(1 for h in g[-6:] if bugun - h["gun"] <= 30))
            out.append(f)
        return out

    def guncelle(self, kosu, q, aralar):
        """Koşu sonucu (gün sonunda uygulanır, aynı günün koşularına sızmaz)."""
        if not q:
            return
        for a, qi, ara in zip(kosu["atlar"], q, aralar):
            if ara is not None and ara > 60 and a["antrenor"]:
                self.bekleyen.append((a["antrenor"], (1.0 if a["sira"] == 1 else 0.0) - qi))

    def gun_sonu(self):
        for t, r in self.bekleyen:
            c = self.ant[t]; c[0] += 1; c[1] += r
        self.bekleyen = []
