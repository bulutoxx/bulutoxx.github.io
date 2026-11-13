#!/usr/bin/env python3
"""📦 Yayın listesi: GitHub Pages'e yalnız uygulamanın gerçekten istediği dosyalar çıkar (denetim P1 #8).

Eskiden deploy işi tüm depoyu (`path: .`) yüklüyordu: lab/, scripts/, data/derin/, robot iç verisi de yayındaydı.
Bu betik listeyi otomatik çıkarır:
  1) Kök uygulama dosyaları: index.html, sw.js, manifest.webmanifest, brain-worker.js, yayin.json (yayın kapısı kaydı).
  2) index.html, sw.js (SHELL), manifest.webmanifest, brain-worker.js ve uygulama paketleri (js/*.js, css/*.css; v143'ten beri
     index.html ince kabuk, katmanlar bu paketlerde) içindeki yol dizeleri: "data/…", "icons/…", "ses/…", "js/…", "css/…".
     - Düz yol ("data/ratings.json?t=" → data/ratings.json) olduğu gibi alınır.
     - Klasör önekli dinamik yol ("data/at/canli/"+gün+".json") → o klasördeki *.json (alt klasöre inmez).
     - Şablon (`data/archive/${d}.json`) → data/archive/*.json.
  3) Bilinen dinamik yollar (BILINEN): betikte tarama kaçırsa bile hep eklenir. Her .webp görselin .png yedeği de eklenir.
  4) ses/ klasörü varsa tamamı (alt klasörler dahil).
Robot iç verisi (DISLA) eşleşse bile yayınlanmaz.

Kullanım:
  python3 lab/yayin_listesi.py liste [--json]          → yayınlanacak dosyalar (depo köküne göre)
  python3 lab/yayin_listesi.py kur _site               → listeyi _site/ klasörüne kopyalar (klasör önce temizlenir)
  python3 lab/yayin_listesi.py ozet                    → yayınlanan / yayınlanmayan boyut özeti
  python3 lab/yayin_listesi.py damga                   → depodaki index.html / sw.js içindeki js/…, css/… ?v= özetlerini yeniler
Önbellek kırma: index.html ve sw.js paketleri "js/core.js?v=<içerik özeti>" ile ister. `kur` hedef klasördeki kopyada bu özetleri
dosyaların GERÇEK içeriğinden yeniden yazar (bir ajan paketi değiştirip özeti unutsa bile yayında eski JS önbellekten gelmez).
Seçenek: --kok DİZİN (varsayılan depo kökü). Yalnız standart kütüphane; ağ isteği yapmaz.

Güvenlik payı: listeden eksik kalan bir dosya uygulamayı kırar. lab/qa.mjs aynı kaynaktan 404 alan her isteği
hata sayar (yayın kapısı reddeder); tarihli dosyalar (ör. data/at/canli/2026-10-28.json) depoda da yoksa 404 normaldir.
"""
import argparse, datetime, fnmatch, json, os, re, shutil, sys

KOK0 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = ["index.html", "sw.js", "manifest.webmanifest", "brain-worker.js"]   # + index.html/sw.js'in andığı js/*.js, css/*.css (paketler())
KOK_DOSYA = ["index.html", "sw.js", "manifest.webmanifest", "brain-worker.js", "yayin.json"]
# Taramanın kaçırabileceği ya da başka bloklarda kurulan dinamik yollar (glob, depo köküne göre).
BILINEN = [
    "data/version.json", "data/ozellik.json", "data/ratings.json", "data/fixtures.json", "data/logos.json", "data/season.json",
    "data/basket.json", "data/bk_form.json", "data/iddaa.json", "data/daily.json", "data/model.json", "data/qa.json",
    "data/archive/*.json",                 # günlük arşiv (data/archive/<gün>.json)
    "data/oxx_kupon/*.json", "data/oxx_kupon/at/*.json",
    "data/at/*.json",                      # at: dizin, jokeyler, kariyer, karne, model, altili_karne, kupon_karne …
    "data/at/canli/*.json", "data/at/oran_izi/*.json", "data/at/tahmin/*.json", "data/at/altili/*.json",
    "icons/oxxai-og.png",                  # paylaşım önizlemesi (og:image)
]
# Eşleşse bile yayınlanmaz: robot iç verisi / deney / büyük ham tablolar
DISLA = [
    "data/derin/*", "data/bk_games.json", "data/bot_tests.json", "data/deney/*", "data/deney_*", "data/acik/*",
    "data/archive/live/*", "data/archive/live_stats/*", "data/archive/eski/*", "data/archive/*.gz",
    "data/at/deneyler*.json", "data/at/arastirma.json", "data/at/replay.json", "data/at/ek_ozellik/*",
    "data/at/oran_izi_v*.json", "data/saglik/*", "data/qa/*",
]
YOL_RE = re.compile(r"(?<![A-Za-z0-9_\-])(?:\./|/)?((?:data|icons|ses|js|css)/[A-Za-z0-9_\-./${}]*)")
PAKET_RE = re.compile(r"((?:js|css)/[A-Za-z0-9_\-]+\.(?:js|css))(?:\?v=[A-Za-z0-9._\-]*)?(?=[\"'])")


