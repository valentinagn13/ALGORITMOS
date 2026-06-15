#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  Configuración del proyecto MIP/IIT"
echo "=========================================="

# --- 1. Verificar Python ---
PYTHON_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2 || true)
if [ -z "$PYTHON_VERSION" ]; then
    echo "[ERROR] Python3 no encontrado. Instala Python 3.11+ primero."
    exit 1
fi
echo "[OK] Python $PYTHON_VERSION detectado."

# --- 2. Crear entorno virtual ---
if [ ! -d "venv" ]; then
    echo "[INFO] Creando entorno virtual..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "[OK] Entorno virtual listo."

# --- 3. Instalar uv ---
if ! command -v uv &>/dev/null; then
    echo "[INFO] Instalando uv..."
    pip install uv
fi
echo "[OK] uv instalado."

# --- 4. Instalar dependencias Python globales ---
echo "[INFO] Instalando dependencias Python (requirements.txt)..."
pip install -r requirements.txt

# --- 5. Sincronizar subproyectos con uv ---
echo "[INFO] Sincronizando QNodes..."
cd QNodes
uv sync
cd ..

echo "[INFO] Sincronizando GeoMIP/Method2..."
cd GeoMIP/src/Method2_Dynamic_Programming_Reformulation
uv sync
cd ../../..

# --- 6. Dependencias Node.js (opencode) ---
if [ -f "package.json" ]; then
    echo "[INFO] Instalando dependencias Node.js..."
    npm install
fi

echo ""
echo "=========================================="
echo "  Configuración completada exitosamente"
echo "=========================================="
echo ""
echo "Para activar el entorno:"
echo "  source venv/bin/activate"
echo ""
echo "Para ejecutar QNodes:"
echo "  cd QNodes && uv run exec.py"
echo ""
echo "Para ejecutar GeoMIP/Method2:"
echo "  cd GeoMIP/src/Method2_Dynamic_Programming_Reformulation && uv run exec.py"
