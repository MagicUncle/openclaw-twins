#!/bin/bash
# OpenClaw Twins - Installation Script

set -e

echo "🤖 OpenClaw Twins Installation"
echo "=============================="
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python version: $PYTHON_VERSION"

# Check Docker (optional)
if command -v docker &> /dev/null; then
    echo "✅ Docker found"
    HAS_DOCKER=true
else
    echo "⚠️  Docker not found (optional)"
    HAS_DOCKER=false
fi

echo ""
echo "📦 Installing OpenClaw Twins..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r src/twins/backend/requirements.txt

# Create data directories
echo "Creating data directories..."
mkdir -p data/backups data/snapshots
mkdir -p metrics/daily metrics/reports metrics/proposals

# Initialize database
echo "Initializing database..."
cd src/twins/backend
python -c "from core.database import engine, Base; Base.metadata.create_all(bind=engine)"
cd ../../..

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Configure environment variables in .env"
echo "  2. Run: make dev        # Start development server"
echo "  3. Open: http://localhost:3000"
echo ""
echo "Documentation: https://github.com/yourname/openclaw-twins#readme"
