#!/bin/bash
# ============================================================
# INDAGO Evidence Capture Platform — Instalación local (demo)
# Requisitos: Python 3.10+ y Node.js 18+
# ============================================================
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════╗"
echo "║   INDAGO Evidence Capture Platform       ║"
echo "║   Instalación modo demo                  ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ── Verificar requisitos ──────────────────────────────────────
check_cmd() {
  command -v "$1" &>/dev/null || { echo -e "${RED}✗ '$1' no encontrado. Instálalo primero.${NC}"; exit 1; }
}
check_cmd python3
check_cmd node
check_cmd npm

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
NODE_VER=$(node -e "console.log(process.versions.node.split('.')[0])")

echo -e "${GREEN}✓ Python $PYTHON_VER${NC}"
echo -e "${GREEN}✓ Node.js $NODE_VER${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Backend ───────────────────────────────────────────────────
echo -e "\n${CYAN}[1/4] Instalando dependencias del backend...${NC}"
cd backend

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements-demo.txt -q

# Playwright (opcional — si falla, las capturas usan modo HTTP)
echo -e "${YELLOW}[opcional] Instalando Playwright Chromium para screenshots...${NC}"
pip install playwright -q && python3 -m playwright install chromium --with-deps 2>/dev/null \
  || echo -e "${YELLOW}  ↳ Playwright omitido — capturas funcionarán sin screenshots${NC}"

deactivate
cd ..

# ── Frontend ──────────────────────────────────────────────────
echo -e "\n${CYAN}[2/4] Instalando dependencias del frontend...${NC}"
cd frontend
npm install --legacy-peer-deps -q
cd ..

# ── Scripts de inicio ─────────────────────────────────────────
echo -e "\n${CYAN}[3/4] Creando scripts de inicio...${NC}"

cat > start-backend.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/backend"
source venv/bin/activate
export DATABASE_URL="sqlite+aiosqlite:////tmp/indago_demo.db"
export EVIDENCE_STORAGE_PATH="/tmp/indago_evidence"
export SECRET_KEY="demo-secret-key-change-in-production"
export DEBUG=true
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
EOF

cat > start-frontend.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/frontend"
export NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"
npm run dev
EOF

chmod +x start-backend.sh start-frontend.sh

# ── Listo ─────────────────────────────────────────────────────
echo -e "\n${CYAN}[4/4] Instalación completada.${NC}"
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗"
echo -e "║  Para iniciar la plataforma, abre 2 terminales:      ║"
echo -e "║                                                      ║"
echo -e "║  Terminal 1 (backend):                               ║"
echo -e "║    ./start-backend.sh                                ║"
echo -e "║                                                      ║"
echo -e "║  Terminal 2 (frontend):                              ║"
echo -e "║    ./start-frontend.sh                               ║"
echo -e "║                                                      ║"
echo -e "║  Luego abre:  http://localhost:3000                  ║"
echo -e "║                                                      ║"
echo -e "║  Credenciales demo:                                  ║"
echo -e "║    admin         /  admin123                         ║"
echo -e "║    investigator  /  investigator123                  ║"
echo -e "╚══════════════════════════════════════════════════════╝${NC}"
