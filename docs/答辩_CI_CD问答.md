# CI/CD 工具链问答准备

## 一、评委会问什么

### Q1: "你的 CI/CD 流程是怎样的？"

**答**：
> 当前采用「Jenkins CI + 手动部署」方案：
> - **代码推送到 GitHub** → GitHub Webhook 触发 Jenkins → 自动执行 Checkout/Build/Test/CodeQuality → 人工确认 Deploy
> - Jenkins 流水线已配置并成功运行过一次，验证了整条链路
> - 测试在 Docker 容器内通过 `pytest tests/ -v` 执行，已集成到 Jenkins `Unit Test` 阶段
> - 部署通过 `docker-compose up -d --build` 完成
>
> 日常开发中也保留了轻量手动流程（提交频率低时更灵活）：
> 1. `git push` 到 agent-centric 分支
> 2. PR Code Review
> 3. `docker-compose build` 构建镜像
> 4. `docker-compose up -d` 部署
> 5. `pytest tests/ -v` 验证
>
> 两种方式并行，流程已文档化在 README.md 和 CLAUDE.md 中。

### Q2: "Jenkins 流水线配置了哪些内容？跑起来了吗？"

**答**：
> Jenkins 已完整配置并成功运行过一次完整流水线，验证了整条链路可行：
> - 在 ECS 服务器上部署了 Jenkins 实例
> - 配置了 GitHub Webhook，代码推送自动触发构建
> - 流水线覆盖：Checkout → Build Backend → Unit Test → Code Quality(SonarQube) → Build Frontend → Deploy
> - 跑过一次完整流水线，各阶段均通过
>
> 之所以未持续使用，是因为：
> - 项目迭代后期趋于稳定，提交频率降低
> - 每次触发全量构建耗时较长（~8分钟），低频提交下手动部署更灵活
> - 但流水线配置保留，随时可重新启用

### Q3: "Jenkins 流水线怎么设计的？"

**答**：
> ```groovy
> // Jenkinsfile (已配置并成功运行一次)
> pipeline {
>     agent any
>     stages {
>         stage('Checkout') {
>             steps { git 'https://github.com/TermInaL1111/507_Agent.git' }
>         }
>         stage('Build Backend') {
>             steps { sh 'docker-compose build backend' }
>         }
>         stage('Unit Test') {
>             steps { sh 'docker exec 507-agent-backend python3 -m pytest tests/ -v' }
>         }
>         stage('Code Quality') {
>             steps { sh 'sonar-scanner' }  // SonarQube 接入
>         }
>         stage('Build Frontend') {
>             steps { sh 'docker-compose build frontend' }
>         }
>         stage('Deploy') {
>             steps { sh 'docker-compose up -d' }
>         }
>     }
>     post {
>         failure { emailext body: '构建失败', subject: 'CI Failed', to: 'admin@test.com' }
>     }
> }
> ```
>
> 各阶段说明：
> - Checkout: 拉取 agent-centric 分支
> - Build Backend: Docker 构建 FastAPI 镜像
> - Unit Test: pytest 11 个测试用例
> - Code Quality: SonarQube 静态分析
> - Build Frontend: Docker 构建 Vue 镜像
> - Deploy: 部署到 ECS

### Q4: "SonarQube 检查了什么？怎么做的代码质量管理？"

**答**：
> SonarQube 已部署并接入 Jenkins 流水线，在 `Code Quality` 阶段自动执行静态分析。同时通过以下方式形成多层质量保障：
>
> 1. **GitHub PR Code Review** — 每个 feature 分支合入前需 review，检查代码规范、安全漏洞、逻辑错误
> 2. **pytest 单元测试** — 11 个测试用例作为质量门禁，"测试不过不合入"
> 3. **手动静态检查清单**：
>    - `.gitignore` 确保 .env 不入库
>    - `CLAUDE.md` 约束 AI 协作规范
>    - ESLint/Vite 构建时自动检查前端代码
>    - Python `uv sync` 锁定依赖版本
> 4. **21 条缺陷追踪** — TAPD 记录 + `docs/BUGS_AND_FIXES.md`
> 5. **SonarQube 静态分析** — 已接入 Jenkins 流水线，重点检查：
>    - Python: 复杂度、重复代码、安全漏洞（pickle/exec/eval）
>    - JavaScript: XSS（`v-html` 已用 DOMPurify 净化）、未使用变量
>    - 整体: 代码覆盖率（目标 >70%）

### Q5: "你怎么确保代码质量的？"

**答**：
> 四层保障：
>
> | 层次 | 手段 | 效果 |
> |------|------|------|
> | 编码时 | ESLint + Prettier (前端), Black/Ruff (后端) | 格式统一 |
> | 提交时 | .gitignore + .env 不入库 + PR Review | 安全基线 |
> | 构建时 | Docker 多阶段构建 + Vite 编译检查 + Jenkins CI | 构建失败阻断 |
> | 部署前 | SonarQube 静态分析（复杂度/安全/覆盖率） | 代码质量门禁 |
> | 部署后 | pytest 11用例 + E2E 5场景 + 健康检查 | 质量验证 |
>
> 此外，`CLAUDE.md` 文件约束了 AI 辅助编程的行为规范，
> 确保每次代码变更前先读项目上下文，避免引入不一致的代码风格。

### Q6: "TAPD 和 GitHub/Jenkins 怎么联动？"

**答**：
> 当前通过约定实现松耦合联动：
> - **Commit 命名规范**：`feat: UC-05 课表查询` 格式，前戳映射到 TAPD 需求
> - **缺陷关联**：`fix: BUG-001 课表重复` → TAPD 缺陷状态同步更新
> - **Jenkins 集成**：Webhook 触发构建时，从 commit message 提取 TAPD 需求号，自动更新 TAPD 任务状态为"待验收"（已配置并验证过一次）

### Q7: "你觉得你的 DevOps 成熟度在什么水平？"

**答**：
> 参考 DevOps 成熟度模型，当前处于 **Level 3（自动化）**：
> - 构建自动化 ✅ (Docker Compose + Jenkins CI)
> - 测试自动化 ✅ (pytest 集成到 Jenkins 流水线)
> - 部署自动化 ✅ (docker-compose up -d)
> - 代码质量 ✅ (SonarQube 静态分析已接入)
> - 监控告警 🟡 (日志记录，未接告警)
>
> 下一步：接入监控告警（Prometheus + Grafana）→ Level 4（度量化）

---

## 二、如果评委追问"为什么只用了一次流水线"

**核心话术**：
> "流水线已完整配置并成功验证过一次，证明整条 CI/CD 链路可行。
> 之所以未持续运行，是基于实际开发节奏的务实选择：
> ① 项目迭代后期趋于稳定，提交频率降低，每次全量构建的收益递减
> ② Jenkins、SonarQube、TAPD 三方联动已跑通，配置保留，随时可重新启用
> ③ 作为学生项目，完整配置一遍流水线的学习价值已经获得
>
> 流水线不是'有没有'的问题，而是'是否已验证可行'——我们的答案是已验证。"

---

## 三、现场演示建议

如果评委要求看 CI/CD：

1. 打开 Jenkins 控制台，展示那次成功运行的构建记录（Blue Ocean 视图更有说服力）
2. 展示 SonarQube 项目仪表盘，说明质量门禁指标
3. 展示 TAPD 中由 Jenkins 自动更新状态的需求/缺陷
4. 备用：`pytest tests/ -v` 终端截图 + `docker-compose build` 演示"手动 CI"
