#!/bin/bash
# Build script for Port Monitor cross-platform executables

set -e

echo "🚀 Port Monitor Build Script"
echo "============================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

print_status "Docker found"

# Build target selection
TARGET=${1:-linux}

case $TARGET in
    linux)
        print_status "Building Linux executable..."
        print_warning "Using simple Dockerfile for faster build..."
        docker build -f Dockerfile.simple -t port-monitor:linux .
        docker create --name temp-linux port-monitor:linux
        docker cp temp-linux:/app/dist ./dist-linux
        docker rm temp-linux
        print_status "Linux build complete! Output: ./dist-linux/"
        ;;
    
    windows)
        print_error "Windows build via Docker is not recommended."
        echo ""
        echo "Docker + Wine cross-compilation is:"
        echo "  • Very slow (15-30 minutes)"
        echo "  • Unreliable"
        echo "  • Produces larger executables"
        echo ""
        print_warning "RECOMMENDED: Build on Windows natively"
        echo ""
        echo "On a Windows machine, run:"
        echo "  pip install -r requirements.txt pyinstaller"
        echo "  pyinstaller --windowed --icon=icon.ico --name \"Port Monitor\" main.py"
        echo ""
        echo "See BUILD.md for detailed instructions."
        echo ""
        read -p "Continue with Docker Wine build anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Build cancelled. Use native Windows build instead."
            exit 0
        fi
        
        print_warning "Building Windows executable (this will take 15-30 minutes)..."
        docker build --target windows-build -t port-monitor:windows .
        docker create --name temp-windows port-monitor:windows
        docker cp temp-windows:/app/dist ./dist-windows
        docker rm temp-windows
        print_status "Windows build complete! Output: ./dist-windows/"
        ;;
    
    clean)
        print_status "Cleaning build artifacts..."
        rm -rf dist-linux dist-windows
        docker rmi port-monitor:linux port-monitor:windows 2>/dev/null || true
        print_status "Clean complete!"
        ;;
    
    *)
        print_error "Unknown target: $TARGET"
        echo ""
        echo "Usage: ./build.sh [target]"
        echo ""
        echo "Targets:"
        echo "  linux     - Build Linux executable (default, recommended)"
        echo "  windows   - Build Windows .exe (NOT RECOMMENDED via Docker)"
        echo "  clean     - Remove build artifacts and images"
        echo ""
        echo "Examples:"
        echo "  ./build.sh           # Build Linux executable"
        echo "  ./build.sh linux     # Build Linux executable"
        echo "  ./build.sh clean     # Clean up"
        echo ""
        echo "For Windows builds, see BUILD.md for native build instructions."
        exit 1
        ;;
esac

echo ""
print_status "Build process completed successfully!"
