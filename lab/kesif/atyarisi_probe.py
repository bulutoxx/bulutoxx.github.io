# BULUTOXX — atyarisi.com keşif sondası (tek seferlik, keşif dalı). Yalnız www.atyarisi.com (llms.txt izni).
# Nazik: istekler arası >= 2 sn, çalışma başına <= 30 istek, UA "BULUTOXX-hobi/1.0".
# Depoya YALNIZ küçük yapısal özet yazılır (ham HTML yazılmaz). tjk.org'a hiçbir istek atılmaz.
import gzip, html, json, os, re, sys, time, urllib.request
from html.parser import HTMLParser

UA = "BULUTOXX-hobi/1.0"
KOK = "https://www.atyarisi.com"
SAYAC = {"n": 0}
LIMIT = 30
YASAK_HOST = re.compile(r"tjk\.org", re.I)


def get(u, accept="text/html,application/json;q=0.9,*/*;q=0.5", maxb=4_000_000):
    if YASAK_HOST.search(u) or SAYAC["n"] >= LIMIT:
        return None, "", {}
    SAYAC["n"] += 1
    time.sleep(2.2)
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA, "Accept": accept,
                                                                      "Accept-Encoding": "gzip"}), timeout=30)
        b = r.read(maxb)
        if r.headers.get("Content-Encoding") == "gzip":
            b = gzip.decompress(b)
        cs = r.headers.get_content_charset() or "utf-8"
        return r.status, b.decode(cs, "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, "", {}
    except Exception as e:
        return None, f"HATA {type(e).__name__}: {str(e)[:150]}", {}


class Metin(HTMLParser):
    def __init__(self):
        super().__init__(); self.atla = 0; self.p = []
    def handle_starttag(self, t, a):
        if t in ("script", "style", "noscript", "svg"):
            self.atla += 1
        if t in ("p", "br", "li", "h1", "h2", "h3", "h4", "div", "tr"):
            self.p.append("\n")
    def handle_endtag(self, t):
        if t in ("script", "style", "noscript", "svg") and self.atla:
            self.atla -= 1
    def handle_data(self, d):
        if not self.atla:
            self.p.append(d)


def gorunur(h):
    m = Metin(); m.feed(h or "")
    t = "".join(m.p)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def yapi(o, d=0, maxd=6):
    """JSON yapısını (anahtarlar + tür + kısa örnek) döner."""
    if d > maxd:
        return "…"
    if isinstance(o, dict):
        return {k: yapi(v, d + 1, maxd) for k, v in list(o.items())[:60]}
    if isinstance(o, list):
        return [len(o), yapi(o[0], d + 1, maxd)] if o else [0]
    if isinstance(o, str):
        return "str:" + o[:40]
    return f"{type(o).__name__}:{o}"


def sayfa_ozet(u, h):
    out = {"url": u, "uzunluk": len(h)}
    out["title"] = (re.findall(r"<title[^>]*>(.*?)</title>", h, re.S | re.I) or [""])[0].strip()[:120]
    out["script_src"] = sorted(set(re.findall(r'<script[^>]+src=["\']([^"\']+)', h, re.I)))[:60]
    inl = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", h, re.S | re.I)
    out["inline_script"] = [{"len": len(s), "bas": s.strip()[:300]} for s in inl if len(s.strip()) > 40][:40]
    out["json_degisken"] = sorted(set(re.findall(r"(window\.[A-Za-z_$][\w$]*|__NEXT_DATA__|__NUXT__|__INITIAL_STATE__|__STATE__|__APOLLO_STATE__)\s*=?", h)))[:40]
    out["url_adaylari"] = sorted(set(m for m in re.findall(r"""["'](/[A-Za-z0-9_\-/{}.?=&]*(?:api|ajax|json|service|Get|get)[A-Za-z0-9_\-/{}.?=&]*)["']""", h)))[:80]
    out["mutlak_url"] = sorted(set(re.findall(r"https?://[a-z0-9.\-]+", h)))[:60]
    out["data_attr"] = sorted(set(re.findall(r"\s(data-[a-z0-9\-]+)=", h)))[:80]
    # tablolar
    tab = []
    for t in re.findall(r"<table.*?</table>", h, re.S | re.I)[:6]:
        ths = [gorunur(x)[:30] for x in re.findall(r"<th[^>]*>(.*?)</th>", t, re.S | re.I)][:40]
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I)
        ornek = []
        for r in rows[1:3]:
            ornek.append([gorunur(x)[:40] for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S | re.I)][:30])
        tab.append({"th": ths, "satir": len(rows), "ornek": ornek, "class": (re.findall(r'class="([^"]+)"', t[:300]) or [""])[0]})
    out["tablolar"] = tab
    cls = {}
    for c in re.findall(r'class="([^"]+)"', h):
        for x in c.split():
            cls[x] = cls.get(x, 0) + 1
    out["sik_class"] = sorted(cls.items(), key=lambda x: -x[1])[:80]
    # anahtar kelimeler
    kw = {}
    for k in ["AGF", "HP", "KGS", "EİD", "EID", "Orijin", "Takı", "St", "Handikap", "Son 6", "S20", "Jokey", "Kilo", "Ganyan", "apranti", "Apr"]:
        kw[k] = len(re.findall(re.escape(k), h))
    out["anahtar_sayim"] = kw
    vis = gorunur(h)
    out["gorunur_bas"] = vis[:2500]
    i = vis.find("AGF")
    out["gorunur_agf_cevre"] = vis[max(0, i - 600): i + 1500] if i >= 0 else ""
    # gömülü JSON
    m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    if m:
        try:
            out["next_data_yapi"] = yapi(json.loads(m.group(1)))
        except Exception as e:
            out["next_data_yapi"] = f"okunamadı {e}"
    # tarih/arşiv bağlantıları
    out["tarih_linkleri"] = sorted(set(re.findall(r'href="([^"]*(?:20\d\d-\d\d-\d\d|\d\d[./-]\d\d[./-]20\d\d|tarih=)[^"]*)"', h)))[:40]
    out["select_option"] = re.findall(r"<option[^>]*value=\"([^\"]*)\"", h)[:60]
    out["form_action"] = re.findall(r'<form[^>]*action="([^"]*)"', h)[:10]
    return out


