"""🧮 BULUTOXX pazar motoru (v1, 2026-10-26) — tüm pazarlar TEK skor ızgarasından.

Uygulamanın sunduğu yol (index.html dist() ile aynı): oranlı maçta power marj ayırma → gol beklentisi tablosu (fitMarket) →
gol ölçeği g → ilk yarı / ikinci yarı ayrı Dixon-Coles (İY payı = lig h1, 2Y rho×0,6) → maç sonu = iki yarının birleşimi.
MS 1/X/2'ye mevcut calT/dk kalibrasyonu, 2,5 A/Ü'ye mevcut (ham) yol uygulanır — eski öneri/Altın düzeni aynen korunur.
Diğer pazarlar aynı ızgaradan türetilir; birleşik pazarlar (MS×2,5, MS×KG, İY/MS) satır/sütun toplamları kalibre
marjinallere eşit olacak şekilde orantılı sığdırılır (IPF), böylece "1&U25 + 1&A25 = MS 1" gibi eşitlikler hep tutar.
Pazar bazlı ek kalibrasyon (Platt / sıcaklık) yalnız aylık ileriye dönük sınamada İKİ zaman diliminde de log-kaybı
düşürürse kullanılır.

Çıktılar (veri sözleşmesi, arayüz okumazsa zararsız):
  data/pazar_karne.json            toplu geri test istatistiği (takım adı / ham kaynak verisi yok)
  fixtures.json maç kaydı  "pz"   {kod: olasılık} (PZ_FX: tümleyenler hariç, p(A25)=1−p(U25) vb.), "pzy" "p" (piyasa yolu) | "m" (model yolu), "po" {kod: iddaa oranı}
  predlog.json kaydı       "pz"   PZ_KAYIT sırasıyla binde tamsayı listesi, "pzv" sürüm; sonuçta "rh" (İY skoru)
"""
import json, os, math, collections
from datetime import date, timedelta
import numpy as np

PAZAR_V = 1
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# ------------------------------------------------------------------ katalog (kod → ad, grup) — kodlar kararlıdır
_R = {"1": "1", "X": "X", "2": "2"}
CATALOG = [
    ("1", "MS 1", "MS"), ("X", "MS X", "MS"), ("2", "MS 2", "MS"),
    ("1X", "Çifte şans 1X", "ÇŞ"), ("12", "Çifte şans 12", "ÇŞ"), ("X2", "Çifte şans X2", "ÇŞ"),
    ("U15", "1,5 Üst", "AÜ"), ("A15", "1,5 Alt", "AÜ"), ("U25", "2,5 Üst", "AÜ"), ("A25", "2,5 Alt", "AÜ"),
    ("U35", "3,5 Üst", "AÜ"), ("A35", "3,5 Alt", "AÜ"),
    ("KGV", "KG Var", "KG"), ("KGY", "KG Yok", "KG"),
    ("IY1", "İY 1", "İY"), ("IYX", "İY X", "İY"), ("IY2", "İY 2", "İY"),
    ("IYU05", "İY 0,5 Üst", "İY"), ("IYA05", "İY 0,5 Alt", "İY"), ("IYU15", "İY 1,5 Üst", "İY"), ("IYA15", "İY 1,5 Alt", "İY"),
    ("2Y1", "2Y 1", "2Y"), ("2YX", "2Y X", "2Y"), ("2Y2", "2Y 2", "2Y"),
    ("2YU05", "2Y 0,5 Üst", "2Y"), ("2YA05", "2Y 0,5 Alt", "2Y"), ("2YU15", "2Y 1,5 Üst", "2Y"), ("2YA15", "2Y 1,5 Alt", "2Y"),
] + [(f"IYMS_{a}_{b}", f"İY/MS {a}/{b}", "İYMS") for a in "1X2" for b in "1X2"] + [
    (f"{r}&{s}25", f"MS {r} & 2,5 {'Üst' if s == 'U' else 'Alt'}", "BİRLEŞİK") for r in "1X2" for s in "UA"] + [
    (f"{r}&KG{s}", f"MS {r} & KG {'Var' if s == 'V' else 'Yok'}", "BİRLEŞİK") for r in "1X2" for s in "VY"] + [
    ("DGY1", "Daha gollü yarı: 1. yarı", "YARI"), ("DGYE", "Daha gollü yarı: eşit", "YARI"), ("DGY2", "Daha gollü yarı: 2. yarı", "YARI")]
CODES = [c[0] for c in CATALOG]
NAME = {c[0]: c[1] for c in CATALOG}; GROUP = {c[0]: c[2] for c in CATALOG}
ESKI = ["1", "X", "2", "U25", "A25"]                      # mevcut öneri/Altın havuzu (arayüz kodları "1","X","2","U","A")
ESDEGER = {"U": "U25", "A": "A25"}
# "En olası seçenek" kümeleri (aynı maçta birbirini dışlayan seçenekler)
SETS = {"MS": ["1", "X", "2"], "ÇŞ": ["1X", "12", "X2"], "AÜ15": ["U15", "A15"], "AÜ25": ["U25", "A25"], "AÜ35": ["U35", "A35"],
        "KG": ["KGV", "KGY"], "İY": ["IY1", "IYX", "IY2"], "İYAÜ05": ["IYU05", "IYA05"], "İYAÜ15": ["IYU15", "IYA15"],
        "2Y": ["2Y1", "2YX", "2Y2"], "2YAÜ05": ["2YU05", "2YA05"], "2YAÜ15": ["2YU15", "2YA15"],
        "İYMS": [f"IYMS_{a}_{b}" for a in "1X2" for b in "1X2"], "MS&AÜ": [f"{r}&{s}25" for r in "1X2" for s in "UA"],
        "MS&KG": [f"{r}&KG{s}" for r in "1X2" for s in "VY"], "YARI": ["DGY1", "DGYE", "DGY2"]}
