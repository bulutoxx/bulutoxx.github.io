# BULUTOXX at yarışı laboratuvarı — gece boru hattı.
# 1) Aynayı sığ klonla/güncelle (yalnız github.com/cenkozgur/tjk-data; tjk.org'a istek YOK)
# 2) Sızıntısız özellikler + tam yeniden eğitim + zaman sıralı sınama
# 3) KAPI: yeni katsayılar ancak sınama log-loss'unu düşürür ve ilk-seçim isabetini bozmazsa kabul
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
TAKIP = [("2026-10-25", "İstanbul", 5)]   # raporda kalıcı izlenen örnek koşu(lar)

IFADE = {  # özellik -> (lehine, aleyhine)
    "yeni": ("", "ilk koşusu, geçmiş verisi yok"),
    "n_kosu": ("az koşmuş, gelişime açık", "çok koşmuş"),
    "skor_son": ("son koşusunda iyi derece", "son koşusunda geride kaldı"),
    "skor3": ("son 3 koşu formu iyi", "son 3 koşu formu zayıf"),
    "skor5": ("son 5 koşu formu iyi", "son 5 koşu formu zayıf"),
    "skor10": ("son 10 koşu formu iyi", "son 10 koşu formu zayıf"),
    "galibiyet10": ("son koşularda kazanma oranı yüksek", "son koşularda kazanamadı"),
    "ilk3_10": ("sık sık ilk 3'te", "nadiren ilk 3'te"),
    "geri_son": ("son koşuda kazanana yakın bitirdi", "son koşuda kazananın epey gerisinde"),
    "geri3": ("son koşularda kazanana yakın", "son koşularda kazananın gerisinde"),
    "piyasa_son": ("son koşusunda piyasa onu öne çıkarmıştı", "son koşusunda piyasa ilgisi düşüktü"),
    "piyasa3": ("son koşularında piyasanın gözdesiydi", "son koşularında piyasa ilgisi düşüktü"),
    "log_gun": ("dinlenme süresi uygun", "dinlenme süresi aleyhine"),
    "uzun_ara": ("", "uzun aradan dönüyor"),
    "pist_uyum": ("bu pistte iyi koşuyor", "bu pistte zayıf"),
    "pist_payi": ("bu pist tecrübesi fazla", "bu pistte az tecrübeli"),
    "mesafe_uyum": ("bu mesafede başarılı", "bu mesafede zayıf"),
    "mesafe_degisim": ("mesafe değişimi lehine", "mesafe değişimi aleyhine"),
    "hipodrom_uyum": ("bu hipodromda başarılı", "bu hipodromda zayıf"),
    "sinif_degisim": ("sınıf düşüyor (daha kolay koşu)", "sınıf yükseliyor (daha zor koşu)"),
    "kilo_fark": ("kilo durumu lehine", "kilo durumu aleyhine"),
    "kilo_degisim": ("kilo değişimi lehine", "kilo değişimi aleyhine"),
    "yas2": ("yaşı lehine", "yaşı aleyhine"), "yas3": ("yaşı lehine", "yaşı aleyhine"),
    "yas6p": ("yaşı lehine", "yaşı aleyhine"),
    "jokey_gal60": ("jokeyi son 60 günde formda", "jokeyinin son 60 günü zayıf"),
    "jokey_ae": ("jokeyi piyasa beklentisinin üstünde kazanıyor", "jokeyi piyasa beklentisinin altında"),
    "antrenor_gal60": ("antrenörü son 60 günde formda", "antrenörünün son 60 günü zayıf"),
    "antrenor_ae": ("antrenörü piyasa beklentisinin üstünde", "antrenörü piyasa beklentisinin altında"),
    "jokey_at_n": ("jokeyiyle çok koştu", "jokeyiyle az koştu"),
    "jokey_at_uyum": ("bu jokeyle iyi sonuçlar almış", "bu jokeyle sonuçları zayıf"),
    "jokey_degisti": ("jokey değişimi lehine", "jokey değişti"),
    "alan_x_form": ("alan büyüklüğü formuna uygun", "alan büyüklüğü aleyhine"),
}


