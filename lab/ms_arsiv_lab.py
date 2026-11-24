#!/usr/bin/env python3
"""YH-96 — YH-95 zinciri koptuğunda kilitli arşivin son bilinen MS oranına düşülmesi: önceden kayıtlı kapı ölçümü.

  Veri : git geçmişindeki data/fixtures.json görüntüleri (2026-10-20 → bugün). Her maç için başlamadan önceki son görüntü (A),
         YH-95 (B1: o ana kadar oranlı son görüntü) ve YH-96 (B2: B1 yoksa o commit'teki data/archive kaydı — sızıntısız).
  Sonuç: son data/archive (iid → kilitli `ms` ve skor).
  Kapı : lab/YOL_HARITASI.md YH-96 (1) kazanım ≥ 3, (2) kilitli kayıtla %100 tutarlılık, (3) kalite, (4) birim sınaması.
  Çıktı: data/ms_arsiv_lab.json (yalnız türetilmiş özet; ham oran yazılmaz).
"""
import json, os, subprocess, sys, tempfile
from datetime import datetime, timezone, timedelta
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab")); sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ms_kapali_lab as M95   # noqa: E402


def goruntuler():
    """son[k] = (maç, commit zamanı, commit); sonio[k] = oranlı son görüntü."""
    revs = subprocess.run(["git", "-C", ROOT, "log", f"--since={M95.SINCE}", "--format=%H %cI", "--", "data/fixtures.json"],
                          capture_output=True, text=True).stdout.split("\n")
    son, sonio = {}, {}
    for line in reversed([r for r in revs if r.strip()]):
        h, t = line.split(); ct = datetime.fromisoformat(t)
        try: L = json.loads(subprocess.run(["git", "-C", ROOT, "show", h + ":data/fixtures.json"], capture_output=True, text=True).stdout)
        except Exception: continue
        for f in L:
            if not isinstance(f, dict) or not f.get("iid"): continue
            k0 = M95.ko(f)
            if k0 is None or ct >= k0: continue
            k = str(f["iid"]); son[k] = (f, ct, h)
            if f.get("io"): sonio[k] = (f, ct)
    return son, sonio


_ARS = {}
def arsiv_o_an(h, ct):
    """O commit'teki data/archive (dün … ileri günler) → update.arsiv_oran ile aynı kural."""
    if h in _ARS: return _ARS[h]
    import update as U
    ls = subprocess.run(["git", "-C", ROOT, "ls-tree", "--name-only", h, "data/archive/"], capture_output=True, text=True).stdout.split()
    g0 = (ct - timedelta(days=1)).date().isoformat()
    with tempfile.TemporaryDirectory() as td:
        for p in ls:
            b = os.path.basename(p)
            if len(b) != 15 or not b.endswith(".json") or b[:10] < g0: continue
            icerik = subprocess.run(["git", "-C", ROOT, "show", f"{h}:{p}"], capture_output=True, text=True).stdout
            open(os.path.join(td, b), "w", encoding="utf-8").write(icerik)
        _ARS[h] = U.arsiv_oran(td, ct.astimezone(timezone.utc))
    return _ARS[h]


def birim():
    import update as U
    simdi = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc); t = simdi.timestamp()
    with tempfile.TemporaryDirectory() as td:
        json.dump({"7": {"ts": t + 3600, "ms": [1.05, 8.38, 11.65], "ou": [1.06, 4.74], "kgo": [1.41, 2.23]},
                   "8": {"ts": t - 60, "ms": [1.1, 7.0, 12.0]},          # başlamış
                   "9": {"ts": t + 3600}},                                # oransız
                  open(os.path.join(td, "2026-11-24.json"), "w"))
        json.dump({"6": {"ts": t + 9e4, "ms": [2.0, 3.0, 3.5]}}, open(os.path.join(td, "2026-11-20.json"), "w"))  # eski gün okunmaz
        E = U.arsiv_oran(td, simdi)
    ok = set(E) == {"7"} and E["7"]["io"] == [1.05, 8.38, 11.65] and E["7"]["iou"] == [1.06, 4.74] and E["7"]["ikg"] == [1.41, 2.23]
    ok = ok and E["7"]["po"] == {"1": 1.05, "X": 8.38, "2": 11.65, "U25": 1.06, "A25": 4.74, "KGV": 1.41, "KGY": 2.23}
    src = open(os.path.join(ROOT, "scripts", "update.py"), encoding="utf-8").read()
    i95, i96 = src.find('f["ioe"] = 1'), src.find('f["ioe"] = 2')
    ok = ok and 0 < i95 < i96 and "arsiv_io = arsiv_oran()" in src and 'f["io"] = mk["ms"]' in src
    return bool(ok)


def main():
    son, sonio = goruntuler(); A = M95.arsiv()
    hedef = [k for k in son if not son[k][0].get("io") and k not in sonio]   # B1 (YH-95) sonrası hâlâ oransız
    kaz = {}
    for k in hedef:
        f, ct, h = son[k]
        o = arsiv_o_an(h, ct).get(k)
        if o: kaz[k] = o
    bitti, tutarli, ll_b, fav = 0, 0, [], []
    for k, o in kaz.items():
        r = A.get(k)
        if not r or not r.get("ms"): continue
        tutarli_mi = [round(float(v), 2) for v in r["ms"]] == [round(float(v), 2) for v in o["io"]]
        y = M95.sonuc(r)
        if y is None: continue
        bitti += 1; tutarli += tutarli_mi
        p = M95.power(o["io"]); ll_b.append(-np.log(max(p[y], 1e-9))); fav.append(int(np.argmax(p) == y))
    kay95 = {k for k in son if not son[k][0].get("io") and k in sonio}
    ll_t = []
    for k, r in A.items():
        if k in kaz or k in kay95 or not r.get("ms"): continue
        y = M95.sonuc(r)
        if y is None: continue
        try: ms = [float(v) for v in r["ms"]]
        except Exception: continue
        if len(ms) != 3 or not (M95.BANT[0] <= min(ms) <= M95.BANT[1]) or (k in son and not son[k][0].get("io")): continue
        p = M95.power(ms); ll_t.append(-np.log(max(p[y], 1e-9)))
    ust = M95.boot_ust(ll_t) if ll_t else None
    k1 = len(kaz) >= 3
    k2 = bitti > 0 and tutarli == bitti
    k3 = (bool(ll_b) and ust is not None and float(np.mean(ll_b)) <= ust) if bitti >= 3 else None
    k4 = birim()
    out = {"tarih": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "madde": "YH-96", "veri_bas": M95.SINCE,
           "mac": len(son), "b1_sonrasi_oransiz": len(hedef), "kazanim": len(kaz),
           "kazanim_i_lig": sum(1 for k in kaz if str(son[k][0].get("lg", "")).startswith("i")),
           "sonuclanan": bitti, "kilitli_tutarli": tutarli,
           "ll_tasinan": round(float(np.mean(ll_b)), 4) if ll_b else None, "isabet_tasinan": round(float(np.mean(fav)), 4) if fav else None,
           "ll_taze_bant": round(float(np.mean(ll_t)), 4) if ll_t else None, "ll_taze_bant_ga_ust": round(ust, 4) if ust else None,
           "n_taze_bant": len(ll_t),
           "kapi": {"1_kazanim": k1, "2_tutarlilik": k2, "3_kalite": k3, "4_birim": k4},
           "gecti": bool(k1 and k2 and k4 and k3 is not False)}
    json.dump(out, open(os.path.join(DATA, "ms_arsiv_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
