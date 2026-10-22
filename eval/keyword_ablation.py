# -*- coding: utf-8 -*-
"""四档对比：裸BM25 / 数字加权 / 查询扩展 / 两者叠加"""
import sys, os, re, json
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import BM25, load

ROOT = r"D:\project\fitloop-kb"
ANSWERS = {
    "成年人每天应该吃多少蔬菜": "300~500g",
    "每天吃盐不超过多少": "5g",
    "每天烹调油吃多少": "25~30g",
    "每天应该吃多少种食物": "12种以上",
    "全谷物和杂豆每天吃多少": "50~150g",
    "每天应该喝多少水": "1500~1700ml",
    "每天奶类摄入多少": "300~500g",
    "每天大豆及坚果吃多少": "25~35g",
    "成年人每周应该运动多少分钟": "150~300",
}

NUM_RE = re.compile(r"\d+\s*[~\-]?\s*\d*\s*(g|ml|克|毫升|kcal|千卡|分钟|小时)", re.I)


def norm(t):
    return re.sub(r"\s+", "", re.sub(r"[～〜~—–\-]", "~", t))


rows = load()
bm = BM25(rows)
gold = [json.loads(l) for l in open(os.path.join(ROOT, "eval", "gold_10.jsonl"), encoding="utf-8")]
has_num = [bool(NUM_RE.search(r["text"])) for r in rows]

def top5(q, num_bonus=False, expand=False):
    qq = q + " 推荐量 摄入量 多少" if expand else q
    sc = bm.score(qq)
    if num_bonus:
        sc = [(s * (1.25 if has_num[i] else 1.0), i) for s, i in sc]
        sc.sort(reverse=True)
    return [i for _, i in sc[:5]]

variants = {
    "A 裸 BM25": dict(),
    "B 数字加权": dict(num_bonus=True),
    "C 查询扩展": dict(expand=True),
    "D 两者叠加": dict(num_bonus=True, expand=True),
}

for name, kw in variants.items():
    hit = 0
    miss = []
    for g in gold:
        ans = ANSWERS.get(g["q"])
        if not ans:
            continue
        tops = top5(g["q"], **kw)
        if any(norm(ans) in norm(rows[i]["text"]) for i in tops):
            hit += 1
        else:
            miss.append(g["q"][:10])
    print(f"{name:<12}{hit}/9 = {hit/9:.2f}   漏: {miss}")
