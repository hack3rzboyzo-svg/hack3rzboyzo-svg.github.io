#!/bin/bash
# =============================================================================
# WiFi Backup Script - Version 2.0
# Author: Mikail
# Repository: https://github.com/hack3rzboyzo-svg/hack3rzboyzo-svg.github.io
# =============================================================================

# Exit on error, undefined variables, and pipe failures
set -euo pipefail

# =============================================================================
# COLOR DEFINITIONS
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# =============================================================================
# CONFIGURATION
# =============================================================================
BACKUP_DIR="/root/wifi_backup_$(date +%Y%m%d_%H%M%S)"
ENCRYPT_BACKUP=false
ENCRYPT_PASSWORD=""
EXPORT_FORMAT="txt" # txt, json, csv

# =============================================================================
# FUNCTIONS
# =============================================================================

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${CYAN}▶ $1${NC}"
}

# Check if script is running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (sudo)"
        echo "Please run with: sudo $0"
        exit 1
    else
        log_success "Running as root user"
    fi
}

# Display warning and get confirmation
confirm_backup() {
    echo ""
    echo -e "${YELLOW}⚠️  WARNING: You are about to backup WiFi passwords${NC}"
    echo "This script will save passwords locally on your system"
    echo -e "${YELLOW}Make sure you trust this source before continuing${NC}"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
}

