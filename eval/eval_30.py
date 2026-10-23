# -*- coding: utf-8 -*-
"""30 题评测：书面 + 口语各跑一遍，失败分两类（检索问题 / 事实问题）。"""
import sys, re, json
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.server import search

items = json.load(open(r"D:\project\fitloop-kb\eval\gold_30.json", encoding="utf-8"))

def n(t): return re.sub(r"\s+", "", re.sub(r"[～〜~—–\-]", "~", str(t)))

def check(q, it):
    r = search(q, k=5)
    hits = r.get("results", [])
    for h in hits:
        if h["chunk_id"] == it["chunk_id"]:
            return True, h.get("via"), h["text"]
    v = n(it["value"])
    for h in hits:
        if v and v in n(h["text"]):
            return True, h.get("via"), h["text"]
    return False, None, (hits[0]["text"] if hits else "")

wb = sk = 0
misses = []
for it in items:
    a, va, ta = check(it["q"], it)
    b, vb, tb = check(it["spoken"], it)
    wb += a; sk += b
    if not a:
        misses.append(("书面", it, ta))

print(f"书面 {wb}/{len(items)}    口语 {sk}/{len(items)}\n")
print("书面失败的题（看是检索问题还是事实问题）:")
for kind, it, got in misses[:12]:
    print(f"  问：{it['q']}")
    print(f"    期望：{it['value']}{it['unit']} (p{it['page']})")
    print(f"    实际首位：{got[:60]}")
