#!/usr/bin/env python3
"""🌱 Taze veri kapısı: gölge kayıt (data/tazeveri.json) → zaman sıralı sınama → kapı (alfa yatırımı) → üretim → 14 gün izleme → geri alma.

Adaylar (scripts/tazeveri.py; her biri ayrı kapı, varsayılan kapalı): kadro_1x2, kadro_ou, hareket_1x2, hareket_ou, karisim_1x2, karisim_ou.
Ölçüm (önceden kayıtlı):
  • Satırlar başlama saatine göre sıralanır; parametre ilk 2/3'te ızgarayla seçilir (yalnız geçmiş), son 1/3'te sınanır.
  • ΔLL = LL(ayarlı) − LL(temel), lig×gün blok bootstrap'ı (lab/fb_guc_lab.blok_boot).
Kapı (hepsi gerekli): yeterli örnek (ESIK), sınama ΔLL %95 GA üst sınırı < 0, sınamanın iki yarısında ΔLL < 0, ΔBrier ≤ 0,
  tek yanlı p ≤ α_t (alfa yatırımı lab/oxx_ogren, alan "tazeveri-<yıl>"; mFDR ≤ 0,05). Kapı günde en çok bir kez karar verir.
  Alfa yalnız ön elemeyi (sınamada ΔLL < 0, iki yarı < 0, ΔBrier ≤ 0) geçen adaya harcanır; reddedilen aday 14 gün ve
  uygun satır sayısı son sınamanın 1,5 katına çıkana dek yeniden sınanmaz (ölçüm sürer).
Geçerse: parametre TÜM veride yeniden seçilir, durum "aktif" (motor fixtures.json'a uygular), 14 gün izleme:
  yayındaki maçlarda (gölge satırı s) ayarlı − temel; n ≥ 60 ve GA alt sınırı > 0 → hemen geri al; 14 gün dolunca ortalama ΔLL > 0 → geri al,
  değilse "kalici". Kalıcıda da her ölçümde sınama GA alt sınırı > 0 ise geri alınır. Geri alınan aday 14 gün dondurulur.
  Koruyucu geri alması (rollback.json) ya da oxx_rollback donmus["tazeveri"] varken hiçbir aday uygulanmaz (scripts/tazeveri.aktifler).

  python3 lab/tazeveri_kapi.py olc              # yalnız ölçüm (yazmaz)
  python3 lab/tazeveri_kapi.py karar [--kuru]   # ölç + karar + izle → data/tazeveri_ayar.json (sürekli deney karar işi)
  python3 lab/tazeveri_kapi.py gecmis           # bir kez: git geçmişindeki fixtures.json anlık görüntülerinden gölge kaydı tohumla
"""
import argparse, json, math, os, subprocess, sys
from datetime import date, datetime, timedelta, timezone

import numpy as np

LAB = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(LAB)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(ROOT, "scripts"))
import tazeveri as TZ  # noqa: E402

GELISIM = os.path.join(DATA, "gelisim.json")
IZLEME_GUN, BEKLEME_GUN, DONMA_GUN, MIN_IZ_N = 14, 14, 14, 60
# örnek eşiği: (toplam uygun puanlı satır, sinyali sıfırdan farklı satır)
ESIK = {"kadro": (300, 80), "hareket": (600, 300), "karisim": (600, 600)}
IZGARA = {"kadro": {"k": np.arange(0, 4.01, 0.25), "ke": np.arange(-0.03, 0.051, 0.01)},
          "hareket": {"b": np.arange(-1, 2.01, 0.1), "bo": np.arange(-1, 2.01, 0.1)},
          "karisim": {"w": np.arange(0, 0.61, 0.02), "wo": np.arange(0, 0.61, 0.02)}}
BASLIK = {"kadro": "Kadro / eksik oyuncu düzeltmesi", "hareket": "Oran hareketi (açılış → son oran)",
          "karisim": "Oranlı maçlarda piyasa + model karışımı"}


def bugun(): return (datetime.now(timezone.utc) + timedelta(hours=3)).date()


def temiz(s):
    import re
    s = re.sub(r"(?i)bahis", "tahmin", str(s or "")); s = re.sub(r"(?i)ganyan", "tahmin", s)
    s = re.sub(r"(?i)kupon", "KUPO", s); s = re.sub(r"(?i)bulut", "OXX", s); return re.sub(r"(?i)banko", "güçlü", s)


