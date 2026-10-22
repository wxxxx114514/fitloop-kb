# -*- coding: utf-8 -*-
"""查询扩展：把口语词映射到指南里的正式用词。
只用"文档确实换了个词"的情况，不堆同义词表。"""

# 口语 -> 指南用词。左边是用户会说的，右边是书上写的。
SYNONYMS = {
    "喝水": ["饮水", "饮水量"],
    "水": ["饮水"],
    "吃盐": ["食盐"],
    "盐": ["食盐"],
    "油": ["烹调油"],
    "吃肉": ["畜禽鱼蛋", "动物性食物"],
    "吃饭": ["进餐"],
    "零食": ["加餐"],
    "蔬菜水果": ["蔬果"],
    "主食": ["谷类", "薯类"],
    "减重": ["减脂", "体重管理"],
}

def expand(query):
    """返回扩展后的查询串（原句 + 命中的正式用词）。"""
    extra = []
    for k, vs in SYNONYMS.items():
        if k in query:
            extra.extend(vs)
    if not extra:
        return query
    seen, uniq = set(), []
    for w in extra:
        if w not in seen:
            seen.add(w); uniq.append(w)
    return query + " " + " ".join(uniq)
