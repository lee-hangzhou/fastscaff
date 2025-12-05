# FastScaff

FastAPI 项目脚手架工具 - 快速创建规范的 FastAPI 项目结构

[English](README.md)

## 特性

- 一键创建标准化的 FastAPI 项目结构
- 支持多种 ORM（Tortoise ORM / SQLAlchemy）
- 内置 JWT 认证
- 基于 structlog 的结构化日志
- 统一异常处理
- Docker 部署支持
- 测试框架集成
- 默认使用 SQLite（零配置即可运行）

## 安装

```bash
# 从源码安装
cd FastScaff
pip install -e .

# 或直接安装依赖
pip install -r requirements.txt
```

## 快速开始

### 创建新项目

```bash
# 使用 SQLAlchemy（默认 SQLite）
fastscaff new myproject --orm sqlalchemy

# 使用 Tortoise ORM
fastscaff new myproject --orm tortoise

# 指定输出目录
fastscaff new myproject --output /path/to/dir
```

### 生成的项目结构

```
myproject/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logger.py
│   │   ├── lifespan.py
│   │   ├── security.py
│   │   └── redis.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       ├── deps.py
│   │       └── endpoints/
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── middleware/
│   ├── exceptions/
│   └── utils/
├── tests/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

### 运行生成的项目

```bash
cd myproject
pip install -r requirements.txt
make dev
```

项目默认使用 SQLite，无需任何配置即可运行。

## 命令参考

```bash
# 查看帮助
fastscaff --help

# 创建新项目
fastscaff new <project_name>
  --orm         ORM 选择: tortoise 或 sqlalchemy（默认: tortoise）
  --output      输出目录（默认: 当前目录）
  --force       强制覆盖已存在的目录
  --with-rbac   启用基于 Casbin 的 RBAC

# 查看版本
fastscaff version
```

## 项目分层

| 层级 | 目录 | 职责 |
|------|------|------|
| API 层 | `api/` | HTTP 请求处理、参数校验 |
| Service 层 | `services/` | 业务逻辑、事务管理 |
| Repository 层 | `repositories/` | 数据访问、CRUD 操作 |
| Model 层 | `models/` | 数据库表定义 |
| Schema 层 | `schemas/` | 请求/响应数据结构 |

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
ruff check --fix .
ruff format .
```

## 许可证

MIT

