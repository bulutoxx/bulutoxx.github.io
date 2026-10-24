"""Açık kaynak dil modellerinin Türkçe niyet anlama sınaması (GitHub Actions, CPU).
Uygulamadaki 'Akıllı mod' için hangi modelin seçileceğini ölçer; ayrıca MLC (WebLLM) indirme boyutlarını toplar."""
import json, time, os, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, "nlu_test.json"), encoding="utf-8"))
SYS = open(os.path.join(HERE, "brain_prompt.txt"), encoding="utf-8").read()
out = {"modeller": {}, "boyut": {}}

def mlc_size(mid):
    try:
        j = json.load(urllib.request.urlopen(f"https://huggingface.co/mlc-ai/{mid}/resolve/main/tensor-cache.json", timeout=60))
    except Exception:
        try: j = json.load(urllib.request.urlopen(f"https://huggingface.co/mlc-ai/{mid}/resolve/main/ndarray-cache.json", timeout=60))
        except Exception as e: return str(e)
    return round(sum(r.get("nbytes", 0) for r in j.get("records", [])) / 1e6, 1)

for mid in ["Qwen3.5-0.8B-q4f16_1-MLC", "Qwen3.5-0.8B-q4f32_1-MLC", "Qwen3.5-2B-q4f16_1-MLC", "Qwen3-1.7B-q4f16_1-MLC", "gemma3-1b-it-q4f16_1-MLC", "Llama-3.2-1B-Instruct-q4f16_1-MLC"]:
    out["boyut"][mid] = mlc_size(mid); print(mid, out["boyut"][mid], flush=True)
json.dump(out, open(os.path.join(HERE, "brain_probe.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
torch.set_num_threads(4)
for name in sys.argv[1:]:
    try:
        tok = AutoTokenizer.from_pretrained(name); mdl = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float32); mdl.eval()
    except Exception as e:
        out["modeller"][name] = {"hata": str(e)[:300]}; print(name, e, flush=True); continue
    res = []; t0 = time.time()
    for x in T:
        msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": x["q"]}]
        try: ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", enable_thinking=False)
        except TypeError: ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt")
        if not torch.is_tensor(ids): ids = ids["input_ids"]
        t1 = time.time()
        with torch.no_grad(): g = mdl.generate(ids, max_new_tokens=110, do_sample=False)
        txt = tok.decode(g[0, ids.shape[1]:], skip_special_tokens=True).strip()
        try:
            s = txt[txt.index("{"): txt.rindex("}") + 1]; j = json.loads(s)
        except Exception: j = {}
        ok = j.get("niyet") == x["niyet"]
        res.append({"q": x["q"], "beklenen": x["niyet"], "cikti": txt[:220], "ok": ok, "sn": round(time.time() - t1, 1)})
        print(name, ok, x["q"], "→", txt[:160].replace("\n", " "), flush=True)
        out["modeller"][name] = {"isabet": round(sum(r["ok"] for r in res) / len(res), 3), "n": len(res), "sure": round(time.time() - t0), "sonuclar": res}
        json.dump(out, open(os.path.join(HERE, "brain_probe.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    out["modeller"][name] = {"isabet": round(sum(r["ok"] for r in res) / len(res), 3), "sure": round(time.time() - t0), "sonuclar": res}
    json.dump(out, open(os.path.join(HERE, "brain_probe.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(out, open(os.path.join(HERE, "brain_probe.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
