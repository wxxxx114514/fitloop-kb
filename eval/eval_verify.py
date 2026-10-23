# -*- coding: utf-8 -*-
"""加 verify 前后对比：只看"是否给出了不该给的答案"。"""
import sys, re
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.server import search

QS = [
    "隔夜水能喝吗", "运动完要不要多喝水", "不吃晚饭能减肥吗", "空腹跑步行不行",
    "孕妇补叶酸吗", "一周得动弹多久", "豆浆一天喝多少", "红肉吃多了好不好",
    "一天得吃多少菜啊", "盐一天别超多少", "每天走多少步", "晚上几点后别吃东西",
]

def clean(t): return re.sub(r"\s+", "", t)
for q in QS:
    a = search(q, k=2, verify_on=False).get("results", [])
    b = search(q, k=2, verify_on=True).get("results", [])
    fa = clean(a[0]["text"])[:30] if a else "—"
    fb = clean(b[0]["text"])[:30] if b else "（空）"
    mark = "改" if fa != fb else ""
    print(f"{q:<14} 筛前 {fa:<32} 筛后 {fb:<32} {mark}")
