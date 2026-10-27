# OXXai at yarışı laboratuvarı — "Ek kaynak A" çekici ve türetici (v6b).
#
# Ek kaynak A: üçüncü bir kişinin herkese açık yayınladığı hazır at verisi dosyaları (program: start, handikap puanı,
# baba; idman/galop dereceleri; sonuçlar). Kullanıcı kararı (27.10.2026): lisans olmasa da YALNIZ MODEL EĞİTİMİ için
# okunur; ham veri yeniden yayınlanmaz, depoya yalnız TÜRETİLMİŞ özellikler yazılır (data/at/ek_ozellik/<ay>.json.gz).
# Kaynağın adresi depoda hiçbir yerde geçmez: URL yalnız ortam değişkeni AT_EK_KAYNAK'tan (GitHub secret) okunur ve
# hiçbir çıktıya/günlüğe yazılmaz. Kaynaktaki kodlar ÇALIŞTIRILMAZ; yalnız CSV dosyaları okunur. Video/medya
# bağlantıları (yasak alanlar) okunmaz, açılmaz. tjk.org / atyarisi.com'a bu modülden hiçbir istek gitmez.
#
#   AT_EK_KAYNAK=<gizli> python lab/at/ek_kaynak.py          # sığ+seyrek klon -> türet -> ham veriyi sil
#   AT_EK_YOL=/yerel/klon  python lab/at/ek_kaynak.py         # yerel (önceden indirilmiş) kopyadan türet, silmez
# Secret yoksa sessizce atlanır ("ek kaynak yok"); özellikler "ek yok" bayrağıyla sıfır kalır, yayın durmaz.
#
# Sızıntı: her özellik koşu GÜNÜNDEN ÖNCE bilinen bilgiden türetilir.
#   st, hk          : koşu programı (yarıştan önce ilan edilir).
#   soy_*           : babanın yavrularının yalnız koşu gününden ÖNCEKİ sonuçları (gün gün birikimli; aynı gün eklenmez).
#   id_*            : atın koşu gününden ÖNCEKİ (it < tarih) idman/galop kayıtları.
import csv, glob, gzip, json, math, os, shutil, subprocess, sys
from collections import defaultdict
from datetime import date

BURA = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.abspath(os.path.join(BURA, "..", ".."))
CIKTI = os.path.join(KOK, "data", "at", "ek_ozellik")
HAM = os.path.join(KOK, "_ek_kaynak")
SEYREK = ["data/program/", "data/sonuclar/", "data/galop/", "data/idman.csv.gz", "data/yillik/"]
HIP = {"istanbul": "İstanbul", "izmir": "İzmir", "adana": "Adana", "bursa": "Bursa", "ankara": "Ankara",
       "sanliurfa": "Şanlıurfa", "antalya": "Antalya", "elazig": "Elazığ", "kocaeli": "Kocaeli",
       "diyarbakir": "Diyarbakır"}
HAM_ALANLAR = ["st", "n", "hk", "soy_ae", "soy_pist", "soy_mes", "soy_n", "id_gun", "id_n30", "id_400", "id_600"]
# Depoya yazılan biçim: ham program değerleri değil, koşu içi GÖRELİ/türetilmiş değerler (ham veri yeniden yayınlanmaz).
#   st_g  = (start − 1) / (alan − 1)            hp_f = handikap puanı − programdaki alanın ortalaması (0 = puansız → boş)
#   id_400f/id_600f = en iyi idman derecesi − programdaki alanın ortancası   (at6'da alan içi farka çevrilir; kayma
#   değişmezliği sayesinde özellikler ham değerle kurulanla birebir aynıdır)
ALANLAR = ["st_g", "hp_f", "soy_ae", "soy_pist", "soy_mes", "soy_n", "id_gun", "id_n30", "id_400f", "id_600f"]
ILK_AY = "2025-01"
SOY_K = 8.0   # babanın beklenen galibiyete göre oranı için küçültme (sanal beklenen galibiyet)


def _ad(s):
    import re, unicodedata
    s = unicodedata.normalize("NFC", str(s or "")).strip()
    return re.sub(r"\s+", " ", s).upper()


def _f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _gz(yol):
    return csv.DictReader(gzip.open(yol, "rt", encoding="utf-8", newline=""))


