#!/usr/bin/env python3
"""⚖️ Oransız model yolu kapısı: ölç → kapı (alfa yatırımı) → üretim → 14 gün kilitli gölge A/B izleme → otomatik geri alma.

Üretim adayları (önceden kayıtlı; her biri ayrı kapı):
  poisson_oransiz  Oransız liglerde Poisson decay/prior (yalnız gol hedefi). Üretimde: ratings.json (uygulamanın maç ekranı),
                   motorun pazar olasılıkları ve kilitli tahmin p'si bu ayarla. Ölçüt: uygulama yolu (gscale, iki yarı DC, calT/dk) 1X2 LL.
  topluluk_1x2     Poisson + Elo + pi yığını → fixtures.json kp (uygulamanın öneri yolu recOf bunu kullanır), kilitli p.
  topluluk_ou      Aynı yığının 2,5 üst olasılığı → fixtures.json ko. Ölçüt: A/Ü LL.
Gölge (yalnız ölçülür, üretime girmez): C1k, C2 Elo, C3 pi, C5, C6 (laboratuvar karnesinde her çalışmada yeniden ölçülür).

Kapı (hepsi gerekli; lab/fb_guc_lab.py, zaman sıralı ileri yürüyüş, son 180 gün sınama):
  ΔLL (aday − üretim) %95 GA üst sınırı < 0 (lig×gün blok bootstrap'ı), sınamanın iki yarısında ΔLL < 0, ΔBrier ≤ 0,
  tek yanlı bootstrap p ≤ α_t — alfa yatırımı (lab/oxx_ogren.yatirim_alfa / yatirim_guncelle; alan "fb_model-<yıl>", mFDR ≤ 0,05).
  Reddedilen aday 14 gün yeniden sınanmaz (yalnız ölçülür).
İzleme (uygulamadan sonra 14 gün; data/predlog.json kilitli kayıtlar):
  Kilitli tahminde eski üretim yolu da gölge olarak tutulur (g0/g0o; poisson için gp). Eşleştirilmiş ΔLL, lig×gün blok bootstrap'ı.
  n ≥ 60 ve GA alt sınırı > 0 (anlamlı kötüleşme) → hemen geri al; 14 gün dolunca ortalama ΔLL > 0 → geri al, değilse kalıcı.
  Laboratuvar yeniden ölçümünde GA alt sınırı > 0 → geri al. Geri alınan aday 14 gün dondurulur (fb_guc.json donmus).
Kadro sinyali (scripts/kadro.py): kilitli kayıtlarda kd alanı birikince (≥300 puanlı, ≥80 kilit eksikli) aynı kapıdan sınanır.

  python3 lab/fb_guc_kapi.py dongu [--kuru]          # ölç + karar + izle (yerel / tek iş)
  python3 lab/fb_guc_kapi.py olc --cikti <dosya>     # yalnız ölçüm (surekli-deney matris işi)
  python3 lab/fb_guc_kapi.py karar --kaynak <dizin>  # son ölçüm dosyasıyla karar + izle (surekli-deney karar işi)
  python3 lab/fb_guc_kapi.py ileri                   # kilitli kayıtlarda (predlog) adayların ileriye dönük kıyası
"""
import argparse, collections, glob, json, math, os, sys, time
from datetime import date, datetime, timedelta, timezone

import numpy as np

LAB = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(LAB)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fb_guc_lab as FL  # noqa: E402
import guc as G  # noqa: E402

