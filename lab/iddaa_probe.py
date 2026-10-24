import json, urllib.request, collections
H = {"User-Agent": "Mozilla/5.0 Chrome/130", "Accept": "application/json"}
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30).read())
out = {}
for sp in (1, 2):
    d = get(f"https://statisticsv2.iddaa.com/live-results?sportId={sp}")["data"]
    o = {"keys": list(d), "types": {k: type(v).__name__ for k, v in d.items()}}
    for k, v in d.items():
        if k == "competitions": continue
        if isinstance(v, dict): o[k + "_n"] = len(v); smp = list(v.values())[:1]
        elif isinstance(v, list): o[k + "_n"] = len(v); smp = v[:1]
        else: o[k] = v; continue
        o[k + "_ornek"] = smp
        items = list(v.values()) if isinstance(v, dict) else v
        o[k + "_alanlar"] = collections.Counter(kk for x in items if isinstance(x, dict) for kk in x).most_common(60)
        # canlı olanlardan örnek
        lv = [x for x in items if isinstance(x, dict) and any(str(x.get(f)).lower() in ("1", "true", "live", "inprogress") for f in ("s", "st", "status", "il", "isLive", "live"))]
        o[k + "_canli_ornek"] = lv[:3]
    out[sp] = o
json.dump(out, open("lab/iddaa_probe.json", "w"), ensure_ascii=False, indent=1, default=str)
