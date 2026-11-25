"""YH-98 · Yedek kurtarıcı çağrısı.

GitHub zamanlayıcısı yoğun saatlerde kısa aralıklı cron'ları seyreltiyor (2026-11-22 → 25: kurtarici.yml beklenen ≈ 246
turdan 30'u, update.yml ≈ 82 saatlik turdan 24'ü başladı); kurtarıcı başlamayınca bayat motor da yeniden tetiklenmiyor.
Bu betik, zaten çalışan başka bir işin (canlı kayıt döngüsü, sürekli deney) içinden çağrılır: son kurtarıcı turu
ARALIK_DK dakikadan eskiyse ve çalışan / kuyrukta kurtarıcı yoksa kurtarici.yml'yi workflow_dispatch ile bir kez başlatır.
Neyi yeniden tetikleyeceğine yine yalnız lab/kurtarici.py karar verir (tek karar yeri).
Hiçbir dosya yazmaz; her hatada sessizce 0 döner (çağıran işi asla bozmaz). YEDEK_DENEME=1 → yalnız karar yazdırılır."""
import json, os, subprocess, sys
from datetime import datetime, timezone

ARALIK_DK = float(os.environ.get("YEDEK_ARALIK_DK", "40"))
DENEME = os.environ.get("YEDEK_DENEME") == "1"


def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True, timeout=45)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout


def karar(runs, simdi, aralik_dk=ARALIK_DK):
    """runs: gh run list --json status,createdAt çıktısı. Döner: (tetikle?, neden)."""
    if any(r.get("status") in ("queued", "in_progress", "waiting", "pending", "requested") for r in runs):
        return False, "kurtarıcı çalışıyor / kuyrukta"
    if not runs:
        return True, "kurtarıcı kaydı yok"
    son = max(datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00")) for r in runs)
    dk = (simdi - son).total_seconds() / 60
    if dk > aralik_dk:
        return True, f"son kurtarıcı {dk:.0f} dk önce (> {aralik_dk:.0f})"
    return False, f"son kurtarıcı {dk:.0f} dk önce"


def main():
    try:
        runs = json.loads(gh("run", "list", "-w", "kurtarici.yml", "-L", "5", "--json", "status,createdAt"))
        t, neden = karar(runs, datetime.now(timezone.utc))
        if t and not DENEME:
            gh("workflow", "run", "kurtarici.yml", "--ref", "main")
        print(f"yedek kurtarıcı: {'tetiklendi' if t and not DENEME else ('tetiklenirdi' if t else 'gerek yok')} — {neden}")
    except Exception as e:
        print(f"yedek kurtarıcı: atlandı ({str(e)[:120]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
