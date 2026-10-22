# -*- coding: utf-8 -*-
"""用 cases_30.json 里的证据（逐字片段）判分，对照人标的 expect。"""
import sys, json, os
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.path.insert(0, r"D:\project\fitloop-kb\eval")
sys.stdout.reconfigure(encoding="utf-8")
from score import new_hit, load_gold

ROOT = r"D:\project\fitloop-kb"
cases = json.load(open(os.path.join(ROOT, "eval", "cases_30.json"), encoding="utf-8"))
gold = {g["q"]: g for g in load_gold()}

ok = 0
bad = []
for c in cases:
    got = new_hit(c["snippet"], gold[c["q"]])
    if got == c["expect"]:
        ok += 1
    else:
        bad.append((c, got))
print(f"判分器 vs 标注：{ok}/{len(cases)} 一致\n")
for c, got in bad:
    print(f"[{c['cat']}] {c['q']}  p{c['page']} {c['chunk_id']}")
    print(f"   标注 {c['expect']} / 判分 {got}")
    print(f"   证据: {c['snippet'][:110]}")
    print()
