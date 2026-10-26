# BULUTOXX · At Yarışı bölümü: yeniden tasarım

_Araştırma, bilgi mimarisi ve uygulama yol haritası · 2026-10-26 · dal `r_tasarim`_
_Prototip: `lab/at/prototip.html` (tek dosya, dış kaynak yok, gerçek `data/at/` verisiyle çalışır)._
_Bu aşamada `index.html` ve `sw.js` değiştirilmedi._

> Kurallar her ekranda geçerli: tjk.org ve atyarisi.com'a istek atılmaz. Bahis sitesine bağlantı verilmez. Para tutarı ve olası kazanç gösterilmez. Logo ya da marka taklidi yapılmaz. Hobi amaçlı olasılıktır, garanti değildir · 18+.

---

## 0. Kısa özet

- **Ana sorun içerikte değil, düzende.** Bugünkü bölümde veri zengin ama koşu kartına ulaşmak için iki ekran kaydırmak gerekiyor. Hero, "Model ne kadar başarılı?" kutusu ve 7 paragraflık Padok Notu önce geliyor; sekmeler ancak ondan sonra başlıyor (`at_tasarim_shots/mevcut_02_at_tam_390.png`). Takipçinin en sık sorduğu iki soru, "sıradaki koşu ne zaman?" ve "bu koşuda kim önde?", ilk ekranda yanıt bulmuyor.
- **Yeni yapı:** At bölümünün içinde yapışkan bir üst sekme çubuğu: **Bugün · Program · Bahis · Sonuç · Kupon**. Bunun altında yığın (stack) mantığıyla açılan detay ekranları var: **Koşu kartı → At profili → Jokey/Antrenör profili**. Takip listesi ve İstatistik ekranlarına başlıktaki iki düğmeyle ulaşılır.
- **KUPO at bölümünün içine:** Ayrı bir kupon sistemi kurulmaz. **KUPO'nun "At Kuponu" verisi at bölümünde iki yerden görünür:** (1) "Kupon" sekmesi, (2) at bölümünün her ekranında, alt menünün üstünde yüzen **"At kuponum" çubuğu**. Aynı `bx-kuponlar` kaydı kullanılır, bu yüzden iki yerde de aynı kupon görünür. Futbol kuponları KUPO'da kalır.
- **Dürüst veri sınırı:** Meraklıların istediği alanların bir kısmı açık aynada yok: start/kulvar, handikap puanı, sahip, pedigri, idman/galop, AGF ve video. Bunlar uydurulmaz; arayüzde "henüz veri yok" kutusuyla açıkça yazılır. Oran hareketi ve at kariyer tablosu ise **kendi verimizden türetilebilir** (bkz. §6).

---

## 1. Araştırma bulguları

### 1.1 İncelenen ürünler (kaynaklar)

