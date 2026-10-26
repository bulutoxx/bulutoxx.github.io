# 🐎 OXXai At Yarışı Uzman Ekibi — Görev Dağılımı (üst düzey prompt)

Bu dosya, at yarışı laboratuvarındaki robot ve ajanların rollerini, veri sınırlarını ve "bitti" ölçütlerini tanımlar.
Ana kurallar `GOREV.md`'dedir (tjk.org'a istek yok, ham veri yayınlanmaz, sıfır maliyet, her değişiklik sınamadan geçer).

## Roller
| Uzman | Sorumluluk | Çıktı |
|---|---|---|
| 📊 Baş istatistikçi (gece.py) | Günlük yeniden eğitim, kapı, sabah kilidi | data/at/model.json, data/at/tahmin/ |
| ⏱️ Gün içi analist (canli.py) | 30 dk'da bir oranla harman, aynı akşam sonuç ve karne | data/at/canli/, data/at/karne.json |
| 🔁 Geriye dönük test uzmanı (replay.py) | Geçmiş günleri "hiç oynanmamış gibi" yeniden yarıştırma; Altın at kuralını ayrılmış dönemde seçme | data/at/replay.json, model.json → altin_kural |
| 🏇 Jokey ve ahır uzmanı (jokey.py) | Jokey/antrenör becerisi (atın gücünden arındırılmış), ikili uyum, jokey değişimi, form momentumu, iş yükü, uzmanlık (pist/mesafe/hipodrom) | data/at/jokeyler.json, yeni özellik grupları |
| ⚡ Hız ve sınıf uzmanı | Beyer tipi hız figürü, sınıf düzeyi, handikap puanı vekili | ozellik.py grupları |
| 🔬 Araştırmacı (arastirma.py) | Açık kaynak tarama: yeni veri setleri, idman/galop verisi, yöntemler; lisans kontrolü | data/at/arastirma.json |
| 🛡️ Denetçi | Sızıntı testi, kapı kararları, karne tutarlılığı | test_sizinti.py, RAPOR.md |

## Ortak ölçüt (kapı)
- Zaman sıralı çok katlı sınama; koşu başına log-loss ve ilk seçim isabeti.
- Kabul: ortalama log-loss düşer, ilk seçim düşmez, son kat kötüleşmez, harman 0,001'den fazla bozulmaz.
- Koşu-bootstrap %95 güven aralığı her deneyde raporlanır.

## Veri sınırları
- Kaynak: herkese açık TJK sonuç arşivi (github.com/cenkozgur/tjk-data).
- İdman/galop/sprint: lisanslı açık kaynak bulunana kadar kullanılmaz (araştırmacı her gün arar).
- Jokey ve antrenör adları kamuya açık spor bilgisidir; yalnız türetilmiş istatistikler yayınlanır.
