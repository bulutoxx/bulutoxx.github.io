# OXXai (eski adı BULUTOXX) at yarışı laboratuvarı — v6 at özellikleri (derin tarama turu, 26.10.2026).
#
# Açık kaynak taraması (lab/at/KAYNAKLAR.md) sonunda TJK dışından yasal + ücretsiz + ölçülebilir tek yeni sinyal
# hava oldu (Open-Meteo arşivi, CC BY 4.0). Diğer adaylar aynanın HENÜZ KULLANILMAYAN boyutlarından türetildi.
#
# Gruplar (deney masası: lab/at/deney6.py, deney4 iki katlı kapı):
#   a6_hava    : hipodromun yağış/ıslaklık endeksi (yarış günü + önceki 3 gün, yarı ömürlü), sıcaklık; atın ıslak
#                pistteki kişisel uyumu (küçültmeli), ıslaklık × (uyum, alan içi reyting, kilo, çim). Pist durumu
#                (trackCondition) aynada yalnız 2026-04'ten beri ve çoğu gün yarış saatine yakın yazılıyor; hava ise
#                2023'ten beri her gün için var → sabah kilidinde bilinen bir pist durumu vekili.
#   a6_pist    : AYNADAN sabah bilinen pist/hava vekili (TJK dışı istek yok; yalnız cenkozgur/tjk-data günlük programları,
#                2026-04'ten beri): yarış günü programındaki hava (yağmur/sağanak bayrağı), nem, sıcaklık; aynı hipodrom
#                ve aynı pist türünde ÖNCEKİ yarış gününün pist durumu (ıslaklık sırası, gün aralığıyla sönümlü). Atın
#                ıslak pist uyumu × beklenen ıslaklık, × kilo, × reyting. v3'te elenen "zemin" grubundan farkı: yarış
#                günü pist durumunu (çoğu gün 14:00'te yazılıyor) KULLANMAZ → sabah kilidinde de aynı değer.
#   a6_kalman  : at başına durum-uzay (Kalman) hız figürü: yetenek zamanla rastgele yürür (gün başına süreç varyansı),
#                her figür gürültülü bir gözlem. Ortalama − alan ortalaması, belirsizlik, z, alan içi sıra; figür
#                tutarlılığı (son 6 figürün std'si, küçültmeli).
#   a6_mesafe  : mesafe profili: ±%10 mesafedeki en iyi figür − genel en iyi, figür–log(mesafe) eğimi (küçültmeli) ×
#                bugünkü mesafe sapması, en iyi figürün mesafesine uzaklık.
#   a6_gelisim : yaş × ara gelişim eğrisi: aynı atın ardışık figür farkının (yaş, ara kovası) ortalaması (çevrimiçi,
#                küçültmeli) → bugünkü beklenen gelişim, alana göre.
# Sızıntı yok: atın geçmişi ozellik.Durum'da gün sonunda eklenir; Kalman ve gelişim tabloları gün sonunda (o günün
# figürleri hesaplandıktan SONRA) güncellenir; hava yalnız (hipodrom, tarih) ile okunur — üretimde yarış günü değeri
# Open-Meteo TAHMİNİ, önceki günler arşiv/yeniden analiz (lab/at/hava.py).
import csv, math, os
from collections import defaultdict
from datetime import date, timedelta

KOK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

A6_OZELLIKLER = [
    ("a6_h_islak", "a6_hava"), ("a6_h_yok", "a6_hava"), ("a6_h_sicak", "a6_hava"), ("a6_h_uyum", "a6_hava"),
    ("a6_h_x_uyum", "a6_hava"), ("a6_h_x_r", "a6_hava"), ("a6_h_x_kilo", "a6_hava"), ("a6_h_x_cim", "a6_hava"),
    ("a6_p_yagmur", "a6_pist"), ("a6_p_nem", "a6_pist"), ("a6_p_sicak", "a6_pist"), ("a6_p_dun", "a6_pist"),
    ("a6_p_yok", "a6_pist"), ("a6_p_x_uyum", "a6_pist"), ("a6_p_x_kilo", "a6_pist"), ("a6_p_x_r", "a6_pist"),
    ("a6_k_m", "a6_kalman"), ("a6_k_sd", "a6_kalman"), ("a6_k_z", "a6_kalman"), ("a6_k_sira", "a6_kalman"),
    ("a6_k_tutarli", "a6_kalman"),
    ("a6_m_yakin", "a6_mesafe"), ("a6_m_egim", "a6_mesafe"), ("a6_m_uzak", "a6_mesafe"),
    ("a6_g_proj", "a6_gelisim"), ("a6_g_alan", "a6_gelisim"),
]
A6_ADLAR = [o[0] for o in A6_OZELLIKLER]
A6_GRUPLAR = list(dict.fromkeys(g for _, g in A6_OZELLIKLER))
# Kapıdan geçen gruplar (lab/at/deney6.py ile seçilir; yayın tarifine eklenir — bkz. ozellik.SECILI_GRUPLAR)
# 27.10.2026 deney6: a6_kalman ΔLL −0,0037 [−0,0065; −0,0009], a6_mesafe −0,0010, a6_gelisim −0,0007 kapıyı geçti;
# toplam −0,0055 [−0,0084; −0,0023]. a6_pist (±0,0000) ve m6_rank (+0,0006) elendi; a6_hava ölçülemedi.
A6_SECILI = ["a6_kalman", "a6_mesafe", "a6_gelisim"]

