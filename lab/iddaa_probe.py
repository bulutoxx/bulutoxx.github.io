import json, urllib.request
H = {"User-Agent": "Mozilla/5.0 Chrome/130", "Accept": "application/json"}
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40).read())
out = {}
for sp in (1, 2):
    lr = get(f"https://statisticsv2.iddaa.com/live-results?sportId={sp}")
    d = lr["data"]; keep = {e["eventId"] for e in d["events"] if e["phase"] == 1}
    ev = get(f"https://sportsbookv2.iddaa.com/sportsbook/events?st={sp}&type=1&version=0")
    keep |= {e["i"] for e in ev["data"]["events"] if e.get("s") == 1}
    d["events"] = [e for e in d["events"] if e["eventId"] in keep]
    d["sc"] = {k: v for k, v in d["sc"].items() if int(k) in keep}
    used = {e["ci"] for e in d["events"]}
    d["competitions"] = {k: v for k, v in d["competitions"].items() if int(k) in used}
    ev["data"]["events"] = [e for e in ev["data"]["events"] if e["i"] in keep]
    out[f"lr{sp}"] = lr; out[f"ev{sp}"] = ev
json.dump(out, open("lab/iddaa_probe.json", "w"), ensure_ascii=False)