def _boot(delta, blok):
    import fb_guc_lab as FL
    return FL.blok_boot(np.asarray(delta, float), np.asarray(blok))


def _y(r): return 0 if r[0] > r[1] else 1 if r[0] == r[1] else 2


def _ll3(P, y): return -np.log(np.clip(P[np.arange(len(y)), y], 1e-9, 1))
def _br3(P, y): return ((P - np.eye(3)[y]) ** 2).sum(1)
def _ll2(p, y): p = np.clip(p, 1e-6, 1 - 1e-6); return -(y * np.log(p) + (1 - y) * np.log(1 - p))
def _br2(p, y): return (p - y) ** 2


# ------------------------------------------------------------------ ölçüm
def satirlar(G, sin, paz):
    """Uygun puanlı satırlar (başlama saatine göre sıralı)."""
    out = []
    for k, e in ((G or {}).get("mac") or {}).items():
        if not isinstance(e.get("r"), list) or not e.get("b"): continue
        if paz == "ou" and e.get("bo") is None: continue
        if sin == "kadro" and not e.get("kd"): continue
        if sin == "hareket" and not (e.get("o0") and e.get("o1")): continue
        if sin == "karisim" and not (e.get("o1") and e.get("pm")) or (sin == "karisim" and paz == "ou" and e.get("pmo") is None): continue
        out.append(dict(e, id=k))
    out.sort(key=lambda e: (e["bt"], e["id"]))
    return out


def _sinyal_var(e, sin, paz):
    if sin == "kadro": return bool(TZ.kadro_kayma(e["kd"], {"k": 1, "ke": 0.01}))
    if sin == "hareket": return (e["o0"] != e["o1"]) if paz == "1x2" else (e.get("u0") != e.get("u1"))
    return True


def _skor(rows, aday, prm):
    """(ll, brier) dizileri: ayarlı ve temel."""
    paz = aday.split("_")[1]
    if paz == "1x2":
        y = np.array([_y(e["r"]) for e in rows])
        P = np.array([TZ.ayarla(e, aday, prm) or e["b"] for e in rows], float); B = np.array([e["b"] for e in rows], float)
        P /= P.sum(1, keepdims=True); B /= B.sum(1, keepdims=True)
        return _ll3(P, y), _ll3(B, y), _br3(P, y), _br3(B, y)
    y = np.array([float(sum(e["r"]) > 2) for e in rows])
    P = np.array([(lambda v: e["bo"] if v is None else v)(TZ.ayarla(e, aday, prm)) for e in rows], float)
    B = np.array([e["bo"] for e in rows], float)
    return _ll2(P, y), _ll2(B, y), _br2(P, y), _br2(B, y)


def _sec(rows, aday):
    """Izgarada ortalama LL'yi en düşük yapan parametre (yalnız ilgili pazarın parametresi aranır)."""
    sin, paz = aday.split("_")
    tam = dict(TZ.VARSAYILAN[sin])
    adlar = {"kadro": ["k", "ke"], "hareket": ["b" if paz == "1x2" else "bo"], "karisim": ["w" if paz == "1x2" else "wo"]}[sin]
    best, bs = None, 9e9
    if len(adlar) == 2:
        kandid = [{adlar[0]: float(a), adlar[1]: float(b)} for a in IZGARA[sin][adlar[0]] for b in IZGARA[sin][adlar[1]]]
    else:
        kandid = [{adlar[0]: float(a)} for a in IZGARA[sin][adlar[0]]]
    for c in kandid:
        prm = dict(tam, **c)
        s = float(_skor(rows, aday, prm)[0].mean())
        if s < bs - 1e-12: best, bs = c, s
    return {k: round(v, 4) for k, v in best.items()}


