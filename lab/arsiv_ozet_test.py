#!/usr/bin/env python3
"""YH-66 kapı testi: karne arşiv özetinde olasılık tabanı (0,70) dört okuyucunun sonucunu değiştirmez.

Okuyucular (JS anlamıyla birebir yeniden yazıldı):
  core goldKarne  : ok!=null, rp!=null, ro doğru;  rp>=.78 (ayrıca .82 sınanır), omin<=ro<=omax → n, h(ok)
  core tpKarne    : aynı alanlar, rp>=.70 → n, h
  ekran tpKarne   : core tpKarne + g (eşleşen kaydı olan gün sayısı)
  arayuz goldKarne: sk doğru, sp!=null, sok!=null; oran sk'den (ms / ou); +sp>=.78, omin<=o<=omax → n, h(sok)
Veri: depodaki arşiv günleri + her günün git geçmişinden en çok 4 anlık görüntü; kayan 30 günlük pencereler.
Kullanım: python3 lab/arsiv_ozet_test.py   (çıkış 0 = kapı (1) geçti)
"""
import json, math, os, subprocess, sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "lab"))
import yayin_listesi as YL  # noqa: E402

OMIN, OMAX = 1.15, 2.00


def num(x):
    if x is None:
        return 0.0 if x is not None else float("nan")
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if s == "":
            return 0.0
        try:
            return float(s)
        except ValueError:
            return float("nan")
    return float("nan")


def ge(a, b):          # JS a>=b (null → 0, undefined → NaN; özette ikisi de "alan yok"/None olarak gelir)
    x = num(a) if a is not None else 0.0
    return not math.isnan(x) and x >= b


def le(a, b):
    x = num(a) if a is not None else 0.0
    return not math.isnan(x) and x <= b


def truthy(x):
    if x is None or x is False:
        return False
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return x != 0 and not math.isnan(x)
    if isinstance(x, str):
        return x != ""
    return True       # dizi / nesne JS'te her zaman doğru


def a_ok(v):
    return v.get("ok") is not None and v.get("rp") is not None and truthy(v.get("ro"))


def gold_core(A, thr=.78):
    n = h = 0
    for v in A.values():
        if not a_ok(v):
            continue
        if ge(v["rp"], thr) and ge(v["ro"], OMIN) and le(v["ro"], OMAX):
            n += 1
            h += truthy(v.get("ok"))
    return n, h


def tp_ekran(A):
    n = h = 0
    had = 0
    for v in A.values():
        if not a_ok(v):
            continue
        if ge(v["rp"], .70) and ge(v["ro"], OMIN) and le(v["ro"], OMAX):
            n += 1; had = 1
            h += truthy(v.get("ok"))
    return n, h, had


def odd(v, k):
    if k in ("1", "X", "2"):
        i = "1X2".index(k)
        m = v.get("ms")
        return num(m[i]) if isinstance(m, list) and i < len(m) else (float("nan") if isinstance(m, list) else None)
    if k in ("U", "A"):
        o = v.get("ou")
        i = 0 if k == "U" else 1
        return num(o[i]) if isinstance(o, list) and i < len(o) else (float("nan") if isinstance(o, list) else None)
    return None


def gold_sunulan(A):
    n = h = 0
    for v in A.values():
        if not v or not truthy(v.get("sk")) or v.get("sp") is None or v.get("sok") is None:
            continue
        sk = v["sk"]
        k = sk if isinstance(sk, str) else (str(int(sk)) if isinstance(sk, (int, float)) and float(sk).is_integer() else str(sk))
        o = odd(v, k)
        if ge(v["sp"], .78) and o is not None and truthy(o) and o >= OMIN and o <= OMAX:
            n += 1
            h += truthy(v.get("sok"))
    return n, h


def ozet(gunler, taban):
    G = {}
    for d, A in gunler.items():
        if not isinstance(A, dict):
            continue
        R = {}
        for k, v in A.items():
            if isinstance(v, dict):
                s = YL.arsiv_kayit_sec(v, taban)
                if s is not None:
                    R[k] = s
        G[d] = R
    return G


def pencereler(G):
    gun = sorted(G)
    out = []
    for i in range(len(gun)):
        W = gun[max(0, i - 29):i + 1]
        r = {"gold78": [0, 0], "gold82": [0, 0], "tp": [0, 0, 0], "sun": [0, 0]}
        for d in W:
            A = G[d]
            for key, f in (("gold78", lambda A: gold_core(A, .78)), ("gold82", lambda A: gold_core(A, .82)),
                           ("tp", tp_ekran), ("sun", gold_sunulan)):
                x = f(A)
                for j, y in enumerate(x):
                    r[key][j] += y
        out.append((gun[i], r))
    return out


def anlik(yol, en_cok=4):
    try:
        c = subprocess.run(["git", "-C", KOK, "log", "--format=%H", "--", yol], capture_output=True, text=True, timeout=60).stdout.split()
    except Exception:
        c = []
    if len(c) > en_cok:
        adim = (len(c) - 1) / (en_cok - 1)
        c = [c[round(i * adim)] for i in range(en_cok)]
    S = []
    for h in c:
        try:
            S.append(json.loads(subprocess.run(["git", "-C", KOK, "show", f"{h}:{yol}"], capture_output=True, text=True, timeout=60).stdout))
        except Exception:
            pass
    return S


def main():
    ad = sorted(f for f in os.listdir(os.path.join(KOK, "data/archive")) if f.endswith(".json") and len(f) == 15)
    guncel = {f[:-5]: json.load(open(os.path.join(KOK, "data/archive", f), encoding="utf-8")) for f in ad}
    gecmis = {d: anlik(f"data/archive/{d}.json") for d in guncel}
    dunyalar = [guncel] + [{d: (S[i] if i < len(S) else guncel[d]) for d, S in gecmis.items()} for i in range(4)]
    karsilastirma = fark = negatif = kayit_eski = kayit_yeni = 0
    for D in dunyalar:
        E = ozet(D, None); Y = ozet(D, YL.ARSIV_OZET_TABAN); N = ozet(D, 0.80)
        kayit_eski += sum(len(x) for x in E.values()); kayit_yeni += sum(len(x) for x in Y.values())
        PE, PY, PN = pencereler(E), pencereler(Y), pencereler(N)
        for (d, a), (_, b), (_, c) in zip(PE, PY, PN):
            for k in a:
                karsilastirma += 1
                fark += a[k] != b[k]
                negatif += a[k] != c[k]
    toplam_n = sum(r["tp"][0] + r["sun"][0] for _, r in pencereler(ozet(guncel, None)))
    sonuc = {"gun": len(guncel), "anlik_goruntu": sum(len(s) for s in gecmis.values()), "dunya": len(dunyalar),
             "karsilastirma": karsilastirma, "fark": fark, "negatif_denetim_fark": negatif,
             "kayit_eski": kayit_eski, "kayit_yeni": kayit_yeni, "pencere_n_toplam": toplam_n}
    print(json.dumps(sonuc, ensure_ascii=False))
    ok = fark == 0 and negatif > 0 and toplam_n > 0
    print("KAPI (1):", "GEÇTİ" if ok else "KALDI")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
