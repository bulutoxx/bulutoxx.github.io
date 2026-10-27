# Küresel at yarışı kaynakları — tarama, yasal durum, robota aktarım (26–27.10.2026)

Kapsam: Türkiye dışı veri setleri, açık veri portalları, akademik yöntemler, pedigri kaynakları ve kamuya açık
hız/handikap/kilo metodolojileri. Türkiye'ye özgü kaynaklar (TJK aynaları, Open-Meteo, aynadaki kullanılmayan alanlar)
ayrı ajanın işidir (at-derin dalı, KAYNAKLAR.md) ve burada tekrarlanmadı.

**Kural özeti:** tjk.org, medya-cdn.tjk.org, vhs*.tjk.org, atyarisi.com (+alt alanlar) ve web.archive.org kopyalarına hiç
istek atılmadı. Kazımayı yasaklayan siteler kazınmadı. Ücretli API, hesap açma, giriş, kişisel veri yok. Ham veri commit
edilmedi; depoda yalnız türetilmiş küçük tablolar (WFA ölçeği, deney metrikleri) var.

**Ortam kısıtı (ölçüldü):** bu oturumun ağ geçidi yalnız GitHub (git clone / raw) ve PyPI'ye izin veriyor;
Kaggle, Hugging Face, Zenodo, Dryad, Figshare, CRAN, data.gouv.fr, storage.googleapis.com bağlantıları 403 ile reddedildi.
GitHub arama API'si de oturuma bağlı depolarla sınırlı. 27.10.2026 yeniden ölçüldü: query.wikidata.org ve www.wikidata.org da 403 (vekil reddi). Bu yüzden veri indirmesi gerektiren adaylar “erişim: ortamda
kapalı” olarak işaretlendi; karar sütunu yasal kullanılabilirliği ayrıca gösterir.

## Aynanın sınırı (tüm aktarımı belirleyen gerçek)

`cenkozgur/tjk-data` at satırında yalnız `name, no, jockey, trainer, weight, odds, age, position, finishTime, nonRunner,
form(boş)` var. **Baba/anne/aygır alanı yok, cinsiyet yok, kulvar (start no) yok, koşu içi pozisyon yok.** Sonuç:
aygır/baba önseli (“baba gücü / mesafe eğilimi / pist eğilimi”) aynayla eşlenemez; bağlanabilecek tek köprü at adıdır
ve uluslararası açık pedigri kaynakları (Wikipedia/Wikidata) yalnız ünlü atları içerir — Türkiye'de koşan atların
çok küçük bir bölümü. Pedigri alanı başka bir yasal kaynaktan gelirse, aşağıdaki P-satırları hazır yöntemdir.

## En iyi 10 (robota aktarılabilirlik × kanıt × yasal açıklık)

| sıra | # | kaynak | neden | durum |
|---|---|---|---|---|
| 1 | 41 | Benter 1994 iki aşamalı model + piyasa | yayındaki harmanın temeli; 2. aşama eğriliği (gl_flb) sınandı | ✅ zaten var + gl_flb sınandı |
| 2 | 38 | Lo & Bacon-Shone indirimli Harville (γ, δ) | 2./3. sıra olasılıkları (ikili/üçlü tahmini) | ✅ gl_harville denetimi |
| 3 | 43 | Shin 1992/93 marj ayırma | kayırma–uzun atış (FLB) düzeltmeli piyasa olasılığı | ✅ gl_piyasa adayı |
| 4 | 44 | Odds-ratio (Cheung 2015) / power (Clarke vd. 2017) | FLB'ye duyarlı q; power ≡ harman β | ✅ gl_piyasa adayı |
| 5 | 30 | ARCI-010-020 WFA ölçeği | kamuya açık, tarih/mesafe/yaş tablosu; sabah bilinir | ✅ gl_wfa |
| 6 | 51/66 | Burges LambdaMART / LightGBM lambdarank | sıralama amaçlı GBM | ✅ gl_lambdarank (+ deney6 m6_rank) |
| 7 | 47 | Snowberg & Wolfers 2010 | FLB'nin algı hatası olduğu → q'da eğrilik terimi gerekçesi | 📘 gl_flb gerekçesi |
| 8 | 24 | Sharman vd. 2022 (CC0, İngiltere/İrlanda hız verisi) | açık lisanslı büyük veri; yaş/ebeveyn yaşı etkisi | ⏸ ortamda kapalı, anonim |
| 9 | 56 | Wikidata P22/P25 (CC0) aygır önseli | pedigri önseli (h²≈0,1–0,3) | ⏸ ortamda 403; aynada baba adı yok, Ek kaynak A soy grubu (a6_ek_soy) zaten elendi |
| 10 | 13 | Huggy Database (Fransa, 356 bin koşu) | jokey/antrenör/kilo/oran etkilerinin dış kıyası | ⏸ ortamda kapalı, lisans belirsiz |

