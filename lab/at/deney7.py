# OXXai at yarışı laboratuvarı — v7 deney masası: "daha sık güncelleme" ve gün içi öğrenme (elle çalıştırılır).
# Kalıp ve kapı: lab/at/deney4.py (Masa, gecer) + deney5.gecer_harman — iki zaman katı (A: 2025-11-01 → son %30'un başı,
# B: son %30), zaman sıralı walk-forward, yalnız geçmişle eğitim. Ek ölçüler: Brier (koşu başına Σ(p−y)²), ilk-1 isabet,
# ilk-3 isabeti (ilk seçimin ilk 3'e girmesi).
# Adaylar:
#   e1_hafta_kal : ham katman (doğrusal + GBM) ayda bir; kalibrasyon/harman katmanı HAFTADA bir, son 90 günle yeniden.
#   e1_gun_kal   : aynı, kalibrasyon HER YARIŞ GÜNÜ (dünkü sonuçlar dahil) yeniden.
#   e2_hafta_ham : ham katman da haftada bir yeniden eğitilir (yayındaki gece yenilemesinin ölçümü; YENILEME_GUN için kanıt).
#   e3_gun_ici   : gün içi katman (yalnız canlı/harman tarafı): aynı gün DAHA ÖNCE biten koşulardan jokey/antrenör
#                  "bugünkü kalıntısı" (Σ(y − p) önceki koşularında) ve hipodromun bugünkü favori sapması; katsayılar
#                  kalibrasyon penceresinde (ayın öncesindeki 90 gün) koşullu logitle öğrenilir.
#   e4_gbm_kalinti : GBM doğrusal puandan başlar (init_score) — kalıntı ağaçlar.
#   e5_alan_ici    : 12 temel özelliğin koşu içi z ve sıra yüzdeliği (eşitlere ORTALAMA sıra: satır sırası bitiş sırasıdır,
#                    kararlı sıralama sonucu sızdırır — ilk denemede yakalandı, düzeltildi).
# Sonuç (28.10.2026; ortalama 2 kat, yalnız-model / harman log-loss): taban 1,8476 / 1,7889. e1_hafta_kal 1,8475 / 1,7887,
#   e1_gun_kal 1,8474 / 1,7887, e2_hafta_ham 1,8463 / 1,7883 (ilk seçim −0,04 puan; GA sıfırı kapsıyor), e3_gun_ici
#   1,8495 / 1,7888 — hepsi gürültü içinde, elendi. e4: yalnız-model +0,0004 [−0,0028; +0,0035] ama HARMAN −0,0020
#   [−0,0033; −0,0006] (B katı −0,0027 [−0,0046; −0,0008]) → harman kapısını geçti: model.HARMAN_KALINTI (yalnız p_harman
#   ayrı kalıntı GBM'le; sabah olasılığı aynen). Yayına girişi gece kapısının harman dalı (gece.kapi_karari) ortak sınama
#   koşularında yeniden ölçerek verir. e5 1,8478 / 1,7891 elendi.
# Çıktı: data/at/deneyler_v7.json (yalnız türetilmiş metrikler).
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney7.py [--hizli]
import json, math, os, sys, time
from collections import defaultdict

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import veri, ozellik as O, model as M  # noqa: E402
from deney4 import Masa, gecer, KATLAR, bootstrap  # noqa: E402
from deney5 import gecer_harman  # noqa: E402

CIKTI = os.path.join(BURA, "..", "..", "data", "at", "deneyler_v7.json")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- ölçüm
def olc(p, K, sec=None):
    """n, log-loss, Brier, ilk-1, ilk-3 (koşu düzeyinde). sec: koşu maskesi."""
    R = np.arange(K.R) if sec is None else np.flatnonzero(sec)
    ll, br, i1, i3 = [], [], [], []
    for r in R:
        a, b = K.bas[r], K.bas[r] + K.n[r]
        pr, y, s = p[a:b], K.y[a:b], K.sira[a:b]
        ll.append(-math.log(max(float(pr[y > 0][0]), 1e-12)))
        br.append(float(((pr - y) ** 2).sum()))
        j = int(np.argmax(pr))
        i1.append(float(y[j] > 0)); i3.append(float(1 <= s[j] <= 3))
    f = lambda v: round(float(np.mean(v)), 4)
    return {"n": len(R), "log_loss": f(ll), "brier": f(br), "ilk1": f(i1), "ilk3": f(i3)}


