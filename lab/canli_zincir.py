"""YH-100 · Canlı kayıt döngüsünün kendini zincirlemesi.

GitHub zamanlayıcısı bazı saatlerde depoda hiçbir işi başlatmıyor (2026-11-26 05:45 → 10:14 UTC: sıfır iş). live-log.yml
25 dk sürüp bitince YH-98 yedek çağrısı da susuyor ve bayat motoru tetikleyecek kimse kalmıyor. Bu betik live-log.yml'nin
son adımıdır: kuyrukta / bekleyen başka live-log yoksa live-log.yml'yi bir kez workflow_dispatch ile başlatır
(concurrency "live-log" en çok 1 çalışan + 1 bekleyen tutar). Döngü sürdükçe her turdaki yedek çağrı kurtarıcıyı
başlatır; neyi yeniden tetikleyeceğine yine yalnız lab/kurtarici.py karar verir.
Kapatma: data/ozellik.json → "canli_zincir": false. Hiçbir dosya yazmaz; her hatada 0 döner. ZINCIR_DENEME=1 → yalnız karar."""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DENEME = os.environ.get("ZINCIR_DENEME") == "1"
BEKLEYEN = ("queued", "waiting", "pending", "requested")


def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True, timeout=45)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout


def acik():
    try:
        return json.load(open(os.path.join(ROOT, "data", "ozellik.json"), encoding="utf-8")).get("canli_zincir", True) is not False
    except Exception:
        return True


def karar(runs, kendi_id, bayrak=True):
    """runs: gh run list --json databaseId,status çıktısı. Döner: (tetikle?, neden)."""
    if not bayrak:
        return False, "bayrak kapalı (ozellik.json canli_zincir=false)"
    diger = [r for r in runs if str(r.get("databaseId")) != str(kendi_id)]
    if any(r.get("status") in BEKLEYEN for r in diger):
        return False, "bekleyen live-log var"
    if any(r.get("status") == "in_progress" for r in diger):
        return False, "başka live-log çalışıyor"
    return True, "bekleyen yok"


def main():
    try:
        runs = json.loads(gh("run", "list", "-w", "live-log.yml", "-L", "10", "--json", "databaseId,status"))
        t, neden = karar(runs, os.environ.get("GITHUB_RUN_ID", ""), acik())
        if t and not DENEME:
            gh("workflow", "run", "live-log.yml", "--ref", "main")
        print(f"canlı zincir: {'sonraki tur başlatıldı' if t and not DENEME else ('başlatılırdı' if t else 'gerek yok')} — {neden}")
    except Exception as e:
        print(f"canlı zincir: atlandı ({str(e)[:120]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
