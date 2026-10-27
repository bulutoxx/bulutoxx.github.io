#!/usr/bin/env python3
"""🗃️ Büyük önbellek arşivi: uygulamanın OKUMADIĞI büyük, sık değişen dosyalar git geçmişine girmez, GitHub Release asset'i olarak
saklanır (sabit etiket "veri-arsiv", ön sürüm; ücretsiz, kalıcı, depo boyutunu büyütmez).

  python3 lab/arsiv.py indir dosya...                 # iş başında: release → (olmazsa) sabit git yedeği → (o da olmazsa) dosyasız devam
  python3 lab/arsiv.py yukle [--en-az-saat 6] dosya...  # iş sonunda: yalnız içerik değiştiyse ve son yüklemeden bu yana yeterli süre geçtiyse
  python3 lab/arsiv.py durum                          # release'teki asset'ler ve manifest
  --kuru: ağa yazmaz, yalnız ne yapılacağını söyler.

Asset adı: depo içi yol, "/" → "__", gzip'li (".gz"). manifest.json asset'i: dosya → sha256, boyut, yükleme zamanı.
Yükleme: önce geçici adla yüklenir, sonra eski asset silinip yeni ad verilir (asset hiçbir an yok olmaz; --clobber eşdeğeri).
Yalnız GitHub REST API (`gh api`; GraphQL gerekmez). GH_TOKEN (Actions: github.token, contents: write) ve GH_REPO / GITHUB_REPOSITORY.
Release yoksa yüklemede oluşturulur. Hiçbir dosya git'e eklenmez (.gitignore'da)."""
import argparse, gzip, hashlib, json, os, subprocess, sys, time, urllib.parse
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ETIKET = "veri-arsiv"
# Son çare yedek: GitHub'da bulunan, dört dosyanın da izlendiği bir commit (asıl yedek: dosyaya dokunan son commit, bkz. yedekten).
YEDEK_COMMIT = "ba93d38ad8f3d1988cda44b659cad027c6994b70"
ARSIV_DOSYALARI = ["data/bk_games.json", "data/at/gbm_uretim.txt", "data/at/sinama_izi.json", "data/at/replay_kosular.json"]
# Birlikte geçerli olması gereken çiftler: GBM ağaçları yalnız aynı sürümlü data/at/model.json ile kullanılabilir.
# Sürüm uyuşmazsa dosya yazılmaz; at modeli kendi doğrusal yedeğine düşer (lab/at/model.py: _yedekte).
ESLESME = {"data/at/gbm_uretim.txt": ("data/at/model.json", "surum")}
KURU = False


def eslesme_degeri(yol, rev=None):
    if yol not in ESLESME: return None
    hedef, anahtar = ESLESME[yol]
    try:
        if rev:
            r = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{hedef}"], capture_output=True)
            return json.loads(r.stdout).get(anahtar) if r.returncode == 0 else None
        return json.load(open(os.path.join(ROOT, hedef), encoding="utf-8")).get(anahtar)
    except Exception:
        return None


def repo():
    r = os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY") or os.environ.get("ARSIV_REPO")
    if not r: raise RuntimeError("GH_REPO / GITHUB_REPOSITORY tanımlı değil")
    return r


def gh(*a, girdi=None, ikili=False):
    r = subprocess.run(["gh", "api", *a], capture_output=True, input=girdi, timeout=300)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).decode("utf-8", "replace").strip()[:300])
    return r.stdout if ikili else (json.loads(r.stdout.decode("utf-8")) if r.stdout.strip() else None)


def asset_adi(yol): return yol.replace("/", "__") + ".gz"


def sha(b): return hashlib.sha256(b).hexdigest()


def release(olustur=False):
    try:
        return gh(f"repos/{repo()}/releases/tags/{ETIKET}")
    except RuntimeError as e:
        if "404" not in str(e) and "Not Found" not in str(e): raise
    if not olustur: return None
    if KURU:
        print(f"[kuru] release '{ETIKET}' oluşturulurdu"); return {"id": 0, "assets": []}
    return gh(f"repos/{repo()}/releases", "-X", "POST", "-f", f"tag_name={ETIKET}", "-f", "name=OXXai veri arşivi (otomatik)",
              "-F", "prerelease=true", "-f",
              "body=Uygulamanın okumadığı büyük önbellek dosyaları (lab/arsiv.py). Otomatik güncellenir; elle düzenlemeyin. Sürüm değildir.")