## Aday tablosu (66 aday)

Değer: **V** = doğrudan veri, **Ö** = önsel (sabit tablo/katsayı), **Y** = yöntem. Karar: ✅ uygulandı/sınandı,
📘 yalnız yöntem notu, ⏸ yasal ama ortamda erişilemez / eşleşme yok, ⛔ kullanım şartı/ücret nedeniyle kullanılmaz.

### Veri setleri

| # | Kaynak | İçerik / kapsam | Erişim | Lisans / şart | Değer | Karar |
|---|---|---|---|---|---|---|
| 1 | Kaggle `gdaley/hkracing` | HKJC 1997–2005 koşular+koşanlar (≈6 bin koşu, kulvar, at kilosu, oran) | Kaggle (giriş gerekir) | Kaggle sayfası lisansı; kaynak HKJC | V/Ö (genel kilo/ara etkisi) | ⏸ giriş + ortamda kapalı |
| 2 | Kaggle `jeffreymuller` HK 2013–2020 | HKJC sonuçları | Kaggle (giriş) | belirsiz; kaynak HKJC | V | ⏸ |
| 3 | eprochasson HK/Singapur kazıyıcı çıktısı (1979–2018; aygır/anne, sektörel) | GitHub (URL bulunamadı) | lisans belirsiz; kaynak HKJC/STC | V/Ö | ⏸ depo adresi doğrulanamadı |
| 4 | renavon.com HKJC paketleri | sonuç, oran, sektörel, “comments on running” | ücretli | ticari | V | ⛔ ücretli |
| 5 | Apify HKJC/Equibase/Zeturf kazıyıcıları | kazıyıcı hizmetleri | ücretli/hesap | kaynak site şartları | V | ⛔ |
| 6 | Kaggle Big Data Derby 2022 (NYRA) | NYRA 2019 koşu içi GPS izleme, 4 hipodrom | Kaggle (giriş) | yarışma kuralları (yarışma dışı kullanım kısıtlı) | Y (tempo/pozisyon modelleme fikri) | ⏸ + aynada konum yok |
| 7 | Kaggle UK/IRE sonuç setleri (Racing Post kaynaklı türevler) | 1990–2020 İngiltere/İrlanda | Kaggle | kaynak RP şartları kazımayı yasaklar | V | ⛔ türetilmiş kaynak sorunlu |
| 8 | `joenano/rpscrape` | Racing Post kazıyıcısı | GitHub | RP şartlarına aykırı kullanım | — | ⛔ |
| 9 | Equibase (ABD) | sonuç, chart | site | Terms of Use otomatik erişimi yasaklar; ücretli veri | V | ⛔ |
| 10 | Equibase “complimentary dataset” (araştırmacılara 1 yıllık) | ABD | başvuru/hesap | sözleşmeli | V | ⛔ hesap |
| 11 | netkeiba / `nkparser` | JRA sonuçları | site | site şartları otomatik toplamaya kapalı | V | ⛔ |
| 12 | JRA-VAN Data Lab | JRA resmi verisi | ücretli abonelik | ticari | V | ⛔ |
| 13 | Huggy Database (HF, Fransa 1996–2026, 356 bin koşu) | PMU/PMH; jokey, antrenör, kilo, oran | HF (ortamda kapalı) | lisans belirtilmemiş; örnek 1999 Ç1 | V/Ö | ⏸ |
| 14 | `huggydatabase/turf-baseline-bernoulli` (HF model) | Fransız taban modeli | HF | belirsiz | Y | 📘 |
| 15 | HF `infinite-dataset-hub/HorseRacePredictor` | sentetik (LLM üretimi) | HF | — | yok | ⛔ sentetik |
| 16 | PMU “turfinfo” JSON uç noktaları | Fransız program/oran | resmi olmayan API | açık izin yok | V | ⛔ izin belirsiz |
| 17 | data.gouv.fr “L’institution des courses” | kurum/istatistik (koşu düzeyi değil) | portal (ortamda kapalı) | Licence Ouverte | — | ⏸ koşu verisi değil |
| 18 | data.gov.uk equine exports | at ihracat istatistikleri | portal | OGL | — | ⛔ ilgisiz |
| 19 | BHA aylık/yıllık “Racing Data Packs” (PDF) | toplu istatistik (alan büyüklüğü, ödül) | PDF | BHA | Ö (toplu oranlar) | 📘 |
| 20 | Betfair historic data (BASIC ücretsiz katman) | borsa fiyat akışı | Betfair hesabı | Betfair şartları | V (FLB) | ⛔ hesap |
| 21 | `betfair/historic-data-workbook` | Betfair geçmiş verisi işleme örnekleri | GitHub | açık kaynak | Y | 📘 |
| 22 | Betfair Data Scientists (AU) model/oran paylaşımları | Avustralya oranları/derecelendirme | site/GitHub | Betfair şartları | Y | 📘 |
| 23 | `ohenery` R paketi `race_data` | 3 haftalık dünya koşuları (36 bin satır) | CRAN (ortamda kapalı) | paket lisansı; veri “web'den” | Y (Henery modeli örneği) | 📘 |
| 24 | Dryad/Zenodo 10.5061/dryad.qbzkh18m0 (Sharman vd. 2022) | İngiltere/İrlanda safkan hız verisi, anonim, ebeveyn yaşı | Zenodo/Dryad (ortamda kapalı) | **CC0** | Ö (yaş/ebeveyn yaşı etkisi) | ⏸ yasal, ortamda kapalı; at adı anonim → eşleşme yok |
| 25 | Figshare British Eventing yaş/cinsiyet çalışması | binicilik (yarış değil) | Figshare | açık | — | ⛔ ilgisiz |
| 26 | The Racing API | küresel program/sonuç | ücretli | ticari | V | ⛔ |
| 27 | `TamB10/ourhub-racing-api` | kazıma tabanlı API | GitHub | kaynak şartları | V | ⛔ |
| 28 | Racing Australia / Racing NSW koşul kitapları (PDF) | WFA (kg) ve set weights | PDF | kamuya açık kurallar | Ö | ⏸ (sayfa ortamda kapalı; ARCI tablosu kullanıldı) |
| 29 | DRF arşivi (Kentucky Üniv., 1896–) | tarihî ölçek/sonuçlar | site | kamu malı (eski) | Ö (tarihî WFA) | 📘 (eski; ARCI tercih edildi) |

