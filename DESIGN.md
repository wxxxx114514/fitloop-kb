# fitloop-kb · 实施文档

> 定位：**fitloop 的知识后端**。不是第三个独立项目，是那个 Agent 依赖的一层。
> 边界：kb 只负责「有出处的事实」，不做判定、不做算术。

---

## 1. 和 fitloop 的关系

~~~
fitloop（Agent，已有）  ──MCP client──▶  fitloop-kb（知识服务，新仓库）
   编排 / 数字 / 交互                      语料 / 检索 / 引用 / 拒答
~~~

**规则**：fitloop 的 5 节点图一条不动。只新增一条「问知识」的工具调用路径，和一条失败降级。

---

## 2. 边界：三路分开，这是这个项目最该讲的设计

| 路径 | 内容 | 为什么不能混 |
|---|---|---|
| **检索（RAG）** | 膳食指南、ACSM/WHO 活动指南、ISSN 立场声明 | 这类要「出处」，答错能追到某页 |
| **结构化表（SQL）** | 食物营养成分 | 数值查询用 SQL 又快又准，**进向量库是设计失误** |
| **代码计算** | 热量区间、蛋白缺口、负荷 | fitloop 已有，kb 不碰 |

> 面试一句话：「我把『该用数据库的』和『该用检索的』分开了。」

---

## 3. 目录结构

~~~
fitloop-kb/
  corpus/
    raw/            原始 PDF / HTML（不进仓库，只留清单和哈希）
    sources.yaml    语料清单：来源、年份、机构、许可、抓取时间、sha256
  build/
    fetch.py        下载 + 校验哈希
    parse_pdf.py    中文 PDF 解析（表格、双栏、脚注）
    chunk.py        切分：按章节 + 段落，保留 page/section
    ingest.py       写 chunks 表 + 向量
  kb/
    store.py        SQLite：chunks / foods / sources
    retrieve.py     BM25 + 向量 + rerank + metadata 过滤
    cite.py         取原文片段（防模型改写）
    tools.py        四个 MCP 工具的实现
    server.py       MCP server（stdio）
  eval/
    gold_150.jsonl  150 题：问题 → 应命中 source+page → 关键事实
    run_eval.py     Recall@5 / MRR / 引用准确率 / 拒答精确率
    ablation.md     四档消融结果
  docs/
    设计.md  风险.md
~~~

---

## 4. 语料清单（按实测可达性排）

| # | 来源 | 具体文件 | 可达性（本机实测） | 用途 |
|---|---|---|---|---|
| 1 | WHO | Guidelines on physical activity and sedentary behaviour (2020) | ✅ 200 | 活动量下限、久坐 |
| 2 | ISSN / JISSN | Position Stand: Protein and exercise (Jäger 2017) | ✅ 200 | 蛋白 1.4–2.0 g/kg |
| 3 | ISSN / JISSN | Position Stand: Diets and body composition（减脂期） | ✅ 同域可达 | 热量缺口、减重速度 |
| 4 | 中国营养学会 | 中国居民膳食指南（2022） | ✅ 200 | 中文权威口径、食物份量 |
| 5 | 中国营养学会 | 中国居民膳食营养素参考摄入量（DRIs） | ✅ 同上域名 | 能量/蛋白 RNI |
| 6 | ACSM | Position Stand: Weight Loss in Wrestlers / 运动减重相关 | 待验 | 快速减重的风险 |
| 7 | ISSN / JISSN | Position Stand: Nutritional Concerns of the Female Athlete | ✅ 同域 | 人群差异（为 metadata 过滤提供理由） |
| 8 | USDA FDC API | 食物营养查询（英文） | ✅ 200（需重试） | lookup_food 的表 |

**已排除**：Frontiers（本机 SSL 证书被拦）；商业出版社全文（付费）。

### 抓取策略（实测后改过，原方案有坑）

