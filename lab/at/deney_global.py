# BULUTOXX at yarışı laboratuvarı — KÜRESEL deney masası (elle çalıştırılır; gece akışının parçası değil).
# Kalıp: lab/at/deney5.py. Kapı: lab/at/deney4.py iki katlı kapı (Masa, gecer) aynen:
#   özellik/amaç adımları: katların ORTALAMA yalnız-model log-loss'u düşmeli (> 0,0001), ortalama ilk-seçim isabeti
#   düşmemeli, en güncel kat (B) kötüleşmemeli, harman 0,001'den fazla bozulmamalı.
#   harman adımı (gl_piyasa): harman ort. LL düşmeli (> 0,0001), harman ilk seçimi düşmemeli, B harman LL kötüleşmemeli.
# Taban: yayındaki tarif (v4 + jk_uzman, jk_apr, jk_beceri + a5_sinif = ozellik.SECILI_GRUPLAR).
# Adaylar (lab/at/global/kuresel.py): gl_piyasa (Shin / odds-ratio; yöntem sınama ÖNCESİ dönemde seçilir),
#   gl_wfa (ARCI yaşa göre kilo önseli), gl_lambdarank (GBM amacı LambdaMART).
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
}


def kaydet(yol, d):
    d["olusturma"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    tmp = yol + ".tmp"
    json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, yol)


def tablo(kosular):
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
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


def harman_q(masa, E, kal, q_alt):
    """Yalnız-model aynı; harman α, β kalibrasyon penceresinde alternatif q ile yeniden öğrenilir."""
    T2 = dict(masa.T, q=q_alt)
    m2 = Masa(masa.kosular, T2)
    pm, _, modeller = masa.tahmin(E, kal)
    ph = np.zeros(len(m2.Ks.y))
    for d, m in zip(E["aylar"], modeller):
        g0 = M._gun(d["ay"] + "-01"); kb = g0 - M.KAL_GUN
        Kh = M._ozel(m2.K, (m2.gunler >= kb) & (m2.gunler < g0) & m2.tam)
        Ka = m2.Ks.alt(d["satir"])
        sbh = m.cl * d["s_h"] + (m.cg * d["g_h"] if d["g_h"] is not None and m.cg else 0.0)
        pkh = M.kal_uygula(m.kal, sbh, Kh)
        ab = M.clogit(np.c_[np.log(np.clip(pkh, 1e-12, 1)), np.log(np.clip(Kh.q, 1e-9, 1))], Kh, 1e-6)
        ph[d["satir"]] = M.softmax_kosu(ab[0] * np.log(np.clip(pm[d["satir"]], 1e-12, 1))
                                        + ab[1] * np.log(np.clip(Ka.q, 1e-9, 1)), Ka)
    return pm, ph, m2


def main():
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T = tablo(kosular)
    print(f"tablo {T['X'].shape} {time.time() - t0:.0f} sn", flush=True)
    masa = Masa(kosular, T)
    adla = lambda gr: [a for a, g in O.TUM_OZELLIKLER if g in gr] + (G.GL_WFA_ADLAR if "gl_wfa" in gr else [])
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
    secili = {"gruplar": [], "piyasa": "orantili", "gbm_amac": "softmax"}
    q_aktif = [None]

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
        if q_aktif[0] is None:
            return masa.ozet(*masa.tahmin(E2, kal)[:2])
        pm, ph, m2 = harman_q(masa, E2, kal, q_aktif[0])
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
        ok, d = f(f"{ad} — {ADLAR[ad]}")
        if not ok and d < 0:
            yakin.append((ad, f))
    for ad, f in yakin:
        if (ad == "gl_wfa" and "gl_wfa" in secili["gruplar"]) or (ad == "gl_lambdarank" and secili["gbm_amac"] != "softmax"):
            continue
        if not any(s["gecti"] for s in kayit["adimlar"][1:]):
            break   # taban değişmediyse tekrar anlamsız (aynı sonuç)
        f(f"yeniden (yeni tabanda): {ad} — {ADLAR[ad]}")

    kayit["secim"] = secili
    kayit["toplam"] = {"model": masa.fark(v_cur, v_taban, "model"), "harman": masa.fark(v_cur, v_taban, "harman")}
    kayit["sure_sn"] = round(time.time() - t0)
    kaydet(CIKTI, kayit)
    GLOBAL_SECILI = (["gl_piyasa:" + secili["piyasa"]] if secili["piyasa"] != "orantili" else []) + secili["gruplar"] + \
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
