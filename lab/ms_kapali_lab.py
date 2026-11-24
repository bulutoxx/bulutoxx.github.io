#!/usr/bin/env python3
"""YH-95 — iddaa MS oranı kapanan maçta son bilinen oranın bültende tutulması: önceden kayıtlı kapı ölçümü.

  Veri : git geçmişindeki data/fixtures.json görüntüleri (2026-10-20 → bugün); her maç için başlamadan önceki son görüntü
         (A = üretim) ve o ana kadar oranlı son görüntü (B = aday; yalnız geçmiş görüntüler, sızıntı yok).
  Sonuç: data/archive (iid → kilitli `ms` ve skor).
  Kapı : lab/YOL_HARITASI.md YH-95 (1) kapsam, (2) kilitli kayıtla tutarlılık, (3) kalite (taze oranlı aynı bant), (4) birim sınaması.
  Çıktı: data/ms_kapali_lab.json (yalnız türetilmiş özet; ham oran yazılmaz).
"""
import glob, json, os, subprocess, sys
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
UK = ZoneInfo("Europe/London")
SINCE, BANT, B = "2026-10-20", (1.04, 1.12), 4000
RNG = np.random.default_rng(95)


def ko(f):
    try: return datetime.fromisoformat(f["d"] + "T" + (f.get("t") or "00:00")).replace(tzinfo=UK)
    except Exception: return None


def goruntuler():
    revs = subprocess.run(["git", "-C", ROOT, "log", f"--since={SINCE}", "--format=%H %cI", "--", "data/fixtures.json"],
                          capture_output=True, text=True).stdout.split("\n")
    son, sonio = {}, {}
    for line in reversed([r for r in revs if r.strip()]):
        h, t = line.split(); ct = datetime.fromisoformat(t)
        try: L = json.loads(subprocess.run(["git", "-C", ROOT, "show", h + ":data/fixtures.json"], capture_output=True, text=True).stdout)
        except Exception: continue
        for f in L:
            if not isinstance(f, dict) or not f.get("iid"): continue
            k0 = ko(f)
            if k0 is None or ct >= k0: continue
            k = str(f["iid"]); son[k] = (f, ct)
            if f.get("io"): sonio[k] = (f, ct)
    return son, sonio


def arsiv():
    A = {}
    for p in glob.glob(os.path.join(DATA, "archive", "*.json")):
        try: D = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        if isinstance(D, dict): A.update({str(k): r for k, r in D.items() if isinstance(r, dict)})
    return A


def power(o):
    from update import power_devig
    return np.array(power_devig(list(o)), float)


def sonuc(r):
    if not (isinstance(r.get("hs"), int) and isinstance(r.get("as"), int)): return None
    return 0 if r["hs"] > r["as"] else 1 if r["hs"] == r["as"] else 2


def birim():
    """(4) merge_iddaa'nın add_io dalı yerine son_bilinen_oran + taşıma kuralı sahte verilerle."""
    import tempfile, update as U
    simdi = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)
    eski = [{"d": "2026-11-24", "t": "20:00", "iid": 1, "io": [1.05, 8.4, 11.6], "odds": [1.05, 8.4, 11.6], "po": {"1": 1.05}},
            {"d": "2026-11-24", "t": "09:00", "iid": 2, "io": [1.06, 7.0, 12.0]},     # başlamış
            {"d": "2026-11-25", "t": "18:00", "iid": 3}]                                # oransız
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh: json.dump(eski, fh); p = fh.name
    E = U.son_bilinen_oran(p, simdi); os.unlink(p)
    ok = set(E) == {"1"} and E["1"]["io"] == [1.05, 8.4, 11.6] and E["1"]["po"] == {"1": 1.05}
    # kaynak kodda taşıma dalı ve işaret
    src = open(os.path.join(ROOT, "scripts", "update.py"), encoding="utf-8").read()
    ok = ok and 'f["ioe"] = 1' in src and "eski_io = son_bilinen_oran(" in src
    # MS açık dal değişmedi: add_io'da 'f["io"] = mk["ms"]' satırı aynen
    ok = ok and 'f["io"] = mk["ms"]' in src
    return bool(ok)


def boot_ust(x):
    x = np.asarray(x); i = RNG.integers(0, len(x), (B, len(x)))
    return float(np.percentile(x[i].mean(1), 97.5))


def main():
    son, sonio = goruntuler(); A = arsiv()
    kay = [k for k in son if not son[k][0].get("io") and k in sonio]
    i_lig = [k for k in kay if str(son[k][0].get("lg", "")).startswith("i")]
    bitti, tutarli, ll_b = 0, 0, []
    for k in kay:
        r = A.get(k)
        if not r: continue
        y = sonuc(r)
        if y is None: continue
        bitti += 1
        io = sonio[k][0]["io"]
        if r.get("ms") and [round(float(v), 2) for v in r["ms"]] == [round(float(v), 2) for v in io]: tutarli += 1
        p = power(io); ll_b.append(-np.log(max(p[y], 1e-9)))
    kay_set = set(kay); ll_t = []
    for k, r in A.items():
        if k in kay_set or not r.get("ms"): continue
        y = sonuc(r)
        if y is None: continue
        try: ms = [float(v) for v in r["ms"]]
        except Exception: continue
        if len(ms) != 3 or not (BANT[0] <= min(ms) <= BANT[1]): continue
        if (k in son and not son[k][0].get("io")): continue
        p = power(ms); ll_t.append(-np.log(max(p[y], 1e-9)))
    ust = boot_ust(ll_t) if ll_t else None
    k1 = len(kay) >= 50 and len(i_lig) >= 30
    k2 = bitti > 0 and tutarli / bitti >= 0.95
    k3 = bool(ll_b) and ust is not None and float(np.mean(ll_b)) <= ust
    k4 = birim()
    bosluk = sorted((ko(son[k][0]) - sonio[k][1]).total_seconds() / 3600 for k in kay)
    out = {"tarih": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "madde": "YH-95", "veri_bas": SINCE,
           "mac": len(son), "kaybolan": len(kay), "kaybolan_i_lig": len(i_lig), "sonuclanan": bitti,
           "kilitli_tutarli": tutarli, "kilitli_tutarli_oran": round(tutarli / bitti, 4) if bitti else None,
           "ll_tasinan": round(float(np.mean(ll_b)), 4) if ll_b else None,
           "isabet_tasinan": None,
           "ll_taze_bant": round(float(np.mean(ll_t)), 4) if ll_t else None, "ll_taze_bant_ga_ust": round(ust, 4) if ust else None,
           "n_taze_bant": len(ll_t), "oransiz_saat_medyan": round(float(np.median(bosluk)), 2) if bosluk else None,
           "kapi": {"1_kapsam": k1, "2_tutarlilik": k2, "3_kalite": k3, "4_birim": k4}, "gecti": bool(k1 and k2 and k3 and k4)}
    # isabet (favori kazandı mı) — bilgi
    fav = [int(np.argmax(power(sonio[k][0]["io"])) == sonuc(A[k])) for k in kay if A.get(k) and sonuc(A[k]) is not None]
    out["isabet_tasinan"] = round(float(np.mean(fav)), 4) if fav else None
    json.dump(out, open(os.path.join(DATA, "ms_kapali_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
