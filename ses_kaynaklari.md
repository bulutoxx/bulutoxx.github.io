# OXXai ses kaynakları (v121)

OXXai'deki gerçek kayıtlar `ses/v121/` klasöründedir. Her kayıt Opus (`.webm`) ve MP3 (`.mp3`, iOS yedeği) olarak durur.
Hepsi mono, 48 kHz. Kayıtlar kısaltıldı, baştaki ve sondaki sessizlik temizlendi, yumuşak giriş ve çıkış eklendi, ses yüksekliği eşitlendi (tepe ≤ −1,5 dBFS).
Bu değişiklikler aşağıda "değiştirildi" diye geçer.

Uygulamada atıf Ayarlar › Sesler bölümünün altındaki "Ses kaynakları" satırında gösterilir.
Telifli maç anonsu, TV ya da yayın kaydı kullanılmamıştır.

Kayıtlar Ubuntu 24.04 (noble) arşivindeki özgür paketlerden alındı.
Her dosyanın lisansı o paketin `debian/copyright` (DEP-5) kaydında dosya bazında belirtilmiştir.
Freesound ve SoundBible bu çalışma ortamından erişilemediği için lisans, Debian/Ubuntu paketleyicilerinin dosya bazındaki kaydıyla doğrulandı.

| Dosya | Kullanıldığı ses | Asıl kayıt ve yazarı | Lisans | Kaynak | Alındığı paket |
|---|---|---|---|---|---|
| `gol_kalabalik` | Gol (stadyum patlaması), rakip gol "ahh" (perdesi düşürülüp süzülerek), kırmızı kart "ooh" | "goal scored", jordiroquer (2012) | CC BY 3.0 | https://freesound.org/people/jordiroquer/sounds/148153/ | `supertuxkart-data` 1.4+dfsg-3ubuntu1, `data/sfx/goal_scored.ogg` |
| `alkis` | Gol alkış dalgası, KUPO tuttu, bir maç tuttu, maç bitti, basket, at KUPO'su | "10 Second Applause", Mike Koenig (2009) | CC BY 3.0 | http://soundbible.com/989-10-Second-Applause.html | `supertuxkart-data` 1.4+dfsg-3ubuntu1, `data/sfx/gp_end.ogg` |
| `tezahurat` | Gol tezahüratı, KUPO tuttu, at kazandı, basket maç bitti | `sg_cheers.mp3`, Steffen Gerlach (C-evo, 1999–2013) | CC BY 3.0 | https://sourceforge.net/projects/c-evo-eh/ | `c-evo-dh-data` 1.10-1build3, `Sounds/sg_cheers.mp3` |
| `dortnala` | At start, at kazandı, at KUPO'su tuttu | `sg_horsemen.mp3`, Steffen Gerlach (C-evo, 1999–2013) | CC BY 3.0 | https://sourceforge.net/projects/c-evo-eh/ | `c-evo-dh-data` 1.10-1build3, `Sounds/sg_horsemen.mp3` |
| `duduk` | Maç başladı, ilk yarı bitti, maç bitti, kırmızı kart (hakem düdüğü) | "whistle", cityrocker | CC0 1.0 | https://freesound.org/people/cityrocker/sounds/121342/ | `cdogs-sdl-data` 2.0.0+dfsg-1, `sounds/whistle.ogg` |
| `file` | Basket seçimi tuttu (file "swish") | "swoosh echo", Electroviolence | CC0 1.0 | https://freesound.org/people/Electroviolence/sounds/234553/ | `cdogs-sdl-data` 2.0.0+dfsg-1, `missions/custom/techdemo/funwithguns.cdogscpn/sounds/swoosh_echo.ogg` |
| `buzzer` | Basket seçimi tuttu, takip edilen basket maçı bitti | `buzz.wav`, TuxMath | Kamu malı (Public Domain) | https://github.com/tux4kids/tuxmath | `tuxmath-data` 2.0.3-9build2, `data/sounds/buzz.wav` (`Files: data/sounds/*` → Public Domain) |

## Sentez olan sesler

Aşağıdaki sesler gerçek kayıt değildir; uygulama içinde Web Audio ile üretilir:

- menü ve arayüz sesleri
- OXXai imza motifi (D5 → A5 → F#6)
- brass ve korna vurguları
- at "çağrı" borusu (OXXai'nin kendi bestesi)
- KUPO ekle/çıkar
- "tutmadı"

Gerçek kayıtlar yüklenemezse (çevrimdışı ya da ağ hatası) bu olaylar da sentez yedeğiyle çalar.

## Lisans notları

- **CC BY 3.0:** https://creativecommons.org/licenses/by/3.0/ — atıf zorunludur. Atıf, uygulamadaki "Ses kaynakları" satırında ve bu dosyada verilmiştir. Kayıtlar değiştirilmiştir.
- **CC0 1.0:** https://creativecommons.org/publicdomain/zero/1.0/ — atıf gerekmez, nezaketen yazılmıştır.
- **Kamu malı:** TuxMath Debian kaydı, `data/sounds/*` dosyalarının kamu malı olduğunu belirtir. `01_rush.ogg`, `02_on_the_edge_of_the_universe.ogg` ve `03_gravity.ogg` bu kuralın dışında tutulmuştur; bu dosyalar kullanılmadı.

## Önbellek

`ses/` yolu `data/` dışındadır. Mevcut `sw.js`, `data/` dışındaki dosyaları ilk istekten sonra kendi önbelleğinden (cache-first) verir.
Bu yüzden kayıtlar bir kez indirilir. Uygulama sürümü değişince servis çalışanının önbelleği yenilenir.
Klasör adı sürümlü (`v121`) tutulduğu için eski bir kayıt bayat kalmaz.

İndirme ilk kullanıcı dokunuşundan sonra, tarayıcı boşta kalınca bir kez yapılır; uygulama açılışını yavaşlatmaz.
Cihaz başına indirilen boyut yaklaşık 130 KB (Opus) ya da 185 KB'dir (MP3).
