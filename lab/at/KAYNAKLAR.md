# BULUTOXX 🐎 At Yarışı — Açık Kaynak Taraması (derin tur, 26.10.2026)

Amaç: modele TJK yasağını çiğnemeden, ücretsiz ve lisansı uygun **yeni bilgi** bulmak. Kırmızı çizgiler:
tjk.org, medya-cdn.tjk.org, vhs*.tjk.org, atyarisi.com ve tüm alt alanları (tjkbulten, tjkgw, help, content) —
doğrudan da dolaylı da (proxy, önbellek, web.archive.org kopyası, bu alanları kazıyan üçüncü taraf deposu) **istek yok,
içerik yok**. Kazımayı yasaklayan site kazınmaz; ücretli API yok; kişisel veri yok; lisansı belirsiz kaynak üretime alınmaz.

Ortam notu: bu oturumun ağı yalnız GitHub (git protokolü), PyPI ve npm kayıt defterine açıktı; GitHub arama API'si,
Kaggle, Hugging Face, Zenodo, DergiPark, arXiv, Open-Meteo doğrudan erişilemedi. Bunlar web arama motoru +
sayfa okuma (WebSearch/WebFetch) ile tarandı; GitHub aday listesi gece araştırmacısının (`lab/at/arastirma.py`,
GitHub arama API'si, Actions'ta) `data/at/arastirma.json` birikiminden alındı ve 20 aday deposu **sığ klonlanıp**
dosya/kaynak/lisans envanteri çıkarıldı (ham veri depoya alınmadı).

## Tarama tablosu (46 aday)

Karar: **BAĞLI** = üretimde · **DENEY** = ölçüldü (sonuç aşağıda) · **YOL** = yasal, üretim yolu hazır · **RED** = elendi.

