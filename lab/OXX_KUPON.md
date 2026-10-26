# 🎟️ OXXai kupon robotu ve sürekli öğrenme — veri sözleşmesi (v1, 2026-10-26)

Bu belge arayüzü yapacak uzman içindir: **hangi dosya, kim yazar, hangi alan ne demek**. Arayüz yalnız okur; hiçbir dosyayı
yazmaz. Alan eklemek geriye uyumludur (yeni alanı tanımayan okuyucu görmezden gelir); alan silmek / anlam değiştirmek `v` artırır.
Hobi amaçlı ölçümdür: **para tutarı, bahis bağlantısı yoktur**; `oran` yalnız bilgi amaçlı bülten oranıdır. 18+ uyarısı `uyari` alanındadır.

## Dosyalar ve yazarlar (tek yazar kuralı)

| Dosya | Yazar (iş akışı) | Sıklık | İçerik |
|---|---|---|---|
| `data/oxx_kupon/<GGGG-AA-GG>.json` | `scripts/oxx_kupon.py` (update.yml) | saatlik :17 | O günün **futbol + basket** kilitli kuponları ve sonuçları; `at` bölümü at dosyasının salt-okunur kopyası |
| `data/oxx_kupon/at/<GGGG-AA-GG>.json` | `scripts/oxx_kupon.py --at` (at-canli.yml) | 30 dk (yarış günü) | O günün **at** kilitli kuponları ve sonuçları (en güncel at verisi burada) |
| `data/oxx_karne.json` | `scripts/oxx_kupon.py` (update.yml) | saatlik | Strateji başına karne |
| `data/oxx_ayar.json` | `lab/oxx_ogren.py` (otonom-ekip.yml) | 03:07 / 15:07 UTC | Öğrenilmiş strateji ayarları (yalnız varsayılandan farklılar) |
| `data/deney_kuyrugu.json` | `lab/oxx_ogren.py` | aynı | Deney adayları |
| `data/ogrenme_gunlugu.json` | `lab/oxx_ogren.py` | aynı | Her kararın kaydı (ne denendi, rakamlar, kabul/ret) |
| `data/oxx_rollback.json` | `lab/oxx_ogren.py` | aynı | OXXai geri alma durumu (rollback.json kalıbı) |

Gün = **İstanbul takvim günü** (maçın/koşunun TSİ başlama günü). Zamanlar: `*_utc` = `GGGG-AA-GGTSS:DDZ`, `*_tsi` = `GGGG-AA-GG SS:DD` (İstanbul).

## Stratejiler (kimlikler kararlıdır)

