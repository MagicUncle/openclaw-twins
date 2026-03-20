# 🤖 OpenClaw Twins

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-blue.svg" alt="version">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="license">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="python">
  <img src="https://img.shields.io/badge/FastAPI-0.100%2B-teal.svg" alt="fastapi">
</p>

<p align="center">
  <b>Self-Monitoring · Self-Evolving · Twin-Agent Intelligence Platform</b>
</p>

<p align="center">
  <b>English</b> | <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#deployment">Deployment</a> •
  <a href="#documentation">Docs</a>
</p>

---

## ✨ Features

OpenClaw Twins is a **Twin-Agent Intelligence Platform** that brings self-monitoring and self-evolution to your AI agent systems.

### 👯 Twin-Agent Architecture

| Twin | Role | Function |
|------|------|----------|
| **Twin A (Overseer)** | 🛡️ Monitoring Optimizer | Real-time system monitoring, performance scoring, anomaly detection |
| **Twin B (Architect)** | 🏗️ Evolution Mentor | Gap analysis, auto-generates optimization proposals, drives continuous improvement |

### 🚀 Core Capabilities

- **📊 Real-time Monitoring**: Live session tracking, token usage, cost estimation
- **🎯 Performance Scoring**: Efficiency = (Calls × Success Rate) / (Tokens/1000)
- **⚠️ Intelligent Alerts**: P0/P1/P2 alert levels with automatic notifications
- **💡 Auto-Optimization**: AI-generated improvement proposals with risk assessment
- **💰 Budget Governance**: Dynamic quota management with usage warnings
- **📈 Canary Deployment**: Safe rollout with automated health checks

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenClaw Twins Platform                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │  Twin A      │ ───→ │   Twins      │ ←─── │  Twin B      │  │
│  │  Overseer    │      │   Control    │      │  Architect   │  │
│  │              │      │   Center     │      │              │  │
│  │ • Monitor    │      │              │      │ • Analyze    │  │
│  │ • Score      │      │ • Dashboard  │      │ • Propose    │  │
│  │ • Alert      │      │ • API        │      │ • Evolve     │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│          ↑                                      ↑               │
│          └──────────────────────────────────────┘               │
│                    Data Feedback Loop                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Agent Sessions → Overseer (Analyze) → Metrics → Architect (Optimize) → Proposals
      ↑                                                                     ↓
      └────────────────── Implemented ←─ Approved ←─ Reviewed ←─────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourname/openclaw-twins.git
cd openclaw-twins

# 2. Install dependencies
make install

# 3. Start development environment
make dev

# 4. Access the dashboard
open http://localhost:3000
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose -f deploy/docker/docker-compose.yml up -d

# Or use Makefile
make deploy-local
```

---

## 🚢 Deployment

### Kubernetes

```bash
# Deploy to production
kubectl apply -k deploy/k8s/production

# Or use the GitHub Action
make deploy-production
```

### Canary Deployment

```bash
# Start canary with 5% traffic
make deploy-canary VERSION=3.1.0

# Auto-promote if health checks pass
```

---

## 📊 Dashboard

The **Twins Control Center** provides a unified view of your agent ecosystem:

| Feature | Description |
|---------|-------------|
| **Overview** | Real-time metrics, system health, active alerts |
| **Staff View** | Per-agent session details, token usage, status |
| **Budget** | Quota management, usage tracking, cost estimation |
| **Proposals** | Optimization suggestions, approval workflow |

---

## 🛠️ Development

```bash
# Run tests
make test

# Lint code
make lint

# Build images
make build

# Create backup
make backup

# Version management
make bump-patch  # or bump-minor, bump-major
```

---

## 📁 Project Structure

```
openclaw-twins/
├── src/
│   ├── twins/              # Core platform (backend + frontend)
│   └── agents/
│       ├── overseer/       # Twin A: Monitoring agent
│       └── architect/      # Twin B: Evolution agent
├── deploy/
│   ├── docker/             # Docker configurations
│   └── k8s/                # Kubernetes manifests
├── .github/
│   └── workflows/          # CI/CD pipelines
├── tests/                  # Test suites
├── data/                   # Data & backups
├── Makefile               # Command shortcuts
└── VERSION                # Current version
```

---

## 🔄 GitOps Workflow

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR | Lint, test, build |
| `release.yml` | Tag/Release | Build images, create release |
| `backup.yml` | Scheduled | Automated data backup |
| `rollback.yml` | Manual | Version rollback |
| `canary.yml` | Manual | Canary deployment |

---

## 📚 Documentation

- [GitOps Architecture](.github/GITOPS_ARCHITECTURE.md) - Deployment & operations guide
- [API Documentation](docs/api/) - API reference
- [Architecture Guide](docs/architecture/) - System design

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ and 🤖 by the OpenClaw Twins Team
</p>
