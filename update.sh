#!/bin/bash
# =============================================================================
# WiFi Password Export Script
# Author: Mikail
# Description: Simple WiFi password backup to user's home directory
# =============================================================================

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the actual user's home directory (even when run with sudo)
if [[ -n "$SUDO_USER" ]]; then
    USER_HOME=$(eval echo ~$SUDO_USER)
else
    USER_HOME="$HOME"
fi

# Set backup file path
BACKUP_FILE="$USER_HOME/wifi_passwords_$(date +%Y%m%d_%H%M%S).txt"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (sudo)"
        echo "Please run with: sudo $0"
        exit 1
    fi
}

# Confirm with user
confirm_backup() {
    echo ""
    echo -e "${YELLOW}⚠️  This script will extract and save ALL WiFi passwords${NC}"
    echo -e "📁 Save location: ${GREEN}$BACKUP_FILE${NC}"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
}

# Extract WiFi passwords
extract_wifi_passwords() {
    log_info "Extracting WiFi passwords..."
    
    # Start the backup file
    {
        echo "============================================"
        echo "  WIFI PASSWORDS BACKUP"
        echo "============================================"
        echo "Date: $(date)"
        echo "Host: $(hostname)"
        echo "User: $(whoami)"
        echo "============================================"
        echo ""
    } > "$BACKUP_FILE"
    
    # Method 1: Using nmcli (NetworkManager)
    if command -v nmcli &>/dev/null; then
        log_info "Using nmcli to find WiFi passwords..."
        echo "--- NETWORKMANAGER WIFI CONNECTIONS ---" >> "$BACKUP_FILE"
        echo "" >> "$BACKUP_FILE"
        
        # Get all WiFi connections
        connections=$(nmcli -t -f NAME,TYPE connection show | grep -i "802-11-wireless" | cut -d':' -f1 || true)
        
        if [[ -z "$connections" ]]; then
            echo "No WiFi connections found in NetworkManager" >> "$BACKUP_FILE"
        else
            while IFS= read -r conn_name; do
                [[ -z "$conn_name" ]] && continue
                
                echo "----------------------------------------" >> "$BACKUP_FILE"
                echo "Connection: $conn_name" >> "$BACKUP_FILE"
                
                # Get SSID
                ssid=$(nmcli -t -f 802-11-wireless.ssid connection show "$conn_name" 2>/dev/null | cut -d':' -f2 || echo "Unknown")
                echo "SSID: $ssid" >> "$BACKUP_FILE"
                
                # Get password
                pwd=$(nmcli -s connection show "$conn_name" | grep "802-11-wireless-security.psk:" | awk '{print $2}' 2>/dev/null || echo "No password found")
                echo "Password: $pwd" >> "$BACKUP_FILE"
                
                # Get security type
                security=$(nmcli -t -f 802-11-wireless-security.key-mgmt connection show "$conn_name" 2>/dev/null | cut -d':' -f2 || echo "Unknown")
                echo "Security: $security" >> "$BACKUP_FILE"
                
                echo "" >> "$BACKUP_FILE"
            done <<< "$connections"
        fi
    else
        log_warning "nmcli not found - skipping NetworkManager connections"
    fi
    
    # Method 2: Using wpa_supplicant
    if [[ -f "/etc/wpa_supplicant/wpa_supplicant.conf" ]]; then
        log_info "Checking wpa_supplicant.conf..."
        echo "" >> "$BACKUP_FILE"
        echo "--- WPA_SUPPLICANT CONFIG ---" >> "$BACKUP_FILE"
        echo "" >> "$BACKUP_FILE"
        
        # Extract SSID and PSK from wpa_supplicant.conf
        grep -E "ssid=|psk=" /etc/wpa_supplicant/wpa_supplicant.conf 2>/dev/null | while read -r line; do
            echo "$line" >> "$BACKUP_FILE"
        done || echo "No wpa_supplicant entries found" >> "$BACKUP_FILE"
    fi
    
    # Method 3: Try to extract from known locations
    log_info "Checking other locations..."
    echo "" >> "$BACKUP_FILE"
    echo "--- OTHER LOCATIONS ---" >> "$BACKUP_FILE"
    echo "" >> "$BACKUP_FILE"
    
    # Check /var/lib/NetworkManager
    if [[ -d "/var/lib/NetworkManager" ]]; then
        echo "NetworkManager secrets:" >> "$BACKUP_FILE"
        find /var/lib/NetworkManager -type f -name "*.nmconnection" 2>/dev/null | while read -r file; do
            echo "File: $file" >> "$BACKUP_FILE"
            strings "$file" 2>/dev/null | grep -E "(psk|password|key)" | head -3 >> "$BACKUP_FILE" 2>/dev/null || true
            echo "" >> "$BACKUP_FILE"
        done
    fi
    
    # Summary
    echo "" >> "$BACKUP_FILE"
    echo "============================================" >> "$BACKUP_FILE"
    echo "  BACKUP COMPLETE" >> "$BACKUP_FILE"
    echo "  File: $BACKUP_FILE" >> "$BACKUP_FILE"
    echo "  Date: $(date)" >> "$BACKUP_FILE"
    echo "============================================" >> "$BACKUP_FILE"
}

# Show result
show_result() {
    echo ""
    log_success "✅ WiFi passwords saved to: $BACKUP_FILE"
    echo ""
    echo "📄 Preview:"
    echo "----------------------------------------"
    head -20 "$BACKUP_FILE"
    echo "----------------------------------------"
    echo ""
    echo "📁 Full file: $BACKUP_FILE"
    echo ""
    log_warning "⚠️  This file contains PLAINTEXT PASSWORDS!"
    echo "Keep it secure and delete when no longer needed."
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    echo ""
    echo "========================================"
    echo "  WIFI PASSWORD EXPORTER"
    echo "========================================"
    echo "Running as: $(whoami)"
    echo "Saving to: $USER_HOME/"
    echo "========================================"
    
    # Check root
    check_root
    
    # Confirm with user
    confirm_backup
    
    # Extract passwords
    extract_wifi_passwords
    
    # Show results
    show_result
}

# Run main
main "$@"

# =============================================================================
# END OF SCRIPT
# =============================================================================
