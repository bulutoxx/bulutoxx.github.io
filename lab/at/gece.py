# BULUTOXX at yarışı laboratuvarı — gece boru hattı.
# 1) Aynayı sığ klonla/güncelle (yalnız github.com/cenkozgur/tjk-data; tjk.org'a istek YOK)
# 2) Sızıntısız özellikler + tam yeniden eğitim + zaman sıralı sınama
# 3) KAPI: yeni tarif ancak aynı sınama koşularında yalnız-model log-loss'unu düşürür, ilk-seçim isabetini bozmaz
#    ve harmanı kötüleştirmezse kabul; tarif aynıysa yeni veriyle yeniden eğitim (bozulma korumalı)
# 4) Bugün/yarın programları için tahminleri KİLİTLE (data/at/tahmin/<tarih>.json; bir kez yazılır, ezilmez)
# 5) Sonucu gelen kilitli tahminleri puanla (data/at/karne.json)
# 6) data/at/model.json ve lab/at/RAPOR.md yaz
# Depoya yalnız türetilmiş sayılar + at adları/koşu kimlikleri yazılır; ham veri yazılmaz.
import argparse, json, math, os, subprocess, sys
from datetime import date, datetime, timedelta, timezone

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.abspath(os.path.join(BURA, "..", ".."))
sys.path.insert(0, BURA)
os.environ.setdefault("AT_KAYNAK", os.path.join(KOK, "_tjk-data"))

import veri, ozellik, model as M  # noqa: E402

CIKTI = os.path.join(KOK, "data", "at")
TAHMIN = os.path.join(CIKTI, "tahmin")
RAPOR = os.path.join(BURA, "RAPOR.md")
GBM_DOSYA = os.path.join(CIKTI, "gbm_uretim.txt")      # yayın modelinin ağaçları (uygulama okumaz)
IZ_DOSYA = os.path.join(CIKTI, "sinama_izi.json")     # kapı için koşu başına sınama izi
DENEY_DOSYA = os.path.join(CIKTI, "deneyler.json")
YENILEME_GUN = 7   # aynı tarifte yayın katsayılarının yenilenme aralığı (gün)
TAKIP = [("2026-10-25", "İstanbul", 5)]   # raporda kalıcı izlenen örnek koşu(lar)

IFADE = {  # özellik -> (değeri koşu ortalamasından YÜKSEKSE, DÜŞÜKSE) — yön katkının işaretinden ayrı seçilir
    "yeni": ("ilk koşusu, geçmiş verisi yok", ""),
    "n_kosu": ("çok koşmuş", "az koşmuş, gelişime açık"),
    "skor_son": ("son koşusunda iyi derece", "son koşusunda geride kaldı"),
    "skor3": ("son 3 koşu formu iyi", "son 3 koşu formu zayıf"),
    "skor5": ("son 5 koşu formu iyi", "son 5 koşu formu zayıf"),
    "skor10": ("son 10 koşu formu iyi", "son 10 koşu formu zayıf"),
    "galibiyet10": ("son koşularda kazanma oranı yüksek", "son koşularda kazanamadı"),
    "ilk3_10": ("sık sık ilk 3'te", "nadiren ilk 3'te"),
    "geri_son": ("son koşuda kazananın epey gerisinde", "son koşuda kazanana yakın bitirdi"),
    "geri3": ("son koşularda kazananın gerisinde", "son koşularda kazanana yakın"),
    "piyasa_son": ("son koşusunda piyasa onu öne çıkarmıştı", "son koşusunda piyasa ilgisi düşüktü"),
    "piyasa3": ("son koşularında piyasanın gözdesiydi", "son koşularında piyasa ilgisi düşüktü"),
    "log_gun": ("uzun süredir koşmuyor", "sık koşuyor"),
    "uzun_ara": ("uzun aradan dönüyor", ""),
    "pist_uyum": ("bu pistte iyi koşuyor", "bu pistte zayıf"),
    "pist_payi": ("bu pist tecrübesi fazla", "bu pistte az tecrübeli"),
    "mesafe_uyum": ("bu mesafede başarılı", "bu mesafede zayıf"),
    "mesafe_degisim": ("mesafe değişiyor", ""),
    "hipodrom_uyum": ("bu hipodromda başarılı", "bu hipodromda zayıf"),
    "sinif_degisim": ("sınıf yükseliyor (daha zor koşu)", "sınıf düşüyor (daha kolay koşu)"),
    "kilo_fark": ("alan ortalamasından ağır kilo", "alan ortalamasından hafif kilo"),
    "kilo_degisim": ("kilosu arttı", "kilosu azaldı"),
    "yas2": ("2 yaşında", ""), "yas3": ("3 yaşında", ""), "yas6p": ("6 yaş ve üstü", ""),
    "jokey_gal60": ("jokeyi son 60 günde formda", "jokeyinin son 60 günü zayıf"),
    "jokey_ae": ("jokeyi piyasa beklentisinin üstünde kazanıyor", "jokeyi piyasa beklentisinin altında"),
    "antrenor_gal60": ("antrenörü son 60 günde formda", "antrenörünün son 60 günü zayıf"),
    "antrenor_ae": ("antrenörü piyasa beklentisinin üstünde", "antrenörü piyasa beklentisinin altında"),
    "jokey_at_n": ("jokeyiyle çok koştu", "jokeyiyle az koştu"),
    "jokey_at_uyum": ("bu jokeyle iyi sonuçlar almış", "bu jokeyle sonuçları zayıf"),
    "jokey_degisti": ("jokey değişti", ""),
    "alan_x_form": ("", ""),
    "pz_ewma": ("son koşularında piyasa onu öne çıkarıyordu", "son koşularında piyasa ilgisi düşüktü"),
    "pz_en_iyi5": ("yakın geçmişte piyasanın gözdesi olmuştu", "yakın geçmişte piyasa ilgisi hep düşüktü"),
    "p_sira_son": ("son koşusunda piyasada geride sıralanmıştı", "son koşusunda piyasada önde sıralanmıştı"),
    "p_sira3": ("son koşularında piyasada geride", "son koşularında piyasada önde"),
    "fav_son": ("son koşusunda favoriydi", ""),
    "yenilen_fav": ("son koşusunda favoriyken kazanamadı", ""),
    "piyasa_ustu": ("piyasanın beklediğinden iyi koşuyor", "piyasanın beklediğinden kötü koşuyor"),
    "piyasa_reyting": ("piyasa gözünde rakiplerinden güçlü", "piyasa gözünde rakiplerinden zayıf"),
    "piyasa_yok": ("geçmiş oran bilgisi yok", ""),
    "r_at": ("yarış reytingi yüksek", "yarış reytingi düşük"),
    "r_jokey": ("jokey reytingi yüksek", "jokey reytingi düşük"),
    "r_antrenor": ("antrenör reytingi yüksek", "antrenör reytingi düşük"),
    "r_at_belirsiz": ("reytingi henüz belirsiz (az koşu)", ""),
    "r_at_alan": ("reytingi alanın üstünde", "reytingi alanın altında"),
    "handikap": ("", ""), "maiden": ("", ""), "sinif_r": ("", ""),
    "kilo_hnd": ("handikapta üst kilo (resmî puanı yüksek)", "handikapta alt kilo"),
    "sinif_r_degisim": ("sınıf yükseliyor (alan düzeyi)", "sınıf düşüyor (alan düzeyi)"),
    "at_ustu_sinif": ("reytingi bu sınıfın üstünde", "reytingi bu sınıfın altında"),
    "hiz_son": ("son hız puanı yüksek", "son hız puanı düşük"), "hiz_en_iyi": ("en iyi hız puanı yüksek", "en iyi hız puanı düşük"),
    "hiz_ort3": ("hız puanları yüksek", "hız puanları düşük"), "hiz_yok": ("hız puanı yok", ""),
    "hiz_pist": ("bu pistte daha hızlı", "bu pistte daha yavaş"),
    "skor_sonum": ("yakın dönem formu iyi", "yakın dönem formu zayıf"),
    "geri_sonum": ("yakın dönemde kazananın gerisinde", "yakın dönemde kazanana yakın"),
    "geri_en_iyi5": ("son 5 koşuda kazanana hiç yaklaşamadı", "son 5 koşuda kazanana çok yaklaştı"),
    "jokey_pz60": ("jokeyi son dönemde gözde atlara biniyor", "jokeyi son dönemde gözde olmayan atlara biniyor"),
    "antrenor_pz60": ("ahırının atları son dönemde gözde", "ahırının atları son dönemde gözde değil"),
    "jokey_r_degisim": ("daha güçlü bir jokeye geçti", "daha zayıf bir jokeye geçti"),
    "ekuri": ("koşuda aynı antrenörden başka at var", ""),
}