def cek(hedef=HAM):
    """AT_EK_KAYNAK'taki depoyu sığ + seyrek klonlar (yalnız SEYREK yolları). Adres hiçbir yere yazılmaz."""
    url = os.environ.get("AT_EK_KAYNAK", "").strip()
    if not url:
        print("ek kaynak yok")
        return None
    shutil.rmtree(hedef, ignore_errors=True)
    sessiz = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)   # git hata metni adresi içerebilir
    try:
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout", url, hedef],
                       check=True, timeout=600, **sessiz)
        subprocess.run(["git", "-C", hedef, "sparse-checkout", "set", "--no-cone"] + SEYREK, check=True, timeout=120, **sessiz)
        subprocess.run(["git", "-C", hedef, "checkout", "-q"], check=True, timeout=900, **sessiz)
    except Exception as e:   # noqa: BLE001
        print("ek kaynak alınamadı:", type(e).__name__)
        shutil.rmtree(hedef, ignore_errors=True)
        return None
    return hedef


def _program(ham):
    P = {}
    for f in sorted(glob.glob(os.path.join(ham, "data", "program", "*.csv.gz"))):
        for r in _gz(f):
            h = HIP.get(r.get("hipodrom"))
            if not h or not r.get("tarih"):
                continue
            try:
                k = (r["tarih"], h, int(r["kosu"]), str(r["no"]).strip())
            except (TypeError, ValueError):
                continue
            P[k] = {"at": _ad(r.get("p_at")), "baba": _ad(r.get("baba")), "st": _f(r.get("st")), "hk": _f(r.get("hk"))}
    return P


def _sonuclar(ham):
    """(tarih, hipodrom, koşu) -> [(no, sıra, at)] (koşmayanlar hariç); pist/mesafe programdan değil buradan gelmez."""
    S = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(ham, "data", "sonuclar", "*.csv.gz"))):
        for r in _gz(f):
            h = HIP.get(r.get("hipodrom"))
            if not h or str(r.get("kosmadi")).lower() == "true":
                continue
            try:
                S[(r["tarih"], h, int(r["kosu"]))].append((str(r["no"]).strip(), int(float(r["sira"] or 0)), _ad(r.get("at"))))
            except (TypeError, ValueError):
                continue
    return S


def _idman(ham):
    """at -> zaman sıralı [(gün, 400 m, 600 m)] (galop klasörü + idman.csv.gz; video sütunu okunmaz)."""
    I = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(ham, "data", "galop", "*.csv.gz"))):
        for r in _gz(f):
            try:
                g = date.fromisoformat(r["it"]).toordinal()
            except (KeyError, TypeError, ValueError):
                continue
            I[_ad(r.get("at"))].append((g, _f(r.get("p400")), _f(r.get("p600"))))
    yol = os.path.join(ham, "data", "idman.csv.gz")
    if os.path.exists(yol):
        for r in _gz(yol):
            try:
                g = date.fromisoformat(r["it"]).toordinal()
            except (KeyError, TypeError, ValueError):
                continue
            I[_ad(r.get("at"))].append((g, _f(r.get("m400")), _f(r.get("m600"))))
    for a in I:
        I[a] = sorted(set(I[a]), key=lambda x: (x[0], x[1] or 0, x[2] or 0))   # aynı gün tekrarları tek
    return I


