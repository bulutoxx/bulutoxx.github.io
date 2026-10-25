# BULUTOXX at yarışı laboratuvarı — koşu içi koşullu logit (Benter) + piyasa harmanı + Harville/Henery.
# Değerlendirme zaman sıralıdır: [ısınma | model eğitimi | harman/kalibrasyon | SINAMA (son %30)].
import math

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


def clogit(X, K, lam=1.0, iters=50, w0=None):
    """Koşu içi koşullu logit, L2 (lam), Newton yöntemi. X standartlaştırılmış olmalı."""
    d = X.shape[1]
    w = np.zeros(d) if w0 is None else w0.copy()
    onceki = None
    for _ in range(iters):
        p = softmax_kosu(X @ w, K)
        ll = np.sum(np.log(p[K.y > 0] + 1e-300)) - 0.5 * lam * w @ w
        g = X.T @ (K.y - p) - lam * w
        M = np.add.reduceat(p[:, None] * X, K.bas)
        H = (X * p[:, None]).T @ X - M.T @ M + lam * np.eye(d)
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


# ---------------------------------------------------------------- tam boru hattı
class Model:
    """Standartlaştırma + ağırlıklar + harman/kalibrasyon parametreleri. JSON'a yazılabilir."""

    def __init__(self, adlar, mu, sd, w, T, alfa, beta, gam, dlt, lam):
        self.adlar, self.mu, self.sd, self.w = list(adlar), np.asarray(mu), np.asarray(sd), np.asarray(w)
        self.T, self.alfa, self.beta, self.gam, self.dlt, self.lam = T, alfa, beta, gam, dlt, lam

    def puan(self, X):
        return ((X - self.mu) / self.sd) @ self.w

    def p_model(self, X, K):
        return softmax_kosu(self.puan(X) / self.T, K)

    def p_harman(self, X, K, q):
        s = self.alfa * np.log(softmax_kosu(self.puan(X), K)) + self.beta * np.log(np.clip(q, 1e-9, 1))
        return softmax_kosu(s, K)

    def json(self):
        return {"ozellikler": self.adlar, "ortalama": [round(float(v), 6) for v in self.mu],
                "olcek": [round(float(v), 6) for v in self.sd], "agirlik": [round(float(v), 6) for v in self.w],
                "sicaklik": round(self.T, 4), "alfa": round(self.alfa, 4), "beta": round(self.beta, 4),
                "henery_gamma": self.gam, "henery_delta": self.dlt, "lambda": self.lam}

    @staticmethod
    def yukle(j):
        return Model(j["ozellikler"], j["ortalama"], j["olcek"], j["agirlik"], j["sicaklik"], j["alfa"],
                     j["beta"], j["henery_gamma"], j["henery_delta"], j.get("lambda"))


def _ozel(K, m):
    """Satır maskesi yerine koşu maskesi alır."""
    return K.alt(m[K.seg])


def egit(K_fit, K_har, adlar, lam=None, sutun=None, henery=True):
    """K_fit: model eğitimi; K_har: harman/kalibrasyon dilimi (tam oranlı koşular). sutun: kullanılacak özellikler."""
    sutun = np.arange(K_fit.X.shape[1]) if sutun is None else np.asarray(sutun)
    Xf, Xh = K_fit.X[:, sutun], K_har.X[:, sutun]
    mu, sd = Xf.mean(0), Xf.std(0) + 1e-9
    Zf, Zh = (Xf - mu) / sd, (Xh - mu) / sd
    if lam is None:
        en = (1e9, None)
        for l in LAMBDALAR:
            w = clogit(Zf, K_fit, l)
            ll = logloss(softmax_kosu(Zh @ w, K_har), K_har)
            en = min(en, (ll, l))
        lam = en[1]
    w = clogit(Zf, K_fit, lam)
    s = Zh @ w
    # sıcaklık (yalnız model): p ∝ exp(s / T)
    a = clogit(s[:, None], K_har, 1e-6)[0]
    T = 1.0 / a if a > 1e-3 else 1.0
    # piyasa harmanı: p ∝ exp(α log p_model + β log q)
    lpm = np.log(softmax_kosu(s, K_har))
    ab = clogit(np.c_[lpm, np.log(K_har.q)], K_har, 1e-6)
    m = Model([adlar[i] for i in sutun], mu, sd, w, float(T), float(ab[0]), float(ab[1]), 1.0, 1.0, lam)
    if henery:
        ph = m.p_harman(Xh, K_har, K_har.q)
        m.gam = henery_ussu(ph, K_har, 2)
        m.dlt = henery_ussu(ph, K_har, 3)
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