def tablo_olc(masa, pm, ph):
    out = {}
    for kt in KATLAR:
        m = masa.kat_r == kt
        out[kt] = {"model": olc(pm, masa.Ks, m), "harman": olc(ph, masa.Ks, m), "piyasa": olc(masa.Ks.q, masa.Ks, m)}
    return out


# ---------------------------------------------------------------- dönemli walk-forward
def _hafta(g):
    from datetime import date
    return g - date.fromordinal(int(g)).weekday()   # pazartesi


def ham_puan(ham, KK, sut):
    X = KK.X[:, sut]
    s = ((X - ham["mu"]) / ham["sd"]) @ ham["w"]
    g = ham["booster"].predict(X, raw_score=True) if ham["booster"] is not None else None
    return s, g


def donemli(masa, E, kal_donem="hafta", ham_donem=None, sut=None):
    """E: masa.egit çıktısı (aylık hamlar). kal_donem: 'hafta' | 'gun' — kalibrasyon/harman katmanı her dönem başında
    son KAL_GUN günle yeniden öğrenilir. ham_donem='hafta': ham katman da haftalık yeniden eğitilir (E kullanılmaz)."""
    Ks = masa.Ks
    sut = E["sut"] if sut is None else sut
    g_satir = masa.gunler[Ks.kosu_no]
    pm = np.zeros(len(Ks.y)); ph = np.zeros(len(Ks.y))
    anahtar = (lambda g: _hafta(g)) if kal_donem == "hafta" else (lambda g: g)
    hamlar = {}
    if ham_donem == "hafta":
        for w in sorted({_hafta(g) for g in g_satir}):
            kb = w - M.KAL_GUN
            Kf = M._ozel(masa.K, (masa.idx >= masa.ilk) & (masa.gunler < kb))
            Kh = M._ozel(masa.K, (masa.gunler >= kb) & (masa.gunler < w) & masa.tam)
            ag = 0.5 ** ((kb - masa.gunler[Kf.kosu_no[Kf.bas]]) / M.YARI_OMUR)
            hamlar[w] = M.egit_ham(Kf, Kh, sut, None, ag, True)
        log(f"  haftalık ham: {len(hamlar)} hafta")
    kk = np.array([anahtar(g) for g in g_satir]) if kal_donem == "hafta" else g_satir
    for d in E["aylar"]:
        satir_ay = d["satir"]
        ay0 = M._gun(d["ay"] + "-01")
        for k in sorted(set(kk[satir_ay].tolist())):
            satir = satir_ay & (kk == k)
            if not satir.any():
                continue
            g0 = max(int(k), ay0)   # ayı kesen hafta: pencere ayın hamının eğitim sınırıyla çakışmasın
            kb = g0 - M.KAL_GUN
            Kh = M._ozel(masa.K, (masa.gunler >= kb) & (masa.gunler < g0) & masa.tam)
            ham = hamlar.get(_hafta(g0)) if hamlar else d["ham"]
            s_h, g_h = ham_puan(ham, Kh, sut)
            m = M.egit_kal(ham, Kh, masa.T["adlar"], sut, s=s_h, g=g_h, henery=False, kal_ayar=M.KAL_AYAR)
            Ka = Ks.alt(satir)
            s_a, g_a = ham_puan(ham, Ka, sut)
            sb = m.cl * s_a + (m.cg * g_a if g_a is not None and m.cg else 0.0)
            p = M.kal_uygula(m.kal, sb, Ka)
            pm[satir] = p
            ph[satir] = M.softmax_kosu(m.alfa * np.log(np.clip(p, 1e-12, 1)) + m.beta * np.log(np.clip(Ka.q, 1e-9, 1)), Ka)
    return pm, ph