def turet(ham, kosu_meta=None):
    """Ham dosyalardan koşan başına ara değerler: {"tarih|hipodrom|koşu|no": [HAM_ALANLAR...]} (goreli() ile yazılır).
    kosu_meta: (tarih, hipodrom, koşu) -> (pist, mesafe) (aynadan; yoksa soy_pist/soy_mes boş)."""
    import bisect
    P, S, I = _program(ham), _sonuclar(ham), _idman(ham)
    kosu_meta = dict(kosu_meta or {})
    for f in sorted(glob.glob(os.path.join(ham, "data", "yillik", "eslesme_*.csv.gz"))):   # aynadan önceki yıllar
        for r in _gz(f):
            h = HIP.get(r.get("hipodrom"))
            try:
                kk = (r["tarih"], h, int(r["kosu"]))
            except (TypeError, ValueError, KeyError):
                continue
            if h and kk not in kosu_meta:
                kosu_meta[kk] = (r.get("pist") or None, int(_f(r.get("mesafe")) or 0) or None)
    S_gun = defaultdict(list)
    for x in S:
        S_gun[x[0]].append(x)
    alan_n = defaultdict(int)
    for (t, h, k, no) in P:
        alan_n[(t, h, k)] += 1
    # babanın birikimli istatistiği: anahtar -> [koşu, galibiyet, beklenen galibiyet]
    soy = defaultdict(lambda: [0, 0.0, 0.0])
    gunler = sorted({t for (t, _, _, _) in P} | {t for (t, _, _) in S})
    P_gun = defaultdict(list)
    for key in P:
        P_gun[key[0]].append(key)
    out = {}

    def ae_k(a):   # küçültmeli (galibiyet + K) / (beklenen + K)
        return math.log((a[1] + SOY_K) / (a[2] + SOY_K)) if a[0] else None

    def mes_k(m):
        return None if not m else (0 if m <= 1300 else 1 if m <= 1800 else 2)

    for t in gunler:
        gun = date.fromisoformat(t).toordinal()
        # 1) bugünün özellikleri (yalnız dünden önce biriken soy + bugünden önceki idmanlar)
        for key in P_gun.get(t, []):
            r = P[key]
            pist, mes = kosu_meta.get(key[:3], (None, None))
            b = r["baba"]
            a0 = soy.get((b,)) if b else None
            ap = soy.get((b, "p", pist)) if (b and pist) else None
            am = soy.get((b, "m", mes_k(mes))) if (b and mes) else None
            L = I.get(r["at"]) or []
            i = bisect.bisect_left([x[0] for x in L], gun) if L else 0
            once = L[:i]
            id_gun = (gun - once[-1][0]) if once else None
            n30 = sum(1 for x in once if gun - x[0] <= 30)
            y45 = [x for x in once if gun - x[0] <= 45]
            b4 = min((x[1] for x in y45 if x[1] and 18 < x[1] < 40), default=None)
            b6 = min((x[2] for x in y45 if x[2] and 30 < x[2] < 60), default=None)
            out["|".join([key[0], key[1], str(key[2]), key[3]])] = [
                r["st"], alan_n[key[:3]], r["hk"], ae_k(a0) if a0 else None, ae_k(ap) if ap else None,
                ae_k(am) if am else None, a0[0] if a0 else 0, id_gun, n30, b4, b6]
        # 2) günün sonuçları soy tablosuna (gün sonunda)
        for (tt, h, k), L in ((x, S[x]) for x in S_gun.get(t, [])):
            N = len(L)
            if N < 2:
                continue
            pist, mes = kosu_meta.get((tt, h, k), (None, None))
            for no, sira, at in L:
                pr = P.get((tt, h, k, no))
                b = pr["baba"] if pr else ""
                if not b:
                    continue
                kaz = 1.0 if sira == 1 else 0.0
                for anah in [(b,)] + ([(b, "p", pist)] if pist else []) + ([(b, "m", mes_k(mes))] if mes else []):
                    s = soy[anah]; s[0] += 1; s[1] += kaz; s[2] += 1.0 / N
    return out


