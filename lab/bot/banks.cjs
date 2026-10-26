// OXXai sohbet koçu — aday bilgi bankası.
// Koç her gece buradan (ve günün verisinden) aday üretir; aday yalnız telefondaki bot üzerinde sınanıp işe yararsa ve
// tüm test kümesinin başarısını düşürmezse data/bot_kb.json'a girer. Burada kullanıcı mesajı YOKTUR; hepsi elle yazılmış örnek cümlelerdir.

// ---- Kalıp cümleler: [soru, kategori, ölçüt, bunun yerine kullanılacak bilinen soru] ----
const P = (q, k, c, canon) => ({ q, k, c: c || {}, canon });
const para = [
  // tarih / program
  P("bugün hangi karşılaşmalar var", "tarih", { day: ["+0"] }, "bugün hangi maçlar var"),
  P("bugünün programı", "tarih", { day: ["+0"] }, "bugün hangi maçlar var"),
  P("bugün kimler oynuyor", "tarih", { day: ["+0"] }, "bugün hangi maçlar var"),
  P("bugün kimin maçı var", "tarih", { day: ["+0"] }, "bugün hangi maçlar var"),
  P("bugünün fikstürü", "tarih", { day: ["+0"] }, "bugün hangi maçlar var"),
  P("bugün oynanacak maçlar", "tarih", { day: ["+0"] }, "bugün hangi maçlar var"),
  P("bu akşamki maçlar", "tarih", { day: ["+0", "+1"] }, "bu akşam hangi maçlar var"),
  P("akşamki karşılaşmalar", "tarih", { day: ["+0", "+1"] }, "bu akşam hangi maçlar var"),
  P("bu geceki maçlar neler", "tarih", { day: ["+0", "+1"] }, "bu akşam hangi maçlar var"),
  P("yarınki karşılaşmalar", "tarih", { day: ["+1"] }, "yarın maç var mı"),
  P("yarın kimler oynuyor", "tarih", { day: ["+1"] }, "yarın maç var mı"),
  P("yarın oynanacak maçlar", "tarih", { day: ["+1"] }, "yarın maç var mı"),
  P("yarının programı", "tarih", { day: ["+1"] }, "yarın maç var mı"),
  P("ertesi gün maç var mı", "tarih", { day: ["+2"] }, "2 gün sonra hangi maçlar var"),
  P("hafta sonu kimler oynuyor", "tarih", { day: ["Cmt", "Paz"] }, "hafta sonu maçları"),
  P("maç programı", "tarih", { day: ["+0", "+1"] }, "bugün hangi maçlar var"),
  P("bugün maç var mı", "tarih", { day: ["+0"] }, "bugün hangi maçlar var"),
  P("bugun mac varmi", "tarih", { day: ["+0"] }, "bugün hangi maçlar var"),
  // güvenli
  P("riski az maçlar", "guvenli", {}, "en güvenli maçlar"),
  P("risksiz maç ver", "guvenli", {}, "en güvenli maçlar"),
  P("en olası maçlar", "guvenli", {}, "en güvenli maçlar"),
  P("yüksek ihtimalli maçlar", "guvenli", {}, "en güvenli maçlar"),
  P("yatmayacak maç ver", "guvenli", {}, "en güvenli maçlar"),
  P("sağlama maç ver", "guvenli", {}, "en güvenli maçlar"),
  P("en emin olduğun maçlar", "guvenli", {}, "en güvenli maçlar"),
  P("güvenilir maçlar", "guvenli", {}, "en güvenli maçlar"),
  P("kesine yakın maçlar", "guvenli", {}, "en güvenli maçlar"),
  P("düşük riskli maçlar", "guvenli", {}, "en güvenli maçlar"),
  P("en çok güvendiğin maç", "guvenli", {}, "en güvenli maçlar"),
  P("tutma ihtimali en yüksek maçlar", "guvenli", {}, "en güvenli maçlar"),
  P("en garanti 2 maç", "guvenli", { n: 2 }, "en güvenli 2 maç"),
  // altın
  P("günün altın seçimi", "altin", {}, "altın tahminler"),
  P("altın maç var mı", "altin", {}, "altın tahminler"),
  P("altınlar neler", "altin", {}, "altın tahminler"),
  P("bugünün altını", "altin", {}, "altın tahminler"),
  P("altın rozetli maçlar", "altin", {}, "altın tahminler"),
  // liste
  P("kupon oluştur", "liste", {}, "3 maçlık liste yap"),
  P("bana kupon yaz", "liste", {}, "3 maçlık liste yap"),
  P("üçlü kupon yap", "liste", { n: 3 }, "3 maçlık liste yap"),
  P("ikili liste hazırla", "liste", { n: 2 }, "2 maçlık liste yap"),
  P("kombine yap", "liste", {}, "3 maçlık liste yap"),
  P("3 maç seç listeye koy", "liste", { n: 3 }, "3 maçlık liste yap"),
  P("bir kupon ayarla", "liste", {}, "3 maçlık liste yap"),
  P("hazır kupon ver", "liste", {}, "3 maçlık liste yap"),
  // karne
  P("ne kadar isabetlisin", "karne", {}, "dünkü karne"),
  P("tahmin başarın ne", "karne", {}, "dünkü karne"),
  P("dün kaç tanesi tuttu", "karne", {}, "dünkü karne"),
  P("dün kaçta kaç yaptın", "karne", {}, "dünkü karne"),
  P("doğru bildin mi", "karne", {}, "dünkü karne"),
  P("kaç maç bildin", "karne", {}, "dünkü karne"),
  P("tutturma oranın kaç", "karne", {}, "dünkü karne"),
  P("istatistiklerin nasıl", "karne", {}, "dünkü karne"),
  P("dünkü tahminler ne oldu", "karne", {}, "dünkü karne"),
  P("sonuçların nasıl", "karne", {}, "dünkü karne"),
  // terimler
  P("kg ne anlama geliyor", "terim", { kw: /karşılıklı gol|iki takım(ın)? da gol/i }, "kg var ne demek"),
  P("üst ne demek", "terim", { kw: /3 (veya|ya da) daha fazla gol/i }, "2.5 üst nedir"),
  P("alt ne demek", "terim", { kw: /en fazla 2 gol/i }, "2,5 alt ne demek"),
  P("iy ne demek", "terim", { kw: /ilk yarı/i }, "iy ms ne demek"),
  P("ms ne demek", "terim", { kw: /ev sahibi|maç sonu/i }, "ms 1 nedir"),
  P("handikap nedir", "terim", { kw: /handikap/i }, "handikap ne demek"),
  P("çifte şans ne demek", "terim", { kw: /1X|iki sonuc/i }, "çifte şans nedir"),
  P("pas geçmek ne demek", "terim", { kw: /%\s?58|dengeli/i }, "pas ne demek"),
  P("güçlü tahmin nedir", "terim", { kw: /%\s?70/ }, "güçlü tahmin ne demek"),
  P("karşılıklı gol var ne demek", "terim", { kw: /iki takım(ın)? da gol/i }, "kg var ne demek"),
  // uygulama yardımı
  P("listeye nasıl eklenir", "apphelp", { kw: /Liste|ekle/ }, "listeye nasıl maç eklerim"),
  P("ana ekrana ekleme nasıl", "apphelp", { kw: /ana ekran/i }, "ana ekrana nasıl eklerim"),
  P("bildirimleri nasıl açarım", "apphelp", { kw: /bildirim|gol uyarısı/i }, "gol bildirimi nasıl açılır"),
  P("karne nerede", "apphelp", { kw: /karne/i, kw2: /Menü|menü/ }, "karneyi nerede görürüm"),
  P("uygulama ne işe yarıyor", "apphelp", { kw: /tahmin/i }, "bu uygulama ne işe yarar"),
  P("bu program ne yapıyor", "apphelp", { kw: /tahmin/i }, "bu uygulama ne işe yarar"),
  P("telefona nasıl yüklerim", "apphelp", { kw: /ana ekran/i }, "ana ekrana nasıl eklerim"),
  // yardım
  P("neler sorabilirim", "yardim", {}, "yardım"),
  P("ne sorabilirim", "yardim", {}, "yardım"),
  P("komutlar neler", "yardim", {}, "yardım"),
  P("seni nasıl kullanırım", "yardim", {}, "yardım"),
  P("yardım eder misin", "yardim", {}, "yardım"),
  P("ne işe yararsın", "yardim", {}, "yardım"),
  P("sana ne sorayım", "yardim", {}, "yardım"),
  // selam / teşekkür / kim
  P("selamün aleyküm", "selam", {}, "selam"),
  P("merhabalar", "selam", {}, "merhaba"),
  P("iyi günler", "selam", {}, "selam"),
  P("hayırlı akşamlar", "selam", {}, "iyi akşamlar"),
  P("selam dostum", "selam", {}, "selam"),
  P("eline sağlık", "tesekkur", {}, "teşekkürler"),
  P("çok teşekkür ederim", "tesekkur", {}, "teşekkürler"),
  P("sağ ol", "tesekkur", {}, "teşekkürler"),
  P("tşk", "tesekkur", {}, "teşekkürler"),
  P("teşekkür ederim bulut", "tesekkur", {}, "teşekkürler"),
  P("kimsin sen", "kim", {}, "sen kimsin"),
  P("sen nesin", "kim", {}, "sen kimsin"),
  P("adın ne", "kim", {}, "sen kimsin"),
  // canlı
  P("şu anda oynanan maçlar", "canli", {}, "canlı"),
  P("anlık maçlar", "canli", {}, "canlı"),
  P("maçlar başladı mı", "canli", {}, "canlı"),
  P("canlı maç var mı", "canli", {}, "canlı"),
  P("şimdi hangi maçlar oynanıyor", "canli", {}, "canlı"),
  P("şu an hangi maçlar var", "canli", {}, "canlı"),
];

