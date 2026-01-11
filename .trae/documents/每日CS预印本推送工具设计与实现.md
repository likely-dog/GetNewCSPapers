**目标与范围**

* 采集 arXiv、OpenReview 上最新计算机相关预印本，统一清洗与去重。

* 按 CCF 推荐分类对研究方向进行分类；抽取摘要、改进方法/算法、实验效果。

* 如检测到已投稿在审，给出对应会议名称与 CCF 等级。

* 本地每日推送：用户选择感兴趣领域（≤5），每日推送 5–10 篇。

**数据来源**

* arXiv API：使用 Atom 接口 export.arxiv.org/api/query，解析 summary、authors、category、arxiv:comment、primary\_category 等字段，支持关键词与学科过滤。[arXiv API Basics](https://info.arxiv.org/help/api/basics.html)、[User’s Manual](https://info.arxiv.org/help/api/user-manual.html)

* OpenReview API：用 openreview-py 客户端或 REST v2，检索特定 venue 的 Blind\_Submission/Submission 与 replies（Official\_Review/Decision 等），辅助判断“在审/已收录”。[OpenReview Python Client](https://openreview-py.readthedocs.io/en/latest/api.html)、[Using the API](https://docs.openreview.net/getting-started/using-the-api)、[Notes v2 检索](https://docs.openreview.net/how-to-guides/data-retrieval-and-modification/how-to-get-all-notes-for-submissions-reviews-rebuttals-etc)

**分类与映射（CCF）**

* 构建 taxonomy 文件（ccf\_taxonomy.yaml）：涵盖用户给出的 12 大方向及子方向；为每类维护关键词、常见 arXiv primary\_category 映射、代表会议。

* 分类策略：

  * 一级规则：arXiv primary\_category 与标题/摘要关键词匹配（多标签打分）。

  * 二级补充：LLM 对研究方向进行归类，输出标准化标签；与规则融合（加权投票）。

* 示例方向映射：

  * 计算机体系结构/并行与分布/存储：isca、micro、hpca、asplos、ppopp、sc、eurosys、FAST 等关键词与 cs.AR/cs.DC/cs.SY。

  * 计算机网络：sigcomm、nsdi、infocom、conext；cs.NI。

  * 网络与信息安全：s\&p、ccs、usenix security、ndss；cs.CR。

  * 软件工程/系统软件/程序语言：icse、fse、ase、pldi、popl、oopsla；cs.SE/cs.PL。

  * 数据库/数据挖掘/检索：sigmod、vldb、kdd、icdm、www；cs.DB/cs.IR。

  * 理论：stoc、focs、soda；cs.CC/cs.DS。

  * 图形学与多媒体：siggraph、mm、cvpr/iccV 相关多模态交叉；cs.GR/cs.MM。

  * 人工智能：neurips、icml、iclr、aaai、ijcai；cs.AI、stat.ML。

  * 人机交互与普适计算：chi、ubicomp、uist；cs.HC。

  * 交叉/综合/新兴：ml-systems、robustness、privacy、bioAI 等跨域标签。

**会议信息检测**

* arXiv 元数据：解析 arxiv:comment/journal\_ref 字段内的“under review at/Submitted to/在审/投稿至”等正则，识别会议名与年份。

* OpenReview 交叉检索：

  * 在活跃顶会（ICLR/NeurIPS/AAAI 等）范围，用标题+作者模糊匹配（归一化后 FuzzyRatio ≥0.9）查找 Blind\_Submission；读取 content.venueid/status。

  * 记录 venue\_name、year、status（submission/withdrawn/desk\_rejected/accepted），来源（arXiv/OpenReview），匹配置信度。

* CCF 等级映射：维护 ccf\_venues.json（会议→等级/方向），支持别名与大小写归一；若不在映射，标注“未收录/待确认”。

**摘要与方法/实验抽取（LLM）**

* 触发条件：标题/摘要足够长或需结构化总结时；对规则抽取得到的要点进行增强。

* 提示格式：要求 JSON 输出，字段包括 direction、summary、method\_improvement、experiments、venue\_hint。

* 使用 DeepSeek API（OpenAI 兼容）进行 Chat Completions，虚拟 KEY 与接口占位：

```python
from openai import OpenAI
DEEPSEEK_API_KEY = "sk-your-virtual-key"
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
resp = client.chat.completions.create(
  model="deepseek-chat",
  messages=[
    {"role": "system", "content": "你是严谨的学术助手，按要求输出JSON"},
    {"role": "user", "content": prompt_text}
  ]
)
content = resp.choices[0].message.content
```

**推送机制**

* 推送形态：

  * 本地 HTML 报告（轻量模板），含分类导航与检索；

  * 可选邮件推送（SMTP）或 Windows Toast 通知快捷入口。

* 频率与上限：每日固定时间（默认 8:00），按用户选定 ≤5 个领域，每领域 1–2 篇，总量 5–10 篇。

* 去重策略：

  * 基于 arXiv id/OpenReview note id；

  * 标题+作者指纹哈希；

  * 本地 SQLite 记录已推送。

**项目结构**

* getnewcspapers/

  * sources/

    * arxiv\_client.py（arxiv.py 封装与规则查询）

    * openreview\_client.py（openreview-py/v2 REST 封装）

  * classify/

    * taxonomy.py（加载 ccf\_taxonomy.yaml）

    * rule\_classifier.py（关键词/类别规则）

    * llm\_classifier.py（DeepSeek 分类增强）

  * summarize/

    * llm\_summarizer.py（摘要/方法/实验 JSON 抽取）

    * heuristics.py（规则抽取补充）

  * venue/

    * detector.py（评论正则+OpenReview 交叉）

    * ccf\_map.py（ccf\_venues.json 加载与别名匹配）

  * storage/

    * db.py（SQLite，papers/users/preferences/tables）

    * models.py（Pydantic/Dataclasses）

  * delivery/

    * html\_report.py、email\_sender.py、win\_toast.py

  * scheduler/

    * job.py（每日任务）、cli.py（选择领域与预览）

  * config/

    * settings.toml（源站速率、推送时间、最大篇数等）

    * ccf\_taxonomy.yaml、ccf\_venues.json

  * tests/（端到端与模块单测）

**核心流程**

* ingest：按方向构造 arXiv 查询（cs.\* + 关键词），抓取近 1–3 天新稿；OpenReview 作为补充源。

* normalize：统一字段，生成指纹，去重落库。

* classify：规则打分→LLM 复核→融合标签。

* summarize：LLM 结构化摘要；规则补充实验指标（如 Top-1/Accuracy/mAP/FLOPs）。

* venue detect：评论正则与 OpenReview 交叉，映射 CCF 等级。

* rank & select：按用户偏好、热度（提交时间/引用数估计/关键词匹配度）选取 5–10 篇。

* deliver：生成报告与推送，标记已推送。

**关键技术细节**

* arXiv 查询构造：search\_query=all:"keyword"+AND+cat:cs.AI，分页与排序使用 SubmittedDate；建议使用 arxiv.py 封装以处理速率与重试。[arxiv.py](https://github.com/lukasschwab/arxiv.py)

* OpenReview v2：通过 venue\_id 的 Submission 邀请与 details=replies 获取状态与评论；accepted 用 content.venueid 过滤。[Notes v2 指南](https://docs.openreview.net/how-to-guides/data-retrieval-and-modification/how-to-get-all-notes-for-submissions-reviews-rebuttals-etc)

* 速率限制：arXiv 每次请求间隔≥3s（客户端可配置 delay\_seconds）；OpenReview 使用分页与 limit 控制。

* 模糊匹配：归一化标题（去停用词/大小写/符号），Levenshtein/rapidfuzz 比对。

* 安全：不写入任何真实 API Key；从环境变量读取；日志屏蔽敏感信息。

**隐私与合规**

* 尊重 arXiv/OpenReview Terms；仅抓取公开元数据与全文链接，不批量下载 PDF。

* LLM 输出仅用于摘要结构化，不传递 PDF 原文。

**交付物**

* CLI：选择兴趣领域（≤5）、设置推送时间与渠道；预览当日候选。

* 本地数据库与报告模板；示例配置与映射文件（带占位）。

* 单元测试与端到端脚本（模拟 1 天流程）。

**后续可扩展**

* 增加源：dblp 更新、Semantic Scholar 元数据。

* 指标抽取：表格/图片识别（后续可选）。

* 个性化过滤：作者黑白名单、机构偏好、关键词权重。

**请确认**

* 是否采用本方案的分类与推送形态？

* 是否优先支持 HTML 本地报告+可选邮件推送？

* 是否需要预置特定会议集（如 AI 与系统方向）作为 OpenReview 检索白名单？

