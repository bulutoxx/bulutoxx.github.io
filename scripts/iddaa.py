"""Resmi iddaa bülteni (iddaa.com; robots.txt herkese açık izin verir).
Bilyoner, Nesine, Misli gibi siteler aynı resmi bülteni satar: maç listesi ve oranlar buradan gelir.
Yalnızca maç, saat, lig ve temel oranlar (MS 1X2, 2,5 alt/üst, KG; basketbolda MS, handikap, toplam) alınır.
Futbolda ek pazarlar (çifte şans, 1,5/3,5 A/Ü, İY/2Y sonucu ve A/Ü, İY/MS, MS+2,5, MS+KG, daha gollü yarı) mk["px"]'e
pazar motoru kodlarıyla eklenir (bkz. extra_markets; tanınmayan pazar sessizce atlanır).
Sanal/e-spor yarışmaları alınmaz."""
import json, re, urllib.request, difflib, unicodedata
from datetime import datetime, timezone, timedelta

BASE = "https://sportsbookv2.iddaa.com/sportsbook"
LAST_RAW = []
UA = {"User-Agent": "Mozilla/5.0 (BULUTOXX; bulten)", "Accept": "application/json"}
SKIP = re.compile(r"(e-?spor|e-?futbol|e-?soccer|esoccer|efootball|e-?basket|ebasket|sanal|virtual|simul|fifa\b|nba ?2k|cyber)", re.I)

def _get(path, timeout=40):
    r = urllib.request.urlopen(urllib.request.Request(f"{BASE}/{path}", headers=UA), timeout=timeout)
    j = json.loads(r.read().decode("utf-8"))
    if not j.get("isSuccess", True): raise RuntimeError(j.get("message") or "iddaa hata")
    return j.get("data")

def _mk(m):
    return {o.get("n"): o.get("odd") for o in (m.get("o") or []) if o.get("odd")}

# ---- ek pazarlar (2026-10-26, pazar motoru). Pazar adları resmi pazar tanımından (sportsbook/get_market_config:
# data.m["{t}_{st}"].n, sov yer tutucusu "{0}") okunur; tanım alınamazsa yalnız bilinen alt türler (1 MS, 101 A/Ü, 89 KG).
# Her şey savunmacıdır: tanınmayan pazar / seçenek adı sessizce atlanır, eski alanlar (ms, ou, kg) hiç değişmez.
_CFG = None
def market_config():
    global _CFG
    if _CFG is None:
        try:
            d = _get("get_market_config") or {}
            m = d.get("m") if isinstance(d, dict) else None
            _CFG = {str(k): (v.get("n") or "") for k, v in (m or {}).items() if isinstance(v, dict)}
        except Exception:
            _CFG = {}
    return _CFG

def _low(s):
    return (s or "").replace("İ", "i").replace("I", "ı").lower()

def _res(tok):
    t = tok.strip().upper()
    return {"1": "1", "0": "X", "X": "X", "2": "2"}.get(t)

def _sov(x):
    try: return float(str(x).replace(",", "."))
    except (TypeError, ValueError): return None

_BAD = re.compile(r"(korner|kart|handikap|dakika|ev sahibi|deplasman|takım|tek ?/ ?çift|tam skor|ilk gol|son gol|penalt|kırmızı|aralık|gol sayısı|her iki yarı|kazanır|sıradaki)")
def _kind(name):
    """Pazar adı → tür. Bilinmeyen → None."""
    n = _low(name).replace("altı/üstü", "alt/üst").replace("alt / üst", "alt/üst")
    if _BAD.search(n): return None
    if "hangi yarı" in n and "gol" in n: return "dgy"
    if re.match(r"^ilk yarı ?/ ?maç sonucu\s*$", n): return "iyms"
    if n.startswith("maç sonucu ve alt/üst"): return "msau"
    if n.startswith("maç sonucu ve karşılıklı gol"): return "mskg"
    if n.startswith("çifte şans") and "ve" not in n: return "cs"
    if n.startswith("ilk yarı sonucu") and " ve " not in n: return "iy"
    if (n.startswith("ikinci yarı sonucu") or n.startswith("2. yarı sonucu")) and " ve " not in n: return "2y"
    if (n.startswith("ilk yarı alt/üst") or n.startswith("ilk yarı toplam gol")) and " ve " not in n: return "iyau"
    if (n.startswith("ikinci yarı alt/üst") or n.startswith("2. yarı alt/üst")) and " ve " not in n: return "2yau"
    if (n.startswith("alt/üst") or n.startswith("toplam gol alt/üst") or n == "toplam gol") and " ve " not in n: return "au"
    if n.startswith("karşılıklı gol") and " ve " not in n and "yarı" not in n: return "kg"
    return None

