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


URL_RE = re.compile(r"""["'`]((?:https?:)?//[a-z0-9.\-]*atyarisi\.com[^"'`\s]*|/[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-{}.$]+)*/(?:[A-Za-z0-9_\-]*(?:[Pp]rogram|[Aa]gf|AGF|[Rr]esult|[Ss]onuc|[Bb]ulten|[Rr]ace|[Hh]orse|[Kk]osu|[Ss]tatist|[Cc]ontent|[Pp]age|[Hh]elp)[A-Za-z0-9_\-{}.$?=&/]*))["'`]""")
GIZLI = re.compile(r"(token|key|secret|auth)[\w]*\s*[=:]\s*['\"][^'\"]{6,}['\"]", re.I)


def cevre(t, kelime, n=6, w=250):
    return [t[max(0, m.start() - w): m.end() + w] for m in re.finditer(kelime, t)][:n]


def p2(out):
    st, h, _ = get(KOK + "/tjk-at-yarisi-programi")
    inl = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", h, re.S | re.I)
    cfg = [GIZLI.sub(r"\1=<gizlendi>", s.strip())[:12000] for s in inl
           if re.search(r"WebsiteUrl|Site\.Init|RefreshTimeInMiliseconds|selectedBultenMenu|ApiUrl|injectReactApps", s)]
    out["program_config_scriptleri"] = cfg
    out["program_hostlar"] = sorted(set(re.findall(r"https?://[a-z0-9.\-]+atyarisi\.com", h)))
    out["program_govde_idleri"] = sorted(set(re.findall(r'id="([^"]+)"', h)))[:200]
    srcs = [s if s.startswith("http") else "https:" + s for s in re.findall(r'<script[^>]+src=["\']([^"\']+)', h, re.I)]
    out["jsler"] = {}
    loader = [s for s in srcs if "react-app-loader" in s]
    for u in loader + [s for s in srcs if "NesineAllJS" in s]:
        st, js, _ = get(u, "*/*", 15_000_000)
        out["jsler"][u] = {"durum": st, "uzunluk": len(js), "urller": sorted(set(URL_RE.findall(js)))[:300],
                           "inject_cevre": cevre(js, r"injectReactApp\w*|manifest|ReactApps?Url|reactApp", 8, 400),
                           "tjk_cevre": cevre(js, r"tjkbulten|tjkgw|Program|AGF|Agf", 12, 200)}
    # yükleyicinin işaret ettiği manifest/uygulama listesi
    manifestler = set()
    for u, v in out["jsler"].items():
        for x in v["urller"]:
            if re.search(r"manifest|apps?\.json|asset", x, re.I):
                manifestler.add(x)
        for c in v["inject_cevre"]:
            for x in re.findall(r"""["']((?:https?:)?//[^"']+\.json[^"']*|/[^"']+\.json[^"']*)["']""", c):
                manifestler.add(x)
    out["manifest_adaylari"] = sorted(manifestler)[:30]
    out["manifestler"] = {}
    for m in sorted(manifestler)[:4]:
        u = m if m.startswith("http") else ("https:" + m if m.startswith("//") else "https://sc.atyarisi.com" + m)
        st, t, _ = get(u, "application/json")
        out["manifestler"][u] = {"durum": st, "uzunluk": len(t), "metin": t[:20000]}
    # hostların robots.txt'leri
    out["robots_alt"] = {}
    for host in ["tjkbulten.atyarisi.com", "tjkgw.atyarisi.com", "content.atyarisi.com", "sc.atyarisi.com"]:
        st, t, _ = get(f"https://{host}/robots.txt", "text/plain")
        out["robots_alt"][host] = {"durum": st, "metin": t[:1500]}


STR_RE = re.compile(r"""["'`](/[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-{}.$:]*)*(?:\?[^"'`\s]*)?)["'`]""")


def js_ozet(js, kelimeler):
    yollar = sorted(set(x for x in STR_RE.findall(js) if 3 < len(x) < 120 and not x.endswith((".css", ".png", ".svg", ".jpg", ".woff2"))))
    return {"uzunluk": len(js), "yollar": yollar[:400], "urller": sorted(set(URL_RE.findall(js)))[:100],
            "cevre": {k: cevre(js, k, 10, 220) for k in kelimeler}}


def p3(out):
    sc = "https://sc.atyarisi.com/10979123351/www/nsn-react/public/js/"
    st, js, _ = get(sc + "StaticPages.min.js", "*/*", 15_000_000)
    out["staticpages"] = dict(js_ozet(js, ["ContentMicroUrl", "kullanim", "Kullanım", "api/", "fetch\\(", "axios"]), durum=st)
    st, js, _ = get(sc + "TJK.min.js", "*/*", 25_000_000)
    out["tjk_js"] = dict(js_ozet(js, ["TjkApiUrl", "TjkGwApiUrl", "WebsiteUrl", "AGF", "Agf", "Handikap", "Program",
                                      "RaceResult", "StartDate"]), durum=st)
    st, t, _ = get(KOK + "/sitemap.xml", "application/xml")
    out["sitemap"] = {"durum": st, "uzunluk": len(t), "loc": re.findall(r"<loc>(.*?)</loc>", t)[:80]}
    for host in ["help.atyarisi.com", "rt.atyarisi.com", "comment.atyarisi.com"]:
        st, t, _ = get(f"https://{host}/robots.txt", "text/plain")
        out.setdefault("robots_alt", {})[host] = {"durum": st, "metin": t[:800]}


def p4(out):
    """Kullanım şartları metni: StaticPages paketindeki 'kullanim-sartlari' bileşeninin metni (gömülü ise)."""
    sc = "https://sc.atyarisi.com/10979123351/www/nsn-react/public/js/"
    st, js, _ = get(sc + "StaticPages.min.js", "*/*", 15_000_000)
    out["durum"] = st
    m = re.search(r'path:"/hakkimizda/kullanim-sartlari",component:([A-Za-z_$][\w$]*)', js)
    comp = m.group(1) if m else None
    out["bilesen"] = comp
    tanim = []
    if comp:
        for mm in re.finditer(r"[,;\s]" + re.escape(comp) + r"=(?:function|\(|[A-Za-z_$])", js):
            tanim.append(js[mm.start(): mm.start() + 2500])
    out["bilesen_tanim"] = tanim[:4]
    # Uzun Türkçe metin parçaları (sırasıyla), şart metnine özgü kelimeleri içerenlerin çevresi
    strs = [(mm.start(), mm.group(1)) for mm in re.finditer(r'"((?:[^"\\]|\\.){60,})"', js)]
    tr = [(i, s) for i, s in strs if re.search(r"[şğıüçŞĞİÜÇ]", s)]
    anahtar = re.compile(r"kullanım şart|kullanim|işbu|site(?:mizi|nin|de)|telif|fikri|kopyala|çoğalt|izin|otomatik|robot|yazılım|ticari", re.I)
    sec = [s for i, s in tr if anahtar.search(s)]
    out["tr_metin_sayisi"] = len(tr)
    out["sart_adaylari"] = sec[:200]
    out["sart_toplam_uzunluk"] = sum(len(s) for s in sec)


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
    elif hedef == "p2":
        p2(out)
    elif hedef == "p3":
        p3(out)
    elif hedef == "p4":
        p4(out)
    out["istek_sayisi"] = SAYAC["n"]
    json.dump(out, open(f"lab/kesif/atyarisi/{hedef}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("tamam", SAYAC["n"], "istek")


if __name__ == "__main__":
    main()
