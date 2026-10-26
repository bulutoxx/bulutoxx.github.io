"""🧹 Veri ve güvenlik denetçisi (her gün).
Veri: aynı maçın iki kez kaydı, imkânsız skor, bir takımın iki tarafta görünmesi, uzun süredir güncellenmeyen lig,
anormal bahis marjı, bülten eşleşme oranı. Güvenlik: depoya yanlışlıkla gizli anahtar/şifre yazılmış mı.
Çıktı: data/dq.json; ciddi sorun varsa iş akışı uyarı kaydı açar."""
import json, os, re, glob, collections
from datetime import date, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

def main():
    out = {"tarih": date.today().isoformat(), "ciddi": [], "uyari": [], "bilgi": {}}
    try: S = json.load(open(os.path.join(DATA, "season.json"), encoding="utf-8"))
    except Exception as e: out["ciddi"].append(f"season.json okunamadı: {e}"); S = {}
    today = date.today()
    dup = bad = same = odd_bad = 0; stale = []
    for lg, d in S.items():
        ms = d.get("matches", []); seen = set()
        for m in ms:
            k = (m.get("d"), m.get("h"), m.get("a"))
            if k in seen: dup += 1
            seen.add(k)
            ft = m.get("ft") or [0, 0]
            if any(x is None or x < 0 or x > 15 for x in ft[:2]): bad += 1
            if m.get("h") == m.get("a"): same += 1
            o = m.get("odds")
            if o and all(o):
                ov = sum(1 / x for x in o)
                if ov < 0.98 or ov > 1.35: odd_bad += 1
        if ms and not d.get("cup"):
            last = max(m["d"] for m in ms)
            if last < (today - timedelta(days=45)).isoformat() and d.get("asOf", "") >= (today - timedelta(days=200)).isoformat():
                stale.append(f"{lg} ({last})")
    out["bilgi"].update({"lig": len(S), "mac": sum(len(d.get("matches", [])) for d in S.values()), "tekrar": dup, "imkansiz_skor": bad,
                         "ayni_takim": same, "anormal_marj": odd_bad})
    if dup > 50: out["uyari"].append(f"{dup} tekrar eden maç kaydı")
    if bad: out["ciddi"].append(f"{bad} imkânsız skor")
    if same: out["ciddi"].append(f"{same} maçta aynı takım iki tarafta (isim eşleme hatası)")
    if odd_bad > 100: out["uyari"].append(f"{odd_bad} maçta anormal piyasa marjı")
    if stale: out["uyari"].append("Uzun süredir yeni maç gelmeyen ligler (sezon arası olabilir): " + ", ".join(stale[:10]))
    try:
        fx = json.load(open(os.path.join(DATA, "fixtures.json"), encoding="utf-8"))
        n_i = sum(1 for f in fx if f.get("iid")); out["bilgi"]["fikstur"] = len(fx); out["bilgi"]["iddaa_eslesen"] = n_i
        if fx and n_i / len(fx) < 0.3: out["uyari"].append(f"Bültenin yalnız %{round(n_i / len(fx) * 100)}'i iddaa ile eşleşiyor")
    except Exception: pass
    # güvenlik: gizli anahtar taraması (yalnız depodaki metin dosyaları)
    pat = re.compile(r"(api[_-]?key|secret|password|şifre|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}", re.I)
    leaks = []
    for f in glob.glob(os.path.join(ROOT, "**", "*.*"), recursive=True):
        if any(x in f for x in ("/.git/", "/node_modules/", "/data/archive/", "season.json", "bk_games.json")) or not f.endswith((".py", ".js", ".mjs", ".html", ".yml", ".json", ".md")): continue
        try:
            if os.path.getsize(f) > 2_000_000: continue
            if pat.search(open(f, encoding="utf-8", errors="ignore").read()): leaks.append(os.path.relpath(f, ROOT))
        except Exception: pass
    if leaks: out["ciddi"].append("Olası gizli anahtar/şifre izi: " + ", ".join(leaks[:5]))
    out["bilgi"]["guvenlik_tarama"] = "temiz" if not leaks else f"{len(leaks)} dosya"
    out["alarm"] = bool(out["ciddi"])
    json.dump(out, open(os.path.join(DATA, "dq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False)[:800])

if __name__ == "__main__":
    main()