def jyaz(yol, veri_):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    tmp = yol + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
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
def kosu_tahmini(mj, kosu, durum, yayin_modu):
    m = M.Model.yukle(mj)
    X = durum.ozellik(kosu)
    K = M.Kume(X, np.zeros(len(X)), np.zeros(len(X)), np.zeros(len(X)), np.zeros(len(X), int))
    q = veri.piyasa_q([a["oran"] for a in kosu["atlar"]])
    if q is not None and yayin_modu == "model+piyasa":
        p = m.p_harman(X, K, np.asarray(q)); mod = "model+piyasa"
    elif q is not None:
        p = np.asarray(q); mod = "yalnız piyasa (model sınamada piyasayı geçemedi)"
    else:
        p = m.p_model(X, K); mod = "yalnız model (piyasa oranı henüz yok)"
    so = M.sirali_olasiliklar(p, m.gam, m.dlt)
    Z = (X - m.mu) / m.sd
    katki = (Z - Z.mean(0)) * m.w / m.T
    atlar = []
    for i, a in enumerate(kosu["atlar"]):
        o = np.argsort(-katki[i])
        lehte = [IFADE[m.adlar[k]][0] for k in o if katki[i, k] > 0.04 and IFADE[m.adlar[k]][0]][:2]
        aleyh = [IFADE[m.adlar[k]][1] for k in o[::-1] if katki[i, k] < -0.12 and IFADE[m.adlar[k]][1]][:1]
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


def kilitle(gunler, son_sonuc, mj, durum, yayin_modu, surum):
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
            kt = kosu_tahmini(mj, k, durum, yayin_modu)
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


