# -*- coding: utf-8 -*-
"""生成带证据的用例表：每条从真实块里逐字抓片段，记 chunk_id + page。
人只判 expect，不许凭记忆写答案。"""
import sys, re, json, os
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import load

ROOT = r"D:\project\fitloop-kb"
rows = load()

def n(t): return re.sub(r"\s+", "", t)

# (类别, 题, 页, 定位标记, 期望, 是否优先表格块)
RAW = [
    ("A", "每天奶类摄入多少", 11,  "烟熏和腌制肉类", False, False),
    ("A", "每天奶类摄入多少", 72,  "奶制品",         True,  True),
    ("A", "每天奶类摄入多少", 90,  "相当于每周吃鱼", False, False),
    ("A", "每天奶类摄入多少", 91,  "鱼、禽、蛋类",    False, False),
    ("A", "成年人每天应该吃多少蔬菜", 11, "烟熏和腌制肉类", False, False),
    ("A", "成年人每天应该吃多少蔬菜", 72, "不少于300g",    True,  True),
    ("A", "每天应该喝多少水", 11,  "烟熏和腌制肉类", False, False),
    ("A", "每天应该喝多少水", 138, "适宜摄入量",     True,  False),
    ("A", "每天奶类摄入多少", 70,  "液态奶",         True,  False),
    ("A", "每天奶类摄入多少", 138, "适宜摄入量",     False, False),

    ("B", "每天吃盐不超过多少", 11, "食盐不超过", True,  False),
    ("B", "每天烹调油吃多少", 11, "烹调油25",     True,  False),
    ("B", "每天大豆及坚果吃多少", 72, "大豆制品",   True,  True),
    ("B", "全谷物和杂豆每天吃多少", 72, "全谷物",   True,  True),
    ("B", "每天应该吃多少种食物", 72, "蔬菜|水果",  False, False),
    ("B", "每天大豆及坚果吃多少", 11, "烟熏和腌制肉类", False, False),
    ("B", "每天烹调油吃多少", 63, "蔬菜",         False, False),
    ("B", "每天吃盐不超过多少", 109, "少盐少油",   True,  False),
    ("B", "全谷物和杂豆每天吃多少", 63, "全谷物",   True,  False),
    ("B", "每天应该吃多少种食物", 10, "12种以上",  True,  False),

    ("C", "每天吃盐不超过多少", 11,  "食盐不超过",   True,  False),
    ("C", "每天吃盐不超过多少", 109, "少盐少油",     True,  False),
    ("C", "每天烹调油吃多少", 109, "烹调油摄入量", True,  False),
    ("C", "全谷物和杂豆每天吃多少", 61, "少吃1~2口", False, False),
    ("C", "每天奶类摄入多少", 29, "避免营养缺乏",   False, False),
    ("C", "每天大豆及坚果吃多少", 46, "食不过量",    False, False),
    ("C", "每天应该喝多少水", 148, "增加饮水量",     False, False),
    ("C", "成年人每周应该运动多少分钟", 43, "运动",   True,  False),
    ("C", "每天烹调油吃多少", 11, "避免过多动物性油脂", True, False),
    ("C", "每天吃盐不超过多少", 46, "食不过量",      False, False),
]

out = []
for cat, q, page, marker, expect, prefer_table in RAW:
    hits = [r for r in rows if r["page"] == page and marker in n(r["text"])]
    if not hits:
        out.append({"cat": cat, "q": q, "page": page, "marker": marker,
                    "expect": expect, "chunk_id": None, "snippet": None,
                    "note": "块未找到"}); continue
    if prefer_table:
        t = [r for r in hits if r["kind"] == "table"]
        hits = t or hits
    r0 = hits[0]
    text = n(r0["text"])
    out.append({"cat": cat, "q": q, "page": page, "marker": marker, "expect": expect,
                "chunk_id": r0["id"], "kind": r0["kind"], "snippet": text[:200]})

json.dump(out, open(os.path.join(ROOT, "eval", "cases_30.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("生成", len(out), "条，带 chunk_id 的:", sum(1 for o in out if o["chunk_id"]))
for o in out:
    if not o["chunk_id"]:
        print("  缺块:", o["q"], o["page"], o["marker"])