def paketler(kok):
    """index.html'in (ve sw.js SHELL'in) yüklediği uygulama paketleri: js/*.js, css/*.css (sırayla, tekrarsız)."""
    out = []
    for f in ("index.html", "sw.js"):
        p = os.path.join(kok, f)
        if os.path.isfile(p):
            for m in PAKET_RE.finditer(open(p, encoding="utf-8", errors="replace").read()):
                if m.group(1) not in out:
                    out.append(m.group(1))
    return out


def ozet_kisa(yol):
    import hashlib
    with open(yol, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:10]


def damgala(kok, dosyalar=("index.html", "sw.js")):
    """Dosyalardaki js/…, css/… adreslerinin ?v= kısmını paketin gerçek içerik özetiyle yazar. Değişen dosya listesini döner."""
    degisen = []
    for f in dosyalar:
        p = os.path.join(kok, f)
        if not os.path.isfile(p):
            continue
        metin = open(p, encoding="utf-8").read()
        def yaz(m):
            y = os.path.join(kok, m.group(1))
            return f"{m.group(1)}?v={ozet_kisa(y)}" if os.path.isfile(y) else m.group(0)
        yeni = PAKET_RE.sub(yaz, metin)
        if yeni != metin:
            open(p, "w", encoding="utf-8").write(yeni)
            degisen.append(f)
    return degisen


PZ_DOSYA = "data/fx_pz.json"
PZ_YAKIN = "data/fx_pz_yakin.json"
PO_ISARET = "fx_pz:po"   # YH-71: istemci po'yu ayrık dosyadan bağlayabiliyor


