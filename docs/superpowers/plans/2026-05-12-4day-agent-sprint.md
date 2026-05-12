# 4-Day Agent Sprint Plan — 507 Agent

> 参考: HelloAgents (ReAct + Tool Registry + Memory as Tool)

## Day 1 — Agent 可观测性 + 个性化 ✅

- [x] P1: 工具调用可视化（ReAct: Thought → Action → Observation）
  - Backend: `thought` SSE event
  - Frontend: 可展开工具卡片，显示思考/参数/结果
  - 中文工具名映射
- [x] P3: 用户上下文注入 System Prompt
  - Django API 查用户 → 注入姓名/学号/班级
  - Agent 回答个性化

## Day 2 — 知识库 + 记忆工具

- [ ] P2: 补充知识库
  - 用户提供办事指南/教师信息 PDF
  - 导入 kb_shared
  - 重新生成 FAQ
- [ ] Memory Tool (HelloAgents Part 3 模式):
  - 新工具: `remember_user_context(key, value)` — 存储偏好
  - 新工具: `recall_user_context(key)` — 读取
  - 存入 Redis（key=user_id:context:key, TTL 7天）
  - Agent 可自主决定何时存储/读取

## Day 3 — 课表 + 前端 Agent 化

- [ ] P0: 课表页面修复
  - 表格时间显示修正
  - 周视图日期范围修正
  - 添加 Agent 呼出按钮
- [ ] 全局 Agent 挂件
  - 悬浮聊天按钮 (FAB)
  - 可在任何页面呼出 Agent 对话
  - 复用 AIChat 组件（iframe 或 portal）

## Day 4 — 打磨 + 答辩准备

- [ ] 端到端测试 + Bug 修复
- [ ] 知识库内容最终补充
- [ ] README 更新
- [ ] 演示视频脚本
