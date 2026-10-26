# BULUTOXX at yarışı laboratuvarı — v5 deney masası (elle çalıştırılır; gece akışının parçası değil).
# Kalıp: lab/at/deney_jokey.py. Kapı: lab/at/deney4.py iki katlı kapı (Masa, gecer) aynen:
#   katların ORTALAMA yalnız-model log-loss'u düşmeli (> 0,0001), ortalama ilk-seçim isabeti düşmemeli, en güncel kat (B)
#   kötüleşmemeli, harman 0,001'den fazla bozulmamalı. Her adımda önceki kabule göre koşu başına eşleştirilmiş ΔLL ve
#   koşu-bootstrap %95 GA (birleşik + kat kat).
# Taban: yayındaki tarif (v4 + jk_uzman, jk_apr, jk_beceri). Adaylar (en fazla 4):
#   a5_sinif, a5_kilo, a5_taze (lab/at/at5.py) — özellik grupları, tek tek eklenir; geçen bir sonrakinin tabanı olur.
#   hm_alan — harman katmanı: p ∝ exp((α + α'·z)·log p + (β + β'·z)·log q), z = log N − log 10 (alan büyüklüğü).
#             Yalnız-model değişmez; kapısı harmanın kendisi: harman ort. LL düşmeli (> 0,0001), harman ort. ilk
#             seçimi düşmemeli, B katında harman LL kötüleşmemeli.
# Yalnız ilk-seçim kuralına takılan özellik grupları (ΔLL < 0) yeni tabanda bir kez daha denenir.
# Çıktı: data/at/deneyler_v5.json (yalnız türetilmiş metrikler).
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney5.py            # deneyler
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney5.py --devam    # yarıda kalan deneyden devam (kayıtlı adımlar atlanır)
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney5.py --sizinti  # a5_* sızıntı testi
import json, os, sys, time

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import veri, ozellik as O, model as M, at5 as A5  # noqa: E402
from deney4 import Masa, gecer, KATLAR  # noqa: E402
from deney_jokey import _kisalt  # noqa: E402

CIKTI = os.path.join(BURA, "..", "..", "data", "at", "deneyler_v5.json")
ADLAR_GRUP = {
    "a5_sinif": "sınıf-ayarlı form: son koşulardaki rakip alan düzeyi (alanın PL at reytingi) − bugünkü alan, ilk 3'e "
                "girdiği en güçlü alan, güçlü alanlarda ilk 3 payı",
    "a5_kilo": "göreli kilo değişimi: (kilo − alan ort.) bugün − son koşu, kilo × mesafe, galibiyet sonrası kilo, "
               "iyi koştuğu kiloya göre fark",
    "a5_taze": "dinlenme eğrisi: atın uzun aradan / sık koşudaki kişisel uyumu, antrenörün uzun aradan dönüş kalıntısı "
               "(piyasaya göre), log(ara)², son 30 günde koşu",
    "hm_alan": "harman ağırlığı alan büyüklüğüne göre: (α + α'·z)·log p + (β + β'·z)·log q",
}


def tahmin(masa, E, kal, hm_alan=False):
    """Masa.tahmin + isteğe bağlı alan büyüklüğüne duyarlı harman (kalibrasyon penceresinde öğrenilir)."""
    pm, ph, modeller = masa.tahmin(E, kal)
    if not hm_alan:
        return pm, ph
    ph = ph.copy()
    for d, m in zip(E["aylar"], modeller):
        Kh, Ka = d["Kh"], d["Ka"]
        sbh = m.cl * d["s_h"] + (m.cg * d["g_h"] if d["g_h"] is not None and m.cg else 0.0)
        lp = np.log(np.clip(M.kal_uygula(m.kal, sbh, Kh), 1e-12, 1)); lq = np.log(np.clip(Kh.q, 1e-9, 1))
        z = M._alan_dN(Kh)
        w = M.clogit(np.c_[lp, lq, z * lp, z * lq], Kh, 1e-6)
        lpa = np.log(np.clip(pm[d["satir"]], 1e-12, 1)); lqa = np.log(np.clip(Ka.q, 1e-9, 1))
        za = M._alan_dN(Ka)
        ph[d["satir"]] = M.softmax_kosu(np.c_[lpa, lqa, za * lpa, za * lqa] @ w, Ka)
    return pm, ph


