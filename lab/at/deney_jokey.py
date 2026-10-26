# OXXai at yarışı laboratuvarı — 🏇 jokey/ahır deney masası (elle çalıştırılır; gece akışının parçası değil).
# v4'ün iki katlı kapısı (lab/at/deney4.py: Masa, gecer, bootstrap) aynen kullanılır:
#   katların ORTALAMA yalnız-model log-loss'u düşmeli (> 0,0001), ortalama ilk-seçim isabeti düşmemeli, en güncel kat (B)
#   kötüleşmemeli, harman 0,001'den fazla bozulmamalı. Her adımda önceki kabule göre koşu başına eşleştirilmiş ΔLL ve
#   koşu-bootstrap %95 GA (birleşik + kat kat).
# Taban: yayındaki v4 tarifi (gruplar, patlatılmış logit derinlik 2, beta kalibrasyonu). jk_* grupları tek tek eklenir;
# geçen bir sonrakinin tabanı olur. Yalnız ilk-seçim kuralına takılanlar (ΔLL < 0) yeni tabanda bir kez daha denenir.
# Çıktı: data/at/jokeyler.json içindeki "deney" anahtarı (yalnız türetilmiş metrikler).
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney_jokey.py            # deneyler
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney_jokey.py --devam    # yarıda kalan deneyden devam (kayıtlı adımlar atlanır)
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney_jokey.py --sizinti  # jk_* sızıntı testi
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney_jokey.py --ayar     # Bayes PL ayar ızgarası (yalnız A katından önce)
import json, math, os, sys, time

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import veri, ozellik as O, model as M, jokey as J  # noqa: E402
from deney4 import Masa, gecer, KATLAR  # noqa: E402

CIKTI = os.path.join(BURA, "..", "..", "data", "at", "jokeyler.json")
ADLAR_GRUP = {
    "jk_beceri": "beceri: attan arındırılmış jokey/antrenör/at gücü (ortak Bayes Plackett-Luce), jokey z, alan içi ortak güç",
    "jk_ikili": "ikili uyum: jokey–antrenör ve jokey–at birlikteliği (jokeysiz beklentiye göre kalıntı, küçültmeli)",
    "jk_degisim": "jokey değişimi: önceki jokeye göre beceri farkı, yükseltme/düşürme, ilk kez bu ikili",
    "jk_form": "form momentumu: jokey kalıntısı son 14/30 gün, 30 gün − 365 gün z, ahır 30 gün",
    "jk_yuk": "günlük iş yükü: o gün kaç biniş (programdan), tek binişlik gün",
    "jk_uzman": "uzmanlık: jokeyin pist / mesafe kovası / hipodrom kalıntısı − genel",
    "jk_apr": "apranti vekili: az biniş / yeni lisans, × kilo farkı, tecrübe",
    "jk_secim": "üst jokey seçimi: düzenli ahırlarının atları varken bu ata binmesi (× beceri), ahırın ana jokeyi başka atta (terk), ana jokey",
}


def jyaz_deney(kayit):
    try:
        js = json.load(open(CIKTI, encoding="utf-8"))
    except Exception:
        js = {}
    js["deney"] = kayit
    tmp = CIKTI + ".tmp"
    json.dump(js, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, CIKTI)


def _kisalt(r):
    """Kayıt için kova tablolarını at (yalnız özet metrikler)."""
    return {"model": r["model"], "harman": r["harman"], "piyasa": r["piyasa"],
            "katlar": {k: {a: r["katlar"][k][a] for a in ("kosu", "model", "harman", "piyasa")} for k in KATLAR}}


