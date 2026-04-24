#!/bin/bash

set -e

REPO_NAME="terminal-software"
BASE_URL="https://raw.githubusercontent.com/bobbythedemon/terminal-software/main"
PKG_VERSION="1.0.0"
PKG_NAME="terminal-software"

check_deps() {
    if ! command -v curl &> /dev/null; then
        echo "Installing curl..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y curl
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y curl
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm curl
        elif command -v apk &> /dev/null; then
            sudo apk add curl
        else
            echo "Error: Cannot install curl. Please install it manually."
            exit 1
        fi
    fi
}

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    elif [ -f /etc/redhat-release ]; then
        DISTRO="fedora"
    elif [ -f /etc/arch-release ]; then
        DISTRO="arch"
    elif [ -f /etc/alpine-release ]; then
        DISTRO="alpine"
    else
        DISTRO="unknown"
    fi
}

install_package() {
    local deb_file="/tmp/${PKG_NAME}.deb"
    local deb_url="${BASE_URL}/terminal-software.bin"
    
    echo "Downloading ${PKG_NAME} v${PKG_VERSION}..."
    curl -fsSL "$deb_url" -o "$deb_file" || {
        echo "Error: Failed to download package"
        exit 1
    }
    
    echo "Installing package..."
    sudo dpkg -i "$deb_file" || sudo apt-get install -f -y
    
    rm -f "$deb_file"
    echo "Installation complete!"
}

install_other() {
    echo "Installing dependencies..."
    
    case "$DISTRO" in
        debian|ubuntu|linuxmint)
            sudo apt-get update
            sudo apt-get install -y python3 python3-curses
            ;;
        fedora|rhel|centos)
            sudo dnf install -y python3
            ;;
        arch)
            sudo pacman -S --noconfirm python python-curses
            ;;
        alpine)
            sudo apk add python3 py3-curses
            ;;
        *)
            echo "Please install python3 and python3-curses manually."
            ;;
    esac
    
    install_package
}

uninstall() {
    echo "Removing ${PKG_NAME}..."
    sudo dpkg -r "$PKG_NAME"
    echo "Uninstall complete!"
}

show_help() {
    echo "Terminal Software Installer v1.0.0"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install    Install terminal-software (default)"
    echo "  uninstall  Remove terminal-software"
    echo "  help       Show this help message"
    echo ""
    echo "Quick install:"
    echo "  curl -sSL ${BASE_URL}/install.sh | bash"
}

main() {
    echo "=========================================="
    echo "  Terminal Software Package Installer"
    echo "=========================================="
    echo ""
    
    check_deps
    detect_distro
    
    case "${1:-install}" in
        install)
            install_other
            ;;
        uninstall)
            uninstall
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"