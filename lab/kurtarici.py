"""🛟 Kurtarıcı bekçi (20 dakikada bir): yarım kalan / hata veren / hiç çalışmayan otomatik işleri fark eder ve devam ettirir.
Yalnız GitHub'ın açık kaynak `gh` aracını kullanır (ücretsiz). Issue, mail, bildirim AÇMAZ; ne yaptığını data/bekci.json'a,
sistemin sağlık özetini data/saglik.json'a yazar.
Kurallar (döngüye girmemesi için sınırlı):
  1) Hata veren son çalışma → yalnız 1 kez "başarısız adımları yeniden çalıştır" (run_attempt == 1 ise; 6 saatten eski hatalara dokunmaz).
  2) Kuyrukta 45 dk'dan uzun bekleyen çalışma → iptal + yeniden başlat.
  3) Son başarılı çalışma beklenen aralığın çok gerisinde ve şu an çalışan yoksa → elle tetikle (iş başına 2 saatte en çok 1 kez).
  4) SAĞLIK: iş akışları adımları hatayı yuttuğu için "success" görünür. Bu yüzden ayrıca data/saglik/<iş>.json (lab/adim.py:
     adım çıkış kodları) ve ana çıktı dosyalarının tazeliği okunur. Önemli bir adım başarısızsa ya da beklenen dosya bayatsa
     ilgili iş akışı bir kez yeniden tetiklenir: aynı sorun imzası için 6 saatte en çok 1 kez, kural 3'ün "2 saatte 1 elle
     tetikleme" sınırı ve "çalışan varsa dokunma" kuralı aynen geçerli. Kalite alarmları (data/qa*.json) yalnız kaydedilir.
  5) GEÇİCİ / KALICI: aynı adım imzası (<iş akışı>/<adım>) 24 saatte ≥3 kez hata verdiyse (lab/adim.py hata_24s) hata KALICI
     sayılır: yeniden tetikleme döngüsüne SOKULMAZ (aynı hatayı tekrar üretir, dakika harcar), yalnız data/saglik.json
     "kalici_alarm" listesinde raporlanır. Geçici hatalar kural 4'teki gibi bir kez yeniden tetiklenir.
  KURTARICI_DENEME=1 ile yalnız rapor eder, hiçbir şey yapmaz ve dosya yazmaz."""
import glob, json, os, subprocess, sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIKTI = os.path.join(ROOT, "data", "bekci.json")
SAGLIK = os.path.join(ROOT, "data", "saglik.json")
SAGLIK_DIZIN = os.path.join(ROOT, "data", "saglik")
DENEME = os.environ.get("KURTARICI_DENEME") == "1"
SAGLIK_TEKRAR_SAAT = 6.0
KALICI_ESIK, KALICI_SAAT = 3, 24

# dosya: (görünen ad, en fazla kaç saat başarısız kalabilir, yalnız bu UTC saatlerinde bekle)
ISLER = {
    "update.yml":        ("Futbol motoru",          2.5,  None),
    "live-log.yml":      ("Canlı kayıt",            1.0,  None),
    "at-canli.yml":      ("At yarışı canlı",        2.0,  range(9, 22)),
    "at-lab.yml":        ("At yarışı gece",         14.0, None),
    "otonom-ekip.yml":   ("Otonom ekip",            14.0, None),
    "auto-lab.yml":      ("Otomatik laboratuvar",   30.0, None),
    "surekli-deney.yml": ("Sürekli deney",          8.0,  None),
}

