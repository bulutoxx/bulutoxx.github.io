"""🛡️ Koruyucu botu (her gün): otomatik uygulanan her değişikliği kaydeder ve sonrasını izler.
Bir değişiklikten sonra kilitli önerilerin gerçek isabeti belirgin şekilde kötüleşirse otomatik olarak geri alır
(data/rollback.json: motor 14 gün boyunca değişiklikten önceki ayarlarla çalışır, botların yeni uygulamaları dondurulur).

İzlenen yapılandırma: motor ayarları (decay, prior, rho, mkt, marketW, kalibrasyon), motor sürümü, marj yöntemi, analist katsayıları.
Ölçüt: kilitli önerilerin Brier skoru (düşük = iyi). Değişiklikten önceki ve sonraki dönemde en az 400'er öneri gerekir;
fark 0,01'den büyükse geri alınır (gürültüyle karışmasın diye eşik bilerek yüksek)."""
import json, os, glob
from datetime import date, datetime, timezone, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
KEYS = ["decay", "prior", "rho", "mkt", "formW", "marketW", "calT", "gscale", "dk"]
MIN_N, MARGIN, FREEZE_DAYS = 400, 0.01, 14

def jl(p, d=None):
    try: return json.load(open(os.path.join(DATA, p), encoding="utf-8"))
    except Exception: return d

def config():
    m = jl("model.json", {}); P = m.get("params", {}); r = jl("research.json", {}) or {}; a = jl("analyst.json", {}) or {}
    return {"engine": m.get("engine"), "params": {k: P.get(k) for k in KEYS if k in P},
            "devig": r.get("devig", "power") if r.get("devig_kabul") else "power", "analist": bool(a.get("kabul")), "auto_lab": P.get("auto_lab")}

def recs_between(d0, d1):
    out = []
    for f in glob.glob(os.path.join(DATA, "archive", "*.json")):
        d = os.path.basename(f)[:10]
        if d0 <= d < d1:
            out += [r for r in json.load(open(f, encoding="utf-8")).values() if r.get("ok") is not None and r.get("rp")]
    return out

def brier(rs): return sum((r["rp"] - r["ok"]) ** 2 for r in rs) / len(rs)

def main():
    today = date.today().isoformat()
    log = jl("changes.json", {"degisiklikler": []}) or {"degisiklikler": []}
    cur = config(); last = log["degisiklikler"][-1]["config"] if log["degisiklikler"] else None
    if last != cur:
        diff = {}
        if last:
            if last.get("engine") != cur["engine"]: diff["motor sürümü"] = [last.get("engine"), cur["engine"]]
            for k in KEYS:
                a, b = (last.get("params") or {}).get(k), cur["params"].get(k)
                if a != b: diff[k] = [a, b]
            for k in ("devig", "analist", "auto_lab"):
                if last.get(k) != cur.get(k): diff[k] = [last.get(k), cur.get(k)]
        log["degisiklikler"].append({"tarih": today, "config": cur, "fark": diff, "durum": "izleniyor" if last else "başlangıç"})
        log["degisiklikler"] = log["degisiklikler"][-60:]
    rb = jl("rollback.json", {}) or {}
    if rb.get("aktif") and rb.get("bitis", "") < today: rb = {"aktif": False, "gecmis": rb.get("gecmis", [])}
    # izlenen değişiklikleri değerlendir
    for i, ch in enumerate(log["degisiklikler"]):
        if ch.get("durum") != "izleniyor" or i == 0: continue
        d = ch["tarih"]; before = recs_between((date.fromisoformat(d) - timedelta(days=14)).isoformat(), d)
        after = recs_between(d, (date.fromisoformat(d) + timedelta(days=14)).isoformat())
        ch["once_n"], ch["sonra_n"] = len(before), len(after)
        if len(before) < MIN_N or len(after) < MIN_N:
            if (date.fromisoformat(today) - date.fromisoformat(d)).days > 21: ch["durum"] = "yeterli veri yok, kabul"
            continue
        b0, b1 = brier(before), brier(after); ch["brier_once"], ch["brier_sonra"] = round(b0, 4), round(b1, 4)
        if b1 > b0 + MARGIN and not rb.get("aktif"):
            prev = log["degisiklikler"][i - 1]["config"]
            ch["durum"] = "GERİ ALINDI"
            rb = {"aktif": True, "baslangic": today, "bitis": (date.fromisoformat(today) + timedelta(days=FREEZE_DAYS)).isoformat(),
                  "neden": f"{d} tarihli değişiklikten sonra isabet kötüleşti (Brier {b0:.4f} → {b1:.4f})", "params": prev.get("params"),
                  "devig": prev.get("devig", "power"), "analist": prev.get("analist", False), "gecmis": (rb.get("gecmis") or [])[-10:] + [d]}
        elif len(after) >= MIN_N:
            ch["durum"] = "kalıcı (isabet korunuyor)"
    json.dump(log, open(os.path.join(DATA, "changes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(rb, open(os.path.join(DATA, "rollback.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Koruyucu: {len(log['degisiklikler'])} kayıtlı değişiklik; geri alma {'AKTİF: ' + rb['neden'] if rb.get('aktif') else 'yok'}")

if __name__ == "__main__":
    main()