def olc_aday(G, aday):
    sin, paz = aday.split("_")
    rows = satirlar(G, sin, paz)
    ns = sum(1 for e in rows if _sinyal_var(e, sin, paz))
    out = {"n": len(rows), "n_sinyal": ns, "esik": list(ESIK[sin])}
    if len(rows) < 30:
        out["durum"] = "veri_yetersiz"; return out
    cut = int(len(rows) * 2 / 3)
    tr, te = rows[:cut], rows[cut:]
    c = _sec(tr, aday)
    prm = dict(TZ.VARSAYILAN[sin], **c)
    la, lb, ba, bb = _skor(te, aday, prm)
    d = la - lb; h = len(d) // 2
    bl = [f"{e['lg']}|{e['d']}" for e in te]
    out.update({"secilen": c, "n_egitim": len(tr), "n_sinama": len(te),
                "sinama": {"ll_temel": round(float(lb.mean()), 5), "ll_ayarli": round(float(la.mean()), 5),
                           "brier_temel": round(float(bb.mean()), 5), "brier_ayarli": round(float(ba.mean()), 5),
                           "fark": _boot(d, bl), "yari1": round(float(d[:h].mean()), 5) if h else None,
                           "yari2": round(float(d[h:].mean()), 5) if h else None, "brier_fark": round(float((ba - bb).mean()), 5)},
                "tum_secilen": _sec(rows, aday),
                "donem": [rows[0]["d"], rows[-1]["d"]], "durum": "olculdu"})
    out["yeterli"] = bool(len(rows) >= ESIK[sin][0] and ns >= ESIK[sin][1])
    return out


def olc(G=None):
    G = G if G is not None else (TZ.jl(TZ.GOLGE, {}) or {})
    return {a: olc_aday(G, a) for a in TZ.ADAYLAR}


# ------------------------------------------------------------------ karar ve izleme
def _geri_al(A, ak, neden, Gel, guardian, gs):
    st = A["adaylar"][ak]
    st.update({"durum": "geri_alindi", "geri_alma": gs, "neden": neden}); st.pop("izleme_bitis", None)
    A["donmus"][ak] = (date.fromisoformat(gs) + timedelta(days=DONMA_GUN)).isoformat()
    A["gecmis"].append({"tarih": gs, "aday": ak, "karar": "geri_alindi", "neden": neden})
    if guardian:
        guardian.gelisim_ekle(Gel, "geri", temiz(f"Tahmin ayarı geri alındı: {BASLIK[ak.split('_')[0]]} ({'maç sonucu' if ak.endswith('1x2') else '2,5 alt/üst'})"),
                              temiz(neden + ". 14 gün yeniden denenmeyecek."), f"taze-geri-{ak}-{gs}", gs)
    print("GERİ ALINDI:", ak, neden)


def izle(A, G, Gel, guardian, gs):
    for ak, st in A.get("adaylar", {}).items():
        if st.get("durum") != "aktif": continue
        bas = st.get("baslangic_ts", 0)
        rows = [e for e in satirlar(G, *ak.split("_")) if e["bt"] >= bas and ak in (e.get("s") or [])]
        if not rows: st["izleme"] = {"n": 0}; continue
        la, lb, _, _ = _skor(rows, ak, TZ.parametre(A, ak.split("_")[0]))
        r = _boot(la - lb, [f"{e['lg']}|{e['d']}" for e in rows]); st["izleme"] = r
        if r["n"] >= MIN_IZ_N and r["ga95"][0] > 0:
            _geri_al(A, ak, f"yayında temel tahminden anlamlı kötü (ΔLL {r['fark']:+.4f}, GA {r['ga95']}, n={r['n']})", Gel, guardian, gs)
        elif gs >= st.get("izleme_bitis", "9999"):
            if r["fark"] > 0:
                _geri_al(A, ak, f"14 günlük izlemede temel tahminden kötü (ΔLL {r['fark']:+.4f}, n={r['n']})", Gel, guardian, gs)
            else:
                st["durum"] = "kalici"; st["kalici"] = gs
                A["gecmis"].append({"tarih": gs, "aday": ak, "karar": "kalici", "izleme": r})
                if guardian:
                    guardian.gelisim_ekle(Gel, "gelisme", temiz(f"Tahmin ayarı kalıcı: {BASLIK[ak.split('_')[0]]}"),
                                          temiz(f"14 günlük izlemede temel tahmine göre log-kayıp farkı {r['fark']:+.4f} ({r['n']} maç)."), f"taze-kalici-{ak}-{gs}", gs)