def main(devam=False):
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    print(f"tablo {T['X'].shape} {time.time() - t0:.0f} sn", flush=True)
    masa = Masa(kosular, T)
    adla = lambda gr: [a for a, g in O.TUM_OZELLIKLER if g in gr]
    gr = [g for g in O.SECILI_GRUPLAR if not g.startswith("jk_")]
    egitim = {"yari_omur": None, "gbm_ayar": None, "patlat_ag": tuple(M.PATLAT), "tohumlar": tuple(M.GBM_TOHUM),
              "patlat_gbm": M.PATLAT_GBM}
    kal = dict(M.KAL_AYAR)
    E = masa.egit(adla(gr), **egitim)
    cur, v_cur = masa.ozet(*masa.tahmin(E, kal)[:2])
    v_taban = v_cur
    kayit = {"olusturma": None, "katlar": masa.B["tarih"]["katlar"], "kapi": "deney4 iki katlı kapı", "adimlar": [
        {"no": 0, "deney": "v4 taban (yayındaki tarif)", "gecti": None, **_kisalt(cur)}],
        "ayar": {"onsel": J.JK_ONSEL, "surukle_gun": {k: round(v * 365, 4) for k, v in J.JK_SURUKLE.items()},
                 "kademe": list(J.JK_KADEME)}}
    print(0, cur["model"], cur["harman"], {k: cur["katlar"][k]["model"] for k in KATLAR}, f"{time.time() - t0:.0f} sn", flush=True)

    def kaydet():
        kayit["olusturma"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        jyaz_deney(kayit)
    no = [0]
    yapilan = {}   # deney adı -> (geçti, ΔLL)
    if devam:   # yarıda kalan koşudan devam: kayıtlı adımlar atlanır, kabul edilenlerle güncel taban yeniden kurulur
        eski = (json.load(open(CIKTI, encoding="utf-8")).get("deney") or {})
        if eski.get("adimlar"):
            kayit = dict(eski, adimlar=[dict(eski["adimlar"][0], **_kisalt(cur))] + eski["adimlar"][1:])
            for s_ in eski["adimlar"][1:]:
                yapilan[s_["deney"]] = (s_["gecti"], s_["fark_model"]["dll"])
                if s_["gecti"]:
                    gr = gr + [s_["deney"].split(" — ")[0].replace("yeniden (yeni tabanda): ", "")]
            no[0] = eski["adimlar"][-1]["no"]
            if len(yapilan) and any(v[0] for v in yapilan.values()):
                cur, v_cur = masa.ozet(*masa.tahmin(masa.egit(adla(gr), **egitim), kal)[:2])
            print("devam:", no[0], "adım kayıtlı; güncel gruplar:", [g for g in gr if g.startswith("jk_")], cur["model"],
                  f"{time.time() - t0:.0f} sn", flush=True)
    kaydet()

    def dene(ad, gr2):
        nonlocal cur, v_cur
        if ad in yapilan:
            return yapilan[ad]
        E2 = masa.egit(adla(gr2), **egitim)
        r, v = masa.ozet(*masa.tahmin(E2, kal)[:2])
        no[0] += 1
        fm = masa.fark(v, v_cur, "model"); fh = masa.fark(v, v_cur, "harman")
        ok = gecer(r, cur)
        kayit["adimlar"].append({"no": no[0], "deney": ad, "gecti": ok, "fark_model": fm, "fark_harman": fh, **_kisalt(r)})
        print(no[0], ad[:60], "GEÇTİ" if ok else "kaldı", r["model"], r["harman"],
              {k: r["katlar"][k]["model"] for k in KATLAR}, "ΔLL", fm["dll"], fm["ga95"], "A", fm["A"]["dll"], "B",
              fm["B"]["dll"], f"{time.time() - t0:.0f} sn", flush=True)
        if ok:
            cur, v_cur = r, v
        kaydet()
        return ok, fm["dll"]

    yakin = []
    for g in J.JK_GRUPLAR:
        ok, d = dene(f"{g} — {ADLAR_GRUP[g]}", gr + [g])
        if ok and g not in gr:
            gr = gr + [g]
        elif d < 0:
            yakin.append(g)
    for g in yakin:   # tek tekrar, yeni tabanda (deney4'teki 8a/8b ile aynı usul)
        ok, _ = dene(f"yeniden (yeni tabanda): {g}", gr + [g])
        if ok and g not in gr:
            gr = gr + [g]
    secilen = list(dict.fromkeys(g for g in gr if g.startswith("jk_")))
    kayit["secim"] = secilen
    kayit["toplam"] = {"model": masa.fark(v_cur, v_taban, "model"), "harman": masa.fark(v_cur, v_taban, "harman")}
    kayit["sure_sn"] = round(time.time() - t0)
    kaydet()
    print("bitti, seçilen:", secilen, f"{time.time() - t0:.0f} sn")


def sizinti():
    """jk_* sütunları için sızıntı testi: (1) kesme: D gününün özellikleri yalnız D'den önceki koşularla kurulan durumla
    tam tabloyla aynı; (2) D gününün sonuçları (sıra, derece, oran) karıştırılınca D'nin özellikleri değişmiyor;
    (3) gün içi koşu sırası ters çevrilince aynı."""
    import random
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    sut = [O.TUM_ADLAR.index(a) for a in J.JK_ADLAR]
    gunler = sorted({k["tarih"] for k in kosular})
    rng = np.random.default_rng(11)
    hata = []
    for D in sorted(rng.choice(gunler[60:], size=4, replace=False)):
        once = [k for k in kosular if k["tarih"] < D]
        bugun = [k for k in kosular if k["tarih"] == D]
        _, durum = O.tablo_kur(once, adlar=O.TUM_ADLAR)
        Xd = np.vstack([durum.ozellik(k, J.JK_ADLAR) for k in bugun])
        bas = sum(len(k["atlar"]) for k in once)
        Xt = T["X"][bas: bas + len(Xd)][:, sut]
        ok1 = np.allclose(Xd, Xt, atol=1e-9)
        karisik = json.loads(json.dumps(bugun))
        for k in karisik:
            s = [a["sira"] for a in k["atlar"]]; random.Random(1).shuffle(s)
            o = [a["oran"] for a in k["atlar"]]; random.Random(2).shuffle(o)
            for a, x, y in zip(k["atlar"], s, o):
                a["sira"], a["oran"], a["sure"] = x, y, None
        Xk = np.vstack([durum.ozellik(k, J.JK_ADLAR) for k in karisik])
        ok2 = np.allclose(Xd, Xk, atol=1e-12)
        Xr = [durum.ozellik(k, J.JK_ADLAR) for k in reversed(bugun)]
        ok3 = np.allclose(Xd, np.vstack(list(reversed(Xr))), atol=1e-12)
        print(f"{D}: {len(Xd)} satır · kesme {'AYNI' if ok1 else 'FARKLI'} · sonuç karıştırma {'AYNI' if ok2 else 'FARKLI'} · "
              f"ters sıra {'AYNI' if ok3 else 'FARKLI'}", flush=True)
        if not (ok1 and ok2 and ok3):
            hata.append(D)
    print(f"bitti {time.time() - t0:.0f} sn")
    if hata:
        print("SIZINTI ŞÜPHESİ:", hata)
        sys.exit(1)
    print("SIZINTI YOK (jk_*)")


def ayar():
    """Bayes PL hiperparametreleri: reytingin tek başına koşu öncesi kazanma log-loss'u, YALNIZ 2025-03-01 → 2025-10-31
    (A katından önce; sınama katlarına bakılmaz). Küçük ızgara; en iyisi jokey.py'deki varsayılanlardır."""
    import itertools
    kosular, _ = veri.sonuclari_yukle()
    bas, son = M.ISINMA_SONU, M.KAT_BAS

    def calis(on, sur, kad):
        J.JK_ONSEL.update(on); J.JK_SURUKLE.update(sur); J.JK_KADEME = kad
        jd, ll = J.JokeyDurum(), []
        for x in kosular:
            if bas <= x["tarih"] < son:
                th, _ = jd.theta(x, J.gun_no(x["tarih"]))
                p = J._softmax(th)
                ll.append(-math.log(p[next(i for i, a in enumerate(x["atlar"]) if a["sira"] == 1)]))
            jd.guncelle(x)
        return sum(ll) / len(ll)
    sonuc = []
    for aj, jj, tt, sm, kad in itertools.product((0.4, 0.8, 1.6), (0.03, 0.12, 0.3, 0.6), (0.03, 0.06, 0.12), (0.5, 1, 2, 4),
                                                 ((1.0,), (1.0, 0.5, 0.25))):
        on = {"at": aj, "jokey": jj, "antrenor": tt}
        sur = {"at": sm * aj / 2 / 365, "jokey": sm * jj / 3 / 365, "antrenor": sm * tt / 3 / 365}
        sonuc.append((round(calis(on, sur, kad), 4), on, sm, kad))
        print(*sonuc[-1], flush=True)
    print("en iyi:", sorted(sonuc, key=lambda z: z[0])[:5])


if __name__ == "__main__":
    sizinti() if "--sizinti" in sys.argv else (ayar() if "--ayar" in sys.argv else main(devam="--devam" in sys.argv))
