# OXXai at yarışı laboratuvarı — koşu içi koşullu logit (Benter) + isteğe bağlı GBM + piyasa harmanı + Harville/Henery.
# Değerlendirme zaman sıralıdır: ısınma | eğitim | SINAMA (son %30, aylık walk-forward yeniden eğitimle).
import math
import os

import numpy as np

ISINMA_SONU = "2025-03-01"   # bu tarihten önceki koşular yalnız geçmiş biriktirmek içindir (özellikler boş)
SINAMA_PAYI = 0.30
HARMAN_PAYI = 0.15           # sınamadan hemen önceki dilim: α, β, sıcaklık, γ, δ burada öğrenilir
LAMBDALAR = [0.3, 3.0, 30.0, 300.0]
KOVALAR = [0.0, 0.05, 0.10, 0.20, 0.30, 0.50, 1.0001]


# ---------------------------------------------------------------- koşu kümeleri
class Kume:
    """Koşu sırasına göre bitişik satırlar. bas: her koşunun ilk satırı."""

    def __init__(self, X, y, sira, q, kosu_no):
        self.X, self.y, self.sira, self.q, self.kosu_no = X, y, sira, q, kosu_no
        deg = np.r_[True, kosu_no[1:] != kosu_no[:-1]]
        self.bas = np.flatnonzero(deg)
        self.seg = np.cumsum(deg) - 1
        self.R = len(self.bas)
        self.n = np.diff(np.r_[self.bas, len(y)])

    def alt(self, satir_maskesi):
        m = satir_maskesi
        return Kume(self.X[m], self.y[m], self.sira[m], self.q[m], self.kosu_no[m])


def softmax_kosu(s, K):
    mx = np.maximum.reduceat(s, K.bas)
    e = np.exp(s - mx[K.seg])
    return e / np.add.reduceat(e, K.bas)[K.seg]


def clogit(X, K, lam=1.0, iters=50, w0=None, agirlik=None):
    """Koşu içi koşullu logit, L2 (lam), Newton yöntemi. X standartlaştırılmış olmalı.
    agirlik: koşu başına ağırlık (zaman ağırlıklı eğitim için); None = hepsi 1."""
    d = X.shape[1]
    w = np.zeros(d) if w0 is None else w0.copy()
    rw = np.ones(K.R) if agirlik is None else np.asarray(agirlik, float)
    sw = rw[K.seg]
    onceki = None
    for _ in range(iters):
        p = softmax_kosu(X @ w, K)
        ll = np.sum((sw * np.log(p + 1e-300))[K.y > 0]) - 0.5 * lam * w @ w
        g = X.T @ (sw * (K.y - p)) - lam * w
        M = np.add.reduceat(p[:, None] * X, K.bas)
        H = (X * (sw * p)[:, None]).T @ X - (M * rw[:, None]).T @ M + lam * np.eye(d)
        adim = np.linalg.solve(H + 1e-9 * np.eye(d), g)
        w = w + adim
        if onceki is not None and abs(ll - onceki) < 1e-7 * max(1.0, abs(ll)):
            break
        onceki = ll
    return w


def logloss(p, K):
    return float(-np.mean(np.log(np.clip(p[K.y > 0], 1e-12, 1))))


# ---------------------------------------------------------------- Harville + Henery
def henery_ussu(p, K, yer=2):
    """2. (yer=2) veya 3. (yer=3) sıra için üs: P(j | öncekiler) ∝ p_j^γ. Izgara üzerinde olabilirlik."""
    en, eniyi = -1e18, 1.0
    lp = np.log(np.clip(p, 1e-12, 1))
    for gam in np.arange(0.40, 1.31, 0.02):
        top = 0.0
        for r in range(K.R):
            a, b = K.bas[r], K.bas[r] + K.n[r]
            s = K.sira[a:b]
            if np.sum(s == yer) != 1 or K.n[r] <= yer:
                continue
            kalan = s >= yer
            v = gam * lp[a:b]
            mx = v[kalan].max()
            top += v[s == yer][0] - (mx + math.log(np.exp(v[kalan] - mx).sum()))
        if top > en:
            en, eniyi = top, float(gam)
    return round(eniyi, 2)


def sira_ll(p, K, gam=1.0, dlt=1.0):
    """İndirimli Harville sınaması: gerçek (1., 2.) ikilisinin ve (1., 2., 3.) üçlüsünün koşu başına −log olasılığı.
    P(i 1., j 2., k 3.) = p_i · p_j^γ/Σ_{l≠i} p_l^γ · p_k^δ/Σ_{l≠i,j} p_l^δ (her adımda yeniden normalize)."""
    l2, l3 = [], []
    lp = np.log(np.clip(p, 1e-12, 1))
    for r in range(K.R):
        a, b = K.bas[r], K.bas[r] + K.n[r]
        s = K.sira[a:b]
        if K.n[r] < 3 or np.sum(s == 1) != 1 or np.sum(s == 2) != 1 or np.sum(s == 3) != 1:
            continue
        v = lp[a:b]
        i, j, k = int(np.flatnonzero(s == 1)[0]), int(np.flatnonzero(s == 2)[0]), int(np.flatnonzero(s == 3)[0])
        m2 = np.ones(len(v), bool); m2[i] = False
        g2 = gam * v
        x2 = g2[j] - (g2[m2].max() + math.log(np.exp(g2[m2] - g2[m2].max()).sum()))
        m3 = m2.copy(); m3[j] = False
        g3 = dlt * v
        x3 = g3[k] - (g3[m3].max() + math.log(np.exp(g3[m3] - g3[m3].max()).sum()))
        l2.append(-(v[i] + x2)); l3.append(-(v[i] + x2 + x3))
    return np.asarray(l2), np.asarray(l3)


def sirali_olasiliklar(p, gam=1.0, dlt=1.0, ilk3=True):
    """Tek koşu: kazanma p'den ikili (sıralı) matris ve ilk-2/ilk-3 olasılıkları (Harville + Henery)."""
    p = np.asarray(p, float); n = len(p)
    pg, pd = p ** gam, p ** dlt
    E = np.zeros((n, n))
    for i in range(n):
        den = pg.sum() - pg[i]
        if den > 0:
            E[i] = p[i] * pg / den
        E[i, i] = 0.0
    ilk2 = E.sum(0) + p
    sonuc = {"ikili": E, "ilk2": ilk2}
    if ilk3 and n >= 3:
        ilk3v = ilk2.copy()
        for i in range(n):
            for j in range(n):
                if i == j or E[i, j] == 0:
                    continue
                den = pd.sum() - pd[i] - pd[j]
                if den <= 0:
                    continue
                k = pd / den
                k[i] = k[j] = 0.0
                ilk3v += E[i, j] * k
        sonuc["ilk3"] = np.minimum(ilk3v, 1.0)
    return sonuc


