# OXXai at yarışı laboratuvarı — 🎯 6'LI GANYAN modülü.
# Görev: lab/at/ALTILI_GOREV.md. Hobi amaçlı: yalnız olasılık ve KOMBİNASYON SAYISI; para tutarı, bahis bağlantısı yok.
#
# Kurallar (araştırma): 6'lı ganyan, programda "ganyan başlangıcı" işaretli koşudan (aynada isGanyanStart) başlayan
# ardışık 6 koşudur; günde bir ya da iki 6'lı olur (ör. 8 koşulu gün: 1–6 ve 3–8; 9 koşulu: 1–6 ve 4–9; 7 koşulu: 2–7).
# Bayrak yoksa (aynada günlük program 2026-04 öncesi yok) "son 6 koşu" varsayılır — bayraklı günlerde son 6 koşu her
# zaman gerçek bir 6'lıdır (geri testte ölçülür, karnede `varsayim_dogrulama`). Ekürili atlar bir ayakta tek seçim
# (tek birim) sayılır; birimin olasılığı üyelerin toplamıdır. Koşmayan at programdan zaten düşer.
#
# Matematik: ayak olasılığı = seçilen birimlerin (kalibre) olasılık toplamı; 6'lı olasılığı = ayakların çarpımı
# (koşular bağımsız varsayılır). Kombinasyon = ayaklardaki birim sayılarının çarpımı. Dağıtım: bütçe (kombinasyon
# üst sınırı) altında Σ log(ayak olasılığı)'nı TAM en büyükleyen dinamik programlama (açgözlü Δlog P/Δlog C'den
# her zaman ≥; geri testte ikisi de ölçülür). "Altın ayak" (banko): ayağın en güçlü birimi p ≥ p_min ve 2. birime
# fark ≥ fark_min ise o ayak tek birimle geçilir. Eşikler ve kalibrasyon üssü τ YALNIZ seçim diliminde (ilk 2/3 gün)
# seçilir; son 1/3 gün (sınama) ayrı raporlanır.
#
# Çıktılar: data/at/altili/<gün>.json (canli.py gün içinde günceller; ilk ayak başlayınca kupon kilitlenir, sonuçlar
# geldikçe puanlanır), data/at/altili_karne.json (gece.py: geri test + canlı karne).
#   python lab/at/altili.py --geri-test        # yalnız geri test + karne
#   python lab/at/altili.py --gun 2026-10-25   # o günün 6'lısını data/at/canli (yoksa tahmin) ile kur/puanla
import argparse, glob, json, math, os, sys
from datetime import datetime, timedelta, timezone

BURA = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.abspath(os.path.join(BURA, "..", ".."))
CIKTI = os.path.join(KOK, "data", "at")
ALTILI = os.path.join(CIKTI, "altili")
KARNE = os.path.join(CIKTI, "altili_karne.json")
REPLAY_KOSU = os.path.join(CIKTI, "replay_kosular.json")

# Kombinasyon bütçeleri (para değil). Geri testte daha geniş bir ızgara da ölçülür (karne: `butce_izgarasi`).
SEVIYE = {"dar": 64, "orta": 192, "genis": 576}
IZGARA = [16, 32, 64, 96, 192, 384, 576, 1000]
TAU_IZGARA = [0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2]
P_IZGARA = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65]
F_IZGARA = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40]
ALTIN_YOK = {"p_min": None, "fark_min": None}
MIN_ALTIN_ORAN = 0.25   # aday kural: seçim diliminde 6'lı başına en az bu kadar altın ayak (çok seyrek kural anlamsız)
ZORLA_SIGMA = 2.0       # banko zorlaması yalnız seçim diliminde zorlamasıza göre bu kadar σ fazla isabet getirirse açılır
UYARI = "Hobi amaçlı olasılıklardır; garanti değildir. Para tutarı gösterilmez · 18+"


def tsi_simdi():
    return datetime.now(timezone.utc) + timedelta(hours=3)


