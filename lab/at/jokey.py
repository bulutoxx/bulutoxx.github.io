# OXXai at yarışı laboratuvarı — 🏇 jokey ve ahır uzmanı.
#
# 1) ATIN GÜCÜNDEN ARINDIRILMIŞ BECERİ: koşu içi Plackett-Luce (ilk JK_KADEME sıra) ile at + jokey + antrenör güçleri
#    ORTAK tahmin edilir: θ_i = μ_at + μ_jokey + μ_antrenör. Her varlığın güç tahmini Gauss (ortalama μ, varyans σ²):
#    önsel N(0, σ0²) (küçültme), zamanla varyans geri açılır (σ² += τ·gün, σ0² tavanlı), her koşudan sonra tek Newton
#    (Laplace / Kalman) adımı: Δμ_e = σ²_e·g_i / (1 + v_i·h_i), σ²_e −= σ⁴_e·h_i / (1 + v_i·h_i)  (v_i = Σ σ²).
#    Jokeyin μ'sü, aynı at ve antrenörle "ortalama jokey"e göre güç farkıdır (logit birimi).
# 2) "Jokey katkısı" (kalıntı): her binişte kazandı − p_beklenen, p_beklenen = koşu içi softmax(μ_at + μ_antrenör)
#    (jokeysiz; koşudan ÖNCEKİ durumla). Bunun pencereli/koşullu ortalamaları: form (14/30 gün), jokey–antrenör ve
#    jokey–at birlikteliği, pist/mesafe/hipodrom uzmanlığı.
# 3) Diğer sinyaller: jokey değişimi (daha iyi/kötü jokeye geçiş), günlük iş yükü (o gün kaç biniş; günün programından —
#    sabah bilinir), apranti vekili (yeni lisans/az biniş × düşük kilo), "üst jokey seçimi" (jokeyin düzenli çalıştığı
#    başka ahırların atları aynı koşudayken bu ata binmesi; ahırın ana jokeyinin başka ata binmesi = terk).
# Sızıntı yok: özellikler yalnız koşu GÜNÜNDEN önceki sonuçlarla (ozellik.Durum ile aynı gün sırası); iş yükü yalnız
# günün programındaki binişlerden (sonuç değil). Ham koşu satırı yazılmaz; jokeyler.json yalnız türetilmiş istatistiktir.
import json, math, os
from collections import Counter, defaultdict, deque
from datetime import date, datetime, timedelta, timezone

import veri

# ---------------------------------------------------------------- ayarlar
# σ0², τ ve kademeler yalnız A katından ÖNCEKİ dönemde (2025-03 → 2025-10) reytingin tek başına tahmin log-loss'una
# göre küçük bir ızgarada seçildi (sınama katlarına bakılmadan; bkz. deney_jokey.py --ayar).
JK_ONSEL = {"at": 0.80, "jokey": 0.30, "antrenor": 0.06}       # σ0² (logit²) — küçültme gücü
JK_SURUKLE = {"at": 0.80 / 365, "jokey": 0.20 / 365, "antrenor": 0.04 / 365}   # τ (σ² artışı / gün)
JK_TABAN = 0.05        # varyans tabanı (önselin oranı) — aşırı güveni engeller
JK_KADEME = (1.0, 0.5, 0.25)   # PL kademe ağırlıkları (1., 2., 3. sıra)
MESAFE_K = ((0, 1400, "kısa"), (1400, 2000, "orta"), (2000, 99999, "uzun"))
UZ_YARI = 180.0        # uzmanlık kalıntılarının yarı ömrü (gün)
IKILI_YARI = 365.0     # jokey–antrenör / jokey–at birlikteliği yarı ömrü