// ---- Eş anlamlı kelimeler (kelime → bot'un bildiği karşılık). Yalnız bir kalıp cümleyi gerçekten düzeltiyorsa ve testi düşürmüyorsa girer. ----
const esanlam = {
  "karsilasma": "maç", "karsilasmalar": "maçlar", "karsilasmalari": "maçları", "karsilasmasi": "maçı",
  "musabaka": "maç", "musabakalar": "maçlar",
  "aksamki": "akşam", "geceki": "gece",
  "risksiz": "güvenli", "emniyetli": "güvenli", "guvenilir": "güvenli",
  "kombinasyon": "kupon",
  "bildin": "tuttu", "bildi": "tuttu", "tutturdun": "tuttu",
  "ispanyol": "ispanya", "italyan": "italya", "alman": "almanya", "fransiz": "fransa", "portekizli": "portekiz", "hollandali": "hollanda", "ingiliz": "ingiltere",
  "anlik": "canlı",
};
// çok kelimeli eş anlamlılar
const esanlamIfade = {
  "riski az": "en güvenli", "dusuk riskli": "en güvenli", "en olasi": "en güvenli", "yuksek ihtimalli": "en güvenli", "kesine yakin": "en güvenli",
  "en cok guvendigin": "en güvenli", "tutma ihtimali en yuksek": "en güvenli", "turk ligi": "süper lig", "ne anlama geliyor": "ne demek", "ne manaya gelir": "ne demek",
};

