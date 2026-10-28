"""OXXai · Canlı güç modeli (CG) — maç içi kalan gol modeli (sunucu tarafı tek kaynak; uygulamadaki <script id="canli-guc"> ile BİREBİR).

Eski canlı model (canli_istat.rem_lams): kalan süre payı × maç öncesi gol beklentisi, sabit ±%10 skor etkisi, kırmızı kart,
bağımsız Poisson. Eksikleri: (1) maçta şimdiye kadar atılan gol takımın gerçek gücü hakkında bilgi taşır ama yok sayılır,
(2) Poisson aşırı kesin (uygulama bu yüzden Platt b≈0,58 ile çok sert büzüyordu), (3) skor etkileri ölçülmemiş sabitler.

CG (parametreler yalnız kayıtlı canlı anlık görüntüler + maç sonuçlarından, zaman sıralı öğrenilir — lab/canli_guc_lab.py):
  rem      = kalan süre gol payı (canli_istat.rem_share, v117 biçimi: e1/e2 uzatma + yarı içi artan yoğunluk ξ; h1 öğrenilir)
  el       = 1 − rem  (geçen süre payı)
  durum    = t ≥ 15 ise skor durumu çarpanı: geride exp(g_tr + g_trl·geç), önde exp(g_ld), eşit exp(g_lv); geç = sınırla((t−60)/30, 0, 1)
  geç      = v136 son dakika düzeltmesi (lab/canli_guc_lab.py "gec" kapısı; geçmezse nötr): uzatma beklentisi e2 ve kalan süre tabanı
             rmin öğrenilir; 70→85. dk arası artan yoğunluk exp(g_l2·sınırla((t−70)/15, 0, 1)) her iki takıma; önde olan takımın geç
             dakika hızı exp(g_ld + g_ldl·geç). Nötr değerler (e2=3, rmin=1, g_l2=0, g_ldl=0) eski CG ile birebir aynıdır.
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
       "g_tr": 0.1, "g_trl": 0.0, "g_ld": -0.1, "g_lv": -0.1, "rc_own": 0.72, "rc_opp": 1.25, "nmax": 10,
       "g_l2": 0.0, "g_ldl": 0.0}
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
    late = min(1.0, max(0.0, (t - 60) / 30)); kL = math.exp(P["g_l2"] * min(1.0, max(0.0, (t - 70) / 15)))
    def st(dd):
        if t < 15: return 1.0
        return math.exp(P["g_tr"] + P["g_trl"] * late) if dd < 0 else math.exp(P["g_ld"] + P["g_ldl"] * late) if dd > 0 else math.exp(P["g_lv"])
    rc = rc or [0, 0]; a = P["a"]; s = P["s"]
    kH = P["rc_own"] ** (rc[0] or 0) * P["rc_opp"] ** (rc[1] or 0); kA = P["rc_own"] ** (rc[1] or 0) * P["rc_opp"] ** (rc[0] or 0)
    bH = (a + hs) / (a + s * lh * el); bA = (a + as_) / (a + s * la * el)
    return s * lh * rem * st(d) * kH * bH * kL, s * la * rem * st(-d) * kA * bA * kL, a + hs, a + as_


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
    """Maç toplamı line'ı aşar: kalan gol > line − mevcut. (v144: piyasa harmanı açıksa ana çizgide harmanlı olasılık.)"""
    if Pr.get("ouL") is not None and float(line) == Pr["ouL"]: return Pr["ouP"]
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


# ---------------------------------------------------------------- v144 · YH-10 · canlı piyasa olasılığı + CG harmanı
# Uygulamadaki <script id="canli-piyasa-v144"> (js/katmanlar.js) ve canli-gt-v107 core kancası ile BİREBİR.
#   piyasa(e)  : iddaa canlı etkinliğinden marjı ayrılmış olasılıklar (power yöntemi, uygulamadaki implied() ile aynı 40 adım ikiye bölme)
#                ms = [1, X, 2] · ou = [ana çizgi, Üst] (|alt − üst| en küçük çizgi; idlOdds ile aynı) · ng = [ev, olmaz, dep.] (sıradaki gol)
#                kapalı (askıdaki) pazar → yok. Ham oran döndürmez / kaydedilmez.
#   harman     : her pazar için p_i ∝ exp(a·ln p_CG,i + b·ln p_piyasa,i) (ikili pazarda logit p = a·logit p_CG + b·logit p_piyasa);
#                (a, b) pazar (ms / ou / ng) ve dakika dilimine (0–30, 30–60, 60–75, 75+) göre lab/canli_piyasa_lab.py'de zaman sıralı öğrenilir.
#                Piyasası olmayan pazarda CG aynen kalır.
# Bayrak: data/canli_piyasa.json {kullan, W:{"ms":{"0":[a,b],"30":…,"60":…,"75":…},"ou":{…},"ng":{…}}, golge_W, durum, …}
DILIMLER = (0, 30, 60, 75)
PAZARLAR = ("ms", "ou", "ng")
HARMAN_GOLGE = {m: {str(d): [0.5, 0.5] for d in DILIMLER} for m in PAZARLAR}     # öğrenilmiş ağırlık yokken gölge kaydı için önsel