def gecer_harman(r, cur):
    return (r["harman"]["ll"] < cur["harman"]["ll"] - 1e-4 and r["harman"]["ilk"] >= cur["harman"]["ilk"]
            and r["katlar"]["B"]["harman"]["ll"] <= cur["katlar"]["B"]["harman"]["ll"] + 1e-9)


def kaydet_json(kayit):
    kayit["olusturma"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    tmp = CIKTI + ".tmp"
    json.dump(kayit, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, CIKTI)


def main(devam=False):
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    print(f"tablo {T['X'].shape} {time.time() - t0:.0f} sn", flush=True)
    masa = Masa(kosular, T)
    adla = lambda gr: [a for a, g in O.TUM_OZELLIKLER if g in gr]
    gr = [g for g in O.SECILI_GRUPLAR if not g.startswith("a5_")]
    egitim = {"yari_omur": None, "gbm_ayar": None, "patlat_ag": tuple(M.PATLAT), "tohumlar": tuple(M.GBM_TOHUM),
              "patlat_gbm": M.PATLAT_GBM}
    kal = dict(M.KAL_AYAR)
    hm = [False]
    E = masa.egit(adla(gr), **egitim)
    cur, v_cur = masa.ozet(*tahmin(masa, E, kal))
    cur_E = E
    v_taban = v_cur
    kayit = {"olusturma": None, "katlar": masa.B["tarih"]["katlar"], "kapi": "deney4 iki katlı kapı (hm_alan: harman kapısı)",
             "taban_gruplar": list(gr), "adimlar": [{"no": 0, "deney": "taban (yayındaki tarif: v4 + jk_uzman, jk_apr, jk_beceri)",
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
                g_ = s_["deney"].split(" — ")[0].replace("yeniden (yeni tabanda): ", "")
                if s_["gecti"]:
                    if g_ == "hm_alan":
                        hm[0] = True
                    elif g_ not in gr:
                        gr = gr + [g_]
            no[0] = eski["adimlar"][-1]["no"]
            if any(v[0] for v in yapilan.values()):
                cur_E = masa.egit(adla(gr), **egitim)
                cur, v_cur = masa.ozet(*tahmin(masa, cur_E, kal, hm[0]))
            print("devam:", no[0], "adım kayıtlı; güncel:", [g for g in gr if g.startswith("a5_")], "hm", hm[0], cur["model"],
                  f"{time.time() - t0:.0f} sn", flush=True)
    kaydet_json(kayit)

    def adim(ad, r, v, harman=False):
        nonlocal cur, v_cur
        no[0] += 1
        fm = masa.fark(v, v_cur, "model"); fh = masa.fark(v, v_cur, "harman")
        ok = gecer_harman(r, cur) if harman else gecer(r, cur)
        kayit["adimlar"].append({"no": no[0], "deney": ad, "gecti": ok, "fark_model": fm, "fark_harman": fh, **_kisalt(r)})
        print(no[0], ad[:60], "GEÇTİ" if ok else "kaldı", r["model"], r["harman"],
              {k: r["katlar"][k]["model"] for k in KATLAR}, "ΔLL", fm["dll"], fm["ga95"], "A", fm["A"]["dll"], "B",
              fm["B"]["dll"], "harman ΔLL", fh["dll"], fh["ga95"], f"{time.time() - t0:.0f} sn", flush=True)
        if ok:
            cur, v_cur = r, v
        kaydet_json(kayit)
        return ok, (fh if harman else fm)["dll"]

    def dene(ad, gr2):
        nonlocal cur_E
        if ad in yapilan:
            return yapilan[ad]
        E2 = masa.egit(adla(gr2), **egitim)
        r, v = masa.ozet(*tahmin(masa, E2, kal, hm[0]))
        ok, d = adim(ad, r, v)
        if ok:
            cur_E = E2
        return ok, d

    yakin = []
    for g in A5.A5_GRUPLAR:
        ok, d = dene(f"{g} — {ADLAR_GRUP[g]}", gr + [g])
        if ok and g not in gr:
            gr = gr + [g]
        elif not ok and d < 0:
            yakin.append(g)
    ad = f"hm_alan — {ADLAR_GRUP['hm_alan']}"
    if ad not in yapilan:
        r, v = masa.ozet(*tahmin(masa, cur_E, kal, True))
        ok, _ = adim(ad, r, v, harman=True)
        hm[0] = hm[0] or ok
    for g in yakin:   # tek tekrar, yeni tabanda (deney4 8a/8b usulü)
        ok, _ = dene(f"yeniden (yeni tabanda): {g}", gr + [g])
        if ok and g not in gr:
            gr = gr + [g]
    kayit["secim"] = {"gruplar": list(dict.fromkeys(g for g in gr if g.startswith("a5_"))), "hm_alan": hm[0]}
    kayit["toplam"] = {"model": masa.fark(v_cur, v_taban, "model"), "harman": masa.fark(v_cur, v_taban, "harman")}
    kayit["model_vs_piyasa"] = {"dll": round(float((v_cur["model"][0] - v_cur["piyasa"][0]).mean()), 4)}
    kayit["harman_vs_piyasa"] = {"dll": round(float((v_cur["harman"][0] - v_cur["piyasa"][0]).mean()), 4)}
    kayit["sure_sn"] = round(time.time() - t0)
    kaydet_json(kayit)
    print("bitti, seçilen:", kayit["secim"], f"{time.time() - t0:.0f} sn")


def sizinti():
    """a5_* sütunları için sızıntı testi (deney_jokey --sizinti kalıbı): (1) kesme: D gününün özellikleri yalnız D'den
    önceki koşularla kurulan durumla tam tablodakiyle aynı; (2) D'nin sonuçları (sıra, derece, oran) karıştırılınca
    D'nin özellikleri değişmiyor; (3) gün içi koşu sırası ters çevrilince aynı."""
    import random
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    sut = [O.TUM_ADLAR.index(a) for a in A5.A5_ADLAR]
    gunler = sorted({k["tarih"] for k in kosular})
    rng = np.random.default_rng(13)
    hata = []
    for D in sorted(rng.choice(gunler[60:], size=4, replace=False)):
        once = [k for k in kosular if k["tarih"] < D]
        bugun = [k for k in kosular if k["tarih"] == D]
        _, durum = O.tablo_kur(once, adlar=O.TUM_ADLAR)
        Xd = np.vstack([durum.ozellik(k, A5.A5_ADLAR) for k in bugun])
        bas = sum(len(k["atlar"]) for k in once)
        Xt = T["X"][bas: bas + len(Xd)][:, sut]
        ok1 = np.allclose(Xd, Xt, atol=1e-9)
        karisik = json.loads(json.dumps(bugun))
        for k in karisik:
            s = [a["sira"] for a in k["atlar"]]; random.Random(1).shuffle(s)
            o = [a["oran"] for a in k["atlar"]]; random.Random(2).shuffle(o)
            for a, x, y in zip(k["atlar"], s, o):
                a["sira"], a["oran"], a["sure"] = x, y, None
        Xk = np.vstack([durum.ozellik(k, A5.A5_ADLAR) for k in karisik])
        ok2 = np.allclose(Xd, Xk, atol=1e-12)
        Xr = [durum.ozellik(k, A5.A5_ADLAR) for k in reversed(bugun)]
        ok3 = np.allclose(Xd, np.vstack(list(reversed(Xr))), atol=1e-12)
        dolu = float((np.abs(Xd) > 0).mean())
        print(f"{D}: {len(Xd)} satır · dolu %{100 * dolu:.0f} · kesme {'AYNI' if ok1 else 'FARKLI'} · sonuç karıştırma "
              f"{'AYNI' if ok2 else 'FARKLI'} · ters sıra {'AYNI' if ok3 else 'FARKLI'}", flush=True)
        if not (ok1 and ok2 and ok3):
            hata.append(D)
    print(f"bitti {time.time() - t0:.0f} sn")
    if hata:
        print("SIZINTI ŞÜPHESİ:", hata)
        sys.exit(1)
    print("SIZINTI YOK (a5_*)")


if __name__ == "__main__":
    sizinti() if "--sizinti" in sys.argv else main(devam="--devam" in sys.argv)
