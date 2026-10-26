"""⚔️ Derbi karnesi (yalnız repodaki veriyle; ağ kullanmaz).

Derbi listesi index.html içindeki `<script id="derbi-v95">` bloğundaki DERBI_DATA sabitinden okunur (tek kaynak);
ad eşleştirme kuralları oradaki JavaScript ile birebir aynıdır (Türkçe karakter, FC/SK/AŞ/JK ekleri, U17–U23 / B / II /
kadın takımı ayrımı; genç/kadın takımı ana derbi sayılmaz).

Ölçüm (fb_gelistir.py yöntemi): bitmiş maçlar = data/season.json + data/derin (oranlı) ve kilitli iddaa arşivi
(data/archive) + kilitli model günlüğü (data/predlog.json). Her kaynakta derbi ve derbi olmayan maçlar için:
n, favori (en düşük MS oranı) kazanma oranı, oranın ima ettiği favori olasılığı, beraberlik oranı, sürpriz (favori kaybı),
sunulan olasılıkla (piyasa yolu → kalibre MS) en olası sonuç isabeti ve MS log-kaybı.
Çıktı: data/derbi_karne.json (yalnız toplu istatistik; takım adı / ham veri yazılmaz)."""
import json, os, re, sys, glob, math, unicodedata, collections, time
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
EPS = 1e-6

def jl(p):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return None

def derbi_data():
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    m = re.search(r"/\*DERBI_JSON\*/(.*?)/\*/DERBI_JSON\*/", html, re.S)
    return json.loads(m.group(1))

# ------------------------------------------------------------------ ad normalleştirme (index.html'deki dxNz ile aynı)
WOM_LG = {"wsl", "esw", "frw", "mxw", "nlw", "ausw", "nwsl", "ncaaw", "wnba"}
WOM_TAG = re.compile(r"^(k|w|wsl|esw|frw|nlw|mxw|ausw|kadin|women|f)$")
NOISE = {"fc", "cf", "sk", "jk", "fk", "kk", "bc", "as", "ac", "afc", "sl", "rcd", "ssc", "ss", "sv", "club"}
DENY = {"sc", "cd", "ec"}
def base(s):
    s = str(s or "").replace("İ", "i").replace("I", "i").lower().replace("ı", "i")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def nz(name, lg=None):
    s = base(name); v = set()
    def par(mo):
        c = re.sub(r"[^a-z0-9]+", "", mo.group(1))
        if WOM_TAG.match(c): v.add("k"); return " "
        return " @" + c + " " if c else " "
    s = re.sub(r"\(([^)]*)\)", par, s)
    s = re.sub(r"\ba\.s\.?", " as ", s)
    s = re.sub(r"\bu[\s-]+(1[5-9]|2[0-3])\b", r"u\1", s)
    t = [x for x in re.sub(r"[^a-z0-9@]+", " ", s).split(" ") if x]
    out = []
    for i, x in enumerate(t):
        if re.match(r"^u(1[5-9]|2[0-3])$", x): v.add(x); continue
        if x in ("reserves", "reserve", "res"): v.add("res"); continue
        if x in ("academy", "akademi", "youth", "primavera"): v.add("y"); continue
        if x in ("women", "womens", "kadin", "femenino", "feminino", "frauen", "dames", "ladies", "feminine"): v.add("k"); continue
        if x in ("castilla", "atletic") and i > 0: v.add("b"); continue
        if x == "jong" and i == 0: v.add("b"); continue
        out.append(x)
    while out and out[-1] in ("b", "ii", "k", "w", "2"):
        z = out.pop(); v.add("k" if z in ("k", "w") else "b")
    if lg and lg in WOM_LG: v.add("k")
    if out and out[0] == "1": out = out[1:]
    out = [x for x in out if x not in NOISE]
    return out, ",".join(sorted(v))

