# BULUTOXX at yarışı laboratuvarı — koşu içi koşullu logit (Benter) + isteğe bağlı GBM + piyasa harmanı + Harville/Henery.
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


def _gun(t):
    from datetime import date
    return date.fromisoformat(t).toordinal()


def gbm_egit(X, K, agirlik=None, ayar=None, init=None):
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
           "bagging_freq": 1, "lambda_l2": a["l2"], "verbose": -1, "seed": 1, "deterministic": True,
           "num_threads": min(4, os.cpu_count() or 1)}
    return lgb.train(par, lgb.Dataset(X, free_raw_data=False), num_boost_round=a["n_agac"])


def gbm_yukle(metin):
    if lgb is None or not metin:
        return None
    return lgb.Booster(model_str=metin)


# ---------------------------------------------------------------- tam boru hattı
class Model:
    """Standartlaştırma + doğrusal ağırlıklar (+ isteğe bağlı GBM) + kalibrasyon/harman parametreleri.
    Birleşik puan s = cl·(doğrusal) + cg·(GBM); yalnız model: p ∝ exp(s / T); harman: p ∝ exp(α log p_s + β log q).
    Eski (v1) model.json'lar da okunur: cl=1, cg=0, T=sıcaklık."""

    def __init__(self, adlar, mu, sd, w, T, alfa, beta, gam, dlt, lam, cl=1.0, cg=0.0, gbm=None, yedek=None,
                 ku=1.0, cu=0.0):
        self.adlar, self.mu, self.sd, self.w = list(adlar), np.asarray(mu), np.asarray(sd), np.asarray(w)
        self.T, self.alfa, self.beta, self.gam, self.dlt, self.lam = T, alfa, beta, gam, dlt, lam
        self.cl, self.cg, self.gbm, self.yedek = cl, cg, gbm, yedek
        self.ku, self.cu = ku, cu   # üst uç kalibrasyonu: s = ku·s0 + cu·max(log p0 − log eşik, 0)
        self.bq, self.gbm_artik, self.ab_artik = 1.0, None, None
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

    def _ust(self, s0, K):
        if not self.cu or self._yedekte():
            return s0
        lp = np.log(softmax_kosu(s0, K))
        return self.ku * s0 + self.cu * np.maximum(lp - math.log(UST_ESIK), 0.0)

    def p_model(self, X, K):
        return softmax_kosu(self._ust(self.birlesik(X), K) / self.T, K)

    def p_harman(self, X, K, q):
        a, b = (self.yedek["alfa"], self.yedek["beta"]) if self._yedekte() else (self.alfa, self.beta)
        s = a * np.log(softmax_kosu(self._ust(self.birlesik(X), K), K)) + b * np.log(np.clip(q, 1e-9, 1))
        return softmax_kosu(s, K)

    def p_keskin(self, K, q):
        """Piyasa keskinleştirme kontrolü: p ∝ q^β (β kalibrasyon penceresinde)."""
        return softmax_kosu(self.bq * np.log(np.clip(q, 1e-9, 1)), K)

    def p_harman_artik(self, X, K, q):
        """Harman + kalıntı GBM (init_score = log q ile eğitilmiş ağaçlar)."""
        if self.gbm_artik is None or not self.ab_artik:
            return self.p_harman(X, K, q)
        a, b, c = self.ab_artik
        s = (a * np.log(softmax_kosu(self._ust(self.birlesik(X), K), K)) + b * np.log(np.clip(q, 1e-9, 1))
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
                "k_ust": round(float(self.ku), 5), "c_ust": round(float(self.cu), 5), "ust_esik": UST_ESIK,
                "yedek": ({k: round(float(v), 5) for k, v in self.yedek.items()} if self.yedek else None)}

    @staticmethod
    def yukle(j, gbm_metin=None):
        m = Model(j["ozellikler"], j["ortalama"], j["olcek"], j["agirlik"], j["sicaklik"], j["alfa"],
                     j["beta"], j["henery_gamma"], j["henery_delta"], j.get("lambda"),
                     cl=j.get("c_dogrusal", 1.0), cg=j.get("c_gbm", 0.0), ku=j.get("k_ust", 1.0), cu=j.get("c_ust", 0.0),
                     gbm=(gbm_yukle(gbm_metin) if j.get("gbm") else None), yedek=j.get("yedek"))
        m.gam_m = j.get("henery_gamma_model", m.gam); m.dlt_m = j.get("henery_delta_model", m.dlt)
        m.bq = j.get("piyasa_keskin_beta", 1.0)
        return m


def _ozel(K, m):
    """Satır maskesi yerine koşu maskesi alır."""
    return K.alt(m[K.seg])


