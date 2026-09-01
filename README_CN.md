# FastScaff

FastAPI 项目脚手架工具 - 快速生成规范的 FastAPI 项目结构

[English](README.md)

## 安装

```bash
pip install fastscaff
```

## 命令

### 创建项目

```bash
fastscaff new myproject --orm sqlalchemy
```

选项:
- `--orm` - ORM 选择: `sqlalchemy` 或 `tortoise` (默认: `tortoise`)
- `--output` - 输出目录 (默认: 当前目录)
- `--with-rbac` - 启用 Casbin RBAC 权限控制
- `--with-celery` - 启用 Celery 任务队列
- `--force` - 强制覆盖已存在的目录

示例:

```bash
# 基础 SQLAlchemy 项目
fastscaff new myproject --orm sqlalchemy

# 完整功能项目
fastscaff new myproject --orm sqlalchemy --with-celery --with-rbac

# 指定输出目录
fastscaff new myproject --output /path/to/dir
```

### 从数据库生成模型

通过反射 MySQL 数据库表结构生成 ORM 模型:

```bash
cd myproject
fastscaff models --db-url "mysql://user:pass@localhost:3306/mydb"
```

选项:
- `--db-url` - 数据库连接地址 (必填)
- `--orm` - 目标 ORM: `sqlalchemy` 或 `tortoise` (自动从 requirements.txt 检测)
- `--tables` - 逗号分隔的表名 (默认: 所有表)
- `--output` - 输出目录 (默认: 当前目录)

示例:

```bash
# 在项目目录内运行 - 自动检测 ORM
cd myproject
fastscaff models --db-url "mysql://root:password@localhost:3306/mydb"

# 生成指定表的模型
fastscaff models --db-url "mysql://..." --tables user,order,product

# 显式指定 ORM
fastscaff models --db-url "mysql://..." --orm tortoise
```

生成的模型包含:
- 字段类型映射
- 主键和自增
- 索引
- 外键关系
- 表注释和字段注释

## 项目结构

```
myproject/
├── app/
│   ├── main.py              # 应用入口
│   ├── core/
│   │   ├── config.py        # 配置管理 (基于环境变量)
│   │   ├── database.py      # 数据库连接
│   │   ├── redis.py         # Redis 客户端
│   │   ├── security.py      # 密码哈希, JWT
│   │   ├── logger.py        # 结构化日志
│   │   └── lifespan.py      # 启动/关闭事件
│   ├── api/v1/
│   │   ├── router.py        # API 路由
│   │   └── endpoints/       # 路由处理器
│   ├── models/              # ORM 模型
│   ├── schemas/             # Pydantic 模式
│   ├── repositories/        # 数据访问层
│   ├── services/            # 业务逻辑层
│   ├── middleware/          # 请求/响应中间件
│   ├── exceptions/          # 自定义异常
│   └── utils/               # 工具函数
├── deploy/                  # 测试 Compose + 生产 K8s
├── tests/
├── .env.example
├── Makefile
└── requirements.txt
```

## 架构设计

生成的项目采用分层架构:

| 层级 | 目录 | 职责 |
|------|------|------|
| API 层 | `api/` | HTTP 处理、请求校验、响应格式化 |
| Service 层 | `services/` | 业务逻辑、流程编排 |
| Repository 层 | `repositories/` | 数据访问、数据库查询 |
| Model 层 | `models/` | 数据库表定义 |
| Schema 层 | `schemas/` | 请求/响应数据结构 |

Service 通过单例注册表模式访问:

```python
from app.services import registry

user = await registry.user_service.get_user_by_id(user_id)
```

## 内置功能

### 中间件

- CORS 跨域处理
- 请求日志 (带 Trace ID)
- JWT 认证
- 安全响应头
- 请求签名验证

### 工具类

- 雪花 ID 生成器
- 限流器 (基于 Redis)
- 缓存装饰器
- 密码哈希

### 数据库

- 默认 SQLite (零配置)
- 支持 MySQL/PostgreSQL (修改 `DATABASE_URL` 即可)
- 异步数据库操作
- 请求级 Session 管理 (SQLAlchemy)

## 运行项目

```bash
cd myproject
pip install -r requirements.txt
make dev
```

项目默认使用 SQLite，无需配置数据库即可直接运行。

可用的 make 命令:

```bash
make up            # 测试部署：build → 切换 → 等 ready
make down          # 停止测试栈
make dev           # 本机 uvicorn
make test          # 运行测试
make lint          # 运行 linter
```

部署：测试走 Compose + `deploy/.env.test` 占位（`source /etc/profile` 注入真值）；生产走 `deploy/deployment.yaml`（ConfigMap/Secret）。详见生成项目的 `deploy/README.md`。

如果启用了 Celery:

```bash
make celery-worker  # 启动 Celery worker
make celery-beat    # 启动 Celery 定时任务调度器
```

## 配置

配置通过环境变量管理。复制 `.env.example` 为 `.env`:

```bash
# 应用
ENV=dev
DEBUG=true
PORT=8000

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./app.db
# DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/mydb

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Celery (如果启用)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

## 开发

```bash
# 克隆仓库
git clone https://github.com/lee-hangzhou/fastscaff.git
cd fastscaff

# 开发模式安装
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
ruff check --fix .
ruff format .
```

## 许可证

MIT