def pz_ayir(hedef, sec):
    """YH-43 (v156): yayın kopyasında fixtures.json'un pazar motoru olasılıkları (pz) data/fx_pz.json'a ayrılır; uygulama onu
    açılışta değil boşta / maç penceresinde indirir. Depodaki data/fixtures.json DEĞİŞMEZ (Python okuyucuları pz'yi orada okur).
    Yalnız yayınlanan paketlerden biri fx_pz.json'u istiyorsa ayrılır (geri alınan eski uygulama pz'yi fixtures'ta bekler)."""
    fx = os.path.join(hedef, "data", "fixtures.json")
    if "data/fixtures.json" not in sec or not os.path.isfile(fx):
        return 0
    if not any(PZ_DOSYA in open(os.path.join(hedef, y), encoding="utf-8", errors="replace").read()
               for y in sec if y.endswith(".js") or y == "index.html"):
        return 0
    try:
        F = json.load(open(fx, encoding="utf-8"))
    except Exception:
        return 0
    if not isinstance(F, list):
        return 0
    # YH-71: iddaa ek pazar oranları (po) istemcide yalnız pazar motoru olasılığı (pz) bağlandıktan sonra okunur (pazar.js oddOf);
    # uygulama bunu destekliyorsa (paketlerde PO_ISARET) pz'si ayrılan maçların po'su da aynı ayrık dosyalara ("o") taşınır.
    po_ayir = any(PO_ISARET in open(os.path.join(hedef, y), encoding="utf-8", errors="replace").read()
                  for y in sec if y.endswith(".js") or y == "index.html")
    M, O = {}, {}
    for f in F:
        if isinstance(f, dict) and isinstance(f.get("pz"), dict):
            k = f"{f.get('lg')}|{f.get('d')}|{f.get('h')}|{f.get('a')}"
            M[k] = f.pop("pz")
            if po_ayir and isinstance(f.get("po"), dict):
                O[k] = f.pop("po")
    if not M:
        return 0
    json.dump(F, open(fx, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    tam = {"v": 1, "m": M}
    if O:
        tam["o"] = O
    json.dump(tam, open(os.path.join(hedef, PZ_DOSYA), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"[yayın listesi] pz ayrıldı: {len(M)} maç → {PZ_DOSYA} ({round(os.path.getsize(os.path.join(hedef, PZ_DOSYA)) / 1024)} KB), "
          f"fixtures.json {round(os.path.getsize(fx) / 1024)} KB" + (f"; po {len(O)} maç ayrıldı" if O else ""))
    # YH-48: boşta indirilen yakın parça — yalnız bugün + yarın (İstanbul günü, yayın anı). Diğer günler maç penceresi /
    # KUPO açılınca tam dosyadan gelir. Uygulama bu dosyayı istemiyorsa yazılmaz.
    if any(PZ_YAKIN in open(os.path.join(hedef, y), encoding="utf-8", errors="replace").read()
           for y in sec if y.endswith(".js") or y == "index.html"):
        bugun = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)).date()
        gunler = {bugun.isoformat(), (bugun + datetime.timedelta(days=1)).isoformat()}
        Y = {k: v for k, v in M.items() if k.split("|")[1] in gunler}
        yakin = {"v": 1, "gunler": sorted(gunler), "m": Y}
        if O:
            yakin["o"] = {k: v for k, v in O.items() if k in Y}
        json.dump(yakin, open(os.path.join(hedef, PZ_YAKIN), "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))
        print(f"[yayın listesi] yakın pz: {len(Y)} maç → {PZ_YAKIN} ({round(os.path.getsize(os.path.join(hedef, PZ_YAKIN)) / 1024)} KB)")
    return len(M)


ARSIV_OZET = "data/arsiv_ozet.json"
ARSIV_OZET_GUN = 45
ARSIV_OZET_TABAN = 0.70   # YH-66: okuyucuların (goldKarne / tpKarne) en düşük olasılık eşiği; altındaki kayıt hiçbir karneye girmez


def _olas(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def arsiv_kayit_sec(v, taban=ARSIV_OZET_TABAN):
    """YH-66: bir arşiv kaydının özete hangi alanlarla gireceği (None → girmez). taban=None → YH-48 davranışı (eşiksiz)."""
    a = v.get("ok") is not None and v.get("rp") is not None and bool(v.get("ro"))
    b = bool(v.get("sk")) and v.get("sp") is not None and v.get("sok") is not None
    if taban is not None:
        a = a and (_olas(v.get("rp")) or 0) >= taban
        b = b and (_olas(v.get("sp")) or 0) >= taban
    if not (a or b):
        return None
    alan = ("ok", "rp", "ro", "sk", "sp", "sok") + (("ms", "ou") if b else ())
    return {x: v[x] for x in alan if x in v}


def arsiv_ozet(hedef, sec):
    """YH-48: açılıştaki karne hesapları (Altın / hazır tahmin karnesi) son 30 günün tam arşiv dosyalarını ayrı ayrı indiriyordu
    (≈ 1,5 MB). Yayın kopyasına yalnız bu hesapların okuduğu alanları taşıyan tek özet yazılır; depo arşivi DEĞİŞMEZ.
    Kayıt: (ok, rp, ro dolu, rp ≥ 0,70) ya da (sk, sp, sok dolu, sp ≥ 0,70) olanlar (YH-66), değerler olduğu gibi; ms / ou yalnız ikinci gruptakilerde (oran için).
    Özette olmayan gün → istemci tam dosyaya düşer; dosyası olmayan gün → null (eskiden de 404 → atlanıyordu)."""
    if not any(ARSIV_OZET in open(os.path.join(hedef, y), encoding="utf-8", errors="replace").read()
               for y in sec if y.endswith(".js") or y == "index.html"):
        return 0
    gunler = sorted(y for y in sec if re.fullmatch(r"data/archive/\d{4}-\d{2}-\d{2}\.json", y))[-ARSIV_OZET_GUN:]
    G = {}
    for y in gunler:
        d = y[len("data/archive/"):-5]
        try:
            A = json.load(open(os.path.join(hedef, y), encoding="utf-8"))
        except Exception:
            continue                                          # okunamayan gün özete girmez → istemci tam dosyayı dener
        if not isinstance(A, dict):
            continue
        R = {}
        for k, v in A.items():
            if not isinstance(v, dict):
                continue
            s = arsiv_kayit_sec(v)
            if s is not None:
                R[k] = s
        G[d] = R
    json.dump({"v": 1, "g": G}, open(os.path.join(hedef, ARSIV_OZET), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"[yayın listesi] arşiv özeti: {len(G)} gün → {ARSIV_OZET} ({round(os.path.getsize(os.path.join(hedef, ARSIV_OZET)) / 1024)} KB)")
    return len(G)


PAZAR_KARNE = "data/pazar_karne.json"
# YH-68: istemcinin pazar karnesinden okuduğu alanlar (js/pazar.js KAR / calNote, js/guvenilirlik.js ST.pk). Yeni bir alan okunursa
# pazar_karne_kirp() bunu kaynak taramasıyla görür ve kırpmadan tam dosyayı yayınlar (sessiz bozulma yok).
PK_UST = {"pazarlar", "gruplar", "n_mac"}
PK_PAZAR = {"kalibrasyon", "oneriye_uygun"}
PK_ST = {"canli"}
PK_CANLI = {"guvenilirlik"}


def _pk_erisim(hedef, sec):
    """İstemci kaynağındaki pazar karnesi erişimlerini çıkarır; beklenmeyen okuyucu / alan varsa None."""
    okuyan = [y for y in sec if (y.endswith(".js") or y == "index.html")
              and PAZAR_KARNE in open(os.path.join(hedef, y), encoding="utf-8", errors="replace").read()]
    if sorted(okuyan) != ["js/guvenilirlik.js", "js/pazar.js"]:
        return None
    pz = open(os.path.join(hedef, "js/pazar.js"), encoding="utf-8").read()
    gv = open(os.path.join(hedef, "js/guvenilirlik.js"), encoding="utf-8").read()
    ust = set(re.findall(r"\bKAR(?:&&KAR)?\.(\w+)", pz))
    i, j = pz.find("function calNote"), pz.find("window.pzCal")
    if i < 0 or j < i:
        return None
    paz = set(re.findall(r"\bK\.(\w+)", pz[i:j]))
    st = set(re.findall(r"\bST\.pk(?:&&ST\.pk)?\.(\w+)", gv))
    cn = set(re.findall(r"\bST\.pk\.canli(?:&&ST\.pk\.canli)?\.(\w+)", gv))
    if not (ust <= PK_UST and paz <= PK_PAZAR and st <= PK_ST and cn <= PK_CANLI):
        return None
    return ust, paz, st, cn


def pazar_karne_kirp(hedef, sec):
    """YH-68: data/pazar_karne.json (≈ 116 KB) açılışta iniyor ama istemci yalnız pazar kalibrasyon kovalarını, grup isabetini,
    maç sayısını ve canlı güvenilirlik özetini okuyor. Yayın kopyasında yalnız bu alanlar kalır; depo dosyası DEĞİŞMEZ."""
    if PAZAR_KARNE not in sec:
        return 0
    y = os.path.join(hedef, PAZAR_KARNE)
    if _pk_erisim(hedef, sec) is None:
        print(f"[yayın listesi] pazar karnesi kırpılmadı: istemcide beklenmeyen okuyucu / alan")
        return 0
    try:
        D = json.load(open(y, encoding="utf-8"))
    except Exception:
        return 0
    if not isinstance(D, dict):
        return 0
    K = {k: D[k] for k in ("v", "guncelleme") if k in D}
    for k in PK_UST:
        if k in D:
            K[k] = D[k]
    if isinstance(D.get("pazarlar"), dict):
        K["pazarlar"] = {e: ({a: v[a] for a in PK_PAZAR if a in v} if isinstance(v, dict) else v) for e, v in D["pazarlar"].items()}
    if isinstance(D.get("canli"), dict):
        K["canli"] = {a: D["canli"][a] for a in PK_CANLI if a in D["canli"]}
    K["yayin_kirpik"] = 1
    once = os.path.getsize(y)
    json.dump(K, open(y, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"[yayın listesi] pazar karnesi kırpıldı: {round(once / 1024)} → {round(os.path.getsize(y) / 1024)} KB")
    return 1


def kucult(hedef, sec, kok=KOK0):
    """YH-69: yayın kopyasındaki js/*.js paketlerini boşluk / yorum küçültmesinden geçirir (lab/kucult.cjs; terser
    compress/mangle kapalı + acorn ağaç eşitliği denetimi). Yalnız OXX_KUCULT ortam değişkeni (terser + acorn kurulu klasör)
    ve node varsa çalışır; yoksa ya da herhangi bir hata olursa kopya özgün kalır (davranış değişmez). Depo dosyaları değişmez."""
    import subprocess
    d = os.environ.get("OXX_KUCULT")
    if not d or not shutil.which("node"):
        return None
    js = [y for y in sec if re.fullmatch(r"js/[A-Za-z0-9_\-]+\.js", y)]
    if not js:
        return None
    try:
        r = subprocess.run(["node", os.path.join(kok, "lab", "kucult.cjs"), hedef] + js, capture_output=True, text=True,
                           timeout=180, env=dict(os.environ, OXX_KUCULT=d))
        o = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
    except Exception as e:
        print(f"[yayın listesi] küçültme atlandı ({str(e)[:80]})")
        return None
    if o.get("durum") != "tamam":
        print(f"[yayın listesi] küçültme atlandı ({o.get('neden', '?')})")
        return o
    damgala(hedef)                       # içerik değişti → ?v= özetleri yeniden
    kal = ", ".join(f"{x['y']} ({x['neden'][:40]})" for x in o.get("ozgun_kalan", [])) or "yok"
    print(f"[yayın listesi] küçültme: {len(o['kucultulen'])} paket, {round(o['once'] / 1024)} → {round(o['sonra'] / 1024)} KB; özgün kalan: {kal}")
    return o


def kucult_css(hedef, sec, kok=KOK0):
    """YH-70: yayın kopyasındaki css/*.css paketleri ve index.html <style> blokları için boşluk / yorum küçültmesi (lab/kucult_css.cjs;
    css-tree ayrıştır → üret, dönüştürme yok + ağaç eşitliği denetimi). Yalnız OXX_KUCULT (css-tree kurulu klasör) ve node varsa
    çalışır; yoksa ya da herhangi bir hata olursa kopya özgün kalır. Depo dosyaları değişmez."""
    import subprocess
    d = os.environ.get("OXX_KUCULT")
    if not d or not shutil.which("node"):
        return None
    hedefler = [y for y in sec if re.fullmatch(r"css/[A-Za-z0-9_\-]+\.css", y)] + ["index.html"]
    try:
        r = subprocess.run(["node", os.path.join(kok, "lab", "kucult_css.cjs"), hedef] + hedefler, capture_output=True, text=True,
                           timeout=120, env=dict(os.environ, OXX_KUCULT=d))
        o = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
    except Exception as e:
        print(f"[yayın listesi] CSS küçültme atlandı ({str(e)[:80]})")
        return None
    if o.get("durum") != "tamam":
        print(f"[yayın listesi] CSS küçültme atlandı ({o.get('neden', '?')})")
        return o
    damgala(hedef)                       # css içeriği değişti → ?v= özetleri yeniden
    kal = ", ".join(f"{x['y']} ({x['neden'][:40]})" for x in o.get("ozgun_kalan", [])) or "yok"
    print(f"[yayın listesi] CSS küçültme: {len(o['kucultulen'])} parça, {round(o['once'] / 1024)} → {round(o['sonra'] / 1024)} KB; özgün kalan: {kal}")
    return o


def tara(kok):
    """Kaynak dosyalardaki yol dizelerini (düz, klasör öneki, şablon) çıkarır → glob listesi."""
    desen = set()
    for f in KAYNAK + [y for y in paketler(kok) if y not in KAYNAK]:
        p = os.path.join(kok, f)
        if not os.path.isfile(p):
            continue
        metin = open(p, encoding="utf-8", errors="replace").read()
        for m in YOL_RE.finditer(metin):
            y = m.group(1)
            if "${" in y:                                 # `data/archive/${d}.json` → data/archive/*.json
                y = re.sub(r"\$\{[^}]*\}?", "*", y)
                y = y.split("$")[0]
            y = y.rstrip(".")
            parca = y.split("/")
            if y.endswith("/"):
                if len(parca) < 3:                       # "data/", "icons/" gibi kök önekleri (sw.js "/data/") → alma
                    continue
                y += "*.json" if parca[0] == "data" else "*"
            elif "." not in parca[-1]:                    # uzantısız parça (ör. "data/at" kelimesi) → alma
                continue
            desen.add(y)
    return desen


def eslesir(yol, desenler):
    # fnmatch'te * "/" ile de eşleşir; alt klasöre inmemek için parça sayısını da karşılaştır
    for d in desenler:
        if d.count("/") == yol.count("/") and fnmatch.fnmatchcase(yol, d):
            return True
    return False


def liste(kok=KOK0):
    desen = tara(kok) | set(BILINEN)
    sec = set(f for f in KOK_DOSYA if os.path.isfile(os.path.join(kok, f)))
    eksik = []
    for d in sorted(desen):
        if not any(c in d for c in "*?["):
            if os.path.isfile(os.path.join(kok, d)):
                sec.add(d)
            else:
                eksik.append(d)
            continue
        klasor = os.path.join(kok, os.path.dirname(d))
        if os.path.isdir(klasor):
            for f in os.listdir(klasor):
                y = os.path.dirname(d) + "/" + f
                if os.path.isfile(os.path.join(kok, y)) and eslesir(y, [d]):
                    sec.add(y)
    # görsel yedeği: uygulama .webp yüklenemezse aynı adlı .png'ye düşer (src.replace(/\.webp…/, ".png"))
    for y in list(sec):
        if y.endswith(".webp"):
            png = y[:-5] + ".png"
            if os.path.isfile(os.path.join(kok, png)):
                sec.add(png)
    ses = os.path.join(kok, "ses")
    if os.path.isdir(ses):
        for d, _, fs in os.walk(ses):
            for f in fs:
                sec.add(os.path.relpath(os.path.join(d, f), kok).replace(os.sep, "/"))
    sec = sorted(y for y in sec if not eslesir(y, DISLA) and not any(fnmatch.fnmatchcase(y, d) and d.endswith("/*") for d in DISLA))
    return sec, eksik


def boyut(kok, yollar):
    return sum(os.path.getsize(os.path.join(kok, y)) for y in yollar)


def depo_dosyalari(kok):
    out = []
    for d, ds, fs in os.walk(kok):
        ds[:] = [x for x in ds if x not in (".git", ".github", "node_modules", "_site")]
        for f in fs:
            out.append(os.path.relpath(os.path.join(d, f), kok).replace(os.sep, "/"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("komut", choices=["liste", "kur", "ozet", "damga"])
    ap.add_argument("hedef", nargs="?")
    ap.add_argument("--kok", default=KOK0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    kok = os.path.abspath(a.kok)
    if a.komut == "damga":
        d = damgala(kok)
        print(f"[yayın listesi] ?v= özetleri yenilendi: {', '.join(d) if d else 'değişiklik yok'}")
        return 0
    sec, eksik = liste(kok)
    for y in ("index.html", "sw.js", "manifest.webmanifest"):
        if y not in sec:
            print(f"[yayın listesi] HATA: {y} yok", file=sys.stderr); return 2
    eksik_paket = [y for y in paketler(kok) if y not in sec]
    if eksik_paket:
        print(f"[yayın listesi] HATA: index.html/sw.js'in yüklediği paket depoda yok: {', '.join(eksik_paket)}", file=sys.stderr); return 2
    if a.komut == "liste":
        print(json.dumps({"dosyalar": sec, "bulunamayan": eksik}, ensure_ascii=False, indent=1) if a.json else "\n".join(sec))
        return 0
    if a.komut == "ozet":
        tum = depo_dosyalari(kok)
        print(json.dumps({"yayin_dosya": len(sec), "yayin_kb": round(boyut(kok, sec) / 1024),
                          "depo_dosya": len(tum), "depo_kb": round(boyut(kok, tum) / 1024),
                          "bulunamayan": eksik}, ensure_ascii=False, indent=1))
        return 0
    if not a.hedef:
        print("kullanım: yayin_listesi.py kur <hedef_klasor>", file=sys.stderr); return 2
    hedef = os.path.abspath(a.hedef)
    if hedef == kok or kok.startswith(hedef + os.sep):
        print("[yayın listesi] hedef depo kökü olamaz", file=sys.stderr); return 2
    if os.path.isdir(hedef):
        shutil.rmtree(hedef)
    for y in sec:
        h = os.path.join(hedef, y)
        os.makedirs(os.path.dirname(h), exist_ok=True)
        shutil.copy2(os.path.join(kok, y), h)
    damgala(hedef)                       # yayın kopyasında ?v= = paketin gerçek içerik özeti (önbellek kırma)
    print(f"[yayın listesi] {len(sec)} dosya, {round(boyut(kok, sec) / 1024)} KB → {hedef}")
    pz_ayir(hedef, sec)
    arsiv_ozet(hedef, sec)
    pazar_karne_kirp(hedef, sec)
    kucult(hedef, sec, kok)
    kucult_css(hedef, sec, kok)
    eksik = [y for y in eksik if y not in (PZ_DOSYA, PZ_YAKIN, ARSIV_OZET)]
    if eksik:
        print(f"[yayın listesi] kaynakta geçen ama depoda olmayan {len(eksik)} yol (dinamik olabilir): {', '.join(eksik[:12])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
