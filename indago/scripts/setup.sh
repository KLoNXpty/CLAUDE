#!/bin/bash
# INDAGO Evidence Capture Platform - Setup Script

set -e

echo "=============================================="
echo " INDAGO Evidence Capture Platform Setup"
echo " Digital Evidence Preservation Platform"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check Docker
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker first."
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "Docker Compose is not installed."
fi

info "Starting INDAGO services..."

# Navigate to docker directory
cd "$(dirname "$0")/../docker"

# Start infrastructure services first
info "Starting database and cache services..."
docker compose up -d postgres redis minio

# Wait for PostgreSQL
info "Waiting for PostgreSQL to be ready..."
timeout 60 bash -c 'until docker exec indago-postgres pg_isready -U indago -d indago_db; do sleep 2; done'
success "PostgreSQL ready"

# Wait for Redis
info "Waiting for Redis to be ready..."
timeout 30 bash -c 'until docker exec indago-redis redis-cli ping | grep -q PONG; do sleep 1; done'
success "Redis ready"

# Start all services
info "Starting all INDAGO services..."
docker compose up -d

# Wait for backend
info "Waiting for backend API..."
timeout 60 bash -c 'until curl -sf http://localhost:8000/api/health > /dev/null; do sleep 3; done'
success "Backend API ready"

echo ""
echo "=============================================="
echo -e "${GREEN} INDAGO Evidence Capture Platform is running!${NC}"
echo "=============================================="
echo ""
echo " Service URLs:"
echo "  📋 Web Interface:    http://localhost:3000"
echo "  🔌 API:              http://localhost:8000/api/v1"
echo "  📚 API Docs:         http://localhost:8000/api/docs"
echo "  💾 MinIO Console:    http://localhost:9001"
echo ""
echo " Default Credentials:"
echo "  Username: admin"
echo "  Password: IndagoAdmin2024!"
echo ""
echo " To create an admin user, run:"
echo "  docker exec indago-backend python scripts/create_admin.py"
echo ""