# ---------------------------------------------------------------- gün içi katman
def gun_ici_ozellik(masa, p, kosu_satir):
    """Satır başına gün içi özellikler (yalnız AYNI GÜN, AYNI hipodromda DAHA ÖNCE biten koşulardan; koşu no sırası):
    f1 = jokeyin bugünkü önceki binişlerinde Σ(y − p)  (p: o koşudaki yalnız-model olasılığı — piyasa değil)
    f2 = antrenörün aynı kalıntısı
    f3 = hipodromun bugünkü önceki koşularında 'model favorisi kazandı mı' kalıntısı Σ(1[fav kazandı] − p_fav) × (bu at
         koşunun model favorisi mi)
    f4 = bugünkü önceki koşu sayısı (log1p) × log p  (gün ilerledikçe modele güven ölçeği)
    p ve kosu_satir masa.K (tüm tablo) dizinlerinde. Döner: (N_satir, 4)."""
    K, kos = masa.K, masa.kosular
    F = np.zeros((len(K.y), 4))
    gun_hip = defaultdict(list)
    for r in range(K.R):
        ko = kos[K.kosu_no[K.bas[r]]]
        gun_hip[(ko["tarih"], ko["hipodrom"])].append(r)
    for (_, _), rs in gun_hip.items():
        rs = sorted(rs, key=lambda r: kos[K.kosu_no[K.bas[r]]]["kosu"])
        jk, an = defaultdict(float), defaultdict(float)
        fav_k, onceki = 0.0, 0
        for r in rs:
            a, b = K.bas[r], K.bas[r] + K.n[r]
            ko = kos[K.kosu_no[a]]
            if not kosu_satir[a]:   # p bilinmiyor (sınama dışı) — yine de durumu ilerletme: p yok, atla
                continue
            pr = p[a:b]
            j = int(np.argmax(pr))
            for i, at in enumerate(ko["atlar"]):
                F[a + i, 0] = jk.get(at["jokey"], 0.0)
                F[a + i, 1] = an.get(at["antrenor"], 0.0)
                F[a + i, 2] = fav_k if i == j else 0.0
                F[a + i, 3] = math.log1p(onceki) * math.log(max(pr[i], 1e-9))
            y = K.y[a:b]
            for i, at in enumerate(ko["atlar"]):
                jk[at["jokey"]] += y[i] - pr[i]
                an[at["antrenor"]] += y[i] - pr[i]
            fav_k += float(y[j] > 0) - pr[j]
            onceki += 1
    return F


def e3(masa, E, pm_tum_K, bilinen):
    """Gün içi katman: s = log p_model + θ·F; harman: α log p' + β log q. θ, α, β ayın öncesindeki 90 günde öğrenilir."""
    Ks = masa.Ks
    F = gun_ici_ozellik(masa, pm_tum_K, bilinen)
    pm = np.zeros(len(Ks.y)); ph = np.zeros(len(Ks.y))
    rows_s = Ks_rows(masa)
    thetas = []
    for d in E["aylar"]:
        g0 = M._gun(d["ay"] + "-01"); kb = g0 - M.KAL_GUN
        mk = (masa.gunler >= kb) & (masa.gunler < g0) & masa.tam
        satir_h = mk[masa.K.seg] & bilinen
        rk = np.unique(masa.K.seg[satir_h])
        tam_kosu = np.zeros(masa.K.R, bool); tam_kosu[rk] = True
        # yalnız tüm satırları bilinen koşular
        bil_k = np.add.reduceat(bilinen.astype(int), masa.K.bas) == masa.K.n
        tam_kosu &= bil_k
        sh = tam_kosu[masa.K.seg]
        Kh = masa.K.alt(sh)
        lp = np.log(np.clip(pm_tum_K[sh], 1e-12, 1))
        Xh = np.c_[lp, F[sh]]
        th = M.clogit(Xh, Kh, 1.0)
        p1 = M.softmax_kosu(Xh @ th, Kh)
        ab = M.clogit(np.c_[np.log(np.clip(p1, 1e-12, 1)), np.log(np.clip(Kh.q, 1e-9, 1))], Kh, 1e-6)
        thetas.append([round(float(x), 4) for x in th])
        Ka = Ks.alt(d["satir"])
        ix = rows_s[d["satir"]]
        Xa = np.c_[np.log(np.clip(pm_tum_K[ix], 1e-12, 1)), F[ix]]
        p = M.softmax_kosu(Xa @ th, Ka)
        pm[d["satir"]] = p
        ph[d["satir"]] = M.softmax_kosu(ab[0] * np.log(np.clip(p, 1e-12, 1)) + ab[1] * np.log(np.clip(Ka.q, 1e-9, 1)), Ka)
    return pm, ph, thetas


def Ks_rows(masa):
    """masa.Ks satırlarının masa.K'deki dizinleri."""
    m = masa.B["sinama_katli"][masa.K.seg]
    return np.flatnonzero(m)


