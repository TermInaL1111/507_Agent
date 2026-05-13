# 507 Agent (CampusAgent) — Agent-Centric 部署说明

507 Agent 是一个以 **AI Agent 对话为核心** 的校园智能助手平台。将传统菜单式 Web 应用改造为统一对话入口：用户通过自然语言即可触发课表查询、校园导航、培养方案检索、选课建议、文书辅助（请假条生成）等全部功能。

当前活跃分支：`agent-centric`

## 一、系统组成

| 服务 | 目录 | 容器端口 | 说明 |
| --- | --- | --- | --- |
| 前端服务 | `front` | `80` | Vue 3 + Element Plus，Nginx 反代 |
| AI 后端服务 | `backend` | `8000` | FastAPI + LangChain Agent (18 工具, DeepSeek V3) + ChromaDB RAG |
| 用户服务 | `DjangoUserService` | `8001` | Django 5.2 + DRF + SimpleJWT |
| MySQL | — | `3306` | 用户、会话、日程、文件索引 |
| Redis | — | `6379` | 缓存、限流、用户信息缓存 |

### Agent 工具清单（18 个）

| 工具 | 功能 | 输出 |
|------|------|------|
| `rag_summary_tools` | RAG 知识库检索 | 文本+来源 |
| `get_schedule_week` | 整周课表 | schedule_card |
| `get_schedule_today` | 今日课表 | schedule_card |
| `create_schedule_event` | 创建日程+冲突检测 | check_card |
| `search_campus_locations_tool` | 校园地点搜索 | 文本 |
| `get_campus_route` | 校园路线规划 | navigation_card |
| `get_training_program` | 培养方案检索 | 文本+来源 |
| `recommend_courses` | 选课建议 | recommendation_card |
| `doc_preview` | 通用文书生成 | document_card |
| `faq_recommend` | FAQ 推荐 | faq_card |
| `get_campus_service_link` | 业务办理入口链接 | recommendation_card |
| `extract_time_nodes` | 对话时间节点提取 | schedule_card |
| `remember_user_context` | 存储用户偏好至 Redis | 文本 |
| `recall_user_context` | 读取用户偏好 | 文本 |
| `get_weather_tools` | 天气查询 | 文本 |
| `what_time_is_now` | 当前时间 | 文本 |
| `get_user_info_tools` | 用户信息 | 文本 |
| `reorder_documents_tools` | 文档重排序 | 文本 |

## 二、Docker 部署（完整步骤）

以下步骤基于阿里云 ECS (Ubuntu 22.04, 4C4G) 实际部署验证。

### 1. 服务器要求

- CPU：2 核及以上
- 内存：4 GB 及以上（前端构建时峰值内存约 2.5G，建议预留）
- 磁盘：40 GB 及以上
- Docker：24+
- Docker Compose：v2+（v1.29.2 不兼容 Docker 29.x）
- Git

安装 Docker：

```bash
curl -fsSL https://get.docker.com | sudo bash
sudo systemctl enable docker
sudo systemctl start docker
docker --version          # 应 >= 24
docker compose version    # 应 >= 2
```

国内服务器配置镜像加速（可选但推荐）：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
}
EOF
sudo systemctl restart docker
```

### 2. 获取代码

```bash
git clone https://github.com/TermInaL1111/507_Agent.git
cd 507_Agent
git checkout agent-centric    # 当前主开发分支
```

### 3. 配置环境变量

```bash
cp .env.docker.example .env
nano .env
```

**必须配置的核心变量：**

```env
# ── 数据库 ──
MYSQL_ROOT_PASSWORD=<强密码>
MYSQL_DATABASE=chat_history
MYSQL_USER=agent_user
MYSQL_PASSWORD=<强密码>
MYSQL_HOST=507-agent-mysql        # 容器名，手动 docker run 时需设置

DJANGO_DB_NAME=django_user_service
DJANGO_DB_USER=agent_user
DJANGO_DB_PASSWORD=<同上密码>
DJANGO_DB_HOST=507-agent-mysql    # 容器名，手动 docker run 时需设置

# ── JWT ──（SECRET_KEY 和 DJANGO_SECRET_KEY 必须一致）
SECRET_KEY=<随机生成64字符>
DJANGO_SECRET_KEY=<与 SECRET_KEY 相同>

