# AI 个人工具链指南

> 整理日期：2026-05-15 | 持续更新

---

## 1. 工具链总览

### 主力：VS Code + Claude Code

```
┌──────────┐     Anthropic 协议      ┌──────────────┐
│ VS Code  │ ──→  api.deepseek.com  ──→ │ DeepSeek V4  │
│ CC 插件  │     /anthropic           │   (主力模型)   │
└──────────┘                          └──────────────┘
```

- **Claude Code 插件**（`anthropic.claude-code`）：VS Code 内嵌 Agent，直接对话
- **底层模型**：DeepSeek V4 Pro（通过 Anthropic 兼容协议中转）
- **环境变量**：
  ```bash
  ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
  ANTHROPIC_DEFAULT_OPUS_MODEL=DeepSeek-V4-Pro[1m]
  ANTHROPIC_DEFAULT_SONNET_MODEL=DeepSeek-V4-Pro[1m]
  ANTHROPIC_DEFAULT_HAIKU_MODEL=DeepSeek-V4-Pro[1m]
  ```

### 备用/闲置

| 工具 | 状态 | 原因 |
|------|------|------|
| **Windsurf** | 闲置 | 不支持 BYOK，只能 Anthropic 官方，无法接 DeepSeek |

### 辅助平台

| 服务 | 用途 |
|------|------|
| **poloapi** | API 中转站，提供多模型接入（Claude、GPT 等），统一计费 |
| **DashScope（阿里云）** | Qwen3-Reranker 重排序模型 |

---

## 2. 模型策略

### 分层

```
90% 日常任务          10% 多模态任务
┌─────────────┐     ┌─────────────────┐
│ DeepSeek V4 │     │ Claude (中转站)   │
│ 便宜 / 够用  │     │ poloapi 切换     │
└─────────────┘     └─────────────────┘
```

### DeepSeek V4 已知短板

- **无多模态**：不能读图、截图、PDF 截图
- **长上下文衰减**：128K 标注，但超长对话后期质量下降
- **工具调用稳定性**：复杂多工具联动偶尔会掉链

### 切换触发条件

| 场景 | 动作 |
|------|------|
| 用户发截图 / 图片 | 切 Claude（poloapi）|
| 需要 OCR / 视觉理解 | 切 Claude（poloapi）|
| 其余一切 | DeepSeek V4 |

---

## 3. 中转站 & 模型切换

### poloapi 使用方式

poloapi 是一个 API 代理/中转平台，聚合了多个模型厂商的 API。对使用者来说就是一个**统一 Base URL + 统一 API Key**，通过切换 model 参数来选择不同后端模型。

典型用法：在 `settings.json` 里改 `ANTHROPIC_BASE_URL` 和 `ANTHROPIC_AUTH_TOKEN` 指向 poloapi，然后用 poloapi 提供的 model ID 来选择 Claude 多模态模型。

### 切换方式对比

#### 方式一：ccswitch（有坑）

```
本地 VS Code  ✅  正常工作，能切
云服务器       ❌  不生效
```

**问题表现**：ccswitch 在本地能切换成功，但同样的配置放到云服务器上完全无效。

**根因**：ccswitch 依赖 VS Code 扩展 API 或特定的配置文件路径，云服务器上 VS Code Server 的文件结构和本地不同，导致 ccswitch 找不到或写不到正确的配置文件。

#### 方式二：手动改 settings.json（推荐）

```json
// ~/.claude/settings.json  或 项目级 .claude/settings.json
{
  "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
  "ANTHROPIC_AUTH_TOKEN": "sk-xxx"
}
```

```
本地 VS Code  ✅  能用
云服务器       ✅  能用
```

| | ccswitch | 手动 settings.json |
|------|-----------|-------------------|
| **本地** | ✅ | ✅ |
| **云服务器** | ❌ | ✅ |
| **切换速度** | 快（一键） | 慢（改文件） |
| **可靠性** | 取决于插件环境 | 可靠 |

**当前结论**：云服务器上别用 ccswitch，老实改 settings.json。可以考虑写个脚本封装切换逻辑，但底层就是替换 URL 和 key。

---

## 4. Superpowers 技能工作流

### 技能链全景

```
brainstorming → writing-plans → TDD → dispatching-agents → verification → code-review → finish
    (设计)        (计划)      (实现)     (并行执行)          (验证)        (审查)       (收尾)
```

### 核心技能

| 技能 | 何时用 | 体感 |
|------|--------|------|
| **brainstorming** | 任何新功能/改动前 | 强制我停下来想清楚再动手，避免盲目写码 |
| **writing-plans** | 设计确认后 | 把想法变成可执行的 checklist |
| **test-driven-development** | 写实现代码前 | 先写测试再写码，减少回归 bug |
| **dispatching-parallel-agents** | 多独立任务 | 并行分发，大幅提速 |
| **verification-before-completion** | 声称"做完"前 | 强制跑验证，杜绝"我以为没问题" |
| **requesting-code-review** | 完成功能后 | 结构化的审查流程 |
| **finishing-a-development-branch** | 审查通过后 | 决定合并/PR/清理 |

### 体感

- **约束感强**：每个阶段都有硬关卡，逼你不能跳步
- **减少返工**：brainstorming 阶段过滤掉 80% 的错误方向
- **适合复杂项目**：多文件、多服务协作时价值最大
- **小任务有点重**：改一行 typo 没必要走全流程

---

## 5. 踩坑记录

### 坑1：DeepSeek V4 无多模态

- **表现**：发截图给 Agent，报错或返回乱码
- **解决**：切到 poloapi 中转站的 Claude 模型
- **教训**：选模型先确认能力边界

### 坑2：ccswitch 云服务器不生效

- **表现**：本地正常，云服务器上切换无效
- **解决**：直接用 `settings.json` 手动配置
- **教训**：VS Code Server 环境 ≠ 本地 VS Code，插件工具要实测

### 坑3：Windsurf 不支持 BYOK

- **表现**：无法接入 DeepSeek API
- **现状**：闲置
- **教训**：选编辑器前确认模型自由度

---

## 6. 备忘

```
# 本地开发环境变量（~/.bashrc 或项目 .env）
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_AUTH_TOKEN=sk-xxx
ANTHROPIC_DEFAULT_OPUS_MODEL=DeepSeek-V4-Pro[1m]
ANTHROPIC_DEFAULT_SONNET_MODEL=DeepSeek-V4-Pro[1m]
ANTHROPIC_DEFAULT_HAIKU_MODEL=DeepSeek-V4-Pro[1m]

# 多模态切回（poloapi 中转站）
# ANTHROPIC_BASE_URL=<poloapi 提供的 base url>
# ANTHROPIC_DEFAULT_OPUS_MODEL=<poloapi 上的 Claude 模型 ID>
```
