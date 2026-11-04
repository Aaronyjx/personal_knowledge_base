# Legal Registry V2 项目进度跟踪清单

## 1. 项目目标

建立以 Canonical Registry V2 为权威结构化数据层、
以 Qdrant 为派生向量检索层的法律 RAG 数据架构。

通过统一的法律身份、法律版本、权威来源、法条正文及来源追溯关系，
保证法律数据可识别、可验证、可重建、可追溯。

本文件是项目长期进度跟踪基准。

每个阶段开始前，应先阅读本文件，确认整体路线、已完成阶段、
当前阶段、阶段目标和进入条件。

每个阶段结束后，应及时更新本文件，记录实际交付物、
验证结果、Git Commit 和下一阶段安排。

## 2. 项目架构边界

项目采用以下分层：

1. 权威法律来源层：保存官方原始法律文件及来源信息。
2. Canonical Registry 层：管理法律、法律版本、来源、法条及身份关系。
3. Qdrant 向量检索层：从正式 Registry 派生构建向量和 Payload。
4. 检索与决策层：使用检索结果提供法律依据，并交由法律规则和决策系统处理。

核心原则：

- Canonical Registry 是法律结构化数据及身份关系的权威来源。
- Qdrant 是派生检索层，不反向决定法律身份、版本或权威正文。
- 新 Qdrant 数据必须从正式 Registry 重新构建。
- 不使用旧 Qdrant Points 作为新 Collection 的迁移数据来源。
- LegalArticle 与 Qdrant Point 不预设一对一关系。
- 旧 Collection 在新 Collection 完整验收前不得删除。
- 删除旧 Collection 前必须重新核对目标并取得用户明确确认。
- Registry JSON 的事务保护机制必须保留。

## 3. 总体阶段路线

状态说明：

- [x] 已完成
- [ ] 待开始
- [~] 进行中
- [!] 阻塞或需要处理

| 阶段 | 工作内容 | 当前状态 |
|---|---|---|
| 第一阶段 | Canonical Registry V2 数据结构与身份协议设计 | [x] 已完成 |
| 第二阶段 | Canonical Registry Builder 重构 | [ ] 待开始 |
| 第三阶段 | 正式 Registry 构建与完整性验收 | [ ] 待开始 |
| 第四阶段 | Qdrant Collection V2 技术设计 | [ ] 待开始 |
| 第五阶段 | Registry → Qdrant 构建与验收流程设计 | [ ] 待开始 |
| 第六阶段 | Qdrant Collection V2 实现及数据入库 | [ ] 待开始 |
| 第七阶段 | 新 Collection 完整性和检索效果验收 | [ ] 待开始 |
| 第八阶段 | 新旧 Collection 切换与旧数据清理 | [ ] 待开始 |
| 第九阶段 | 完整回归、版本审计及正式发布 | [ ] 待开始 |

## 4. 各阶段任务与验收标准

### 第一阶段：Canonical Registry V2 数据结构与身份协议设计

状态：[x] 已完成

目标：

完成 Canonical Registry V2 的正式数据结构、实体关系、
身份生成协议、法律版本管理、来源追溯和事务保护设计。

主要交付物：

- `docs/legal_registry_schema_v2_design.md`

主要设计内容：

- Law、LawVersion、LawVersionSource、LegalArticle、
  LegalArticleSource 和 SourceLocation。
- Law、Version、Source、Article 和 ArticleSource 的 UUID5 身份协议。
- 保留现有 ARTICLE_NAMESPACE 和 build_article_id()。
- 法律版本及适用日期管理。
- 官方来源和正文 Hash 追溯。
- Registry 文件锁、事务备份、原子写入和 fsync 保护。
- Qdrant 与 Registry 的架构边界。
- 后续 Qdrant 设计及构建验收的独立设计要求。

验收结果：

- 设计文档结构和关键规范检查通过。
- Git 差异审计通过。
- 正式提交并推送 GitHub。

正式 Commit：

`a2d16cff71b431cf9056f2da7f5140a82f407fb2`

提交说明：

`docs: clarify registry and qdrant architecture boundaries`

完成时间：2026-11-04

### 第二阶段：Canonical Registry Builder 重构

状态：[ ] 待开始

当前阶段开始时，先进行只读代码审计，不直接修改代码。

审计范围：

