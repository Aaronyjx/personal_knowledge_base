# Legal Registry Schema V2 设计规范

## 1. 设计目标

以权威法律 DOCX 和生产 Parser 输出为唯一正文来源，
建立稳定、可追溯、支持法律版本和适用日期的 Canonical Registry。

本设计不迁移旧 Qdrant Points，不依赖旧 Qdrant 正文。

### 1.1 文档定位

本文档定义 Legal Registry V2（Canonical Registry V2）的正式数据结构、
实体关系、身份生成协议、法律版本管理、来源追溯及持久化事务保护规则。

Canonical Registry V2 是本项目法律数据的规范化权威数据层，
也是后续向量数据库构建和检索的数据来源。

本文档完成的是 Canonical Registry 层的设计定稿，
不代表整个法律 RAG 数据存储与检索架构已经全部设计完成。

### 1.2 整体数据架构

本项目采用分层数据架构：

1. 权威法律来源层：保存官方原始法律文件及其来源信息。
2. Canonical Registry 层：统一管理法律身份、版本、法条正文、
   来源记录及其关联关系。
3. 向量检索层：基于 Canonical Registry 构建 Qdrant Collection，
   保存向量及可追溯的 Payload。
4. 检索与决策层：利用向量检索结果获取法律依据，
   并交由现有法律规则与决策系统处理。

各层职责必须明确：

- 权威法律文件是原始法律内容的来源。
- Canonical Registry 是法律结构化数据及其身份关系的权威来源。
- Qdrant 是由 Canonical Registry 派生构建的向量检索存储层。
- Qdrant 不得反向决定法律身份、法律版本或权威正文。

### 1.3 本文档的设计范围

本文档负责定稿：

- Law、LawVersion、Source、Article 等实体结构；
- 法律、版本、来源及法条关联关系；
- UUID5 身份协议；
- 法律版本和适用日期管理；
- 权威来源及正文 Hash 追溯；
- Registry 数据完整性及事务保护要求。

本文档不负责定稿 Qdrant Collection 的完整技术结构，
也不负责定稿 Registry 到 Qdrant 的实际构建、写入和验收实现。

### 1.4 后续配套设计

后续必须形成两份独立的配套设计：

1. Qdrant Collection V2 设计规范：
   定义 Collection、Vector、Point ID、Payload、索引、
   向量配置及检索过滤规则。
2. Registry → Qdrant 构建与验收规范：
   定义 Registry 数据读取、Embedding 生成、批量写入、
   失败处理、数据一致性验证、检索验收及 Collection 切换流程。

两份配套设计必须遵守本文档已经定稿的身份协议、
正文来源规则和数据追溯要求。

如后续发现 Canonical Registry 结构需要调整，
应先修改并确认本文档，再实施相关代码变更。

### 1.5 设计状态

本文档代表 Canonical Registry V2 的正式设计基线。

后续 Builder、Registry 验证器及 Qdrant 构建程序
均应以本文档为依据实现。

Qdrant Collection V2 和 Registry → Qdrant 构建与验收规范
属于后续独立设计阶段，完成评审和确认后方可进入相应实施阶段。

## 2. Registry 顶层结构

保持现有顶层数组结构：

- schema_version
- updated_at
- laws
- law_versions

Schema 版本升级为 2.0。

Law 与 LawVersion 通过 law_id 关联。
LawVersion 独立保存，不嵌套在 Law 内。

## 3. 实体关系

LegalRegistry
├── laws[]
│   └── Law
└── law_versions[]
    └── LawVersion
        ├── sources[]
        │   └── LawVersionSource
        └── articles[]
            └── LegalArticle
                └── sources[]
                    └── LegalArticleSource
                        └── locations[]
                            └── SourceLocation

## 4. 身份协议

所有身份使用 UUID5。

### law_id

固定 Law Namespace。

身份输入：
jurisdiction + 规范化法律名称。

### version_id

固定 Version Namespace。

身份输入：
law_id + version_key。

### source_id

固定 Source Namespace。

身份输入：规范化后的官方来源 URL + 原始来源文件 SHA256。