# Tazelik: (ad, dosya şablonu, zaman kaynağı, beklenen en fazla yaş (saat), sorumlu iş akışı, koşul)
#   zaman kaynağı: "commit" = dosyanın son commit zamanı; "alan:<anahtar>[:TR]" = dosyanın içindeki zaman alanı
TAZELIK = [
    ("Fikstür ve oranlar", "data/fixtures.json", "commit", 4.0, "update.yml", None),
    ("Futbol modeli", "data/model.json", "alan:updated:TR", 4.0, "update.yml", None),
    ("Günlük karne (toplayıcı)", "data/daily.json", "alan:updated", 4.0, "update.yml", None),
    ("Kilitli tahmin günlüğü (predlog)", "data/predlog.json", "commit", 12.0, "update.yml", None),
    ("Canlı kayıt nabzı", "data/health.json", "alan:zaman", 1.5, "live-log.yml", None),
    ("At yarışı canlı (bugün)", "data/at/canli/{bugun}.json", "alan:guncelleme_tsi:TR", 1.5, "at-canli.yml", "at_gunu"),
]


def gh(*a, js=True):
    r = subprocess.run(["gh", *a], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return json.loads(r.stdout) if js else r.stdout


def zaman(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def jl(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


# ------------------------------------------------------------------ tazelik
def _sig(*a):
    try:
        return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""


def commit_zamani(yol):
    """Dosyanın son commit zamanı. Tam geçmiş varsa yerel git, sığ klonda (Actions) GitHub API."""
    if _sig("rev-parse", "--is-shallow-repository") == "false":
        s = _sig("log", "-1", "--format=%cI", "--", yol)
        if s: return datetime.fromisoformat(s)
    try:
        s = gh("api", "-X", "GET", "repos/{owner}/{repo}/commits", "-f", f"path={yol}", "-f", "per_page=1",
               "--jq", ".[0].commit.committer.date", js=False).strip()
        return zaman(s) if s else None
    except Exception:
        return None


def alan_zamani(yol, anahtar, tr):
    d = jl(os.path.join(ROOT, yol))
    if not isinstance(d, dict) or not d.get(anahtar): return None
    s = str(d[anahtar]).replace(" UTC", "").replace("Z", "").replace(" ", "T")
    try:
        t = datetime.fromisoformat(s)
    except Exception:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone(timedelta(hours=3)) if tr else timezone.utc)
    return t


def tazelik(simdi):
    tr = simdi + timedelta(hours=3)
    bugun = tr.date().isoformat()
    out = []
    for ad, sablon, kaynak, beklenen, wf, kosul in TAZELIK:
        yol = sablon.format(bugun=bugun)
        if kosul == "at_gunu":
            # yalnız yarış günü (sabah kilidi var) ve TSİ 12:00–23:59 arası beklenir
            if not os.path.exists(os.path.join(ROOT, "data", "at", "tahmin", f"{bugun}.json")) or not (12 <= tr.hour <= 23):
                continue
        if kaynak == "commit":
            t = commit_zamani(yol) if os.path.exists(os.path.join(ROOT, yol)) else None
        else:
            _, anahtar, *tz = kaynak.split(":")
            t = alan_zamani(yol, anahtar, bool(tz))
        yas = round((simdi - t).total_seconds() / 3600, 2) if t else None
        out.append({"ad": ad, "dosya": yol, "yas_saat": yas, "beklenen_saat": beklenen, "is_akisi": wf,
                    "bayat": yas is None or yas > beklenen})
    return out


# ------------------------------------------------------------------ adım kayıtları ve kalite alarmları
def hata_24(a, simdi):
    n = 0
    for t in a.get("hata_24s") or []:
        try:
            if (simdi - zaman(t)).total_seconds() < KALICI_SAAT * 3600: n += 1
        except Exception:
            pass
    return n


def adim_kayitlari(simdi=None):
    """data/saglik/*.json → {iş akışı: {dosya: özet}}; yalnız o dosyadaki son çalışmanın adımları değerlendirilir.
    Her başarısız adım: sinif = kalici (24 saatte ≥KALICI_ESIK hata) | gecici."""
    simdi = simdi or datetime.now(timezone.utc)
    out = {}
    for p in sorted(glob.glob(os.path.join(SAGLIK_DIZIN, "*.json"))):
        D = jl(p, {}) or {}
        wf = D.get("is_akisi") or os.path.basename(p).replace(".json", ".yml")
        run = D.get("run")
        bas, bilgi = [], []
        for ad, a in (D.get("adimlar") or {}).items():
            if a.get("run") != run or a.get("rc") == 0: continue
            n24 = hata_24(a, simdi)
            kayit = {"adim": ad, "rc": a.get("rc"), "hata_tur": f"{a.get('hata', 1)}/{a.get('tur', 1)}", "hata_24s": n24,
                     "sinif": "kalici" if n24 >= KALICI_ESIK else "gecici", "imza": a.get("imza") or f"{wf}/{ad}",
                     "onem": a.get("onem", "onemli"), "bitis": a.get("bitis")}
            (bilgi if a.get("onem") == "bilgi" else bas).append(kayit)
        out.setdefault(wf, {})[os.path.basename(p)] = {"run": run, "guncelleme": D.get("guncelleme"), "basarisiz": bas, "bilgi_hata": bilgi}
    return out


def kalite_alarmlari():
    out = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "qa*.json"))):
        D = jl(p, {}) or {}
        if not isinstance(D, dict): continue
        out[os.path.basename(p)] = {"alarm": bool(D.get("alarm")), "zaman": D.get("zaman"), "hatalar": (D.get("hatalar") or [])[:8],
                                    "acilis_ms": D.get("acilis_ms")}
    return out