JK_OZELLIKLER = [
    # beceri: ortak (at+jokey+antrenör) Bayes PL tahmini
    ("jk_j", "jk_beceri"), ("jk_jz", "jk_beceri"), ("jk_t", "jk_beceri"), ("jk_at", "jk_beceri"),
    ("jk_at_s", "jk_beceri"), ("jk_logp", "jk_beceri"),
    # ikili uyum
    ("jk_jt", "jk_ikili"), ("jk_jt_n", "jk_ikili"), ("jk_ja", "jk_ikili"), ("jk_ja_n", "jk_ikili"),
    # jokey değişimi
    ("jk_dj", "jk_degisim"), ("jk_ust", "jk_degisim"), ("jk_alt", "jk_degisim"), ("jk_yeni_ikili", "jk_degisim"),
    # form momentumu (14/30 gün)
    ("jk_f14", "jk_form"), ("jk_f30", "jk_form"), ("jk_mom", "jk_form"), ("jk_tf30", "jk_form"),
    # günlük iş yükü
    ("jk_yuk", "jk_yuk"), ("jk_tek", "jk_yuk"),
    # uzmanlık
    ("jk_uz_pist", "jk_uzman"), ("jk_uz_mes", "jk_uzman"), ("jk_uz_hip", "jk_uzman"),
    # apranti vekili
    ("jk_apr", "jk_apr"), ("jk_apr_kilo", "jk_apr"), ("jk_tecrube", "jk_apr"),
    # üst jokey seçimi / ahır jokeyi
    ("jk_secim", "jk_secim"), ("jk_secim_ust", "jk_secim"), ("jk_terk", "jk_secim"), ("jk_ana", "jk_secim"),
]
JK_ADLAR = [o[0] for o in JK_OZELLIKLER]
JK_GRUPLAR = list(dict.fromkeys(g for _, g in JK_OZELLIKLER))
# Kapıdan geçen gruplar (lab/at/deney_jokey.py ile seçilir; yayın tarifine eklenir — bkz. ozellik.SECILI_GRUPLAR)
# Jokey turu (deney4 iki katlı kapı, 26.10.2026): jk_uzman ve jk_apr ilk turda, jk_beceri yeni tabanda geçti;
# jk_ikili, jk_degisim, jk_form, jk_yuk, jk_secim elendi. Toplam ΔLL (yalnız model) −0,0114 [−0,0157; −0,0074].
JK_SECILI = ["jk_uzman", "jk_apr", "jk_beceri"]

IFADE = {
    "jk_j": ("jokeyi (attan arındırılmış) güçlü", "jokeyi (attan arındırılmış) zayıf"),
    "jk_jz": ("jokeyinin becerisi istatistiksel olarak belirgin", ""),
    "jk_t": ("ahırı (attan arındırılmış) güçlü", "ahırı (attan arındırılmış) zayıf"),
    "jk_at": ("at gücü (jokeyden arındırılmış) yüksek", "at gücü (jokeyden arındırılmış) düşük"),
    "jk_at_s": ("at gücü henüz belirsiz", ""), "jk_logp": ("at+jokey+ahır gücü alanın üstünde", "at+jokey+ahır gücü alanın altında"),
    "jk_jt": ("jokey–antrenör ikilisi beklentinin üstünde", "jokey–antrenör ikilisi beklentinin altında"),
    "jk_jt_n": ("jokey bu ahırla sık çalışıyor", ""), "jk_ja": ("jokey bu atla iyi sonuç almış", "jokey bu atla sonuç alamamış"),
    "jk_ja_n": ("jokey bu ata sık biniyor", ""),
    "jk_dj": ("daha iyi bir jokeye geçti", "daha zayıf bir jokeye geçti"), "jk_ust": ("jokey yükseltmesi", ""),
    "jk_alt": ("jokey düşürmesi", ""), "jk_yeni_ikili": ("jokey bu ata ilk kez biniyor", ""),
    "jk_f14": ("jokeyi son 14 günde beklentinin üstünde", "jokeyi son 14 günde beklentinin altında"),
    "jk_f30": ("jokeyi son 30 günde beklentinin üstünde", "jokeyi son 30 günde beklentinin altında"),
    "jk_mom": ("jokeyinin formu yükselişte", "jokeyinin formu düşüşte"),
    "jk_tf30": ("ahırı son 30 günde beklentinin üstünde", "ahırı son 30 günde beklentinin altında"),
    "jk_yuk": ("jokeyin bugün çok binişi var", "jokeyin bugün az binişi var"),
    "jk_tek": ("jokey bugün yalnız bu ata biniyor", ""),
    "jk_uz_pist": ("jokeyi bu pistte başarılı", "jokeyi bu pistte zayıf"),
    "jk_uz_mes": ("jokeyi bu mesafede başarılı", "jokeyi bu mesafede zayıf"),
    "jk_uz_hip": ("jokeyi bu hipodromda başarılı", "jokeyi bu hipodromda zayıf"),
    "jk_apr": ("apranti (az tecrübeli) jokey", ""), "jk_apr_kilo": ("", ""), "jk_tecrube": ("tecrübeli jokey", "az tecrübeli jokey"),
    "jk_secim": ("jokey başka ahırların atları yerine bunu seçti", ""), "jk_secim_ust": ("üst jokey bu atı seçti", ""),
    "jk_terk": ("ahırın ana jokeyi başka ata biniyor", ""), "jk_ana": ("ahırın ana jokeyi binişte", ""),
}


def gun_no(t):
    return date.fromisoformat(t).toordinal()


