"""Elle teşhis: canlı futbol bülteninde aranan takımın olay kaydı (yalnız o maç)."""
import sys, json, os, urllib.request; sys.path.insert(0, "scripts")
import iddaa as ID
q = os.environ.get("ARA", "Bayern")
ev = (ID._get("events?st=1&type=1&version=0") or {}).get("events") or []
print("canlı olay:", len(ev))
hit = [e for e in ev if q.lower() in ((e.get("hn") or "") + " " + (e.get("an") or "")).lower()]
for e in hit:
    print(json.dumps(e, ensure_ascii=False)[:6000])
try:
    r = json.loads(urllib.request.urlopen(urllib.request.Request("https://statisticsv2.iddaa.com/live-results?sportId=1", headers=ID.UA), timeout=30).read().decode())
    d = r.get("data") or r
    ids = {str(e.get("i")) for e in hit}
    for k, v in (d.get("sc") or {}).items():
        if k in ids: print("skor", k, json.dumps(v, ensure_ascii=False)[:1500])
    for e in d.get("events") or []:
        if str(e.get("eventId")) in ids: print("olay", json.dumps(e, ensure_ascii=False)[:1500])
except Exception as x: print("live-results hata", x)
