"""🛟 Kurtarıcı bekçi (20 dakikada bir): yarım kalan / hata veren / hiç çalışmayan otomatik işleri fark eder ve devam ettirir.
Yalnız GitHub'ın açık kaynak `gh` aracını kullanır (ücretsiz). Issue, mail, bildirim AÇMAZ; ne yaptığını data/bekci.json'a yazar.
Kurallar (döngüye girmemesi için sınırlı):
  1) Hata veren son çalışma → yalnız 1 kez "başarısız adımları yeniden çalıştır" (run_attempt == 1 ise; 6 saatten eski hatalara dokunmaz).
  2) Kuyrukta 45 dk'dan uzun bekleyen çalışma → iptal + yeniden başlat.
  3) Son başarılı çalışma beklenen aralığın çok gerisinde ve şu an çalışan yoksa → elle tetikle (iş başına 2 saatte en çok 1 kez).
  KURTARICI_DENEME=1 ile yalnız rapor eder, hiçbir şey yapmaz."""
import json, os, subprocess, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIKTI = os.path.join(ROOT, "data", "bekci.json")
DENEME = os.environ.get("KURTARICI_DENEME") == "1"

# dosya: (görünen ad, en fazla kaç saat başarısız kalabilir, yalnız bu UTC saatlerinde bekle)
ISLER = {
    "update.yml":      ("Futbol motoru",          2.5,  None),
    "live-log.yml":    ("Canlı kayıt",            1.0,  None),
    "at-canli.yml":    ("At yarışı canlı",        2.0,  range(9, 22)),
    "at-lab.yml":      ("At yarışı gece",         14.0, None),
    "otonom-ekip.yml": ("Otonom ekip",            14.0, None),
    "auto-lab.yml":    ("Otomatik laboratuvar",   30.0, None),
}


def gh(*a, js=True):
    r = subprocess.run(["gh", *a], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return json.loads(r.stdout) if js else r.stdout


def zaman(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main():
    simdi = datetime.now(timezone.utc)
    durum, eylem = [], []
    for dosya, (ad, sinir_saat, saatler) in ISLER.items():
        try:
            runs = gh("run", "list", "-w", dosya, "-L", "15", "--json",
                      "databaseId,status,conclusion,createdAt,updatedAt,attempt,event")
        except Exception as e:
            durum.append({"is": ad, "durum": "okunamadı", "not": str(e)[:120]}); continue
        tamam = [r for r in runs if r["status"] == "completed"]
        calisan = [r for r in runs if r["status"] in ("in_progress", "queued", "waiting", "pending", "requested")]
        basari = [r for r in tamam if r["conclusion"] == "success"]
        son_basari_saat = round((simdi - zaman(basari[0]["updatedAt"])).total_seconds() / 3600, 2) if basari else None
        satir = {"is": ad, "son_basari_saat": son_basari_saat, "calisan": len(calisan), "durum": "sağlıklı"}

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
        if gec and bekleme_saati and not calisan:
            son_elle = [r for r in runs if r["event"] == "workflow_dispatch"
                        and (simdi - zaman(r["createdAt"])).total_seconds() < 2 * 3600]
            if son_elle:
                if satir["durum"] == "sağlıklı": satir["durum"] = "gecikmede (az önce tetiklendi, bekleniyor)"
            else:
                eylem.append({"is": ad, "eylem": f"{son_basari_saat} saattir başarı yok → yeniden başlatıldı"})
                if not DENEME:
                    try: gh("workflow", "run", dosya, "--ref", "main", js=False)
                    except Exception as e: eylem[-1]["not"] = str(e)[:120]
                satir["durum"] = "durmuştu → yeniden başlatıldı"
        durum.append(satir)

    try:
        eski = json.load(open(CIKTI, encoding="utf-8"))
    except Exception:
        eski = {}
    gecmis = (eski.get("gecmis") or [])
    if eylem:
        gecmis = ([{"zaman": simdi.strftime("%Y-%m-%dT%H:%MZ"), **e} for e in eylem] + gecmis)[:40]
    out = {"zaman": simdi.strftime("%Y-%m-%dT%H:%MZ"), "deneme": DENEME, "isler": durum, "eylem": eylem, "gecmis": gecmis}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    # Yalnız durum değiştiyse dosyayı yaz (gereksiz commit olmasın)
    imza = lambda d: json.dumps([[s["is"], s["durum"]] for s in d.get("isler", [])] + [d.get("gecmis", [])[:1]], ensure_ascii=False)
    if not DENEME and (imza(out) != imza(eski) or eylem):
        json.dump(out, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