SET_OF = {c: k for k, L in SETS.items() for c in L}
# predlog kaydı: bağımsız temel (tümleyenler ve çifte şans buradan türetilir)
PZ_KAYIT = ["1", "X", "2", "U15", "U25", "U35", "KGV", "IY1", "IYX", "IYU05", "IYU15", "2Y1", "2YX", "2YU05", "2YU15",
            "IYMS_1_1", "IYMS_1_X", "IYMS_1_2", "IYMS_X_1", "IYMS_X_X", "IYMS_X_2", "IYMS_2_1", "IYMS_2_X",
            "1&U25", "X&U25", "2&U25", "1&KGV", "X&KGV", "2&KGV", "DGY1", "DGY2"]
# fixtures.json'da yazılmayan tümleyenler (boyut): p(kod) = 1 − p(eş)
TUMLEYEN = {"A15": "U15", "A25": "U25", "A35": "U35", "KGY": "KGV", "IYA05": "IYU05", "IYA15": "IYU15", "2YA05": "2YU05", "2YA15": "2YU15"}
PZ_FX = [c for c in CODES if c not in TUMLEYEN]
NEEDS_HT = {c for c in CODES if GROUP[c] in ("İY", "2Y", "İYMS", "YARI")}
# kalibre edilebilir marjinaller: ad → (tür, kodlar)
CALS = {"U15": ("ikili", ["U15"]), "U35": ("ikili", ["U35"]), "KGV": ("ikili", ["KGV"]),
        "IY": ("uclu", ["IY1", "IYX", "IY2"]), "IYU05": ("ikili", ["IYU05"]), "IYU15": ("ikili", ["IYU15"]),
        "2Y": ("uclu", ["2Y1", "2YX", "2Y2"]), "2YU05": ("ikili", ["2YU05"]), "2YU15": ("ikili", ["2YU15"]),
        "YARI": ("uclu", ["DGY1", "DGYE", "DGY2"])}

def full(pz):
    """Kayıt temelinden (veya eksik sözlükten) tüm kodları türet."""
    p = dict(pz)
    g = lambda k: p.get(k)
    for a, b in (("U15", "A15"), ("U25", "A25"), ("U35", "A35"), ("KGV", "KGY"), ("IYU05", "IYA05"), ("IYU15", "IYA15"), ("2YU05", "2YA05"), ("2YU15", "2YA15")):
        if g(a) is not None and g(b) is None: p[b] = 1 - p[a]
    if all(g(k) is not None for k in "1X2"):
        p.setdefault("1X", p["1"] + p["X"]); p.setdefault("12", p["1"] + p["2"]); p.setdefault("X2", p["X"] + p["2"])
        for r in "1X2":
            if g(f"{r}&U25") is not None: p.setdefault(f"{r}&A25", p[r] - p[f"{r}&U25"])
            if g(f"{r}&KGV") is not None: p.setdefault(f"{r}&KGY", p[r] - p[f"{r}&KGV"])
    if all(g(f"IYMS_{a}_{b}") is not None for a, b in ("11", "1X", "12", "X1", "XX", "X2", "21", "2X")):
        p.setdefault("IYMS_2_2", 1 - sum(p[f"IYMS_{a}_{b}"] for a, b in ("11", "1X", "12", "X1", "XX", "X2", "21", "2X")))
    if g("DGY1") is not None and g("DGY2") is not None: p.setdefault("DGYE", 1 - p["DGY1"] - p["DGY2"])
    return {k: max(0.0, min(1.0, v)) for k, v in p.items()}

# ------------------------------------------------------------------ sonuç (tuttu mu?)
def outcome(code, ft, ht):
    """ft, ht: [ev, dep] (ht yoksa None). Dönüş True/False, belirlenemezse None."""
    a, b = ft; R = lambda x, y: "1" if x > y else "X" if x == y else "2"
    if code in ("1", "X", "2"): return R(a, b) == code
    if code in ("1X", "12", "X2"): return R(a, b) in code
    if code[0] in "UA" and code[1:].isdigit():
        line = int(code[1:]) / 10; o = a + b > line; return o if code[0] == "U" else not o
    if code == "KGV": return a > 0 and b > 0
    if code == "KGY": return not (a > 0 and b > 0)
    if "&" in code:
        r, s = code.split("&")
        if R(a, b) != r: return False
        if s == "U25": return a + b > 2
        if s == "A25": return a + b <= 2
        return (a > 0 and b > 0) == (s == "KGV")
    if ht is None or len(ht) != 2 or ht[0] is None: return None
    c, d = ht; e, f = a - c, b - d
    if e < 0 or f < 0: return None
    if code in ("IY1", "IYX", "IY2"): return R(c, d) == code[2]
    if code in ("2Y1", "2YX", "2Y2"): return R(e, f) == code[2]
    if code.startswith("IYU") or code.startswith("IYA"):
        line = int(code[3:]) / 10; o = c + d > line; return o if code[2] == "U" else not o
    if code.startswith("2YU") or code.startswith("2YA"):
        line = int(code[3:]) / 10; o = e + f > line; return o if code[2] == "U" else not o
    if code.startswith("IYMS_"): _, x, y = code.split("_"); return R(c, d) == x and R(a, b) == y
    if code == "DGY1": return c + d > e + f
    if code == "DGY2": return e + f > c + d
    if code == "DGYE": return c + d == e + f
    return None

# ------------------------------------------------------------------ ızgara → olasılıklar
def _dc(l1, l2, rho, K=7):
    k = np.arange(K + 1); lf = np.array([math.lgamma(i + 1) for i in k])
    a = np.exp(-l1[:, None] + k[None] * np.log(np.maximum(l1[:, None], 1e-9)) - lf); b = np.exp(-l2[:, None] + k[None] * np.log(np.maximum(l2[:, None], 1e-9)) - lf)
    g = a[:, :, None] * b[:, None, :]
    g[:, 0, 0] *= np.maximum(1 - l1 * l2 * rho, 0); g[:, 0, 1] *= 1 + l1 * rho; g[:, 1, 0] *= 1 + l2 * rho; g[:, 1, 1] *= 1 - rho
    g = np.maximum(g, 0); return g / g.sum((1, 2), keepdims=True)