1. `src/legal_identity.py`：Namespace、身份生成函数和调用关系。
2. `src/legal_registry_builder.py`：当前 Builder 构建流程和字段映射。
3. Registry 数据模型。
4. Registry 校验器。
5. Registry Store 及事务保护机制。
6. Registry 初始化入口。
7. 全项目 UUID Namespace 使用情况。
8. 新增 Namespace 是否已在其他代码中使用。
9. 现有 ARTICLE_NAMESPACE 和 build_article_id() 的兼容性。

实施要求：

- 先形成只读审计报告。
- 明确现有实现与正式设计文档的差异。
- 制定 Builder 重构方案。
- 经审查后再实施代码修改。
- 保留 Registry Store 现有事务安全机制。
- 保留现有 Article 身份协议。

交付物：

- Builder 重构前审计报告。
- Builder 重构方案。
- Canonical Registry Builder 实现。
- 对应单元测试和集成测试。

完成条件：

- Builder 按正式 Schema V2 生成完整数据结构。
- 各类身份生成结果稳定且可重复。
- Article 身份协议保持兼容。
- 数据关系、字段及来源信息通过验证。
- 相关测试全部通过。
- 完成工程目录整理、Git 差异审计和 GitHub 提交。

### 第三阶段：正式 Registry 构建与完整性验收

状态：[ ] 待开始

主要任务：

1. 从权威法律原始文件读取数据。
2. 使用正式 Parser 解析 DOCX。
3. 使用完成重构的 Builder 构建 Registry。
4. 验证 Law、Version、Source 和 Article 身份。
5. 验证 Article 正文及 Hash。
6. 验证 SourceLocation 和关联关系。
7. 验证数据唯一性、完整性和一致性。
8. 验证 Registry Store 事务安全性。

首批数据目标：

- 4 Laws。
- 4 LawVersions。
- 4 Version Sources。
- 297 LegalArticles。
- 297 ArticleSources。
- 297 SourceLocations。

交付物：

- 正式 Canonical Registry V2 JSON。
- Registry 完整性验收报告。
- 对应测试结果。

完成条件：

Registry 数据结构、身份、正文、Hash、来源和关联关系全部通过验收。

在此阶段完成之前，不开始正式 Qdrant 数据入库。

### 第四阶段：Qdrant Collection V2 技术设计

状态：[ ] 待开始

主要设计范围：

1. Collection 命名和生命周期。
2. Vector 配置及 Embedding 模型版本。
3. Point ID 生成规则。
4. Payload 完整结构。
5. Payload 索引。
6. 法律版本及适用日期过滤。
7. Law、Version、Article 和 Source 追溯。
8. Chunk 切分策略。
9. 多向量和多检索表示方案。
10. Collection 重建和切换策略。

设计原则：

不预先固定未经评审的技术参数。

每个 Point 必须能够追溯到相应法律、版本和法条。

交付物：

`docs/qdrant_collection_v2_design.md`

完成条件：

Qdrant 数据结构、身份、索引、向量配置和检索过滤规则完成独立设计与确认。

### 第五阶段：Registry → Qdrant 构建与验收流程设计

状态：[ ] 待开始

主要设计范围：

1. 正式 Registry 读取。
2. Schema 和身份关系验证。
3. 正文与 Hash 验证。
4. Embedding 生成及模型版本管理。
5. 批量处理和失败重试。
6. Point 与 Payload 构建。
7. Qdrant 批量写入。
8. 数据数量和身份关系核验。
9. 重复、遗漏和孤立 Point 检测。
10. 检索过滤及法律版本约束测试。
11. 新 Collection 验收。
12. Collection 切换和旧数据清理条件。

交付物：

`docs/registry_to_qdrant_build_and_validation_v2.md`

完成条件：

构建流程、失败处理、一致性验证、验收标准和安全边界完成独立设计与确认。

### 第六阶段：Qdrant Collection V2 实现及数据入库

状态：[ ] 待开始

主要任务：

1. 按正式设计创建新 Collection。
2. 实现 Registry 到 Qdrant 的构建程序。
3. 生成 Embedding。
4. 构建 Point 和 Payload。
5. 批量写入新 Collection。
6. 记录构建结果及失败信息。
7. 执行数据一致性检查。

交付物：

- Qdrant Collection V2。
- 构建和入库程序。
- 入库记录及验收数据。

完成条件：

新 Collection 数据写入完成，所有 Point 均具备正确的身份追溯关系。

### 第七阶段：新 Collection 完整性和检索效果验收

状态：[ ] 待开始

主要任务：