# ---------------------------------------------------------------- ölçüm
def metrikler(p, K, gam=1.0):
    y = K.y
    brier = np.add.reduceat((p - y) ** 2, K.bas)
    top1 = ikili = iki_ilk2 = 0
    for r in range(K.R):
        a, b = K.bas[r], K.bas[r] + K.n[r]
        pr, s = p[a:b], K.sira[a:b]
        o = np.argsort(-pr)
        top1 += int(s[o[0]] == 1)
        if len(pr) >= 2:
            E = sirali_olasiliklar(pr, gam, ilk3=False)["ikili"]
            i, j = np.unravel_index(np.argmax(E), E.shape)
            ikili += int(s[i] == 1 and s[j] == 2)
            iki_ilk2 += int(set(s[o[:2]]) == {1, 2})
    out = {"kosu": int(K.R), "log_loss": round(logloss(p, K), 4), "brier": round(float(brier.mean()), 4),
           "ilk_secim_isabet": round(top1 / K.R, 4), "ikili_sirali_isabet": round(ikili / K.R, 4),
           "ilk_iki_ikisi_de_ilk2": round(iki_ilk2 / K.R, 4)}
    for esik in (0.30, 0.50):
        m = p >= esik
        out[f"p>={esik:.2f}"] = {"secim": int(m.sum()), "isabet": round(float(y[m].mean()), 4) if m.any() else None,
                                 "ort_p": round(float(p[m].mean()), 4) if m.any() else None}
    return out


def kovalar(p, y):
    t = []
    for lo, hi in zip(KOVALAR[:-1], KOVALAR[1:]):
        m = (p >= lo) & (p < hi)
        if m.any():
            t.append({"aralik": f"{lo:.2f}-{min(hi, 1):.2f}", "at": int(m.sum()),
                      "ort_tahmin": round(float(p[m].mean()), 4), "gercek": round(float(y[m].mean()), 4)})
    return t




# ---------------------------------------------------------------- gradyan artırmalı ağaçlar (isteğe bağlı)
# LightGBM, koşu içi softmax (koşullu logit) amacıyla özel amaç fonksiyonu üzerinden eğitilir. Kurulu değilse
# sistem yalnız doğrusal koşullu logite düşer (model.json'daki "yedek" kalibrasyonu ile).
try:
    import lightgbm as lgb
except Exception:  # pragma: no cover
    lgb = None

GBM_AYAR = {"n_agac": 600, "ogrenme": 0.03, "yaprak": 7, "min_yaprak": 500, "oznitelik_payi": 0.8, "l2": 10.0}
ARTIK_AYAR = {"n_agac": 300, "ogrenme": 0.02, "yaprak": 7, "min_yaprak": 800, "l2": 30.0}
HENERY_MODEL = True   # yalnız-model olasılıkları için ayrı γ, δ (sabah kilitleri yalnız modeldir)
UST_KAL = True        # üst uç kalibrasyonu: p > UST_ESIK bölgesinde ayrı eğim (deney 7, kapıdan geçti)
UST_ESIK = 0.25
KAL_GUN = 90          # kalibrasyon (birleştirme katsayıları, α, β) penceresi: tahmin ayının hemen öncesindeki 90 gün
YARI_OMUR = 180.0     # zaman ağırlıklı eğitim: koşu ağırlığı 0.5^(yaş/180 gün)
# v4 ayarları (deney4.py kapısıyla seçilir; tarif() bunları kaydeder)
KAL_AYAR = {"alan": False, "beta": True, "izo": False}   # kalibrasyon adımları (ust = UST_KAL); v4: beta geçti, alan/izotonik elendi
PATLAT = (1.0, 0.5)   # v4: derinlik 2 geçti (deney 8b). patlatılmış (sıralı) logit: kademe ağırlıkları; (1.0,) = yalnız kazanan (klasik)
PATLAT_GBM = False    # aynı sıralı amaç GBM'de de kullanılsın mı
GBM_TOHUM = (1,)      # GBM torbalama tohumları (ham puanları ortalanır)
GBM_INIT_DOGRUSAL = False   # v7 adayı: GBM doğrusal koşullu logit puanından başlar (init_score), ağaçlar yalnız kalıntıyı öğrenir
# v7 (deney7 e4, harman kapısı): harman (model + oran) için AYRI bir kalıntı GBM — doğrusal puandan başlar; kendi yığma,
# kalibrasyon ve α/β katsayıları. Yalnız-model (sabah) olasılığı DEĞİŞMEZ; yalnız p_harman bu yoldan hesaplanır.
HARMAN_KALINTI = True
KAT_BAS = "2025-11-01"   # çok katlı sınama: A katı KAT_BAS → son %30'un başı, B katı = son %30 (en güncel)


def _gun(t):
    from datetime import date
    return date.fromisoformat(t).toordinal()


def gbm_egit(X, K, agirlik=None, ayar=None, init=None, tohum=1):
    """Koşu içi softmax (grup-softmax) amacı: gradyan p − y, hessian p(1 − p) (koşu ağırlıklı).
    init: satır başına başlangıç puanı (ör. log q → kalıntı modeli)."""
    a = dict(GBM_AYAR, **(ayar or {}))
    b0 = np.zeros(len(K.y)) if init is None else np.asarray(init, float)
    sw = (np.ones(K.R) if agirlik is None else np.asarray(agirlik, float))[K.seg]

    def amac(preds, ds):
        p = softmax_kosu(preds + b0, K)
        return sw * (p - K.y), sw * np.maximum(p * (1 - p), 1e-6)
    par = {"objective": amac, "learning_rate": a["ogrenme"], "num_leaves": a["yaprak"],
           "min_data_in_leaf": a["min_yaprak"], "feature_fraction": a["oznitelik_payi"], "bagging_fraction": 0.8,
           "bagging_freq": 1, "lambda_l2": a["l2"], "verbose": -1, "seed": tohum, "deterministic": True,
           "num_threads": min(4, os.cpu_count() or 1)}
    return lgb.train(par, lgb.Dataset(X, free_raw_data=False), num_boost_round=a["n_agac"])


AYIRAC = "\n#==== BULUTOXX GBM TOHUM ====\n"
AYIRAC_H = "\n#==== BULUTOXX GBM HARMAN ====\n"   # gbm_uretim.txt: <yalnız-model ağaçları> AYIRAC_H <harman kalıntı ağaçları>


