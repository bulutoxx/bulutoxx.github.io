# Küresel at yarışı kaynakları — tarama, yasal durum, robota aktarım (26.10.2026)

Kapsam: Türkiye dışı veri setleri, açık veri portalları, akademik yöntemler, pedigri kaynakları ve kamuya açık
hız/handikap/kilo metodolojileri. Türkiye'ye özgü kaynaklar (TJK aynaları, Open-Meteo, aynadaki kullanılmayan alanlar)
ayrı ajanın işidir (at-derin dalı, KAYNAKLAR.md) ve burada tekrarlanmadı.

**Kural özeti:** tjk.org, medya-cdn.tjk.org, vhs*.tjk.org, atyarisi.com (+alt alanlar) ve web.archive.org kopyalarına hiç
istek atılmadı. Kazımayı yasaklayan siteler kazınmadı. Ücretli API, hesap açma, giriş, kişisel veri yok. Ham veri commit
edilmedi; depoda yalnız türetilmiş küçük tablolar (WFA ölçeği, deney metrikleri) var.

**Ortam kısıtı (ölçüldü):** bu oturumun ağ geçidi yalnız GitHub (git clone / raw) ve PyPI'ye izin veriyor;
Kaggle, Hugging Face, Zenodo, Dryad, Figshare, CRAN, data.gouv.fr, storage.googleapis.com bağlantıları 403 ile reddedildi.
GitHub arama API'si de oturuma bağlı depolarla sınırlı. Bu yüzden veri indirmesi gerektiren adaylar “erişim: ortamda
kapalı” olarak işaretlendi; karar sütunu yasal kullanılabilirliği ayrıca gösterir.

## Aynanın sınırı (tüm aktarımı belirleyen gerçek)

`cenkozgur/tjk-data` at satırında yalnız `name, no, jockey, trainer, weight, odds, age, position, finishTime, nonRunner,
form(boş)` var. **Baba/anne/aygır alanı yok, cinsiyet yok, kulvar (start no) yok, koşu içi pozisyon yok.** Sonuç:
aygır/baba önseli (“baba gücü / mesafe eğilimi / pist eğilimi”) aynayla eşlenemez; bağlanabilecek tek köprü at adıdır
ve uluslararası açık pedigri kaynakları (Wikipedia/Wikidata) yalnız ünlü atları içerir — Türkiye'de koşan atların
çok küçük bir bölümü. Pedigri alanı başka bir yasal kaynaktan gelirse, aşağıdaki P-satırları hazır yöntemdir.

## Aday tablosu (55 aday)

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
“carreras de caballos datos github predicción”, “corse di cavalli dati github”. Türkçe: “Arap atı yarış performansı
kalıtım TJK çalışma”.

## Yasal notlar

- Kullanılan tek dış veri: ARCI-010-020 WFA tablosu (düzenleyici model kural metni, kamuya açık; yalnız 4×12×6 sayı,
  `kuresel.py` içinde atıf ile). Kişisel veri yok.
- Yöntemler (Shin, odds-ratio, LambdaMART, Harville/Henery, Benter) yayımlanmış akademik literatürdür; kod bağımsız
  yazıldı, dış paket kodu kopyalanmadı.
- Racing Post, Equibase, netkeiba, HKJC türevleri ve ücretli API'ler bilerek dışarıda bırakıldı.
- CC0 olan Sharman vd. verisi yasal olarak kullanılabilir; ancak ortamda erişim kapalı ve at kimlikleri anonim olduğundan
  Türkiye aynasıyla eşlenemez — yalnız genel yaş etkisi önseli için aday (gelecek iş).
