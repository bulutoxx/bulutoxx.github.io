# OXXai at yarışı laboratuvarı — KÜRESEL deney masası (elle çalıştırılır; gece akışının parçası değil).
# Kalıp: lab/at/deney5.py. Kapı: lab/at/deney4.py iki katlı kapı (Masa, gecer) aynen:
#   özellik/amaç adımları: katların ORTALAMA yalnız-model log-loss'u düşmeli (> 0,0001), ortalama ilk-seçim isabeti
#   düşmemeli, en güncel kat (B) kötüleşmemeli, harman 0,001'den fazla bozulmamalı.
#   harman adımı (gl_piyasa): harman ort. LL düşmeli (> 0,0001), harman ilk seçimi düşmemeli, B harman LL kötüleşmemeli.
# Taban: yayındaki tarif (v4 + jk_uzman, jk_apr, jk_beceri + a5_sinif = ozellik.SECILI_GRUPLAR).
# Adaylar (lab/at/global/kuresel.py): gl_piyasa (Shin / odds-ratio; yöntem sınama ÖNCESİ dönemde seçilir),
#   gl_flb (Benter 2. aşamasına kayırma–uzun atış eğriliği: harmanda (log q)² terimi), gl_wfa (ARCI yaşa göre kilo
#   önseli), gl_lambdarank (GBM amacı LambdaMART) + gl_harville denetimi (indirimli Harville γ/δ öğrenimi; 2./3. sıra LL,
#   kazanan LL'sini değiştirmez → ayrı kapı: iki katta da Harville'den (γ=δ=1) iyi olmalı).
# Çıktı: lab/at/global/deneyler_global.json (yalnız türetilmiş metrikler) + lab/at/global/oncul.json (GLOBAL_SECILI).
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney_global.py
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney_global.py --sizinti
import json, os, sys, time

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
GL = os.path.join(BURA, "global")
sys.path.insert(0, BURA)
sys.path.insert(0, GL)
import veri, ozellik as O, model as M  # noqa: E402
import kuresel as G  # noqa: E402
from deney4 import Masa, gecer, KATLAR  # noqa: E402
from deney_jokey import _kisalt  # noqa: E402
from deney5 import gecer_harman  # noqa: E402

CIKTI = os.path.join(GL, "deneyler_global.json")
ONCUL = os.path.join(GL, "oncul.json")
ADLAR = {
    "gl_piyasa": "piyasa olasılığında kayırma–uzun atış düzeltmesi (Shin / odds-ratio) — harmanda log q yerine",
    "gl_wfa": "yaşa göre kilo önseli (ARCI-010-020 WFA tablosu): WFA avantajı, etkin kilo, WFA × log mesafe",
    "gl_lambdarank": "GBM amacı LambdaMART (lambdarank, ilk 3 etiketi) — koşu-içi softmax yerine",
    "gl_flb": "Benter 2. aşaması + kayırma–uzun atış eğriliği: harman = α log p + β log q + κ (log q)²",
    "gl_harville": "indirimli Harville (Lo–Bacon-Shone): 2./3. sıra üsleri γ, δ kalibrasyon penceresinde öğrenilir",
}
LBS = (0.81, 0.65)   # Lo, Bacon-Shone & Busche (1995) Hong Kong tahmini (yaklaşık) — sabit literatür üssü karşılaştırması


def kaydet(yol, d):
    d["olusturma"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    tmp = yol + ".tmp"
    json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, yol)


def tablo(kosular):
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    if all(a in T["adlar"] for a in G.GL_WFA_ADLAR):   # ozellik.py gl_* sütunlarını zaten üretiyor (bağlandıktan sonra)
        return T
    W = G.wfa_tablosu(kosular)
    assert len(W) == len(T["X"])
    T["X"] = np.hstack([T["X"], W])
    T["adlar"] = list(T["adlar"]) + G.GL_WFA_ADLAR
    return T


