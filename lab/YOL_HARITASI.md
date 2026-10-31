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

### YH-23 · futbol · Shin yöntemiyle marj ayıklama (ve odds-ratio) — sunulan piyasa olasılığı
- **Açıklama:** Uygulamanın sunduğu piyasa olasılığı (`js/core.js implied()`, `fitMarket`, Python aynaları `ui_market_lam` / `pazar.py` / `collector.py`) marjı power yöntemiyle ayırıyor; motorun öğrenme hedefi (`market_xg`) ise araştırmacı botun seçtiği yöntemi (`data/research.json → devig`) kullanıyor. Shin (içeriden bilgi payı z), odds-ratio (Cheung 2015), oransal ve toplamsal yöntemler aynı arşivde (football-data derin arşivi + season.json; kilitli iddaa arşivi) 1X2 ve 2,5 A/Ü ayrı ayrı power'a karşı ölçülür; geçen yöntem tek fonksiyon olarak Python ve JS'de birebir aynı uygulanır.
- **Beklenen kazanç:** Štrumbelj (2014) Shin olasılıklarının oransal yöntemden ve çoğu durumda diğerlerinden daha iyi kalibre olduğunu bildiriyor; yüksek marjlı (iddaa ~%18) oranlarda yöntem farkı büyür. Tipik ΔLL −0,0005 … −0,003.
- **Efor:** S · **Risk:** düşük (bayrakla geri alınır; kalibrasyon katmanları power yolunda öğrenildiği için geçişte yeniden öğrenme gerekir) · **Veri:** mevcut, ücretsiz.
- **Nasıl sınanır (kapı):** SK — zaman sıralı arşivde power'a göre ΔLL %95 GA (lig×gün blok bootstrap, B = 2000) üst sınırı < 0, iki zaman yarısında ΔLL < 0, ΔBrier ≤ 0; 1X2 ve A/Ü ayrı. Geçerse `data/devig.json {yontem}` bayrağı, Python–JS eşitlik testi, 14 gün izleme.
- **Kaynak:** Štrumbelj (2014) IJF 30(4) "On determining probability forecasts from betting odds" [EconBiz](https://econbiz.de/Record/on-determining-probability-forecasts-from-betting-odds-%C5%A1trumbelj-erik/10010517776) · Shin (1993) Economic Journal 103(420) "Measuring the incidence of insider trading in a market for state-contingent claims" [IDEAS](https://ideas.repec.org/a/ecj/econjl/v103y1993i420p1141-53.html) · Cheung (2015) "Fixed-odds betting and traditional odds" (çalışma notu; R `implied` paketinde `or` yöntemi)
- **Durum:** gölgede (2026-10-29) — hiçbir yöntem power'ı standart kapıda geçmedi; üretim (power) değişmedi. `lab/marj_lab.py` → `data/marj_lab.json`, haftalık gölge ölçüm `keskin-lab.yml` (pazar).
  ΔLL = aday − power, lig×gün blok bootstrap B = 2000. **iddaa kilitli arşivi** (uygulamanın gösterdiği oran, marj %17,9; 2026-10-24…29):
  1X2 n = 1.705 — Shin −0,0020 [−0,0044, +0,0003] yarılar −0,0041 / +0,0001; odds-ratio −0,0019 [−0,0039, +0,0001] yarılar −0,0038 / +0,0001; oransal −0,0014 [−0,0067, +0,0039]; toplamsal −0,0010 [−0,0027, +0,0005] (yarılar −0,0018 / −0,0002).
  A/Ü n = 1.353 — Shin = toplamsal −0,0012 [−0,0025, +0,0002] yarılar −0,0024 / +0,0001; odds-ratio −0,0008 [−0,0018, +0,0001]; oransal −0,0016 [−0,0047, +0,0014].
  **Derin arşiv** (football-data 2021→ + season.json, marj %6,8): 1X2 n = 66.990 — power en iyi ya da eşdeğer (Shin +0,0001 [+0,00002, +0,0002], odds-ratio +0,0002, oransal +0,0008, toplamsal −0,00004 [−0,0001, +0,00002]); A/Ü n = 40.757 — tümü ±0,0002 içinde, power ≤.
  Yorum: yüksek marjlı iddaa oranlarında Shin / odds-ratio yönü olumlu ama yalnız 5 günlük arşivde ve ikinci yarıda sıfır; düşük marjda power en iyi. Arşiv büyüdükçe (iddaa ≥ 5.000 maç) haftalık ölçüm yeniden karar verir; `aday` çıkarsa geçiş: tek fonksiyon (Python `devig` + JS `implied`), bayrak `data/devig.json {yontem}`, eşitlik testi, 14 gün izleme. Not: motorun öğrenme hedefi (`market_xg`) araştırmacı bot kararıyla zaten `shin` kullanıyor (`data/research.json`); bu madde yalnız sunulan olasılığı kapsar.

### YH-24 · futbol · ClubElo ücretsiz API ile bağımsız güç sinyali (kupa / oransız maçlar)
- **Açıklama:** Club Elo günlük puanları (tüm Avrupa kulüpleri) oransız lig ve kupa maçlarında bağımsız güç sinyali olarak topluluğa (Maher-Poisson + Elo + pi) aday girdi; oranlı maçlarda yalnız konsey adayı. Şu an yalnız kupa çapası olarak kullanılıyor.
- **Beklenen kazanç:** Oransız ve ligler arası (kupa, Avrupa) maçlarda ΔLL −0,002 … −0,008; kendi Elo'muzla yüksek ilişki nedeniyle lig içi katkı küçük.
- **Efor:** S · **Risk:** düşük–orta (takım adı eşleme; kaynak kesintisi) · **Veri:** Club Elo API, açık, atıf (yalnız türetilmiş puan depoya).
- **Nasıl sınanır (kapı):** `fb_guc_lab.py` zaman sıralı SK; kupa alt kümesinde de ΔLL < 0.
- **Kaynak:** [clubelo.com API](http://clubelo.com/API) · Hvattum & Arntzen (2010) [doi:10.1016/j.ijforecast.2009.10.002](https://doi.org/10.1016/j.ijforecast.2009.10.002)
- **Durum:** beklemede (2026-10-29): ClubElo ücretsiz API kapalı, kayıt kapalı; sayfa kazıma yapılmaz. Kendi Elo'muz zaten toplulukta (Elo+pi) — ayrı madde gerekmez

### YH-25 · futbol · Hiyerarşik Bayes güç modeli (Baio & Blangiardo 2010)
- **Açıklama:** Takım hücum/savunma güçleri lig içinde ortak önselden (değiştirilebilir hiyerarşi) çekilir; az maçlı takımlar lig ortalamasına küçülür, büyük skorlar tek başına gücü uçurmaz (karışım önseli). Ampirik Bayes ya da Laplace yaklaşımıyla sıfır maliyetle Actions'ta çalışır. **Not:** YH-21 (küçük liglerde güç önseli) ile aynı model ailesi — birlikte uygulanabilir; biri yayına alınırsa diğeri `birleştirildi` yapılır.
- **Beklenen kazanç:** Model yolunda ΔLL −0,002 … −0,006 (özellikle sezon başı ve küçük ligler); aşırı uyumun azalması.
- **Efor:** M · **Risk:** orta (hesap süresi; Dixon-Coles ile uyum) · **Veri:** mevcut, ücretsiz.
- **Nasıl sınanır (kapı):** `fb_guc_lab.py espn` / `derin` SK; sezonun ilk 8 haftasında ayrıca ΔLL < 0.
- **Kaynak:** Baio & Blangiardo (2010) J. Applied Statistics [doi:10.1080/02664760802684177](https://doi.org/10.1080/02664760802684177)
- **Durum:** reddedildi (2026-10-29) — `lab/hb_guc_lab.py` → `data/hb_guc_lab.json`; üretim değişmedi.
  Aday: lig×hafta ampirik Bayes (eşlenik Gamma; τ² moment yöntemi, hücum/savunma ayrı, ligler arası önsele n0 ile çekme; isteğe bağlı gol tavanı), yalnız geçmiş maçlarla; ızgara (τ²_0, n0, tavan; 18) seçim diliminde (< 2026-04-01) → (0,03, 5, tavansız). Kıyas: üretim model yolu = topluluk C4 (Poisson decay 0,003 / prior 10 + Elo + pi, aylık genişleyen yığın), aday = aynı topluluk, Poisson girdisi HB.
  Seçim diliminde iyi görünüyordu (C4 LL 1,0060 vs 1,0097, n = 2.503) ama **sınamada tutmadı** (n = 4.397, 28 oransız lig, lig×gün blok B = 2000): 1X2 ΔLL +0,0016 [−0,0003, +0,0034] yarılar +0,0009 / +0,0023, ΔBrier +0,0010, sezonun ilk 8 haftası (n = 828) +0,0045; A/Ü ΔLL +0,0011 [+0,0001, +0,0021]; yalnız Poisson ΔLL +0,0128 [+0,0085, +0,0169]. Alfa yatırımı (fb_model-2026): α 0,031 / 0,021, iki test geçmedi.
  Yorum: lig başına kestirilen τ² (çoğu ligde 0,03–0,05) üretimin tek önselinden (prior 10 ≈ τ² 0,08) daha sıkı küçültüyor; Elo/pi zaten az maçlı takımları topluluğa taşıdığından ek küçültme bilgi eklemiyor. YH-21 (eşik altı kapsam) aynı `hb_fit`'i yeniden kullanabilir; orada ölçüt kapsam + taban modele göre ΔLL olduğu için ayrı sınanmalı.

### YH-26 · altyapı · Uyumlu (conformal) tahmin aralıkları
- **Açıklama:** Olasılık ve gol / sayı beklentilerine dağılımdan bağımsız, kapsama güvenceli aralıklar: yürüyen pencerede (zaman sıralı, uyarlamalı conformal) kalibrasyon kümesinden uygunsuzluk puanları; basket toplam sayı ve fark, futbol gol beklentisi ve olasılık bantları için "%80 aralık". Arayüzde yalnız kapsaması tuttuğu kanıtlanmış aralık gösterilir.
- **Beklenen kazanç:** Belirsizliğin dürüst gösterimi; hedef kapsama ±2 puan içinde (şu an aralık yok). Doğrudan LL kazancı beklenmez.
- **Efor:** M · **Risk:** düşük (yalnız gösterim; dağılım kayması → uyarlamalı sürüm) · **Veri:** mevcut, ücretsiz.
- **Nasıl sınanır (kapı):** Zaman sıralı sınamada gerçekleşen kapsama hedefin ±2 puanı içinde, iki zaman yarısında da; aralık genişliği taban (sabit genişlik) yöntemden dar ya da eşit.
- **Kaynak:** Angelopoulos & Bates (2023) "Conformal prediction: a gentle introduction" [arXiv:2107.07511](https://arxiv.org/abs/2107.07511) · Gibbs & Candès (2021) NeurIPS "Adaptive conformal inference under distribution shift" [arXiv:2106.00170](https://arxiv.org/abs/2106.00170)
- **Durum:** yayında — kısmi (2026-10-29, v146; yalnız basket; 14 gün izleme) — `lab/aralik_lab.py` → `data/aralik_lab.json` + bayrak `data/bk_aralik.json`, haftalık yenileme `bk-tempo-lab.yml`; arayüz katmanı `aralik-v146` (`js/katmanlar.js`).
  Üretim ridge'i haftalık ileri yürüyüş; aralıklar yalnız önceki haftaların artıklarından (lig başına son 400). Yöntem/γ her ligin ilk yarısında seçildi, karar ikinci yarıda (iki tarih yarısı). Taban T0 = seçim diliminde donmuş sabit genişlik.
  **Geçti:** pro toplam (NBA/WNBA/GL) uyarlamalı conformal γ = 0,01 — n = 1.093, kapsama %79,7 / %80,9, genişlik 46,4 ≤ T0 47,5 · kolej toplam (γ = 0,01) — n = 4.930, %79,8 / %79,7, 42,2 ≤ 44,3 · kolej fark (γ = 0,005) — %80,1 / %79,9, 29,1 ≤ 32,7.
  **Geçmedi:** pro fark (asimetrik; %78,2 / %77,9, 35,5 > T0 34,9) · Avrupa toplam/fark (n = 159; yarılar %83,3 / %77,8) · NBL/EC (yetersiz). Yayın koşulu lig başına da: sınamada ≥ 100 maç ve kapsama %80 ± 4.
  Arayüz: aralık yalnız piyasa çizgisiyle birleştirilmemiş maçta (sınanan yol = takım-gücü tahmini); fark aralığı kscale = 1 ve dinlenme düzeltmesi yokken. Futbol gol beklentisi / olasılık bantları: sayım hedefi kesikli olduğundan %80 kapsamaya tam oturmaz — ayrı madde olarak ele alınmalı.

### YH-27 · basket · Dean Oliver dört faktör / verimlilik modeli
- **Açıklama:** Kutu skorundan takım başına dört faktör (eFG%, top kaybı oranı, hücum ribaund oranı, serbest atış oranı; hücum ve savunma) ve hücum / savunma verimliliği (100 hücum başına sayı); yürüyen ortalamalar ridge'e ek girdi olarak fark ve kazanma olasılığında sınanır. YH-14 (tempo) bulgusu: sayı ridge'i tempo × verimi büyük ölçüde taşıyor — burada ek bilgi yalnız faktör ayrışımından beklenir.
- **Beklenen kazanç:** Model yolu fark MAE −%1…−%3, kazanma ΔLL −0,002 … −0,006 (literatürde dört faktör kazanma varyansının büyük kısmını açıklar).
- **Efor:** M · **Risk:** orta (YH-14 gibi fark çıkmayabilir; sızıntı → yalnız maç öncesi kutu skorları) · **Veri:** ESPN herkese açık kutu skorları, ücretsiz (ham veri commit edilmez).
- **Nasıl sınanır (kapı):** `bk_tempo_lab.py` deseni, zaman sıralı SK; NBA / WNBA / diğer ayrı rapor.
- **Kaynak:** Oliver (2004) *Basketball on Paper* · Kubatko ve ark. (2007) JQAS [doi:10.2202/1559-0410.1070](https://doi.org/10.2202/1559-0410.1070)
- **Durum:** reddedildi (2026-10-29; SK geçmedi, üretim değişmedi) — `lab/bk_dortfaktor_lab.py` → `data/bk_dortfaktor_lab.json`, `bk-dortfaktor-lab.yml` haftalık yeniden ölçüm (yalnız ölçüm; sınama run 40964901925, commit f6ecdff).
  Pro ligler (NBA/WNBA/G League/NBL): ESPN maç özeti kutu skoru → dört faktörün tamamı (eFG%, FTr, TOV%, ORB%); kolej: skor tablosu → eFG%, FTr, ribaund payı. Faktör başına ridge (basket.fit) + önceki haftaların örneklem dışı satırlarıyla yığma; taban da aynı yığma (yalnız taban fark) — haftalık ileri yürüyüş, sınama n = 12.502.
  Kazanma ΔLL +0,0012 [GA −0,0003, +0,0027], ΔBrier +0,0005, p = 0,95; dilim 1 ΔLL +0,0003, dilim 2 +0,0021 [+0,00004, +0,0043] (anlamlı kötü) → **geçmedi**. Fark ΔMAE −0,033 sayı [−0,074, +0,005] (yalnız dilim 1'de anlamlı).
  Grup: NBA n = 1.151 ΔLL +0,0025 [−0,0034, +0,0089] · WNBA n = 388 +0,0065 [−0,0006, +0,0144] (MAE anlamlı kötü) · kolej n = 10.709 +0,0007 [−0,0010, +0,0024] · G League n = 254 (NBL kapsam 54 maç → dışarıda) — hiçbir grup geçmedi.
  Yorum: YH-14 ile aynı — sayı ridge'i faktörlerin taşıdığı bilgiyi zaten içeriyor; faktör ayrışımı kazanma olasılığına ek bilgi katmıyor, yığma yalnız gürültü ekliyor.

### YH-28 · at · Bolton–Chapman / Benter çok aşamalı birleşim
- **Açıklama:** YH-08 bulgusu: sabah modeli kapanış piyasasına bilgi ekliyor (**a = 0,314 [0,256, 0,375]**, b = 0,827, n = 3.282 koşu). Benter'in ikinci aşaması `p ∝ exp(a·ln p_model + b·ln q_piyasa)` şu an yalnız ölçüm; çok aşamalı birleşim bu ağırlıkları (alan büyüklüğü, koşu türü, piyasa derinliği / erken–geç oran kovaları gibi) koşullu öğrenip sunulan at olasılığına uygular; birinci aşama koşullu logit (Bolton–Chapman) zaten var.
- **Beklenen kazanç:** YH-08 ileri yürüyüşü: harman − kapanış ΔLL −0,0137 [−0,0191, −0,0079]; koşullu ağırlıklarla ek −0,001 … −0,004. Kilit anında kapanış oranı yok — kazanç yalnız piyasa oranı mevcutken sunulan güncel olasılıkta.
- **Efor:** M · **Risk:** orta (kilit anı / kapanış ayrımı; sızıntı) · **Veri:** mevcut izinli ayna kaynağı, ücretsiz (TJK / atyarisi.com yok).
- **Nasıl sınanır (kapı):** Koşu-günü blok bootstrap, aylık ileri yürüyüş; mevcut harmana göre ΔLL %95 GA üst < 0, iki yarıda < 0.
- **Kaynak:** Bolton & Chapman (1986) Management Science [doi:10.1287/mnsc.32.8.1040](https://doi.org/10.1287/mnsc.32.8.1040) · Benter (1994) [World Scientific](https://worldscientific.com/doi/abs/10.1142/9789812819192_0019)
- **Durum:** reddedildi (2026-10-30; kapı geçmedi, üretim değişmedi) — `lab/at/benter_kosullu_lab.py` → `data/at/benter_kosullu_lab.json`, `at-benter-lab.yml` haftalık yeniden ölçüm (cumartesi; yalnız ölçüm).
  Aylık ileri yürüyüş, n = 2.492 koşu / 149 gün (2026-05 … 2026-10; toplam 3.282 koşu). Birincil aday K4 (alan + tür + favori q + hipodrom kovaları, L2 λ = 30) − tek (a, b) harman: **ΔLL +0,00524 [+0,00218, +0,00838]**, yarılar +0,00854 / +0,00194 (kötüleşme). Tek aile adayları da geçmedi: alan +0,00162 [−0,00013, +0,00349], tür +0,00129 [+0,00014, +0,00250], favori q +0,00215 [+0,00058, +0,00369], hipodrom +0,00084 [−0,00084, +0,00254]; λ = 5 / 150 duyarlılığı +0,00722 / +0,00256. Sonuç: koşullu ağırlıklar örneklem dışında aşırı uyuyor; tek (a, b) yeterli. Sınama run 40991220382, commit e464b62.

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
- **Durum:** gölgede (2026-10-28; 1X2 reddedildi, 2,5 A/Ü kapıyı geçti ama etki pratik eşiğin altında) — `lab/keskin_piyasa.py` → `data/keskin_piyasa.json`,
  `keskin-lab.yml` haftalık (yalnız ölçüm). football-data 22 ana lig 2020–2026 + 16 yeni lig (68.078 maç), power marj + T yürüyen pencerede, yıllık katlar 2022–2025,
  lig×gün blok bootstrap B = 2000; referans = Avg (üretim). **1X2 maç öncesi** (n = 26.168): PS ΔLL −0,00018 [GA −0,00044, +0,00008], uzlaşı (w ≈ 0,9–1)
  −0,00020 [−0,00046, +0,00006], isabet −0,07…−0,09 puan → **geçmedi**. **1X2 kapanış** (yeni ligler dahil, n = 42.397): PS −0,00017 [−0,00045, +0,00010],
  son iki katta +0,0001/+0,0011 → **geçmedi**. **2,5 A/Ü maç öncesi** (n = 26.087): PS ΔLL −0,00018 [−0,00034, −0,00003], yarılar −0,00024/−0,00012,
  ΔBrier −0,00015, isabet +0,09 puan, p = 0,011 → **SK geçti**; ancak kazanç beklenenin (−0,001…) ~1/10'u ve üretime almak f.ou'yu (gösterilen ve değer
  hesabında kullanılan oranı) değiştirir → yayına alınmadı, haftalık izlemede. Yeniden değerlendirme: ≥ 3 ardışık hafta geçerse yalnız olasılık yoluna
  (gösterim değişmeden) ayrı alanla bağlanır. (b) iddaa × keskin piyasa uzlaşısı: tazeveri 2026-10-23'ten beri (FD liglerinde ≈ 250 sonuçlu maç) → ≥ 30 gün sonra.
  Commit: dal `yh02-keskin` (4d120b8), sınama çalışması 40670911382.

### YH-03 · futbol · Şut tabanlı güç robotu (GAP / sözde-xG) — oranlı ligler
- **Açıklama:** `update.py` football-data'dan isabetli şutu (`HST/AST` → `m["st"]`) zaten indiriyor ama yalnız korner/kart modelinde kullanıyor. Wheatcroft'un GAP puanı gibi her takıma şut ve isabetli şut üretme/yeme gücü (ev/deplasman ayrı, üstel unutma) çıkar; beklenen isabetli şut → beklenen gol dönüşümü öğrenilir. `guc.py` topluluğuna 4. robot ve 2,5 üst yığınlayıcısına girdi olarak eklenir; oranlı maçta piyasa ile karışım `karisim` gölgesinde ölçülür.
- **Beklenen kazanç:** Şut istatistikleri gole göre daha az gürültülü; literatürde şut tabanlı puanlar gol tabanlılara bilgi ekliyor ve piyasaya karşı bile bilgi taşıyor (Wheatcroft). Tipik model yolu ΔLL −0,003 … −0,010; piyasa üstüne katkı ≈ 0 … −0,002.
- **Efor:** M · **Risk:** orta (sızıntı: yalnız maçtan önceki şutlar) · **Veri:** mevcut, ücretsiz.
- **Nasıl sınanır:** `lab/fb_guc_lab.py derin` alanında SK (model yolu) + ayrı olarak piyasa üstü yığmada ΔLL üst sınırı < 0 ise `karisim` adayına bağlanır.
- **Kaynak:** Wheatcroft (2021) J. Sports Analytics 7(2) [doi:10.3233/JSA-200462](https://doi.org/10.3233/JSA-200462), [arXiv:2001.09097](https://arxiv.org/abs/2001.09097) · Wheatcroft (2020) IJF "A profitable model for predicting the over/under market" [doi:10.1016/j.ijforecast.2019.11.001](https://doi.org/10.1016/j.ijforecast.2019.11.001)
- **Durum:** reddedildi (2026-10-28; 1X2 ve piyasa üstü kapıyı geçmedi; 2,5 A/Ü model yolu sınırda → haftalık gölge ölçüm) — `lab/sut_guc_lab.py` → `data/sut_guc_lab.json`,
  `sut-guc-lab.yml` haftalık (yalnız ölçüm). football-data 22 ana lig 2020–2026 isabetli şut (HST/AST), GAP λ/φ seçim diliminde (< 2024-07-01) seçildi → λ = 0,2, φ = 0,6;
  yığınlayıcılar aylık genişleyen pencere, lig×gün blok bootstrap B = 2000, sınama n = 15.461 (2024-07 → 2026-10). Model yolu 1X2 (Poisson+Elo+pi → +GAP): ΔLL −0,00002
  [GA −0,00054, +0,00047], yarılar −0,00036/+0,00031 → **geçmedi**. Model yolu 2,5 A/Ü: ΔLL −0,00033 [−0,00082, +0,00014], yarılar −0,00032/−0,00035, ΔBrier −0,00016,
  isabet −0,11 puan, p = 0,085 > α = 0,05 → **geçmedi (sınırda)**. Piyasa üstü 1X2: +0,00007 [−0,00019, +0,00031]; piyasa+topluluk üstü: +0,00012 [−0,00011, +0,00036];
  piyasa üstü 2,5 A/Ü: −0,00004 [−0,00025, +0,00017] → **geçmedi** (`karisim` adayına bağlanmadı). Yorum: isabetli şut bilgisi Poisson+Elo+pi ve piyasada büyük ölçüde zaten var;
  beklenen −0,003…−0,010 görülmedi. Yeniden değerlendirme: haftalık ölçümde A/Ü ≥ 3 ardışık hafta SK geçerse yalnız oranlı liglerin model yolu A/Ü'süne (gösterim değişmeden) bayraklı bağlanır.
  Commit: dal `yh03-sut-guc` (a86905a4), sınama çalışması 40705069565.

### YH-04 · basket · Dinlenme günü, arka arkaya maç ve deplasman serisi düzeltmesi
- **Açıklama:** `bk_games.json` maç tarihlerinden her takım için dinlenme günü (0 = arka arkaya), son 7 günde maç sayısı ve üst üste deplasman sayısı türetilir; ridge güç modelinin beklenen sayı farkına öğrenilen toplamsal düzeltme olarak eklenir (lig grubuna göre: pro / avrupa / kolej).
- **Beklenen kazanç:** NBA'de dinlenme eksikliği ev avantajının önemli bir parçası; 538 modeli arka arkaya maçı ~1–2 sayı (≈ 25–45 Elo) düzeltir. Tipik MS ΔLL −0,002 … −0,005 (NBA/WNBA), toplam sayı MAE küçük iyileşme.
- **Efor:** S · **Risk:** düşük · **Veri:** mevcut (ESPN / EuroLeague takvimi), ücretsiz.
- **Nasıl sınanır:** `lab/bk_gelistir.py` adayı olarak: gün kümeli bootstrap ΔLL üst sınırı < 0, ΔBrier < 0, isabet düşmüyor, iki zaman diliminde de.
- **Kaynak:** Entine & Small (2008) JQAS "The Role of Rest in the NBA Home-Court Advantage" [UPenn](https://repository.upenn.edu/entities/publication/e871ae9f-87db-40bd-922e-53064fae121f) · [FiveThirtyEight: NBA tahmin yöntemi](https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- **Durum:** gölgede (2026-10-28; kapıyı geçmedi) — `scripts/bk_dinlenme.py` (özellikler: b2b < 36 saat, dinlenme 0–3 gün, üst üste deplasman 0–4,
  salon koordinatından seyahat km — yalnız NBA/WNBA), `lab/bk_dinlenme_lab.py` → `data/bk_dinlenme_lab.json`, bayrak `data/bk_dinlenme.json`
  (`kullan.<grup>`, şu an üçü de false). Sınama: `bk_games.json` arşivi (2025-04 → 2026-10, 8 lig), üretim fit'i haftalık ileri yürüyüş, β grup başına
  yalnız önceki haftaların artıklarından (ridge, λ = 200), σ önceki haftalardan; gün kümeli bootstrap B = 2000. Mevcut n = 12.557, LL 0,5399, isabet %71,67.
  **pro** (NBA·WNBA·GL·NBL, n = 2.262): b2b ΔLL −0,00065 [GA −0,00146, +0,00017]; b2b+dinlenme −0,00085 [−0,00188, +0,00020]; tam −0,00127
  [−0,00278, +0,00046], isabet −0,35 puan; literatür ön bilgili b2b (1,6 sayı) −0,00063 [−0,00217, +0,00086] → **geçmedi** (öğrenilen b2b β ≈ 1,1–1,4 sayı,
  538 ile uyumlu ama örnek küçük). **kolej** (n = 9.859): tam −0,00030 [−0,00119, +0,00058], isabet −0,13 puan → geçmedi. **avrupa** (n = 436): tam +0,00074 → geçmedi
  (yurt içi lig maçları veride yok, dinlenme özelliği Avrupa'da ölçülemiyor). Üretim: kilitli kayda gölge Δ (`ydg`) yazılır, `bk_dinlenme.json.golge` ölçer;
  kapı gece (basket.py → lab/bk_dinlenme_lab.py --yaz) her gün yeniden sınanır, geçen grupta bayrak açılır (kilit + fikstür `yd`, uygulamada bkPredict),
  14 gün izleme, ΔLL > +0,002 (n ≥ 30) olursa otomatik geri alma (30 gün yeniden açılmaz).

### YH-05 · canlı · Basket canlı kazanma olasılığı: kayıt + Brown hareketi kalibrasyonu + piyasa çapası
- **Açıklama:** Uygulamadaki `bkLivePred` Stern tipi normal model kullanıyor ama σ (`p.sm`) ve sürüklenme hiç canlı veriyle sınanmadı ve kayıt yok. (1) Canlı kayıt işine basket anlık görüntüsü ekle (skor, kalan süre, maç öncesi olasılık / çizgi); (2) σ'yı kalan süreye göre ve sürüklenmeyi maç öncesi piyasa çizgisinden (Polson–Stern "örtük oynaklık") öğren; (3) Platt ile kalibre et; tek formül sunucu ve uygulamada birebir.
- **Beklenen kazanç:** Kalibrasyonsuz canlı modellerde son çeyrekte aşırı güven yaygın; tipik canlı ΔLL −0,01 … −0,03 (özellikle 4. çeyrek), kalibrasyon hatası yarıya.
- **Efor:** M · **Risk:** orta (saat ayrıştırma, uzatma) · **Veri:** ESPN / EuroLeague canlı akışı (zaten okunuyor), ücretsiz.
- **Nasıl sınanır:** `canli_guc_lab.py` protokolü: sınama günü D için yalnız D'den önce biten maçlarla öğren; ≥ 600 anlık görüntü / ≥ 120 maç; maç-blok bootstrap ΔLL üst sınırı < 0; Brier kötüleşmiyor; günlerin çoğunda iyi.
- **Kaynak:** Stern (1994) JASA "A Brownian motion model for the progress of sports scores" [doi:10.1080/01621459.1994.10476866](https://doi.org/10.1080/01621459.1994.10476866) · Polson & Stern (2015) JQAS [doi:10.1515/jqas-2014-0095](https://www.degruyterbrill.com/document/doi/10.1515/jqas-2014-0095/html)
- **Durum:** gölgede, kayıt başladı (2026-10-28; çevrimdışı sınama geçti, canlı kapı veri bekliyor) — `scripts/bk_canli.py`, bayrak `data/bk_canli.json`
  (`kullan: false`). Model: P = Φ((d + w·μ·r) / max(1,5; k·σ·r^(0,5+γ))), σ = sm·√(toplam / 2mu), μ = σ·Φ⁻¹(p0) (p0 = uygulamada gösterilen maç öncesi
  olasılık: çapa / piyasa harmanı / model); sunucu `p_yeni` ve uygulama `bkLivePred` birebir (Node ↔ Python 6 hane aynı). (a) Kayıt: `live-log.yml` arka plan adımı,
  5 dk arayla ESPN canlı (NBA, WNBA, NBL, GL, NCAA; EuroLeague/EuroCup ESPN'de yok) → `data/archive/bk_live/<gün>.json` (maç öncesi p0, fark, σ, toplam + anlık
  görüntüler eski/yeni olasılıkla), maç bitince sonuç (ESPN, olmazsa bk_predlog/bk_games). (b) Çevrimdışı kanıt (`lab/bk_canli_lab.py` → `data/bk_canli_lab.json`):
  arşivdeki 12.556 maçın çeyrek / devre sonu skorları (27.674 anlık görüntü), maç öncesi fark ve σ üretim modelinin ileri yürüyüşünden, (k, w, γ) haftalık yalnız
  önceki haftalarla: LL 0,4053 → 0,4016, ΔLL −0,00365 [maç-blok GA −0,00505, −0,00221], yarılar −0,00252 / −0,00470, ΔBrier −0,00097, isabet %80,19 → %80,23
  → **geçti** (en çok 3. çeyrek sonunda: 0,3161 → 0,3108). Öğrenmesiz sürüm (k = w = 1, γ = 0) ΔLL +0,00001 → kazanç öğrenilen parametrelerden:
  k = 1,2 (σ daha geniş), w = 1,4 (maç öncesi güç farkı r ile doğrusaldan güçlü sürüyor), γ = 0. Bunlar `onbilgi` olarak bayrak dosyasında.
  (c) Kapı: gece (basket.py, günde bir) ≥ 300 sonuçlu anlık görüntü ve ≥ 40 maçta gün sıralı (haftalık öğrenme, ön bilgiye çekilmiş) maç-blok bootstrap
  ΔLL GA üst < 0, iki yarı < 0, ΔBrier ≤ 0, isabet düşmez → `kullan: true` (uygulama yeni formüle geçer); 14 gün izleme, ΔLL > +0,002 (≥ 20 maç) → geri alma.
  Kalan: Platt kalibrasyonu ve piyasa canlı çizgisi (Polson–Stern örtük oynaklık) kayıt birikince ayrı aday.

### YH-06 · futbol · Beta kalibrasyonu (2,5 alt/üst, KG ve pazar motoru ek pazarları)
- **Açıklama:** `pazar.py` ek kalibrasyonda yalnız Platt / sıcaklık deniyor. Beta kalibrasyonu (3 parametre: ln p ve ln(1−p) ayrı eğim) asimetrik sapmayı (ör. düşük olasılıklı "üst" uçlarında) düzeltebilir; Platt'ı özel durum olarak içerir. İzotonik yalnız karşılaştırma için (büyük örnekte).
- **Beklenen kazanç:** Kalibrasyon makalelerinde beta, Platt'a göre çoğu veri kümesinde daha düşük log-kayıp; tipik ΔLL −0,0005 … −0,002 pazar başına.
- **Efor:** S · **Risk:** düşük · **Veri:** mevcut.
- **Nasıl sınanır:** `pazar.py` aylık ileriye dönük sınaması: İKİ zaman diliminde de LL düşmeli + SK.
- **Kaynak:** Kull, Silva Filho, Flach (2017) AISTATS [PMLR v54](https://proceedings.mlr.press/v54/kull17a.html) · Walsh & Joshi (2024) "Machine learning for sports betting: should model selection be based on accuracy or calibration?" [Bath](https://researchportal.bath.ac.uk/en/publications/machine-learning-for-sports-betting-should-model-selection-be-bas/)
- **Durum:** reddedildi (2026-10-28; beta Platt'tan ayırt edilemiyor, hiçbir pazarda kapı geçmedi) — `lab/beta_kal_lab.py` → `data/beta_kal_lab.json`.
  Aylık ileriye dönük (yalnız önceki aylarla), 2025-12-01…2026-10-26, n = 6.659 maç, lig×gün blok bootstrap B = 2000, α = 0,05/7. Aday beta vs üretim yolu (Platt kabul edilen pazarda Platt, diğerlerinde ham):
  U15 ΔLL +0,00013 [−0,00011, +0,00038] · U35 −0,00001 [−0,00005, +0,00005] · KGV +0,00001 [−0,00012, +0,00015] · İY 0,5 Ü +0,00016 [−0,00043, +0,00076] ·
  İY 1,5 Ü 0,00000 [−0,00002, +0,00002] · 2Y 0,5 Ü −0,00044 [−0,00086, −0,00001] (yarılar −0,00008 / −0,00079, p = 0,024 > α → geçmedi) · 2Y 1,5 Ü +0,00002 [−0,00096, +0,00098];
  2,5 Ü (yalnız bilgi) +0,00022 [−0,00040, +0,00080]. Beta − Platt farkı tüm pazarlarda |ΔLL| ≤ 0,00002 (öğrenilen a ≈ b: asimetrik sapma yok).
  Zayıf ridge (λ = 3) duyarlılığı daha kötü. Üretim değişmedi; 2Y 0,5 Üst için Platt/beta kabul sınırda — pazar karnesi kendi aylık kapısıyla izlemeye devam ediyor.

### YH-07 · basket · Sayı farkı ağırlıklı Elo robotu + ridge ile yığma
- **Açıklama:** Basket motoru tek model (ağırlıklı ridge hücum/savunma). Sayı farkı çarpanlı, sezon başı ortalamaya çekmeli Elo ayrı robot olarak çalıştırılır; lojistik yığınlayıcı (girdiler: ridge fark/σ, Elo farkı, dinlenme) yalnız geçmişle öğrenir.
- **Beklenen kazanç:** Farklı hata yapısına sahip iki güç ölçüsünün birleşimi tek modele göre tipik olarak ΔLL −0,002 … −0,006; özellikle sezon başı ve NCAA'da.
- **Efor:** S–M · **Risk:** düşük · **Veri:** mevcut.
- **Nasıl sınanır:** `bk_gelistir.py` kapısı (gün kümeli bootstrap, iki zaman dilimi) + lig grubu başına ayrı karar.
- **Kaynak:** [FiveThirtyEight NBA Elo](https://fivethirtyeight.com/features/how-we-calculate-nba-elo-ratings/) · Hvattum & Arntzen (2010) IJF [doi:10.1016/j.ijforecast.2009.10.002](https://doi.org/10.1016/j.ijforecast.2009.10.002)
- **Durum:** reddedildi (2026-10-28; hiçbir lig grubunda SK geçmedi, üretim değişmedi) — `lab/bk_elo_lab.py` → `data/bk_elo_lab.json`.
  Haftalık ileri yürüyüş (üretim ridge'i aynen, σ yalnız önceki haftalardan), Elo (K = 20, ev 100, MOV çarpanı, sezon arası ¼ ortalamaya) hafta başında
  dondurulmuş; yığınlayıcı `logit p = c + a·logit p_ridge + b·ΔElo + d·dinlenme` grup başına yalnız önceki haftalarla, (0,1,0,0) ön bilgisine L2 (λ = 300),
  gün-blok bootstrap B = 2000, α = 0,05/4. n = 12.557 maç: **pro** (NBA/WNBA/GL/NBL, n = 2.262) LL 0,61885 → 0,61614, ΔLL −0,00271 [−0,00443, −0,00090],
  p = 0,0005 ama 1. yarı +0,00028, 2. yarı −0,00569, isabet −0,13 puan → geçmedi (Elo katsayısı b = 0,12: gerçek ek bilgi, yalnız ikinci yarıda) ·
  **avrupa** (n = 436) ΔLL +0,00012 [−0,00089, +0,00112] → geçmedi · **kolej** (n = 9.859) ΔLL −0,00116 [−0,00237, +0,00012], p = 0,033, isabet −0,04 puan →
  geçmedi (kazanç Elo'dan değil, kesişim −0,12 ve a = 1,09 yeniden kalibrasyondan; Elo tek başına LL 0,561, ridge 0,518) · tümü ΔLL −0,00139
  [−0,00233, −0,00035] ama isabet −0,06 puan, 1. yarı GA sıfırı içeriyor. Beklenen −0,002…−0,006 yalnız pro 2. yarıda görüldü; NBA 2026-27 sezonu
  verisi birikince (≥ 1.000 yeni pro maçı) aynı betikle yeniden sınanabilir.

### YH-08 · at · Sabah olasılığının kapanış piyasasına bilgi katkısı (at için CLV)
- **Açıklama:** Sabah kilitli model olasılığı ile kapanış oranı (izinli ayna kaynağı, marjı ayrılmış) arasında: (a) sabah p kapanış hareketinin yönünü öngörüyor mu (kapanış − açılış/ön oran farkının sabah p − piyasa farkına regresyonu), (b) Benter iki aşaması: `logit p = a·logit p_model + b·logit p_kapanış` içinde a > 0 mı. Karneye "sabah modeli piyasaya bilgi ekliyor mu" satırı olarak girer; harman ağırlığının sağlık izlemesi olur.
- **Beklenen kazanç:** Doğrudan ölçüm kalitesi; Benter'e göre modelin değeri tam olarak bu bilgi katkısıdır. Harman ağırlığı a'nın GA'sı sıfırı kapsıyorsa sabah modeli için alarm.
- **Efor:** S · **Risk:** düşük · **Veri:** mevcut (yalnız izinli kaynak; TJK yok).
- **Nasıl sınanır:** Yürüyen pencerede a'nın koşu-günü blok bootstrap GA'sı; a > 0 (alt sınır > 0) karnede "doğrulandı".
- **Kaynak:** Benter (1994) "Computer based horse race handicapping and wagering systems" (Efficiency of Racetrack Betting Markets, World Scientific) [World Scientific](https://worldscientific.com/doi/abs/10.1142/9789812819192_0019) · Bolton & Chapman (1986) Management Science [doi:10.1287/mnsc.32.8.1040](https://doi.org/10.1287/mnsc.32.8.1040)
- **Durum:** yayında (2026-10-29; ölçüm, karnede satır) — **doğrulandı**: sabah modeli kapanış piyasasına bilgi ekliyor. `lab/at/bilgi_katkisi.py` → `data/at/bilgi_katkisi.json` + `data/at/karne.json → bilgi_katkisi` (at-lab her çalışmada yeniden hesaplar; commit ff5bf7b / a1b6ef5, ölçüm 4c4e7d8).
  p_sabah: replay.py'nin gün gün sızıntısız oransız olasılığı; q: aynanın nihai oranı (marj orantılı ayrılmış). Koşullu logit p ∝ exp(a·ln p_sabah + b·ln q),
  koşu-günü blok bootstrap B = 2000. Tüm dönem (2026-03-16…10-23, n = 3.282 koşu / 195 gün): **a = 0,314 [0,256, 0,375]**, b = 0,827 [0,764, 0,891];
  son 90 gün (n = 1.112): a = 0,368 [0,268, 0,473] (alarm yok); yarılar a = 0,283 [0,202, 0,375] / 0,349 [0,264, 0,440].
  Aylık ileri yürüyüş (yalnız önceki aylarla öğrenilen a, b) harman − kapanış ΔLL −0,0137 [−0,0191, −0,0079], yarılar −0,0093 / −0,0180 (n = 2.492; her ay < 0).
  (a) Yön: ln q_kapanış − ln q_erken'in ln p_sabah − ln q_erken'e eğimi 0,555 [0,530, 0,580] (n = 878 koşu, erken = koşudan ≥ 30 dk önce, 2026-04…06 görüntüleri):
  piyasa sabah modelinin yönüne kayıyor. Üretim değişmedi (harman zaten yayında); karar: son 90 gün a GA'sı 0'ı kapsarsa karnede alarm.

### YH-09 · altyapı · Skor ayrışımı (güvenilirlik / çözünürlük) ve ECE'nin tüm karnelere eklenmesi
- **Açıklama:** Brier'in Murphy ayrışımı (güvenilirlik − çözünürlük + belirsizlik) ve beklenen kalibrasyon hatası (ECE, eşit örnekli kovalar) futbol, basket, at, canlı karnelerine eklenir. Kötüleşmenin kalibrasyondan mı (düzeltilebilir: yeniden kalibre) yoksa çözünürlükten mi (model/veri sorunu) geldiğini drift alarmı ve koruyucu ayırt edebilir. Ana ölçüt log-kayıp kalır (RPS önerilmez).
- **Beklenen kazanç:** Teşhis hızı; geri alma yerine yeniden kalibrasyonla çözülebilecek durumların ayrılması.
- **Efor:** S · **Risk:** çok düşük · **Veri:** mevcut.
- **Nasıl sınanır:** Kapı yok (ölçüm); birim testi: ayrışım toplamı Brier'e eşit (±1e-9).
- **Kaynak:** Murphy (1973) J. Applied Meteorology [doi:10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2](https://doi.org/10.1175/1520-0450(1973)012%3C0595:ANVPOT%3E2.0.CO;2) · Wheatcroft (2021) JQAS 17(4) "Evaluating probabilistic forecasts of football matches: the case against the ranked probability score" [arXiv:1908.08980](https://arxiv.org/abs/1908.08980)
- **Durum:** yayında (2026-10-28, v138) — tek hesap yeri `scripts/guvenilirlik.py` (10 eşit kova; güvenilirlik − çözünürlük + belirsizlik + `kova_ici` = Brier,
  kova_ici Stephenson 2008 kova içi terimi; ECE ağırlıklı; kova başına Wilson %95). Karne betiklerinden çağrılır, yeni alan adı `guvenilirlik`:
  `data/daily.json` (collector, kilitli arşiv önerileri) n = 1.497, ECE 0,0225, güv. 0,0013, çöz. 0,0072 · `daily.canli` (kayıt anındaki p, 75. dk hariç) n = 1.989, ECE 0,0387, güv. 0,0017, çöz. 0,0085 ·
  `data/pazar_karne.json → canli` (kilitli 1X2 model yolu, zaman damgalı) 203 maç / 609 olasılık, ECE 0,0409, güv. 0,0029; model − piyasa LL n = 30 (veri az) ·
  `data/basket.json → live` (favori, Φ((ph−pa)/sm)) n = 54, ECE 0,0781, güv. 0,0128 · `data/at/karne.json` (koşudan önce, doğru mod) 177 at / 15 koşu, ECE 0,0183, güv. 0,0018 ·
  `data/oxx_karne.json → stratejiler.*` (canlı KUPO bacakları). Birim testi `lab/guvenilirlik_test.py` (300 rastgele + uç durum, toplam = Brier ±1e-9): geçti. Not: kovalar eşit genişlikte (görev tanımı), eşit örnekli değil.

### YH-10 · canlı · Canlı piyasa olasılığı + CG harmanı (futbol)
- **Açıklama:** Uygulama iddaa canlı oranlarını okuyup gösteriyor; CG modeli ise canlı piyasayı kullanmıyor. Canlı kayıt anlık görüntüsüne marjı ayrılmış canlı MS ve 2,5 olasılığı eklenir (yoksa boş); `logit p = a·logit p_CG + b·logit p_canlı-piyasa` dakika dilimine göre öğrenilir. Canlı piyasa yokken CG aynen kalır.
- **Beklenen kazanç:** Maç öncesinde olduğu gibi canlıda da piyasa en güçlü tahminci; tipik canlı ΔLL −0,01 … −0,04 (piyasası olan anlık görüntülerde).
- **Efor:** M · **Risk:** orta (canlı oran askıya alınmış anlar; gecikme sızıntısı → yalnız kayıt anından önceki oran) · **Veri:** zaten okunan kaynak, ücretsiz; ham oran depoya yazılmaz (yalnız marjı ayrılmış olasılık, 3 hane).
- **Nasıl sınanır:** `canli_guc_lab.py` protokolü + ayrıca "piyasası olan" alt kümede SK; ≥ 600 anlık görüntü.
- **Kaynak:** Robberechts, Van Haaren, Davis (2021) KDD "A Bayesian approach to in-game win probability in soccer" [arXiv:1906.05029](https://arxiv.org/abs/1906.05029) · Croxson & Reade (2014) Economic Journal "Information and efficiency: goal arrival in soccer betting" [doi:10.1111/ecoj.12033](https://doi.org/10.1111/ecoj.12033)
- **Durum:** gölgede (2026-10-28, v144; kapı veri yetersizliğinden geçmedi, veri birikiyor) — Mevcut canlı kayıtlarda (3.097 anlık görüntü, 5 gün)
  yalnız seçilen tarafın tek oranı vardı (`o`), marj ayrılamaz → piyasalı sınama satırı **n = 0** (gerekli ≥ 600 / ≥ 120 maç). Vekil ölçüm (karar dışı, tek gün,
  seçim yanlı): kayıtlı seçimlerde CG `pc` LL 0,651 / Brier 0,228, marjlı `1/o` LL 0,729 / Brier 0,258 (n = 370).
  Yapılan: `scripts/canli_guc.py` `piyasa()` (power marj ayırma, uygulamadaki `implied()` ile aynı) + `harman()` (`p ∝ exp(a·ln p_CG + b·ln p_piyasa)`,
  pazar × dakika dilimi 0/30/60/75); `scripts/collector.py` her canlı kayda `mk` (ms, ana çizgi ou, ng; 3 hane, ham oran yok) + gölge harman olasılığı `ph`
  yazar (`hv`: 1 = harman açık); `lab/canli_piyasa_lab.py` genişleyen pencere sınama + SK (lig×gün blok bootstrap, iki yarı, ΔBrier, pazar başına ΔLL ≤ 0,
  alfa yatırımı) → `data/canli_piyasa.json` (kullan=false, gölge ağırlık önsel 0,5/0,5); auto-lab'da her gece yeniden sınama, geçerse 14 gün izleme,
  tutmazsa geri alma. Uygulama: `canli-piyasa-v144` (js/katmanlar.js) + canli-gt-v107 core kancası — bayrak kapalıyken etkisiz; JS ↔ Python birebir
  (`lab/canli_piyasa_test.cjs`, 400 durum, fark < 1e-12).

### YH-11 · futbol · Skor güdümlü (GAS) dinamik güç modeli — model yolu
- **Açıklama:** Poisson robotu haftalık yeniden eğitim + üstel unutma kullanıyor. Skor güdümlü modelde her maçtan sonra hücum/savunma gücü log-olabilirlik gradyanıyla güncellenir (öğrenilen adım ve kalıcılık); Koopman–Lit'in iki değişkenli Poisson sürümü. Topluluğa 5. robot ya da Poisson'un yerine aday.
- **Beklenen kazanç:** Koopman & Lit, statik ve basit dinamik modellere göre ulusal liglerde tahmin doğruluğunda ve olasılık skorlarında iyileşme bildiriyor; tipik model yolu ΔLL −0,002 … −0,006 (oransız liglerde en çok).
- **Efor:** M · **Risk:** orta (ilk haftalar kararsızlığı) · **Veri:** mevcut.
- **Nasıl sınanır:** `fb_guc_lab.py espn` ve `derin` alanlarında SK.
- **Kaynak:** Koopman & Lit (2019) IJF [VU araştırma](https://research.vu.nl/en/publications/forecasting-football-match-results-in-national-league-competition-2/), [Tinbergen DP 17-062](https://papers.tinbergen.nl/17062.pdf) · Koopman & Lit (2015) JRSS-A [doi:10.1111/rssa.12042](https://doi.org/10.1111/rssa.12042)
- **Durum:** reddedildi — gölgede (2026-10-28) — robot `scripts/gas.py` (birim ölçekli skor güncellemesi, A/B seçim diliminde ızgarayla), topluluğa 4. üye
  adayı; `lab/fb_guc_lab.py` iki alanda da ölçüyor, `lab/fb_guc_kapi.py` adayları `gas_1x2` / `gas_ou` (taban: mevcut topluluk; bayrak `gas_aktif` / `gas_ko_aktif`,
  kilitli kayıtta GAS'sız gölge `gt`/`gto`, 14 gün izleme + geri alma). Sınama (zaman sıralı, sızıntısız; sonuç `data/gas_lab.json`):
  oransız (espn, n = 3.574, sınır 2026-05-01): GAS tek başına LL 1,0047 (Poisson 1,0053, topluluk 1,0031); topluluk+GAS − topluluk ΔLL −0,0004 [GA −0,0017, +0,0010],
  ΔBrier −0,0004; A/Ü ΔLL −0,0002 [−0,0010, +0,0005] → **SK geçmedi** (GA sıfırı içeriyor). Oranlı model yolu (derin, n = 15.363, sınır 2025-07-01):
  GAS tek başına +0,0110 (piyasa xg hedefli Poisson'dan kötü); topluluk+GAS − topluluk ΔLL −0,0003 [−0,0006, 0,0000], ilk yarı +0,0000;
  üretim yoluna göre −0,0006 [−0,0012, +0,0001]; A/Ü −0,0001 [−0,0002, +0,0000] → **SK geçmedi**. Beklenen −0,002…−0,006 görülmedi: GAS bilgisi
  Poisson + Elo + pi'nin taşıdığıyla büyük ölçüde örtüşüyor. Kapı her ölçümde yeniden dener (alfa yatırımı; ret sonrası 14 gün bekleme), gölge farkı `fb_guc.json golge_gas`.

### YH-12 · futbol · Oransız ligler için ESPN maç istatistiklerinden şut gücü
- **Açıklama:** YH-03'ün oransız ligler sürümü: ESPN maç özetindeki takım istatistikleri (şut, isabetli şut, korner) yalnız türetilmiş takım puanı olarak saklanır (ham yanıt depoya girmez); `guc.py` topluluğu bu puanı oransız liglerde kullanır. YH-03 kapıdan geçmeden başlanmaz.
- **Beklenen kazanç:** Oransız liglerde piyasa çapası olmadığından sinyal ekleme değeri en yüksek; tipik ΔLL −0,003 … −0,008.
- **Efor:** M · **Risk:** orta (ESPN kapsamı ligden lige değişir; eksik istatistikte robot sessiz kalır) · **Veri:** ESPN herkese açık uç noktası, ücretsiz.
- **Nasıl sınanır:** `fb_guc_lab.py espn` SK; ayrıca kapsam ≥ %60 olan liglerle sınırlı alt küme raporu.
- **Kaynak:** Wheatcroft (2021) [doi:10.3233/JSA-200462](https://doi.org/10.3233/JSA-200462) · Mead, O'Hare, McMenemy (2023) PLoS ONE "Expected goals in football" [doi:10.1371/journal.pone.0282295](https://doi.org/10.1371/journal.pone.0282295)
- **Durum:** ertelendi (2026-10-29; ön koşul sağlanmadı: YH-03 şut gücü kapıyı geçmedi — oranlı liglerde isabetli şut Poisson+Elo+pi üstüne bilgi eklemedi, n = 15.461). YH-03 haftalık gölge ölçümü A/Ü'de kapıyı geçerse yeniden `bekliyor` yapılır.

### YH-13 · arayüz · Şeffaf güvenilirlik paneli
- **Açıklama:** Motor sayfasına kilitli kayıtlardan çizilen güvenilirlik eğrisi (söylenen % ↔ gerçekleşen %), son 30 / 90 gün, pazar seçimi; YH-01 ve YH-09 ölçütleri tek satırda. Yalnız ölçülmüş rakam; az örnekte kova gizlenir (n < 50).
- **Beklenen kazanç:** Güven ve dürüstlük; olasılıklı tahminlerin belirsizlikle birlikte sunulması kullanıcı kararlarını iyileştiriyor.
- **Efor:** S · **Risk:** düşük (duman testi + kalite ekran görüntüsü) · **Veri:** mevcut.
- **Nasıl sınanır:** Kalite botu (360/390 px ekran görüntüsü), duman testi, açılış süresi artışı < 50 ms; görünür metin yasaklı kelime taraması.
- **Kaynak:** Joslyn & LeClerc (2012) J. Exp. Psychology: Applied [doi:10.1037/a0025185](https://doi.org/10.1037/a0025185) · Gigerenzer & Hoffrage (1995) Psychological Review [doi:10.1037/0033-295X.102.4.684](https://doi.org/10.1037/0033-295X.102.4.684)
- **Durum:** yayında (2026-10-28, v138) — Tahmin karnesinde katlanır "📐 Güvenilirlik raporu" (`<script id="guvenilirlik-v138">`): Futbol / Canlı / Basket / At sekmeleri,
  kova başına "%X dediğimiz n tahmin gerçekte %Y tuttu" + %95 aralık çubuğu, n < 50 "veri az" (gizlemek yerine işaret), futbolda gösterilen öneri vs piyasa
  log-kayıp (n = 474: fark −0,0026 [−0,0145, 0,0092], anlamlı değil) ve 1X2 model yolu vs piyasa (n = 30: +0,0045 [−0,0271, 0,0361], veri az). Panel açılmadan ek dosya indirmez.
  Sınama: Playwright 390 px koyu/açık şema, 4 sekmede rakamlar karne dosyalarıyla birebir, 0 sayfa hatası, yatay taşma yok, yasak kelime yok.
  Son 30/90 gün ve pazar seçimi henüz yok (veri tüm dönem).

### YH-14 · basket · Tempo (hücum sayısı) tabanlı toplam sayı modeli
- **Açıklama:** Toplam sayı şu an hücum/savunma sayı ridge'inden geliyor. ESPN kutu skorundan (FGA, FTA, TOV, OREB) hücum sayısı tahmini → takım temposu ve hücum başına verim ayrı öğrenilir; toplam = tempo × (verim_ev + verim_dep). Alt/üst ve handikap dağılımı bundan türetilir.
- **Beklenen kazanç:** Tempo ve verimi ayırmak toplam tahmininde varyansı düşürür; tipik toplam MAE −%2 … −%5, alt/üst ΔLL −0,003 … −0,008.
- **Efor:** M · **Risk:** orta (EuroLeague kutu skoru biçimi farklı) · **Veri:** ESPN / EuroLeague herkese açık, ücretsiz; yalnız türetilmiş takım değerleri saklanır.
- **Nasıl sınanır:** `bk_gelistir.py`: toplam MAE ve alt/üst LL için gün kümeli bootstrap üst sınırı < 0, iki dilimde de.
- **Kaynak:** Kubatko, Oliver, Pelton, Rosenbaum (2007) JQAS "A starting point for analyzing basketball statistics" [doi:10.2202/1559-0410.1070](https://doi.org/10.2202/1559-0410.1070)
- **Durum:** reddedildi (2026-10-29; SK geçmedi, üretim değişmedi) — `lab/bk_tempo_lab.py` → `data/bk_tempo_lab.json`, `bk-tempo-lab.yml` haftalık yeniden ölçüm (yalnız ölçüm; run 40856566483, commit 6a8dbb9).
  ESPN skor tablosu takım istatistikleri (kapsam NBA/WNBA/NCAA/NCAAW/G League ≈ %100, NBL %24; OREB/TOV yok → hücum ≈ FGA + 0,44·FTA), tempo ve 100 hücum verimi ayrı ridge, haftalık ileri yürüyüş, sınama n = 12.729.
  `tempo`: ΔMAE toplam +0,009 [GA −0,0004, +0,018], A/Ü ΔLL +0,0004 [−0,00002, +0,0009], ΔBrier +0,0002, ilk dilim anlamlı kötü → **geçmedi**. `harman` (ağırlık yalnız önceki haftalardan; ort. w NBA 0, NCAA 0, G League 0,79):
  ΔMAE +0,00002 [−0,0011, +0,0011], ΔLL 0,0000 [−0,00005, +0,00005] → **geçmedi** (fark yok). Yorum: sayı ridge'i (hücum/savunma) tempo × verim yapısını zaten taşıyor; beklenen −%2…−%5 MAE görülmedi. Yalnız G League'de küçük olumlu eğilim (n = 340, anlamsız).

### YH-15 · at · Koşu belirsizliğine göre seçici gösterim (pas eşiği)
- **Açıklama:** Futboldaki "%58 altı pas" kuralının at karşılığı: koşu düzeyinde entropi, alan büyüklüğü ve ilk iki olasılık farkından "güven sınıfı" üret; Altın ve öne çıkan seçimler yalnız geçmişte kalibre olduğu sınıflarda gösterilir. Eşik yürüyen pencerede seçilir.
- **Beklenen kazanç:** Seçici tahmin: kapsamı %20–30 azaltarak gösterilen seçimlerin isabetini birkaç puan artırma (risk–kapsam eğrisi).
- **Efor:** S · **Risk:** düşük · **Veri:** mevcut.
- **Nasıl sınanır:** Zaman sıralı: aynı kapsamda rastgele seçime göre isabet farkının GA alt sınırı > 0; yalnız-model ve harman ayrı.
- **Kaynak:** Geifman & El-Yaniv (2017) NeurIPS "Selective classification for deep neural networks" [arXiv:1705.08500](https://arxiv.org/abs/1705.08500)
- **Durum:** yayında (2026-10-30, v148; bayraklı, 14 gün izleme) — `lab/at/secici_lab.py` → `data/at/secici_lab.json` + bayrak/katsayı `data/at/secici.json`, `at-secici-lab.yml` haftalık yeniden ölçüm (kapı geçmezse `aktif=false`, etiket kendiliğinden kalkar).
  Güven puanı = lojistik(p1, p1−p2, normalize entropi, ln alan), aylık ileri yürüyüş, eşik eğitimde %25'lik dilim. Sınama 2026-05-01…10-23, n = 2.494 koşu / 149 gün:
  **sabah**: kapsam %69, seçilenlerde ilk seçim isabeti %33,3 vs tüm koşular %29,3 → fark +3,96 puan [GA +2,90, +5,04], yarılar +4,1 / +3,9, p < 0,001 → **geçti**; pas edilenlerde isabet %20,5.
  **harman** (ayrı): kapsam %72, %37,8 vs %33,4 → +4,4 puan [+3,35, +5,51]. Bilgi: aynı kapsamda yalnız p1 eşiği de geçiyor (+3,35 [+2,3, +4,4]); entropi/alan p1'in üstüne anlamlı katkı vermedi (+0,62 [−0,28, +1,49]).
  Uygulama: açık koşularda "≈ Belirsiz koşu" etiketi + koşu ekranında ölçülmüş not (`js/at2.js belirsiz()`); Altın kuralı (p ≥ %35, fark ≥ 12) değişmedi. İzleme notu: ilk canlı 50 koşuda etiket oranı %52 (alanlar replay ortalamasından büyük: ln n 2,37 vs 2,24).

### YH-16 · basket · Sakatlık raporu (NBA / WNBA) — dakika ağırlıklı kayıp
- **Açıklama:** ESPN takım sakatlık listesinden "oynamaz / şüpheli" oyuncular; oyuncunun son maçlardaki dakika payı × takım içi etki (kutu skorundan basit artı-eksi ya da sayı payı) ile beklenen fark düzeltmesi. Yalnız türetilmiş takım düzeltmesi depoya; oyuncu düzeyi birikim önbellekte (futbol `kadro.py` ilkesi).
- **Beklenen kazanç:** Piyasası olmayan / model yolu tahminlerinde en büyük eksik bilgi; tipik model yolu ΔLL −0,003 … −0,010 (yıldız eksikliği olan maçlarda çok daha fazla). Piyasa çapası yayındaysa katkı küçük.
- **Efor:** M · **Risk:** orta (rapor zamanlaması → sızıntı; yalnız kilit anından önceki rapor) · **Veri:** ESPN herkese açık, ücretsiz.
- **Nasıl sınanır:** Gölge kayıt (≥ 300 maç, ≥ 80 sinyalli) → `tazeveri` tipi kapı, SK.
- **Kaynak:** Kubatko ve ark. (2007) [doi:10.2202/1559-0410.1070](https://doi.org/10.2202/1559-0410.1070) · [FiveThirtyEight RAPTOR / kadro düzeltmesi](https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- **Durum:** gölgede, kayıt başladı (2026-10-30; kapı veri bekliyor, üretime etkisi yok) — `scripts/bk_sakatlik.py` (update.yml adımı `bk-sakatlik`, saatlik) → `data/bk_sakatlik.json` (yalnız takım düzeyi `dk` = Σ w·dakika/240, `pt` = Σ w·sayı; w: Out 1 · Doubtful 0,75 · Questionable/DTD 0,5 · Probable 0,1; oyuncu ortalamaları yalnız `actions/cache` `.bk_sakatlik_onbellek/`).
  `basket.py lock_and_grade`: kilitli ph/pa değişmez; maç başlayana dek `skg = {x: [dk_dep−dk_ev, pt_dep−pt_ev], d: 0,5·x₂, ts}` tazelenir (`skg0` = kilit anı), yalnız ≤ 3 saat taze sinyal; başlamış maça yazılmaz. Gölge özeti `golge` (lig başına n, sinyalli, önsel ΔLL).
  Ağsız birim sınaması `lab/bk_sakatlik_test.py` 14/14 (ayrıştırma, kayıp hesabı, bayat sinyal reddi, sızıntısızlık, kilit değişmezliği). Kapı: ≥ 300 sonuçlanmış NBA/WNBA maçı ve ≥ 80 sinyalli → β geçmiş artıklardan ridge (skg son görüntü), zaman sıralı SK; geçerse yalnız kilit anı sinyaliyle (`skg0`) üretime.

### YH-17 · altyapı · Sıralı (her an geçerli) test ile gölge sürenin kısaltılması
- **Açıklama:** Gölge ölçüm ve 14 gün izleme sabit süreli. Karışım SPRT / e-değer tabanlı "her an geçerli" güven dizileri, istenildiği an bakılsa bile I. tür hata kontrolünü korur; açık iyileşmede erken yayın, açık kötüleşmede erken geri alma sağlar. Alfa yatırımıyla uyumlu (e-değerler LORD/alfa yatırımına bağlanabilir).
- **Beklenen kazanç:** Aynı hata oranında ortalama karar süresinde %30–50 kısalma (literatürdeki A/B testi sonuçları); döngü hızı artar.
- **Efor:** M · **Risk:** orta (yanlış uygulama → hata kontrolü kaybı; önce gölgede eski kapıyla paralel) · **Veri:** mevcut.
- **Nasıl sınanır:** Benzetim: sıfır hipotezi altında 10.000 tekrar, yanlış red oranı ≤ 0,05; geçmiş kapı kararlarıyla ≥ %90 uyum.
- **Kaynak:** Johari, Pekelis, Walsh (2017/2022) "Always valid inference" [arXiv:1512.04922](https://arxiv.org/abs/1512.04922) · Howard, Ramdas, McAuliffe, Sekhon (2021) Annals of Statistics [arXiv:1810.08240](https://arxiv.org/abs/1810.08240)
- **Durum:** yayında — gölge ölçüm aracı (2026-10-30; kapı geçti, karar yetkisi yok, eski kapı karar verir) — `lab/siralik.py` (asimptotik güven dizisi, Robbins normal karışımı; blok = gün; küçük örneklem t/z çarpanı + uzun dönem varyans düzeltmesi; ısınma 5 blok) · `lab/siralik_lab.py` → `data/siralik_lab.json`, haftalık `siralik-lab.yml` (salı). Kanıt: sıfır benzetimi 10.000 tekrar × 90 bakış, yanlış red **0,026** [MC GA 0,023–0,029] ≤ 0,05 (saf "her gün %95 GA'ya bak": 0,56); geçmiş kapı kararlarıyla uyum **%96,2** (n = 78 karar, 3 geçen kararın 3'ü korunuyor), koruyucu 14 gün izleme tekrarı 10/10 uyum. Karar süresi (sabit 14 güne göre): tasarım etkisinde ≈ aynı (×1,02), 1,5× etkide %39, 2× etkide %53 kısa; küçük etkide (0,5×) daha uzun. Sınır: bloklar arası güçlü ardışık ilişkide (AR 0,3) yanlış red 0,11 → üretim kararına bağlanmadan önce gerçek gölge serilerinde φ̂ izlenecek. Sıradaki adım (ayrı madde gerekmez): `surekli_deney` gölge adaylarına ve koruyucuya paralel kayıt.

### YH-18 · futbol · Gol sayısı dağılımında aşırı/eksik yayılım (Weibull sayım / NB) — model yolu
- **Açıklama:** Model yolu Poisson + Dixon-Coles. Weibull sayım (ya da negatif binom) dağılımı gol varyansını ayrı parametreyle öğrenir; 2,5 ve 3,5 alt/üst, KG ve net skor pazarlarına etki eder. Yalnız oransız yolda; piyasa yolundaki gol tablosu değişmez.
- **Beklenen kazanç:** Boshnakov ve ark., Weibull sayım + kopula modelinin Poisson'a göre daha iyi kalibre alt/üst olasılıkları verdiğini bildiriyor; tipik alt/üst ΔLL −0,001 … −0,004.
- **Efor:** M · **Risk:** orta (ızgara ve DC uyumu) · **Veri:** mevcut.
- **Nasıl sınanır:** `fb_guc_lab.py` 2,5 Ü ve net skor LL için SK.
- **Kaynak:** Boshnakov, Kharrat, McHale (2017) IJF [doi:10.1016/j.ijforecast.2016.11.006](https://doi.org/10.1016/j.ijforecast.2016.11.006) · Karlis & Ntzoufras (2003) JRSS-D [doi:10.1111/1467-9884.00366](https://doi.org/10.1111/1467-9884.00366)
- **Durum:** reddedildi (2026-10-30; kapı geçmedi, üretim değişmedi) — `lab/sayim_lab.py` → `data/sayim_lab.json`. Aynı ileri yürüyüş λ'sı (oransız Poisson decay 0,003 / prior 10) ve aynı Dixon-Coles ızgarası; yalnız marjinal şekli değişir (ortalama eşlemeli NB, Conway–Maxwell–Poisson, Weibull sayım; c = 1 / ν = 1 denetimi Poisson'dan ≤ 0,00012 sapma). Şekil parametresi her ay yalnız geçmiş aylarla seçildi.
  **Oransız ligler (karar alanı)**, sınama 2026-04-01+ n = 4.417 (28 lig): CMP ve Weibull her ay Poisson'u seçti (fark 0); NB (r = 100) 2,5 A/Ü ΔLL −0,00009 [GA −0,0002, +0,00001], p 0,047 > α_t 0,0136, net skor ΔLL +0,00025, 1X2 +0,00012 → **geçmedi**. Artık yayılım ev 1,035 / dep 1,018 (Poisson'a çok yakın).
  Sağlamlık (oranlı ligler, model yolu, yalnız rapor — `data/sayim_lab_derin.json`, n = 15.444): hafif eksik yayılım (CMP ν = 1,1) 2,5 A/Ü ΔLL −0,00016 [−0,00029, −0,00003], net skor −0,0014; ancak 1,5/3,5 A/Ü kötüleşiyor ve bu yol oranlı maçlarda sunulmuyor. Alfa yatırımı `fb_model-2026` testi düşüldü.

### YH-19 · canlı · Kırmızı kart etkisinin kayıtlardan öğrenilmesi
- **Açıklama:** CG'de kırmızı kart çarpanları sabit (0,72 / 1,25). Kayıtlı canlı anlık görüntülerde kart olayı biriktikçe (≥ 150 kartlı maç) çarpanlar dakika ve skor durumuna göre Bayes küçültmeyle (önsel = mevcut sabitler) öğrenilir.
- **Beklenen kazanç:** Kartlı anlık görüntülerde ΔLL −0,01 … −0,03; genel etki küçük (kartlı maç payı ~%10).
- **Efor:** S · **Risk:** düşük (önsel küçültme) · **Veri:** mevcut kayıtlar.
- **Nasıl sınanır:** `canli_guc_lab.py` kapısı; yalnız kartlı alt kümede de ΔLL < 0.
- **Kaynak:** Titman, Costain, Ridall, Gould (2015) JRSS-A "Joint modelling of goals and bookings in association football" [doi:10.1111/rssa.12075](https://doi.org/10.1111/rssa.12075) · Vecer, Kopriva, Ichiba (2009) JQAS "Estimating the effect of the red card in soccer" [ideas.repec](https://ideas.repec.org/a/bpj/jqsprt/v5y2009i1n8.html)
- **Durum:** gölgede, veri bekliyor (2026-10-31; öğrenme + kapı kodu hazır, üretim değişmedi — sabitler 0,72 / 1,25 kalır) — `lab/canli_guc_lab.py` 3. aşama `kart_eval` / `fit_kart` (log ölçekte Gauss önsel, std 0,2, önsel = mevcut sabitler; maç başına toplam ağırlık 1; diğer CG parametreleri sabit) → `data/canli_guc.json → kart` (auto-lab adımı `canli-guc` her çalışmada günceller). Kapı: toplam ≥ 150 kartlı sonuçlu maç ve sınamada ≥ 100; kartlı alt kümede birleşik (MS + 2,5) ΔLL maç-blok %95 GA üst < 0, iki zaman yarısında < 0, ΔBrier MS ve 2,5 ≤ 0; geçince öğrenilen çarpanlar `params.rc_own/rc_opp` olarak yazılır (Python `canli_guc.py` ve JS `canli-gt.js` bunları zaten okur). Bugünkü veri: 554 sonuçlu canlı maçın yalnız **18**'i kartlı (112 anlık görüntü; pay %3,2) → zaman sıralı sınamada hiçbir gün ≥ 20 kartlı eğitim maçı yok, ΔLL = 0, durum "veri bekliyor". Yalnız bilgi (örneklem içi, karar değil): küçültülmüş çarpanlar kendi 0,687 / rakip 1,361, kartlı satırlarda ΔLL −0,0166. Bu hızla 150 kartlı maça ≈ 7–8 hafta; ölçüm kendiliğinden karar verir.

### YH-20 · futbol · Milli takım maçları için Elo (CC0 açık geçmiş)
- **Açıklama:** Motorda milli takım ligi yok; milli maçlar yalnız piyasa yolunda. martj42/international_results (CC0, 1872 → bugün) ile Dünya Futbol Elo usulü (turnuva önemi K katsayısı, gol farkı çarpanı) puanlar; oransız milli maçlarda ve hazırlık maçlarında model yolu sağlanır, oranlıda konsey adayı olarak yarışır.
- **Beklenen kazanç:** Kapsam (oransız milli maçlarda tahmin) + Elo'nun milli maçlarda iyi bilinen başarısı; piyasa üstü katkı beklenmez.
- **Efor:** M · **Risk:** düşük · **Veri:** CC0, ücretsiz (yalnız türetilmiş puan depoya).
- **Nasıl sınanır:** Zaman sıralı: lig ortalamasına (taban) göre ΔLL üst sınırı < 0; oranlı alt kümede piyasaya karşı yalnız rapor.
- **Kaynak:** [martj42/international_results (CC0)](https://github.com/martj42/international_results) · Hvattum & Arntzen (2010) [doi:10.1016/j.ijforecast.2009.10.002](https://doi.org/10.1016/j.ijforecast.2009.10.002) · Lasek, Szlávik, Bhulai (2013) "The predictive power of ranking systems in association football" [Inderscience](https://inderscience.com/offer.php?id=52339)
- **Durum:** yayında (veri katmanı + kilitli gölge; 2026-10-31) — kapı geçti, sunulan olasılık değişmedi. `scripts/milli_elo.py` (update.yml adımı `milli-elo`, saatlik; CC0 ham CSV yalnız `actions/cache` `.milli_elo_onbellek/`) → `data/milli_elo.json` (son 4 yılda oynamış 257 takımın türetilmiş puanı, sıralı lojit 1X2 eşlemesi, parametreler) + `data/milli_elo_golge.json` (bültende iki takımı da milli olan maçlara maçtan önce bir kez yazılan Elo 1X2 + piyasa 1X2; sonuç CC0'dan eklenir). Sınama `lab/milli_elo_lab.py` → `data/milli_elo_lab.json` (haftalık `keskin-lab.yml`): K 60/50/40/30/20, G gol farkı çarpanı; H / R0 / K çarpanı yalnız 2008–2015 ile seçildi (H 100, R0 1300, K×1); eşleme ve taban her sınama yılında yalnız önceki 12 yılla. **Sınama 2016-01-01 → 2026-10-06, n = 10.139 FIFA içi maç**: ΔLL (Elo − geçmiş 1X2 sıklığı, ev/tarafsız ayrı) **−0,1717 [GA −0,1824, −0,1611]**, yarılar −0,1716 / −0,1718, ΔBrier −0,1160, p 0,0 ≤ α_t 0,0090 (fb_model-2026, servet işlendi), isabet %47,7 → %60,0; hazırlık maçlarında ΔLL −0,112 (n 2.883), resmi −0,195; ev kazanır kalibrasyonu 10 kovada ≤ 0,02 sapma → **SK geçti**. Üretim notu: bugün bültende oransız milli maç yolu yok (iddaa milli maçları oranlı, ESPN fikstüründe milli yarışma yok), bu yüzden sunulan olasılık değişmedi; oranlı milli maçlarda konsey adaylığı kararı gölge kayıttan verilir (≥ 60 sonuçlu piyasalı kayıt, Elo LL < piyasa LL ve GA üst < 0 ise konsey girdisi olur; aksi hâlde yalnız kapsam katmanı olarak kalır).

### YH-21 · futbol · Hiyerarşik Bayes küçültme ile yeni / az veri liglerde güç önseli
- **Açıklama:** Oransız küçük liglerde takım güçleri az maçla gürültülü. Takım gücü ~ N(lig ortalaması, τ_lig²), τ_lig ve ev avantajı ligler arası önselden (ampirik Bayes) öğrenilir; sezon başında ve ligde < 45 maç varken de tahmin yapılabilir (şu an uygunluk eşiği dışında kalanlar).
- **Beklenen kazanç:** Kapsam artışı (eşik altı maçlar) + küçük liglerde ΔLL −0,002 … −0,005; Baio & Blangiardo küçültmenin aşırı uyumu azalttığını gösteriyor.
- **Efor:** M · **Risk:** orta · **Veri:** mevcut.
- **Nasıl sınanır:** `fb_guc_lab.py espn` SK + yeni kapsanan maçlarda taban modele göre ΔLL üst sınırı < 0.
- **Kaynak:** Baio & Blangiardo (2010) J. Applied Statistics [doi:10.1080/02664760802684177](https://doi.org/10.1080/02664760802684177) · Ley, Van de Wiele, Van Eetvelde (2019) Statistical Modelling [doi:10.1177/1471082X18817650](https://doi.org/10.1177/1471082X18817650)
- **Durum:** reddedildi (2026-10-31; kapı geçmedi, üretim değişmedi) — `lab/esik_alti_lab.py` → `data/esik_alti_lab.json`. Önceden kayıtlı tasarım, ızgara yok: YH-25'in `hb_fit`'i (τ²_0 0,03, n0 5, tavansız, decay 0,003) yalnız geçmişle; küme = 450 günlük pencerede ≥ 10 eğitim maçı olan ama üretimin uygun saymadığı maçlar (lig < 45: 972, takım < 3: 185; **n = 1.157, 28 oransız lig, 2025-08-11 → 2026-10-25**); taban = o güne kadarki tüm oransız maçların havuz 1X2 / 2,5 sıklığı. 1X2: HB − taban ΔLL **−0,0237 [GA −0,0386, −0,0089]**, ΔBrier −0,0166, ama yarılar **+0,0042** / −0,0493 (ilk yarı geçmedi); tek önselli üretim Poisson'una (prior 10) karşı ΔLL **+0,0134 [+0,0056, +0,0216]** — HB daha kötü (her iki alt kümede de: lig<45 +0,0136, takım<3 +0,0128). 2,5 A/Ü: tabana karşı ΔLL +0,0086 [−0,0110, +0,0287] → geçmedi. Yorum: YH-25 ile aynı — lig τ² tahmini az maçta aşırı sıkı küçültüyor; eşik altında bilgi taşıyan yol tek önselli Poisson (tabana göre ΔLL ≈ −0,037), ama bugün fikstürde eşik altı oransız maç yok (31 Ekim: 1.240 maçın 236'sı oransız; 224'ü topluluk yolunda, 10'u verisiz iddaa ligi, 2'si TBD) → kapsam kazancı sıfır, ayrı madde açılmadı. YH-25 ile birlikte bu aile kapandı.

### YH-22 · arayüz · "Neden bu tahmin?" kısa açıklaması
- **Açıklama:** Maç kartında olasılığa en çok katkı yapan 2–3 etken (piyasa, güç farkı, form/şut, kadro, dinlenme) yüzde puan olarak; yalnız modelde gerçekten kullanılan ve kapıdan geçmiş girdiler gösterilir. Yanıltıcı kesinlik dili yok.
- **Beklenen kazanç:** Anlaşılırlık ve güven; açıklamalı olasılık sunumu kullanıcıların olasılığı doğru yorumlamasına yardım eder (ölçülebilir: sohbet asistanına "neden" sorularının azalması, kalite botu).
- **Efor:** M · **Risk:** düşük–orta (performans; yasaklı kelime taraması) · **Veri:** mevcut.
- **Nasıl sınanır:** Duman + kalite testleri, açılış süresi artışı < 50 ms, `bot_coach` "neden" niyetli soruların faydalı oranı düşmüyor.
- **Kaynak:** Lundberg & Lee (2017) NeurIPS "A unified approach to interpreting model predictions" [arXiv:1705.07874](https://arxiv.org/abs/1705.07874) · Joslyn & LeClerc (2012) [doi:10.1037/a0025185](https://doi.org/10.1037/a0025185)
- **Durum:** yayında (v145, 2026-10-28) · kanıt: `js/katmanlar.js` katman `neden-v145` + `css/katmanlar.css`; maç penceresi öneri kutusunda "ⓘ Neden bu tahmin?", bülten ve Canlı sekmesi satırında uzun basma, basket penceresi, at koşu kartı / at profili (ayrı fonksiyon). İçerik aynı hesaplardan (fullPred/kpFix/recOf, idlPred/idlPick/liveCal, bkPredict, BX_AT.merged + sinyal) ve kilitli karne kovalarından; verisi olmayan madde gösterilmez, en çok 6 madde. Playwright 390 px: oranlı, oransız (güç modeli ve Poisson), bülten uzun basma, sahte canlı maç (pencere + Canlı satırı), basket, at koşusu → 62/62 (kart açılıyor, yüzde ekranla aynı, taşma yok, yasak kelime yok, 0 sayfa hatası); kart hesabı ≈ 1 ms, açılışta hesap yok; `lab/canli_gt_test.cjs` 62/62, `lab/canli_isaret_test.cjs` 20/20.

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
