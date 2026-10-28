"""OXXai · Canlı altın KUPO kuralı (sunucu tarafı; uygulamadaki <script id="canli-v70"> build() ve pwLiveCands() ile AYNI formül).

Bayrak: data/canli_altin.json  {tekli, kombine, aday, dkmax, baslangic, bitis, durum, onceki, olcum, karar}
  • tekli   = tek başına altın seçim eşiği (uygulamada SOLO; eski sabit 0,85)
  • kombine = 2–4 maçlık altın KUPO'nun birlikte tutma eşiği (uygulamada TH; eski sabit 0,75)
  • aday    = canlı aday tabanı (uygulamada PW.pick; 0,80 — değişmedi)
  • dkmax   = bu dakika ve sonrasında altın / tavsiye yok (v135: 75)
  • durum   = "deneme" (48 saatlik canlı kapı sürüyor) | "kalici" | "geri_alindi"
Dosya yoksa ya da bozuksa eski sabitler (VARSAYILAN) kullanılır. Eşik seçimi ve 48 saat kapısı: lab/canli_altin_lab.py.

Kural (uygulama ile aynı):
  1) her canlı maçta en olası seçim (oranı ≥ 1,03, olasılığı ≥ 0,60; olasılık = gösterilen canlı olasılık);
     dakika ≥ dkmax ise maç atlanır; gösterilen olasılık ≥ aday ise aday listesine girer (üst sınır 0,99), olasılığa göre sıralanır;
  2) altın adayları: oran ≥ 1,05, dakika < dkmax, maç başına bir seçim, en çok 12;
  3) farklı maçlardan 2–4 seçim, olasılıklar çarpımı ≥ kombine olan EN YÜKSEK toplam oranlı kombinasyon;
  4) yoksa olasılığı ≥ tekli olan en güçlü tek seçim.
"""
import json, math, os

VARSAYILAN = {"tekli": 0.85, "kombine": 0.75, "aday": 0.80, "dkmax": 75}


def ayar(data_dir):
    F = dict(VARSAYILAN)
    try:
        j = json.load(open(os.path.join(data_dir, "canli_altin.json"), encoding="utf-8"))
        for k in VARSAYILAN:
            v = j.get(k)
            if isinstance(v, (int, float)) and math.isfinite(v): F[k] = float(v)
        if not (0.5 <= F["tekli"] <= 0.99 and 0.5 <= F["kombine"] <= 0.99 and 0.5 <= F["aday"] <= 0.99 and 30 <= F["dkmax"] <= 120): return dict(VARSAYILAN)
        F["durum"] = j.get("durum")
    except Exception:
        pass
    return F


def uygulama_adaylari(e, Pr, hs, as_):
    """iddaa canlı etkinliğinden (sportsbook events) uygulamadaki idlOdds + idlPick aday listesi: [(rk, p, oran|None)].
    Alt/Üst: oranları en dengeli çizgi (|alt − üst| en küçük); kapalı pazarın oranı yok sayılır."""
    import canli_guc as CG
    ms = ng = None; ous = []
    for m in e.get("m") or []:
        if m.get("t") != 4: continue
        v = {o.get("n"): o.get("odd") for o in m.get("o") or [] if o.get("odd") and o["odd"] > 1.01}
        lock = m.get("s") != 1
        if ms is None and m.get("st") in (4, 1) and all(x in v for x in ("1", "0", "2")): ms = (None if lock else [v["1"], v["0"], v["2"]])
        if ng is None and m.get("st") == 34 and all(x in v for x in ("1", "Olmaz", "2")): ng = (None if lock else [v["1"], v["Olmaz"], v["2"]])
        if "Alt" in v and "Üst" in v and m.get("sov") and m.get("st") in (14, 101): ous.append((float(m["sov"]), v["Alt"], v["Üst"], lock))
    ou = sorted(ous, key=lambda x: abs(x[1] - x[2]))[0] if ous else None
    line = ou[0] if ou else hs + as_ + .5
    po = CG.over(Pr, line, hs + as_)
    c = [("1", Pr["H"], ms and ms[0]), ("X", Pr["D"], ms and ms[1]), ("2", Pr["A"], ms and ms[2]),
         ("A" + str(line), 1 - po, ou and not ou[3] and ou[1] or None), ("U" + str(line), po, ou and not ou[3] and ou[2] or None),
         ("G1", Pr["nh"], ng and ng[0]), ("G0", Pr["none"], ng and ng[1]), ("G2", Pr["na"], ng and ng[2])]
    return c


def kal(p, cal):
    """Gösterilen canlı olasılık: CG açıkken kendi Platt'ı (data/canli_guc.json → kal), yoksa olduğu gibi."""
    if not cal or not (0 < p < 1): return p
    x = math.log(p / (1 - p)); return 1 / (1 + math.exp(-(cal["a"] + cal["b"] * x)))


def mac_adayi(cands, dk, F, cal=None):
    """1. adım (pwLiveCands): maçın en olası seçimi → aday sözlüğü ya da None."""
    if dk is not None and dk >= F["dkmax"]: return None
    ok = [c for c in cands if c[2] and c[2] >= 1.03 and c[1] is not None and math.isfinite(c[1]) and c[1] >= .6]
    if not ok: return None
    b = max(ok, key=lambda c: c[1]); p = kal(b[1], cal)
    if p < F["aday"]: return None
    return {"k": b[0], "p": min(p, .99), "ham": b[1], "o": b[2]}


