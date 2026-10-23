# -*- coding: utf-8 -*-
"""查询改写：把口语问句翻成指南用词。

设计约束（故意这么做）：
1. 无状态：不读对话、不写对话，输入只有这一句
2. 只在别名匹配失败时调用，不是每次都调
3. 输出必须能校验：返回的词会拿去和事实表比对，命中不了就丢
4. 失败就返回空列表，调用方回落原来的检索——不影响可用性
"""
import os, json, httpx

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS = """把用户的口语问题翻译成《中国居民膳食指南》里会用的说法。
只输出 JSON：{"terms":["书面用词1","书面用词2"]}
要求：
- 只给名词或名词短语，2~4 个，不要句子
- 想的是"书里会怎么写"，不是同义词大全
- 例如「一周得动弹多久」→ ["身体活动","运动"]
- 例如「一天喝几杯水」→ ["饮水","饮水量"]
- 想不出来就返回 {"terms":[]}
"""


def _key():
    cfg = {}
    for p in (os.path.join(HERE, "..", "fitloop", ".env"), os.path.join(HERE, "..", ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    cfg.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    key = os.environ.get("FITLOOP_API_KEY") or cfg.get("FITLOOP_API_KEY") or cfg.get("OPENAI_API_KEY")
    base = os.environ.get("FITLOOP_BASE_URL") or cfg.get("FITLOOP_BASE_URL") or "https://api.deepseek.com"
    return key, base


def terms(query, timeout=8.0):
    """单次、无状态。任何异常都返回 []，绝不打断检索。"""
    key, base = _key()
    if not key:
        return []
    try:
        r = httpx.post(base.rstrip("/") + "/chat/completions",
                       headers={"Authorization": "Bearer " + key},
                       json={"model": "deepseek-chat", "temperature": 0,
                             "response_format": {"type": "json_object"},
                             "messages": [{"role": "system", "content": SYS},
                                          {"role": "user", "content": query}]},
                       timeout=timeout)
        data = json.loads(r.json()["choices"][0]["message"]["content"])
        return [str(t).strip() for t in (data.get("terms") or []) if str(t).strip()]
    except Exception:
        return []


if __name__ == "__main__":
    for q in ["一周得动弹多久", "一天喝几杯水", "坚果能抓一把吗", "每天奶类摄入多少"]:
        print(f"{q} → {terms(q)}")
