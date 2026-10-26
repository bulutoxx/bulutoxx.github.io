# OXXai at yarışı laboratuvarı — v3 deney masası (elle çalıştırılır; gece akışının parçası değildir).
# Taban: yayındaki v2 tarifi (aylık walk-forward, zaman ağırlığı, doğrusal + LightGBM, üst uç kalibrasyonu).
# Her adım AYNI sınama dilimiyle (son %30, tam oranlı koşular) ölçülür. Kapı:
#   yalnız-model sınama log-loss'u düşmeli VE yalnız-model ilk-seçim isabeti düşmemeli (harman adımlarında: harman).
# Her adım için önceki kabul edilen adıma göre koşu başına eşleştirilmiş ΔLL ve koşu-bootstrap %95 güven aralığı.
# Çıktı: data/at/deneyler_v3.json (yalnız türetilmiş metrikler).
#   AT_KAYNAK=/yol/tjk-data python lab/at/deney3.py
import json, os, sys, time

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import veri, ozellik as O, model as M  # noqa: E402

B_SAYI = 2000


def bootstrap(d, n=B_SAYI, tohum=7):
    """Koşu başına farkların ortalaması için koşu-bootstrap %95 GA."""
    r = np.random.default_rng(tohum)
    idx = r.integers(0, len(d), size=(n, len(d)))
    ort = d[idx].mean(1)
    return [round(float(np.percentile(ort, 2.5)), 4), round(float(np.percentile(ort, 97.5)), 4)]


def kosu_vektor(p, Ks):
    w = Ks.y > 0
    ll = -np.log(np.clip(p[w], 1e-12, 1))
    ilk = np.array([Ks.y[Ks.bas[r] + int(np.argmax(p[Ks.bas[r]: Ks.bas[r] + Ks.n[r]]))] > 0 for r in range(Ks.R)], float)
    return ll, ilk


def olc(T, kosular, gruplar, **kw):
    adlar = [a for a, g in O.TUM_OZELLIKLER if g in gruplar]
    sut = [T["adlar"].index(a) for a in adlar]
    T2 = dict(T); T2["X"] = T["X"][:, sut]; T2["adlar"] = adlar
    r = M.sina(T2, kosular, "aylik", gbm=True, **kw)
    Ks = r["Ks"]; pm, ph = r["p"]
    v = {"model": kosu_vektor(pm, Ks), "harman": kosu_vektor(ph, Ks), "piyasa": kosu_vektor(Ks.q, Ks),
         "piyasa_keskin": kosu_vektor(r["p_ek"]["keskin"], Ks)}
    if "harman_artik" in r["metrik"]:
        v["harman_artik"] = kosu_vektor(r["p_ek"]["harman_artik"], Ks)
    ozet = {k: {"ll": m["log_loss"], "brier": m["brier"], "ilk": m["ilk_secim_isabet"], "ilk2": m["ilk_iki_ikisi_de_ilk2"],
                "p50": [m["p>=0.50"]["secim"], m["p>=0.50"]["isabet"]]} for k, m in r["metrik"].items()}
    ozet["sira_ll"] = r.get("sira_ll")
    ozet["kovalar_model"] = r["kovalar"]["model"]
    ozet["henery"] = [{"g": x.gam, "d": x.dlt, "gm": x.gam_m, "dm": x.dlt_m, "bq": round(x.bq, 3),
                       "ab": [round(x.alfa, 3), round(x.beta, 3)]} for x in r["modeller"]]
    return ozet, v


def fark(v_yeni, v_eski, anahtar):
    d = v_yeni[anahtar][0] - v_eski[anahtar][0]
    return {"dll": round(float(d.mean()), 4), "ga95": bootstrap(d),
            "d_ilk": round(float(v_yeni[anahtar][1].mean() - v_eski[anahtar][1].mean()), 4)}


