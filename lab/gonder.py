#!/usr/bin/env python3
"""📤 Veri kaybetmeyen kaydet-gönder (tüm iş akışlarının ortak commit/push adımı).

Eski kalıp `git pull --rebase -X theirs` idi: çakışan parçada yerel sürüm kazanır, diğer işin aynı dosyaya yaptığı
değişiklik sessizce kaybolur (ör. canlı kayıt ile toplayıcının data/archive/live/<gün>.json'u; tek satırlık JSON'da
dosyanın tamamı). Ayrıca üç deneme de başarısız olursa döngü 0 ile biterdi (veri sessizce gitmiş olurdu).

Bu betik:
  1) yalnız verilen yolları ekler ve TEK commit yapar (aynı işteki birden çok tur birleşir);
  2) uzak dal ilerlediyse yeniden temellendirme yerine dosya dosya 3 yollu birleştirme yapar:
       - yalnız biz değiştirdiysek bizimki, yalnız onlar değiştirdiyse onlarınki;
       - ikimiz de değiştirdiysek JSON dosyaları ANAHTAR DÜZEYİNDE birleşir (sözlükler anahtar anahtar, kimlikli kayıt listeleri
         kimlik kimlik, günlük listeleri birleşim); aynı alanı ikimiz de değiştirdiysek yerel kazanır (eski -X theirs ile aynı ilke);
       - diğer metin dosyaları `git merge-file --ours` ile (çakışmayan parçalar ikisinden de alınır);
       - --yeniden "komut" verilirse birleştirme yerine güncel uçta komut yeniden çalıştırılır (karar işleri için en güvenlisi);
  3) birkaç kez dener; hepsi başarısızsa 1 ile çıkar (adim.py kaydı ve kurtarıcı görür).
Nabız süzgeci: değişiklik yalnız data/saglik/*.json ise ve durum imzası aynıysa (6 saatten yeni) commit atılmaz (depo şişmesin).

  python3 lab/gonder.py -m "mesaj" [--yeniden "komut"] yol...      # kaydet + gönder
  python3 lab/gonder.py --tazele yol...                              # uzak daldaki güncel girdileri çalışma ağacına al (eklemez)
  python3 lab/gonder.py --birlestir-dene taban.json bizim.json onlar.json   # birleştirme sınaması (çıktı stdout)
Yalnız standart kütüphane.
"""
import argparse, json, os, random, subprocess, sys, time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIMLIK = ("id", "kosu_id", "anahtar", "key", "is", "run")
YOK = object()


def git(*a, ok=False, girdi=None, metin=True):
    r = subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=metin, input=girdi)
    if not ok and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(a[:3])}: {(r.stderr or '')[-300:]}")
    return r


def blob(rev, yol):
    r = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{yol}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