| 实测 | 结论 |
|---|---|
| `jissn.biomedcentral.com/articles/...` **没有**跳到 springer，最终 URL 仍是 jissn，200 | 只有 PDF 端点会跳/失败，页面本身可达 |
| `.../counter/pdf/....pdf` 与 `link.springer.com/content/pdf/....pdf` **都 SSL EOF 失败** | 本机抓 PDF 不稳 |
| 页面 HTML 全文完整可读 | **改为 HTML 优先** |

> 所以 `fetch.py` 的顺序是：**HTML 全文 → 失败再退 PDF**，不是反过来。
> 每次抓取记录 `content-type` + `sha256` 到 `sources.yaml`，抓不到就明确标 `unavailable`，不让构建带着空 chunk 往下跑。

### 传输方式

| 阶段 | 方式 | 为什么 |
|---|---|---|
| 开发 | **stdio** | Claude Desktop / 本地调试最省事 |
| 验收 | **streamable-http** | 要被多个调用方复用时 HTTP 才行 |

面试问「为什么两种」正好有话说：**stdio 是本地进程，http 是服务**；验证方式不同，不该只留一个。

### 两条必须写进文档的限制

1. **USDA 是英文库**。「黄焖鸡」「卤蛋」查不到——中文别名表不拍脑袋：**从 fitloop 的 data.db 历史条目统计 token 频次，取 top 200**。这样「先 200 条」有依据，也是个能写进 README 的小工程。
2. **PDF 解析是真难点**。中文指南里的表格（食物份量表）和双栏排版，解析错一行就毁一个 chunk。**W1 有一半天要花在这上面。**

---

## 5. 四个工具的 JSON schema

统一的返回约定：**每条结果必须带 citation；检索为空就返回空数组，让调用方拒答。**

~~~json
// 1) search_guideline(query, topic?, population?, year_min?)
{
  "results": [
    {
      "chunk_id": "who-2020#p12-b3",
      "text": "成人每周应进行 150–300 分钟中等强度……",
      "source": "who-2020",
      "page": 12,
      "section": "3.1 Adults",
      "year": 2020,
      "score": 0.83
    }
  ],
  "note": "为空时 results=[]，调用方应拒答而不是让模型编"
}
~~~

~~~json
// 2) get_recommendation(topic, population)
{
  "topic": "protein_intake",
  "population": "adult_cut",
  "ranges": [
    {"source": "issn-protein-2017", "low": 1.4, "high": 2.0, "unit": "g/kg/day"},
    {"source": "cns-dietary-2022", "low": 1.2, "high": 1.5, "unit": "g/kg/day"}
  ],
  "citations": [
    {"source": "issn-protein-2017", "page": 4, "quote": "1.4–2.0 g/kg"},
    {"source": "cns-dietary-2022", "page": 88, "quote": "1.2–1.5 g/kg"}
  ],
  "conflict": true,
  "decision_owner": "caller",
  "conflict_note": "kb 不选；由调用方按规则挑，规则在调用方代码里可测"
}
~~~

~~~json
// 3) lookup_food(name) —— 走表，不走向量
{
  "query": "chicken breast",
  "matched": "CHICKEN BREAST",
  "per_100g": {"kcal": 165, "protein_g": 20.4, "fat_g": 8.1, "carb_g": 1.06},
  "source": "usda-fdc",
  "fdc_id": 171477,
  "confidence": "high"
}
~~~

~~~json
// 4) cite(chunk_id) —— 取原文，防模型改写
{
  "chunk_id": "who-2020#p12-b3",
  "text": "……原文逐字……",
  "source": "who-2020",
  "page": 12
}
~~~

参数约束写进 schema：`topic` 只能是枚举（protein_intake / calorie_deficit / training_volume / weight_loss_rate），
`population` 只能是（adult / older_adult / female_athlete / adolescent）。**枚举之外一律拒答。**

---

## 6. 检索方案（四档消融，每档留数字）

