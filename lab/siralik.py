#!/usr/bin/env python3
"""⏱️ YH-17 · Her an geçerli (sıralı) test yardımcıları — yalnız ölçüm; üretim tahminine dokunmaz.

Sabit süreli kapıda (ör. 14 gün izleme, tek seferlik %95 GA) sonuçlara her gün bakmak I. tür hatayı şişirir. Burada
Robbins normal karışım martingali ile kurulan **asimptotik güven dizisi** (Waudby-Smith, Arbour, Sinha, Kennedy, Ramdas 2021,
"Time-uniform central limit theory and asymptotic confidence sequences", arXiv:2103.06476; Howard ve ark. 2021, arXiv:1810.08240)
kullanılır: her t anında

    ort_t ± σ̂_t · sqrt( 2(tρ²+1) / (t²ρ²) · log( sqrt(tρ²+1) / α ) )

aralığı, istenildiği kadar bakılsa bile (tüm t'ler için aynı anda) ≥ 1−α olasılıkla gerçek ortalamayı kapsar (iki yanlı).
ρ, hedef karar zamanı t* için en dar olacak biçimde seçilir: ρ² = (−2 log α + log(1 − 2 log α)) / t*.

Birim = blok (gün ya da lig×gün) ortalaması: blok içi bağımlılık bloğun içinde kalır. Isınma: t < T_MIN blokta karar verilmez.
Düzeltmeler (benzetimle, geliştirme tohumu 17'de seçildi; kapı ölçümü ayrı tohumla): küçük örneklem çarpanı t_{0,975; t−1} / z_{0,975};
bloklar arası pozitif ardışık ilişkide uzun dönem varyans çarpanı (1+φ̂)/(1−φ̂) (t ≥ 10).
e-değer (alfa yatırımına bağlanabilir; düzeltmesiz ham hâli): E_t = (1+ρ²V)^{-1/2} · exp(ρ² S² / (2(1+ρ²V))), V = t σ̂².
"""
import math

import numpy as np
from scipy import stats as _st

T_MIN = 5          # ısınma: en az bu kadar blok olmadan karar yok (σ̂ kararsız)
SIG_TABAN = 1e-9


def rho2(t_hedef, alfa):
    la = -2.0 * math.log(alfa)
    return (la + math.log(1.0 + la)) / max(1.0, float(t_hedef))


def yaricap(t, sig, alfa, t_hedef):
    """t blok, σ̂ (blok başına) → ortalama için her an geçerli yarıçap. t ve sig dizi olabilir."""
    t = np.asarray(t, float); sig = np.maximum(np.asarray(sig, float), SIG_TABAN)
    r2 = rho2(t_hedef, alfa); u = t * r2
    return sig * np.sqrt(2.0 * (u + 1.0) / (t * u) * np.log(np.sqrt(u + 1.0) / alfa))


def kucuk_orneklem(t):
    """Küçük örneklem düzeltmesi: σ̂ eklentisinin az blokta dar kalmasını Student-t / normal oranıyla telafi eder (benzetimle seçildi)."""
    t = np.asarray(t, float); df = np.maximum(t - 1.0, 1.0)
    return _st.t.ppf(0.975, df) / _st.norm.ppf(0.975)


def katsayi(oran, alfa=0.05):
    """Sabit örneklem σ_ort çarpanı: yarıçap = σ_ort · katsayi(t/t*). (Özet istatistikten yaklaşık karar için.)"""
    la = -2.0 * math.log(alfa); u = (la + math.log(1.0 + la)) * oran
    return math.sqrt(2.0 * (u + 1.0) / u * math.log(math.sqrt(u + 1.0) / alfa))