def main():
    hedef = sys.argv[1] if len(sys.argv) > 1 else "p1"
    os.makedirs("lab/kesif/atyarisi", exist_ok=True)
    out = {"tur": hedef, "zaman": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ua": UA}
    if hedef == "p1":
        st, t, _ = get(KOK + "/robots.txt", "text/plain"); out["robots"] = {"durum": st, "metin": t[:4000]}
        st, t, _ = get(KOK + "/llms.txt", "text/plain"); out["llms"] = {"durum": st, "metin": t[:3000]}
        st, h, hd = get(KOK + "/hakkimizda/kullanim-sartlari")
        sart = {"durum": st, "uzunluk": len(h)}
        vis = gorunur(h)
        i = vis.find("Kullanım Şartları")
        sart["gorunur_tumu"] = vis[:60000]
        # gömülü JSON / script içindeki uzun Türkçe metinler (şartlar JSON'dan çiziliyor olabilir)
        uzun = []
        for s in re.findall(r"<script[^>]*>(.*?)</script>", h, re.S | re.I):
            for x in re.findall(r'"((?:[^"\\]|\\.){400,})"', s):
                try:
                    x2 = json.loads('"' + x + '"')
                except Exception:
                    x2 = x
                x2 = gorunur(html.unescape(x2))
                if re.search(r"[şğıöüçŞĞİÖÜÇ]", x2):
                    uzun.append(x2[:30000])
        sart["script_metinleri"] = uzun[:10]
        kel = {}
        for k in ["otomatik", "robot", "bot", "örümcek", "tarama", "kazı", "scrap", "kopyala", "çoğalt", "izinsiz",
                  "ticari", "yeniden yayın", "veritabanı", "fikri", "telif", "içerik", "yazılım", "izin"]:
            kel[k] = [vis[max(0, m.start() - 300): m.start() + 300] for m in re.finditer(k, vis, re.I)][:6]
        sart["anahtar_cevre"] = kel
        out["sartlar"] = sart
        for p in ["/tjk-at-yarisi-programi", "/tjk-at-yarisi-muhtemel-agf", "/tjk-at-yarisi-sonuclari",
                  "/tjk-at-yarisi-istatistikler", "/tjk-at-yarisi-bulteni"]:
            st, h, hd = get(KOK + p)
            o = sayfa_ozet(KOK + p, h) if h and st == 200 else {"url": KOK + p, "hata": h[:200]}
            o["durum"] = st; o["content_type"] = hd.get("Content-Type")
            out.setdefault("sayfalar", []).append(o)
    out["istek_sayisi"] = SAYAC["n"]
    json.dump(out, open(f"lab/kesif/atyarisi/{hedef}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("tamam", SAYAC["n"], "istek")


if __name__ == "__main__":
    main()