def _cal3(p, T, dk):
    q = np.maximum(p, 1e-12) ** T; q /= q.sum(1, keepdims=True); q[:, 1] *= dk; return q / q.sum(1, keepdims=True)

def _rake(T, r, c, it=30):
    """IPF: T (n,R,C) tablosunu satır toplamı r (n,R), sütun toplamı c (n,C) olacak şekilde ölçekle."""
    T = np.maximum(T, 1e-12)
    for _ in range(it):
        T = T * (r / T.sum(2))[:, :, None]
        T = T * (c / T.sum(1))[:, None, :]
    return T

def _logit(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p) - np.log(1 - p)
def _sig(z): return 1 / (1 + np.exp(-z))

def raw_marginals(lh, la, s, P):
    """Kalibrasyonsuz ızgara olasılıkları + birleşik tablolar. lh, la: maç sonu gol beklentisi (kıstırılmamış), s: İY payı."""
    rho = P.get("rho", -0.06); g = P.get("gscale", 1.0)
    lh = np.clip(np.asarray(lh, float), .15, 4.5) * g; la = np.clip(np.asarray(la, float), .1, 4) * g; s = np.broadcast_to(np.asarray(s, float), lh.shape)
    g1 = _dc(lh * s, la * s, rho); g2 = _dc(lh * (1 - s), la * (1 - s), rho * .6)
    n = len(lh)
    ft = np.zeros((n, 15, 15))
    for a in range(8):
        for b in range(8): ft[:, a:a + 8, b:b + 8] += g1[:, a, b, None, None] * g2
    i, j = np.meshgrid(np.arange(15), np.arange(15), indexing="ij"); tot = i + j
    rm = [(i > j), (i == j), (i < j)]
    M = {}
    M["ms0"] = np.stack([(ft * m).sum((1, 2)) for m in rm], 1)
    for L, k in ((1, "U15"), (2, "U25"), (3, "U35")): M[k] = (ft * (tot > L)).sum((1, 2))
    M["KGV"] = ft[:, 1:, 1:].sum((1, 2))
    M["msou"] = np.stack([np.stack([(ft * m * (tot <= 2)).sum((1, 2)), (ft * m * (tot > 2)).sum((1, 2))], 1) for m in rm], 1)   # (n,3,[A,Ü])
    M["mskg"] = np.stack([np.stack([(ft * m * ((i == 0) | (j == 0))).sum((1, 2)), (ft[:, 1:, 1:] * m[1:, 1:]).sum((1, 2))], 1) for m in rm], 1)   # (n,3,[Yok,Var])
    a8, b8 = np.meshgrid(np.arange(8), np.arange(8), indexing="ij")
    for G, pre in ((g1, "IY"), (g2, "2Y")):
        M[pre] = np.stack([(G * (a8 > b8)).sum((1, 2)), (G * (a8 == b8)).sum((1, 2)), (G * (a8 < b8)).sum((1, 2))], 1)
        M[pre + "U05"] = 1 - G[:, 0, 0]; M[pre + "U15"] = (G * ((a8 + b8) > 1)).sum((1, 2))
    T1 = np.zeros((n, 15)); T2 = np.zeros((n, 15)); D1 = np.zeros((n, 15)); D2 = np.zeros((n, 15))
    for a in range(8):
        for b in range(8):
            T1[:, a + b] += g1[:, a, b]; T2[:, a + b] += g2[:, a, b]; D1[:, a - b + 7] += g1[:, a, b]; D2[:, a - b + 7] += g2[:, a, b]
    x, y = np.meshgrid(np.arange(15), np.arange(15), indexing="ij")
    JT = T1[:, :, None] * T2[:, None, :]
    M["YARI"] = np.stack([(JT * (x > y)).sum((1, 2)), (JT * (x == y)).sum((1, 2)), (JT * (x < y)).sum((1, 2))], 1)
    JD = D1[:, :, None] * D2[:, None, :]; d1 = x - 7; ds = d1 + (y - 7)
    r1 = [(d1 > 0), (d1 == 0), (d1 < 0)]; r2 = [(ds > 0), (ds == 0), (ds < 0)]
    M["iyms"] = np.stack([np.stack([(JD * (u & v)).sum((1, 2)) for v in r2], 1) for u in r1], 1)   # (n, İY, MS)
    return M

