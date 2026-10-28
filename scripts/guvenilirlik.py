#!/usr/bin/env python3
"""📐 Güvenilirlik raporu (YH-09): tüm karnelerin ortak ölçüm yardımcısı. Yalnız standart kütüphane; ağ yok.

Girdi her zaman SONUÇLANMIŞ ve KİLİTLİ tahminlerdir (olasılık p, gerçekleşme y ∈ {0,1}); seçimi çağıran karne betiği yapar.

Brier ayrışımı (Murphy 1973), 10 eşit genişlikte kova (0–0,1 … 0,9–1,0):
    Brier = güvenilirlik − çözünürlük + belirsizlik + kova_ici
  güvenilirlik = Σ n_k (p̄_k − ō_k)² / N            (küçük = iyi kalibre; yeniden kalibrasyonla düzelir)
  çözünürlük   = Σ n_k (ō_k − ō)² / N              (büyük = iyi; model/veri ayırt ediciliği)
  belirsizlik  = ō (1 − ō)                          (yalnız veriye bağlı)
  kova_ici     = Σ_k Σ_i [(p_i − p̄_k)² − 2 (p_i − p̄_k)(y_i − ō_k)] / N
                 (Stephenson vd. 2008: kova içinde tahminler aynı olmadığından kalan terim; toplam Brier'e TAM eşittir)
ECE (ağırlıklı) = Σ n_k |p̄_k − ō_k| / N, aynı 10 kova. Her kovada Wilson %95 aralığı.
Çok sonuçlu tahminler (1X2, at koşusu) "her seçenek ayrı ikili tahmin" olarak düzleştirilir (Brier = çok sınıflı Brier / K).
"""
import math

KOVA = 10
AZ_N = 50          # bu sayının altındaki kovalar arayüzde "veri az" diye işaretlenir (YH-13)


def wilson(k, n, z=1.959964):
    if not n: return [None, None]
    ph = k / n; d = 1 + z * z / n
    m = (ph + z * z / (2 * n)) / d; h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return [max(0.0, m - h), min(1.0, m + h)]


def _kova(p, k=KOVA):
    return min(k - 1, max(0, int(p * k)))


def ayrisim(p, y, k=KOVA):
    """Ham (yuvarlanmamış) bileşenler. p, y: eşit uzunlukta diziler."""
    p = [min(1.0, max(0.0, float(a))) for a in p]; y = [1.0 if b else 0.0 for b in y]
    N = len(p)
    if N == 0 or N != len(y): return None
    ob = sum(y) / N
    K = {}
    for a, b in zip(p, y): K.setdefault(_kova(a, k), []).append((a, b))
    rel = res = wb = ece = 0.0; kv = []
    for j in sorted(K):
        L = K[j]; n = len(L); pm = sum(a for a, _ in L) / n; om = sum(b for _, b in L) / n
        rel += n * (pm - om) ** 2; res += n * (om - ob) ** 2; ece += n * abs(pm - om)
        wb += sum((a - pm) ** 2 - 2 * (a - pm) * (b - om) for a, b in L)
        lo, hi = wilson(sum(b for _, b in L), n)
        kv.append({"alt": j / k, "ust": (j + 1) / k, "n": n, "tahmin": pm, "gercek": om, "wilson95": [lo, hi]})
    eps = 1e-12
    return {"n": N, "brier": sum((a - b) ** 2 for a, b in zip(p, y)) / N,
            "guvenilirlik": rel / N, "cozunurluk": res / N, "belirsizlik": ob * (1 - ob), "kova_ici": wb / N,
            "ece": ece / N, "log_kayip": -sum(math.log(max(eps, a if b else 1 - a)) for a, b in zip(p, y)) / N,
            "ort_tahmin": sum(p) / N, "gercek_oran": ob, "kovalar": kv}


def rapor(p, y, k=KOVA, nd=6):
    """Karneye yazılacak yuvarlanmış blok (veri yoksa {"n": 0})."""
    A = ayrisim(p, y, k)
    if not A: return {"n": 0}
    R = lambda v: None if v is None else round(v, nd)
    out = {kk: (R(v) if isinstance(v, float) else v) for kk, v in A.items() if kk != "kovalar"}
    out["kovalar"] = [{"aralik": f"{b['alt']:.1f}-{b['ust']:.1f}", "n": b["n"], "tahmin": R(b["tahmin"]), "gercek": R(b["gercek"]),
                       "wilson95": [R(b["wilson95"][0]), R(b["wilson95"][1])], **({"veri_az": True} if b["n"] < AZ_N else {})}
                      for b in A["kovalar"]]
    out["yontem"] = "Murphy (1973) Brier ayrışımı + kova_ici (Stephenson 2008), ECE 10 eşit kova ağırlıklı, Wilson %95"
    return out


def coklu(P, Y, k=KOVA):
    """Çok sonuçlu tahminler: P = [[p_1..p_K], ...], Y = gerçekleşen sonucun indeksi. Her seçenek ayrı ikili tahmin."""
    p, y = [], []
    for ps, yi in zip(P, Y):
        for j, a in enumerate(ps): p.append(a); y.append(int(j == yi))
    return rapor(p, y, k)


