"""🔬 Araştırmacı botu (her gün, GitHub Actions).
1) Kaynak keşfi: iddaa'nın sunduğu tüm yarışmaları tarar, yeni açılan ligleri ve kapsamımızı raporlar
   (motor yeni ligleri zaten otomatik alır; burada izlenir ve kayıt tutulur).
2) Kütüphane takibi: açık kaynak penaltyblog'un yeni sürümünü PyPI'dan izler (haftalık laboratuvar yeni sürümü otomatik dener).
3) Deney: kendi kilitli arşivimizde bahis marjını ayırma yöntemlerini (power / oransal / Shin) yarıştırır;
   arşivin iki yarısında da mevcut yöntemi geçen yöntem data/research.json'a yazılır ve motor bir sonraki çalışmada onu kullanır.
"""
import json, os, glob, math, urllib.request, sys
from datetime import date
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = {"User-Agent": "Mozilla/5.0 (BULUTOXX research)", "Accept": "application/json"}

def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read().decode("utf-8"))

HYB_MARGIN = 0.12   # scripts/update.py ile aynı eşik

def devig(o, m):
    q = [1 / x for x in o]
    if m == "hibrit":   # marja duyarlı: düşük marjlı (kapanış/Pinnacle tipi, <%12) oranlarda power, yüksek marjlı (iddaa ~%18) oranlarda oransal
        return devig(o, "power" if sum(q) - 1 < HYB_MARGIN else "prop")
    if m == "prop": s = sum(q); return [x / s for x in q]
    if m == "power":
        lo, hi = 1.0, 3.0
        for _ in range(40):
            k = (lo + hi) / 2
            if sum(x ** k for x in q) > 1: lo = k
            else: hi = k
        p = [x ** k for x in q]; s = sum(p); return [x / s for x in p]
    if m == "shin":   # Shin (1993): içeriden bilgi payı z ile
        B = sum(q); lo, hi = 0.0, 0.4
        for _ in range(50):
            z = (lo + hi) / 2
            p = [(math.sqrt(z * z + 4 * (1 - z) * x * x / B) - z) / (2 * (1 - z)) for x in q]
            if sum(p) > 1: lo = z
            else: hi = z
        s = sum(p); return [x / s for x in p]

def main():
    old = {}
    try: old = json.load(open(os.path.join(DATA, "research.json"), encoding="utf-8"))
    except Exception: pass
    out = {"tarih": date.today().isoformat(), "bulgular": []}
    # 1) kaynak keşfi
    try:
        comps = get("https://sportsbookv2.iddaa.com/sportsbook/competitions").get("data") or []
        names = sorted({c.get("n") for c in comps if c.get("n")})
        known = set(old.get("yarismalar", []))
        new = [n for n in names if n not in known] if known else []
        out["yarismalar"] = names; out["yarisma_sayisi"] = len(names); out["yeni_yarismalar"] = new[:50]
        if new: out["bulgular"].append(f"iddaa'da {len(new)} yeni yarışma açıldı (ör. {', '.join(new[:3])}); motor bunları bültene otomatik alıyor.")
    except Exception as e:
        out["bulgular"].append(f"Yarışma listesi alınamadı ({e.__class__.__name__}).")
    # 2) kütüphane takibi
    try:
        v = get("https://pypi.org/pypi/penaltyblog/json")["info"]["version"]; out["penaltyblog"] = v
        if old.get("penaltyblog") and old["penaltyblog"] != v: out["bulgular"].append(f"penaltyblog {old['penaltyblog']} → {v} yayınlandı; pazar günkü laboratuvar yeni sürümü yarıştıracak.")
    except Exception: out["penaltyblog"] = old.get("penaltyblog")
    # 3) marj ayırma deneyi (kendi arşivimiz)
    recs = []
    for f in sorted(glob.glob(os.path.join(DATA, "archive", "*.json"))):
        for r in json.load(open(f, encoding="utf-8")).values():
            if r.get("hs") is not None and r.get("ms") and len(r["ms"]) == 3: recs.append((os.path.basename(f)[:10], r))
    out["devig"] = old.get("devig", "power"); out["devig_kabul"] = old.get("devig_kabul", False)
    if len(recs) >= 1500:
        recs.sort(key=lambda x: x[0]); mid = recs[len(recs) // 2][0]
        res = {}
        for m in ("power", "prop", "shin", "hibrit"):
            for half, rs in (("1", [r for d, r in recs if d < mid]), ("2", [r for d, r in recs if d >= mid])):
                ll = 0.0
                for r in rs:
                    p = devig(r["ms"], m); k = 0 if r["hs"] > r["as"] else 1 if r["hs"] == r["as"] else 2
                    ll -= math.log(max(p[k], 1e-9))
                res.setdefault(m, {})[half] = round(ll / max(1, len(rs)), 5)
        out["devig_deney"] = {"n": len(recs), "ayrim": mid, "logloss": res}
        cur = out["devig"]; best = cur
        for m in res:
            if m != cur and all(res[m][h] < res[cur][h] - 0.0003 for h in ("1", "2")) and sum(res[m].values()) < sum(res[best].values()): best = m
        if best != cur:
            out["devig"] = best; out["devig_kabul"] = True
            out["bulgular"].append(f"Marj ayırma: '{best}' yöntemi arşivin iki yarısında da '{cur}' yöntemini geçti; motor artık '{best}' kullanacak.")
        else:
            out["bulgular"].append(f"Marj ayırma deneyi ({len(recs)} maç): mevcut '{cur}' yöntemi en iyi ya da fark anlamlı değil.")
    else:
        out["bulgular"].append(f"Marj ayırma deneyi için arşivde {len(recs)} maç var; 1.500 gerekli, veri birikiyor.")
    json.dump(out, open(os.path.join(DATA, "research.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(out["bulgular"]))

if __name__ == "__main__":
    main()
