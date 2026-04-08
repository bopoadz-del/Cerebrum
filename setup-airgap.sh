#!/bin/bash
# =============================================================================
# Cerebrum Air-Gapped Deployment Setup
# One-command setup for offline/local deployment
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CEREBRUM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$CEREBRUM_DIR/data"
MODELS_DIR="$DATA_DIR/models"
OLLAMA_MODELS="gemma3:270m nomic-embed-text"

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is required but not installed."
        exit 1
    fi
    print_success "$1 is installed"
}

# =============================================================================
# Pre-flight Checks
# =============================================================================

print_header "Cerebrum Air-Gapped Setup"
echo ""

echo "Checking prerequisites..."
check_command docker
check_command docker-compose
check_command curl

echo ""

# =============================================================================
# Directory Setup
# =============================================================================

print_header "Setting up directories"

mkdir -p "$DATA_DIR"/{uploads,documents,models,backups}
mkdir -p "$CEREBRUM_DIR/init-scripts"

print_success "Created data directories"

# =============================================================================
# Environment Configuration
# =============================================================================

print_header "Environment Configuration"

ENV_FILE="$CEREBRUM_DIR/.env.airgap"

if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << EOF
# Cerebrum Air-Gapped Environment Configuration
# Generated on $(date)

# Database
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)

# Security
SECRET_KEY=$(openssl rand -base64 64 | tr -dc 'a-zA-Z0-9' | head -c 50)

# Local Paths
DATA_PATH=$DATA_DIR
UPLOADS_PATH=$DATA_DIR/uploads
EOF
    print_success "Created $ENV_FILE"
    print_warning "Please review and customize $ENV_FILE before starting"
else
    print_warning "$ENV_FILE already exists, skipping creation"
fi

# =============================================================================
# Download Models (if not present)
# =============================================================================

print_header "Model Download"

echo "Checking for Ollama models..."
echo ""
echo "Models will be downloaded on first run."
echo "This may take 10-30 minutes depending on your connection."
echo ""
print_warning "Ensure you have at least 2GB free disk space"

# =============================================================================
# Docker Images
# =============================================================================

print_header "Pulling Docker Images"

# Pull images that will be needed
echo "Pulling required images..."
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull ollama/ollama:latest

print_success "Docker images ready"

# =============================================================================
# Build Application Images
# =============================================================================

print_header "Building Application Images"

echo "Building backend image..."
docker-compose -f "$CEREBRUM_DIR/docker-compose.airgap.yml" build api

echo "Building frontend image..."
docker-compose -f "$CEREBRUM_DIR/docker-compose.airgap.yml" build frontend

print_success "Application images built"

# =============================================================================
# Database Initialization
# =============================================================================

print_header "Database Initialization"

cat > "$CEREBRUM_DIR/init-scripts/01-init.sql" << 'EOF'
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS agent;
CREATE SCHEMA IF NOT EXISTS documents;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA agent TO cerebrum;
GRANT ALL PRIVILEGES ON SCHEMA documents TO cerebrum;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA agent TO cerebrum;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA documents TO cerebrum;
EOF

print_success "Created database initialization script"

# =============================================================================
# Startup Script
# =============================================================================

print_header "Creating Startup Script"

cat > "$CEREBRUM_DIR/start-airgap.sh" << 'EOF'
#!/bin/bash
# Start Cerebrum in air-gapped mode

set -e

CEREBRUM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Cerebrum (Air-Gapped Mode)..."
echo ""

# Load environment
export $(grep -v '^#' "$CEREBRUM_DIR/.env.airgap" | xargs)

# Start services
docker-compose -f "$CEREBRUM_DIR/docker-compose.airgap.yml" up -d

echo ""
echo "Waiting for services to be ready..."
sleep 10

# Wait for Ollama
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    echo "  Waiting for Ollama..."
    sleep 5
done

echo ""
echo "Pulling required models..."
# Pull models if not present
curl -s http://localhost:11434/api/tags | grep -q "gemma3:270m" || curl -s -X POST http://localhost:11434/api/pull -d '{"name": "gemma3:270m"}' > /dev/null 2>&1 &
curl -s http://localhost:11434/api/tags | grep -q "nomic-embed-text" || curl -s -X POST http://localhost:11434/api/pull -d '{"name": "nomic-embed-text"}' > /dev/null 2>&1 &

echo ""
echo "============================================"
echo "Cerebrum is starting up!"
echo "============================================"
echo ""
echo "Services:"
echo "  Frontend:  http://localhost"
echo "  API:       http://localhost:8000"
echo "  Ollama:    http://localhost:11434"
echo ""
echo "Model download is in progress (background)."
echo "Check status: curl http://localhost:11434/api/tags"
echo ""
echo "To stop: ./stop-airgap.sh"
echo ""
EOF

chmod +x "$CEREBRUM_DIR/start-airgap.sh"
print_success "Created start-airgap.sh"

# =============================================================================
# Stop Script
# =============================================================================

cat > "$CEREBRUM_DIR/stop-airgap.sh" << 'EOF'
#!/bin/bash
# Stop Cerebrum air-gapped deployment

CEREBRUM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping Cerebrum..."
docker-compose -f "$CEREBRUM_DIR/docker-compose.airgap.yml" down

echo "Cerebrum stopped."
EOF

chmod +x "$CEREBRUM_DIR/stop-airgap.sh"
print_success "Created stop-airgap.sh"

# =============================================================================
# Backup Script
# =============================================================================

cat > "$CEREBRUM_DIR/backup-airgap.sh" << EOF
#!/bin/bash
# Backup Cerebrum data

BACKUP_DIR="$DATA_DIR/backups"
TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="\$BACKUP_DIR/cerebrum_backup_\$TIMESTAMP.tar.gz"

mkdir -p "\$BACKUP_DIR"

echo "Creating backup: \$BACKUP_FILE"

# Backup database
docker exec cerebrum-postgres pg_dump -U cerebrum cerebrum > "\$BACKUP_DIR/db_\$TIMESTAMP.sql"

# Backup uploads and data
tar -czf "\$BACKUP_FILE" -C "$DATA_DIR" uploads documents

# Add database dump to archive
tar -rf "\$BACKUP_FILE" -C "\$BACKUP_DIR" "db_\$TIMESTAMP.sql"
gzip "\$BACKUP_FILE"

rm "\$BACKUP_DIR/db_\$TIMESTAMP.sql"

echo "Backup complete: \$BACKUP_FILE"
EOF

chmod +x "$CEREBRUM_DIR/backup-airgap.sh"
print_success "Created backup-airgap.sh"

# =============================================================================
# Summary
# =============================================================================

print_header "Setup Complete!"

echo ""
echo "Your air-gapped Cerebrum deployment is ready."
echo ""
echo "Next steps:"
echo ""
echo "1. Review configuration:"
echo "   cat .env.airgap"
echo ""
echo "2. Start Cerebrum:"
echo "   ./start-airgap.sh"
echo ""
echo "3. Access the application:"
echo "   Frontend: http://localhost"
echo "   API:      http://localhost:8000"
echo ""
echo "4. To stop:"
echo "   ./stop-airgap.sh"
echo ""
echo "5. To backup data:"
echo "   ./backup-airgap.sh"
echo ""
print_warning "Note: Model downloads (~500MB) will happen on first start"
echo ""
