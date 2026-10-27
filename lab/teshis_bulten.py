"""Elle teşhis: iddaa bülteninde Türkiye Kupası / belirli takım var mı (yalnız ad ve pazar türleri yazılır, oran yazılmaz)."""
import sys, collections; sys.path.insert(0, "scripts")
import iddaa as ID
comps = {c["i"]: c for c in (ID._get("competitions") or [])}
for st in (1,):
    ev = (ID._get(f"events?st={st}&type=0&version=0") or {}).get("events") or []
    print("toplam olay:", len(ev))
    for c in comps.values():
        if "Türkiye" in (c.get("n") or "") or "Turkiye" in (c.get("n") or ""): print("yarışma:", c.get("i"), c.get("n"), c.get("cid"))
    for e in ev:
        ad = (e.get("hn") or "") + " " + (e.get("an") or "")
        cn = comps.get(e.get("ci"), {}).get("n", "")
        if any(k in ad for k in ("Kocaeli", "Fosfat")) or "Türkiye Kupas" in cn:
            print("olay:", e.get("i"), e.get("ci"), cn, "|", ad, "| d", e.get("d"), "| pazarlar", sorted({(m.get("st"), str(m.get("sov"))) for m in e.get("m") or []})[:15])
print("--- fetch(1) süzgeci")
out = ID.fetch(1)
for e in ev:
    ad = (e.get("hn") or "") + " " + (e.get("an") or "")
    if "Kocaeli" in ad or "Bingöl" in ad:
        for m in e.get("m") or []:
            if m.get("st") == 1:
                o = ID._mk(m); print("MS seçenek adları:", sorted(o), "hepsi>1.01:", all(o.get(k, 0) > 1.01 for k in ("1", "0", "2")), "ham o:", [(x.get("n"), x.get("odd") is not None) for x in (m.get("o") or [])])
        print("fetch çıktısında:", any(x["iid"] == e.get("i") for x in out))
