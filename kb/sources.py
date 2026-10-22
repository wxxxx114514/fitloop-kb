# -*- coding: utf-8 -*-
"""语料来源的元数据：供引用显示用。新增来源在这里登记一行即可。"""

SOURCES = {
    "cns-book-2022": {
        "title": "中国居民膳食指南（2022）",
        "org": "中国营养学会",
        "year": 2022,
        "edition": "人民卫生出版社",
    },
}


def title_of(source_id):
    return SOURCES.get(source_id, {}).get("title") or source_id