def oos_tum(masa, E):
    """Gün içi katmanın eğitimi için tüm tablo satırlarında örneklem-dışı yalnız-model p: her ay için o ayın hamı +
    kalibrasyonu; kat öncesi 90 gün + sınama aylarını kapsar (her satır yalnız kendi ayından ÖNCEKİ verilerle eğitilmiş
    modelle). Kat öncesi dönem için ilk sınama ayının modelinden 3 ay geriye ayrı aylık modeller eğitilir."""
    K = masa.K
    p = np.zeros(len(K.y)); bilinen = np.zeros(len(K.y), bool)
    from datetime import date
    ilk_ay = E["aylar"][0]["ay"]
    y0, a0 = int(ilk_ay[:4]), int(ilk_ay[5:7])
    once = []
    for k in (3, 2, 1):
        a = a0 - k; y = y0
        while a <= 0:
            a += 12; y -= 1
        once.append(f"{y}-{a:02d}")
    ay_satir = np.array([masa.tarih[i][:7] for i in K.kosu_no])
    for ay in once + [d["ay"] for d in E["aylar"]]:
        g0 = M._gun(ay + "-01"); kb = g0 - M.KAL_GUN
        d = next((x for x in E["aylar"] if x["ay"] == ay), None)
        if d is None:
            Kf = M._ozel(K, (masa.idx >= masa.ilk) & (masa.gunler < kb))
            Kh = M._ozel(K, (masa.gunler >= kb) & (masa.gunler < g0) & masa.tam)
            ag = 0.5 ** ((kb - masa.gunler[Kf.kosu_no[Kf.bas]]) / M.YARI_OMUR)
            ham = M.egit_ham(Kf, Kh, E["sut"], None, ag, True)
        else:
            ham = d["ham"]
            Kh = d["Kh"]
        s_h, g_h = ham_puan(ham, Kh, E["sut"])
        m = M.egit_kal(ham, Kh, masa.T["adlar"], E["sut"], s=s_h, g=g_h, henery=False, kal_ayar=M.KAL_AYAR)
        satir = (ay_satir == ay)
        if not satir.any():
            continue
        Ka = K.alt(satir)
        s_a, g_a = ham_puan(ham, Ka, E["sut"])
        sb = m.cl * s_a + (m.cg * g_a if g_a is not None and m.cg else 0.0)
        p[satir] = M.kal_uygula(m.kal, sb, Ka)
        bilinen |= satir
    return p, bilinen


# ---------------------------------------------------------------- e5: alan içi göreli özellikler
E5_TABAN = ["r_at", "piyasa_reyting", "pz_ewma", "hz_en_iyi3", "hz_ort3", "jk_j", "jk_logp", "a5_sr_ort5", "skor5",
            "geri_en_iyi5", "a6_k_m", "n_kosu"]


def alan_ici(T):
    """Koşu içi z (alan ortalama/sapmasına göre) ve sıra yüzdeliği (0 = alanın en düşüğü, 1 = en yükseği).
    Yalnız aynı koşunun koşu öncesi özelliklerinden; sızıntı yok."""
    K = M.kume_kur(T)
    ix = [T["adlar"].index(a) for a in E5_TABAN]
    X = T["X"][:, ix]
    n = K.n[K.seg][:, None]
    mu = (np.add.reduceat(X, K.bas) / K.n[:, None])[K.seg]
    sd = np.sqrt((np.add.reduceat((X - mu) ** 2, K.bas) / K.n[:, None]))[K.seg]
    Z = np.where(sd > 1e-9, (X - mu) / np.maximum(sd, 1e-9), 0.0)
    Rk = np.zeros_like(X)
    for r in range(K.R):
        a, b = K.bas[r], K.bas[r] + K.n[r]
        if b - a < 2:
            continue
        x = X[a:b]   # ortalama sıra (eşitler aynı değeri alır): satır sırası bitiş sırasıdır, kararlı sıralama SIZDIRIR
        alt = (x[:, None, :] > x[None, :, :]).sum(1) + 0.5 * ((x[:, None, :] == x[None, :, :]).sum(1) - 1)
        Rk[a:b] = alt / (b - a - 1)
    T2 = dict(T)
    T2["X"] = np.hstack([T["X"], Z, Rk])
    T2["adlar"] = list(T["adlar"]) + [f"e5_z_{a}" for a in E5_TABAN] + [f"e5_r_{a}" for a in E5_TABAN]
    return T2