def degerlendir(T, kosular, ablasyon=True):
    """Zaman sıralı tam değerlendirme. Sözlük döner: model, metrikler, önem, ablasyon, kovalar."""
    K = kume_kur(T)
    B = bolumle(T, kosular)
    Kf, Kh, Ks = _ozel(K, B["egitim"]), _ozel(K, B["harman"]), _ozel(K, B["sinama"])
    m, _ = egit(Kf, Kh, T["adlar"])
    pm = m.p_model(Ks.X, Ks)
    ph = m.p_harman(Ks.X, Ks, Ks.q)
    pq = Ks.q
    pu = 1.0 / Ks.n[Ks.seg]
    sonuc = {"bolum": B["tarih"], "kosu_sayisi": {"egitim": int(Kf.R), "harman": int(Kh.R), "sinama": int(Ks.R)}}
    sonuc["metrik"] = {
        "model": metrikler(pm, Ks, m.gam), "piyasa": metrikler(pq, Ks, m.gam),
        "harman": metrikler(ph, Ks, m.gam), "duzgun": {k: v for k, v in metrikler(pu, Ks, 1.0).items()
                                                      if k in ("kosu", "log_loss", "brier")}}
    # harman - piyasa: koşu başına log-loss farkının ortalaması ve standart hatası (eşleştirilmiş)
    w = Ks.y > 0
    for ad_, pp in (("harman", ph), ("model", pm)):
        d = -np.log(np.clip(pp[w], 1e-12, 1)) + np.log(pq[w])
        sonuc[f"{ad_}_eksi_piyasa"] = {"ll_fark": round(float(d.mean()), 4), "std_hata": round(float(d.std() / math.sqrt(len(d))), 4)}
    # favori tabanı: piyasa favorisi kazanır, ikili = en düşük iki oran sırasıyla
    fav = metrikler(pq, Ks, 1.0)
    sonuc["metrik"]["favori"] = {k: fav[k] for k in ("kosu", "ilk_secim_isabet", "ikili_sirali_isabet", "ilk_iki_ikisi_de_ilk2")}
    sonuc["kovalar"] = {"harman": kovalar(ph, Ks.y), "model": kovalar(pm, Ks.y), "piyasa": kovalar(pq, Ks.y)}
    sonuc["onem"] = sorted([{"ozellik": a, "std_katsayi": round(float(w), 4)} for a, w in zip(m.adlar, m.w)],
                           key=lambda d: -abs(d["std_katsayi"]))
    if ablasyon:
        from ozellik import OZELLIKLER, GRUPLAR
        tab = []
        for g in GRUPLAR:
            sut = [i for i, (_, gg) in enumerate(OZELLIKLER) if gg != g]
            mg, s = egit(Kf, Kh, T["adlar"], lam=m.lam, sutun=sut, henery=False)
            Xs = Ks.X[:, s]
            tab.append({"grup_cikarildi": g,
                        "model_ll_fark": round(logloss(mg.p_model(Xs, Ks), Ks) - sonuc["metrik"]["model"]["log_loss"], 4),
                        "harman_ll_fark": round(logloss(mg.p_harman(Xs, Ks, Ks.q), Ks) - sonuc["metrik"]["harman"]["log_loss"], 4)})
        sonuc["ablasyon"] = sorted(tab, key=lambda d: -d["model_ll_fark"])
    return m, sonuc, (K, B)


def eski_modeli_sina(eski_json, K, B):
    """Kaydedilmiş (dünkü) değerlendirme modelini BUGÜNKÜ sınama dilimiyle ölçer (aynı koşullarda kıyas)."""
    from ozellik import ADLAR
    if not eski_json or eski_json.get("ozellikler") != ADLAR:
        return None
    m = Model.yukle(eski_json)
    Ks = _ozel(K, B["sinama"])
    ph = m.p_harman(Ks.X, Ks, Ks.q)
    return {"log_loss": round(logloss(ph, Ks), 4), "ilk_secim_isabet": metrikler(ph, Ks, m.gam)["ilk_secim_isabet"]}


def uretim_modeli(T, kosular, lam):
    """Yayın için aynı tarif, pencere kaydırılmış: model tüm geçmişin ilk %85'i, harman son %15 ile."""
    K = kume_kur(T)
    tarih = np.array([k["tarih"] for k in kosular])
    R = len(kosular)
    tam_oran = np.array([not any(a["oran"] is None for a in k["atlar"]) for k in kosular])
    ilk = int(np.searchsorted(tarih, ISINMA_SONU))
    kes = int(R * (1 - HARMAN_PAYI)); kes = int(np.searchsorted(tarih, tarih[kes]))
    idx = np.arange(R)
    m, _ = egit(_ozel(K, (idx >= ilk) & (idx < kes)), _ozel(K, (idx >= kes) & tam_oran), T["adlar"], lam=lam)
    return m