// ---- Terim sözlüğü (v69'un kendi terimlerinde olmayanlar). {veri} kısımları koç tarafından günün verisiyle doldurulur. ----
const sozluk = [
  { k: "xg", re: "\\bxg\\b|gol beklenti", q: "xg ne demek", kw: /gol beklentisi/i,
    html: "<b>Gol beklentisi (xG)</b>: bir takımın o maçta atması beklenen ortalama gol sayısı. OXXai bunu lig gol ortalaması, iç/dış saha gücü ve piyasa oranlarından hesaplar; ör. 1,8'e 0,9 beklenti ev sahibini favori yapar ama sonucu garanti etmez." },
  { k: "form", re: "\\bform\\w*", q: "form ne demek", kw: /son maç/i,
    html: "<b>Form</b>: takımın son maçlardaki gidişatı (son 5-6 maçın sonuçları ve golleri). OXXai formu tek başına değil, lig gücü ve piyasa oranlarıyla birlikte kullanır; form tek başına yanıltıcı olabilir." },
  { k: "elo", re: "\\belo\\b", q: "elo puanı nedir", kw: /güç/i,
    html: "<b>Elo puanı</b>: takımların güç puanı; her maçtan sonra kazanan, kaybedenden puan alır, sürpriz galibiyet daha çok puan getirir. OXXai'nin robot arenasında Elo robotu da yarışır; piyasaya bilgi eklemediği ölçüldüğü için ana tahminde ağırlığı yoktur." },
  { k: "poisson", re: "poisson", q: "poisson modeli nedir", kw: /skor/i,
    html: "<b>Poisson modeli</b>: iki takımın gol beklentisinden her skorun olasılığını hesaplayan klasik yöntem (ör. 1-0, 1-1, 2-1 için ayrı yüzdeler). Robot arenasındaki Poisson robotu bu yöntemi kullanır; uygulamadaki skor olasılıkları da gol beklentisine dayanır." },
  { k: "kalibrasyon", re: "kalibr", q: "kalibrasyon ne demek", kw: /geçmiş|arşiv/i,
    html: "<b>Kalibrasyon</b>: gösterilen yüzdenin, geçmişte aynı güvendeki tahminlerin gerçek tutma oranına göre düzeltilmesi. Yani %80 dediğim seçimler, kilitli arşivde gerçekten yaklaşık %80 tutmuş seviyededir.{karne}" },
  { k: "marj", re: "\\bmarj\\w*", q: "bahis marjı nedir", kw: /marj/i, kw2: /ayıkla/i,
    html: "<b>Bahis marjı</b>: şirketin oranlara eklediği pay; oranların ters çevrilmiş toplamı %100'ü aşar (ör. toplam %107 → %7 marj). OXXai piyasa olasılığını hesaplarken bu marjı ayıklar.{devig}" },
  { k: "brier", re: "brier", q: "brier skoru ne demek", kw: /0'a/i,
    html: "<b>Brier skoru</b>: olasılık tahminlerinin isabet ölçüsü; 0'a ne kadar yakınsa o kadar iyi. Koruyucu bot, otomatik bir değişiklikten sonra Brier skoru belirgin kötüleşirse (+0,01) değişikliği 14 gün geri alır." },
  { k: "mbs", re: "\\bmbs\\b|minimum bahis", q: "mbs ne demek", kw: /minimum (bahis|seçim) sayısı/i,
    html: "<b>MBS</b> (minimum seçim sayısı): iddaa'da bir maçın en az kaç maçla birlikte oynanabileceği. OXXai bir şans oyunu aracı olmadığı için MBS göstermez; yalnız tutma olasılığını gösterir." },
  { k: "powernow", re: "power ?now", q: "power now nedir", kw: /canlı/i, kw2: /%\s?80/,
    html: "<b>Power Now</b>: canlı maçlarda tutma olasılığı %80 ve üstü olan anlık seçimlerin ekranı (alt menü). Canlı oranlar saniyeler içinde değişir; seçimler maç içinde kilitlenip sonradan puanlanır." },
  { k: "favori", re: "\\bfavori\\w*", q: "favori ne demek", kw: /olasılığı en yüksek/i,
    html: "<b>Favori</b>: kazanma olasılığı en yüksek görülen taraf. Favori olmak kazanmak demek değildir: %60 favori, 10 benzer maçın yaklaşık 4'ünü kazanamaz." },
  { k: "surpriz", re: "\\bsurpriz\\w*", q: "sürpriz sonuç ne demek", kw: /olasılığı düşük/i,
    html: "<b>Sürpriz</b>: olasılığı düşük görülen sonucun gerçekleşmesi (ör. %20 görülen deplasman galibiyeti). Futbolda sık olur; bu yüzden tek maçta \"kesin\" yoktur." },
  { k: "evsahibi", re: "ev sahibi avantaj|saha avantaj|ic saha", q: "ev sahibi avantajı ne demek", kw: /kendi sahasında/i,
    html: "<b>Ev sahibi avantajı</b>: kendi sahasında oynayan takımın istatistiksel üstünlüğü. OXXai modeli bunu iç/dış saha gücü olarak hesaba katar." },
  { k: "deplasman", re: "\\bdeplasman\\w*", q: "deplasman ne demek", kw: /konuk|rakip sahada/i,
    html: "<b>Deplasman</b>: rakip sahada oynayan (konuk) takım; maç adında ikinci yazılan takımdır. <b>MS 2</b> deplasman galibiyeti demektir." },
  { k: "beraberlik", re: "\\bberaber\\w*", q: "beraberlik ne demek", kw: /eşit/i,
    html: "<b>Beraberlik (MS X)</b>: maçın normal süre sonunda eşitlikle bitmesi (0-0, 1-1…). Dengeli maçlarda beraberlik olasılığı %30'u bulabilir." },
  { k: "kilitli", re: "kilitli|kilitlen\\w*", q: "kilitli tahmin ne demek", kw: /maç başlamadan/i,
    html: "<b>Kilitli tahmin</b>: maç başlamadan arşive yazılan ve sonradan değiştirilemeyen öneri. Karnedeki tüm isabet rakamları bu kilitli kayıtlardan hesaplanır.{karne}" },
  { k: "korner", re: "\\bkorner\\w*|\\bkorner\\b", q: "korner tahmini var mı ne demek", kw: /korner/i,
    html: "<b>Korner</b> (köşe vuruşu) sayısı üzerine pazarlar vardır ama OXXai korner tahmini üretmez; uydurmamak için bu pazarı önermem. Gol, MS, KG ve İY olasılıklarını sorabilirsin." },
];