class GbmTorba:
    """Birden çok tohumla eğitilmiş GBM'lerin ham puan ortalaması (varyans azaltma)."""

    def __init__(self, boosters):
        self.b = list(boosters)

    def predict(self, X, raw_score=True):
        return np.mean([b.predict(X, raw_score=True) for b in self.b], axis=0)

    def model_to_string(self):
        return AYIRAC.join(b.model_to_string() for b in self.b)


def gbm_yukle(metin):
    if lgb is None or not metin:
        return None
    return GbmTorba([lgb.Booster(model_str=m) for m in metin.split(AYIRAC) if m.strip()])


# ---------------------------------------------------------------- patlatılmış (sıralı) logit — Bolton–Chapman
def patlat(K, agirliklar=PATLAT, rw=None):
    """Koşuyu kademelere açar: 1. kademe tüm atlar (hedef kazanan), 2. kademe kazanan hariç (hedef ikinci), ...
    Alt sıraların gürültüsü için kademe ağırlıkları azalır. Döner: (genişletilmiş Kume, koşu ağırlıkları)."""
    rw = np.ones(K.R) if rw is None else np.asarray(rw, float)
    if len(agirliklar) <= 1:
        return K, rw
    satir, yy, kno, w = [], [], [], []
    yeni = 0
    for r in range(K.R):
        a, b = K.bas[r], K.bas[r] + K.n[r]
        s = K.sira[a:b]
        kalan = np.arange(a, b)
        for d, ag in enumerate(agirliklar):
            hedef = d + 1
            if len(kalan) < 2 or np.sum(K.sira[kalan] == hedef) != 1:
                break
            satir.append(kalan); yy.append((K.sira[kalan] == hedef).astype(float))
            kno.append(np.full(len(kalan), yeni)); w.append(rw[r] * ag); yeni += 1
            kalan = kalan[K.sira[kalan] != hedef]
    ix = np.concatenate(satir)
    Ke = Kume(K.X[ix], np.concatenate(yy), K.sira[ix], K.q[ix], np.concatenate(kno))
    return Ke, np.asarray(w)


# ---------------------------------------------------------------- kalibrasyon adımları
def izotonik(x, y, w=None):
    """Ağırlıklı PAV (artan). Döner: (düğüm x'leri, düğüm değerleri) — aradeğerleme ile uygulanır."""
    o = np.argsort(x)
    x, y = x[o], y[o]
    w = np.ones(len(x)) if w is None else np.asarray(w, float)[o]
    v, ww, xs, n = [], [], [], []
    for xi, yi, wi in zip(x, y, w):
        v.append(yi); ww.append(wi); xs.append(xi); n.append(1)
        while len(v) > 1 and v[-2] >= v[-1]:
            t = ww[-2] + ww[-1]
            v[-2] = (v[-2] * ww[-2] + v[-1] * ww[-1]) / t; ww[-2] = t
            xs[-2] = (xs[-2] * n[-2] + xs[-1] * n[-1]) / (n[-2] + n[-1]); n[-2] += n[-1]
            v.pop(); ww.pop(); xs.pop(); n.pop()
    return np.asarray(xs), np.asarray(v)


def _alan_dN(K):
    return np.log(K.n[K.seg]) - math.log(10.0)


def kal_uygula(adimlar, s0, K):
    """Kalibrasyon adımlarını sırayla uygular; olasılık döner."""
    s = s0
    for ad_, *par in adimlar:
        if ad_ == "alan":
            s = par[0] * s + par[1] * s * _alan_dN(K)
        elif ad_ == "beta":
            p = softmax_kosu(s, K)
            s = par[0] * s + par[1] * np.log(np.clip(1 - p, 1e-6, 1))
        elif ad_ == "ust":
            lp = np.log(softmax_kosu(s, K))
            s = par[0] * s + par[1] * np.maximum(lp - math.log(par[2] if len(par) > 2 else UST_ESIK), 0.0)
        elif ad_ == "izo":
            p = softmax_kosu(s, K)
            xs, ys, karis = np.asarray(par[0]), np.asarray(par[1]), par[2]
            pi = np.interp(p, xs, ys)
            p2 = np.clip((1 - karis) * p + karis * pi, 1e-6, 1)
            s = np.log(p2 / np.add.reduceat(p2, K.bas)[K.seg])
    return softmax_kosu(s, K)


def kal_ogren(sb, K, ayar=None, ust=None):
    """Kalibrasyon penceresinde (K) adımları sırayla öğrenir. sb: birleşik (yığılmış) puan."""
    ayar = dict(KAL_AYAR, **(ayar or {}))
    ust = UST_KAL if ust is None else ust
    adimlar = []
    s = sb
    if ayar.get("alan"):
        a, b = (float(v) for v in clogit(np.c_[s, s * _alan_dN(K)], K, 1e-6))
        adimlar.append(["alan", a, b]); s = kal_uygula([adimlar[-1]], s, K); s = np.log(s)
    if ayar.get("beta"):
        p = softmax_kosu(s, K)
        a, b = (float(v) for v in clogit(np.c_[s, np.log(np.clip(1 - p, 1e-6, 1))], K, 1e-6))
        adimlar.append(["beta", a, b]); s = np.log(kal_uygula([adimlar[-1]], s, K))
    if ust:
        h = np.maximum(np.log(softmax_kosu(s, K)) - math.log(UST_ESIK), 0.0)
        a, b = (float(v) for v in clogit(np.c_[s, h], K, 1e-6))
        adimlar.append(["ust", a, b, UST_ESIK]); s = np.log(kal_uygula([adimlar[-1]], s, K))
    if ayar.get("izo"):
        p = softmax_kosu(s, K)
        xs, ys = izotonik(p, K.y)
        # düğüm sayısını sınırla (json boyutu): 40 nicelik noktasında örnekle
        q = np.unique(np.quantile(p, np.linspace(0, 1, 41)))
        q = np.r_[q, np.linspace(q[-1], 1.0, 5)[1:]] if q[-1] < 1 else q
        yq = np.interp(q, xs, ys)
        adimlar.append(["izo", [round(float(v), 5) for v in q], [round(float(v), 5) for v in yq], float(ayar.get("izo_karis", 0.5))])
    return adimlar