| # | aday | içerik | kapsam / güncellik | erişim | lisans / şart | TJK yasağıyla ilişki | karar | gerekçe |
|---|---|---|---|---|---|---|---|---|
| 1 | github.com/cenkozgur/tjk-data — `data/results`, `data/daily` | sonuç, program, nihai ganyan, derece, kilo, yaş, pist durumu/hava (2026-04+) | 2025-01 → bugün, 10 hipodrom | git clone | belirtilmemiş (kamuya açık ayna) | TJK'dan türemiş açık ayna; önceden onaylı tek kaynak | BAĞLI | mevcut sistemin temeli |
| 2 | aynanın **git geçmişi** (`data/daily` 5.578 sürüm, 2026-06-12 → bugün; öncesi tek commit'e ezilmiş) | gün içi oran görüntüleri (seyrek: günde 1–4), pist durumunun yazılma saati | 1.515 koşu yarıştan ≥30 dk önce oranlı | blobless clone + toplu blob çekme | aynı (1) | aynı (1) | DENEY → RED | oran hareketi harmana bilgi katmadı (ΔLL +0,0003 [−0,0023; +0,0029]); pist durumu çoğu gün 14:00'te yazılıyor → sabah kilidinde yok |
| 3 | aynanın `data/odds-snapshots` + `odds-steam-counterfactual` | 6–30 dk'lık oran izi, "steam" deneyi | 57 gün (2026-04-13 → 06-12), DURMUŞ | ayna | aynı (1) | aynı (1) | DENEY → RED | (2) ile birlikte ölçüldü; 2026-06'da durduğu için üretimde zaten yok |
| 4 | aynanın `memory/predictions` (üçüncü taraf tahmin günlüğü; git'te ilk sürüm sabah 00–04) | at başına olasılık (ilk 6 at), "odds" alanı sabit 5 | 2026-06-13 → bugün | ayna git geçmişi | aynı (1) | aynı (1) | DENEY → RED | kendi LL'si 2,144 (bizim sabah 1,932); yığmada ΔLL −0,0019 [−0,0055; +0,0015] anlamsız; ezilmiş dönem sonuç içeriyor (sızıntı) |
| 5 | aynanın `memory/horses|jockeys|trainers|tracks.json` | sonuçlardan türetilmiş özetler | bugünkü durum | ayna | aynı (1) | aynı (1) | RED | geleceği içerir (sızıntı); pedigri/sahip/orijin alanı YOK |
| 6 | aynada kullanılmayan alanlar: `nonRunners`, `unplaced` ("Derecesiz"), `ganyanSixPrizes`, `isGanyanStart`, `ekuriGroups`, `form` dizisi, `time` | koşmaz/derecesiz, 6'lı ikramiyesi, ekuri, eski form | 169 koşmaz + 43 derecesiz (tüm dönem); form/saat yalnız 2026-04+ | ayna | aynı (1) | aynı (1) | RED | olay sayısı çok az / geçmiş çok kısa; ekuri v2'de elendi. Start/kulvar, HP, sahip, yetiştirici, baba/anne, galop, AGF alanı aynada YOK |
| 7 | **Open-Meteo** arşiv + tahmin API'si | günlük yağış, sıcaklık (ERA5 tabanlı), 1–2 gün tahmin | 1940 → bugün, her koordinat | HTTPS, anahtarsız (Actions'tan erişilir; bu oturumdan engelli) | **CC BY 4.0**, ücretsiz katman ticari olmayan kullanım; atıf + lisans bağlantısı | TJK ile ilgisi yok | YOL (+ DENEY) | `lab/at/hava.py` üretim çekicisi; deney (8) üzerinden ölçüldü |
| 8 | github.com/dogankorkmaz-tjk/tjk-sistem — `data/hava/gunluk.csv` | (7)'nin 10 hipodrom için günlük kopyası (`tjk/hava_cek.py` Open-Meteo arşivinden çekiyor) | 2023-01-01 → 2026-10-12 | git clone | depo lisanssız; **veri Open-Meteo'nun (CC BY 4.0)** | TJK ile ilgisi yok | DENEY (yalnız çevrimdışı ölçüm) | bu oturum Open-Meteo'ya erişemediği için ölçüm bu kopyayla yapıldı; üretim veriyi (7)'den kendisi çeker, bu depo üretime bağlanmaz |
| 9 | aynı depo — `data/galop`, `idman.csv.gz`, `agf`, `agf_zaman`, `canli_oran`, `kosmaz`, `jokey_degisiklik` | idman/galop, AGF, canlı oran | 2026 | git clone | lisanssız | **tjkbulten.atyarisi.com API + tjk.org'dan kazınmış** (kodda açıkça) + agftablosu.com | RED | yasaklı alanların dolaylı kopyası; açılmadı, okunmadı |
| 10 | npm `tjk-api` (bilaleren/tjk-api) | Node paketi: program, sonuç, AGF, muhtemeller | 2026-01 | npm | MIT (kod) | **tjk.org / vhs.tjk.org / medya-cdn'e istek atar** | RED | yasak alan |
| 11 | SezerFidanci/TJK-API | TJK API sarmalayıcı | 2021 | git | yok | ebayi.tjk.org | RED | yasak alan |
| 12 | ZehraK/TJK---Horse-Race-Scraping-Results | tjk.org kazıyıcı | 2021 | git | yok | tjk.org | RED | yasak alan, veri yok |
| 13 | egeaydin/HorseRacingAPI | tjk.org API | 2019 | git | yok | tjk.org | RED | yasak alan |
| 14 | uveysservetoglu/tjk-crawler | günlük program kazıyıcı | 2018 | git | yok | tjk.org | RED | yasak alan |
| 15 | cagataygulten/horse-racing-prediction | 1 haftalık csv (12–18.04.2021) + model | 2021 | git | MIT | tjk.org'dan kazınmış | RED | eski, tek hafta, yasak alandan türemiş |
| 16 | desscartes/horseride | kupon arayüzü, program csv | 2026-10 | git | yok | medya-cdn.tjk.org CSV | RED | yasak alan |
| 17 | erkansinan/horsewashing | tjk_real_races.csv, program jsonl | 2026-08/09 | git | yok | medya-cdn.tjk.org | RED | yasak alan + lisanssız |
| 18 | Mehmet-Pasha/ganian | ganyan aracı | 2026-10 | git | yok | ebayi.tjk.org | RED | yasak alan |
| 19 | skynet34/horseIQ | analiz | 2026-10 | git | yok | vhs.tjk.org | RED | yasak alan |
| 20 | hakanberil2010-cpu/yaristutkusu | topluluk sitesi | 2026-10 | git | yok | tjk.org AGFv2 | RED | yasak alan |
| 21 | Metin-1/Gazi-Web-Site | Gazi koşusu sitesi | 2026-03 | git | yok | medya-cdn.tjk.org | RED | veri yok, yasak alan |
| 22 | tnaekc25/horse-racing | yenibeygir.com kazıyıcı | 2025-02 | git | yok | üçüncü taraf (TJK verisi) | RED | yenibeygir şartları doğrulanamadı → belirsiz |
| 23 | Elif-Yildiz/at-yarisi-siralama-tahmini | LightGBM LambdaRank (Hong Kong verisi) | 2026-10 | git | yok | – | YÖNTEM | m6_rank deneyinin esin kaynağı; veri Türkiye değil |
| 24 | Hidayet17/at-yarisi-tahmini-modeli | Excel modeli (Ankara) | 2026-08 | git | yok | – | RED | veri yok |
| 25 | buyhan-lab/kosai-at-yarisi-analiz | sinyal doğrulama notları | 2026-07 | git | yok | – | RED | veri yok |
| 26 | cnszr71/tjk-racing-agent | ajan çerçevesi | 2026-10 | git | yok | – | RED | veri yok |
| 27 | uruzgar/AtYarisi | "geçmiş yarışlar veri tabanı" | 2026-02 | git | yok | – | RED | depoda veri dosyası yok |
| 28 | huseyinhim20-prog/TRAKUS96 | analiz | 2026-09 | git | yok | – | RED | boş |
| 29 | dogankorkmaz-tjk/tjk-sistem — agftablosu.com, liderform, ganyancanavari, nalsesleri yoklamaları | üçüncü taraf AGF/form siteleri | – | erişilemedi | şartlar doğrulanamadı | içerik TJK'dan türemiş | RED | şart belirsiz; AGF ancak lisanslı kaynakla düşünülebilir |
| 30 | sporx.com `at-yarisi-agf`, `muhtemeller`, `sonuclar` | AGF yüzdeleri, muhtemel oranlar ("TJK tarafından") | güncel | HTML | "Yasal Uyarı" sayfası; veri lisansı yok | TJK verisinin yeniden yayını | RED | kazıma izni yok/belirsiz; sabah AGF'si değerli olurdu ama yasal yol yok |
| 31 | Kaggle "sanlian / Turkiye Horse Racing January 2024 Race Results" (baselight aynası) | 1 aylık sonuç | 2024-01 | Kaggle | doğrulanamadı | büyük olasılıkla tjk.org kazıması | RED | dönem aynanın dışında, tek ay, lisans belirsiz |
| 32 | Kaggle/baselight Hong Kong (gdaley/hkracing, jeffreymuller 2013–2020) | HK sonuç + oran | 1997–2020 | Kaggle | çeşitli | – | RED | Türkiye değil (yalnız yöntem kıyası) |
| 33 | HF forum "Huggy" Fransız yarışları veritabanı | 356 bin Fransız koşusu | 1996–2026 | HF | belirsiz | – | RED | Türkiye değil |
| 34 | AltılıOyna (Product Hunt) | ticari tahmin platformu | 2026 | web | kapalı | – | RED | açık veri yok |
| 35 | The Racing API (theracingapi.com) | ticari yarış verisi | 2017–2026 | API | **ücretli** | – | RED | ücretli |
| 36 | renavon.com HKJC paketleri | HK oran/sonuç | – | API | ücretli | – | RED | ücretli, Türkiye değil |
| 37 | Equibase / Apify Equibase scraper | ABD verisi | – | – | ücretli/şartlı | – | RED | Türkiye değil |
| 38 | PyPI: `tjk`, `tjk-api`, `tjkapi`, `tjk-data`, `ganyan`, `altili`, `hipodrom`, `atyarisi`, `at-yarisi`, `pytjk`, `tjk-scraper`, `horse-racing`, `horseracing` | – | – | pypi.org JSON | – | – | RED | hiçbiri yok (404) |
| 39 | PyPI `racing-data` (justjasongreen), `pedigree` (jbaber) | Avustralya yarış sınıfları; genel soy ağacı aracı | – | PyPI | MIT / GPL | – | RED | veri değil, Türkiye değil |
| 40 | npm arama "tjk", "horse racing turkey" | `@tjk/sentry-vue3`, `hkjc-api` … | – | npm | – | – | RED | ilgisiz |
| 41 | Pedigri (allbreedpedigree, ifce infochevaux, arabianhorses.org DataSource, tbheritage) | baba/anne hatları | – | web | kazıma yasak / üyelik / yabancı atlar | – | RED | Türk atlarını kapsayan açık + lisanslı pedigri bulunamadı; TJK pedigrisi yasak alanda |
| 42 | Ekiz, Koçak, Yılmaz (2005) *Arch. Anim. Breed.* 48:121 — İngiliz atı yarış özelliklerinin kalıtımı | derece h²≈0,32, en iyi derece h²≈0,47, sıra h²≈0,13; yaş, cinsiyet, ay etkili | akademik | açık PDF | CC BY | – | BİLGİ | pedigri sinyali olsaydı en iyi dereceye anlamlı katkı beklenirdi; veri yok |
| 43 | Koçak & Ekiz (2005) *Indian Vet. J.* — çevresel etkenler | ay/mevsim, pist | akademik | özet yok | – | – | BİLGİ | hava/pist sinyalinin dayanağı |
| 44 | YÖK tez: "Devlet haraları orijinli safkan Arap atlarının yarış performansı" | pist (çim/kum) ve mevsim anlamlı | 1960–1988 | acikbilim.yok.gov.tr | açık erişim | – | BİLGİ | mevsim/pist etkisi; veri yok |
| 45 | Türk Arap atı pedigri analizi (Uludağ Üni., akrabalı yetiştirme) | popülasyon yapısı | akademik | avesis | – | – | BİLGİ | açık veri yok |
| 46 | arXiv 2503.16470 (Ornstein–Uhlenbeck: sürü ve bilgili bahisçi), 2207.04981 ("What AI can do for horse racing"), 2410.21484 (spor bahsi ML derlemesi); Maynooth "Weather and racing" (2001) | oran hareketi, hava–piyasa etkinliği | akademik | açık | – | – | BİLGİ | (2) ve (7)'nin yöntem dayanağı |

Ayrıca bakılıp sonuç vermeyenler: Meteostat toplu veri (CC BY-NC 4.0, istasyon tabanlı — Open-Meteo yedeği olabilir),
NASA POWER (kamu malı, 0,5° — yedek), NOAA GHCN-Daily (kamu malı, istasyon) — üçü de bu oturumdan erişilemedi;
üretimde Open-Meteo yeterli. Zenodo/Figshare/data.world/Google Dataset Search aramalarında Türkiye at yarışı veri
seti çıkmadı.

## Arama sorguları

WebSearch (Türkçe/İngilizce, lakap ve yazım varyantlarıyla): `TJK at yarışı veri seti dataset kaggle` · `turkish horse
racing dataset` · `kaggle turkiye horse racing race results dataset` · `"sanlian" turkiye horse racing kaggle` · `at yarışı
makine öğrenmesi tahmin tez dergipark` · `at yarışı derin öğrenme yüksek lisans tezi yarış sonucu tahmini` · `dergipark at
yarışı tahmin yapay sinir ağı safkan arap performans` · `github tjk scraper ganyan python` · `"altılı ganyan" tahmin yapay
zeka github` · `huggingface datasets horse racing turkey tjk` · `horse racing pedigree open dataset arabian thoroughbred sire
dam csv` · `horse racing pedigree database turkey "tjk" sire dam open data arabian` · `tjk api github npm "tjk" at yarışı
paket` · `site:github.com tjk at yarışı` · `site:github.com ganyan` · `site:github.com "horse racing" turkey OR turkish OR
tjk` · `site:github.com hipodrom OR veliefendi` · `yenibeygir.com at yarışı istatistik` · `agftablosu.com AGF tablosu` ·
`liderform at yarışı form analiz` · `"AGF" at yarışı nedir altılı ganyan favorileri yüzde tahmin başarısı` · `sporx.com
yasal uyarı içerik izinsiz kopyalanamaz` · `zenodo OR figshare horse racing dataset results odds` · `"tjk" csv veri indir at
yarışı sonuçları excel github` · `reddit turkish horse racing data tjk betting model` · `arxiv horse racing prediction
learning to rank plackett-luce neural 2024 2025` · `horse racing track condition weather rainfall effect prediction model
going rain study` · `Open-Meteo historical weather API license CC BY 4.0 non-commercial terms` · `Meteostat bulk data license
CC BY-NC turkey stations` · `Google dataset search "horse racing" turkey OR istanbul dataset`.

GitHub depo araması (gece araştırmacısı, `data/at/arastirma.json`): `tjk in:name,description,readme` · `jokey kulübü` ·
`"at yarışı"` · `horse racing turkey` · `horse racing prediction conditional logit` · `horse racing benter model` · `harville
exacta probability` · `idman galop` · `tjk idman` · `idman at yarışı` · `galop at` · `horse workout turkey` · `horse racing
workout data`. Bu oturumdan ek GitHub arama API'si denemesi (tjk, tjk data/scraper/api/bot, ganyan, altılı/altili/6'lı,
hipodrom, veliefendi, at yarışı/yarisi, agf, handikap puanı, galop, idman, pedigri, safkan arap, İngiliz atı, jokey,
antrenör, tay, kısrak, sprinter, horse racing lambdarank/benter/speed figure …) oturum politikasıyla engellendi (403).