class Derbi:
    def __init__(self, D):
        self.idx = []
        for k, al in D["teams"].items():
            for a in al:
                ex = a.startswith("=")
                t, _ = nz(a[1:] if ex else a)
                if t: self.idx.append((k, t, ex))
        self.pairs = {}
        for a, b, n in D["pairs"]: self.pairs[tuple(sorted((a, b)))] = n
        self.cache = {}
    def team(self, name, lg=None):
        t, v = nz(name, lg); best = None
        for k, a, ex in self.idx:
            if ex:
                if t != a: continue
            else:
                if t[:len(a)] != a: continue
                tail = t[len(a):]
                if any(x.startswith("@") or x in DENY for x in tail): continue
            if best is None or len(a) > len(best[1]): best = (k, a)
        return (best[0], v) if best else None
    def of(self, h, a, lg=None):
        key = (h, a, lg)
        if key in self.cache: return self.cache[key]
        r = None; A = self.team(h, lg); B = self.team(a, lg)
        if A and B and A[0] != B[0]:
            n = self.pairs.get(tuple(sorted((A[0], B[0]))))
            if n and A[1] == B[1]:
                kind = "ana" if not A[1] else ("kadin" if "k" in A[1].split(",") else "genc")
                r = {"n": n, "kind": kind}
        self.cache[key] = r
        return r

# ------------------------------------------------------------------ veri
def load_hist():
    S = jl(os.path.join(DATA, "season.json")) or {}
    out = []; first = {}
    for lg, d in S.items():
        if d.get("cup") and lg not in ("ucl", "uel", "uecl"): continue
        ms = [m for m in d["matches"] if m.get("ft") and m.get("odds") and all(m["odds"])]
        if d["matches"]: first[lg] = min(m["d"] for m in d["matches"])
        for m in ms:
            out.append({"d": m["d"], "lg": lg, "h": m["h"], "a": m["a"], "ft": m["ft"], "odds": m["odds"], "ou": m.get("ou") if m.get("ou") and all(m["ou"]) else None})
    for f in sorted(glob.glob(os.path.join(DATA, "derin", "*-*.json"))):
        D = jl(f) or {}; lg = D.get("lg"); cut = first.get(lg, "9999")
        for r in D.get("m", []):
            if r[0] < cut and r[5] and r[6] and r[7] and r[3] is not None:
                out.append({"d": r[0], "lg": lg, "h": r[1], "a": r[2], "ft": [r[3], r[4]], "odds": [r[5], r[6], r[7]], "ou": [r[8], r[9]] if r[8] and r[9] else None})
    out.sort(key=lambda m: m["d"])
    return out

def load_archive():
    out = []
    for f in sorted(glob.glob(os.path.join(DATA, "archive", "2*.json"))):
        for k, r in (jl(f) or {}).items():
            if r.get("hs") is None or not r.get("ms") or not all(r["ms"]): continue
            out.append(r)
    return out

# ------------------------------------------------------------------ ölçüler
def block(odds, res, q=None):
    """odds: n×3, res: 0/1/2, q: sunulan/model olasılığı n×3 (isteğe bağlı)."""
    n = len(res)
    if not n: return {"n": 0}
    O = np.asarray(odds, float); res = np.asarray(res)
    imp = 1 / O; imp = imp / imp.sum(1, keepdims=True)
    fav = O[:, [0, 2]].argmin(1) * 2          # 0 = ev, 2 = deplasman (beraberlik favori sayılmaz)
    fp = imp[np.arange(n), fav]
    fw = (res == fav).astype(float)
    dog = np.where(fav == 0, 2, 0)
    R = {"n": int(n),
         "favori_kazanma": round(float(fw.mean()), 4),
         "favori_beklenen": round(float(fp.mean()), 4),
         "favori_fark": round(float(fw.mean() - fp.mean()), 4),
         "beraberlik": round(float((res == 1).mean()), 4),
         "beraberlik_beklenen": round(float(imp[:, 1].mean()), 4),
         "surpriz": round(float((res == dog).mean()), 4),
         "surpriz_beklenen": round(float(imp[np.arange(n), dog].mean()), 4)}
    if q is not None:
        q = np.asarray(q, float)
        R["model_isabet"] = round(float((q.argmax(1) == res).mean()), 4)
        R["model_ms_ll"] = round(float(-np.log(np.clip(q[np.arange(n), res], EPS, 1)).mean()), 4)
    # oranlara göre fark anlamlı mı? (bağımsız Bernoulli varsayımı; |z| > 1,96)
    se = math.sqrt(float((fp * (1 - fp)).sum())) / n
    R["favori_fark_z"] = round(float((fw.mean() - fp.mean()) / se), 2) if se > 0 else None
    # favori kazanma oranı için %95 güven aralığı (Wilson)
    z = 1.96; p = fw.mean()
    d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    R["favori_kazanma_ga95"] = [round(c - h, 4), round(c + h, 4)]
    return R

