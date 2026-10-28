#!/usr/bin/env python3
"""🗃️ Büyük önbellek arşivi: uygulamanın OKUMADIĞI büyük, sık değişen dosyalar git geçmişine girmez, GitHub Release asset'i olarak
saklanır (sabit etiket "veri-arsiv", ön sürüm; ücretsiz, kalıcı, depo boyutunu büyütmez).

  python3 lab/arsiv.py indir dosya...                 # iş başında: release → (olmazsa) sabit git yedeği → (o da olmazsa) dosyasız devam
  python3 lab/arsiv.py yukle [--en-az-saat 6] dosya...  # iş sonunda: yalnız içerik değiştiyse ve son yüklemeden bu yana yeterli süre geçtiyse
  python3 lab/arsiv.py durum                          # release'teki asset'ler ve manifest
  --kuru: ağa yazmaz, yalnız ne yapılacağını söyler.

Asset adı: depo içi yol, "/" → "__", gzip'li (".gz"). manifest.json asset'i: dosya → sha256, boyut, yükleme zamanı.
Yükleme: uploads.github.com'a urllib ile Content-Length'li POST (eski `gh api --input -` yolu hep "Bad Content-Length (HTTP 400)"
alıyordu); geçici adla yüklenip eski silinir ve yeniden adlandırılır (asset hiçbir an yok olmaz). REST olmazsa yedek:
`gh release upload veri-arsiv <dosya> --clobber`. İndirme: REST asset uç noktası (octet-stream), olmazsa browser_download_url.
GH_TOKEN (Actions: github.token, contents: write) ve GH_REPO / GITHUB_REPOSITORY. Release yoksa yüklemede oluşturulur.

🔒 HAM VERİ RELEASE'E GİRMEZ: depo herkese açık, release asset'leri de herkese açıktır. Üçüncü taraf ham verisi içeren dosyalar
(HAM: ESPN maç skorları/logoları, at yarışı koşu sonuçları) release'e yüklenmez; iş akışlarında actions/cache ile saklanır
(anahtar arsiv-<ad>-<run>, restore-keys arsiv-<ad>-). Bu betik HAM dosyada yalnız yerel kopyayı (önbellekten gelen) kullanır,
yoksa git yedeğine düşer; yüklemede HAM dosyayı atlar. Release'te yalnız türetilmiş dosyalar (model ağaçları, sınama izi) durur.
Hiçbir dosya git'e eklenmez (.gitignore'da)."""
import argparse, gzip, hashlib, json, os, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ETIKET = "veri-arsiv"
# Son çare yedek: GitHub'da bulunan, dört dosyanın da izlendiği bir commit (asıl yedek: dosyaya dokunan son commit, bkz. yedekten).
YEDEK_COMMIT = "ba93d38ad8f3d1988cda44b659cad027c6994b70"
ARSIV_DOSYALARI = ["data/bk_games.json", "data/at/gbm_uretim.txt", "data/at/sinama_izi.json", "data/at/replay_kosular.json"]
# Birlikte geçerli olması gereken çiftler: GBM ağaçları yalnız aynı sürümlü data/at/model.json ile kullanılabilir.
# Sürüm uyuşmazsa dosya yazılmaz; at modeli kendi doğrusal yedeğine düşer (lab/at/model.py: _yedekte).
# Ham üçüncü taraf verisi: herkese açık release'e yüklenmez (actions/cache'te saklanır; bkz. üst açıklama).
HAM = {"data/bk_games.json": "ESPN maç skorları ve takım logoları (ham)",
       "data/at/replay_kosular.json": "at yarışı koşu sonuçları / bitiş sıraları (ham)"}
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


def gh(*a, girdi=None, ikili=False, api=True):
    r = subprocess.run(["gh", "api", *a] if api else ["gh", *a], capture_output=True, input=girdi, timeout=300)
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
    """REST: Accept octet-stream ile asset (gh api yönlendirmeyi izler); olmazsa herkese açık browser_download_url."""
    try:
        return gh("-H", "Accept: application/octet-stream", f"repos/{repo()}/releases/assets/{a['id']}", ikili=True)
    except Exception:
        with urllib.request.urlopen(a["browser_download_url"], timeout=300) as r:
            return r.read()


def manifest(R):
    a = next((x for x in (R or {}).get("assets", []) if x["name"] == "manifest.json"), None)
    if not a: return {}, None
    try:
        return json.loads(asset_indir(a).decode("utf-8")), a
    except Exception:
        return {}, a


def _yukle_rest(R, ad, veri, tur):
    """uploads.github.com'a Content-Length'li POST (urllib). Dönüş: yeni asset JSON'u."""
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not tok: raise RuntimeError("GH_TOKEN / GITHUB_TOKEN yok")
    url = f"https://uploads.github.com/repos/{repo()}/releases/{R['id']}/assets?name={urllib.parse.quote(ad)}"
    q = urllib.request.Request(url, data=veri, method="POST", headers={
        "Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": tur, "Content-Length": str(len(veri)), "User-Agent": "oxxai-arsiv"})
    try:
        with urllib.request.urlopen(q, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"yükleme HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}")


def asset_yukle(R, ad, veri, tur="application/octet-stream"):
    """--clobber eşdeğeri, asset hiçbir an yok olmadan: geçici adla yükle → eski aynı adlıyı sil → yeniden adlandır.
    Önce REST (urllib, Content-Length'li); olmazsa `gh release upload --clobber` (Actions'ta GITHUB_TOKEN ile çalışır)."""
    if KURU:
        print(f"[kuru] {ad} yüklenirdi ({len(veri)} bayt)"); return
    gecici = f"_yeni_{int(time.time())}_{ad}"
    try:
        yeni = _yukle_rest(R, gecici, veri, tur)
    except Exception as e:
        print(f"  REST yükleme olmadı ({str(e)[:160]}); gh release upload --clobber deneniyor")
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, ad)
            open(p, "wb").write(veri)
            gh("release", "upload", ETIKET, p, "--clobber", "-R", repo(), api=False)
        return
    for x in gh(f"repos/{repo()}/releases/{R['id']}/assets", "-X", "GET", "-f", "per_page=100") or []:
        if x["name"] == ad and x["id"] != yeni["id"]:
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
        if yol in HAM:
            if os.path.exists(os.path.join(ROOT, yol)):
                print(f"  {yol}: Actions önbelleğinden/yerelden ({os.path.getsize(os.path.join(ROOT, yol))} bayt; ham veri, release'te tutulmaz)")
                continue
            a = None
        else:
            a = assets.get(asset_adi(yol))
        v = None; kaynak = None
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
    ham = [y for y in dosyalar if y in HAM]
    for y in ham:
        print(f"  {y}: ham veri ({HAM[y]}) → herkese açık release'e yüklenmez; Actions önbelleğinde (actions/cache) saklanır")
    dosyalar = [y for y in dosyalar if y not in HAM]
    if not dosyalar:
        print("arşiv: release'e yüklenecek türetilmiş dosya yok"); return 0
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
