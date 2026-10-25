# BULUTOXX at yarışı laboratuvarı — deney masası (elle çalıştırılır; gece akışının parçası değildir).
# Her deney AYNI sınama dilimiyle (son %30, tam oranlı koşular) ölçülür. Kapı (her adım için):
#   yalnız-model sınama log-loss'u düşmeli VE yalnız-model ilk-seçim isabeti düşmemeli. Geçen adım kalır.
# Çıktı: data/at/deneyler.json (yalnız türetilmiş metrikler).
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney.py
import json, os, sys, time

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import veri, ozellik as O, model as M  # noqa: E402


def ozet(m):
    return {"ll": m["log_loss"], "brier": m["brier"], "ilk": m["ilk_secim_isabet"], "ilk2": m["ilk_iki_ikisi_de_ilk2"],
            "p30": [m["p>=0.30"]["secim"], m["p>=0.30"]["isabet"], m["p>=0.30"]["ort_p"]],
            "p50": [m["p>=0.50"]["secim"], m["p>=0.50"]["isabet"], m["p>=0.50"]["ort_p"]]}


def olc(T, kosular, gruplar, **kw):
    adlar = [a for a, g in O.TUM_OZELLIKLER if g in gruplar]
    sut = [T["adlar"].index(a) for a in adlar]
    T2 = dict(T); T2["X"] = T["X"][:, sut]; T2["adlar"] = adlar
    r = M.sina(T2, kosular, **kw)
    return {"model": ozet(r["metrik"]["model"]), "harman": ozet(r["metrik"]["harman"]),
            "piyasa": ozet(r["metrik"]["piyasa"]), "kovalar_model": r["kovalar"]["model"]}


def gecer(yeni, eski):
    return yeni["model"]["ll"] < eski["model"]["ll"] - 1e-4 and yeni["model"]["ilk"] >= eski["model"]["ilk"]


def main():
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    print(f"tablo {T['X'].shape} {time.time() - t0:.0f} sn", flush=True)
    adimlar = []

    def kaydet(no, ad, r, gecti, aciklama):
        adimlar.append({"no": no, "deney": ad, "gecti": gecti, "aciklama": aciklama, **r})
        print(no, ad, "GEÇTİ" if gecti else "kaldı", r["model"], r["harman"], f"{time.time() - t0:.0f} sn", flush=True)

    M.UST_KAL = False   # 0-10. adımlar üst uç kalibrasyonu olmadan ölçülür
    gr = list(O.V1_GRUPLAR)
    taban = olc(T, kosular, gr, protokol="sabit", yari_omur=None)
    kaydet(0, "v1 (yayındaki model): tek eğitim, sabit bölüm", taban, None, "karşılaştırma tabanı")
    cur = olc(T, kosular, gr, protokol="aylik", yari_omur=None)
    kaydet(1, "aylık walk-forward yeniden eğitim (v1 özellikleri)", cur, gecer(cur, taban),
           "sınamanın her ayı için o aya kadarki veriyle yeniden eğitim; kalibrasyon önceki 90 gün")
    sira = [("piyasa_hafiza", "1: piyasa hafızası (EWMA, piyasa sırası, yenilen favori, piyasa reytingi)"),
            ("reyting", "2a: Plackett-Luce at/jokey/antrenör reytingi"),
            ("sinif2", "2b: sayısal sınıf (tür, alanın reyting düzeyi, handikap kilosu)"),
            ("hiz", "3: hız puanı (standart derece + gün/pist değişkeni)"),
            ("fark2", "4: zaman sönümlü form ve kazanana uzaklık"),
            ("jokey2", "ek: jokey/antrenör binişlerine piyasa ilgisi, jokey yükseltmesi, ekuri")]
    for i, (g, ad) in enumerate(sira):
        r = olc(T, kosular, gr + [g], protokol="aylik", yari_omur=None)
        ok = gecer(r, cur)
        kaydet(2 + i, ad, r, ok, "grup eklendi" if ok else "grup eklenmedi")
        if ok:
            gr, cur = gr + [g], r
    r = olc(T, kosular, gr, protokol="aylik", yari_omur=180.0)
    ok = gecer(r, cur)
    kaydet(8, "6a: zaman ağırlıklı eğitim (yarı ömür 180 gün)", r, ok, "")
    yo = 180.0 if ok else None
    if ok:
        cur = r
    gbm_ok = False
    if M.lgb is not None:
        varsayilan = dict(M.GBM_AYAR)
        for no, ayar, ad in ((9, {"yaprak": 15, "min_yaprak": 200}, "6b: LightGBM (koşu içi softmax amacı) + doğrusal birleşim; 15 yaprak, en az 200 at/yaprak"),
                             (10, {"yaprak": 7, "min_yaprak": 500}, "6c: aynı, daha düzenli ağaçlar: 7 yaprak, en az 500 at/yaprak")):
            M.GBM_AYAR.update(ayar)
            r = olc(T, kosular, gr, protokol="aylik", yari_omur=yo, gbm=True)
            ok = gecer(r, cur)
            kaydet(no, ad, r, ok, "birleştirme katsayıları (sıcaklık dahil) kalibrasyon penceresinde öğrenilir")
            if ok:
                cur, gbm_ok, secilen = r, True, dict(M.GBM_AYAR)
                break
        M.GBM_AYAR.clear(); M.GBM_AYAR.update(secilen if gbm_ok else varsayilan)
    M.UST_KAL = True
    r = olc(T, kosular, gr, protokol="aylik", yari_omur=yo, gbm=gbm_ok)
    ok = gecer(r, cur)
    kaydet(11, f"7: üst uç kalibrasyonu (p > {M.UST_ESIK:.2f} bölgesine ayrı eğim, kalibrasyon penceresinde)", r, ok, "")
    ust_ok = ok
    kayit = {"olusturma": time.strftime("%Y-%m-%dT%H:%M:%S"), "secili_gruplar": gr, "yari_omur": yo,
             "gbm": gbm_ok, "gbm_ayar": dict(M.GBM_AYAR), "ust_kal": ust_ok, "adimlar": adimlar,
             "not": "Kapı: yalnız-model log-loss düşmeli ve ilk-seçim isabeti düşmemeli. Deney 5 (sabah form dizisi) RAPOR.md'de."}
    json.dump(kayit, open(os.path.join(BURA, "..", "..", "data", "at", "deneyler.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"bitti {time.time() - t0:.0f} sn; seçili: {gr}")


if __name__ == "__main__":
    main()
