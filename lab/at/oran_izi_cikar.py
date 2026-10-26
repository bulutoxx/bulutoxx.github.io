# OXXai at lab — v6: aynanın git geçmişinden oran izi çıkarıcı (yalnız türetilmiş özet yazar; depoya girmez).
# Kullanım: git clone --filter=blob:none --no-checkout https://github.com/cenkozgur/tjk-data T; git -C T log --format='C %H %ct' --raw --no-abbrev -- data/daily/ > raw.txt
#   (eksik blob'lar: awk ile oid listesi → git fetch origin <oid...>); python lab/at/oran_izi_cikar.py T raw.txt iz.json
# Aynanın git geçmişinden (data/daily sürümleri) at başına oran izi çıkarır. Yalnız türetilmiş özet yazar.
import json, subprocess, sys, collections
REPO, RAW, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
surum = []   # (ct, oid, tarih)
ct = None
for ln in open(RAW):
    if ln.startswith("C "):
        ct = int(ln.split()[2])
    elif "data/daily/" in ln:
        p = ln.split()
        surum.append((ct, p[3], p[-1].split("/")[-1][:10]))
surum.sort()
iz = collections.defaultdict(dict)   # (tarih, hip, kosu) -> {"saat":..., "tc": [(ct,tc)], "o": {ad: [(ct, oran)]}}
proc = subprocess.Popen(["git", "-C", REPO, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
for i, (ct, oid, tarih) in enumerate(surum):
    proc.stdin.write((oid + "\n").encode()); proc.stdin.flush()
    hdr = proc.stdout.readline().split()
    n = int(hdr[2]); data = proc.stdout.read(n); proc.stdout.read(1)
    try:
        js = json.loads(data)
    except Exception:
        continue
    for r in js:
        k = (r.get("date") or tarih, r.get("venue"), int(r.get("raceNo") or 0))
        d = iz[k]
        d["saat"] = r.get("time")
        cap = (r.get("snapshotRef") or {}).get("capturedAt")
        tc = r.get("trackCondition")
        if tc and (not d.get("tc") or d["tc"][-1][1] != tc):
            d.setdefault("tc", []).append((ct, tc))
        oo = {h.get("name"): h.get("odds") for h in r.get("horses") or [] if h.get("odds")}
        if oo:
            o = d.setdefault("o", {})
            sig = json.dumps(sorted(oo.items()), ensure_ascii=False)
            if d.get("_sig") != sig:
                d["_sig"] = sig
                d.setdefault("t", []).append([ct, cap])
                for a, v in oo.items():
                    o.setdefault(a, []).append([ct, v])
    if i % 500 == 0:
        print(i, len(surum), flush=True)
for d in iz.values():
    d.pop("_sig", None)
json.dump({"|".join(map(str, k)): v for k, v in iz.items()}, open(OUT, "w"), ensure_ascii=False)
print("bitti", len(iz))
