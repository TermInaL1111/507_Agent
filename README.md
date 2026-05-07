# 507 Agent v1.0 云服务器部署说明

507 Agent 是一个面向校园场景的 AI 助手系统，当前版本包含 AI 问答、RAG 知识库、培养方案检索、时间表管理、校园导航、用户登录与会话管理等功能。

本 README 主要说明如何把当前 `version1.0` 分支部署到云服务器。

## 一、系统组成

项目由三个主要服务组成：

| 服务 | 目录 | 默认端口 | 说明 |
| --- | --- | --- | --- |
| 前端服务 | `front` | `3000` / Nginx 静态服务 | Vue 3 + Vite |
| AI 后端服务 | `backend` | `8000` | FastAPI + LangChain + RAG |
| 用户服务 | `DjangoUserService` | `8001` | Django 用户登录、注册、用户信息 |

依赖的基础组件：

- MySQL：存储用户、会话、日程、文件索引等结构化数据
- Redis：缓存、限流、用户信息缓存
- Chroma：本地向量库，默认保存在 `backend/data/chromadb`
- DashScope / 通义千问 API：大模型和 embedding
- 高德地图 API：校园地图和站内路线规划

## 二、推荐服务器环境

推荐使用 Ubuntu 22.04 / 24.04 云服务器。

最低建议配置：

- CPU：2 核及以上
- 内存：4 GB 及以上，若本地加载 reranker 建议 8 GB+
- 磁盘：40 GB 及以上
- Python：3.12
- Node.js：20 LTS
- MySQL：8.x
- Redis：6.x / 7.x
- Nginx：用于反向代理和前端静态资源服务

## 三、获取代码

```bash
git clone https://github.com/TermInaL1111/507_Agent.git
cd 507_Agent
git checkout version1.0
```

如果服务器无法访问 GitHub，可以先在本地下载压缩包，再上传到服务器。

## 四、安装系统依赖

```bash
sudo apt update
sudo apt install -y git curl wget nginx mysql-server redis-server python3.12 python3.12-venv python3-pip
```

安装 `uv`：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

安装 Node.js 20：

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

## 五、数据库准备

登录 MySQL：

```bash
sudo mysql
```

创建数据库和用户，密码请自行替换：

```sql
CREATE DATABASE chat_history CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE django_user_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'agent_user'@'localhost' IDENTIFIED BY 'your_mysql_password';
GRANT ALL PRIVILEGES ON chat_history.* TO 'agent_user'@'localhost';
GRANT ALL PRIVILEGES ON django_user_service.* TO 'agent_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

启动 Redis：

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

## 六、环境变量配置

不要提交真实 `.env` 文件到 GitHub。部署时在服务器上复制示例文件：

```bash
cp backend/.env.example backend/.env
cp front/.env.example front/.env.local
cp DjangoUserService/.env.example DjangoUserService/.env
```

### 1. `backend/.env`

```env
MYSQL_USER=agent_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=chat_history

DJANGO_API_URL=http://127.0.0.1:8001

SECRET_KEY=your_shared_jwt_secret
ALGORITHM=HS256

ALIYUN_ACCESS_KEY_SECRET=your_dashscope_api_key
ALIYUN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=your_dashscope_api_key

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=3

AMAP_WEB_SERVICE_KEY=your_amap_web_service_key

SKIP_RERANKER_DOWNLOAD=true
RERANKER_MODEL_PATH=/opt/models/Qwen3-Reranker-0.6B

LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=507-agent
```

### 2. `DjangoUserService/.env`

```env
DJANGO_SECRET_KEY=your_django_secret_key
DJANGO_DB_NAME=django_user_service
DJANGO_DB_USER=agent_user
DJANGO_DB_PASSWORD=your_mysql_password
DJANGO_DB_HOST=localhost
DJANGO_DB_PORT=3306

CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/2
DJANGO_REDIS_CACHE_URL=redis://127.0.0.1:6379/3
```

### 3. `front/.env.local`

```env
VITE_AMAP_KEY=your_amap_js_api_key
VITE_AMAP_SECURITY_CODE=your_amap_security_js_code
```

注意：`VITE_` 开头变量会进入前端构建产物，不要把数据库密码、DashScope Key、Web Service Key 放到前端。

## 七、安装项目依赖

### 1. FastAPI 后端

```bash
cd backend
uv sync
cd ..
```

### 2. Django 用户服务

```bash
cd DjangoUserService
uv sync
uv run python manage.py migrate
cd ..
```

### 3. 前端

```bash
cd front
npm install
npm run build
cd ..
```

构建完成后，前端静态文件在：

```text
front/dist
```

## 八、测试启动

先用命令行测试两个后端服务是否正常。

### 1. 启动 FastAPI

```bash
cd backend
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

访问：

```text
http://服务器IP:8000/docs
```

### 2. 启动 Django 用户服务

```bash
cd DjangoUserService
uv run python manage.py runserver 127.0.0.1:8001
```

确认服务可以启动后，再配置 systemd 长期运行。

## 九、systemd 服务配置

假设项目目录为：

