# 2. tur: atyarisi.com llms.txt + sayfa yapısı (yalnız birkaç sayfa), sporx yasal uyarı (doğru kodlama). Veri toplamaz.
import json, re, html, time, urllib.request
UA = "Mozilla/5.0 (compatible; BULUTOXX-kaynak-kontrol/0.2; hobi)"
def get(u, enc=None):
    try:
        time.sleep(2); r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=25); b = r.read(600000)
        cs = enc or r.headers.get_content_charset() or "utf-8"
        return r.status, b.decode(cs, "replace")
    except Exception as e: return None, str(e)[:200]
def text(h): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", h or "", flags=re.S | re.I))))
out = {}
st, t = get("https://www.atyarisi.com/llms.txt"); out["atyarisi_llms"] = {"durum": st, "metin": (t or "")[:6000]}
st, h = get("https://www.atyarisi.com/")
links = sorted({m for m in re.findall(r'href=["\']([^"\']+)', h or "")})
out["atyarisi_baglantilar"] = [l for l in links if re.search(r"program|agf|sonuc|bulten|yaris|kosu|handikap|idman|galop|at-|jokey|kullan|yasal|kosul", l, re.I)][:150]
for l in [x for x in out["atyarisi_baglantilar"] if re.search(r"kullan|yasal|kosul|sartlar", x, re.I)][:3]:
    u = l if l.startswith("http") else "https://www.atyarisi.com" + l; s, b = get(u)
    out.setdefault("atyarisi_kosullar", []).append({"url": u, "metin": text(b)[:4000]})
# bir program sayfasının yapısı (yalnız tablo başlıkları)
prog = [x for x in out["atyarisi_baglantilar"] if re.search(r"program", x, re.I)][:1]
for l in prog:
    u = l if l.startswith("http") else "https://www.atyarisi.com" + l; s, b = get(u)
    heads = [re.sub(r"\s+", " ", text(x)).strip() for x in re.findall(r"<th[^>]*>(.*?)</th>", b or "", re.S | re.I)][:60]
    out["atyarisi_program_ornek"] = {"url": u, "durum": s, "tablo_basliklari": heads, "uzunluk": len(b or "")}
s, b = get("https://www.sporx.com/hakkimizda/yasal_uyari.php", "windows-1254"); out["sporx_yasal"] = text(b)[:5000]
json.dump(out, open("lab/kesif/robots.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("tamam")