def piyasa_sec(kosular, masa):
    """Yöntemi yalnız sınama katlarından ÖNCEKİ tam oranlı koşularda (ısınma sonrası) seçer."""
    kat_bas = masa.B["tarih"]["katlar"]["A"][0]
    sec = {}
    for y in G.PIYASA_YONTEM:
        ll, n = 0.0, 0
        for k in kosular:
            if not (M.ISINMA_SONU <= k["tarih"] < kat_bas):
                continue
            q = G.piyasa_q([a["oran"] for a in k["atlar"]], y)
            if not q:
                continue
            w = [i for i, a in enumerate(k["atlar"]) if a["sira"] == 1][0]
            ll += -np.log(max(q[w], 1e-12)); n += 1
        sec[y] = round(ll / n, 5)
    return sec


def harman_genel(masa, E, kal, q_alt=None, flb=False):
    """Yalnız-model aynı; harman katsayıları kalibrasyon penceresinde yeniden öğrenilir.
    q_alt: alternatif piyasa olasılığı (gl_piyasa); flb: (log q)² terimi (gl_flb, Benter 2. aşaması + FLB eğriliği)."""
    m2 = Masa(masa.kosular, dict(masa.T, q=q_alt)) if q_alt is not None else masa
    pm, _, modeller = masa.tahmin(E, kal)
    ph = np.zeros(len(m2.Ks.y))
    kats = []
    for d, m in zip(E["aylar"], modeller):
        g0 = M._gun(d["ay"] + "-01"); kb = g0 - M.KAL_GUN
        Kh = M._ozel(m2.K, (m2.gunler >= kb) & (m2.gunler < g0) & m2.tam)
        Ka = m2.Ks.alt(d["satir"])
        sbh = m.cl * d["s_h"] + (m.cg * d["g_h"] if d["g_h"] is not None and m.cg else 0.0)
        pkh = M.kal_uygula(m.kal, sbh, Kh)

        def oz(p, q):
            lq = np.log(np.clip(q, 1e-9, 1))
            return np.c_[np.log(np.clip(p, 1e-12, 1)), lq] if not flb else np.c_[np.log(np.clip(p, 1e-12, 1)), lq, lq * lq]
        ab = M.clogit(oz(pkh, Kh.q), Kh, 1e-6)
        kats.append([round(float(x), 4) for x in ab])
        ph[d["satir"]] = M.softmax_kosu(oz(pm[d["satir"]], Ka.q) @ np.asarray(ab), Ka)
    return pm, ph, m2, kats


def harman_q(masa, E, kal, q_alt):
    pm, ph, m2, _ = harman_genel(masa, E, kal, q_alt)
    return pm, ph, m2


def _sira_ll(p, K, gam, dlt):
    """Koşu başına −log P(2. | 1.) − log P(3. | 1., 2.) (indirimli Harville: p^γ, p^δ). Tam ilk 3'ü olan koşular."""
    lp = np.log(np.clip(p, 1e-12, 1))
    out = np.full(K.R, np.nan)
    for r in range(K.R):
        a, b = K.bas[r], K.bas[r] + K.n[r]
        s = np.asarray(K.sira[a:b])
        if K.n[r] < 4 or any(np.sum(s == j) != 1 for j in (1, 2, 3)):
            continue
        t = 0.0
        for yer, u in ((2, gam), (3, dlt)):
            kalan = s >= yer
            v = u * lp[a:b]
            mx = v[kalan].max()
            t -= v[s == yer][0] - (mx + np.log(np.exp(v[kalan] - mx).sum()))
        out[r] = t
    return out


