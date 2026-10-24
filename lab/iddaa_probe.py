import json, urllib.request
H = {"User-Agent": "Mozilla/5.0 Chrome/130", "Accept": "application/json", "Origin": "https://bulutoxx.github.io"}
def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30); b = r.read()
    return r.status, r.headers.get("access-control-allow-origin"), b.decode("utf-8", "replace")
ev = json.loads(get("https://sportsbookv2.iddaa.com/sportsbook/events?st=1&type=1&version=0")[2])["data"]["events"]
lv = [e for e in ev if e.get("s") == 1][:2]
out = {"live": [{k: v for k, v in e.items() if k != "m"} for e in lv]}
e = lv[0] if lv else ev[0]
i, bri, bgi = e["i"], e.get("bri"), e.get("bgi")
S, B = "https://statisticsv2.iddaa.com", "https://sportsbookv2.iddaa.com"
urls = [f"{B}/sportsbook/live-events-for-widget", f"{B}/sportsbook/live-events-for-widget?st=1", f"{B}/sportsbook/upcoming-events-for-widget",
        f"{B}/sportsbook/event/{i}", f"{B}/sportsbook/played-event-percentage",
        f"{S}/live-results/sports", f"{S}/live-results/sports/1", f"{S}/statistics/live-results/sports/1", f"{B}/live-results/sports/1",
        f"{S}/statistics/eventsummary/{i}", f"{S}/statistics/eventsummary/1/{i}", f"{S}/statistics/eventsummary/{bri}",
        f"{S}/statistics/soccer/match-card/{i}", f"{S}/statistics/soccer/match-card/{bri}", f"{S}/statistics/eventcommentary/{i}",
        f"https://commonv2.iddaa.com/live-results/sports", f"https://contentv2.iddaa.com/live-results/sports"]
for u in urls:
    try:
        st, a, t = get(u); out[u] = {"st": st, "acao": a, "len": len(t), "head": t[:1500]}
    except Exception as ex: out[u] = {"hata": str(ex)[:120]}
json.dump(out, open("lab/iddaa_probe.json", "w"), ensure_ascii=False, indent=1)