def main():
    t0 = time.time()
    kosular, _ = veri.sonuclari_yukle()
    T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
    print(f"tablo {T['X'].shape} {time.time() - t0:.0f} sn", flush=True)
    zemin_kosu = sum(1 for k in kosular if k.get("zemin"))
    print("pist durumu eşlenen koşu:", zemin_kosu, flush=True)
    adimlar = []
    gr = list(O.SECILI_GRUPLAR)
    taban, v_taban = olc(T, kosular, gr, henery=True)
    adimlar.append({"no": 0, "deney": "v2 taban (yayındaki tarif)", "gecti": None, **taban})
    print(0, taban["model"], taban["harman"], f"{time.time() - t0:.0f} sn", flush=True)
    cur, v_cur = taban, v_taban

    def adim(no, ad, r, v, anahtar="model"):
        nonlocal cur, v_cur
        fm = fark(v, v_cur, "model"); fh = fark(v, v_cur, "harman")
        ok = (r[anahtar]["ll"] < cur[anahtar]["ll"] - 1e-4 and r[anahtar]["ilk"] >= cur[anahtar]["ilk"]
              and (anahtar != "model" or r["harman"]["ll"] <= cur["harman"]["ll"] + 0.001))
        adimlar.append({"no": no, "deney": ad, "gecti": ok, "olcut": anahtar, "fark_model": fm, "fark_harman": fh, **r})
        print(no, ad, "GEÇTİ" if ok else "kaldı", r["model"], r["harman"], fm, fh, f"{time.time() - t0:.0f} sn", flush=True)
        if ok:
            cur, v_cur = r, v
        return ok

    # B1: pist durumu (aynanın kesik "Çok"/"Biraz" değerleri ayrı kategori; tarih+hipodrom+koşu ile eşlendi)
    r, v = olc(T, kosular, gr + ["zemin"], henery=True)
    if adim(1, "B1: pist durumu (zemin sırası, zemin uyumu, zemin×kilo, zemin×form)", r, v):
        gr = gr + ["zemin"]
    # B2: Beyer tarzı hız figürü
    r, v = olc(T, kosular, gr + ["hiz3"], henery=True)
    if adim(2, "B2: hız figürü (par + projeksiyonlu, küçültmeli gün değişkeni; en iyi/son/ort3/eğilim/alana göre)", r, v):
        gr = gr + ["hiz3"]
    # B3: kalıntı GBM (init_score = log q) yalnız harman için
    r, v = olc(T, kosular, gr, henery=True, artik=True)
    r2 = dict(r); r2["harman"] = r["harman_artik"]
    v2 = dict(v); v2["harman"] = v["harman_artik"]
    artik_ok = adim(3, "B3: kalıntı LightGBM (init_score = log q) harmana eklenir", r2, v2, anahtar="harman")
    son = adimlar[-1]
    son["fark_harman_artik_vs_harman"] = fark({"h": v["harman_artik"]}, {"h": v["harman"]}, "h")
    kayit = {"olusturma": time.strftime("%Y-%m-%dT%H:%M:%S"), "secili_gruplar": gr, "artik": artik_ok,
             "pist_durumu_eslenen_kosu": zemin_kosu, "adimlar": adimlar,
             "piyasa_keskin_vs_piyasa": fark(v_cur, v_cur, "piyasa_keskin") | {
                 "dll": round(float((v_cur["piyasa_keskin"][0] - v_cur["piyasa"][0]).mean()), 4),
                 "ga95": bootstrap(v_cur["piyasa_keskin"][0] - v_cur["piyasa"][0])},
             "harman_vs_keskin": {"dll": round(float((v_cur["harman"][0] - v_cur["piyasa_keskin"][0]).mean()), 4),
                                  "ga95": bootstrap(v_cur["harman"][0] - v_cur["piyasa_keskin"][0])},
             "harman_vs_piyasa": {"dll": round(float((v_cur["harman"][0] - v_cur["piyasa"][0]).mean()), 4),
                                  "ga95": bootstrap(v_cur["harman"][0] - v_cur["piyasa"][0])},
             "model_vs_piyasa": {"dll": round(float((v_cur["model"][0] - v_cur["piyasa"][0]).mean()), 4),
                                 "ga95": bootstrap(v_cur["model"][0] - v_cur["piyasa"][0])},
             "not": "Kapı: yalnız-model log-loss düşmeli ve ilk-seçim isabeti düşmemeli; ΔLL = yeni − önceki kabul (koşu başına), "
                    f"%95 GA koşu-bootstrap ({B_SAYI} örnek)."}
    json.dump(kayit, open(os.path.join(BURA, "..", "..", "data", "at", "deneyler_v3.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"bitti {time.time() - t0:.0f} sn; seçili: {gr}")


if __name__ == "__main__":
    main()
