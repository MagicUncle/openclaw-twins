# OpenClaw Twins - GitOps 架构设计

## 概述

本文档定义 OpenClaw Twins 的完整 GitOps 工作流，支持自动化备份、版本发布、快速还原和灰度发布。

## 架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GitHub Repository                               │
│                   github.com/yourname/openclaw-twins                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   main      │  │  release/*  │  │  hotfix/*   │  │      deploy/*       │ │
│  │  (主分支)    │  │  (版本分支)  │  │  (热修分支)  │  │   (部署配置分支)     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                    │            │
│         └────────────────┴────────────────┘                    │            │
│                          │                                     │            │
│                    ┌─────┴─────┐                      ┌────────┴────────┐   │
│                    │  CI/CD    │                      │  GitOps Config  │   │
│                    │ Workflows │                      │   (ArgoCD/Flux) │   │
│                    └─────┬─────┘                      └────────┬────────┘   │
│                          │                                    │            │
└──────────────────────────┼────────────────────────────────────┼────────────┘
                           │                                    │
           ┌───────────────┼────────────────┐                   │
           │               │                │                   │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐      ┌──────▼──────┐
    │  Staging    │ │ Production  │ │  Rollback   │      │   Canary    │
    │  (预发布)    │ │   (生产)     │ │  (回滚区)    │      │  (灰度区)    │
    └─────────────┘ └─────────────┘ └─────────────┘      └─────────────┘
```

## 分支策略 (Git Flow 简化版)

```
main (受保护)
  │
  ├── release/v1.0.0  ────  版本准备 ────►  Tag v1.0.0
  │                               │
  ├── release/v1.1.0  ────  版本准备 ────►  Tag v1.1.0
  │                               │
  ├── hotfix/v1.0.1   ────  热修复 ──────►  Tag v1.0.1
  │
  └── deploy/staging      GitOps 部署配置
  └── deploy/production   GitOps 部署配置
```

### 分支说明

| 分支类型 | 命名规范 | 来源 | 合并目标 | 保护级别 |
|---------|---------|------|---------|---------|
| main | `main` | - | - | 🔴 严格保护 |
| 功能分支 | `feature/*` | main | main | 🟡 需PR |
| 版本分支 | `release/v*.*.*` | main | main + tag | 🔴 严格保护 |
| 热修分支 | `hotfix/v*.*.*` | main | main + tag | 🔴 严格保护 |
| 部署配置 | `deploy/*` | - | - | 🟡 需PR |

## 版本号规范 (SemVer)

```
主版本号.次版本号.修订号
   │       │       │
   │       │       └── 向后兼容的问题修复
   │       │           例：修复 bug、安全补丁
   │       │
   │       └── 向后兼容的功能新增
   │           例：新增 API、新增配置项
   │
   └── 不兼容的 API 修改
       例：重构接口、删除功能

示例：1.2.3
```

### 版本标签

- `v{major}.{minor}.{patch}` - 正式版本
- `v{major}.{minor}.{patch}-rc.{n}` - 候选版本
- `v{major}.{minor}.{patch}-beta.{n}` - 公测版本

## 目录结构

```
openclaw-twins/
├── .github/
│   ├── workflows/              # CI/CD 工作流
│   │   ├── ci.yml              # 持续集成
│   │   ├── release.yml         # 版本发布
│   │   ├── backup.yml          # 自动备份
│   │   ├── rollback.yml        # 快速回滚
│   │   └── deploy.yml          # 部署触发
│   ├── scripts/                # 自动化脚本
│   │   ├── version-bump.sh     # 版本号升级
│   │   ├── backup-data.sh      # 数据备份
│   │   ├── restore-data.sh     # 数据还原
│   │   └── canary-deploy.sh    # 灰度发布
│   └── GITOPS_ARCHITECTURE.md  # 本文档
│
├── src/                        # 源代码
│   ├── twins/                  # 核心系统 (原 saas)
│   │   ├── backend/
│   │   ├── frontend/
│   │   └── docker-compose.yml
│   ├── agents/
│   │   ├── overseer/           # Twin A: 监控优化师
│   │   └── architect/          # Twin B: 进化导师
│   └── shared/                 # 共享组件
│
├── deploy/                     # 部署配置
│   ├── docker/
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   └── docker-compose.yml
│   ├── k8s/                    # Kubernetes 配置
│   │   ├── base/               # 基础资源
│   │   ├── staging/            # 预发布覆盖
│   │   ├── production/         # 生产覆盖
│   │   └── canary/             # 灰度发布配置
│   └── helm/                   # Helm Charts
│
├── scripts/                    # 运维脚本
│   ├── install.sh              # 一键安装
│   ├── upgrade.sh              # 升级脚本
│   └── backup.sh               # 本地备份
│
├── docs/                       # 文档
│   ├── architecture/           # 架构文档
│   ├── api/                    # API 文档
│   └── deployment/             # 部署指南
│
├── tests/                      # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── data/                       # 数据目录 (gitignore)
│   ├── backups/                # 备份文件
│   └── snapshots/              # 系统快照
│
├── VERSION                     # 当前版本号
├── CHANGELOG.md                # 变更日志
└── README.md
```

## CI/CD 工作流

### 1. CI Pipeline (ci.yml)

```yaml
触发条件:
  - push 到 main
  - pull_request 到 main

任务:
  1. 代码检查 (lint)
  2. 单元测试 (pytest)
  3. 集成测试 (docker-compose)
  4. 构建镜像
  5. 安全扫描 (trivy)
```

### 2. Release Pipeline (release.yml)

```yaml
触发条件:
  - 手动触发
  - push 到 release/* 分支

任务:
  1. 版本号验证
  2. 生成 CHANGELOG
  3. 构建生产镜像
  4. 推送到容器仓库
  5. 创建 Git Tag
  6. 创建 GitHub Release
  7. 触发部署工作流
```

### 3. Backup Pipeline (backup.yml)

```yaml
触发条件:
  - 定时触发 (每天 02:00 UTC)
  - 手动触发

任务:
  1. 导出数据库
  2. 打包配置文件
  3. 备份到 GitHub Artifacts
  4. 可选：上传到云存储 (S3/OSS)
  5. 保留最近 30 天备份
```

### 4. Rollback Pipeline (rollback.yml)

```yaml
触发条件:
  - 手动触发

输入参数:
  - target_version: 目标版本号
  - environment: 目标环境

任务:
  1. 验证目标版本存在
  2. 备份当前状态
  3. 拉取目标版本镜像
  4. 执行数据库回滚 (如有)
  5. 更新部署配置
  6. 验证服务健康
```

## 灰度发布 (Canary Deployment)

### 流量分配策略

```
阶段 1: 0%   → 5%   (金丝雀测试，观察 15 分钟)
阶段 2: 5%   → 25%  (小流量验证，观察 30 分钟)
阶段 3: 25%  → 50%  (半量发布，观察 1 小时)
阶段 4: 50%  → 100% (全量发布)
```

### 自动化检查点

```yaml
检查点:
  - error_rate < 0.1%
  - latency_p99 < 500ms
  - cpu_usage < 80%
  - memory_usage < 85%
  
自动回滚条件:
  - error_rate > 1%
  - 5xx 错误数 > 10
  - 健康检查失败
```

## 数据备份策略

| 数据类型 | 路径 | 备份频率 | 保留期 |
|---------|------|---------|-------|
| SQLite DB | `data/*.db` | 每日 | 30 天 |
| 配置文件 | `config/` | 每次变更 | 90 天 |
| Session 数据 | `agents/*/sessions/` | 实时同步 | 7 天 |
| 提案数据 | `metrics/proposals/` | 每日 | 永久 |
| 监控报告 | `metrics/daily/` | 每日 | 90 天 |

## 快速还原

### 场景一：回滚到上一版本
```bash
# 自动模式
make rollback

# 指定版本
make rollback VERSION=v1.0.0
```

### 场景二：灾难恢复
```bash
# 1. 停止服务
make stop

# 2. 从备份还原
make restore BACKUP_FILE=backup-20240320.tar.gz

# 3. 启动服务
make start
```

## Makefile 命令速查

```makefile
# 开发
make dev          # 启动开发环境
make test         # 运行测试
make lint         # 代码检查

# 构建
make build        # 构建镜像
make push         # 推送镜像

# 部署
make deploy-staging     # 部署到预发布
make deploy-production  # 部署到生产
make deploy-canary      # 灰度发布

# 备份与还原
make backup       # 创建备份
make list-backups # 列出备份
make restore      # 还原备份

# 版本管理
make version      # 显示当前版本
make bump-patch   # 升级修订号
make bump-minor   # 升级次版本
make bump-major   # 升级主版本
make release      # 创建发布
```

---

*OpenClaw Twins GitOps Architecture v1.0*
