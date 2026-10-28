"""OXXai · Canlı altın eşiği laboratuvarı — veriye dayalı eşik seçimi + 48 saatlik canlı kapı (ağ kullanmaz; yalnız numpy).

  python3 lab/canli_altin_lab.py olc [--uygula]   eşik adaylarını zaman sıralı ölç; --uygula: data/canli_altin.json'a "deneme" yaz
  python3 lab/canli_altin_lab.py kapi             48 saat dolduysa deneme dönemindeki gerçek altın seçimleriyle karar ver
  python3 lab/canli_altin_lab.py gunluk           update.yml adımı: kapı + günde bir ölçüm (seçilen eşik değiştiyse yeni 48 sa deneme)

ÖLÇÜM (olc): kayıtlı canlı seçimler (data/archive/live/*.json, sonuçlu) gün gün; her sınama günü D için canlı güç modeli (CG,
lab/canli_guc_lab.py) yalnız D başlamadan sonucu kesin maçlarla öğrenilir ve seçimin olasılığı bu modelle yeniden hesaplanır
(uygulamanın gösterdiği canlı olasılık; CG kalibrasyonu kal=null → olduğu gibi). Yalnız dakika < dkmax ve oran ≥ 1,05.
  • tekli aday eşikleri 0,80 / 0,85 / 0,90 / 0,95: maç başına eşiği ilk aştığı an (uygulamada ilk göründüğü an) bir seçim;
  • kombine aday eşikleri 0,75 / 0,80 / 0,85 / 0,90: her kayıt turunda (aynı ts) uygulamanın kombinasyon kuralı (scripts/canli_altin.py),
    aynı kombinasyon tekrar sayılmaz; tutma = tüm ayaklar tuttu.
  Her aday: seçim sayısı / gün, gerçek isabet, Wilson %95 alt sınırı, kalibrasyon farkı (gerçek − ortalama tahmin).
  SEÇİM KURALI: Wilson alt sınırı ≥ eşik − 0,05 VE günde ≥ 3 seçim olan EN DÜŞÜK eşik; hiçbiri sağlamazsa mevcut değer kalır.
KAPI (kapi): deneme bitişinden (başlangıç + 48 sa) ≥ 3 sa sonra (son maçlar puanlansın) — deneme dönemindeki gerçek altın
seçimleri (toplayıcı canlı kayıtta "g": 1 ve "ga" ile işaretler, "gok" ile puanlar). Tekli: (maç, seçim) başına ilk görünüş;
kombine: benzersiz kombinasyon. n < 10 → "yetersiz"; bir türde n ≥ 10 ve Wilson alt sınırı < eşik − 0,05 → "başarısız";
ikisi de n < 10 ama toplam ≥ 10 ise birleşik isabet min(eşik) − 0,05 ile sınanır. Başarısız/yetersiz → eşikler önceki değerlere
döner (durum "geri_alindi"); başarılı → durum "kalici". Karar data/gelisim.json'a olay olarak yazılır.
"""
import glob, json, math, os, sys, collections
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import canli_altin as CA
DATA = os.path.join(ROOT, "data"); FLAG = os.path.join(DATA, "canli_altin.json"); GEL = os.path.join(DATA, "gelisim.json")
TEKLI = (0.80, 0.85, 0.90, 0.95); KOMBINE = (0.75, 0.80, 0.85, 0.90)
PAY, GUNDE, KAPI_N, DENEME_SA, BEKLE_SA, BEKLEME_GUN = 0.05, 3.0, 10, 48, 3, 7
KAPI_KURAL = (f"deneme bitişinden ≥ {BEKLE_SA} sa sonra: deneme dönemindeki altın seçimleri (tekli ilk görünüş, kombine benzersiz) — "
              f"toplam n < {KAPI_N} → yetersiz; n ≥ {KAPI_N} olan türde Wilson %95 alt sınırı < eşik − {PAY} → başarısız; ikisinde de geri alınır")


def wilson(h, n, z=1.96):
    if n == 0: return None
    p = h / n; d = 1 + z * z / n; c = p + z * z / (2 * n); r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((c - r) / d, 4)