### Ölçekler / kamu metodolojileri

| # | Kaynak | İçerik | Erişim | Lisans | Değer | Karar |
|---|---|---|---|---|---|---|
| 30 | **ARCI-010-020 Section D Table 1** (Scale of Weights for Age) | 2/3/4/5+ yaş × ay × 6 mesafe (lb) | rtip.arizona.edu PDF | kamuya açık model kural metni | **Ö** | ✅ `gl_wfa` |
| 31 | BHA/Avrupa WFA ölçeği (2017 revizyonu) | yarım ay × furlong | BHA (tam tablo yayımlanmış PDF bulunamadı) | BHA | Ö | 📘 (yalnız değişiklik özeti bulundu) |
| 32 | Beyer hız figürü (Beyer 1975, “Picking Winners”) | par zaman + günlük varyant | kitap | — | Y | zaten var (hiz3) |
| 33 | Timeform derecelendirme yöntemi (lb/boy ölçeği) | boy→lb dönüşümü mesafeye göre | yöntem yazıları | — | Y | 📘 (a5_kilo_x_mes v5'te elendi) |
| 34 | Racing Post RPR yöntem notları | handikap reytingi | site | şart: kazıma yok | Y | 📘 |
| 35 | ATR/TPD sektörel “finishing speed %” (Rowlands) | tempo ayarlı figür | site | — | Y | ⏸ aynada sektörel yok |
| 36 | Ragozin/Thoro-Graph “sheets” | kilo+kulvar+zemin ayarlı figür | ücretli | ticari | Y | 📘 |

### Akademik yöntemler

| # | Kaynak | Yöntem | Değer | Karar |
|---|---|---|---|---|
| 37 | Harville 1973 (JASA) | sıra olasılığı p_j/(1−p_i) | Y | zaten var |
| 38 | Henery 1981; **Lo & Bacon-Shone 1994/2008** (discounted Harville) | 2./3. sıra için p^γ, p^δ | Y | zaten var (model.henery_ussu, γ/δ) |
| 39 | Stern 1990 (gamma sıra modelleri) | Harville alternatifi | Y | 📘 |
| 40 | Bolton & Chapman 1986 | çok terimli/patlatılmış logit | Y | zaten var (PATLAT 1, 0.5) |
| 41 | **Benter 1994** | model + piyasa iki aşamalı birleştirme | Y | zaten var (α log p + β log q); ortak tahmin elendi |
| 42 | Hausch, Ziemba & Rubinstein 1981 | ikincil havuz verimliliği | Y | 📘 (bahis yok) |
| 43 | **Shin 1992/1993**; Štrumbelj 2014; `shin` (PyPI, mberk) | içeriden bilgili oyuncu modeliyle marj ayırma | Y | ✅ `gl_piyasa` adayı |
| 44 | **Odds-ratio yöntemi** (Cheung 2015); Clarke, Kovalchik & Ingram 2017 (power) | FLB düzeltmeli marj ayırma | Y | ✅ `gl_piyasa` adayı (power ≡ harman β) |
| 45 | `implied` R paketi (Lunde) | basic/shin/bb/wpo/or/power/additive/jsd | Y | 📘 (yöntem listesi) |
| 46 | `goto_conversion` (PyPI) | FLB'ye duyarlı oran→olasılık | Y | 📘 (Shin/OR ile aynı aile) |
| 47 | Snowberg & Wolfers 2010 (JPE) | FLB = algı hatası | Y | 📘 (gerekçe) |
| 48 | Jullien & Salanié 2000 | FLB fayda modelleri | Y | 📘 |
| 49 | Silverman & Suchard 2013 (JPM) | kırılganlıklı düzenlemeli koşullu logit | Y | 📘 (λ ızgarası zaten var) |
| 50 | Lessmann, Sung & Johnson 2009/2010; Edelman 2007 | SVM/SVR + piyasa iki aşaması | Y | 📘 (GBM katmanı benzer rol) |
| 51 | **Burges 2010 LambdaMART**; LightGBM `lambdarank` | sıralama amaçlı GBM | Y | ✅ `gl_lambdarank` |
| 52 | Sharman vd. 2022 (R. Soc. Open Sci.) | ebeveyn yaşı → hız | Ö | ⏸ aynada ebeveyn yok |
| 53 | Safkan/Arap kalıtım çalışmaları (Ank. Üniv. Vet. Fak. Derg. 2009; Uludağ; AAB 2010/2023) | kalıtım derecesi h²≈0,1–0,3 | Ö | 📘 (pedigri gelirse çekme katsayısı) |
| 54 | Wikipedia “Leading sire in GB&IRE / North America / Japan” | lider aygır listeleri (CC BY-SA) | Ö | ⏸ aynada baba yok |
| 55 | WAHO / Arap stud book'ları; allbreedpedigree, pedigreequery | Arap/safkan pedigri | — | ⛔ üyelik/şart; ⏸ eşleşme yok |

### Ek tarama (27.10.2026: pedigri, sıralama kütüphaneleri, ayna/kazıyıcı türevleri)

| # | Kaynak | İçerik | Erişim | Lisans / şart | Değer | Karar |
|---|---|---|---|---|---|---|
| 56 | **Wikidata** (P22 baba, P25 anne, P31=Q726 “at”, yarış atı alt sınıfları) | ünlü safkan/Arap atların ebeveynleri, SPARQL | query.wikidata.org (ortamda 403) | **CC0** | Ö (aygır önseli) | ⏸ yasal; ama aynada baba adı yok → eşleşecek alan yok |
| 57 | DBpedia (`dbo:sire`, `dbo:dam`, Wikipedia bilgi kutularından) | ünlü atların pedigrisi | dbpedia.org | CC BY-SA 3.0 | Ö | ⏸ aynı neden (eşleşme alanı yok) |
| 58 | WAHO (World Arabian Horse Organization) üye stud book listesi | Arap ırkı kayıt kurumları (TJK dahil) | waho.org | site şartları | Ö (yalnız kurum listesi) | 📘 koşu/pedigri verisi açık değil |
| 59 | `PlackettLuce` R paketi (Turner vd. 2020) | PL sıralama modeli, eşitlik/kısmi sıralama | CRAN (ortamda kapalı) | GPL-3 | Y | 📘 (ozellik.reyting zaten PL) |
| 60 | `hyper2` R paketi, “Generalized Plackett-Luce Likelihoods” (Hankin) | genelleştirilmiş PL, at yarışı örnekleri | CRAN | GPL-2 | Y | 📘 |
| 61 | `choix` (Python, Maystre) | PL/Bradley-Terry çıkarımı (ILSR) | PyPI (ortamda açık) | MIT | Y | 📘 (bağımlılık eklemeye değmez; PL zaten var) |
| 62 | baselight.app Kaggle aynaları (`gdaley_hkracing`, `jeffreymuller_…2013_to_2020`) | HKJC setlerinin SQL aynası | site (hesap) | Kaggle/HKJC şartları | V | ⛔ hesap + türev şartı |
| 63 | Apify netkeiba aktörleri (`jpmarketdata/netkeiba-race-checker`, `datamill/netkeiba-race-scraper`) | JRA program/sonuç kazıyıcı | ücretli/hesap | netkeiba şartları | V | ⛔ |
| 64 | Georgetown öğrenci projesi “Data Gathering” (HK at yarışı) | HKJC veri toplama + modelleme notları | web | belirsiz | Y | 📘 |
| 65 | “Predicting horse racing results with deep learning” (TDS, HK) | HK verisinde sinir ağı + Benter kıyası | web | — | Y | 📘 (GBM katmanı benzer; ayrı ağ gereksiz) |
| 66 | `lightgbm` `lambdarank` / `rank_xendcg` amaçları | LambdaMART uygulaması | PyPI (kurulu) | MIT | Y | ✅ `gl_lambdarank` |

Kaynak bağlantıları (yalnız bilgi; veri indirilmedi): https://www.rdocumentation.org/packages/PlackettLuce ·
https://cran.uni-muenster.de/web/packages/hyper2/vignettes/hyper3.html ·
https://baselight.app/u/kaggle/dataset/gdaley_hkracing ·
https://mail.mattcarswell.georgetown.domains/gathering/gathering.html ·
https://towardsdatascience.com/predicting-horse-racing-results-with-deep-learning-7942846287bf/

### Aygır önseli neden sınanamadı (ölçüldü, 27.10.2026)

Aynanın hem `results/*.json` hem `daily/*.json` at satırları: `no, name, jockey, trainer, weight, age, form, odds,
position, finishTime` — **baba/anne adı hiçbir dosyada yok**. Wikidata/DBpedia'daki aygırlarla eşleştirmenin tek yolu
baba adı olurdu; at adının kendisi Wikidata'da yalnız ünlü (çoğu yabancı) atlarda var. Bu yüzden aygır önseli
deney masasına alınmadı; pedigri alanı yasal bir kaynaktan aynaya eklenirse (Türkiye ekibinin işi) #53/#56 yöntemi hazır:
baba başına küçültmeli kazanma/mesafe eğilimi (h²≈0,1–0,3 → k≈20 sanal koşu önseli).

## Deney sonuçları — v6b tabanına karşı (27.10.2026, `lab/at/deney_global.py`)

Taban: main'deki yayın tarifi (v4 + jk + a5_sinif + v6b `A6_SECILI`: a6_kalman, a6_mesafe, a6_gelisim, a6_ek_st,
a6_ek_idman, a6_ek_hp, a6_hava). 5.453 sınama koşusu, katlar A (2025-11-01 → 2026-03-16, 2.175 koşu) ve B
(2026-03-17 → 2026-10-25, 3.278 koşu); walk-forward aylık eğitim. Kapı: deney4 iki katlı kapı (özellik/amaç adımları);
piyasa yönlü adaylar yalnız harman kapısıyla (sabah kilidi yalnız modeldir, `lab/at/kilit.py`; harman yalnız koşuya
≤ 15 dk kala oran kapısı geçince devreye girer). ΔLL < 0 iyileşme; GA = koşu-bootstrap %95.

