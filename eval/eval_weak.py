# -*- coding: utf-8 -*-
"""弱模板：只用主体问「多少合适」，不给指标词 —— 逼检索自己判断问的是哪个指标。"""
import sys, re, json
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.server import search

items = json.load(open(r"D:\project\fitloop-kb\eval\gold_30.json", encoding="utf-8"))

def n(t): return re.sub(r"\s+", "", re.sub(r"[～〜~—–\-]", "~", str(t)))

def weak(it):
    s = re.sub(r"（[^）]*）", "", it["subject"])
    if any(k in s for k in ("活动", "运动", "步")):
        return f"{s}到什么程度合适"
    return f"{s}吃多少合适"

def check(q, it):
    for h in search(q, k=5).get("results", []):
        if h["chunk_id"] == it["chunk_id"]:
            return True
        if n(it["value"]) in n(h["text"]):
            return True
    return False

hit = 0
for it in items:
    hit += check(weak(it), it)
print(f"弱模板（只给主体）  {hit}/{len(items)}")
print("样例:", weak(items[0]), "|", weak(items[3]))
