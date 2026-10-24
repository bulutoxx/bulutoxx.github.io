# BULUTOXX mimarisi

Tamamen GitHub üzerinde, ücretsiz ve insan müdahalesi olmadan çalışan, kendini ölçüp geliştiren bir tahmin sistemi.
Hiçbir yapay zekâ servisine (Claude vb.) bağlı değildir; tüm botlar GitHub Actions'ta çalışan Python/Node betikleridir.

## Katmanlar

```
 Kaynaklar (ücretsiz, herkese açık)          Botlar (GitHub Actions)                     Çıktı (data/*.json)            Uygulama (GitHub Pages)
 ───────────────────────────────            ───────────────────────────                 ─────────────────────          ────────────────────────
 football-data.co.uk  ─┐                    🧠 Motor          her saat :17               season, model, fixtures        Bülten · Canlı · Power Now
 ESPN (lig + kupa)     ├──────────────────▶ 🗂️ Toplayıcı      her saat (motordan sonra)   archive/*, daily               Sonuçlar · Kupon · Motor
 iddaa.com (bülten,    │                    ⏱️ Canlı kayıt     15 dakikada bir             archive/live/*, health         (tarayıcı canlı skor ve
   canlı, sonuçlar)    │                    🛡️ Bekçi           15 dakikada bir             health                          canlı oranları doğrudan
 EuroLeague            ┘                    🔬 Araştırmacı     her gece 03:07 UTC          research                        iddaa'dan okur)
 PyPI (penaltyblog)  ──────────────────────▶📊 Analist         her gece                    analyst
                                            🛟 Koruyucu        her gece                    changes, rollback
                                            🧹 Denetçi         her gece                    dq
                                            🎨 Kalite          her gece                    qa, qa/*.jpg
                                            🧪 Laboratuvar     her pazar 02:41 UTC         auto_lab
                                            🤖 Robot arenası   her pazar (laboratuvarla)   arena
```

## Altın kurallar

1. **Kanıtsız değişiklik yok.** Her otomatik değişiklik önce eski veride öğrenilir, sonra hiç görmediği yeni veride sınanır
   (motor: son %30; laboratuvar: iki sezon; analist/araştırmacı: arşivin iki yarısı). Geçemeyen uygulanmaz.
2. **Uygulanan değişiklik izlenir.** Koruyucu, değişiklikten önceki ve sonraki 14 günün kilitli önerilerini karşılaştırır;
   isabet belirgin düşerse (Brier +0,01) 14 gün boyunca önceki yapılandırmaya döner.
3. **Tahminler maçtan önce kilitlenir.** Toplayıcı ve canlı kayıt, sonradan değiştirilemeyen kayıt tutar; tüm isabet raporları bu kayıtlardan gelir.
4. **Hata sistemi durdurmaz.** Her bot kendi adımında çalışır; biri hata verirse diğerleri ve yayın devam eder.
   Motor hatası `data/engine_error.txt`'e yazılır; sorunlar ve gelişmeler e-posta/bildirim yerine uygulama içinde gösterilir (Motor sayfası, ana ekran uyarısı, Gelişim günlüğü).
5. **Gizlilik ve lisans.** Depoya anahtar/şifre yazılmaz (denetçi her gün tarar); ham ücretli veri yayınlanmaz;
   açık kaynak bileşenler yalnız uygun lisanslı (penaltyblog: MIT) ve laboratuvarda yarıştırılarak kullanılır.
6. **Ücretsiz kalır.** Depo herkese açık olduğundan GitHub Actions ve Pages ücretsizdir; ücretli API gerekmez.

## Yanılma payını düşürme ilkeleri

Futbolda tek maçın sonucu doğası gereği belirsizdir; hiçbir model her maçı bilemez. Yanılma payı şu dört yolla düşük tutulur:

1. **Doğru referans:** Bahis piyasası en güçlü tek tahmincidir. Robot arenası her hafta beş bağımsız robotu
   (piyasa, Poisson, Elo, form, momentum) ve onları birleştiren öğrenen konseyi piyasaya karşı yarıştırır.
   İlk ölçümde (5.657 maç, iki sezon) konsey ağırlığın tamamını piyasaya verdi: diğer robotlar piyasaya bilgi eklemiyor.
   Sistem bu yüzden piyasa + kalibrasyon üzerine kuruludur. Konsey bir pazarda iki sezonda da piyasayı geçerse onay beklemeden devreye girer (scripts/konsey.py yaklaşan maçlara konsey olasılığını ekler); koruyucu sonrasını izler.
2. **Kalibrasyon:** Gösterilen yüzde, geçmişte o güvendeki önerilerin gerçek tutma oranına göre düzeltilir
   (maç öncesi: 9.000+ maç; canlı: kilitli canlı seçimler; lig bazında: analist).
3. **Seçicilik (pas geçme):** Güven %58'in altındaysa öneri verilmez ("⏸️ Pas"). Güçlü öneri %70+, Power Now canlı %80+.
   Az ama isabetli öneri, çok ama yarı yarıya öneriden iyidir.
4. **Dürüst ölçüm ve geri alma:** Her öneri maçtan önce kilitlenir, sonuçla puanlanır; koruyucu bozulan değişikliği geri alır.

## Veri sözleşmeleri (data/)

| Dosya | Üreten | Okuyan | İçerik |
|---|---|---|---|
| season.json | Motor | Motor, denetçi | Tüm liglerin maçları, oranlar, piyasa beklenen golü |
| model.json | Motor | Uygulama, koruyucu, bekçi | Ayarlar, geriye dönük test, öneri kalibrasyonu, kupa gücü |
| fixtures.json | Motor | Uygulama | Yaklaşan maçlar + iddaa oranları, MBS, yarışma adı |
| iddaa.json | Motor | Uygulama, canlı kayıt | Maç öncesi gol beklentisi (8 gün) |
| archive/GGGG-AA-GG.json | Toplayıcı | Motor, analist, araştırmacı, koruyucu | Kilitli öneri + oran + sonuç |
| archive/live/*.json | Canlı kayıt | Toplayıcı | Kilitli canlı seçimler ve sonuçları |
| daily.json | Toplayıcı | Uygulama | Günlük karne, canlı kalibrasyon |
| research.json | Araştırmacı | Motor, uygulama | Yeni ligler, kütüphane sürümü, marj yöntemi |
| analyst.json | Analist | Uygulama | Lig güven katsayıları (doğrulanmışsa) |
| changes.json, rollback.json | Koruyucu | Motor, analist, uygulama | Değişiklik geçmişi, geri alma |
| dq.json | Denetçi | Uygulama | Veri bütünlüğü ve güvenlik taraması |
| qa.json, qa/*.jpg | Kalite | Uygulama | Düğme testi, açılış süresi, ekran görüntüleri |
| health.json | Bekçi | Uygulama | Nabız; gecikmede uyarı |
| auto_lab.json | Laboratuvar | Motor, uygulama | Açık kaynak modellerle yarış sonucu |
| arena.json | Robot arenası | Motor (konsey), uygulama | 5 robot + konsey: sezon sezon isabet, ağırlıklar, kabul edilen pazarlar (uygula) |
| gelisim.json | Koruyucu | Uygulama | Gelişim günlüğü: otomatik uygulanan gelişmeler, geri almalar, ölçümler, karneler |

## Yeni bot eklemek

1. `lab/<bot>.py` (veya `.mjs`) yaz: girdiyi `data/`'dan okusun, çıktıyı tek bir `data/<bot>.json`'a yazsın, hata verse bile sıfırdan farklı çıkmasın.
2. Uygulanacak bir değişiklik üretiyorsa: öğrenme/sınama ayrımı yap ve sonuca `kabul: true/false` koy; okuyan taraf yalnız `kabul` ise kullansın.
3. `.github/workflows/otonom-ekip.yml`'e bir adım ekle (veya kendi zamanlamasıyla yeni iş akışı); `git add` listesine çıktısını ekle.
4. Uygulamadaki Motor sayfasının "Otonom ekip" paneline bir satır ekle.
5. Koruyucu, `config()` içine eklenen her ayarı otomatik izler.
