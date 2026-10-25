# Yalnız robots.txt ve kullanım koşulu sayfalarını okur (veri sayfası çekmez). Sonucu lab/kesif/robots.json'a yazar.
import json, re, html, time, urllib.request
UA = "Mozilla/5.0 (compatible; BULUTOXX-kaynak-kontrol/0.1; hobi)"
def get(u):
    try:
        time.sleep(1.5); r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=25)
        return r.status, r.read(400000).decode("utf-8", "replace")
    except Exception as e: return None, str(e)[:200]
out = {}
for site in ["https://www.sporx.com", "https://www.habergazetesi.com.tr", "https://www.yarisdergisi.com", "https://www.horseturk.com", "https://www.atyarisi.com"]:
    st, t = get(site + "/robots.txt"); rec = {"robots_durum": st, "robots": (t or "")[:3000]}
    st2, h = get(site + "/")
    links = sorted({m for m in re.findall(r'href=["\']([^"\']+)', h or "") if re.search(r"yasal|kullan|kosul|koşul|gizlilik|terms|telif", m, re.I)})[:15]
    rec["kosul_baglantilari"] = links; rec["kosullar"] = []
    for l in links[:4]:
        u = l if l.startswith("http") else site + ("" if l.startswith("/") else "/") + l
        s3, b = get(u)
        if b:
            body = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", b, flags=re.S | re.I))))
            for m in re.finditer(r"[^.]{0,220}(kopyal|çoğalt|izinsiz|izin alın|otomatik|robot|bot |kazı|scrap|ticari|alıntı|kaynak göster)[^.]{0,220}\.", body, re.I):
                rec["kosullar"].append({"url": u, "cumle": m.group(0).strip()[:450]})
    out[site] = rec
json.dump(out, open("lab/kesif/robots.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("tamam")