def rapor_yaz(mj, karne, bugun, ayna_durumu):
    d = mj["degerlendirme"]; mt = d["metrik"]; kp = mj["kapi"]; kap = mj["kapsam"]
    L = []
    a = L.append
    a("# BULUTOXX 🐎 At Yarışı Laboratuvarı — Rapor")
    a("")
    a(f"_Otomatik üretildi: {mj['guncelleme']} · model sürümü `{mj['surum']}` · hobi amaçlıdır, garanti değildir · 18+_")
    a("")
    hp = d["harman_eksi_piyasa"]
    anlamli = hp["ll_fark"] + 2 * hp["std_hata"] < 0
    a("## Kısa sonuç (dürüst)")
    a("")
    a(f"- Yalnız geçmiş verilerle kurulan model **tek başına piyasadan belirgin biçimde zayıf**: sınama log-loss "
      f"{mt['model']['log_loss']} (piyasa {mt['piyasa']['log_loss']}), ilk seçim isabeti {_y(mt['model']['ilk_secim_isabet'])} "
      f"(piyasa favorisi {_y(mt['favori']['ilk_secim_isabet'])}).")
    a(f"- Model + piyasa harmanı log-loss'u {mt['harman']['log_loss']}: piyasaya göre fark **{hp['ll_fark']:+.4f} ± {hp['std_hata']:.4f}** "
      f"(std. hata). " + ("Bu fark istatistiksel olarak anlamlı bir iyileşme." if anlamli else
                          "Bu fark **gürültü sınırları içinde**; modelin piyasaya kalıcı bir üstünlüğü kanıtlanmadı."))
    a(f"- Harmanın ilk seçim isabeti {_y(mt['harman']['ilk_secim_isabet'])}, piyasa favorisi {_y(mt['favori']['ilk_secim_isabet'])}. "
      f"Yayın modu: **{mj['yayin_modu']}** (kural: harman sınama log-loss'u piyasadan düşükse model+piyasa yayınlanır).")
    ust = d["kovalar"]["harman"][-1]
    a(f"- Harman en yüksek kovada aşırı güvenli: {ust['aralik']} aralığında ortalama tahmin {_y(ust['ort_tahmin'])}, gerçek {_y(ust['gercek'])} "
      f"({ust['at']} at). Piyasa aynı kovada {_y(d['kovalar']['piyasa'][-1]['ort_tahmin'])} / {_y(d['kovalar']['piyasa'][-1]['gercek'])}.")
    a("- Piyasa (son koşu öncesi ganyan oranı) bu veride en güçlü bilgi; model şimdilik ancak küçük düzeltmeler yapıyor. "
      "Pratikte: koşu öncesi oran varken en güvenilir olasılık piyasanın kendisidir; model yorum/gerekçe katmanı olarak değerli.")
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
    a(f"- Zaman sıralı bölüm: ısınma (yalnız geçmiş biriktirme) < {b['isinma_bitis']}; model eğitimi {b['egitim'][0]}→{b['egitim'][1]} "
      f"({d['kosu_sayisi']['egitim']} koşu); harman/kalibrasyon {b['harman'][0]}→{b['harman'][1]} ({d['kosu_sayisi']['harman']}); "
      f"**sınama (son %30) {b['sinama'][0]}→{b['sinama'][1]} ({d['kosu_sayisi']['sinama']} koşu)**.")
    a("- Piyasa olasılığı q: **nihai** ganyan oranından (1/oran, marj ayrılmış). Bu, \"son koşu öncesi\" piyasayı temsil eder; "
      "sabah programında oran yoktur. Yani harman ancak koşudan hemen önce kullanılabilir; sabah kilitlenen tahminler yalnız modeldir.")
    a("- Kullanılmayanlar: aynanın memory/*.json özetleri (geleceği içerir → sızıntı), gün içi oran görüntüleri (yalnız 57 gün), "
      "hava/nem (yalnız 2026-04 sonrası programlarda).")
    a("")
    a("## Sınama metrikleri (son %30, yalnız tam oranlı koşular)")
    a("")
    a("| | log-loss ↓ | Brier ↓ | ilk seçim | ikili (sıralı) | ilk iki → ilk 2 | p≥.30 seçim / isabet (ort. p) | p≥.50 seçim / isabet (ort. p) |")
    a("|---|---|---|---|---|---|---|---|")
    for ad_, et in (("model", "Model (yalnız geçmiş)"), ("piyasa", "Piyasa q"), ("harman", "**Model + piyasa**"), ("favori", "Favori tabanı"), ("duzgun", "Düzgün (1/N)")):
        r = mt[ad_]

        def es(k):
            v = r.get(k)
            return f"{v['secim']} / {_y(v['isabet'])} ({_y(v['ort_p'])})" if v else "–"
        a(f"| {et} | {r.get('log_loss', '–')} | {r.get('brier', '–')} | {_y(r.get('ilk_secim_isabet'))} | {_y(r.get('ikili_sirali_isabet'))} | "
          f"{_y(r.get('ilk_iki_ikisi_de_ilk2'))} | {es('p>=0.30')} | {es('p>=0.50')} |")
    a("")
    mp = d["model_eksi_piyasa"]
    a(f"Eşleştirilmiş log-loss farkı (koşu başına, ± std. hata): harman − piyasa = {hp['ll_fark']:+.4f} ± {hp['std_hata']:.4f}; "
      f"model − piyasa = {mp['ll_fark']:+.4f} ± {mp['std_hata']:.4f}.")
    m = mj["uretim_modeli"]
    a("")
    a(f"Parametreler (yayın modeli): harman α = {m['alfa']}, β = {m['beta']}; yalnız-model sıcaklığı T = {m['sicaklik']}; "
      f"Henery üsleri γ(2.) = {m['henery_gamma']}, δ(3.) = {m['henery_delta']}; L2 λ = {m['lambda']}.")
    a("")
    a("### Kalibrasyon (sınama, model + piyasa)")
    a("")
    a("| tahmin aralığı | at | ort. tahmin | gerçek kazanma |")
    a("|---|---|---|---|")
    for k in d["kovalar"]["harman"]:
        a(f"| {k['aralik']} | {k['at']} | {_y(k['ort_tahmin'])} | {_y(k['gercek'])} |")
    a("")
    a("## Neler önemli?")
    a("")
    a("Standartlaştırılmış katsayılar (en büyük 10; + kazanma şansını artırır):")
    a("")
    a("| özellik | katsayı |")
    a("|---|---|")
    for o in d["onem"][:10]:
        a(f"| {o['ozellik']} | {o['std_katsayi']:+.3f} |")
    a("")
    a("Ablasyon — grup çıkarılınca sınama log-loss'u ne kadar kötüleşiyor (+ = grup faydalı):")
    a("")
    a("| çıkarılan grup | yalnız model Δ | model+piyasa Δ |")
    a("|---|---|---|")
    for o in d.get("ablasyon", []):
        a(f"| {o['grup_cikarildi']} | {o['model_ll_fark']:+.4f} | {o['harman_ll_fark']:+.4f} |")
    a("")
    a("Yorum: jokeyin son 60 gün formu, at formu (son koşu sıraları, kazanana uzaklık), geçmiş koşulardaki piyasa ilgisi ve "
      "pist/mesafe/hipodrom uyumu modeli tek başına en çok taşıyan bilgiler. Ancak bunların çoğu piyasada zaten fiyatlanmış; "
      "harman sütunundaki farklar ±0,001 düzeyinde, yani piyasanın üstüne eklenen bilgi çok az.")
    a("")
    a("## Kapı (sürekli öğrenme)")
    a("")
    a(f"- Son karar ({kp['tarih']}): **{kp['karar']}** — {kp['neden']}")
    if kp.get("yeni"):
        a(f"- Yeni deneme: log-loss {kp['yeni']['log_loss']}, ilk seçim {_y(kp['yeni']['ilk_secim_isabet'])}; "
          f"kayıtlı model aynı sınamada: " + (f"log-loss {kp['eski']['log_loss']}, ilk seçim {_y(kp['eski']['ilk_secim_isabet'])}" if kp.get("eski") else "yok"))
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
    # gösteri
    a(f"## Gösteri: {bugun} İstanbul tahminleri")
    a("")
    kt = joku(os.path.join(TAHMIN, bugun + ".json"))
    ist = [k for k in (kt or {}).get("kosular", []) if k["hipodrom"] == "İstanbul"]
    if ist:
        a(f"Kilit zamanı {kt.get('kilit_zamani_tsi', kt['kilit_zamani'])} TSİ. Mod: {ist[0]['mod']}. (Oran olmadığında bunlar **yalnız model** "
          "olasılıklarıdır; sınamada yalnız model piyasa favorisinden zayıftı — bilgi amaçlıdır.) "
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
        a(f"{k['mesafe']} m {k['pist']}, {k['sinif']}, saat {k.get('saat') or '–'}. Mod: {k['mod']}. Kilit: {kt.get('kilit_zamani_tsi', kt['kilit_zamani'])} TSİ.")
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
    a("## Denenmiş ama kapıdan geçmemiş fikirler (25.10.2026 ölçümü)")
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
    a("- Kapı tek sınama dilimine bakıyor; günlük gürültüyle sık red beklenir (koruyucu tasarım).")
    a("- Sabah kilitleri yalnız model olasılığıdır; piyasa harmanı için koşu öncesi oran gerekir (ayna gün içi oranları düzenli yayınlamıyor).")
    a("")
    a("## Sonraki deneyler")
    a("")
    a("1. Koşu öncesi anlık oran (gün içi görüntüler düzenli gelirse) ile oran hareketi özelliği ve sabah→koşu öncesi harman.")
    a("2. Hız puanı: hipodrom/pist/mesafe standart derecesine göre normalize derece (beaten-time yerine), pist durumu düzeltmeli.")
    a("3. Genişleyen pencerede (walk-forward, aylık yeniden eğitim) harman α/β'nın kararlılığı; dönem kayması için zaman ağırlıklı eğitim.")
    a("4. Programdaki form dizilerinden (2025 öncesi koşular) eski kariyer bilgisini çıkarmak; pedigri/idman verisi açık kaynakta bulunursa.")
    a("")
    a("## Zamanlama")
    a("")
    a("`.github/workflows/at-lab.yml` her gece 02:23 UTC (05:23 TSİ) için ayarlı; **ancak GitHub zamanlanmış iş akışlarını yalnız varsayılan "
      "daldan (main) çalıştırır**. Bu dosya main'e birleştirilene kadar iş akışı yalnız `at-hazirlik` dalına `lab/at/**` itildiğinde "
      "veya elle (workflow_dispatch) çalışır. Çıktılar her durumda yalnız `at-hazirlik` dalına yazılır.")
    a("")
    a(f"_Kaynak atfı: TJK verilerinin herkese açık aynası {veri.AYNA_URL}. Model ve olasılıklar BULUTOXX laboratuvarınındır._")
    open(RAPOR, "w", encoding="utf-8").write("\n".join(L) + "\n")


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
    T, durum = ozellik.tablo_kur(kosular)
    print("tablo:", T["X"].shape)
    m_eval, sonuc, (K, B) = M.degerlendir(T, kosular, ablasyon=not ar.ablasyonsuz)
    yeni = {"log_loss": sonuc["metrik"]["harman"]["log_loss"], "ilk_secim_isabet": sonuc["metrik"]["harman"]["ilk_secim_isabet"]}
    eski = joku(os.path.join(CIKTI, "model.json"))
    simdi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    eski_olcum = None
    if not eski:
        kabul, neden = True, "ilk model (kayıtlı model yok)"
    else:
        eski_olcum = M.eski_modeli_sina(eski.get("degerlendirme_modeli"), K, B)
        ref = eski_olcum or {"log_loss": eski["degerlendirme"]["metrik"]["harman"]["log_loss"],
                             "ilk_secim_isabet": eski["degerlendirme"]["metrik"]["harman"]["ilk_secim_isabet"]}
        ek = "" if eski_olcum else " (özellik listesi değişti; kayıtlı metriklerle kıyaslandı)"
        if yeni["log_loss"] < ref["log_loss"] - 1e-5 and yeni["ilk_secim_isabet"] >= ref["ilk_secim_isabet"]:
            kabul, neden = True, f"log-loss {ref['log_loss']}→{yeni['log_loss']}, ilk seçim {ref['ilk_secim_isabet']}→{yeni['ilk_secim_isabet']}{ek}"
        elif yeni["log_loss"] >= ref["log_loss"] - 1e-5:
            kabul, neden = False, f"log-loss düşmedi ({ref['log_loss']} → {yeni['log_loss']}); dünkü model korunuyor{ek}"
        else:
            kabul, neden = False, f"ilk seçim isabeti düştü ({ref['ilk_secim_isabet']} → {yeni['ilk_secim_isabet']}); dünkü model korunuyor{ek}"
    kapi = {"tarih": simdi, "karar": "KABUL" if kabul else "RED", "neden": neden, "yeni": yeni, "eski": eski_olcum}
    print("kapı:", kapi["karar"], neden)
    if kabul:
        uretim = M.uretim_modeli(T, kosular, m_eval.lam)
        mj = {"surum": simdi[:16].replace(":", "").replace("-", ""), "olusturma": simdi,
              "degerlendirme": sonuc, "degerlendirme_modeli": m_eval.json(), "uretim_modeli": uretim.json(),
              "gecmis": (eski or {}).get("gecmis", [])}
    else:
        mj = eski
        mj["reddedilen_son_deneme"] = {"tarih": simdi, "metrik": sonuc["metrik"]}
    mj["guncelleme"] = simdi
    mj["kapsam"] = veri.kapsam(kosular)
    mj["atilan"] = atilan
    mj["kapi"] = kapi
    mj["gecmis"] = (mj.get("gecmis", []) + [{"tarih": simdi, "karar": kapi["karar"], "log_loss": yeni["log_loss"],
                                               "ilk_secim_isabet": yeni["ilk_secim_isabet"]}])[-60:]
    mt = mj["degerlendirme"]["metrik"]
    mj["yayin_modu"] = "model+piyasa" if mt["harman"]["log_loss"] < mt["piyasa"]["log_loss"] else "yalniz_piyasa"
    mj["kaynak"] = {"ayna": veri.AYNA_URL, "lisans": "belirtilmemiş", "not": "Ham veri bu depoya kopyalanmaz; tjk.org'a istek atılmaz."}
    mj["uyari"] = "Hobi amaçlıdır; tahmin garanti değildir · 18+"

    son_sonuc = kosular[-1]["tarih"]
    kilit = kilitle([bugun, yarin], son_sonuc, mj["uretim_modeli"], durum, mj["yayin_modu"], mj["surum"])
    print("kilitlenen:", kilit)
    karne, puanlanan = puanla(kosular)
    print("puanlanan:", puanlanan)
    jyaz(os.path.join(CIKTI, "model.json"), mj)
    rapor_yaz(mj, karne, bugun, ayna)
    print("tamam")


if __name__ == "__main__":
    main()
