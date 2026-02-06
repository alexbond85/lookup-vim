#!/bin/bash
# VimLookup Standalone App Build Script
#
# This script builds a fully standalone desktop application that includes:
# - The Python backend (compiled with PyInstaller)
# - The Tauri desktop shell
# - All frontend assets
#
# Prerequisites:
# - Python 3.9+ with pip
# - Rust and Cargo
# - For Intel build on Apple Silicon: Rosetta 2
#
# Usage:
#   ./build.sh                    # Full build for current architecture
#   ./build.sh --arch aarch64     # Build for Apple Silicon
#   ./build.sh --arch x86_64      # Build for Intel (requires Rosetta on M1/M2/M3/M4)
#   ./build.sh backend            # Build only Python backend
#   ./build.sh tauri              # Build only Tauri app (assumes backend is built)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default to current architecture
TARGET_ARCH=""
RUST_TARGET=""
PYINSTALLER_ARCH=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_step() {
    echo -e "${GREEN}==>${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

echo_error() {
    echo -e "${RED}Error:${NC} $1"
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --arch)
                TARGET_ARCH="$2"
                shift 2
                ;;
            backend|tauri|all)
                BUILD_CMD="$1"
                shift
                ;;
            *)
                BUILD_CMD="$1"
                shift
                ;;
        esac
    done

    # Set architecture-specific variables
    if [[ -z "$TARGET_ARCH" ]]; then
        # Default to current architecture
        TARGET_ARCH=$(uname -m)
        if [[ "$TARGET_ARCH" == "arm64" ]]; then
            TARGET_ARCH="aarch64"
        fi
    fi

    case "$TARGET_ARCH" in
        aarch64|arm64)
            TARGET_ARCH="aarch64"
            RUST_TARGET="aarch64-apple-darwin"
            PYINSTALLER_ARCH=""  # Native, no arch prefix needed
            ;;
        x86_64)
            RUST_TARGET="x86_64-apple-darwin"
            PYINSTALLER_ARCH="arch -x86_64"  # Run under Rosetta
            ;;
        *)
            echo_error "Unsupported architecture: $TARGET_ARCH"
            echo "Supported: aarch64, x86_64"
            exit 1
            ;;
    esac

    echo_step "Target architecture: $TARGET_ARCH"
}

# Get platform string for sidecar naming (uses TARGET_ARCH)
get_platform_string() {
    local os=$(uname -s)

    case "$os" in
        Darwin)
            echo "${TARGET_ARCH}-apple-darwin"
            ;;
        Linux)
            echo "${TARGET_ARCH}-unknown-linux-gnu"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "${TARGET_ARCH}-pc-windows-msvc"
            ;;
        *)
            echo_error "Unsupported operating system: $os"
            exit 1
            ;;
    esac
}

build_backend() {
    echo_step "Building Python backend with PyInstaller for ${TARGET_ARCH}..."

    # Require venv
    if [[ ! -f ".venv/bin/activate" ]]; then
        echo_error "No .venv found. Run: uv sync --all-extras"
        exit 1
    fi

    source .venv/bin/activate

    # Verify PyInstaller is available
    if ! python -c "import PyInstaller" 2>/dev/null; then
        echo_error "PyInstaller not found. Run: uv sync --all-extras"
        exit 1
    fi

    # Run PyInstaller (with arch prefix for cross-compilation via Rosetta)
    echo_step "Running PyInstaller..."
    if [[ -n "$PYINSTALLER_ARCH" ]]; then
        echo_warn "Building for $TARGET_ARCH using Rosetta..."
        $PYINSTALLER_ARCH python -m PyInstaller --clean --noconfirm vimlookup.spec
    else
        python -m PyInstaller --clean --noconfirm vimlookup.spec
    fi

    # Copy to Tauri binaries directory with platform suffix
    local platform=$(get_platform_string)
    local binary_name="vimlookup-server-${platform}"
    local dest_dir="web/tauri/src-tauri/binaries"

    echo_step "Copying binary to Tauri binaries directory..."
    mkdir -p "$dest_dir"

    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        cp "dist/vimlookup-server.exe" "${dest_dir}/${binary_name}.exe"
    else
        cp "dist/vimlookup-server" "${dest_dir}/${binary_name}"
        chmod +x "${dest_dir}/${binary_name}"
    fi

    echo_step "Backend build complete: ${dest_dir}/${binary_name}"
}

build_tauri() {
    echo_step "Building Tauri application for ${TARGET_ARCH}..."

    # Add cargo to PATH if needed
    if [[ -f "$HOME/.cargo/env" ]]; then
        source "$HOME/.cargo/env"
    elif [[ -d "$HOME/.cargo/bin" ]]; then
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    # Check if cargo is available
    if ! command -v cargo &> /dev/null; then
        echo_error "Rust/Cargo not found. Please install Rust: https://rustup.rs"
        exit 1
    fi

    # Check if tauri-cli is installed
    if ! cargo tauri --version &> /dev/null; then
        echo_step "Installing Tauri CLI..."
        cargo install tauri-cli
    fi

    # Ensure the Rust target is installed
    if ! rustup target list --installed | grep -q "$RUST_TARGET"; then
        echo_step "Installing Rust target: $RUST_TARGET"
        rustup target add "$RUST_TARGET"
    fi

    # Clear Tauri's codegen asset cache to ensure fresh frontend files are embedded.
    # Without this, Tauri may reuse stale compressed assets even when frontend files change.
    local build_dir="web/tauri/src-tauri/target/${RUST_TARGET}/release/build"
    if [[ -d "$build_dir" ]]; then
        echo_step "Clearing Tauri asset cache..."
        find "$build_dir" -path "*/tauri-*/out" -type d -exec rm -rf {} + 2>/dev/null || true
    fi

    # Build the Tauri app
    echo_step "Running Tauri build for target: $RUST_TARGET"
    pushd web/tauri > /dev/null
    cargo tauri build --target "$RUST_TARGET" --bundles app
    popd > /dev/null

    echo_step "Tauri build complete!"
    echo ""
    echo "Output locations:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  - App: web/tauri/src-tauri/target/${RUST_TARGET}/release/bundle/macos/VimLookup.app"
        echo "  - DMG: web/tauri/src-tauri/target/${RUST_TARGET}/release/bundle/dmg/VimLookup_*.dmg"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "  - AppImage: web/tauri/src-tauri/target/${RUST_TARGET}/release/bundle/appimage/"
        echo "  - Deb: web/tauri/src-tauri/target/${RUST_TARGET}/release/bundle/deb/"
    fi
}

# Main
BUILD_CMD="all"
parse_args "$@"

case "$BUILD_CMD" in
    backend)
        build_backend
        ;;
    tauri)
        build_tauri
        ;;
    all)
        build_backend
        build_tauri
        ;;
    *)
        echo "Usage: $0 [--arch aarch64|x86_64] [backend|tauri|all]"
        echo ""
        echo "Options:"
        echo "  --arch aarch64  Build for Apple Silicon (default on M1/M2/M3/M4)"
        echo "  --arch x86_64   Build for Intel (requires Rosetta on Apple Silicon)"
        echo ""
        echo "Commands:"
        echo "  backend  - Build only the Python backend with PyInstaller"
        echo "  tauri    - Build only the Tauri app (requires backend to be built first)"
        echo "  all      - Build everything (default)"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Build complete for ${TARGET_ARCH}!${NC}"
