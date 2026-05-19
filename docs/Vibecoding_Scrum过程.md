# Vibecoding + Scrum 开发过程总结

## 一、我们的开发模式

**"Vibecoding" = AI 辅助编程 + 敏捷 Scrum 框架**。不是"AI 瞎写就完事"，而是用 AI 加速 Scrum 的每一个阶段。

```
传统 Scrum:  PO写Story → Dev编码 → Test测试 → Review
Vibecoding:   用户口述需求 → AI编码实现 → 用户验收 → AI修复Bug
              ↑                              ↑
             Product Owner               Developer + Tester
```

**角色映射**：

| Scrum 角色 | 谁承担 | 干什么 |
|------------|--------|--------|
| Product Owner | 你 | 口述需求、设定优先级、验收功能 |
| Scrum Master | 你 | 跟踪进度、TAPD 看板、判断是否"Done" |
| Developer | Claude (AI) | 编码实现、写测试、修 Bug、写文档 |

> AI 在这里不是"替代开发者"，而是"把 PO 的想法以 10x 速度变成代码"。

---

## 二、4 轮 Sprint 回顾

### Sprint 1 — MVP 主链路打通 (5/1-5/5)

**Sprint Goal**: 用户能登录、聊天、RAG 问答

| 日期 | 完成事项 | 提交数 | TAPD关联 |
|------|----------|--------|----------|
| 5/1-5/2 | 项目初始化、Docker Compose 部署 | 8 | UC-01 |
| 5/2-5/3 | Agent 工具注册、SSE 流式、System Prompt | 5 | UC-03 |
| 5/3-5/5 | RAG 问答链路、ChromaDB 向量检索 | 6 | UC-02,04 |

**Sprint Review**: 用户可通过对话提问校园知识，带来源引用 ✅
**Retrospective**: Agent 工具太少（5个），需要扩展；前端太朴素

### Sprint 2 — 核心业务扩展 (5/5-5/9)

**Sprint Goal**: 课表服务、课程规划、教师信息

| 日期 | 完成事项 | 提交数 | TAPD关联 |
|------|----------|--------|----------|
| 5/5-5/6 | 新增 7 个 Agent 工具（课表3+校园2+培养1+选课1） | 7 | UC-05,06,07,08 |
| 5/7-5/8 | PDF 课表解析上传、节次→时间映射 | 4 | UC-05 |
| 5/8-5/9 | 教师信息导入 (60人)、知识库隔离 | 3 | P2 (知识库) |

**Sprint Review**: 12 个工具可用，课表/导航/培养方案/选课建议全部打通 ✅
**Retrospective**: 课表 pre-check 用正则拦截了 Agent，违背架构初衷；需要重构

### Sprint 3 — Agent 优先 + UX 增强 (5/9-5/15)

**Sprint Goal**: 删除 pre-check、ReAct 可视化、UI 重设计

| 日期 | 完成事项 | 提交数 | TAPD关联 |
|------|----------|--------|----------|
| 5/9-5/10 | 模型切换 Qwen→DeepSeek V3 | 3 | EN-01 |
| 5/10-5/12 | 删除课表 pre-check、ReAct 可视化、Memory Tool | 12 | EN-01,02 |
| 5/12-5/13 | AgentPanel、FAB、欢迎页重设计 | 8 | EN-07 |
| 5/13-5/14 | 双校区导航、课表周偏移、入口链接工具 | 6 | UC-08 |
| 5/14-5/15 | 可信度提示、重名消歧、DESIGN.md 配色 | 5 | EN-03 |

**Sprint Review**: 18→30 个工具，ReAct 可视化，UI 改头换面 ✅
**Retrospective**: 工具太多，部分工具的 description 需要优化

### Sprint 4 — 测试 + 答辩准备 (5/15-5/19)

**Sprint Goal**: 单元测试、缺陷修复、文档完善