def jyaz(yol, veri_, sikisik=False):
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


def ayna_guncelle(kaynak):
    """Aynayı sığ klonlar ya da günceller. Yalnız GitHub'daki herkese açık ayna."""
    try:
        if os.path.isdir(os.path.join(kaynak, ".git")):
            subprocess.run(["git", "-C", kaynak, "fetch", "-q", "--depth", "1", "origin", "HEAD"], check=True, timeout=600)
            subprocess.run(["git", "-C", kaynak, "reset", "-q", "--hard", "FETCH_HEAD"], check=True, timeout=120)
        else:
            subprocess.run(["git", "clone", "-q", "--depth", "1", veri.AYNA_URL, kaynak], check=True, timeout=900)
        return "güncellendi"
    except Exception as e:
        return f"güncellenemedi ({type(e).__name__}); mevcut kopya kullanılıyor"


# ---------------------------------------------------------------- tahmin
def model_yukle(uj):
    """Yayın modelini (JSON + varsa GBM dosyası) yükler. LightGBM yoksa model kendi doğrusal yedeğine düşer."""
    metin = None
    if uj.get("gbm"):
        try:
            metin = open(GBM_DOSYA, encoding="utf-8").read()
        except Exception:
            metin = None
    return M.Model.yukle(uj, metin)


def kosu_tahmini(m, kosu, durum, yayin_modu):
    X = durum.ozellik(kosu, m.adlar)
    K = M.Kume(X, np.zeros(len(X)), np.zeros(len(X)), np.zeros(len(X)), np.zeros(len(X), int))
    q = veri.piyasa_q([a["oran"] for a in kosu["atlar"]])
    if q is not None and yayin_modu == "model+piyasa":
        p = m.p_harman(X, K, np.asarray(q)); mod = "model+piyasa"
    elif q is not None:
        p = np.asarray(q); mod = "yalnız piyasa (model sınamada piyasayı geçemedi)"
    else:
        p = m.p_model(X, K); mod = "yalnız model (piyasa oranı henüz yok)"
    so = M.sirali_olasiliklar(p, m.gam, m.dlt)
    katki = m.katki(X)
    sapma = X - X.mean(0)

    def ifade(i, k):
        e = IFADE.get(m.adlar[k], ("", ""))
        return e[0] if sapma[i, k] > 0 else e[1]
    atlar = []
    for i, a in enumerate(kosu["atlar"]):
        o = np.argsort(-katki[i])
        lehte = [ifade(i, k) for k in o if katki[i, k] > 0.04 and ifade(i, k)]
        tekil = {}
        for x in lehte:   # aynı anlamdaki ifadeleri (ör. iki "sınıf düşüyor") tekille
            tekil.setdefault(" ".join(x.split()[:2]), x)
        lehte = list(tekil.values())[:2]
        aleyh = [ifade(i, k) for k in o[::-1] if katki[i, k] < -0.12 and ifade(i, k)][:1]
        ger = "; ".join(lehte) if lehte else "belirgin artısı yok"
        if aleyh:
            ger += " · dikkat: " + aleyh[0]
        atlar.append({"no": a["no"], "ad": a["ad"], "p_kazanma": round(float(p[i]), 4),
                      "p_ilk2": round(float(min(so["ilk2"][i], 1)), 4),
                      "p_ilk3": round(float(so["ilk3"][i]), 4) if "ilk3" in so else None, "gerekce": ger})
    E = so["ikili"]
    i, j = np.unravel_index(np.argmax(E), E.shape)
    atlar.sort(key=lambda d: -d["p_kazanma"])
    return {"kosu_id": f'{kosu["tarih"]}/{kosu["hipodrom"]}/{kosu["kosu"]}', "hipodrom": kosu["hipodrom"],
            "kosu": kosu["kosu"], "saat": kosu.get("saat"), "mesafe": kosu["mesafe"], "pist": kosu["pist"],
            "sinif": kosu["sinif"], "mod": mod, "atlar": atlar,
            "ikili_onerisi": {"sira": [kosu["atlar"][i]["no"], kosu["atlar"][j]["no"]], "p": round(float(E[i, j]), 4)}}


