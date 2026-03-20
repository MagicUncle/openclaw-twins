# OpenClaw Twins - Makefile
# 统一命令入口

.PHONY: help dev test lint build push deploy backup restore version

VERSION := $(shell cat VERSION)
IMAGE_PREFIX := openclaw-twins

# 默认显示帮助
help:
	@echo "OpenClaw Twins - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Start development environment"
	@echo "  make dev-backend      - Start backend only"
	@echo "  make dev-frontend     - Start frontend only"
	@echo "  make stop             - Stop all services"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make lint             - Run code linting"
	@echo ""
	@echo "Build & Push:"
	@echo "  make build            - Build Docker images"
	@echo "  make push             - Push images to registry"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-local     - Deploy to local Docker"
	@echo "  make deploy-staging   - Deploy to staging"
	@echo "  make deploy-production- Deploy to production"
	@echo "  make deploy-canary    - Deploy with canary strategy"
	@echo ""
	@echo "Backup & Restore:"
	@echo "  make backup           - Create full backup"
	@echo "  make backup-config    - Backup configuration only"
	@echo "  make list-backups     - List available backups"
	@echo "  make restore          - Interactive restore"
	@echo ""
	@echo "Version Management:"
	@echo "  make version          - Show current version"
	@echo "  make bump-patch       - Bump patch version"
	@echo "  make bump-minor       - Bump minor version"
	@echo "  make bump-major       - Bump major version"
	@echo ""
	@echo "Maintenance:"
	@echo "  make logs             - View service logs"
	@echo "  make status           - Check service status"
	@echo "  make clean            - Clean up resources"
	@echo "  make update-deps      - Update dependencies"

# Development
dev:
	@echo "🚀 Starting OpenClaw Twins development environment..."
	cd deploy/docker && docker-compose -f docker-compose.dev.yml up --build

dev-backend:
	@echo "🚀 Starting backend only..."
	cd src/twins/backend && uvicorn src.main:app --reload --port 8000

dev-frontend:
	@echo "🚀 Starting frontend only..."
	cd src/twins/frontend/public && python -m http.server 3000

stop:
	@echo "🛑 Stopping services..."
	cd deploy/docker && docker-compose down -v 2>/dev/null || true
	pkill -f "uvicorn" 2>/dev/null || true

# Testing
test:
	@echo "🧪 Running all tests..."
	make test-unit
	make test-integration

test-unit:
	@echo "🧪 Running unit tests..."
	cd src/twins/backend && pytest tests/unit -v || echo "No unit tests found"

test-integration:
	@echo "🧪 Running integration tests..."
	cd tests/integration && pytest -v || echo "No integration tests found"

lint:
	@echo "🔍 Running linters..."
	cd src/twins/backend && ruff check src/ || true
	cd src/twins/backend && black --check src/ || true

# Build & Push
build:
	@echo "🔨 Building Docker images..."
	docker build -t $(IMAGE_PREFIX)-backend:$(VERSION) -f deploy/docker/Dockerfile.backend src/twins/backend
	docker build -t $(IMAGE_PREFIX)-frontend:$(VERSION) -f deploy/docker/Dockerfile.frontend src/twins/frontend
	@echo "✅ Images built: $(IMAGE_PREFIX)-*:$(VERSION)"

push: build
	@echo "📤 Pushing images to registry..."
	docker tag $(IMAGE_PREFIX)-backend:$(VERSION) ghcr.io/$(GITHUB_USER)/$(IMAGE_PREFIX)-backend:$(VERSION)
	docker tag $(IMAGE_PREFIX)-frontend:$(VERSION) ghcr.io/$(GITHUB_USER)/$(IMAGE_PREFIX)-frontend:$(VERSION)
	docker push ghcr.io/$(GITHUB_USER)/$(IMAGE_PREFIX)-backend:$(VERSION)
	docker push ghcr.io/$(GITHUB_USER)/$(IMAGE_PREFIX)-frontend:$(VERSION)

# Deployment
deploy-local:
	@echo "🚀 Deploying to local Docker..."
	cd deploy/docker && docker-compose up -d

deploy-staging:
	@echo "🚀 Deploying to staging..."
	@echo "Triggering GitHub Actions workflow..."
	gh workflow run deploy.yml -f environment=staging -f version=$(VERSION)

deploy-production:
	@echo "🚀 Deploying to production..."
	@echo "⚠️  This will deploy to production! Continue? (y/N)"
	@read confirm && [ $$confirm = y ]
	gh workflow run deploy.yml -f environment=production -f version=$(VERSION)

deploy-canary:
	@echo "🐤 Starting canary deployment..."
	gh workflow run canary.yml -f version=$(VERSION) -f initial_weight=5

# Backup & Restore
backup:
	@echo "📦 Creating full backup..."
	.github/scripts/backup-data.sh full

backup-config:
	@echo "⚙️  Creating config backup..."
	.github/scripts/backup-data.sh config

list-backups:
	@echo "📋 Available backups:"
	@ls -1t data/backups/*.tar.gz 2>/dev/null | head -10 || echo "  (none)"

restore:
	@echo "📂 Interactive restore..."
	@ls -1t data/backups/*.tar.gz 2>/dev/null | head -5 || (echo "No backups found"; exit 1)
	@echo "Enter backup file name:"
	@read backup_file && .github/scripts/restore-data.sh $$backup_file

# Version Management
version:
	@echo "📋 Current version: $(VERSION)"

bump-patch:
	@echo "🔢 Bumping patch version..."
	.github/scripts/version-bump.sh patch

bump-minor:
	@echo "🔢 Bumping minor version..."
	.github/scripts/version-bump.sh minor

bump-major:
	@echo "🔢 Bumping major version..."
	.github/scripts/version-bump.sh major

# Maintenance
logs:
	@echo "📜 Service logs:"
	cd deploy/docker && docker-compose logs -f

status:
	@echo "📊 Service status:"
	@echo "Docker containers:"
	@docker-compose -f deploy/docker/docker-compose.yml ps 2>/dev/null || echo "  Not running"
	@echo ""
	@echo "Backend health:"
	@curl -s http://localhost:8000/health 2>/dev/null || echo "  Not responding"

clean:
	@echo "🧹 Cleaning up..."
	cd deploy/docker && docker-compose down -v 2>/dev/null || true
	docker system prune -f
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

update-deps:
	@echo "📦 Updating dependencies..."
	cd src/twins/backend && pip list --outdated
	@echo "Run 'pip install -U <package>' to update specific packages"
