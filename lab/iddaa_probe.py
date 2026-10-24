import json, sys, collections
sys.path.insert(0, "lab"); import iddaa as I
out = {}
for sp in (1, 2):
    ev = I._get(f"events?st={sp}&type=0&version=0")["events"]
    # basketbol: ilk 3 maçın tüm sov'lu pazarları (st, sov, oranlar)
    if sp == 2:
        out["bk_markets"] = [{"h": e["hn"], "a": e["an"], "m": [(m.get("st"), m.get("t"), m.get("sov"), {o.get("n"): o.get("odd") for o in m.get("o", [])}) for m in e.get("m", [])]} for e in ev[:4]]
    st = collections.Counter(m.get("st") for e in ev for m in e.get("m", []))
    out[f"st_{sp}"] = st.most_common(40)
    p = I.fetch(sp)
    out[f"parsed_{sp}"] = {"n": len(p), "ornek": p[:12], "comps": collections.Counter(x["comp"] for x in p).most_common(200),
                           "cc": collections.Counter(x["cc"] for x in p).most_common(60), "no_ou": sum(1 for x in p if "ou" not in x["mk"] and "tot" not in x["mk"])}
json.dump(out, open("lab/iddaa_probe.json", "w"), ensure_ascii=False, indent=1)
