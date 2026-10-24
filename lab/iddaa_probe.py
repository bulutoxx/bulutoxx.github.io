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
urls = [f"{S}/statistics/soccer/match-card/{i}", f"{S}/live-results/events/1", f"{S}/live-results/events?sportId=1", f"{S}/live-results/sport/1",
        f"{S}/live-results/1", f"{S}/live-results?sportId=1", f"{S}/live-results/events?sport=1", f"{S}/live-results/matches/1",
        f"{S}/live-results/sports/1/events", f"{S}/live-results/live/1", f"{S}/live-results/events?sportId=1&date=2026-10-24",
        f"{S}/live-results/tournaments/1", f"{S}/live-results/score/{i}", f"{S}/statistics/soccer/scoreboard/{i}", f"{S}/statistics/eventsummary/1/{i}"]
for u in urls:
    try:
        st, a, t = get(u); out[u] = {"st": st, "acao": a, "len": len(t), "head": t[:6000]}
    except Exception as ex: out[u] = {"hata": str(ex)[:120]}
json.dump(out, open("lab/iddaa_probe.json", "w"), ensure_ascii=False, indent=1)
