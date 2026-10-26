# 🎯 6'lı Ganyan Modülü — Görev Tanımı (üst düzey prompt)

## Amaç
Her hipodromun 6'lı ganyan(lar)ı için, OXXai olasılıklarıyla ayak ayak seçim yapan, "altı ayağın hepsini tutturma"
olasılığını dürüstçe hesaplayan ve geçmişte nasıl sonuç verdiğini gösteren modül. Hobi amaçlı; para tutarı, bahis
bağlantısı ve "kesin" ifadesi yok; yalnız olasılık ve kombinasyon sayısı.

## Araştırma bulguları (kurallar)
- 6'lı ganyan, programda "ganyan başlangıcı" işaretli koşudan (aynada `isGanyanStart: true`) başlayan ardışık 6 koşudur.
  10 koşulu günlerde genelde iki 6'lı vardır (1. ve 5. koşulardan başlar); kısa günlerde tek 6'lı.
- Bir ayakta birden çok at işaretlenebilir; kombinasyon sayısı = ayaklardaki seçim sayılarının çarpımı.
- Ekürili atlar aynı koşuda tek grup gibi sayılır (aynada `ekuriGroups`). Koşmayan atın yerine Altılı Ganyan
  Favorisi (AGF) sayılır; bunu modelde "koşmayan seçim → o ayağın favorisine kaydır" diye yaklaşıklarız.
- Kaynak: At Yarışları Müşterek Bahisler mevzuatı özeti (alomaliye.com). tjk.org'a istek atılmaz.

## Matematik
- Ayak olasılığı: seçilen atların kazanma olasılıklarının toplamı (ekürili gruplar birleştirilir).
- 6'lı olasılığı: ayak olasılıklarının çarpımı (koşular bağımsız varsayılır).
- Seçim: kombinasyon bütçesi altında toplam olasılığı en büyükleyen açgözlü algoritma — her adımda
  Δlog(P) / Δlog(kombinasyon) en büyük olan atı ekle. Bütçeler: Dar ≤ 24, Orta ≤ 96, Geniş ≤ 384 kombinasyon.
- "Altın banko": ayağın en güçlü atı Altın at kuralını geçiyorsa o ayak tek atla oynanabilir diye işaretlenir.
- Olasılık kaynağı: koşu öncesi oran varsa oranla harman (p_oran), yoksa sabah modeli (p_sabah).

## Geriye dönük test (zorunlu)
- `data/at/replay_kosular.json` üzerinden 2026-03-16'dan bugüne her geçmiş 6'lı için sabah olasılıklarıyla seçim yap,
  gerçek sonuçla puanla: her bütçe için isabet sayısı, beklenen (tahmin edilen) olasılık toplamı ve gerçekleşen
  isabet (kalibrasyon), ortalama kombinasyon, ayak başına isabet, "5 ayak tuttu" sayısı.
- Algoritma ayarları (bütçe kademeleri, banko eşiği) ilk 2/3 dönemde seçilir, son 1/3'te raporlanır.

## Çıktılar
- `data/at/altili/<gün>.json` (günlük, canlı robot oranla günceller), `data/at/altili_karne.json` (geriye dönük + canlı).
- Arayüz: At bölümünde "🎯 6'lı" sekmesi, OXXai cevapları, paylaşım.
