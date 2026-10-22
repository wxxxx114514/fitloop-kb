# -*- coding: utf-8 -*-
"""Cross-Encoder 重排：把 query 和文档拼成一对送进模型，输出相关性分数。
用本地 ONNX 文件，不依赖 fastembed 的下载器。"""
import os
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".models", "reranker")


class Reranker:
    def __init__(self, path=D):
        self.tok = Tokenizer.from_file(os.path.join(path, "tokenizer.json"))
        self.tok.enable_truncation(max_length=512)
        self.tok.enable_padding()
        self.sess = ort.InferenceSession(os.path.join(path, "onnx", "model.onnx"),
                                         providers=["CPUExecutionProvider"])
        self.inputs = [i.name for i in self.sess.get_inputs()]

    def scores(self, query, docs, batch=8):
        out = []
        for i in range(0, len(docs), batch):
            chunk = docs[i:i + batch]
            enc = self.tok.encode_batch([(query, d) for d in chunk])
            feed = {"input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                    "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
                    "token_type_ids": np.array([e.type_ids for e in enc], dtype=np.int64)}
            feed = {k: v for k, v in feed.items() if k in self.inputs}
            logits = self.sess.run(None, feed)[0]
            out.extend(np.asarray(logits).reshape(len(chunk), -1)[:, 0].tolist())
        return out


if __name__ == "__main__":
    r = Reranker()
    docs = ["每天摄入食盐不超过5g", "儿童青少年处于生长发育阶段"]
    print("输入:", r.inputs)
    print("分数:", r.scores("每天吃盐不超过多少", docs))
