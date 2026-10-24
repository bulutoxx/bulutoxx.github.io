import json, re, urllib.request
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30).read().decode("utf-8", "replace")
out = {"hosts": set(), "paths": set(), "ws": set()}
pages = ["https://www.iddaa.com/", "https://www.iddaa.com/program/canli/futbol", "https://www.iddaa.com/canli-skor"]
js = set()
for p in pages:
    try:
        h = get(p); out.setdefault("pages", {})[p] = len(h)
        js |= {("https://www.iddaa.com" + s) if s.startswith("/") else s for s in re.findall(r'src="([^"]+\.js)"', h)}
    except Exception as e: out.setdefault("pages", {})[p] = str(e)[:100]
out["n_js"] = len(js)
for u in sorted(js)[:80]:
    try: t = get(u)
    except Exception: continue
    out["hosts"] |= set(re.findall(r'https?://[a-z0-9.-]*iddaa\.com', t))
    out["ws"] |= set(re.findall(r'wss?://[a-z0-9./-]+', t))
    for m in re.findall(r'["\'`](/[a-zA-Z0-9_\-/]*(?:score|live|canli|statistic|event|match)[a-zA-Z0-9_\-/]*)', t): out["paths"].add(m)
    for m in re.finditer(r'.{80}(?:livescore|liveScore|scoreboard|matchTracker|getScores).{120}', t): out.setdefault("ctx", []).append(m.group(0)[:200])
out = {k: sorted(v) if isinstance(v, set) else v for k, v in out.items()}
out["ctx"] = out.get("ctx", [])[:40]
json.dump(out, open("lab/iddaa_probe.json", "w"), ensure_ascii=False, indent=1)
