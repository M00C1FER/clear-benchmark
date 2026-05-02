#!/usr/bin/env bash
# CLEAR Benchmark — install wizard
# Supports: Linux, WSL, Termux (Android)
set -euo pipefail

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
prompt()  { echo -e "${YELLOW}[INPUT]${NC} $*"; }

detect_platform() {
    if [ -n "${TERMUX_VERSION:-}" ] || [ -d "/data/data/com.termux" ]; then echo "termux"
    elif grep -qi microsoft /proc/version 2>/dev/null; then echo "wsl"
    else echo "linux"; fi
}

install_deps_system() {
    local plat="$1"
    case "$plat" in
        termux) pkg update -y; pkg install -y python git ;;
        wsl|linux)
            if command -v apt-get &>/dev/null; then
                sudo apt-get update -qq
                sudo apt-get install -y python3 python3-venv python3-pip git
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y python3 python3-virtualenv git
            elif command -v pacman &>/dev/null; then
                sudo pacman -Sy --noconfirm python git
            fi ;;
    esac
}

PLATFORM=$(detect_platform)
INSTALL_DIR="${HOME}/.local/share/clear-benchmark"
VENV_DIR="${INSTALL_DIR}/.venv"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║        CLEAR Benchmark  v1.0.0           ║"
echo "║  AI agent composite performance scoring  ║"
echo "╚══════════════════════════════════════════╝"
echo ""
info "Platform: $PLATFORM"
info "CLEAR = Cost · Latency · Efficiency · Assurance · Reliability"

install_deps_system "$PLATFORM"

info "Installing psutil for resource monitoring..."
mkdir -p "$INSTALL_DIR"
if [ "$PLATFORM" = "termux" ]; then
    python -m venv "$VENV_DIR"
else
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install . -q

ENV_FILE="${INSTALL_DIR}/.env"
touch "$ENV_FILE"; chmod 600 "$ENV_FILE"

echo ""
echo "────────────────────────────────────────────"
echo " Benchmark Configuration (all optional)"
echo "────────────────────────────────────────────"

prompt "SQLite results database path (default: ~/.local/share/clear-benchmark/benchmarks.db):"
read -r db_path
if [ -n "$db_path" ]; then echo "CLEAR_BENCHMARK_DB=${db_path}" >> "$ENV_FILE"; fi

prompt "CLEAR Benchmark home directory (default: $INSTALL_DIR):"
read -r home_path
if [ -n "$home_path" ]; then echo "CLEAR_BENCHMARK_HOME=${home_path}" >> "$ENV_FILE"; fi

success "Config saved to $ENV_FILE"

WRAPPER="${HOME}/.local/bin/clear-bench"
mkdir -p "$(dirname "$WRAPPER")"
cat > "$WRAPPER" << WRAPEOF
#!/usr/bin/env bash
set -a; [ -f "${ENV_FILE}" ] && . "${ENV_FILE}"; set +a
exec "${VENV_DIR}/bin/clear-bench" "\$@"
WRAPEOF
chmod +x "$WRAPPER"

echo ""
success "Installation complete!"
echo ""
echo "  Run all tiers:   clear-bench"
echo "  Run one tier:    clear-bench --tier 2"
echo "  JSON output:     clear-bench --json"
echo "  HTML report:     clear-bench --html"
echo "  Docs:            https://github.com/M00C1FER/clear-benchmark"