完整规范见第 13.5 节。相同文件 Hash、不同官方来源 URL，必须生成不同 source_id。

### article_id

保留现有 ARTICLE_NAMESPACE 和 build_article_id()。

身份输入：
version_id + 规范化 article_number。

### article_source_id

固定 ArticleSource Namespace。

身份输入：
article_id + source_id。

所有 Namespace 均为永久项目常量。
新增 Namespace 不得复用 ARTICLE_NAMESPACE。

身份输入的字段顺序、分隔符、编码和规范化规则
必须在实现中固定并测试。

## 5. Law

保留现有字段：

- law_id
- law_name
- law_type
- issuing_authority
- aliases
- created_at

增加：

- jurisdiction

jurisdiction 使用稳定的司法管辖区代码。
本轮中国法律数据使用 CN。

## 6. LawVersion

保留：

- version_id
- law_id
- version_key
- version_label
- promulgation_date
- effective_date
- expiry_date
- amendment_description
- sources
- articles
- verification_status
- verified_at
- verification_note
- validity_status
- validity_checked_at
- validity_note

version_key 是版本身份的一部分，不得随意修改。

日期使用 ISO 8601 日期格式。

有效区间采用左闭右开区间：

[effective_date, expiry_date)

expiry_date 为 null 表示尚未记录失效边界，
不能据此单独断言法律当前有效。

verification_status 与 validity_status 分别表达来源核验
和法律效力状态，不得混用。

## 7. LawVersionSource

保留现有来源字段：

- source_id
- source_name
- original_download_url
- official_source_url
- official_source_type
- source_hash
- retrieved_at
- record_located_at
- provenance_type
- provenance_status
- content_match_status
- verification_note

增加：

- source_file_path
- normalization_profile
- normalized_document_sha256

source_hash 保存原始文件 SHA256。

normalized_document_sha256 保存 Parser 规范化文档 Hash。

官方原始 DOCX 是本轮权威来源文件。
PDF 等格式不得自动替代权威来源身份。

## 8. LegalArticle

保留：

- article_id
- article_number
- article_text_hash
- sources

增加：

- article_text

article_text 必须直接来自生产 Parser 的 ParsedArticle.article_text。

article_text_hash 必须直接采用
ParsedArticle.article_text_sha256。

不得从旧 Qdrant 读取正文。
不得在 Builder 中重新清洗或规范化正文。

article_number 必须经过 normalize_article_number()。

## 9. LegalArticleSource 与 SourceLocation

保留现有字段和结构。

LegalArticleSource：

- article_source_id
- article_id
- source_id
- locations

SourceLocation：

- paragraph_start
- paragraph_end
- paragraph_numbers

段落位置必须来自生产 Parser 的 SourceLocation，
不得由另一套 DOCX 提取逻辑重新推算。

## 10. 本轮数据范围

首批数据：

- 4 个 Law
- 4 个 LawVersion
- 4 个 LawVersionSource
- 297 个 LegalArticle
- 297 个 LegalArticleSource
- 297 个 SourceLocation

四份权威 DOCX：

1. 中华人民共和国劳动争议调解仲裁法：54 条
2. 中华人民共和国劳动合同法：98 条
3. 中华人民共和国劳动合同法实施条例：38 条
4. 中华人民共和国劳动法：107 条

合计 297 条。

## 11. 重建原则

1. 旧 Qdrant Points 不迁移。
2. 新 Registry 正文来自权威 DOCX Parser。
3. 先构建并验证 Canonical Registry。
4. 再创建新 Qdrant Collection。
5. 新 Collection 完整验收后，才考虑删除旧 Collection。
6. 删除旧 Collection 前必须重新核对名称并取得用户明确确认。
7. Registry JSON 文件事务保护必须保留：
   文件锁、原子写入、fsync 和提交前文件备份。

## 12. 后续实施路线与阶段交付物

本项目按照以下阶段推进：

