# -*- coding: utf-8 -*-
"""独立题库：凭常识写 30 条真实问法（不看事实表），跑完人工判 top1 是否相关。"""
import sys, re
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.server import search

QS = [
    "一天得吃多少菜啊", "水果一天能吃多少", "牛奶一天喝多少合适", "鸡蛋一天几个",
    "盐一天别超多少", "炒菜放多少油", "糖一天最多多少", "米饭一顿吃多少",
    "主食一天吃多少", "粗粮吃多少", "坚果能抓一把吗", "豆浆一天喝多少",
    "肉一天吃多少", "鱼一周吃几次", "红肉吃多了好不好", "一周得动弹多久",
    "每天走多少步", "运动完要不要多喝水", "一天喝几杯水", "隔夜水能喝吗",
    "减脂期蛋白质吃多少", "减重一周掉多少斤算正常", "不吃晚饭能减肥吗",
    "空腹跑步行不行", "晚上几点后别吃东西", "喝咖啡有影响吗",
    "糖尿病能吃水果吗", "高血压一天吃多少盐", "孕妇补叶酸吗", "小孩吃多少肉",
]

def clean(t): return re.sub(r"\s+", "", t)

print(f"{'问':<18}{'via':<9}top1")
for q in QS:
    r = search(q, k=1)
    hits = r.get("results", [])
    if hits:
        h = hits[0]
        print(f"{q:<18}{str(h.get('via')):<9}p{h['page']} {clean(h['text'])[:40]}")
    else:
        print(f"{q:<18}{'-':<9}（无结果）")
