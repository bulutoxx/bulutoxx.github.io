# BULUTOXX at yarışı laboratuvarı — v4 deney masası ("üst seviye" sabah modeli; elle çalıştırılır, gece akışının parçası değil).
#
# 0) SAĞLAM ÖLÇÜM: iki zaman katı (walk-forward, genişleyen eğitim, her ay yeniden eğitim):
#      A katı: 2025-11-01 → son %30'un başı (≈4,5 ay)      B katı: son %30 (≈7 ay, v3 sınamasıyla aynı koşular)
#    KAPI (yalnız-model, yani sabah tahmini): katların ORTALAMA log-loss'u düşmeli (> 0,0001), katların ortalama
#    ilk-seçim isabeti düşmemeli, en güncel kat (B) log-loss'u kötüleşmemeli ve harman ortalaması 0,001'den fazla
#    bozulmamalı. Kalibrasyon adımlarında (sıralamayı değiştirmeyen dönüşümler) ölçüt: log-loss kötüleşmemeli.
#    Her adım için önceki kabule göre koşu başına eşleştirilmiş ΔLL ve koşu-bootstrap %95 GA (birleşik + kat kat).
# Pahalı eğitim katmanı (doğrusal + GBM) ay başına bir kez hesaplanır; kalibrasyon deneyleri aynı ham puanları kullanır.
# Çıktı: data/at/deneyler_v4.json (yalnız türetilmiş metrikler).
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney4.py
import json, math, os, sys, time

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import veri, ozellik as O, model as M  # noqa: E402

B_SAYI = 2000
CIKTI = os.path.join(BURA, "..", "..", "data", "at", "deneyler_v4.json")
KATLAR = ("A", "B")


def bootstrap(d, n=B_SAYI, tohum=7):
    r = np.random.default_rng(tohum)
    idx = r.integers(0, len(d), size=(n, len(d)))
    ort = d[idx].mean(1)
    return [round(float(np.percentile(ort, 2.5)), 4), round(float(np.percentile(ort, 97.5)), 4)]


def kosu_vektor(p, K):
    w = K.y > 0
    ll = -np.log(np.clip(p[w], 1e-12, 1))
    ilk = np.array([K.y[K.bas[r] + int(np.argmax(p[K.bas[r]: K.bas[r] + K.n[r]]))] > 0 for r in range(K.R)], float)
    return ll, ilk


