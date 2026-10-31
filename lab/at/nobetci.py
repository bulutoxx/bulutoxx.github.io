# OXXai at yarışı — KAYNAK NÖBETÇİSİ (v152; at bölümü kapalıyken).
# At bölümü data/ozellik.json ile kapatıldı (açık sonuç/program aynası 27.10.2026'dan beri güncellenmiyor) ve at-canli.yml /
# at-lab.yml GitHub'da devre dışı. Bu betik günde bir kez (auto-lab.yml) aynanın son commit karmasını `git ls-remote` ile okur
# (klonlama yok, tek hafif istek) ve data/saglik/at-kaynak.json'daki kayıtlı değerle karşılaştırır:
#   • kayıt yoksa: karmayı yazar (başlangıç);
#   • karma değiştiyse: "at_kaynak_dondu": <TSİ tarih> yazar → kaynak yeniden güncelleniyor, at bölümü geri açılabilir.
# Yalnız yazar: at iş akışlarını TETİKLEMEZ, uygulamada görünmez, alarm üretmez. Değişiklik yoksa dosyaya dokunmaz (boş commit yok).
# Hata (ağ yok vb.) sessizce geçilir, çıkış kodu 0.
import json, os, subprocess, sys
from datetime import datetime, timedelta, timezone

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAGLIK = os.path.join(KOK, "data", "saglik", "at-kaynak.json")
AYNA = "https://github.com/cenkozgur/tjk-data"
TSI = timezone(timedelta(hours=3))


def karma():
    r = subprocess.run(["git", "ls-remote", AYNA, "HEAD"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError((r.stderr or "boş yanıt").strip()[:160])
    return r.stdout.split()[0]


def main():
    try:
        D = json.load(open(SAGLIK, encoding="utf-8"))
        if not isinstance(D, dict): D = {}
    except Exception:
        D = {}
    try:
        h = karma()
    except Exception as e:  # noqa: BLE001
        print(f"[at-nöbetçi] ayna okunamadı: {e}"); return 0
    simdi = datetime.now(TSI)
    eski = D.get("nobetci_karma")
    if eski == h:
        print(f"[at-nöbetçi] değişiklik yok ({h[:10]})"); return 0
    D["nobetci_karma"] = h
    D["nobetci_not"] = ("At bölümü kapalıyken kaynak nöbetçisi (lab/at/nobetci.py, auto-lab.yml): aynanın HEAD karması değişince "
                        "at_kaynak_dondu yazılır. Geri açmak: data/ozellik.json \"at\": true + at-canli.yml, at-lab.yml enable.")
    if eski:
        D["at_kaynak_dondu"] = simdi.date().isoformat()
        D["nobetci_degisim"] = simdi.strftime("%Y-%m-%dT%H:%M%z")
        print(f"[at-nöbetçi] KAYNAK GÜNCELLENDİ: {eski[:10]} → {h[:10]} (at_kaynak_dondu = {D['at_kaynak_dondu']})")
    else:
        D["nobetci_ilk"] = simdi.strftime("%Y-%m-%dT%H:%M%z")
        print(f"[at-nöbetçi] başlangıç karması kaydedildi: {h[:10]}")
    os.makedirs(os.path.dirname(SAGLIK), exist_ok=True)
    with open(SAGLIK + ".tmp", "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, indent=1); f.write("\n")
    os.replace(SAGLIK + ".tmp", SAGLIK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
