# -*- coding: utf-8 -*-
"""用**上线同一个 search()** 跑 9 题 × 两种问法，避免评测和线上是两套代码。"""
import sys, re, json
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.path.insert(0, r"D:\project\fitloop-kb\eval")
sys.stdout.reconfigure(encoding="utf-8")
from kb.server import search
from score import new_hit

gold = json.load(open(r"D:\project\fitloop-kb\eval\gold_9.json", encoding="utf-8"))
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

def n(t): return re.sub(r"\s+", "", re.sub(r"[～〜~—–\-]", "~", str(t)))
def hit(q, g):
    r = search(q, k=5)
    for x in r.get("results", []):
        if new_hit(x["text"], g):
            return True, x.get("via")
    return False, None

print(f"{'题':<20}{'书面':>6}{'via':>9}{'口语':>6}{'via':>9}")
wb = sk = 0
for g in gold:
    a, va = hit(g["q"], g)
    b, vb = hit(SPOKEN[g["q"]], g)
    wb += a; sk += b
    print(f"{g['q'][:18]:<20}{'✓' if a else '✗':>6}{str(va):>9}{'✓' if b else '✗':>6}{str(vb):>9}")
print(f"\n书面 {wb}/9    口语 {sk}/9")
