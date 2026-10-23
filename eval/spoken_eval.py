# -*- coding: utf-8 -*-
"""口语版问句：同一批答案，换成人话问法，看召回掉多少。"""
import sys, re, json
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.path.insert(0, r"D:\project\fitloop-kb\eval")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import BM25, load
from kb.query import expand
from kb.rerank import Reranker
from score import new_hit

rows = load(); bm = BM25(rows); rr = Reranker()
gold = json.load(open(r"D:\project\fitloop-kb\eval\gold_9.json", encoding="utf-8"))

# 书面问句 → 口语问法
SPOKEN = {
    "成年人每天应该吃多少蔬菜": "一天得吃多少菜啊",
    "每天吃盐不超过多少": "盐一天别超多少",
    "每天烹调油吃多少": "炒菜放多少油合适",
    "每天应该吃多少种食物": "每天吃的种类要几种",
    "全谷物和杂豆每天吃多少": "粗粮杂豆吃多少",
    "每天应该喝多少水": "一天喝几杯水",
    "每天奶类摄入多少": "牛奶酸奶一天喝多少",
    "每天大豆及坚果吃多少": "坚果能抓一把吗",
    "成年人每周应该运动多少分钟": "一周得动弹多久",
}

def run(use_spoken):
    hit = 0
    detail = []
    for g in gold:
        q = SPOKEN[g["q"]] if use_spoken else g["q"]
        cand = [i for _, i in bm.score(expand(q))[:30]]
        if cand:
            sc = rr.scores(expand(q), [rows[i]["text"] for i in cand])
            top = [cand[k] for k in sorted(range(len(cand)), key=lambda k: -sc[k])][:5]
        else:
            top = []
        ok = any(new_hit(rows[i]["text"], g) for i in top)
        hit += ok
        detail.append((q, ok))
    return hit, detail

h1, _ = run(False)
h2, d2 = run(True)
print(f"书面问法  {h1}/9")
print(f"口语问法  {h2}/9\n")
for q, ok in d2:
    print(f"  {'✓' if ok else '✗'}  {q}")