def kilitle(gunler, son_sonuc, m, durum, yayin_modu, surum):
    yazilan = []
    for t in gunler:
        yol = os.path.join(TAHMIN, t + ".json")
        if os.path.exists(yol) or t <= son_sonuc:
            continue
        prog = veri.program_yukle(t)
        if not prog:
            continue
        simdi_tr = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
        ks = []
        for k in prog:
            kt = kosu_tahmini(m, k, durum, yayin_modu)
            # koşu saati geçtiyse kilit "canlı" sayılmaz (sızıntısızdır ama koşudan sonra atılmıştır)
            kt["kosudan_once"] = not (k.get("saat") and f"{t} {k['saat']}" <= simdi_tr)
            ks.append(kt)
        jyaz(yol, {"tarih": t, "kilit_zamani": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "kilit_zamani_tsi": simdi_tr, "model_surumu": surum,
                   "not": "Hobi amaçlı olasılıklar; garanti değildir · 18+. kosudan_once=false olan koşular canlı karneye sayılmaz.",
                   "kosular": ks})
        yazilan.append(t)
    return yazilan


# ---------------------------------------------------------------- karne
def puanla(kosular):
    karne = joku(os.path.join(CIKTI, "karne.json"), None) or {"gunler": {}, "kosular": []}
    sonuc = {(k["tarih"], k["hipodrom"], k["kosu"]): k for k in kosular}
    yeni = []
    for f in sorted(os.listdir(TAHMIN)) if os.path.isdir(TAHMIN) else []:
        t = f[:-5]
        if not f.endswith(".json") or t in karne["gunler"]:
            continue
        kt = joku(os.path.join(TAHMIN, f), {})
        satir = []
        for kp in kt.get("kosular", []):
            r = sonuc.get((t, kp["hipodrom"], kp["kosu"]))
            if not r:
                continue
            sira = {a["ad"]: a["sira"] for a in r["atlar"]}
            kaz = next(a["ad"] for a in r["atlar"] if a["sira"] == 1)
            ikinci = next((a["no"] for a in r["atlar"] if a["sira"] == 2), None)
            atl = [a for a in kp["atlar"] if a["ad"] in sira]
            if not atl:
                continue
            s = sum(a["p_kazanma"] for a in atl)  # koşmayan çıkarsa yeniden ölçekle
            pk = next((a["p_kazanma"] / s for a in atl if a["ad"] == kaz), None)
            if pk is None:
                continue
            ilk = max(atl, key=lambda a: a["p_kazanma"])
            kaz_no = next(a["no"] for a in r["atlar"] if a["sira"] == 1)
            satir.append({"kosu_id": kp["kosu_id"], "mod": kp["mod"], "kosudan_once": kp.get("kosudan_once", True), "kazanan": kaz, "p_kazanan": round(pk, 4),
                          "log_loss": round(-math.log(max(pk, 1e-12)), 4), "ilk_secim": ilk["ad"],
                          "ilk_secim_tuttu": ilk["ad"] == kaz,
                          "ikili_tuttu": kp["ikili_onerisi"]["sira"] == [kaz_no, ikinci],
                          "pw": [[round(a["p_kazanma"] / s, 4), int(a["ad"] == kaz)] for a in atl]})
        if not satir:
            continue
        karne["kosular"].extend(satir)
        canli = [x for x in satir if x["kosudan_once"]] or satir
        karne["gunler"][t] = {"canli": any(x["kosudan_once"] for x in satir), "kosu": len(canli), "log_loss": round(float(np.mean([x["log_loss"] for x in canli])), 4),
                              "ilk_secim_isabet": round(float(np.mean([x["ilk_secim_tuttu"] for x in canli])), 4),
                              "ikili_isabet": round(float(np.mean([x["ikili_tuttu"] for x in canli])), 4)}
        yeni.append(t)
    ks = [x for x in karne["kosular"] if x.get("kosudan_once", True)]
    karne["gecikmeli_kilit_sayisi"] = sum(1 for x in karne["kosular"] if not x.get("kosudan_once", True))
    if ks:
        pw = np.array([v for x in ks for v in x["pw"]])
        karne["toplam"] = {"kosu": len(ks), "log_loss": round(float(np.mean([x["log_loss"] for x in ks])), 4),
                           "ilk_secim_isabet": round(float(np.mean([x["ilk_secim_tuttu"] for x in ks])), 4),
                           "ikili_isabet": round(float(np.mean([x["ikili_tuttu"] for x in ks])), 4),
                           "kovalar": M.kovalar(pw[:, 0], pw[:, 1])}
    karne["guncelleme"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    jyaz(os.path.join(CIKTI, "karne.json"), karne)
    return karne, yeni


# ---------------------------------------------------------------- rapor
def _y(v):
    return "–" if v is None else (f"%{100 * v:.1f}" if isinstance(v, float) and v <= 1 else str(v))


def _ll(v):
    return "–" if v is None else f"{v:.4f}"


def _deney_tablosu(a):
    dj = joku(DENEY_DOSYA)
    if not dj or not dj.get("adimlar"):
        a("- Deney kaydı yok (`lab/at/deney.py` elle çalıştırılır).")
        return
    a("Hepsi aynı sınama diliminde (son %30, aynı koşular). Kapı: yalnız-model log-loss düşmeli **ve** yalnız-model "
      "ilk seçim isabeti düşmemeli; geçen adım bir sonrakinin tabanı olur.")
    a("")
    a("| # | deney | sonuç | yalnız model: log-loss / Brier / ilk seçim / ilk iki | yalnız model p≥.30 · p≥.50 (seçim, isabet) | harman: log-loss / ilk seçim |")
    a("|---|---|---|---|---|---|")
    for s in dj["adimlar"]:
        m, h = s["model"], s["harman"]
        sonuc = "taban" if s["gecti"] is None else ("✅ kaldı" if s["gecti"] else "❌ elendi")
        a(f"| {s['no']} | {s['deney']} | {sonuc} | {m['ll']:.4f} / {m['brier']:.4f} / {_y(m['ilk'])} / {_y(m['ilk2'])} | "
          f"{m['p30'][0]}, {_y(m['p30'][1])} · {m['p50'][0]}, {_y(m['p50'][1])} | {h['ll']:.4f} / {_y(h['ilk'])} |")
    a("")
    a(f"Piyasa (aynı koşular): log-loss {dj['adimlar'][0]['piyasa']['ll']:.4f}, favori ilk seçim {_y(dj['adimlar'][0]['piyasa']['ilk'])}. "
      f"Deney kaydı: `data/at/deneyler.json` ({dj.get('olusturma', '')}).")


def rapor_yaz(mj, karne, bugun, ayna_durumu):
    d = mj["degerlendirme"]; mt = d["metrik"]; kp = mj["kapi"]; kap = mj["kapsam"]
    L = []
    a = L.append
    a("# BULUTOXX 🐎 At Yarışı Laboratuvarı — Rapor")
    a("")
    a(f"_Otomatik üretildi: {mj['guncelleme']} · model sürümü `{mj['surum']}` · hobi amaçlıdır, garanti değildir · 18+_")
    a("")
    hp = d["harman_eksi_piyasa"]; mp = d["model_eksi_piyasa"]
    anlamli = hp["ll_fark"] + 2 * hp["std_hata"] < 0
    dj = joku(DENEY_DOSYA) or {}
    v1 = (dj.get("adimlar") or [{}])[0]
    a("## Özet: v2 güncellemesi (25.10.2026)")
    a("")
    a("Uygulamadaki **sabah tahminleri yalnız modeldir** (sabah programında ganyan oranı yok). Bu yüzden bu turda hedef, "
      "oransız (yalnız geçmişe dayalı) tahmini güçlendirmekti. Yapılanlar:")
    a("")
    if v1.get("model"):
        a(f"- **Yalnız model (sabah) sınama log-loss'u {v1['model']['ll']:.4f} → {mt['model']['log_loss']:.4f}; ilk seçim isabeti "
          f"{_y(v1['model']['ilk'])} → {_y(mt['model']['ilk_secim_isabet'])}** (aynı {d['kosu_sayisi']['sinama']:,} sınama koşusu). "
          f"Piyasa favorisi hâlâ önde: {_y(mt['favori']['ilk_secim_isabet'])}, piyasa log-loss {mt['piyasa']['log_loss']:.4f}.")
        a(f"- Model + piyasa harmanı: log-loss {v1['harman']['ll']:.4f} → {mt['harman']['log_loss']:.4f} "
          f"(piyasaya göre {hp['ll_fark']:+.4f} ± {hp['std_hata']:.4f}; " + ("anlamlı iyileşme" if anlamli else "küçük, gürültü sınırında") + ").")
    a("- Yeni bilgiler: atın **geçmiş koşulardaki piyasa değerlendirmesi** (oran hafızası: üstel ortalama, piyasa sırası, yenilen favori, "
      "piyasanın beklediğinden iyi/kötü koşma, rakiplere göre aktarılan \"piyasa reytingi\"), her koşudan sonra güncellenen "
      "**Plackett-Luce reytingleri** (at + jokey + antrenör), **sayısal sınıf** (koşu türü, alanın reyting düzeyi, handikapta kilo), "
      "**zaman sönümlü form**.")
    a("- Eğitim: sınamada her ay **yalnız o aydan önceki veriyle yeniden eğitim** (walk-forward; gece akışı da her gün böyle eğitir), "
      "eski koşulara daha az ağırlık (yarı ömür 180 gün), ve doğrusal modelin yanına **LightGBM** (koşu içi softmax amacıyla) eklendi; "
      "ikisinin karışımı, sıcaklık ve %25 üstü olasılıklar için ayrı bir \"üst uç\" eğimi son 90 günde kalibre edilir.")
    a("- Kapı artık **yalnız-model** ölçülerine bakıyor (sabah ekranı bunu gösteriyor), harman da kötüleşmemeli; tarif değişince eski ve "
      "yeni tahminler aynı sınama koşularında kıyaslanıyor (bkz. Kapı).")
    a("- Elenenler: hız puanı, jokey/antrenör piyasa ilgisi + ekuri (log-loss'u çok az düşürdü ama ilk seçim isabetini düşürdü); "
      "sabah programındaki form dizisi (yalnız 2026-04 sonrasında var, eğitim geçmişi yetersiz).")
    a("- Dürüst sonuç: model tek başına **hâlâ piyasa favorisinin gerisinde**. Sabah tahminleri bilgi amaçlıdır; koşu öncesi oran "
      "geldiğinde en güvenilir olasılık piyasa (ve harman) olur.")
    a("")
    a("## Kısa sonuç (dürüst)")
    a("")
    a(f"- Yalnız geçmiş verilerle kurulan model (sabah tahmini) **tek başına piyasadan zayıf**: sınama log-loss "
      f"{mt['model']['log_loss']} (piyasa {mt['piyasa']['log_loss']}), ilk seçim isabeti {_y(mt['model']['ilk_secim_isabet'])} "
      f"(piyasa favorisi {_y(mt['favori']['ilk_secim_isabet'])}). Fark model − piyasa = {mp['ll_fark']:+.4f} ± {mp['std_hata']:.4f}.")
    a(f"- Model + piyasa harmanı log-loss'u {mt['harman']['log_loss']}: piyasaya göre fark **{hp['ll_fark']:+.4f} ± {hp['std_hata']:.4f}** "
      f"(std. hata). " + ("Bu fark istatistiksel olarak anlamlı bir iyileşme (2 std. hatadan büyük)." if anlamli else
                          "Bu fark **gürültü sınırları içinde**; modelin piyasaya kalıcı bir üstünlüğü kanıtlanmadı."))
    a(f"- Harmanın ilk seçim isabeti {_y(mt['harman']['ilk_secim_isabet'])}, piyasa favorisi {_y(mt['favori']['ilk_secim_isabet'])}. "
      f"Yayın modu: **{mj['yayin_modu']}** (kural: harman sınama log-loss'u piyasadan düşükse model+piyasa yayınlanır).")
    um = d["kovalar"]["model"][-1]; ust = d["kovalar"]["harman"][-1]
    a(f"- Kalibrasyon, en yüksek kova: yalnız model {um['aralik']} aralığında ortalama tahmin {_y(um['ort_tahmin'])}, gerçek {_y(um['gercek'])} "
      f"({um['at']} at); harman {_y(ust['ort_tahmin'])} / {_y(ust['gercek'])} ({ust['at']} at). Yani %50+ verilen atlarda model hâlâ "
      "biraz iyimser; bu atlar gerçekte yaklaşık yarı yarıya kazanıyor.")
    a("")
    a("## Veri kapsamı")
    a("")
    a(f"- Kaynak: herkese açık ayna [{veri.AYNA_URL}]({veri.AYNA_URL}) (lisans belirtilmemiş). Ayna durumu: {ayna_durumu}. "
      "tjk.org'a hiçbir istek atılmaz; ham veri bu depoya kopyalanmaz.")
    a(f"- Sonuçlar: {kap['ilk_tarih']} → {kap['son_tarih']}, **{kap['kosu']:,} yerli koşu**, {kap['kosan_at']:,} koşan at; "
      f"tam oranlı koşu {kap['tam_oranli_kosu']:,}. Yabancı (simulcast) koşular ve kazananı belirsiz koşular çıkarıldı "
      f"({mj['atilan']}).")
    a("- Hipodromlar: " + ", ".join(f"{k} {v}" for k, v in kap["hipodrom"].items()) + ".")
    b = d["bolum"]
    a(f"- Zaman sıralı ölçüm: ısınma (yalnız geçmiş biriktirme) < {b['isinma_bitis']}; **sınama (son %30) {b['sinama'][0]}→{b['sinama'][1]} "
      f"({d['kosu_sayisi']['sinama']} tam oranlı koşu)**. {d.get('protokol', '')}.")
    a("- Piyasa olasılığı q: **nihai** ganyan oranından (1/oran, marj ayrılmış). Bu, \"son koşu öncesi\" piyasayı temsil eder; "
      "sabah programında oran yoktur. Yani harman ancak koşudan hemen önce kullanılabilir; sabah kilitlenen tahminler yalnız modeldir. "
      "Geçmiş koşuların oranları ise (o koşular bittiği için) sabah da bilinir ve modelde \"piyasa hafızası\" olarak kullanılır.")
    a("- Kullanılmayanlar: aynanın memory/*.json özetleri (geleceği içerir → sızıntı), gün içi oran görüntüleri (yalnız 57 gün), "
      "hava/nem ve form dizileri (yalnız 2026-04 sonrası programlarda).")
    a("")
    a("## Sınama metrikleri (son %30, yalnız tam oranlı koşular)")
    a("")
    a("| | log-loss ↓ | Brier ↓ | ilk seçim | ikili (sıralı) | ilk iki → ilk 2 | p≥.30 seçim / isabet (ort. p) | p≥.50 seçim / isabet (ort. p) |")
    a("|---|---|---|---|---|---|---|---|")
    for ad_, et in (("model", "**Yalnız model (sabah)**"), ("piyasa", "Piyasa q"), ("harman", "**Model + piyasa**"), ("favori", "Favori tabanı"), ("duzgun", "Düzgün (1/N)")):
        r = mt[ad_]

        def es(k):
            v = r.get(k)
            return f"{v['secim']} / {_y(v['isabet'])} ({_y(v['ort_p'])})" if v else "–"
        a(f"| {et} | {r.get('log_loss', '–')} | {r.get('brier', '–')} | {_y(r.get('ilk_secim_isabet'))} | {_y(r.get('ikili_sirali_isabet'))} | "
          f"{_y(r.get('ilk_iki_ikisi_de_ilk2'))} | {es('p>=0.30')} | {es('p>=0.50')} |")
    a("")
    a(f"Eşleştirilmiş log-loss farkı (koşu başına, ± std. hata): harman − piyasa = {hp['ll_fark']:+.4f} ± {hp['std_hata']:.4f}; "
      f"model − piyasa = {mp['ll_fark']:+.4f} ± {mp['std_hata']:.4f}.")
    m = mj["uretim_modeli"]
    a("")
    a(f"Parametreler (yayın modeli): birleşik puan = {m.get('c_dogrusal', 1)} × doğrusal + {m.get('c_gbm', 0)} × GBM "
      f"(GBM {'açık' if m.get('gbm') else 'kapalı'}); harman α = {m['alfa']}, β = {m['beta']}; "
      f"Henery üsleri γ(2.) = {m['henery_gamma']}, δ(3.) = {m['henery_delta']}; L2 λ = {m['lambda']}. "
      "LightGBM kurulu değilse model doğrusal yedeğe (kendi kalibrasyonuyla) düşer.")
    a("")
    for anah, baslik in (("model", "yalnız model (sabah tahmini)"), ("harman", "model + piyasa")):
        a(f"### Kalibrasyon (sınama, {baslik})")
        a("")
        a("| tahmin aralığı | at | ort. tahmin | gerçek kazanma |")
        a("|---|---|---|---|")
        for k in d["kovalar"][anah]:
            a(f"| {k['aralik']} | {k['at']} | {_y(k['ort_tahmin'])} | {_y(k['gercek'])} |")
        a("")
    a("## Deneyler (25.10.2026, yalnız model odaklı)")
    a("")
    _deney_tablosu(a)
    a("")
    a("Ölçülen ama tabloya girmeyenler:")
    a("")
    a("- **Deney 5 — sabah programındaki form dizisi** (ör. \"621-141\", 2025 öncesi kariyeri de içerir): yalnız 2026-04'ten beri var. "
      "Sınamanın Nisan–Haziran kısmında öğrenilip Temmuz–Ekim'de (1.377 koşu) denendiğinde yalnız-model log-loss'u ≈0,004 düşürdü; "
      "etkinin çoğu \"form dizisi boş = gerçekten ilk koşu\" bayrağından. Eğitim geçmişinde bu bilgi olmadığı için yayına alınmadı; "
      "program arşivi uzadıkça yeniden denenecek.")
    a("- **Reyting ayarları** (öğrenme hızı, kaç bitiş sırası kullanılacağı, piyasa reytingi hızı, sönüm): değişiklikler ±0,002–0,008 "
      "log-loss oynattı ama ilk seçim isabetini düşürdü; varsayılanlar korundu (aşırı ayar = sınamaya uydurma riski).")
    a("- **GBM ayarı**: ilk denenen ayar (15 yaprak) log-loss'u en çok düşürdü ama ilk seçim isabeti 0,18 puan (6 koşu) düştüğü için "
      "kurala göre elendi; ikinci ve son denenen daha düzenli ayar (7 yaprak, en az 500 at) kapıdan geçti. İki deneme yapıldığı açıkça kayıtlı.")
    a("- **Deney 7 — kalibrasyon**: sıcaklık doğrusal+GBM karışımıyla birlikte son 90 günde öğreniliyor; üstüne %25 üstü bölge için ayrı "
      "eğim eklendi (kapıdan geçti, %50+ seçim sayısını azalttı). Tekdüze dağılımla karıştırma log-loss'u iyileştirmedi. Buna rağmen "
      "%50+ kovasında ≈10 puanlık iyimserlik sürüyor (az örnek: ≈140 at) ve raporda açıkça gösteriliyor.")
    a("- **Kalibrasyon penceresi 150 gün** (90 yerine) ve **λ = 100**: ikisi de kötüleştirdi.")
    a("")
    a("## Neler önemli?")
    a("")
    a("Doğrusal katmanın standartlaştırılmış katsayıları (en büyük 12; + kazanma şansını artırır; GBM katmanı ayrıca etkileşimleri yakalar):")
    a("")
    a("| özellik | katsayı |")
    a("|---|---|")
    for o in d["onem"][:12]:
        a(f"| {o['ozellik']} | {o['std_katsayi']:+.3f} |")
    a("")
    if d.get("ablasyon"):
        a("Ablasyon — grup çıkarılınca sınama log-loss'u ne kadar kötüleşiyor (+ = grup faydalı; yalnız doğrusal katmanla, aylık walk-forward):")
        a("")
        a("| çıkarılan grup | yalnız model Δ | model+piyasa Δ |")
        a("|---|---|---|")
        for o in d.get("ablasyon", []):
            a(f"| {o['grup_cikarildi']} | {o['model_ll_fark']:+.4f} | {o['harman_ll_fark']:+.4f} |")
        a("")
    a("Yorum: sabah tahmininde en çok taşıyan bilgiler reytingler (at/jokey/antrenör), pist/mesafe/hipodrom uyumu, atın geçmişte "
      "piyasada nasıl değerlendirildiği (piyasa hafızası) ve dinlenme. Jokeyin son 60 gün oranı artık jokey reytingiyle örtüştüğü için "
      "tek başına katkısı kalmadı. Grupların çoğu birbiriyle örtüştüğünden tek grup çıkarmak az fark yaratır; harmana katkıları ±0,001 düzeyinde.")
    a("")
    a("## Kapı (sürekli öğrenme)")
    a("")
    a("- Kural: tarif (özellikler/ayarlar) değişirse yeni model ancak **aynı sınama koşularında** yalnız-model log-loss'u düşürür, "
      "ilk seçim isabetini düşürmez ve harman log-loss'unu 0,001'den fazla bozmazsa kabul edilir. Tarif aynıysa özellikler her gece "
      "yeni sonuçlarla güncellenir, katsayılar haftada bir yeniden eğitilir (KORU = bu gece yenileme günü değil); ortak koşularda "
      "belirgin bozulma (veri sorunu) olursa dünkü model korunur. İz: `data/at/sinama_izi.json`.")
    a(f"- Son karar ({kp['tarih']}): **{kp['karar']}** — {kp['neden']}")
    if kp.get("yeni") and kp.get("eski"):
        y, e = kp["yeni"], kp["eski"]
        a(f"- Yeni: yalnız model log-loss {_ll(y['model_ll'])}, ilk seçim {_y(y['model_ilk'])}; harman {_ll(y['harman_ll'])}. "
          f"Kıyas: yalnız model {_ll(e['model_ll'])}, ilk seçim {_y(e['model_ilk'])}; harman {_ll(e['harman_ll'])}.")
    a("")
    a("## Canlı karne (kilitlenmiş tahminler, sonuç gelince)")
    a("")
    if karne.get("toplam"):
        tp = karne["toplam"]
        a(f"- Koşudan önce kilitlenmiş toplam {tp['kosu']} koşu: log-loss {tp['log_loss']}, ilk seçim isabeti {_y(tp['ilk_secim_isabet'])}, ikili isabeti {_y(tp['ikili_isabet'])}.")
        for t, g in sorted(karne["gunler"].items())[-7:]:
            a(f"  - {t}: {g['kosu']} koşu, ilk seçim {_y(g['ilk_secim_isabet'])}, log-loss {g['log_loss']}")
    else:
        a("- Henüz puanlanmış kilitli tahmin yok (sonuçlar aynaya düştükçe her gece puanlanır).")
    a("")
    a(f"## Gösteri: {bugun} İstanbul tahminleri")
    a("")
    kt = joku(os.path.join(TAHMIN, bugun + ".json"))
    ist = [k for k in (kt or {}).get("kosular", []) if k["hipodrom"] == "İstanbul"]
    if ist:
        a(f"Kilit zamanı {kt.get('kilit_zamani_tsi', kt['kilit_zamani'])} TSİ, model sürümü `{kt.get('model_surumu', '?')}` "
          "(kilitler ezilmez; bu günün kilidi önceki modelle atılmış olabilir). Mod: " + ist[0]["mod"] + ". "
          "`*` = kilit koşu saatinden sonra atıldı (sızıntısız ama canlı karneye sayılmaz).")
        a("")
        a("| koşu | saat | mesafe/pist | ilk 3 (kazanma olasılığı) | ikili önerisi |")
        a("|---|---|---|---|---|")
        for k in ist:
            ilk3 = ", ".join(f"{x['no']} {x['ad']} ({_y(x['p_kazanma'])})" for x in k["atlar"][:3])
            a(f"| {k['kosu']}{'' if k.get('kosudan_once', True) else '*'} | {k.get('saat') or '–'} | {k['mesafe']} {k['pist']} | {ilk3} | {'-'.join(k['ikili_onerisi']['sira'])} ({_y(k['ikili_onerisi']['p'])}) |")
    else:
        a("- Bu gün için İstanbul programı/kilidi yok.")
    a("")
    for (t, h, n) in TAKIP:
        kt = joku(os.path.join(TAHMIN, t + ".json"))
        k = next((k for k in (kt or {}).get("kosular", []) if k["hipodrom"] == h and k["kosu"] == n), None)
        a(f"### İzlenen koşu: {t} {h} {n}. koşu")
        a("")
        if not k:
            a("- Kilitli tahmin yok.")
            a("")
            continue
        a(f"{k['mesafe']} m {k['pist']}, {k['sinif']}, saat {k.get('saat') or '–'}. Mod: {k['mod']}. Kilit: {kt.get('kilit_zamani_tsi', kt['kilit_zamani'])} TSİ "
          f"(model `{kt.get('model_surumu', '?')}`).")
        if not k.get("kosudan_once", True):
            a("")
            a("> Not: bu kilit koşu saatinden **sonra** atıldı. Sonuç aynada yokken ve yalnız önceki günlerin verisiyle üretildi "
              "(sızıntısız), ama dürüstlük gereği canlı karneye sayılmaz; yalnız gösterim amaçlıdır.")
        a("")
        a("| no | at | kazanma | ilk 2 | ilk 3 | gerekçe |")
        a("|---|---|---|---|---|---|")
        for x in k["atlar"]:
            a(f"| {x['no']} | {x['ad']} | {_y(x['p_kazanma'])} | {_y(x['p_ilk2'])} | {_y(x['p_ilk3'])} | {x['gerekce']} |")
        g = next((g for g in karne.get("kosular", []) if g["kosu_id"] == k["kosu_id"]), None)
        a("")
        if g:
            a(f"**Sonuç:** kazanan {g['kazanan']} (modelin verdiği olasılık {_y(g['p_kazanan'])}); ilk seçim {g['ilk_secim']} → "
              f"{'TUTTU' if g['ilk_secim_tuttu'] else 'tutmadı'}; ikili {'tuttu' if g['ikili_tuttu'] else 'tutmadı'}.")
        else:
            a("**Sonuç:** henüz aynada yok (son sonuç günü " + kap["son_tarih"] + "); sonuç gelince gece robotu otomatik puanlayacak.")
        a("")
    a("## Daha önce denenmiş ama kapıdan geçmemiş fikirler")
    a("")
    a("- Benter'in ortak tahmini (log q'yu modelin içine sabit girdi olarak koyup birlikte eğitmek): harman diliminde piyasayı "
      "≈0,009 log-loss iyileştirdi, fakat sınamada fark +0,0002 ± 0,003 (iyileşme yok) → dönem kayması işareti. Yayına alınmadı.")
    a("- Uzun-atış yanlılığı düzeltmesi (log q'ya ikinci derece terim): sınamada etkisiz (±0,001).")
    a("")
    a("## Sınırlamalar ve riskler")
    a("")
    a("- Veri yalnız 2025-01-01'den başlıyor: atların daha eski kariyerleri görünmüyor (ilk aylarda özellikler zayıf, ısınma ile kısmen çözüldü).")
    a("- Ayna lisanssız ve tek kişinin bakımında; kesilirse sistem son kopyayla çalışır, yeni sonuç gelmez.")
    a("- At adları kimlik olarak kullanılıyor (aynı adlı iki at nadir ama mümkün). Ekürili atlarda ganyan oranı ortaktır.")
    a("- Sınama tek bir zaman dilimi (≈7 ay); deneylerdeki 0,001–0,003'lük farklar gürültü düzeyinde, büyük kazançlar (walk-forward, "
      "piyasa hafızası, reyting, GBM) ise tutarlı. İlk seçim isabetinin standart hatası ≈ ±0,8 puan.")
    a("- GBM katmanı `lightgbm` paketine dayanır (iş akışı kurar). Kurulamazsa model doğrusal yedeğe düşer; gerekçeler yalnız doğrusal katmandan üretilir.")
    a("- Sabah kilitleri yalnız model olasılığıdır; piyasa harmanı için koşu öncesi oran gerekir (ayna gün içi oranları düzenli yayınlamıyor).")
    a("- Uygulamadaki üst özet kutusu `degerlendirme.metrik.harman` isabetini gösteriyor; sabah tahmininin kendi isabeti (yalnız model) daha düşüktür.")
    a("")
    a("## Sonraki deneyler")
    a("")
    a("1. Program arşivi uzadıkça form dizisi (2025 öncesi kariyer, gerçek ilk koşu bayrağı) — şimdiden +0,004 işareti var.")
    a("2. Koşu öncesi anlık oran (gün içi görüntüler düzenli gelirse) ile oran hareketi ve sabah→koşu öncesi harman.")
    a("3. Üst kovadaki iyimserlik için izotonik/parçalı kalibrasyon (yeterli örnek birikince).")
    a("4. Hız puanını kilo ve pist durumuyla düzeltip yeniden denemek; pedigri/idman verisi açık kaynakta bulunursa.")
    a("")
    a("## Zamanlama")
    a("")
    a("`.github/workflows/at-lab.yml` her gün 05:23 ve 12:23 TSİ'de, ayrıca `lab/at/**` değişince veya elle çalışır (main dalı). "
      "Çıktılar yalnız `data/at/` ve `lab/at/RAPOR.md`'ye yazılır. Gece akışı ≈3–5 dakika sürer.")
    a("")
    a(f"_Kaynak atfı: TJK verilerinin herkese açık aynası {veri.AYNA_URL}. Model ve olasılıklar BULUTOXX laboratuvarınındır._")
    open(RAPOR, "w", encoding="utf-8").write("\n".join(L) + "\n")


# ---------------------------------------------------------------- kapı
def tarif():
    """Modelin tarifi (özellikler + ayarlar). Tarif aynıysa gece yalnız yeni veriyle yeniden eğitir."""
    return {"surum": "v2", "ozellikler": list(ozellik.ADLAR), "gbm": M.lgb is not None, "gbm_ayar": M.GBM_AYAR,
            "kal_gun": M.KAL_GUN, "yari_omur": M.YARI_OMUR, "pl_hiz": ozellik.PL_HIZ, "pl_kademe": ozellik.PL_KADEME,
            "pm_hiz": ozellik.PM_HIZ, "ewma": ozellik.EWMA_A, "sonum_gun": ozellik.SONUM_GUN}


def kapi_karari(yeni, iz, trf, eski, eski_iz):
    """KAPI. Ana ölçüt yalnız-model (sabah tahmini) log-loss ve ilk-seçim isabeti; harman log-loss'u da kötüleşmemeli.
    - Tarif aynı + iz var: gece yeniden eğitimi; ortak koşularda belirgin kötüleşme (veri sorunu) yoksa KABUL.
    - Tarif değişti + iz var: eski ve yeni tahminler ORTAK sınama koşularında kıyaslanır (adil, aynı dilim).
    - İz yok (v1'den geçiş): kayıtlı sınama metrikleriyle kıyaslanır."""
    if not eski:
        return {"karar": "KABUL", "neden": "ilk model (kayıtlı model yok)", "yeni": yeni, "eski": None}
    k = M.iz_kiyas(iz, eski_iz["iz"]) if eski_iz and eski_iz.get("iz") else None
    if k and eski.get("tarif") == trf:
        y, e = k["yeni"], k["eski"]
        try:
            yas = (datetime.now(timezone.utc) - datetime.fromisoformat(eski["olusturma"])).days
        except Exception:
            yas = 99
        if yas < YENILEME_GUN:
            # Depo şişmesin diye (GBM dosyası ≈0,5 MB) aynı tarifte katsayılar haftada bir yenilenir; özellikler
            # (form, reyting, piyasa hafızası) her gece yeni sonuçlarla güncellenir.
            return {"karar": "KORU", "neden": f"aynı tarif; katsayılar {yas} günlük (haftalık yenileme), özellikler bu gece "
                    f"yeni sonuçlarla güncellendi", "yeni": y, "eski": e}
        if y["model_ll"] > e["model_ll"] + 0.01 or y["harman_ll"] > e["harman_ll"] + 0.01:
            return {"karar": "RED", "neden": f"aynı tarif ama ortak {k['kosu']} koşuda log-loss belirgin kötüleşti "
                    f"(model {e['model_ll']}→{y['model_ll']}); veri sorunu olabilir, dünkü model korunuyor", "yeni": y, "eski": e}
        return {"karar": "KABUL", "neden": f"aynı tarif, yeni veriyle yeniden eğitim (ortak {k['kosu']} koşuda model log-loss "
                f"{e['model_ll']}→{y['model_ll']})", "yeni": y, "eski": e}
    if k:
        y, e, ek = k["yeni"], k["eski"], f" (ortak {k['kosu']} sınama koşusunda)"
    else:
        mt = eski["degerlendirme"]["metrik"]
        e = {"model_ll": mt["model"]["log_loss"], "model_ilk": mt["model"]["ilk_secim_isabet"],
             "harman_ll": mt["harman"]["log_loss"], "harman_ilk": mt["harman"]["ilk_secim_isabet"]}
        y, ek = yeni, " (tarif değişti; kayıtlı sınama metrikleriyle kıyaslandı)"
    if y["model_ll"] >= e["model_ll"] - 1e-5:
        return {"karar": "RED", "neden": f"yalnız-model log-loss düşmedi ({e['model_ll']} → {y['model_ll']}); dünkü model korunuyor{ek}", "yeni": y, "eski": e}
    if y["model_ilk"] < e["model_ilk"]:
        return {"karar": "RED", "neden": f"yalnız-model ilk seçim isabeti düştü ({e['model_ilk']} → {y['model_ilk']}); dünkü model korunuyor{ek}", "yeni": y, "eski": e}
    if y["harman_ll"] > e["harman_ll"] + 0.001:
        return {"karar": "RED", "neden": f"harman log-loss kötüleşti ({e['harman_ll']} → {y['harman_ll']}); dünkü model korunuyor{ek}", "yeni": y, "eski": e}
    return {"karar": "KABUL", "neden": f"yalnız-model log-loss {e['model_ll']}→{y['model_ll']}, ilk seçim {e['model_ilk']}→{y['model_ilk']}; "
            f"harman log-loss {e['harman_ll']}→{y['harman_ll']}{ek}", "yeni": y, "eski": e}


# ---------------------------------------------------------------- ana akış
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guncelleme-yok", action="store_true", help="aynayı güncelleme (salt-okunur yerel kopya)")
    ap.add_argument("--bugun", default=None, help="YYYY-MM-DD (varsayılan: İstanbul saatiyle bugün)")
    ap.add_argument("--ablasyonsuz", action="store_true")
    ar = ap.parse_args()
    kaynak = os.environ["AT_KAYNAK"]
    ayna = "güncellenmedi (yerel kopya)" if ar.guncelleme_yok else ayna_guncelle(kaynak)
    print("ayna:", ayna, kaynak)
    bugun = ar.bugun or (datetime.now(timezone.utc) + timedelta(hours=3)).date().isoformat()
    yarin = (date.fromisoformat(bugun) + timedelta(days=1)).isoformat()

    kosular, atilan = veri.sonuclari_yukle()
    T, durum = ozellik.tablo_kur(kosular, adlar=ozellik.TUM_ADLAR)
    sec = [ozellik.TUM_ADLAR.index(a) for a in ozellik.ADLAR]
    T_sec = dict(T); T_sec["X"] = T["X"][:, sec]; T_sec["adlar"] = list(ozellik.ADLAR)
    print("tablo:", T_sec["X"].shape, "gbm:", M.lgb is not None)
    m_eval, sonuc, iz = M.degerlendir(T_sec, kosular, ablasyon=not ar.ablasyonsuz, gbm=True)
    mt_y = sonuc["metrik"]
    yeni = {"model_ll": mt_y["model"]["log_loss"], "model_ilk": mt_y["model"]["ilk_secim_isabet"],
            "harman_ll": mt_y["harman"]["log_loss"], "harman_ilk": mt_y["harman"]["ilk_secim_isabet"]}
    eski = joku(os.path.join(CIKTI, "model.json"))
    eski_iz = joku(IZ_DOSYA)
    trf = tarif()
    simdi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    kapi = kapi_karari(yeni, iz, trf, eski, eski_iz)
    kabul = kapi["karar"] == "KABUL"
    kapi["tarih"] = simdi
    print("kapı:", kapi["karar"], kapi["neden"])
    if kabul:
        uretim = M.uretim_modeli(T_sec, kosular, m_eval.lam, gbm=True)
        mj = {"surum": simdi[:16].replace(":", "").replace("-", ""), "olusturma": simdi, "tarif": trf,
              "degerlendirme": sonuc, "uretim_modeli": uretim.json(), "gecmis": (eski or {}).get("gecmis", [])}
        if uretim.gbm is not None and uretim.cg:
            os.makedirs(CIKTI, exist_ok=True)
            with open(GBM_DOSYA + ".tmp", "w", encoding="utf-8") as f:
                f.write(uretim.gbm.model_to_string())
            os.replace(GBM_DOSYA + ".tmp", GBM_DOSYA)
        jyaz(IZ_DOSYA, {"surum": mj["surum"], "tarif": trf,
                        "alanlar": ["kosu_id", "model_-logp_kazanan", "model_ilk_tuttu", "harman_-logp_kazanan", "harman_ilk_tuttu"],
                        "iz": iz}, sikisik=True)
        m_uretim = uretim
    elif kapi["karar"] == "KORU":
        # aynı tarif: ölçüm güncel tutulur (aynı tarifin bu geceki walk-forward sonucu), yayın katsayıları korunur
        mj = eski
        mj["degerlendirme"] = sonuc
        jyaz(IZ_DOSYA, dict(eski_iz, iz=iz), sikisik=True)
        m_uretim = model_yukle(mj["uretim_modeli"])
    else:
        mj = eski
        mj["reddedilen_son_deneme"] = {"tarih": simdi, "metrik": sonuc["metrik"]}
        m_uretim = model_yukle(mj["uretim_modeli"])
    mj["guncelleme"] = simdi
    mj["kapsam"] = veri.kapsam(kosular)
    mj["atilan"] = atilan
    mj["kapi"] = kapi
    mj["gecmis"] = (mj.get("gecmis", []) + [{"tarih": simdi, "karar": kapi["karar"], "log_loss": yeni["harman_ll"],
                                               "ilk_secim_isabet": yeni["harman_ilk"], "model_log_loss": yeni["model_ll"],
                                               "model_ilk_secim_isabet": yeni["model_ilk"]}])[-60:]
    mt = mj["degerlendirme"]["metrik"]
    mj["yayin_modu"] = "model+piyasa" if mt["harman"]["log_loss"] < mt["piyasa"]["log_loss"] else "yalniz_piyasa"
    mj["kaynak"] = {"ayna": veri.AYNA_URL, "lisans": "belirtilmemiş", "not": "Ham veri bu depoya kopyalanmaz; tjk.org'a istek atılmaz."}
    mj["uyari"] = "Hobi amaçlıdır; tahmin garanti değildir · 18+"
    mj["gbm_kurulu"] = M.lgb is not None

    son_sonuc = kosular[-1]["tarih"]
    kilit = kilitle([bugun, yarin], son_sonuc, m_uretim, durum, mj["yayin_modu"], mj["surum"])
    print("kilitlenen:", kilit)
    karne, puanlanan = puanla(kosular)
    print("puanlanan:", puanlanan)
    jyaz(os.path.join(CIKTI, "model.json"), mj)
    rapor_yaz(mj, karne, bugun, ayna)
    print("tamam")


if __name__ == "__main__":
    main()
