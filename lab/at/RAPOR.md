# BULUTOXX 🐎 At Yarışı Laboratuvarı — Rapor

_Otomatik üretildi: 2026-10-26T14:39:15+00:00 · model sürümü `20261026T1431` · hobi amaçlıdır, garanti değildir · 18+_

## Yeniden oynatma (replay): 2026-03-16 → 2026-10-23

Geçmiş koşular hiç oynanmamış gibi yeniden yarıştırıldı: 195 yarış günü, 3,284 koşu (3,282 tam oranlı). Her gün için tahmin, yayındaki sistemin o sabah üreteceği gibi: katsayılar 7 günde bir yalnız o günden önceki sonuçlarla yeniden eğitildi (31 yenileme), özellikler o günden önceki sonuçlarla. **sabah** = yalnız model (oransız), **oran** = model + nihai ganyan oranı harmanı, **favori** = yalnız nihai oran. Süre: 99 dk 41 sn (yerel, 2 çekirdek). `lab/at/replay.py`, çıktı `data/at/replay.json`; at bazında olasılıklar `data/at/replay_kosular.json`.

| senaryo | koşu | ilk seçim kazandı | ilk seçim ilk 3'te | ikili sıralı | ikili sırasız | log-loss |
|---|---|---|---|---|---|---|
| sabah | 3,284 | %30.4 | %64.4 | %9.5 | %16.0 | 1.9100 |
| oran | 3,282 | %34.4 | %69.1 | %10.7 | %19.0 | 1.8137 |
| favori | 3,282 | %35.4 | %70.1 | %11.1 | %18.9 | 1.8277 |

- sabah − piyasa (ortak 3,282 koşu): log-loss +0.0821 [+0.0634, +0.1002], ilk seçim -5.0 puan [-0.0664, -0.0338].
- oran − piyasa (ortak 3,282 koşu): log-loss -0.0141 [-0.0206, -0.0076], ilk seçim -1.0 puan [-0.0195, -0.0012].

| hipodrom | koşu | sabah ilk | oran ilk | favori ilk | sabah LL | sabah − piyasa LL [%95 GA] |
|---|---|---|---|---|---|---|
| İstanbul | 684 | %30.3 | %32.9 | %32.6 | 1.9136 | +0.0735 [+0.0331, +0.1133] |
| Ankara | 520 | %32.5 | %36.0 | %38.5 | 1.8413 | +0.1235 [+0.0786, +0.1685] |
| Bursa | 496 | %30.0 | %33.7 | %35.3 | 1.9169 | +0.0367 [-0.0118, +0.0845] |
| İzmir | 423 | %36.9 | %40.0 | %38.8 | 1.7964 | +0.1029 [+0.0484, +0.1558] |
| Kocaeli | 282 | %28.4 | %30.1 | %28.7 | 1.923 | +0.0619 [+0.0009, +0.1260] |
| Elazığ | 278 | %25.9 | %33.5 | %33.8 | 2.1025 | +0.0967 [+0.0282, +0.1645] |
| Adana | 248 | %32.3 | %40.7 | %45.2 | 1.8274 | +0.0948 [+0.0282, +0.1648] |
| Şanlıurfa | 156 | %26.3 | %28.8 | %32.7 | 2.1156 | +0.0653 [-0.0212, +0.1552] |
| Antalya | 99 | %25.2 | %36.4 | %37.4 | 1.8195 | +0.1708 [+0.0567, +0.2848] |
| Diyarbakır | 98 | %18.4 | %20.6 | %25.8 | 2.0947 | -0.0169 [-0.1498, +0.1170] |

| pist | koşu | sabah ilk | oran ilk | favori ilk | sabah LL | sabah − piyasa LL [%95 GA] |
|---|---|---|---|---|---|---|
| Kum | 1867 | %30.4 | %34.0 | %35.3 | 1.9119 | +0.0946 [+0.0689, +0.1211] |
| Çim | 962 | %30.7 | %34.8 | %35.6 | 1.9153 | +0.0528 [+0.0180, +0.0893] |
| Sentetik | 455 | %29.7 | %34.9 | %35.4 | 1.8908 | +0.0927 [+0.0426, +0.1428] |

| alan (koşan at) | koşu | sabah ilk | oran ilk | favori ilk | sabah LL | sabah − piyasa LL [%95 GA] |
|---|---|---|---|---|---|---|
| 7-9 | 1171 | %32.9 | %37.1 | %37.6 | 1.7877 | +0.0944 [+0.0632, +0.1246] |
| 10-12 | 945 | %27.4 | %31.9 | %32.6 | 2.0262 | +0.0815 [+0.0430, +0.1188] |
| 13+ | 711 | %23.5 | %27.3 | %28.3 | 2.2626 | +0.0576 [+0.0146, +0.0995] |
| 2-6 | 457 | %40.7 | %43.5 | %46.6 | 1.4347 | +0.0898 [+0.0424, +0.1374] |

| sınıf türü | koşu | sabah ilk | oran ilk | favori ilk | sabah LL | sabah − piyasa LL [%95 GA] |
|---|---|---|---|---|---|---|
| şartlı | 1134 | %32.5 | %36.0 | %36.2 | 1.844 | +0.0993 [+0.0642, +0.1321] |
| handikap | 968 | %26.1 | %30.4 | %32.1 | 2.0478 | +0.0751 [+0.0434, +0.1095] |
| maiden | 661 | %29.6 | %33.9 | %35.1 | 1.9213 | +0.0478 [+0.0082, +0.0898] |
| kısa vade | 353 | %36.0 | %41.4 | %42.8 | 1.7143 | +0.0949 [+0.0355, +0.1527] |
| satış | 86 | %26.7 | %31.4 | %32.6 | 1.9306 | +0.0512 [-0.0672, +0.1638] |
| grup/kv-g | 81 | %35.8 | %35.8 | %37.0 | 1.9309 | +0.1825 [+0.0676, +0.2970] |
| diğer | 1 | %100.0 | %0.0 | %0.0 | 1.4622 | -0.0531 – |

### Altın at kuralı (seçim 2026-03-16→2026-07-26, 130 gün; rapor 2026-07-27→2026-10-23, 65 gün — sınama dilimine bakılmadan)

Tarama: p_min × fark_min × günde en çok (sabah olasılığı; arayüzdeki gibi p + fark sırasıyla). Koşul: gunde_ort ≥ 0.7 ve n ≥ 150 (tam döneme oranlanmış: seçim diliminde ≥ 100). En iyi uygun 8 satır (seçim dilimi) ve aynı kuralların sınama dilimi sonucu:

| p_min | fark_min | günde en çok | n | kazanma isabeti | ilk 3 isabeti | günde ort. | sınama: n / isabet / ilk 3 |
|---|---|---|---|---|---|---|---|
| 0.45 | 0.15 | 1 | 104 | %58.7 | %92.3 | 0.80 | 29 / %34.5 / %86.2 |
| 0.45 | 0.20 | 1 | 101 | %58.4 | %92.1 | 0.78 | 27 / %33.3 / %85.2 |
| 0.45 | 0.10 | 1 | 105 | %58.1 | %92.4 | 0.81 | 30 / %36.7 / %86.7 |
| 0.45 | 0.05 | 1 | 106 | %57.6 | %92.5 | 0.81 | 30 / %36.7 / %86.7 |
| 0.30 | 0.15 | 1 | 127 | %56.7 | %89.0 | 0.98 | 62 / %32.3 / %74.2 |
| 0.40 | 0.15 | 1 | 120 | %56.7 | %90.0 | 0.92 | 50 / %32.0 / %76.0 |
| 0.30 | 0.05 | 1 | 129 | %56.6 | %89.1 | 0.99 | 65 / %35.4 / %75.4 |
| 0.35 | 0.15 | 1 | 124 | %56.5 | %89.5 | 0.95 | 57 / %33.3 / %77.2 |

- Seçim dilimindeki en iyi aday: p ≥ 0.45, fark ≥ 0.15, günde en çok 1 → sınamada 29 seçim, isabet %34.5 (%95 GA [+0.1994, +0.5266]), ilk 3 %86.2, günde 0.45.
- Mevcut arayüz kuralı (p ≥ .35, fark ≥ .12, günde 3) sınamada: 140 seçim, isabet %42.1 (%95 GA [+0.3428, +0.5043]), ilk 3 %82.1, günde 2.15.
- **Karar: mevcut kural (aday sınama diliminde mevcut kuraldan kötü)** → `model.json` `altin_kural`: p ≥ 0.35, fark ≥ 0.12, günde en çok 3 (sınama isabeti %42.1, n 140).

### İdman (galop/sprint) verisi araştırması

- Gece araştırmacısı (2026-10-26): idman/galop ile ilgili 0 GitHub adayı, açık lisanslı 0; hiçbiri otomatik bağlanmaz (`data/at/arastirma.json`).

## Özet: v4 turu — sabah (oransız) modeli, iki katlı sağlam ölçüm (25.10.2026 gece)