IFADE = {
    "a6_h_uyum": ("ıslak pistte formu iyi", "ıslak pistte formu zayıf"),
    "a6_k_m": ("hız figürü eğilimi (Kalman) alanın üstünde", "hız figürü eğilimi (Kalman) alanın altında"),
    "a6_m_yakin": ("bu mesafede en iyi derecelerini yapıyor", "en iyi dereceleri başka mesafede"),
    "a6_p_x_uyum": ("ağır/ıslak pist beklentisinde formu iyi", "ağır/ıslak pist beklentisinde formu zayıf"),
}

# --- hava (Open-Meteo, CC BY 4.0): hipodrom adı (ascii) -> aynadaki ad
HIPODROM = {"istanbul": "İstanbul", "izmir": "İzmir", "adana": "Adana", "bursa": "Bursa", "ankara": "Ankara",
            "sanliurfa": "Şanlıurfa", "antalya": "Antalya", "elazig": "Elazığ", "kocaeli": "Kocaeli",
            "diyarbakir": "Diyarbakır"}
ISLAK_ESIK = math.log1p(3.0)   # ıslak koşu: ağırlıklı yağış ≥ 3 mm
K_UYUM = 3.0
# --- Kalman (hız figürü ölçeğinde; aynadan ölçüldü: figür sd ≈ 59, ardışık fark varyansı ≈ 580 + 1,5/gün)
K_ONSEL_M, K_ONSEL_V = -31.0, 3500.0
K_R = 290.0       # gözlem (tek koşu figürü) gürültü varyansı
K_Q = 1.5         # süreç varyansı / gün (yetenek rastgele yürüyüşü)
K_V_TAVAN = 3500.0
G_K = 30.0        # gelişim tablosu küçültmesi (sanal gözlem)
# Yarış günü yağışı: üretimde sabah kilidinde Open-Meteo TAHMİNİDİR (deneyde arşiv değeri). Sağlamlık sınaması için
# False → endeks yalnız önceki 3 günden (yarış günü 0 sayılır) ve sıcaklık önceki günden.
HAVA_BUGUN = os.environ.get("AT_HAVA_BUGUN", "1") != "0"


_HAVA_ONBELLEK = {}
# a6_pist: yarış günü programındaki hava/nem/sıcaklık kullanılsın mı (sağlamlık sınaması için False: yalnız önceki günler)
PIST_BUGUN = os.environ.get("AT_PIST_BUGUN", "1") != "0"
_YAGIS = ("YAĞMUR", "SAĞANAK", "FIRTINA", "KAR", "DOLU")
_PROGRAM_ONBELLEK = {}


