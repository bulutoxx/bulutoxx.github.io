"""BULUTOXX veri toplayıcı (kendini geliştirme modülü) — her saat çalışır.

1) Resmi iddaa bülteninden maç başlamadan önceki son oranları ve BULUTOXX önerisini kaydeder (maç başlayınca kilitlenir).
2) Biten maçların sonucunu iddaa sonuç servisinden alıp kayda ekler ve öneriyi puanlar (tuttu / tutmadı).
3) Günlük özet (data/daily.json): "Dün önerilerin %X'i tuttu", güven dilimine ve lige göre isabet.
4) Arşiv (data/archive/GGGG-AA-GG.json): tüm liglerden oran + sonuç verisi; motorun öneri kalibrasyonu ve
   haftalık laboratuvar bu kendi verimizle zamanla daha da isabetli hale gelir.
"""
import json, math, os, sys, glob, collections
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iddaa as ID
import update as U

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data"); ARC = os.path.join(DATA, "archive")
TR = ZoneInfo("Europe/Istanbul")
KEEP_DAYS = 120

def rec_for(ms, ou, rho):
    """Uygulamadaki öneriyle aynı kural: MS 1/X/2 ve 2,5 Alt/Üst içinden oranı ≥1,15 olan en yüksek olasılık."""
    tmp = [dict({"odds": ms}, **({"ou": ou} if ou else {}))]
    U.market_xg(tmp)
    lh, la = tmp[0]["xg"]
    p, pO, pB, _ = U.outcome_probs(np.array([lh]), np.array([la]), rho)
    p = p[0]; pO = float(pO[0])
    c = [("1", float(p[0]), ms[0]), ("X", float(p[1]), ms[1]), ("2", float(p[2]), ms[2])]
    if ou: c += [("U", pO, ou[0]), ("A", 1 - pO, ou[1])]   # alt/üst oranı yoksa gol beklentisi belirsiz: alt/üst önerilmez
    ok = [x for x in c if x[2] is None or x[2] >= 1.15]
    k, pp, o = max(ok or c, key=lambda x: x[1])
    return {"lam": [lh, la], "p": [round(float(x), 4) for x in p], "o25": round(pO, 4), "kg": round(float(pB[0]), 4), "rk": k, "rp": round(pp, 4), "ro": o}

def hit(rk, hs, as_):
    if rk == "1": return hs > as_
    if rk == "X": return hs == as_
    if rk == "2": return hs < as_
    if rk == "U": return hs + as_ > 2
    if rk == "A": return hs + as_ < 3
    return None

def load_day(d):
    p = os.path.join(ARC, f"{d}.json")
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return {}