def kaynak_alarmlari():
    """data/saglik/at-kaynak.json (lab/at/kaynak_durum.py): açık arşiv aynasının gecikmesi. Yeniden tetikleme düzeltmez → yalnız rapor."""
    D = jl(os.path.join(SAGLIK_DIZIN, "at-kaynak.json"), {}) or {}
    if not isinstance(D, dict) or not D.get("alarm"): return []
    return [f"at kaynak gecikmesi: {x}" for x in (D.get("sorunlar") or ["alarm"])[:4]]


# ------------------------------------------------------------------ ana
def main():
    simdi = datetime.now(timezone.utc)
    durum, eylem = [], []
    eski = jl(CIKTI, {}) or {}
    tetik_gecmisi = dict(eski.get("saglik_tetik") or {})
    run_bilgi = {}
    for dosya, (ad, sinir_saat, saatler) in ISLER.items():
        try:
            runs = gh("run", "list", "-w", dosya, "-L", "15", "--json",
                      "databaseId,status,conclusion,createdAt,updatedAt,attempt,event")
        except Exception as e:
            durum.append({"is": ad, "durum": "okunamadı", "not": str(e)[:120]}); run_bilgi[dosya] = None; continue
        tamam = [r for r in runs if r["status"] == "completed"]
        calisan = [r for r in runs if r["status"] in ("in_progress", "queued", "waiting", "pending", "requested")]
        basari = [r for r in tamam if r["conclusion"] == "success"]
        son_basari_saat = round((simdi - zaman(basari[0]["updatedAt"])).total_seconds() / 3600, 2) if basari else None
        satir = {"is": ad, "son_basari_saat": son_basari_saat, "calisan": len(calisan), "durum": "sağlıklı"}
        eylem_oncesi = len(eylem)

        # 2) kuyrukta takılı kalan
        for r in calisan:
            if r["status"] in ("queued", "waiting", "pending", "requested") and (simdi - zaman(r["createdAt"])).total_seconds() > 45 * 60:
                eylem.append({"is": ad, "eylem": "takılı çalışma iptal edilip yeniden başlatıldı", "run": r["databaseId"]})
                if not DENEME:
                    try: gh("run", "cancel", str(r["databaseId"]), js=False)
                    except Exception: pass
                    try: gh("workflow", "run", dosya, "--ref", "main", js=False)
                    except Exception: pass
                satir["durum"] = "takıldı → kurtarıldı"; calisan = [r]
                break

        # 1) hata veren son çalışma → bir kez yeniden dene
        if tamam and tamam[0]["conclusion"] in ("failure", "timed_out", "startup_failure") and not calisan:
            r = tamam[0]
            yas = (simdi - zaman(r["updatedAt"])).total_seconds() / 3600
            if r.get("attempt", 1) == 1 and yas < 6:
                eylem.append({"is": ad, "eylem": "hata veren çalışma yeniden denendi", "run": r["databaseId"]})
                if not DENEME:
                    try: gh("run", "rerun", str(r["databaseId"]), "--failed", js=False)
                    except Exception as e: eylem[-1]["not"] = str(e)[:120]
                satir["durum"] = "hata → yeniden denendi"; calisan = [r]
            elif satir["durum"] == "sağlıklı":
                satir["durum"] = "hata (yeniden deneme hakkı bitti)"

        # 3) uzun süredir başarı yok ve çalışan yok → tetikle
        bekleme_saati = saatler is None or simdi.hour in saatler
        gec = son_basari_saat is None or son_basari_saat > sinir_saat
        son_elle = [r for r in runs if r["event"] == "workflow_dispatch"
                    and (simdi - zaman(r["createdAt"])).total_seconds() < 2 * 3600]
        if gec and bekleme_saati and not calisan:
            if son_elle:
                if satir["durum"] == "sağlıklı": satir["durum"] = "gecikmede (az önce tetiklendi, bekleniyor)"
            else:
                eylem.append({"is": ad, "eylem": f"{son_basari_saat} saattir başarı yok → yeniden başlatıldı"})
                if not DENEME:
                    try: gh("workflow", "run", dosya, "--ref", "main", js=False)
                    except Exception as e: eylem[-1]["not"] = str(e)[:120]
                satir["durum"] = "durmuştu → yeniden başlatıldı"
        run_bilgi[dosya] = {"calisan": bool(calisan), "son_elle": bool(son_elle), "eylem_var": len(eylem) > eylem_oncesi,
                            "bekleme_saati": bekleme_saati, "ad": ad}
        durum.append(satir)

    # 4) sağlık: adım çıkış kodları + dosya tazeliği + kalite alarmları
    adimlar = adim_kayitlari(simdi)
    taze = tazelik(simdi)
    kalite = kalite_alarmlari()
    sorun_is = {}
    kalici_alarm = []           # 5) kalıcı hatalar: yalnız rapor, yeniden tetikleme yok
    for wf, dosyalar in adimlar.items():
        for f, oz in dosyalar.items():
            for b in oz["basarisiz"] + oz["bilgi_hata"]:
                if b["sinif"] == "kalici":
                    kalici_alarm.append({"imza": b["imza"], "is_akisi": wf, "dosya": f, "adim": b["adim"], "rc": b["rc"],
                                         "hata_24s": b["hata_24s"], "onem": b["onem"], "son": b["bitis"]})
            for b in oz["basarisiz"]:
                if b["sinif"] == "kalici": continue
                sorun_is.setdefault(wf, []).append(f"adım başarısız: {b['adim']} (çıkış {b['rc']}, {b['hata_tur']} tur)")
    for t in taze:
        if t["bayat"]:
            sorun_is.setdefault(t["is_akisi"], []).append(f"bayat dosya: {t['dosya']} ({t['yas_saat']} sa > {t['beklenen_saat']} sa)")
    for wf, sorunlar in sorun_is.items():
        imza = " | ".join(sorted(sorunlar))
        rb = run_bilgi.get(wf)
        satir = next((s for s in durum if rb and s["is"] == rb["ad"]), None)
        if satir is not None and satir["durum"] == "sağlıklı": satir["durum"] = "sağlık sorunu"
        if satir is not None: satir["saglik"] = sorunlar[:6]
        if wf not in ISLER or not rb:
            continue                         # tanınmayan iş ya da çalışma listesi okunamadı → yalnız kayıt
        onceki = tetik_gecmisi.get(wf) or {}
        ayni_yakin = onceki.get("imza") == imza and (simdi - zaman(onceki.get("zaman", "2000-01-01T00:00Z"))).total_seconds() < SAGLIK_TEKRAR_SAAT * 3600
        if rb["calisan"] or rb["eylem_var"] or not rb["bekleme_saati"]:
            continue
        if rb["son_elle"] or ayni_yakin:
            if satir is not None: satir["durum"] = "sağlık sorunu (bir kez tetiklendi, bekleniyor)"
            continue
        eylem.append({"is": rb["ad"], "eylem": "sağlık kaydında sorun → bir kez yeniden tetiklendi", "neden": sorunlar[:4]})
        if not DENEME:
            try: gh("workflow", "run", wf, "--ref", "main", js=False)
            except Exception as e: eylem[-1]["not"] = str(e)[:120]
        tetik_gecmisi[wf] = {"imza": imza, "zaman": simdi.strftime("%Y-%m-%dT%H:%MZ")}
        if satir is not None: satir["durum"] = "sağlık sorunu → yeniden tetiklendi"
    # çözülen sorunların imzasını unut (aynı sorun ileride yeniden çıkarsa yine bir kez tetiklenebilsin)
    tetik_gecmisi = {k: v for k, v in tetik_gecmisi.items() if k in sorun_is}

    sorunlar = [f"{ISLER.get(wf, (wf,))[0]}: {s}" for wf, L in sorun_is.items() for s in L]
    sorunlar += [f"KALICI hata ({k['imza']}): 24 saatte {k['hata_24s']} kez, çıkış {k['rc']} — yeniden tetiklenmez, elle düzeltme gerekir"
                 for k in kalici_alarm if k["onem"] != "bilgi"]
    sorunlar += [f"kalite alarmı ({k}): {', '.join(v['hatalar'][:3]) or 'alarm'}" for k, v in kalite.items() if v["alarm"]]
    sorunlar += kaynak_alarmlari()   # yalnız rapor (kaynak yayınlayınca at-canli kendiliğinden toparlar)
    saglik = {"zaman": simdi.strftime("%Y-%m-%dT%H:%MZ"), "alarm": bool(sorunlar), "sorunlar": sorunlar,
              "kalici_alarm": kalici_alarm, "adimlar": adimlar, "tazelik": taze, "kalite": kalite,
              "aciklama": "Sağlık özeti (lab/kurtarici.py): adım çıkış kodları (data/saglik/*.json, lab/adim.py), ana dosyaların tazeliği, "
                          "kalite alarmları. Geçici sorunda ilgili iş akışı bir kez yeniden tetiklenir; kalici_alarm (aynı adım 24 saatte ≥3 hata) "
                          "yalnız raporlanır, yeniden tetiklenmez. Issue/mail/bildirim açılmaz."}

    gecmis = (eski.get("gecmis") or [])
    if eylem:
        gecmis = ([{"zaman": simdi.strftime("%Y-%m-%dT%H:%MZ"), **e} for e in eylem] + gecmis)[:40]
    out = {"zaman": simdi.strftime("%Y-%m-%dT%H:%MZ"), "deneme": DENEME, "isler": durum, "eylem": eylem, "gecmis": gecmis,
           "saglik_tetik": tetik_gecmisi}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: saglik[k] for k in ("alarm", "sorunlar", "tazelik")}, ensure_ascii=False, indent=1))
    if DENEME:
        return 0
    # Yalnız durum değiştiyse dosyayı yaz (gereksiz commit olmasın)
    imza = lambda d: json.dumps([[s["is"], s["durum"]] for s in d.get("isler", [])] + [d.get("gecmis", [])[:1]], ensure_ascii=False)
    if imza(out) != imza(eski) or eylem:
        json.dump(out, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    s_eski = jl(SAGLIK, {}) or {}
    try:
        s_yas = (simdi - zaman(s_eski.get("zaman", "2000-01-01T00:00Z"))).total_seconds() / 3600
    except Exception:
        s_yas = 99
    if s_eski.get("sorunlar") != saglik["sorunlar"] or s_eski.get("kalici_alarm") != saglik["kalici_alarm"] or s_yas > 3:
        json.dump(saglik, open(SAGLIK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
