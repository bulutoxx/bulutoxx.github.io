"""🛡️ Koruyucu botu (her gün): otomatik uygulanan her değişikliği kaydeder ve sonrasını izler.
Bir değişiklikten sonra kilitli önerilerin gerçek isabeti belirgin şekilde kötüleşirse otomatik olarak geri alır
(data/rollback.json: motor 14 gün boyunca değişiklikten önceki ayarlarla çalışır, botların yeni uygulamaları dondurulur).

İzlenen yapılandırma: motor ayarları (decay, prior, rho, mkt, marketW, kalibrasyon), motor sürümü, marj yöntemi, analist katsayıları,
canlı Platt, kalibrasyon yolu (cal_yol: 'sunulan' = uygulamanın gösterdiği piyasa yolunda öğrenilmiş, 'model' = eski yöntem).
Ölçüt: kilitli önerilerin Brier skoru (düşük = iyi). ml80'den beri iki dönemde de en az 400'er 'sunulan' kayıt varsa
(toplayıcı 'sp'/'sok': uygulamanın gösterdiği, calT/gscale/dk dahil öneri) ölçüt odur; yoksa ham 'rp'/'ok'. Değişiklikten önceki ve sonraki dönemde en az 400'er öneri gerekir;
fark 0,01'den büyükse geri alınır (gürültüyle karışmasın diye eşik bilerek yüksek)."""
import json, os, glob, sys
from datetime import date, datetime, timezone, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import arsiv   # güncel + kalıcı arşiv katmanı (yalnız standart kütüphane)
KEYS = ["decay", "prior", "rho", "mkt", "formW", "marketW", "calT", "gscale", "dk"]
MIN_N, MARGIN, FREEZE_DAYS = 400, 0.01, 14

def jl(p, d=None):
    try: return json.load(open(os.path.join(DATA, p), encoding="utf-8"))
    except Exception: return d

def config():
    m = jl("model.json", {}); P = m.get("params", {}); r = jl("research.json", {}) or {}; a = jl("analyst.json", {}) or {}
    cfg = {"engine": m.get("engine"), "params": {k: P.get(k) for k in KEYS if k in P},
           "devig": r.get("devig", "power") if r.get("devig_kabul") else "power", "analist": bool(a.get("kabul")), "auto_lab": P.get("auto_lab")}
    pl = ((jl("daily.json", {}) or {}).get("canli") or {}).get("platt")
    if pl is not None: cfg["canli_platt"] = bool(pl.get("kabul"))   # canlı Platt kalibrasyonu (toplayıcı, zaman sıralı sınama)
    if P.get("cal_yol"): cfg["cal_yol"] = P["cal_yol"]               # ml70: calT/gscale/dk hangi yolda öğrenildi ('sunulan' / 'model')
    ek = jl("acik/elo_kupa.json", None)                                # 🌐 açık veri: Club Elo → kupa güçleri bayrağı (lab/acik_lab.py)
    if ek is not None: cfg["elo_kupa"] = bool(ek.get("aktif"))
    return cfg

def recs_between(d0, d1):
    return [r for _, r in arsiv.kayitlar(DATA, d0, d1)]

def brier(rs): return sum((r["rp"] - r["ok"]) ** 2 for r in rs) / len(rs)