PyPI/npm doğrudan ad sorgusu: yukarıdaki 13 PyPI adı; npm `tjk`, `tjk-api`, `ganyan`, `altili`, `hipodrom`, `atyarisi`,
`tjk-scraper` + npm arama `tjk`, `horse racing turkey`.

## Yasal notlar

- **Kullanılabilir ve kullanılan:** cenkozgur/tjk-data (kamuya açık ayna; önceden onaylı) ve onun git geçmişi (aynı
  kaynak, aynı şart — yalnız türetilmiş ölçüm, ham veri depoya girmez). **Open-Meteo** (CC BY 4.0): atıf "Hava verisi:
  Open-Meteo.com (CC BY 4.0)" + https://open-meteo.com/ bağlantısı; ücretsiz katman ticari olmayan kullanım içindir
  (bu proje hobi amaçlı). İndirilen hava dosyası `_hava/` altında, depoya yazılmaz.
- **Çevrimdışı ölçüm istisnası:** tjk-sistem deposundaki `gunluk.csv` yalnız Open-Meteo verisinin kopyası olduğu için
  ölçümde kullanıldı (veri CC BY 4.0); depo lisanssız olduğundan üretime **bağlanmadı**, üretim veriyi Open-Meteo'dan
  kendisi çeker. Aynı depodaki galop/idman/AGF/canlı oran dosyaları atyarisi/tjk kazımasıdır → açılmadı.
- **Yasak alan türevleri** (10–21, 9, 29–31): hepsi tjk.org / medya-cdn / vhs / ebayi.tjk.org / atyarisi API'lerine istek
  atıyor ya da bunlardan kazınmış; bağlanmadı ve çalıştırılmadı.
- **Bulunamayanlar:** start/kulvar, handikap puanı, sahip/yetiştirici, pedigri, idman/galop, AGF ve sabah oranları için
  yasal + lisanslı + ücretsiz açık kaynak YOK. Bunlar ancak TJK'nın açık lisanslı bir veri yayını ya da aynanın bu alanları
  eklemesiyle gelebilir (gece araştırmacısı izlemeye devam ediyor).

## Ölçüm sonuçları

Bkz. `lab/at/RAPOR.md` → "v6 turu: derin tarama" bölümü ve `data/at/deneyler_v6.json`.
