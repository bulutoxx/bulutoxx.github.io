import json, urllib.request, collections
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://bulutoxx.github.io"}
B = "https://sportsbookv2.iddaa.com/sportsbook"
out = {}
for u in [f"{B}/events?st=1&type=1&version=0", f"{B}/events?st=1&type=2&version=0", f"{B}/events?st=1&type=0&version=0",
          f"{B}/live-events?st=1", f"{B}/livescore", "https://sportsbookv2.iddaa.com/livescore/events?st=1",
          "https://statistics.iddaa.com/api/livescore?sportId=1", "https://sportsbook.iddaa.com/sportsbook/events?st=1&type=1&version=0",
          "https://www.iddaa.com/canli-futbol"]:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30); b = r.read()
        e = {"status": r.status, "len": len(b), "acao": r.headers.get("access-control-allow-origin"), "ctype": r.headers.get("content-type")}
        try:
            j = json.loads(b); d = j.get("data") if isinstance(j, dict) else j
            ev = d.get("events") if isinstance(d, dict) else d
            if isinstance(ev, list):
                e["n"] = len(ev)
                e["keys"] = collections.Counter(k for x in ev[:200] if isinstance(x, dict) for k in x).most_common(40)
                lv = [x for x in ev if isinstance(x, dict) and (x.get("s") not in (0, None) or x.get("bp"))]
                e["n_live_like"] = len(lv)
                smp = (lv or ev)[:2]
                e["ornek"] = [{k: v for k, v in x.items() if k != "m"} for x in smp if isinstance(x, dict)]
            else: e["head"] = str(j)[:600]
        except Exception: e["head"] = b[:300].decode("utf-8", "replace")
        out[u] = e
    except Exception as ex: out[u] = {"hata": str(ex)[:200]}
json.dump(out, open("lab/iddaa_probe.json", "w"), ensure_ascii=False, indent=1)
