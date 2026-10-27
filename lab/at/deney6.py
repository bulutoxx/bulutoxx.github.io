# OXXai at yarışı laboratuvarı — v6 deney masası (derin tarama turu; elle çalıştırılır, gece akışının parçası değil).
# Kalıp: lab/at/deney5.py. Kapı: lab/at/deney4.py iki katlı kapı (Masa, gecer) aynen:
#   katların ORTALAMA yalnız-model log-loss'u düşmeli (> 0,0001), ortalama ilk-seçim isabeti düşmemeli, en güncel kat (B)
#   kötüleşmemeli, harman 0,001'den fazla bozulmamalı. Her adımda önceki kabule göre koşu başına eşleştirilmiş ΔLL ve
#   koşu-bootstrap %95 GA (birleşik + kat kat). Walk-forward: her ay yalnız o aydan önceki veriyle eğitim → "hiç
#   oynanmamış gibi" sanal oynatma.
# Taban: yayındaki tarif (v4 + jk_uzman, jk_apr, jk_beceri + a5_sinif). Adaylar (en fazla 5):
#   a6_pist, a6_kalman, a6_mesafe, a6_gelisim (lab/at/at6.py) — özellik grupları, tek tek eklenir; geçen sonrakinin tabanı.
#   a6_hava (Open-Meteo) yalnız AT_HAVA ile lisanslı bir hava dosyası verildiyse denenir (Open-Meteo'dan lab/at/hava.py ile
#   çekilmiş _hava/gunluk.csv; lisansı belirsiz üçüncü taraf kopyaları KULLANILMAZ). Dosya yoksa "ölçülemedi" yazılır.
#   m6_rank — model yöntemi: GBM katmanının amacı koşu içi softmax yerine LightGBM LambdaRank (ilk 3 kademeli alaka:
#             1.=3, 2.=2, 3.=1, diğer 0); doğrusal+GBM yığma katsayıları kalibrasyon penceresinde aynı yolla öğrenilir.
# a6_pist (ya da a6_hava) kapıyı geçerse sağlamlık satırı: yarış günü değerleri bilinmiyor sayılarak (yalnız önceki günler) yeniden ölçülür
#   (üretimde yarış günü değeri tahmindir; deneyde arşiv değeri). Bu satır seçimi değiştirmez, yalnız raporlanır.
# Yalnız ilk-seçim kuralına takılan özellik grupları (ΔLL < 0) yeni tabanda bir kez daha denenir.
# Çıktı: data/at/deneyler_v6.json (yalnız türetilmiş metrikler).
#   AT_KAYNAK=/yol/tjk-data AT_HAVA=/yol/gunluk.csv python lab/at/deney6.py            # deneyler
#   AT_KAYNAK=/yol/tjk-data AT_HAVA=/yol/gunluk.csv python lab/at/deney6.py --devam    # yarıda kalan deneyden devam
#   AT_KAYNAK=/yol/tjk-data AT_HAVA=/yol/gunluk.csv python lab/at/deney6.py --sizinti  # a6_* sızıntı testi
import json, os, sys, time

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import veri, ozellik as O, model as M, at6 as A6  # noqa: E402
from deney4 import Masa, gecer, KATLAR  # noqa: E402
from deney_jokey import _kisalt  # noqa: E402

CIKTI = os.path.join(BURA, "..", "..", "data", "at", "deneyler_v6.json")
# --devam önbelleği (depoya girmez): taban ve güncel kabulün koşu başına vektörleri; yeniden başlatmada pahalı eğitimi atlar
ONBELLEK = os.environ.get("AT_DENEY6_ONBELLEK") or os.path.join(BURA, "..", "..", "_deney6_onbellek")
ADLAR_GRUP = {
    "a6_pist": "ayna programından sabah bilinen pist/hava vekili: yağış bayrağı, nem, sıcaklık, aynı hipodrom+pistte önceki "
               "yarış gününün pist durumu (sönümlü); beklenen ıslaklık × (ıslak pist uyumu, kilo, reyting)",
    "a6_hava": "hava (Open-Meteo): ıslaklık endeksi (yarış günü + önceki 3 gün), sıcaklık, atın ıslak pist uyumu, "
               "ıslaklık × (uyum, alan içi reyting, kilo, çim)",
    "a6_kalman": "Kalman hız figürü: at başına durum-uzay yetenek (gün başına süreç varyansı) − alan, belirsizlik, z, "
                 "alan içi sıra, figür tutarlılığı",
    "a6_mesafe": "mesafe profili: ±%10 mesafedeki en iyi figür − genel en iyi, figür–log(mesafe) eğimi × sapma, en iyi "
                 "figürün mesafesine uzaklık",
    "a6_gelisim": "yaş × ara gelişim eğrisi: ardışık figür farkının (yaş, ara kovası) ortalaması, alana göre",
    "m6_rank": "GBM amacı LambdaRank (ilk 3 kademeli alaka) — koşu içi softmax yerine",
}
_GBM_ASIL = M.gbm_egit