def implied(o):
    q = [1.0 / x for x in o]; lo, hi, k = 1.0, 3.0, 1.0
    for _ in range(40):
        k = (lo + hi) / 2
        if sum(b ** k for b in q) > 1: lo = k
        else: hi = k
    p = [x ** k for x in q]; s = sum(p)
    return [x / s for x in p]


def piyasa(e):
    """iddaa sportsbook canlı etkinliği → {"ms": [..3], "ou": [çizgi, p_üst], "ng": [..3]} (yalnız açık pazarlar)."""
    ms = ng = None; ous = []                     # uygulamadaki idlOdds gibi: türünün İLK pazarı alınır (kapalıysa o tür yok)
    for m in e.get("m") or []:
        if m.get("t") != 4: continue
        v = {o.get("n"): o.get("odd") for o in m.get("o") or [] if o.get("odd") and o["odd"] > 1.01}
        lock = m.get("s") != 1
        if ms is None and m.get("st") in (4, 1) and all(x in v for x in ("1", "0", "2")): ms = (lock, [v["1"], v["0"], v["2"]])
        if ng is None and m.get("st") == 34 and all(x in v for x in ("1", "Olmaz", "2")): ng = (lock, [v["1"], v["Olmaz"], v["2"]])
        if "Alt" in v and "Üst" in v and m.get("sov") and m.get("st") in (14, 101): ous.append((float(m["sov"]), v["Alt"], v["Üst"], lock))
    out = {}
    if ms and not ms[0]: out["ms"] = implied(ms[1])
    if ng and not ng[0]: out["ng"] = implied(ng[1])
    if ous:
        ou = sorted(ous, key=lambda x: abs(x[1] - x[2]))[0]
        if not ou[3]: out["ou"] = [ou[0], implied([ou[1], ou[2]])[1]]
    return out


def mk_kayit(mk):
    """Canlı kayda yazılan biçim (3 hane; ham oran yok)."""
    r3 = lambda x: round(float(x), 3)
    o = {}
    if mk.get("ms"): o["ms"] = [r3(x) for x in mk["ms"]]
    if mk.get("ou"): o["ou"] = [float(mk["ou"][0]), r3(mk["ou"][1])]
    if mk.get("ng"): o["ng"] = [r3(x) for x in mk["ng"]]
    return o


def dilim(t):
    return "75" if t >= 75 else "60" if t >= 60 else "30" if t >= 30 else "0"


def _hk(pc, pm, a, b):
    z = [a * math.log(max(x, 1e-9)) + b * math.log(max(y, 1e-9)) for x, y in zip(pc, pm)]; mx = max(z)
    e = [math.exp(v - mx) for v in z]; s = sum(e)
    return [v / s for v in e]


def harman_ayar(data_dir, golge=False):
    """data/canli_piyasa.json → ağırlık sözlüğü {pazar: {dilim: (a, b)}}. golge=False: yalnız kullan=true ise; golge=True: gölge ağırlıklar
    (öğrenilmiş W varsa o, yoksa golge_W, yoksa önsel). Geçersiz değer → None."""
    try: j = json.load(open(os.path.join(data_dir, "canli_piyasa.json"), encoding="utf-8"))
    except Exception: j = {}
    if not golge and j.get("kullan") is not True: return None
    W = (j.get("W") or j.get("golge_W") or HARMAN_GOLGE) if golge else j.get("W")
    try:
        out = {}
        for m in PAZARLAR:
            out[m] = {}
            for d in DILIMLER:
                a, b = W[m][str(d)]; a, b = float(a), float(b)
                if not (math.isfinite(a) and math.isfinite(b) and 0 <= a <= 2 and 0 <= b <= 2): return None
                out[m][str(d)] = (a, b)
        return out
    except Exception:
        return None


def harman(Pr, mk, t, W, cur):
    """cur = mevcut toplam gol. CG olasılıkları (probs çıktısı) + piyasa (piyasa() çıktısı) → harmanlı kopya. W None ya da piyasa yoksa Pr aynen döner."""
    if not W or not mk: return Pr
    dl = dilim(t); R = dict(Pr)
    if mk.get("ms"): R["H"], R["D"], R["A"] = _hk([Pr["H"], Pr["D"], Pr["A"]], mk["ms"], *W["ms"][dl])
    if mk.get("ng"): R["nh"], R["none"], R["na"] = _hk([Pr["nh"], Pr["none"], Pr["na"]], mk["ng"], *W["ng"][dl])
    if mk.get("ou"):
        L = float(mk["ou"][0]); po = over(Pr, L, cur)
        if 0 < po < 1: R["ouL"] = L; R["ouP"] = _hk([po, 1 - po], [mk["ou"][1], 1 - mk["ou"][1]], *W["ou"][dl])[0]
    return R
