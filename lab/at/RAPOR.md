# BULUTOXX 🐎 At Yarışı Laboratuvarı — Rapor

_Otomatik üretildi: 2026-10-25T15:09:00+00:00 · model sürümü `20261025T1503` · hobi amaçlıdır, garanti değildir · 18+_

## Özet: v2 güncellemesi (25.10.2026)

Uygulamadaki **sabah tahminleri yalnız modeldir** (sabah programında ganyan oranı yok). Bu yüzden bu turda hedef, oransız (yalnız geçmişe dayalı) tahmini güçlendirmekti. Yapılanlar:

- **Yalnız model (sabah) sınama log-loss'u 2.0057 → 1.9348; ilk seçim isabeti %26.7 → %29.4** (aynı 3,282 sınama koşusu). Piyasa favorisi hâlâ önde: %35.4, piyasa log-loss 1.8277.
- Model + piyasa harmanı: log-loss 1.8262 → 1.8180 (piyasaya göre -0.0098 ± 0.0030; anlamlı iyileşme).
- Yeni bilgiler: atın **geçmiş koşulardaki piyasa değerlendirmesi** (oran hafızası: üstel ortalama, piyasa sırası, yenilen favori, piyasanın beklediğinden iyi/kötü koşma, rakiplere göre aktarılan "piyasa reytingi"), her koşudan sonra güncellenen **Plackett-Luce reytingleri** (at + jokey + antrenör), **sayısal sınıf** (koşu türü, alanın reyting düzeyi, handikapta kilo), **zaman sönümlü form**.
- Eğitim: sınamada her ay **yalnız o aydan önceki veriyle yeniden eğitim** (walk-forward; gece akışı da her gün böyle eğitir), eski koşulara daha az ağırlık (yarı ömür 180 gün), ve doğrusal modelin yanına **LightGBM** (koşu içi softmax amacıyla) eklendi; ikisinin karışımı, sıcaklık ve %25 üstü olasılıklar için ayrı bir "üst uç" eğimi son 90 günde kalibre edilir.
- Kapı artık **yalnız-model** ölçülerine bakıyor (sabah ekranı bunu gösteriyor), harman da kötüleşmemeli; tarif değişince eski ve yeni tahminler aynı sınama koşularında kıyaslanıyor (bkz. Kapı).
- Elenenler: hız puanı, jokey/antrenör piyasa ilgisi + ekuri (log-loss'u çok az düşürdü ama ilk seçim isabetini düşürdü); sabah programındaki form dizisi (yalnız 2026-04 sonrasında var, eğitim geçmişi yetersiz).
- Dürüst sonuç: model tek başına **hâlâ piyasa favorisinin gerisinde**. Sabah tahminleri bilgi amaçlıdır; koşu öncesi oran geldiğinde en güvenilir olasılık piyasa (ve harman) olur.

## Kısa sonuç (dürüst)

- Yalnız geçmiş verilerle kurulan model (sabah tahmini) **tek başına piyasadan zayıf**: sınama log-loss 1.9348 (piyasa 1.8277), ilk seçim isabeti %29.4 (piyasa favorisi %35.4). Fark model − piyasa = +0.1071 ± 0.0098.
- Model + piyasa harmanı log-loss'u 1.818: piyasaya göre fark **-0.0098 ± 0.0030** (std. hata). Bu fark istatistiksel olarak anlamlı bir iyileşme (2 std. hatadan büyük).
- Harmanın ilk seçim isabeti %34.4, piyasa favorisi %35.4. Yayın modu: **model+piyasa** (kural: harman sınama log-loss'u piyasadan düşükse model+piyasa yayınlanır).
- Kalibrasyon, en yüksek kova: yalnız model 0.50-1.00 aralığında ortalama tahmin %58.2, gerçek %48.6 (140 at); harman %58.3 / %53.3 (396 at). Yani %50+ verilen atlarda model hâlâ biraz iyimser; bu atlar gerçekte yaklaşık yarı yarıya kazanıyor.

## Veri kapsamı

- Kaynak: herkese açık ayna [https://github.com/cenkozgur/tjk-data](https://github.com/cenkozgur/tjk-data) (lisans belirtilmemiş). Ayna durumu: güncellendi. tjk.org'a hiçbir istek atılmaz; ham veri bu depoya kopyalanmaz.
- Sonuçlar: 2025-01-01 → 2026-10-23, **10,895 yerli koşu**, 105,851 koşan at; tam oranlı koşu 10,861. Yabancı (simulcast) koşular ve kazananı belirsiz koşular çıkarıldı ({'yabanci': 3205, 'kazanansiz': 21, 'az_at': 0}).
- Hipodromlar: İstanbul 2069, İzmir 1720, Bursa 1413, Adana 1297, Ankara 1291, Şanlıurfa 802, Antalya 764, Elazığ 688, Kocaeli 572, Diyarbakır 279.
- Zaman sıralı ölçüm: ısınma (yalnız geçmiş biriktirme) < 2025-03-01; **sınama (son %30) 2026-03-16→2026-10-23 (3282 tam oranlı koşu)**. aylık walk-forward: sınamanın her ayı için yalnız o aydan önceki verilerle yeniden eğitim; kalibrasyon ayın hemen öncesindeki 90 günde; zaman ağırlığı yarı ömrü 180 gün.
- Piyasa olasılığı q: **nihai** ganyan oranından (1/oran, marj ayrılmış). Bu, "son koşu öncesi" piyasayı temsil eder; sabah programında oran yoktur. Yani harman ancak koşudan hemen önce kullanılabilir; sabah kilitlenen tahminler yalnız modeldir. Geçmiş koşuların oranları ise (o koşular bittiği için) sabah da bilinir ve modelde "piyasa hafızası" olarak kullanılır.
- Kullanılmayanlar: aynanın memory/*.json özetleri (geleceği içerir → sızıntı), gün içi oran görüntüleri (yalnız 57 gün), hava/nem ve form dizileri (yalnız 2026-04 sonrası programlarda).

## Sınama metrikleri (son %30, yalnız tam oranlı koşular)

| | log-loss ↓ | Brier ↓ | ilk seçim | ikili (sıralı) | ilk iki → ilk 2 | p≥.30 seçim / isabet (ort. p) | p≥.50 seçim / isabet (ort. p) |
|---|---|---|---|---|---|---|---|
| **Yalnız model (sabah)** | 1.9348 | 0.8194 | %29.4 | %8.3 | %14.7 | 1587 / %36.5 (%38.2) | 140 / %48.6 (%58.2) |
| Piyasa q | 1.8277 | 0.7848 | %35.4 | %11.1 | %18.9 | 2022 / %41.2 (%40.3) | 272 / %57.4 (%57.5) |
| **Model + piyasa** | 1.818 | 0.7836 | %34.4 | %10.9 | %18.9 | 2327 / %39.2 (%41.3) | 396 / %53.3 (%58.3) |
| Favori tabanı | – | – | %35.4 | %11.1 | %18.9 | – | – |
| Düzgün (1/N) | 2.2414 | 0.8873 | – | – | – | – | – |

Eşleştirilmiş log-loss farkı (koşu başına, ± std. hata): harman − piyasa = -0.0098 ± 0.0030; model − piyasa = +0.1071 ± 0.0098.

Parametreler (yayın modeli): birleşik puan = 0.37852 × doğrusal + 0.58709 × GBM (GBM açık); harman α = 0.2963, β = 0.8618; Henery üsleri γ(2.) = 0.84, δ(3.) = 0.74; L2 λ = 300.0. LightGBM kurulu değilse model doğrusal yedeğe (kendi kalibrasyonuyla) düşer.

### Kalibrasyon (sınama, yalnız model (sabah tahmini))

| tahmin aralığı | at | ort. tahmin | gerçek kazanma |
|---|---|---|---|
| 0.00-0.05 | 12655 | %2.5 | %2.6 |
| 0.05-0.10 | 8019 | %7.3 | %8.0 |
| 0.10-0.20 | 7349 | %14.1 | %14.2 |
| 0.20-0.30 | 3004 | %24.4 | %22.9 |
| 0.30-0.50 | 1447 | %36.3 | %35.4 |
| 0.50-1.00 | 140 | %58.2 | %48.6 |

### Kalibrasyon (sınama, model + piyasa)

| tahmin aralığı | at | ort. tahmin | gerçek kazanma |
|---|---|---|---|
| 0.00-0.05 | 14893 | %2.4 | %2.4 |
| 0.05-0.10 | 6808 | %7.2 | %7.6 |
| 0.10-0.20 | 6027 | %14.2 | %14.7 |
| 0.20-0.30 | 2559 | %24.3 | %23.9 |
| 0.30-0.50 | 1931 | %37.8 | %36.4 |
| 0.50-1.00 | 396 | %58.3 | %53.3 |

## Deneyler (25.10.2026, yalnız model odaklı)

Hepsi aynı sınama diliminde (son %30, aynı koşular). Kapı: yalnız-model log-loss düşmeli **ve** yalnız-model ilk seçim isabeti düşmemeli; geçen adım bir sonrakinin tabanı olur.

| # | deney | sonuç | yalnız model: log-loss / Brier / ilk seçim / ilk iki | yalnız model p≥.30 · p≥.50 (seçim, isabet) | harman: log-loss / ilk seçim |
|---|---|---|---|---|---|
| 0 | v1 (yayındaki model): tek eğitim, sabit bölüm | taban | 2.0057 / 0.8366 / %26.7 / %12.5 | 1576, %33.2 · 224, %42.0 | 1.8262 / %34.0 |
| 1 | aylık walk-forward yeniden eğitim (v1 özellikleri) | ✅ kaldı | 1.9879 / 0.8312 / %27.2 / %12.7 | 1374, %34.8 · 161, %47.8 | 1.8234 / %34.1 |
| 2 | 1: piyasa hafızası (EWMA, piyasa sırası, yenilen favori, piyasa reytingi) | ✅ kaldı | 1.9781 / 0.8286 / %27.5 / %13.4 | 1460, %34.9 · 181, %46.4 | 1.8231 / %34.1 |
| 3 | 2a: Plackett-Luce at/jokey/antrenör reytingi | ✅ kaldı | 1.9639 / 0.8262 / %28.1 / %14.0 | 1548, %35.3 · 205, %47.3 | 1.8222 / %33.9 |
| 4 | 2b: sayısal sınıf (tür, alanın reyting düzeyi, handikap kilosu) | ✅ kaldı | 1.9630 / 0.8256 / %28.7 / %14.2 | 1547, %35.0 · 211, %46.5 | 1.8221 / %34.0 |
| 5 | 3: hız puanı (standart derece + gün/pist değişkeni) | ❌ elendi | 1.9603 / 0.8251 / %28.5 / %14.1 | 1574, %35.3 · 211, %50.2 | 1.8216 / %33.8 |
| 6 | 4: zaman sönümlü form ve kazanana uzaklık | ✅ kaldı | 1.9588 / 0.8247 / %28.8 / %14.3 | 1580, %35.0 · 204, %49.0 | 1.8216 / %34.1 |
| 7 | ek: jokey/antrenör binişlerine piyasa ilgisi, jokey yükseltmesi, ekuri | ❌ elendi | 1.9585 / 0.8246 / %28.7 / %14.3 | 1581, %35.0 · 207, %49.8 | 1.8216 / %34.0 |
| 8 | 6a: zaman ağırlıklı eğitim (yarı ömür 180 gün) | ✅ kaldı | 1.9549 / 0.8238 / %29.3 / %14.8 | 1610, %35.0 · 214, %46.7 | 1.8215 / %34.3 |
| 9 | 6b: LightGBM (koşu içi softmax amacı) + doğrusal birleşim; 15 yaprak, en az 200 at/yaprak | ❌ elendi | 1.9362 / 0.8200 / %29.1 / %15.0 | 1627, %36.9 · 216, %45.8 | 1.8185 / %34.4 |
| 10 | 6c: aynı, daha düzenli ağaçlar: 7 yaprak, en az 500 at/yaprak | ✅ kaldı | 1.9360 / 0.8200 / %29.4 / %14.7 | 1603, %36.6 · 200, %44.5 | 1.8184 / %34.3 |
| 11 | 7: üst uç kalibrasyonu (p > 0.25 bölgesine ayrı eğim, kalibrasyon penceresinde) | ✅ kaldı | 1.9348 / 0.8194 / %29.4 / %14.7 | 1587, %36.5 · 140, %48.6 | 1.8180 / %34.4 |

Piyasa (aynı koşular): log-loss 1.8277, favori ilk seçim %35.4. Deney kaydı: `data/at/deneyler.json` (2026-10-25T17:54:45).

Ölçülen ama tabloya girmeyenler:

- **Deney 5 — sabah programındaki form dizisi** (ör. "621-141", 2025 öncesi kariyeri de içerir): yalnız 2026-04'ten beri var. Sınamanın Nisan–Haziran kısmında öğrenilip Temmuz–Ekim'de (1.377 koşu) denendiğinde yalnız-model log-loss'u ≈0,004 düşürdü; etkinin çoğu "form dizisi boş = gerçekten ilk koşu" bayrağından. Eğitim geçmişinde bu bilgi olmadığı için yayına alınmadı; program arşivi uzadıkça yeniden denenecek.
- **Reyting ayarları** (öğrenme hızı, kaç bitiş sırası kullanılacağı, piyasa reytingi hızı, sönüm): değişiklikler ±0,002–0,008 log-loss oynattı ama ilk seçim isabetini düşürdü; varsayılanlar korundu (aşırı ayar = sınamaya uydurma riski).
- **GBM ayarı**: ilk denenen ayar (15 yaprak) log-loss'u en çok düşürdü ama ilk seçim isabeti 0,18 puan (6 koşu) düştüğü için kurala göre elendi; ikinci ve son denenen daha düzenli ayar (7 yaprak, en az 500 at) kapıdan geçti. İki deneme yapıldığı açıkça kayıtlı.
- **Deney 7 — kalibrasyon**: sıcaklık doğrusal+GBM karışımıyla birlikte son 90 günde öğreniliyor; üstüne %25 üstü bölge için ayrı eğim eklendi (kapıdan geçti, %50+ seçim sayısını azalttı). Tekdüze dağılımla karıştırma log-loss'u iyileştirmedi. Buna rağmen %50+ kovasında ≈10 puanlık iyimserlik sürüyor (az örnek: ≈140 at) ve raporda açıkça gösteriliyor.
- **Kalibrasyon penceresi 150 gün** (90 yerine) ve **λ = 100**: ikisi de kötüleştirdi.

## Neler önemli?

Doğrusal katmanın standartlaştırılmış katsayıları (en büyük 12; + kazanma şansını artırır; GBM katmanı ayrıca etkileşimleri yakalar):

| özellik | katsayı |
|---|---|
| r_jokey | +0.282 |
| piyasa_reyting | +0.199 |
| geri_en_iyi5 | -0.176 |
| n_kosu | -0.159 |
| sinif_degisim | -0.132 |
| hipodrom_uyum | +0.118 |
| geri_son | -0.116 |
| sinif_r_degisim | -0.116 |
| skor_son | +0.114 |
| pist_uyum | +0.087 |
| uzun_ara | -0.078 |
| r_antrenor | +0.076 |

Ablasyon — grup çıkarılınca sınama log-loss'u ne kadar kötüleşiyor (+ = grup faydalı; yalnız doğrusal katmanla, aylık walk-forward):

| çıkarılan grup | yalnız model Δ | model+piyasa Δ |
|---|---|---|
| reyting | +0.0136 | +0.0006 |
| pist_mesafe_hipodrom | +0.0113 | +0.0011 |
| piyasa_hafiza | +0.0059 | +0.0003 |
| dinlenme | +0.0050 | +0.0004 |
| form | +0.0038 | -0.0002 |
| fark2 | +0.0023 | +0.0003 |
| kilo | +0.0008 | +0.0002 |
| jokey_at | +0.0006 | -0.0003 |
| piyasa_gecmisi | +0.0006 | +0.0001 |
| fark | +0.0005 | +0.0001 |
| alan | +0.0003 | +0.0001 |
| sinif2 | +0.0002 | +0.0001 |
| antrenor | +0.0001 | +0.0001 |
| sinif | +0.0000 | +0.0002 |
| yas | -0.0004 | -0.0002 |
| jokey | -0.0011 | -0.0001 |

Yorum: sabah tahmininde en çok taşıyan bilgiler reytingler (at/jokey/antrenör), pist/mesafe/hipodrom uyumu, atın geçmişte piyasada nasıl değerlendirildiği (piyasa hafızası) ve dinlenme. Jokeyin son 60 gün oranı artık jokey reytingiyle örtüştüğü için tek başına katkısı kalmadı. Grupların çoğu birbiriyle örtüştüğünden tek grup çıkarmak az fark yaratır; harmana katkıları ±0,001 düzeyinde.

## Kapı (sürekli öğrenme)

- Kural: tarif (özellikler/ayarlar) değişirse yeni model ancak **aynı sınama koşularında** yalnız-model log-loss'u düşürür, ilk seçim isabetini düşürmez ve harman log-loss'unu 0,001'den fazla bozmazsa kabul edilir. Tarif aynıysa özellikler her gece yeni sonuçlarla güncellenir, katsayılar haftada bir yeniden eğitilir (KORU = bu gece yenileme günü değil); ortak koşularda belirgin bozulma (veri sorunu) olursa dünkü model korunur. İz: `data/at/sinama_izi.json`.
- Son karar (2026-10-25T15:09:00+00:00): **KORU** — aynı tarif; katsayılar 0 günlük (haftalık yenileme), özellikler bu gece yeni sonuçlarla güncellendi
- Yeni: yalnız model log-loss 1.9348, ilk seçim %29.4; harman 1.8180. Kıyas: yalnız model 1.9348, ilk seçim %29.4; harman 1.8180.

## Canlı karne (kilitlenmiş tahminler, sonuç gelince)

- Henüz puanlanmış kilitli tahmin yok (sonuçlar aynaya düştükçe her gece puanlanır).

## Gösteri: 2026-10-25 İstanbul tahminleri

Kilit zamanı 2026-10-25 16:41 TSİ, model sürümü `20261025T1341` (kilitler ezilmez; bu günün kilidi önceki modelle atılmış olabilir). Mod: yalnız model (piyasa oranı henüz yok). `*` = kilit koşu saatinden sonra atıldı (sızıntısız ama canlı karneye sayılmaz).

| koşu | saat | mesafe/pist | ilk 3 (kazanma olasılığı) | ikili önerisi |
|---|---|---|---|---|
| 1* | 14:00 | 1400 Çim | 8 ZERYA (%18.2), 5 LA CORDIALE (%17.0), 7 STORM OF SARYA (%16.9) | 8-5 (%3.6) |
| 2* | 14:30 | 2200 Çim | 2 SUPERSONIC BOOM (%28.0), 3 KING OF THE WIN (%26.5), 1 BLACKFYRE (%20.2) | 2-3 (%9.5) |
| 3* | 15:00 | 1400 Çim | 1 BATTLE QUEEN (%15.3), 2 CRAFTY WARRIOR (%15.1), 4 LİNARAL (%15.0) | 1-2 (%2.6) |
| 4* | 15:30 | 1600 Çim | 1 BOLU RAZ (%35.1), 2 TANKIZI (%28.0), 6 NADİYEKINALI (%13.1) | 1-2 (%13.5) |
| 5* | 16:00 | 2100 Sentetik | 4 MODERN WARRIOR (%36.2), 2 JOHN ABRUZZI (%18.8), 6 CALVADOS (%13.9) | 4-2 (%10.0) |
| 6* | 16:30 | 1600 Çim | 3 HAROLDCOOPER (%23.9), 10 BELLEZA (%11.1), 1 ANTIGONIA (%10.0) | 3-10 (%3.3) |
| 7 | 17:00 | 1600 Çim | 5 LOCO SUGAR (IRE) (%63.0), 2 GRAY DREAM (%13.7), 4 JAEHAERA (%8.2) | 5-2 (%21.7) |
| 8 | 17:30 | 1600 Çim | 2 JOYFUL FOREVER (%30.9), 1 TOUCH OF THUNDER (%27.9), 5 GIRALAMO (%15.1) | 2-1 (%11.5) |
| 9 | 18:00 | 1400 Çim | 8 BİÇERGİLLER (%15.6), 7 GÜRCEYHUN (%13.2), 2 ERDEK (%12.9) | 8-7 (%2.3) |

### İzlenen koşu: 2026-10-25 İstanbul 5. koşu

2100 m Sentetik, Kısa Vade Handikap 24 /H1, saat 16:00. Mod: yalnız model (piyasa oranı henüz yok). Kilit: 2026-10-25 16:41 TSİ (model `20261025T1341`).

> Not: bu kilit koşu saatinden **sonra** atıldı. Sonuç aynada yokken ve yalnız önceki günlerin verisiyle üretildi (sızıntısız), ama dürüstlük gereği canlı karneye sayılmaz; yalnız gösterim amaçlıdır.

| no | at | kazanma | ilk 2 | ilk 3 | gerekçe |
|---|---|---|---|---|---|
| 4 | MODERN WARRIOR | %36.2 | %60.3 | %76.6 | son koşusunda piyasa onu öne çıkarmıştı; jokeyi son 60 günde formda · dikkat: sınıf yükseliyor (daha zor koşu) |
| 2 | JOHN ABRUZZI | %18.8 | %38.2 | %56.2 | sınıf düşüyor (daha kolay koşu); jokeyi son 60 günde formda · dikkat: bu hipodromda zayıf |
| 6 | CALVADOS | %13.9 | %29.9 | %46.7 | sınıf düşüyor (daha kolay koşu); yaşı lehine · dikkat: jokeyinin son 60 günü zayıf |
| 1 | RIDE THE LIGHTNING | %11.3 | %25.0 | %40.4 | sınıf düşüyor (daha kolay koşu); bu hipodromda başarılı · dikkat: jokeyinin son 60 günü zayıf |
| 5 | PITFALL | %10.3 | %23.2 | %37.9 | jokeyi son 60 günde formda; az koşmuş, gelişime açık · dikkat: sınıf yükseliyor (daha zor koşu) |
| 3 | DRAGON KINGDOM | %4.8 | %11.8 | %21.3 | sınıf düşüyor (daha kolay koşu) · dikkat: çok koşmuş |
| 7 | BİKATİ | %4.7 | %11.6 | %20.9 | bu hipodromda başarılı; yaşı lehine · dikkat: sınıf yükseliyor (daha zor koşu) |

**Sonuç:** henüz aynada yok (son sonuç günü 2026-10-23); sonuç gelince gece robotu otomatik puanlayacak.

## Daha önce denenmiş ama kapıdan geçmemiş fikirler

- Benter'in ortak tahmini (log q'yu modelin içine sabit girdi olarak koyup birlikte eğitmek): harman diliminde piyasayı ≈0,009 log-loss iyileştirdi, fakat sınamada fark +0,0002 ± 0,003 (iyileşme yok) → dönem kayması işareti. Yayına alınmadı.
- Uzun-atış yanlılığı düzeltmesi (log q'ya ikinci derece terim): sınamada etkisiz (±0,001).

## Sınırlamalar ve riskler

- Veri yalnız 2025-01-01'den başlıyor: atların daha eski kariyerleri görünmüyor (ilk aylarda özellikler zayıf, ısınma ile kısmen çözüldü).
- Ayna lisanssız ve tek kişinin bakımında; kesilirse sistem son kopyayla çalışır, yeni sonuç gelmez.
- At adları kimlik olarak kullanılıyor (aynı adlı iki at nadir ama mümkün). Ekürili atlarda ganyan oranı ortaktır.
- Sınama tek bir zaman dilimi (≈7 ay); deneylerdeki 0,001–0,003'lük farklar gürültü düzeyinde, büyük kazançlar (walk-forward, piyasa hafızası, reyting, GBM) ise tutarlı. İlk seçim isabetinin standart hatası ≈ ±0,8 puan.
- GBM katmanı `lightgbm` paketine dayanır (iş akışı kurar). Kurulamazsa model doğrusal yedeğe düşer; gerekçeler yalnız doğrusal katmandan üretilir.
- Sabah kilitleri yalnız model olasılığıdır; piyasa harmanı için koşu öncesi oran gerekir (ayna gün içi oranları düzenli yayınlamıyor).
- Uygulamadaki üst özet kutusu `degerlendirme.metrik.harman` isabetini gösteriyor; sabah tahmininin kendi isabeti (yalnız model) daha düşüktür.

## Sonraki deneyler

1. Program arşivi uzadıkça form dizisi (2025 öncesi kariyer, gerçek ilk koşu bayrağı) — şimdiden +0,004 işareti var.
2. Koşu öncesi anlık oran (gün içi görüntüler düzenli gelirse) ile oran hareketi ve sabah→koşu öncesi harman.
3. Üst kovadaki iyimserlik için izotonik/parçalı kalibrasyon (yeterli örnek birikince).
4. Hız puanını kilo ve pist durumuyla düzeltip yeniden denemek; pedigri/idman verisi açık kaynakta bulunursa.

## Zamanlama

`.github/workflows/at-lab.yml` her gün 05:23 ve 12:23 TSİ'de, ayrıca `lab/at/**` değişince veya elle çalışır (main dalı). Çıktılar yalnız `data/at/` ve `lab/at/RAPOR.md`'ye yazılır. Gece akışı ≈3–5 dakika sürer.

_Kaynak atfı: TJK verilerinin herkese açık aynası https://github.com/cenkozgur/tjk-data. Model ve olasılıklar BULUTOXX laboratuvarınındır._