| # | deney | kapı | model LL / ilk | ΔLL model [%95 GA] | A / B | ΔLL harman [%95 GA] | sonuç |
|---|---|---|---|---|---|---|---|
| 0 | taban (v6b) | – | 1,8478 / %32,6 | – | – | harman 1,7887 / %35,3 | taban |
| 1 | gl_piyasa (odds-ratio; sınama öncesi dönemde seçildi) | harman | 1,8478 | 0 | – | +0,0024 [+0,0009; +0,0039] (A +0,0013, B +0,0032) | ❌ elendi |
| 2 | gl_flb (harmanda κ (log q)², κ ort. −0,013) | harman | 1,8478 | 0 | – | +0,0001 [−0,0006; +0,0008] | ❌ elendi |
| 3 | gl_wfa (ARCI WFA önseli) | model | 1,8468 / %32,6 | −0,0008 [−0,0020; +0,0004] | −0,0015 / −0,0004 | −0,0005 [−0,0011; +0,0001] | ✅ geçti |
| 4 | gl_lambdarank (LambdaMART, ilk 3) | model | 1,8493 / %32,3 | +0,0023 [+0,0001; +0,0045] | +0,0033 / +0,0017 | +0,0009 | ❌ elendi |
| D | gl_harville denetimi (2.+3. sıra LL, 5.423 koşu) | ayrı | Harville 3,6324 | öğrenilen γ/δ −0,0511 [−0,0602; −0,0418]; LBS sabiti (0,81/0,65) −0,0506 | A −0,0585 / B −0,0462 | – | ✅ yayındaki öğrenilen γ/δ doğrulandı |

