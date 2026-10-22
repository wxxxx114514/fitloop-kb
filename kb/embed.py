# -*- coding: utf-8 -*-
"""向量编码：用 fastembed 的标准写法。
模型首次运行自动下载到 ~/.cache/fastembed（约 90 MB），之后离线可用。"""
import numpy as np

_MODEL = "BAAI/bge-small-zh-v1.5"
_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding
        _embedder = TextEmbedding(_MODEL)
    return _embedder


def encode(texts, batch=16):
    """返回 L2 归一化后的向量矩阵 (n, 512)。"""
    vecs = list(get_embedder().embed(list(texts), batch_size=batch))
    arr = np.vstack(vecs).astype("float32")
    arr /= (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9)
    return arr


if __name__ == "__main__":
    v = encode(["测试中文向量"])
    print("维度:", v.shape, "| 归一化:", round(float(np.linalg.norm(v[0])), 4))