def _phi_dizi(x):
    """Her önek için lag-1 ilişki (0..0,9'a kırpılmış); x: (R, T). t < 10 → 0."""
    R, T = x.shape; t = np.arange(1, T + 1, dtype=float)
    s = np.cumsum(x, 1); s2 = np.cumsum(x * x, 1); m = s / t
    xy = np.concatenate([np.zeros((R, 1)), np.cumsum(x[:, :-1] * x[:, 1:], 1)], 1)       # Σ_{i<t} x_i x_{i+1}
    sa = s - x                                                                            # Σ x_1..x_{t-1}
    sb = s - x[:, :1]                                                                     # Σ x_2..x_t
    num = xy - m * (sa + sb) + (t - 1) * m * m
    den = s2 - t * m * m
    with np.errstate(invalid="ignore", divide="ignore"):
        phi = np.where(den > 0, num / den * t / np.maximum(t - 1, 1), 0.0)
    phi = np.clip(np.nan_to_num(phi), 0.0, 0.9); phi[:, t < 10] = 0.0
    return phi


def guven_matris(x, alfa=0.05, t_hedef=14):
    """x: (R, T) blok ortalamaları. Dönüş: ort, yarıçap (R, T). Küçük örneklem ve uzun dönem varyans düzeltmeli."""
    x = np.atleast_2d(np.asarray(x, float)); R, T = x.shape; t = np.arange(1, T + 1, dtype=float)
    s = np.cumsum(x, 1); s2 = np.cumsum(x * x, 1); ort = s / t
    var = np.maximum(s2 / t - ort ** 2, 0.0) * t / np.maximum(t - 1.0, 1.0)
    phi = _phi_dizi(x); lrv = (1 + phi) / (1 - phi)
    r = yaricap(t[None, :], np.sqrt(var * lrv), alfa, t_hedef) * kucuk_orneklem(t)[None, :]
    r[:, t < T_MIN] = np.inf
    return ort, r


def guven_dizisi(x, alfa=0.05, t_hedef=14):
    """x: blok ortalamaları (zaman sırasıyla). Dönüş: (t, ort, alt, üst) dizileri; t < T_MIN için alt/üst = ∓inf."""
    x = np.asarray(x, float); n = len(x)
    if n == 0: return (np.zeros(0),) * 4
    ort, r = guven_matris(x[None, :], alfa, t_hedef); ort, r = ort[0], r[0]
    return np.arange(1, n + 1, dtype=float), ort, ort - r, ort + r


def e_deger(x, alfa=0.05, t_hedef=14):
    """Normal karışım e-süreci (asimptotik, σ̂ ile). 0 hipotezi: ortalama = 0."""
    t, ort, _, _ = guven_dizisi(x, alfa, t_hedef)
    x = np.asarray(x, float)
    var = np.array([np.var(x[:i], ddof=1) if i > 1 else np.inf for i in range(1, len(x) + 1)])
    V = t * var; r2 = rho2(t_hedef, alfa); S = ort * t
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        e = np.exp(r2 * S * S / (2.0 * (1.0 + r2 * V))) / np.sqrt(1.0 + r2 * V)
    e[t < T_MIN] = 1.0
    return np.nan_to_num(e, nan=1.0)


def karar(x, alfa=0.05, t_hedef=14, marj=0.0):
    """ΔLL (aday − üretim; negatif = iyi) blok dizisi için ilk kesin karar.
    'iyi'  : üst sınır < −marj  (aday açıkça iyi → erken yayın)
    'kotu' : alt sınır > marj   (aday açıkça kötü → erken geri alma / ret)
    'devam': henüz karar yok.  Dönüş: {"karar", "t", "ort", "alt", "ust"} (karar anı ya da son an)."""
    t, ort, lo, hi = guven_dizisi(x, alfa, t_hedef)
    for i in range(len(t)):
        if hi[i] < -marj: return {"karar": "iyi", "t": int(t[i]), "ort": float(ort[i]), "alt": float(lo[i]), "ust": float(hi[i])}
        if lo[i] > marj: return {"karar": "kotu", "t": int(t[i]), "ort": float(ort[i]), "alt": float(lo[i]), "ust": float(hi[i])}
    if not len(t): return {"karar": "devam", "t": 0}
    f = lambda v: None if not np.isfinite(v) else float(v)
    return {"karar": "devam", "t": int(t[-1]), "ort": float(ort[-1]), "alt": f(lo[-1]), "ust": f(hi[-1])}