def mesafe_k(m):
    for lo, hi, ad_ in MESAFE_K:
        if lo <= (m or 0) < hi:
            return ad_
    return "orta"


def _softmax(s):
    mx = max(s)
    e = [math.exp(v - mx) for v in s]
    z = sum(e)
    return [v / z for v in e]


class _Pen:
    """Kayan pencere toplamları: (gün, kalıntı, varyans p(1−p), kazandı, ilk3)."""
    __slots__ = ("d", "gun", "n", "r", "v", "w", "i3")

    def __init__(self, gun):
        self.d, self.gun, self.n, self.r, self.v, self.w, self.i3 = deque(), gun, 0, 0.0, 0.0, 0, 0

    def ekle(self, g, r, v, w, i3):
        self.d.append((g, r, v, w, i3)); self.n += 1; self.r += r; self.v += v; self.w += w; self.i3 += i3

    def buda(self, bugun):
        while self.d and self.d[0][0] <= bugun - self.gun:
            _, r, v, w, i3 = self.d.popleft(); self.n -= 1; self.r -= r; self.v -= v; self.w -= w; self.i3 -= i3
        return self


class _Sonum:
    """Üstel sönümlü (yarı ömür) toplam: [n, Σ kalıntı] — O(1) güncelleme."""
    __slots__ = ("n", "r", "g")

    def __init__(self):
        self.n, self.r, self.g = 0.0, 0.0, None

    def oku(self, bugun, yari):
        if self.g is None:
            return 0.0, 0.0
        c = 0.5 ** ((bugun - self.g) / yari)
        return self.n * c, self.r * c

    def ekle(self, bugun, r, yari):
        n, s = self.oku(bugun, yari)
        self.n, self.r, self.g = n + 1.0, s + r, bugun