# ---------------------------------------------------------------- tam boru hattı
class Model:
    """Standartlaştırma + doğrusal ağırlıklar (+ isteğe bağlı GBM) + kalibrasyon/harman parametreleri.
    Birleşik puan s = cl·(doğrusal) + cg·(GBM); yalnız model: p ∝ exp(s / T); harman: p ∝ exp(α log p_s + β log q).
    Eski (v1) model.json'lar da okunur: cl=1, cg=0, T=sıcaklık."""

    def __init__(self, adlar, mu, sd, w, T, alfa, beta, gam, dlt, lam, cl=1.0, cg=0.0, gbm=None, yedek=None,
                 ku=1.0, cu=0.0, kal=None):
        self.adlar, self.mu, self.w = list(adlar), np.asarray(mu), np.asarray(w)
        # eğitimde sabit kalan sütun (ölçek≈0; json'da 0'a yuvarlanır): tahminde değer değişirse 0'a bölme/NaN olmasın.
        # Ağırlığı eğitimde zaten ~0'dır; ölçeği 1 almak puanı değiştirmez.
        self.sd = np.where(np.asarray(sd, dtype=float) < 1e-6, 1.0, np.asarray(sd, dtype=float))
        self.T, self.alfa, self.beta, self.gam, self.dlt, self.lam = T, alfa, beta, gam, dlt, lam
        self.cl, self.cg, self.gbm, self.yedek = cl, cg, gbm, yedek
        # kalibrasyon adımları (v4): [["alan", a, b], ["beta", a, b], ["ust", k, c, eşik], ["izo", xs, ys, karışım]]
        # eski model.json: üst uç kalibrasyonu s = ku·s0 + cu·max(log p0 − log eşik, 0)
        self.kal = kal if kal is not None else ([["ust", ku, cu, UST_ESIK]] if cu else [])
        self.bq, self.gbm_artik, self.ab_artik = 1.0, None, None
        self.h, self.gbm_h = None, None   # v7 harman kalıntı GBM: {"cl", "cg", "kal", "alfa", "beta"} + ağaçlar
        self.gam_m, self.dlt_m = gam, dlt

    def _yedekte(self):
        return bool(self.cg) and self.gbm is None and bool(self.yedek)

    def puan(self, X):
        return ((X - self.mu) / self.sd) @ self.w

    def birlesik(self, X):
        if self._yedekte():
            return self.yedek["cl"] * self.puan(X)
        s = self.cl * self.puan(X)
        if self.cg and self.gbm is not None:
            s = s + self.cg * self.gbm.predict(X, raw_score=True)
        return s

    def _kalp(self, X, K):
        """Kalibre yalnız-model olasılığı (sıcaklık T dahil)."""
        s0 = self.birlesik(X) / self.T
        if self._yedekte() or not self.kal:
            return softmax_kosu(s0, K)
        return kal_uygula(self.kal, s0, K)

    def p_model(self, X, K):
        return self._kalp(X, K)

    def p_harman(self, X, K, q):
        if self.h and self.gbm_h is not None and not self._yedekte():
            h = self.h
            s0 = h["cl"] * self.puan(X) + h["cg"] * self.gbm_h.predict(X, raw_score=True)
            pk = kal_uygula(h["kal"], s0, K) if h["kal"] else softmax_kosu(s0, K)
            s = h["alfa"] * np.log(np.clip(pk, 1e-12, 1)) + h["beta"] * np.log(np.clip(q, 1e-9, 1))
            return softmax_kosu(s, K)
        a, b = (self.yedek["alfa"], self.yedek["beta"]) if self._yedekte() else (self.alfa, self.beta)
        s = a * np.log(np.clip(self._kalp(X, K), 1e-12, 1)) + b * np.log(np.clip(q, 1e-9, 1))
        return softmax_kosu(s, K)

    def p_keskin(self, K, q):
        """Piyasa keskinleştirme kontrolü: p ∝ q^β (β kalibrasyon penceresinde)."""
        return softmax_kosu(self.bq * np.log(np.clip(q, 1e-9, 1)), K)

    def p_harman_artik(self, X, K, q):
        """Harman + kalıntı GBM (init_score = log q ile eğitilmiş ağaçlar)."""
        if self.gbm_artik is None or not self.ab_artik:
            return self.p_harman(X, K, q)
        a, b, c = self.ab_artik
        s = (a * np.log(np.clip(self._kalp(X, K), 1e-12, 1)) + b * np.log(np.clip(q, 1e-9, 1))
             + c * self.gbm_artik.predict(X, raw_score=True))
        return softmax_kosu(s, K)

    def katki(self, X):
        """Gerekçe için doğrusal katkılar (koşu ortalamasına göre, kalibre ölçekte)."""
        Z = (X - self.mu) / self.sd
        c = (self.yedek["cl"] if self._yedekte() else self.cl) / self.T
        return (Z - Z.mean(0)) * self.w * c

    def json(self):
        return {"ozellikler": self.adlar, "ortalama": [round(float(v), 6) for v in self.mu],
                "olcek": [round(float(v), 6) for v in self.sd], "agirlik": [round(float(v), 6) for v in self.w],
                "sicaklik": round(self.T, 4), "alfa": round(self.alfa, 4), "beta": round(self.beta, 4),
                "henery_gamma": self.gam, "henery_delta": self.dlt, "lambda": self.lam,
                "henery_gamma_model": self.gam_m, "henery_delta_model": self.dlt_m,
                "piyasa_keskin_beta": round(float(self.bq), 4),
                "c_dogrusal": round(float(self.cl), 5), "c_gbm": round(float(self.cg), 5),
                "gbm": self.gbm is not None and bool(self.cg),
                "kalibrasyon": [[a[0]] + [(round(float(v), 5) if not isinstance(v, list) else v) for v in a[1:]] for a in self.kal],
                "gbm_tohum": (len(self.gbm.b) if isinstance(self.gbm, GbmTorba) else (1 if self.gbm is not None else 0)),
                **({"harman_kalinti": {"cl": round(float(self.h["cl"]), 5), "cg": round(float(self.h["cg"]), 5),
                                       "alfa": round(float(self.h["alfa"]), 4), "beta": round(float(self.h["beta"]), 4),
                                       "kal": [[a[0]] + [(round(float(v), 5) if not isinstance(v, list) else v) for v in a[1:]]
                                               for a in self.h["kal"]]}}
                   if self.h and self.gbm_h is not None else {}),
                "yedek": ({k: round(float(v), 5) for k, v in self.yedek.items()} if self.yedek else None)}

    def gbm_metin(self):
        """gbm_uretim.txt içeriği: yalnız-model ağaçları (+ varsa AYIRAC_H + harman kalıntı ağaçları)."""
        t = self.gbm.model_to_string() if self.gbm is not None else ""
        if self.h and self.gbm_h is not None:
            t += AYIRAC_H + self.gbm_h.model_to_string()
        return t

    @staticmethod
    def yukle(j, gbm_metin=None):
        gbm_metin_h = None
        if gbm_metin and AYIRAC_H in gbm_metin:
            gbm_metin, gbm_metin_h = gbm_metin.split(AYIRAC_H, 1)
        m = Model(j["ozellikler"], j["ortalama"], j["olcek"], j["agirlik"], j["sicaklik"], j["alfa"],
                     j["beta"], j["henery_gamma"], j["henery_delta"], j.get("lambda"),
                     cl=j.get("c_dogrusal", 1.0), cg=j.get("c_gbm", 0.0), ku=j.get("k_ust", 1.0), cu=j.get("c_ust", 0.0),
                     kal=j.get("kalibrasyon"),
                     gbm=(gbm_yukle(gbm_metin) if j.get("gbm") else None), yedek=j.get("yedek"))
        m.gam_m = j.get("henery_gamma_model", m.gam); m.dlt_m = j.get("henery_delta_model", m.dlt)
        m.bq = j.get("piyasa_keskin_beta", 1.0)
        hk = j.get("harman_kalinti")
        if hk and j.get("gbm") and gbm_metin_h:   # ağaçlar yoksa (sürüm uyuşmazlığı / LightGBM yok) klasik harmana düşer
            m.gbm_h = gbm_yukle(gbm_metin_h)
            if m.gbm_h is not None:
                m.h = {"cl": hk["cl"], "cg": hk["cg"], "alfa": hk["alfa"], "beta": hk["beta"], "kal": hk.get("kal") or []}
        return m


