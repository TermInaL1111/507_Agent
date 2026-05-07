# GitHub 上传与环境变量配置说明

本项目上传到 GitHub 时不要提交真实的 `.env`、`.env.local`、数据库文件、向量库数据、日志、虚拟环境或 `node_modules`。这些内容已经通过 `.gitignore` 排除。

## 1. 需要复制的环境变量文件

上传后，本地运行前按下面方式创建真实配置文件：

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item front\.env.example front\.env.local
Copy-Item DjangoUserService\.env.example DjangoUserService\.env
```

然后把其中的 `change-me`、`your_xxx_key` 替换为自己的真实配置。

## 2. FastAPI 后端配置

文件位置：`backend/.env`

| 变量名 | 是否必填 | 用途 |
| --- | --- | --- |
| `MYSQL_USER` | 是 | FastAPI 后端 MySQL 用户名 |
| `MYSQL_PASSWORD` | 是 | FastAPI 后端 MySQL 密码 |
| `MYSQL_HOST` | 是 | MySQL 地址，默认 `localhost` |
| `MYSQL_PORT` | 是 | MySQL 端口，默认 `3306` |
| `MYSQL_DATABASE` | 是 | FastAPI 使用的数据库，默认 `chat_history` |
| `DJANGO_API_URL` | 是 | Django 用户服务地址，默认 `http://127.0.0.1:8001` |
| `SECRET_KEY` | 是 | JWT 校验密钥，需要和用户服务保持一致 |
| `ALGORITHM` | 是 | JWT 算法，默认 `HS256` |
| `ALIYUN_ACCESS_KEY_SECRET` | 是 | DashScope / 通义千问 API Key |
| `DASHSCOPE_API_KEY` | 建议 | DashScope embedding 或兼容 SDK 使用 |
| `ALIYUN_BASE_URL` | 否 | DashScope 兼容接口地址 |
| `REDIS_HOST` | 是 | Redis 地址 |
| `REDIS_PORT` | 是 | Redis 端口 |
| `REDIS_DB` | 是 | Redis DB 编号 |
| `AMAP_WEB_SERVICE_KEY` | 是 | 高德 Web 服务 Key，用于站内路线规划 |
| `SKIP_RERANKER_DOWNLOAD` | 否 | 本地不下载 reranker 时设为 `true` |
| `RERANKER_MODEL_PATH` | 否 | 本地 reranker 模型路径 |
| `LANGCHAIN_TRACING_V2` | 否 | 是否启用 LangSmith 追踪 |
| `LANGCHAIN_API_KEY` | 否 | LangSmith API Key |
| `LANGCHAIN_PROJECT` | 否 | LangSmith 项目名 |

## 3. Vue 前端配置

文件位置：`front/.env.local`

| 变量名 | 是否必填 | 用途 |
| --- | --- | --- |
| `VITE_AMAP_KEY` | 是 | 高德 JS API Key，用于校园地图渲染 |
| `VITE_AMAP_SECURITY_CODE` | 是 | 高德 JS API securityJsCode |

注意：`VITE_` 开头的变量会被打包进前端代码。不要把后端数据库密码、模型 API Key、Web 服务 Key 放到前端环境变量里。

## 4. Django 用户服务配置

文件位置：`DjangoUserService/.env`

| 变量名 | 是否必填 | 用途 |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | 是 | Django 项目密钥 |
| `DJANGO_DB_NAME` | 是 | Django 用户服务数据库名 |
| `DJANGO_DB_USER` | 是 | Django 数据库用户名 |
| `DJANGO_DB_PASSWORD` | 是 | Django 数据库密码 |
| `DJANGO_DB_HOST` | 是 | Django 数据库地址 |
| `DJANGO_DB_PORT` | 是 | Django 数据库端口 |
| `CELERY_BROKER_URL` | 否 | Celery broker 地址 |
| `CELERY_RESULT_BACKEND` | 否 | Celery 结果后端 |
| `DJANGO_REDIS_CACHE_URL` | 否 | Django Redis 缓存地址 |

## 5. 上传前检查命令

```powershell
git status --short
git add -n .
```

确认输出里不包含这些内容：

- `.env`
- `.env.local`
- `.venv`
- `node_modules`
- `dist`
- `data`
- `logs`
- `*.log`
- 本地数据库文件

## 6. 推荐分支与版本标签

当前建议使用新分支：

```powershell
git checkout -b version1.0
```

提交后可以推送到远端新分支：

```powershell
git remote add origin <你的 GitHub 仓库地址>
git push -u origin version1.0
```

如需打版本标签：

```powershell
git tag v1.0
git push origin v1.0
```
