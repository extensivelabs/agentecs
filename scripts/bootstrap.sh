#!/usr/bin/env bash
# AgentECS Bootstrap Script
# Installs required development tools: uv, task, and direnv
# Supports Linux and macOS

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

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     OS=Linux;;
        Darwin*)    OS=Mac;;
        *)          OS="UNKNOWN"
    esac
    info "Detected OS: $OS"
}

# Install uv (Python package manager)
install_uv() {
    if check_command uv; then
        info "uv is already installed: $(uv --version)"
        return 0
    fi

    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add to current session PATH
    export PATH="$HOME/.cargo/bin:$PATH"

    if check_command uv; then
        info "✓ uv installed successfully: $(uv --version)"
    else
        error "Failed to install uv. Please install manually from https://github.com/astral-sh/uv"
    fi
}

# Install task (Task runner)
install_task() {
    if check_command task; then
        info "task is already installed: $(task --version)"
        return 0
    fi

    info "Installing task..."

    if [ "$OS" = "Mac" ]; then
        if check_command brew; then
            brew install go-task
        else
            warn "Homebrew not found. Installing task manually..."
            sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d
        fi
    elif [ "$OS" = "Linux" ]; then
        sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin
        export PATH="$HOME/.local/bin:$PATH"
    fi

    if check_command task; then
        info "✓ task installed successfully: $(task --version)"
    else
        error "Failed to install task. Please install manually from https://taskfile.dev"
    fi
}

# Install direnv (Environment switcher)
install_direnv() {
    if check_command direnv; then
        info "direnv is already installed: $(direnv --version)"
        return 0
    fi

    info "Installing direnv..."

    if [ "$OS" = "Mac" ]; then
        if check_command brew; then
            brew install direnv
        else
            warn "Homebrew not found. Please install direnv manually from https://direnv.net"
            return 1
        fi
    elif [ "$OS" = "Linux" ]; then
        # Try package manager first
        if check_command apt-get; then
            sudo apt-get update && sudo apt-get install -y direnv
        elif check_command dnf; then
            sudo dnf install -y direnv
        elif check_command pacman; then
            sudo pacman -S --noconfirm direnv
        else
            # Fallback to binary install
            curl -sfL https://direnv.net/install.sh | bash
        fi
    fi

    if check_command direnv; then
        info "✓ direnv installed successfully: $(direnv --version)"
    else
        warn "direnv installation may have failed. Check manually."
        return 1
    fi
}

# Setup direnv shell hook
setup_direnv_hook() {
    local shell_rc=""

    if [ -n "$BASH_VERSION" ]; then
        shell_rc="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        shell_rc="$HOME/.zshrc"
    else
        warn "Unknown shell. Please add direnv hook manually."
        info "Add this to your shell rc file: eval \"\$(direnv hook <shell>)\""
        return 1
    fi

    if [ -f "$shell_rc" ]; then
        if ! grep -q "direnv hook" "$shell_rc"; then
            info "Adding direnv hook to $shell_rc"
            echo "" >> "$shell_rc"
            echo "# direnv hook" >> "$shell_rc"
            if [ -n "$BASH_VERSION" ]; then
                echo 'eval "$(direnv hook bash)"' >> "$shell_rc"
            elif [ -n "$ZSH_VERSION" ]; then
                echo 'eval "$(direnv hook zsh)"' >> "$shell_rc"
            fi
            info "✓ direnv hook added to $shell_rc"
            warn "Please restart your shell or run: source $shell_rc"
        else
            info "direnv hook already configured in $shell_rc"
        fi
    fi
}

# Check Python version
check_python() {
    if ! check_command python3; then
        error "Python 3 not found. Please install Python 3.11 or later."
    fi

    local py_version
    py_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    info "Python version: $py_version"

    # Check if version is >= 3.11
    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)'; then
        error "Python 3.11 or later required. Found: $py_version"
    fi
}

# Main installation
main() {
    info "AgentECS Bootstrap Script"
    info "========================="

    detect_os

    if [ "$OS" = "UNKNOWN" ]; then
        error "Unsupported operating system. This script supports Linux and macOS only."
    fi

    check_python

    install_uv
    install_task
    install_direnv
    setup_direnv_hook

    echo ""
    info "========================="
    info "Bootstrap complete!"
    info "========================="
    echo ""
    info "Next steps:"
    info "1. Restart your shell or run: source ~/.bashrc (or ~/.zshrc)"
    info "2. Navigate to the project directory"
    info "3. Allow direnv: direnv allow"
    info "4. Run: task setup"
    echo ""
    info "Available tools:"
    info "  - uv:     $(which uv 2>/dev/null || echo 'not in PATH yet')"
    info "  - task:   $(which task 2>/dev/null || echo 'not in PATH yet')"
    info "  - direnv: $(which direnv 2>/dev/null || echo 'not in PATH yet')"
}

main "$@"