def ll_karsilastir(pm, pp, nd=5):
    """Aynı olaylarda model (pm) ve piyasa (pp) log-kaybı: gerçekleşen sonuca verilen olasılıklar. fark = model − piyasa
    (negatif = model daha iyi); %95 aralık eşleştirilmiş farkın normal yaklaşımı."""
    n = len(pm)
    if not n or n != len(pp): return {"n": 0}
    lm = [-math.log(max(1e-9, a)) for a in pm]; lp = [-math.log(max(1e-9, b)) for b in pp]
    d = [a - b for a, b in zip(lm, lp)]; md = sum(d) / n
    sd = math.sqrt(sum((x - md) ** 2 for x in d) / (n - 1)) if n > 1 else None
    ga = [round(md - 1.96 * sd / math.sqrt(n), nd), round(md + 1.96 * sd / math.sqrt(n), nd)] if sd is not None else [None, None]
    return {"n": n, "ll_model": round(sum(lm) / n, nd), "ll_piyasa": round(sum(lp) / n, nd), "fark": round(md, nd), "fark_ga95": ga}


# ------------------------------------------------------------------ karne bağlayıcıları (her karne betiği yalnız bunu çağırır)
def karne_futbol_oneri(kayitlar):
    """collector.py → daily.json: kilitli arşiv önerileri (maç başlayınca kayıt değişmez).
    tum: kayıttaki öneri (rp/ok, ham piyasa ölçeği; karnenin 'toplam'ı ile aynı küme).
    gosterilen: uygulamanın gösterdiği öneri (sp/sok, ml80 sonrası) + aynı seçimde piyasanın marjı ayrılmış olasılığıyla log-kayıp."""
    A = [r for r in kayitlar if r.get("ok") is not None and r.get("rp")]
    out = {"tum": rapor([r["rp"] for r in A], [r["ok"] for r in A])}
    S = [r for r in A if r.get("sp") and r.get("sok") is not None]
    out["gosterilen"] = rapor([r["sp"] for r in S], [r["sok"] for r in S])
    pm, pp = [], []
    for r in S:
        q = _piyasa_p(r.get("sk"), r.get("ms"), r.get("ou"))
        if q is None: continue
        pm.append(r["sp"] if r["sok"] else 1 - r["sp"]); pp.append(q if r["sok"] else 1 - q)
    out["piyasa"] = dict(ll_karsilastir(pm, pp), kapsam="gösterilen öneri; piyasa = aynı seçeneğin oranından orantılı marj ayrımı")
    return out


def _piyasa_p(k, ms, ou):
    try:
        if k in ("1", "X", "2") and ms:
            inv = [1 / float(x) for x in ms]; return inv["1X2".index(k)] / sum(inv)
        if k in ("U", "A") and ou:
            inv = [1 / float(x) for x in ou]; return inv[0 if k == "U" else 1] / sum(inv)
    except Exception: return None
    return None


def karne_canli(kayitlar, esik_dk=75):
    """collector.py → daily.canli: canlı seçimler, KAYIT ANINDAKİ olasılık (p) ile; karne kuralı gibi esik_dk ve sonrası hariç."""
    A = [r for r in kayitlar if r.get("ok") is not None and r.get("p") is not None and (r.get("t") if r.get("t") is not None else 0) < esik_dk]
    return rapor([r["p"] for r in A], [r["ok"] for r in A])


def karne_futbol_1x2(plog):
    """pazar.live_scores → pazar_karne.canli: kilitli (zaman damgalı, maç öncesi) 1X2 model yolu tahminleri ve oranlı
    maçlarda piyasa (mp) ile log-kayıp karşılaştırması. Zaman damgası olmayan eski kayıtlar (kilit kuralından önce) alınmaz."""
    es = [e for e in plog if e.get("r") and e.get("ts") and e.get("p") and len(e["p"]) == 3]
    res = lambda e: 0 if e["r"][0] > e["r"][1] else 1 if e["r"][0] == e["r"][1] else 2
    out = {"model": dict(coklu([e["p"] for e in es], [res(e) for e in es]), n_mac=len(es))}
    mk = [e for e in es if e.get("mp") and len(e["mp"]) == 3]
    out["piyasa"] = dict(ll_karsilastir([e["p"][res(e)] for e in mk], [e["mp"][res(e)] for e in mk]), kapsam="oranlı maçlar, 1X2")
    return out


def karne_basket(plog, sm):
    """basket.live_report → basket.json live: kilitli maç öncesi tahminlerde favorinin kazanma olasılığı Φ((ph−pa)/sm_lig)
    (uygulamadaki dönüşüm), y = favori kazandı."""
    p, y = [], []
    for e in plog:
        if not e.get("r") or e["r"][0] == e["r"][1]: continue
        kt = e.get("ts") or (e.get("pz0") or {}).get("ts")     # kilit zamanı (eski kayıtlarda kilit anı piyasa görüntüsü)
        if not kt or not e.get("dt") or kt[:16] > e["dt"][:16]: continue
        s = (sm or {}).get(e.get("lg")) or 12.0
        q = 0.5 * (1 + math.erf((e["ph"] - e["pa"]) / s / math.sqrt(2)))
        fav_ev = q >= 0.5
        p.append(q if fav_ev else 1 - q); y.append(int((e["r"][0] > e["r"][1]) == fav_ev))
    return rapor(p, y)


def karne_at(kosular):
    """lab/at/gece.puanla → data/at/karne.json: her atın kazanma olasılığı (koşudan önce kilitli, kosudan_once ve doğru mod)."""
    p, y = [], []; nk = 0
    for x in kosular:
        if not x.get("kosudan_once", True) or x.get("mod_hatali") or not x.get("pw"): continue
        nk += 1
        for a, b in x["pw"]: p.append(a); y.append(b)
    return dict(rapor(p, y), n_kosu=nk)


def karne_bacak(bacaklar):
    """oxx_kupon.karne_kur → oxx_karne: canlı (geriye dönük olmayan) KUPO bacakları."""
    B = [(b["p"], b["tuttu"]) for b in bacaklar if b.get("p") is not None and b.get("tuttu") is not None]
    return rapor([a for a, _ in B], [c for _, c in B])