def save_day(d, recs):
    os.makedirs(ARC, exist_ok=True)
    json.dump({k: recs[k] for k in sorted(recs)}, open(os.path.join(ARC, f"{d}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

def main():
    now = datetime.now(timezone.utc); nts = now.timestamp()
    try: rho = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"].get("rho", -0.06)
    except Exception: rho = -0.06
    # 1) maç öncesi kayıt (başlamamış maçlar güncellenir; başlayınca son hali kilitli kalır)
    days = {}
    def day_of(ts): return datetime.fromtimestamp(ts, timezone.utc).astimezone(TR).date().isoformat()
    n_pre = 0
    try:
        evs = ID.fetch(1, days=2)
        for e in evs:
            if e["ts"] <= nts: continue
            d = day_of(e["ts"]); recs = days.setdefault(d, load_day(d)); k = str(e["iid"])
            r = recs.get(k, {})
            if r.get("hs") is not None: continue
            try: rr = rec_for(e["mk"]["ms"], e["mk"].get("ou"), rho)
            except Exception: continue
            r.update({"ts": e["ts"], "c": e["comp"], "cc": e["cc"], "h": e["h"], "a": e["a"], "ms": e["mk"]["ms"], "ou": e["mk"].get("ou"),
                      "kgo": e["mk"].get("kg"), "mbs": e.get("mbc")}, **rr)
            recs[k] = r; n_pre += 1
    except Exception as ex:
        print("bülten alınamadı:", ex.__class__.__name__, ex, flush=True)
    # 2) sonuçlar: dün ve bugün
    n_res = 0
    for back in (2, 1, 0):
        d = (now.astimezone(TR).date() - timedelta(days=back)).isoformat()
        try:
            import urllib.request
            req = urllib.request.Request(f"https://statisticsv2.iddaa.com/live-results?sportId=1&date={d}", headers=ID.UA)
            j = json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8")); data = j.get("data") or {}
        except Exception as ex:
            print("sonuç alınamadı", d, ex.__class__.__name__, flush=True); continue
        recs = days.setdefault(d, load_day(d)); sc = data.get("sc") or {}
        for ev in data.get("events") or []:
            if ev.get("phase") != 2: continue
            k = str(ev["eventId"]); r = recs.get(k)
            s = sc.get(k)
            if not r or not s or not s.get("ht") or s["ht"].get("c") is None: continue
            if r.get("hs") is not None: continue
            r["hs"], r["as"] = int(s["ht"]["c"]), int(s["at"]["c"])
            if s["ht"].get("ht") is not None: r["h1"], r["a1"] = s["ht"]["ht"], s["at"]["ht"]
            r["ok"] = hit(r.get("rk"), r["hs"], r["as"]); n_res += 1
    for d, recs in days.items(): save_day(d, recs)
    # eski arşivleri temizle
    cut = (now.astimezone(TR).date() - timedelta(days=KEEP_DAYS)).isoformat()
    for f in glob.glob(os.path.join(ARC, "*.json")):
        if os.path.basename(f)[:10] < cut: os.remove(f)
    # 3) günlük özet
    summ = []
    for f in sorted(glob.glob(os.path.join(ARC, "*.json")))[-30:]:
        d = os.path.basename(f)[:10]; recs = json.load(open(f, encoding="utf-8"))
        g = [r for r in recs.values() if r.get("ok") is not None]
        if not g: summ.append({"d": d, "n": 0, "kayit": len(recs)}); continue
        tiers = {"guclu": [r for r in g if r["rp"] >= .70], "oneri": [r for r in g if .58 <= r["rp"] < .70], "riskli": [r for r in g if r["rp"] < .58]}
        top = sorted([r for r in tiers["guclu"] if r["ok"]], key=lambda r: -r["rp"])[:5]
        NM = {"1": "MS 1", "X": "MS X", "2": "MS 2", "U": "2,5 Üst", "A": "2,5 Alt"}
        summ.append({"d": d, "n": len(g), "kayit": len(recs), "hit": round(sum(r["ok"] for r in g) / len(g), 4),
                     **{k: {"n": len(v), "hit": round(sum(r["ok"] for r in v) / len(v), 4) if v else None} for k, v in tiers.items()},
                     "ornek": [{"h": r["h"], "a": r["a"], "s": f"{r['hs']}-{r['as']}", "o": NM.get(r["rk"], r["rk"]), "p": r["rp"], "odd": r.get("ro")} for r in top]})
    allg = [r for f in glob.glob(os.path.join(ARC, "*.json")) for r in json.load(open(f, encoding="utf-8")).values() if r.get("ok") is not None]
    out = {"updated": now.strftime("%Y-%m-%dT%H:%MZ"), "gunler": summ,
           "toplam": {"n": len(allg), "hit": round(sum(r["ok"] for r in allg) / len(allg), 4) if allg else None,
                      "guclu_n": sum(1 for r in allg if r["rp"] >= .7), "guclu_hit": (round(sum(r["ok"] for r in allg if r["rp"] >= .7) / max(1, sum(1 for r in allg if r["rp"] >= .7)), 4))}}
    json.dump(out, open(os.path.join(DATA, "daily.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"Toplayıcı: {n_pre} maç öncesi kayıt, {n_res} sonuç işlendi; arşivde {len(allg)} puanlanmış öneri", flush=True)

if __name__ == "__main__":
    try: main()
    except Exception as e:
        import traceback; traceback.print_exc(); print("toplayıcı hata verdi, sonraki saatte tekrar denenecek")