def program_havasi(kaynak=None):
    """Aynanın günlük programlarından (data/daily) (tarih, hipodrom) -> (yağış bayrağı, nem, sıcaklık) ve
    (tarih, hipodrom, pist) -> o günün en ağır pist durumu sırası. Yalnız ayna okunur; ham veri depoya yazılmaz."""
    import json, re
    import veri
    d = os.path.join(kaynak or veri.KAYNAK, "data", "daily")
    try:
        imza = (d, tuple(sorted(os.listdir(d)))[-1:], len(os.listdir(d)))
    except OSError:
        return {}, {}
    if imza in _PROGRAM_ONBELLEK:
        return _PROGRAM_ONBELLEK[imza]
    hv, zm = {}, {}
    for f in sorted(os.listdir(d)):
        if not re.match(r"\d{4}-\d{2}-\d{2}\.json$", f):
            continue
        try:
            js = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except Exception:
            continue
        for r in js:
            h, t = r.get("venue"), r.get("date") or f[:10]
            if h not in veri.YERLI:
                continue
            w = veri.ad(r.get("weatherCondition"))
            nem = r.get("humidity")
            m = re.search(r"NEM%(\d+)", w)
            if nem in (None, "") and m:
                nem = int(m.group(1))
            if "PDF" in w or "PROGRAM" in w:
                w = ""
            try:
                nem = float(nem) if nem not in (None, "") else None
            except (TypeError, ValueError):
                nem = None
            try:
                sc = float(r.get("temperature")) if r.get("temperature") not in (None, "") else None
            except (TypeError, ValueError):
                sc = None
            yb = (1.0 if any(x in w for x in _YAGIS) else 0.0) if w else None
            eski = hv.get((t, h))
            if eski is None or (eski[0] is None and yb is not None):
                hv[(t, h)] = (yb, nem, sc)
            z = veri.zemin_sira(veri.zemin_norm(r.get("trackCondition")))
            if z is not None:
                k = (t, h, r.get("surface") or "")
                zm[k] = max(zm.get(k, 0), z)
    _PROGRAM_ONBELLEK.clear()
    _PROGRAM_ONBELLEK[imza] = (hv, zm)
    return hv, zm


def hava_yolu():
    return os.environ.get("AT_HAVA") or os.path.join(KOK, "_hava", "gunluk.csv")