1. Collection 配置核验。
2. Vector 配置核验。
3. Point 数量和唯一性核验。
4. Payload 字段和关联核验。
5. Article、Version、Law 追溯测试。
6. 法律版本过滤测试。
7. 适用日期过滤测试。
8. 检索效果回归测试。
9. 异常数据和边界条件测试。

交付物：

新 Collection 完整验收报告及检索回归结果。

完成条件：

新 Collection 完整性和检索效果均通过验收。

新 Collection 完整验收前不得删除旧 Collection。

### 第八阶段：新旧 Collection 切换与旧数据清理

状态：[ ] 待开始

主要任务：

1. 确认新 Collection 已完整验收。
2. 制定新旧 Collection 切换方案。
3. 切换检索程序使用的新 Collection。
4. 验证业务检索正常。
5. 单独核对旧 Collection 的准确名称和属性。
6. 取得用户对旧 Collection 删除的明确确认。
7. 确认后再执行旧 Collection 删除。
8. 审计专为旧 Qdrant 备份和恢复编写的退出代码。

安全约束：

切换与删除是两个独立操作。

不得将旧 Collection 删除作为切换操作的自动后续动作。

未经用户明确确认，不得删除旧 Collection。

交付物：

- Collection 切换记录。
- 旧 Collection 清理审计。
- 退出代码清单及处理记录。

### 第九阶段：完整回归、版本审计及正式发布

状态：[ ] 待开始

主要任务：

1. 完整测试套件回归。
2. 法律规则和决策链路回归。
3. Registry 与 Qdrant 数据一致性复核。
4. 工程目录整理。
5. 清理本项目阶段产生且确定不再需要的临时文件。
6. 检查 Git 已跟踪和未跟踪文件。
7. 审查完整 Git 差异。
8. 确认正式发布版本。
9. 精确暂存目标文件。
10. 提交并推送 GitHub。
11. 核对本地与远程版本一致。

交付物：

完整回归报告、版本审计记录及正式 GitHub Commit。

## 5. 当前项目进度

当前已完成：

- Canonical Registry V2 设计文档定稿。
- 权威 DOCX Parser 验收。
- 旧 Qdrant 数据只读覆盖审计。
- Registry 与 Qdrant 架构边界明确。
- 九阶段实施路线建立。

当前阶段：

第二阶段：Canonical Registry Builder 重构。

当前具体任务：

只读审计现有 Builder、Identity、Registry Model、Validator、
Store、初始化入口和 UUID Namespace 使用情况。

当前任务尚未开始代码修改。

下一步：

形成 Builder 重构前只读审计报告，并根据正式设计文档
制定具体重构方案。

## 6. 重要安全约束

1. 不得未经审计修改现有法律身份生成协议。
2. 不得修改或复用现有 ARTICLE_NAMESPACE。
3. 不得破坏现有 build_article_id() 的身份稳定性。
4. 不得弱化 Registry 文件锁、事务备份、原子替换和 fsync。
5. 不得从旧 Qdrant Points 迁移新 Registry 正文。
6. 不得在 Registry 完整性验收前正式入库。
7. 不得在新 Collection 完整验收前删除旧 Collection。
8. 删除旧 Collection 前必须取得用户明确确认。
9. 不得把历史未跟踪文件自动加入新提交。
10. 每阶段必须完成验证、目录整理、Git 审计和 GitHub 提交。

## 7. 阶段完成记录模板

每完成一个阶段，及时更新本文件：

### 第 X 阶段：阶段名称

- 状态：已完成
- 完成日期：
- 实际完成内容：
- 交付文件：
- 测试及验收结果：
- 工程目录整理结果：
- Git Commit SHA：
- GitHub 推送状态：
- 未解决问题：
- 下一阶段：

如果阶段未通过验收，应保留进行中或阻塞状态，
不得提前标记为已完成。

## 8. 进度维护规则

1. 本文件是整个项目的长期进度跟踪入口。
2. 每次开始新阶段前，先阅读本文件。
3. 不得跳过阶段依赖条件。
4. 阶段范围发生变化时，先更新本文件并说明原因。
5. 阶段完成后及时记录真实结果，不预填尚未发生的结果。
6. Git Commit SHA 必须来自实际提交记录。
7. 未完成的工作不得标记为已完成。
8. 项目设计发生正式变更时，应同步更新相关设计文档和本进度清单。
9. 每次更新后进行文档差异审计，并按项目提交流程推送 GitHub。

---

本文件只用于跟踪项目计划、阶段状态和交付记录。
具体技术规范以对应的正式设计文档为准。