def gbm_lambdarank(X, K, agirlik=None, ayar=None, init=None, tohum=1):
    """LightGBM LambdaRank: koşu = sorgu grubu, alaka 1.=3, 2.=2, 3.=1, diğer 0. Zaman ağırlığı satıra yayılır."""
    a = dict(M.GBM_AYAR, **(ayar or {}))
    rel = np.where(K.sira == 1, 3, np.where(K.sira == 2, 2, np.where(K.sira == 3, 1, 0)))
    sw = None if agirlik is None else np.asarray(agirlik, float)[K.seg]
    par = {"objective": "lambdarank", "lambdarank_truncation_level": 10, "label_gain": [0, 1, 3, 7],
           "learning_rate": a["ogrenme"], "num_leaves": a["yaprak"], "min_data_in_leaf": a["min_yaprak"],
           "feature_fraction": a["oznitelik_payi"], "bagging_fraction": 0.8, "bagging_freq": 1, "lambda_l2": a["l2"],
           "verbose": -1, "seed": tohum, "deterministic": True, "num_threads": min(4, os.cpu_count() or 1)}
    ds = M.lgb.Dataset(X, label=rel, group=K.n, weight=sw, free_raw_data=False)
    return M.lgb.train(par, ds, num_boost_round=a["n_agac"])


def _vkaydet(ad, r, v):
    os.makedirs(ONBELLEK, exist_ok=True)
    np.savez(os.path.join(ONBELLEK, ad + ".npz"), **{f"{k}_{i}": v[k][i] for k in v for i in (0, 1)})
    json.dump(r, open(os.path.join(ONBELLEK, ad + ".json"), "w"), default=float)


def _vyukle(ad):
    try:
        z = np.load(os.path.join(ONBELLEK, ad + ".npz"))
        r = json.load(open(os.path.join(ONBELLEK, ad + ".json")))
    except (OSError, ValueError):
        return None
    return r, {k: (z[f"{k}_0"], z[f"{k}_1"]) for k in ("model", "harman", "piyasa")}


