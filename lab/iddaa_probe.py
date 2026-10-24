"""iddaa.com resmi bülten erişim denemesi: robots.txt + olası bülten uç noktaları. Yalnızca durum ve yapı kaydedilir."""
import json, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (BULUTOXX bulten denemesi)", "Accept": "application/json, text/plain, */*"}
URLS = ["https://www.iddaa.com/robots.txt", "https://sportsbookv2.iddaa.com/robots.txt", "https://www.iddaa.com/",
        "https://sportsbookv2.iddaa.com/sportsbook/events?st=1&type=0&version=0",
        "https://sportsbookv2.iddaa.com/sportsbook/events?st=2&type=0&version=0",
        "https://sportsbookv2.iddaa.com/sportsbook/competitions",
        "https://sportsbookv2.iddaa.com/sportsbook/get_markets_config"]
out = {}
for u in URLS:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25); b = r.read()
        e = {"status": r.status, "len": len(b), "ctype": r.headers.get("content-type")}
        t = b.decode("utf-8", "replace")
        if u.endswith("robots.txt"): e["text"] = t[:3000]
        else:
            try:
                j = json.loads(t); e["keys"] = list(j)[:20] if isinstance(j, dict) else f"list[{len(j)}]"
                d = j.get("data") if isinstance(j, dict) else None
                if isinstance(d, dict):
                    e["data_keys"] = list(d)[:20]
                    evs = d.get("events") or []
                    e["n_events"] = len(evs)
                    if evs: e["ornek"] = json.dumps(evs[0], ensure_ascii=False)[:2500]
                elif isinstance(d, list):
                    e["n_data"] = len(d); e["ornek"] = json.dumps(d[0], ensure_ascii=False)[:1500] if d else None
            except Exception: e["head"] = t[:400]
        out[u] = e
    except Exception as ex:
        out[u] = {"hata": f"{ex.__class__.__name__}: {str(ex)[:200]}"}
json.dump(out, open("lab/iddaa_probe.json", "w"), ensure_ascii=False, indent=1)
