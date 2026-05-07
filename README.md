# 507 Agent v1.0 部署说明

507 Agent 是一个面向校园场景的 AI 助手系统，当前版本包含 AI 问答、RAG 知识库、培养方案检索、时间表管理、校园导航、用户登录与会话管理等功能。

推荐使用 Docker Compose 一键部署。传统手动部署说明保留在后文，便于排查或二次开发。

## 一、系统组成

| 服务 | 目录 | 容器端口 | 说明 |
| --- | --- | --- | --- |
| 前端服务 | `front` | `80` | Vue 3 构建后由 Nginx 托管 |
| AI 后端服务 | `backend` | `8000` | FastAPI + LangChain + RAG |
| 用户服务 | `DjangoUserService` | `8001` | Django 登录、注册、用户信息 |
| MySQL | Docker volume | `3306` | 用户、会话、日程、文件索引 |
| Redis | Docker volume | `6379` | 缓存、限流、用户信息缓存 |

## 二、Docker 一键部署

### 1. 服务器要求

推荐 Ubuntu 22.04 / 24.04：

- CPU：2 核及以上
- 内存：4 GB 及以上，若启用本地 reranker 建议 8 GB+
- 磁盘：40 GB 及以上
- Docker：24+
- Docker Compose：v2+

安装 Docker：

```bash
curl -fsSL https://get.docker.com | sudo bash
sudo systemctl enable docker
sudo systemctl start docker
docker --version
docker compose version
```

### 2. 获取代码

```bash
git clone https://github.com/TermInaL1111/507_Agent.git
cd 507_Agent
git checkout version1.0
```

### 3. 创建 Docker 环境变量

```bash
cp .env.docker.example .env
```

编辑 `.env`：

```bash
nano .env
```

至少需要替换这些值：

```env
MYSQL_ROOT_PASSWORD=change-me-root-password
MYSQL_PASSWORD=change-me-mysql-password
DJANGO_DB_PASSWORD=change-me-mysql-password

SECRET_KEY=change-me-shared-jwt-secret
DJANGO_SECRET_KEY=change-me-django-secret

ALIYUN_ACCESS_KEY_SECRET=your_dashscope_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key

AMAP_WEB_SERVICE_KEY=your_amap_web_service_key
VITE_AMAP_KEY=your_amap_js_api_key
VITE_AMAP_SECURITY_CODE=your_amap_security_js_code
```

说明：

- `VITE_AMAP_KEY` 和 `VITE_AMAP_SECURITY_CODE` 会进入前端构建产物。
- 不要把数据库密码、DashScope Key、`AMAP_WEB_SERVICE_KEY` 放到前端环境变量。
- 如果你暂时不想下载 reranker，保持 `SKIP_RERANKER_DOWNLOAD=true`。

### 4. 一键启动

```bash
docker compose up -d --build
```

首次构建会安装 Python、Node、前后端依赖，耗时较长。后端依赖包含 AI/RAG 相关包，云服务器内存太小时可能会比较吃力。

查看容器：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f backend
docker compose logs -f django-user
docker compose logs -f frontend
```

访问系统：

```text
http://服务器IP
```

默认由 `frontend` 容器暴露 `80` 端口。若服务器 80 已被占用，修改 `.env`：

```env
FRONTEND_PORT=8080
```

然后重新启动：

```bash
docker compose up -d
```

访问：

```text
http://服务器IP:8080
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

- 用户登录、注册与登录状态处理
- AI 智能问答与会话管理
- RAG 知识库检索与来源反馈
- 知识库文件上传、预览和管理
- 培养方案文件列表与 AI 问答检索
- 每周时间表、当天甘特图、AI 自动加入日程
- 校园地图、地点搜索、站内路线规划
- 未登录使用受限功能时的登录提示

## 八、GitHub 上传注意事项

不要上传以下文件或目录：

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
