# -*- coding: utf-8 -*-
"""坐标框 → 版面块 → chunks 入库。
块比之前小（目标 260 字），表格单独成块（Markdown），图表只剩图注。"""
import sys, os, re, json, sqlite3
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.path.insert(0, r"D:\project\fitloop-kb\build")
sys.stdout.reconfigure(encoding="utf-8")
from layout import parse_page

ROOT = r"D:\project\fitloop-kb"
BOXES = os.path.join(ROOT, "corpus", "boxes")
DB = os.path.join(ROOT, "kb.db")
TARGET = 260

def clean_table(md):
    """Markdown 表格里的空列和分隔符对 bigram 是噪声，压缩掉。"""
    rows = []
    for line in md.splitlines():
        if set(line.replace("|", "").strip()) <= {"-", "~"}:
            continue                      # 分隔行整行丢掉
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        cells = [c for c in cells if c and c not in ("~~~", "~~")]
        if cells:
            rows.append(" | ".join(cells))
    return "。".join(rows)

def pack(blocks):
    """同一栏里连续的 text 块拼成 ~TARGET 字的 chunk；table 独立成块。"""
    out = []
    for b in blocks:
        if b["type"] == "table":
            t = clean_table(b["text"])
            if t:
                out.append(("table", t))
            continue
        if b["type"] == "figure":
            out.append(("figure", b["text"]))
            continue
        txt = b["text"].strip()
        if not txt:
            continue
        if out and out[-1][0] == "text" and len(out[-1][1]) + len(txt) <= TARGET:
            out[-1] = ("text", out[-1][1] + txt)
        else:
            out.append(("text", txt))
    return out

def main():
    files = sorted(f for f in os.listdir(BOXES) if f.endswith(".json"))
    if not files:
        print("没有坐标框文件"); return
    con = sqlite3.connect(DB)
    con.execute("DROP TABLE IF EXISTS chunks")
    con.execute("""CREATE TABLE chunks(
        id TEXT PRIMARY KEY, source TEXT, page INT, ord INT, text TEXT, chars INT,
        kind TEXT, is_tip INT DEFAULT 0)""")
    rows, skipped = [], 0
    for fn in files:
        page = int(re.search(r"p(\d+)", fn).group(1))
        blocks = parse_page(json.load(open(os.path.join(BOXES, fn), encoding="utf-8")))
        packs = pack(blocks)
        if not packs:
            skipped += 1; continue
        for i, (kind, txt) in enumerate(packs):
            tip = 1 if ("小贴士" in txt or "贴士：" in txt) else 0
            rows.append((f"cns-book-2022#p{page:03d}-{i}", "cns-book-2022", page, i,
                         txt, len(txt), kind, tip))
    con.executemany("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?)", rows)
    con.commit(); con.close()
    kinds = {}
    for r in rows: kinds[r[6]] = kinds.get(r[6], 0) + 1
    print(f"页 {len(files)} | chunks {len(rows)} | 空页 {skipped} | 类型 {kinds}")
    print(f"平均 {sum(r[5] for r in rows)/max(1,len(rows)):.0f} 字")

if __name__ == "__main__":
    main()