def jyaz(yol, veri_, sikisik=True):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    tmp = yol + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if sikisik:
            json.dump(veri_, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(veri_, f, ensure_ascii=False, indent=1)
    os.replace(tmp, yol)


def joku(yol, vars_=None):
    try:
        return json.load(open(yol, encoding="utf-8"))
    except Exception:
        return vars_


def _r(v, n=4):
    return None if v is None else round(float(v), n)


# ---------------------------------------------------------------- çekirdek
def birimler(atlar, ekuri, tau=1.0):
    """atlar: [(no, p)] ; ekuri: [[no, no], ...] -> [{"nolar": [...], "p": kalibre p}] p'ye göre azalan.
    Kalibrasyon: p^τ, koşu içinde yeniden normalize (τ<1 güçlü atları biraz yumuşatır)."""
    grup = {}
    for i, g in enumerate(ekuri or []):
        for n in g:
            grup[str(n)] = i
    U = {}
    for no, p in atlar:
        no = str(no)
        k = ("e", grup[no]) if no in grup else no
        u = U.setdefault(k, {"nolar": [], "p0": 0.0})
        u["nolar"].append(no)
        u["p0"] += max(float(p or 0.0), 0.0)
    L = list(U.values())
    q = [u["p0"] ** tau if u["p0"] > 0 else 0.0 for u in L]
    s = sum(q) or 1.0
    for u, x in zip(L, q):
        u["p"] = x / s
    L.sort(key=lambda u: -u["p"])
    return L


def altin_mi(U, kural):
    if not kural or kural.get("p_min") is None or not U:
        return False
    p1 = U[0]["p"]
    p2 = U[1]["p"] if len(U) > 1 else 0.0
    return p1 >= kural["p_min"] - 1e-12 and p1 - p2 >= kural["fark_min"] - 1e-12


def dagit(ayaklar, butce, sabit=None):
    """ayaklar: her ayak için birim olasılıkları (azalan). Π n_i ≤ bütçe altında Σ log(Σ_{j<n_i} p_ij) TAM en büyük.
    sabit[i]=True olan ayak (altın) tek birimle. Eşitlikte daha az kombinasyon. Döner: n listesi."""
    # durum: (kombinasyon, Σlog, seçimler). Pareto budaması: daha az ya da eşit kombinasyonla daha yüksek
    # Σlog'a ulaşan bir durum varsa diğeri atılır — sonuç tam DP ile aynı, durum sayısı küçük kalır.
    dp = [(1, 0.0, ())]
    for i, P in enumerate(ayaklar):
        cum, s = [], 0.0
        for x in P:
            s += x
            cum.append(math.log(max(s, 1e-12)))
        izin = 1 if (sabit and sabit[i]) else len(cum)
        yeni = []
        for c, v, ch in dp:
            for n in range(1, izin + 1):
                c2 = c * n
                if c2 > butce:
                    break
                yeni.append((c2, v + cum[n - 1], ch + (n,)))
        yeni.sort(key=lambda x: (x[0], -x[1]))
        dp, en = [], -1e300
        for x in yeni:
            if x[1] > en + 1e-12:
                dp.append(x)
                en = x[1]
    return list(dp[-1][2])


def dagit_acgozlu(ayaklar, butce, sabit=None):
    """Karşılaştırma için: her adımda Δlog P / Δlog C en büyük birimi ekle."""
    n = [1] * len(ayaklar)
    S = [P[0] for P in ayaklar]
    while True:
        C = math.prod(n)
        en, ei = 0.0, None
        for i, P in enumerate(ayaklar):
            if (sabit and sabit[i]) or n[i] >= len(P) or C // n[i] * (n[i] + 1) > butce:
                continue
            r = (math.log(S[i] + P[n[i]]) - math.log(S[i])) / (math.log(n[i] + 1) - math.log(n[i]))
            if r > en:
                en, ei = r, i
        if ei is None:
            return n
        S[ei] += ayaklar[ei][n[ei]]
        n[ei] += 1


_ONB = {}


def kupon(ayak_birim, butce, kural, acgozlu=False, anahtar=None):
    """ayak_birim: 6 ayağın birim listeleri. Döner: (n listesi, altın bayrakları, p, kombinasyon).
    anahtar verilirse (geri test) aynı 6'lı + aynı altın maskesi + bütçe için dağıtım önbellekten gelir."""
    alt = [altin_mi(U, kural) for U in ayak_birim]
    sabit = alt if (kural or {}).get("zorla") else [False] * len(alt)
    P = [[u["p"] for u in U] for U in ayak_birim]
    ak = None if anahtar is None else (anahtar, tuple(sabit), butce, acgozlu)
    n = _ONB.get(ak) if ak else None
    if n is None:
        n = (dagit_acgozlu if acgozlu else dagit)(P, butce, sabit)
        if ak:
            _ONB[ak] = n
    p = math.prod(sum(P[i][:n[i]]) for i in range(len(P)))
    return n, alt, p, math.prod(n)


def altililari_bul(kosular_hip, gs_al, no_al):
    """Bir hipodromun bir günlük koşuları (koşu no sıralı) -> [(sıra, başlangıç no, [6 koşu], varsayım mı)].
    Bayrak varsa: işaretli her koşudan başlayan ardışık 6 koşu (6 koşu yoksa ya da eksik koşu varsa alınmaz).
    Hiç bayrak yoksa (None): son 6 koşu varsayımı."""
    by = {no_al(k): k for k in kosular_hip}
    if not by:
        return []
    son = max(by)
    bay = [gs_al(k) for k in kosular_hip]
    out = []
    if all(b is None for b in bay):
        bas = [son - 5] if son >= 6 else []
        vars_ = True
    else:
        bas = sorted(no_al(k) for k in kosular_hip if gs_al(k))
        vars_ = False
    for b in bas:
        seq = [by.get(b + j) for j in range(6)]
        if b >= 1 and all(seq):
            out.append((b, seq, vars_))
    return [(i + 1, b, seq, v) for i, (b, seq, v) in enumerate(out)]


# ---------------------------------------------------------------- geri test
def _replay_altililar(R):
    """replay_kosular.json -> 6'lı listesi (her ayak: koşu sözlüğü). Eksik ayaklı 6'lılar sayılır, atlanır."""
    gun = {}
    for k in R["kosular"]:
        gun.setdefault((k["t"], k["h"]), []).append(k)
    out, eksik = [], 0
    dogr = {"gun_hip": 0, "son6_gercek": 0}
    for (t, h), L in sorted(gun.items()):
        L.sort(key=lambda k: k["k"])
        A = altililari_bul(L, lambda k: k["gs"], lambda k: k["k"])
        bayrakli = any(k["gs"] is not None for k in L)
        if bayrakli:
            # bayraklı başlangıçlardan 6 koşusu tamam olmayanlar (sonuçta eksik/çift kazananlı koşu) eksik sayılır
            son = max(k["k"] for k in L)
            for k in L:
                if k["gs"] and k["k"] + 5 <= son and not any(a[1] == k["k"] for a in A):
                    eksik += 1
            dogr["gun_hip"] += 1
            dogr["son6_gercek"] += int(any(k["gs"] and k["k"] == son - 5 for k in L))
        for no, b, seq, v in A:
            out.append({"id": f"{t}/{h}/{no}", "t": t, "h": h, "no": no, "bas": b, "varsayim": v, "ayak": seq})
    return out, eksik, dogr


def _ayak_birim(k, tau, sutun=1):
    return birimler([(a[0], a[sutun]) for a in k["a"]], k["e"], tau)


def _kazanan_birim(U, k):
    w = next((a[0] for a in k["a"] if a[3] == 1), None)
    return w, next((i for i, u in enumerate(U) if w in u["nolar"]), None)


def tau_sec(kosular):
    """Kalibrasyon üssü: kazanan birim log-olasılığı en iyi τ (yalnız verilen koşularda)."""
    sonuc = []
    for tau in TAU_IZGARA:
        s = n = 0
        for k in kosular:
            U = _ayak_birim(k, tau)
            _, wi = _kazanan_birim(U, k)
            if wi is None:
                continue
            s -= math.log(max(U[wi]["p"], 1e-9))
            n += 1
        sonuc.append((tau, s / max(n, 1)))
    return min(sonuc, key=lambda x: x[1])[0], [[t, round(v, 5)] for t, v in sonuc]


_UB = {}


def oynat(altililar, tau, kural, butceler, acgozlu=False):
    """Her 6'lı ve bütçe için kupon + puan. Döner: satırlar."""
    sat = []
    for X in altililar:
        ub = (X["id"], tau)
        if ub not in _UB:
            _UB[ub] = [_ayak_birim(k, tau) for k in X["ayak"]]
        UB = _UB[ub]
        kaz = [_kazanan_birim(U, k)[1] for U, k in zip(UB, X["ayak"])]
        r = {"id": X["id"], "t": X["t"], "varsayim": X["varsayim"], "b": {}}
        for B in butceler:
            n, alt, p, c = kupon(UB, B, kural, acgozlu, anahtar=(X["id"], tau))
            at = [kaz[i] is not None and kaz[i] < n[i] for i in range(6)]
            r["b"][B] = {"p": p, "c": c, "at": at, "alt": alt, "w0": [kaz[i] == 0 for i in range(6)], "n": n,
                         "pa": [sum(u["p"] for u in UB[i][:n[i]]) for i in range(6)],
                         "p1": [UB[i][0]["p"] for i in range(6)]}
        sat.append(r)
    return sat


def _kova(ps, hs):
    sinir = [0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 1.01]
    out = []
    for lo, hi in zip(sinir, sinir[1:]):
        L = [(p, h) for p, h in zip(ps, hs) if lo <= p < hi]
        if L:
            out.append({"aralik": [lo, min(hi, 1.0)], "n": len(L), "tahmin_ort": _r(sum(p for p, _ in L) / len(L)),
                        "gerceklesen": _r(sum(h for _, h in L) / len(L))})
    return out


def ozet(sat, B):
    L = [r["b"][B] for r in sat]
    if not L:
        return {"n": 0}
    n = len(L)
    hit = sum(all(x["at"]) for x in L)
    bek = sum(x["p"] for x in L)
    var = sum(x["p"] * (1 - x["p"]) for x in L)
    ayak = [sum(x["at"][i] for x in L) / n for i in range(6)]
    al = [(x["w0"][i], x["p1"][i]) for x in L for i in range(6) if x["alt"][i]]   # altın ayak: en güçlü at kazandı mı
    nalt = [(x["at"][i], x["pa"][i]) for x in L for i in range(6) if not x["alt"][i]]
    return {
        "n": n, "isabet": hit, "isabet_orani": _r(hit / n), "beklenen": _r(bek, 2), "beklenen_oran": _r(bek / n),
        "z": _r((hit - bek) / math.sqrt(var), 2) if var > 0 else None,
        "bes_ayak": sum(sum(x["at"]) == 5 for x in L), "ort_ayak_tutan": _r(sum(sum(x["at"]) for x in L) / n, 3),
        "ort_kombinasyon": _r(sum(x["c"] for x in L) / n, 1), "ort_p": _r(bek / n),
        "ayak_isabet": _r(sum(ayak) / 6), "ayak_isabet_sira": [_r(a) for a in ayak],
        "ayak_beklenen": _r(sum(sum(x["pa"]) for x in L) / (6 * n)),
        "altin_ayak": {"tanim": "kurala uyan ayaklarda en güçlü atın (tek at) kazanma isabeti", "n": len(al),
                       "kuponda_tek_at": sum(1 for x in L for i in range(6) if x["alt"][i] and x["n"][i] == 1), "isabet": _r(sum(a for a, _ in al) / len(al)) if al else None,
                       "beklenen": _r(sum(p for _, p in al) / len(al)) if al else None,
                       "altili_basina": _r(len(al) / n, 3)},
        "diger_ayak": {"n": len(nalt), "isabet": _r(sum(a for a, _ in nalt) / len(nalt)) if nalt else None,
                       "beklenen": _r(sum(p for _, p in nalt) / len(nalt)) if nalt else None},
        "kalibrasyon": _kova([x["p"] for x in L], [int(all(x["at"])) for x in L]),
    }


def _skor(sat, butceler):
    """Seçim ölçütü: bütçeler üzerinden toplam isabet; eşitlikte toplam tutan ayak (daha az gürültülü)."""
    return (sum(all(r["b"][B]["at"]) for r in sat for B in butceler),
            sum(sum(r["b"][B]["at"]) for r in sat for B in butceler))


def geri_test(R=None, log=print):
    R = R or joku(REPLAY_KOSU)
    if not R:
        return None
    altililar, eksik, dogr = _replay_altililar(R)
    gunler = sorted({k["t"] for k in R["kosular"]})
    kes = gunler[int(round(len(gunler) * 2 / 3))]
    sec_k = [k for k in R["kosular"] if k["t"] < kes]
    tau, tau_tab = tau_sec(sec_k)
    log(f"6'lı: {len(altililar)} (eksik ayaklı atlanan {eksik}); kesim {kes}; τ={tau}")
    A = [x for x in altililar if x["t"] < kes]
    Bs = [x for x in altililar if x["t"] >= kes]
    butce = list(SEVIYE.values())
    # 1) Altın ayak eşikleri — YALNIZ seçim dilimi, Altın at mantığıyla: 6'lı başına ≥ MIN_ALTIN_ORAN altın ayak
    #    şartıyla en güçlü atın kazanma isabeti en yüksek eşik çifti (eşitlikte daha çok ayak).
    # 2) Banko zorlaması (altın ayağı tek atla geçmek): seçim diliminde zorlamasız tam-DP kupona göre bütçeler toplamı
    #    isabeti ZORLA_SIGMA·√beklenen'den fazla artırıyorsa açılır; yoksa altın ayak yalnız işarettir (kalibre
    #    olasılıklarla zorlama beklenen isabeti tanım gereği düşürür; küçük gerçekleşen farklar gürültüdür).
    sec_ayak = []
    for X in A:
        for k in X["ayak"]:
            U = _ayak_birim(k, tau)
            sec_ayak.append((U[0]["p"], U[0]["p"] - (U[1]["p"] if len(U) > 1 else 0.0), _kazanan_birim(U, k)[1] == 0))
    tablo = []
    taban_s = oynat(A, tau, ALTIN_YOK, butce)
    taban_sk = _skor(taban_s, butce)
    taban_bek = sum(r["b"][B]["p"] for r in taban_s for B in butce)
    for pm in P_IZGARA:
        for fm in F_IZGARA:
            kr = {"p_min": pm, "fark_min": fm}
            L = [w for p1, f, w in sec_ayak if p1 >= pm - 1e-12 and f >= fm - 1e-12]
            zs = oynat(A, tau, {**kr, "zorla": True}, butce)
            sk = _skor(zs, butce)
            tablo.append({**kr, "altin_ayak": len(L), "altin_altili_basina": round(len(L) / max(len(A), 1), 3),
                          "altin_isabet": _r(sum(L) / len(L)) if L else None,
                          "zorla_isabet_toplam": sk[0], "zorla_ayak_toplam": sk[1],
                          "zorla_beklenen_toplam": _r(sum(r["b"][B]["p"] for r in zs for B in butce), 2),
                          "uygun": len(L) / max(len(A), 1) >= MIN_ALTIN_ORAN})
    uy = [r for r in tablo if r["uygun"] and r["altin_isabet"] is not None]
    en = max(uy, key=lambda r: (r["altin_isabet"], r["altin_ayak"]))
    esik = ZORLA_SIGMA * math.sqrt(max(taban_bek, 1.0))
    kazanc = en["zorla_isabet_toplam"] - taban_sk[0]
    kural = {"p_min": en["p_min"], "fark_min": en["fark_min"], "zorla": kazanc >= esik}
    zorla_karar = {"zorlamasiz_isabet_toplam": taban_sk[0], "zorlamasiz_beklenen_toplam": _r(taban_bek, 2),
                   "zorlali_isabet_toplam": en["zorla_isabet_toplam"], "zorlali_beklenen_toplam": en["zorla_beklenen_toplam"],
                   "kazanc": kazanc, "esik": _r(esik, 1), "zorla": kural["zorla"],
                   "en_iyi_zorlali_aday": max(tablo, key=lambda r: r["zorla_isabet_toplam"])}
    log(f"altın kural (seçim dilimi): {kural} altın isabet {en['altin_isabet']} ({en['altin_ayak']} ayak) · zorlama "
        f"{en['zorla_isabet_toplam']} vs zorlamasız {taban_sk[0]} (eşik +{esik:.1f})")
    tum = oynat(altililar, tau, kural, IZGARA)
    karsi = {**kural, "zorla": not kural["zorla"]}
    tum_yok = oynat(altililar, tau, karsi, butce)
    tum_ac = oynat(altililar, tau, kural, butce, acgozlu=True)
    bayrakli = [r for r in tum if not r["varsayim"]]
    sec = [r for r in tum if r["t"] < kes]
    sin = [r for r in tum if r["t"] >= kes]
    seviye = lambda S: {ad: ozet(S, B) for ad, B in SEVIYE.items()}
    out = {
        "olusturma": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "aciklama": ("Geriye dönük test: data/at/replay_kosular.json (gün gün yeniden oynatma, sızıntısız) üzerinden her "
                     "geçmiş 6'lı 'hiç oynanmamış gibi' yalnız sabah olasılığıyla (p_sabah, oransız) seçildi; sonuç yalnız "
                     "puanlamada kullanıldı. Kalibrasyon üssü τ ve altın eşikleri yalnız seçim diliminde (ilk 2/3 gün) seçildi."),
        "donem": [gunler[0], gunler[-1]], "bolum": {"secim": [gunler[0], gunler[gunler.index(kes) - 1]], "sinama": [kes, gunler[-1]]},
        "altili": len(tum), "altili_bayrakli": len(bayrakli), "altili_varsayim": len(tum) - len(bayrakli),
        "eksik_ayakli_atlanan": eksik,
        "varsayim_dogrulama": {**dogr, "not": "bayraklı gün-hipodromlarda son 6 koşunun gerçek bir 6'lı başlangıcı olma oranı; "
                                               "bayraksız (2026-04 öncesi) günlerde 'son 6 koşu' varsayımının dayanağı"},
        "butce": SEVIYE, "tau": tau, "tau_tablo": tau_tab, "altin_kural": {**kural, "kaynak": "geri test seçim dilimi"},
        "zorlama_karari": zorla_karar,
        "seviyeler": seviye(tum),
        "secim": {"altili": len(sec), "seviyeler": seviye(sec)},
        "sinama": {"altili": len(sin), "seviyeler": seviye(sin)},
        "yalniz_bayrakli": {"altili": len(bayrakli), "seviyeler": seviye(bayrakli)},
        "karsi_politika": {"zorla": karsi["zorla"], "seviyeler": {ad: {k: v for k, v in ozet(tum_yok, B).items() if k in ("n", "isabet", "beklenen", "bes_ayak", "ayak_isabet")}
                             for ad, B in SEVIYE.items()},
        "sinama": {ad: {k: v for k, v in ozet([r for r in tum_yok if r["t"] >= kes], B).items()
                                         if k in ("n", "isabet", "beklenen", "bes_ayak", "ayak_isabet")} for ad, B in SEVIYE.items()}},
        "acgozlu_karsilastirma": {ad: {"dp_beklenen": ozet(tum, B)["beklenen"], "acgozlu_beklenen": ozet(tum_ac, B)["beklenen"],
                                       "dp_isabet": ozet(tum, B)["isabet"], "acgozlu_isabet": ozet(tum_ac, B)["isabet"]}
                                  for ad, B in SEVIYE.items()},
        "butce_izgarasi": [{"kombinasyon": B, **{k: v for k, v in ozet(tum, B).items() if k in ("n", "isabet", "beklenen", "isabet_orani", "beklenen_oran", "ort_kombinasyon")},
                            "sinama": {k: v for k, v in ozet(sin, B).items() if k in ("n", "isabet", "beklenen")}} for B in IZGARA],
        "altin_tarama": sorted(tablo, key=lambda r: (not r["uygun"], -(r["altin_isabet"] or 0), -r["altin_ayak"])),
    }
    return out


# ---------------------------------------------------------------- günlük (canlı) 6'lı
def gun_programi(tarih, kaynak=None):
    """Aynanın günlük programından (data/daily) (hipodrom, koşu no) -> (isGanyanStart, ekuri grupları)."""
    import veri
    f = os.path.join(kaynak or veri.KAYNAK, "data", "daily", tarih + ".json")
    out = {}
    try:
        js = json.load(open(f, encoding="utf-8"))
    except Exception:
        return out
    for r in js if isinstance(js, list) else []:
        if r.get("venue") not in veri.YERLI:
            continue
        gs = r.get("isGanyanStart")
        eg = [[str(x) for x in g] for g in (r.get("ekuriGroups") or []) if isinstance(g, list) and len(g) > 1]
        out[(r["venue"], int(r.get("raceNo") or 0))] = (None if gs is None else bool(gs), eg)
    return out


def _gun_kosulari(tarih):
    """data/at/canli/<gün>.json (p_sabah, p_oran, sonuç) yoksa data/at/tahmin/<gün>.json (p_kazanma)."""
    c = joku(os.path.join(CIKTI, "canli", tarih + ".json"))
    if c and c.get("kosular"):
        ks = []
        for k in c["kosular"]:
            ks.append({"hipodrom": k["hipodrom"], "kosu": k["kosu"], "saat": k.get("saat"), "kosu_id": k["kosu_id"],
                       "atlar": [{"no": str(a["no"]), "ad": a.get("ad"), "p_sabah": a.get("p_sabah"), "p_oran": a.get("p_oran")}
                                 for a in k["atlar"]],
                       "kazanan": (k.get("sonuc") or {}).get("kazanan")})
        return ks, c.get("model_surumu")
    t = joku(os.path.join(CIKTI, "tahmin", tarih + ".json"))
    if t and t.get("kosular"):
        return [{"hipodrom": k["hipodrom"], "kosu": k["kosu"], "saat": k.get("saat"), "kosu_id": k["kosu_id"],
                 "atlar": [{"no": str(a["no"]), "ad": a.get("ad"), "p_sabah": a.get("p_kazanma"), "p_oran": None} for a in k["atlar"]],
                 "kazanan": None} for k in t["kosular"]], t.get("model_surumu")
    return [], None


def _ayak_p(k, yalniz_sabah=False):
    """Ayak olasılık kaynağı: tüm atlarda oranlı harman (p_oran) varsa o, yoksa sabah modeli. Kupon ilk kez
    6'lı başladıktan sonra kuruluyorsa (yalniz_sabah) nihai oran sonradan bilgi sayılır: yalnız sabah modeli."""
    if not yalniz_sabah and k["atlar"] and all(a.get("p_oran") is not None for a in k["atlar"]):
        return "oran", [(a["no"], a["p_oran"]) for a in k["atlar"]]
    return "sabah", [(a["no"], a.get("p_sabah") or 0.0) for a in k["atlar"]]


def kupon_kur(seq, eku, tau, kural, yalniz_sabah=False):
    """6 koşu (gün kaydı) -> seviyeler sözlüğü + kaynak."""
    UB, kay = [], []
    for k in seq:
        s, P = _ayak_p(k, yalniz_sabah)
        kay.append(s)
        UB.append(birimler(P, eku.get(k["kosu"], []), tau))
    sev = {}
    for ad, B in SEVIYE.items():
        n, alt, p, c = kupon(UB, B, kural)
        ay = []
        for i, k in enumerate(seq):
            ad_ = {a["no"]: a.get("ad") for a in k["atlar"]}
            sec = [no for u in UB[i][:n[i]] for no in u["nolar"]]
            ay.append({"kosu": k["kosu"], "saat": k.get("saat"), "secim": sec, "birim": n[i], "banko": bool(alt[i] and n[i] == 1), "altin": bool(alt[i]),
                       "p_ayak": _r(sum(u["p"] for u in UB[i][:n[i]])), "p_ilk": _r(UB[i][0]["p"]),
                       "fark": _r(UB[i][0]["p"] - (UB[i][1]["p"] if len(UB[i]) > 1 else 0.0)),
                       "ekuri": [u["nolar"] for u in UB[i][:n[i]] if len(u["nolar"]) > 1],
                       "atlar": [[no, ad_.get(no) or "", _r(u["p"] / len(u["nolar"]) if len(u["nolar"]) > 1 else u["p"])]
                                 for u in UB[i][:n[i]] for no in u["nolar"]]})
        sev[ad] = {"butce": B, "kombinasyon": c, "p": _r(p, 6), "altin_ayak": sum(1 for a in ay if a["banko"]), "ayaklar": ay}
    return sev, ("oran" if "oran" in kay else "sabah")


def _puanla(X, by):
    kaz = [by.get(a["kosu"], {}).get("kazanan") for a in X["seviyeler"]["dar"]["ayaklar"]]
    S = {"kazananlar": kaz, "biten_ayak": sum(1 for w in kaz if w), "tamam": all(kaz)}
    S["ayak_tuttu"], S["tuttu"] = {}, {}
    for ad, L in X["seviyeler"].items():
        at = [None if w is None else str(w) in [str(x) for x in a["secim"]] for a, w in zip(L["ayaklar"], kaz)]
        S["ayak_tuttu"][ad] = at
        S["tuttu"][ad] = all(at) if S["tamam"] else (False if any(x is False for x in at) else None)
    return S


def mirror_kazananlar(tarih, kaynak=None):
    """Aynanın sonuç dosyasından (data/results/<gün>.json) (hipodrom, koşu no) -> kazanan at no (yalnız okunur)."""
    import veri
    out = {}
    try:
        js = json.load(open(os.path.join(kaynak or veri.KAYNAK, "data", "results", tarih + ".json"), encoding="utf-8"))
    except Exception:
        return out
    for r in js if isinstance(js, list) else []:
        if r.get("venue") not in veri.YERLI:
            continue
        bir = [h for h in r.get("horses") or [] if not h.get("nonRunner") and str(h.get("position") or "") == "1"]
        if len(bir) == 1:
            out[(r["venue"], int(r.get("raceNo") or 0))] = str(bir[0].get("no") or "")
    return out


def gun_guncelle(tarih, kaynak=None, simdi=None, kurallar=None, log=print):
    """O günün 6'lılarını kurar/günceller. Kilit: ilk ayağın saatine (TSİ) gelinince ya da herhangi bir ayağın sonucu
    geldiyse kupon değişmez; sonra yalnız sonuç puanlanır. İlk kez kilitten sonra kurulan kupon kosudan_once=false
    (canlı karneye sayılmaz)."""
    ks, surum = _gun_kosulari(tarih)
    if not ks:
        return None
    mk = mirror_kazananlar(tarih, kaynak)
    for k in ks:
        if not k.get("kazanan"):
            k["kazanan"] = mk.get((k["hipodrom"], k["kosu"]))
    simdi = simdi or tsi_simdi()
    sim = simdi.strftime("%Y-%m-%d %H:%M")
    K = kurallar or joku(KARNE, {}).get("geriye_donuk") or {}
    tau = K.get("tau", 1.0)
    kural = K.get("altin_kural") or dict(ALTIN_YOK)
    prog = gun_programi(tarih, kaynak)
    gs = {k: v[0] for k, v in prog.items()}
    yol = os.path.join(ALTILI, tarih + ".json")
    eski = {x["id"]: x for x in (joku(yol, {}) or {}).get("altililar", [])}
    hip = {}
    for k in ks:
        hip.setdefault(k["hipodrom"], []).append(k)
    out = []
    for h, L in sorted(hip.items()):
        L.sort(key=lambda k: k["kosu"])
        by = {k["kosu"]: k for k in L}
        eku = {k["kosu"]: [[n for n in g if n in {a["no"] for a in k["atlar"]}] for g in prog.get((h, k["kosu"]), (None, []))[1]]
               for k in L}
        eku = {n: [g for g in G if len(g) > 1] for n, G in eku.items()}
        for no, b, seq, vars_ in altililari_bul(L, lambda k: gs.get((h, k["kosu"])), lambda k: k["kosu"]):
            xid = f"{tarih}/{h}/{no}"
            bas_saat = seq[0].get("saat")
            basladi = bool(bas_saat and f"{tarih} {bas_saat}" <= sim) or any(k.get("kazanan") for k in seq)
            E = eski.get(xid)
            if E and (E.get("kilitli") or basladi) and E.get("seviyeler"):
                X = dict(E)
                if not X.get("kilitli"):
                    X["kilitli"], X["kilit_tsi"] = True, sim
            else:
                sev, kay = kupon_kur(seq, eku, tau, kural, yalniz_sabah=basladi)
                X = {"id": xid, "hipodrom": h, "no": no, "baslangic_kosu": b, "saat": bas_saat,
                     "kosular": [k["kosu"] for k in seq], "varsayim": vars_, "kaynak": kay, "seviyeler": sev,
                     "kurulus_tsi": sim, "kosudan_once": not basladi, "kilitli": basladi,
                     "kilit_tsi": sim if basladi else None}
            X["sonuc"] = _puanla(X, by)
            out.append(X)
    if not out:
        return None
    veri_ = {"tarih": tarih, "guncelleme_tsi": sim, "model_surumu": surum, "butce": SEVIYE, "tau": tau,
             "altin_kural": kural, "aciklama": "6'yı birden tutma olasılığı = ayaklardaki seçilen atların toplam olasılığının "
             "çarpımı (koşular bağımsız varsayılır). Kombinasyon = ayaklardaki seçim sayılarının çarpımı (ekürili atlar tek "
             "seçim). KUPO ilk ayak başlayınca kilitlenir.", "uyari": UYARI, "altililar": out}
    onceki = joku(yol)
    if onceki and {k: v for k, v in onceki.items() if k != "guncelleme_tsi"} == \
            json.loads(json.dumps({k: v for k, v in veri_.items() if k != "guncelleme_tsi"}, ensure_ascii=False)):
        return veri_
    jyaz(yol, veri_)
    log(f"6'lı {tarih}: {len(out)} altılı yazıldı")
    return veri_


# ---------------------------------------------------------------- karne
def canli_karne():
    """data/altili/*.json içinden koşudan önce kurulmuş ve tamamlanmış 6'lıların karnesi."""
    sev = {ad: {"n": 0, "isabet": 0, "beklenen": 0.0, "bes_ayak": 0, "ayak_tutan": 0, "ort_kombinasyon": 0.0,
                "altin_n": 0, "altin_isabet": 0} for ad in SEVIYE}
    gun = 0
    for f in sorted(glob.glob(os.path.join(ALTILI, "*.json"))):
        d = joku(f, {})
        say = False
        for X in d.get("altililar", []):
            S = X.get("sonuc") or {}
            if not (X.get("kosudan_once") and S.get("tamam")):
                continue
            say = True
            for ad, L in X["seviyeler"].items():
                if ad not in sev:
                    continue
                at = S["ayak_tuttu"][ad]
                s = sev[ad]
                s["n"] += 1
                s["isabet"] += int(all(at))
                s["beklenen"] += L["p"]
                s["bes_ayak"] += int(sum(map(bool, at)) == 5)
                s["ayak_tutan"] += sum(map(bool, at))
                s["ort_kombinasyon"] += L["kombinasyon"]
                for a, ok in zip(L["ayaklar"], at):
                    if a.get("banko"):
                        s["altin_n"] += 1
                        s["altin_isabet"] += int(bool(ok))
        gun += say
    for s in sev.values():
        n = s["n"]
        s["beklenen"] = round(s["beklenen"], 2)
        s["ort_kombinasyon"] = round(s["ort_kombinasyon"] / n, 1) if n else 0
        t = s.pop("ayak_tutan")
        s["ayak_isabet"] = round(t / (6 * n), 4) if n else None
        s["altin_isabet"] = round(s["altin_isabet"] / s["altin_n"], 4) if s["altin_n"] else None
    return {"gun": gun, "seviyeler": sev, "not": "Yalnız ilk ayaktan önce kurulmuş (kosudan_once) ve 6 ayağı biten 6'lılar."}


def karne_guncelle(log=print):
    g = geri_test(log=log)
    eski = joku(KARNE, {}) or {}
    out = {"guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"), "uyari": UYARI,
           "geriye_donuk": g or eski.get("geriye_donuk"), "canli": canli_karne()}
    jyaz(KARNE, out, sikisik=False)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geri-test", action="store_true")
    ap.add_argument("--gun", action="append", default=[])
    ap.add_argument("--simdi", default=None, help="'YYYY-MM-DD HH:MM' TSİ (kilit sınaması için)")
    ar = ap.parse_args()
    sys.path.insert(0, BURA)
    if ar.geri_test or not ar.gun:
        k = karne_guncelle()
        g = k["geriye_donuk"]
        print(json.dumps({"altili": g["altili"], "tau": g["tau"], "altin": g["altin_kural"],
                          "seviye": {a: {x: g["seviyeler"][a][x] for x in ("n", "isabet", "beklenen", "ayak_isabet", "bes_ayak")} for a in SEVIYE},
                          "sinama": {a: {x: g["sinama"]["seviyeler"][a][x] for x in ("n", "isabet", "beklenen", "ayak_isabet")} for a in SEVIYE}},
                         ensure_ascii=False, indent=1))
    simdi = datetime.strptime(ar.simdi, "%Y-%m-%d %H:%M") if ar.simdi else None
    for t in ar.gun:
        gun_guncelle(t, simdi=simdi)
    if ar.gun:
        jyaz(KARNE, {**(joku(KARNE, {}) or {}), "canli": canli_karne()}, sikisik=False)


if __name__ == "__main__":
    main()
