# OXXai at yarışı — Ek kaynak A'dan GÜN İÇİ SONUÇ yoklaması (canli.py yedek sonuç kaynağı).
#
# Kullanıcı kararı (28.10.2026): Ek kaynak A, aynanın (github.com/cenkozgur/tjk-data) sonuçları geç yayınladığı
# durumlarda koşu SONUCUNU (bitiş sırası) almak için de kullanılabilir. Kurallar ek_kaynak.py ile aynı:
#   - Adres yalnız AT_EK_KAYNAK ortam değişkeninden (GitHub secret) okunur; hiçbir dosyaya/günlüğe/commit'e yazılmaz
#     (git çıktısı tamamen susturulur, hata yalnız tür adıyla basılır).
#   - Kaynaktaki kodlar ÇALIŞTIRILMAZ; yalnız data/sonuclar/ altındaki CSV dosyaları okunur (seyrek klon).
#   - Ham veri depoya yazılmaz: canli.py yalnız ilk 4 at numarası + kazanan adı gibi sonuç ÖZETİNİ yazar (aynadan gelen
#     sonuçla aynı biçim). Klon _ek_sonuc/ altında (gitignore) iş boyunca tutulur; iş bitince runner ile silinir.
#   - Hız sınırı: aynı iş içinde en sık YOKLA_SN saniyede bir `git fetch --depth 1` (sığ, yalnız yeni commit).
#   - Koşu anı (canlı derece/sıralama) verisi bu kaynakta YOKSA uydurulmaz; durum dosyası yalnız var olan sütunları bildirir.
# Durum (adres içermez): data/at/ek_ozellik/_sonuc_durum.json — sütun adları, son commit zamanı, son tarih, gün başına koşu.
import csv, glob, gzip, io, json, os, re, subprocess, sys, time
from collections import defaultdict
from datetime import datetime, timezone

BURA = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.abspath(os.path.join(BURA, "..", ".."))
HAM = os.path.join(KOK, "_ek_sonuc")
DURUM = os.path.join(KOK, "data", "at", "ek_ozellik", "_sonuc_durum.json")
SEYREK = ["data/sonuclar/"]
YOKLA_SN = 240
HIP = {"istanbul": "İstanbul", "izmir": "İzmir", "adana": "Adana", "bursa": "Bursa", "ankara": "Ankara",
       "sanliurfa": "Şanlıurfa", "antalya": "Antalya", "elazig": "Elazığ", "kocaeli": "Kocaeli",
       "diyarbakir": "Diyarbakır"}
CANLI_SUTUN = re.compile(r"derece|sure|süre|zaman|time|anlik|canli|fark|ganyan|odds", re.I)
_SESSIZ = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _ad(s):
    import unicodedata
    s = unicodedata.normalize("NFC", str(s or "")).strip()
    return re.sub(r"\s+", " ", s).upper()


def _git(*a, timeout=300):
    subprocess.run(["git", "-C", HAM, *a], check=True, timeout=timeout, **_SESSIZ)


def guncelle(zorla=False):
    """Seyrek klonu kurar ya da sığ günceller. Döner: 'yok' (secret/klon yok), 'taze' (yakın zamanda yoklandı),
    'guncel' (yoklandı), 'hata:<tür>'. Adres hiçbir çıktıya yazılmaz."""
    url = os.environ.get("AT_EK_KAYNAK", "").strip()
    damga = os.path.join(HAM, ".oxx_yoklama")
    if os.path.isdir(os.path.join(HAM, ".git")):
        try:
            if not zorla and time.time() - os.path.getmtime(damga) < YOKLA_SN:
                return "taze"
        except OSError:
            pass
        try:
            _git("fetch", "-q", "--depth", "1", "origin", timeout=300)
            _git("reset", "-q", "--hard", "FETCH_HEAD", timeout=600)
        except Exception as e:   # noqa: BLE001
            return "hata:" + type(e).__name__
    else:
        if not url:
            return "yok"
        import shutil
        shutil.rmtree(HAM, ignore_errors=True)
        try:
            subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout", url, HAM],
                           check=True, timeout=600, **_SESSIZ)
            _git("sparse-checkout", "set", "--no-cone", *SEYREK, timeout=120)
            _git("checkout", "-q", timeout=900)
        except Exception as e:   # noqa: BLE001
            shutil.rmtree(HAM, ignore_errors=True)
            return "hata:" + type(e).__name__
    try:
        open(damga, "w").close()
    except OSError:
        pass
    return "guncel"


def _dosyalar(tarih=None):
    fs = sorted(glob.glob(os.path.join(HAM, "data", "sonuclar", "**", "*.csv*"), recursive=True))
    if not tarih:
        return fs
    for anahtar in (tarih, tarih.replace("-", ""), tarih[:7], tarih[:7].replace("-", ""), tarih[:4]):
        s = [f for f in fs if anahtar in os.path.basename(f)]
        if s:
            return s
    return fs


