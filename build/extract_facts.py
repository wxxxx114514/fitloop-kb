# -*- coding: utf-8 -*-
"""试点：让模型把块抽成结构化条目，并**用原文校验**——值必须在原文里找得到，否则丢弃。
这是"标注即证据"用在机器标注上。"""
import sys, re, json, os
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import load
sys.path.insert(0, r"D:\project\fitloop")
import app
client = app._client()

SYS = """你从《中国居民膳食指南》的原文里抽取"摄入量"类事实。
只输出 JSON：{"facts":[{"subject":"主体","alias":["口语别名"],"metric":"指标","value":"数值","unit":"单位","quote":"原文片段"}]}
要求：
1. value 必须能在原文里逐字找到（含数字和符号）
2. alias 填普通人会说的口语词，比如"蔬菜"→["菜","青菜"]
3. 原文没有具体数值的，不要编，返回空数组
4. 不要抽取"患病率/消费量调查"这类背景数据，只抽"推荐摄入量"
"""

rows = load()
# 挑含关键数值的块
picked = []
for r in rows:
    t = r["text"]
    if re.search(r"\d+\s*[~\-]\s*\d+\s*g", t) and any(k in t for k in ("推荐", "不少于", "摄入")):
        picked.append(r)
    if len(picked) >= 12:
        break
print("试点块数:", len(picked), "\n")

facts, dropped = [], []
for r in picked:
    msgs = [{"role": "system", "content": SYS},
            {"role": "user", "content": "原文：\n" + r["text"][:900]}]
    d = app._json_msgs(msgs, max_tokens=600)
    for f in (d.get("facts") or []):
        v = str(f.get("value") or "").strip()
        ok = bool(v) and v.replace(" ", "") in re.sub(r"\s+", "", r["text"])
        if ok:
            f["page"] = r["page"]
            facts.append(f)
        else:
            dropped.append((r["page"], v, f.get("subject")))

print(f"抽出 {len(facts)} 条，原文校验不通过丢弃 {len(dropped)} 条\n")
for f in facts[:12]:
    print(f"  {f.get('subject')} | {f.get('metric')} | {f.get('value')} {f.get('unit')} | p{f['page']} | 别名 {f.get('alias')}")
print("\n被丢弃的（值在原文里找不到 = 模型编的）:")
for p, v, s in dropped[:5]:
    print(f"  p{p} {s} → 「{v}」")
json.dump(facts, open(r"D:\project\fitloop-kb\corpus\facts_pilot.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)