**Ölçüm artık tek bir 7 aylık dilime dayanmıyor.** İki zaman katı, her ikisinde de her ay yalnız o aydan önceki veriyle yeniden eğitim (genişleyen pencere): **A katı 2025-11-01 → 2026-03-15** (2,153 koşu), **B katı 2026-03-16 → 2026-10-23** (3,282 koşu; v3'ün sınama dilimiyle aynı). Kapı: katların ortalama yalnız-model log-loss'u düşmeli, ortalama ilk-seçim isabeti düşmemeli, en güncel kat (B) kötüleşmemeli ve harman 0,001'den fazla bozulmamalı. Her adım için koşu başına eşleştirilmiş ΔLL ve koşu-bootstrap %95 GA.

| | yalnız model LL (A / B / ort.) | ilk seçim (A / B / ort.) | harman LL ort. | piyasa LL ort. |
|---|---|---|---|---|
| v3 tarifi (önce) | 1.8623 / 1.9166 / **1.8895** | %32.9 / %30.4 / **%31.6** | 1.7968 | 1.8149 |
| v4 tarifi (sonra) | 1.8591 / 1.9094 / **1.8842** | %33.1 / %30.4 / **%31.8** | 1.7960 | 1.8149 |

- Toplam: ortalama yalnız-model log-loss 1.8895 → 1.8842 (-0.0053); B katı 1.9166 → 1.9094; A katı 1.8623 → 1.8591. Kazanç küçük: sabah modeli hâlâ piyasanın belirgin gerisinde.
- **Toplam eşleştirilmiş fark (v4 − v3, yalnız model):** birleşik -0.0057 [-0.0092, -0.0019]; A katı -0.0033 [-0.0096, +0.0035]; B katı -0.0072 [-0.0112, -0.0034]. İlk seçim isabeti farkı +0.09 puan. Harman: -0.0009 [-0.0022, +0.0005].
- Yalnız model − piyasa (iki kat birleşik): +0.0719 [+0.0565, +0.0851]; harman − piyasa: -0.0179 [-0.0232, -0.0128].

Kapılı deneyler (ΔLL = yeni − önceki kabul, koşu başına; köşeli parantez koşu-bootstrap %95 GA, iki kat birleşik):

| # | deney | sonuç | ort. LL / ilk seçim | A: LL / ilk | B: LL / ilk | ΔLL birleşik [%95 GA] | ΔLL A [%95 GA] | ΔLL B [%95 GA] | harman ort. |
|---|---|---|---|---|---|---|---|---|---|
| 0 | v3 taban (yayındaki tarif), iki katta | taban | 1.8895 / %31.6 | 1.8623 / %32.9 | 1.9166 / %30.4 | – | – | – | 1.7968 |
| 1 | 1: handikap reytingi vekili (kilo sırası, en hafife göre kg, kg×sınıf, örtük HP: atın son 3 handikap değerinin medyanı, bugünkü örtük HP, değişim, alana göre; apranti indirimi medyanla) | ❌ elendi | 1.8880 / %31.4 | 1.8620 / %32.5 | 1.9140 / %30.4 | -0.0017 [-0.0035, +0.0002] | -0.0004 [-0.0034, +0.0028] | -0.0026 [-0.0049, -0.0002] | 1.7968 |
| 2 | 2a: alan büyüklüğüne duyarlı sıcaklık | ❌ elendi | 1.8901 / %31.6 | 1.8626 / %32.9 | 1.9175 / %30.4 | +0.0006 [-0.0003, +0.0016] | +0.0003 [-0.0014, +0.0020] | +0.0009 [-0.0003, +0.0021] | 1.7969 |
| 3 | 2b: beta kalibrasyonu (log p, log(1−p)) | ✅ kaldı | 1.8893 / %31.6 | 1.8629 / %32.9 | 1.9157 / %30.4 | -0.0003 [-0.0008, +0.0003] | +0.0006 [-0.0004, +0.0015] | -0.0009 [-0.0016, -0.0002] | 1.7967 |
| 4 | 2c: izotonik (kalibrasyon penceresi, %50 karışım) | ❌ elendi | 1.8892 / %31.6 | 1.8620 / %32.9 | 1.9164 / %30.4 | +0.0000 [-0.0011, +0.0012] | -0.0009 [-0.0026, +0.0010] | +0.0006 [-0.0009, +0.0022] | 1.7963 |
| 5 | 2d: izotonik, yuvarlanan 180 gün önceki sınama-dışı tahminlerden (%50 karışım) | ❌ elendi | 1.8910 / %31.6 | 1.8650 / %32.9 | 1.9171 / %30.4 | +0.0016 [+0.0005, +0.0028] | +0.0021 [-0.0001, +0.0043] | +0.0013 [+0.0002, +0.0024] | 1.7969 |
| 6 | 2e: izotonik, yuvarlanan 180 gün (%100) | ❌ elendi | 1.8946 / %31.6 | 1.8697 / %32.9 | 1.9195 / %30.4 | +0.0050 [+0.0027, +0.0073] | +0.0068 [+0.0024, +0.0112] | +0.0038 [+0.0014, +0.0060] | 1.7972 |
| 7 | 3a: patlatılmış logit (doğrusal) derinlik 3, ağırlık 1/0.5/0.25 | ❌ elendi | 1.8869 / %31.6 | 1.8586 / %32.9 | 1.9152 / %30.3 | -0.0020 [-0.0035, -0.0005] | -0.0043 [-0.0071, -0.0017] | -0.0005 [-0.0020, +0.0010] | 1.7963 |
| 8 | 3b: patlatılmış logit (doğrusal) derinlik 2, ağırlık 1/0.5 | ❌ elendi | 1.8863 / %31.6 | 1.8574 / %33.2 | 1.9153 / %30.0 | -0.0024 [-0.0037, -0.0012] | -0.0055 [-0.0079, -0.0032] | -0.0004 [-0.0016, +0.0008] | 1.7963 |
| 9 | 4: değişim sinyalleri (işaretli mesafe değişimi, pist değişimi/ilk kez, jokey reyting farkı, ara kovaları, uzun aradan sonra 2. koşu, 2 yaş×mesafe, sınıf düşüş/çıkış) | ✅ kaldı | 1.8875 / %31.6 | 1.8640 / %32.8 | 1.9109 / %30.5 | -0.0025 [-0.0053, +0.0006] | +0.0011 [-0.0042, +0.0065] | -0.0048 [-0.0080, -0.0017] | 1.7961 |
| 10 | 6: GBM 3 tohum torbalama (ham puan ortalaması; doğrusal+GBM yığma katsayıları ayrı pencerede) | ❌ elendi | 1.8870 / %31.6 | 1.8629 / %32.6 | 1.9110 / %30.6 | -0.0004 [-0.0012, +0.0003] | -0.0010 [-0.0021, +0.0001] | +0.0000 [-0.0010, +0.0010] | 1.7960 |
| 11 | 7a: GBM 15 yaprak, en az 300 | ❌ elendi | 1.8866 / %31.4 | 1.8619 / %32.6 | 1.9112 / %30.0 | -0.0007 [-0.0024, +0.0011] | -0.0020 [-0.0046, +0.0004] | +0.0002 [-0.0021, +0.0028] | 1.7957 |
| 12 | 7b: GBM 7 yaprak, en az 300, 900 ağaç, öğrenme 0.02 | ❌ elendi | 1.8874 / %31.6 | 1.8633 / %33.1 | 1.9114 / %30.2 | +0.0000 [-0.0011, +0.0011] | -0.0007 [-0.0025, +0.0011] | +0.0004 [-0.0009, +0.0019] | 1.7960 |
| 13 | 7c: GBM 5 yaprak, en az 800 | ❌ elendi | 1.8893 / %31.9 | 1.8653 / %33.4 | 1.9132 / %30.3 | +0.0018 [+0.0006, +0.0032] | +0.0013 [-0.0006, +0.0033] | +0.0022 [+0.0004, +0.0040] | 1.7968 |
| 14 | 7d: zaman ağırlığı yarı ömrü 365 gün | ❌ elendi | 1.8891 / %31.8 | 1.8653 / %33.1 | 1.9128 / %30.5 | +0.0017 [+0.0005, +0.0029] | +0.0014 [-0.0002, +0.0029] | +0.0019 [+0.0001, +0.0036] | 1.7966 |
| 15 | 7e: zaman ağırlığı yarı ömrü 120 gün | ❌ elendi | 1.8881 / %31.7 | 1.8642 / %32.9 | 1.9121 / %30.6 | +0.0008 [-0.0006, +0.0023] | +0.0003 [-0.0023, +0.0032] | +0.0012 [-0.0005, +0.0028] | 1.7963 |
| 16 | 8a: yeniden: handikap reytingi vekili (yeni tabanda) | ✅ kaldı | 1.8857 / %31.6 | 1.8612 / %32.6 | 1.9101 / %30.7 | -0.0016 [-0.0035, +0.0002] | -0.0028 [-0.0057, +0.0003] | -0.0008 [-0.0029, +0.0015] | 1.7960 |
| 17 | 8b: yeniden: patlatılmış logit derinlik 2 (yeni tabanda) | ✅ kaldı | 1.8842 / %31.8 | 1.8591 / %33.1 | 1.9094 / %30.4 | -0.0013 [-0.0025, -0.0001] | -0.0021 [-0.0044, +0.0002] | -0.0008 [-0.0021, +0.0006] | 1.7960 |

Kalibrasyon — yalnız model, kat kat (önce = v3 tarifi, sonra = v4 tarifi):

| kat | tahmin aralığı | önce: at / ort. tahmin / gerçek | sonra: at / ort. tahmin / gerçek |
|---|---|---|---|
| A | 0.00-0.05 | 7972 / %2.5 / %2.5 | 7957 / %2.5 / %2.5 |
| A | 0.05-0.10 | 4985 / %7.3 / %7.5 | 4913 / %7.3 / %7.3 |
| A | 0.10-0.20 | 4716 / %14.1 / %13.4 | 4798 / %14.2 / %13.4 |
| A | 0.20-0.30 | 2017 / %24.5 / %25.1 | 2038 / %24.2 / %25.0 |
| A | 0.30-0.50 | 1028 / %36.0 / %37.2 | 1015 / %36.3 / %37.7 |
| A | 0.50-1.00 | 97 / %57.5 / %61.9 | 94 / %56.8 / %60.6 |
| B | 0.00-0.05 | 13091 / %2.5 / %2.5 | 13124 / %2.4 / %2.5 |
| B | 0.05-0.10 | 7705 / %7.3 / %7.7 | 7520 / %7.3 / %7.7 |
| B | 0.10-0.20 | 7183 / %14.1 / %14.7 | 7366 / %14.2 / %14.4 |
| B | 0.20-0.30 | 2881 / %24.4 / %22.6 | 2852 / %24.2 / %23.0 |
| B | 0.30-0.50 | 1584 / %36.5 / %35.8 | 1572 / %36.8 / %36.0 |
| B | 0.50-1.00 | 170 / %58.9 / %47.6 | 180 / %57.9 / %51.1 |

**Üst kova (%50+) bulgusu:** v3 raporundaki "%59 tahmin, %48 gerçek" iyimserliği **yalnız B katında** var; A katında aynı tarif tam tersine **temkinli** (tahmin ≈%57, gerçek ≈%62). İki katta birlikte fark ≈5 puan ve kova başına yalnız 90–180 at (std. hata ≈4 puan). Pencerede öğrenilen düzeltmeler (alan büyüklüğüne duyarlı sıcaklık, izotonik — hem kalibrasyon penceresinde hem önceki ayların sınama-dışı tahminlerinden) bu yüzden dışarıda tutmadı: iyimserlik kalıcı bir yanlılık değil, döneme bağlı bir dalgalanma gibi davranıyor. v4 tarifiyle (beta kalibrasyonu + yeni özellikler) B katındaki %50+ farkı ≈11 puandan ≈7 puana indi, A katındaki temkinlilik ≈4 puan; kalan farkı raporda açıkça gösteriyoruz ve kovaya düşen at sayısı arttıkça yeniden bakacağız.

- Kabul edilenler: **değişim sinyalleri** (işaretli mesafe değişimi, pist değişimi / ilk kez bu pist, jokey reyting farkı, ara kovaları, uzun aradan sonraki 2. koşu, 2 yaş×mesafe, sınıf düşüşü/çıkışı), **beta kalibrasyonu**, **handikap reytingi vekili** ve **patlatılmış (sıralı) logit, derinlik 2** (Bolton–Chapman; 2. sıra 0,5 ağırlıkla). Son ikisi ilk denemede yalnız ilk-seçim kuralına takıldı (log-loss düşüyordu); yeni tabanda bir kez daha denendi ve geçti — bu tekrar tabloda açıkça var.
- Elenenler: alan büyüklüğüne duyarlı sıcaklık, izotonik (üç türü), GBM 3 tohum torbalama (etkisiz, üç kat süre), GBM ayarları (15/5 yaprak, daha yavaş öğrenme) ve zaman ağırlığı yarı ömrü 120/365 gün.
- Handikap vekili yan bulgusu: örtük sınıf düzeyleri veriden tamamen kendiliğinden doğru sıralandı (Handikap 13 < 14 < 15 < 16 < 17 < 21 < KV-22/24) ve apranti indirimi tahmini 0–3,5 kg aralığında — vekil anlamlı, ama bilgisi büyük ölçüde mevcut kilo/reyting özellikleriyle örtüşüyor.
- Deney kaydı: `data/at/deneyler_v4.json` (2026-10-25T20:12:38; süre 2084 sn); deney masası `lab/at/deney4.py`.

## Jokey ve ahır (attan arındırılmış beceri)

Jokey, antrenör ve at güçleri koşu içi Plackett-Luce ile **ortak** ve Bayes küçültmeli tahmin edilir (her varlık için ortalama + belirsizlik; zamanla belirsizlik geri açılır). Jokeyin "katkısı" aynı at ve ahırla ortalama jokeye göre güç farkıdır; ek sinyaller jokeysiz beklentiye göre kalıntılardan: jokey–antrenör / jokey–at birlikteliği, jokey değişimi, son 14/30 gün formu, günlük iş yükü (programdan), pist/mesafe/hipodrom uzmanlığı, apranti vekili, "üst jokey seçimi". Hepsi yalnız koşu gününden önceki veriyle (sızıntı testi: `python lab/at/deney_jokey.py --sizinti`).

Kapılı deneyler (v4 iki katlı kapı; ΔLL = yeni − önceki kabul, yalnız model, koşu-bootstrap %95 GA):

| # | grup | sonuç | ort. LL / ilk seçim | B: LL / ilk | ΔLL birleşik [%95 GA] | ΔLL A | ΔLL B | harman ort. |
|---|---|---|---|---|---|---|---|---|
| 0 | v4 taban (yayındaki tarif) | taban | 1.8842 / %31.8 | 1.9094 / %30.4 | – | – | – | 1.7960 |
| 1 | jk_beceri — beceri: attan arındırılmış jokey/antrenör/at gücü (ortak Bayes Plackett-Luce), jokey z, alan içi ortak güç | ❌ elendi | 1.8727 / %31.6 | 1.9000 / %29.9 | -0.0110 [-0.0149, -0.0071] | -0.0136 [-0.0190, -0.0082] | -0.0094 [-0.0150, -0.0037] | 1.7938 |
| 2 | jk_ikili — ikili uyum: jokey–antrenör ve jokey–at birlikteliği (jokeysiz beklentiye göre kalıntı, küçültmeli) | ❌ elendi | 1.8839 / %31.6 | 1.9096 / %30.4 | -0.0002 [-0.0018, +0.0014] | -0.0009 [-0.0035, +0.0016] | +0.0002 [-0.0020, +0.0023] | 1.7958 |
| 3 | jk_degisim — jokey değişimi: önceki jokeye göre beceri farkı, yükseltme/düşürme, ilk kez bu ikili | ❌ elendi | 1.8847 / %31.8 | 1.9095 / %30.5 | +0.0004 [-0.0009, +0.0019] | +0.0009 [-0.0012, +0.0031] | +0.0001 [-0.0017, +0.0018] | 1.7960 |
| 4 | jk_form — form momentumu: jokey kalıntısı son 14/30 gün, 30 gün − 365 gün z, ahır 30 gün | ❌ elendi | 1.8857 / %31.4 | 1.9109 / %30.2 | +0.0015 [-0.0002, +0.0032] | +0.0014 [-0.0014, +0.0047] | +0.0015 [-0.0002, +0.0033] | 1.7964 |
| 5 | jk_yuk — günlük iş yükü: o gün kaç biniş (programdan), tek binişlik gün | ❌ elendi | 1.8843 / %31.7 | 1.9089 / %30.5 | +0.0000 [-0.0012, +0.0012] | +0.0008 [-0.0010, +0.0025] | -0.0005 [-0.0021, +0.0011] | 1.7959 |
| 6 | jk_uzman — uzmanlık: jokeyin pist / mesafe kovası / hipodrom kalıntısı − genel | ✅ kaldı | 1.8836 / %31.8 | 1.9085 / %30.8 | -0.0007 [-0.0022, +0.0009] | -0.0004 [-0.0029, +0.0020] | -0.0009 [-0.0030, +0.0012] | 1.7958 |
| 7 | jk_apr — apranti vekili: az biniş / yeni lisans, × kilo farkı, tecrübe | ✅ kaldı | 1.8830 / %31.8 | 1.9079 / %30.8 | -0.0005 [-0.0019, +0.0010] | -0.0005 [-0.0030, +0.0020] | -0.0006 [-0.0024, +0.0013] | 1.7957 |
| 8 | jk_secim — üst jokey seçimi: düzenli ahırlarının atları varken bu ata binmesi (× beceri), ahırın ana jokeyi başka atta (terk), ana jokey | ❌ elendi | 1.8830 / %31.9 | 1.9075 / %30.8 | -0.0001 [-0.0015, +0.0013] | +0.0003 [-0.0018, +0.0024] | -0.0004 [-0.0022, +0.0014] | 1.7957 |
| 9 | yeniden (yeni tabanda): jk_beceri | ✅ kaldı | 1.8722 / %31.9 | 1.8997 / %30.3 | -0.0102 [-0.0141, -0.0065] | -0.0134 [-0.0189, -0.0080] | -0.0082 [-0.0135, -0.0025] | 1.7936 |
| 10 | yeniden (yeni tabanda): jk_ikili | ❌ elendi | 1.8731 / %32.1 | 1.9017 / %30.6 | +0.0010 [-0.0006, +0.0026] | -0.0004 [-0.0030, +0.0022] | +0.0019 [+0.0000, +0.0039] | 1.7938 |
| 11 | yeniden (yeni tabanda): jk_secim | ❌ elendi | 1.8731 / %31.7 | 1.9010 / %30.2 | +0.0009 [-0.0005, +0.0023] | +0.0003 [-0.0018, +0.0024] | +0.0013 [-0.0003, +0.0030] | 1.7938 |

- Yayına giren jk grupları: **jk_uzman, jk_apr, jk_beceri** (yayındaki: jk_uzman, jk_apr, jk_beceri). Deney kaydı: `data/at/jokeyler.json` → `deney` (2026-10-26T03:18:27; süre 1243 sn).
- Toplam (seçilenler − v4 taban): yalnız model -0.0114 [-0.0157, -0.0074]; harman -0.0022 [-0.0038, -0.0007].
- Dönem 2026-07-28 → 2026-10-25 (son 90 gün, en az 30 biniş). Katkı = 10 atlı koşuda ortalama ata binince kazanma olasılığının ortalama jokeye göre farkı (puan). İlk 5:

| jokey | biniş (90 g) | kazanma | ilk 3 | katkı (puan) | z | form | uzmanlık |
|---|---|---|---|---|---|---|---|
| GÖKHAN KOCAKAYA | 208 | %23.1 | %53.4 | +15.2 | 9.9 | sabit | Sentetik / kısa / İstanbul |
| VEDAT ABİŞ | 290 | %24.5 | %59.3 | +14.0 | 12.4 | sabit | Kum / orta / Adana |
| HALİS KARATAŞ | 121 | %19.8 | %54.5 | +12.4 | 6.8 | sabit | Kum / kısa / Ankara |
| AHMET ÇELİK | 59 | %17.0 | %49.1 | +10.6 | 7.0 | yukseliyor | Çim / kısa / Adana |
| SELİM KAYA | 48 | %18.8 | %45.8 | +9.6 | 4.2 | sabit | Kum / orta / Adana |

## v5 turu: sınıf-ayarlı form, kilo, dinlenme, harman

Aynada start/kulvar numarası ve koşu içi pozisyon (tempo) yok; kulvar yanlılığı ve koşu stili kurulamadı. Aynı gün pist yanlılığı sabah kilidinde bilinemediği için denenmedi. Adaylar `lab/at/at5.py`; kapı deney4 iki katlı kapı (hm_alan için harmanın kendi kapısı). Sızıntı testi: `python lab/at/deney5.py --sizinti`.

| # | deney | sonuç | ort. LL / ilk seçim | B: LL / ilk | ΔLL birleşik [%95 GA] | ΔLL A | ΔLL B | harman ort. LL / ilk | ΔLL harman |
|---|---|---|---|---|---|---|---|---|---|
| 0 | taban (yayındaki tarif: v4 + jk_uzman, jk_apr, jk_beceri) | taban | 1.8729 / %31.8 | 1.9016 / %30.2 | – | – | – | 1.7948 / %35.2 | – |
| 1 | a5_sinif — sınıf-ayarlı form: son koşulardaki rakip alan düzeyi (alanın PL at reytingi) − bugünkü alan, ilk 3'e girdiği en güçlü alan, güçlü alanlarda ilk 3 payı | ✅ kaldı | 1.8616 / %31.9 | 1.8937 / %30.8 | -0.0106 [-0.0140, -0.0075] | -0.0148 [-0.0193, -0.0098] | -0.0079 [-0.0126, -0.0033] | 1.7906 / %35.4 | -0.0038 [-0.0052, -0.0024] |
| 2 | a5_kilo — göreli kilo değişimi: (kilo − alan ort.) bugün − son koşu, kilo × mesafe, galibiyet sonrası kilo, iyi koştuğu kiloya göre fark | ❌ elendi | 1.8613 / %31.8 | 1.8929 / %30.5 | -0.0004 [-0.0018, +0.0011] | +0.0001 [-0.0024, +0.0025] | -0.0007 [-0.0025, +0.0012] | 1.7907 / %35.1 | +0.0001 [-0.0005, +0.0007] |
| 3 | a5_taze — dinlenme eğrisi: atın uzun aradan / sık koşudaki kişisel uyumu, antrenörün uzun aradan dönüş kalıntısı (piyasaya göre), log(ara)², son 30 günde koşu | ❌ elendi | 1.8609 / %31.8 | 1.8929 / %30.5 | -0.0007 [-0.0023, +0.0008] | -0.0007 [-0.0036, +0.0022] | -0.0007 [-0.0024, +0.0011] | 1.7904 / %35.5 | -0.0001 [-0.0008, +0.0005] |
| 4 | hm_alan — harman ağırlığı alan büyüklüğüne göre: (α + α'·z)·log p + (β + β'·z)·log q | ❌ elendi | 1.8616 / %31.9 | 1.8937 / %30.8 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 1.7913 / %35.4 | +0.0007 [-0.0007, +0.0021] |
| 5 | yeniden (yeni tabanda): a5_kilo | ❌ elendi | 1.8613 / %31.8 | 1.8929 / %30.5 | -0.0004 [-0.0018, +0.0011] | +0.0001 [-0.0024, +0.0025] | -0.0007 [-0.0025, +0.0012] | 1.7907 / %35.1 | +0.0001 [-0.0005, +0.0007] |
| 6 | yeniden (yeni tabanda): a5_taze | ❌ elendi | 1.8609 / %31.8 | 1.8929 / %30.5 | -0.0007 [-0.0023, +0.0008] | -0.0007 [-0.0036, +0.0022] | -0.0007 [-0.0024, +0.0011] | 1.7904 / %35.5 | -0.0001 [-0.0008, +0.0005] |

- Yayına giren a5 grupları: **a5_sinif** (yayındaki: a5_sinif); alan büyüklüğüne duyarlı harman: hayır. Deney kaydı: `data/at/deneyler_v5.json` (2026-10-26T17:19:19; süre 2417 sn).
- Toplam (seçilenler − taban): yalnız model -0.0106 [-0.0140, -0.0075]; harman -0.0038 [-0.0052, -0.0024].

## Özet: v3 turu (25.10.2026 akşam; rakamlar v3 modelinin)

**Yeni veri kaynağı (atyarisi.com) — bağlanmadı.** Keşif (yalnız GitHub Actions'tan, ≤30 istek, ≥2 sn ara) şunu gösterdi: www.atyarisi.com sayfaları yalnız boş bir uygulama kabuğu; program/AGF/sonuç verisi tarayıcıda `tjkbulten.atyarisi.com/api` ve `tjkgw.atyarisi.com/api` adreslerinden çekiliyor ve bu iki alan adının robots.txt'i **tüm robotlara `Disallow: /`** diyor. llms.txt izni yalnız `www.atyarisi.com` için. Kullanım Şartları metni de robots ile kapalı `help.atyarisi.com`'dan yükleniyor (otomatik okunamadı). Kırmızı çizgi (robots'a uy) gereği kaynak bağlanmadı; HP, kulvar, AGF, KGS, EİD, orijin özellikleri bu turda yok (bkz. model.json `kaynaklar`).

Kapılı deneyler (aynı 3.282 sınama koşusu; ΔLL = yeni − önceki kabul, koşu başına; köşeli parantez koşu-bootstrap %95 GA):

| # | deney | sonuç | yalnız model LL / ilk seçim | harman LL / ilk seçim | ΔLL model [%95 GA] | ΔLL harman [%95 GA] |
|---|---|---|---|---|---|---|
| 0 | v2 taban (yayındaki tarif) | taban | 1.9348 / %29.4 | 1.8180 / %34.4 | – | – |
| 1 | B1: pist durumu (zemin sırası, zemin uyumu, zemin×kilo, zemin×form) | ❌ elendi | 1.9366 / %29.1 | 1.8184 / %34.5 | +0.0017 [+0.0007, +0.0029] | +0.0004 [+0.0001, +0.0007] |
| 2 | B2: hız figürü (par + projeksiyonlu, küçültmeli gün değişkeni; en iyi/son/ort3/eğilim/alana göre) | ✅ kaldı | 1.9166 / %30.4 | 1.8146 / %34.5 | -0.0182 [-0.0244, -0.0120] | -0.0033 [-0.0056, -0.0012] |
| 3 | B3: kalıntı LightGBM (init_score = log q) harmana eklenir | ❌ elendi | 1.9166 / %30.4 | 1.8135 / %34.5 | +0.0000 [+0.0000, +0.0000] | -0.0011 [-0.0030, +0.0008] |

- Piyasa keskinleştirme kontrolü (q^β tek başına): keskin − piyasa -0.0009 [-0.0035, +0.0019]; **harman − keskin piyasa -0.0122 [-0.0185, -0.0061]** (model ancak bu negatifse piyasaya bilgi katıyor demektir); harman − piyasa -0.0131 [-0.0195, -0.0066]; yalnız model − piyasa +0.0889 [+0.0704, +0.1074].
- Hız figürü gün değişkeni: Beyer projeksiyonu (atların önceki figürleri) yerine kazanan − par − sınıf ofseti kullanılsaydı yalnız-model LL +0.0101 [+0.0054, +0.0149] kötüleşirdi (cins/sınıf karışımı yüzünden); projeksiyon yayında.
- İndirimli Harville (ikili/üçlü sıralı log-loss, sınama): yalnız model γ,δ öğrenilmiş 3.7441 / 5.5180 vs düz Harville 3.7550 / 5.5589; harman 3.6205 / 5.3830 vs 3.6317 / 5.4300 (3262 koşu).
- Sızıntı testi (`lab/at/test_sizinti.py`, her gece): aynı (at, gün) satırları özdeş; rastgele günlerde yalnız geçmişten yeniden kurulan durum tam tabloyla birebir aynı; gün içi koşu sırası özellikleri değiştirmiyor.

## Özet: v2 güncellemesi (25.10.2026)

Uygulamadaki **sabah tahminleri yalnız modeldir** (sabah programında ganyan oranı yok). Bu yüzden bu turda hedef, oransız (yalnız geçmişe dayalı) tahmini güçlendirmekti. Yapılanlar:

- **Yalnız model (sabah) sınama log-loss'u 2.0057 → 1.8937; ilk seçim isabeti %26.7 → %30.8** (aynı 3,278 sınama koşusu). Piyasa favorisi hâlâ önde: %35.2, piyasa log-loss 1.8305.
- Model + piyasa harmanı: log-loss 1.8262 → 1.8124 (piyasaya göre -0.0181 ± 0.0040; anlamlı iyileşme).
- Yeni bilgiler: atın **geçmiş koşulardaki piyasa değerlendirmesi** (oran hafızası: üstel ortalama, piyasa sırası, yenilen favori, piyasanın beklediğinden iyi/kötü koşma, rakiplere göre aktarılan "piyasa reytingi"), her koşudan sonra güncellenen **Plackett-Luce reytingleri** (at + jokey + antrenör), **sayısal sınıf** (koşu türü, alanın reyting düzeyi, handikapta kilo), **zaman sönümlü form**.
- Eğitim: sınamada her ay **yalnız o aydan önceki veriyle yeniden eğitim** (walk-forward; gece akışı da her gün böyle eğitir), eski koşulara daha az ağırlık (yarı ömür 180 gün), ve doğrusal modelin yanına **LightGBM** (koşu içi softmax amacıyla) eklendi; ikisinin karışımı, sıcaklık ve %25 üstü olasılıklar için ayrı bir "üst uç" eğimi son 90 günde kalibre edilir.
- Kapı artık **yalnız-model** ölçülerine bakıyor (sabah ekranı bunu gösteriyor), harman da kötüleşmemeli; tarif değişince eski ve yeni tahminler aynı sınama koşularında kıyaslanıyor (bkz. Kapı).
- Elenenler: basit hız puanı (v3'te Beyer tarzı figür olarak yeniden yazıldı ve kapıdan geçti), jokey/antrenör piyasa ilgisi + ekuri (log-loss'u çok az düşürdü ama ilk seçim isabetini düşürdü); sabah programındaki form dizisi (yalnız 2026-04 sonrasında var, eğitim geçmişi yetersiz).
- Dürüst sonuç: model tek başına **hâlâ piyasa favorisinin gerisinde**. Sabah tahminleri bilgi amaçlıdır; koşu öncesi oran geldiğinde en güvenilir olasılık piyasa (ve harman) olur.

## Kısa sonuç (dürüst)

- Yalnız geçmiş verilerle kurulan model (sabah tahmini) **tek başına piyasadan zayıf**: sınama log-loss 1.8937 (piyasa 1.8305), ilk seçim isabeti %30.8 (piyasa favorisi %35.2). Fark model − piyasa = +0.0631 ± 0.0096.
- Model + piyasa harmanı log-loss'u 1.8124: piyasaya göre fark **-0.0181 ± 0.0040** (std. hata). Bu fark istatistiksel olarak anlamlı bir iyileşme (2 std. hatadan büyük).
- Harmanın ilk seçim isabeti %34.3, piyasa favorisi %35.2. Yayın modu: **model+piyasa** (kural: harman sınama log-loss'u piyasadan düşükse model+piyasa yayınlanır).
- Kalibrasyon, en yüksek kova: yalnız model 0.50-1.00 aralığında ortalama tahmin %58.1, gerçek %52.5 (219 at); harman %58.6 / %54.5 (415 at). Yani %50+ verilen atlarda model hâlâ biraz iyimser; bu atlar gerçekte yaklaşık yarı yarıya kazanıyor.

## Veri kapsamı

- Kaynak: herkese açık ayna [https://github.com/cenkozgur/tjk-data](https://github.com/cenkozgur/tjk-data) (lisans belirtilmemiş). Ayna durumu: güncellendi. tjk.org'a hiçbir istek atılmaz; ham veri bu depoya kopyalanmaz.
- Sonuçlar: 2025-01-01 → 2026-10-25, **10,913 yerli koşu**, 106,041 koşan at; tam oranlı koşu 10,879. Yabancı (simulcast) koşular ve kazananı belirsiz koşular çıkarıldı ({'yabanci': 3205, 'kazanansiz': 21, 'az_at': 0}).
- Hipodromlar: İstanbul 2078, İzmir 1720, Bursa 1413, Adana 1306, Ankara 1291, Şanlıurfa 802, Antalya 764, Elazığ 688, Kocaeli 572, Diyarbakır 279.
- Zaman sıralı ölçüm: ısınma (yalnız geçmiş biriktirme) < 2025-03-01; **sınama (son %30) 2026-03-17→2026-10-25 (3278 tam oranlı koşu)**. aylık walk-forward: sınamanın her ayı için yalnız o aydan önceki verilerle yeniden eğitim; kalibrasyon ayın hemen öncesindeki 90 günde; zaman ağırlığı yarı ömrü 180 gün.
- Piyasa olasılığı q: **nihai** ganyan oranından (1/oran, marj ayrılmış). Bu, "son koşu öncesi" piyasayı temsil eder; sabah programında oran yoktur. Yani harman ancak koşudan hemen önce kullanılabilir; sabah kilitlenen tahminler yalnız modeldir. Geçmiş koşuların oranları ise (o koşular bittiği için) sabah da bilinir ve modelde "piyasa hafızası" olarak kullanılır.
- Kullanılmayanlar: aynanın memory/*.json özetleri (geleceği içerir → sızıntı), gün içi oran görüntüleri (yalnız 57 gün), hava/nem ve form dizileri (yalnız 2026-04 sonrası programlarda).

## Sınama metrikleri (son %30, yalnız tam oranlı koşular)

| | log-loss ↓ | Brier ↓ | ilk seçim | ikili (sıralı) | ilk iki → ilk 2 | p≥.30 seçim / isabet (ort. p) | p≥.50 seçim / isabet (ort. p) |
|---|---|---|---|---|---|---|---|
| **Yalnız model (sabah)** | 1.8937 | 0.8075 | %30.8 | %9.3 | %15.7 | 1858 / %37.5 (%39.5) | 219 / %52.5 (%58.1) |
| Piyasa q | 1.8305 | 0.7856 | %35.2 | %10.9 | %18.8 | 2016 / %41.0 (%40.3) | 272 / %57.7 (%57.5) |
| **Model + piyasa** | 1.8124 | 0.7824 | %34.3 | %10.9 | %19.1 | 2297 / %39.8 (%41.6) | 415 / %54.5 (%58.6) |
| Favori tabanı | – | – | %35.2 | %10.9 | %18.8 | – | – |
| Düzgün (1/N) | 2.2411 | 0.8873 | – | – | – | – | – |

Eşleştirilmiş log-loss farkı (koşu başına, ± std. hata): harman − piyasa = -0.0181 ± 0.0040; model − piyasa = +0.0631 ± 0.0096.

Parametreler (yayın modeli): birleşik puan = 0.55409 × doğrusal + 0.4453 × GBM (GBM açık); harman α = 0.4076, β = 0.7473; Henery üsleri γ(2.) = 0.84, δ(3.) = 0.76; L2 λ = 300.0. LightGBM kurulu değilse model doğrusal yedeğe (kendi kalibrasyonuyla) düşer.

### Kalibrasyon (sınama, yalnız model (sabah tahmini))

| tahmin aralığı | at | ort. tahmin | gerçek kazanma |
|---|---|---|---|
| 0.00-0.05 | 13406 | %2.3 | %2.4 |
| 0.05-0.10 | 7287 | %7.3 | %7.9 |
| 0.10-0.20 | 7233 | %14.2 | %14.6 |
| 0.20-0.30 | 2783 | %24.3 | %22.9 |
| 0.30-0.50 | 1639 | %37.0 | %35.4 |
| 0.50-1.00 | 219 | %58.1 | %52.5 |

### Kalibrasyon (sınama, model + piyasa)

| tahmin aralığı | at | ort. tahmin | gerçek kazanma |
|---|---|---|---|
| 0.00-0.05 | 14892 | %2.3 | %2.3 |
| 0.05-0.10 | 6689 | %7.2 | %7.9 |
| 0.10-0.20 | 6145 | %14.2 | %14.6 |
| 0.20-0.30 | 2544 | %24.5 | %23.5 |
| 0.30-0.50 | 1882 | %37.9 | %36.6 |
| 0.50-1.00 | 415 | %58.6 | %54.5 |

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
| a5_sr_ort5 | +0.213 |
| hz_alan | +0.162 |
| jk_logp | +0.155 |
| hz_son | +0.142 |
| hz_ort3 | +0.141 |
| jk_at_s | +0.128 |
| jk_j | +0.114 |
| r_jokey | +0.107 |
| piyasa_reyting | +0.105 |
| n_kosu | -0.100 |
| hipodrom_uyum | +0.099 |
| geri_en_iyi5 | -0.089 |

Ablasyon — grup çıkarılınca sınama log-loss'u ne kadar kötüleşiyor (+ = grup faydalı; yalnız doğrusal katmanla, aylık walk-forward):

| çıkarılan grup | yalnız model Δ | model+piyasa Δ |
|---|---|---|
| hiz3 | +0.0175 | +0.0041 |
| a5_sinif | +0.0108 | +0.0026 |
| jk_beceri | +0.0076 | +0.0008 |
| pist_mesafe_hipodrom | +0.0073 | +0.0014 |
| degisim | +0.0053 | +0.0017 |
| piyasa_hafiza | +0.0025 | +0.0003 |
| kilo | +0.0019 | +0.0009 |
| form | +0.0013 | -0.0002 |
| jk_uzman | +0.0008 | +0.0003 |
| hp | +0.0007 | +0.0000 |
| dinlenme | +0.0006 | +0.0001 |
| sinif | +0.0006 | +0.0002 |
| piyasa_gecmisi | +0.0004 | +0.0002 |
| alan | +0.0003 | +0.0001 |
| fark2 | +0.0003 | +0.0000 |
| jk_apr | +0.0003 | +0.0002 |
| antrenor | +0.0000 | +0.0000 |
| fark | -0.0003 | +0.0000 |
| jokey | -0.0004 | -0.0001 |
| reyting | -0.0004 | -0.0003 |
| sinif2 | -0.0004 | +0.0000 |
| yas | -0.0006 | -0.0002 |
| jokey_at | -0.0009 | -0.0007 |

Yorum: sabah tahmininde en çok taşıyan bilgiler reytingler (at/jokey/antrenör), pist/mesafe/hipodrom uyumu, atın geçmişte piyasada nasıl değerlendirildiği (piyasa hafızası) ve dinlenme. Jokeyin son 60 gün oranı artık jokey reytingiyle örtüştüğü için tek başına katkısı kalmadı. Grupların çoğu birbiriyle örtüştüğünden tek grup çıkarmak az fark yaratır; harmana katkıları ±0,001 düzeyinde.

## Kapı (sürekli öğrenme)

- Kural: tarif (özellikler/ayarlar) değişirse yeni model ancak **aynı sınama koşularında** yalnız-model log-loss'u düşürür, ilk seçim isabetini düşürmez ve harman log-loss'unu 0,001'den fazla bozmazsa kabul edilir. Tarif aynıysa özellikler her gece yeni sonuçlarla güncellenir, katsayılar haftada bir yeniden eğitilir (KORU = bu gece yenileme günü değil); ortak koşularda belirgin bozulma (veri sorunu) olursa dünkü model korunur. İz: `data/at/sinama_izi.json`.
- Son karar (2026-10-26T14:39:15+00:00): **KORU** — aynı tarif; katsayılar 0 günlük (haftalık yenileme), özellikler bu gece yeni sonuçlarla güncellendi
- Yeni: yalnız model log-loss 1.8681, ilk seçim %31.7; harman 1.7950. Kıyas: yalnız model 1.8681, ilk seçim %31.7; harman 1.7950.

## Canlı karne (kilitlenmiş tahminler, sonuç gelince)

- Koşudan önce kilitlenmiş toplam 12 koşu: log-loss 2.078, ilk seçim isabeti %25.0, ikili isabeti %0.0.
  - 2026-10-25: 12 koşu, ilk seçim %25.0, log-loss 2.078

## Gösteri: 2026-10-26 İstanbul tahminleri

- Bu gün için İstanbul programı/kilidi yok.

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

**Sonuç:** kazanan MODERN WARRIOR (modelin verdiği olasılık %36.2); ilk seçim MODERN WARRIOR → TUTTU; ikili tutmadı.

## Gün içi robot (canlı oran + aynı akşam karne)

- `lab/at/canli.py` (`.github/workflows/at-canli.yml`, 11:00–00:30 TSİ her 30 dk; gece akışıyla aynı eşzamanlılık grubu, üst üste binmez). Yeniden eğitim yok: kayıtlı yayın modeli yüklenir, durum yalnız koşu gününden ÖNCEKİ sonuçlarla kurulur (sızıntısız; özellikler gece akışıyla birebir aynı, ölçüldü). Süre ≈10 sn.
- Ayna yarış günü gün içinde senkronlanıyor: programdaki atların güncel ganyan oranı (sabah 0) ve akşam sonuç dosyası. Alanın en az yarısında oran varsa `p_piyasa` (marjı ayrılmış) ve `p_oran` (gece ile aynı α/β harmanı) hesaplanır; oranı 0 olan at (genelde koşmayan) piyasa/harman dışında kalır.
- Sonucu gelen koşular aynı akşam `data/at/canli/<tarih>.json` içinde puanlanır; sabah kilitli tahminler `data/at/karne.json`'a koşu kimliğiyle idempotent eklenir (çift sayım yok, gün özeti yeniden hesaplanır).
- Son canlı dosya 2026-10-26 (güncelleme 2026-10-26 11:37 TSİ): 16 koşu, 16 oranlı bekleyen, 0 bitti; modelin (sabah) ilk seçimi 0/0 tuttu.

## Daha önce denenmiş ama kapıdan geçmemiş fikirler

- Benter'in ortak tahmini (log q'yu modelin içine sabit girdi olarak koyup birlikte eğitmek): harman diliminde piyasayı ≈0,009 log-loss iyileştirdi, fakat sınamada fark +0,0002 ± 0,003 (iyileşme yok) → dönem kayması işareti. Yayına alınmadı.
- Uzun-atış yanlılığı düzeltmesi (log q'ya ikinci derece terim): sınamada etkisiz (±0,001).

## Sınırlamalar ve riskler

- Veri yalnız 2025-01-01'den başlıyor: atların daha eski kariyerleri görünmüyor (ilk aylarda özellikler zayıf, ısınma ile kısmen çözüldü).
- Ayna lisanssız ve tek kişinin bakımında; kesilirse sistem son kopyayla çalışır, yeni sonuç gelmez.
- At adları kimlik olarak kullanılıyor (aynı adlı iki at nadir ama mümkün). Ekürili atlarda ganyan oranı ortaktır.
- v4'ten beri ölçüm iki zaman katında (A ≈4,5 ay, B ≈7 ay). Yine de deneylerdeki 0,001–0,003'lük farklar gürültü düzeyinde; katlar arasında işaret değiştiren sonuçlar (ör. üst kova kalibrasyonu) dönemsel dalgalanmadır. İlk seçim isabetinin standart hatası kat başına ≈ ±0,8–1,0 puan; "ilk seçim düşmemeli" kuralı bu yüzden bazı gerçek log-loss kazançlarını da eler (bilerek temkinli).
- GBM katmanı `lightgbm` paketine dayanır (iş akışı kurar). Kurulamazsa model doğrusal yedeğe düşer; gerekçeler yalnız doğrusal katmandan üretilir.
- Sabah kilitleri yalnız model olasılığıdır; piyasa harmanı için koşu öncesi oran gerekir (ayna gün içi oranları düzenli yayınlamıyor).
- Uygulamadaki üst özet kutusu `degerlendirme.metrik.harman` isabetini gösteriyor; sabah tahmininin kendi isabeti (yalnız model) daha düşüktür.

## Sonraki deneyler

1. Program arşivi uzadıkça form dizisi (2025 öncesi kariyer, gerçek ilk koşu bayrağı) — şimdiden +0,004 işareti var.
2. Koşu öncesi anlık oran (gün içi görüntüler düzenli gelirse) ile oran hareketi ve sabah→koşu öncesi harman.
3. Üst kova: izotonik/alan duyarlı kalibrasyon v4'te denendi, dışarıda tutmadı; katlar biriktikçe (≥3 kat) yeniden bakılacak.
4. Hız puanını kilo ve pist durumuyla düzeltip yeniden denemek; pedigri/idman verisi açık kaynakta bulunursa.
5. Patlatılmış amacı GBM'ye de uygulamak (v4'te sıra gelmedi: doğrusal derinlik 2 ancak tekrarda geçti).

## Zamanlama

`.github/workflows/at-lab.yml` her gün 05:23 ve 12:23 TSİ'de, ayrıca `lab/at/**` değişince veya elle çalışır (main dalı). Çıktılar yalnız `data/at/` ve `lab/at/RAPOR.md`'ye yazılır. Gece akışı 2 çekirdekte ≈5–6 dakika sürer (ablasyon haftada bir; ölçüldü: ablasyonlu tam akış 347 sn).

_Kaynak atfı: TJK verilerinin herkese açık aynası https://github.com/cenkozgur/tjk-data. Model ve olasılıklar BULUTOXX laboratuvarınındır._
