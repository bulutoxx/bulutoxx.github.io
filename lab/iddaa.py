"""Resmi iddaa bülteni (iddaa.com; robots.txt herkese açık izin verir).
Bilyoner, Nesine, Misli gibi siteler aynı resmi bülteni satar: maç listesi ve oranlar buradan gelir.
Yalnızca maç, saat, lig ve temel oranlar (MS 1X2, 2,5 alt/üst, KG; basketbolda MS, handikap, toplam) alınır.
Sanal/e-spor yarışmaları alınmaz."""
import json, re, urllib.request, difflib, unicodedata
from datetime import datetime, timezone, timedelta

BASE = "https://sportsbookv2.iddaa.com/sportsbook"
UA = {"User-Agent": "Mozilla/5.0 (BULUTOXX; bulten)", "Accept": "application/json"}
SKIP = re.compile(r"(e-?spor|e-?futbol|e-?soccer|esoccer|efootball|e-?basket|ebasket|sanal|virtual|simul|fifa\b|nba ?2k|cyber)", re.I)

def _get(path, timeout=40):
    r = urllib.request.urlopen(urllib.request.Request(f"{BASE}/{path}", headers=UA), timeout=timeout)
    j = json.loads(r.read().decode("utf-8"))
    if not j.get("isSuccess", True): raise RuntimeError(j.get("message") or "iddaa hata")
    return j.get("data")

def _mk(m):
    return {o.get("n"): o.get("odd") for o in (m.get("o") or []) if o.get("odd")}

def fetch(sport, days=7):
    """sport: 1 futbol, 2 basketbol. Dönüş: [{iid, ts(UTC epoch), comp, cc, h, a, mbc, mk:{...}}]"""
    comps = {c["i"]: c for c in (_get("competitions") or [])}
    ev = (_get(f"events?st={sport}&type=0&version=0") or {}).get("events") or []
    now = datetime.now(timezone.utc).timestamp(); lim = now + days * 86400
    out = []
    for e in ev:
        ts = e.get("d") or 0
        if not (now - 3 * 3600 < ts < lim): continue
        c = comps.get(e.get("ci"), {})
        cname = c.get("n") or ""
        if SKIP.search(cname) or SKIP.search(e.get("hn", "")) or SKIP.search(e.get("an", "")): continue
        mk = {}; tots = []
        for m in e.get("m") or []:
            st, sov, o = m.get("st"), m.get("sov"), _mk(m)
            if sport == 1:
                if st == 1 and all(k in o for k in ("1", "0", "2")): mk["ms"] = [o["1"], o["0"], o["2"]]
                elif st == 101 and str(sov) == "2.5" and "Üst" in o and "Alt" in o: mk["ou"] = [o["Üst"], o["Alt"]]
                elif st == 89 and "Var" in o and "Yok" in o: mk["kg"] = [o["Var"], o["Yok"]]
            else:
                if st == 2 and "1" in o and "2" in o: mk["ms"] = [o["1"], o["2"]]
                elif sov not in (None, ""):
                    try: line = float(sov)
                    except ValueError: continue
                    if "Alt" in o and "Üst" in o: tots.append((line, o["Üst"], o["Alt"]))
        if sport != 1:
            bal = lambda x: abs(x[1] - x[2])
            if tots:
                mx = max(t[0] for t in tots); c_ = [t for t in tots if t[0] >= 0.85 * mx]
                mk["tot"] = list(min(c_, key=bal))
        if "ms" not in mk: continue
        out.append({"iid": e.get("i"), "ts": ts, "comp": cname, "ci": e.get("ci"), "cc": (c.get("cid") or "")[:3],
                    "h": (e.get("hn") or "").strip(), "a": (e.get("an") or "").strip(), "mbc": e.get("mbc"), "mk": mk})
    return out

# ---- isim eşleme
STOPW = {"fc", "cf", "sk", "ac", "as", "fk", "sc", "cd", "ud", "club", "de", "the", "afc", "bk", "if", "kulubu", "jk", "sv", "spor", "calcio", "bc", "basketbol", "basket", "basketball"}
def tnorm(s):
    s = unicodedata.normalize("NFKD", (s or "").replace("ı", "i").replace("İ", "I")).encode("ascii", "ignore").decode().lower()
    w = [x for x in re.split(r"[^a-z0-9]+", s) if x and x not in STOPW]
    return " ".join(w)

def sim(a, b):
    x, y = tnorm(a), tnorm(b)
    if not x or not y: return 0.0
    if x == y: return 1.0
    r = difflib.SequenceMatcher(None, x, y).ratio()
    if len(x) >= 4 and len(y) >= 4 and (x in y or y in x): r = max(r, 0.9)
    tx, ty = set(x.split()), set(y.split())
    big = {t for t in tx & ty if len(t) >= 4}
    if big: r = max(r, 0.75 + 0.05 * min(len(big), 3))
    # kısaltma: "Chiangrai Ut" ~ "Chiangrai United"
    if x.split()[0] == y.split()[0] and len(x.split()[0]) >= 5: r = max(r, 0.8)
    return r

def best_name(name, known, cutoff=0.8):
    best, bs = None, 0
    for k in known:
        s = sim(name, k)
        if s > bs: best, bs = k, s
    return best if bs >= cutoff else None