def _ozel(K, m):
    """Satır maskesi yerine koşu maskesi alır."""
    return K.alt(m[K.seg])


def egit_ham(K_fit, K_har, sutun, lam=None, agirlik=None, gbm=True, gbm_ayar=None, patlat_ag=None, tohumlar=None,
             patlat_gbm=None, harman_kalinti=None):
    """Eğitim katmanı (pahalı kısım): standartlaştırma, doğrusal koşullu logit (isteğe bağlı patlatılmış/sıralı),
    LightGBM (isteğe bağlı birden çok tohum). Kalibrasyon penceresi yalnız λ seçimi için kullanılır."""
    patlat_ag = PATLAT if patlat_ag is None else patlat_ag
    tohumlar = GBM_TOHUM if tohumlar is None else tohumlar
    patlat_gbm = PATLAT_GBM if patlat_gbm is None else patlat_gbm
    harman_kalinti = HARMAN_KALINTI if harman_kalinti is None else harman_kalinti
    Xf, Xh = K_fit.X[:, sutun], K_har.X[:, sutun]
    mu, sd = Xf.mean(0), Xf.std(0) + 1e-9
    Zf, Zh = (Xf - mu) / sd, (Xh - mu) / sd
    Kz = Kume(Zf, K_fit.y, K_fit.sira, K_fit.q, K_fit.kosu_no)
    Ke, ag_e = patlat(Kz, patlat_ag, agirlik)
    if lam is None:
        en = (1e9, None)
        for l in LAMBDALAR:
            w = clogit(Ke.X, Ke, l, agirlik=ag_e)
            ll = logloss(softmax_kosu(Zh @ w, K_har), K_har)
            en = min(en, (ll, l))
        lam = en[1]
    w = clogit(Ke.X, Ke, lam, agirlik=ag_e)
    booster = None
    if gbm and lgb is not None:
        if patlat_gbm and len(patlat_ag) > 1:
            Kg, ag_g = patlat(K_fit.alt(np.ones(len(K_fit.y), bool)), patlat_ag, agirlik)
            Kg = Kume(Kg.X[:, sutun], Kg.y, Kg.sira, Kg.q, Kg.kosu_no)
        else:
            Kg, ag_g = Kume(Xf, K_fit.y, K_fit.sira, K_fit.q, K_fit.kosu_no), agirlik
        ini = None
        if GBM_INIT_DOGRUSAL and not (patlat_gbm and len(patlat_ag) > 1):
            ini = Zf @ w   # doğrusal puan (eğitim kümesinde); tahminde ağaç çıktısı ayrı, yığma katsayıları birleştirir
        bs = [gbm_egit(Kg.X, Kg, ag_g, gbm_ayar, init=ini, tohum=t) for t in tohumlar]
        booster = GbmTorba(bs)
    booster_h = None
    if gbm and lgb is not None and harman_kalinti and not GBM_INIT_DOGRUSAL:
        Kh0 = Kume(Xf, K_fit.y, K_fit.sira, K_fit.q, K_fit.kosu_no)
        booster_h = GbmTorba([gbm_egit(Xf, Kh0, agirlik, gbm_ayar, init=Zf @ w, tohum=tohumlar[0])])
    return {"mu": mu, "sd": sd, "w": w, "lam": lam, "booster": booster, "booster_h": booster_h}


def egit_kal(ham, K_har, adlar, sutun, s=None, g=None, henery=True, kal_ayar=None, ust=None):
    """Kalibrasyon katmanı (ucuz): doğrusal+GBM yığma katsayıları, kalibrasyon adımları, harman α/β, Henery.
    s, g: K_har üzerindeki ham doğrusal ve GBM puanları (verilmezse hesaplanır)."""
    Xh = K_har.X[:, sutun]
    mu, sd, w, lam, booster = ham["mu"], ham["sd"], ham["w"], ham["lam"], ham["booster"]
    if s is None:
        s = ((Xh - mu) / sd) @ w
    lq = np.log(K_har.q)
    # yalnız doğrusal: sıcaklık (c = 1/T) ve harman — GBM yoksa ya da yedek olarak
    c_lin = float(clogit(s[:, None], K_har, 1e-6)[0])
    ab_y = clogit(np.c_[np.log(softmax_kosu(c_lin * s, K_har)), lq], K_har, 1e-6)
    yedek = {"cl": c_lin, "alfa": float(ab_y[0]), "beta": float(ab_y[1])}
    cl, cg = c_lin, 0.0
    if booster is not None:
        if g is None:
            g = booster.predict(Xh, raw_score=True)
        cl, cg = (float(v) for v in clogit(np.c_[s, g], K_har, 1e-6))
        sb = cl * s + cg * g
    else:
        sb = c_lin * s
    kal = kal_ogren(sb, K_har, kal_ayar, ust)
    pk = kal_uygula(kal, sb, K_har)
    ab = clogit(np.c_[np.log(np.clip(pk, 1e-12, 1)), lq], K_har, 1e-6)
    m = Model([adlar[i] for i in sutun], mu, sd, w, 1.0, float(ab[0]), float(ab[1]), 1.0, 1.0, lam,
              cl=cl, cg=cg, gbm=booster, yedek=(yedek if booster is not None else None), kal=kal)
    m.bq = float(clogit(lq[:, None], K_har, 1e-6)[0])
    harman_kal_ogren(m, ham.get("booster_h"), K_har, s, Xh, kal_ayar, ust)
    if henery:
        ph = m.p_harman(Xh, K_har, K_har.q)
        m.gam = henery_ussu(ph, K_har, 2)
        m.dlt = henery_ussu(ph, K_har, 3)
        if HENERY_MODEL:
            pmh = m.p_model(Xh, K_har)
            m.gam_m = henery_ussu(pmh, K_har, 2)
            m.dlt_m = henery_ussu(pmh, K_har, 3)
    return m


