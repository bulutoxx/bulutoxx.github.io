"""🧩 Uygulama kaynağı okuyucu (Python; lab/_kaynak.cjs ile aynı kural, v143).
index.html ince kabuk; katmanlar js/*.js paketlerinde `/* id: <eski-id> */` işaretiyle, stiller css/*.css'te.
  from _kaynak import tum_kaynak, blok
  tum_kaynak(kok)      → index.html + yüklediği tüm js/ css/ paketleri (sırayla) tek metin
  blok("derbi-v95")    → o bloğun kaynak metni
"""
import os, re

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PAKET = re.compile(r'(?:src|href)="((?:js|css)/[^"?]+)')
_SARMA = re.compile(r'/\* id: ([\w.\-]+) \*/ try \{(.*?)\} catch \(e\) \{[^\n]*?/\* /id: \1 \*/\n', re.S)


def paketler(kok=KOK):
    html = open(os.path.join(kok, "index.html"), encoding="utf-8").read()
    return list(dict.fromkeys(_PAKET.findall(html)))


def tum_kaynak(kok=KOK):
    parca = [open(os.path.join(kok, "index.html"), encoding="utf-8").read()]
    for y in paketler(kok):
        p = os.path.join(kok, y)
        if os.path.isfile(p):
            parca.append(open(p, encoding="utf-8").read())
    return "\n".join(parca)


def blok(bid, kok=KOK):
    html = open(os.path.join(kok, "index.html"), encoding="utf-8").read()
    m = re.search(r'<script id="%s">(.*?)</script>' % re.escape(bid), html, re.S)
    if m:
        return m.group(1)
    for y in paketler(kok):
        if not y.endswith(".js"):
            continue
        t = open(os.path.join(kok, y), encoding="utf-8").read()
        for m in _SARMA.finditer(t):
            if m.group(1) == bid:
                return m.group(2)
        m = re.match(r'/\* id: ([\w.\-]+) \*/(?! try \{)', t)
        if m and m.group(1) == bid:
            return t[m.end():]
    raise KeyError(f"blok bulunamadı: {bid}")