def brier_srv(rs):
    """ml80: uygulamanın gösterdiği öneri (toplayıcı 'sp'/'sok'; calT/gscale/dk dahil). rp bu ayarlardan etkilenmediği için
    kalibrasyon değişiklikleri ancak bununla izlenebilir."""
    v = [r for r in rs if r.get("sp") is not None and r.get("sok") is not None]
    return (sum((r["sp"] - r["sok"]) ** 2 for r in v) / len(v), len(v)) if v else (None, 0)

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
            for k in ("devig", "analist", "auto_lab", "canli_platt", "cal_yol", "elo_kupa"):
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
        (s0, n0), (s1, n1) = brier_srv(before), brier_srv(after)
        if n0 >= MIN_N and n1 >= MIN_N:   # iki dönemde de yeterli 'sunulan' kayıt varsa ölçüt odur (kalibrasyon değişikliklerini görür)
            ch["olcut"] = "sunulan"; ch["brier_ham_once"], ch["brier_ham_sonra"] = ch["brier_once"], ch["brier_sonra"]
            b0, b1 = s0, s1; ch["brier_once"], ch["brier_sonra"] = round(b0, 4), round(b1, 4)
        if b1 > b0 + MARGIN and not rb.get("aktif"):
            prev = log["degisiklikler"][i - 1]["config"]
            ch["durum"] = "GERİ ALINDI"
            rb = {"aktif": True, "baslangic": today, "bitis": (date.fromisoformat(today) + timedelta(days=FREEZE_DAYS)).isoformat(),
                  "neden": f"{d} tarihli değişiklikten sonra isabet kötüleşti (Brier {b0:.4f} → {b1:.4f})", "params": prev.get("params"),
                  "devig": prev.get("devig", "power"), "analist": prev.get("analist", False), "canli_platt": prev.get("canli_platt", False),
                  "cal_yol": prev.get("cal_yol", "model"), "elo_kupa": prev.get("elo_kupa", False), "gecmis": (rb.get("gecmis") or [])[-10:] + [d]}
        elif len(after) >= MIN_N:
            ch["durum"] = "kalıcı (isabet korunuyor)"
    # 📈 Gelişim günlüğü: uygulamada gösterilen, sistemin kendi kendine yaptığı gelişmeler ve ölçümler
    G = jl("gelisim.json", {"olaylar": []}) or {"olaylar": []}; ev = G["olaylar"]
    def add(tur, baslik, detay, anahtar):
        if any(e.get("anahtar") == anahtar for e in ev): return
        ev.append({"tarih": today, "tur": tur, "baslik": baslik, "detay": detay, "anahtar": anahtar})
    NM = {"devig": "Bahis marjı ayırma yöntemi", "analist": "Lig güven katsayıları", "auto_lab": "Laboratuvar karışımı", "motor sürümü": "Motor sürümü", "canli_platt": "Canlı olasılık kalibrasyonu (Platt)",
          "cal_yol": "Olasılık kalibrasyonunun öğrenildiği yol", "elo_kupa": "Kupa güçlerinde Club Elo (açık veri)"}
    for ch in log["degisiklikler"]:
        f = ch.get("fark") or {}
        for k, (a, b) in f.items():
            if k in NM: add("gelisme", f"{NM[k]} güncellendi", f"{a} → {b}", f"{ch['tarih']}-{k}-{b}")
        pk = [k for k in f if k in KEYS]
        if pk: add("ogrenme", "Motor ayarlarını yeni maçlarla yeniden öğrendi", ", ".join(f"{k} {f[k][0]}→{f[k][1]}" for k in pk[:4]), f"{ch['tarih']}-ayar")
        if ch.get("durum") == "GERİ ALINDI": add("geri", "Koruyucu bir değişikliği geri aldı", rb.get("neden", ""), f"{ch['tarih']}-geri")
        if ch.get("durum", "").startswith("kalıcı"): add("onay", "Değişiklik kalıcı oldu", f"{ch['tarih']} tarihli değişiklikten sonra isabet korundu", f"{ch['tarih']}-kalici")
    A = jl("arena.json", {}) or {}
    if A.get("tarih"):
        u = A.get("uygula") or {}
        if u.get("1x2") or u.get("ou"): add("gelisme", "Robot konseyi devreye girdi", A.get("karar", ""), f"{A['tarih']}-konsey-on")
        else: add("olcum", "Robot arenası haftalık savaşı", A.get("karar", ""), f"{A['tarih']}-arena")
    L = jl("auto_lab.json", {}) or {}
    if L.get("tarih"): add("olcum", "Laboratuvar: açık kaynak modellerle yarış", (L.get("karar") or {}).get("aciklama", ""), f"{L['tarih']}-lab")
    D = jl("daily.json", {}) or {}
    for g in (D.get("gunler") or [])[-3:]:
        if g.get("n", 0) >= 20 and g["d"] < today:
            gu = g.get("guclu") or {}
            add("karne", f"{g['d']} karnesi", f"{g['n']} kilitli öneri, %{round(g['hit'] * 100)} tuttu" + (f"; güçlü önerilerin %{round(gu['hit'] * 100)}'i ({gu['n']} öneri)" if gu.get("n") else ""), f"{g['d']}-karne")
    C = (D.get("canli") or {})
    if C.get("n", 0) >= 50: add("karne", "Canlı karne", f"{C['n']} kilitli canlı seçim, %{round(C['hit'] * 100)} tuttu", f"{today}-canli")
    G["olaylar"] = ev[-150:]; G["guncel"] = today
    json.dump(G, open(os.path.join(DATA, "gelisim.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(log, open(os.path.join(DATA, "changes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(rb, open(os.path.join(DATA, "rollback.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Koruyucu: {len(log['degisiklikler'])} kayıtlı değişiklik; geri alma {'AKTİF: ' + rb['neden'] if rb.get('aktif') else 'yok'}")

if __name__ == "__main__":
    main()