| 阶段 | 工作内容 | 主要交付物 |
|---|---|---|
| 第一阶段 | Canonical Registry V2 数据结构与身份协议设计 | 本文档 |
| 第二阶段 | Canonical Registry Builder 重构 | Builder 实现及测试 |
| 第三阶段 | 正式 Registry 构建与完整性验收 | Canonical Registry V2 数据文件及验收报告 |
| 第四阶段 | Qdrant Collection V2 技术设计 | 独立 Qdrant 设计规范 |
| 第五阶段 | Registry → Qdrant 构建与验收流程设计 | 独立构建与验收规范 |
| 第六阶段 | Qdrant Collection V2 实现及数据入库 | 新 Collection 及入库报告 |
| 第七阶段 | 新 Collection 完整性和检索效果验收 | 验收报告及回归测试结果 |
| 第八阶段 | 新旧 Collection 切换与旧数据清理 | 切换记录及清理审计 |
| 第九阶段 | 完整回归、版本审计及 GitHub 提交 | 正式发布版本 |

阶段之间必须遵循依赖关系。

在 Canonical Registry V2 正式构建并通过完整性验收前，
不得开始正式 Qdrant 数据入库。

在新 Collection 完整验收前，不得删除旧 Collection。

删除旧 Collection 前，必须重新核对目标 Collection 名称，
并取得用户明确确认。

每个阶段均应完成独立验证、工程目录整理、
Git 差异审计及 GitHub 提交。


## 13. 身份协议与事务保护补充定稿

本章节是身份生成和 Registry 持久化的正式补充规范。
如前文存在简略描述，以本章节的精确规则为准。

### 13.1 永久 UUID5 Namespace

新增以下固定 Namespace：

| 常量 | UUID |
|---|---|
| LAW_NAMESPACE | `0e6d1b4a-72c8-5f31-9a40-2b7e6d8c1f53` |
| VERSION_NAMESPACE | `1f7c2a90-8b43-5d61-ae20-3c9f7b5d1a64` |
| SOURCE_NAMESPACE | `2a8e3c51-9d74-5f20-b136-4e0a8c6d2f75` |
| ARTICLE_SOURCE_NAMESPACE | `3b9f4d62-ae85-5c31-c247-5f1b9d7e3a86` |

现有 ARTICLE_NAMESPACE 必须保持：

`b6d7e8f1-2a3c-4d5e-8f90-1a2b3c4d5e6f`

所有 Namespace 均为永久项目常量。
已经正式使用后，不得随意修改、复用或重新分配。

### 13.2 统一身份输入编码

除现有 article_id 规则外，新增身份规则统一采用：

1. 对身份字段执行本章节规定的规范化。
2. 构造字段名固定的 JSON 对象。
3. 使用 UTF-8 编码。
4. JSON 序列化采用：
   - ensure_ascii=False
   - sort_keys=True
   - separators=(",", ":")
5. 将序列化结果作为 UUID5 的 name 输入。

不得依赖 Python 字典插入顺序、随机 UUID、文件路径或当前时间。

### 13.3 Law ID

身份字段：

- jurisdiction
- canonical_law_name

法律名称规范化：

1. Unicode NFKC。
2. 去除首尾空白。
3. 将连续空白折叠为一个普通空格。
4. 不删除法律名称中的实质性字符。
5. 不将简称自动等同于正式名称。

本项目首批数据 jurisdiction 为 `CN`。

身份输入对象：

`{"jurisdiction":"CN","canonical_law_name":"规范化后的正式法律名称"}`

使用 LAW_NAMESPACE 生成 law_id。

### 13.4 Version ID

身份字段：

- law_id
- version_key

version_key 必须稳定、非空，并由明确的版本识别规则生成。

身份输入对象：

`{"law_id":"...","version_key":"..."}`

使用 VERSION_NAMESPACE 生成 version_id。

版本日期和文件 Hash 不单独决定 version_id。
同一法律的不同修正版本必须拥有不同 version_key。

### 13.5 Source ID：来源记录身份

source_id 不再仅由 source_hash 生成。

身份字段：

- canonical_official_source_url
- source_hash

URL 规范化规则：