// ---- Yazım hatası adayları: [doğru kelime, test kalıbı, kategori, ölçüt] ----
const yazimKelime = [
  ["pazartesi", "{w} maçları", "tarih", { day: ["Pzt"] }],
  ["carsamba", "{w} maçları", "tarih", { day: ["Çar"] }],
  ["persembe", "{w} maçları", "tarih", { day: ["Per"] }],
  ["cumartesi", "{w} maçları", "tarih", { day: ["Cmt"] }],
  ["guvenli", "en {w} maçlar", "guvenli", {}],
  ["kupon", "2 maçlık {w} yap", "liste", { n: 2 }],
];

// ---- Büyük takım listesi (öne çıkan maç seçimi için; uygulamanın kendi takım listesinden bağımsız küçük bir çekirdek) ----
const buyuk = ["Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor", "Başakşehir", "Arsenal", "Chelsea", "Liverpool", "Manchester City", "Manchester United", "Tottenham",
  "Real Madrid", "Barcelona", "Atlético Madrid", "Juventus", "Inter", "Milan", "Napoli", "Roma", "Bayern", "Dortmund", "Leverkusen", "Paris Saint", "Marseille", "Ajax", "PSV", "Feyenoord",
  "Benfica", "FC Porto", "Sporting CP"];

module.exports = { para, esanlam, esanlamIfade, sozluk, yazimKelime, buyuk };
