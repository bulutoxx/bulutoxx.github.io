"""🛡️ Bekçi botu (15 dakikada bir): sistemin nabzını tutar. Motor, toplayıcı ve canlı kayıt zamanında çalışıyor mu?
Sorun varsa data/health.json'da işaretler (uygulama kullanıcıya 'veriler gecikiyor' der) ve iş akışı GitHub'da bir uyarı kaydı (issue) açar."""
import json, os, glob
from datetime import datetime, timezone
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

def age_h(s):
    if not s: return None
    try:
        s = s.replace(" UTC", "").replace("Z", "")
        dt = datetime.fromisoformat(s.replace(" ", "T")) if "T" in s or " " in s else datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc) if "T" in s else dt
        return (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600
    except Exception: return None

def main():
    chk = {}
    try:
        m = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))
        # model.updated İstanbul saatiyle "YYYY-MM-DD HH:MM"
        u = m.get("updated", ""); dt = datetime.fromisoformat(u.replace(" ", "T") + ":00+03:00") if u else None
        chk["motor"] = round((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 2) if dt else None
    except Exception: chk["motor"] = None
    try: chk["toplayici"] = round(age_h(json.load(open(os.path.join(DATA, "daily.json"), encoding="utf-8")).get("updated")), 2)
    except Exception: chk["toplayici"] = None
    lf = sorted(glob.glob(os.path.join(DATA, "archive", "live", "*.json")))
    chk["canli_kayit"] = round((datetime.now(timezone.utc).timestamp() - os.path.getmtime(lf[-1])) / 3600, 2) if lf else None
    err = os.path.exists(os.path.join(DATA, "engine_error.txt"))
    sorun = []
    if chk["motor"] is None or chk["motor"] > 3: sorun.append(f"Motor {chk['motor']} saattir güncellemedi")
    if chk["toplayici"] is None or chk["toplayici"] > 3: sorun.append(f"Veri toplayıcı {chk['toplayici']} saattir çalışmadı")
    if err: sorun.append("Motor son çalışmada hata verdi (data/engine_error.txt)")
    out = {"zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "yas_saat": chk, "sorun": sorun, "alarm": bool(sorun)}
    json.dump(out, open(os.path.join(DATA, "health.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()
