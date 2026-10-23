# -*- coding: utf-8 -*-
"""从 455 条事实里随机抽 30 条造题：书面问法按模板，口语问法交给模型改写。
随机抽样是为了避免"我专挑自己会答的题"。"""
import sys, re, json, random, sqlite3
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.path.insert(0, r"D:\project\fitloop")
sys.stdout.reconfigure(encoding="utf-8")
import app

DB = r"D:\project\fitloop-kb\kb.db"
OUT = r"D:\project\fitloop-kb\eval\gold_30.json"

con = sqlite3.connect(DB)
rows = con.execute("SELECT chunk_id,page,subject,metric,value,unit,alias FROM facts").fetchall()
con.close()

def canon(s):
    return re.sub(r"（[^）]*）|\([^)]*\)", "", s).replace("类", "").strip()

# 每个主体只留一条，且值里必须有数字
seen, pool = set(), []
for cid, page, subj, metric, val, unit, alias in rows:
    c = canon(subj)
    if not any(ch.isdigit() for ch in str(val)) or len(c) < 2 or c in seen:
        continue
    seen.add(c)
    pool.append({"chunk_id": cid, "page": page, "subject": subj, "metric": metric,
                 "value": val, "unit": unit or "",
                 "alias": json.loads(alias) if alias else []})

random.seed(20261023)
picked = random.sample(pool, min(30, len(pool)))
print("候选主体:", len(pool), "| 抽中:", len(picked))

# 书面问法：模板
for p in picked:
    m = p["metric"] or "推荐量"
    p["q"] = f"{p['subject']}的{m}是多少"

# 口语问法：交给模型，一次 6 条
SYS = """把下面每条"书面问句"改写成普通人会说的口语问法。
只输出 JSON：{"items":[{"i":0,"spoken":"..."}]}
要求：用生活化说法（比如"蔬菜的每天摄入量是多少" → "一天吃多少菜合适"），不要改变问的是同一件事。
"""
for i in range(0, len(picked), 6):
    batch = picked[i:i+6]
    lines = "\n".join(f'{j}. {b["q"]}' for j, b in enumerate(batch))
    d = app._json_msgs([{"role": "system", "content": SYS},
                        {"role": "user", "content": lines}], max_tokens=600)
    for it in (d.get("items") or []):
        j = it.get("i")
        if isinstance(j, int) and 0 <= j < len(batch):
            batch[j]["spoken"] = it.get("spoken") or batch[j]["q"]
    for b in batch:
        b.setdefault("spoken", b["q"])

for p in picked:
    p["subject_terms"] = [p["subject"]] + p["alias"]
    p["values"] = [p["value"]] + ([p["value"] + p["unit"]] if p["unit"] else [])

json.dump(picked, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("写入", OUT)
for p in picked[:6]:
    print(f"  书面 {p['q']}")
    print(f"  口语 {p['spoken']}")
    print(f"  答案 {p['value']}{p['unit']} p{p['page']}\n")