def apply_cal(M, P, kal=None, kp=None, ko=None):
    """Ham marjinallere mevcut MS kalibrasyonu (calT/dk) + kabul edilmiş pazar kalibrasyonları; birleşikler IPF ile.
    kp/ko: robot konseyi MS / 2,5 Üst olasılığı (arayüz recOf ile aynı öncelik). Dönüş: {kod: dizi}."""
    kal = kal or {}
    q = _cal3(M["ms0"], P.get("calT", 1.0), P.get("dk", 1.0))
    if kp is not None: q = np.where(np.isnan(kp).any(1, keepdims=True), q, kp)
    u25 = M["U25"] if ko is None else np.where(np.isnan(ko), M["U25"], ko)
    out = {"1": q[:, 0], "X": q[:, 1], "2": q[:, 2], "U25": u25}
    for nm, (tp, codes) in CALS.items():
        src = {"U15": M["U15"], "U35": M["U35"], "KGV": M["KGV"], "IY": M["IY"], "IYU05": M["IYU05"], "IYU15": M["IYU15"],
               "2Y": M["2Y"], "2YU05": M["2YU05"], "2YU15": M["2YU15"], "YARI": M["YARI"]}[nm]
        c = kal.get(nm)
        if tp == "ikili":
            v = _sig(c["a"] + c["b"] * _logit(src)) if c else src
            out[codes[0]] = v
        else:
            v = _cal3(src, c["T"], c["dk"]) if c else src
            for k_, col in zip(codes, v.T): out[k_] = col
    # tutarlılık: 1,5 Üst ≥ 2,5 Üst ≥ 3,5 Üst, İY 0,5 Üst ≥ İY 1,5 Üst
    out["U15"] = np.maximum(out["U15"], out["U25"]); out["U35"] = np.minimum(out["U35"], out["U25"])
    for p_ in ("IY", "2Y"): out[p_ + "U15"] = np.minimum(out[p_ + "U15"], out[p_ + "U05"])
    for a, b in (("U15", "A15"), ("U25", "A25"), ("U35", "A35"), ("KGV", "KGY"), ("IYU05", "IYA05"), ("IYU15", "IYA15"), ("2YU05", "2YA05"), ("2YU15", "2YA15")):
        out[b] = 1 - out[a]
    out["1X"] = q[:, 0] + q[:, 1]; out["12"] = q[:, 0] + q[:, 2]; out["X2"] = q[:, 1] + q[:, 2]
    T = _rake(M["msou"], q, np.stack([1 - u25, u25], 1))
    K = _rake(M["mskg"], q, np.stack([out["KGY"], out["KGV"]], 1))
    I = _rake(M["iyms"], np.stack([out["IY1"], out["IYX"], out["IY2"]], 1), q)
    for ri, r in enumerate("1X2"):
        out[f"{r}&A25"] = T[:, ri, 0]; out[f"{r}&U25"] = T[:, ri, 1]; out[f"{r}&KGY"] = K[:, ri, 0]; out[f"{r}&KGV"] = K[:, ri, 1]
        for ci, c_ in enumerate("1X2"): out[f"IYMS_{r}_{c_}"] = I[:, ri, ci]
    return {k: np.clip(out[k], 0, 1) for k in CODES}

# ------------------------------------------------------------------ kalibratörler
def fit_platt(p, y, lam=30.0, it=25):
    """Ridge (0,1) yönüne çekilen Platt: logit(q) = a + b·logit(p). Newton."""
    x = _logit(p); y = y.astype(float); w = np.array([0.0, 1.0])
    for _ in range(it):
        z = w[0] + w[1] * x; q = _sig(z); r = q * (1 - q)
        gr = np.array([(q - y).sum(), ((q - y) * x).sum()]) + lam * (w - np.array([0, 1]))
        H = np.array([[r.sum(), (r * x).sum()], [(r * x).sum(), (r * x * x).sum()]]) + lam * np.eye(2)
        w = w - np.linalg.solve(H, gr)
    return {"a": round(float(w[0]), 4), "b": round(float(w[1]), 4)}

def fit_temp(p, yi):
    """Üçlü pazar: q ∝ p^T, orta seçenek × dk (MS kalibrasyonuyla aynı biçim). Izgara araması."""
    best = (9e9, 1.0, 1.0); idx = np.arange(len(yi))
    for T in np.arange(0.8, 1.31, 0.05):
        for dk in np.arange(0.85, 1.21, 0.03):
            q = _cal3(p, T, dk); ll = -np.log(np.maximum(q[idx, yi], 1e-9)).mean()
            if ll < best[0]: best = (ll, float(T), float(dk))
    return {"T": round(best[1], 2), "dk": round(best[2], 2)}

def fit_cals(M, Y, mask):
    """M: ham marjinaller, Y: {kod: 0/1/nan}, mask: eğitim satırları. Dönüş: aday kalibratörler."""
    out = {}
    for nm, (tp, codes) in CALS.items():
        if tp == "ikili":
            y = Y[codes[0]]; m = mask & ~np.isnan(y)
            if m.sum() >= 800: out[nm] = fit_platt(M[codes[0]][m], y[m])
        else:
            key = {"IY": "IY", "2Y": "2Y", "YARI": "YARI"}[nm]
            ys = np.stack([Y[c] for c in codes], 1); m = mask & ~np.isnan(ys).any(1)
            if m.sum() >= 800: out[nm] = fit_temp(M[key][m], ys[m].argmax(1))
    return out

# ------------------------------------------------------------------ geri test verisi
def h1_forward(rows, h1d):
    """Her maç için lig İY payı — yalnız o tarihten ÖNCEKİ maçlarla (arayüz fitLeague formülü: (İY gol + h1·60)/(MS gol + 60))."""
    acc = collections.defaultdict(lambda: [0.0, 0.0]); out = np.zeros(len(rows)); pend = []; last = None
    order = sorted(range(len(rows)), key=lambda t: rows[t]["d"])
    for t in order:
        r = rows[t]
        if r["d"] != last:
            for lg, a, b in pend: acc[lg][0] += a; acc[lg][1] += b
            pend = []; last = r["d"]
        g1, g = acc[r["lg"]]; out[t] = min(max((g1 + h1d * 60) / (g + 60), .36), .52)
        pend.append((r["lg"], sum(r["ht"]), sum(r["ft"])))
    return out

def h1_league(season, h1d):
    """Canlı kullanım: arayüzle aynı (sezon dosyasındaki tüm İY'li maçlar)."""
    out = {}
    for lg, d in season.items():
        if d.get("cup"): continue
        g1 = g = 0
        for m in d.get("matches", []):
            if m.get("ht") and m.get("ft"): g1 += sum(m["ht"]); g += sum(m["ft"])
        out[lg] = min(max((g1 + h1d * 60) / (g + 60), .36), .52)
    return out

def hist_rows(season):
    rows = []
    for lg, d in season.items():
        if d.get("cup") or d.get("src") == "espn": continue
        for m in d.get("matches", []):
            ht = m.get("ht")
            if m.get("odds") and m.get("ou") and ht and len(ht) == 2 and ht[0] is not None and m["ft"][0] >= ht[0] and m["ft"][1] >= ht[1]:
                rows.append({"lg": lg, "d": m["d"], "ft": m["ft"], "ht": ht, "odds": m["odds"], "ou": m["ou"]})
    rows.sort(key=lambda r: r["d"])
    return rows