def harville_denetim(masa, E, kal):
    """gl_harville: aynı harman olasılığından 2./3. sıra LL'si — Harville (1,1) vs öğrenilen (γ,δ) vs LBS sabiti."""
    pm, ph, modeller = masa.tahmin(E, kal)
    Ks = masa.Ks
    v = {"harville": [], "ogrenilen": [], "lbs": []}
    kat = []
    gd = []
    for d, m in zip(E["aylar"], modeller):
        Kh = d["Kh"]
        sbh = m.cl * d["s_h"] + (m.cg * d["g_h"] if d["g_h"] is not None and m.cg else 0.0)
        pkh = M.kal_uygula(m.kal, sbh, Kh)
        phh = M.softmax_kosu(m.alfa * np.log(np.clip(pkh, 1e-12, 1)) + m.beta * np.log(np.clip(Kh.q, 1e-9, 1)), Kh)
        g, dl = M.henery_ussu(phh, Kh, 2), M.henery_ussu(phh, Kh, 3)   # yalnız kalibrasyon penceresinden
        gd.append([d["ay"], round(float(g), 2), round(float(dl), 2)])
        Ka = d["Ka"]
        p = ph[d["satir"]]
        v["harville"].append(_sira_ll(p, Ka, 1.0, 1.0))
        v["ogrenilen"].append(_sira_ll(p, Ka, g, dl))
        v["lbs"].append(_sira_ll(p, Ka, *LBS))
        rr = np.unique(Ks.seg[d["satir"]])          # bu ayın koşuları (Ks koşu sırası = Ka koşu sırası)
        assert len(rr) == Ka.R
        kat.append(np.asarray(masa.kat_r)[rr])
    for a in v:
        v[a] = np.concatenate(v[a])
    ok_mask = ~np.isnan(v["harville"])
    kr = np.concatenate(kat)
    from deney4 import bootstrap
    sonuc = {"gamma_delta_ay": gd, "kosu": int(ok_mask.sum())}
    for a in ("ogrenilen", "lbs"):
        dd = v[a] - v["harville"]
        sonuc[a] = {"dll": round(float(np.nanmean(dd)), 4), "ga95": bootstrap(dd[ok_mask]),
                    **{kt: round(float(np.nanmean(dd[ok_mask & (kr == kt)])), 4) for kt in KATLAR}}
    sonuc["harville_ll"] = round(float(np.nanmean(v["harville"])), 4)
    sonuc["gecti"] = bool(all(sonuc["ogrenilen"][kt] < -1e-4 for kt in KATLAR))
    return sonuc