- Sızıntı testi (`python lab/at/deney_global.py --sizinti`): 6 rastgele gün; kesme, sonuç/oran karıştırma, ters gün içi
  sıra → hepsi AYNI → **sızıntı yok** (gl_wfa yalnız bugünkü programdaki yaş, kilo, ay, mesafeden).
- Piyasa yöntem seçimi (sınama öncesi dönem, kazanan LL): orantılı 1,8071 < odds-ratio 1,8129 < Shin 1,8221. Türkiye
  havuzunda (pari-mutuel) FLB marj ayırma yöntemleri orantılıdan kötü; harmanın β üssü (power yöntemi) eğriliği zaten alıyor.
- LambdaRank v6'da (m6_rank +0,0006) ve burada (+0,0023) iki kez elendi: koşu-içi softmax amacı olasılık kalibrasyonunda üstün.
- Öğrenilen γ/δ (aylık 0,74–0,92 / 0,60–0,78) Lo–Bacon-Shone Hong Kong değerlerine çok yakın; yayında zaten
  `model.henery_ussu` ile öğreniliyor → değişiklik gerekmedi.
- **GLOBAL_SECILI = ["gl_wfa"]** (`lab/at/global/oncul.json`) → `ozellik.SECILI_GRUPLAR` → gece.py eğitimi, sabah kilidi ve
  gerekçe ifadeleri. Deney süresi 641 sn (2 çekirdek).
