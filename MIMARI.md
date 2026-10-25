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
 football-data (eski sezonlar) ────────────▶🗄️ Derin arşiv     her gece (bir kez indirir)  derin/*
                                            🛟 Koruyucu        her gece                    changes, rollback
                                            🧹 Denetçi         her gece                    dq
                                            🎨 Kalite          her gece                    qa, qa/*.jpg
                                            💬 Sohbet koçu     her gece (kaliteden sonra)  bot_kb, bot_coach, bot_tests
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
   Maç öncesi ayarlar (calT keskinleştirme, gscale gol ölçeği, dk beraberlik payı) **uygulamanın gerçekten gösterdiği yolda**
   öğrenilir (`calibrate_served`, `params.cal_yol = "sunulan"`): power marj ayırma → gol beklentisi tablosu → iki yarı Dixon-Coles → T/dk.
   Amaç = oranlı maç payı × piyasa yolu + kalanı × model yolu; ilk %70 (+ derin arşiv) öğrenme, son %30 sınama; şu anki yapılandırmadan
   iyi değilse veya Altın isabetini düşürürse eski (model yolu) ayar kalır. Koruyucu `cal_yol`'u izler, geri almada dondurur.
3. **Seçicilik (pas geçme):** Güven %58'in altındaysa öneri verilmez ("⏸️ Pas"). Güçlü öneri %70+, Power Now canlı %80+.
   Az ama isabetli öneri, çok ama yarı yarıya öneriden iyidir.
4. **Dürüst ölçüm ve geri alma:** Her öneri maçtan önce kilitlenir, sonuçla puanlanır; koruyucu bozulan değişikliği geri alır.

## Veri sözleşmeleri (data/)

| Dosya | Üreten | Okuyan | İçerik |
|---|---|---|---|
| season.json | Motor | Motor, denetçi | Tüm liglerin maçları, oranlar, piyasa beklenen golü |
| model.json | Motor | Uygulama, koruyucu, bekçi | Ayarlar (`cal_yol`), geriye dönük test (`backtest.kalibrasyon.sunulan`: son %30 kimlik/eski/aday karşılaştırması), öneri kalibrasyonu, kupa gücü, `veritabani` (sezon/derin/arşiv büyüklüğü) |
| fixtures.json | Motor | Uygulama | Yaklaşan maçlar + iddaa oranları, MBS, yarışma adı |
| iddaa.json | Motor | Uygulama, canlı kayıt | Maç öncesi gol beklentisi (8 gün) |
| archive/GGGG-AA-GG.json | Toplayıcı | Motor, analist, araştırmacı, koruyucu, uygulama (son 30 gün) | Kilitli öneri + oran + sonuç (son 120 gün) |
| archive/eski/GGGG-AA-GG.json | Toplayıcı (`scripts/arsiv.py`) | Motor, analist, araştırmacı, koruyucu | 120 günden eski günler: yalnız puanlı kayıtlar, `lam` atılmış; bir kez yazılır, **silinmez** |
| derin/<lig>-<sezon>.json, derin/index.json | Derin arşiv (`lab/derin.py`) | Motor (`load_deep` → kalibrasyon) | football-data bitmiş eski sezonlar (son 5): `m` = [tarih, ev, dep, ev_gol, dep_gol, o1, oX, o2, o2.5üst, o2.5alt]; `tam: false` = ağ yokken season.json'dan geçici kopya |
| archive/live/*.json | Canlı kayıt | Toplayıcı | Kilitli canlı seçimler ve sonuçları |
| daily.json | Toplayıcı | Uygulama, koruyucu | Günlük karne, `veritabani` (arşiv gün/kayıt/puanlı), canlı kalibrasyon (`canli.bins`; `canli.platt` = zaman sıralı sınamayı geçerse `kabul: true` olan logit-doğrusal canlı kalibrasyon) |
| research.json | Araştırmacı | Motor, uygulama | Yeni ligler, kütüphane sürümü, marj yöntemi (power / prop / shin / hibrit: marj <%12 power, üstü oransal) |
| analyst.json | Analist | Uygulama | Lig güven katsayıları (doğrulanmışsa; ampirik Bayes küçültme), `teshis`: pazar ve oran bandına göre sapma |
| changes.json, rollback.json | Koruyucu | Motor, analist, uygulama | Değişiklik geçmişi, geri alma |
| dq.json | Denetçi | Uygulama | Veri bütünlüğü ve güvenlik taraması |
| qa.json, qa/*.jpg | Kalite | Uygulama | Düğme testi, açılış süresi, ekran görüntüleri |
| health.json | Bekçi | Uygulama | Nabız; gecikmede uyarı |
| auto_lab.json | Laboratuvar | Motor, uygulama | Açık kaynak modellerle yarış sonucu |
| arena.json | Robot arenası | Motor (konsey), uygulama | 5 robot + konsey: sezon sezon isabet, ağırlıklar, kabul edilen pazarlar (uygula) |
| gelisim.json | Koruyucu, sohbet koçu | Uygulama | Gelişim günlüğü: otomatik uygulanan gelişmeler, geri almalar, ölçümler, karneler |
| bot_kb.json | Sohbet koçu | Uygulama (Bulut, `bot-v70`) | Bulut'un bilgi bankası: takım takma adları/okunuşları (`takim`), lig adları (`lig`), eş anlamlılar (`esanlam`), yazım hataları (`yazim`), kalıp cümleler (`para`), terimler (`sozluk`), öne çıkan maçlar (`onemli`), `sayim` |
| bot_coach.json | Sohbet koçu | Uygulama (sohbet başlığı, Otonom ekip paneli) | Son gece: soru sayısı, niyet/faydalı %, önceki bankayla karşılaştırma, eklenenler, yayın kararı ve nedeni; `yayin` = yayındaki bankanın skoru; `gecmis` |
| bot_tests.json | Sohbet koçu | Sohbet koçu | Her gece büyüyen test soruları (veriye bağlı olanlar 21 gün sonra emekli olur); sabit 224 soru `lab/bot/suite.cjs`'te |

## 💬 Bulut'un kendini geliştirmesi (v70)

Bulut (sohbet asistanı) tamamen telefonda çalışır; yapay zekâ servisi ve sunucu yoktur. **Kullanıcının yazdıkları hiçbir zaman telefondan çıkmaz.**

1. **Gece koçu** (`lab/bot_coach.mjs`, otonom ekip iş akışında): yalnız uygulama verisinden (fikstür, lig adları, karne, uygulamanın kendi takım listesi)
   aday bilgi üretir, uygulamayı başsız tarayıcıda açıp Bulut'a soru sorarak her adayı sınar (aday olmadan yanlış, adayla doğru → kabul).
   Kabul edilen sorular test kümesine eklenir; küme her gün büyür (sabit 224 soru + üretilenler).
2. **Kapı (tek yönlü iyileşme):** dünkü banka ve yeni banka aynı sorularla çalıştırılır. Yeni banka yalnız niyet doğruluğu ve faydalı cevap oranı
   düşmüyorsa, dünkü bankanın doğru bildiği hiçbir soru yanlışa dönmüyorsa (iki kez sorularak doğrulanır) ve sayfa hatası yoksa yayınlanır.
   Gerileme varsa suçlu bilgi tek tek çıkarılarak aranır; yine geçmezse dünkü banka kalır. Kararın nedeni `bot_coach.json`'da yazar.
3. **Telefonda öğrenme** (`localStorage` "bx-bot70", ≤16 KB): anlaşılmayan mesajdan sonra dokunulan çip / yeniden yazılan cümle eşlenir,
   👍/👎 ile beğenilmeyen cevapta alternatif sunulur, "takımım …" ile favori takım hatırlanır. "ne öğrendin?" gösterir, "öğrendiklerini sıfırla" siler.
4. Sohbet başlığında "Bu gece X yeni şey öğrendim · test başarısı %Y" satırı `bot_coach.json`'dan gelir (yalnız ölçülmüş rakamlar).

Yerel deneme: `node lab/bot_coach.mjs --dry` (dosya yazmaz) · `node lab/bot_coach.mjs --eval` (yalnız test kümesi) ·
`BOT_COACH_TIME=2026-10-25T12:00:00+03:00` saati sabitler · `BOT_COACH_INDEX=<dosya>` başka bir index.html'i sınar.

## Yeni bot eklemek

1. `lab/<bot>.py` (veya `.mjs`) yaz: girdiyi `data/`'dan okusun, çıktıyı tek bir `data/<bot>.json`'a yazsın, hata verse bile sıfırdan farklı çıkmasın.
2. Uygulanacak bir değişiklik üretiyorsa: öğrenme/sınama ayrımı yap ve sonuca `kabul: true/false` koy; okuyan taraf yalnız `kabul` ise kullansın.
3. `.github/workflows/otonom-ekip.yml`'e bir adım ekle (veya kendi zamanlamasıyla yeni iş akışı); `git add` listesine çıktısını ekle.
4. Uygulamadaki Motor sayfasının "Otonom ekip" paneline bir satır ekle.
5. Koruyucu, `config()` içine eklenen her ayarı otomatik izler.

## Veri tabanı ve eğitim (ml70, 2026-10-25)

- **Hiçbir kilitli öneri silinmez.** Toplayıcı 120 günden eski arşiv günlerini `archive/eski/`'ye taşır (`scripts/arsiv.py`); tüm okuyucular
  (`arsiv.kayitlar`) iki katmanı birlikte okur. `predlog.json` 400 gün tutulur.
- **Derin arşiv:** gece botu football-data'nın bitmiş son 5 sezonunu bir kez indirir (≈50 bin maç); sonra yalnız eksik sezonu dener.
- **Eğitim:** saatlik motor yeni sonuç gelince tam öğrenir; kalibrasyon artık uygulamanın sunduğu yolda ve derin arşivle öğrenilir.
  Ölçüm (8.990 maç, Ocak–Ekim 2026, aylık yürüyen pencere, piyasa yolu): 1X2 log-loss 1,00220 → 1,00106; öneri Brier 0,23661 → 0,23611;
  %70+ öneri isabeti %74,2 → %75,9; Altın (≥%78, oran 1,20–2,00, günde ≤3) %76,1 → %77,9. Bedel: oransız (yalnız model) yolda 1X2 log-loss 1,0095 → 1,0104.