def olc():
    import numpy as np
    import canli_guc_lab as L, canli_guc as CG
    try: h1 = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"].get("h1", .4428)
    except Exception: h1 = .4428
    F = CA.ayar(DATA); dkmax = F["dkmax"]
    fin, snaps = L.load(); days = sorted({r["d"] for r in snaps}); R = []; gunler = []
    for D in days[1:]:
        t0 = L.day_start(D); tr = {k for k, M in fin.items() if M["ts"] + 2.5 * 3600 < t0}
        if len({r["id"] for r in snaps if r["id"] in tr}) < 30: continue
        P, _ = L.fit(L.rows_of(snaps, fin, tr, extra=True), dict(CG.DEF, h1=h1))
        n0 = len(R)
        for r in snaps:
            if r["d"] != D or r.get("ok") is None or r["t"] >= dkmax or not (r.get("o") and r["o"] >= 1.05): continue
            p = L.cg_pick_p(r, P)
            if p is None: continue
            R.append({"d": D, "id": r["id"], "k": r["rk"], "p": min(.99, p), "o": r["o"], "dk": r["t"], "ts": r.get("ts") or 0, "ok": bool(r["ok"])})
        if len(R) > n0: gunler.append(D)
    G = max(1, len(gunler)); out = {"gunler": gunler, "secim_kayit": len(R), "tekli": [], "kombine": []}
    for th in TEKLI:
        first = {}
        for x in sorted(R, key=lambda x: (x["ts"], x["dk"])):
            if x["p"] >= th and x["id"] not in first: first[x["id"]] = x
        v = list(first.values()); n = len(v); h = sum(x["ok"] for x in v)
        out["tekli"].append({"esik": th, "n": n, "gunde": round(n / G, 2), "gercek": round(h / n, 4) if n else None, "wilson_alt": wilson(h, n),
                             "ort_p": round(sum(x["p"] for x in v) / n, 4) if n else None, "kal_fark": round(h / n - sum(x["p"] for x in v) / n, 4) if n else None})
    by_ts = collections.defaultdict(list)
    for x in R: by_ts[(x["d"], x["ts"])].append(x)
    for th in KOMBINE:
        Fk = dict(F, kombine=th, tekli=2.0); seen = {}
        for key in sorted(by_ts):
            c = [x for x in by_ts[key] if x["p"] >= F["aday"]]
            K = CA.sec(c, Fk)
            if not K or K["tur"] != "kombine": continue
            sig = tuple(sorted((x["id"], x["k"]) for x in K["sel"]))
            if sig in seen: continue
            seen[sig] = {"p": K["p"], "ok": all(x["ok"] for x in K["sel"]), "n": len(K["sel"])}
        v = list(seen.values()); n = len(v); h = sum(x["ok"] for x in v)
        out["kombine"].append({"esik": th, "n": n, "gunde": round(n / G, 2), "gercek": round(h / n, 4) if n else None, "wilson_alt": wilson(h, n),
                               "ort_p": round(sum(x["p"] for x in v) / n, 4) if n else None, "kal_fark": round(h / n - sum(x["p"] for x in v) / n, 4) if n else None,
                               "ort_ayak": round(sum(x["n"] for x in v) / n, 2) if n else None})
    def pick(rows):
        for r in rows:
            if r["n"] and r["wilson_alt"] is not None and r["wilson_alt"] >= r["esik"] - PAY and r["gunde"] >= GUNDE: return r["esik"]
        return None
    out["secilen"] = {"tekli": pick(out["tekli"]), "kombine": pick(out["kombine"])}
    out["kural"] = f"Wilson %95 alt sınırı ≥ eşik − {PAY} ve günde ≥ {GUNDE:g} seçim olan en düşük eşik; yoksa mevcut değer"
    out["yontem"] = "zaman sıralı: her gün CG yalnız o gün başlamadan sonucu kesin maçlarla öğrenilir; kayıtlı canlı seçimler bu olasılıkla yeniden puanlanır; dakika < dkmax, oran ≥ 1,05"
    return out