1. 去除 URL 首尾空白。
2. 只接受 HTTP 或 HTTPS URL。
3. scheme 和 hostname 转为小写。
4. 删除默认端口（HTTP 80、HTTPS 443）。
5. 删除 fragment。
6. 保留 path 的实际内容。
7. 保留 query 参数及其原始顺序，不擅自排序或删除参数。
8. 不将不同 URL 自动判断为同一来源。
9. 不允许 URL 包含用户名或密码。

source_hash 使用原始文件 SHA256 的小写十六进制值。

身份输入对象：

`{"canonical_official_source_url":"规范化后的官方来源 URL","source_hash":"原始文件 SHA256"}`

使用 SOURCE_NAMESPACE 生成 source_id。

重要约束：

- 同一官方 URL、同一文件 Hash：生成相同 source_id。
- 不同官方 URL、相同文件 Hash：生成不同 source_id。
- 同一官方 URL、不同文件 Hash：生成不同 source_id。
- 不得仅因文件内容相同而合并不同来源渠道的记录。

retrieved_at 是获取记录的时间，不参与 source_id 身份计算。
同一来源文件重复获取，不因获取时间不同而自动生成新的来源身份。

如果官方来源 URL 缺失，Builder 不得擅自使用文件名或本地路径代替；
必须将来源身份问题作为数据校验错误处理。

### 13.6 Article ID

继续使用现有实现：

`build_article_id(version_id, article_number)`

继续使用现有 ARTICLE_NAMESPACE。

身份输入保持现有格式：

`version_id + "|" + normalize_article_number(article_number)`

不得改变现有 UUID5 输入格式。
不得修改现有 ARTICLE_NAMESPACE。

### 13.7 Article Source ID

身份字段：

- article_id
- source_id

身份输入对象：

`{"article_id":"...","source_id":"..."}`

使用 ARTICLE_SOURCE_NAMESPACE 生成 article_source_id。

同一法条由不同来源文件支持时，应产生不同的 ArticleSource 关联记录。

### 13.8 Source 与正文 Hash 的区别

必须分别保存：

- source_hash：原始来源文件的 SHA256。
- normalized_document_sha256：Parser 规范化后的完整文档 SHA256。
- article_text_hash：单条法条正文的 SHA256。

三者的计算对象不同，不得混用。

### 13.9 Registry 事务保护

现有 `src/legal_registry_store.py` 的事务保护机制必须保留。

必须保留：

1. 跨进程文件锁，使用 `fcntl.flock(LOCK_EX)`。
2. 事务锁内重新读取并校验 Registry。
3. 提交前 JSON 文件备份。
4. 临时文件写入。
5. 临时文件 fsync。
6. 原子替换，使用 `os.replace`。
7. 替换后父目录 fsync。
8. 失败时不留下半写入的正式 Registry。

现有以下机制不得删除或弱化：

- `_fsync_directory`
- `_create_backup`
- `_atomic_write`
- `registry_transaction`

Registry 备份属于 JSON 事务保护，不属于 Qdrant 备份。
不得因为退出 Qdrant 备份流程而删除 Registry 事务备份机制。

### 13.10 jurisdiction 字段

Law 增加 jurisdiction 字段。

本项目首批中国法律使用 `CN`。
该字段用于法律身份范围和后续多司法管辖区扩展。

jurisdiction 必须非空，并使用明确的稳定代码。
jurisdiction 参与 law_id 身份生成，不得在不执行身份迁移设计的情况下随意修改。

### 13.11 Builder 的身份稳定性测试

正式 Builder 实现必须验证：

1. 同一输入重复运行，所有身份 ID 完全一致。
2. 法律版本变化，version_id 发生变化。
3. 同一版本不同条号，article_id 不同。
4. 不同版本相同条号，article_id 不同。
5. 相同官方 URL 和相同文件 Hash，source_id 相同。
6. 不同官方 URL 和相同文件 Hash，source_id 不同。
7. 相同 article_id、不同 source_id，article_source_id 不同。
8. 改变 retrieved_at 不改变 source_id。
9. 身份生成不依赖随机数、当前时间和本地绝对路径。

### 13.12 Qdrant 数据结构边界

