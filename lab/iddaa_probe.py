import json, urllib.request, collections, time
H = {"User-Agent": "Mozilla/5.0 Chrome/130", "Accept": "application/json"}
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30).read())
out = {}
for sp in (1, 2):
    d = get(f"https://statisticsv2.iddaa.com/live-results?sportId={sp}")["data"]
    ev = {e["eventId"]: e for e in d["events"]}; sc = d["sc"]
    out[sp] = {"phase": collections.Counter(e["phase"] for e in d["events"]).most_common(),
               "s": collections.Counter(v["s"] for v in sc.values()).most_common(),
               "phase_s": collections.Counter((ev.get(int(k), {}).get("phase"), v["s"], "min" in v) for k, v in sc.items()).most_common(),
               "min_ornek": [dict(v, ev=ev.get(int(k))) for k, v in sc.items() if "min" in v][:6], "now": time.time(),
               "sc_key_type": type(next(iter(sc))).__name__}
    lv = get(f"https://sportsbookv2.iddaa.com/sportsbook/events?st={sp}&type=1&version=0")["data"]["events"]
    live_ids = [e["i"] for e in lv if e.get("s") == 1]
    out[sp]["sb_live"] = len(live_ids); out[sp]["sb_live_in_sc"] = sum(1 for i in live_ids if str(i) in sc or i in sc)
    out[sp]["sb_live_phase"] = collections.Counter(ev.get(i, {}).get("phase") for i in live_ids).most_common()
json.dump(out, open("lab/iddaa_probe.json", "w"), ensure_ascii=False, indent=1, default=str)