def extra_markets(e):
    """Etkinliğin ek pazar oranları → {kod: oran} (pazar motoru kodları, scripts/pazar.py)."""
    out = {}
    cfg = market_config()
    for m in e.get("m") or []:
        try:
            st, sov, o = m.get("st"), _sov(m.get("sov")), _mk(m)
            o = {str(k).strip(): v for k, v in o.items() if isinstance(v, (int, float)) and v > 1.01}
            if not o: continue
            name = cfg.get(f"{m.get('t')}_{st}") or ""
            kind = _kind(name) if name else {1: "ms", 101: "au", 89: "kg"}.get(st)
            if kind is None and st == 101: kind = "au"
            if kind is None and st == 89: kind = "kg"
            if kind is None: continue
            if kind == "au" and sov in (1.5, 2.5, 3.5) and "Üst" in o and "Alt" in o:
                L = {1.5: "15", 2.5: "25", 3.5: "35"}[sov]; out[f"U{L}"] = o["Üst"]; out[f"A{L}"] = o["Alt"]
            elif kind in ("iyau", "2yau") and sov in (0.5, 1.5) and "Üst" in o and "Alt" in o:
                pre = "IY" if kind == "iyau" else "2Y"; L = {0.5: "05", 1.5: "15"}[sov]; out[f"{pre}U{L}"] = o["Üst"]; out[f"{pre}A{L}"] = o["Alt"]
            elif kind == "kg" and "Var" in o and "Yok" in o:
                out["KGV"] = o["Var"]; out["KGY"] = o["Yok"]
            elif kind in ("iy", "2y"):
                r = {_res(k): v for k, v in o.items() if _res(k)}
                if len(r) == 3:
                    pre = "IY" if kind == "iy" else "2Y"
                    for k, v in r.items(): out[f"{pre}{k}"] = v
            elif kind == "cs":
                r = {}
                for k, v in o.items():
                    t = [x for x in re.split(r"[^0-9A-Za-z]+", k) if x]
                    if len(t) == 1 and len(t[0]) == 2: t = list(t[0])
                    rr = sorted({_res(x) for x in t if _res(x)}, key="1X2".index)
                    if len(rr) == 2: r["".join(rr)] = v
                if len(r) == 3:
                    out.update(r)
            elif kind == "iyms":
                r = {}
                for k, v in o.items():
                    t = [x for x in re.split(r"[^0-9A-Za-z]+", k) if x]
                    if len(t) == 2 and _res(t[0]) and _res(t[1]): r[f"IYMS_{_res(t[0])}_{_res(t[1])}"] = v
                if len(r) == 9: out.update(r)
            elif kind in ("msau", "mskg"):
                if kind == "msau" and sov not in (None, 2.5): continue
                r = {}
                for k, v in o.items():
                    kl = _low(k); t = [x for x in re.split(r"[^0-9a-zçğıöşü]+", kl) if x]
                    rs = [_res(x) for x in t if _res(x)]
                    if len(rs) != 1: continue
                    if kind == "msau":
                        side = "U" if any(x.startswith("üst") for x in t) else "A" if any(x.startswith("alt") for x in t) else None
                        if side: r[f"{rs[0]}&{side}25"] = v
                    else:
                        side = "V" if "var" in t else "Y" if "yok" in t else None
                        if side: r[f"{rs[0]}&KG{side}"] = v
                if len(r) == 6: out.update(r)
            elif kind == "dgy":
                r = {}
                for k, v in o.items():
                    kl = _low(k)
                    if "eşit" in kl or kl.strip() in ("x", "0"): r["DGYE"] = v
                    elif kl.strip().startswith("1") or "ilk" in kl: r["DGY1"] = v
                    elif kl.strip().startswith("2") or "ikinci" in kl: r["DGY2"] = v
                if len(r) == 3: out.update(r)
        except Exception:
            continue
    return out

def market_names(evs_raw, limit=400):
    """Teşhis: bültende görülen pazar adları ve seçenek adları (oran değeri yok). Bir sonraki ayrıştırma iyileştirmesi için."""
    cfg = market_config(); seen = {}
    for e in evs_raw[:limit]:
        for m in e.get("m") or []:
            k = f"{m.get('t')}_{m.get('st')}"
            if k not in seen: seen[k] = {"ad": cfg.get(k, ""), "secenek": sorted({str(o.get("n")) for o in (m.get("o") or [])})[:12], "n": 0,
                                         "tur": _kind(cfg.get(k, "")) if cfg.get(k) else None}
            seen[k]["n"] += 1
    return seen

def fetch(sport, days=7):
    """sport: 1 futbol, 2 basketbol. Dönüş: [{iid, ts(UTC epoch), comp, cc, h, a, mbc, mk:{...}}]"""
    comps = {c["i"]: c for c in (_get("competitions") or [])}
    ev = (_get(f"events?st={sport}&type=0&version=0") or {}).get("events") or []
    now = datetime.now(timezone.utc).timestamp(); lim = now + days * 86400
    out = []
    global LAST_RAW
    LAST_RAW = ev if sport == 1 else LAST_RAW
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
                if st == 1 and all(o.get(k, 0) > 1.01 for k in ("1", "0", "2")): mk["ms"] = [o["1"], o["0"], o["2"]]
                elif st == 101 and str(sov) == "2.5" and "Üst" in o and "Alt" in o: mk["ou"] = [o["Üst"], o["Alt"]]
                elif st == 89 and "Var" in o and "Yok" in o: mk["kg"] = [o["Var"], o["Yok"]]
            else:
                if st == 2 and o.get("1", 0) > 1.01 and o.get("2", 0) > 1.01: mk["ms"] = [o["1"], o["2"]]
                elif sov not in (None, ""):
                    try: line = float(sov)
                    except ValueError: continue
                    if "Alt" in o and "Üst" in o: tots.append((line, o["Üst"], o["Alt"]))
        if sport != 1:
            bal = lambda x: abs(x[1] - x[2])
            if tots:
                mx = max(t[0] for t in tots); c_ = [t for t in tots if t[0] >= 0.85 * mx and t[0] >= 110]   # maç toplamı (yarı/çeyrek değil)
                if c_: mk["tot"] = list(min(c_, key=bal))
        if "ms" not in mk: continue
        if sport == 1:
            try:
                px = extra_markets(e)
                if px: mk["px"] = px
            except Exception: pass
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