- Gece ölçümü (gl_wfa bağlı, 2 çekirdek, ayna yerel): `gece.py` toplam **11 dk 56 sn** (≤ 25 dk); yayın kapısı KABUL
  (yalnız-model LL 1,8526 → 1,8518, ilk seçim %32,35 → %32,39; harman 1,7923 → 1,7918, 5.453 ortak koşu).

## Sorgu listesi (kullanılan)

İngilizce: “Kaggle Hong Kong horse racing dataset HKJC races runs csv”, “github horse racing dataset csv open license
results UK Ireland”, “Hugging Face datasets horse racing”, “Big Data Derby Kaggle NYRA”, “Betfair historical data free
basic BSP csv”, “Lo Bacon-Shone discounted Harville”, “Shin method overround favourite-longshot power method Clarke 2017”,
“weight for age scale BHA table”, “arXiv horse racing deep learning Plackett-Luce”, “github Benter model conditional
logit”, “Wikidata thoroughbred leading sire”, “horse racing results Zenodo OR Figshare”, “Kaggle horse racing Australia”,
“eprochasson github horse racing”, “goto_conversion”, “Benter 1994 pdf”, “Jockey Club scale of weights for age”,
“Australian weight for age scale”, “Equibase terms of use scraping”, “HKJC terms of use”, “Racing Post terms scraping”,
“Sharman Wilson 2022 Dryad CC0”, “thoroughbred heritability sire distance aptitude”, “Silverman Suchard 2013”,
“Lessmann Sung Johnson two-stage”, “Simon Rowlands finishing speed”, “Snowberg Wolfers 2010”, “Štrumbelj 2014 Shin”,
“Betfair Data Scientists hub”, “Big Data Derby license”.
Japonca: “競馬 データセット github JRA 機械学習 オープンデータ”, “keiba 競馬 データ csv LightGBM”, “netkeiba 利用規約
スクレイピング”. Çince: “賽馬 香港 數據 預測”. Fransızca: “data.gouv.fr courses hippiques PMU données ouvertes”,
“courses hippiques prediction données github”. Almanca: “pferderennen daten vorhersage”. İspanyolca/İtalyanca:
“carreras de caballos datos github predicción”, “corse di cavalli dati github”. Ek (27.10): “Kaggle horse racing dataset Australia OR Japan JRA OR Hong Kong csv”,
“github Plackett-Luce horse racing Benter conditional logit python”, “Wikidata thoroughbred racehorse sire property P22 SPARQL”. Türkçe: “Arap atı yarış performansı
kalıtım TJK çalışma”.

## Yasal notlar

- Kullanılan tek dış veri: ARCI-010-020 WFA tablosu (düzenleyici model kural metni, kamuya açık; yalnız 4×12×6 sayı,
  `kuresel.py` içinde atıf ile). Kişisel veri yok.
- Yöntemler (Shin, odds-ratio, LambdaMART, Harville/Henery, Benter) yayımlanmış akademik literatürdür; kod bağımsız
  yazıldı, dış paket kodu kopyalanmadı.
- Racing Post, Equibase, netkeiba, HKJC türevleri ve ücretli API'ler bilerek dışarıda bırakıldı.
- CC0 olan Sharman vd. verisi yasal olarak kullanılabilir; ancak ortamda erişim kapalı ve at kimlikleri anonim olduğundan
  Türkiye aynasıyla eşlenemez — yalnız genel yaş etkisi önseli için aday (gelecek iş).