# ------------------------------------------------------------------ JSON 3 yollu birleştirme
def _js(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def _kimlik(*listeler):
    for k in KIMLIK:
        ok = True
        for L in listeler:
            if L is YOK or L is None: continue
            if not all(isinstance(x, dict) and k in x for x in L) or len({_js(x[k]) for x in L}) != len(L):
                ok = False; break
        if ok and any(L not in (YOK, None) and len(L) for L in listeler):
            return k
    return None


def birlestir(b, o, t):
    """b: ortak taban (YOK olabilir), o: bizim, t: onların. Sonuç: birleşmiş nesne (YOK = sil)."""
    if _js(o) == _js(t): return o
    if b is not YOK and _js(b) == _js(o): return t
    if b is not YOK and _js(b) == _js(t): return o
    if isinstance(o, dict) and isinstance(t, dict):
        bb = b if isinstance(b, dict) else {}
        out = {}
        for k in list(t.keys()) + [k for k in o if k not in t]:
            vb = bb.get(k, YOK)
            if k in o and k in t:
                v = birlestir(vb, o[k], t[k])
            elif k in o:          # onlarda yok: tabanda varsa onlar silmiş
                v = YOK if (vb is not YOK and _js(vb) == _js(o[k])) else o[k]
            else:                 # bizde yok: tabanda varsa biz silmişiz
                v = YOK if (vb is not YOK and _js(vb) == _js(t[k])) else t[k]
            if v is not YOK: out[k] = v
        return out
    if isinstance(o, list) and isinstance(t, list):
        bl = b if isinstance(b, list) else []
        k = _kimlik(bl, o, t)
        if k:
            sb = {_js(x[k]): x for x in bl}; so = {_js(x[k]): x for x in o}; st = {_js(x[k]): x for x in t}
            m = birlestir(sb, so, st)
            return list(m.values())
        if all(isinstance(x, (dict, list)) for x in o + t):     # kayıt/günlük listesi: küme birleşimi (sıra: onlarınki + bizim yeniler)
            bs = {_js(x) for x in bl}; os_ = {_js(x) for x in o}; ts = {_js(x) for x in t}
            return [x for x in t if not (_js(x) in bs and _js(x) not in os_)] + [x for x in o if _js(x) not in ts and _js(x) not in bs]
    return o                                                    # skaler / tür uyuşmazlığı: yerel kazanır


def bicimle(obj, ornek):
    """Bizim dosyanın biçimini koru (girinti / sıkışık, ensure_ascii)."""
    s = ornek.decode("utf-8", "replace") if isinstance(ornek, bytes) else (ornek or "")
    ascii_ = "\\u" in s and all(ord(c) < 128 for c in s)
    satirlar = s.split("\n")
    if len(satirlar) > 2 and satirlar[0].strip() in ("{", "["):
        ilk = satirlar[1]; girinti = len(ilk) - len(ilk.lstrip(" "))
        metin = json.dumps(obj, ensure_ascii=ascii_, indent=girinti or 1)
    elif ", " in s[:2000] or ": " in s[:2000]:
        metin = json.dumps(obj, ensure_ascii=ascii_)
    else:
        metin = json.dumps(obj, ensure_ascii=ascii_, separators=(",", ":"))
    if s.endswith("\n"): metin += "\n"
    return metin.encode("utf-8")


def dosya_birlestir(yol, b, o, t):
    """Bayt düzeyi: None = dosya yok. Dönüş: (sonuç baytları | None=sil, yöntem)."""
    if o == t: return o, "aynı"
    if t == b: return o, "yalnız biz"
    if o == b: return t, "yalnız onlar"
    if o is None: return t, "biz sildik, onlar değiştirdi → onlarınki korunur"
    if t is None: return o, "onlar sildi, biz değiştirdik → bizimki korunur"
    if yol.endswith(".json"):
        try:
            oo, to = json.loads(o), json.loads(t)
            bo = json.loads(b) if b is not None else YOK
            m = birlestir(bo, oo, to)
            return bicimle(m, o), "JSON anahtar düzeyi"
        except Exception:
            return o, "JSON okunamadı → yerel"
    if b is not None and b"\0" not in o and b"\0" not in t:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            ps = []
            for ad, v in (("o", o), ("b", b), ("t", t)):
                p = os.path.join(d, ad); open(p, "wb").write(v); ps.append(p)
            r = subprocess.run(["git", "merge-file", "-p", "--ours", *ps], capture_output=True)
            if r.returncode >= 0 and r.stdout:
                return r.stdout, "metin 3 yollu (çakışmada yerel)"
    return o, "yerel"


# ------------------------------------------------------------------ git akışı
def ekle(yollar):
    for y in yollar:
        git("add", "-A", "--", y, ok=True)


def nabiz_suzgeci(saat):
    """Yalnız data/saglik/*.json değiştiyse ve imza aynıysa (son yazım < saat) bu dosyaları geri al."""
    deg = [x for x in git("diff", "--cached", "--name-only").stdout.split("\n") if x]
    if not deg or not all(x.startswith("data/saglik/") and x.endswith(".json") for x in deg):
        return
    for x in deg:
        try:
            eski = json.loads(blob("HEAD", x) or b"{}"); yeni = json.load(open(os.path.join(ROOT, x), encoding="utf-8"))
            yas = (datetime.now(timezone.utc) - datetime.fromisoformat(eski.get("guncelleme", "2000-01-01T00:00:00Z").replace("Z", "+00:00"))).total_seconds() / 3600
            if eski.get("imza") != yeni.get("imza") or yas > saat:
                return
        except Exception:
            return
    for x in deg:
        git("reset", "-q", "--", x, ok=True); git("checkout", "--", x, ok=True)
    print("yalnız nabız kaydı değişti, durum aynı → commit atılmadı")


def kimlik_ayarla():
    if not git("config", "user.email", ok=True).stdout.strip():
        git("config", "user.name", "bulutoxx-bot"); git("config", "user.email", "bulutoxx-bot@users.noreply.github.com")


def onde_mi():
    return git("merge-base", "--is-ancestor", "origin/main", "HEAD", ok=True).returncode == 0


def kac_ileride():
    r = git("rev-list", "--count", "origin/main..HEAD", ok=True)
    return int(r.stdout.strip() or 0) if r.returncode == 0 else 0


def commitle(mesaj):
    if git("diff", "--cached", "--quiet", ok=True).returncode == 0:
        return False
    git("commit", "-q", "-m", mesaj); return True


def gonder(mesaj, yollar, yeniden=None, deneme=6, nabiz=6.0):
    kimlik_ayarla()
    ekle(yollar); nabiz_suzgeci(nabiz)
    commitle(mesaj)
    for i in range(1, deneme + 1):
        if git("fetch", "-q", "origin", "main", ok=True).returncode != 0:
            print(f"deneme {i}: fetch başarısız"); time.sleep(5 + random.random() * 10); continue
        if kac_ileride() == 0:
            print("değişiklik yok"); return 0
        if not onde_mi():
            if yeniden:
                print(f"deneme {i}: uzak dal ilerlemiş → güncel uçta yeniden üretiliyor: {yeniden}")
                git("reset", "-q", "--hard", "origin/main")
                rc = subprocess.run(["bash", "-o", "pipefail", "-c", yeniden], cwd=ROOT).returncode
                if rc != 0: print(f"yeniden üretim çıkış kodu {rc}")
                ekle(yollar); nabiz_suzgeci(nabiz)
                if not commitle(mesaj):
                    print("yeniden üretimden sonra değişiklik yok"); return 0
            else:
                taban = git("merge-base", "HEAD", "origin/main").stdout.strip()
                dosyalar = [x for x in git("diff", "--name-only", "--no-renames", taban, "HEAD").stdout.split("\n") if x]
                sonuc = {}
                for y in dosyalar:
                    sonuc[y] = dosya_birlestir(y, blob(taban, y), blob("HEAD", y), blob("origin/main", y))
                git("reset", "-q", "--hard", "origin/main")
                for y, (v, yontem) in sonuc.items():
                    p = os.path.join(ROOT, y)
                    if v is None:
                        if os.path.exists(p): os.remove(p)
                    else:
                        os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(v)
                    if yontem not in ("aynı", "yalnız biz"): print(f"  {y}: {yontem}")
                    git("add", "-A", "--", y, ok=True)
                if not commitle(mesaj):
                    print("birleştirmeden sonra fark kalmadı"); return 0
                print(f"deneme {i}: {len(dosyalar)} dosya uzak dalın üstüne birleştirildi")
        elif kac_ileride() > 1:                                  # birden çok yerel commit → tek commit
            git("reset", "-q", "--soft", "origin/main"); commitle(mesaj)
        r = git("push", "-q", "origin", "HEAD:main", ok=True)
        if r.returncode == 0:
            print(f"gönderildi ({git('rev-parse', '--short', 'HEAD').stdout.strip()})"); return 0
        print(f"deneme {i}: push reddedildi: {(r.stderr or '').strip()[-200:]}")
        time.sleep(3 + random.random() * 9)
    print("::error title=Kaydetme başarısız::değişiklikler gönderilemedi (tüm denemeler bitti)")
    return 1


def tazele(yollar):
    """Uzak daldaki güncel sürümleri çalışma ağacına yazar (index'e eklemez). Uzun döngülü işlerin girdileri için."""
    if git("fetch", "-q", "origin", "main", ok=True).returncode != 0:
        print("tazele: fetch başarısız, mevcut kopya kullanılıyor"); return 0
    n = 0
    for y in yollar:
        for f in [x for x in git("ls-tree", "-r", "--name-only", "origin/main", "--", y, ok=True).stdout.split("\n") if x]:
            v = blob("origin/main", f)
            if v is None: continue
            p = os.path.join(ROOT, f); os.makedirs(os.path.dirname(p), exist_ok=True)
            try:
                if open(p, "rb").read() == v: continue
            except Exception:
                pass
            open(p, "wb").write(v); n += 1
    print(f"tazele: {n} girdi dosyası güncellendi")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--mesaj"); ap.add_argument("--yeniden", default=None)
    ap.add_argument("--deneme", type=int, default=6); ap.add_argument("--nabiz-saat", type=float, default=6.0)
    ap.add_argument("--tazele", action="store_true"); ap.add_argument("--birlestir-dene", action="store_true")
    ap.add_argument("yollar", nargs="*")
    ar = ap.parse_args()
    if ar.birlestir_dene:
        b, o, t = (open(p, "rb").read() if os.path.exists(p) else None for p in ar.yollar[:3])
        v, yontem = dosya_birlestir(ar.yollar[1], b, o, t)
        print(yontem, file=sys.stderr); sys.stdout.write((v or b"").decode("utf-8")); return 0
    if ar.tazele:
        return tazele(ar.yollar)
    if not ar.mesaj or not ar.yollar:
        ap.error("-m ve en az bir yol gerekli")
    return gonder(ar.mesaj, ar.yollar, ar.yeniden, ar.deneme, ar.nabiz_saat)


if __name__ == "__main__":
    sys.exit(main())