def main():
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T = tablo(kosular)
    print(f"tablo {T['X'].shape} {time.time() - t0:.0f} sn", flush=True)
    masa = Masa(kosular, T)
    adla = lambda gr: list(dict.fromkeys([a for a, g in O.TUM_OZELLIKLER if g in gr] + (G.GL_WFA_ADLAR if "gl_wfa" in gr else [])))
    gr = list(O.SECILI_GRUPLAR)
    egitim = {"yari_omur": None, "gbm_ayar": None, "patlat_ag": tuple(M.PATLAT), "tohumlar": tuple(M.GBM_TOHUM),
              "patlat_gbm": M.PATLAT_GBM}
    kal = dict(M.KAL_AYAR)
    E = masa.egit(adla(gr), **egitim)
    cur, v_cur = masa.ozet(*masa.tahmin(E, kal)[:2])
    v_taban = v_cur
    cur_E = E
    kayit = {"olusturma": None, "katlar": masa.B["tarih"]["katlar"], "kapi": "deney4 iki katlı kapı (gl_piyasa: harman kapısı)",
             "taban_gruplar": list(gr),
             "adimlar": [{"no": 0, "deney": "taban (yayındaki tarif: v4 + jk + a5_sinif)", "gecti": None, **_kisalt(cur)}]}
    print(0, cur["model"], cur["harman"], cur["piyasa"], f"{time.time() - t0:.0f} sn", flush=True)
    kaydet(CIKTI, kayit)
    no = [0]
    secili = {"gruplar": [], "piyasa": "orantili", "gbm_amac": "softmax", "flb": False}
    q_aktif = [None]
    flb_aktif = [False]

    def adim(ad, r, v, harman=False, ek=None):
        nonlocal cur, v_cur
        no[0] += 1
        fm = masa.fark(v, v_cur, "model"); fh = masa.fark(v, v_cur, "harman")
        ok = gecer_harman(r, cur) if harman else gecer(r, cur)
        kayit["adimlar"].append({"no": no[0], "deney": ad, "gecti": ok, "fark_model": fm, "fark_harman": fh,
                                 **_kisalt(r), **(ek or {})})
        print(no[0], ad[:60], "GEÇTİ" if ok else "kaldı", r["model"], r["harman"], "ΔLL", fm["dll"], fm["ga95"],
              "A", fm["A"]["dll"], "B", fm["B"]["dll"], "harman ΔLL", fh["dll"], fh["ga95"], f"{time.time() - t0:.0f} sn",
              flush=True)
        if ok:
            cur, v_cur = r, v
        kaydet(CIKTI, kayit)
        return ok, (fh if harman else fm)["dll"]

    def ozet_q(E2):
        if q_aktif[0] is None and not flb_aktif[0]:
            return masa.ozet(*masa.tahmin(E2, kal)[:2])
        pm, ph, m2, _ = harman_genel(masa, E2, kal, q_aktif[0], flb_aktif[0])
        r, v = masa.ozet(pm, ph)
        return r, v

    # 1) gl_piyasa — yöntem sınama öncesi dönemde seçilir, harman kapısıyla sınanır
    sec = piyasa_sec(kosular, masa)
    yontem = min((y for y in sec if y != "orantili"), key=lambda y: sec[y])
    print("piyasa yöntem seçimi (sınama öncesi piyasa LL):", sec, "→", yontem, flush=True)
    q_alt = G.q_tablosu(kosular, yontem)
    pm, ph, m2 = harman_q(masa, cur_E, kal, q_alt)
    r, v = masa.ozet(pm, ph)
    _, v_p2 = m2.ozet(pm, ph)
    piy = {"piyasa_alt_ll": round(float(v_p2["piyasa"][0].mean()), 4), "piyasa_orantili_ll": cur["piyasa"]["ll"],
           "secim_donemi_ll": sec, "yontem": yontem}
    ok, _ = adim(f"gl_piyasa ({yontem}) — {ADLAR['gl_piyasa']}", r, v, harman=True, ek={"piyasa": piy})
    if ok:
        secili["piyasa"] = yontem; q_aktif[0] = q_alt

    # 1b) gl_flb — Benter 2. aşamasına (log q)² eğriliği (harman kapısı)
    pm, ph, _, kats = harman_genel(masa, cur_E, kal, q_aktif[0], flb=True)
    r, v = masa.ozet(pm, ph)
    kappa = [k[2] for k in kats]
    ok, _ = adim(f"gl_flb — {ADLAR['gl_flb']}", r, v, harman=True,
                 ek={"flb": {"kappa_ort": round(float(np.mean(kappa)), 4), "kappa_aylik": kappa}})
    if ok:
        secili["flb"] = True; flb_aktif[0] = True

    # 2) gl_wfa, 3) gl_lambdarank
    yakin = []

    def dene_wfa(ad):
        nonlocal cur_E, gr
        E2 = masa.egit(adla(gr + ["gl_wfa"]), **egitim)
        r, v = ozet_q(E2)
        ok, d = adim(ad, r, v)
        if ok:
            cur_E = E2; gr = gr + ["gl_wfa"]; secili["gruplar"].append("gl_wfa")
        return ok, d

    def dene_lr(ad):
        nonlocal cur_E
        eski = M.gbm_egit
        M.gbm_egit = G.gbm_egit_lambdarank(M, M.lgb)
        try:
            E2 = masa.egit(adla(gr), **egitim)
        finally:
            M.gbm_egit = eski
        r, v = ozet_q(E2)
        ok, d = adim(ad, r, v)
        if ok:
            cur_E = E2; secili["gbm_amac"] = "lambdarank"
        return ok, d

    for ad, f in (("gl_wfa", dene_wfa), ("gl_lambdarank", dene_lr)):
        if ad == "gl_wfa" and "gl_wfa" in gr:   # yayında (taban zaten içeriyor)
            secili["gruplar"].append("gl_wfa"); continue
        ok, d = f(f"{ad} — {ADLAR[ad]}")
        if not ok and d < 0:
            yakin.append((ad, f))
    for ad, f in yakin:
        if (ad == "gl_wfa" and "gl_wfa" in secili["gruplar"]) or (ad == "gl_lambdarank" and secili["gbm_amac"] != "softmax"):
            continue
        if not any(s["gecti"] for s in kayit["adimlar"][1:]):
            break   # taban değişmediyse tekrar anlamsız (aynı sonuç)
        f(f"yeniden (yeni tabanda): {ad} — {ADLAR[ad]}")

    # 4) gl_harville denetimi (kazanan LL'sini değiştirmez; ayrı kapı)
    th = time.time()
    hv = harville_denetim(masa, cur_E, kal)
    hv["sure_sn"] = round(time.time() - th)
    kayit["harville"] = hv
    print("gl_harville:", hv, flush=True)
    secili["harville"] = "ogrenilen" if hv["gecti"] else "harville"

    kayit["secim"] = secili
    kayit["toplam"] = {"model": masa.fark(v_cur, v_taban, "model"), "harman": masa.fark(v_cur, v_taban, "harman")}
    kayit["sure_sn"] = round(time.time() - t0)
    kaydet(CIKTI, kayit)
    GLOBAL_SECILI = (["gl_piyasa:" + secili["piyasa"]] if secili["piyasa"] != "orantili" else []) + \
                    (["gl_flb"] if secili["flb"] else []) + secili["gruplar"] + \
                    (["gl_lambdarank"] if secili["gbm_amac"] == "lambdarank" else [])
    kaydet(ONCUL, {"GLOBAL_SECILI": GLOBAL_SECILI, "secim": secili, "piyasa_secim_donemi_ll": sec,
                   "wfa_kaynak": "ARCI-010-020 Section D Table 1 (Scale of Weights for Age)",
                   "deney": "lab/at/global/deneyler_global.json"})
    print("bitti, GLOBAL_SECILI:", GLOBAL_SECILI, f"{time.time() - t0:.0f} sn")


