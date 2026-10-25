# -*- coding: utf-8 -*-
"""把 609 块的向量算出来存盘，检索时只做余弦，不重新编码语料。"""
import sys, os, json
sys.path.insert(0, "D:/project/fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from kb.retrieve import load
from kb.embed import encode

ROOT = r"D:\project\fitloop-kb"
rows = load()
print("块数:", len(rows))
V = encode([r["text"] for r in rows])
np.save(os.path.join(ROOT, "corpus", "emb_609.npy"), V)
json.dump([r["id"] for r in rows], open(os.path.join(ROOT, "corpus", "emb_609_ids.json"), "w",
          encoding="utf-8"), ensure_ascii=False)
print("维度:", V.shape, "→ corpus/emb_609.npy")
