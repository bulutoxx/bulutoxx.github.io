# OXXai yol haritası — kanıta dayalı iyileştirme listesi (otonom döngü backlog'u)

Hazırlanma: 2026-10-28 · Kapsam: futbol, basket, at, canlı, altyapı, arayüz · Sıra: beklenen değer / efor (yüksekten düşüğe).

## Otonom döngü kuralları

1. Her döngüde aşağıdaki listeden **en üstteki `durum: bekliyor`** maddeyi al; ayrı bir dalda uygula, yalnız o maddenin dosyalarına dokun.
2. Maddeyi kendi **kapı ölçütünden** geçir (zaman sıralı, yalnız geçmişle öğrenilmiş; ΔLL %95 GA üst sınırı < 0, iki zaman yarısında da ΔLL < 0, ΔBrier ≤ 0, tek yanlı p ≤ α_t alfa yatırımı); geçemezse yayına alma.
3. Geçerse yayına al (bayraklı, geri alınabilir, 14 gün izleme); maddenin durumunu `yayında` ya da `reddedildi` yap ve yanına kanıtı (tarih, n, ΔLL [GA], commit / `data/...json` yolu) yaz.
4. Değişmez kurallar: sıfır maliyet (ücretli API / sunucu yok); kilitli tahmin asla değişmez; uygulamada görünen metinde "bahis", "ganyan", "banko", "bulut", "kupon" kelimeleri yok; TJK ve atyarisi.com alanlarına (alt alanlar ve archive.org kopyaları dahil) hiçbir istek yok.
5. Futbol ve at modelleri ayrı tutulur (ortak kod yalnız ölçüm yardımcıları); ek kaynak adresleri yalnız secret'ta, depoda yazılmaz; ham üçüncü taraf verisi commit edilmez (yalnız türetilmiş özet).

## Mevcut sistem (tekrar önerilmeyenler)

Maher-Poisson + Elo + pi-rating topluluğu (oransız ligler, `scripts/guc.py`), iki yarı Dixon-Coles, piyasa (power/Shin/hibrit marj) +
sunulan yolda yürüyen pencere kalibrasyonu (calT/gscale/dk), Club Elo kupa çapası, kadro / oran hareketi / karışım gölge kaydı
(`tazeveri`), canlı CG modeli (Gamma-Poisson, skor durumu, son dakika) + canlı istatistik ayarı, robot arenası ve konsey, alfa yatırımı
kapıları, koruyucu geri alma, at modeli v7 (koşullu logit + GBM + harman + Harville/Henery/Lo–Bacon-Shone), basket piyasa harmanı (gölgede),
drift alarmı ve kapanış kilidi (yolda). Aşağıdaki maddeler bunların **üzerine** gelir; çakışan bir şey bulunursa madde `reddedildi (zaten var)` yapılır.

## Ortak tanımlar

- **ΔLL** = LL(aday) − LL(üretim), maç (ya da koşu) başına ortalama log-kayıp; negatif = iyi. GA: lig×gün (at: koşu günü) blok bootstrap, B = 2000.
- **Standart kapı (SK)**: sınama diliminde ΔLL %95 GA üst sınırı < 0 · sınamanın iki yarısında ΔLL < 0 · ΔBrier ≤ 0 · isabet / Altın isabeti düşmüyor · p ≤ α_t.
- Beklenen kazançlar literatürdeki **tipik** büyüklüklerdir; OXXai verisinde ölçülmeden doğru kabul edilmez.

---