def labels(rows):
    return {c: np.array([np.nan if (v := outcome(c, r["ft"], r["ht"])) is None else float(v) for r in rows]) for c in CODES}

# ------------------------------------------------------------------ ölçütler
def _bins(p, y, edges=np.linspace(0, 1, 11)):
    o = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & ((p < hi) if hi < 1 else (p <= hi))
        if m.sum(): o.append({"aralik": f"{lo:.1f}-{hi:.1f}", "n": int(m.sum()), "tahmin": round(float(p[m].mean()), 4), "gercek": round(float(y[m].mean()), 4)})
    return o

def stats(p, y, base=None):
    m = ~np.isnan(y); p, y = np.clip(p[m], 1e-6, 1 - 1e-6), y[m]
    if not len(p): return None
    B = _bins(p, y); n = len(p)
    ece = sum(b["n"] * abs(b["tahmin"] - b["gercek"]) for b in B) / n
    hi = [b for b in B if b["tahmin"] >= .55 and b["n"] >= 30]; nh = sum(b["n"] for b in hi)
    ece55 = sum(b["n"] * abs(b["tahmin"] - b["gercek"]) for b in hi) / nh if nh else None
    br = float(np.mean((p - y) ** 2)); r = {"n": n, "logloss": round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 5), "brier": round(br, 5),
         "ece": round(ece, 4), "ece55": round(ece55, 4) if ece55 is not None else None, "n55": nh,
         "ort_tahmin": round(float(p.mean()), 4), "ort_gercek": round(float(y.mean()), 4)}
    if base is not None:
        b0 = float(np.mean((base - y) ** 2)); r["brier_beceri"] = round(1 - br / b0, 4) if b0 > 0 else None
    return r, B

def set_hits(PZ, Y, idx):
    """Her kümede en olası seçenek: kod başına seçilme ve tutma; küme başına isabet."""
    per = {}; grp = {}
    for k, L in SETS.items():
        P_ = np.stack([PZ[c][idx] for c in L], 1); Yk = np.stack([Y[c][idx] for c in L], 1)
        ok = ~np.isnan(Yk).any(1); a = P_.argmax(1); hit = Yk[np.arange(len(idx)), a]
        grp[k] = {"n": int(ok.sum()), "isabet": round(float(np.nanmean(hit[ok])), 4) if ok.any() else None}
        for t, c in enumerate(L):
            m = ok & (a == t)
            per[c] = {"secilme": int(m.sum()), "isabet": round(float(hit[m].mean()), 4) if m.any() else None}
    return per, grp

# ------------------------------------------------------------------ öneri / Altın sınaması
def _picks(PZ, rows, idx, pool, odds_of, need_odds_for_old=True, min_fair=None):
    """recOf ile aynı: havuzdaki en yüksek olasılık. Eski kodlar (oranlı) + yeni kodlar (oranı yoksa adil oran 1/p).
    Dönüş: (gün, kod, p, oran|None, tuttu)."""
    out = []
    for t in idx:
        best = None
        for c in pool:
            p = PZ[c][t]
            if c not in ESKI and min_fair and 1 / max(p, 1e-9) < min_fair: continue
            if best is None or p > best[1]: best = (c, p)
        c, p = best; o = odds_of(rows[t], c)
        y = outcome(c, rows[t]["ft"], rows[t]["ht"])
        out.append((rows[t]["d"], c, float(p), o, bool(y)))
    return out

def _hist_odds(r, c):
    if c in ("1", "X", "2"): return r["odds"]["1X2".index(c)]
    if c == "U25": return r["ou"][0]
    if c == "A25": return r["ou"][1]
    return None

def tier_stats(PK):
    if not PK: return {}
    pp = np.array([x[2] for x in PK]); yy = np.array([x[4] for x in PK], float)
    o = {"n": len(PK), "isabet": round(float(yy.mean()), 4), "brier": round(float(np.mean((pp - yy) ** 2)), 5)}
    for lb, th in (("oneri58", .58), ("guclu70", .70)):
        m = pp >= th; o[lb] = {"n": int(m.sum()), "isabet": round(float(yy[m].mean()), 4) if m.any() else None,
                                "ort_p": round(float(pp[m].mean()), 4) if m.any() else None}
    fo = np.array([1 / max(x[2], 1e-9) for x in PK]); o["ort_adil_oran"] = round(float(fo.mean()), 3)
    o["dagilim"] = dict(collections.Counter(x[1] for x in PK).most_common(8))
    return o

def gold_stats(PK, thr=.78, omin=1.15, omax=2.0, per=3):
    by = collections.defaultdict(list)
    for x in PK:
        if x[3] is not None and x[2] >= thr and omin <= x[3] <= omax: by[x[0]].append(x)
    G = [x for L in by.values() for x in sorted(L, key=lambda x: -x[2])[:per]]
    if not G: return {"n": 0, "isabet": None}
    return {"n": len(G), "isabet": round(float(np.mean([x[4] for x in G])), 4), "ort_oran": round(float(np.mean([x[3] for x in G])), 3),
            "dagilim": dict(collections.Counter(x[1] for x in G).most_common(6))}