def harman_kal_ogren(m, booster_h, K_har, s, Xh, kal_ayar=None, ust=None):
    """v7: harman kalıntı GBM'inin yığma (doğrusal + kalıntı ağaçlar), kalibrasyon ve α/β katsayıları — kalibrasyon
    penceresinde (yalnız-model katmanıyla aynı pencere ve adımlar)."""
    if booster_h is None:
        return
    gh = booster_h.predict(Xh, raw_score=True)
    cl, cg = (float(v) for v in clogit(np.c_[s, gh], K_har, 1e-6))
    sb = cl * s + cg * gh
    kal = kal_ogren(sb, K_har, kal_ayar, ust)
    pk = kal_uygula(kal, sb, K_har)
    ab = clogit(np.c_[np.log(np.clip(pk, 1e-12, 1)), np.log(K_har.q)], K_har, 1e-6)
    m.gbm_h = booster_h
    m.h = {"cl": cl, "cg": cg, "kal": kal, "alfa": float(ab[0]), "beta": float(ab[1])}


def egit(K_fit, K_har, adlar, lam=None, sutun=None, henery=True, agirlik=None, gbm=True, artik=False):
    """K_fit: model eğitimi; K_har: kalibrasyon/harman dilimi (tam oranlı koşular). sutun: kullanılacak özellikler.
    agirlik: K_fit koşuları için ağırlık (zaman ağırlıklı eğitim). gbm: LightGBM katmanı (kuruluysa)."""
    sutun = np.arange(K_fit.X.shape[1]) if sutun is None else np.asarray(sutun)
    ham = egit_ham(K_fit, K_har, sutun, lam, agirlik, gbm)
    m = egit_kal(ham, K_har, adlar, sutun, henery=False)
    Xh = K_har.X[:, sutun]
    lq = np.log(K_har.q)
    sb = np.log(np.clip(m.p_model(Xh, K_har), 1e-12, 1))
    # piyasa keskinleştirme kontrolü: q^β tek başına (aynı kalibrasyon penceresinde)
    m.bq = float(clogit(lq[:, None], K_har, 1e-6)[0])
    if artik and lgb is not None:
        # Kalıntı GBM: init_score = log q (piyasa) — ağaçlar yalnız piyasanın bilmediğini öğrenir (koşu öncesi harman için)
        tam = np.isfinite(K_fit.q)
        tam_k = np.add.reduceat(tam.astype(int), K_fit.bas) == K_fit.n
        Kq = K_fit.alt(tam_k[K_fit.seg])
        agq = None if agirlik is None else np.asarray(agirlik, float)[tam_k]
        m.gbm_artik = gbm_egit(Kq.X[:, sutun], Kq, agq, ARTIK_AYAR, init=np.log(np.clip(Kq.q, 1e-9, 1)))
        fh = m.gbm_artik.predict(Xh, raw_score=True)
        m.ab_artik = [float(v) for v in clogit(np.c_[np.log(softmax_kosu(sb, K_har)), lq, fh], K_har, 1e-6)]
    if henery:
        ph = m.p_harman(Xh, K_har, K_har.q)
        m.gam = henery_ussu(ph, K_har, 2)
        m.dlt = henery_ussu(ph, K_har, 3)
        if HENERY_MODEL:
            pmh = m.p_model(Xh, K_har)
            m.gam_m = henery_ussu(pmh, K_har, 2)
            m.dlt_m = henery_ussu(pmh, K_har, 3)
    return m, sutun


def bolumle(T, kosular):
    """Zaman sıralı bölüm: koşu indeksleri üzerinden ısınma / eğitim / harman / sınama maskeleri."""
    tarih = np.array([k["tarih"] for k in kosular])
    R = len(kosular)
    tam_oran = np.array([not any(a["oran"] is None for a in k["atlar"]) for k in kosular])
    ilk = int(np.searchsorted(tarih, ISINMA_SONU))
    kes_s = int(R * (1 - SINAMA_PAYI)); kes_s = int(np.searchsorted(tarih, tarih[kes_s]))
    kes_h = int(R * (1 - SINAMA_PAYI - HARMAN_PAYI)); kes_h = int(np.searchsorted(tarih, tarih[kes_h]))
    idx = np.arange(R)
    kat_bas = min(int(np.searchsorted(tarih, KAT_BAS)), kes_s)
    return {"egitim": (idx >= ilk) & (idx < kes_h), "harman": (idx >= kes_h) & (idx < kes_s) & tam_oran,
            "sinama": (idx >= kes_s) & tam_oran, "sinama_tum": idx >= kes_s,
            "sinama_katli": (idx >= kat_bas) & tam_oran, "kat": np.where(idx >= kes_s, "B", "A"),
            "tarih": {"isinma_bitis": ISINMA_SONU, "egitim": [tarih[ilk], tarih[kes_h - 1]],
                      "harman": [tarih[kes_h], tarih[kes_s - 1]], "sinama": [tarih[kes_s], tarih[-1]],
                      "katlar": {"A": [tarih[kat_bas], tarih[kes_s - 1]], "B": [tarih[kes_s], tarih[-1]]}}}


def kume_kur(T):
    return Kume(T["X"], T["y"], T["sira"], T["q"], T["kid"])


def _pencereler(kosular):
    tarih = np.array([k["tarih"] for k in kosular])
    gunler = np.array([_gun(t) for t in tarih])
    tam_oran = np.array([not any(a["oran"] is None for a in k["atlar"]) for k in kosular])
    return tarih, gunler, tam_oran, np.arange(len(kosular)), int(np.searchsorted(tarih, ISINMA_SONU))


