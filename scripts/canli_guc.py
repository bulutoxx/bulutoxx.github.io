"""OXXai · Canlı güç modeli (CG) — maç içi kalan gol modeli (sunucu tarafı tek kaynak; uygulamadaki <script id="canli-guc"> ile BİREBİR).

Eski canlı model (canli_istat.rem_lams): kalan süre payı × maç öncesi gol beklentisi, sabit ±%10 skor etkisi, kırmızı kart,
bağımsız Poisson. Eksikleri: (1) maçta şimdiye kadar atılan gol takımın gerçek gücü hakkında bilgi taşır ama yok sayılır,
(2) Poisson aşırı kesin (uygulama bu yüzden Platt b≈0,58 ile çok sert büzüyordu), (3) skor etkileri ölçülmemiş sabitler.

CG (parametreler yalnız kayıtlı canlı anlık görüntüler + maç sonuçlarından, zaman sıralı öğrenilir — lab/canli_guc_lab.py):
  rem      = kalan süre gol payı (canli_istat.rem_share, v117 biçimi: e1/e2 uzatma + yarı içi artan yoğunluk ξ; h1 öğrenilir)
  el       = 1 − rem  (geçen süre payı)
  durum    = t ≥ 15 ise skor durumu çarpanı: geride exp(g_tr + g_trl·geç), önde exp(g_ld), eşit exp(g_lv); geç = sınırla((t−60)/30, 0, 1)
  kart     = 0,72^kendi kırmızı × 1,25^rakip kırmızı   (Titman ve ark. 2015; kayıtlarda kart verisi az → sabit)
  Bayes    = takım gücü çarpanı θ ~ Gamma(a, a) (ortalama 1). Atılan gol x, geçen beklenen gol E = s·λ·el →
             θ | veri ~ Gamma(a + x, a + E)  (eşlenik güncelleme)
  kalan gol ~ Negatif Binom(ortalama μ = s·λ·rem·durum·kart·(a + x)/(a + E), şekil r = a + x)   (Gamma-Poisson öngörü dağılımı)
  İki takım bağımsız; ızgara 0..10.
Kaynaklar: Dixon & Robinson (1998) — skor durumuna bağlı gol hızları; Maher (1982) / Karlis & Ntzoufras (2003) — Poisson ve aşırı
yayılım; Gelman ve ark. BDA (Gamma-Poisson eşlenik). Kayıt dışı canlı istatistik (ESPN şut vb.) ayarı ayrıdır (canli_istat.mult) ve
yalnız ayrı kapısını geçerse etkindir.
"""
import json, math, os

DEF = {"s": 1.0, "h1": 0.4437, "xi": 1.0, "e1": 3.0, "e2": 3.0, "rmin": 1.0, "a": 8.0,
       "g_tr": 0.1, "g_trl": 0.0, "g_ld": -0.1, "g_lv": -0.1, "rc_own": 0.72, "rc_opp": 1.25, "nmax": 10}
KEYS = ("s", "h1", "xi", "a", "g_tr", "g_trl", "g_ld", "g_lv")


def ayar(data_dir=None):
    """data/canli_guc.json → {"kullan": bool, "params": {...}} ; kullan=false ya da dosya yoksa None (eski yol)."""
    try:
        j = json.load(open(os.path.join(data_dir, "canli_guc.json"), encoding="utf-8"))
        if not j.get("kullan"): return None
        P = dict(DEF)
        for k, v in (j.get("params") or {}).items():
            if k in P and isinstance(v, (int, float)) and math.isfinite(v): P[k] = float(v)
        return P
    except Exception:
        return None


def _F(u, xi): return u + xi * (u * u - u) / 2


def rem_share(t, pd, P):
    h1 = P["h1"]
    if pd == 0: return 1 - h1
    if pd is None: pd = 1 if t < 45 else 2
    xi, e1, e2, rmin = P["xi"], P["e1"], P["e2"], P["rmin"]
    if pd == 1:
        a = max(0.0, t); r = (45 - t) + e1 if t < 45 else max(e1 - (t - 45), rmin)
        return (1 - _F(a / (a + r), xi)) * h1 + (1 - h1)
    a = max(0.0, t - 45); r = (90 - t) + e2 if t < 90 else max(e2 - (t - 90), rmin)
    return max(.004, (1 - _F(a / (a + r), xi)) * (1 - h1))


def lams(lh, la, hs, as_, t, rc, pd, P):
    """Kalan sürede ortalama gol (μH, μA) ve NB şekilleri (rH, rA)."""
    rem = rem_share(t, pd, P); el = max(0.0, 1 - rem); d = hs - as_
    late = min(1.0, max(0.0, (t - 60) / 30))
    def st(dd):
        if t < 15: return 1.0
        return math.exp(P["g_tr"] + P["g_trl"] * late) if dd < 0 else math.exp(P["g_ld"]) if dd > 0 else math.exp(P["g_lv"])
    rc = rc or [0, 0]; a = P["a"]; s = P["s"]
    kH = P["rc_own"] ** (rc[0] or 0) * P["rc_opp"] ** (rc[1] or 0); kA = P["rc_own"] ** (rc[1] or 0) * P["rc_opp"] ** (rc[0] or 0)
    bH = (a + hs) / (a + s * lh * el); bA = (a + as_) / (a + s * la * el)
    return s * lh * rem * st(d) * kH * bH, s * la * rem * st(-d) * kA * bA, a + hs, a + as_


def nb_pmf(mu, r, n):
    q = r / (r + mu); p = [q ** r]
    for k in range(n): p.append(p[-1] * (k + r) / (k + 1) * (mu / (r + mu)))
    z = sum(p)
    return [x / z for x in p]       # kuyruk (> n) ızgaraya katılır


def probs(lh, la, hs, as_, t, rc, pd, P):
    """MS 1/X/2, maç sonu 2,5 Üst, kalan gol dağılımı, gol olmaz, sıradaki gol (H/A)."""
    mH, mA, rH, rA = lams(lh, la, hs, as_, t, rc, pd, P); n = int(P["nmax"])
    ph, pa = nb_pmf(mH, rH, n), nb_pmf(mA, rA, n)
    H = D = A = O = 0.0; tot = [0.0] * (2 * n + 1)
    for i in range(n + 1):
        for j in range(n + 1):
            q = ph[i] * pa[j]; fh, fa = hs + i, as_ + j
            if fh > fa: H += q
            elif fh == fa: D += q
            else: A += q
            if fh + fa > 2: O += q
            tot[i + j] += q
    none = ph[0] * pa[0]; s = mH + mA or 1e-9
    return {"H": H, "D": D, "A": A, "o25": O, "tot": tot, "none": none, "nh": (1 - none) * mH / s, "na": (1 - none) * mA / s, "LH": mH, "LA": mA}


def over(Pr, line, cur):
    """Maç toplamı line'ı aşar: kalan gol > line − mevcut."""
    need = int(math.floor(line)) - cur + 1
    if need <= 0: return 1.0
    return max(0.0, 1 - sum(Pr["tot"][:need]))


def pick_p(Pr, rk, hs, as_):
    """Kayıtlı canlı seçimin (rk) CG olasılığı."""
    if rk == "1": return Pr["H"]
    if rk == "X": return Pr["D"]
    if rk == "2": return Pr["A"]
    if rk and rk[0] in "UA" and rk[1:]:
        po = over(Pr, float(rk[1:]), hs + as_); return po if rk[0] == "U" else 1 - po
    if rk == "G1": return Pr["nh"]
    if rk == "G2": return Pr["na"]
    if rk == "G0": return Pr["none"]
    return None