| 档 | 做法 | 预期问题 |
|---|---|---|
| A | 裸向量（bge-small 中文 + e5 英文） | 专有名词查不准（1.6 g/kg 这种） |
| B | + BM25 混合（RRF 融合） | 数字和英文缩写能命中 |
| C | + cross-encoder rerank（top20→top5） | 精度上去了，延迟变高 |
| D | + metadata 过滤（population / year / 来源） | 冲突场景的关键：问「减脂期蛋白」不该混进「老年人 RNI」 |

**A→D 每档在同一个 150 题 gold 集上跑，表里只放数字。**

---

## 7. 冲突消解（这个项目最能体现深度的地方）

同一问题、不同机构、不同年份，答案不一样。**不要试图合并成一个数。**

**分工（这条必须写死，否则行为不确定、测试写不了）：**

| 谁 | 干什么 |
|---|---|
| **kb** | 返回 `ranges[]` + `citations[]` + `conflict: true`。**不选，不合并，不排序** |
| **调用方（fitloop）** | 用自己的纯函数 `pick_recommendation(population, training_freq)` 选一条，带单测 |

~~~
kb 返回：
  ISSN(2017)  1.4–2.0 g/kg  ← 训练人群保肌
  CNS(2022)   1.2–1.5 g/kg  ← 普通人群上限
  conflict: true, decision_owner: caller

fitloop 的 pick_recommendation 选一个：
  training_freq >= 3  → 用 ISSN 区间
  training_freq <  3  → 用 CNS 区间
  选完把「为什么选这条」和没选那条一起说出来
~~~

> 这样冲突消解是**可测代码**，不是模型自由发挥。也守住 fitloop 那条「能算的归代码」。

---

## 8. 拒答策略

三种情况必须拒，且拒得明确：

| 情况 | 判断依据 | 返回 |
|---|---|---|
| 语料里没有 | top1 分数 < 阈值。**阈值不是常数**：余弦(0–1)、RRF(几十)、cross-encoder(logits 可负) 三种量纲，必须每档单独标定 | 空结果 + note |
| 超出枚举 | topic/population 不在白名单 | 参数错误 |
| 医疗判断 | 命中医疗关键词（沿用 fitloop 的 is_medical 思路） | 直接建议就医，不检索 |

**分母要分开写，不然指标会混：**

| 指标 | 分母 | 说明 |
|---|---|---|
| Recall@5 / MRR / 引用准确率 | **120**（150 减去 30 道应拒答） | 检索类指标只在「有答案」的题上算 |
| 拒答精确率 | **30** | 只看该拒的会不会拒 |

两组不混算。混淆分母是这类项目最常见的指标问题（哪怕不是故意的）。

---

## 9. 150 题 gold 集怎么造

**配比（先定这个，再出题）**

| 类型 | 数量 | 考什么 |
|---|---|---|
| 事实定位 | 50 | 能不能找到那句话 |
| 数值查询 | 30 | 1.6 g/kg 这种精确值 |
| 冲突消解 | 20 | 两个机构口径不同 |
| 人群/年份过滤 | 20 | metadata 起不起作用 |
| 语料外（应拒答） | 30 | 拒答精确率 |

**每条的结构**

~~~json
{"q": "减脂期蛋白质吃多少",
 "expect_sources": ["issn-protein-2017#p4", "cns-dietary-2022#p88"],
 "expect_facts": ["1.4", "2.0"],
 "type": "conflict",
 "must_not": ["0.8"]}
~~~

**判分方式（关键：不靠 LLM judge）**

- 检索：看 `expect_sources` 里有没有命中 top-5 → Recall@5、MRR
- 引用准确率：答案里出现的关键事实字符串，是否真在被引 chunk 的原文里 → 纯字符串匹配
- 数值题：解析出数字，判断是否落在 `expect_facts` 区间
- 拒答题：返回空 = 对；返回了内容 = 错

> 这套和 fitloop 那 19 条解析评测是同一个方法论：**能字符串匹配就不上模型判分。**

---

## 10. 接进 fitloop（改动要小到可回滚）

新增一处，改一处：

