#!/usr/bin/env python3
"""YH-102 yeniden oynatma: data/saglik/*.json git geçmişinden adım çıkışlarını çıkarır, her 20 dk'lık bekçi anında
yalnız o ana kadarki kayıtlarla eski kural (A: 24 saatte ≥3 hata → kalıcı) ve yeni kural (B: A + son 7 günde ≥3 farklı
günde hata, son çalışma başarısız → tekrar) alarmlarını hesaplar. Yalnız standart kütüphane; çıktı data/tekrar_alarm_lab.json.
  python3 lab/tekrar_alarm_lab.py [--bas 2026-10-28]"""
import json, os, subprocess, sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lab"))
import kurtarici as K  # noqa: E402

BAS = sys.argv[sys.argv.index("--bas") + 1] if "--bas" in sys.argv else "2026-10-28"
Z = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))


def olaylar():
    log = subprocess.run(["git", "log", f"--since={BAS}", "--reverse", "--format=@%H", "--name-only", "--", "data/saglik/"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    istek, c = [], None
    for ln in log.splitlines():
        if ln.startswith("@"): c = ln[1:]
        elif ln.startswith("data/saglik/") and ln.endswith(".json"): istek.append((c, ln))
    p = subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    ev = {}
    for c, yol in istek:
        p.stdin.write(f"{c}:{yol}\n".encode()); p.stdin.flush()
        bas = p.stdout.readline().split()
        if len(bas) < 3 or bas[1] == b"missing": continue
        veri = p.stdout.read(int(bas[2])); p.stdout.read(1)
        try: D = json.loads(veri)
        except Exception: continue
        wf = D.get("is_akisi") or os.path.basename(yol).replace(".json", ".yml")
        for ad, a in (D.get("adimlar") or {}).items():
            if not a.get("bitis") or a.get("rc") is None: continue
            imza = a.get("imza") or f"{wf}/{ad}"
            k = (imza, os.path.basename(yol), a.get("run"), a.get("tur", 1))
            ev[k] = {"imza": imza, "dosya": os.path.basename(yol), "run": a.get("run"), "rc": a.get("rc"),
                     "bitis": a["bitis"], "onem": a.get("onem", "onemli")}
    p.stdin.close(); p.wait()
    return sorted(ev.values(), key=lambda e: e["bitis"])


def main():
    E = olaylar()
    bas = Z(BAS + "T00:00:00Z"); son = datetime.now(timezone.utc)
    seri = {}
    for e in E: seri.setdefault((e["dosya"], e["imza"]), []).append(e)
    A, B = {}, {}   # imza → ilk alarm anı
    t = bas
    while t <= son:
        for (f, im), L in seri.items():
            gecmis = [e for e in L if Z(e["bitis"]) <= t]
            if not gecmis or gecmis[-1]["rc"] == 0: continue
            hatalar = [Z(e["bitis"]) for e in gecmis if e["rc"] != 0]
            a = {"hata_24s": [h.strftime("%Y-%m-%dT%H:%M:%SZ") for h in hatalar if h > t - timedelta(hours=24)],
                 "hata_gun": sorted(set(h.strftime("%Y-%m-%d") for h in hatalar if h.strftime("%Y-%m-%d") >= (t - timedelta(days=6)).strftime("%Y-%m-%d")))}
            n24 = K.hata_24(a, t); ng = K.hata_gun_say(a, t)
            kalici = n24 >= K.KALICI_ESIK
            if kalici: A.setdefault(im, t.strftime("%Y-%m-%dT%H:%MZ")); B.setdefault(im, t.strftime("%Y-%m-%dT%H:%MZ"))
            elif ng >= K.TEKRAR_ESIK: B.setdefault(im, t.strftime("%Y-%m-%dT%H:%MZ"))
        t += timedelta(minutes=20)
    ek = {im: B[im] for im in B if im not in A}
    gunler = {im: sorted(set(e["bitis"][:10] for (f, i2), L in seri.items() if i2 == im for e in L if e["rc"] != 0)) for im in ek}
    hedef = ["auto-lab.yml/canli-guc", "auto-lab.yml/canli-piyasa"]
    k1 = all(h in ek and ek[h][:10] <= "2026-11-24" for h in hedef) and not any(h in A for h in hedef)
    k2 = len(ek) <= 6 and all(len(gunler[im]) >= 3 for im in ek)
    out = {"zaman": son.strftime("%Y-%m-%dT%H:%MZ"), "bas": BAS, "olay": len(E), "imza": len(seri),
           "hata_olayi": sum(1 for e in E if e["rc"] != 0), "A_alarm": A, "B_ek_alarm": ek, "B_ek_hata_gunleri": gunler,
           "kapi": {"1_hedef_erken": k1, "2_gurultu": k2, "gecti": k1 and k2},
           "aciklama": "YH-102 yeniden oynatma (lab/tekrar_alarm_lab.py). A = 24 saatte ≥3 hata; B = A + son 7 günde ≥3 farklı günde hata "
                       "ve son çalışma başarısız. Alarm anı = ilk 20 dk'lık bekçi anı."}
    json.dump(out, open(os.path.join(ROOT, "data", "tekrar_alarm_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("olay", "imza", "hata_olayi", "A_alarm", "B_ek_alarm", "B_ek_hata_gunleri", "kapi")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