def goreli(ara):
    """HAM_ALANLAR -> ALANLAR: koşu içi göreli değerler (ham start/puan/derece depoya yazılmaz)."""
    kos = defaultdict(list)
    for k, v in ara.items():
        kos[k.rsplit("|", 1)[0]].append((k, dict(zip(HAM_ALANLAR, v))))
    out = {}
    for _, L in kos.items():
        hk = [r["hk"] for _, r in L if r["hk"]]
        hk_m = sum(hk) / len(hk) if hk else 0.0
        def med(xs):
            xs = sorted(x for x in xs if x)
            return xs[len(xs) // 2] if xs else 0.0
        m4, m6 = med(r["id_400"] for _, r in L), med(r["id_600"] for _, r in L)
        for k, r in L:
            st_g = ((r["st"] - 1) / max((r["n"] or 1) - 1, 1)) if r["st"] else None
            out[k] = [st_g, (r["hk"] - hk_m) if r["hk"] else None, r["soy_ae"], r["soy_pist"], r["soy_mes"], r["soy_n"],
                      r["id_gun"], r["id_n30"], (r["id_400"] - m4) if r["id_400"] else None,
                      (r["id_600"] - m6) if r["id_600"] else None]
    return out


def yaz(ozellik, cikti=CIKTI):
    """Aylık dosyalar (yalnız değişen ay yeniden yazılır). ozellik: goreli() çıktısı."""
    os.makedirs(cikti, exist_ok=True)
    aylar = defaultdict(dict)
    for k, v in ozellik.items():
        if k[:7] < ILK_AY:   # aynanın başlangıcından önceki aylar yalnız soy birikimi içindir; yazılmaz
            continue
        aylar[k[:7]][k] = [None if x is None else (round(x, 4) if isinstance(x, float) else x) for x in v]
    n = 0
    for ay, d in sorted(aylar.items()):
        yol = os.path.join(cikti, ay + ".json.gz")
        veri_ = {"alanlar": ALANLAR, "kaynak": "Ek kaynak A (türetilmiş; ham veri yayınlanmaz)", "v": d}
        ham = json.dumps(veri_, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        try:
            eski = gzip.open(yol).read()
        except OSError:
            eski = None
        if eski != ham:
            with open(yol + ".tmp", "wb") as f:
                f.write(gzip.compress(ham, mtime=0))
            os.replace(yol + ".tmp", yol)
            n += 1
    return n


def sizinti_testi(ham, meta, gunler):
    """Her D günü için: sonuçlar ve idmanlar D ve sonrasından ARINDIRILARAK yeniden türetilir; D'nin özellikleri tam
    türetmeyle birebir aynı olmalı (gelecekten bilgi yok). Ayrıca D'nin sonuçları karıştırılınca D değişmemeli."""
    global _program, _sonuclar, _idman
    tam = turet(ham, meta)
    asil = (_sonuclar, _idman)
    hata = []
    for D in gunler:
        g = date.fromisoformat(D).toordinal()
        _sonuclar = lambda h, _s=asil[0], _D=D: defaultdict(list, {k: v for k, v in _s(h).items() if k[0] < _D})
        _idman = lambda h, _i=asil[1], _g=g: defaultdict(list, {a: [x for x in L if x[0] < _g] for a, L in _i(h).items()})
        try:
            kes = turet(ham, meta)
        finally:
            _sonuclar, _idman = asil
        anah = [k for k in tam if k.startswith(D + "|")]
        fark = [k for k in anah if kes.get(k) != tam[k]]
        print(f"ek kaynak sızıntı {D}: {len(anah)} koşan, farklı {len(fark)}", flush=True)
        if fark or not anah:
            hata.append(D)
    return hata


_YUK = {}


def yukle(dizin=None):
    """Türetilmiş tablo: key -> dict(alan -> değer). Yoksa boş (özellikler 'ek yok')."""
    dizin = dizin or os.environ.get("AT_EK_OZELLIK") or CIKTI
    try:
        imza = (dizin, tuple(sorted((f, os.path.getmtime(os.path.join(dizin, f))) for f in os.listdir(dizin))))
    except OSError:
        return {}
    if imza in _YUK:
        return _YUK[imza]
    out = {}
    for f in sorted(glob.glob(os.path.join(dizin, "*.json.gz"))):
        try:
            d = json.loads(gzip.open(f).read())
        except (OSError, ValueError):
            continue
        al = d.get("alanlar") or ALANLAR
        for k, v in (d.get("v") or {}).items():
            out[k] = dict(zip(al, v))
    _YUK.clear()
    _YUK[imza] = out
    return out


def guncelle(kosular=None):
    """Üretim kancası (gece.py/canli.py): secret varsa çek -> türet -> yaz -> ham veriyi sil. Sağlık kaydı döner."""
    yerel = os.environ.get("AT_EK_YOL")
    ham = yerel or cek()
    if not ham:
        return {"durum": "atlandı", "neden": "ek kaynak yok"}
    try:
        meta = {}
        for k in kosular or []:
            meta[(k["tarih"], k["hipodrom"], k["kosu"])] = (k["pist"], k["mesafe"])
        if not meta:
            sys.path.insert(0, BURA)
            import veri
            for k in veri.sonuclari_yukle()[0]:
                meta[(k["tarih"], k["hipodrom"], k["kosu"])] = (k["pist"], k["mesafe"])
        oz = goreli(turet(ham, meta))
        n = yaz(oz)
        return {"durum": "tamam", "kosan": len(oz), "yazilan_ay": n}
    except Exception as e:   # noqa: BLE001
        return {"durum": "hata", "neden": type(e).__name__}
    finally:
        if not yerel:
            shutil.rmtree(ham, ignore_errors=True)   # ham veri diskte bırakılmaz


def _taze_mi(saat):
    """--gerekirse N: türetilmiş tablo son N saatte yazıldıysa yeniden çekme (gün içi akış her 30 dk çalışır)."""
    import time
    try:
        son = max(os.path.getmtime(f) for f in glob.glob(os.path.join(CIKTI, "*.json.gz")))
    except ValueError:
        return False
    durum = os.path.join(CIKTI, "_durum.json")
    try:
        son = max(son, json.load(open(durum)).get("ts", 0))
    except (OSError, ValueError):
        pass
    return time.time() - son < saat * 3600


if __name__ == "__main__":
    import time
    sys.path.insert(0, BURA)
    if "--gerekirse" in sys.argv:
        n = float(sys.argv[sys.argv.index("--gerekirse") + 1])
        if _taze_mi(n):
            print(f"ek kaynak: tablo {n:g} saatten taze, atlandı")
            sys.exit(0)
    sonuc = guncelle()
    if sonuc.get("durum") == "tamam":
        os.makedirs(CIKTI, exist_ok=True)
        json.dump({"ts": int(time.time()), **sonuc}, open(os.path.join(CIKTI, "_durum.json"), "w"), ensure_ascii=False)
    print("ek kaynak:", json.dumps(sonuc, ensure_ascii=False))
    sys.exit(1 if sonuc.get("durum") == "hata" else 0)