def _oku(f):
    ac = gzip.open(f, "rt", encoding="utf-8", newline="") if f.endswith(".gz") else open(f, encoding="utf-8", newline="")
    with ac as h:
        yield from csv.DictReader(h)


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def _sayi(x):
    try:
        v = float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return v if v > 1.0 else None


def gun_sonuclari(tarih):
    """(hipodrom, koşu no) -> canli.gun_sonuclari ile aynı biçimde sonuç özeti; yalnız sırası belli, tek kazananlı koşular."""
    if not os.path.isdir(os.path.join(HAM, "data")):
        return {}
    K = defaultdict(list)
    for f in _dosyalar(tarih):
        try:
            for r in _oku(f):
                if (r.get("tarih") or "")[:10] != tarih:
                    continue
                h = HIP.get((r.get("hipodrom") or "").strip().lower())
                ko = _int(r.get("kosu"))
                if not h or not ko:
                    continue
                K[(h, ko)].append(r)
        except (OSError, EOFError, csv.Error, UnicodeDecodeError):
            continue
    out = {}
    for anah, L in K.items():
        kosmayan = sorted({str(r.get("no") or "").strip() for r in L if str(r.get("kosmadi")).lower() == "true"} - {""},
                          key=lambda x: (len(x), x))
        kos = [r for r in L if str(r.get("kosmadi")).lower() != "true" and (_int(r.get("sira")) or 0) > 0]
        if not kos:
            continue
        kos.sort(key=lambda r: _int(r.get("sira")))
        if _int(kos[0].get("sira")) != 1 or sum(1 for r in kos if _int(r.get("sira")) == 1) != 1:
            continue
        poz = [_int(r.get("sira")) for r in kos[:4]]
        kaz = kos[0]
        out[anah] = {"sira": [str(r.get("no") or "").strip() for r in kos[:4]], "kazanan": str(kaz.get("no") or "").strip(),
                     "kazanan_ad": _ad(kaz.get("at")), "ganyan": _sayi(kaz.get("ganyan")),
                     "kosan": len([r for r in L if str(r.get("kosmadi")).lower() != "true"]),
                     "derece": poz, "esit": len(set(poz)) < len(poz), "kosmayan": kosmayan,
                     "_sira_no": {str(r.get("no") or "").strip(): _int(r.get("sira")) for r in kos}}
    return out


def durum_yaz(yoklama):
    """Adres içermeyen yoklama özeti (iş akışı günlükleri indirilemediği için depoya yazılır)."""
    d = {"ts": int(time.time()), "guncelleme_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "yoklama": yoklama}
    if os.path.isdir(os.path.join(HAM, ".git")):
        try:
            r = subprocess.run(["git", "-C", HAM, "log", "-1", "--format=%cI"], capture_output=True, text=True, timeout=30)
            d["son_commit"] = r.stdout.strip() or None
        except Exception:   # noqa: BLE001
            pass
        fs = _dosyalar()
        d["dosya"] = len(fs)
        d["ad_bicimi"] = sorted({re.sub(r"\d", "9", os.path.basename(f)) for f in fs})[:6]
        if fs:
            son = max(fs, key=os.path.getmtime)
            try:
                g = _oku(son)
                ilk = next(g, None)
                d["sutunlar"] = list(ilk.keys()) if ilk else []
                tar = defaultdict(set)
                for r in [ilk] + list(g) if ilk else []:
                    t = (r.get("tarih") or "")[:10]
                    if t:
                        tar[t].add(((r.get("hipodrom") or "").lower(), r.get("kosu")))
                son4 = sorted(tar)[-4:]
                d["son_tarih"] = son4[-1] if son4 else None
                d["gun_kosu"] = {t: len(tar[t]) for t in son4}
            except (OSError, EOFError, csv.Error, UnicodeDecodeError, StopIteration) as e:
                d["okuma"] = type(e).__name__
            d["kosu_ani_sutunu"] = [c for c in d.get("sutunlar", []) if CANLI_SUTUN.search(c)]
    os.makedirs(os.path.dirname(DURUM), exist_ok=True)
    eski = {}
    try:
        eski = json.load(open(DURUM, encoding="utf-8"))
    except (OSError, ValueError):
        pass
    # yalnız içerik değişince ya da 6 saatte bir yaz (gereksiz commit yok)
    if {k: v for k, v in eski.items() if k not in ("ts", "guncelleme_utc")} == {k: v for k, v in d.items() if k not in ("ts", "guncelleme_utc")} \
            and time.time() - eski.get("ts", 0) < 6 * 3600:
        return d
    json.dump(d, open(DURUM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return d


if __name__ == "__main__":
    y = guncelle(zorla="--zorla" in sys.argv)
    d = durum_yaz(y)
    print("ek sonuç:", json.dumps({k: d.get(k) for k in ("yoklama", "son_commit", "dosya", "son_tarih", "gun_kosu")}, ensure_ascii=False))
