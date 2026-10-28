#!/usr/bin/env python3
"""🚦 Yayın kapısı (update.yml → deploy işi). Pages "GitHub Actions" kaynağından, artifact ile yayınlanıyor; bu yüzden kapı
yalnız iş akışında kurulur, depo ayarı gerekmez.

Uygulama dosyaları (index.html, sw.js, manifest.webmanifest, brain-worker.js, icons/, js/, css/) yayındakinden farklıysa yayından ÖNCE
duman testi koşar (lab/duman.sh). Test geçmezse Pages'e YENİ uygulama çıkmaz: çalışma ağacındaki uygulama dosyaları son başarılı
sürüme (yayındaki yayin.json → uygulama_commit) geri alınır, veri (data/*) yine yeni haliyle yayınlanır. Yalnız veri değiştiyse
test atlanır, yayın eskisi kadar hızlıdır.

Yayındaki sürüm bilgisi Pages'teki /yayin.json dosyasındadır (depoya yazılmaz, her yayında yeniden üretilir):
  {"uygulama_ozet": sha256, "uygulama_commit": sha, "zaman": ..., "red": {"ozet": .., "commit": .., "zaman": .., "neden": ..}}

  python3 lab/yayin_kapisi.py karar --canli https://x.github.io       → GITHUB_OUTPUT: karar=atla|test|red, ozet, canli_ozet, canli_commit
  python3 lab/yayin_kapisi.py geri --commit SHA --canli URL           → uygulama dosyalarını son iyi sürüme döndürür
  python3 lab/yayin_kapisi.py yaz --commit SHA [--red-ozet .. --red-commit .. --red-neden .. --red-neden-qa qa.json] [--onceki-red-koru]
  python3 lab/yayin_kapisi.py bekle --canli URL --ozet X [--sn 300]   → CDN yeni yayin.json'u gösterene dek bekler
  python3 lab/yayin_kapisi.py denetle [--kok DİZİN]                    → boyut / paket denetimi (duman testinden önce; hata → 1)
Boyut denetimi (v143, index.html paketlere bölündü): index.html ≤ 1500 KB (qa.mjs bütçesiyle aynı, GEVŞETİLMEZ; hedef < 300 KB),
her js/ css/ paketi ≤ 600 KB, ilk yük (index.html + yüklediği tüm paketler) ≤ 2000 KB (1700 KB üstü uyarı), index.html içindeki
satır içi script toplamı 30 KB üstüyse uyarı (yeni katman index.html'e değil js/ paketine eklenir, MIMARI.md). Her paket
`node --check` ile sözdizimi denetlenir (node varsa): bozuk paket o dosyadaki TÜM katmanları durdurur.
Yalnız standart kütüphane. Issue, mail, bildirim AÇMAZ. tjk.org / atyarisi.com'a istek ATMAZ.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UYGULAMA = ["index.html", "sw.js", "manifest.webmanifest", "brain-worker.js", "icons", "js", "css"]
SINIR_KB = {"index": 1500, "paket": 600, "ilk_yuk": 2000, "ilk_yuk_uyari": 1700, "satir_ici_script_uyari": 30}
RED_SAAT = 6.0          # reddedilen aynı uygulama sürümü bu süre içinde yeniden test edilmez (doğrudan son iyi sürüm yayınlanır)
YAYIN = os.path.join(ROOT, "yayin.json")


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ozet():
    """Uygulama dosyalarının (çalışma ağacı) içerik özeti."""
    h = hashlib.sha256()
    for kok in UYGULAMA:
        p = os.path.join(ROOT, kok)
        dosyalar = [p] if os.path.isfile(p) else sorted(
            os.path.join(d, f) for d, _, fs in os.walk(p) for f in fs) if os.path.isdir(p) else []
        for f in dosyalar:
            h.update(os.path.relpath(f, ROOT).encode() + b"\0")
            with open(f, "rb") as fh:
                h.update(hashlib.sha256(fh.read()).digest())
    return h.hexdigest()


def getir(url, sn=25):
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "oxxai-yayin-kapisi"})
    with urllib.request.urlopen(req, timeout=sn) as r:
        return r.read()


def canli_bilgi(canli):
    try:
        return json.loads(getir(canli.rstrip("/") + f"/yayin.json?t={int(time.time())}"))
    except Exception as e:
        print(f"[kapı] yayındaki yayin.json okunamadı ({str(e)[:80]}); ilk kurulum sayılır")
        return {}


def cikti(**kv):
    yol = os.environ.get("GITHUB_OUTPUT")
    for k, v in kv.items():
        print(f"[kapı] {k}={v}")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def yas_saat(z):
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(str(z).replace("Z", "+00:00"))).total_seconds() / 3600
    except Exception:
        return 99.0


def cmd_karar(a):
    o = ozet()
    c = canli_bilgi(a.canli)
    co, cc, red = c.get("uygulama_ozet") or "", c.get("uygulama_commit") or "", c.get("red") or {}
    if co and co == o:
        karar = "atla"                      # uygulama yayındakiyle aynı: yalnız veri değişti, test gerekmez
    elif red.get("ozet") == o and yas_saat(red.get("zaman")) < RED_SAAT:
        karar = "red"                       # bu sürüm az önce reddedildi: yeniden test etmeden son iyi sürümü yayınla
    else:
        karar = "test"
    cikti(karar=karar, ozet=o, canli_ozet=co or "yok", canli_commit=cc or "yok",
          red_zaman=red.get("zaman") or "yok", red_neden=(red.get("neden") or "yok").replace("\n", " ")[:200])
    return 0


def cmd_geri(a):
    commit = (a.commit or "").strip()
    if commit and commit != "yok":
        if subprocess.run(["git", "-C", ROOT, "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True).returncode != 0:
            subprocess.run(["git", "-C", ROOT, "fetch", "-q", "--depth=1", "origin", commit], check=False)
        var = subprocess.run(["git", "-C", ROOT, "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True).returncode == 0
        if var:
            for kok in UYGULAMA:
                p = os.path.join(ROOT, kok)
                if subprocess.run(["git", "-C", ROOT, "cat-file", "-e", f"{commit}:{kok}"], capture_output=True).returncode != 0:
                    continue                # o sürümde bu dosya yoksa mevcut olan kalır
                if os.path.isdir(p): shutil.rmtree(p)
                elif os.path.exists(p): os.remove(p)
                subprocess.run(["git", "-C", ROOT, "checkout", commit, "--", kok], check=True)
            print(f"[kapı] uygulama dosyaları {commit[:10]} sürümüne döndürüldü")
            return 0
        print(f"[kapı] {commit[:10]} getirilemedi; yayındaki dosyalar indirilecek")
    if not a.canli:
        print("[kapı] son iyi sürüm bulunamadı", file=sys.stderr); return 1
    # ilk kurulum (yayında yayin.json yok) ya da commit getirilemedi: yayındaki uygulama dosyalarını aynen al (icons/ değişmez)
    alinan = {}
    try:
        for f in ["index.html", "sw.js", "manifest.webmanifest", "brain-worker.js"]:
            alinan[f] = getir(a.canli.rstrip("/") + f"/{f}?t={int(time.time())}", 60)
    except Exception as e:
        print(f"[kapı] yayındaki dosyalar indirilemedi: {str(e)[:120]}", file=sys.stderr); return 1
    if len(alinan.get("index.html", b"")) < 10000:
        print("[kapı] yayındaki index.html beklenenden küçük; kullanılmadı", file=sys.stderr); return 1
    # v143: index.html'in yüklediği paketler (js/…, css/… ?v=) de yayındaki sürümden alınır
    try:
        import re as _re
        for y in dict.fromkeys(_re.findall(r'(?:src|href)="((?:js|css)/[A-Za-z0-9_\-]+\.(?:js|css))', alinan["index.html"].decode("utf-8", "replace"))):
            alinan[y] = getir(a.canli.rstrip("/") + f"/{y}?t={int(time.time())}", 60)
    except Exception as e:
        print(f"[kapı] yayındaki paketler indirilemedi: {str(e)[:120]}", file=sys.stderr); return 1
    for f, v in alinan.items():
        os.makedirs(os.path.dirname(os.path.join(ROOT, f)), exist_ok=True)
        with open(os.path.join(ROOT, f), "wb") as fh:
            fh.write(v)
    print("[kapı] uygulama dosyaları yayındaki sürümden alındı")
    return 0


def cmd_yaz(a):
    eski = {}
    if a.onceki_red_koru and a.canli:
        eski = canli_bilgi(a.canli).get("red") or {}
    d = {"uygulama_ozet": ozet(), "uygulama_commit": a.commit if a.commit and a.commit != "yok" else None, "zaman": simdi(),
         "aciklama": "Yayın kapısı kaydı (lab/yayin_kapisi.py). red = test edilip yayından alıkonan uygulama sürümü."}
    if a.red_ozet:
        neden = a.red_neden or ""
        if a.red_neden_qa:
            try:
                neden = (neden + " " + " | ".join((json.load(open(a.red_neden_qa, encoding="utf-8")).get("hatalar") or [])[:3])).strip()
            except Exception:
                neden = (neden + " duman testi sonuç üretmedi").strip()
        d["red"] = {"ozet": a.red_ozet, "commit": a.red_commit, "zaman": simdi(), "neden": neden[:300] or "test başarısız"}
    elif eski:
        d["red"] = eski
    with open(YAYIN, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(json.dumps(d, ensure_ascii=False))
    return 0


def cmd_bekle(a):
    son = time.time() + a.sn
    while time.time() < son:
        try:
            if json.loads(getir(a.canli.rstrip("/") + f"/yayin.json?t={int(time.time())}")).get("uygulama_ozet") == a.ozet:
                print("[kapı] yeni sürüm yayında görünüyor"); return 0
        except Exception:
            pass
        time.sleep(10)
    print("[kapı] yeni sürüm süre içinde görünmedi (CDN gecikmesi olabilir)"); return 1


def satir_ici_script_kb(html):
    import re
    return sum(len(m.group(1).encode("utf-8")) for m in re.finditer(r"<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)) / 1024


def cmd_denetle(a):
    """Boyut ve paket denetimi. Sınır aşımı / eksik paket / sözdizimi hatası → 1 (kapı: yeni uygulama yayınlanmaz)."""
    import re
    kok = os.path.abspath(a.kok or ROOT)
    hata, uyari = [], []
    ip = os.path.join(kok, "index.html")
    html = open(ip, encoding="utf-8").read()
    kb = lambda p: os.path.getsize(p) / 1024
    index_kb = kb(ip)
    paket = list(dict.fromkeys(re.findall(r'(?:src|href)="((?:js|css)/[A-Za-z0-9_\-]+\.(?:js|css))', html)))
    toplam = index_kb
    satir = [f"index.html {index_kb:.1f} KB"]
    for y in paket:
        p = os.path.join(kok, y)
        if not os.path.isfile(p):
            hata.append(f"index.html'in yüklediği paket yok: {y}"); continue
        k = kb(p); toplam += k; satir.append(f"{y} {k:.1f} KB")
        if k > SINIR_KB["paket"]:
            hata.append(f"{y} {k:.0f} KB > {SINIR_KB['paket']} KB (paketi böl: yeni dosya index.html'de aynı sıraya)")
    if index_kb > SINIR_KB["index"]:
        hata.append(f"index.html {index_kb:.0f} KB > {SINIR_KB['index']} KB")
    if toplam > SINIR_KB["ilk_yuk"]:
        hata.append(f"ilk yük {toplam:.0f} KB > {SINIR_KB['ilk_yuk']} KB")
    elif toplam > SINIR_KB["ilk_yuk_uyari"]:
        uyari.append(f"ilk yük {toplam:.0f} KB > {SINIR_KB['ilk_yuk_uyari']} KB (sınır {SINIR_KB['ilk_yuk']} KB)")
    si = satir_ici_script_kb(html)
    if si > SINIR_KB["satir_ici_script_uyari"]:
        uyari.append(f"index.html satır içi script {si:.1f} KB > {SINIR_KB['satir_ici_script_uyari']} KB: yeni katmanı js/katmanlar.js sonuna "
                     "`/* id: … */` ile ekleyin (MIMARI.md → Uygulama dosya yapısı)")
    node = shutil.which("node")
    if node:
        for y in paket:
            p = os.path.join(kok, y)
            if y.endswith(".js") and os.path.isfile(p):
                r = subprocess.run([node, "--check", p], capture_output=True, text=True)
                if r.returncode != 0:
                    hata.append(f"{y} sözdizimi hatası: {(r.stderr or '').strip().splitlines()[-1:] or ['?']}")
    else:
        uyari.append("node yok: paket sözdizimi denetlenmedi")
    print(f"[kapı] boyut: {' · '.join(satir)} · ilk yük {toplam:.1f} KB · satır içi script {si:.1f} KB")
    for u in uyari:
        print(f"::warning title=Yayın kapısı (boyut)::{u}")
    for h in hata:
        print(f"::error title=Yayın kapısı (boyut)::{h}")
    return 1 if hata else 0


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="k", required=True)
    k = alt.add_parser("karar"); k.add_argument("--canli", required=True)
    g = alt.add_parser("geri"); g.add_argument("--commit", default=""); g.add_argument("--canli", default="")
    y = alt.add_parser("yaz"); y.add_argument("--commit", default=""); y.add_argument("--canli", default="")
    y.add_argument("--red-ozet", default=""); y.add_argument("--red-commit", default=""); y.add_argument("--red-neden", default="")
    y.add_argument("--red-neden-qa", default="", help="neden: bu qa çıktısının ilk hataları")
    y.add_argument("--onceki-red-koru", action="store_true")
    d = alt.add_parser("denetle"); d.add_argument("--kok", default="")
    b = alt.add_parser("bekle"); b.add_argument("--canli", required=True); b.add_argument("--ozet", required=True); b.add_argument("--sn", type=int, default=300)
    a = ap.parse_args()
    return {"karar": cmd_karar, "geri": cmd_geri, "yaz": cmd_yaz, "bekle": cmd_bekle, "denetle": cmd_denetle}[a.k](a)


if __name__ == "__main__":
    sys.exit(main())
