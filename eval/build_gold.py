# -*- coding: utf-8 -*-
"""造第一版 gold 集：先按答案关键词在语料里找页，再定"应命中页"。
找不到答案的，标成 not_in_corpus，用作拒答题。"""
import sys, re, json, os, sqlite3
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\project\fitloop-kb"
con = sqlite3.connect(os.path.join(ROOT, "kb.db"))
rows = con.execute("SELECT id, page, text FROM chunks").fetchall()
con.close()

SPECS = [
    ("成年人每天应该吃多少蔬菜", r"\d+\s*[~-]\s*\d+\s*g", "蔬菜"),
    ("每天吃盐不超过多少", r"不超过\s*\d\s*g|食盐不超过", "盐"),
    ("每天烹调油吃多少", r"\d+\s*[~-]\s*\d+\s*g", "油"),
    ("每天应该吃多少种食物", r"12\s*种以上|25\s*种以上", "食物种类"),
    ("全谷物和杂豆每天吃多少", r"\d+\s*[~-]\s*\d+\s*g", "全谷物"),
    ("每天应该喝多少水", r"\d+\s*[~-]\s*\d+\s*ml|毫升", "水"),
    ("每天奶类摄入多少", r"\d+\s*[~-]\s*\d+\s*g", "奶"),
    ("每天大豆及坚果吃多少", r"\d+\s*[~-]\s*\d+\s*g", "大豆"),
    ("成年人每周应该运动多少分钟", r"\d+\s*[~-]\s*\d+\s*分钟", "运动"),
    ("维生素D每天补多少国际单位", r"国际单位|IU", "维生素D"),
]

gold = []
for q, pat, kw in SPECS:
    cand = []
    for cid, page, text in rows:
        if re.search(pat, text) and kw in text:
            cand.append(page)
    cand = sorted(set(cand))
    item = {"q": q, "expect_pages": cand[:3], "type": "lookup" if cand else "refuse",
            "answer_pattern": pat}
    gold.append(item)
    flag = "OK  " if cand else "REFUSE"
    print(f"{flag} {q:<24} 页码 {cand[:5]}")

os.makedirs(os.path.join(ROOT, "eval"), exist_ok=True)
with open(os.path.join(ROOT, "eval", "gold_10.jsonl"), "w", encoding="utf-8") as f:
    for g in gold:
        f.write(json.dumps(g, ensure_ascii=False) + "\n")
print("\n写入 eval/gold_10.jsonl")