def asset_indir(a):
    return gh("-H", "Accept: application/octet-stream", f"repos/{repo()}/releases/assets/{a['id']}", ikili=True)


def manifest(R):
    a = next((x for x in (R or {}).get("assets", []) if x["name"] == "manifest.json"), None)
    if not a: return {}, None
    try:
        return json.loads(asset_indir(a).decode("utf-8")), a
    except Exception:
        return {}, a


def asset_yukle(R, ad, veri, tur):
    """Geçici adla yükle → eskisini sil → yeniden adlandır."""
    if KURU:
        print(f"[kuru] {ad} yüklenirdi ({len(veri)} bayt)"); return
    gecici = f"_yeni_{int(time.time())}_{ad}"
    url = f"https://uploads.github.com/repos/{repo()}/releases/{R['id']}/assets?name={urllib.parse.quote(gecici)}"
    yeni = gh("-X", "POST", url, "-H", f"Content-Type: {tur}", "--input", "-", girdi=veri)
    for x in R.get("assets", []):
        if x["name"] == ad:
            try: gh("-X", "DELETE", f"repos/{repo()}/releases/assets/{x['id']}")
            except Exception as e: print(f"  eski {ad} silinemedi: {e}")
    gh("-X", "PATCH", f"repos/{repo()}/releases/assets/{yeni['id']}", "-f", f"name={ad}")


def _goster(rev, yol):
    r = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{yol}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def yedekten(yol):
    """Release yoksa: dosyanın git'teki SON izlenen sürümü. Önce GitHub API ile dosyaya dokunan son commit bulunur
    (izlemeyi bırakan commit ise ebeveyni); olmazsa sabit YEDEK_COMMIT. Sığ klonda gereken commit tek başına çekilir.
    Dönüş: (bayt, rev) ya da (None, None)."""
    adaylar = []
    try:
        s = gh("-X", "GET", f"repos/{repo()}/commits", "-f", f"path={yol}", "-f", "per_page=1")
        if s: adaylar += [s[0]["sha"], s[0]["sha"] + "~1"]
    except Exception:
        pass
    adaylar.append(YEDEK_COMMIT)
    for rev in adaylar:
        v = _goster(rev, yol)
        if v is None:
            kok = rev.split("~")[0]
            subprocess.run(["git", "-C", ROOT, "fetch", "-q", "--depth", "2", "origin", kok], capture_output=True, timeout=300)
            v = _goster(rev, yol)
        if v is not None:
            return v, rev
    return None, None


def yaz(yol, v):
    p = os.path.join(ROOT, yol); os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".arsivtmp"
    open(tmp, "wb").write(v); os.replace(tmp, p)


