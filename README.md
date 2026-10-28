# OXXai

İlk yarı, ikinci yarı ve maç sonu net skor tahmini yapan, her gün kendini yeniden eğiten futbol ve basketbol tahmin uygulaması. Telefona uygulama gibi kurulur, ücretsiz GitHub Pages üzerinde çalışır ve hiçbir yapay zekâ servisine bağlı değildir.

## Nasıl çalışır

- **Uygulama** (`index.html` + `js/`, `css/` paketleri; yapı ve yeni katman kuralı: MIMARI.md → Uygulama dosya yapısı): Takımları yazınca ligi bulur, son 5 maçı doldurur ve tahmin üretir. İlk yarı, ikinci yarı ve maç sonu net skorunu, İY/MS, 1X2, alt/üst ve KG var/yok olasılıklarını verir. Oran girilirse değerli bahisleri işaretler.
- **Veri ve öğrenme motoru** (`scripts/update.py`): GitHub Actions bu betiği her saat :17'de çalıştırır (akıllı nöbet). Yeni maç sonucu geldiyse tam öğrenme yapar, gelmediyse aynı veriyle yeniden eğitmek bir şey katmayacağı için yalnızca oranları, fikstürü ve tahmin karnesini tazeler.
  1. 38 ligin (Avrupa'nın 22 ligi ile Brezilya, Arjantin, MLS, Meksika, Japonya, Çin ve diğerleri) bu ve geçen sezon sonuçlarını, ilk yarı skorlarını ve bahis oranlarını [football-data.co.uk](https://www.football-data.co.uk)'tan; Şampiyonlar Ligi, Avrupa Ligi ve Konferans Ligi maçlarını [TheSportsDB](https://www.thesportsdb.com)'den indirir. Farklı liglerden takımları karşılaştırmak için lig gücü katsayılarını kupa sonuçlarından öğrenir.
  2. Her maçı yalnızca o haftadan önceki maçlarla tahmin ederek geriye dönük test yapar.
  3. Test sonucuna göre model ayarlarını kendisi seçer: zaman ağırlığı, ortalamaya çekme, düşük skor düzeltmesi, form ağırlığı ve piyasa ağırlığı.
  4. Sonuçları `data/` klasörüne yazar ve siteyi yeniden yayınlar.
- **Basketbol motoru** (`scripts/basket.py`): NBA, EuroLeague, EuroCup, WNBA, NBL ve NCAA maçlarını çeyrek skorlarıyla indirir, her lig için hücum/savunma gücü modeli kurar, aynı kurallarla kendini test eder ve ayarlar.

## Çalışma prensibi (öğrenme kuralları)

Bu kurallar 2022-23'ten 2026-27'ye 53.000+ futbol ve 26.000+ basketbol maçıyla yapılan "3 ay önceden tahmin" deneyinden çıkarıldı:

1. **Geleceği görmeden test:** Her maç, yalnızca maçtan önceki verilerle eğitilmiş modelle tahmin edilir ve gerçek sonuçla karşılaştırılır. Kısa vade (1 hafta önce) ve uzun vade (3 ay önce) ayrı ayrı ölçülür.
2. **Ezber koruması:** Ayarlar maçların ilk %70'inde öğrenilir, son %30'unda doğrulanır. Son %30'da kötüleşen hiçbir değişiklik kabul edilmez; eski ayar korunur. (Deneyde 2024'te seçilen ayarların küçük liglerde 2025'te kötüleştiği görüldü, bu kural o yüzden var.)
3. **Bir yeteneğin kalıcı olması için en az iki farklı sezonda kazanç göstermesi gerekir.** Denenip elenenler: yaz arası güç küçültmesi, lige özel beraberlik ayarı, Elo karışımı (kazanç < 0,0005 log-kayıp).
4. **Kalıcı olanlar:** lige yeni gelen takım ön bilgisi (futbol: hücum 0,95 / savunma 1,05; tahmin kapsamı %90'dan %100'e), uzun vadede daha yavaş unutma (zaman ağırlığı 0,010; 3 sezonda da daha iyi), basketbolda lige göre öğrenilen yeni takım ön bilgisi.
5. **Yüksek oran kutusu:** Dört kural (en yüksek oran, akıllı sürpriz, geniş akıllı sürpriz, beraberlik avcısı) her güncellemede gerçek kapanış oranlarıyla yarışır; ilk %70'te seçilir, son %30'da doğrulanır. 2024-25'ten bugüne üç sezonda da hiçbir kural piyasayı yenmedi; en az kaybettiren beraberlik avcısıydı (%26 tutma, -%6/-%8), en yüksek oran kuralı -%12 kaybettirdi.
6. **Dürüst kıyas:** Model her zaman kapanış oranlarıyla (piyasa) karşılaştırılır. Uzun vadede piyasa hâlâ daha iyidir; oran girildiğinde uygulama ikisini birleştirir.

- **Öğrenme geçmişi** (`data/history.json`): Her güncellemenin isabet oranları burada tutulur. Uygulamadaki Motor sekmesi bunları öğrenme eğrisi olarak gösterir.

## Kurulum (bir kez, yaklaşık 5 dakika)

1. github.com'da ücretsiz hesap aç.
2. Yeni bir **public** depo oluştur, adı `KULLANICIADIN.github.io` olsun (böylece adres kısa olur).
3. Bu klasördeki her şeyi depoya yükle. Gizli `.github` klasörü de yüklenmeli.
4. Depoda **Settings → Pages → Build and deployment → Source: GitHub Actions** seç.
5. **Actions** sekmesinde "OXXai güncelle ve yayınla" iş akışını aç ve **Run workflow** ile ilk çalıştırmayı başlat.

Birkaç dakika sonra uygulama `https://KULLANICIADIN.github.io` adresinde yayında olur. OXXai'nin adresi: **https://bulutoxx.github.io**

## Telefona kurma

- **iPhone:** Adresi Safari'de aç → Paylaş → Ana Ekrana Ekle.
- **Android:** Adresi Chrome'da aç → menü (⋮) → Uygulamayı yükle veya Ana ekrana ekle.

## Notlar

- Kaydedilen tahminler ve sonuçlar her telefonda ayrı tutulur. Ortak model her gün herkes için güncellenir.
- Hiçbir model net skoru kesin bilemez. Motor sekmesi modelin gerçek isabetini gösterir.
- 18 yaş altına uygun değildir. Destek için: YEDAM 115.
