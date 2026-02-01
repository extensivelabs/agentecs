#!/usr/bin/env bash
# AgentECS Development Environment Setup
# Creates virtual environment, installs dependencies, and sets up pre-commit hooks
# Run this after bootstrap.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."

    if ! check_command uv; then
        error "uv not found. Please run scripts/bootstrap.sh first"
    fi

    if ! check_command task; then
        error "task not found. Please run scripts/bootstrap.sh first"
    fi

    if ! check_command python3; then
        error "python3 not found. Please install Python 3.11 or later"
    fi

    # Check Python version
    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)'; then
        local py_version
        py_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        error "Python 3.11 or later required. Found: $py_version"
    fi

    info "✓ All prerequisites met"
}

# Create virtual environment
create_venv() {
    if [ -d .venv ]; then
        info "Virtual environment already exists"
        return 0
    fi

    info "Creating virtual environment with uv..."
    uv venv --python python3

    if [ -d .venv ]; then
        info "✓ Virtual environment created"
    else
        error "Failed to create virtual environment"
    fi
}

# Install dependencies
install_dependencies() {
    info "Installing dependencies..."

    # Activate venv for current script
    source .venv/bin/activate

    uv pip install -e ".[dev,pydantic]"

    info "✓ Dependencies installed"
}

# Setup pre-commit hooks
setup_hooks() {
    info "Setting up pre-commit hooks..."

    source .venv/bin/activate
    pre-commit install

    info "✓ Pre-commit hooks installed"
}

# Setup .env file
setup_env() {
    if [ -f .env ]; then
        info ".env file already exists"
        return 0
    fi

    if [ -f .env.template ]; then
        info "Creating .env from template..."
        cp .env.template .env
        info "✓ Created .env file (customize as needed)"
    else
        warn ".env.template not found, skipping .env creation"
    fi
}

# Setup direnv
setup_direnv() {
    if ! check_command direnv; then
        warn "direnv not found. Environment won't auto-activate"
        warn "Install with: brew install direnv (Mac) or sudo apt install direnv (Linux)"
        return 1
    fi

    if [ -f .envrc ]; then
        info "Allowing direnv for this directory..."
        direnv allow
        info "✓ direnv configured"
    else
        warn ".envrc not found"
    fi
}

# Verify installation
verify_installation() {
    info "Verifying installation..."

    source .venv/bin/activate

    # Check Python packages
    local packages=("pytest" "ruff" "mypy" "pre-commit")
    for pkg in "${packages[@]}"; do
        if python -c "import $pkg" 2>/dev/null; then
            info "✓ $pkg installed"
        else
            warn "✗ $pkg not found"
        fi
    done

    # Run a simple test
    info "Running quick sanity check..."
    if python -c "import agentecs; print(f'AgentECS {agentecs.__version__} loaded')"; then
        info "✓ AgentECS package importable"
    else
        warn "✗ AgentECS package not importable"
    fi
}

# Main setup
main() {
    info "AgentECS Development Environment Setup"
    info "======================================"

    # Ensure we're in project root
    if [ ! -f "pyproject.toml" ]; then
        error "pyproject.toml not found. Please run this script from the project root"
    fi

    check_prerequisites
    create_venv
    install_dependencies
    setup_hooks
    setup_env
    setup_direnv

    echo ""
    info "======================================"
    info "Setup complete!"
    info "======================================"
    echo ""

    verify_installation

    echo ""
    info "Next steps:"
    info "1. Activate the environment:"
    if check_command direnv; then
        info "   - direnv will auto-activate when you cd into the directory"
        info "   - Or manually: source .venv/bin/activate"
    else
        info "   source .venv/bin/activate"
    fi
    info "2. Run tests: task test"
    info "3. See available commands: task --list"
    info "4. Read CONTRIBUTING.md for development guidelines"
    echo ""
}

main "$@"
