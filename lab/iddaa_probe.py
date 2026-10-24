import json, urllib.request
H = {"User-Agent": "Mozilla/5.0 Chrome/130", "Accept": "application/json"}
out = {}
for q in ["sportId=1&date=2026-10-23", "sportId=1&eventDate=2026-10-23", "sportId=1&day=-1", "sportId=1&date=23.10.2026"]:
    try:
        d = json.loads(urllib.request.urlopen(urllib.request.Request("https://statisticsv2.iddaa.com/live-results?" + q, headers=H), timeout=30).read())["data"]
        ph = {}
        for e in d["events"]: ph[e["phase"]] = ph.get(e["phase"], 0) + 1
        out[q] = {"date": d.get("date"), "n": len(d["events"]), "phase": ph, "sc": len(d.get("sc", {}))}
    except Exception as e: out[q] = str(e)[:100]
json.dump(out, open("lab/iddaa_probe.json", "w"), ensure_ascii=False, indent=1)
