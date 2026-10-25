# BULUTOXX at yarışı laboratuvarı — araştırmacı.
# GitHub arama API'si ile yeni açık TJK veri kaynakları ve at yarışı modelleme depoları arar; adayları
# data/at/arastirma.json'a yazar. HİÇBİR kaynağa otomatik bağlanmaz (bağlantı ancak lisans/erişim uygun ve
# sınamada katkısı ölçülürse elle yapılır). tjk.org'a istek atmaz. GITHUB_TOKEN varsa (Actions) kullanır.
import json, os, time, urllib.parse, urllib.request
from datetime import datetime, timezone

KOK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CIKTI = os.environ.get("AT_ARASTIRMA_CIKTI") or os.path.join(KOK, "data", "at", "arastirma.json")
SORGULAR = [
    ("tjk veri", "tjk in:name,description,readme"),
    ("tjk veri", "jokey kulübü"),
    ("tjk veri", "\"at yarışı\""),
    ("türk at yarışı", "horse racing turkey"),
    ("modelleme", "horse racing prediction conditional logit"),
    ("modelleme", "horse racing benter model"),
    ("modelleme", "harville exacta probability"),
    # idman (workout) verisi: galop/sprint dereceleri. Aday yalnız kaydedilir; lisans + kaynak (tjk.org kazıması mı?)
    # elle incelenmeden ve sınamada katkısı ölçülmeden BAĞLANMAZ.
    ("idman verisi", "idman galop"),
    ("idman verisi", "tjk idman"),
    ("idman verisi", "\"tjk idman\""),
    ("idman verisi", "idman at yarışı"),
    ("idman verisi", "galop at"),
    ("idman verisi", "horse workout turkey"),
    ("idman verisi", "horse racing workout data"),
    ("idman verisi", "tjk in:name,description idman OR galop OR workout"),
]
IDMAN_KELIME = ("idman", "galop", "workout", "sprint", "breeze", "antrenman")
TJK_KELIME = ("tjk", "jokey", "türk", "turk", "turkey", "istanbul", "veliefendi", "at yar")
BILINEN = {"cenkozgur/tjk-data": "bağlı (ana ayna)"}


def ara(q, token):
    u = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": q, "sort": "updated", "order": "desc", "per_page": 15})
    h = {"Accept": "application/vnd.github+json", "User-Agent": "bulutoxx-at-arastirma"}
    if token:
        h["Authorization"] = "Bearer " + token
    with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=30) as r:
        return json.load(r).get("items", [])


def main():
    token = os.environ.get("GITHUB_TOKEN")
    try:
        eski = json.load(open(CIKTI, encoding="utf-8"))
    except Exception:
        eski = {"adaylar": []}
    aday = {a["ad"]: a for a in eski.get("adaylar", [])}
    hatalar, simdi = [], datetime.now(timezone.utc).isoformat(timespec="seconds")
    for tur, q in SORGULAR:
        try:
            for it in ara(q, token):
                ad = it.get("full_name")
                if not ad or it.get("fork"):
                    continue
                d = aday.get(ad, {"ilk_gorulme": simdi})
                metin = " ".join(str(it.get(x) or "") for x in ("full_name", "description")).lower()
                topic = " ".join(it.get("topics") or []).lower()
                idman_ilgi = any(k in metin or k in topic for k in IDMAN_KELIME)
                tjk_ilgi = any(k in metin or k in topic for k in TJK_KELIME)
                if tur == "idman verisi" and not (idman_ilgi or tjk_ilgi):
                    continue   # alakasız (ör. yalnız "galop" geçen oyun depoları)
                d.update({"ad": ad, "url": it.get("html_url"), "tur": (tur if tur != "idman verisi" else "idman verisi" if idman_ilgi else d.get("tur") or "tjk veri"),
                          "idman_ilgili": bool(idman_ilgi and tjk_ilgi),
                          "lisans": ((it.get("license") or {}).get("spdx_id") or "belirtilmemiş"),
                          "son_itme": it.get("pushed_at"), "yildiz": it.get("stargazers_count"),
                          "aciklama": (it.get("description") or "")[:200], "dil": it.get("language"),
                          "durum": BILINEN.get(ad, "aday — bağlanmadı (lisans/erişim/sınama değerlendirmesi bekliyor)"),
                          "son_gorulme": simdi})
                aday[ad] = d
        except Exception as e:
            hatalar.append({"sorgu": q, "hata": f"{type(e).__name__}: {str(e)[:120]}"})
        time.sleep(7 if not token else 2)  # arama API hız sınırına saygı
    ad_list = sorted(aday.values(), key=lambda a: (a.get("tur") != "tjk veri", -(a.get("yildiz") or 0)))
    idman = [a for a in ad_list if a.get("idman_ilgili")]
    out = {"guncelleme": simdi, "kural": "Adaylar otomatik bağlanmaz. Lisansı/erişimi uygun ve sınamada katkısı ölçülen kaynak elle eklenir.",
           "sorgular": [q for _, q in SORGULAR], "hatalar": hatalar, "aday_sayisi": len(ad_list),
           "idman": {"aday_sayisi": len(idman),
                     "lisansli": [a["ad"] for a in idman if a.get("lisans") not in (None, "belirtilmemiş", "NOASSERTION")],
                     "not": "idman_ilgili = ad/açıklamada hem idman/galop/workout hem TJK/Türkiye geçiyor. Hiçbiri otomatik "
                            "bağlanmaz; açık lisans + tjk.org'a robot isteği gerektirmeyen kaynak + sınamada ölçülmüş katkı şart."},
           "adaylar": ad_list[:150]}
    os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
    json.dump(out, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"araştırma: {len(ad_list)} aday ({len(idman)} idman ilgili), {len(hatalar)} hata")


if __name__ == "__main__":
    main()