| id | spor | ad | kural (varsayılan ayar) |
|---|---|---|---|
| `fb_altin` | futbol | Altın kupon | Uygulamadaki öneri (recOf: MS 1/X/2, 2,5 A/Ü; oranı olan seçenekler içinde en yüksek OXXai olasılığı) ≥ `p_min` 0,78, oran 1,15–2,00, günde en fazla 3 maç, hepsi tek kupon |
| `fb_70` | futbol | %70+ kupon | Olasılığı ≥ 0,70 ve oranı ≥ 1,05 öneriler (en olası 12) içinden birlikte tutma ≥ 0,70 kalan 2–4 maçlık kombinasyonların toplam oranı en yüksek olanı |
| `fb_3lu` | futbol | 3 maçlık en olası | En olası 3 öneri (≥ 0,58, oran ≥ 1,15) |
| `fb_deger` | futbol | Değerli kupon | Her maçta OXXai olasılığı × oran en yüksek seçenek (olasılık ≥ 0,40); değer katsayısı en yüksek 2 maç. Bacakta `deger` = p × oran |
| `fb_guvenli` | futbol | Güvenli kupon (yeni pazarlar) | `pazar_karne.json` → `oneriye_uygun` yeni pazarlar; her maçın en olası seçeneği ≥ 0,80, iddaa oranı (yoksa adil oran 1/p) ≥ 1,15; en olası 3 maç |
| `bk_en_olasi` | basket | Günün en olası seçimleri | Kazanma olasılığı Φ(fark/σ·ölçek) ≥ 0,60 en olası 3 maç (3.'sü < 0,70 ise 2 maç) |
| `at_altin` | at | Altın atlar | `data/at/model.json → altin_kural` (p ≥ p_min, ikinciden fark ≥ fark_min, günde ≤ gunluk_max); her at ayrı ganyan kuponu |
| `at_sirali_ikili` | at | OXXai sıralı ikili | Her koşuda (≥ 4 at) indirimli Harville ile en olası sıralı 1.–2. |
| `at_ikili` | at | OXXai ikili | Her koşuda (≥ 7 at) en olası sırasız ilk iki |
| `at_cifte` | at | OXXai çifte | Her hipodromda ardışık iki koşu favorisinin birlikte kazanma olasılığı en yüksek çift |
| `at_altili_dar` / `_orta` / `_genis` | at | 6'lı 64 / 192 / 576 | `lab/at/altili.py` kuponu, ilk ayaktan önce kilitlendiği haliyle |

Olasılık kaynağı: futbol = pazar motorunun sunduğu yol (`fixtures.json → pz`, uygulamanın gösterdiğiyle aynı);
basket = kilitli `bk_predlog` tahmini; at = gece robotunun koşudan önce kilitlediği `data/at/tahmin/<gün>.json`.
Kupon olasılığı `p` = bacak olasılıklarının çarpımı (farklı maçlar bağımsız varsayılır).

## `data/oxx_kupon/<gün>.json`

```jsonc
{
  "tarih": "2026-10-26", "oxx_v": "oxx1",
  "geriye_donuk": false,            // true: kilit sistemi o gün çalışmıyordu, kuponlar SONRADAN kuruldu (rozet göster: "geriye dönük")
  "not": "…",                       // yalnız geriye dönük dosyalarda
  "bilgi_kesimi": "…",              // yalnız geriye dönük: kullanılan bilginin sınırı
  "uyari": "…18+",
  "futbol": {                       // yoksa o gün henüz kilitlenmedi (en az 10 aday maç gerekir)
    "kilit_utc": "…", "kilit_tsi": "…",            // KİLİT ANI: bu bölüm bir daha değişmez (yalnız sonuç alanları dolar)
    "motor": {"oxx": "oxx1", "futbol": "2026-10-25.ml80", "pazar_v": 1, "basket": "…", "at": "…"},
    "ayar_surum": "varsayilan",     // data/oxx_ayar.json sürümü (kilit anındaki)
    "aday_mac": 42,
    "kaynak": "…",                  // yalnız geriye dönük: arşiv (iddaa) ya da season.json (kapanış oranı)
    "kuponlar": [KUPON, …]
  },
  "basket": { …futbol ile aynı biçim… },
  "at": { "kilit_utc", "kilit_tsi", "motor", "ayar_surum", "kuponlar": [KUPON…], "kaynak": "data/oxx_kupon/at/<gün>.json" },  // ≤1 saat gecikmeli kopya
  "golge": { "futbol": {"ayar_surum": "onceki", "kuponlar": [KUPON…]} },   // isteğe bağlı: izlenen ayar değişikliğinde önceki ayarla kurulan kupon (öğrenme döngüsü için; arayüzde gösterme)
  "guncelleme_utc": "…"
}
```

### KUPON

```jsonc
{
  "id": "2026-10-26/fb_altin/1",    // kararlı kimlik
  "strateji": "fb_altin",
  "p": 0.5263,                      // OXXai'ye göre birlikte tutma olasılığı (0–1)
  "oran": 1.8,                      // bacak oranlarının çarpımı (bilgi; herhangi bir bacakta oran yoksa null)
  "durum": "bekliyor" | "tuttu" | "tutmadi" | "gecersiz",   // gecersiz: sonuç 3–4 gün içinde bulunamadı (ertelendi); karneye girmez
  "tuttu": true | false | null,
  "bacaklar": [BACAK, …],
  // at'a özgü: "tur": "cifte" (at_cifte); 6'lı: "altili_id", "hipodrom", "saat", "kombinasyon", "kilit_tsi", "kosudan_once", "oxx_kilit_utc"
}
```

### BACAK

Futbol: `{"mac": "tr1|2026-10-26|Galatasaray|Fenerbahçe", "lg": "tr1", "lig": "Türkiye Süper Lig", "h": "…", "a": "…", "bas_utc": "…", "iid": 3241596|null,
"kod": "1", "secim": "MS 1", "p": 0.78, "oran": 1.42, "deger": 1.07 (yalnız fb_deger), "sonuc": "2-1", "iy": "1-0", "tuttu": true|false|null}`
— `kod` pazar kataloğu kodudur (`pazar_karne.json → katalog`); `secim` görünen addır.

Basket: `{"mac": "<espn/iddaa id>", "lg", "lig", "h", "a", "bas_utc", "kod": "1"|"2", "secim": "MS 1 (ev)", "p", "oran"|null, "tahmin": "112-104", "sonuc": "108-101", "tuttu"}`

At: `{"kosu_id": "2026-10-26/Bursa/5", "hipodrom", "kosu", "saat", "bas_utc", "tur": "ganyan"|"sirali_ikili"|"ikili", "secim": ["3"] | ["3","7"], "adlar": ["…"], "p",
"fark" (yalnız at_altin), "sonuc": ["3","7","1","5"] (ilk dört at no), "tuttu"}`;
6'lı ayağı: `{"kosu", "saat", "tur": "ayak", "secim": [at no…], "p" (ayak olasılığı), "kazanan", "tuttu"}`.

## `data/oxx_kupon/at/<gün>.json`

`{"tarih", "oxx_v", "geriye_donuk", "uyari", "kilit_utc", "kilit_tsi", "motor", "ayar_surum", "tahmin_kilit_tsi", "aday_kosu", "kuponlar": [KUPON…], "guncelleme_utc"}`
Kilit: o gün at-canli'nin, gece robotunun tahmin dosyası hazır olduktan sonraki ilk çalıştırması; yalnız henüz başlamamış koşular.
6'lılar altili.py ilk ayakta kilitlediğinde (yalnız `kosudan_once`) bir kez eklenir.

## `data/oxx_karne.json`

```jsonc
{
  "v": 1, "oxx_v": "oxx1", "guncelleme_utc": "…", "uyari": "…", "aciklama": "…",
  "donem": {"geriye_donuk": ["2026-09-26", "2026-10-25"], "canli": ["2026-10-26", "…"]},
  "ayar_surum": "…", "motor": {…},
  "stratejiler": {
    "fb_altin": {
      "ad": "Altın kupon", "spor": "futbol", "kural": "…",
      "n": 8, "tutan": 2, "isabet": 0.25,            // puanlanmış kupon sayısı, tutan, oran
      "beklenen": 5.02, "beklenen_oran": 0.6275,     // Σ kupon p (iyi kalibre robotta tutan ≈ beklenen)
      "z": -2.25,                                    // (tutan − beklenen)/√Σp(1−p); |z|>2 sistematik sapma
      "bacak": {"n": 19, "tutan": 13, "isabet": 0.6842, "beklenen": 15.55},   // maç/satır isabeti
      "kalibrasyon": {"gercek_bolu_beklenen": 0.398, "kovalar": [{"aralik": "0.5-0.6", "n", "tahmin", "gercek"}]},
      "son7": {…aynı özet…}, "son30": {…}, "canli": {…}, "geriye_donuk": {…},
      "seri": {"guncel": -2, "en_uzun_tutan": 2, "en_uzun_tutmayan": 4},   // guncel > 0: art arda tutan, < 0: tutmayan
      "bekleyen": 1,                                  // sonucu beklenen kupon
      "gunluk": [{"d": "2026-10-25", "n": 1, "tutan": 0, "beklenen": 0.6, "geriye_donuk": true}]   // son 30 gün
    }, …
  }
}
```
Özet alanları (`son7`, `son30`, `canli`, `geriye_donuk`) `{n, tutan, isabet, beklenen, beklenen_oran, z, bacak}` biçimindedir; `n = 0` ise yalnız `{n, tutan, isabet: null, beklenen: 0}`.
**Arayüz önerisi:** "canlı" ve "geriye dönük" sayılarını ayrı göster; geriye dönük kısmı açıkça işaretle.

## Öğrenme döngüsü dosyaları (bilgi paneli için)

- `data/oxx_ayar.json`: `{"v", "surum", "aciklama", "params": {strateji: {ayar: değer}, "duzeltme": {"pazar": {kod: {"a","b"}}}, "lig_dis": [lig]},
  "izlenen": [{"anahtar", "anahtar_yol", "onceki", "yeni", "stratejiler", "alan", "tur", "kabul_tarihi", "yeniden_sinama"}], "gecmis": [{"tarih", "olay": "kabul"|"geri_alindi"|"kalici", "anahtar", …}]}`
- `data/deney_kuyrugu.json`: `{"guncelleme", "aciklama", "adaylar": [{"anahtar", "tur": "esik"|"pazar"|"lig"|"bk_olcek"|"at_tau", "alan", "yol", "deger", "stratejiler",
  "sinyal": {"n", "tutan", "beklenen", "z", "kaynak"}, "aciklama", "eklenme", "durum": "bekliyor"|"denendi", "oncelik", "son_deneme", "sonuc"}]}`
- `data/ogrenme_gunlugu.json`: `{"v", "guncelleme", "kurallar", "sayac": {"futbol-2026": m, …}, "ozet", "kayitlar": [{"tarih", "anahtar", "tur", "alan", "aciklama", "sinyal", "deger",
  "olcut", "alfa", "deneme_no", "secim": {gun, fark, taban, aday}, "sinama": {gun, fark, alt_sinir, bootstrap_B, taban, aday, bacak_taban, bacak_aday},
  "koruma": {altin_taban, altin_aday, guclu_taban, guclu_aday}, "karar": "kabul"|"ret"|"dondurulmus"|"veri_yetersiz"|"hata", "neden", "uygulandi", "sure_sn"}]}`;
  yeniden sınama kayıtları `"tur": "yeniden_sinama"`, `"karar": "kalıcı"|"GERİ ALINDI"|"uzatıldı"`, `"sanal": {onceki, yeni}`, `"canli_golge"`.
- `data/oxx_rollback.json`: `{"aktif", "baslangic", "bitis", "neden", "params": {yol: önceki değer}, "donmus": {anahtar: bitiş}, "gecmis": [anahtar]}`.

## Öğrenme döngüsünün kuralları (özet)

1. **Sinyal:** kilitli OXXai kuponları/bacakları, `pazar_karne.json → canli`, `predlog.json` (lig), `bk_predlog.json`, `data/at/karne.json`;
   |z| ≥ 1,5 olan sistematik fark aday olur (öncelik |z|). Sinyal yoksa sıradaki keşif adayı (eşik ±0,02).
2. **Sanal oynatma:** bu yılın maçları, her gün yalnız o günden önce bilinenle (maç öncesi oran, önceki aylarla öğrenilmiş kalibratör,
   o günden önceki maçlarla basket modeli, sızıntısız at yeniden oynatması). Günler 2/3 seçim, 1/3 sınama.
3. **Kapı:** seçimde iyileşme; sınamada eşleştirilmiş gün bootstrap'ı (B=2000) tek yanlı alt sınır > 0, α = 0,05/m (m = o alanda bu yıl yapılan
   sınama sayısı, Bonferroni); Altın ve güçlü (≥%70) bacak isabeti düşmez; kupon sayısı ≥ tabanın %70'i; koruyucu geri alması aktifken kabul yok.
   Günde en fazla 3 aday (iş akışı iki kez çalışsa da).
4. **Uygulama:** yalnız `oxx_ayar.json` (motorun `model.json` ayarlarına dokunulmaz; onları saatlik motor öğrenir, koruyucu izler).
5. **14 gün sonra yeniden sınama:** kabulden sonraki günlerle sanal oynatma + canlı gölge kuponlar; kötüleşme (isabet −2 puan ya da Brier +0,002;
   canlıda −5 puan ve Brier kötü) → otomatik geri alma, anahtar 14 gün dondurulur. Veri azsa 7 gün uzatılır (en fazla 2 kez).

## Yerel deneme

```
python scripts/oxx_kupon.py                         # futbol + basket kilit/puan + karne
python scripts/oxx_kupon.py --at                    # at kilit/puan
python scripts/oxx_kupon.py --geriye 30             # geriye dönük 30 gün (varsayılan kurallarla) + karne
python scripts/oxx_kupon.py --simdi 2026-10-26T08:00:00+00:00
python lab/oxx_ogren.py --kuru                      # öğrenme döngüsü, dosya yazmadan
```