# ── DashScope API ──
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALIYUN_ACCESS_KEY_SECRET=<与 DASHSCOPE_API_KEY 相同>

# ── 高德地图 ──
AMAP_WEB_SERVICE_KEY=<高德 Web 服务 Key>
VITE_AMAP_KEY=<高德 JS API Key>
VITE_AMAP_SECURITY_CODE=<高德安全密钥>

# ── Redis ──
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=3

# ── Reranker ──（内存不足时建议跳过）
SKIP_RERANKER_DOWNLOAD=true
```

> **关键**：`SECRET_KEY` 和 `DJANGO_SECRET_KEY` 必须一致，否则 FastAPI 无法解码 Django 签发的 JWT → 所有 `/api/*` 请求 401。

### 4. 构建与启动

#### 方式一：Docker Compose（推荐）

```bash
# 构建并启动全部服务
docker compose up -d --build
```

首次构建耗时约 10-20 分钟（安装 Python/Node 依赖 + 构建前端）。

#### 方式二：手动 docker run（Compose 不可用时）

当 docker-compose v1 不兼容 Docker 29.x 时，可手动创建容器。

**前置：创建 Docker 网络**

```bash
docker network create zhsx_default
```

**Step 1 — MySQL**

```bash
docker run -d --name 507-agent-mysql \
  --network zhsx_default \
  --network-alias mysql \
  -e MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  -e MYSQL_DATABASE="$MYSQL_DATABASE" \
  -e MYSQL_USER="$MYSQL_USER" \
  -e MYSQL_PASSWORD="$MYSQL_PASSWORD" \
  -e MYSQL_ONETIME_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  -v mysql_data:/var/lib/mysql \
  -p 3306:3306 \
  mysql:8.4
```

> MySQL 8.4 需要 `MYSQL_ONETIME_PASSWORD` 环境变量。

**Step 2 — Redis**

```bash
docker run -d --name 507-agent-redis \
  --network zhsx_default \
  --network-alias redis \
  -v redis_data:/data \
  -p 6379:6379 \
  redis:7-alpine redis-server --appendonly yes
```

**Step 3 — Django 用户服务**

```bash
docker build -t zhsx_django-user -f DjangoUserService/Dockerfile DjangoUserService

docker run -d --name 507-agent-django-user \
  --network zhsx_default \
  --network-alias django-user \
  --env-file .env \
  -v django_media:/app/media \
  -p 8001:8001 \
  zhsx_django-user
```

**Step 4 — FastAPI 后端**

```bash
docker build -t 507-backend -f backend/Dockerfile backend

docker run -d --name 507-agent-backend \
  --network zhsx_default \
  --network-alias backend \
  --env-file .env \
  -v "$(pwd)/Training Program:/app/Training Program:ro" \
  -v backend_data:/app/data \
  -p 8000:8000 \
  507-backend
```

**Step 5 — 前端（Vue 3 + Nginx）**

```bash
# 从 .env 导出 VITE_ 变量用于构建时注入
export $(grep -E '^VITE_' .env | xargs)

docker build \
  --build-arg VITE_AMAP_KEY="$VITE_AMAP_KEY" \
  --build-arg VITE_AMAP_SECURITY_CODE="$VITE_AMAP_SECURITY_CODE" \
  -t 507-frontend -f front/Dockerfile front

docker run -d --name 507-agent-frontend \
  --network zhsx_default \
  -p 80:80 \
  507-frontend
```

> **重要**：`VITE_AMAP_KEY` 和 `VITE_AMAP_SECURITY_CODE` 在构建时通过 `--build-arg` 注入。不传则前端地图无法加载。

**Step 6 — 验证**

```bash
docker ps --format '{{.Names}} {{.Status}}'

# 验证各服务
curl -s http://localhost:80/ | head -5       # 前端 HTML
curl -s http://localhost:8000/               # {"message":"Hello World"}
curl -s http://localhost:8001/               # Django
```

访问：`http://服务器IP`

### 5. 查看日志

```bash
docker logs -f 507-agent-backend
docker logs -f 507-agent-django-user
docker logs -f 507-agent-frontend
```

## 三、Docker 服务说明

### 1. 数据持久化

Docker Compose 使用这些 volume：

| volume | 用途 |
| --- | --- |
| `mysql_data` | MySQL 数据 |
| `redis_data` | Redis 数据 |
| `backend_data` | FastAPI 上传文件、Chroma 向量库等运行数据 |
| `django_media` | Django 用户服务媒体文件 |

不要随意删除 volume，否则数据库和向量库数据会丢失。

### 2. 培养方案文件

项目目录里的 `Training Program` 会以只读方式挂载进后端容器：

```yaml
./Training Program:/Training Program:ro
```

前端“培养方案”页面可以读取文件列表。AI 问答要检索培养方案内容时，需要先通过后端导入流程写入 Chroma 向量库。向量库数据保存在 `backend_data` volume。

### 3. MySQL 数据库

Compose 会自动创建：

- `chat_history`
- `django_user_service`

如果你修改了 `.env` 中的数据库名或用户名，首次启动前修改即可。MySQL volume 已存在后，初始化脚本不会重复执行。

### 4. 前端高德 Key 修改后需要重建

因为 `VITE_` 变量在构建时注入，修改下面两个变量后需要重新 build：

```env
VITE_AMAP_KEY=...
VITE_AMAP_SECURITY_CODE=...
```

执行：

```bash
docker compose up -d --build frontend
```

## 四、常用 Docker 命令

停止服务：

```bash
docker compose down
```

停止并删除 volume，慎用：

```bash
docker compose down -v
```

重新构建全部服务：

```bash
docker compose up -d --build
```

进入后端容器：

```bash
docker compose exec backend bash
```

进入 Django 容器：

```bash
docker compose exec django-user bash
```

执行 Django 迁移：

```bash
docker compose exec django-user uv run python manage.py migrate
```

查看 FastAPI 文档：

```text
http://服务器IP/docs
```

如果直接访问后端容器端口，需要在 `docker-compose.yml` 中给 `backend` 增加端口映射。

## 五、HTTPS 与域名

如果你有域名，推荐在服务器宿主机再放一层 Nginx 或使用宝塔 / 1Panel / Caddy 做 HTTPS 终止，然后反代到 Docker 暴露的前端端口。

示例：Docker 前端暴露 `8080`，宿主机 Nginx 监听 `80/443`：

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

申请 HTTPS：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com
```

## 六、手动部署方式

如果不使用 Docker，可以按下面方式手动部署。

### 1. 安装基础环境

```bash
sudo apt update
sudo apt install -y git curl wget nginx mysql-server redis-server python3.12 python3.12-venv python3-pip
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2. 创建数据库

```sql
CREATE DATABASE chat_history CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE django_user_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'agent_user'@'localhost' IDENTIFIED BY 'your_mysql_password';
GRANT ALL PRIVILEGES ON chat_history.* TO 'agent_user'@'localhost';
GRANT ALL PRIVILEGES ON django_user_service.* TO 'agent_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 配置环境变量

```bash
cp backend/.env.example backend/.env
cp front/.env.example front/.env.local
cp DjangoUserService/.env.example DjangoUserService/.env
```

然后按实际情况填写数据库、Redis、DashScope、高德地图等配置。

### 4. 安装依赖并构建

```bash
cd backend
uv sync
cd ../DjangoUserService
uv sync
uv run python manage.py migrate
cd ../front
npm install
npm run build
```

### 5. 启动服务

FastAPI：

```bash
cd backend
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Django：

```bash
cd DjangoUserService
uv run python manage.py runserver 127.0.0.1:8001
```

前端生产环境建议使用 Nginx 托管 `front/dist`，并把 `/api/` 代理到 `127.0.0.1:8000`，把 `/user/` 和 `/file/` 代理到 `127.0.0.1:8001`。

## 七、当前版本已实现功能

| 用例 | 功能 | 触发方式 |
|------|------|----------|
| UC-01 | 用户注册/登录/注销/资料管理 | 独立页面 |
| UC-02 | 校园知识问答（RAG + 引用来源） | Agent 对话 |
| UC-03 | 统一智能体多轮对话 + SSE 流式 | Agent 对话 |
| UC-04 | 知识库文档上传/向量化/重排 | 知识库管理页 |
| UC-05 | 课表查询（今日/周）+ 冲突提醒 | Agent 对话 / 课表页 |
| UC-06 | 课程规划（培养方案检索） | Agent 对话 / 培养方案页 |
| UC-07 | 选课建议（多策略） | Agent 对话 |
| UC-08 | 校园导航（地点检索 + 路线规划） | Agent 对话 / 地图页 |
| UC-09 | 文书辅助（请假条 docx 生成） | Agent 对话 / 文书辅助页 |
| UC-10 | 管理员运维（Redis 限流 + 日志） | 后台自动 |

**SSE 事件类型**：`thought` | `response` | `tool_call` | `tool_result` | `sources` | `done` | `error`

**前端特性**：
- ReAct 可视化: Thought → Action → Observation 可展开卡片
- AgentPanel: 课表/导航页嵌入侧边 Agent 聊天
- Agent FAB: 全局悬浮按钮一键呼出 Agent
- 8 种 result_card: answer/recommendation/navigation/schedule/check/document_preview/document_result/process_guide/faq
- PDF 课表上传 → 自动解析去重 → 创建日程
- 可信度提示 (📌/⚠️/💡)
- 收藏功能 (Redis)
- Markdown 渲染 (marked + highlight.js + DOMPurify)

**知识库内容**:
- 学生手册 (2023版, 315 chunks)
- 计算机学院教师信息 (60人, 含个人主页)
- 4个学院培养方案 (15 PDF)
- 校园业务入口链接 (8个)

## 八、常见故障排查

### 401 Unauthorized
- 检查 `.env` 中 `SECRET_KEY` 和 `DJANGO_SECRET_KEY` 是否一致
- 重新登录获取新 token

### MySQL 连接失败 `Can't connect to MySQL server on 'localhost'`
- `.env` 中必须设置 `MYSQL_HOST` 和 `DJANGO_DB_HOST` 为 MySQL 容器名
- 确认 MySQL 容器在同一 Docker 网络中

### Nginx 启动失败 `host not found in upstream "backend"`
- 确保 backend/django 容器创建时带了 `--network-alias backend` / `--network-alias django-user`
- 运行 `docker network inspect zhsx_default` 确认所有容器在同一网络

### 前端高德地图不加载
- 构建时是否传入了 `--build-arg VITE_AMAP_KEY=...`
- 浏览器控制台查看是否正确加载 AMap JS API

### 内存不足（前端构建 OOM）
```bash
# 临时停止非必要容器释放内存
docker stop 507-agent-backend 507-agent-django-user
# 构建完成后重启
docker start 507-agent-backend 507-agent-django-user
```

### Agent 工具调用不显示（tool_call/tool_result 不触发）
- 确认 `agent.py` 中 `astream` 循环的 `intermediate_steps` 处理使用 `if` 而非 `elif`
- `chunk` 可能同时包含 `output` 和 `intermediate_steps`

### ChromaDB 检索为空
```bash
# 导入培养方案 PDF 到向量库
for f in "Training Program"/*.pdf; do
  curl -X POST http://localhost:8000/api/training-program/import \
    -H "Authorization: Bearer <token>"
done
```

### 容器全部重建（保留数据卷）
```bash
docker stop 507-agent-frontend 507-agent-backend 507-agent-django-user
docker rm 507-agent-frontend 507-agent-backend 507-agent-django-user
# 重新构建镜像...
# 重新 docker run...（数据卷 mysql_data/redis_data/backend_data 不受影响）
```

## 九、开发环境

```bash
# 后端
cd backend && uv sync && uv run uvicorn main:app --port 8000 --reload

# Django
cd DjangoUserService && uv sync && uv run python manage.py migrate && uv run python manage.py runserver 127.0.0.1:8001

# 前端
cd front && npm install && npm run dev
```

## 十、GitHub 上传注意事项

不要上传以下文件或目录（已配置 `.gitignore`）：

- `.env`
- `.env.local`
- `.venv`
- `node_modules`
- `dist`
- `backend/data`
- `backend/logs`
- `*.log`
- 本地数据库文件

仓库中提供的是示例配置：

- `.env.docker.example`
- `backend/.env.example`
- `front/.env.example`
- `DjangoUserService/.env.example`
- `docs/github_setup.md`

真实密码和 Key 只放在服务器本地 `.env` 文件中。