AYAR = G.AYAR
GELISIM = os.path.join(DATA, "gelisim.json")
IZLEME_GUN, BEKLEME_GUN, DONMA_GUN, MIN_IZ_N = 14, 14, 14, 60
SINAMA_GUN = 180
ADAY = {
    "poisson_oransiz": {"ad": "C1s Poisson yeniden ayarlı (uygulama yolu)", "ll": "ll", "br": "brier", "y1": "ll_yari1", "y2": "ll_yari2",
                        "baslik": "Oransız liglerde Poisson ayarı (yalnız gol hedefi)"},
    "topluluk_1x2": {"ad": "C4 Topluluk (Poisson+Elo+pi)", "ll": "ll", "br": "brier", "y1": "ll_yari1", "y2": "ll_yari2",
                     "baslik": "Oransız maçlarda topluluk tahmini (Poisson + Elo + pi-rating), maç sonucu"},
    "topluluk_ou": {"ad": "C4 Topluluk (Poisson+Elo+pi)", "ll": "ou_ll", "br": "ou_brier", "y1": "ou_ll_yari1", "y2": "ou_ll_yari2",
                    "baslik": "Oransız maçlarda topluluk tahmini, 2,5 alt/üst"},
}
GOLGE_ADLAR = ["C1k Poisson + yığın kalibrasyonu", "C2 Elo", "C3 pi-rating", "C5 Poisson+pi", "C6 Poisson+Elo", "R0 taban oranları (referans)"]


def bugun(): return (datetime.now(timezone.utc) + timedelta(hours=3)).date()
def jl(p, d=None):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d
def jw(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True); tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(o, f, ensure_ascii=False, indent=1, default=float)
    os.replace(tmp, p)


def temiz(s):
    import re
    s = re.sub(r"(?i)bahis", "tahmin", str(s or "")); s = re.sub(r"(?i)ganyan", "tahmin", s)
    s = re.sub(r"(?i)kupon", "KUPO", s); return re.sub(r"(?i)banko", "güçlü", s)


# ------------------------------------------------------------------ ölçüm
def olc():
    S = jl(os.path.join(DATA, "season.json"), {}) or {}
    son = max((m["d"] for d in S.values() if d.get("src") == "espn" for m in d.get("matches", []) if m.get("ft")), default=None)
    del S
    if not son: return None
    sinir = (date.fromisoformat(son) - timedelta(days=SINAMA_GUN)).isoformat()
    karne, x = FL.calistir("espn", sinir)
    karne["uretim_agirlik"] = {"W": np.asarray(x["W_tum"]).round(6).tolist(), "Wo": np.asarray(x["Wo_tum"]).round(6).tolist(),
                               "poisson": {"decay": x["k1"][0], "prior": x["k1"][1]},
                               "prm": {"elo": {"K": x["ke"][0], "eta": x["ke"][1]}, "pi": {"lam": x["kp"][0], "gam": x["kp"][1]}},
                               "ligler": karne["lig"], "son_tarih": x["son_tarih"]}
    karne["ileri_agirlik"] = {"W": np.asarray(x["W"]).round(6).tolist(), "Wo": np.asarray(x["Wo"]).round(6).tolist()}
    return karne


# ------------------------------------------------------------------ kapı ve karar
def _kapi(k, ak, alfa):
    a = ADAY[ak]; ll = k[a["ll"]]
    g = {"ga95_ust": ll["ga95"][1], "yari1": k[a["y1"]], "yari2": k[a["y2"]], "brier": k[a["br"]]["fark"], "p_tek": ll["p_tek"], "alfa": round(alfa, 5),
         "fark": ll["fark"], "ga95": ll["ga95"], "n": ll["n"]}
    g["gecti"] = bool(ll["ga95"][1] < 0 and k[a["y1"]] < 0 and k[a["y2"]] < 0 and k[a["br"]]["fark"] <= 0 and ll["p_tek"] <= alfa)
    g["istatistik_gecti"] = bool(ll["p_tek"] <= alfa)
    return g


