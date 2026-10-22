# -*- coding: utf-8 -*-
"""把 OCR 出来的逐页文本切成 chunks，写进 kb.db。
切块规则：按句子断，目标 450 字，重叠 80；不跨页（保证 page 引用是准的）。"""
import os, re, sys, sqlite3, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "corpus", "raw", "cns-book-2022")
DB = os.path.join(ROOT, "kb.db")

TARGET, OVERLAP, MIN_PAGE = 450, 80, 80


def split_sentences(t):
    return [s for s in re.split(r"(?<=[。！？；])", t) if s.strip()]


def chunk_page(text):
    text = re.sub(r"[ \t]+", "", text).strip()
    if len(text) < MIN_PAGE:
        return []
    out, buf = [], ""
    for s in split_sentences(text):
        if len(buf) + len(s) <= TARGET:
            buf += s
        else:
            if buf:
                out.append(buf)
            buf = (buf[-OVERLAP:] if len(buf) > OVERLAP else "") + s
    if buf.strip():
        out.append(buf)
    # 尾巴太短的并进上一块
    if len(out) >= 2 and len(out[-1]) < 120:
        out[-2] += out[-1]
        out.pop()
    return out


def main():
    con = sqlite3.connect(DB)
    con.execute("DROP TABLE IF EXISTS chunks")
    con.execute("""CREATE TABLE chunks(
        id TEXT PRIMARY KEY, source TEXT, page INT, ord INT, text TEXT, chars INT,
        is_tip INT DEFAULT 0)""")

    rows, skipped = [], 0
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".txt"):
            continue
        page = int(re.search(r"p(\d+)", f).group(1))
        text = open(os.path.join(SRC, f), encoding="utf-8").read()
        parts = chunk_page(text)
        if not parts:
            skipped += 1
            continue
        for i, p in enumerate(parts):
            # 「小贴士」框是重复样板，查询词密度高但没有答案，检索时降权
            tip = 1 if ("小贴士" in p or "贴士：" in p) else 0
            rows.append((f"cns-book-2022#p{page:03d}-{i}", "cns-book-2022", page, i, p, len(p), tip))

    con.executemany("INSERT INTO chunks VALUES (?,?,?,?,?,?,?)", rows)
    con.commit()

    pages = len({r[2] for r in rows})
    total = sum(r[5] for r in rows)
    print(f"页文件 {len(os.listdir(SRC))} 个 | 出块 {pages} 页 | 跳过空页 {skipped}")
    tips = sum(1 for r in rows if r[6])
    print(f"chunks: {len(rows)} | 平均 {total/max(1,len(rows)):.0f} 字 | 总计 {total} 字")
    print(f"其中小贴士框: {tips} 块（检索时降权 0.5）")
    print("示例:", rows[0][0], "→", rows[0][4][:80])
    con.close()


if __name__ == "__main__":
    main()