class Masa:
    """Tablo + walk-forward ay pencereleri (2 kat)."""

    def __init__(self, kosular, T):
        self.kosular, self.T = kosular, T
        self.K = M.kume_kur(T)
        self.B = M.bolumle(T, kosular)
        self.tarih, self.gunler, self.tam, self.idx, self.ilk = M._pencereler(kosular)
        self.Ks = M._ozel(self.K, self.B["sinama_katli"])
        r0 = self.Ks.kosu_no[self.Ks.bas]
        self.kat_r = self.B["kat"][r0]                 # koşu başına kat
        self.ay_r = np.array([self.tarih[i][:7] for i in r0])
        self.aylar = sorted(set(self.ay_r))

    def egit(self, adlar, yari_omur=None, gbm_ayar=None, patlat_ag=None, tohumlar=None, patlat_gbm=None, lam=None):
        """Ay ay ham puanlar: kalibrasyon penceresinde (s_h, g_h) ve sınama ayında (s_a, g_a)."""
        yari_omur = M.YARI_OMUR if yari_omur is None else yari_omur
        sut = np.array([self.T["adlar"].index(a) for a in adlar])
        aylar = []
        for ay in self.aylar:
            g0 = M._gun(ay + "-01"); kb = g0 - M.KAL_GUN
            Kf = M._ozel(self.K, (self.idx >= self.ilk) & (self.gunler < kb))
            Kh = M._ozel(self.K, (self.gunler >= kb) & (self.gunler < g0) & self.tam)
            ag = 0.5 ** ((kb - self.gunler[Kf.kosu_no[Kf.bas]]) / yari_omur) if yari_omur else None
            ham = M.egit_ham(Kf, Kh, sut, lam, ag, True, gbm_ayar, patlat_ag, tohumlar, patlat_gbm)
            satir = (self.ay_r == ay)[self.Ks.seg]
            Ka = self.Ks.alt(satir)
            d = {"ay": ay, "Kh": Kh, "Ka": Ka, "satir": satir, "ham": ham}
            for k, KK in (("h", Kh), ("a", Ka)):
                X = KK.X[:, sut]
                d["s_" + k] = ((X - ham["mu"]) / ham["sd"]) @ ham["w"]
                d["g_" + k] = ham["booster"].predict(X, raw_score=True) if ham["booster"] is not None else None
            aylar.append(d)
        return {"adlar": list(adlar), "sut": sut, "aylar": aylar}

    def tahmin(self, E, kal_ayar=None, ust=None, izo_gecmis=None):
        """Ham puanlardan kalibre yalnız-model ve harman olasılıkları (tüm sınama satırları).
        izo_gecmis: (gün sayısı, karışım) → izotonik eşleme kalibrasyon penceresi yerine ÖNCEKİ ayların
        sınama-dışı tahminlerinden (yuvarlanan pencere) öğrenilir."""
        Ks = self.Ks
        pm = np.zeros(len(Ks.y)); ph = np.zeros(len(Ks.y))
        ham_p = np.zeros(len(Ks.y))   # izotonik öncesi (yuvarlanan izotonik için)
        bilinen = np.zeros(len(Ks.y), bool)
        modeller = []
        kal2 = dict(kal_ayar or {})
        if izo_gecmis:
            kal2["izo"] = False
        for d in E["aylar"]:
            m = M.egit_kal(d["ham"], d["Kh"], self.T["adlar"], E["sut"], s=d["s_h"], g=d["g_h"], henery=False,
                           kal_ayar=kal2, ust=ust)
            Ka = d["Ka"]
            sb = m.cl * d["s_a"] + (m.cg * d["g_a"] if d["g_a"] is not None and m.cg else 0.0)
            p = M.kal_uygula(m.kal, sb, Ka)
            ham_p[d["satir"]] = p
            if izo_gecmis:
                gun, karis = izo_gecmis
                g0 = M._gun(d["ay"] + "-01")
                gr = self.gunler[Ks.kosu_no]
                mk = bilinen & (gr >= g0 - gun) & (gr < g0)
                if mk.sum() > 2000:
                    xs, ys = M.izotonik(ham_p[mk], Ks.y[mk])
                    q = np.unique(np.quantile(ham_p[mk], np.linspace(0, 1, 41)))
                    q = np.r_[q, np.linspace(q[-1], 1.0, 5)[1:]] if q[-1] < 1 else q
                    adim = ["izo", list(q), list(np.interp(q, xs, ys)), karis]
                    p = M.kal_uygula([adim], np.log(np.clip(p, 1e-12, 1)), Ka)
                    m.kal = m.kal + [adim]
                    # harman α, β yeniden (kalibrasyon penceresinde aynı zincirle)
                    sbh = m.cl * d["s_h"] + (m.cg * d["g_h"] if d["g_h"] is not None and m.cg else 0.0)
                    pkh = M.kal_uygula(m.kal, sbh, d["Kh"])
                    ab = M.clogit(np.c_[np.log(np.clip(pkh, 1e-12, 1)), np.log(d["Kh"].q)], d["Kh"], 1e-6)
                    m.alfa, m.beta = float(ab[0]), float(ab[1])
            bilinen[d["satir"]] = True
            pm[d["satir"]] = p
            ph[d["satir"]] = M.softmax_kosu(m.alfa * np.log(np.clip(p, 1e-12, 1)) + m.beta * np.log(np.clip(Ka.q, 1e-9, 1)), Ka)
            modeller.append(m)
        return pm, ph, modeller

    def ozet(self, pm, ph):
        Ks = self.Ks
        v = {"model": kosu_vektor(pm, Ks), "harman": kosu_vektor(ph, Ks), "piyasa": kosu_vektor(Ks.q, Ks)}
        o = {"katlar": {}}
        for kt in KATLAR:
            mr = self.kat_r == kt
            ms = mr[Ks.seg]
            Kk = Ks.alt(ms)
            o["katlar"][kt] = {
                "kosu": int(mr.sum()),
                **{a: {"ll": round(float(v[a][0][mr].mean()), 4), "ilk": round(float(v[a][1][mr].mean()), 4)} for a in v},
                "kova_model": M.kovalar(pm[ms], Kk.y), "kova_harman": M.kovalar(ph[ms], Kk.y),
                "brier_model": M.metrikler(pm[ms], Kk)["brier"]}
        for a in ("model", "harman", "piyasa"):
            o[a] = {"ll": round(float(np.mean([o["katlar"][k][a]["ll"] for k in KATLAR])), 4),
                    "ilk": round(float(np.mean([o["katlar"][k][a]["ilk"] for k in KATLAR])), 4)}
        o["kova_model_tum"] = M.kovalar(pm, Ks.y)
        o["kova_harman_tum"] = M.kovalar(ph, Ks.y)
        return o, v

    def fark(self, v_yeni, v_eski, a="model"):
        d = v_yeni[a][0] - v_eski[a][0]
        out = {"dll": round(float(d.mean()), 4), "ga95": bootstrap(d),
               "d_ilk": round(float(v_yeni[a][1].mean() - v_eski[a][1].mean()), 4)}
        for kt in KATLAR:
            mr = self.kat_r == kt
            out[kt] = {"dll": round(float(d[mr].mean()), 4), "ga95": bootstrap(d[mr]),
                       "d_ilk": round(float(v_yeni[a][1][mr].mean() - v_eski[a][1][mr].mean()), 4)}
        return out