~~~
新增  fitloop/kb_client.py      MCP 客户端，带 3 秒超时 + 1 次重试
改    fitloop/graph_app.py      query 分支里加一条：问「为什么/能不能/什么时候」→ 调 kb
~~~

**降级路径（面试最想听的一段）**：

| kb 状态 | fitloop 行为 |
|---|---|
| 正常 | 回答带引用 |
| 超时 / 挂掉 | 退回纯计算：只说数字，不解释原因 |
| 检索为空 | 明确说「我这儿没有依据」，不编 |

**fitloop 的 5 节点图和已有测试一条不改**——新增的是工具调用，不是新节点。

---

## 11. 三周排期（按天，别按周）

**W1**
| 天 | 事 |
|---|---|
| 1 | 语料清单定稿 + fetch.py（含 sha256 校验） |
| 2–3 | 中文 PDF 解析（表格/双栏是硬仗），先只啃膳食指南一本 |
| 4 | chunk 策略：按章节切，保留 page/section |
| 5 | SQLite 建表 + 导入 + 简单关键词检索先跑通 |
| 6 | MCP server 四个工具的最小实现（cite 先返回原文） |
| 7 | fitloop 接上 + 降级路径 |

**W2**
| 天 | 事 |
|---|---|
| 8–9 | 向量 + BM25 混合（RRF） |
| 10 | rerank（先用小模型，别一上来上大的） |
| 11 | metadata 过滤（population / year / source） |
| 12 | 冲突消解：citations 数组 + conflict 标记 |
| 13 | 拒答阈值标定（拿 30 题语料外样本） |
| 14 | 补语料：ISSN 三份 + WHO + USDA 别名表 |

**W3**
| 天 | 事 |
|---|---|
| 15–17 | 150 题 gold 集（每天 50 题，边出边标） |
| 18 | run_eval.py：四个指标 |
| 19 | 四档消融，出表 |
| 20 | README：架构图 + 指标表 + 已知限制 |
| 21 | 缓冲 / 修评估暴露的问题 |

---

## 12. 已知风险（写进 README，别等被问）

| 风险 | 现在的态度 |
|---|---|
| 语料只有 1000+ chunks，被问「这点量用得上向量库吗」 | 用**杂**回答：多机构、多语种、跨年份；真正的价值在冲突消解，不在规模 |
| 中文 PDF 解析质量 | W1 会先量一遍：解析正确率低于 90% 就换工具链 |
| USDA 英文库 | 中文菜靠别名表，覆盖不到的直接走「查不到」而不是猜 |
| 没有 LLM judge | 是有意的：能字符串匹配就不上模型判分 |
| 三个指标都是我自测 | README 里写明「自建 gold 集，指标是自测值」 |

---

## 13. 简历两行怎么连起来

> **陪跑 fitloop**：LangGraph 5 节点状态图，数值判定全归代码（{N} 条断言），19 题解析评测拆对 {X}%
>
> **fitloop-kb**：运动营养知识服务，BM25+向量混合检索 + 重排，Recall@5 {a}→{b}，引用准确率 {c}%，语料外拒答 {d}/30；MCP 暴露 4 个工具，被 fitloop 作为知识后端接入，服务不可用时降级为纯计算

**占位符规则**：

- `{N}` 断言数**只用一处**：`test_core.py` 的条数（现在 107），别把五套加起来又说成 N
- `{X}` 取自 `eval/run_parse.py` 的实际输出
- kb 的四个数 W3 才测，**测完再填**；README 里注明「自建 gold 集、自测值」
- 拒答写 `{d}/30` 而不是百分比：整数 100% 反而可疑，`30/30` 才像真测过

> 「0 死代码」不要写进简历——那是 `check_wiring.py` 的自检结论，不是评测指标。
> 要讲就在面试里讲：「我写了个检查脚本，查出 5 处死代码」，比塞进简历一行更值钱。

**两行连起来是一条链路：一个 Agent，加一个它依赖的知识服务。**