### YH-01 · altyapı · Öneri CLV karnesi (kapanış çizgisi değeri)
- **Açıklama:** Kapanış kilidi geldiğinde her kilitli öneri için `clv = ln(p_kapanış / p_kilit)` (marjı ayrılmış piyasa olasılığı; öneri tarafı) ve "kapanışı geçti" oranı hesaplanır; Motor sayfası, drift alarmı ve koruyucu için sonuçtan çok daha hızlı yakınsayan bir erken uyarı ölçütü olur. Model yolu (oransız) önerilerinde de modelin kilit anındaki olasılığı ile kapanış piyasası karşılaştırılır.
- **Beklenen kazanç:** Doğrudan isabet değil, ölçüm hızı: CLV'nin varyansı sonuçtan çok küçük olduğundan bir değişikliğin iyi/kötü olduğu ~5–10 kat daha az maçla görülür. Kapanış oranı en bilgili tahmindir; kapanışa doğru hareket eden seçimler uzun vadede daha iyi sonuç verir.
- **Efor:** S (kapanış kilidine bağımlı) · **Risk:** düşük (yalnız ölçüm) · **Veri:** kendi kayıtlarımız, ücretsiz.
- **Nasıl sınanır:** Önce doğrulama: geçmiş 90 günde CLV ile gerçekleşen LL farkı arasında aylık korelasyon > 0 (blok bootstrap GA alt sınırı > 0). Sonra karneye girer; kapı gerekmez (karar üretmez).
- **Kaynak:** Kaunitz, Zhong, Kreiner (2017) [arXiv:1710.02824](https://arxiv.org/abs/1710.02824) · Štrumbelj (2014) IJF [doi:10.1016/j.ijforecast.2014.02.008](https://doi.org/10.1016/j.ijforecast.2014.02.008)
- **Durum:** gölgede (2026-10-28; doğrulama geçmedi, veri birikiyor) — `lab/clv_karne.py` → `data/clv.json`, otonom ekipte günde 2 kez (yalnız ölçüm, arayüzde yok).
  Kilit = arşiv oranı (iddaa kimliği), kapanış = tazeveri `o1/u1` (başlamadan medyan ≈ 16 dk önce son görülen oran). n = 1.791 öneri (1X2 804, 2,5 A/Ü 987), 5 gün;
  öneri tarafı ort. clv −0,0007 [GA −0,0013, −0,0004], kapanışı geçen %5,6 (öneri oranlarının %86,9'u kilitten kapanışa hiç oynamadı).
  Doğrulama: corr(clv, y − p_kilit) = −0,038 [GA −0,063, −0,016] (n = 1.450 sonuçlu) → **geçmedi**; ayrıca iddaa kapanışı kilitten daha bilgili değil:
  ΔLL(kapanış − kilit) = +0,0006 [+0,0003, +0,0016] (n = 2.604). Yorum: yerel piyasada maça yakın hareket az ve bilgi taşımıyor; 90 günlük örnekte
  yeniden değerlendirilecek (≥ 30 gün, corr GA alt > 0 olursa karneye ve drift alarmına bağlanır). Model yolu CLV'si için sonuçlu Pinnacle kapanışı gerekir (YH-02 ile).

### YH-02 · futbol · Keskin piyasa önceliği (Pinnacle / uzlaşı) hem öğrenme hedefinde hem yaklaşan maçlarda
- **Açıklama:** Motor kapanışta önce `AvgC*`, yaklaşanlarda önce `Avg*` kullanıyor; football-data aynı satırda Pinnacle (`PSCH…`, `PSH…`) ve en yüksek oranı da veriyor. Aday: (a) kalibrasyon hedefi = Pinnacle kapanışı (yoksa ortalama), (b) yaklaşan maçta iddaa olasılığı ile football-data Pinnacle/ortalama olasılığının log-uzlaşısı (ağırlık yürüyen pencerede öğrenilir).
- **Beklenen kazanç:** Düşük marjlı keskin piyasa, ortalamadan ve yüksek marjlı yerel piyasadan daha iyi kalibre; tipik ΔLL −0,001 … −0,004 (1X2, oranlı maçlar).
- **Efor:** S · **Risk:** düşük (bayraklı; iddaa gösterimi değişmez, yalnız olasılık) · **Veri:** football-data.co.uk, ücretsiz (atıf).
- **Nasıl sınanır:** `_served_walkforward` katlarında üç hedef (Avg / PS / uzlaşı) yarışır; SK + katların çoğunda daha iyi + Altın isabeti düşmüyor.
- **Kaynak:** Štrumbelj (2014) [doi:10.1016/j.ijforecast.2014.02.008](https://doi.org/10.1016/j.ijforecast.2014.02.008) · Hubáček, Šourek, Železný (2019) IJF [ideas.repec](https://ideas.repec.org/a/eee/intfor/v35y2019i2p783-796.html) · [football-data.co.uk notları](https://www.football-data.co.uk/notes.txt)
- **Durum:** bekliyor

### YH-03 · futbol · Şut tabanlı güç robotu (GAP / sözde-xG) — oranlı ligler
- **Açıklama:** `update.py` football-data'dan isabetli şutu (`HST/AST` → `m["st"]`) zaten indiriyor ama yalnız korner/kart modelinde kullanıyor. Wheatcroft'un GAP puanı gibi her takıma şut ve isabetli şut üretme/yeme gücü (ev/deplasman ayrı, üstel unutma) çıkar; beklenen isabetli şut → beklenen gol dönüşümü öğrenilir. `guc.py` topluluğuna 4. robot ve 2,5 üst yığınlayıcısına girdi olarak eklenir; oranlı maçta piyasa ile karışım `karisim` gölgesinde ölçülür.
- **Beklenen kazanç:** Şut istatistikleri gole göre daha az gürültülü; literatürde şut tabanlı puanlar gol tabanlılara bilgi ekliyor ve piyasaya karşı bile bilgi taşıyor (Wheatcroft). Tipik model yolu ΔLL −0,003 … −0,010; piyasa üstüne katkı ≈ 0 … −0,002.
- **Efor:** M · **Risk:** orta (sızıntı: yalnız maçtan önceki şutlar) · **Veri:** mevcut, ücretsiz.
- **Nasıl sınanır:** `lab/fb_guc_lab.py derin` alanında SK (model yolu) + ayrı olarak piyasa üstü yığmada ΔLL üst sınırı < 0 ise `karisim` adayına bağlanır.
- **Kaynak:** Wheatcroft (2021) J. Sports Analytics 7(2) [doi:10.3233/JSA-200462](https://doi.org/10.3233/JSA-200462), [arXiv:2001.09097](https://arxiv.org/abs/2001.09097) · Wheatcroft (2020) IJF "A profitable model for predicting the over/under market" [doi:10.1016/j.ijforecast.2019.11.001](https://doi.org/10.1016/j.ijforecast.2019.11.001)
- **Durum:** bekliyor

### YH-04 · basket · Dinlenme günü, arka arkaya maç ve deplasman serisi düzeltmesi
- **Açıklama:** `bk_games.json` maç tarihlerinden her takım için dinlenme günü (0 = arka arkaya), son 7 günde maç sayısı ve üst üste deplasman sayısı türetilir; ridge güç modelinin beklenen sayı farkına öğrenilen toplamsal düzeltme olarak eklenir (lig grubuna göre: pro / avrupa / kolej).
- **Beklenen kazanç:** NBA'de dinlenme eksikliği ev avantajının önemli bir parçası; 538 modeli arka arkaya maçı ~1–2 sayı (≈ 25–45 Elo) düzeltir. Tipik MS ΔLL −0,002 … −0,005 (NBA/WNBA), toplam sayı MAE küçük iyileşme.
- **Efor:** S · **Risk:** düşük · **Veri:** mevcut (ESPN / EuroLeague takvimi), ücretsiz.
- **Nasıl sınanır:** `lab/bk_gelistir.py` adayı olarak: gün kümeli bootstrap ΔLL üst sınırı < 0, ΔBrier < 0, isabet düşmüyor, iki zaman diliminde de.
- **Kaynak:** Entine & Small (2008) JQAS "The Role of Rest in the NBA Home-Court Advantage" [UPenn](https://repository.upenn.edu/entities/publication/e871ae9f-87db-40bd-922e-53064fae121f) · [FiveThirtyEight: NBA tahmin yöntemi](https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- **Durum:** bekliyor

### YH-05 · canlı · Basket canlı kazanma olasılığı: kayıt + Brown hareketi kalibrasyonu + piyasa çapası
- **Açıklama:** Uygulamadaki `bkLivePred` Stern tipi normal model kullanıyor ama σ (`p.sm`) ve sürüklenme hiç canlı veriyle sınanmadı ve kayıt yok. (1) Canlı kayıt işine basket anlık görüntüsü ekle (skor, kalan süre, maç öncesi olasılık / çizgi); (2) σ'yı kalan süreye göre ve sürüklenmeyi maç öncesi piyasa çizgisinden (Polson–Stern "örtük oynaklık") öğren; (3) Platt ile kalibre et; tek formül sunucu ve uygulamada birebir.
- **Beklenen kazanç:** Kalibrasyonsuz canlı modellerde son çeyrekte aşırı güven yaygın; tipik canlı ΔLL −0,01 … −0,03 (özellikle 4. çeyrek), kalibrasyon hatası yarıya.
- **Efor:** M · **Risk:** orta (saat ayrıştırma, uzatma) · **Veri:** ESPN / EuroLeague canlı akışı (zaten okunuyor), ücretsiz.
- **Nasıl sınanır:** `canli_guc_lab.py` protokolü: sınama günü D için yalnız D'den önce biten maçlarla öğren; ≥ 600 anlık görüntü / ≥ 120 maç; maç-blok bootstrap ΔLL üst sınırı < 0; Brier kötüleşmiyor; günlerin çoğunda iyi.
- **Kaynak:** Stern (1994) JASA "A Brownian motion model for the progress of sports scores" [doi:10.1080/01621459.1994.10476866](https://doi.org/10.1080/01621459.1994.10476866) · Polson & Stern (2015) JQAS [doi:10.1515/jqas-2014-0095](https://www.degruyterbrill.com/document/doi/10.1515/jqas-2014-0095/html)
- **Durum:** bekliyor

### YH-06 · futbol · Beta kalibrasyonu (2,5 alt/üst, KG ve pazar motoru ek pazarları)
- **Açıklama:** `pazar.py` ek kalibrasyonda yalnız Platt / sıcaklık deniyor. Beta kalibrasyonu (3 parametre: ln p ve ln(1−p) ayrı eğim) asimetrik sapmayı (ör. düşük olasılıklı "üst" uçlarında) düzeltebilir; Platt'ı özel durum olarak içerir. İzotonik yalnız karşılaştırma için (büyük örnekte).
- **Beklenen kazanç:** Kalibrasyon makalelerinde beta, Platt'a göre çoğu veri kümesinde daha düşük log-kayıp; tipik ΔLL −0,0005 … −0,002 pazar başına.
- **Efor:** S · **Risk:** düşük · **Veri:** mevcut.
- **Nasıl sınanır:** `pazar.py` aylık ileriye dönük sınaması: İKİ zaman diliminde de LL düşmeli + SK.
- **Kaynak:** Kull, Silva Filho, Flach (2017) AISTATS [PMLR v54](https://proceedings.mlr.press/v54/kull17a.html) · Walsh & Joshi (2024) "Machine learning for sports betting: should model selection be based on accuracy or calibration?" [Bath](https://researchportal.bath.ac.uk/en/publications/machine-learning-for-sports-betting-should-model-selection-be-bas/)
- **Durum:** bekliyor

### YH-07 · basket · Sayı farkı ağırlıklı Elo robotu + ridge ile yığma
- **Açıklama:** Basket motoru tek model (ağırlıklı ridge hücum/savunma). Sayı farkı çarpanlı, sezon başı ortalamaya çekmeli Elo ayrı robot olarak çalıştırılır; lojistik yığınlayıcı (girdiler: ridge fark/σ, Elo farkı, dinlenme) yalnız geçmişle öğrenir.
- **Beklenen kazanç:** Farklı hata yapısına sahip iki güç ölçüsünün birleşimi tek modele göre tipik olarak ΔLL −0,002 … −0,006; özellikle sezon başı ve NCAA'da.
- **Efor:** S–M · **Risk:** düşük · **Veri:** mevcut.
- **Nasıl sınanır:** `bk_gelistir.py` kapısı (gün kümeli bootstrap, iki zaman dilimi) + lig grubu başına ayrı karar.
- **Kaynak:** [FiveThirtyEight NBA Elo](https://fivethirtyeight.com/features/how-we-calculate-nba-elo-ratings/) · Hvattum & Arntzen (2010) IJF [doi:10.1016/j.ijforecast.2009.10.002](https://doi.org/10.1016/j.ijforecast.2009.10.002)
- **Durum:** bekliyor

### YH-08 · at · Sabah olasılığının kapanış piyasasına bilgi katkısı (at için CLV)
- **Açıklama:** Sabah kilitli model olasılığı ile kapanış oranı (izinli ayna kaynağı, marjı ayrılmış) arasında: (a) sabah p kapanış hareketinin yönünü öngörüyor mu (kapanış − açılış/ön oran farkının sabah p − piyasa farkına regresyonu), (b) Benter iki aşaması: `logit p = a·logit p_model + b·logit p_kapanış` içinde a > 0 mı. Karneye "sabah modeli piyasaya bilgi ekliyor mu" satırı olarak girer; harman ağırlığının sağlık izlemesi olur.
- **Beklenen kazanç:** Doğrudan ölçüm kalitesi; Benter'e göre modelin değeri tam olarak bu bilgi katkısıdır. Harman ağırlığı a'nın GA'sı sıfırı kapsıyorsa sabah modeli için alarm.
- **Efor:** S · **Risk:** düşük · **Veri:** mevcut (yalnız izinli kaynak; TJK yok).
- **Nasıl sınanır:** Yürüyen pencerede a'nın koşu-günü blok bootstrap GA'sı; a > 0 (alt sınır > 0) karnede "doğrulandı".
- **Kaynak:** Benter (1994) "Computer based horse race handicapping and wagering systems" (Efficiency of Racetrack Betting Markets, World Scientific) [World Scientific](https://worldscientific.com/doi/abs/10.1142/9789812819192_0019) · Bolton & Chapman (1986) Management Science [doi:10.1287/mnsc.32.8.1040](https://doi.org/10.1287/mnsc.32.8.1040)
- **Durum:** bekliyor

### YH-09 · altyapı · Skor ayrışımı (güvenilirlik / çözünürlük) ve ECE'nin tüm karnelere eklenmesi
- **Açıklama:** Brier'in Murphy ayrışımı (güvenilirlik − çözünürlük + belirsizlik) ve beklenen kalibrasyon hatası (ECE, eşit örnekli kovalar) futbol, basket, at, canlı karnelerine eklenir. Kötüleşmenin kalibrasyondan mı (düzeltilebilir: yeniden kalibre) yoksa çözünürlükten mi (model/veri sorunu) geldiğini drift alarmı ve koruyucu ayırt edebilir. Ana ölçüt log-kayıp kalır (RPS önerilmez).
- **Beklenen kazanç:** Teşhis hızı; geri alma yerine yeniden kalibrasyonla çözülebilecek durumların ayrılması.
- **Efor:** S · **Risk:** çok düşük · **Veri:** mevcut.
- **Nasıl sınanır:** Kapı yok (ölçüm); birim testi: ayrışım toplamı Brier'e eşit (±1e-9).
- **Kaynak:** Murphy (1973) J. Applied Meteorology [doi:10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2](https://doi.org/10.1175/1520-0450(1973)012%3C0595:ANVPOT%3E2.0.CO;2) · Wheatcroft (2021) JQAS 17(4) "Evaluating probabilistic forecasts of football matches: the case against the ranked probability score" [arXiv:1908.08980](https://arxiv.org/abs/1908.08980)
- **Durum:** bekliyor

### YH-10 · canlı · Canlı piyasa olasılığı + CG harmanı (futbol)
- **Açıklama:** Uygulama iddaa canlı oranlarını okuyup gösteriyor; CG modeli ise canlı piyasayı kullanmıyor. Canlı kayıt anlık görüntüsüne marjı ayrılmış canlı MS ve 2,5 olasılığı eklenir (yoksa boş); `logit p = a·logit p_CG + b·logit p_canlı-piyasa` dakika dilimine göre öğrenilir. Canlı piyasa yokken CG aynen kalır.
- **Beklenen kazanç:** Maç öncesinde olduğu gibi canlıda da piyasa en güçlü tahminci; tipik canlı ΔLL −0,01 … −0,04 (piyasası olan anlık görüntülerde).
- **Efor:** M · **Risk:** orta (canlı oran askıya alınmış anlar; gecikme sızıntısı → yalnız kayıt anından önceki oran) · **Veri:** zaten okunan kaynak, ücretsiz; ham oran depoya yazılmaz (yalnız marjı ayrılmış olasılık, 3 hane).
- **Nasıl sınanır:** `canli_guc_lab.py` protokolü + ayrıca "piyasası olan" alt kümede SK; ≥ 600 anlık görüntü.
- **Kaynak:** Robberechts, Van Haaren, Davis (2021) KDD "A Bayesian approach to in-game win probability in soccer" [arXiv:1906.05029](https://arxiv.org/abs/1906.05029) · Croxson & Reade (2014) Economic Journal "Information and efficiency: goal arrival in soccer betting" [doi:10.1111/ecoj.12033](https://doi.org/10.1111/ecoj.12033)
- **Durum:** bekliyor

### YH-11 · futbol · Skor güdümlü (GAS) dinamik güç modeli — model yolu
- **Açıklama:** Poisson robotu haftalık yeniden eğitim + üstel unutma kullanıyor. Skor güdümlü modelde her maçtan sonra hücum/savunma gücü log-olabilirlik gradyanıyla güncellenir (öğrenilen adım ve kalıcılık); Koopman–Lit'in iki değişkenli Poisson sürümü. Topluluğa 5. robot ya da Poisson'un yerine aday.
- **Beklenen kazanç:** Koopman & Lit, statik ve basit dinamik modellere göre ulusal liglerde tahmin doğruluğunda ve olasılık skorlarında iyileşme bildiriyor; tipik model yolu ΔLL −0,002 … −0,006 (oransız liglerde en çok).
- **Efor:** M · **Risk:** orta (ilk haftalar kararsızlığı) · **Veri:** mevcut.
- **Nasıl sınanır:** `fb_guc_lab.py espn` ve `derin` alanlarında SK.
- **Kaynak:** Koopman & Lit (2019) IJF [VU araştırma](https://research.vu.nl/en/publications/forecasting-football-match-results-in-national-league-competition-2/), [Tinbergen DP 17-062](https://papers.tinbergen.nl/17062.pdf) · Koopman & Lit (2015) JRSS-A [doi:10.1111/rssa.12042](https://doi.org/10.1111/rssa.12042)
- **Durum:** bekliyor

### YH-12 · futbol · Oransız ligler için ESPN maç istatistiklerinden şut gücü
- **Açıklama:** YH-03'ün oransız ligler sürümü: ESPN maç özetindeki takım istatistikleri (şut, isabetli şut, korner) yalnız türetilmiş takım puanı olarak saklanır (ham yanıt depoya girmez); `guc.py` topluluğu bu puanı oransız liglerde kullanır. YH-03 kapıdan geçmeden başlanmaz.
- **Beklenen kazanç:** Oransız liglerde piyasa çapası olmadığından sinyal ekleme değeri en yüksek; tipik ΔLL −0,003 … −0,008.
- **Efor:** M · **Risk:** orta (ESPN kapsamı ligden lige değişir; eksik istatistikte robot sessiz kalır) · **Veri:** ESPN herkese açık uç noktası, ücretsiz.
- **Nasıl sınanır:** `fb_guc_lab.py espn` SK; ayrıca kapsam ≥ %60 olan liglerle sınırlı alt küme raporu.
- **Kaynak:** Wheatcroft (2021) [doi:10.3233/JSA-200462](https://doi.org/10.3233/JSA-200462) · Mead, O'Hare, McMenemy (2023) PLoS ONE "Expected goals in football" [doi:10.1371/journal.pone.0282295](https://doi.org/10.1371/journal.pone.0282295)
- **Durum:** bekliyor

### YH-13 · arayüz · Şeffaf güvenilirlik paneli
- **Açıklama:** Motor sayfasına kilitli kayıtlardan çizilen güvenilirlik eğrisi (söylenen % ↔ gerçekleşen %), son 30 / 90 gün, pazar seçimi; YH-01 ve YH-09 ölçütleri tek satırda. Yalnız ölçülmüş rakam; az örnekte kova gizlenir (n < 50).
- **Beklenen kazanç:** Güven ve dürüstlük; olasılıklı tahminlerin belirsizlikle birlikte sunulması kullanıcı kararlarını iyileştiriyor.
- **Efor:** S · **Risk:** düşük (duman testi + kalite ekran görüntüsü) · **Veri:** mevcut.
- **Nasıl sınanır:** Kalite botu (360/390 px ekran görüntüsü), duman testi, açılış süresi artışı < 50 ms; görünür metin yasaklı kelime taraması.
- **Kaynak:** Joslyn & LeClerc (2012) J. Exp. Psychology: Applied [doi:10.1037/a0025185](https://doi.org/10.1037/a0025185) · Gigerenzer & Hoffrage (1995) Psychological Review [doi:10.1037/0033-295X.102.4.684](https://doi.org/10.1037/0033-295X.102.4.684)
- **Durum:** bekliyor

### YH-14 · basket · Tempo (hücum sayısı) tabanlı toplam sayı modeli
- **Açıklama:** Toplam sayı şu an hücum/savunma sayı ridge'inden geliyor. ESPN kutu skorundan (FGA, FTA, TOV, OREB) hücum sayısı tahmini → takım temposu ve hücum başına verim ayrı öğrenilir; toplam = tempo × (verim_ev + verim_dep). Alt/üst ve handikap dağılımı bundan türetilir.
- **Beklenen kazanç:** Tempo ve verimi ayırmak toplam tahmininde varyansı düşürür; tipik toplam MAE −%2 … −%5, alt/üst ΔLL −0,003 … −0,008.
- **Efor:** M · **Risk:** orta (EuroLeague kutu skoru biçimi farklı) · **Veri:** ESPN / EuroLeague herkese açık, ücretsiz; yalnız türetilmiş takım değerleri saklanır.
- **Nasıl sınanır:** `bk_gelistir.py`: toplam MAE ve alt/üst LL için gün kümeli bootstrap üst sınırı < 0, iki dilimde de.
- **Kaynak:** Kubatko, Oliver, Pelton, Rosenbaum (2007) JQAS "A starting point for analyzing basketball statistics" [doi:10.2202/1559-0410.1070](https://doi.org/10.2202/1559-0410.1070)
- **Durum:** bekliyor

### YH-15 · at · Koşu belirsizliğine göre seçici gösterim (pas eşiği)
- **Açıklama:** Futboldaki "%58 altı pas" kuralının at karşılığı: koşu düzeyinde entropi, alan büyüklüğü ve ilk iki olasılık farkından "güven sınıfı" üret; Altın ve öne çıkan seçimler yalnız geçmişte kalibre olduğu sınıflarda gösterilir. Eşik yürüyen pencerede seçilir.
- **Beklenen kazanç:** Seçici tahmin: kapsamı %20–30 azaltarak gösterilen seçimlerin isabetini birkaç puan artırma (risk–kapsam eğrisi).
- **Efor:** S · **Risk:** düşük · **Veri:** mevcut.
- **Nasıl sınanır:** Zaman sıralı: aynı kapsamda rastgele seçime göre isabet farkının GA alt sınırı > 0; yalnız-model ve harman ayrı.
- **Kaynak:** Geifman & El-Yaniv (2017) NeurIPS "Selective classification for deep neural networks" [arXiv:1705.08500](https://arxiv.org/abs/1705.08500)
- **Durum:** bekliyor

### YH-16 · basket · Sakatlık raporu (NBA / WNBA) — dakika ağırlıklı kayıp
- **Açıklama:** ESPN takım sakatlık listesinden "oynamaz / şüpheli" oyuncular; oyuncunun son maçlardaki dakika payı × takım içi etki (kutu skorundan basit artı-eksi ya da sayı payı) ile beklenen fark düzeltmesi. Yalnız türetilmiş takım düzeltmesi depoya; oyuncu düzeyi birikim önbellekte (futbol `kadro.py` ilkesi).
- **Beklenen kazanç:** Piyasası olmayan / model yolu tahminlerinde en büyük eksik bilgi; tipik model yolu ΔLL −0,003 … −0,010 (yıldız eksikliği olan maçlarda çok daha fazla). Piyasa çapası yayındaysa katkı küçük.
- **Efor:** M · **Risk:** orta (rapor zamanlaması → sızıntı; yalnız kilit anından önceki rapor) · **Veri:** ESPN herkese açık, ücretsiz.
- **Nasıl sınanır:** Gölge kayıt (≥ 300 maç, ≥ 80 sinyalli) → `tazeveri` tipi kapı, SK.
- **Kaynak:** Kubatko ve ark. (2007) [doi:10.2202/1559-0410.1070](https://doi.org/10.2202/1559-0410.1070) · [FiveThirtyEight RAPTOR / kadro düzeltmesi](https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- **Durum:** bekliyor

### YH-17 · altyapı · Sıralı (her an geçerli) test ile gölge sürenin kısaltılması
- **Açıklama:** Gölge ölçüm ve 14 gün izleme sabit süreli. Karışım SPRT / e-değer tabanlı "her an geçerli" güven dizileri, istenildiği an bakılsa bile I. tür hata kontrolünü korur; açık iyileşmede erken yayın, açık kötüleşmede erken geri alma sağlar. Alfa yatırımıyla uyumlu (e-değerler LORD/alfa yatırımına bağlanabilir).
- **Beklenen kazanç:** Aynı hata oranında ortalama karar süresinde %30–50 kısalma (literatürdeki A/B testi sonuçları); döngü hızı artar.
- **Efor:** M · **Risk:** orta (yanlış uygulama → hata kontrolü kaybı; önce gölgede eski kapıyla paralel) · **Veri:** mevcut.
- **Nasıl sınanır:** Benzetim: sıfır hipotezi altında 10.000 tekrar, yanlış red oranı ≤ 0,05; geçmiş kapı kararlarıyla ≥ %90 uyum.
- **Kaynak:** Johari, Pekelis, Walsh (2017/2022) "Always valid inference" [arXiv:1512.04922](https://arxiv.org/abs/1512.04922) · Howard, Ramdas, McAuliffe, Sekhon (2021) Annals of Statistics [arXiv:1810.08240](https://arxiv.org/abs/1810.08240)
- **Durum:** bekliyor

### YH-18 · futbol · Gol sayısı dağılımında aşırı/eksik yayılım (Weibull sayım / NB) — model yolu
- **Açıklama:** Model yolu Poisson + Dixon-Coles. Weibull sayım (ya da negatif binom) dağılımı gol varyansını ayrı parametreyle öğrenir; 2,5 ve 3,5 alt/üst, KG ve net skor pazarlarına etki eder. Yalnız oransız yolda; piyasa yolundaki gol tablosu değişmez.
- **Beklenen kazanç:** Boshnakov ve ark., Weibull sayım + kopula modelinin Poisson'a göre daha iyi kalibre alt/üst olasılıkları verdiğini bildiriyor; tipik alt/üst ΔLL −0,001 … −0,004.
- **Efor:** M · **Risk:** orta (ızgara ve DC uyumu) · **Veri:** mevcut.
- **Nasıl sınanır:** `fb_guc_lab.py` 2,5 Ü ve net skor LL için SK.
- **Kaynak:** Boshnakov, Kharrat, McHale (2017) IJF [doi:10.1016/j.ijforecast.2016.11.006](https://doi.org/10.1016/j.ijforecast.2016.11.006) · Karlis & Ntzoufras (2003) JRSS-D [doi:10.1111/1467-9884.00366](https://doi.org/10.1111/1467-9884.00366)
- **Durum:** bekliyor

### YH-19 · canlı · Kırmızı kart etkisinin kayıtlardan öğrenilmesi
- **Açıklama:** CG'de kırmızı kart çarpanları sabit (0,72 / 1,25). Kayıtlı canlı anlık görüntülerde kart olayı biriktikçe (≥ 150 kartlı maç) çarpanlar dakika ve skor durumuna göre Bayes küçültmeyle (önsel = mevcut sabitler) öğrenilir.
- **Beklenen kazanç:** Kartlı anlık görüntülerde ΔLL −0,01 … −0,03; genel etki küçük (kartlı maç payı ~%10).
- **Efor:** S · **Risk:** düşük (önsel küçültme) · **Veri:** mevcut kayıtlar.
- **Nasıl sınanır:** `canli_guc_lab.py` kapısı; yalnız kartlı alt kümede de ΔLL < 0.
- **Kaynak:** Titman, Costain, Ridall, Gould (2015) JRSS-A "Joint modelling of goals and bookings in association football" [doi:10.1111/rssa.12075](https://doi.org/10.1111/rssa.12075) · Vecer, Kopriva, Ichiba (2009) JQAS "Estimating the effect of the red card in soccer" [ideas.repec](https://ideas.repec.org/a/bpj/jqsprt/v5y2009i1n8.html)
- **Durum:** bekliyor

### YH-20 · futbol · Milli takım maçları için Elo (CC0 açık geçmiş)
- **Açıklama:** Motorda milli takım ligi yok; milli maçlar yalnız piyasa yolunda. martj42/international_results (CC0, 1872 → bugün) ile Dünya Futbol Elo usulü (turnuva önemi K katsayısı, gol farkı çarpanı) puanlar; oransız milli maçlarda ve hazırlık maçlarında model yolu sağlanır, oranlıda konsey adayı olarak yarışır.
- **Beklenen kazanç:** Kapsam (oransız milli maçlarda tahmin) + Elo'nun milli maçlarda iyi bilinen başarısı; piyasa üstü katkı beklenmez.
- **Efor:** M · **Risk:** düşük · **Veri:** CC0, ücretsiz (yalnız türetilmiş puan depoya).
- **Nasıl sınanır:** Zaman sıralı: lig ortalamasına (taban) göre ΔLL üst sınırı < 0; oranlı alt kümede piyasaya karşı yalnız rapor.
- **Kaynak:** [martj42/international_results (CC0)](https://github.com/martj42/international_results) · Hvattum & Arntzen (2010) [doi:10.1016/j.ijforecast.2009.10.002](https://doi.org/10.1016/j.ijforecast.2009.10.002) · Lasek, Szlávik, Bhulai (2013) "The predictive power of ranking systems in association football" [Inderscience](https://inderscience.com/offer.php?id=52339)
- **Durum:** bekliyor

### YH-21 · futbol · Hiyerarşik Bayes küçültme ile yeni / az veri liglerde güç önseli
- **Açıklama:** Oransız küçük liglerde takım güçleri az maçla gürültülü. Takım gücü ~ N(lig ortalaması, τ_lig²), τ_lig ve ev avantajı ligler arası önselden (ampirik Bayes) öğrenilir; sezon başında ve ligde < 45 maç varken de tahmin yapılabilir (şu an uygunluk eşiği dışında kalanlar).
- **Beklenen kazanç:** Kapsam artışı (eşik altı maçlar) + küçük liglerde ΔLL −0,002 … −0,005; Baio & Blangiardo küçültmenin aşırı uyumu azalttığını gösteriyor.
- **Efor:** M · **Risk:** orta · **Veri:** mevcut.
- **Nasıl sınanır:** `fb_guc_lab.py espn` SK + yeni kapsanan maçlarda taban modele göre ΔLL üst sınırı < 0.
- **Kaynak:** Baio & Blangiardo (2010) J. Applied Statistics [doi:10.1080/02664760802684177](https://doi.org/10.1080/02664760802684177) · Ley, Van de Wiele, Van Eetvelde (2019) Statistical Modelling [doi:10.1177/1471082X18817650](https://doi.org/10.1177/1471082X18817650)
- **Durum:** bekliyor

### YH-22 · arayüz · "Neden bu tahmin?" kısa açıklaması
- **Açıklama:** Maç kartında olasılığa en çok katkı yapan 2–3 etken (piyasa, güç farkı, form/şut, kadro, dinlenme) yüzde puan olarak; yalnız modelde gerçekten kullanılan ve kapıdan geçmiş girdiler gösterilir. Yanıltıcı kesinlik dili yok.
- **Beklenen kazanç:** Anlaşılırlık ve güven; açıklamalı olasılık sunumu kullanıcıların olasılığı doğru yorumlamasına yardım eder (ölçülebilir: sohbet asistanına "neden" sorularının azalması, kalite botu).
- **Efor:** M · **Risk:** düşük–orta (performans; yasaklı kelime taraması) · **Veri:** mevcut.
- **Nasıl sınanır:** Duman + kalite testleri, açılış süresi artışı < 50 ms, `bot_coach` "neden" niyetli soruların faydalı oranı düşmüyor.
- **Kaynak:** Lundberg & Lee (2017) NeurIPS "A unified approach to interpreting model predictions" [arXiv:1705.07874](https://arxiv.org/abs/1705.07874) · Joslyn & LeClerc (2012) [doi:10.1037/a0025185](https://doi.org/10.1037/a0025185)
- **Durum:** bekliyor

---

## Ücretsiz veri kaynakları (durum)

| Kaynak | Lisans / şart | Kullanım | Not |
|---|---|---|---|
| football-data.co.uk (sonuç, oran, şut, korner) | ücretsiz, atıf | bağlı | YH-02, YH-03 mevcut sütunları kullanır |
| openfootball (CC0) | kamu malı | bağlı (kupa) | — |
| Club Elo API | açık, atıf | bağlı (kupa çapası) | — |
| martj42/international_results | CC0 | YH-20 | yalnız türetilmiş puan |
| ESPN herkese açık uç noktaları | belgelenmemiş, ücretsiz | bağlı | YH-12, YH-14, YH-16; ham yanıt commit edilmez |
| StatsBomb open data | kullanıcı sözleşmesi + atıf | yalnız araştırma | güncel sezon yok; üretim girdisi değil |
| Understat / FBref | kazıma, şartlar uygun değil | kullanılmaz | — |
| tjk.org, atyarisi.com ve alt alanları, archive.org kopyaları | yasak | **asla** | — |