def indir(dosyalar):
    """Her zaman 0 döner (iş akışı dosyasız da çalışabilmeli); sonuç satırları ve eksikler yazdırılır."""
    try:
        R = release()
    except Exception as e:
        print(f"arşiv: release okunamadı ({e}); git yedeğine düşülüyor"); R = None
    assets = {a["name"]: a for a in (R or {}).get("assets", [])}
    M = {}
    if R and any(y in ESLESME for y in dosyalar):
        try: M, _ = manifest(R)
        except Exception: M = {}
    eksik = []
    for yol in dosyalar:
        a = assets.get(asset_adi(yol)); v = None; kaynak = None
        es = eslesme_degeri(yol)
        if a and es is not None and (M.get(yol) or {}).get("eslesme") not in (None, es):
            print(f"  {yol}: release sürümü ({M[yol]['eslesme']}) yerel {ESLESME[yol][0]} sürümüyle ({es}) eşleşmiyor → yazılmadı")
            continue
        if a:
            try:
                v = gzip.decompress(asset_indir(a)); kaynak = f"release ({a.get('updated_at', '')[:16]})"
            except Exception as e:
                print(f"  {yol}: release indirilemedi ({str(e)[:120]})")
        if v is None:
            v, rev = yedekten(yol)
            if v is not None and es is not None and eslesme_degeri(yol, rev) != es:
                print(f"  {yol}: git yedeği başka model sürümüne ait → yazılmadı (doğrusal yedeğe düşülür)"); v = None
                if os.path.exists(os.path.join(ROOT, yol)): continue
            if v is not None: kaynak = f"git yedeği {rev[:7]}{rev[40:]} (bayat olabilir; iş artımlı tamamlar)"
        if v is None:
            if os.path.exists(os.path.join(ROOT, yol)):
                print(f"  {yol}: indirilemedi, yerel kopya kullanılıyor"); continue
            eksik.append(yol); print(f"  {yol}: YOK → betik kendi yedek yoluna düşer (sıfırdan/eksik çalışır)"); continue
        if KURU:
            print(f"[kuru] {yol} ← {kaynak} ({len(v)} bayt)"); continue
        yaz(yol, v); print(f"  {yol} ← {kaynak} ({len(v)} bayt)")
    if eksik: print(f"::warning title=Arşiv::indirilemeyen dosya: {', '.join(eksik)}")
    return 0


def yukle(dosyalar, en_az_saat):
    R = release(olustur=True)
    M, _ = manifest(R)
    simdi = datetime.now(timezone.utc)
    degisen = 0
    for yol in dosyalar:
        p = os.path.join(ROOT, yol)
        if not os.path.exists(p):
            print(f"  {yol}: yerelde yok, atlandı"); continue
        v = open(p, "rb").read(); h = sha(v); m = M.get(yol) or {}
        if m.get("sha256") == h:
            print(f"  {yol}: değişmedi"); continue
        if m.get("yukleme") and en_az_saat > 0:
            yas = (simdi - datetime.fromisoformat(m["yukleme"].replace("Z", "+00:00"))).total_seconds() / 3600
            if yas < en_az_saat:
                print(f"  {yol}: değişti ama son yükleme {yas:.1f} sa önce (< {en_az_saat} sa) → sonraki çalışmaya"); continue
        asset_yukle(R, asset_adi(yol), gzip.compress(v, 9, mtime=0), "application/gzip")
        M[yol] = {"sha256": h, "boyut": len(v), "yukleme": simdi.strftime("%Y-%m-%dT%H:%M:%SZ"), "asset": asset_adi(yol),
                  "run": os.environ.get("GITHUB_RUN_ID", "yerel")}
        if eslesme_degeri(yol) is not None: M[yol]["eslesme"] = eslesme_degeri(yol)
        degisen += 1; print(f"  {yol}: yüklendi ({len(v)} bayt)")
    if degisen:
        if not KURU: R = release()          # asset listesi değişti
        asset_yukle(R, "manifest.json", json.dumps(M, ensure_ascii=False, indent=1).encode("utf-8"), "application/json")
    print(f"arşiv: {degisen} dosya yüklendi")
    return 0


def durum():
    R = release()
    if not R: print("release yok"); return 0
    for a in R.get("assets", []): print(f"  {a['name']}: {a['size']} bayt, {a.get('updated_at')}")
    print(json.dumps(manifest(R)[0], ensure_ascii=False, indent=1)); return 0


def main():
    global KURU
    ap = argparse.ArgumentParser()
    ap.add_argument("komut", choices=["indir", "yukle", "durum"]); ap.add_argument("dosyalar", nargs="*")
    ap.add_argument("--en-az-saat", type=float, default=6.0); ap.add_argument("--kuru", action="store_true")
    ar = ap.parse_args()
    KURU = ar.kuru
    ds = ar.dosyalar or ARSIV_DOSYALARI
    if ar.komut == "indir": return indir(ds)
    if ar.komut == "durum": return durum()
    try:
        return yukle(ds, ar.en_az_saat)
    except Exception as e:
        print(f"::warning title=Arşiv yükleme::{str(e)[:200]}"); return 1


if __name__ == "__main__":
    sys.exit(main())
