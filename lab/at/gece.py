# OXXai at yarışı laboratuvarı — gece boru hattı.
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
import at5  # noqa: E402  (v5 at özellikleri: a5_* grupları, lab/at/deney5.py)
import at6  # noqa: E402  (v6 derin tarama: a6_* grupları, lab/at/deney6.py; kaynaklar lab/at/KAYNAKLAR.md)
import jokey  # noqa: E402  (🏇 jokey/ahır uzmanı: data/at/jokeyler.json + jk_* özellik grupları)

CIKTI = os.path.join(KOK, "data", "at")
TAHMIN = os.path.join(CIKTI, "tahmin")
RAPOR = os.path.join(BURA, "RAPOR.md")
GBM_DOSYA = os.path.join(CIKTI, "gbm_uretim.txt")      # yayın modelinin ağaçları (uygulama okumaz)
IZ_DOSYA = os.path.join(CIKTI, "sinama_izi.json")     # kapı için koşu başına sınama izi
DENEY_DOSYA = os.path.join(CIKTI, "deneyler.json")
REPLAY_DOSYA = os.path.join(CIKTI, "replay.json")      # gün gün yeniden oynatma (lab/at/replay.py)
# Altın at kuralı: replay.py seçer (seçim ilk 2/3 gün, rapor son 1/3) ve model.json'a yazar; gece korur.
ALTIN_VARSAYILAN = {"p_min": 0.35, "fark_min": 0.12, "gunluk_max": 3, "kaynak": "varsayılan (arayüz kuralı)"}


def altin_kural(eski):
    """Önce kayıtlı model.json kuralı, yoksa replay.json'daki seçilen kural, o da yoksa arayüzün varsayılanı."""
    k = (eski or {}).get("altin_kural")
    if k and all(x in k for x in ("p_min", "fark_min", "gunluk_max")):
        return k
    r = (joku(REPLAY_DOSYA) or {}).get("secilen_altin") or {}
    if r.get("kural"):
        return dict(r["kural"], donem=(joku(REPLAY_DOSYA) or {}).get("donem"))
    return dict(ALTIN_VARSAYILAN)
V5_DOSYA = os.path.join(CIKTI, "deneyler_v5.json")     # v5 deney kaydı (a5_* grupları, harman hm_alan)
V6_DOSYA = os.path.join(CIKTI, "deneyler_v6.json")     # v6 deney kaydı (derin tarama: a6_* grupları, m6_rank)
V6_PIYASA = os.path.join(CIKTI, "oran_izi_v6.json")    # v6 harman katmanı ölçümleri (oran izi, üçüncü taraf)
JOKEY_DOSYA = os.path.join(CIKTI, "jokeyler.json")    # arayüz: attan arındırılmış jokey/antrenör istatistikleri
YENILEME_GUN = 7   # aynı tarifte yayın katsayılarının yenilenme aralığı (gün)
TAKIP = [("2026-10-25", "İstanbul", 5)]   # raporda kalıcı izlenen örnek koşu(lar)
KAYNAKLAR = ["github.com/cenkozgur/tjk-data (herkese açık ayna; tjk.org'a istek yok)"]

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
    "zemin_ord": ("", ""), "zemin_yok": ("", ""),
    "zemin_uyum": ("ağır/yumuşak zeminde iyi koşmuş", "ağır/yumuşak zeminde zayıf"),
    "zemin_x_kilo": ("ağır zeminde üst kilo", "ağır zeminde hafif kilo avantajı"),
    "zemin_x_skor": ("", ""),
    "hz_son": ("son hız figürü yüksek", "son hız figürü düşük"),
    "hz_en_iyi3": ("son 3 koşudaki en iyi hız figürü yüksek", "son 3 koşuda hız figürü düşük"),
    "hz_ort3": ("hız figürleri istikrarlı yüksek", "hız figürleri düşük"),
    "hz_trend": ("hız figürü yükselişte", "hız figürü düşüşte"),
    "hz_yok": ("hız figürü yok", ""),
    "hz_alan": ("hız figürü rakiplerinin üstünde", "hız figürü rakiplerinin altında"),
    # v4: handikap reytingi vekili ve değişim sinyalleri
    "hp_once": ("handikap puanı (kilodan tahmin) yüksek", "handikap puanı (kilodan tahmin) düşük"),
    "hp_yok": ("handikap geçmişi yok", ""),
    "hp_bugun": ("handikapçı bugün ona yüksek puan vermiş", "handikapçı bugün ona düşük puan vermiş"),
    "hp_degisim": ("handikap puanı yükseltilmiş (form iyileşmesi)", "handikap puanı düşürülmüş"),
    "hp_alan": ("handikap puanı alanın üstünde", "handikap puanı alanın altında"),
    "kilo_sira_h": ("handikapta üst sıralarda kilo", "handikapta alt sıralarda kilo"),
    "kilo_min_h": ("en hafif ata göre epey kilo veriyor", "en hafif kiloya yakın"),
    "kilo_x_sinif": ("", ""),
    "mesafe_deg_y": ("mesafe uzuyor", "mesafe kısalıyor"),
    "pist_degisti": ("pist değişiyor", ""), "pist_ilk": ("bu pistte ilk kez koşuyor", ""),
    "jokey_r_fark": ("daha güçlü bir jokeye geçti", "daha zayıf bir jokeye geçti"),
    "ara_10": ("çok kısa arayla koşuyor", ""), "ara_60_120": ("2–4 aylık aradan dönüyor", ""),
    "ara_120_240": ("4–8 aylık aradan dönüyor", ""), "ara_240p": ("çok uzun aradan dönüyor", ""),
    "donus_2": ("uzun aradan sonraki ikinci koşusu", ""), "yas2_mesafe": ("", ""),
    "sinif_dus": ("belirgin sınıf düşüşü", ""), "sinif_cik": ("belirgin sınıf yükselişi", ""),
}
IFADE.update(jokey.IFADE)   # jk_* özellikleri (yalnız seçilmişse gerekçede görünür)
IFADE.update(at5.IFADE)     # a5_* özellikleri


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


def _tam(v):
    try:
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


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
    # indirimli Harville: yalnız-model olasılıkları için ayrı (kendi kalibrasyonunda öğrenilen) γ, δ
    g, d = (m.gam, m.dlt) if mod.startswith("model+") or mod.startswith("yalnız piyasa") else (m.gam_m, m.dlt_m)
    so = M.sirali_olasiliklar(p, g, d)
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
                      "p_ilk3": round(float(so["ilk3"][i]), 4) if "ilk3" in so else None, "gerekce": ger,
                      # ek (isteğe bağlı) alanlar: programdaki herkese açık sportif bilgiler
                      "jokey": a.get("jokey") or None, "kilo": a.get("kilo"), "yas": _tam(a.get("yas")),
                      "form": a.get("form") or None})
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
                   "kilit_zamani_tsi": simdi_tr, "model_surumu": surum, "kaynaklar": KAYNAKLAR,
                   "not": "Hobi amaçlı olasılıklar; garanti değildir · 18+. kosudan_once=false olan koşular canlı karneye sayılmaz.",
                   "kosular": ks})
        yazilan.append(t)
    return yazilan