def kaydet_json(kayit):
    kayit["olusturma"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    tmp = CIKTI + ".tmp"
    json.dump(kayit, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, CIKTI)


def hava_kapsami(kosular):
    d = A6.A6Durum()
    var = sum(1 for k in kosular if d.islak(k["hipodrom"], O.gun_no(k["tarih"])) is not None)
    return {"kosu": len(kosular), "hava_var": var, "dosya": os.path.basename(A6.hava_yolu()),
            "son_tarih": max((t for _, t in d.hava), default=None)}


def main(devam=False):
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    print(f"tablo {T['X'].shape} {time.time() - t0:.0f} sn", hava_kapsami(kosular), flush=True)
    masa = Masa(kosular, T)
    adla = lambda gr: [a for a, g in O.TUM_OZELLIKLER if g in gr]
    gr = [g for g in O.SECILI_GRUPLAR if not g.startswith("a6_")]
    egitim = {"yari_omur": None, "gbm_ayar": None, "patlat_ag": tuple(M.PATLAT), "tohumlar": tuple(M.GBM_TOHUM),
              "patlat_gbm": M.PATLAT_GBM}
    kal = dict(M.KAL_AYAR)
    rank = [False]

    def egit(gr_, rank_):
        M.gbm_egit = gbm_lambdarank if rank_ else _GBM_ASIL
        try:
            return masa.egit(adla(gr_), **egitim)
        finally:
            M.gbm_egit = _GBM_ASIL

    yuk = _vyukle("taban") if devam else None
    if yuk:
        cur, v_cur = yuk
    else:
        cur, v_cur = masa.ozet(*masa.tahmin(egit(gr, False), kal)[:2])
        _vkaydet("taban", cur, v_cur)
    v_taban = v_cur
    kayit = {"olusturma": None, "katlar": masa.B["tarih"]["katlar"], "kapi": "deney4 iki katlı kapı",
             "hava": hava_kapsami(kosular), "taban_gruplar": list(gr),
             "adimlar": [{"no": 0, "deney": "taban (yayındaki tarif: v4 + jk_uzman, jk_apr, jk_beceri + a5_sinif)",
                          "gecti": None, **_kisalt(cur)}]}
    print(0, cur["model"], cur["harman"], {k: cur["katlar"][k]["model"] for k in KATLAR}, f"{time.time() - t0:.0f} sn", flush=True)
    no = [0]
    yapilan = {}
    if devam and os.path.exists(CIKTI):
        eski = json.load(open(CIKTI, encoding="utf-8"))
        if eski.get("adimlar"):
            kayit = dict(eski, adimlar=[dict(eski["adimlar"][0], **_kisalt(cur))] + eski["adimlar"][1:])
            for s_ in eski["adimlar"][1:]:
                yapilan[s_["deney"]] = (s_["gecti"], s_["fark_model"]["dll"])
                if s_.get("saglamlik"):
                    continue
                g_ = s_["deney"].split(" — ")[0].replace("yeniden (yeni tabanda): ", "")
                if s_["gecti"]:
                    if g_ == "m6_rank":
                        rank[0] = True
                    elif g_ not in gr:
                        gr = gr + [g_]
            no[0] = eski["adimlar"][-1]["no"]
            if any(v[0] for v in yapilan.values()):
                yuk = _vyukle("guncel")
                cur, v_cur = yuk if yuk else masa.ozet(*masa.tahmin(egit(gr, rank[0]), kal)[:2])
            print("devam:", no[0], "adım kayıtlı; güncel:", [g for g in gr if g.startswith("a6_")], "rank", rank[0],
                  cur["model"], f"{time.time() - t0:.0f} sn", flush=True)
    kaydet_json(kayit)

    def adim(ad, r, v, saglamlik=False):
        nonlocal cur, v_cur
        no[0] += 1
        fm = masa.fark(v, v_cur, "model"); fh = masa.fark(v, v_cur, "harman")
        ok = gecer(r, cur)
        kayit["adimlar"].append({"no": no[0], "deney": ad, "gecti": ok, "fark_model": fm, "fark_harman": fh,
                                 **({"saglamlik": True} if saglamlik else {}), **_kisalt(r)})
        print(no[0], ad[:60], "GEÇTİ" if ok else "kaldı", r["model"], r["harman"],
              {k: r["katlar"][k]["model"] for k in KATLAR}, "ΔLL", fm["dll"], fm["ga95"], "A", fm["A"]["dll"], "B",
              fm["B"]["dll"], "harman ΔLL", fh["dll"], fh["ga95"], f"{time.time() - t0:.0f} sn", flush=True)
        if ok and not saglamlik:
            cur, v_cur = r, v
            _vkaydet("guncel", r, v)
        kaydet_json(kayit)
        return ok, fm["dll"]

    def dene(ad, gr2, rank2):
        if ad in yapilan:
            return yapilan[ad]
        r, v = masa.ozet(*masa.tahmin(egit(gr2, rank2), kal)[:2])
        return adim(ad, r, v)

    yakin = []
    hava_var = os.path.exists(A6.hava_yolu())
    kayit["hava_durumu"] = ("ölçüldü: " + os.path.basename(A6.hava_yolu())) if hava_var else \
        "ölçülemedi: Open-Meteo bu ortamdan erişilemedi; lisanslı hava dosyası yok (üretim çekicisi lab/at/hava.py hazır)"
    for g in A6.A6_GRUPLAR:
        if g == "a6_hava" and not hava_var:
            continue
        ok, d = dene(f"{g} — {ADLAR_GRUP[g]}", gr + [g], rank[0])
        if ok and g not in gr:
            gr = gr + [g]
        elif not ok and d < 0:
            yakin.append(g)
    ok, _ = dene(f"m6_rank — {ADLAR_GRUP['m6_rank']}", gr, True)
    rank[0] = rank[0] or ok
    for g in yakin:   # tek tekrar, yeni tabanda (deney4 8a/8b usulü)
        ok, _ = dene(f"yeniden (yeni tabanda): {g}", gr + [g], rank[0])
        if ok and g not in gr:
            gr = gr + [g]
    # sağlamlık: a6_pist / a6_hava seçildiyse yarış günü değerleri bilinmiyor sayılarak (yalnız önceki günler)
    for g_s, bayrak, ad_s in (("a6_pist", "PIST_BUGUN", "sağlamlık: a6_pist yarış günü programı havası olmadan (yalnız önceki "
                                                      "yarış günlerinin pist durumu)"),
                              ("a6_hava", "HAVA_BUGUN", "sağlamlık: a6_hava yarış günü yağışı olmadan (yalnız önceki 3 gün; "
                                                      "sıcaklık önceki gün)")):
        if g_s not in gr or ad_s in yapilan:
            continue
        setattr(A6, bayrak, False)
        try:
            T2, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
        finally:
            setattr(A6, bayrak, True)
        masa_asil = masa
        masa = Masa(kosular, T2)
        try:
            r, v = masa.ozet(*masa.tahmin(egit(gr, rank[0]), kal)[:2])
            adim(ad_s, r, v, saglamlik=True)
        finally:
            masa = masa_asil
    kayit["secim"] = {"gruplar": list(dict.fromkeys(g for g in gr if g.startswith("a6_"))), "m6_rank": rank[0]}
    kayit["toplam"] = {"model": masa.fark(v_cur, v_taban, "model"), "harman": masa.fark(v_cur, v_taban, "harman")}
    kayit["model_vs_piyasa"] = {"dll": round(float((v_cur["model"][0] - v_cur["piyasa"][0]).mean()), 4)}
    kayit["harman_vs_piyasa"] = {"dll": round(float((v_cur["harman"][0] - v_cur["piyasa"][0]).mean()), 4)}
    kayit["sure_sn"] = round(time.time() - t0)
    kaydet_json(kayit)
    print("bitti, seçilen:", kayit["secim"], f"{time.time() - t0:.0f} sn")


def sizinti():
    """a6_* sütunları için sızıntı testi (deney5 --sizinti kalıbı): (1) kesme: D gününün özellikleri yalnız D'den önceki
    koşularla kurulan durumla tam tablodakiyle aynı; (2) D'nin sonuçları (sıra, derece, oran) karıştırılınca D'nin
    özellikleri değişmiyor; (3) gün içi koşu sırası ters çevrilince aynı."""
    import random
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    sut = [O.TUM_ADLAR.index(a) for a in A6.A6_ADLAR]
    gunler = sorted({k["tarih"] for k in kosular})
    rng = np.random.default_rng(17)
    hata = []
    for D in sorted(rng.choice(gunler[60:], size=4, replace=False)):
        once = [k for k in kosular if k["tarih"] < D]
        bugun = [k for k in kosular if k["tarih"] == D]
        _, durum = O.tablo_kur(once, adlar=O.TUM_ADLAR)
        Xd = np.vstack([durum.ozellik(k, A6.A6_ADLAR) for k in bugun])
        bas = sum(len(k["atlar"]) for k in once)
        Xt = T["X"][bas: bas + len(Xd)][:, sut]
        ok1 = np.allclose(Xd, Xt, atol=1e-9)
        karisik = json.loads(json.dumps(bugun))
        for k in karisik:
            s = [a["sira"] for a in k["atlar"]]; random.Random(1).shuffle(s)
            o = [a["oran"] for a in k["atlar"]]; random.Random(2).shuffle(o)
            for a, x, y in zip(k["atlar"], s, o):
                a["sira"], a["oran"], a["sure"] = x, y, None
        Xk = np.vstack([durum.ozellik(k, A6.A6_ADLAR) for k in karisik])
        ok2 = np.allclose(Xd, Xk, atol=1e-12)
        Xr = [durum.ozellik(k, A6.A6_ADLAR) for k in reversed(bugun)]
        ok3 = np.allclose(Xd, np.vstack(list(reversed(Xr))), atol=1e-12)
        dolu = float((np.abs(Xd) > 0).mean())
        if ok1 and not ok2:
            print("  değişen sütunlar:", [A6.A6_ADLAR[j] for j in range(len(sut)) if not np.allclose(Xd[:, j], Xk[:, j])])
        print(f"{D}: {len(Xd)} satır · dolu %{100 * dolu:.0f} · kesme {'AYNI' if ok1 else 'FARKLI'} · sonuç karıştırma "
              f"{'AYNI' if ok2 else 'FARKLI'} · ters sıra {'AYNI' if ok3 else 'FARKLI'}", flush=True)
        if not (ok1 and ok2 and ok3):
            hata.append(D)
    print(f"bitti {time.time() - t0:.0f} sn")
    if hata:
        print("SIZINTI ŞÜPHESİ:", hata)
        sys.exit(1)
    print("SIZINTI YOK (a6_*)")


if __name__ == "__main__":
    sizinti() if "--sizinti" in sys.argv else main(devam="--devam" in sys.argv)