def egit(K_fit, K_har, adlar, lam=None, sutun=None, henery=True, agirlik=None, gbm=True, artik=False):
    """K_fit: model eğitimi; K_har: kalibrasyon/harman dilimi (tam oranlı koşular). sutun: kullanılacak özellikler.
    agirlik: K_fit koşuları için ağırlık (zaman ağırlıklı eğitim). gbm: LightGBM katmanı (kuruluysa)."""
    sutun = np.arange(K_fit.X.shape[1]) if sutun is None else np.asarray(sutun)
    Xf, Xh = K_fit.X[:, sutun], K_har.X[:, sutun]
    mu, sd = Xf.mean(0), Xf.std(0) + 1e-9
    Zf, Zh = (Xf - mu) / sd, (Xh - mu) / sd
    if lam is None:
        en = (1e9, None)
        for l in LAMBDALAR:
            w = clogit(Zf, K_fit, l, agirlik=agirlik)
            ll = logloss(softmax_kosu(Zh @ w, K_har), K_har)
            en = min(en, (ll, l))
        lam = en[1]
    w = clogit(Zf, K_fit, lam, agirlik=agirlik)
    s = Zh @ w
    lq = np.log(K_har.q)
    # yalnız doğrusal: sıcaklık (c = 1/T) ve harman — GBM yoksa ya da yedek olarak
    c_lin = float(clogit(s[:, None], K_har, 1e-6)[0])
    ab_y = clogit(np.c_[np.log(softmax_kosu(c_lin * s, K_har)), lq], K_har, 1e-6)
    yedek = {"cl": c_lin, "alfa": float(ab_y[0]), "beta": float(ab_y[1])}
    booster, cl, cg = None, c_lin, 0.0
    if gbm and lgb is not None:
        booster = gbm_egit(Xf, K_fit, agirlik)
        g = booster.predict(Xh, raw_score=True)
        cl, cg = (float(v) for v in clogit(np.c_[s, g], K_har, 1e-6))
        sb = cl * s + cg * g
    else:
        sb = c_lin * s
    ku, cu = 1.0, 0.0
    if UST_KAL:
        h = np.maximum(np.log(softmax_kosu(sb, K_har)) - math.log(UST_ESIK), 0.0)
        ku, cu = (float(v) for v in clogit(np.c_[sb, h], K_har, 1e-6))
        sb = ku * sb + cu * h
    ab = clogit(np.c_[np.log(softmax_kosu(sb, K_har)), lq], K_har, 1e-6) if (booster is not None or UST_KAL) else ab_y
    m = Model([adlar[i] for i in sutun], mu, sd, w, 1.0, float(ab[0]), float(ab[1]), 1.0, 1.0, lam,
              cl=cl, cg=cg, gbm=booster, yedek=(yedek if booster is not None else None), ku=ku, cu=cu)
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
    return {"egitim": (idx >= ilk) & (idx < kes_h), "harman": (idx >= kes_h) & (idx < kes_s) & tam_oran,
            "sinama": (idx >= kes_s) & tam_oran, "sinama_tum": idx >= kes_s,
            "tarih": {"isinma_bitis": ISINMA_SONU, "egitim": [tarih[ilk], tarih[kes_h - 1]],
                      "harman": [tarih[kes_h], tarih[kes_s - 1]], "sinama": [tarih[kes_s], tarih[-1]]}}


def kume_kur(T):
    return Kume(T["X"], T["y"], T["sira"], T["q"], T["kid"])


def _pencereler(kosular):
    tarih = np.array([k["tarih"] for k in kosular])
    gunler = np.array([_gun(t) for t in tarih])
    tam_oran = np.array([not any(a["oran"] is None for a in k["atlar"]) for k in kosular])
    return tarih, gunler, tam_oran, np.arange(len(kosular)), int(np.searchsorted(tarih, ISINMA_SONU))