```text
/opt/507_Agent
```

如果你的目录不同，请同步替换下面配置里的路径。

### 1. FastAPI 服务

创建文件：

```bash
sudo nano /etc/systemd/system/507-agent-backend.service
```

写入：

```ini
[Unit]
Description=507 Agent FastAPI Backend
After=network.target mysql.service redis-server.service

[Service]
Type=simple
WorkingDirectory=/opt/507_Agent/backend
ExecStart=/opt/507_Agent/backend/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 2. Django 用户服务

创建文件：

```bash
sudo nano /etc/systemd/system/507-agent-user.service
```

写入：

```ini
[Unit]
Description=507 Agent Django User Service
After=network.target mysql.service redis-server.service

[Service]
Type=simple
WorkingDirectory=/opt/507_Agent/DjangoUserService
ExecStart=/opt/507_Agent/DjangoUserService/.venv/bin/python manage.py runserver 127.0.0.1:8001
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable 507-agent-backend
sudo systemctl enable 507-agent-user
sudo systemctl start 507-agent-backend
sudo systemctl start 507-agent-user
```

查看日志：

```bash
sudo journalctl -u 507-agent-backend -f
sudo journalctl -u 507-agent-user -f
```

## 十、Nginx 配置

创建配置文件：

```bash
sudo nano /etc/nginx/sites-available/507-agent
```

写入，`server_name` 替换为你的域名或服务器 IP：

```nginx
server {
    listen 80;
    server_name your_domain_or_server_ip;

    root /opt/507_Agent/front/dist;
    index index.html;

    client_max_body_size 100m;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /user/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /file/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/507-agent /etc/nginx/sites-enabled/507-agent
sudo nginx -t
sudo systemctl reload nginx
```

浏览器访问：

```text
http://你的服务器IP
```

## 十一、HTTPS 配置

如果已经绑定域名，建议使用 Certbot：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com
```

证书续期测试：

```bash
sudo certbot renew --dry-run
```

## 十二、培养方案与知识库数据

当前项目支持从本地目录读取培养方案文件：

```text
Training Program/
```

目录结构示例：

```text
Training Program/
  地学院/
    地质学培养方案.pdf
  工程学院/
    工程学院培养方案.pdf
```

前端“培养方案”页面会按学院展示文件列表。AI 问答要检索培养方案内容时，需要先将文件导入向量库。向量库默认生成在：

```text
backend/data/chromadb
```

`backend/data` 不建议提交到 GitHub，生产环境需要在服务器上重新导入或迁移数据目录。

## 十三、常见问题

### 1. 前端地图加载失败

检查：

- `front/.env.local` 是否配置了 `VITE_AMAP_KEY`
- `front/.env.local` 是否配置了 `VITE_AMAP_SECURITY_CODE`
- 修改后是否重新执行了 `npm run build`
- 高德控制台里 JS API Key 的域名白名单是否包含你的域名

### 2. 站内路线规划失败

检查：

- `backend/.env` 是否配置了 `AMAP_WEB_SERVICE_KEY`
- 高德 Web 服务 Key 是否开通路径规划相关能力
- 云服务器是否能访问 `https://restapi.amap.com`

### 3. AI 问答无响应或报模型错误

检查：

- `backend/.env` 中 `ALIYUN_ACCESS_KEY_SECRET`
- `backend/.env` 中 `DASHSCOPE_API_KEY`
- DashScope 账号额度和模型权限
- 后端日志：`sudo journalctl -u 507-agent-backend -f`

### 4. 登录后仍显示未登录

检查：

- Django 用户服务是否运行在 `127.0.0.1:8001`
- Nginx 是否正确代理 `/user/` 和 `/file/`
- `backend/.env` 中 `DJANGO_API_URL` 是否正确
- FastAPI 和 Django 使用的 JWT 密钥是否一致

### 5. 上传文件或知识库导入失败

检查：

- Nginx `client_max_body_size`
- `backend/data` 目录是否有写入权限
- PDF / DOCX 文件是否可解析
- DashScope embedding Key 是否有效

## 十四、GitHub 上传注意事项

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

当前仓库已提供：

- `backend/.env.example`
- `front/.env.example`
- `DjangoUserService/.env.example`
- `docs/github_setup.md`

真实密码和 Key 只放在服务器本地 `.env` 文件中。

## 十五、更新部署版本

后续更新代码时：

```bash
cd /opt/507_Agent
git pull origin version1.0

cd backend
uv sync
cd ../DjangoUserService
uv sync
uv run python manage.py migrate
cd ../front
npm install
npm run build

sudo systemctl restart 507-agent-backend
sudo systemctl restart 507-agent-user
sudo systemctl reload nginx
```

## 十六、当前版本已实现功能

- 用户登录、注册与登录状态处理
- AI 智能问答与会话管理
- RAG 知识库检索与来源反馈
- 知识库文件上传、预览和管理
- 培养方案文件列表与 AI 问答检索
- 每周时间表、当天甘特图、AI 自动加入日程
- 校园地图、地点搜索、站内路线规划
- 未登录使用受限功能时的登录提示