| 日期 | 完成事项 | 提交数 | TAPD关联 |
|------|----------|--------|----------|
| 5/15-5/16 | 收藏功能、时间节点提取、冲突检测卡片 | 5 | EN-06,08 |
| 5/16-5/17 | 单元测试 11 用例、缺陷修复 (dedup/地图/来源) | 8 | BUG-001~016 |
| 5/17-5/19 | Jenkins+SonarQube CI/CD 接入、答辩 PPT/文档 | 10 | CI/CD |

**Sprint Review**: 11/11 测试通过，21 缺陷 18 已修复，答辩材料齐备 ✅

---

## 三、Scrum 符合性对照

| Scrum 要素 | 是否做到 | 证据 |
|-----------|---------|------|
| **Product Backlog** | ✅ | 18 条需求，P0-P3 优先级，TAPD 管理 |
| **Sprint Planning** | ✅ | 每轮 Sprint 开始前我们讨论"这轮做什么" |
| **Sprint Backlog** | ✅ | 每轮拆分 5-10 个具体任务 |
| **Daily Standup** | 🟡 | Solo 项目简化为当日进度记录 + TAPD 状态更新 |
| **Sprint Review** | ✅ | 每轮结束你验收功能（"测试一下"） |
| **Sprint Retrospective** | ✅ | 每轮结束我总结"做了什么 + 下轮改进" |
| **Definition of Done** | ✅ | 代码 commit + push + 功能可演示 |
| **Burndown** | 🟡 | Git 提交密度曲线 ≈ 燃尽图（97 commits / 20天） |

### 我们没做到的（诚实说明）

| 缺失项 | 原因 | 替代方案 |
|--------|------|----------|
| Pair Programming | Solo 项目 | AI Pair Programming（Claude = pair） |
| 集体代码所有权 | Solo | GitHub PR + Code Review |
| Stakeholder 定期反馈 | 无客户 | 导师 Weekly Review |

---

## 四、Vibecoding 的 Scrum 适配

**"Vibecoding" 不是反 Scrum，而是加速了 Scrum**：

| Scrum 活动 | 传统耗时 | Vibecoding 耗时 |
|-----------|---------|----------------|
| 编写 User Story | 30 min | 5 min（口述） |
| Sprint Backlog 分解 | 1 h | 10 min（AI 自动拆） |
| 编码实现 | 4-8 h | 30 min-2 h |
| 单元测试 | 1-2 h | 15 min（AI 生成） |
| Bug 修复 | 30 min-2 h | 5-15 min |
| 文档编写 | 2-4 h | 10 min（AI 生成） |

**核心结论**：Vibecoding 让 PO（你）直接驱动开发，消除了"需求→PRD→开发"的中间损耗。AI 承担了传统 Scrum 中 Developer 的角色，但 Scrum 框架（Sprint/Review/Retro/Done）的纪律**依然适用且必须遵守**。

---

## 五、关键数字

| 指标 | 数值 |
|------|------|
| 开发周期 | 20 天 (2026/5/1 - 5/19) |
| Sprint 轮次 | 4 轮 |
| Git 提交 | 97 commits |
| Agent 工具 | 30 个 |
| 单元测试 | 11 用例，100% 通过 |
| 缺陷数 | 21（已修复 18） |
| API 端点 | 30+ |
| Docker 容器 | 5 个（+2 CI/CD） |
| 文档份数 | 15+（SAD/测试/答辩） |

---

## 六、答辩时怎么说（30 秒版本）

> "我们采用 Scrum 框架，4 轮 Sprint，每轮 1 周。
> 我作为 Product Owner 定义需求和优先级，
> 同时借助 AI 辅助编程（Vibecoding）加速开发——AI 承担 Developer 角色。
> TAPD 管理 Backlog 和缺陷，GitHub 管理代码和 PR，
> Jenkins + SonarQube 实现 CI/CD 自动化。
> 20 天完成 30 个 Agent 工具、30+ API 端点、11 个单元测试。
> 这不是"让 AI 瞎写"——Scrum 的纪律（Sprint/Review/Done）全程适用。"