# ---------------------------------------------------------------- ana akış
def main():
    t0 = time.time()
    import at6
    at6.hava_hazirla()
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    log("tablo", T["X"].shape, f"{time.time() - t0:.0f} sn")
    masa = Masa(kosular, T)
    log("aylar:", masa.aylar, {k: int((masa.kat_r == k).sum()) for k in KATLAR})
    kayit = {"olusturma": None, "katlar": masa.B["tarih"]["katlar"], "kapi": "deney4 iki katlı kapı (e3: harman kapısı da)",
             "adimlar": []}

    def kaydet():
        kayit["olusturma"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        json.dump(kayit, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    sadece = [a[2:] for a in sys.argv if a.startswith("--e")]   # ör. --e4: yalnız taban + e4 (önceki kayda eklenir)
    if sadece:
        try:
            eski = json.load(open(CIKTI, encoding="utf-8"))
            kayit["adimlar"] = [a for a in eski.get("adimlar", []) if not a["deney"].startswith("taban")
                               and not any(a["deney"].startswith(m) for m in sadece)]
        except (OSError, ValueError):
            pass
    E = masa.egit(list(O.ADLAR))
    pm0, ph0, _ = masa.tahmin(E, M.KAL_AYAR)
    cur, v0 = masa.ozet(pm0, ph0)
    kayit["adimlar"].append({"deney": "taban (yayındaki tarif, aylık ham + aylık kalibrasyon)", "gecti": None,
                             "olcu": tablo_olc(masa, pm0, ph0), "ozet": {a: cur[a] for a in ("model", "harman", "piyasa")}})
    log("taban", cur["model"], cur["harman"], f"{time.time() - t0:.0f} sn"); kaydet()

    def adim(ad_, pm, ph, harman_kapisi=False, ek=None):
        r, v = masa.ozet(pm, ph)
        g = gecer(r, cur)
        gh = gecer_harman(r, cur) if harman_kapisi else None
        kayit["adimlar"].append({"deney": ad_, "gecti": bool(g), "gecti_harman": gh, "olcu": tablo_olc(masa, pm, ph),
                                 "ozet": {a: r[a] for a in ("model", "harman")},
                                 "fark_model": masa.fark(v, v0, "model"), "fark_harman": masa.fark(v, v0, "harman"), **(ek or {})})
        log(ad_, "geçti" if g else "elendi", "| harman kapısı:", gh, r["model"], r["harman"], f"{time.time() - t0:.0f} sn")
        kaydet()
        return g, gh

    if "e4" in sadece:
        M.GBM_INIT_DOGRUSAL = True
        E4 = masa.egit(list(O.ADLAR))
        M.GBM_INIT_DOGRUSAL = False
        pm, ph, _ = masa.tahmin(E4, M.KAL_AYAR)
        g, gh = adim("e4_gbm_kalinti: GBM doğrusal puandan başlar (init_score), ağaçlar kalıntıyı öğrenir; yığma aynı", pm, ph, True)
        if g:
            pm, ph = donemli(masa, E4, "gun")
            adim("e4 + e1_gun_kal: kalıntı GBM + günlük kalibrasyon", pm, ph, True)
    if "e5" in sadece:
        T2 = alan_ici(T)
        masa2 = Masa(kosular, T2)
        E5 = masa2.egit(list(O.ADLAR) + T2["adlar"][len(T["adlar"]):])
        pm, ph, _ = masa2.tahmin(E5, M.KAL_AYAR)
        g, gh = adim("e5_alan_ici: 12 temel özelliğin koşu içi z ve sıra yüzdeliği (doğrusal + GBM)", pm, ph, True)
    if sadece:
        kayit["sure_sn"] = round(time.time() - t0); kaydet(); log("bitti"); return
    pm, ph = donemli(masa, E, "hafta"); adim("e1_hafta_kal: kalibrasyon/harman haftalık (ham aylık)", pm, ph, True)
    pm, ph = donemli(masa, E, "gun"); adim("e1_gun_kal: kalibrasyon/harman her yarış günü (ham aylık)", pm, ph, True)
    # e3: gün içi katman (yalnız-model ve harman ölçülür; yayında yalnız canlı tarafta kullanılabilir)
    pK, bil = oos_tum(masa, E)
    pm, ph, th = e3(masa, E, pK, bil)
    adim("e3_gun_ici: aynı gün önceki koşulardan jokey/antrenör kalıntısı + favori sapması (canlı katman)", pm, ph, True,
         {"theta_ay": th, "theta_adlar": ["log p", "jokey_bugun", "antrenor_bugun", "fav_bugun", "onceki×log p"]})
    if "--hizli" not in sys.argv:
        pm, ph = donemli(masa, E, "hafta", ham_donem="hafta")
        adim("e2_hafta_ham: ham + kalibrasyon haftalık yeniden eğitim", pm, ph, True)
    kayit["sure_sn"] = round(time.time() - t0)
    kaydet()
    log("bitti")


if __name__ == "__main__":
    main()