def gecer(r, cur, kalibrasyon=False):
    """Kapı: katların ortalaması + en güncel kat (B)."""
    m, c = r["model"], cur["model"]
    b_ok = r["katlar"]["B"]["model"]["ll"] <= c_b(cur) + 1e-9
    h_ok = r["harman"]["ll"] <= cur["harman"]["ll"] + 0.001
    if kalibrasyon:
        return m["ll"] <= c["ll"] + 1e-9 and b_ok and h_ok and m["ilk"] >= c["ilk"] - 0.002
    return m["ll"] < c["ll"] - 1e-4 and m["ilk"] >= c["ilk"] and b_ok and h_ok


def c_b(cur):
    return cur["katlar"]["B"]["model"]["ll"]


def main():
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    print(f"tablo {T['X'].shape} {time.time() - t0:.0f} sn", flush=True)
    masa = Masa(kosular, T)
    print("aylar:", masa.aylar, "koşu:", {k: int((masa.kat_r == k).sum()) for k in KATLAR}, flush=True)
    kayit = {"olusturma": None, "katlar": masa.B["tarih"]["katlar"], "adimlar": []}

    def kaydet():
        kayit["olusturma"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        json.dump(kayit, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    def adla(gr):
        return [a for a, g in O.TUM_OZELLIKLER if g in gr]

    # --- 0) taban: v3 yayın tarifi (UST_KAL, tek tohum, klasik logit)
    gr = [g for g in O.SECILI_GRUPLAR if g not in ("degisim", "hp")]   # v3 yayın grupları
    egitim = {"yari_omur": None, "gbm_ayar": None, "patlat_ag": (1.0,), "tohumlar": (1,), "patlat_gbm": False}
    kal = {"alan": False, "beta": False, "izo": False}
    izo_g = None
    E = masa.egit(adla(gr), **egitim)
    pm, ph, _ = masa.tahmin(E, kal)
    cur, v_cur = masa.ozet(pm, ph)
    v_taban = v_cur
    cur_E = E
    kayit["adimlar"].append({"no": 0, "deney": "v3 taban (yayındaki tarif), iki katta", "gecti": None, **cur})
    kayit["piyasa"] = cur["piyasa"]
    print(0, cur["model"], cur["harman"], {k: cur["katlar"][k]["model"] for k in KATLAR}, f"{time.time() - t0:.0f} sn", flush=True)
    kaydet()
    no = [0]

    def adim(ad, r, v, kalibrasyon=False, ek=None):
        nonlocal cur, v_cur
        no[0] += 1
        fm = masa.fark(v, v_cur, "model"); fh = masa.fark(v, v_cur, "harman")
        ok = gecer(r, cur, kalibrasyon)
        kayit["adimlar"].append({"no": no[0], "deney": ad, "gecti": ok, "kalibrasyon": kalibrasyon, "fark_model": fm,
                                 "fark_harman": fh, **(ek or {}), **r})
        print(no[0], ad, "GEÇTİ" if ok else "kaldı", r["model"], r["harman"],
              {k: r["katlar"][k]["model"] for k in KATLAR}, "ΔLL", fm["dll"], fm["ga95"], "A", fm["A"]["dll"], "B", fm["B"]["dll"],
              f"{time.time() - t0:.0f} sn", flush=True)
        if ok:
            cur, v_cur = r, v
        kaydet()
        return ok

    def dene_egitim(ad, gr2, eg2):
        nonlocal cur_E
        E2 = masa.egit(adla(gr2), **eg2)
        pm2, ph2, _ = masa.tahmin(E2, kal, izo_gecmis=izo_g)
        r, v = masa.ozet(pm2, ph2)
        ok = adim(ad, r, v)
        if ok:
            cur_E = E2
        return ok

    # --- 1) HP vekili
    if dene_egitim("1: handikap reytingi vekili (kilo sırası, en hafife göre kg, kg×sınıf, örtük HP: atın son 3 "
                   "handikap değerinin medyanı, bugünkü örtük HP, değişim, alana göre; apranti indirimi medyanla)",
                   gr + ["hp"], egitim):
        gr = gr + ["hp"]
    # --- 2) kalibrasyon (aynı ham puanlar)
    for ad, k2, ig in (("2a: alan büyüklüğüne duyarlı sıcaklık", {"alan": True}, None),
                       ("2b: beta kalibrasyonu (log p, log(1−p))", {"beta": True}, None),
                       ("2c: izotonik (kalibrasyon penceresi, %50 karışım)", {"izo": True, "izo_karis": 0.5}, None),
                       ("2d: izotonik, yuvarlanan 180 gün önceki sınama-dışı tahminlerden (%50 karışım)", {}, (180, 0.5)),
                       ("2e: izotonik, yuvarlanan 180 gün (%100)", {}, (180, 1.0))):
        kk = dict(kal, **k2)
        pm2, ph2, _ = masa.tahmin(cur_E, kk, izo_gecmis=ig or izo_g)
        r, v = masa.ozet(pm2, ph2)
        if adim(ad, r, v, kalibrasyon=True):
            kal = kk
            if ig:
                izo_g = ig
    kayit["kal_secim"] = {"kal": kal, "izo_gecmis": izo_g}
    # --- 3) patlatılmış logit
    for ad, eg2 in (("3a: patlatılmış logit (doğrusal) derinlik 3, ağırlık 1/0.5/0.25", dict(egitim, patlat_ag=(1.0, 0.5, 0.25))),
                    ("3b: patlatılmış logit (doğrusal) derinlik 2, ağırlık 1/0.5", dict(egitim, patlat_ag=(1.0, 0.5)))):
        if dene_egitim(ad, gr, eg2):
            egitim = eg2
            break
    if len(egitim["patlat_ag"]) > 1:
        eg2 = dict(egitim, patlat_gbm=True)
        if dene_egitim("3c: aynı sıralı amaç GBM'de de", gr, eg2):
            egitim = eg2
    # --- 4) değişim sinyalleri
    if dene_egitim("4: değişim sinyalleri (işaretli mesafe değişimi, pist değişimi/ilk kez, jokey reyting farkı, "
                   "ara kovaları, uzun aradan sonra 2. koşu, 2 yaş×mesafe, sınıf düşüş/çıkış)", gr + ["degisim"], egitim):
        gr = gr + ["degisim"]
    # --- 6) GBM torbalama (tohumlar)
    eg2 = dict(egitim, tohumlar=(1, 2, 3))
    if dene_egitim("6: GBM 3 tohum torbalama (ham puan ortalaması; doğrusal+GBM yığma katsayıları ayrı pencerede)", gr, eg2):
        egitim = eg2
    # --- 7) küçük hiperparametre taraması (kat-sağlam: kapı aynı)
    for ad, ek in (("7a: GBM 15 yaprak, en az 300", {"gbm_ayar": {"yaprak": 15, "min_yaprak": 300}}),
                   ("7b: GBM 7 yaprak, en az 300, 900 ağaç, öğrenme 0.02", {"gbm_ayar": {"min_yaprak": 300, "n_agac": 900, "ogrenme": 0.02}}),
                   ("7c: GBM 5 yaprak, en az 800", {"gbm_ayar": {"yaprak": 5, "min_yaprak": 800}}),
                   ("7d: zaman ağırlığı yarı ömrü 365 gün", {"yari_omur": 365.0}),
                   ("7e: zaman ağırlığı yarı ömrü 120 gün", {"yari_omur": 120.0})):
        eg2 = dict(egitim, **ek)
        if dene_egitim(ad, gr, eg2):
            egitim = eg2
    # --- 8) yalnız ilk-seçim kuralına takılanları YENİ tabanda bir kez daha dene (tek tekrar; aynı kapı)
    if "hp" not in gr and dene_egitim("8a: yeniden: handikap reytingi vekili (yeni tabanda)", gr + ["hp"], egitim):
        gr = gr + ["hp"]
    if len(egitim["patlat_ag"]) == 1:
        eg2 = dict(egitim, patlat_ag=(1.0, 0.5))
        if dene_egitim("8b: yeniden: patlatılmış logit derinlik 2 (yeni tabanda)", gr, eg2):
            egitim = eg2
    if "hp" not in gr and len(egitim["patlat_ag"]) == 1:
        eg2 = dict(egitim, patlat_ag=(1.0, 0.5))
        if dene_egitim("8c: birlikte: handikap vekili + patlatılmış logit derinlik 2", gr + ["hp"], eg2):
            gr = gr + ["hp"]; egitim = eg2
    kayit["secim"] = {"gruplar": gr, "egitim": {k: (list(v) if isinstance(v, tuple) else v) for k, v in egitim.items()},
                      "kal": kal, "izo_gecmis": izo_g}
    kayit["model_vs_piyasa"] = {"dll": round(float((v_cur["model"][0] - v_cur["piyasa"][0]).mean()), 4),
                                "ga95": bootstrap(v_cur["model"][0] - v_cur["piyasa"][0])}
    kayit["harman_vs_piyasa"] = {"dll": round(float((v_cur["harman"][0] - v_cur["piyasa"][0]).mean()), 4),
                                 "ga95": bootstrap(v_cur["harman"][0] - v_cur["piyasa"][0])}
    kayit["toplam"] = {"model": masa.fark(v_cur, v_taban, "model"), "harman": masa.fark(v_cur, v_taban, "harman")}
    t1 = time.time()
    kayit["sure_sn"] = round(t1 - t0)
    kaydet()
    print("bitti", kayit["secim"], f"{t1 - t0:.0f} sn")


def toplam():
    """Kayıtlı seçime göre yalnız taban ve son tarifi yeniden ölçüp toplam eşleştirilmiş farkı ekler (uzun koşuyu tekrarlamadan)."""
    kayit = json.load(open(CIKTI, encoding="utf-8"))
    sc = kayit["secim"]
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    masa = Masa(kosular, T)
    ad = lambda gr: [a for a, g in O.TUM_OZELLIKLER if g in gr]
    E0 = masa.egit(ad([g for g in sc["gruplar"] if g not in ("degisim", "hp")]), patlat_ag=(1.0,), tohumlar=(1,), patlat_gbm=False)
    r0, v0 = masa.ozet(*masa.tahmin(E0, {"alan": False, "beta": False, "izo": False})[:2])
    eg = {k: (tuple(v) if isinstance(v, list) else v) for k, v in sc["egitim"].items()}
    E1 = masa.egit(ad(sc["gruplar"]), **eg)
    r1, v1 = masa.ozet(*masa.tahmin(E1, sc["kal"], izo_gecmis=sc["izo_gecmis"])[:2])
    kayit["toplam"] = {"model": masa.fark(v1, v0, "model"), "harman": masa.fark(v1, v0, "harman"),
                       "kontrol": {"taban": r0["model"], "son": r1["model"]}}
    json.dump(kayit, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(kayit["toplam"])


if __name__ == "__main__":
    toplam() if "--toplam" in sys.argv else main()
