#!/bin/bash
# ============================================================
# INDAGO Forense — Instalación del servidor de captura
# Compatible con Kali Linux (Python externally-managed)
# ============================================================

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/server-venv"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════╗"
echo "║   INDAGO Forense — Setup del Servidor    ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ── Crear entorno virtual ─────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
  echo -e "${CYAN}[1/3] Creando entorno virtual Python...${NC}"
  python3 -m venv "$VENV_DIR"
  echo -e "${GREEN}✓ Entorno virtual creado en $VENV_DIR${NC}"
else
  echo -e "${GREEN}✓ Entorno virtual ya existe${NC}"
fi

source "$VENV_DIR/bin/activate"

# ── Instalar dependencias ─────────────────────────────────────
echo -e "${CYAN}[2/3] Instalando dependencias...${NC}"
pip install --upgrade pip -q
pip install flask flask-cors yt-dlp requests -q
echo -e "${GREEN}✓ Flask, yt-dlp, requests instalados${NC}"

# Playwright (opcional)
echo -e "${YELLOW}[opcional] Instalando Playwright para screenshots automáticos...${NC}"
pip install playwright -q && python3 -m playwright install chromium --with-deps 2>/dev/null \
  && echo -e "${GREEN}✓ Playwright instalado${NC}" \
  || echo -e "${YELLOW}  ↳ Playwright omitido — screenshots serán manuales${NC}"

deactivate

# ── Crear script de inicio ────────────────────────────────────
echo -e "${CYAN}[3/3] Creando script de inicio...${NC}"

cat > "$SCRIPT_DIR/start-server.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
source server-venv/bin/activate
echo ""
echo "  INDAGO Forense — Servidor de Captura Automática"
echo "  http://localhost:8765"
echo ""
python3 server.py
EOF

chmod +x "$SCRIPT_DIR/start-server.sh"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗"
echo -e "║  ✅ Instalación completada                           ║"
echo -e "║                                                      ║"
echo -e "║  Para usar la herramienta:                           ║"
echo -e "║                                                      ║"
echo -e "║  Terminal 1 (servidor):                              ║"
echo -e "║    cd ~/CLAUDE/indago && ./start-server.sh           ║"
echo -e "║                                                      ║"
echo -e "║  Terminal 2 (herramienta):                           ║"
echo -e "║    firefox ~/CLAUDE/indago/INDAGO-FORENSE.html       ║"
echo -e "╚══════════════════════════════════════════════════════╝${NC}"