def sina(T, kosular, protokol="aylik", lam=None, yari_omur="vars", kal_gun=None, henery=False, gbm=False, sutun=None,
         artik=False):
    """Sınama dilimi (son %30, tam oranlı) için tahminleri üretir ve metrikleri döner.
    protokol='sabit': tek model (eğitim → harman → sınama), v1 yöntemi.
    protokol='aylik': sınamanın her ayı için yalnız o aydan önceki verilerle yeniden eğitim (genişleyen pencere);
                      kalibrasyon ayın hemen öncesindeki `kal_gun` günde. Yayındaki modelin gerçekte nasıl
                      çalıştığını (her gece tüm geçmişle eğitim) dürüstçe taklit eder."""
    yari_omur = YARI_OMUR if yari_omur == "vars" else yari_omur
    kal_gun = kal_gun or KAL_GUN
    K = kume_kur(T)
    B = bolumle(T, kosular)
    Ks = _ozel(K, B["sinama"])
    Xs = Ks.X if sutun is None else Ks.X[:, sutun]
    tarih, gunler, tam_oran, idx, ilk = _pencereler(kosular)
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
                for ad_, pp, g, d in (("model", pm[satir], m.gam_m, m.dlt_m), ("harman", ph[satir], m.gam, m.dlt)):
                    l2, l3 = sira_ll(pp, Ka, g, d)
                    h2, h3 = sira_ll(pp, Ka, 1.0, 1.0)
                    s2[ad_].append((l2, l3)); s2[ad_ + "_h1"].append((h2, h3))
            modeller.append(m)
    pq = Ks.q
    out = {"metrik": {"model": metrikler(pm, Ks), "harman": metrikler(ph, Ks), "piyasa": metrikler(pq, Ks),
                      "piyasa_keskin": metrikler(pk, Ks)},
           "kovalar": {"model": kovalar(pm, Ks.y), "harman": kovalar(ph, Ks.y), "piyasa": kovalar(pq, Ks.y)},
           "p": (pm, ph), "p_ek": {"keskin": pk, "harman_artik": pa}, "Ks": Ks, "modeller": modeller, "B": B}
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
    Ks = r["Ks"]; pm, ph = r["p"]
    iz = []
    for k in range(Ks.R):
        a, b = Ks.bas[k], Ks.bas[k] + Ks.n[k]
        y = Ks.y[a:b]; ko = kosular[Ks.kosu_no[a]]
        sat = [f'{ko["tarih"]}/{ko["hipodrom"]}/{ko["kosu"]}']
        for p in (pm[a:b], ph[a:b]):
            sat += [round(float(-np.log(max(p[y > 0][0], 1e-12))), 4), int(y[np.argmax(p)] > 0)]
        iz.append(sat)
    return iz


def iz_kiyas(yeni, eski):
    """Ortak koşularda (ll_model, ilk_model, ll_harman, ilk_harman) ortalamaları: (yeni, eski, n)."""
    e = {s[0]: s for s in eski}
    ort = [s for s in yeni if s[0] in e]
    if not ort:
        return None
    f = lambda L, i: round(float(np.mean([s[i] for s in L])), 4)
    eo = [e[s[0]] for s in ort]
    return {"kosu": len(ort),
            "yeni": {"model_ll": f(ort, 1), "model_ilk": f(ort, 2), "harman_ll": f(ort, 3), "harman_ilk": f(ort, 4)},
            "eski": {"model_ll": f(eo, 1), "model_ilk": f(eo, 2), "harman_ll": f(eo, 3), "harman_ilk": f(eo, 4)}}


def degerlendir(T, kosular, ablasyon=True, gbm=True):
    """Yayın tarifinin tam değerlendirmesi (aylık walk-forward). (son ay modeli, sonuç sözlüğü, iz) döner."""
    r = sina(T, kosular, "aylik", gbm=gbm, henery=True)
    Ks = r["Ks"]; pm, ph = r["p"]; pq = Ks.q
    m = r["modeller"][-1]
    B = r["B"]
    sonuc = {"protokol": f"aylık walk-forward: sınamanın her ayı için yalnız o aydan önceki verilerle yeniden eğitim; "
                         f"kalibrasyon ayın hemen öncesindeki {KAL_GUN} günde; zaman ağırlığı yarı ömrü {YARI_OMUR:g} gün",
             "bolum": B["tarih"], "kosu_sayisi": {"egitim": int(np.sum(B["egitim"])), "harman": int(np.sum(B["harman"])),
                                                   "sinama": int(Ks.R)},
             "gbm": bool(gbm and lgb is not None)}
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
        from ozellik import GRUP
        taban = sina(T, kosular, "aylik", lam=m.lam, gbm=False)
        tab = []
        for g in sorted({GRUP[a] for a in T["adlar"]}):
            sut = [i for i, a in enumerate(T["adlar"]) if GRUP[a] != g]
            rg = sina(T, kosular, "aylik", lam=m.lam, gbm=False, sutun=sut)
            tab.append({"grup_cikarildi": g,
                        "model_ll_fark": round(rg["metrik"]["model"]["log_loss"] - taban["metrik"]["model"]["log_loss"], 4),
                        "harman_ll_fark": round(rg["metrik"]["harman"]["log_loss"] - taban["metrik"]["harman"]["log_loss"], 4)})
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