def yaz_gelisim(tur, baslik, detay, anahtar):
    try:
        sys.path.insert(0, os.path.join(ROOT, "lab")); from guardian import gelisim_ekle
        G = json.load(open(GEL, encoding="utf-8"))
        if gelisim_ekle(G, tur, baslik, detay, anahtar, datetime.now(timezone.utc).date().isoformat()):
            json.dump(G, open(GEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception as ex:
        print("gelişim olayı yazılamadı:", ex.__class__.__name__, ex)


def uygula(O):
    """Ölçümü bayrağa yaz; seçilen eşik mevcut değerden farklıysa 48 saatlik deneme başlat. Süren deneme bozulmaz; geri alınan
    denemeden sonra BEKLEME_GUN gün yeni deneme açılmaz (aynı veride aynı eşiği tekrar tekrar denememek için)."""
    now = datetime.now(timezone.utc)
    try: eski = json.load(open(FLAG, encoding="utf-8"))
    except Exception: eski = {}
    eski["olcum"] = O; eski["olcum_zaman"] = now.strftime("%Y-%m-%dT%H:%MZ")
    if eski.get("durum") == "deneme":
        json.dump(eski, open(FLAG, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print("Süren deneme var; yalnız ölçüm güncellendi."); return eski
    cur = CA.ayar(DATA)
    t = O["secilen"]["tekli"] or cur["tekli"]; k = O["secilen"]["kombine"] or cur["kombine"]
    bekle = False
    try:
        if eski.get("durum") == "geri_alindi":
            z = datetime.fromisoformat(((eski.get("kapi") or {}).get("zaman") or "2000-01-01T00:00Z").replace("Z", "+00:00"))
            bekle = now - z < timedelta(days=BEKLEME_GUN)
    except Exception: pass
    if (t, k) == (cur["tekli"], cur["kombine"]) or bekle:
        F = dict(eski, v=1, tekli=cur["tekli"], kombine=cur["kombine"], aday=cur["aday"], dkmax=cur["dkmax"])
        F.setdefault("durum", "mevcut")
        F["not"] = ("geri almadan sonra bekleme süresi" if bekle else "seçim kuralını sağlayan yeni eşik yok; mevcut değerler korunur")
        json.dump(F, open(FLAG, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print("Deneme açılmadı:", F["not"]); return F
    F = {"v": 1, "tekli": t, "kombine": k, "aday": cur["aday"], "dkmax": cur["dkmax"],
         "baslangic": now.strftime("%Y-%m-%dT%H:%MZ"), "bitis": (now + timedelta(hours=DENEME_SA)).strftime("%Y-%m-%dT%H:%MZ"),
         "durum": "deneme", "onceki": {"tekli": cur["tekli"], "kombine": cur["kombine"]}, "olcum": O, "olcum_zaman": eski["olcum_zaman"],
         "kapi": {"kural": KAPI_KURAL, "karar": None}}
    json.dump(F, open(FLAG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    yaz_gelisim("gelisme", "Canlı altın eşiği denemede",
                f"Kayıtlı canlı seçimlerden seçilen eşik 48 saat canlı denenecek: tekli %{round(t * 100)}+, kombine %{round(k * 100)}+ "
                f"(önceki %{round(cur['tekli'] * 100)}+ / %{round(cur['kombine'] * 100)}+). Gerçek isabet tutmazsa kendiliğinden geri alınır.",
                f"canli-altin-{F['baslangic'][:10]}-deneme")
    print("yazıldı:", FLAG, {k_: F[k_] for k_ in ("tekli", "kombine", "durum", "bitis")})
    return F


def gunluk():
    """update.yml adımı: önce kapı (deneme bittiyse karar), sonra günde bir ölçüm (+ gerekiyorsa yeni deneme)."""
    kapi()
    try: F = json.load(open(FLAG, encoding="utf-8"))
    except Exception: F = {}
    try: son = datetime.fromisoformat((F.get("olcum_zaman") or "2000-01-01T00:00Z").replace("Z", "+00:00"))
    except Exception: son = datetime(2000, 1, 1, tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - son < timedelta(hours=20): print("Ölçüm bugün yapıldı."); return
    uygula(olc())


def deneme_secimleri(F):
    t0 = datetime.fromisoformat(F["baslangic"].replace("Z", "+00:00")).timestamp(); t1 = datetime.fromisoformat(F["bitis"].replace("Z", "+00:00")).timestamp()
    tek = {}; kom = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(DATA, "archive", "live", "*.json"))):
        try: log = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        for r in log.values():
            if r.get("g") != 1 or not isinstance(r.get("ga"), dict) or not (t0 <= (r.get("ts") or 0) < t1): continue
            a = r["ga"]
            if a.get("tur") == "tekli":
                key = (str(r["id"]), a.get("k"))
                if key not in tek or r["ts"] < tek[key]["ts"]: tek[key] = {"ts": r["ts"], "ok": r.get("gok"), "p": a.get("p")}
            else: kom[r["ts"]].append((str(r["id"]), a.get("k"), r.get("gok")))
    T = [x for x in tek.values() if x["ok"] is not None]
    K = {}
    for ts, legs in sorted(kom.items()):
        sig = tuple(sorted((i, k) for i, k, _ in legs))
        if sig in K: continue
        oks = [o for _, _, o in legs]
        if any(o is False for o in oks): K[sig] = False
        elif all(o is True for o in oks): K[sig] = True
    return T, list(K.values())


def kapi():
    try: F = json.load(open(FLAG, encoding="utf-8"))
    except Exception: print("Bayrak yok; kapı atlandı."); return
    if F.get("durum") != "deneme": print("Deneme yok (durum:", F.get("durum"), ")"); return
    now = datetime.now(timezone.utc); bit = datetime.fromisoformat(F["bitis"].replace("Z", "+00:00"))
    if now < bit + timedelta(hours=BEKLE_SA): print(f"Deneme sürüyor; karar {bit + timedelta(hours=BEKLE_SA):%Y-%m-%d %H:%M} UTC sonrası."); return
    T, K = deneme_secimleri(F)
    nt, ht = len(T), sum(1 for x in T if x["ok"]); nk, hk = len(K), sum(1 for x in K if x)
    olc_ = {"tekli": {"esik": F["tekli"], "n": nt, "tuttu": ht, "gercek": round(ht / nt, 4) if nt else None, "wilson_alt": wilson(ht, nt)},
            "kombine": {"esik": F["kombine"], "n": nk, "tuttu": hk, "gercek": round(hk / nk, 4) if nk else None, "wilson_alt": wilson(hk, nk)}}
    if nt + nk < KAPI_N: sonuc = "yetersiz"
    else:
        bad = any(o["n"] >= KAPI_N and o["wilson_alt"] < o["esik"] - PAY for o in olc_.values())
        if not bad and nt < KAPI_N and nk < KAPI_N:
            bad = wilson(ht + hk, nt + nk) < min(F["tekli"], F["kombine"]) - PAY
        sonuc = "basarisiz" if bad else "basarili"
    F["kapi"] = dict(F.get("kapi") or {}, karar=sonuc, zaman=now.strftime("%Y-%m-%dT%H:%MZ"), deneme=olc_)
    tx = lambda o: f"{o['tuttu']}/{o['n']}" + (f" (%{round(o['gercek'] * 100)})" if o["n"] else "")
    if sonuc == "basarili":
        F["durum"] = "kalici"
        yaz_gelisim("gelisme", "Canlı altın eşiği kalıcı oldu",
                    f"48 saatlik canlı denemede altın seçimler eşiği tuttu: tekli %{round(F['tekli'] * 100)}+ {tx(olc_['tekli'])}, "
                    f"kombine %{round(F['kombine'] * 100)}+ {tx(olc_['kombine'])}. Yeni eşikler kalıcı.", f"canli-altin-{F['baslangic'][:10]}-kalici")
    else:
        dene = {"tekli": F["tekli"], "kombine": F["kombine"]}
        F.update(F.get("onceki") or {"tekli": CA.VARSAYILAN["tekli"], "kombine": CA.VARSAYILAN["kombine"]}); F["durum"] = "geri_alindi"; F["denenen"] = dene
        neden = "yeterli seçim çıkmadı" if sonuc == "yetersiz" else "gerçek isabet eşiğin altında kaldı"
        yaz_gelisim("duzeltme", "Canlı altın eşiği geri alındı",
                    f"48 saatlik canlı denemede {neden} (tekli {tx(olc_['tekli'])}, kombine {tx(olc_['kombine'])}). "
                    f"Eşikler önceki değerlere döndü: tekli %{round(F['tekli'] * 100)}+, kombine %{round(F['kombine'] * 100)}+.", f"canli-altin-{F['baslangic'][:10]}-geri")
    json.dump(F, open(FLAG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", sonuc, json.dumps(olc_, ensure_ascii=False))


if __name__ == "__main__":
    a = sys.argv[1:] or ["olc"]
    if a[0] == "olc":
        O = olc(); print(json.dumps(O, ensure_ascii=False, indent=1))
        if "--uygula" in a: uygula(O)
    elif a[0] == "kapi": kapi()
    elif a[0] == "gunluk": gunluk()