def sec(L, F):
    """2–4. adımlar (canli-v70 build). L: [{"id", "k", "p", "o", "dk"}] — olasılığa göre azalan sıralanır.
    Dönüş: {"tur": "kombine"|"tekli", "sel": [...], "p", "o"} ya da None."""
    L = sorted(L, key=lambda x: -x["p"]); seen = set(); c = []
    for x in L:
        if not (x["o"] and x["o"] >= 1.05): continue
        if x.get("dk") is not None and x["dk"] >= F["dkmax"]: continue
        if x["id"] in seen: continue
        seen.add(x["id"]); c.append(x)
        if len(c) >= 12: break
    TH = F["kombine"]; best = [None]
    def rec(i, sel, p, o):
        if len(sel) >= 2 and p >= TH and (best[0] is None or o > best[0]["o"] + 1e-9): best[0] = {"sel": list(sel), "p": p, "o": o}
        if len(sel) >= 4: return
        for j in range(i, len(c)):
            np_ = p * c[j]["p"]
            if np_ < TH: continue
            sel.append(c[j]); rec(j + 1, sel, np_, o * c[j]["o"]); sel.pop()
    rec(0, [], 1.0, 1.0)
    if best[0]: return dict(best[0], tur="kombine")
    s = [x for x in c if x["p"] >= F["tekli"]]
    if s:
        x = max(s, key=lambda x: x["p"]); return {"sel": [x], "p": x["p"], "o": x["o"], "tur": "tekli"}
    return None


def hit(k, fh, fa, hs, as_):
    """Canlı seçimin sonucu (toplayıcı live_grade ile aynı): True/False, belirlenemezse None."""
    if k == "1": return fh > fa
    if k == "X": return fh == fa
    if k == "2": return fh < fa
    if k and k[0] in "UA" and k[1:]:
        line = float(k[1:]); return (fh + fa > line) if k[0] == "U" else (fh + fa < line)
    if k == "G0": return (fh + fa) == (hs + as_)
    if k in ("G1", "G2"):
        dh, da = fh - hs, fa - as_
        if dh + da == 0: return False
        if dh > 0 and da == 0: return k == "G1"
        if da > 0 and dh == 0: return k == "G2"
        return None
    return None


# ---------------------------------------------------------------- v140 · Canlı altın İŞARET (tek maç rozeti)
# Uygulamadaki <script id="canli-isaret-v140"> aiRule() ile AYNI kural. Canlı altın KUPO (sec) ve eşikleri değişmez.
#   1) dakika ≥ dkmax → işaret yok (75. dk sonrası model aşırı güvenliydi; v135 kararı korunur);
#   2) maçın en olası seçimi (oran ≥ 1,03, olasılık ≥ 0,60 — pwLiveCands ile aynı aday), oranı ≥ 1,05 olmalı;
#   3) gösterilen (kalibre) olasılık ≥ esik → işaret açılır; zaten açıksa kapanis altına düşene dek kalır (histerezis).
# Bayrak: data/canli_altin.json → "isaret": {esik, kapanis, dkmax, durum, baslangic, bitis, olcum, kapi}; durum "durduruldu" → işaret yok.
ISARET_VARSAYILAN = {"esik": 0.80, "kapanis": 0.77, "dkmax": 75}


def isaret_ayar(data_dir):
    I = dict(ISARET_VARSAYILAN, durum="deneme")
    try:
        j = (json.load(open(os.path.join(data_dir, "canli_altin.json"), encoding="utf-8")) or {}).get("isaret") or {}
        T = dict(I)
        for k in ISARET_VARSAYILAN:
            v = j.get(k)
            if isinstance(v, (int, float)) and math.isfinite(v): T[k] = float(v)
        if 0.5 <= T["kapanis"] <= T["esik"] <= 0.99 and 30 <= T["dkmax"] <= 120:
            I = T
        I["durum"] = j.get("durum") or "deneme"
        for k in ("baslangic", "bitis"):
            if j.get(k): I[k] = j[k]
    except Exception:
        pass
    return I


def isaret(cands, dk, I, cal=None, onceki=False):
    """cands: uygulama_adaylari() çıktısı [(rk, ham p, oran|None)]; dk: maç dakikası (m.min); onceki: bu maç bir önceki turda işaretli miydi.
    Dönüş: {"k", "p" (gösterilen, ≤ 0,99), "ham", "o"} ya da None."""
    if I.get("durum") == "durduruldu": return None
    if dk is not None and dk >= I["dkmax"]: return None
    ok = [c for c in cands if c[2] and c[2] >= 1.03 and c[1] is not None and math.isfinite(c[1]) and c[1] >= .6]
    if not ok: return None
    b = max(ok, key=lambda c: c[1])
    if not (b[2] >= 1.05): return None
    p = min(kal(b[1], cal), .99)
    if p >= I["esik"] or (onceki and p >= I["kapanis"]):
        return {"k": b[0], "p": p, "ham": b[1], "o": b[2]}
    return None