def sina(T, kosular, protokol="aylik", lam=None, yari_omur="vars", kal_gun=None, henery=False, gbm=False, sutun=None,
         artik=False, katli=False):
    """Sınama dilimi (son %30, tam oranlı) için tahminleri üretir ve metrikleri döner.
    protokol='sabit': tek model (eğitim → harman → sınama), v1 yöntemi.
    protokol='aylik': sınamanın her ayı için yalnız o aydan önceki verilerle yeniden eğitim (genişleyen pencere);
                      kalibrasyon ayın hemen öncesindeki `kal_gun` günde. Yayındaki modelin gerçekte nasıl
                      çalıştığını (her gece tüm geçmişle eğitim) dürüstçe taklit eder.
    katli=True: sınama KAT_BAS'tan başlar (A katı: KAT_BAS → son %30'un başı, B katı: son %30); aylık yeniden eğitim
                tüm katlarda aynı. Ana metrikler B katında (önceki sürümlerle kıyaslanabilir), r["katlar"] her katı ayrı verir."""
    yari_omur = YARI_OMUR if yari_omur == "vars" else yari_omur
    kal_gun = kal_gun or KAL_GUN
    K = kume_kur(T)
    B = bolumle(T, kosular)
    Ks = _ozel(K, B["sinama_katli"] if katli else B["sinama"])
    Xs = Ks.X if sutun is None else Ks.X[:, sutun]
    tarih, gunler, tam_oran, idx, ilk = _pencereler(kosular)
    kat_s = B["kat"][Ks.kosu_no]   # satır başına kat (A/B)
    pm = np.zeros(len(Ks.y)); ph = np.zeros(len(Ks.y)); pk = np.zeros(len(Ks.y)); pa = np.zeros(len(Ks.y))
    s2 = {"model": [], "model_h1": [], "harman": [], "harman_h1": []}
    modeller = []
    if protokol == "sabit":
        Kf, Kh = _ozel(K, B["egitim"]), _ozel(K, B["harman"])
        ag = None
        if yari_omur:
            gk = gunler[Kf.kosu_no[Kf.bas]]
            ag = 0.5 ** ((gk.max() - gk) / yari_omur)
        m, _ = egit(Kf, Kh, T["adlar"], lam=lam, henery=henery, agirlik=ag, gbm=gbm, sutun=sutun, artik=artik)
        pm, ph = m.p_model(Xs, Ks), m.p_harman(Xs, Ks, Ks.q)
        pk, pa = m.p_keskin(Ks, Ks.q), m.p_harman_artik(Xs, Ks, Ks.q)
        modeller.append(m)
    else:
        aylar = np.array([tarih[i][:7] for i in Ks.kosu_no[Ks.bas]])
        for ay in sorted(set(aylar)):
            g0 = _gun(ay + "-01")
            kal_bas = g0 - kal_gun
            Kf = _ozel(K, (idx >= ilk) & (gunler < kal_bas))
            Kh = _ozel(K, (gunler >= kal_bas) & (gunler < g0) & tam_oran)
            ag = 0.5 ** ((kal_bas - gunler[Kf.kosu_no[Kf.bas]]) / yari_omur) if yari_omur else None
            m, _ = egit(Kf, Kh, T["adlar"], lam=lam, henery=henery, agirlik=ag, gbm=gbm, sutun=sutun, artik=artik)
            satir = (aylar == ay)[Ks.seg]
            Ka = Ks.alt(satir)
            Xa = Xs[satir]
            pm[satir] = m.p_model(Xa, Ka)
            ph[satir] = m.p_harman(Xa, Ka, Ka.q)
            pk[satir] = m.p_keskin(Ka, Ka.q)
            pa[satir] = m.p_harman_artik(Xa, Ka, Ka.q)
            if henery:
                sb_ = satir & (kat_s == "B")
                Kb = Ks.alt(sb_)
                for ad_, pp, g, d in (("model", pm[sb_], m.gam_m, m.dlt_m), ("harman", ph[sb_], m.gam, m.dlt)):
                    if Kb.R == 0:
                        continue
                    l2, l3 = sira_ll(pp, Kb, g, d)
                    h2, h3 = sira_ll(pp, Kb, 1.0, 1.0)
                    s2[ad_].append((l2, l3)); s2[ad_ + "_h1"].append((h2, h3))
            modeller.append(m)
    katlar, tum = None, None
    if katli:
        katlar = {}
        for kt in ("A", "B"):
            mk = kat_s == kt
            Kk = Ks.alt(mk)
            if Kk.R == 0:
                continue
            katlar[kt] = {"tarih": B["tarih"]["katlar"][kt], "kosu": int(Kk.R),
                          "metrik": {"model": metrikler(pm[mk], Kk), "harman": metrikler(ph[mk], Kk),
                                     "piyasa": metrikler(Kk.q, Kk)},
                          "kovalar": {"model": kovalar(pm[mk], Kk.y), "harman": kovalar(ph[mk], Kk.y)}}
        tum = (Ks, pm, ph)
        mk = kat_s == "B"
        Ks, pm, ph, pk, pa = Ks.alt(mk), pm[mk], ph[mk], pk[mk], pa[mk]
    pq = Ks.q
    out = {"metrik": {"model": metrikler(pm, Ks), "harman": metrikler(ph, Ks), "piyasa": metrikler(pq, Ks),
                      "piyasa_keskin": metrikler(pk, Ks)},
           "kovalar": {"model": kovalar(pm, Ks.y), "harman": kovalar(ph, Ks.y), "piyasa": kovalar(pq, Ks.y)},
           "p": (pm, ph), "p_ek": {"keskin": pk, "harman_artik": pa}, "Ks": Ks, "modeller": modeller, "B": B}
    if katli:
        out["katlar"] = katlar
        out["Ks_tum"], out["p_tum"] = tum[0], (tum[1], tum[2])
    if artik:
        out["metrik"]["harman_artik"] = metrikler(pa, Ks)
    if henery and protokol != "sabit" and s2["model"]:
        sr = {}
        for k, v in s2.items():
            l2 = np.concatenate([a for a, _ in v]); l3 = np.concatenate([b for _, b in v])
            sr[k] = {"ikili_ll": round(float(l2.mean()), 4), "uclu_ll": round(float(l3.mean()), 4), "kosu": int(len(l2))}
        out["sira_ll"] = sr
    w = Ks.y > 0
    for ad_, pp in (("harman", ph), ("model", pm)):
        d = -np.log(np.clip(pp[w], 1e-12, 1)) + np.log(pq[w])
        out[f"{ad_}_eksi_piyasa"] = {"ll_fark": round(float(d.mean()), 4), "std_hata": round(float(d.std() / math.sqrt(len(d))), 4)}
    return out


def iz_cikar(r, kosular):
    """Sınama izi: her koşu için [kimlik, -log p_kazanan (model), ilk seçim tuttu mu (model), aynısı harman için].
    Kapı, tarif değiştiğinde yeni ve eski izleri ORTAK koşular üzerinde kıyaslar (aynı dilim, adil kıyas)."""
    Ks = r.get("Ks_tum", r["Ks"]); pm, ph = r.get("p_tum", r["p"])
    iz = []
    for k in range(Ks.R):
        a, b = Ks.bas[k], Ks.bas[k] + Ks.n[k]
        y = Ks.y[a:b]; ko = kosular[Ks.kosu_no[a]]
        sat = [f'{ko["tarih"]}/{ko["hipodrom"]}/{ko["kosu"]}']
        for p in (pm[a:b], ph[a:b]):
            sat += [round(float(-np.log(max(p[y > 0][0], 1e-12))), 4), int(y[np.argmax(p)] > 0)]
        iz.append(sat)
    return iz