def sizinti():
    """gl_wfa için sızıntı testi (deney5 --sizinti kalıbı): (1) kesme: D gününün satırları tam tablodakiyle aynı;
    (2) D'nin sonuçları (sıra, derece, oran) karıştırılınca değişmiyor; (3) gün içi koşu sırası ters çevrilince aynı."""
    import random
    kosular, _ = veri.sonuclari_yukle()
    W = G.wfa_tablosu(kosular)
    gunler = sorted({k["tarih"] for k in kosular})
    rng = np.random.default_rng(13)
    hata = []
    for D in sorted(rng.choice(gunler[60:], size=6, replace=False)):
        once = [k for k in kosular if k["tarih"] < D]
        bugun = [k for k in kosular if k["tarih"] == D]
        Xd = G.wfa_tablosu(bugun)
        bas = sum(len(k["atlar"]) for k in once)
        ok1 = np.allclose(Xd, W[bas: bas + len(Xd)], atol=1e-12)
        karisik = json.loads(json.dumps(bugun))
        for k in karisik:
            s = [a["sira"] for a in k["atlar"]]; random.Random(1).shuffle(s)
            o = [a["oran"] for a in k["atlar"]]; random.Random(2).shuffle(o)
            for a, x, y in zip(k["atlar"], s, o):
                a["sira"], a["oran"], a["sure"] = x, y, None
        ok2 = np.allclose(Xd, G.wfa_tablosu(karisik), atol=1e-12)
        ok3 = np.allclose(Xd, np.vstack(list(reversed([G.wfa_satirlar(k) for k in reversed(bugun)]))), atol=1e-12)
        dolu = float((np.abs(Xd) > 0).mean())
        print(f"{D}: {len(Xd)} satır · dolu %{100 * dolu:.0f} · kesme {'AYNI' if ok1 else 'FARKLI'} · sonuç karıştırma "
              f"{'AYNI' if ok2 else 'FARKLI'} · ters sıra {'AYNI' if ok3 else 'FARKLI'}", flush=True)
        if not (ok1 and ok2 and ok3):
            hata.append(D)
    if hata:
        print("SIZINTI ŞÜPHESİ:", hata)
        sys.exit(1)
    print("SIZINTI YOK (gl_wfa)")


if __name__ == "__main__":
    sizinti() if "--sizinti" in sys.argv else main()