| Ürün | Öne çıkan özellik | Kullanıcı şikâyeti / isteği | Kaynak |
|---|---|---|---|
| TJK Mobil / eBayi (TR, resmî) | Program, sonuç, muhtemeller, Mobil TV, kupon durumu, bayi bulucu, kayıtlı kuponlar | 3,5/5 (270 oy). Video sonrası geri/kapat düğmesi kayboluyor; "oyna"ya basınca ana ekrana atıyor; 5'li/4'lü ganyan için sekmeli gezinme isteniyor; uzun oturumda ekran bozuluyor | [App Store TR](https://apps.apple.com/tr/app/tjk-mobil/id735255624?l=tr) |
| AGF sayfaları (Sporx vb.) | Altılı ayak ayak "N. ayak (K. koşu)" düzeni; atlar AGF yüzdesiyle büyükten küçüğe; hipodrom filtresi; muhtemeller, hazır kuponlar, sonuçlar bağlantıları | Sütun başlıkları yazılmıyor; veri gelmemiş ayaklar "%0,00" görünüyor (boş durum yok) | [sporx.com/at-yarisi-agf](https://www.sporx.com/at-yarisi-agf) |
| Liderform (TR) | Uzman tahmini, günlük program ve performans tabloları, **galop verisi** (muhabir gözlemi), tüyolar, at/jokey takibi ve bildirim, "İç-Dış" ve "Çaba" filtreleri, kupon oluşturucu | 3,3/5 (6 oy); yorum metni az | [mwm.ai/liderform](https://mwm.ai/apps/liderform/1380650135) |
| Ganyan Defteri (TR) | Program, altılı önerileri, **takip listesi + özel notlar**, tahmin başarı istatistiği, açık/koyu tema | Az oy | [mwm.ai/ganyan-defteri](https://mwm.ai/it/apps/ganyan-defteri/6756010556) |
| Zeki Beygir (TR) | Bugün/yarın/sonraki gün programı, at detayı, yapay zekâ ile derece tahmini, puan analizi, koşu yorumu; bahis sunmuyor | Az oy | [mwm.ai/zeki-beygir](https://mwm.ai/it/apps/zeki-beygir/6778079754) |
| Racing Post (UK) | Ana sayfa + Yarış + Haber; yarış ekranı hipodroma ya da saate göre sıralanır, düz/engelli filtresi var; yapay zekâ puanlı "Smart View" koşu kartı | Kişiselleştirme sınırlı | [racingpost.com/news](https://racingpost.com/news/welcome-to-the-new-racing-post-app-aO6oH2K41kjn) |
| Horse Racing Tracker (UK) | At, jokey ve antrenör takibi; bildirim **at deklare edilince, yarıştan ~1 saat önce ve sonuçta**; parkur/mesafe/oran filtresi; at+jokey birleşik istatistik | Premium erişim sorunları | [App Store](https://apps.apple.com/us/app/id642052714) |
| Timeform (UK) | Her ata puan (rating) ve **bayrak (flag)**, tempo haritası, tam performans geçmişi, bahis ipuçları | Ücretli | [Sporting Life](https://www.sportinglife.com/racing/news/ultimate-form-guide-for-only-pound30/192190) |
| Equibase (ABD) | Bugün/yarın programı, sabah oranı, **koşmayan at ve değişiklik uyarısı**, idman raporları, Virtual Stable (at takibi), bahis hesaplayıcı | 3,3/5. Küçük ve soluk yazı; tarih seçmek için kaydırmak gerekiyor; hesaplayıcıda numara girmek zor; Virtual Stable uygulama dışına atıyor; sonuç geçmişi yalnız ~1 hafta | [App Store](https://apps.apple.com/us/app/id453573402) |
| Punters (AU) | Form rehberi, **speed map**, seksiyonel süreler, koşmayan at güncellemesi, Blackbook (at/jokey/antrenör takibi), yapay zekâ tahmincisi | **Koşular arasında geçerken ana sayfaya atıyor**; geçmiş bahisleri izleme aracı isteniyor; "3. koşusu" istatistiği isteniyor; tüm hipodromlarda değişkenle arama isteniyor | [App Store AU](https://apps.apple.com/au/app/punters-horse-racing-form/id916114449) |
| Racenet (AU) | Form rehberi, seksiyonel, Blackbook | Uygulamada **at arama yok**; Blackbook senkronu bozuk | [App Store AU](https://apps.apple.com/au/app/racenet-horse-racing-form/id708806967) |
| TwinSpires (ABD) | Bahis, canlı video, handikap bilgisi, tekrar izleme | Bahis odaklı (BULUTOXX için uygun değil) | [Brisnet](https://www.brisnet.com/racing/news/twinspires-com-unveils-new-iphone-app) |
| Form rehberi okuma | Start/barrier, kilo, pedigri, kariyer, pist/mesafe/zemin uygunluğu, ara verme süresi, son 3 koşu, speed map, seksiyonel | — | [GoBet](https://www.gobet.com.au/betting-sites/faq/how-do-i-read-the-horse-racing-form-guide/) |

Not: Mağaza yorum örneklemleri küçük ve çoğu 2019–2023 tarihli. Bu bulgular eğilim gösterir, kesin sonuç değildir. Ekşi Sözlük'teki "hipodrom" başlığı çoğunlukla 2000'lerin başından ve deneyim/nostalji odaklı; uygulama isteği çıkmadı ([eksisozluk.com/hipodrom--48072](https://eksisozluk.com/hipodrom--48072)).

### 1.2 En önemli 10 bulgu

1. **"Sıradaki koşu" ilk bakışta görünmeli.** Program saate ya da hipodroma göre sıralanmalı (Racing Post). Bizde ilk ekranda yok.
2. **Koşudan koşuya geçerken bağlam kaybolmamalı.** Punters ve TJK yorumlarındaki en sık şikâyet: geçişte ana sayfaya atılmak. Koşu kartının üstünde 1…N koşu çipleri olmalı.
3. **Takip listesi (Blackbook / Virtual Stable / Tracker) temel beklenti.** Takip edilen şeyler at, jokey ve antrenördür. Bildirim üç anda gelir: programa girdiğinde, koşudan önce ve sonuçta. Bizde yalnız at takibi var, ayrı bir ekranı yok.
4. **İki ayrı kullanıcı var:** sade bilgi isteyen başlangıç düzeyi (Racing Post "Smart View") ve tüm sütunları isteyen handikapçı (Timeform, Punters). Tek bir görünüm ikisini de memnun etmiyor; **Sade/Meraklı geçişi** gerekiyor.
5. **Türkiye'ye özgü üç kavram:** AGF, 6'lı ayak düzeni ("N. ayak (K. koşu)") ve galop. 6'lı ayak düzeni bizde var. AGF ve galop verisi açık kaynakta yok.
6. **Değişiklik ve koşmayan at uyarısı** (Equibase, Punters) güven veriyor. Açık arşivde `nonRunner` alanı ve `ekuriGroups` var; kullanılabilir.
7. **Okunabilirlik şikâyeti yaygın** (Equibase: küçük/soluk yazı; TJK: üst üste binen yazı). 44 px dokunma alanı, ≥13 px gövde yazısı ve AA kontrast zorunlu.
8. **Geçmiş kupon/bahis karnesi isteniyor** (Punters). Bizde `kupon_karne.json` (geri test) ve `altili_karne.json` var. Bu dürüst karne bir fark yaratır.
9. **Sonuç geçmişi kısa tutulunca şikâyet geliyor** (Equibase: ~1 hafta). Bizde gün seçici var ama yalnız dosyası olan günleri gösteriyor.
10. **Arama eksikliği** (Racenet). At ya da jokey adıyla arama meraklının sık yaptığı iş. Bugünkü veride yapılabilir; geçmiş için laboratuvarın küçük bir dizin dosyası üretmesi gerekir (Aşama 3).

### 1.3 Mevcut BULUTOXX at bölümü: denetim

| Öğe | Durum | Sorun |
|---|---|---|
| Hero + DENEME + "Model ne kadar başarılı?" | Her açılışta en üstte | Dikeyde ~370 px yer kaplıyor; tekrar gelen kullanıcıya yeni bir şey söylemiyor |
| Padok Notu | 6–8 paragraf | Değerli ama koşu listesinin önünde duruyor ve alt menünün altında kalıyor (mevcut_01) |
| Sekmeler (Tahmin/Altın/Sonuç/6'lı/Jokey) | Padok'un altında | İlk ekranda görünmüyor; "Tahmin" sekmesinde bitmemiş koşu kalmadıysa yalnız tek satırlık boş mesaj var |
| Koşu kartı `race()` | İlk 4 at + "Tüm atlar" | Jokey adı, kilo ve form tek satırda sıkışıyor; aynı koşunun meraklı sütunları yok; koşular arasında hızlı geçiş yok |
| At penceresi `horseSheet` | Modal | Jokey ve antrenöre bağlantı yok; son 3 koşu var ama pist/mesafe uygunluğu yorumlanmıyor |
| KUPO at kuponu `atkupon-v98` | Güçlü (8 tür, Harville, ekürili, karne) | Kurucu at bölümünden açılıyor ama kupon KUPO'da yaşıyor; kullanıcı at ekranından ayrılınca kuponunu göremiyor |
| Takip (⭐) | Yalnız at, `bx-at-fav` | Ayrı bir ekranı yok; jokey ve antrenör takip edilemiyor |

---

## 2. Personalar ve temel görevler

| Persona | Kim | En sık 5 görev | Başarı ölçütü |
|---|---|---|---|
| **Başlangıç: "Merak eden"** | Arkadaş grubunda altılıya ortak olan, ayda birkaç kez bakan | 1) Bugün nerede yarış var? 2) Bu koşuda kim önde? 3) Altın at hangisi? 4) Kazandı mı? 5) Arkadaşla paylaş | Tek dokunuşta "kim önde"; terimler açıklamalı |
| **Düzenli takipçi** | Haftada birkaç gün, sabah ve akşam bakan | 1) Sıradaki koşu ve geri sayım 2) Takip ettiğim at ya da jokey bugün koşuyor mu? 3) 6'lı ayakları ve durumu 4) Sonuçlar ve modelin karnesi 5) Kuponuma ekle ve izle | Ana ekranda 3 saniyede sıradaki koşu ve takip; kupon at ekranından kopmadan |
| **Uzman / handikapçı** | Her gün, programı satır satır okuyan | 1) Meraklı koşu kartı (kilo, yaş, form, antrenör, son koşular, pist/mesafe uyumu) 2) Model ile piyasa farkı (değer arama) 3) Jokey/antrenör formu ve uyumu 4) İkili, sıralı, üçlü, çifte kombinasyon olasılıkları 5) Geri test karnesi (model gerçekten kalibre mi?) | Bütün sütunlar tek ekranda; sıralama; kombinasyon olasılığı anında; dürüst karne |

---

## 3. İhtiyaç → mevcut durum → veri karşılığı

Açıklama: ✅ var · 🟡 kısmen · ❌ yok. "Veri" sütunu: **Var** (mevcut dosyamızda) · **Türetilebilir** (açık aynadan ya da kendi zaman serimizden laboratuvarda üretilebilir) · **Yok** (açık kaynakta yok; uydurulmaz).

| # | İhtiyaç | BULUTOXX bugün | Veri karşılığı |
|---|---|---|---|
| 1 | Günün programı, hipodromlar, saatler | ✅ | **Var**: `tahmin/<gün>.json` (hipodrom, koşu, saat, mesafe, pist, sınıf) |
| 2 | Yarın ve dün | 🟡 (dosyası olan günler) | **Var**: gün dosyaları; yarının programı aynanın `data/daily`'sine düşünce |
| 3 | Sıradaki koşu geri sayımı | ❌ | **Var**: saat alanı + `canli.durum` |
| 4 | Koşu kartı: at, no, jokey, antrenör, kilo, yaş | 🟡 (antrenör yalnız modalda) | **Var**: `canli/<gün>.json` atlar[] |
| 5 | Son 6 koşu dereceleri (form) | 🟡 (metin olarak) | **Var**: `form` (örn. "737004") |
| 6 | Son koşuların ayrıntısı (tarih, hipodrom, mesafe, pist, derece) | 🟡 (son 3, modalda) | **Var**: `son3[]`; daha uzun geçmiş **Türetilebilir** (aynanın `memory/horses.json`'ı: `recentForm`, `trackStats`, `distanceStats`, `venueStats`, `classStats`, `jockeyCompatibility`) |
| 7 | Pist/mesafe uygunluğu | ❌ | **Türetilebilir**: `son3` ile kaba hâli hemen; tam tablo `memory/horses.json`'dan |
| 8 | Start/kulvar (barrier) | ❌ | **Yok**: aynada alan yok (`no` yalnız at numarası) |
| 9 | Handikap puanı (HP) | ❌ | **Yok**: aynada alan yok; laboratuvarın "HP vekili" iç özelliktir, gösterilecek bir puan değil |
| 10 | Sahip, yetiştirici, pedigri (baba/anne) | ❌ | **Yok** |
| 11 | İdman/galop | ❌ | **Yok**: `arastirma.json` ve RAPOR.md §İdman, 0 açık lisanslı aday |
| 12 | Ganyan oranı ve piyasa olasılığı | ✅ | **Var**: `oran`, `p_piyasa`, `p_oran` |
| 13 | Oran hareketi (sabahtan koşuya grafik) | ❌ | **Türetilebilir**: `canli.py` zaten 30 dakikada bir oran okuyor; her okumada `oran_izi:[[saat, oran],…]` (son 12 nokta) eklenmesi yeterli. Aynanın `odds-snapshots` klasörü README'de anılıyor ama şu an erişilemiyor (404) |
| 14 | AGF (altılı ganyan favori yüzdeleri) | ❌ | **Yok**: açık aynada yok. Gayriresmî TJK API paketleri (ör. `bilaleren/tjk-api`) TJK'ya istek atar, kuralımıza aykırı. Vekil olarak "piyasa %" (ganyan oranından) kullanılır ve **AGF diye adlandırılmaz** |
| 15 | Favori ve sürpriz | 🟡 (Padok'ta "en açık koşu") | **Var**: olasılık dağılımı, model ile piyasa farkı |
| 16 | Altın atlar | ✅ | **Var** |
| 17 | 6'lı ganyan (ayaklar, banko, kapsam, durum) | ✅ | **Var**: `altili/<gün>.json`, `altili_karne.json` |
| 18 | Diğer türler: ikili, sıralı ikili, çifte, üçlü, tabela, plase | ✅ (KUPO kurucusunda) | **Var**: Harville γ/δ + `kupon_karne.json` |
| 19 | 5'li/4'lü/3'lü ganyan | ❌ | **Türetilebilir**: 6'lı motoru N ayakla aynı mantıkta çalışır; `isGanyanStart` bayrağı aynada var |
| 20 | Sonuç ve dereceler (1–4), ganyan oranı | ✅ | **Var**: `canli.sonuc.sira`, `ganyan`; derece süresi (`finishTime`) aynada var, dosyamıza eklenebilir |
| 21 | Fotofiniş, mesafe farkı (boy) | ❌ | **Yok**: aynada yalnız bitiş süresi var; süre farkı **Türetilebilir** |
| 22 | Koşmayan at ve eküri | 🟡 (eküri kurucuda) | **Var/Türetilebilir**: `nonRunner`, `ekuriGroups` |
| 23 | Pist durumu ve hava | ❌ | **Türetilebilir**: aynanın `daily`'sinde `trackCondition`, `weatherCondition`, `temperature` |
| 24 | At profili | 🟡 (modal) | **Var** + **Türetilebilir** (bkz. 6–7) |
| 25 | Jokey profili ve istatistikleri | 🟡 (sıralama listesi) | **Var**: `jokeyler.json` (90 gün, katkı, uzmanlık, bugünkü binişler) |
| 26 | Antrenör profili | 🟡 | **Var**: `jokeyler.json.antrenorler`; bugünkü atlar `canli`'dan |
| 27 | Jokey–antrenör uyumu | ✅ (liste) | **Var**: `ikililer` |
| 28 | Takip listesi (at, jokey, antrenör) | 🟡 (yalnız at) | **Var**: yerel depolama |
| 29 | "Atım koşuyor" bildirimi | ❌ | **Türetilebilir**: istemcide, uygulama açıkken yerel bildirim yapılabilir; kapalıyken push için sunucu ya da GitHub Actions + Web Push anahtarı gerekir |
| 30 | Kupon kurma | ✅ (KUPO) | **Var** |
| 31 | Geçmiş karne (OXX ve kupon) | ✅ (dağınık) | **Var**: `karne.json`, `kupon_karne.json`, `altili_karne.json`, `replay.json` |
| 32 | Canlı yayın ve tekrar | ❌ | **Yok** (ve TJK yayınına bağlantı verilmez) |
| 33 | At ya da jokey arama | ❌ | Bugün için **Var**; geçmiş için **Türetilebilir** (küçük bir dizin dosyası) |
| 34 | Haber ve uzman yorumu | ❌ | **Yok** (kapsam dışı; Padok Notu kendi yorumumuzdur) |

---

## 4. Bilgi mimarisi

```
At (spor seçicideki 🐎)
├─ [yapışkan üst çubuk]  Başlık "At Yarışı" + alt satır (gün · hipodrom · koşu sayısı)
│                        Sağda: 📊 İstatistik   ⭐ Takip
├─ Sekmeler: Bugün │ Program │ Bahis │ Sonuç │ Kupon(•n)
│
├─ Bugün            ← varsayılan
│   ├─ Gün çipleri (Dün · Bugün · Yarın; yalnız verisi olanlar)
│   ├─ Sıradaki koşu kartı (geri sayım, durum, ilk 3 at) → Koşu kartı
│   ├─ ⭐ Takip ettiklerin koşuyor (varsa)
│   ├─ 🥇 Günün altın atları (yatay kaydırmalı kartlar) → At profili
│   ├─ 📋 Padok Notu (ilk 3 madde + "Devamını oku")
│   └─ Hipodromlar (koşu sayısı, saat aralığı, biten/kalan, 6'lı var) → Program
├─ Program
│   ├─ Gün çipleri · Hipodrom çipleri
│   └─ Koşu satırları (no+saat · en olası at ya da 🏁 kazanan · mesafe/pist/sınıf/at sayısı/6'lı ayağı · durum)
├─ Bahis
│   ├─ 6'lı Ganyan (Dar/Orta/Geniş · ayaklar · banko · durum · "kuponuma ekle")
│   └─ Tüm türler (kural + geri test karnesi + "koşu seç → kupon kur")
├─ Sonuç
│   ├─ Gün özeti (biten/toplam, ilk seçim isabeti, uzun dönem karşılaştırma)
│   ├─ Hipodrom hipodrom biten koşular (ilk 3, ganyan oranı, model ✓/✗) → Koşu kartı
│   └─ 6'lı durumu
└─ Kupon   (= KUPO "At Kuponu", aynı veri)
    ├─ Eşleşme bilgisi ("Bu liste KUPO'daki At Kuponu ile aynıdır")
    ├─ Satırlar (tür · koşu · seçim · kombinasyon · olasılık · durum · sil) · KUPO'da aç
    ├─ OXX'un at kuponları (altın ganyan, ikili önerileri, 6'lı Orta) → kopyala
    └─ OXX karnesi (geri test: gerçekleşen ve beklenen)

Detaylar (yığın; başlıkta "‹ Geri"; donanım/tarayıcı geri tuşu çalışır):
  Koşu kartı  #/kosu/<id>     → At profili  #/at/<id>/<no> → Jokey #/jokey/<ad> · Antrenör #/antrenor/<ad>
  Takip       #/takip         İstatistik  #/istatistik

Her ekranda yüzen "At kuponum" çubuğu (kupon boş değilse ve Kupon sekmesinde değilken) → Kupon
```

**Gezinme kuralları**
- Uygulamanın alt menüsü (Canlı · Bülten · POWER NOW · Sonuçlar · Menü) aynen kalır. At bölümünün kendi gezinmesi **üstte**, yapışkan bölümlü kontroldür (segmented control). Böylece iki alt çubuk üst üste binmez.
- Detay ekranları hash yoluyla açılır: Android geri tuşu ve iOS kaydırarak geri dönme çalışır, derin bağlantı paylaşılabilir (`#at/kosu/...`). Bugünkü modal `horseSheet` yerine yığın ekranı gelir; modal yalnız kupon kurucuda kalır, çünkü kurucu bir "görev".
- Koşu kartındaki **1…N koşu çipleri** aynı hipodromda koşular arasında geri gitmeden geçiş sağlar (Punters şikâyetine çözüm).
- Sekme, gün, hipodrom, Sade/Meraklı ve 6'lı kapsamı seçimleri yerel depolamada hatırlanır.

---

## 5. Ekran ekran tasarım kararları

Görsel dil, `apple-v94` ve `kuponum-v95` ile aynıdır: koyu lacivert yüzey katmanları (`--s0…--s4`), sistem fontu, tip ölçeği 30/22/19/17/15/13/12/11, kart köşesi 20, grup köşesi 16, en az 44 px dokunma alanı. Altın yalnız üç yerde kullanılır: (a) en olası at ve Altın at, (b) kupon seçimi ve "At kuponum" çubuğu, (c) "Tuttu" vurgusu. Mavi degrade birincil eylem (kupona ekle), camgöbeği bağlantı ve "oranla güncel" durumudur.

### 5.1 Bugün (`01_bugun`, `01b_bugun_altin_padok`, `16_bugun_takipli`)
- **Hero kaldırılır.** "DENEME" rozeti ve model başarısı İstatistik ekranına taşınır; üst çubuktaki 📊 düğmesi oraya götürür. İlk ekranda yer açılır.
- **Sıradaki koşu kartı:** Büyük altın geri sayım (sa/dk), hipodrom · koşu · saat, mesafe/pist/sınıf/at sayısı, ilk 3 at (numara rozeti ve olasılıkla). Bütün kart tek dokunma hedefidir ve koşu kartını açar. Gün bittiyse "koşular tamamlandı → Sonuçlar" boş durumu gösterilir.
- **Takip ettiklerin koşuyor:** Takip listesinde koşan bir at, jokey ya da antrenör varsa görünür (bulgu 3).
- **Altın atlar:** Yatay kaydırmalı, yaslanan (snap) kartlar. Büyük olasılık, sonuç rozeti (✓ kazandı / ✗ / saat). Kural metni kartların altında tek satır.
- **Padok Notu:** İlk 3 madde (program ilerlemesi, piyasa sinyali, en açık koşu) gösterilir, gerisi "Devamını oku" ile açılır (`<details>`). İçerik bugünkü `padok()` işlevinin aynısı, yalnız sıralanmış ve kısaltılmış.
- **Hipodromlar:** Biten/kalan koşu sayısı ve "6'lı var" ipucu; dokununca Program o hipodromla açılır.

### 5.2 Program (`02_program`)
- Gün çipleri ve hipodrom çipleri (koşu sayısıyla). Satır şunları gösterir: **koşu no + saat** (sol sütun), **en olası at + olasılık** ya da bittiyse **🏁 kazanan**, mesafe · pist · sınıf · at sayısı · **6'lı ayağı**, sağda durum hapı (Sabah tahmini / Oranla güncel / Sonuç bekleniyor / ✓ ✗ Bitti).
- Altın at noktası (●) ve takipteki at yıldızı (★). Altında kısa bir açıklama satırı (lejant).
- Biten koşular soluklaştırılır ama listede kalır. Bugünkü "Biten koşular" katlanır bölümü kalkar; sıra saate göre ilerler.

### 5.3 Koşu kartı (`03_kosu_sade`, `04_kosu_merakli`, `04b_…alt`, `05_kosu_sonuclu`)
- Üstte **koşu çipleri 1…N** (aria-current), büyük başlık "Hipodrom · N. Koşu", meta hapları (saat, mesafe, pist, sınıf, at sayısı, durum).
- Koşu bittiyse en üstte **🏁 Sonuç kartı** yer alır: 1–4 derece, ganyan oranı, modelin ilk seçimi ✓/✗, koşan at sayısı.
- **Sade ⇄ Meraklı** geçişi kalıcıdır:
  - **Sade:** "Kim kazanır?" İlk 3 at büyük kartlarda: olasılık, ilk 3'e girme, jokey ve kilo, **tek cümlelik "neden"** (modelin `gerekce` alanı + formdan, pist uyumundan, piyasadan üretilen ek). Ardından kalan atlar sade satırlarda; altta sabahın ikili önerisi.
  - **Meraklı:** Sıralama düğmeleri (Olasılık · No · Ganyan · Kilo). Her at için: no, ad, yaş · kilo · jokey; **form çipleri** (1 altın, 2–3 yeşil, 0 soluk; "0 = ilk 9 dışı"); antrenör; dört mini gösterge: **model sabah %**, **piyasa %**, **piyasa farkı ▲/▼ puan** (değer arayanlar için), **pist uyumu** (son 3 koşudan kaçı aynı pistte). Altta lejant ve "Henüz veri yok" kutusu (start, HP, sahip, pedigri, idman, AGF, oran grafiği).
- Alt eylemler: **＋ Kupona ekle** (kupon kurucu alt sayfası) ve **Paylaş**. Koşu başladıysa eylem yerine "Koşu başladı; kupona eklenemez".

### 5.4 At profili (`06_at_profil`)
- Büyük numara rozeti + ad, koşu bağlamı; haplar: yaş, kilo, "N. favori", durum.
- 4 gösterge: kazanma (oranla/sabah), ilk 3, piyasa %, ganyan oranı; altında "neden" cümlesi.
- **Form:** son 6 çip + son 3 koşu listesi ("aynı pist", "benzer mesafe" etiketleri).
- **Ekip:** Jokey ve Antrenör satırları, 90 günlük kazanma ve katkı; ilgili profile gider.
- Eylemler: ☆ Takip et · ＋ Kupona (kurucu bu at seçili açılır).
- Bilgi kutusu: kariyer tablosu Aşama 3'te; pedigri, sahip ve idman yok.

### 5.5 Jokey / Antrenör profili (`07_jokey_profil`)
- Ad, rol hapı, sıralama ("N. sırada"), form eğilimi (📈/📉/➖).
- 4 gösterge: 90 günde biniş/koşu, kazanma, ilk 3, **katkı puanı** (açıklamasıyla: atın gücünden arındırılmış). Uzmanlık: pist, mesafe, hipodrom.
- Seçili günün binişleri/atları: dokununca at profili açılır. Takip et.
- Sıralamaya girmeyen isim için dürüst boş durum ("az koşu").

### 5.6 Sonuç (`08_sonuc`)
- Gün özeti: biten/toplam, ilk seçim kazandı, günlük isabet. Kilitli karne ve uzun dönem karşılaştırması: sabah modeli, oranla harman, ganyan favorisi.
- Hipodrom başlıkları altında, **en yeni koşu üstte**: ilk 3 (kazanan yeşil rozet), ganyan oranı, model ✓/✗ hapı, modelin ilk seçimi ve kazananın sabah olasılığı. Kart koşu kartına gider.
- 6'lı durumu: Tuttu / Tutmadı / Kupon düştü / N/6 ayakta.

### 5.7 Bahis (`09_bahis_altili`, `10_bahis_turler`)
- **6'lı Ganyan:** Kapsam çipleri Dar ≤64 / Orta ≤192 / Geniş ≤576. Kart: 6'yı birden tutma olasılığı, kombinasyon, banko ayak sayısı. Ayak satırları sırayla: "N. ayak · K. koşu · saat" (yerel AGF sayfası alışkanlığı), seçilen atlar (kazanan yeşil), ayak olasılığı ya da "banko". Tutan ayak yeşil, düşen ayak kırmızı. "＋ Bu 6'lıyı kuponuma ekle". Altta geri test karnesi.
- **Tüm türler:** Ganyan, Plase, İkili, Sıralı İkili, Çifte, Sıralı Üçlü, Tabela, 6'lı. Her biri için tek cümlelik kural (`kupon_karne.json.turler[].kural`, "Varsayım" kısmı kırpılır) ve **karne çubuğu**: gerçekleşen isabet (altın çubuk) ile modelin beklediği (camgöbeği çizgi). Kutu (virgüllü) seviyeleri de gösterilir. Eylem: "Koşu seç → kupon kur".
- Aşama 3: 5'li, 4'lü ve 3'lü ganyan aynı ayak bileşeniyle eklenir (TJK yorumundaki istek).

### 5.8 Kupon kurucu (`11_kupon_kurucu`)
- Alt sayfa (bottom sheet), `role="dialog"`, Esc ve arka plana dokunma ile kapanır. Üstte tür çipleri; açıklama satırı; her at için sütun düğmeleri (Seç ya da 1./2./3.). Çiftede ikinci koşunun listesi altta gelir.
- Altta yapışkan özet: **kombinasyon** ve **tutma olasılığı** (indirimli Harville γ/δ, `kupon_karne.json.harville`). Birincil eylem "At kuponuma ekle".
- Gerçek uygulamada bu sayfa **`atkupon-v98` içindeki `openB()` kurucusunun kendisidir**; prototip onun sadeleştirilmiş taslağıdır. Ekürili ve plase kuralları v98'de zaten doğru.

### 5.9 Kupon = KUPO "At Kuponu" (`12_kupon_cubugu`, `13_kuponum`, `18_kupon_bos`)
- **Eşleşme bilgisi** (camgöbeği şerit): "Bu liste KUPO'daki At Kuponu ile aynıdır."
- Satırlar: tür etiketi, koşu, seçim, kombinasyon, tutma olasılığı, durum (bekliyor / ✓ tuttu / ✗ tutmadı), sil. Birden çok satır varsa birlikte tutma olasılığı ve toplam kombinasyon. "KUPO'da aç" ve "Temizle".
- **OXX'un at kuponları:** altın ganyanlar, kalan koşuların ikili önerileri, 6'lı Orta. ＋ ile kopyalanır (aynı koşu ve türde eski satırın yerini alır; v98 kuralı).
- **OXX karnesi:** her tür için geri test isabeti ile beklenti.
- **Yüzen "At kuponum" çubuğu:** alt menünün 10 px üstünde, altın kenarlı cam kart: "At kuponum · N satır · K kombinasyon · M bekliyor · KUPO ile eşli" + "Aç". Kupon sekmesindeyken gizlenir. Boşken hiç görünmez.

### 5.10 Takip ve İstatistik (`14_takip`, `15_istatistik`)
- Takip: Atlar, Jokeyler, Antrenörler. Bugün koşuyorsa bağlam ve durum hapı, yoksa "Bu gün programda yok". Çıkarma düğmesi. Bildirim kartı: "Aşama 4" rozeti ve gerekçesi.
- İstatistik: model başarısı (sabah, harman, favori) + dürüst açıklama; jokey ve antrenör sıralaması (katkı çubuğu); uyumlu ikililer.

### 5.11 Durumlar
- **Yükleniyor:** iskelet kartlar (shimmer; `prefers-reduced-motion` açıksa animasyon kapanır), ekran okuyucu için "Yükleniyor".
- **Boş program** (`17_bos_program_durumu`): "Yakın günlerde koşu programı yok", çalışma saatleri ve "Yeniden dene".
- **Ağ hatası:** "Veri alınamadı" ve "Yeniden dene"; servis çalışanı (SW) önbelleğindeki son veri gösterilir.
- **Boş kupon:** açıklama + "Programa git".
- **Kayıt bulunamadı** (eski bağlantı): "Programa dön".
- **Demo saati:** Prototipte bugünün verisi yoksa, canlı dosyanın son güncelleme anı saat olarak kullanılır ve sarı "demo saati" rozetiyle belirtilir. Uygulamada bu yoktur.

### 5.12 Erişilebilirlik ve 360 px
- Tüm dokunma hedefleri ≥ 40–44 px. Bağlantılar gerçek `<a href>`, eylemler `<button>`. Sekmede `aria-current="page"`, çiplerde `aria-pressed`, koşu çiplerinde `aria-current="true"`. Kurucu `role="dialog" aria-modal`. Ekran değişince odak `main`'e taşınır; `main` `aria-live="polite"`.
- Görünür odak halkası (`--focus`). Renk tek başına anlam taşımaz: ✓/✗ işaretleri, "▲/▼" ve metin etiketleri her zaman vardır.
- Kontrast: gövde `--ink2` (#B6C0D3) ve ikincil `--ink3` (#8893AB), `--s1` üzerinde ≥ 5:1. Altın metin (#F3DC8A) koyu zeminde ≥ 10:1.
- 360 px: sekmeler 5 kısa etiket (Bugün/Program/Bahis/Sonuç/Kupon); `minmax(0,1fr)` ızgaralar; uzun adlarda üç nokta; Meraklı göstergeleri 4 sütun ve ≤370 px'te sola yaslanır; yatay sayfa kaydırması yok (Playwright ile doğrulandı).

---

## 6. Veri eksikleri ve önerilen açık kaynaklar

| Eksik | Öneri | Not |
|---|---|---|
| Oran hareketi | `canli.py`: her 30 dakikalık okumada at başına `oran_izi` (son 12 nokta). Arayüzde küçük çizgi grafiği ve "sabahtan beri ▲▼" | Yeni kaynak gerekmez; tamamen bizim zaman serimiz |
| At kariyer tablosu, pist/mesafe/hipodrom/sınıf uygunluğu, jokeyle uyum | Laboratuvar gece aynanın `memory/horses.json`'ını (~35 MB) okur, **yalnız o günün koşucuları** için küçük bir `data/at/profil/<gün>.json` (≈50–100 KB) yazar | Ham veri depoya kopyalanmaz; yalnız türetilmiş özet |
| Pist durumu ve hava | `daily` dosyasındaki `trackCondition`, `weatherCondition`, `temperature` → `tahmin`'e koşu alanı | `veri.py` zaten okuyor (`zemin`) |
| Koşmayan at | `nonRunner` → canlıda "koştu/koşmadı" ve kuponda uyarı | Kupon durum hesabını da etkiler |
| Derece süresi ve farkı | `finishTime` → sonuç kartında süre ve kazanana göre fark (sn) | Fotofiniş görüntüsü yok |
| 5'li/4'lü/3'lü ganyan | `altili.py` ayak sayısı parametresi + `isGanyanStart` | Arayüz bileşeni aynı |
| AGF | **Yok.** TJK API paketleri kural gereği kullanılmaz. Arayüzde "piyasa %" adı korunur | Araştırmacı `arastirma.json`'da aramaya devam eder |
| İdman/galop, start, HP, sahip, pedigri | **Yok.** Açık lisanslı kaynak bulunana kadar "henüz veri yok" kutusu kalır | `arastirma.json` sorgularına "pedigri", "start no" eklenebilir |
| Arama | Bugün: istemcide. Geçmiş: `data/at/dizin.json` (at → son koşu tarihleri) | Küçük tutulmalı |
| Bildirim | Uygulama açıkken: yerel `Notification` (SW `showNotification`). Kapalıyken: GitHub Actions + Web Push (VAPID) ya da ücretsiz bir kuyruk; kullanıcı onayı şart | Kural: kendiliğinden mail/issue/bildirim yok. Kullanıcının açıkça açacağı bir ayar olmalı |

---

## 7. Uygulama yol haritası

Her aşama ayrı bir `<style id>` ve `<script id>` bloğu olarak eklenir. Bu, mevcut yamalama düzenine uyar: blok silinirse eski görünüm döner. Her aşamadan sonra Playwright ile 390 ve 360 görüntüsü alınır ve `MIMARI.md` güncellenir.

| Aşama | Kapsam | Dosya / blok | Risk ve önlem |
|---|---|---|---|
| **1. İskelet ve gezinme** | Hero ve "Model ne kadar başarılı" İstatistik'e; yapışkan sekme çubuğu (Bugün/Program/Bahis/Sonuç/Kupon); hash yolları `#at/...`; Bugün ekranı (sıradaki koşu, altın kartları, kısaltılmış Padok, hipodromlar); Program satırları | `index.html`: yeni `<style id="at2-v103">`, `<script id="at2-v103">`. `at-v73` IIFE'sindeki `render()` sarmalanır; `BX_AT` çekirdeği (`AT`, `merged`, `cRace`, `load`, `goldOfDay`) olduğu gibi kullanılır | `showSport("at")` ve `goView` ile çakışma: hash yalnız `#at/` önekiyle dinlenir. Eski `AT.tab` değerleri yeni sekmelere eşlenir (`tah→program`, `altin→bugun`, `altili→bahis`, `jokey→istatistik`). `sw.js` önbellek sürümü artırılır |
| **2. Koşu kartı ve profiller** | Koşu çipleri, Sade/Meraklı, sıralama, form çipleri, piyasa farkı, pist uyumu; `horseSheet` modalı yerine At profili ekranı; Jokey/Antrenör profili; Takip ekranı (at+jokey+antrenör, `bx-at-fav` korunur ve `bx-at-takip`'e taşınır) | `at2-v103` (devamı). `atkupon-v98` içindeki `#atSheet .atk-hs` girişleri profil ekranına taşınır | v98'in `horseSheet` sarmalayıcısı kırılabilir: `BX_AT.horseSheet` profil ekranına yönlenen bir uyum işlevi olarak kalır |
| **3. Kupon at bölümünde** | "Kupon" sekmesi = `KX.L` içindeki `spor:"at"` kupon(lar)ın görünümü; yüzen "At kuponum" çubuğu; OXX at kuponları; karne çubukları | `atkupon-v98`'e dokunmadan yeni `<script id="atkupon-at-v104">`. Okuma/yazma yalnız `window.KX` ve `atkOpen`/`atkGrade` üzerinden | **Tek veri kaynağı `bx-kuponlar`**. Satır şeması v98 ile aynı (`{tur,kid,sec,komb,p,…}`). Çubuk, KUPO'daki değişikliği `storage` olayı ve `KX` yeniden çizimiyle izler. Futbol kuponuna asla yazılmaz (v98'in tek spor kuralı) |
| **4. Veri zenginleştirme (lab)** | `oran_izi` (canli.py); `profil/<gün>.json` (gece.py + aynanın `memory/horses.json`'ı); pist durumu/hava; `nonRunner`; `finishTime`; 5'li/4'lü/3'lü | `lab/at/canli.py`, `gece.py`, `altili.py`; yeni `data/at/profil/`; arayüzde Meraklı ve At profili "henüz veri yok" kutularının yerini alır | Depo boyutu: profil dosyası yalnız günün koşucuları için. Zaman aşımı: aynayı sığ klonla. `test_sizinti.py` kapsamına profil alanları eklenir |
| **5. Bildirim ve arama** | Ayarlar'da "Atım koşuyor" anahtarı (önce uygulama açıkken yerel bildirim); arama (bugün → geçmiş dizin) | Yeni blok `at-bildirim-v105`; `sw.js` `notificationclick` (ayrı iş) | İzin istemi yalnız kullanıcı düğmeye basınca. Push sunucusu kararı ayrıca verilir |

**Kabul ölçütleri (her aşama):** İlk ekranda sıradaki koşu ve sekmeler görünmeli (390×844). 360 px'te yatay kaydırma olmamalı. Tüm eylemler ≥ 44 px olmalı. Klavyeyle gezinilebilmeli. KUPO'da eklenen at satırı at Kupon sekmesinde ve çubukta ≤1 saniyede görünmeli, tersi de geçerli. tjk.org'a sıfır istek olmalı (Playwright `route` ile engellenip sayılır).

---

## 8. KUPO'nun at içindeki yeri: öneri

**Evet, at bölümünün içinde olması daha iyi ve daha estetik.** Ancak bu ayrı bir kupon olmamalı, KUPO'nun at kuponunun **ikinci kapısı** olmalı:

1. **Kupon sekmesi:** At bölümünün beşinci sekmesi, sayı rozetiyle. İçeriği KUPO'daki "At Kuponu" ile aynı veridir (`bx-kuponlar`, `spor:"at"`).
2. **Yüzen "At kuponum" çubuğu:** Kullanıcı program, koşu kartı ya da profil ekranındayken kuponunu kaybetmez. Satır, kombinasyon ve bekleyen sayısını gösterir, tek dokunuşla Kupon sekmesini açar.
3. **KUPO aynen kalır:** Futbol, basket ve at kuponlarının ortak arşivi ve "Eski kuponlarım" orada. KUPO'daki at kuponu kartına "At bölümünde aç" bağlantısı eklenir.

Neden: Takipçi kuponu çoğunlukla **koşu kartına bakarken** kurar ve değiştirir. Futbol menüsündeki KUPO'ya gidip gelmek bağlamı kopardığı için başlangıç düzeyi kullanıcı kuponunu "kaybediyor". Tek veri kaynağı da iki yer arasında tutarsızlık riskini ortadan kaldırır.

---

## 9. Prototip ve ekran görüntüleri

- Prototip: `lab/at/prototip.html`. Yerelde `python3 -m http.server` çalıştırılıp `/lab/at/prototip.html` açılır. Veri `../../data/at/` yolundan okunur; `?veri=<yol>` ile değiştirilebilir. Kupon satırları uygulamayı etkilemesin diye yalnız `bx-proto-atk` anahtarına yazılır.
- Ekran görüntüleri (390×844 ve 360×740): `at_tasarim_shots/` (oturumun geçici çalışma klasöründe; depoya eklenmedi). Mevcut durum: `mevcut_*`. Yeni tasarım: `01…18_*`.