def resof(h, a): return 0 if h > a else 1 if h == a else 2

def main():
    DB = Derbi(derbi_data())
    out = {"guncel": time.strftime("%Y-%m-%d %H:%M"), "yontem": "Favori = en düşük MS oranlı taraf (1 ya da 2). Beklenen = oranların marjı temizlenmiş olasılığı. "
           "Model isabeti = uygulamanın sunduğu MS olasılığında (piyasa yolu + kalibrasyon, fb_gelistir.py served_full) en olası sonucun tutma oranı. "
           "Genç/kadın/B takımı derbileri ana derbi sayılmaz, ayrı sayılır.",
           "derbi_cifti": len(DB.pairs), "kaynak": {}}
    # 1) tarihsel lig maçları (season + derin)
    H = load_hist()
    q = None
    try:
        import fb_gelistir as FG
        P = FG.params(); S = FG.served_full([m["odds"] for m in H], [m["ou"] for m in H], P); q = S["q"]
    except Exception as e:
        out["not_model"] = "sunulan olasılık hesaplanamadı: " + str(e)[:120]
    res = np.array([resof(*m["ft"]) for m in H])
    tag = [DB.of(m["h"], m["a"], m["lg"]) for m in H]
    ana = np.array([bool(t and t["kind"] == "ana") for t in tag]); oth = np.array([bool(t and t["kind"] != "ana") for t in tag])
    non = ~(ana | oth)
    odds = np.array([m["odds"] for m in H], float)
    def sub(mask): return block(odds[mask], res[mask], q[mask] if q is not None else None)
    hist = {"donem": [H[0]["d"], H[-1]["d"]] if H else None, "derbi": sub(ana), "derbi_olmayan": sub(non)}
    if oth.any(): hist["genc_kadin_derbi"] = sub(oth)
    # aynı liglerdeki derbi dışı maçlarla karşılaştırma (lig karışımı etkisini ayırmak için)
    lgs = {H[i]["lg"] for i in np.where(ana)[0]}
    same = non & np.array([m["lg"] in lgs for m in H])
    hist["ayni_lig_derbi_olmayan"] = sub(same)
    # derbilerde favori gücüne göre (oran kovası)
    fo = odds[:, [0, 2]].min(1)
    hist["derbi_oran_kovasi"] = {nm: block(odds[ana & mk], res[ana & mk]) for nm, mk in
                                 (("favori oranı <1,60", fo < 1.6), ("1,60–2,20", (fo >= 1.6) & (fo < 2.2)), ("≥2,20 (dengeli)", fo >= 2.2))}
    hist["derbi_cifti_sayisi_veride"] = len({tuple(sorted((DB.team(H[i]["h"], H[i]["lg"])[0], DB.team(H[i]["a"], H[i]["lg"])[0]))) for i in np.where(ana)[0]})
    out["kaynak"]["lig_gecmisi"] = hist
    # 2) kilitli iddaa arşivi (sunulan olasılık p)
    A = load_archive()
    if A:
        ra = np.array([resof(r["hs"], r["as"]) for r in A]); oa = np.array([r["ms"] for r in A], float)
        pa = np.array([r["p"] if r.get("p") else [1 / 3] * 3 for r in A], float)
        ta = np.array([bool((lambda t: t and t["kind"] == "ana")(DB.of(r["h"], r["a"]))) for r in A])
        out["kaynak"]["kilitli_arsiv"] = {"derbi": block(oa[ta], ra[ta], pa[ta]), "derbi_olmayan": block(oa[~ta], ra[~ta], pa[~ta])}
    # 3) kilitli model günlüğü (yalnız model olasılığı; oran yok → favori = modelin favorisi değil, piyasa mp varsa ondan)
    L = [e for e in (jl(os.path.join(DATA, "predlog.json")) or []) if e.get("ft") or e.get("r")]
    rows = []
    for e in L:
        try:
            sc = e.get("r") or [int(x) for x in str(e["ft"]).split("-")]
            rows.append((e, resof(sc[0], sc[1])))
        except Exception: pass
    if rows:
        tl = np.array([bool((lambda t: t and t["kind"] == "ana")(DB.of(e["h"], e["a"], e.get("lg")))) for e, _ in rows])
        rl = np.array([r for _, r in rows]); pl = np.array([e["p"] for e, _ in rows], float)
        def lb(mask):
            n = int(mask.sum())
            if not n: return {"n": 0}
            return {"n": n, "model_isabet": round(float((pl[mask].argmax(1) == rl[mask]).mean()), 4), "beraberlik": round(float((rl[mask] == 1).mean()), 4)}
        out["kaynak"]["model_gunlugu"] = {"derbi": lb(tl), "derbi_olmayan": lb(~tl)}
    # özet + uyarı
    d = hist["derbi"]; nd = hist["ayni_lig_derbi_olmayan"]
    ozet = {"n_derbi": d.get("n", 0), "n_derbi_olmayan": hist["derbi_olmayan"].get("n", 0)}
    if d.get("n"):
        ozet.update({"favori_kazanma_derbi": d["favori_kazanma"], "favori_kazanma_diger": nd["favori_kazanma"],
                     "favori_beklenen_derbi": d["favori_beklenen"], "beraberlik_derbi": d["beraberlik"], "beraberlik_diger": nd["beraberlik"],
                     "surpriz_derbi": d["surpriz"], "surpriz_diger": nd["surpriz"],
                     "model_isabet_derbi": d.get("model_isabet"), "model_isabet_diger": nd.get("model_isabet"),
                     "favori_beklenen_diger": nd["favori_beklenen"], "favori_fark_oran": d["favori_fark"], "favori_fark_z": d.get("favori_fark_z"),
                     "oranlara_gore_anlamli": bool(d.get("favori_fark_z") is not None and abs(d["favori_fark_z"]) > 1.96)})
    ozet["az_veri"] = d.get("n", 0) < 150
    ozet["uyari"] = ("Derbi örneği küçük; fark istatistiksel olarak kesin değildir." if d.get("n", 0) < 150 else
                     "Derbi örneği orta büyüklükte; derbide favori diğer maçlardan daha az kazanıyor, ancak farkın çoğunu oranlar zaten "
                     "fiyatlıyor (derbiler daha dengeli)." + ("" if ozet.get("oranlara_gore_anlamli") else
                     " Oranların beklentisine göre kalan fark istatistiksel olarak anlamlı değil."))
    if "kilitli_arsiv" in out["kaynak"] and out["kaynak"]["kilitli_arsiv"]["derbi"].get("n", 0) < 30:
        ozet["uyari"] += " Kilitli arşivde (son günler) çok az derbi var; o satır yalnız bilgi amaçlıdır."
    out["ozet"] = ozet
    json.dump(out, open(os.path.join(DATA, "derbi_karne.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, allow_nan=False)
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
