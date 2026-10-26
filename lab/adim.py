#!/usr/bin/env python3
"""🩺 Adım kaydedici: iş akışı adımını çalıştırır, çıkış kodunu ve süresini data/saglik/<iş akışı>.json'a yazar.

Hata yutulmaz, kaydedilir: adımın çıkış kodu ne olursa olsun kayıt düşer. Varsayılan olarak bu betik 0 ile çıkar
("hata sistemi durdurmaz" kuralı; diğer adımlar ve yayın devam eder). --kritik verilirse adımın çıkış kodu aynen döner.
Kurtarıcı (lab/kurtarici.py) bu kayıtları okur: önemli bir adım başarısızsa ilgili iş akışını bir kez yeniden tetikler.

  python3 lab/adim.py <ad> [--onem onemli|bilgi] [--kritik] -- komut arg...
  python3 lab/adim.py <ad> -- "kabuk komutu && başka komut"      # tek argüman: bash -o pipefail -c ile çalışır

Dosya adı: GITHUB_WORKFLOW_REF'teki iş akışı dosyasından (ör. live-log.yml → data/saglik/live-log.json);
ADIM_ALT ortam değişkeni varsa sonuna eklenir (matris işleri: surekli-deney-futbol.json). Yerelde --is ile verilebilir.
Yalnız standart kütüphane. Issue, mail, bildirim AÇMAZ.
"""
import argparse, json, os, subprocess, sys, time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIZIN = os.path.join(ROOT, "data", "saglik")


def is_akisi():
    ref = os.environ.get("GITHUB_WORKFLOW_REF", "")          # owner/repo/.github/workflows/x.yml@refs/heads/main
    if ".github/workflows/" in ref:
        return ref.split(".github/workflows/", 1)[1].split("@", 1)[0]
    return os.environ.get("ADIM_IS", "yerel.yml")


def dosya_yolu(wf):
    ad = os.path.splitext(os.path.basename(wf))[0]
    alt = os.environ.get("ADIM_ALT", "").strip()
    return os.path.join(DIZIN, f"{ad}-{alt}.json" if alt else f"{ad}.json")


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def imza(D):
    """Durum imzası: bu çalışmadaki adımların ad + başarılı/başarısız bilgisi (zaman ve süre hariç)."""
    run = D.get("run")
    return "|".join(sorted(f"{k}:{'ok' if a.get('rc') == 0 else 'HATA'}" for k, a in (D.get("adimlar") or {}).items() if a.get("run") == run))


def kaydet(wf, ad, rc, sn, onem):
    p = dosya_yolu(wf)
    try:
        D = json.load(open(p, encoding="utf-8"))
    except Exception:
        D = {}
    run = os.environ.get("GITHUB_RUN_ID", "yerel")
    if D.get("run") != run:
        D["run"], D["deneme"], D["baslangic"] = run, os.environ.get("GITHUB_RUN_ATTEMPT", "1"), simdi()
    D["is_akisi"] = os.path.basename(wf)
    A = D.setdefault("adimlar", {})
    eski = A.get(ad) if (A.get(ad) or {}).get("run") == run else None
    tur = (eski or {}).get("tur", 0) + 1
    hata = (eski or {}).get("hata", 0) + (1 if rc != 0 else 0)
    A[ad] = {"rc": rc, "sn": round(sn, 1), "bitis": simdi(), "run": run, "onem": onem, "tur": tur, "hata": hata}
    D["guncelleme"] = simdi()
    D["imza"] = imza(D)
    D["aciklama"] = "Adım çıkış kodları (lab/adim.py). rc≠0 = adım başarısız; onem=bilgi olanlar yeniden tetikleme sebebi sayılmaz."
    os.makedirs(DIZIN, exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def main():
    argv = sys.argv[1:]
    if "--" not in argv:
        print("kullanım: adim.py <ad> [--onem onemli|bilgi] [--kritik] [--is x.yml] -- komut", file=sys.stderr); return 2
    i = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("ad"); ap.add_argument("--onem", default="onemli", choices=["onemli", "bilgi"])
    ap.add_argument("--kritik", action="store_true"); ap.add_argument("--is", dest="is_", default=None)
    ar = ap.parse_args(argv[:i])
    komut = argv[i + 1:]
    if not komut:
        print("komut yok", file=sys.stderr); return 2
    wf = ar.is_ or is_akisi()
    t0 = time.time()
    try:
        if len(komut) == 1:
            rc = subprocess.run(["bash", "-o", "pipefail", "-c", komut[0]]).returncode
        else:
            rc = subprocess.run(komut).returncode
    except FileNotFoundError as e:
        print(f"komut bulunamadı: {e}", file=sys.stderr); rc = 127
    sn = time.time() - t0
    try:
        kaydet(wf, ar.ad, rc, sn, ar.onem)
    except Exception as e:                      # kayıt yazılamasa da adımın sonucu değişmesin
        print(f"sağlık kaydı yazılamadı: {e}", file=sys.stderr)
    if rc != 0:
        print(f"::warning title=Adım başarısız: {ar.ad}::çıkış kodu {rc}, {sn:.0f} sn (data/saglik kaydına yazıldı)")
    else:
        print(f"[adım] {ar.ad}: tamam ({sn:.0f} sn)")
    return rc if ar.kritik else 0


if __name__ == "__main__":
    sys.exit(main())