后续 Qdrant Payload 至少应能追溯：

- law_id
- version_id
- article_id
- article_number
- article_text_hash
- law_name
- version_key
- promulgation_date
- effective_date
- expiry_date
- source_id
- article_source_id

向量正文必须来自 Canonical Registry 的 article_text。

本章节只定义后续 Payload 的身份和追溯要求。
本阶段不创建 Collection、不生成 Embedding、不写入 Qdrant。

## 14. 后续 Qdrant 与构建验收设计边界

本章节明确后续配套设计的范围和必须遵守的架构约束。
本章节不提前定稿尚未完成评审的 Qdrant 技术参数。

### 14.1 Qdrant Collection V2 设计范围

后续 Qdrant Collection V2 设计必须明确：

1. Collection 的命名和生命周期。
2. Vector 的名称、维度、距离度量及模型版本管理。
3. Point ID 的生成规则和稳定性。
4. Payload 的完整字段结构及字段类型。
5. Payload 索引及法律版本过滤策略。
6. 法律、版本、法条和来源的关联追溯。
7. 检索时的法律版本和适用日期约束。
8. 多向量、Chunk 和不同检索表示的扩展边界。

上述具体技术参数均属于后续独立设计内容，
不得将尚未验证的选择视为本文档已经定稿的规范。

### 14.2 LegalArticle 与 Qdrant Point 的关系

Canonical Registry 中的 LegalArticle 是规范化的法条数据实体。

Qdrant Point 是向量检索层中的存储实体。
二者不应被预先限定为必然一对一关系。

后续应评估：

- 一条 LegalArticle 生成一个 Point；
- 一条较长 LegalArticle 拆分为多个 Chunk 并生成多个 Point；
- 同一 LegalArticle 生成不同检索表示；
- 不同向量模型或检索策略对应的 Point 组织方式。

如果一条 LegalArticle 对应多个 Point，
每个 Point 都必须能够追溯到对应的 article_id、
version_id 和 law_id，并保留必要的正文及来源追溯信息。

Point 的稳定身份规则应在 Qdrant 设计阶段单独确定，
不得直接假定 article_id 可以充当所有 Point 的唯一 ID。

是否采用 Chunk、如何划分 Chunk，
以及是否使用多向量，均须经过独立设计和验证。

### 14.3 Registry → Qdrant 构建流程设计范围

后续构建与验收规范至少应覆盖：

1. 从正式 Canonical Registry 读取数据。
2. Registry Schema 和身份关系验证。
3. Article 正文及 Hash 一致性验证。
4. Embedding 模型、版本和配置管理。
5. Embedding 批处理与失败处理。
6. Qdrant Point 和 Payload 构建。
7. 批量 Upsert、重试和写入结果核验。
8. Registry 与 Qdrant 数据数量及身份关系核验。
9. Point 重复、遗漏和孤立关联检测。
10. 检索过滤和法律版本约束测试。
11. 新 Collection 完整性验收。
12. 新旧 Collection 切换和旧 Collection 清理条件。

### 14.4 数据权威性与重建约束

后续 Qdrant 构建必须遵守：

- Canonical Registry 是结构化法律数据的权威来源。
- 向量正文必须来自 Registry 的 article_text 或其明确派生的 Chunk。
- 每个向量结果必须保留可追溯的法律身份和来源身份。
- 不得使用旧 Qdrant Points 作为新 Collection 的迁移数据来源。
- 新 Collection 应由正式 Registry 和明确版本的 Embedding 配置重新构建。
- 新 Collection 完整验收前，不得删除旧 Collection。
- 删除旧 Collection 前，必须重新核对目标并取得用户明确确认。

### 14.5 配套设计的独立定稿要求

Qdrant Collection V2 设计和 Registry → Qdrant 构建与验收设计
必须分别形成独立设计文档。

每份文档均应明确：

- 设计目标和适用范围；
- 数据结构及字段定义；
- 身份与关联规则；
- 失败处理和一致性约束；
- 验收标准；
- 实施顺序和安全边界。

配套设计经审查和确认后，方可进入对应实现阶段。
