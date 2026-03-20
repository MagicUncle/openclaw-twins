# 🤖 OpenClaw Twins 双子智能平台

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-blue.svg" alt="version">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="license">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="python">
</p>

<p align="center">
  <b>自监控 · 自进化 · 双 Agent 智能平台</b>
</p>

<p align="center">
  <a href="README.md">English</a> | <b>简体中文</b>
</p>

---

## 👯 双子架构

OpenClaw Twins 采用独特的**双 Agent 协作架构**：

| 双子 | 角色 | 核心职责 |
|:----:|:----:|:---------|
| **Twin A**<br>监察者 | 🛡️ 监控优化师 | 实时监控系统状态、性能评分、异常检测、生成告警 |
| **Twin B**<br>架构师 | 🏗️ 进化导师 | 缺口分析、自动生成优化提案、驱动系统持续进化 |

### 工作流程

```
Agent 会话数据 → Twin A 监控分析 → 生成指标报告 → Twin B 消费分析
                                              ↓
优化提案生成 ← 效果追踪验证 ← 实施优化 ← 风险评估
```

---

## ✨ 核心特性

- **📊 实时监控** - 追踪所有 Agent 会话、Token 消耗、成本估算
- **🎯 智能评分** - 效能公式：`(调用次数 × 成功率) / (Token数/1000)`
- **⚠️ 分级告警** - P0/P1/P2 三级告警体系，重要问题即时通知
- **💡 自动优化** - AI 生成优化提案，支持低风险自动执行
- **💰 预算治理** - 动态配额管理，超支预警
- **🚀 灰度发布** - 金丝雀部署，安全发布新版本

---
## 界面预览


## 🚀 快速开始

### 环境要求
- Python 3.11+
- Node.js 20+
- Docker (可选)

### 安装部署

```bash
# 1. 克隆仓库
git clone https://github.com/MagicUncle/openclaw-twins.git
cd openclaw-twins

# 2. 启动开发环境
make dev

# 3. 访问控制台
open http://localhost:3000
```

### Docker 部署

```bash
docker-compose -f deploy/docker/docker-compose.yml up -d
```

---

## 🛠️ 开发命令

| 命令 | 说明 |
|------|------|
| `make dev` | 启动开发环境 |
| `make test` | 运行测试 |
| `make build` | 构建 Docker 镜像 |
| `make deploy-local` | 本地部署 |
| `make backup` | 数据备份 |
| `make bump-minor` | 升级次版本号 |

---

## 📁 项目结构

```
openclaw-twins/
├── agents/
│   ├── overseer/          # Twin A: 监控优化师
│   └── architect/         # Twin B: 进化导师
├── saas/                  # SaaS 平台（后端+前端）
├── deploy/                # 部署配置（Docker/K8s）
├── .github/workflows/     # CI/CD 工作流
└── docs/                  # 文档
```

---

## 🤝 参与贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可证

[MIT](LICENSE) © MagicUncle

---

<p align="center">
  用 ❤️ 和 🤖 构建 | OpenClaw Twins 团队
</p>