def karar_ver(karne, A, kuru=False):
    import oxx_ogren as O
    import guardian
    gun = bugun(); gs = gun.isoformat(); yil = gun.year
    A = A or {"v": 1}
    A.setdefault("adaylar", {}); A.setdefault("gecmis", []); A.setdefault("donmus", {})
    Gel = jl(GELISIM, {"olaylar": []}) or {"olaylar": []}
    notlar = []
    rb = bool((jl(os.path.join(DATA, "rollback.json"), {}) or {}).get("aktif"))
    U = karne["uretim_agirlik"]
    for ak, a in ADAY.items():
        st = A["adaylar"].setdefault(ak, {"durum": "yeni"})
        k = karne["kiyas"].get(a["ad"])
        if not k: continue
        st["son_olcum"] = {"tarih": gs, "fark": k[a["ll"]]["fark"], "ga95": k[a["ll"]]["ga95"], "n": k[a["ll"]]["n"]}
        if st.get("durum") in ("aktif", "kalici"):
            if k[a["ll"]]["ga95"][0] > 0:          # laboratuvar yeniden ölçümünde anlamlı kötüleşme
                _geri_al(A, ak, f"laboratuvar yeniden ölçümü anlamlı kötüleşme gösterdi (ΔLL {k[a['ll']]['fark']:+.4f}, GA {k[a['ll']]['ga95']})", Gel, guardian, gs)
            continue
        if A["donmus"].get(ak, "") >= gs:
            st["durum"] = "donmus"; continue
        if st.get("son_ret") and (gun - date.fromisoformat(st["son_ret"])).days < BEKLEME_GUN:
            st["durum"] = "golge"; continue
        if rb:
            st["durum"] = "golge"; st["not"] = "koruyucu geri alma aktif; kapı denenmedi"; continue
        alan_k = f"fb_model-{yil}"
        c = {"anahtar": ak, "sinyal": {"kaynak": "ön kayıtlı laboratuvar adayı"}}
        alfa = O.yatirim_alfa(A, alan_k, c)
        g = _kapi(k, ak, alfa)
        O.yatirim_guncelle(A, alan_k, alfa, g["istatistik_gecti"])
        st["kapi"] = dict(g, tarih=gs)
        A["gecmis"].append({"tarih": gs, "aday": ak, "karar": "kabul" if g["gecti"] else "ret", **{x: g[x] for x in ("fark", "ga95", "p_tek", "alfa", "n")}})
        if g["gecti"]:
            st.update({"durum": "aktif", "baslangic": gs, "izleme_bitis": (gun + timedelta(days=IZLEME_GUN)).isoformat()})
            notlar.append(f"{ak}: kapı geçti → üretim (14 gün izleme)")
            guardian.gelisim_ekle(Gel, "gelisme", temiz(f"Yeni model ayarı yayında: {a['baslik']}"),
                                  temiz(f"Son {SINAMA_GUN} günde zaman sıralı sınama: log-kayıp farkı {g['fark']:+.4f} (%95 GA {g['ga95'][0]:+.4f}…{g['ga95'][1]:+.4f}, "
                                        f"{g['n']} maç). Eski yol kilitli tahminlerde gölge olarak tutuluyor; 14 gün izlenecek, kötüleşirse kendiliğinden geri alınır."),
                                  f"fbguc-{ak}-{gs}", gs)
        else:
            st.update({"durum": "golge", "son_ret": gs}); notlar.append(f"{ak}: kapı geçilmedi → gölge")
    # üretim ayarlarını yaz (yalnız aktif adayların ilgili alanı kullanılır)
    A["W"], A["Wo"], A["prm"], A["poisson"], A["ligler"] = U["W"], U["Wo"], U["prm"], U["poisson"], U["ligler"]
    A["kullan"] = ["pois", "elo", "pi"]
    po = A["adaylar"].get("poisson_oransiz", {})
    A["poisson_oransiz"] = {"aktif": po.get("durum") in ("aktif", "kalici"), "decay": U["poisson"]["decay"], "prior": U["poisson"]["prior"]}
    A["aktif"] = A["adaylar"].get("topluluk_1x2", {}).get("durum") in ("aktif", "kalici")
    A["ko_aktif"] = A["adaylar"].get("topluluk_ou", {}).get("durum") in ("aktif", "kalici")
    A["golge"] = {ad: karne["kiyas"][ad]["ll"] for ad in GOLGE_ADLAR if ad in karne["kiyas"]}
    A["lab_ozet"] = {"tarih": karne["tarih"], "sinir": karne["sinir"], "n_sinama": karne["n_sinama"], "secilen": karne["secilen"],
                     "modeller": karne["modeller"]}
    izle(A, Gel, guardian)
    A["guncelleme"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    A["gecmis"] = A["gecmis"][-100:]
    A["aciklama"] = ("Oransız maçların model yolu (lab/fb_guc_kapi.py). aktif: kp (1X2) yayında; ko_aktif: ko (2,5 üst) yayında; "
                     "poisson_oransiz.aktif: oransız liglerde Poisson decay/prior. Geri alma: ilgili durum 'geri_alindi' ve donmus tarihi.")
    if not kuru:
        jw(AYAR, A); json.dump(Gel, open(GELISIM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("karar:", "; ".join(notlar) or "değişiklik yok", "| durum:", {k: v.get("durum") for k, v in A["adaylar"].items()})
    return A


def _geri_al(A, ak, neden, Gel, guardian, gs):
    st = A["adaylar"][ak]
    st.update({"durum": "geri_alindi", "geri_alma": gs, "neden": neden}); st.pop("izleme_bitis", None)
    A["donmus"][ak] = (date.fromisoformat(gs) + timedelta(days=DONMA_GUN)).isoformat()
    A["gecmis"].append({"tarih": gs, "aday": ak, "karar": "geri_alindi", "neden": neden})
    guardian.gelisim_ekle(Gel, "geri", temiz(f"Model ayarı geri alındı: {ADAY[ak]['baslik']}"), temiz(neden + ". 14 gün yeniden denenmeyecek."),
                          f"fbguc-geri-{ak}-{gs}", gs)
    print("GERİ ALINDI:", ak, neden)


# ------------------------------------------------------------------ izleme (kilitli gölge A/B)
def _y(r): return 0 if r[0] > r[1] else 1 if r[0] == r[1] else 2


def izle_olc(plog, ak, bas):
    """Kilitli kayıtlarda aday (yayındaki) − eski üretim yolu farkı. Dönüş: blok bootstrap özeti ya da None."""
    rows = []
    for e in plog:
        if not isinstance(e.get("r"), list) or e.get("d", "") < bas or not e.get("g0"): continue
        y = _y(e["r"])
        if ak == "topluluk_1x2":
            if e.get("pk") != "guc": continue
            a, b = e["p"][y], e["g0"][y]
        elif ak == "poisson_oransiz":
            if e.get("pv") != 1: continue
            pp = e.get("gp") if e.get("pk") == "guc" else e["p"]
            a, b = pp[y], e["g0"][y]
        else:
            if e.get("ok_") != "guc" or e.get("g0o") is None: continue
            ov = (e["r"][0] + e["r"][1]) > 2
            a = e["o"] if ov else 1 - e["o"]; b = e["g0o"] if ov else 1 - e["g0o"]
        rows.append((f"{e['lg']}|{e['d']}", -math.log(max(a, 1e-9)) + math.log(max(b, 1e-9))))
    if not rows: return None
    return FL.blok_boot(np.array([r[1] for r in rows]), np.array([r[0] for r in rows]))


def izle_sayac(plog, bas):
    """İzleme penceresindeki kilitli gölge (g0) kayıtları: toplam ve sonuçlanmış."""
    g = [e for e in plog if e.get("g0") and e.get("d", "") >= bas]
    return {"kilitli": len(g), "sonuclu": sum(1 for e in g if isinstance(e.get("r"), list))}


def golge_ileri(plog):
    """Yayında olmayan topluluk adayının kilitli gölge kaydı (gk/gko) ile yayındaki p/o kıyası (yalnız ölçüm)."""
    r1, r2 = [], []
    for e in plog:
        if not isinstance(e.get("r"), list) or not e.get("gk"): continue
        y = _y(e["r"]); bl = f"{e['lg']}|{e['d']}"
        r1.append((bl, -math.log(max(e["gk"][y], 1e-9)) + math.log(max(e["p"][y], 1e-9))))
        if e.get("gko") is not None and e.get("o") is not None:
            ov = sum(e["r"]) > 2
            r2.append((bl, -math.log(max(e["gko"] if ov else 1 - e["gko"], 1e-9)) + math.log(max(e["o"] if ov else 1 - e["o"], 1e-9))))
    f = lambda R: FL.blok_boot(np.array([x[1] for x in R]), np.array([x[0] for x in R])) if R else None
    return {"topluluk_1x2": f(r1), "topluluk_ou": f(r2)}


def izle(A, Gel, guardian):
    plog = jl(os.path.join(DATA, "predlog.json"), []) or []
    gs = bugun().isoformat()
    try: A["golge_ileri"] = golge_ileri(plog)
    except Exception as e: A["golge_ileri"] = {"hata": repr(e)[:120]}
    for ak, st in A.get("adaylar", {}).items():
        if st.get("durum") != "aktif": continue
        r = izle_olc(plog, ak, st["baslangic"])
        if not r:
            # henüz sonuçlanmış kilitli gölge kaydı yok: ölçüm çalıştı ama örneklem boş (karar verilmez, durum görünür kalsın)
            st["izleme"] = {"n": 0, "durum": "sonuc_bekleniyor", "tarih": gs, "golge_kayit": izle_sayac(plog, st["baslangic"])}
            continue
        st["izleme"] = dict(r, durum="olculdu", tarih=gs)
        if r["n"] >= MIN_IZ_N and r["ga95"][0] > 0:
            _geri_al(A, ak, f"kilitli tahminlerde eski yoldan anlamlı kötü (ΔLL {r['fark']:+.4f}, GA {r['ga95']}, n={r['n']})", Gel, guardian, gs)
        elif gs >= st.get("izleme_bitis", "9999"):
            if r["fark"] > 0:
                _geri_al(A, ak, f"14 günlük izlemede eski yoldan kötü (ΔLL {r['fark']:+.4f}, n={r['n']})", Gel, guardian, gs)
            else:
                st["durum"] = "kalici"; st["kalici"] = gs
                A["gecmis"].append({"tarih": gs, "aday": ak, "karar": "kalici", "izleme": r})
                guardian.gelisim_ekle(Gel, "gelisme", temiz(f"Model ayarı kalıcı: {ADAY[ak]['baslik']}"),
                                      temiz(f"14 günlük kilitli izlemede eski yola göre log-kayıp farkı {r['fark']:+.4f} ({r['n']} maç)."), f"fbguc-kalici-{ak}-{gs}", gs)


# ------------------------------------------------------------------ kadro kapısı (veri birikince)
def kadro_sina(A):
    plog = jl(os.path.join(DATA, "predlog.json"), []) or []
    rows = [e for e in plog if isinstance(e.get("r"), list) and isinstance(e.get("kd"), list) and len(e["kd"]) == 7]
    nk = sum(1 for e in rows if e["kd"][1] or e["kd"][4])
    K = A.setdefault("kadro", {"aktif": False})
    K.update({"n": len(rows), "n_kilit": nk, "tarih": bugun().isoformat()})
    if len(rows) < 300 or nk < 80:
        K["durum"] = "veri_yetersiz"; K["not"] = "≥300 puanlı ve ≥80 kilit eksikli kilitli kayıt gerekiyor"; return K
    rows.sort(key=lambda e: e["d"])
    y = np.array([_y(e["r"]) for e in rows]); lp = np.log(np.clip(np.array([e["p"] for e in rows]), 1e-6, 1))
    dl = np.array([e["kd"][5] - e["kd"][2] for e in rows])    # dep kaybı − ev kaybı (ev lehine +)
    X = lambda b: lp + np.stack([b * dl, np.zeros_like(dl), -b * dl], 1)
    cut = int(len(rows) * 2 / 3)
    bs = np.linspace(-3, 6, 91)
    sc = [FL.ll3(np.exp(X(b)[:cut]) / np.exp(X(b)[:cut]).sum(1, keepdims=True), y[:cut]).mean() for b in bs]
    b = float(bs[int(np.argmin(sc))])
    q = np.exp(X(b)); q /= q.sum(1, keepdims=True); p0 = np.exp(lp); p0 /= p0.sum(1, keepdims=True)
    te = slice(cut, None)
    r = FL.blok_boot(FL.ll3(q[te], y[te]) - FL.ll3(p0[te], y[te]), np.array([f"{e['lg']}|{e['d']}" for e in rows])[te])
    K.update({"durum": "olculdu", "beta": b, "sinama": r})
    return K


# ------------------------------------------------------------------ ileriye dönük kontrol (kilitli predlog)
def ileri(karne=None):
    """Kilitli tahmin kayıtlarındaki oransız maçlarda: kilitlenen üretim p'si ile adayların aynı maçlardaki olasılığı.
    Aday durumları yalnız maç gününden önceki sonuçlarla kurulur; yığın ağırlığı kayıt döneminden önceki aylarla öğrenilmiştir."""
    import update as U
    karne = karne or olc()
    S = jl(os.path.join(DATA, "season.json"), {}) or {}
    M = jl(os.path.join(DATA, "model.json"), {}) or {}; P = dict(M.get("params") or {})
    plog = jl(os.path.join(DATA, "predlog.json"), []) or []
    UA = karne["uretim_agirlik"]; IA = karne["ileri_agirlik"]
    A = {"W": IA["W"], "Wo": IA["Wo"], "prm": UA["prm"], "poisson": UA["poisson"], "kullan": ["pois", "elo", "pi"], "aktif": True}
    rows = []
    by = collections.defaultdict(list)
    for e in plog:
        if isinstance(e.get("r"), list) and S.get(e["lg"], {}).get("src") == "espn": by[(e["lg"], e["d"])].append(e)
    for (lg, d), es in by.items():
        sub = {lg: dict(S[lg], matches=[m for m in S[lg]["matches"] if m["d"] < d])}
        fx = [{"lg": lg, "d": d, "h": e["h"], "a": e["a"]} for e in es]
        T = G.tahmin(fx, sub, P, date.fromisoformat(d), U, A, golge=True)
        PP = dict(P, decay=UA["poisson"]["decay"], prior=UA["poisson"]["prior"])
        try:
            F = U.fit(sub[lg]["matches"], date.fromisoformat(d), PP); F0 = U.fit(sub[lg]["matches"], date.fromisoformat(d), P)
        except Exception:
            F = None
        for e in es:
            z = T.get((lg, d, e["h"], e["a"]))
            if not z or not F: continue
            (ah, dh), (aa, da) = F["t"].get(e["h"], U.NEW_TEAM), F["t"].get(e["a"], U.NEW_TEAM)
            ps, os_ = U.served_probs(np.array([F["mu"] * F["gamma"] * ah * da]), np.array([F["mu"] * aa * dh]), P.get("gscale", 1), P.get("rho", -.06), P.get("h1", .4437))
            ps = U._cal3(ps, P.get("calT", 1), P.get("dk", 1))[0]
            (ah, dh), (aa, da) = F0["t"].get(e["h"], U.NEW_TEAM), F0["t"].get(e["a"], U.NEW_TEAM)
            pb, ob = U.served_probs(np.array([F0["mu"] * F0["gamma"] * ah * da]), np.array([F0["mu"] * aa * dh]), P.get("gscale", 1), P.get("rho", -.06), P.get("h1", .4437))
            pb = U._cal3(pb, P.get("calT", 1), P.get("dk", 1))[0]
            rows.append((f"{lg}|{d}", _y(e["r"]), e["p"], z["p"], list(ps), e.get("o"), z["o"], float(os_[0]), int(sum(e["r"]) > 2), list(pb), float(ob[0])))
    if not rows: return {"n": 0}
    y = np.array([r[1] for r in rows]); bl = np.array([r[0] for r in rows])
    p0 = np.array([r[2] for r in rows]); pk = np.array([r[3] for r in rows]); ps = np.array([r[4] for r in rows])
    o0 = np.array([r[5] for r in rows], float); ok_ = np.array([r[6] for r in rows]); os_ = np.array([r[7] for r in rows]); yo = np.array([r[8] for r in rows], float)
    pb = np.array([r[9] for r in rows]); ob = np.array([r[10] for r in rows])
    surumler = collections.Counter(e.get("v") for es in by.values() for e in es)
    out = {"n": len(rows), "not": "kilitli p'yi üreten motor sürümü bugünkünden farklı olabilir (surumler); bugünkü üretim yolu aynı maçlarda "
                                  "maç gününden önceki veriyle yeniden hesaplanır (uretim_bugun). Küçük örneklem, yalnız yön kontrolü.",
           "surumler": dict(surumler),
           "uretim_kilitli": FL.ozet(p0, y, o0, yo), "uretim_bugun": FL.ozet(pb, y, ob, yo),
           "topluluk": FL.ozet(pk, y, ok_, yo), "poisson_uygulama_yolu": FL.ozet(ps, y, os_, yo),
           "fark_topluluk_bugun": FL.blok_boot(FL.ll3(pk, y) - FL.ll3(pb, y), bl), "fark_poisson_bugun": FL.blok_boot(FL.ll3(ps, y) - FL.ll3(pb, y), bl),
           "fark_topluluk_ou_bugun": FL.blok_boot(FL.ll2(ok_, yo) - FL.ll2(ob, yo), bl),
           "fark_topluluk": FL.blok_boot(FL.ll3(pk, y) - FL.ll3(p0, y), bl), "fark_poisson": FL.blok_boot(FL.ll3(ps, y) - FL.ll3(p0, y), bl),
           "fark_topluluk_ou": FL.blok_boot(FL.ll2(ok_, yo) - FL.ll2(o0, yo), bl)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("komut", choices=["dongu", "olc", "karar", "ileri"])
    ap.add_argument("--cikti"); ap.add_argument("--kaynak"); ap.add_argument("--kuru", action="store_true")
    ar = ap.parse_args()
    if ar.komut == "olc":
        k = olc()
        if not k: print("ölçüm yok"); return 1
        p = ar.cikti or os.path.join(DATA, "deney", "fbguc", datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ") + ".json")
        jw(p, {"is": "fbguc", "zaman": datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ"), "karne": k}); print("yazıldı", p); return 0
    if ar.komut == "ileri":
        print(json.dumps(ileri(), ensure_ascii=False, indent=1)); return 0
    A = jl(AYAR, None)
    if ar.komut == "karar":
        fs = sorted(glob.glob(os.path.join(ar.kaynak or os.path.join(DATA, "deney"), "**", "fbguc", "*.json"), recursive=True)
                    + glob.glob(os.path.join(DATA, "deney", "fbguc", "*.json")), key=os.path.basename)
        D = jl(fs[-1]) if fs else None
        if D and A and os.path.basename(fs[-1]) in (A.get("islenen_olcum") or []): D = None     # aynı ölçüm iki kez karara girmesin
        if not D or not D.get("karne"):
            print("ölçüm dosyası yok; yalnız izleme")
            if A:
                import guardian
                Gel = jl(GELISIM, {"olaylar": []}) or {"olaylar": []}
                izle(A, Gel, guardian); kadro_sina(A)
                if not ar.kuru: jw(AYAR, A); json.dump(Gel, open(GELISIM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            return 0
        karne = D["karne"]
    else:
        karne = olc()
        if not karne: print("ölçüm yok"); return 1
    A = karar_ver(karne, A, kuru=ar.kuru)
    if ar.komut == "karar": A["islenen_olcum"] = ((A.get("islenen_olcum") or []) + [os.path.basename(fs[-1])])[-50:]
    kadro_sina(A)
    if not ar.kuru:
        jw(AYAR, A)
    return 0


if __name__ == "__main__":
    sys.exit(main())