def karar_ver(A=None, G=None, kuru=False, guardian=None, O=None):
    gun = bugun(); gs = gun.isoformat()
    A = A if A is not None else (TZ.jl(TZ.AYAR, None) or {"v": 1})
    G = G if G is not None else (TZ.jl(TZ.GOLGE, {}) or {})
    for k in ("adaylar", "donmus", "prm"): A.setdefault(k, {})
    A.setdefault("gecmis", [])
    Gel = TZ.jl(GELISIM, {"olaylar": []}) or {"olaylar": []}
    if guardian is None:
        try: import guardian  # noqa
        except Exception: guardian = None
    if O is None:
        try: import oxx_ogren as O  # noqa
        except Exception: O = None
    K = olc(G); A["olcum"] = {"tarih": gs, **K}
    rb = TZ._geri_alma_aktif()
    gunluk = A.get("son_karar") != gs
    notlar = []
    for ak in TZ.ADAYLAR:
        sin = ak.split("_")[0]
        st = A["adaylar"].setdefault(ak, {"durum": "golge"})
        k = K[ak]
        if st.get("durum") in ("aktif", "kalici"):
            f = ((k.get("sinama") or {}).get("fark") or {})
            if f.get("n", 0) >= MIN_IZ_N and f.get("ga95", [0, 0])[0] > 0:
                _geri_al(A, ak, f"yeniden ölçümde anlamlı kötüleşme (ΔLL {f['fark']:+.4f}, GA {f['ga95']})", Gel, guardian, gs)
            continue
        if A["donmus"].get(ak, "") >= gs: st["durum"] = "donmus"; continue
        st["durum"] = "golge"
        if not k.get("yeterli"):
            st["not"] = f"veri birikiyor: {k['n']}/{ESIK[sin][0]} satır, {k['n_sinyal']}/{ESIK[sin][1]} sinyalli"; continue
        if not gunluk: continue
        if st.get("son_ret") and (gun - date.fromisoformat(st["son_ret"])).days < BEKLEME_GUN:
            st["not"] = "reddedildi; bekleme süresinde"; continue
        if rb: st["not"] = "koruyucu geri alma aktif; kapı denenmedi"; continue
        s = k["sinama"]; f = s["fark"]
        if st.get("son_test_n") and k["n"] < 1.5 * st["son_test_n"]:
            st["not"] = f"yeniden sınama için veri büyümesi bekleniyor ({k['n']}/{int(1.5 * st['son_test_n'])})"; continue
        if not (f["fark"] < 0 and (s["yari1"] or 0) < 0 and (s["yari2"] or 0) < 0 and s["brier_fark"] <= 0):
            st["not"] = "ön eleme: sınamada yön iyileşme göstermiyor (alfa harcanmadı)"; continue
        st["son_test_n"] = k["n"]
        alan = f"tazeveri-{gun.year}"
        alfa = O.yatirim_alfa(A, alan, {"anahtar": ak, "sinyal": {"kaynak": "ön kayıtlı taze veri adayı"}}) if O else 0.01
        istat = bool(f["p_tek"] <= alfa)
        gecti = bool(istat and f["ga95"][1] < 0 and (s["yari1"] or 0) < 0 and (s["yari2"] or 0) < 0 and s["brier_fark"] <= 0)
        if O: O.yatirim_guncelle(A, alan, alfa, istat)
        st["kapi"] = {"tarih": gs, "alfa": round(alfa, 5), "gecti": gecti, "fark": f["fark"], "ga95": f["ga95"], "p_tek": f["p_tek"], "n": f["n"]}
        A["gecmis"].append({"tarih": gs, "aday": ak, "karar": "kabul" if gecti else "ret", "fark": f["fark"], "ga95": f["ga95"], "n": f["n"]})
        if gecti:
            A["prm"].setdefault(sin, {}).update(k["tum_secilen"])
            st.update({"durum": "aktif", "baslangic": gs, "baslangic_ts": int(datetime.now(timezone.utc).timestamp()),
                       "izleme_bitis": (gun + timedelta(days=IZLEME_GUN)).isoformat(), "prm": k["tum_secilen"]})
            notlar.append(f"{ak}: kapı geçti → üretim")
            if guardian:
                guardian.gelisim_ekle(Gel, "gelisme", temiz(f"Yeni tahmin ayarı yayında: {BASLIK[sin]} ({'maç sonucu' if ak.endswith('1x2') else '2,5 alt/üst'})"),
                                      temiz(f"Zaman sıralı sınama ({f['n']} maç): log-kayıp farkı {f['fark']:+.4f} (%95 GA {f['ga95'][0]:+.4f}…{f['ga95'][1]:+.4f}). "
                                            "Ayarsız tahmin gölgede tutuluyor; 14 gün izlenecek, kötüleşirse kendiliğinden geri alınır."), f"taze-{ak}-{gs}", gs)
        else:
            st["son_ret"] = gs; notlar.append(f"{ak}: kapı geçilmedi")
    # gölge parametreleri: aktif olmayan sinyallerde son ölçümün tüm-veri seçimi (gölge tahminler bu parametrelerle yazılır)
    for sin in ("kadro", "hareket", "karisim"):
        if any(A["adaylar"].get(f"{sin}_{p}", {}).get("durum") in ("aktif", "kalici") for p in ("1x2", "ou")): continue
        for p in ("1x2", "ou"):
            k = K[f"{sin}_{p}"]
            if k.get("yeterli") and k.get("tum_secilen"): A["prm"].setdefault(sin, {}).update(k["tum_secilen"])
    izle(A, G, Gel, guardian, gs)
    if gunluk: A["son_karar"] = gs
    A["guncelleme"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    A["gecmis"] = A["gecmis"][-100:]
    A["aciklama"] = ("Taze veri adayları (lab/tazeveri_kapi.py): kadro, oran hareketi, piyasa+model karışımı; 1X2 ve 2,5 alt/üst ayrı. "
                     "durum aktif/kalici olan aday motorca fixtures.json kp/ko'ya uygulanır (tz alanı). Varsayılan kapalı.")
    if not kuru:
        TZ.jw(TZ.AYAR, A)
        if guardian: json.dump(Gel, open(GELISIM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("taze veri kararı:", "; ".join(notlar) or "değişiklik yok", "|", {k: v.get("durum") for k, v in A["adaylar"].items()})
    return A


# ------------------------------------------------------------------ git geçmişinden tohumlama (bir kez, yerel)
def _kickoff(f):
    from zoneinfo import ZoneInfo
    hh, mm = (f.get("t") or "23:59").split(":")[:2]
    return datetime.fromisoformat(f["d"]).replace(hour=int(hh), minute=int(mm), tzinfo=ZoneInfo("Europe/London")).timestamp()


def gecmis(ref="origin/main"):
    """fixtures.json'un git geçmişindeki her anlık görüntüsünü (commit zamanı = görülme zamanı) sırayla gölge kayda işler.
    Kadro alanı tohumlanmaz (kadro.json yalnız bugünden). Model yolu: kilitli predlog p (maçtan önce kilitlenmiş)."""
    log_ = subprocess.run(["git", "-C", ROOT, "log", "--reverse", "--format=%H %ct", ref, "--", "data/fixtures.json"],
                          capture_output=True, text=True, check=True).stdout.split("\n")
    G = TZ.jl(TZ.GOLGE, None) or {}
    plog = TZ.jl(os.path.join(DATA, "predlog.json"), []) or []
    model = {e["id"]: (e["p"], e.get("o")) for e in plog if e.get("p")}
    A = TZ.ayar()
    eski_k = TZ.KADRO; TZ.KADRO = os.path.join(DATA, "_yok_.json")
    n = 0
    try:
        for ln in log_:
            if not ln.strip(): continue
            h, ct = ln.split()
            try:
                fx = json.loads(subprocess.run(["git", "-C", ROOT, "show", f"{h}:data/fixtures.json"], capture_output=True, check=True).stdout)
            except Exception:
                continue
            now = datetime.fromtimestamp(int(ct), timezone.utc)
            TZ.golge_guncelle(fx, _kickoff, model=model, now=now, A=A, G=G, yaz=False); n += 1
            del fx
    finally:
        TZ.KADRO = eski_k
    S = TZ.jl(os.path.join(DATA, "season.json"), {}) or {}
    all_ms = {lg: d.get("matches", []) for lg, d in S.items()}
    del S
    nr = TZ.sonuc_isle(G, all_ms, yaz=False)
    TZ._yaz(G)
    print(f"tohumlama: {n} anlık görüntü, {len(G['mac'])} maç, {nr} sonuç; özet {G['ozet']}")
    return G


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("komut", choices=["olc", "karar", "gecmis"]); ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--kaynak")      # surekli-deney karar işiyle aynı imza (kullanılmaz)
    ar = ap.parse_args()
    if ar.komut == "olc":
        print(json.dumps(olc(), ensure_ascii=False, indent=1)); return 0
    if ar.komut == "gecmis":
        gecmis(); return 0
    try:
        karar_ver(kuru=ar.kuru)
    except Exception as e:
        import traceback; traceback.print_exc(); print("taze veri kapısı hata:", e.__class__.__name__); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