# ------------------------------------------------------------------ karne (geri test)
def karne(season, P, U, log=print):
    """Aylık ileriye dönük sınama. U: update modülü (ui_market_lam için)."""
    import time; t0 = time.time()
    rows = hist_rows(season)
    if len(rows) < 3000: return None
    rho = P.get("rho", -0.06)
    lam = np.zeros((len(rows), 2))
    for s_ in range(0, len(rows), 3000):
        ch = rows[s_:s_ + 3000]; lam[s_:s_ + len(ch)] = U.ui_market_lam([r["odds"] for r in ch], [r["ou"] for r in ch], rho)
    s = h1_forward(rows, P.get("h1", .4442))
    M = raw_marginals(lam[:, 0], lam[:, 1], s, P); Y = labels(rows)
    months = np.array([r["d"][:7] for r in rows]); um = sorted(set(months))
    test_m = [m_ for m_ in um if (months < m_).sum() >= 2500]
    if len(test_m) < 4: return None
    te = np.isin(months, test_m); tidx = np.where(te)[0]
    half = sorted(rows[t]["d"] for t in tidx)[len(tidx) // 2]
    sl = {"A": np.array([t for t in tidx if rows[t]["d"] < half]), "B": np.array([t for t in tidx if rows[t]["d"] >= half])}
    # 1) aylık: kalibratör yalnız önceki aylarla
    monthly = {}
    for m_ in test_m: monthly[m_] = fit_cals(M, Y, months < m_)
    RAW = apply_cal(M, P, None)
    def wf(accept):
        out = {c: RAW[c].copy() for c in CODES}
        for m_ in test_m:
            ix = np.where(months == m_)[0]
            Mi = {k: v[ix] for k, v in M.items()}
            kal = {k: v for k, v in monthly[m_].items() if k in accept}
            Pm = apply_cal(Mi, P, kal)
            for c in CODES: out[c][ix] = Pm[c]
        return out
    CALW = wf(set(CALS))
    # 2) kabul: iki dilimde de log-kayıp düşmeli (küme log-kaybı)
    kabul = {}; kal_rap = {}
    for nm, (tp, codes) in CALS.items():
        r_ = {}
        for k_, ix in sl.items():
            def ll(PZ):
                if tp == "ikili":
                    y = Y[codes[0]][ix]; m = ~np.isnan(y); p = np.clip(PZ[codes[0]][ix][m], 1e-6, 1 - 1e-6); y = y[m]
                    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
                ys = np.stack([Y[c][ix] for c in codes], 1); m = ~np.isnan(ys).any(1)
                pp = np.stack([PZ[c][ix] for c in codes], 1)[m]; yi = ys[m].argmax(1)
                return float(-np.log(np.maximum(pp[np.arange(len(yi)), yi], 1e-9)).mean())
            r_[k_] = {"ham": round(ll(RAW), 5), "kalibre": round(ll(CALW), 5)}
        ok = all(v["kalibre"] < v["ham"] - 1e-4 for v in r_.values())
        kabul[nm] = ok; kal_rap[nm] = dict(r_, kabul=ok, tur="platt" if tp == "ikili" else "sicaklik")
    acc = {k for k, v in kabul.items() if v}
    SRV = wf(acc)
    final_kal = {k: v for k, v in fit_cals(M, Y, np.ones(len(rows), bool)).items() if k in acc}
    # 3) pazar istatistikleri
    base_tr = {}
    pz = {}
    for c in CODES:
        tot = stats(SRV[c][tidx], Y[c][tidx])
        if not tot: continue
        st, B = tot
        sn = {}
        for k_, ix in sl.items():
            # temel tahmin: o dilimden önceki tüm maçların gerçekleşme oranı (beceri ölçüsü)
            prior = Y[c][np.array([t for t in range(len(rows)) if rows[t]["d"] < rows[ix[0]]["d"]])]
            br = np.full(len(ix), np.nanmean(prior) if np.isfinite(np.nanmean(prior)) else .5)
            r2 = stats(SRV[c][ix], Y[c][ix], base=br)
            if r2: sn[k_] = dict(r2[0], aralik=f"{rows[ix[0]]['d']}…{rows[ix[-1]]['d']}")
        pz[c] = {"ad": NAME[c], "grup": GROUP[c], "n": st["n"], "logloss": st["logloss"], "brier": st["brier"], "ece": st["ece"], "ece55": st["ece55"],
                 "ort_tahmin": st["ort_tahmin"], "ort_gercek": st["ort_gercek"], "kalibrasyon": B, "sinama": sn}
    per, grp = set_hits(SRV, Y, tidx)
    perA, grpA = set_hits(SRV, Y, sl["A"]); perB, grpB = set_hits(SRV, Y, sl["B"])
    for c in pz:
        pz[c]["isabet"] = per[c]["isabet"]; pz[c]["secilme"] = per[c]["secilme"]
        for k_, pp_ in (("A", perA), ("B", perB)):
            if k_ in pz[c]["sinama"]: pz[c]["sinama"][k_]["isabet"] = pp_[c]["isabet"]; pz[c]["sinama"][k_]["secilme"] = pp_[c]["secilme"]
    # 4) uygunluk: iki dilimde de iyi kalibre (ECE ≤ 0,02; p≥0,55 bölgesinde sapma ≤ 0,03) ve bilgi taşıyor (Brier becerisi > 0)
    def uygun(c):
        if c in ESKI: return True
        S = pz.get(c, {}).get("sinama", {})
        if pz.get(c, {}).get("n", 0) < 2000 or len(S) < 2: return False
        for v in S.values():
            if v["ece"] > 0.02: return False
            if v.get("ece55") is not None and v["n55"] >= 100 and v["ece55"] > 0.03: return False
            if not (v.get("brier_beceri") or 0) >= 0.002: return False
        return True
    for c in pz: pz[c]["oneriye_uygun"] = bool(uygun(c))
    # 5) öneri ve Altın: eski havuz ile yeni havuz yan yana (aynı sınama maçları, iki dilim)
    pool0 = ESKI; pool1 = ESKI + [c for c in CODES if c not in ESKI and pz.get(c, {}).get("oneriye_uygun")]
    pool2 = ESKI + [c for c in pool1 if c not in ESKI and GROUP[c] not in ("ÇŞ",)]
    cmp_ = {}
    for nm_, pool, mf in (("eski", pool0, None), ("yeni_tum", pool1, 1.15), ("yeni_cs_haric", pool2, 1.15)):
        r_ = {}
        for k_, ix in (("tum", tidx), ("A", sl["A"]), ("B", sl["B"])):
            PK = _picks(SRV, rows, ix, pool, _hist_odds, min_fair=mf)
            r_[k_] = {"oneri": tier_stats(PK), "altin": gold_stats(PK)}
        cmp_[nm_] = dict(r_, havuz=pool)
    # Vekil oranlı Altın sınaması: yeni kodlara iddaa benzeri marjla oran (o = 1/(p + 0,07)) verilirse Altın düşer mi?
    def proxy(r, c, p):
        o = _hist_odds(r, c); return o if o is not None or c in ESKI else round(1 / (p + 0.07), 2)
    vek = {}
    for k_, ix in (("tum", tidx), ("A", sl["A"]), ("B", sl["B"])):
        PK = [(d, c, p, proxy(rows[t], c, p), y) for t, (d, c, p, o, y) in zip(ix, _picks(SRV, rows, ix, pool1, _hist_odds, min_fair=1.15))]
        vek[k_] = gold_stats(PK)
    cmp_["altin_vekil_oranli_yeni"] = vek
    g_eski = [cmp_["eski"][k]["altin"]["isabet"] or 0 for k in ("A", "B")]
    g_vek = [vek[k]["isabet"] if vek[k]["n"] >= 30 else None for k in ("A", "B")]
    altin_yeni_ok = all(v is not None and v >= e - 1e-9 for v, e in zip(g_vek, g_eski))
    # Öneri kararı: yeni havuzun güçlü (≥%70) ve öneri (≥%58) isabeti iki dilimde de eskiden düşük değilse
    def nodrop(a, b):
        for k in ("A", "B"):
            for t_ in ("oneri58", "guclu70"):
                x, y_ = a[k]["oneri"][t_]["isabet"], b[k]["oneri"][t_]["isabet"]
                if x is None or y_ is None or x < y_ - 0.005: return False
        return True
    oneri_karar = {nm_: nodrop(cmp_[nm_], cmp_["eski"]) for nm_ in ("yeni_tum", "yeni_cs_haric")}
    # Skorla uyumlu birleşik seçim (arayüzdeki tutarlı skor: en olası MS sonucu + 2,5 yönü → örn. 2-1 ⇒ "1&U25")
    sb = {}
    for k_, ix in (("tum", tidx), ("A", sl["A"]), ("B", sl["B"])):
        q3 = np.stack([SRV[c][ix] for c in "1X2"], 1); o = q3.argmax(1); ov = SRV["U25"][ix] >= .5
        cc = [f"{'1X2'[a]}&{'U' if b else 'A'}25" for a, b in zip(o, ov)]
        pp = np.array([SRV[c][t] for c, t in zip(cc, ix)]); yy = np.array([Y[c][t] for c, t in zip(cc, ix)])
        r2 = stats(pp, yy)
        sb[k_] = dict({kk: r2[0][kk] for kk in ("n", "logloss", "brier", "ece", "ort_tahmin", "ort_gercek")}, isabet=round(float(yy.mean()), 4),
                      kalibrasyon=r2[1], dagilim=dict(collections.Counter(cc).most_common(6)))
    for c in pz:
        # Altın: oranı olan (iddaa'da açılan) ve kalibrasyonu kanıtlı pazar; ayrıca vekil sınamada Altın isabeti düşmemeli
        # ve canlı arşivde (predlog, gerçek oran) ≥100 Altın benzeri seçimde isabet eski Altın'dan düşük olmamalı.
        pz[c]["altina_uygun"] = bool(c in ESKI)
    out = {"v": PAZAR_V, "donem": f"{rows[tidx[0]]['d']}…{rows[tidx[-1]]['d']}", "n_mac": int(len(tidx)), "n_egitim_ilk": int((~te).sum()),
           "yontem": "aylık ileriye dönük: her ay yalnız önceki aylarla kalibratör; olasılıklar kapanış oranlarından (uygulamanın sunduğu yol); "
                     "lig İY payı yalnız önceki maçlardan; MS/2,5 mevcut ayarlarla",
           "dilimler": {k: f"{rows[ix[0]]['d']}…{rows[ix[-1]]['d']}" for k, ix in sl.items()},
           "esdeger": ESDEGER, "eski_kodlar": ESKI, "kayit_sirasi": PZ_KAYIT, "tumleyen": TUMLEYEN, "fikstur_kodlari": PZ_FX,
           "katalog": [{"kod": c, "ad": NAME[c], "grup": GROUP[c], "kume": SET_OF[c], "iy_gerekir": c in NEEDS_HT} for c in CODES],
           "kalibrator": final_kal, "kalibrator_sinama": kal_rap, "gruplar": {k: dict(v, A=grpA[k], B=grpB[k]) for k, v in grp.items()},
           "oneri_karsilastirma": cmp_, "havuz_isabet_dusmedi": oneri_karar, "altin_vekil_karar": altin_yeni_ok, "skor_birlesik": sb,
           "oneri_kurali": {
               "varsayilan": {"havuz": ESKI, "kural": "değişmedi: oranlı seçenekler (MS 1/X/2, 2,5 A/Ü) içinde en yüksek olasılık (recOf)",
                              "neden": "Birleşik / İY / 2Y sonuç pazarları hiçbir maçta havuzun en olası seçeneği olamaz (1&U25 ≤ MS 1); "
                                       "güvenli çizgiler (2Y 0,5 Üst, Çifte şans, 3,5 Alt, 1,5 Üst) havuza girince önerilerin tamamı ~1,24 adil oranlı "
                                       "güvenli seçeneğe dönüyor ve Altın adayları azalıyor (oranları yok). Varsayılan öneri bu yüzden korunur."},
               "genis": {"havuz": pool1, "min_adil_oran": 1.15, "kural": "isteğe bağlı 'en güvenli seçenek': öneriye uygun tüm pazarlar içinde en yüksek olasılık",
                         "sinama": {k: cmp_["yeni_tum"][k]["oneri"] for k in ("tum", "A", "B")}},
               "skor_birlesik": {"kural": "en olası MS sonucu & (2,5 Üst ≥ 0,5 ? U25 : A25) — gösterilen tutarlı skorla aynı yön", "sinama": sb},
               "altin": {"havuz": ESKI, "kural": "değişmedi; yeni pazar yalnız altina_uygun=true ve gerçek iddaa oranı (po) varsa", "vekil_sinama_gecti": altin_yeni_ok}},
           "kurallar": {"oneriye_uygun": "n ≥ 2000; iki dilimde de ECE ≤ 0,02, p≥0,55 kovalarında sapma ≤ 0,03 (≥100 maç), Brier becerisi ≥ 0,002",
                        "altina_uygun": "eski kodlar; yeni pazar için gerçek oran (po) + canlı arşivde ≥100 Altın benzeri seçimde isabet ≥ eski Altın",
                        "altin": {"p_min": 0.78, "oran": [1.15, 2.0], "gunde": 3}},
           "pazarlar": pz, "sure_sn": round(time.time() - t0, 1)}
    log(f"Pazar karnesi: {len(tidx)} sınama maçı, kabul edilen kalibratör: {sorted(acc)}, öneriye uygun: "
        f"{[c for c in pz if pz[c]['oneriye_uygun'] and c not in ESKI]}, {out['sure_sn']} sn")
    return out

# ------------------------------------------------------------------ canlı karne (kilitli günlükten)
def live_scores(plog, karne_):
    """predlog'daki pz kayıtlarını sonuçla puanla; Altın kapısını (gerçek oranla) burada açar."""
    es = [e for e in plog if e.get("pz") and e.get("r") and e.get("pzv") == PAZAR_V]
    if not es: return {"n": 0}
    rows = []
    for e in es:
        p = full(dict(zip(PZ_KAYIT, [x / 1000 for x in e["pz"]])))
        rows.append((e, p))
    out = {"n": len(rows), "pazarlar": {}}
    for c in CODES:
        ps, ys = [], []
        for e, p in rows:
            y = outcome(c, e["r"], e.get("rh"))
            if y is None or c not in p: continue
            ps.append(p[c]); ys.append(float(y))
        if len(ps) >= 30:
            r = stats(np.array(ps), np.array(ys))
            if r: out["pazarlar"][c] = {k: r[0][k] for k in ("n", "logloss", "brier", "ece", "ort_tahmin", "ort_gercek")}
    # Altın kapısı: yeni kod, gerçek oranla (po) p ≥ .78 ve oran 1,15–2,00 seçimlerinde ≥100 kayıt, isabet ≥ eski Altın
    ref = None
    try: ref = karne_["oneri_karsilastirma"]["eski"]["tum"]["altin"]["isabet"]
    except Exception: pass
    gate = {}
    for c in CODES:
        if c in ESKI: continue
        hits = []
        for e, p in rows:
            o = (e.get("po") or {}).get(c)
            if o and p.get(c, 0) >= .78 and 1.15 <= o <= 2.0:
                y = outcome(c, e["r"], e.get("rh"))
                if y is not None: hits.append(y)
        if hits: gate[c] = {"n": len(hits), "isabet": round(float(np.mean(hits)), 4), "acik": bool(len(hits) >= 100 and ref is not None and np.mean(hits) >= ref)}
    out["altin_kapisi"] = gate
    return out

# ------------------------------------------------------------------ yaklaşan maçlar
def enrich(fx, season, P, karne_, fits=None, today=None, U=None):
    """fixtures kayıtlarına pz/pzy/po ekle. Eski alanlara dokunmaz. Dönüş: {(lg,d,h,a): {kod: p}}."""
    kal = (karne_ or {}).get("kalibrator") or {}
    h1L = h1_league(season, P.get("h1", .4442)); h1d = P.get("h1", .4442)
    teams = {lg: {t for m in d.get("matches", []) for t in (m["h"], m["a"])} for lg, d in season.items() if not d.get("cup")}
    rho = P.get("rho", -0.06)
    mk = [f for f in fx if f.get("odds") and len(f["odds"]) == 3]
    md = [f for f in fx if not (f.get("odds") and len(f["odds"]) == 3)]
    res = {}
    def run(L, lam, kind):
        if not L: return
        # arayüz: iki takım da aynı ligin modelindeyse lig İY payı (FIT[lg].h1), değilse genel h1
        s = np.array([h1L.get(f["lg"], h1d) if f["h"] in teams.get(f["lg"], ()) and f["a"] in teams.get(f["lg"], ()) else h1d for f in L])
        M = raw_marginals(lam[:, 0], lam[:, 1], s, P)
        kp = np.array([f["kp"] if isinstance(f.get("kp"), list) and len(f["kp"]) == 3 else [np.nan] * 3 for f in L], float)
        ko = np.array([f["ko"] if isinstance(f.get("ko"), (int, float)) else np.nan for f in L], float)
        PZ = apply_cal(M, P, kal, kp=kp if not np.isnan(kp).all() else None, ko=ko if not np.isnan(ko).all() else None)
        for t, f in enumerate(L):
            f["pz"] = {c: round(float(PZ[c][t]), 3) for c in PZ_FX}; f["pzy"] = kind
            res[(f["lg"], f["d"], f["h"], f["a"])] = {c: float(PZ[c][t]) for c in CODES}
    if mk:
        lam = U.ui_market_lam([f["odds"] for f in mk], [f["ou"] if f.get("ou") and len(f["ou"]) == 2 else None for f in mk], rho)
        run(mk, lam, "p")
    if md and fits is not None:
        L, lam = [], []
        NT = getattr(U, "NEW_TEAM", (0.95, 1.05))
        for f in md:
            F = fits.get(f["lg"])
            if not F: continue
            (ah, dh), (aa, da) = F["t"].get(f["h"], NT), F["t"].get(f["a"], NT)
            L.append(f); lam.append([F["mu"] * F["gamma"] * ah * da, F["mu"] * aa * dh])
        if L: run(L, np.array(lam), "m")
    return res

def pack(pz):
    return [int(round(pz[c] * 1000)) for c in PZ_KAYIT]
