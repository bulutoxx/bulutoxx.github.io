# BULUTOXX

İlk yarı, ikinci yarı ve maç sonu net skor tahmini yapan, her gün kendini yeniden eğiten futbol tahmin uygulaması. Telefona uygulama gibi kurulur, ücretsiz GitHub Pages üzerinde çalışır ve hiçbir yapay zekâ servisine bağlı değildir.

## Nasıl çalışır

- **Uygulama** (`index.html`): Takımları yazınca ligi bulur, son 5 maçı doldurur ve tahmin üretir. İlk yarı, ikinci yarı ve maç sonu net skorunu, İY/MS, 1X2, alt/üst ve KG var/yok olasılıklarını verir. Oran girilirse değerli bahisleri işaretler.
- **Veri ve öğrenme motoru** (`scripts/update.py`): GitHub Actions bu betiği her gün 08:17, 15:17 ve 23:47'de (İstanbul saati) çalıştırır; pazartesileri ayarları baştan arar.
  1. 38 ligin (Avrupa'nın 22 ligi ile Brezilya, Arjantin, MLS, Meksika, Japonya, Çin ve diğerleri) bu ve geçen sezon sonuçlarını, ilk yarı skorlarını ve bahis oranlarını [football-data.co.uk](https://www.football-data.co.uk)'tan; Şampiyonlar Ligi, Avrupa Ligi ve Konferans Ligi maçlarını [TheSportsDB](https://www.thesportsdb.com)'den indirir. Farklı liglerden takımları karşılaştırmak için lig gücü katsayılarını kupa sonuçlarından öğrenir.
  2. Her maçı yalnızca o haftadan önceki maçlarla tahmin ederek geriye dönük test yapar.
  3. Test sonucuna göre model ayarlarını kendisi seçer: zaman ağırlığı, ortalamaya çekme, düşük skor düzeltmesi, form ağırlığı ve piyasa ağırlığı.
  4. Sonuçları `data/` klasörüne yazar ve siteyi yeniden yayınlar.
- **Öğrenme geçmişi** (`data/history.json`): Her güncellemenin isabet oranları burada tutulur. Uygulamadaki Motor sekmesi bunları öğrenme eğrisi olarak gösterir.

## Kurulum (bir kez, yaklaşık 5 dakika)

1. github.com'da ücretsiz hesap aç.
2. Yeni bir **public** depo oluştur, adı `bulutoxx` olsun.
3. Bu klasördeki her şeyi depoya yükle. Gizli `.github` klasörü de yüklenmeli.
4. Depoda **Settings → Pages → Build and deployment → Source: GitHub Actions** seç.
5. **Actions** sekmesinde "BULUTOXX güncelle ve yayınla" iş akışını aç ve **Run workflow** ile ilk çalıştırmayı başlat.

Birkaç dakika sonra uygulama `https://KULLANICIADIN.github.io/bulutoxx/` adresinde yayında olur.

## Telefona kurma

- **iPhone:** Adresi Safari'de aç → Paylaş → Ana Ekrana Ekle.
- **Android:** Adresi Chrome'da aç → menü (⋮) → Uygulamayı yükle veya Ana ekrana ekle.

## Notlar

- Kaydedilen tahminler ve sonuçlar her telefonda ayrı tutulur. Ortak model her gün herkes için güncellenir.
- Hiçbir model net skoru kesin bilemez. Motor sekmesi modelin gerçek isabetini gösterir.
- 18 yaş altına uygun değildir. Destek için: YEDAM 115.