# Check dependencies
check_dependencies() {
    local deps=()
    
    if ! command -v nmcli &>/dev/null; then
        deps+=("NetworkManager (nmcli)")
    fi
    
    if ! command -v wpa_passphrase &>/dev/null; then
        deps+=("wpa_supplicant (wpa_passphrase)")
    fi
    
    if ! command -v iwconfig &>/dev/null; then
        deps+=("wireless-tools (iwconfig)")
    fi
    
    if [[ ${#deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${deps[*]}"
        echo "Install with:"
        echo "  Debian/Ubuntu: apt-get install network-manager wireless-tools wpasupplicant"
        echo "  RHEL/CentOS: yum install NetworkManager wireless-tools wpa_supplicant"
        echo "  Arch: pacman -S networkmanager wireless-tools wpa_supplicant"
        exit 1
    fi
    
    log_success "All dependencies found"
}

# Create backup directory
create_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    log_success "Created backup directory: $BACKUP_DIR"
}

# Backup WiFi passwords from NetworkManager
backup_nm_connections() {
    log_header "Backing up NetworkManager connections..."
    
    local nm_dir="/etc/NetworkManager/system-connections"
    local nm_backup="$BACKUP_DIR/networkmanager"
    
    if [[ -d "$nm_dir" ]]; then
        mkdir -p "$nm_backup"
        
        # Copy all connection files
        cp -r "$nm_dir"/* "$nm_backup/" 2>/dev/null || true
        
        # Extract passwords from each connection
        for conn_file in "$nm_dir"/*; do
            if [[ -f "$conn_file" ]]; then
                local conn_name=$(basename "$conn_file")
                local output_file="$nm_backup/${conn_name}.password.txt"
                
                echo "=== Connection: $conn_name ===" > "$output_file"
                echo "File: $conn_file" >> "$output_file"
                echo "Modified: $(stat -c %y "$conn_file" 2>/dev/null || stat -f %Sm "$conn_file" 2>/dev/null)" >> "$output_file"
                echo "---" >> "$output_file"
                
                # Extract password if it exists
                if grep -q "psk=" "$conn_file" 2>/dev/null; then
                    local psk=$(grep "^psk=" "$conn_file" | cut -d'=' -f2)
                    echo "Password (PSK): $psk" >> "$output_file"
                elif grep -q "password=" "$conn_file" 2>/dev/null; then
                    local pwd=$(grep "^password=" "$conn_file" | cut -d'=' -f2)
                    echo "Password: $pwd" >> "$output_file"
                fi
                
                # Extract SSID
                if grep -q "ssid=" "$conn_file" 2>/dev/null; then
                    local ssid=$(grep "^ssid=" "$conn_file" | cut -d'=' -f2)
                    echo "SSID: $ssid" >> "$output_file"
                fi
                
                # Extract connection type
                if grep -q "type=" "$conn_file" 2>/dev/null; then
                    local type=$(grep "^type=" "$conn_file" | cut -d'=' -f2)
                    echo "Type: $type" >> "$output_file"
                fi
                
                # Extract MAC address if present
                if grep -q "mac-address=" "$conn_file" 2>/dev/null; then
                    local mac=$(grep "^mac-address=" "$conn_file" | cut -d'=' -f2)
                    echo "MAC Address: $mac" >> "$output_file"
                fi
            fi
        done
        
        log_success "NetworkManager connections backed up to $nm_backup"
    else
        log_warning "NetworkManager directory not found: $nm_dir"
    fi
}

# Backup WiFi passwords using nmcli
backup_nmcli() {
    log_header "Backing up via nmcli..."
    
    local nmcli_backup="$BACKUP_DIR/nmcli_backup.txt"
    local nmcli_json="$BACKUP_DIR/nmcli_backup.json"
    
    echo "=== NMCLI WiFi Profile Backup ===" > "$nmcli_backup"
    echo "Date: $(date)" >> "$nmcli_backup"
    echo "Host: $(hostname)" >> "$nmcli_backup"
    echo "----------------------------------------" >> "$nmcli_backup"
    echo "" >> "$nmcli_backup"
    
    # Get all connections
    local connections=$(nmcli -t -f NAME,TYPE connection show | grep -i "802-11-wireless" | cut -d':' -f1 || true)
    
    if [[ -z "$connections" ]]; then
        log_warning "No WiFi connections found in nmcli"
        echo "No WiFi connections found" >> "$nmcli_backup"
    else
        echo "Found WiFi connections:" >> "$nmcli_backup"
        
        # Initialize JSON array for structured output
        echo "[" > "$nmcli_json"
        local first=true
        
        while IFS= read -r conn_name; do
            [[ -z "$conn_name" ]] && continue
            
            echo "" >> "$nmcli_backup"
            echo "=== Profile: $conn_name ===" >> "$nmcli_backup"
            echo "---" >> "$nmcli_backup"
            
            # Get connection details
            nmcli connection show "$conn_name" >> "$nmcli_backup" 2>&1 || true
            
            # Get password separately (if exists)
            local pwd=$(nmcli -s connection show "$conn_name" | grep "802-11-wireless-security.psk:" | awk '{print $2}' 2>/dev/null || true)
            if [[ -n "$pwd" ]]; then
                echo "PASSWORD: $pwd" >> "$nmcli_backup"
            fi
            
            # Get SSID
            local ssid=$(nmcli -t -f 802-11-wireless.ssid connection show "$conn_name" 2>/dev/null | cut -d':' -f2 || true)
            if [[ -n "$ssid" ]]; then
                echo "SSID: $ssid" >> "$nmcli_backup"
            fi
            
            # Get security type
            local security=$(nmcli -t -f 802-11-wireless-security.key-mgmt connection show "$conn_name" 2>/dev/null | cut -d':' -f2 || true)
            if [[ -n "$security" ]]; then
                echo "Security: $security" >> "$nmcli_backup"
            fi
            
            # Export to JSON
            if [[ "$first" == true ]]; then
                first=false
            else
                echo "," >> "$nmcli_json"
            fi
            
            cat >> "$nmcli_json" << EOF
{
  "name": "$conn_name",
  "ssid": "$ssid",
  "password": "$pwd",
  "security": "$security",
  "backup_date": "$(date -Iseconds)"
}
EOF
        done <<< "$connections"
        
        echo "]" >> "$nmcli_json"
    fi
    
    log_success "nmcli backup created: $nmcli_backup"
    log_info "JSON export: $nmcli_json"
}

# Backup wpa_supplicant configuration
backup_wpa_supplicant() {
    log_header "Backing up wpa_supplicant configuration..."
    
    local wpa_conf="/etc/wpa_supplicant/wpa_supplicant.conf"
    local wpa_backup="$BACKUP_DIR/wpa_supplicant"
    
    mkdir -p "$wpa_backup"
    
    if [[ -f "$wpa_conf" ]]; then
        cp "$wpa_conf" "$wpa_backup/"
        log_success "wpa_supplicant.conf backed up"
    else
        # Look for other possible locations
        for loc in /etc/wpa_supplicant/*.conf /etc/wpa_supplicant.conf /etc/wpa2_supplicant.conf; do
            if [[ -f "$loc" ]]; then
                cp "$loc" "$wpa_backup/"
                log_success "Found and backed up: $loc"
            fi
        done
    fi
    
    # Also backup any wireless configs
    if [[ -d "/etc/wireless" ]]; then
        cp -r "/etc/wireless" "$wpa_backup/" 2>/dev/null || true
        log_success "Wireless configs backed up"
    fi
}

# Get currently connected WiFi info
get_current_connections() {
    log_header "Getting current WiFi connections..."
    
    local current_backup="$BACKUP_DIR/current_connections.txt"
    
    echo "=== CURRENT WIFI CONNECTIONS ===" > "$current_backup"
    echo "Date: $(date)" >> "$current_backup"
    echo "Host: $(hostname)" >> "$current_backup"
    echo "----------------------------------------" >> "$current_backup"
    echo "" >> "$current_backup"
    
    # Get current connection
    echo "Current Active Connection:" >> "$current_backup"
    nmcli -t -f NAME,TYPE,DEVICE connection show --active | grep -i "802-11-wireless" >> "$current_backup" 2>/dev/null || echo "None" >> "$current_backup"
    echo "" >> "$current_backup"
    
    # Get available networks
    echo "Available WiFi Networks (with signal strength):" >> "$current_backup"
    nmcli -t -f SSID,SIGNAL,SECURITY dev wifi list >> "$current_backup" 2>/dev/null || echo "Unable to scan" >> "$current_backup"
    
    # Get interface info
    echo "" >> "$current_backup"
    echo "Wireless Interface Info:" >> "$current_backup"
    iwconfig 2>/dev/null >> "$current_backup" || true
    
    log_success "Current connections saved to $current_backup"
}

# Extract Wi-Fi passwords from known files
extract_from_known_files() {
    log_header "Extracting passwords from known files..."
    
    local extracted_backup="$BACKUP_DIR/extracted_passwords.txt"
    
    echo "=== EXTRACTED WIFI PASSWORDS ===" > "$extracted_backup"
    echo "Date: $(date)" >> "$extracted_backup"
    echo "----------------------------------------" >> "$extracted_backup"
    echo "" >> "$extracted_backup"
    
    # Try to extract from /var/lib/NetworkManager
    if [[ -d "/var/lib/NetworkManager" ]]; then
        echo "NetworkManager secrets:" >> "$extracted_backup"
        find /var/lib/NetworkManager -type f -name "*.nmconnection" 2>/dev/null | while read -r file; do
            echo "--- $file ---" >> "$extracted_backup"
            strings "$file" | grep -E "(psk|password|key)" | head -5 >> "$extracted_backup" 2>/dev/null || true
            echo "" >> "$extracted_backup"
        done
    fi
    
    # Try to extract from gnome-keyring
    if command -v secret-tool &>/dev/null; then
        echo "GNOME Keyring entries:" >> "$extracted_backup"
        secret-tool search --all wifi 2>/dev/null >> "$extracted_backup" || true
    fi
    
    log_success "Extracted passwords saved to $extracted_backup"
}

# Create summary file
create_summary() {
    log_header "Creating summary file..."
    
    local summary="$BACKUP_DIR/README.txt"
    
    cat > "$summary" << EOF
===========================================
WIFI BACKUP SUMMARY
===========================================
Backup Date: $(date)
Hostname: $(hostname)
OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2 2>/dev/null || echo "Unknown")
User: $(whoami)

===========================================
BACKUP CONTENTS
===========================================

This backup contains the following WiFi information:

1. NetworkManager connections (/etc/NetworkManager/system-connections/)
   Location: ./networkmanager/
   Contains: Connection files and extracted passwords

2. nmcli profiles and passwords
   Location: ./nmcli_backup.txt
   Contains: Full connection details with passwords

3. wpa_supplicant configuration
   Location: ./wpa_supplicant/
   Contains: wpa_supplicant.conf files

4. Current connection status
   Location: ./current_connections.txt
   Contains: Active connections and available networks

5. Extracted passwords
   Location: ./extracted_passwords.txt
   Contains: Passwords extracted from various sources

6. JSON export
   Location: ./nmcli_backup.json
   Contains: Machine-readable format for import

===========================================
HOW TO RESTORE
===========================================

1. Copy connection files back to /etc/NetworkManager/system-connections/
   sudo cp -r ./networkmanager/* /etc/NetworkManager/system-connections/

2. Restore permissions:
   sudo chmod 600 /etc/NetworkManager/system-connections/*
   sudo chown root:root /etc/NetworkManager/system-connections/*

3. Restart NetworkManager:
   sudo systemctl restart NetworkManager

4. For wpa_supplicant:
   sudo cp ./wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/
   sudo systemctl restart wpa_supplicant

===========================================
SECURITY WARNING
===========================================
THIS BACKUP CONTAINS PLAINTEXT PASSWORDS!
Store it securely and delete when no longer needed.

===========================================
EOF
    
    log_success "Summary created: $summary"
}

# Encrypt backup
encrypt_backup() {
    if [[ "$ENCRYPT_BACKUP" == true ]]; then
        log_header "Encrypting backup..."
        
        if [[ -z "$ENCRYPT_PASSWORD" ]]; then
            read -s -p "Enter encryption password: " ENCRYPT_PASSWORD
            echo
            read -s -p "Confirm encryption password: " password_confirm
            echo
            if [[ "$ENCRYPT_PASSWORD" != "$password_confirm" ]]; then
                log_error "Passwords do not match"
                exit 1
            fi
        fi
        
        local archive_name="$BACKUP_DIR.tar.gz.enc"
        tar -czf - "$BACKUP_DIR" | openssl enc -aes-256-cbc -salt -out "$archive_name" -pass pass:"$ENCRYPT_PASSWORD"
        
        if [[ $? -eq 0 ]]; then
            rm -rf "$BACKUP_DIR"
            BACKUP_DIR="${archive_name%.enc}"
            log_success "Backup encrypted and saved as: $archive_name"
            log_info "To decrypt: openssl enc -aes-256-cbc -d -salt -in $archive_name -pass pass:PASSWORD | tar -xzv"
        else
            log_error "Encryption failed"
        fi
    fi
}

# Export to CSV for easy viewing
export_csv() {
    if [[ "$EXPORT_FORMAT" == "csv" ]] || [[ "$EXPORT_FORMAT" == "all" ]]; then
        log_header "Exporting to CSV..."
        
        local csv_file="$BACKUP_DIR/wifi_export.csv"
        echo "SSID,Password,Security,Connection Name,Backup Date" > "$csv_file"
        
        # Extract from nmcli backup
        if [[ -f "$BACKUP_DIR/nmcli_backup.txt" ]]; then
            # Parse the text file - simplified version
            grep -A5 "=== Profile:" "$BACKUP_DIR/nmcli_backup.txt" | \
            awk '/=== Profile:/{conn=$3} /SSID:/{ssid=$2} /PASSWORD:/{pwd=$2} /Security:/{sec=$2} /^$/{if(conn!="") print ssid","pwd","sec","conn","'$(date -Iseconds)'"}' >> "$csv_file" 2>/dev/null || true
        fi
        
        log_success "CSV export created: $csv_file"
    fi
}

# =============================================================================
# USAGE/HELP
# =============================================================================

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Backup all WiFi passwords, SSIDs, and connection profiles from your system.

Options:
    -h, --help          Show this help message
    -o, --output DIR    Specify backup output directory (default: ./wifi_backup_*)
    -e, --encrypt       Encrypt the backup with AES-256
    -p, --password PASS Encryption password (if not provided, will prompt)
    -f, --format FORMAT Export format: txt, json, csv, all (default: txt)
    -q, --quiet         Reduce output verbosity
    -v, --verbose       Show detailed output

Examples:
    $0                                      # Basic backup
    $0 -o /path/to/backup                   # Custom output directory
    $0 -e -p MySecurePassword123            # Encrypted backup
    $0 -f all                               # Export in all formats
    $0 -q                                   # Quiet mode

Security Note:
    This backup contains plaintext passwords. Store it securely!
    Recommended: Use -e flag for encryption.

EOF
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Show header
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  WIFI PASSWORD BACKUP UTILITY${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo "Running as: $(whoami)"
    echo "Date: $(date)"
    echo "Host: $(hostname)"
    echo -e "${CYAN}========================================${NC}"
    
    # Check if running as root
    check_root
    
    # Display warning and get confirmation
    confirm_backup
    
    # Check dependencies
    check_dependencies
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -o|--output)
                BACKUP_DIR="$2"
                shift 2
                ;;
            -e|--encrypt)
                ENCRYPT_BACKUP=true
                shift
                ;;
            -p|--password)
                ENCRYPT_PASSWORD="$2"
                ENCRYPT_BACKUP=true
                shift 2
                ;;
            -f|--format)
                EXPORT_FORMAT="$2"
                shift 2
                ;;
            -q|--quiet)
                exec >/dev/null 2>&1
                shift
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Create backup directory
    create_backup_dir
    
    # Perform backups
    backup_nm_connections
    backup_nmcli
    backup_wpa_supplicant
    get_current_connections
    extract_from_known_files
    
    # Export formats
    export_csv
    
    # Create summary
    create_summary
    
    # Encrypt if requested
    encrypt_backup
    
    # Final message
    echo ""
    log_success "✅ WiFi backup completed successfully!"
    log_info "📁 Backup location: $BACKUP_DIR"
    
    if [[ "$ENCRYPT_BACKUP" == true ]]; then
        log_warning "🔒 Backup is encrypted. Remember your password!"
    else
        log_warning "⚠️  Backup contains plaintext passwords! Secure it immediately."
    fi
    
    echo ""
    echo "Quick restore:"
    echo "  sudo cp -r $BACKUP_DIR/networkmanager/* /etc/NetworkManager/system-connections/"
    echo "  sudo systemctl restart NetworkManager"
}

# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================

# If no arguments, show help
if [[ $# -eq 0 ]]; then
    show_help
    echo ""
    read -p "Continue with default backup? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Run main function
main "$@"

# =============================================================================
# END OF SCRIPT
# =============================================================================