# ---------------------------------------------------------------- karne
def _gun_ozeti(satir):
    canli = [x for x in satir if x["kosudan_once"]] or satir
    return {"canli": any(x["kosudan_once"] for x in satir), "kosu": len(canli),
            "log_loss": round(float(np.mean([x["log_loss"] for x in canli])), 4),
            "ilk_secim_isabet": round(float(np.mean([x["ilk_secim_tuttu"] for x in canli])), 4),
            "ikili_isabet": round(float(np.mean([x["ikili_tuttu"] for x in canli])), 4)}


def puanla(kosular, yalniz_degisince=False):
    """Kilitli tahminleri (data/at/tahmin) sonuçla puanlar. Koşu kimliğiyle (kosu_id) idempotent: aynı koşu iki kez
    sayılmaz; gün içinde sonucu gelen koşular (canlı robot) ve geceki tamamlama aynı kayda eklenir, gün özeti
    o günün tüm puanlı koşularından yeniden hesaplanır. yalniz_degisince=True: yeni satır yoksa dosya yazılmaz."""
    karne = joku(os.path.join(CIKTI, "karne.json"), None) or {"gunler": {}, "kosular": []}
    sonuc = {(k["tarih"], k["hipodrom"], k["kosu"]): k for k in kosular}
    var = {x["kosu_id"] for x in karne["kosular"]}
    yeni = []
    for f in sorted(os.listdir(TAHMIN)) if os.path.isdir(TAHMIN) else []:
        t = f[:-5]
        if not f.endswith(".json"):
            continue
        kt = joku(os.path.join(TAHMIN, f), {})
        satir = []
        for kp in kt.get("kosular", []):
            if kp["kosu_id"] in var:
                continue
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
        var.update(x["kosu_id"] for x in satir)
        karne["gunler"][t] = _gun_ozeti([x for x in karne["kosular"] if x["kosu_id"].startswith(t + "/")])
        yeni.append(t)
    if yalniz_degisince and not yeni:
        return karne, yeni
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


DENEY3_DOSYA = os.path.join(CIKTI, "deneyler_v3.json")


def _ga(f):
    return f"{f['dll']:+.4f} [{f['ga95'][0]:+.4f}, {f['ga95'][1]:+.4f}]"


DENEY4_DOSYA = os.path.join(CIKTI, "deneyler_v4.json")


def _kova_satir(k):
    return f"{k['aralik']}: {k['at']} at, tahmin {_y(k['ort_tahmin'])} / gerçek {_y(k['gercek'])}"


