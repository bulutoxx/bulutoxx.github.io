"""🗄️ Kilitli öneri arşivinin kalıcı katmanı (yalnız standart kütüphane; motor, toplayıcı ve tüm lab botları kullanır).

Eskiden toplayıcı 120 günden eski arşiv günlerini SİLİYORDU; sistemin tek gerçek ölçüm verisi (iddaa oranı + kilitli öneri +
sonuç) kayboluyordu. 2026-10-25 (ml70) itibarıyla:
  - data/archive/GGGG-AA-GG.json  son 120 gün (uygulama son 30 günü okur; biçim değişmedi)
  - data/archive/eski/GGGG-AA-GG.json  daha eski günler: yalnız puanlanmış kayıtlar, 'lam' alanı atılmış. Bir kez yazılır,
    bir daha değişmez (git'te gün gün büyüme yok). Hiçbir kayıt silinmez.
kayitlar() iki katmanı birlikte okur; aynı gün iki yerde varsa güncel dosya önceliklidir."""
import json, os, glob
from datetime import date, timedelta

ESKI = "eski"
ATILAN = ("lam",)          # yeniden hesaplanabilir alanlar (oranlardan)

def _jl(p):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception: return None

def gunler(data_dir):
    """{gün: dosya yolu} — güncel katman eski katmanı ezer."""
    arc = os.path.join(data_dir, "archive"); out = {}
    for f in glob.glob(os.path.join(arc, ESKI, "*.json")): out[os.path.basename(f)[:10]] = f
    for f in glob.glob(os.path.join(arc, "*.json")): out[os.path.basename(f)[:10]] = f
    return out

def kayitlar(data_dir, d0=None, d1=None, puanli=True):
    """[(gün, kayıt)] gün sırasıyla. d0 ≤ gün < d1. puanli=True: yalnız sonucu işlenmiş ve önerisi olan kayıtlar."""
    out = []
    for d, f in sorted(gunler(data_dir).items()):
        if (d0 and d < d0) or (d1 and d >= d1): continue
        recs = _jl(f) or {}
        for k, r in recs.items():
            if puanli and (r.get("ok") is None or not r.get("rp")): continue
            out.append((d, dict(r, _id=k)))
    return out

def sikistir(data_dir, keep_days, today):
    """keep_days'ten eski gün dosyalarını eski/ katmanına taşı (silmeden). Dönen: taşınan gün sayısı."""
    arc = os.path.join(data_dir, "archive"); dst = os.path.join(arc, ESKI)
    cut = (today - timedelta(days=keep_days)).isoformat(); n = 0
    for f in sorted(glob.glob(os.path.join(arc, "*.json"))):
        d = os.path.basename(f)[:10]
        if d >= cut: continue
        recs = _jl(f)
        if recs is None: continue           # bozuk dosyaya dokunma
        keep = {k: {kk: vv for kk, vv in r.items() if kk not in ATILAN} for k, r in recs.items() if r.get("ok") is not None}
        old = _jl(os.path.join(dst, f"{d}.json")) or {}
        if not keep and not old:            # o gün hiç sonuçlanmış öneri yok: boş dosya yazılmaz
            os.remove(f); n += 1; continue
        os.makedirs(dst, exist_ok=True)
        old.update(keep)
        with open(os.path.join(dst, f"{d}.json"), "w", encoding="utf-8") as fo:
            json.dump({k: old[k] for k in sorted(old)}, fo, ensure_ascii=False, separators=(",", ":"))
        os.remove(f); n += 1
    return n

def ozet(data_dir):
    """Veritabanı büyüklüğü (uygulama/Motor sayfası için): gün, kayıt, puanlı kayıt, ilk gün."""
    g = gunler(data_dir); n = p = 0
    for d, f in g.items():
        recs = _jl(f) or {}; n += len(recs); p += sum(1 for r in recs.values() if r.get("ok") is not None)
    return {"gun": len(g), "kayit": n, "puanli": p, "ilk": min(g) if g else None, "eski_gun": sum(1 for f in g.values() if os.sep + ESKI + os.sep in f)}
