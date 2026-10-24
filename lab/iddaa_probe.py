import json, sys
sys.path.insert(0, "lab"); import iddaa as I
json.dump({"fb": I.fetch(1), "bk": I.fetch(2)}, open("lab/iddaa_probe.json", "w"), ensure_ascii=False)