def hava_yukle(yol=None):
    """(hipodrom, tarih) -> (yağış mm, ortalama sıcaklık °C). Dosya yoksa boş sözlük (özellikler 'hava yok' olur)."""
    yol = yol or hava_yolu()
    out = {}
    if not os.path.exists(yol):
        return out
    try:
        anahtar = (yol, os.path.getmtime(yol))
    except OSError:
        anahtar = None
    if anahtar and anahtar in _HAVA_ONBELLEK:
        return _HAVA_ONBELLEK[anahtar]
    _HAVA_ONBELLEK.clear()
    if anahtar:
        _HAVA_ONBELLEK[anahtar] = out
    with open(yol, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            h = HIPODROM.get(r.get("hipodrom"), r.get("hipodrom"))
            try:
                y = float(r.get("yagis_mm") or 0.0)
            except ValueError:
                y = 0.0
            try:
                s = float(r.get("sicaklik")) if r.get("sicaklik") not in (None, "") else None
            except ValueError:
                s = None
            out[(h, r["tarih"])] = (y, s)
    return out


def _ara_kova(ara):
    return 0 if ara <= 15 else 1 if ara <= 30 else 2 if ara <= 60 else 3 if ara <= 120 else 4


class A6Durum:
    def __init__(self, hava=None):
        self.hava = hava_yukle() if hava is None else hava
        self._islak_onbellek = {}
        self.kal = {}                                   # at -> [m, v, son gün]
        self.gel = defaultdict(lambda: [0, 0.0])        # (yaş, ara kovası) -> [n, Σ Δfigür]
        self.bekleyen = []                              # (at, yaş) bugün koşanlar
        self._prog = None                               # a6_pist: aynanın program havası/pist tablosu (tembel)

    def _pist_tablolari(self):
        if self._prog is None:
            hv, zm = program_havasi()
            son = defaultdict(list)                     # (hipodrom, pist) -> [(gün, sıra)] zaman sıralı
            for (t, h, p), z in sorted(zm.items()):
                son[(h, p)].append((date.fromisoformat(t).toordinal(), z))
            self._prog = (hv, son)
        return self._prog

    def pist_vekili(self, kosu, bugun):
        """(yağış bayrağı, nem, sıcaklık, önceki gün ıslaklığı, beklenen ıslaklık e∈[0,1]); bilinmeyen None.
        Önceki gün: aynı hipodrom + pist türünde bugünden ÖNCEKİ en son yarış gününün en ağır pist durumu, aralıkla sönümlü."""
        hv, son = self._pist_tablolari()
        yb, nem, sc = hv.get((kosu["tarih"], kosu["hipodrom"]), (None, None, None)) if PIST_BUGUN else (None, None, None)
        dun = None
        L = son.get((kosu["hipodrom"], kosu["pist"]))
        if L:
            import bisect
            i = bisect.bisect_left(L, (bugun, -1)) - 1
            if i >= 0 and bugun - L[i][0] <= 10:
                dun = L[i][1] / 3.0 * 0.5 ** ((bugun - L[i][0] - 1) / 3.0)
        if yb is None and dun is None:
            return None
        e = max(yb or 0.0, dun or 0.0)
        return yb, nem, sc, dun, e

    # ---------------------------------------------------------------- hava
    def islak(self, hipodrom, gun):
        """Ağırlıklı yağış endeksi log1p(y0 + y1/2 + y2/4 + y3/8); bilinmiyorsa None. gun: ordinal."""
        k = (hipodrom, gun)
        if k in self._islak_onbellek:
            return self._islak_onbellek[k]
        t0 = date.fromordinal(gun)
        y0 = self.hava.get((hipodrom, t0.isoformat()))
        v = None
        if y0 is not None:
            w = y0[0] if HAVA_BUGUN else 0.0
            for i in (1, 2, 3):
                yi = self.hava.get((hipodrom, (t0 - timedelta(days=i)).isoformat()))
                w += (yi[0] if yi else 0.0) * 0.5 ** i
            v = math.log1p(max(w, 0.0))
        self._islak_onbellek[k] = v
        return v

    # ---------------------------------------------------------------- özellikler
    _pist_lazim = True

    def satirlar(self, kosu, durum, r_alan, kilo_ort, bugun, r_at_list):
        out = []
        N = len(kosu["atlar"])
        isl = self.islak(kosu["hipodrom"], bugun)
        t = self.hava.get((kosu["hipodrom"], kosu["tarih"] if HAVA_BUGUN else
                           (date.fromordinal(bugun) - timedelta(days=1)).isoformat()))
        sicak = ((t[1] - 15.0) / 10.0) if (t and t[1] is not None) else 0.0
        cim = 1.0 if kosu["pist"] == "Çim" else 0.0
        mes = kosu["mesafe"] or 1400
        pv = self.pist_vekili(kosu, bugun) if self._pist_lazim else None
        # Kalman durumları (bugüne taşınmış)
        km = []
        for a in kosu["atlar"]:
            s = self.kal.get(a["ad"])
            if s:
                v = min(s[1] + K_Q * max(bugun - s[2], 0), K_V_TAVAN)
                km.append((s[0], v))
            else:
                km.append(None)
        bil = [x[0] for x in km if x]
        k_ort = sum(bil) / len(bil) if bil else K_ONSEL_M
        k_min = min(bil) if bil else K_ONSEL_M
        kms = [x[0] if x else k_min for x in km]
        sirali = sorted(kms, reverse=True)
        # gelişim
        gp = []
        for a in kosu["atlar"]:
            g = durum.at.get(a["ad"], [])
            if g and a["yas"]:
                n, s = self.gel.get((int(a["yas"]), _ara_kova(max(bugun - g[-1]["gun"], 1))), (0, 0.0))
                gp.append(s / (n + G_K))
            else:
                gp.append(0.0)
        gp_ort = sum(gp) / N
        for ai, a in enumerate(kosu["atlar"]):
            f = dict.fromkeys(A6_ADLAR, 0.0)
            g = durum.at.get(a["ad"], [])
            kf = (a["kilo"] - kilo_ort) if (a["kilo"] and kilo_ort) else 0.0
            # --- hava
            if isl is None:
                f["a6_h_yok"] = 1.0
            else:
                f["a6_h_islak"] = isl
                f["a6_h_sicak"] = sicak
                f["a6_h_x_r"] = isl * (r_at_list[ai] - r_alan)
                f["a6_h_x_kilo"] = isl * kf
                f["a6_h_x_cim"] = isl * cim
            if g:
                ort = (sum(h["skor"] for h in g) + K_UYUM * 0.5) / (len(g) + K_UYUM)
                s = [h["skor"] for h in g if (self.islak(h["hipodrom"], h["gun"]) or 0.0) >= ISLAK_ESIK]
                if s:
                    f["a6_h_uyum"] = (sum(s) + K_UYUM * ort) / (len(s) + K_UYUM) - ort
                    if isl is not None:
                        f["a6_h_x_uyum"] = isl * f["a6_h_uyum"]
            # --- pist/hava vekili (ayna programı, sabah bilinen)
            if pv is None:
                f["a6_p_yok"] = 1.0
            else:
                yb, nem, sc, dun, e = pv
                f["a6_p_yagmur"] = yb or 0.0
                f["a6_p_nem"] = ((nem - 60.0) / 20.0) if nem is not None else 0.0
                f["a6_p_sicak"] = ((sc - 15.0) / 10.0) if sc is not None else 0.0
                f["a6_p_dun"] = dun or 0.0
                f["a6_p_x_kilo"] = e * kf
                f["a6_p_x_r"] = e * (r_at_list[ai] - r_alan)
                if g:
                    s_ = [h["skor"] for h in g if (h.get("zemin_s") or 0) >= 1]
                    if s_:
                        ort = (sum(h["skor"] for h in g) + K_UYUM * 0.5) / (len(g) + K_UYUM)
                        f["a6_p_x_uyum"] = e * ((sum(s_) + K_UYUM * ort) / (len(s_) + K_UYUM) - ort)
            # --- Kalman
            m = kms[ai]
            v = km[ai][1] if km[ai] else K_ONSEL_V
            f["a6_k_m"] = m - k_ort
            f["a6_k_sd"] = math.sqrt(v) / 30.0
            f["a6_k_z"] = (m - k_ort) / math.sqrt(v + K_R)
            f["a6_k_sira"] = sirali.index(m) / max(N - 1, 1) - 0.5
            hz = [h["hz"] for h in g[-6:] if h.get("hz") is not None]
            if len(hz) >= 2:
                mu = sum(hz) / len(hz)
                sd = math.sqrt(sum((x - mu) ** 2 for x in hz) / (len(hz) - 1))
                f["a6_k_tutarli"] = (sd * len(hz) + 24.0 * 3) / (len(hz) + 3) / 24.0 - 1.0
            # --- mesafe profili
            hm = [(h["hz"], h["mesafe"]) for h in g[-15:] if h.get("hz") is not None and h.get("mesafe")]
            if hm:
                en = max(hm)
                yak = [x for x, d in hm if abs(math.log(d / mes)) <= 0.10]
                f["a6_m_yakin"] = (max(yak) - en[0]) / 30.0 if yak else -1.0
                f["a6_m_uzak"] = abs(math.log(mes / en[1]))
                if len(hm) >= 3:
                    xs = [math.log(d) for _, d in hm]; ys = [x for x, _ in hm]
                    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
                    sxx = sum((x - mx) ** 2 for x in xs)
                    if sxx > 0.005:
                        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
                        b *= len(hm) / (len(hm) + 5.0)
                        f["a6_m_egim"] = max(min(b * (math.log(mes) - mx), 60.0), -60.0) / 30.0
            # --- gelişim
            f["a6_g_proj"] = gp[ai] / 10.0
            f["a6_g_alan"] = (gp[ai] - gp_ort) / 10.0
            out.append(f)
        return out

    # ---------------------------------------------------------------- güncelleme (gün sonu)
    def guncelle(self, kosu):
        for a in kosu["atlar"]:
            self.bekleyen.append((a["ad"], a["yas"]))

    def gun_sonu(self, durum):
        """Günün figürleri (durum._hz_gun_sonu) hesaplandıktan SONRA çağrılır."""
        gel_ek = []
        for ad_, yas in self.bekleyen:
            g = durum.at.get(ad_)
            if not g or g[-1].get("hz") is None:
                continue
            z, gun = g[-1]["hz"], g[-1]["gun"]
            onceki = next((h for h in reversed(g[:-1]) if h.get("hz") is not None), None)
            if onceki is not None and yas:
                gel_ek.append(((int(yas), _ara_kova(max(gun - onceki["gun"], 1))), z - onceki["hz"]))
            s = self.kal.get(ad_)
            if s is None:
                m0, v0 = K_ONSEL_M, K_ONSEL_V
            else:
                m0, v0 = s[0], min(s[1] + K_Q * max(gun - s[2], 0), K_V_TAVAN)
            k = v0 / (v0 + K_R)
            self.kal[ad_] = [m0 + k * (z - m0), (1 - k) * v0, gun]
        for key, d in gel_ek:
            c = self.gel[key]; c[0] += 1; c[1] += max(min(d, 80.0), -80.0)
        self.bekleyen = []


def hava_hazirla():
    """Üretim kancası (gece.py, canli.py): a6_hava yayındaysa Open-Meteo'dan _hava/gunluk.csv'yi tazeler (lab/at/hava.py).
    Hata yayını durdurmaz; dosya yoksa özellikler 'hava yok' olur."""
    if "a6_hava" not in A6_SECILI:
        return None
    try:
        import hava
        n = hava.guncelle()
        _HAVA_ONBELLEK.clear()
        return n
    except Exception as e:   # noqa: BLE001
        print("hava hazırlanamadı:", type(e).__name__, e)
        return None