def _v4_ozet(a, mj):
    """v4 turu: iki katlı sağlam ölçüm + kapılı deneyler (deneyler_v4.json'dan)."""
    dj = joku(DENEY4_DOSYA)
    if not dj or not dj.get("adimlar"):
        return
    ad = dj["adimlar"]
    t0 = ad[0]
    son = t0
    for s_ in ad[1:]:
        if s_["gecti"]:
            son = s_
    kt = dj["katlar"]
    a("## Özet: v4 turu — sabah (oransız) modeli, iki katlı sağlam ölçüm (25.10.2026 gece)")
    a("")
    a(f"**Ölçüm artık tek bir 7 aylık dilime dayanmıyor.** İki zaman katı, her ikisinde de her ay yalnız o aydan önceki veriyle "
      f"yeniden eğitim (genişleyen pencere): **A katı {kt['A'][0]} → {kt['A'][1]}** ({t0['katlar']['A']['kosu']:,} koşu), "
      f"**B katı {kt['B'][0]} → {kt['B'][1]}** ({t0['katlar']['B']['kosu']:,} koşu; v3'ün sınama dilimiyle aynı). "
      "Kapı: katların ortalama yalnız-model log-loss'u düşmeli, ortalama ilk-seçim isabeti düşmemeli, en güncel kat (B) "
      "kötüleşmemeli ve harman 0,001'den fazla bozulmamalı. Her adım için koşu başına eşleştirilmiş ΔLL ve koşu-bootstrap %95 GA.")
    a("")
    a("| | yalnız model LL (A / B / ort.) | ilk seçim (A / B / ort.) | harman LL ort. | piyasa LL ort. |")
    a("|---|---|---|---|---|")
    for et, s_ in (("v3 tarifi (önce)", t0), ("v4 tarifi (sonra)", son)):
        A_, B_ = s_["katlar"]["A"], s_["katlar"]["B"]
        a(f"| {et} | {A_['model']['ll']:.4f} / {B_['model']['ll']:.4f} / **{s_['model']['ll']:.4f}** | "
          f"{_y(A_['model']['ilk'])} / {_y(B_['model']['ilk'])} / **{_y(s_['model']['ilk'])}** | {s_['harman']['ll']:.4f} | "
          f"{s_['piyasa']['ll']:.4f} |")
    a("")
    if son is not t0:
        # önce→sonra toplam fark (kabul zincirinin toplamı; eşleştirilmiş farklar adım adım tabloda)
        a(f"- Toplam: ortalama yalnız-model log-loss {t0['model']['ll']:.4f} → {son['model']['ll']:.4f} "
          f"({son['model']['ll'] - t0['model']['ll']:+.4f}); B katı {t0['katlar']['B']['model']['ll']:.4f} → "
          f"{son['katlar']['B']['model']['ll']:.4f}; A katı {t0['katlar']['A']['model']['ll']:.4f} → {son['katlar']['A']['model']['ll']:.4f}. "
          "Kazanç küçük: sabah modeli hâlâ piyasanın belirgin gerisinde.")
    tp = dj.get("toplam")
    if tp:
        a(f"- **Toplam eşleştirilmiş fark (v4 − v3, yalnız model):** birleşik {_ga(tp['model'])}; A katı {_ga(tp['model']['A'])}; "
          f"B katı {_ga(tp['model']['B'])}. İlk seçim isabeti farkı {tp['model']['d_ilk'] * 100:+.2f} puan. "
          f"Harman: {_ga(tp['harman'])}.")
    if dj.get("model_vs_piyasa"):
        a(f"- Yalnız model − piyasa (iki kat birleşik): {_ga(dj['model_vs_piyasa'])}; harman − piyasa: {_ga(dj['harman_vs_piyasa'])}.")
    a("")
    a("Kapılı deneyler (ΔLL = yeni − önceki kabul, koşu başına; köşeli parantez koşu-bootstrap %95 GA, iki kat birleşik):")
    a("")
    a("| # | deney | sonuç | ort. LL / ilk seçim | A: LL / ilk | B: LL / ilk | ΔLL birleşik [%95 GA] | ΔLL A [%95 GA] | ΔLL B [%95 GA] | harman ort. |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for s_ in ad:
        sonuc = "taban" if s_["gecti"] is None else ("✅ kaldı" if s_["gecti"] else "❌ elendi")
        fm = s_.get("fark_model")
        A_, B_ = s_["katlar"]["A"]["model"], s_["katlar"]["B"]["model"]
        a(f"| {s_['no']} | {s_['deney']} | {sonuc} | {s_['model']['ll']:.4f} / {_y(s_['model']['ilk'])} | "
          f"{A_['ll']:.4f} / {_y(A_['ilk'])} | {B_['ll']:.4f} / {_y(B_['ilk'])} | {_ga(fm) if fm else '–'} | "
          f"{_ga(fm['A']) if fm else '–'} | {_ga(fm['B']) if fm else '–'} | {s_['harman']['ll']:.4f} |")
    a("")
    a("Kalibrasyon — yalnız model, kat kat (önce = v3 tarifi, sonra = v4 tarifi):")
    a("")
    a("| kat | tahmin aralığı | önce: at / ort. tahmin / gerçek | sonra: at / ort. tahmin / gerçek |")
    a("|---|---|---|---|")
    for k in ("A", "B"):
        ko = {x["aralik"]: x for x in t0["katlar"][k]["kova_model"]}
        ks = {x["aralik"]: x for x in son["katlar"][k]["kova_model"]}
        for ar in ko:
            o, s2 = ko[ar], ks.get(ar)
            a(f"| {k} | {ar} | {o['at']} / {_y(o['ort_tahmin'])} / {_y(o['gercek'])} | "
              + (f"{s2['at']} / {_y(s2['ort_tahmin'])} / {_y(s2['gercek'])} |" if s2 else "– |"))
    a("")
    a("**Üst kova (%50+) bulgusu:** v3 raporundaki \"%59 tahmin, %48 gerçek\" iyimserliği **yalnız B katında** var; A katında "
      "aynı tarif tam tersine **temkinli** (tahmin ≈%57, gerçek ≈%62). İki katta birlikte fark ≈5 puan ve kova başına "
      "yalnız 90–180 at (std. hata ≈4 puan). Pencerede öğrenilen düzeltmeler (alan büyüklüğüne duyarlı sıcaklık, izotonik — "
      "hem kalibrasyon penceresinde hem önceki ayların sınama-dışı tahminlerinden) bu yüzden dışarıda tutmadı: iyimserlik "
      "kalıcı bir yanlılık değil, döneme bağlı bir dalgalanma gibi davranıyor. v4 tarifiyle (beta kalibrasyonu + yeni "
      "özellikler) B katındaki %50+ farkı ≈11 puandan ≈7 puana indi, A katındaki temkinlilik ≈4 puan; kalan farkı raporda "
      "açıkça gösteriyoruz ve kovaya düşen at sayısı arttıkça yeniden bakacağız.")
    a("")
    a("- Kabul edilenler: **değişim sinyalleri** (işaretli mesafe değişimi, pist değişimi / ilk kez bu pist, jokey reyting farkı, "
      "ara kovaları, uzun aradan sonraki 2. koşu, 2 yaş×mesafe, sınıf düşüşü/çıkışı), **beta kalibrasyonu**, **handikap reytingi "
      "vekili** ve **patlatılmış (sıralı) logit, derinlik 2** (Bolton–Chapman; 2. sıra 0,5 ağırlıkla). Son ikisi ilk denemede yalnız "
      "ilk-seçim kuralına takıldı (log-loss düşüyordu); yeni tabanda bir kez daha denendi ve geçti — bu tekrar tabloda açıkça var.")
    a("- Elenenler: alan büyüklüğüne duyarlı sıcaklık, izotonik (üç türü), GBM 3 tohum torbalama (etkisiz, üç kat süre), "
      "GBM ayarları (15/5 yaprak, daha yavaş öğrenme) ve zaman ağırlığı yarı ömrü 120/365 gün.")
    a("- Handikap vekili yan bulgusu: örtük sınıf düzeyleri veriden tamamen kendiliğinden doğru sıralandı "
      "(Handikap 13 < 14 < 15 < 16 < 17 < 21 < KV-22/24) ve apranti indirimi tahmini 0–3,5 kg aralığında — vekil anlamlı, "
      "ama bilgisi büyük ölçüde mevcut kilo/reyting özellikleriyle örtüşüyor.")
    a(f"- Deney kaydı: `data/at/deneyler_v4.json` ({dj.get('olusturma', '')}; süre {dj.get('sure_sn', '?')} sn); "
      "deney masası `lab/at/deney4.py`.")
    a("")


def _v5_bolum(a):
    """v5 turu: sınıf-ayarlı form, göreli kilo, dinlenme eğrisi, alan büyüklüğüne duyarlı harman (lab/at/deney5.py)."""
    dj = joku(V5_DOSYA)
    if not dj or not dj.get("adimlar"):
        return
    a("## v5 turu: sınıf-ayarlı form, kilo, dinlenme, harman")
    a("")
    a("Aynada start/kulvar numarası ve koşu içi pozisyon (tempo) yok; kulvar yanlılığı ve koşu stili kurulamadı. Aynı gün pist "
      "yanlılığı sabah kilidinde bilinemediği için denenmedi. Adaylar `lab/at/at5.py`; kapı deney4 iki katlı kapı (hm_alan "
      "için harmanın kendi kapısı). Sızıntı testi: `python lab/at/deney5.py --sizinti`.")
    a("")
    a("| # | deney | sonuç | ort. LL / ilk seçim | B: LL / ilk | ΔLL birleşik [%95 GA] | ΔLL A | ΔLL B | harman ort. LL / ilk | ΔLL harman |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for s_ in dj["adimlar"]:
        sonuc = "taban" if s_["gecti"] is None else ("✅ kaldı" if s_["gecti"] else "❌ elendi")
        fm, fh = s_.get("fark_model"), s_.get("fark_harman")
        B_ = s_["katlar"]["B"]["model"]
        a(f"| {s_['no']} | {s_['deney']} | {sonuc} | {s_['model']['ll']:.4f} / {_y(s_['model']['ilk'])} | "
          f"{B_['ll']:.4f} / {_y(B_['ilk'])} | {_ga(fm) if fm else '–'} | {_ga(fm['A']) if fm else '–'} | "
          f"{_ga(fm['B']) if fm else '–'} | {s_['harman']['ll']:.4f} / {_y(s_['harman']['ilk'])} | {_ga(fh) if fh else '–'} |")
    a("")
    sec = (dj.get("secim") or {}).get("gruplar") or []
    a(f"- Yayına giren a5 grupları: **{', '.join(sec) if sec else 'yok'}** (yayındaki: {', '.join(at5.A5_SECILI) or 'yok'}); "
      f"alan büyüklüğüne duyarlı harman: {'evet' if (dj.get('secim') or {}).get('hm_alan') else 'hayır'}. "
      f"Deney kaydı: `data/at/deneyler_v5.json` ({dj.get('olusturma', '')}; süre {dj.get('sure_sn', '?')} sn).")
    if dj.get("toplam"):
        tp = dj["toplam"]
        a(f"- Toplam (seçilenler − taban): yalnız model {_ga(tp['model'])}; harman {_ga(tp['harman'])}.")
    a("")


def _v6_bolum(a):
    """v6 turu (derin açık kaynak taraması): lab/at/KAYNAKLAR.md + lab/at/deney6.py + harman katmanı ölçümleri."""
    dj = joku(V6_DOSYA)
    if not dj or not dj.get("adimlar"):
        return
    a("## v6 turu: derin açık kaynak taraması (hava, Kalman figür, mesafe profili, gelişim, LambdaRank)")
    a("")
    a("46 aday tarandı (tablo, sorgular ve yasal notlar: `lab/at/KAYNAKLAR.md`). TJK yasağına uyan, ücretsiz ve lisansı "
      "uygun tek yeni dış sinyal **hava** (Open-Meteo, CC BY 4.0) çıktı; start/kulvar, HP, pedigri, idman/galop ve AGF "
      "için yasal açık kaynak yok (bulunan depoların hepsi tjk.org/atyarisi kazıması). Diğer adaylar aynanın kullanılmayan "
      "boyutlarından ve aynanın git geçmişinden kuruldu. Kapı: deney4 iki katlı kapı; walk-forward (her ay yalnız "
      "geçmişle eğitim) = hiç oynanmamış gibi sanal oynatma. Sızıntı testi: `python lab/at/deney6.py --sizinti`.")
    hv = dj.get("hava") or {}
    if hv:
        a(f"Hava kapsamı: {hv.get('hava_var', '?'):,} / {hv.get('kosu', '?'):,} koşu (son gün {hv.get('son_tarih')}).")
    a("")
    a("| # | deney | sonuç | ort. LL / ilk seçim | B: LL / ilk | ΔLL birleşik [%95 GA] | ΔLL A | ΔLL B | harman ort. LL / ilk | ΔLL harman |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for s_ in dj["adimlar"]:
        sonuc = ("taban" if s_["gecti"] is None else "ℹ️ sağlamlık" if s_.get("saglamlik")
                 else ("✅ kaldı" if s_["gecti"] else "❌ elendi"))
        fm, fh = s_.get("fark_model"), s_.get("fark_harman")
        B_ = s_["katlar"]["B"]["model"]
        a(f"| {s_['no']} | {s_['deney']} | {sonuc} | {s_['model']['ll']:.4f} / {_y(s_['model']['ilk'])} | "
          f"{B_['ll']:.4f} / {_y(B_['ilk'])} | {_ga(fm) if fm else '–'} | {_ga(fm['A']) if fm else '–'} | "
          f"{_ga(fm['B']) if fm else '–'} | {s_['harman']['ll']:.4f} / {_y(s_['harman']['ilk'])} | {_ga(fh) if fh else '–'} |")
    a("")
    sec = dj.get("secim") or {}
    a(f"- Kapıdan geçen a6 grupları: **{', '.join(sec.get('gruplar') or []) or 'yok'}**; LambdaRank: "
      f"{'geçti' if sec.get('m6_rank') else 'elendi'}. Yayındaki a6: {', '.join(at6.A6_SECILI) or 'yok'}. "
      f"Deney kaydı: `data/at/deneyler_v6.json` ({dj.get('olusturma', '')}; süre {dj.get('sure_sn', '?')} sn).")
    if dj.get("toplam"):
        tp = dj["toplam"]
        a(f"- Toplam (seçilenler − taban): yalnız model {_ga(tp['model'])}; harman {_ga(tp['harman'])}.")
    pj = joku(V6_PIYASA) or {}
    if pj.get("deneyler"):
        a("")
        a("Harman/yığma katmanı (aynanın git geçmişi; `lab/at/oran_izi.py`, `lab/at/ucuncu_taraf.py`; taban "
          "`replay_kosular.json` sızıntısız olasılıkları, aylık walk-forward):")
        a("")
        a("| deney | koşu | ΔLL [%95 GA] | sonuç |")
        a("|---|---|---|---|")
        for d in pj["deneyler"]:
            a(f"| {d['ad']} | {d['kosu']:,} | {d['dll']:+.4f} [{d['ga95'][0]:+.4f}, {d['ga95'][1]:+.4f}] | "
              f"{'✅' if d['gecti'] else '❌ elendi'} |")
        a("")
        a("- Oran hareketi nihai orana bilgi katmıyor: nihai ganyan oranı erken parayı zaten içeriyor (erken oranın kendi "
          "LL'si çok daha kötü). Aynadaki üçüncü taraf tahminleri bizim sabah modelimizden belirgin zayıf.")
    a("")


def _jokey_bolum(a):
    """🏇 Jokey ve ahır uzmanı: kapılı jk_* deneyleri + jokeyler.json'dan ilk 5 (deney4 kapısı, lab/at/deney_jokey.py)."""
    jj = joku(JOKEY_DOSYA)
    if not jj:
        return
    dj = jj.get("deney") or {}
    a("## Jokey ve ahır (attan arındırılmış beceri)")
    a("")
    a("Jokey, antrenör ve at güçleri koşu içi Plackett-Luce ile **ortak** ve Bayes küçültmeli tahmin edilir (her varlık için "
      "ortalama + belirsizlik; zamanla belirsizlik geri açılır). Jokeyin \"katkısı\" aynı at ve ahırla ortalama jokeye göre "
      "güç farkıdır; ek sinyaller jokeysiz beklentiye göre kalıntılardan: jokey–antrenör / jokey–at birlikteliği, jokey "
      "değişimi, son 14/30 gün formu, günlük iş yükü (programdan), pist/mesafe/hipodrom uzmanlığı, apranti vekili, "
      "\"üst jokey seçimi\". Hepsi yalnız koşu gününden önceki veriyle (sızıntı testi: `python lab/at/deney_jokey.py --sizinti`).")
    a("")
    ad = dj.get("adimlar") or []
    if ad:
        a("Kapılı deneyler (v4 iki katlı kapı; ΔLL = yeni − önceki kabul, yalnız model, koşu-bootstrap %95 GA):")
        a("")
        a("| # | grup | sonuç | ort. LL / ilk seçim | B: LL / ilk | ΔLL birleşik [%95 GA] | ΔLL A | ΔLL B | harman ort. |")
        a("|---|---|---|---|---|---|---|---|---|")
        for s_ in ad:
            sonuc = "taban" if s_["gecti"] is None else ("✅ kaldı" if s_["gecti"] else "❌ elendi")
            fm = s_.get("fark_model")
            B_ = s_["katlar"]["B"]["model"]
            a(f"| {s_['no']} | {s_['deney']} | {sonuc} | {s_['model']['ll']:.4f} / {_y(s_['model']['ilk'])} | "
              f"{B_['ll']:.4f} / {_y(B_['ilk'])} | {_ga(fm) if fm else '–'} | {_ga(fm['A']) if fm else '–'} | "
              f"{_ga(fm['B']) if fm else '–'} | {s_['harman']['ll']:.4f} |")
        a("")
        sec = dj.get("secim") or []
        a(f"- Yayına giren jk grupları: **{', '.join(sec) if sec else 'yok'}** (yayındaki: {', '.join(jokey.JK_SECILI) or 'yok'}). "
          f"Deney kaydı: `data/at/jokeyler.json` → `deney` ({dj.get('olusturma', '')}; süre {dj.get('sure_sn', '?')} sn).")
        if dj.get("toplam"):
            tp = dj["toplam"]
            a(f"- Toplam (seçilenler − v4 taban): yalnız model {_ga(tp['model'])}; harman {_ga(tp['harman'])}.")
    jk = jj.get("jokeyler") or []
    if jk:
        a(f"- Dönem {jj['donem'][0]} → {jj['donem'][1]} (son 90 gün, en az 30 biniş). Katkı = 10 atlı koşuda ortalama ata binince "
          "kazanma olasılığının ortalama jokeye göre farkı (puan). İlk 5:")
        a("")
        a("| jokey | biniş (90 g) | kazanma | ilk 3 | katkı (puan) | z | form | uzmanlık |")
        a("|---|---|---|---|---|---|---|---|")
        for d in jk[:5]:
            u = d.get("uzmanlik") or {}
            a(f"| {d['ad']} | {d['binis_90g']} | {_y(d['kazanma_90g'])} | {_y(d['ilk3_90g'])} | {d['katki']:+.1f} | "
              f"{d.get('katki_z', 0):.1f} | {d['form_trend']} | {u.get('pist') or '–'} / {u.get('mesafe') or '–'} / {u.get('hipodrom') or '–'} |")
    a("")


def _v3_ozet(a, mj):
    """v3 turu (25.10.2026 akşam): atyarisi.com kararı + kapılı deneyler (deneyler_v3.json'dan)."""
    dj = joku(DENEY3_DOSYA)
    a("## Özet: v3 turu (25.10.2026 akşam; rakamlar v3 modelinin)")
    a("")
    a("**Yeni veri kaynağı (atyarisi.com) — bağlanmadı.** Keşif (yalnız GitHub Actions'tan, ≤30 istek, ≥2 sn ara) şunu gösterdi: "
      "www.atyarisi.com sayfaları yalnız boş bir uygulama kabuğu; program/AGF/sonuç verisi tarayıcıda "
      "`tjkbulten.atyarisi.com/api` ve `tjkgw.atyarisi.com/api` adreslerinden çekiliyor ve bu iki alan adının robots.txt'i "
      "**tüm robotlara `Disallow: /`** diyor. llms.txt izni yalnız `www.atyarisi.com` için. Kullanım Şartları metni de "
      "robots ile kapalı `help.atyarisi.com`'dan yükleniyor (otomatik okunamadı). Kırmızı çizgi (robots'a uy) gereği "
      "kaynak bağlanmadı; HP, kulvar, AGF, KGS, EİD, orijin özellikleri bu turda yok (bkz. model.json `kaynaklar`).")
    a("")
    if not dj:
        a("- v3 deney kaydı yok.")
        a("")
        return
    a("Kapılı deneyler (aynı 3.282 sınama koşusu; ΔLL = yeni − önceki kabul, koşu başına; köşeli parantez koşu-bootstrap %95 GA):")
    a("")
    a("| # | deney | sonuç | yalnız model LL / ilk seçim | harman LL / ilk seçim | ΔLL model [%95 GA] | ΔLL harman [%95 GA] |")
    a("|---|---|---|---|---|---|---|")
    for s_ in dj["adimlar"]:
        m, h = s_["model"], s_["harman"]
        sonuc = "taban" if s_["gecti"] is None else ("✅ kaldı" if s_["gecti"] else "❌ elendi")
        fm = _ga(s_["fark_model"]) if s_.get("fark_model") else "–"
        fh = _ga(s_["fark_harman"]) if s_.get("fark_harman") else "–"
        a(f"| {s_['no']} | {s_['deney']} | {sonuc} | {m['ll']:.4f} / {_y(m['ilk'])} | {h['ll']:.4f} / {_y(h['ilk'])} | {fm} | {fh} |")
    a("")
    a(f"- Piyasa keskinleştirme kontrolü (q^β tek başına): keskin − piyasa {_ga(dj['piyasa_keskin_vs_piyasa'])}; "
      f"**harman − keskin piyasa {_ga(dj['harman_vs_keskin'])}** (model ancak bu negatifse piyasaya bilgi katıyor demektir); "
      f"harman − piyasa {_ga(dj['harman_vs_piyasa'])}; yalnız model − piyasa {_ga(dj['model_vs_piyasa'])}.")
    hk = dj.get("hz_sinif_kiyas")
    if hk:
        a(f"- Hız figürü gün değişkeni: Beyer projeksiyonu (atların önceki figürleri) yerine kazanan − par − sınıf ofseti "
          f"kullanılsaydı yalnız-model LL {_ga(hk['fark_model'])} kötüleşirdi (cins/sınıf karışımı yüzünden); projeksiyon yayında.")
    sl = (mj.get("degerlendirme") or {}).get("sira_ll")
    if sl:
        a(f"- İndirimli Harville (ikili/üçlü sıralı log-loss, sınama): yalnız model γ,δ öğrenilmiş {sl['model']['ikili_ll']:.4f} / "
          f"{sl['model']['uclu_ll']:.4f} vs düz Harville {sl['model_h1']['ikili_ll']:.4f} / {sl['model_h1']['uclu_ll']:.4f}; "
          f"harman {sl['harman']['ikili_ll']:.4f} / {sl['harman']['uclu_ll']:.4f} vs {sl['harman_h1']['ikili_ll']:.4f} / "
          f"{sl['harman_h1']['uclu_ll']:.4f} ({sl['model']['kosu']} koşu).")
    a("- Sızıntı testi (`lab/at/test_sizinti.py`, her gece): aynı (at, gün) satırları özdeş; rastgele günlerde yalnız "
      "geçmişten yeniden kurulan durum tam tabloyla birebir aynı; gün içi koşu sırası özellikleri değiştirmiyor.")
    a("")


def _canli_bolum(a):
    """Gün içi robot (lab/at/canli.py) — kısa açıklama + son canlı dosyanın özeti."""
    d = os.path.join(CIKTI, "canli")
    son = sorted(f for f in os.listdir(d) if f.endswith(".json")) if os.path.isdir(d) else []
    a("## Gün içi robot (canlı oran + aynı akşam karne)")
    a("")
    a("- `lab/at/canli.py` (`.github/workflows/at-canli.yml`, 11:00–00:30 TSİ her 30 dk; gece akışıyla aynı eşzamanlılık "
      "grubu, üst üste binmez). Yeniden eğitim yok: kayıtlı yayın modeli yüklenir, durum yalnız koşu gününden ÖNCEKİ "
      "sonuçlarla kurulur (sızıntısız; özellikler gece akışıyla birebir aynı, ölçüldü). Süre ≈10 sn.")
    a("- Ayna yarış günü gün içinde senkronlanıyor: programdaki atların güncel ganyan oranı (sabah 0) ve akşam sonuç dosyası. "
      "Alanın en az yarısında oran varsa `p_piyasa` (marjı ayrılmış) ve `p_oran` (gece ile aynı α/β harmanı) hesaplanır; "
      "oranı 0 olan at (genelde koşmayan) piyasa/harman dışında kalır.")
    a("- Sonucu gelen koşular aynı akşam `data/at/canli/<tarih>.json` içinde puanlanır; sabah kilitli tahminler "
      "`data/at/karne.json`'a koşu kimliğiyle idempotent eklenir (çift sayım yok, gün özeti yeniden hesaplanır).")
    if son:
        cj = joku(os.path.join(d, son[-1]), {})
        ks = cj.get("kosular", [])
        bt = [k for k in ks if k.get("sonuc")]
        a(f"- Son canlı dosya {cj.get('tarih')} (güncelleme {cj.get('guncelleme_tsi')} TSİ): {len(ks)} koşu, "
          f"{sum(k['durum'] == 'oran_var' for k in ks)} oranlı bekleyen, {len(bt)} bitti; modelin (sabah) ilk seçimi "
          f"{sum(k['sonuc']['tuttu'] for k in bt)}/{len(bt)} tuttu.")
    a("")


def _ga_y(g):
    return f"[{g[0]:+.4f}, {g[1]:+.4f}]" if g else "–"


def _replay_ozet(a, mj):
    """Gün gün yeniden oynatma (replay.json) özeti: senaryolar, kırılımlar, Altın at kuralı, deneyler, idman verisi."""
    rj = joku(REPLAY_DOSYA)
    if not rj or not rj.get("ozet"):
        return
    o = rj["ozet"]
    a(f"## Yeniden oynatma (replay): {rj['donem'][0]} → {rj['donem'][1]}")
    a("")
    a(f"Geçmiş koşular hiç oynanmamış gibi yeniden yarıştırıldı: {rj['gun']} yarış günü, {rj['kosu']:,} koşu "
      f"({rj.get('tam_oranli_kosu', 0):,} tam oranlı). Her gün için tahmin, yayındaki sistemin o sabah üreteceği gibi: katsayılar "
      f"{rj['yenileme_gun']} günde bir yalnız o günden önceki sonuçlarla yeniden eğitildi ({rj['yenileme_sayisi']} yenileme), özellikler "
      "o günden önceki sonuçlarla. **sabah** = yalnız model (oransız), **oran** = model + nihai ganyan oranı harmanı, **favori** = "
      f"yalnız nihai oran. Süre: {rj.get('sure_sn', 0) // 60} dk {rj.get('sure_sn', 0) % 60} sn (yerel, 2 çekirdek). `lab/at/replay.py`, "
      "çıktı `data/at/replay.json`; at bazında olasılıklar `data/at/replay_kosular.json`.")
    a("")
    a("| senaryo | koşu | ilk seçim kazandı | ilk seçim ilk 3'te | ikili sıralı | ikili sırasız | log-loss |")
    a("|---|---|---|---|---|---|---|")
    for s_ in ("sabah", "oran", "favori"):
        x = o.get(s_)
        if x:
            a(f"| {s_} | {x['kosu']:,} | {_y(x['ilk_secim'])} | {_y(x['ilk3_icinde'])} | {_y(x['ikili_sirali'])} | "
              f"{_y(x['ikili_sirasiz'])} | {x['log_loss']:.4f} |")
    a("")
    f = rj.get("fark") or {}
    for s_ in ("sabah", "oran"):
        x = f.get(s_ + "_eksi_piyasa")
        if x:
            a(f"- {s_} − piyasa (ortak {x['kosu']:,} koşu): log-loss {x['ll_fark']:+.4f} {_ga_y(x['ga95'])}, ilk seçim "
              f"{100 * x['ilk_fark']:+.1f} puan {_ga_y(x['ilk_ga95'])}.")
    a("")
    kr = rj.get("kirilim") or {}
    for ad_, bas in (("hipodrom", "hipodrom"), ("pist", "pist"), ("alan_buyuklugu", "alan (koşan at)"), ("sinif", "sınıf türü")):
        t = kr.get(ad_)
        if not t:
            continue
        a(f"| {bas} | koşu | sabah ilk | oran ilk | favori ilk | sabah LL | sabah − piyasa LL [%95 GA] |")
        a("|---|---|---|---|---|---|---|")
        for k, v in t.items():
            sp = v.get("sabah_eksi_piyasa_ll") or {}
            a(f"| {k} | {v['kosu']} | {_y((v.get('sabah') or {}).get('ilk_secim'))} | {_y((v.get('oran') or {}).get('ilk_secim'))} | "
              f"{_y((v.get('favori') or {}).get('ilk_secim'))} | {(v.get('sabah') or {}).get('log_loss', '–')} | "
              f"{sp.get('fark', 0):+.4f} {_ga_y(sp.get('ga95'))} |")
        a("")
    if rj.get("yorum"):
        for y in rj["yorum"]:
            a(f"- {y}")
        a("")
    sa = rj.get("secilen_altin") or {}
    if sa:
        b = sa["bolum"]
        a(f"### Altın at kuralı (seçim {b['secim'][0]}→{b['secim'][1]}, {b['gun_secim']} gün; rapor {b['sinama'][0]}→{b['sinama'][1]}, "
          f"{b['gun_sinama']} gün — sınama dilimine bakılmadan)")
        a("")
        a(f"Tarama: p_min × fark_min × günde en çok (sabah olasılığı; arayüzdeki gibi p + fark sırasıyla). Koşul: {b['kosul']}. "
          "En iyi uygun 8 satır (seçim dilimi) ve aynı kuralların sınama dilimi sonucu:")
        a("")
        a("| p_min | fark_min | günde en çok | n | kazanma isabeti | ilk 3 isabeti | günde ort. | sınama: n / isabet / ilk 3 |")
        a("|---|---|---|---|---|---|---|---|")
        for r in [r for r in rj.get("altin_tarama", []) if r["uygun"]][:8]:
            sn = r["sinama"]
            a(f"| {r['p_min']:.2f} | {r['fark_min']:.2f} | {r['gunluk_max']} | {r['n']} | {_y(r['isabet'])} | {_y(r['ilk3_isabet'])} | "
              f"{r['gunde_ort']:.2f} | {sn['n']} / {_y(sn['isabet'])} / {_y(sn['ilk3_isabet'])} |")
        a("")
        m = sa["mevcut"]
        if sa.get("aday"):
            ad = sa["aday"]
            a(f"- Seçim dilimindeki en iyi aday: p ≥ {ad['p_min']:.2f}, fark ≥ {ad['fark_min']:.2f}, günde en çok {ad['gunluk_max']} → "
              f"sınamada {ad['sinama']['n']} seçim, isabet {_y(ad['sinama']['isabet'])} (%95 GA {_ga_y(ad['sinama']['isabet_ga95'])}), "
              f"ilk 3 {_y(ad['sinama']['ilk3_isabet'])}, günde {ad['sinama']['gunde_ort']:.2f}.")
        a(f"- Mevcut arayüz kuralı (p ≥ .35, fark ≥ .12, günde 3) sınamada: {m['sinama']['n']} seçim, isabet {_y(m['sinama']['isabet'])} "
          f"(%95 GA {_ga_y(m['sinama']['isabet_ga95'])}), ilk 3 {_y(m['sinama']['ilk3_isabet'])}, günde {m['sinama']['gunde_ort']:.2f}.")
        k = sa["kural"]
        a(f"- **Karar: {sa['karar']}** → `model.json` `altin_kural`: p ≥ {k['p_min']:.2f}, fark ≥ {k['fark_min']:.2f}, günde en çok "
          f"{k['gunluk_max']} (sınama isabeti {_y(k['isabet_sinama'])}, n {k['n_sinama']}).")
        a("")
    dn = (rj.get("deneyler") or {}).get("adimlar")
    if dn:
        a("### Replay zayıflıklarına göre kapılı deneyler (v4 kapısı, iki kat)")
        a("")
        a("| deney | sonuç | ort. LL / ilk seçim | A: LL / ilk | B: LL / ilk | ΔLL birleşik [%95 GA] | ΔLL A | ΔLL B | harman ort. |")
        a("|---|---|---|---|---|---|---|---|---|")
        for d in dn:
            fm = d.get("fark_model")
            sonuc = "taban" if d["gecti"] is None else ("✅ kaldı" if d["gecti"] else "❌ elendi")
            ka = d["katlar"]
            a(f"| {d['deney']} | {sonuc} | {d['model']['ll']:.4f} / {_y(d['model']['ilk'])} | {ka['A']['model']['ll']:.4f} / "
              f"{_y(ka['A']['model']['ilk'])} | {ka['B']['model']['ll']:.4f} / {_y(ka['B']['model']['ilk'])} | "
              + (f"{fm['dll']:+.4f} {_ga_y(fm['ga95'])} | {fm['A']['dll']:+.4f} {_ga_y(fm['A']['ga95'])} | {fm['B']['dll']:+.4f} {_ga_y(fm['B']['ga95'])}"
                 if fm else "– | – | –") + f" | {d['harman']['ll']:.4f} |")
        a("")
    iv = list(rj.get("idman_verisi") or [])
    ar_ = joku(os.path.join(CIKTI, "arastirma.json")) or {}
    if ar_.get("idman"):
        im = ar_["idman"]
        iv.append(f"Gece araştırmacısı ({ar_.get('guncelleme', '?')[:10]}): idman/galop ile ilgili {im['aday_sayisi']} GitHub adayı, "
                  f"açık lisanslı {len(im['lisansli'])}" + (f" ({', '.join(im['lisansli'][:5])})" if im["lisansli"] else "") +
                  "; hiçbiri otomatik bağlanmaz (`data/at/arastirma.json`).")
    if iv:
        a("### İdman (galop/sprint) verisi araştırması")
        a("")
        for y in iv:
            a(f"- {y}")
        a("")


def rapor_yaz(mj, karne, bugun, ayna_durumu):
    d = mj["degerlendirme"]; mt = d["metrik"]; kp = mj["kapi"]; kap = mj["kapsam"]
    L = []
    a = L.append
    a("# OXXai 🐎 At Yarışı Laboratuvarı — Rapor")
    a("")
    a(f"_Otomatik üretildi: {mj['guncelleme']} · model sürümü `{mj['surum']}` · hobi amaçlıdır, garanti değildir · 18+_")
    a("")
    hp = d["harman_eksi_piyasa"]; mp = d["model_eksi_piyasa"]
    anlamli = hp["ll_fark"] + 2 * hp["std_hata"] < 0
    dj = joku(DENEY_DOSYA) or {}
    v1 = (dj.get("adimlar") or [{}])[0]
    _replay_ozet(a, mj)
    _v4_ozet(a, mj)
    _jokey_bolum(a)
    _v6_bolum(a)
    _v5_bolum(a)
    _v3_ozet(a, mj)
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
    a("- Elenenler: basit hız puanı (v3'te Beyer tarzı figür olarak yeniden yazıldı ve kapıdan geçti), jokey/antrenör piyasa ilgisi + ekuri (log-loss'u çok az düşürdü ama ilk seçim isabetini düşürdü); "
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
    _canli_bolum(a)
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
    a("- v4'ten beri ölçüm iki zaman katında (A ≈4,5 ay, B ≈7 ay). Yine de deneylerdeki 0,001–0,003'lük farklar gürültü düzeyinde; "
      "katlar arasında işaret değiştiren sonuçlar (ör. üst kova kalibrasyonu) dönemsel dalgalanmadır. İlk seçim isabetinin standart "
      "hatası kat başına ≈ ±0,8–1,0 puan; \"ilk seçim düşmemeli\" kuralı bu yüzden bazı gerçek log-loss kazançlarını da eler (bilerek temkinli).")
    a("- GBM katmanı `lightgbm` paketine dayanır (iş akışı kurar). Kurulamazsa model doğrusal yedeğe düşer; gerekçeler yalnız doğrusal katmandan üretilir.")
    a("- Sabah kilitleri yalnız model olasılığıdır; piyasa harmanı için koşu öncesi oran gerekir (ayna gün içi oranları düzenli yayınlamıyor).")
    a("- Uygulamadaki üst özet kutusu `degerlendirme.metrik.harman` isabetini gösteriyor; sabah tahmininin kendi isabeti (yalnız model) daha düşüktür.")
    a("")
    a("## Sonraki deneyler")
    a("")
    a("1. Program arşivi uzadıkça form dizisi (2025 öncesi kariyer, gerçek ilk koşu bayrağı) — şimdiden +0,004 işareti var.")
    a("2. Koşu öncesi anlık oran (gün içi görüntüler düzenli gelirse) ile oran hareketi ve sabah→koşu öncesi harman.")
    a("3. Üst kova: izotonik/alan duyarlı kalibrasyon v4'te denendi, dışarıda tutmadı; katlar biriktikçe (≥3 kat) yeniden bakılacak.")
    a("4. Hız puanını kilo ve pist durumuyla düzeltip yeniden denemek; pedigri/idman verisi açık kaynakta bulunursa.")
    a("5. Patlatılmış amacı GBM'ye de uygulamak (v4'te sıra gelmedi: doğrusal derinlik 2 ancak tekrarda geçti).")
    a("")
    a("## Zamanlama")
    a("")
    a("`.github/workflows/at-lab.yml` her gün 05:23 ve 12:23 TSİ'de, ayrıca `lab/at/**` değişince veya elle çalışır (main dalı). "
      "Çıktılar yalnız `data/at/` ve `lab/at/RAPOR.md`'ye yazılır. Gece akışı 2 çekirdekte ≈5–6 dakika sürer (ablasyon haftada bir; ölçüldü: ablasyonlu tam akış 347 sn).")
    a("")
    a(f"_Kaynak atfı: TJK verilerinin herkese açık aynası {veri.AYNA_URL}. Model ve olasılıklar OXXai laboratuvarınındır._")
    open(RAPOR, "w", encoding="utf-8").write("\n".join(L) + "\n")


# ---------------------------------------------------------------- kapı
def tarif():
    """Modelin tarifi (özellikler + ayarlar). Tarif aynıysa gece yalnız yeni veriyle yeniden eğitir."""
    return {"surum": "v4", "ozellikler": list(ozellik.ADLAR), "gbm": M.lgb is not None, "gbm_ayar": M.GBM_AYAR,
            "kal_ayar": M.KAL_AYAR, "ust_kal": M.UST_KAL, "patlat": list(M.PATLAT), "patlat_gbm": M.PATLAT_GBM,
            "gbm_tohum": list(M.GBM_TOHUM), "kat_bas": M.KAT_BAS, "hp_k": ozellik.HP_K,
            "kal_gun": M.KAL_GUN, "yari_omur": M.YARI_OMUR, "pl_hiz": ozellik.PL_HIZ, "pl_kademe": ozellik.PL_KADEME,
            "pm_hiz": ozellik.PM_HIZ, "ewma": ozellik.EWMA_A, "sonum_gun": ozellik.SONUM_GUN,
            "hz_yontem": ozellik.HZ_YONTEM, "henery_model": M.HENERY_MODEL,
            # jokey turu: Bayes PL ayarları yalnız jk_* grubu yayındaysa tarife girer (yoksa tarif değişmesin)
            **({"jk": {"gruplar": list(jokey.JK_SECILI), "onsel": jokey.JK_ONSEL, "surukle": jokey.JK_SURUKLE,
                       "kademe": list(jokey.JK_KADEME)}} if jokey.JK_SECILI else {}),
            **({"a5": {"gruplar": list(at5.A5_SECILI), "k_uyum": at5.K_UYUM, "ant_k": at5.ANT_K}} if at5.A5_SECILI else {}),
            **({"a6": {"gruplar": list(at6.A6_SECILI), "k_r": at6.K_R, "k_q": at6.K_Q}} if at6.A6_SECILI else {})}


def kapi_karari(yeni, iz, trf, eski, eski_iz, b_bas=None):
    """KAPI. Ana ölçüt yalnız-model (sabah tahmini) log-loss ve ilk-seçim isabeti; harman log-loss'u da kötüleşmemeli.
    - Tarif aynı + iz var: gece yeniden eğitimi; ortak koşularda belirgin kötüleşme (veri sorunu) yoksa KABUL.
    - Tarif değişti + iz var: eski ve yeni tahminler ORTAK sınama koşularında kıyaslanır (adil, aynı dilim).
    - İz yok (v1'den geçiş): kayıtlı sınama metrikleriyle kıyaslanır."""
    if not eski:
        return {"karar": "KABUL", "neden": "ilk model (kayıtlı model yok)", "yeni": yeni, "eski": None}
    k = M.iz_kiyas(iz, eski_iz["iz"], b_bas) if eski_iz and eski_iz.get("iz") else None
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
    if k and k.get("B") and k["B"]["kosu"] < k["kosu"] and k["B"]["yeni"]["model_ll"] > k["B"]["eski"]["model_ll"] + 1e-5:
        return {"karar": "RED", "neden": f"en güncel katta (B) yalnız-model log-loss kötüleşti ({k['B']['eski']['model_ll']} → "
                f"{k['B']['yeni']['model_ll']}); dünkü model korunuyor{ek}", "yeni": y, "eski": e}
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

    at6.hava_hazirla()   # v6: a6_hava yayındaysa Open-Meteo hava tablosu (_hava/, depoya yazılmaz)
    kosular, atilan = veri.sonuclari_yukle()
    T, durum = ozellik.tablo_kur(kosular, adlar=ozellik.TUM_ADLAR)
    sec = [ozellik.TUM_ADLAR.index(a) for a in ozellik.ADLAR]
    T_sec = dict(T); T_sec["X"] = T["X"][:, sec]; T_sec["adlar"] = list(ozellik.ADLAR)
    print("tablo:", T_sec["X"].shape, "gbm:", M.lgb is not None)
    # Ablasyon (yalnız rapor için) haftada bir: süre sınırı (ubuntu-latest'te < 10 dk). Arada son ablasyon taşınır.
    eski0 = joku(os.path.join(CIKTI, "model.json")) or {}
    ab_eski = (eski0.get("degerlendirme") or {}).get("ablasyon")
    ab_tarih = (eski0.get("degerlendirme") or {}).get("ablasyon_tarih")
    try:
        ab_yas = (date.fromisoformat(bugun) - date.fromisoformat(ab_tarih)).days if ab_tarih else 99
    except ValueError:
        ab_yas = 99
    ablasyon = not ar.ablasyonsuz and (not ab_eski or ab_yas >= 7 or ozellik.ADLAR != (eski0.get("tarif") or {}).get("ozellikler"))
    m_eval, sonuc, iz = M.degerlendir(T_sec, kosular, ablasyon=ablasyon, gbm=True)
    if ablasyon:
        sonuc["ablasyon_tarih"] = bugun
    elif ab_eski:
        sonuc["ablasyon"], sonuc["ablasyon_tarih"] = ab_eski, ab_tarih
    mt_y = sonuc["metrik"]
    yeni = {"model_ll": mt_y["model"]["log_loss"], "model_ilk": mt_y["model"]["ilk_secim_isabet"],
            "harman_ll": mt_y["harman"]["log_loss"], "harman_ilk": mt_y["harman"]["ilk_secim_isabet"]}
    eski = joku(os.path.join(CIKTI, "model.json"))
    eski_iz = joku(IZ_DOSYA)
    trf = tarif()
    simdi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    kapi = kapi_karari(yeni, iz, trf, eski, eski_iz, sonuc["bolum"]["sinama"][0])
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
    mj["altin_kural"] = altin_kural(eski0)   # yeni model yazılsa da Altın kural korunur
    mj["kapsam"] = veri.kapsam(kosular)
    mj["atilan"] = atilan
    mj["kapi"] = kapi
    mj["gecmis"] = (mj.get("gecmis", []) + [{"tarih": simdi, "karar": kapi["karar"], "log_loss": yeni["harman_ll"],
                                               "ilk_secim_isabet": yeni["harman_ilk"], "model_log_loss": yeni["model_ll"],
                                               "model_ilk_secim_isabet": yeni["model_ilk"]}])[-60:]
    mt = mj["degerlendirme"]["metrik"]
    mj["yayin_modu"] = "model+piyasa" if mt["harman"]["log_loss"] < mt["piyasa"]["log_loss"] else "yalniz_piyasa"
    mj["kaynak"] = {"ayna": veri.AYNA_URL, "lisans": "belirtilmemiş", "not": "Ham veri bu depoya kopyalanmaz; tjk.org'a istek atılmaz."}
    mj["kaynaklar"] = [
        {"ad": "github.com/cenkozgur/tjk-data", "durum": "bağlı", "lisans": "belirtilmemiş",
         "kullanim": "sonuç, program, oran, pist durumu"},
        {"ad": "atyarisi.com (llms.txt izni)", "durum": "bağlanmadı", "inceleme": "2026-10-25",
         "neden": "veri tjkbulten.atyarisi.com / tjkgw.atyarisi.com API'lerinden geliyor ve robots.txt tüm robotlara "
                  "Disallow: / diyor; llms.txt izni yalnız www için ve www sayfalarında veri yok; kullanım şartları da "
                  "robots-kapalı help alanından yükleniyor."}]
    if "a6_hava" in at6.A6_SECILI:
        mj["kaynaklar"].append({"ad": "Open-Meteo (open-meteo.com)", "durum": "bağlı", "lisans": "CC BY 4.0",
                                "kullanim": "hipodrom yağış/sıcaklık (a6_hava); atıf: Hava verisi Open-Meteo.com"})
    mj["uyari"] = "Hobi amaçlıdır; tahmin garanti değildir · 18+"
    mj["gbm_kurulu"] = M.lgb is not None

    son_sonuc = kosular[-1]["tarih"]
    kilit = kilitle([bugun, yarin], son_sonuc, m_uretim, durum, mj["yayin_modu"], mj["surum"])
    print("kilitlenen:", kilit)
    karne, puanlanan = puanla(kosular)
    print("puanlanan:", puanlanan)
    try:   # 6'lı ganyan: geri test + canlı karne (altili_karne.json), bugün/yarın 6'lıları (canlı dosya yoksa sabah tahmini)
        import altili
        altili.karne_guncelle()
        for t in (bugun, yarin):
            altili.gun_guncelle(t)
    except Exception as e:
        print("6'lı güncellenemedi:", type(e).__name__, e)
    try:   # at kuponu: tüm bahis türleri için geri test karnesi (kupon_karne.json) — hata yayını durdurmaz
        import kupon
        kupon.karne_guncelle()
    except Exception as e:
        print("kupon karnesi güncellenemedi:", type(e).__name__, e)
    try:   # jokey/antrenör özetleri (arayüz) — durum tüm sonuçlarla ilerletilmiş; bugünkü binişler sabah kilidinden
        jj = jokey.jokeyler_json(kosular, durum.jk, bugun, os.path.join(TAHMIN, bugun + ".json"),
                                 deney=(joku(JOKEY_DOSYA) or {}).get("deney"))
        jyaz(JOKEY_DOSYA, jj)
        print("jokeyler:", len(jj["jokeyler"]), "jokey,", len(jj["antrenorler"]), "antrenör,", len(jj["ikililer"]), "ikili")
    except Exception as e:   # arayüz özeti yayın modelini asla durdurmaz
        print("jokeyler.json üretilemedi:", type(e).__name__, e)
    try:   # 🐎 at kariyeri (arayüz At profili): yalnız bugün/yarın koşucuları, sonuç arşivinden türetilmiş kompakt özet
        import kariyer
        print("kariyer:", kariyer.yaz(kosular, [bugun, yarin]), "at")
    except Exception as e:   # arayüz özeti yayın modelini asla durdurmaz
        print("kariyer.json üretilemedi:", type(e).__name__, e)
    jyaz(os.path.join(CIKTI, "model.json"), mj)
    rapor_yaz(mj, karne, bugun, ayna)
    print("tamam")


if __name__ == "__main__":
    main()
