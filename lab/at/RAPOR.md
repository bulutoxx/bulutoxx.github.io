# BULUTOXX 🐎 At Yarışı Laboratuvarı — Rapor

_Otomatik üretildi: 2026-10-25T13:50:37+00:00 · model sürümü `20261025T1341` · hobi amaçlıdır, garanti değildir · 18+_

## Kısa sonuç (dürüst)

- Yalnız geçmiş verilerle kurulan model **tek başına piyasadan belirgin biçimde zayıf**: sınama log-loss 2.0057 (piyasa 1.8277), ilk seçim isabeti %26.7 (piyasa favorisi %35.4).
- Model + piyasa harmanı log-loss'u 1.8262: piyasaya göre fark **-0.0016 ± 0.0029** (std. hata). Bu fark **gürültü sınırları içinde**; modelin piyasaya kalıcı bir üstünlüğü kanıtlanmadı.
- Harmanın ilk seçim isabeti %34.0, piyasa favorisi %35.4. Yayın modu: **model+piyasa** (kural: harman sınama log-loss'u piyasadan düşükse model+piyasa yayınlanır).
- Harman en yüksek kovada aşırı güvenli: 0.50-1.00 aralığında ortalama tahmin %59.4, gerçek %51.5 (478 at). Piyasa aynı kovada %57.5 / %57.4.
- Piyasa (son koşu öncesi ganyan oranı) bu veride en güçlü bilgi; model şimdilik ancak küçük düzeltmeler yapıyor. Pratikte: koşu öncesi oran varken en güvenilir olasılık piyasanın kendisidir; model yorum/gerekçe katmanı olarak değerli.

## Veri kapsamı

- Kaynak: herkese açık ayna [https://github.com/cenkozgur/tjk-data](https://github.com/cenkozgur/tjk-data) (lisans belirtilmemiş). Ayna durumu: güncellendi. tjk.org'a hiçbir istek atılmaz; ham veri bu depoya kopyalanmaz.
- Sonuçlar: 2025-01-01 → 2026-10-23, **10,895 yerli koşu**, 105,851 koşan at; tam oranlı koşu 10,861. Yabancı (simulcast) koşular ve kazananı belirsiz koşular çıkarıldı ({'yabanci': 3205, 'kazanansiz': 21, 'az_at': 0}).
- Hipodromlar: İstanbul 2069, İzmir 1720, Bursa 1413, Adana 1297, Ankara 1291, Şanlıurfa 802, Antalya 764, Elazığ 688, Kocaeli 572, Diyarbakır 279.
- Zaman sıralı bölüm: ısınma (yalnız geçmiş biriktirme) < 2025-03-01; model eğitimi 2025-03-01→2025-11-30 (5064 koşu); harman/kalibrasyon 2025-12-01→2026-03-15 (1618); **sınama (son %30) 2026-03-16→2026-10-23 (3282 koşu)**.
- Piyasa olasılığı q: **nihai** ganyan oranından (1/oran, marj ayrılmış). Bu, "son koşu öncesi" piyasayı temsil eder; sabah programında oran yoktur. Yani harman ancak koşudan hemen önce kullanılabilir; sabah kilitlenen tahminler yalnız modeldir.
- Kullanılmayanlar: aynanın memory/*.json özetleri (geleceği içerir → sızıntı), gün içi oran görüntüleri (yalnız 57 gün), hava/nem (yalnız 2026-04 sonrası programlarda).

## Sınama metrikleri (son %30, yalnız tam oranlı koşular)

| | log-loss ↓ | Brier ↓ | ilk seçim | ikili (sıralı) | ilk iki → ilk 2 | p≥.30 seçim / isabet (ort. p) | p≥.50 seçim / isabet (ort. p) |
|---|---|---|---|---|---|---|---|
| Model (yalnız geçmiş) | 2.0057 | 0.8366 | %26.7 | %6.9 | %12.5 | 1576 / %33.2 (%40.2) | 224 / %42.0 (%59.0) |
| Piyasa q | 1.8277 | 0.7848 | %35.4 | %11.1 | %18.9 | 2022 / %41.2 (%40.3) | 272 / %57.4 (%57.5) |
| **Model + piyasa** | 1.8262 | 0.786 | %34.0 | %11.0 | %18.9 | 2448 / %39.2 (%42.2) | 478 / %51.5 (%59.4) |
| Favori tabanı | – | – | %35.4 | %11.1 | %18.9 | – | – |
| Düzgün (1/N) | 2.2414 | 0.8873 | – | – | – | – | – |

Eşleştirilmiş log-loss farkı (koşu başına, ± std. hata): harman − piyasa = -0.0016 ± 0.0029; model − piyasa = +0.1780 ± 0.0111.

Parametreler (yayın modeli): harman α = 0.2, β = 0.9231; yalnız-model sıcaklığı T = 1.1044; Henery üsleri γ(2.) = 0.86, δ(3.) = 0.76; L2 λ = 30.0.

### Kalibrasyon (sınama, model + piyasa)

| tahmin aralığı | at | ort. tahmin | gerçek kazanma |
|---|---|---|---|
| 0.00-0.05 | 15412 | %2.3 | %2.5 |
| 0.05-0.10 | 6540 | %7.2 | %8.0 |
| 0.10-0.20 | 5718 | %14.2 | %14.7 |
| 0.20-0.30 | 2496 | %24.4 | %22.9 |
| 0.30-0.50 | 1970 | %38.1 | %36.2 |
| 0.50-1.00 | 478 | %59.4 | %51.5 |

## Neler önemli?

Standartlaştırılmış katsayılar (en büyük 10; + kazanma şansını artırır):

| özellik | katsayı |
|---|---|
| sinif_degisim | -0.359 |
| n_kosu | -0.277 |
| jokey_gal60 | +0.257 |
| geri3 | -0.160 |
| piyasa_son | +0.151 |
| skor_son | +0.149 |
| geri_son | -0.128 |
| piyasa3 | +0.124 |
| yas3 | +0.123 |
| yeni | -0.117 |

Ablasyon — grup çıkarılınca sınama log-loss'u ne kadar kötüleşiyor (+ = grup faydalı):

| çıkarılan grup | yalnız model Δ | model+piyasa Δ |
|---|---|---|
| jokey | +0.0199 | -0.0008 |
| form | +0.0115 | -0.0005 |
| piyasa_gecmisi | +0.0111 | +0.0008 |
| pist_mesafe_hipodrom | +0.0104 | +0.0007 |
| dinlenme | +0.0056 | +0.0002 |
| fark | +0.0043 | +0.0002 |
| kilo | +0.0025 | +0.0005 |
| alan | +0.0009 | +0.0002 |
| antrenor | +0.0006 | +0.0001 |
| sinif | +0.0005 | +0.0008 |
| jokey_at | +0.0002 | -0.0005 |
| yas | -0.0001 | -0.0001 |

Yorum: jokeyin son 60 gün formu, at formu (son koşu sıraları, kazanana uzaklık), geçmiş koşulardaki piyasa ilgisi ve pist/mesafe/hipodrom uyumu modeli tek başına en çok taşıyan bilgiler. Ancak bunların çoğu piyasada zaten fiyatlanmış; harman sütunundaki farklar ±0,001 düzeyinde, yani piyasanın üstüne eklenen bilgi çok az.

## Kapı (sürekli öğrenme)

- Son karar (2026-10-25T13:50:37+00:00): **RED** — log-loss düşmedi (1.8262 → 1.8262); dünkü model korunuyor
- Yeni deneme: log-loss 1.8262, ilk seçim %34.0; kayıtlı model aynı sınamada: log-loss 1.8262, ilk seçim %34.0

## Canlı karne (kilitlenmiş tahminler, sonuç gelince)

- Henüz puanlanmış kilitli tahmin yok (sonuçlar aynaya düştükçe her gece puanlanır).

## Gösteri: 2026-10-25 İstanbul tahminleri

Kilit zamanı 2026-10-25 16:41 TSİ. Mod: yalnız model (piyasa oranı henüz yok). (Oran olmadığında bunlar **yalnız model** olasılıklarıdır; sınamada yalnız model piyasa favorisinden zayıftı — bilgi amaçlıdır.) `*` = kilit koşu saatinden sonra atıldı (sızıntısız ama canlı karneye sayılmaz).

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

2100 m Sentetik, Kısa Vade Handikap 24 /H1, saat 16:00. Mod: yalnız model (piyasa oranı henüz yok). Kilit: 2026-10-25 16:41 TSİ.

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

## Denenmiş ama kapıdan geçmemiş fikirler (25.10.2026 ölçümü)

- Benter'in ortak tahmini (log q'yu modelin içine sabit girdi olarak koyup birlikte eğitmek): harman diliminde piyasayı ≈0,009 log-loss iyileştirdi, fakat sınamada fark +0,0002 ± 0,003 (iyileşme yok) → dönem kayması işareti. Yayına alınmadı.
- Uzun-atış yanlılığı düzeltmesi (log q'ya ikinci derece terim): sınamada etkisiz (±0,001).

## Sınırlamalar ve riskler

- Veri yalnız 2025-01-01'den başlıyor: atların daha eski kariyerleri görünmüyor (ilk aylarda özellikler zayıf, ısınma ile kısmen çözüldü).
- Ayna lisanssız ve tek kişinin bakımında; kesilirse sistem son kopyayla çalışır, yeni sonuç gelmez.
- At adları kimlik olarak kullanılıyor (aynı adlı iki at nadir ama mümkün). Ekürili atlarda ganyan oranı ortaktır.
- Kapı tek sınama dilimine bakıyor; günlük gürültüyle sık red beklenir (koruyucu tasarım).
- Sabah kilitleri yalnız model olasılığıdır; piyasa harmanı için koşu öncesi oran gerekir (ayna gün içi oranları düzenli yayınlamıyor).

## Sonraki deneyler

1. Koşu öncesi anlık oran (gün içi görüntüler düzenli gelirse) ile oran hareketi özelliği ve sabah→koşu öncesi harman.
2. Hız puanı: hipodrom/pist/mesafe standart derecesine göre normalize derece (beaten-time yerine), pist durumu düzeltmeli.
3. Genişleyen pencerede (walk-forward, aylık yeniden eğitim) harman α/β'nın kararlılığı; dönem kayması için zaman ağırlıklı eğitim.
4. Programdaki form dizilerinden (2025 öncesi koşular) eski kariyer bilgisini çıkarmak; pedigri/idman verisi açık kaynakta bulunursa.

## Zamanlama

`.github/workflows/at-lab.yml` her gece 02:23 UTC (05:23 TSİ) için ayarlı; **ancak GitHub zamanlanmış iş akışlarını yalnız varsayılan daldan (main) çalıştırır**. Laboratuvar main dalındadır; iş akışı her gün 05:23 ve 12:23 TSİ'de, ayrıca `lab/at/**` değişince veya elle çalışır. Çıktılar yalnız `data/at/` ve `lab/at/RAPOR.md`'ye yazılır.

_Kaynak atfı: TJK verilerinin herkese açık aynası https://github.com/cenkozgur/tjk-data. Model ve olasılıklar BULUTOXX laboratuvarınındır._