class JokeyDurum:
    def __init__(self):
        self.mu = {k: defaultdict(float) for k in JK_ONSEL}
        self.var = {k: {} for k in JK_ONSEL}          # varlık -> (σ², son güncelleme günü)
        self.son_jokey = {}                            # at -> son jokeyi
        self.jp14 = defaultdict(lambda: _Pen(14)); self.jp30 = defaultdict(lambda: _Pen(30))
        self.jp90 = defaultdict(lambda: _Pen(90)); self.jp365 = defaultdict(lambda: _Pen(365))
        self.tp30 = defaultdict(lambda: _Pen(30)); self.tp90 = defaultdict(lambda: _Pen(90))
        self.ikili_jt = defaultdict(_Sonum); self.ikili_ja = defaultdict(_Sonum)
        self.uz = defaultdict(_Sonum)                  # (jokey, tür, değer) -> sönümlü kalıntı
        self.uz_t = defaultdict(_Sonum)                # (antrenör, tür, değer)
        self.tum_j = defaultdict(_Sonum)               # jokey -> tüm sönümlü kalıntı (uzmanlık tabanı)
        self.tum_t = defaultdict(_Sonum)
        self.jn = Counter()                            # jokey toplam biniş (veri başından beri)
        self.ilk_gun = {}                              # jokey -> ilk görüldüğü gün
        self.j_ahir = defaultdict(deque)               # jokey -> (gün, antrenör) son 90 gün
        self.t_jokey = defaultdict(deque)              # antrenör -> (gün, jokey) son 90 gün
        self.kart = {}                                 # tarih -> (jokey Counter, jokey×hipodrom Counter)
        self.veri_bas = None
        self._gc_gun, self._duz, self._ana = None, {}, {}

    # ---------------------------------------------------------------- Bayes güç
    def _v(self, tur, ad_, bugun):
        s0 = JK_ONSEL[tur]
        x = self.var[tur].get(ad_)
        if x is None:
            return s0
        v, g = x
        return min(v + JK_SURUKLE[tur] * max(bugun - g, 0), s0)

    def theta(self, kosu, bugun, jokeysiz=False):
        th, vv = [], []
        for a in kosu["atlar"]:
            t = self.mu["at"].get(a["ad"], 0.0) + self.mu["antrenor"].get(a["antrenor"], 0.0)
            v = self._v("at", a["ad"], bugun) + self._v("antrenor", a["antrenor"], bugun)
            if not jokeysiz:
                t += self.mu["jokey"].get(a["jokey"], 0.0)
                v += self._v("jokey", a["jokey"], bugun)
            th.append(t); vv.append(v)
        return th, vv

    def _pl(self, th, sira):
        """PL log-olabilirliğinin θ'ya göre gradyanı ve köşegen Hessian'ı (kademe ağırlıklı)."""
        N = len(th)
        o = sorted(range(N), key=lambda i: sira[i])
        g, h = [0.0] * N, [0.0] * N
        kalan = list(o)
        for k, ag in enumerate(JK_KADEME):
            if len(kalan) < 2 or k >= N - 1:
                break
            p = _softmax([th[i] for i in kalan])
            for i, pi in zip(kalan, p):
                g[i] -= ag * pi; h[i] += ag * pi * (1 - pi)
            g[o[k]] += ag
            kalan.remove(o[k])
        return g, h

    # ---------------------------------------------------------------- günün programı (iş yükü; sabah bilinir)
    def gun_karti(self, tarih):
        if tarih in self.kart:
            return self.kart[tarih]
        prog = veri.program_yukle(tarih)
        if not prog:
            prog = _sonuc_karti(tarih)
        cj, cjh = Counter(), Counter()
        for k in prog:
            for a in k["atlar"]:
                if a["jokey"]:
                    cj[a["jokey"]] += 1; cjh[(a["jokey"], k["hipodrom"])] += 1
        if len(self.kart) > 4:
            self.kart.pop(next(iter(self.kart)))
        self.kart[tarih] = (cj, cjh)
        return self.kart[tarih]

    @staticmethod
    def _buda90(d, bugun):
        while d and d[0][0] <= bugun - 90:
            d.popleft()
        return d

    # ---------------------------------------------------------------- özellikler (yalnız geçmişten)
    def satirlar(self, kosu):
        bugun = gun_no(kosu["tarih"])
        atlar = kosu["atlar"]
        N = len(atlar)
        th, _ = self.theta(kosu, bugun)
        lp = [math.log(max(p, 1e-12)) - math.log(1.0 / N) for p in _softmax(th)]
        cj, _ = self.gun_karti(kosu["tarih"])
        kl = sorted(a["kilo"] for a in atlar if a["kilo"])
        kmed = kl[len(kl) // 2] if kl else None
        # ahır ↔ jokey düzenli ilişkileri (son 90 gün)
        if self._gc_gun != bugun:   # gün içi önbellek (durum gün içinde değişmez)
            self._gc_gun, self._duz, self._ana = bugun, {}, {}
        duzenli, ana = self._duz, self._ana
        for a in atlar:
            j, t = a["jokey"], a["antrenor"]
            if j not in duzenli:
                c = Counter(x for _, x in self._buda90(self.j_ahir[j], bugun)) if j in self.j_ahir else Counter()
                duzenli[j] = {x for x, n in c.items() if n >= 3}
            if t not in ana:
                c = Counter(x for _, x in self._buda90(self.t_jokey[t], bugun)) if t in self.t_jokey else Counter()
                en = c.most_common(1)
                ana[t] = en[0][0] if en and en[0][1] >= 5 and en[0][1] >= 0.3 * sum(c.values()) else None
        jokeyler_bu = {a["jokey"] for a in atlar}
        out = []
        for i, a in enumerate(atlar):
            j, t, at = a["jokey"], a["antrenor"], a["ad"]
            f = {}
            mj = self.mu["jokey"].get(j, 0.0)
            vj = self._v("jokey", j, bugun)
            f["jk_j"] = mj
            f["jk_jz"] = mj / math.sqrt(vj)
            f["jk_t"] = self.mu["antrenor"].get(t, 0.0)
            f["jk_at"] = self.mu["at"].get(at, 0.0)
            f["jk_at_s"] = math.sqrt(self._v("at", at, bugun) / JK_ONSEL["at"])
            f["jk_logp"] = lp[i]
            n, r = self.ikili_jt[(j, t)].oku(bugun, IKILI_YARI) if (j, t) in self.ikili_jt else (0.0, 0.0)
            f["jk_jt"] = r / (n + 10.0); f["jk_jt_n"] = math.log1p(n)
            n, r = self.ikili_ja[(j, at)].oku(bugun, IKILI_YARI) if (j, at) in self.ikili_ja else (0.0, 0.0)
            f["jk_ja"] = r / (n + 3.0); f["jk_ja_n"] = math.log1p(n)
            onc = self.son_jokey.get(at)
            if onc is not None and onc != j:
                d = mj - self.mu["jokey"].get(onc, 0.0)
                f["jk_dj"] = d
                f["jk_ust"] = 1.0 if d > 0.15 else 0.0
                f["jk_alt"] = 1.0 if d < -0.15 else 0.0
            f["jk_yeni_ikili"] = 1.0 if onc is not None and (j, at) not in self.ikili_ja else 0.0
            p14 = self.jp14[j].buda(bugun) if j in self.jp14 else None
            p30 = self.jp30[j].buda(bugun) if j in self.jp30 else None
            p365 = self.jp365[j].buda(bugun) if j in self.jp365 else None
            f["jk_f14"] = p14.r / (p14.n + 5.0) if p14 else 0.0
            f["jk_f30"] = p30.r / (p30.n + 10.0) if p30 else 0.0
            if p30 and p365 and p30.n and p30.v > 0:
                oran = p365.r / (p365.n + 20.0)
                f["jk_mom"] = max(min((p30.r - p30.n * oran) / math.sqrt(p30.v + 1.0), 3.0), -3.0)
            tp = self.tp30[t].buda(bugun) if t in self.tp30 else None
            f["jk_tf30"] = tp.r / (tp.n + 10.0) if tp else 0.0
            nb = max(cj.get(j, 1), 1)
            f["jk_yuk"] = math.log(nb)
            f["jk_tek"] = 1.0 if nb == 1 and self.jn.get(j, 0) >= 20 else 0.0
            nt, rt = self.tum_j[j].oku(bugun, UZ_YARI) if j in self.tum_j else (0.0, 0.0)
            taban = rt / (nt + 15.0)
            for ad_, anah in (("jk_uz_pist", ("p", kosu["pist"])), ("jk_uz_mes", ("m", mesafe_k(kosu["mesafe"]))),
                              ("jk_uz_hip", ("h", kosu["hipodrom"]))):
                k = (j,) + anah
                if k in self.uz:
                    n, r = self.uz[k].oku(bugun, UZ_YARI)
                    f[ad_] = (r + 15.0 * taban) / (n + 15.0) - taban
            nj = self.jn.get(j, 0)
            ig = self.ilk_gun.get(j)
            yeni_lisans = ig is not None and self.veri_bas is not None and ig - self.veri_bas > 60 and bugun - ig < 365
            apr = 1.0 if nj < 40 or (yeni_lisans and nj < 200) else 0.0
            f["jk_apr"] = apr
            f["jk_apr_kilo"] = apr * (a["kilo"] - kmed) if (a["kilo"] and kmed) else 0.0
            f["jk_tecrube"] = math.log1p(nj)
            # üst jokey seçimi: jokeyin düzenli çalıştığı başka ahırların atları da bu koşuda
            alt = sum(1 for b in atlar if b is not a and b["antrenor"] != t and b["antrenor"] in duzenli[j])
            f["jk_secim"] = 1.0 if alt else 0.0
            f["jk_secim_ust"] = f["jk_secim"] * max(mj, 0.0) / math.sqrt(JK_ONSEL["jokey"])
            aj = ana.get(t)
            f["jk_terk"] = 1.0 if aj and aj != j and aj in jokeyler_bu else 0.0
            f["jk_ana"] = 1.0 if aj and aj == j else 0.0
            out.append(f)
        return out

    # ---------------------------------------------------------------- güncelleme (koşu bittikten sonra)
    def guncelle(self, kosu):
        bugun = gun_no(kosu["tarih"])
        if self.veri_bas is None:
            self.veri_bas = bugun
        atlar = kosu["atlar"]
        N = len(atlar)
        sira = [a["sira"] or N for a in atlar]
        # jokeysiz beklenti (kalıntı için) — güncellemeden ÖNCE
        th0, _ = self.theta(kosu, bugun, jokeysiz=True)
        p0 = _softmax(th0)
        for i, a in enumerate(atlar):
            j, t, at = a["jokey"], a["antrenor"], a["ad"]
            won = 1 if sira[i] == 1 else 0
            i3 = 1 if sira[i] <= 3 else 0
            r = won - p0[i]; v = p0[i] * (1 - p0[i])
            for pen in (self.jp14, self.jp30, self.jp90, self.jp365):
                pen[j].ekle(bugun, r, v, won, i3)
            self.tp30[t].ekle(bugun, r, v, won, i3); self.tp90[t].ekle(bugun, r, v, won, i3)
            self.ikili_jt[(j, t)].ekle(bugun, r, IKILI_YARI)
            self.ikili_ja[(j, at)].ekle(bugun, r, IKILI_YARI)
            for anah in (("p", kosu["pist"]), ("m", mesafe_k(kosu["mesafe"])), ("h", kosu["hipodrom"])):
                self.uz[(j,) + anah].ekle(bugun, r, UZ_YARI)
                self.uz_t[(t,) + anah].ekle(bugun, r, UZ_YARI)
            self.tum_j[j].ekle(bugun, r, UZ_YARI); self.tum_t[t].ekle(bugun, r, UZ_YARI)
            self.jn[j] += 1
            self.ilk_gun.setdefault(j, bugun)
            self.j_ahir[j].append((bugun, t)); self.t_jokey[t].append((bugun, j))
            self._buda90(self.j_ahir[j], bugun); self._buda90(self.t_jokey[t], bugun)
            self.son_jokey[at] = j
        # Bayes PL adımı (at + jokey + antrenör ortak)
        th, vv = self.theta(kosu, bugun)
        g, h = self._pl(th, sira)
        for i, a in enumerate(atlar):
            payda = 1.0 + vv[i] * h[i]
            for tur, ad_ in (("at", a["ad"]), ("jokey", a["jokey"]), ("antrenor", a["antrenor"])):
                s2 = self._v(tur, ad_, bugun)
                self.mu[tur][ad_] += s2 * g[i] / payda
                s2 = max(s2 - s2 * s2 * h[i] / payda, JK_TABAN * JK_ONSEL[tur])
                self.var[tur][ad_] = (s2, bugun)

    def gun_sonu(self):
        pass

    # ---------------------------------------------------------------- arayüz özeti
    def katki_puan(self, mu):
        """Logit güç farkını olasılık puanına çevirir: 10 atlı alanda ortalama ata göre kazanma olasılığı farkı (puan)."""
        return 100.0 * (math.exp(mu) / (math.exp(mu) + 9.0) - 0.1)


def _sonuc_karti(tarih):
    """Programı olmayan (eski) günler için o günün koşu kartı (yalnız jokey binişleri sayılır; sonuç alanı kullanılmaz)."""
    f = os.path.join(veri.KAYNAK, "data", "results", tarih + ".json")
    try:
        js = json.load(open(f, encoding="utf-8"))
    except Exception:
        return []
    out = [veri._kosu(r, sonuc=False) for r in js if r.get("venue") in veri.YERLI]
    return [k for k in out if len(k["atlar"]) >= 2]


# ---------------------------------------------------------------- toplu (batch) arındırılmış beceri — arayüz için
TOPLU_GUN, TOPLU_YARI = 365, 180.0     # son 365 günün koşuları, yarı ömür 180 gün ağırlıkla
TOPLU_ONSEL = {"at": 0.80, "jokey": 0.30, "antrenor": 0.06, "ikili": 0.05}   # ridge = 1/σ0² (Bayes MAP)


def toplu_beceri(kosular, bitis=None, iters=60):
    """Son TOPLU_GUN günde koşu içi patlatılmış PL (1. sıra ağırlık 1, 2. sıra 0,5) ile at + jokey + antrenör +
    jokey×antrenör ikilisi güçlerinin ORTAK MAP tahmini (ridge önseller, blok köşegen-Newton). Çevrimiçi filtreden
    farkı: atın gücü, başka jokeylerle koştuğu koşular dahil TÜM penceredeki koşularından birlikte öğrenilir; bu yüzden
    "iyi ata binme" (seçim) etkisi jokeyin becerisinden daha iyi ayrılır. Döner: {tür: {ad: (μ, std. hata)}}."""
    import numpy as np
    bitis = bitis or kosular[-1]["tarih"]
    gb = gun_no(bitis)
    idx = {k: {} for k in TOPLU_ONSEL}
    ent = {k: [] for k in TOPLU_ONSEL}
    y, grp, w = [], [], []
    g = 0
    for k in kosular:
        d = gb - gun_no(k["tarih"])
        if d < 0 or d >= TOPLU_GUN:
            continue
        ag = 0.5 ** (d / TOPLU_YARI)
        N = len(k["atlar"])
        sira = [a["sira"] or N for a in k["atlar"]]
        kalan = list(range(N))
        for hedef, kw in ((1, 1.0), (2, 0.5)):
            if len(kalan) < 2 or sum(1 for i in kalan if sira[i] == hedef) != 1:
                break
            for i in kalan:
                a = k["atlar"][i]
                for tur, ad_ in (("at", a["ad"]), ("jokey", a["jokey"]), ("antrenor", a["antrenor"]),
                                 ("ikili", (a["jokey"], a["antrenor"]))):
                    ent[tur].append(idx[tur].setdefault(ad_, len(idx[tur])))
                y.append(1.0 if sira[i] == hedef else 0.0); grp.append(g); w.append(ag * kw)
            g += 1
            kalan = [i for i in kalan if sira[i] != hedef]
    if not y:
        return {k: {} for k in TOPLU_ONSEL}
    y, grp, w = np.asarray(y), np.asarray(grp), np.asarray(w)
    E = {k: np.asarray(v) for k, v in ent.items()}
    mu = {k: np.zeros(len(idx[k])) for k in TOPLU_ONSEL}
    lam = {k: 1.0 / v for k, v in TOPLU_ONSEL.items()}
    bas = np.flatnonzero(np.r_[True, grp[1:] != grp[:-1]])

    def olas():
        s = sum(mu[k][E[k]] for k in mu)
        mx = np.maximum.reduceat(s, bas)[grp]
        e = np.exp(s - mx)
        return e / np.add.reduceat(e, bas)[grp]
    for _ in range(iters):
        for k in ("at", "jokey", "antrenor", "ikili"):
            p = olas()
            gr = np.bincount(E[k], w * (y - p), len(mu[k])) - lam[k] * mu[k]
            hs = np.bincount(E[k], w * p * (1 - p), len(mu[k])) + lam[k]
            mu[k] += gr / hs
    p = olas()
    out = {}
    for k in mu:
        hs = np.bincount(E[k], w * p * (1 - p), len(mu[k])) + lam[k]
        se = 1.0 / np.sqrt(hs)
        out[k] = {ad_: (float(mu[k][i]), float(se[i])) for ad_, i in idx[k].items()}
    return out


# ---------------------------------------------------------------- data/at/jokeyler.json
def _uzmanlik(jd, anahtar_sozluk, kim, bugun):
    """(kim, tür, değer) sönümlü kalıntılarından en iyi pist / mesafe / hipodrom (en az 15 etkin biniş)."""
    sonuc = {}
    for tur, et in (("p", "pist"), ("m", "mesafe"), ("h", "hipodrom")):
        en = None
        for k, s in anahtar_sozluk.get((kim, tur), []):
            n, r = s.oku(bugun, UZ_YARI)
            if n < 15:
                continue
            v = r / (n + 15.0)
            if en is None or v > en[0]:
                en = (v, k)
        sonuc[et] = en[1] if en else None
    return sonuc


def jokeyler_json(kosular, jd, bugun=None, tahmin_dosyasi=None, ilk_j=40, ilk_t=25, ilk_i=15, deney=None):
    """Arayüz için türetilmiş jokey/antrenör istatistikleri. jd: tüm sonuçlarla ilerletilmiş JokeyDurum."""
    son = kosular[-1]["tarih"]
    gs = gun_no(son)
    bas = (date.fromordinal(gs - 89)).isoformat()
    st_j = defaultdict(lambda: [0, 0, 0]); st_t = defaultdict(lambda: [0, 0, 0]); st_i = defaultdict(lambda: [0, 0])
    for k in kosular:
        if k["tarih"] < bas:
            continue
        for a in k["atlar"]:
            w = 1 if a["sira"] == 1 else 0
            i3 = 1 if (a["sira"] or 99) <= 3 else 0
            for st, ad_ in ((st_j, a["jokey"]), (st_t, a["antrenor"])):
                s = st[ad_]; s[0] += 1; s[1] += w; s[2] += i3
            s = st_i[(a["jokey"], a["antrenor"])]; s[0] += 1; s[1] += w
    gb = gs + 1   # "bugün": son sonuç gününden sonraki ilk gün (varyans sürüklenmesi için)
    # uzmanlık indeksleri
    idx_j, idx_t = defaultdict(list), defaultdict(list)
    for (kim, tur, deger), s in jd.uz.items():
        idx_j[(kim, tur)].append((deger, s))
    for (kim, tur, deger), s in jd.uz_t.items():
        idx_t[(kim, tur)].append((deger, s))

    def trend(pen30, pen365):
        if not pen30 or not pen30.n or pen30.v <= 0:
            return "sabit"
        oran = pen365.r / (pen365.n + 20.0) if pen365 else 0.0
        z = (pen30.r - pen30.n * oran) / math.sqrt(pen30.v + 1.0)
        return "yukseliyor" if z > 1.0 else ("dusuyor" if z < -1.0 else "sabit")

    # bugünkü binişler: jokey programdan, olasılık kilitli sabah tahmininden (yalnız model; kilit yoksa None)
    bugun_b = defaultdict(list)
    pk = {}
    if tahmin_dosyasi and os.path.exists(tahmin_dosyasi):
        try:
            tj = json.load(open(tahmin_dosyasi, encoding="utf-8"))
            for kp in tj.get("kosular", []):
                for x in kp.get("atlar", []):
                    pk[(kp["kosu_id"], x["ad"])] = x["p_kazanma"]
        except Exception:
            pass
    if bugun:
        for k in veri.program_yukle(bugun):
            kid = f'{k["tarih"]}/{k["hipodrom"]}/{k["kosu"]}'
            for a in k["atlar"]:
                if a["jokey"]:
                    bugun_b[a["jokey"]].append({"kosu_id": kid, "at": a["ad"], "p_kazanma": pk.get((kid, a["ad"]))})
    # toplu (batch) arındırılmış beceri; 90 günün binişlerine göre ortalanır ("ortalama jokey" = 0)
    tb = toplu_beceri(kosular, son)
    ort = {}
    for tur, st in (("jokey", st_j), ("antrenor", st_t)):
        top = sum(st[x][0] * tb[tur].get(x, (0.0, 1.0))[0] for x in st)
        ort[tur] = top / max(sum(v[0] for v in st.values()), 1)

    def kayit(ad_, st, tur):
        mu0, se = tb[tur].get(ad_, (0.0, 1.0))
        mu = mu0 - ort[tur]
        pen30 = (jd.jp30 if tur == "jokey" else jd.tp30).get(ad_)
        pen365 = (jd.jp365 if tur == "jokey" else jd.tp90).get(ad_)
        if pen30:
            pen30.buda(gb)
        if pen365:
            pen365.buda(gb)
        return {"ad": ad_, "binis_90g": st[0], "kazanma_90g": round(st[1] / st[0], 4), "ilk3_90g": round(st[2] / st[0], 4),
                "katki": round(jd.katki_puan(mu), 2), "katki_logit": round(mu, 4), "katki_z": round(mu / se, 2),
                "form_trend": trend(pen30, pen365),
                "uzmanlik": _uzmanlik(jd, idx_j if tur == "jokey" else idx_t, ad_, gb)}

    jok = [kayit(j, s, "jokey") for j, s in st_j.items() if s[0] >= 30 and j]
    jok.sort(key=lambda d: (-d["katki"], -d["binis_90g"]))
    jok = jok[:ilk_j]
    for d in jok:
        d["bugun_binis"] = sorted(bugun_b.get(d["ad"], []), key=lambda x: x["kosu_id"])
    ant = [kayit(t, s, "antrenor") for t, s in st_t.items() if s[0] >= 30 and t]
    for d in ant:
        d["kosu_90g"] = d.pop("binis_90g")
    ant.sort(key=lambda d: (-d["katki"], -d["kosu_90g"]))
    ikililer = []
    for (j, t), s in st_i.items():
        if s[0] < 15 or not j or not t:
            continue
        mu, se = tb["ikili"].get((j, t), (0.0, 1.0))
        top = mu + tb["jokey"].get(j, (0.0, 1.0))[0] - ort["jokey"] + tb["antrenor"].get(t, (0.0, 1.0))[0] - ort["antrenor"]
        ikililer.append({"jokey": j, "antrenor": t, "binis": s[0], "kazanma": round(s[1] / s[0], 4),
                         "katki": round(jd.katki_puan(top), 2), "uyum": round(jd.katki_puan(mu), 2), "uyum_z": round(mu / se, 2)})
    ikililer.sort(key=lambda d: (-d["katki"], -d["binis"]))
    out = {"guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"), "donem": [bas, son],
           "aciklama": ("katki: attan ve ahırdan arındırılmış jokey becerisi — son 365 günün koşularında at + jokey + "
                        "antrenör + jokey×antrenör güçlerinin koşu içi Plackett-Luce ile ortak, Bayes küçültmeli (ridge) "
                        "tahmini; son 90 günün binişlerine göre ortalanmış. Değer: 10 atlı bir koşuda ortalama ata bu jokey "
                        "binerse kazanma olasılığının ortalama jokeye göre farkı (puan). katki_z = katkı / std. hata. "
                        "Jokeyin iyi atları seçebilmesi (seçim etkisi) tamamen ayrılamaz. İkililerde katki: jokey + antrenör + "
                        "ikili uyumunun toplamı (aynı ölçek); uyum: tek tek becerilerin ÖTESİNDEKİ ikili etkisi (çoğu "
                        "küçük ve gürültülü; uyum_z'ye bakın). form_trend: son 30 gün "
                        "kalıntısı 365 güne göre (z > 1 yükseliyor, < −1 düşüyor). bugun_binis.p_kazanma: sabah kilidi "
                        "(yalnız model). Yalnız türetilmiş istatistik; ham koşu satırı yok. Hobi amaçlıdır · 18+."),
           "kaynak": "github.com/cenkozgur/tjk-data (herkese açık ayna; tjk.org'a istek yok)",
           # en güçlü 5 jokey (attan arındırılmış katkıya göre) — kısa özet
           "ilk5": [{k: d[k] for k in ("ad", "binis_90g", "kazanma_90g", "katki", "katki_z", "form_trend")} for d in jok[:5]],
           "jokeyler": jok, "antrenorler": ant[:ilk_t], "ikililer": ikililer[:ilk_i]}
    if deney:
        out["deney"] = deney
    return out