def iz_kiyas(yeni, eski, b_bas=None):
    """Ortak koşularda (ll_model, ilk_model, ll_harman, ilk_harman) ortalamaları: (yeni, eski, n).
    b_bas verilirse ayrıca en güncel katın (tarih ≥ b_bas) ortak koşularındaki ortalamalar ("B")."""
    e = {s[0]: s for s in eski}
    ort = [s for s in yeni if s[0] in e]
    if not ort:
        return None
    f = lambda L, i: round(float(np.mean([s[i] for s in L])), 4)

    def ozet(L):
        eo = [e[s[0]] for s in L]
        return {"kosu": len(L),
                "yeni": {"model_ll": f(L, 1), "model_ilk": f(L, 2), "harman_ll": f(L, 3), "harman_ilk": f(L, 4)},
                "eski": {"model_ll": f(eo, 1), "model_ilk": f(eo, 2), "harman_ll": f(eo, 3), "harman_ilk": f(eo, 4)}}
    out = ozet(ort)
    if b_bas:
        ob = [s for s in ort if s[0][:10] >= b_bas]
        if ob:
            out["B"] = ozet(ob)
    return out


def degerlendir(T, kosular, ablasyon=True, gbm=True):
    """Yayın tarifinin tam değerlendirmesi (aylık walk-forward). (son ay modeli, sonuç sözlüğü, iz) döner."""
    r = sina(T, kosular, "aylik", gbm=gbm, henery=True, katli=True)
    Ks = r["Ks"]; pm, ph = r["p"]; pq = Ks.q
    m = r["modeller"][-1]
    B = r["B"]
    sonuc = {"protokol": f"aylık walk-forward: sınamanın her ayı için yalnız o aydan önceki verilerle yeniden eğitim; "
                         f"kalibrasyon ayın hemen öncesindeki {KAL_GUN} günde; zaman ağırlığı yarı ömrü {YARI_OMUR:g} gün",
             "bolum": B["tarih"], "kosu_sayisi": {"egitim": int(np.sum(B["egitim"])), "harman": int(np.sum(B["harman"])),
                                                   "sinama": int(Ks.R)},
             "gbm": bool(gbm and lgb is not None)}
    sonuc["katlar"] = r.get("katlar")   # v4: iki zaman katı (A: KAT_BAS → B'nin başı, B: son %30; metrik = B katı)
    sonuc["metrik"] = dict(r["metrik"])
    pu = 1.0 / Ks.n[Ks.seg]
    sonuc["metrik"]["duzgun"] = {k: v for k, v in metrikler(pu, Ks, 1.0).items() if k in ("kosu", "log_loss", "brier")}
    fav = r["metrik"]["piyasa"]
    sonuc["metrik"]["favori"] = {k: fav[k] for k in ("kosu", "ilk_secim_isabet", "ikili_sirali_isabet", "ilk_iki_ikisi_de_ilk2")}
    sonuc["harman_eksi_piyasa"] = r["harman_eksi_piyasa"]; sonuc["model_eksi_piyasa"] = r["model_eksi_piyasa"]
    sonuc["sira_ll"] = r.get("sira_ll")   # indirimli Harville (γ, δ öğrenilmiş) vs düz Harville: ikili/üçlü log-loss
    w = Ks.y > 0
    dk = -np.log(np.clip(ph[w], 1e-12, 1)) + np.log(np.clip(r["p_ek"]["keskin"][w], 1e-12, 1))
    sonuc["harman_eksi_keskin_piyasa"] = {"ll_fark": round(float(dk.mean()), 4),
                                          "std_hata": round(float(dk.std() / math.sqrt(len(dk))), 4)}
    sonuc["kovalar"] = r["kovalar"]
    sonuc["onem"] = sorted([{"ozellik": a, "std_katsayi": round(float(w), 4)} for a, w in zip(m.adlar, m.w)],
                           key=lambda d: -abs(d["std_katsayi"]))
    sonuc["birlestirme"] = [{"c_dogrusal": round(float(x.cl), 3), "c_gbm": round(float(x.cg), 3),
                             "alfa": round(float(x.alfa), 3), "beta": round(float(x.beta), 3)} for x in r["modeller"]]
    if ablasyon:
        # Ablasyon yalnız doğrusal katmanla (GBM'siz) ölçülür: hızlıdır ve grubun ham bilgisini gösterir.
        # Süre için klasik (patlatılmamış) logitle; gece akışında haftada bir çalışır (bkz. gece.py).
        from ozellik import GRUP
        global PATLAT
        _p, PATLAT = PATLAT, (1.0,)
        taban = sina(T, kosular, "aylik", lam=m.lam, gbm=False)
        tab = []
        for g in sorted({GRUP[a] for a in T["adlar"]}):
            sut = [i for i, a in enumerate(T["adlar"]) if GRUP[a] != g]
            rg = sina(T, kosular, "aylik", lam=m.lam, gbm=False, sutun=sut)
            tab.append({"grup_cikarildi": g,
                        "model_ll_fark": round(rg["metrik"]["model"]["log_loss"] - taban["metrik"]["model"]["log_loss"], 4),
                        "harman_ll_fark": round(rg["metrik"]["harman"]["log_loss"] - taban["metrik"]["harman"]["log_loss"], 4)})
        PATLAT = _p
        sonuc["ablasyon"] = sorted(tab, key=lambda d: -d["model_ll_fark"])
    return m, sonuc, iz_cikar(r, kosular)


def uretim_modeli(T, kosular, lam=None, gbm=True):
    """Yayın modeli, değerlendirmeyle aynı tarif: son KAL_GUN gün kalibrasyon, öncesi (zaman ağırlıklı) eğitim."""
    K = kume_kur(T)
    tarih, gunler, tam_oran, idx, ilk = _pencereler(kosular)
    g0 = int(gunler[-1]) + 1
    kal_bas = g0 - KAL_GUN
    Kf = _ozel(K, (idx >= ilk) & (gunler < kal_bas))
    Kh = _ozel(K, (gunler >= kal_bas) & tam_oran)
    ag = 0.5 ** ((kal_bas - gunler[Kf.kosu_no[Kf.bas]]) / YARI_OMUR) if YARI_OMUR else None
    m, _ = egit(Kf, Kh, T["adlar"], lam=lam, agirlik=ag, gbm=gbm)
    return m
