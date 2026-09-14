#!/bin/bash
#
# Enhanced Unified Cluster Federation Deployment Script
# Supports: Ubuntu, Debian, AlmaLinux, Rocky Linux
# Features: Multi-OS support with OS-specific YAML quoting, enhanced Cloudsmith integration, comprehensive error handling
# Version: 3.4 - Component versions now sourced from canonical cf.env in Ansible package
#

set -e  # Exit on error
set -o pipefail  # Catch errors in pipes

# ============================================================================
# GLOBAL VARIABLES
# ============================================================================

SCRIPT_VERSION="3.4"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/cf_deploy_$(date +%Y%m%d_%H%M%S).log"
DEPLOY_DIR=""
ANSIBLE_DIR=""
CF_HOSTNAME=""
CF_SSH_USER=""
SSH_KEY_PATH=""
CLOUDSMITH_USERNAME="cf"
CLOUDSMITH_API_KEY=""
APP_VERSION=""
CF_IMG_VERSION=""
PROJECT_NAME="default"
DEPLOY_LOCAL=false

# Version variables (sourced from canonical cf.env)
PROMETHEUS_VERSION=""
NODE_EXPORTER_VERSION=""
GRAFANA_VERSION=""
TEMPORAL_ADMIN_TOOLS_VERSION=""
TEMPORAL_VERSION=""
TEMPORAL_UI_VERSION=""
POSTGRESQL_VERSION=""
OS_ID=""
OS_VERSION=""
OS_FAMILY=""
PKG_MGR=""
NON_INTERACTIVE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# ============================================================================
# LOGGING AND OUTPUT FUNCTIONS
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# Setup logging to capture all output
setup_logging() {
    # Redirect all output to both console and log file
    # Use sed to strip ANSI color codes from log file
    exec > >(tee >(sed -r 's/\x1b\[[0-9;]*m//g' >> "$LOG_FILE"))
    exec 2>&1
    log "=== Script started at $(date) ==="
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    log "INFO: $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    log "SUCCESS: $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    log "WARNING: $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    log "ERROR: $1"
}

print_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    log "STEP: $1"
}

print_progress() {
    echo -e "${MAGENTA}[PROGRESS]${NC} $1"
    log "PROGRESS: $1"
}

# ============================================================================
# ERROR HANDLING AND CLEANUP
# ============================================================================

cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        print_error "Script failed with exit code $exit_code"
        print_info "Log file: $LOG_FILE"
        print_info "Check the log for details"
    fi
}

trap cleanup EXIT

# ============================================================================
# OS DETECTION AND PACKAGE MANAGER ABSTRACTION
# ============================================================================

detect_os() {
    print_info "Detecting operating system..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID="$ID"
        OS_VERSION="$VERSION_ID"
        OS_FAMILY="${ID_LIKE:-$ID}"
        
        print_success "Detected OS: $NAME $VERSION_ID"
        log "OS Details - ID: $OS_ID, Version: $OS_VERSION, Family: $OS_FAMILY"
    else
        print_error "Cannot detect OS - /etc/os-release not found"
        exit 1
    fi
}

get_package_manager() {
    case "$OS_ID" in
        ubuntu|debian)
            PKG_MGR="apt"
            ;;
        almalinux|rhel|centos|rocky)
            if command -v dnf &>/dev/null; then
                PKG_MGR="dnf"
            else
                PKG_MGR="yum"
            fi
            ;;
        fedora)
            PKG_MGR="dnf"
            ;;
        *)
            print_error "Unsupported OS: $OS_ID"
            print_info "Supported: Ubuntu, Debian, AlmaLinux, Rocky Linux"
            exit 1
            ;;
    esac
    
    print_success "Package manager: $PKG_MGR"
    log "Using package manager: $PKG_MGR"
}

update_package_cache() {
    print_info "Updating package cache..."
    case "$PKG_MGR" in
        apt)
            if [ "$NON_INTERACTIVE" = true ]; then
                # Show progress in non-interactive mode to avoid appearing stuck
                apt-get update
            else
                # Quiet mode for interactive use
                apt-get update -qq
            fi
            ;;
        dnf|yum)
            if [ "$NON_INTERACTIVE" = true ]; then
                # Show progress in non-interactive mode
                $PKG_MGR makecache
            else
                # Quiet mode for interactive use
                $PKG_MGR makecache -q
            fi
            ;;
    esac
    print_success "Package cache updated"
}

install_package() {
    local package=$1
    local package_name=${2:-$package}  # Display name, defaults to package name
    
    # Check if already installed
    case "$PKG_MGR" in
        apt)
            if dpkg -l | grep -q "^ii  $package "; then
                print_info "$package_name already installed"
                return 0
            fi
            ;;
        dnf|yum)
            if rpm -q "$package" &>/dev/null; then
                print_info "$package_name already installed"
                return 0
            fi
            ;;
    esac
    
    print_info "Installing $package_name..."
    case "$PKG_MGR" in
        apt)
            DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$package"
            ;;
        dnf|yum)
            $PKG_MGR install -y -q "$package"
            ;;
    esac
    print_success "$package_name installed"
}

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

show_usage() {
    cat <<'EOF'
Usage: deploy_cf_unified.sh [OPTIONS]

OPTIONS:
    --non-interactive    Run in non-interactive mode (requires environment variables)
    --list-versions      List all available CF versions from CloudSmith and exit
    --help              Show this help message

INTERACTIVE MODE (default):
    The script will prompt for all required information interactively.

NON-INTERACTIVE MODE:
    Set the following environment variables before running the script:
    
    Required:
        CF_CLOUDSMITH_API_KEY    CloudSmith API key for authentication
        CF_VERSION               CF version to deploy (e.g., v0.9.2-0-g628d56a7)
                                 Can also be set to "latest" to use the most recent version
    
    Optional:
        CF_PROJECT_NAME          Project name (default: "default")
        CF_SKIP_DISK_CHECK       Skip disk space check (set to "true" or "1")
    
    Example:
        export CF_CLOUDSMITH_API_KEY="your-api-key-here"
        export CF_VERSION="v0.9.2-0-g628d56a7"
        export CF_PROJECT_NAME="production"
        ./deploy_cf_unified.sh --non-interactive

    Example (from Python):
        import subprocess
        import os
        
        env = os.environ.copy()
        env['CF_CLOUDSMITH_API_KEY'] = 'your-api-key'
        env['CF_VERSION'] = 'v0.9.2-0-g628d56a7'
        env['CF_PROJECT_NAME'] = 'production'
        
        result = subprocess.run(
            ['./deploy_cf_unified.sh', '--non-interactive'],
            env=env,
            capture_output=True,
            text=True
        )

LIST VERSIONS:
    Query CloudSmith to display all available CF versions:
    
        export CF_CLOUDSMITH_API_KEY="your-api-key-here"
        ./deploy_cf_unified.sh --list-versions

EOF
    exit 0
}

list_versions() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Cluster Federation - Available Versions"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Check for API key
    if [ -z "$CF_CLOUDSMITH_API_KEY" ]; then
        printf "${RED}ERROR:${NC} CF_CLOUDSMITH_API_KEY environment variable is required\n"
        echo ""
        echo "Usage:"
        echo "  export CF_CLOUDSMITH_API_KEY=\"your-api-key\""
        echo "  $0 --list-versions"
        exit 1
    fi
    
    CLOUDSMITH_API_KEY="$CF_CLOUDSMITH_API_KEY"
    
    # Install jq if not available
    if ! command -v jq &>/dev/null; then
        echo "Installing jq (required for JSON parsing)..."
        if command -v apt-get &>/dev/null; then
            apt-get update -qq && apt-get install -y -qq jq
        elif command -v dnf &>/dev/null; then
            dnf install -y -q jq
        elif command -v yum &>/dev/null; then
            yum install -y -q jq
        else
            printf "${RED}ERROR:${NC} Cannot install jq. Please install it manually.\n"
            exit 1
        fi
    fi
    
    echo "Fetching available versions from CloudSmith..."
    echo ""
    
    # Fetch available image tags
    local tags_json=$(curl -s -u "$CLOUDSMITH_USERNAME:$CLOUDSMITH_API_KEY" \
        "https://docker.lightbitslabs.com/v2/cf/cluster-federation/tags/list" 2>/dev/null)
    
    if [ -z "$tags_json" ] || ! echo "$tags_json" | jq -e '.tags' &>/dev/null; then
        printf "${RED}ERROR:${NC} Could not fetch versions from CloudSmith API\n"
        echo "Please verify:"
        echo "  1. Your API key is correct"
        echo "  2. You have access to the CF repository"
        echo "  3. Network connectivity to CloudSmith"
        exit 1
    fi
    
    # Parse and sort versions
    local versions=$(echo "$tags_json" | jq -r '.tags[]' | sort -V -r)
    local version_count=$(echo "$versions" | wc -l)
    
    if [ "$version_count" -eq 0 ]; then
        printf "${RED}ERROR:${NC} No versions found in CloudSmith\n"
        exit 1
    fi
    
    printf "${GREEN}Found $version_count available versions:${NC}\n"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Display versions
    local i=1
    while IFS= read -r version; do
        if [ -n "$version" ]; then
            # Highlight latest version
            if [ $i -eq 1 ]; then
                printf "  ${GREEN}%3d. %s (latest)${NC}\n" "$i" "$version"
            else
                printf "  %3d. %s\n" "$i" "$version"
            fi
            i=$((i + 1))
        fi
    done <<< "$versions"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "To deploy a specific version (example):"
    echo "  export CF_VERSION=\"v0.9.2-0-g628d56a7\""
    echo "  ./deploy_cf_unified.sh --non-interactive"
    echo ""
    echo "To deploy the latest version:"
    echo "  export CF_VERSION=\"latest\""
    echo "  ./deploy_cf_unified.sh --non-interactive"
    echo ""
    
    exit 0
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        print_info "Usage: sudo $0"
        exit 1
    fi
}

check_disk_space() {
    local required_gb=20
    local available_gb=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    
    if [ "$available_gb" -lt "$required_gb" ]; then
        print_warning "Low disk space: ${available_gb}GB available (${required_gb}GB recommended)"
        
        # In non-interactive mode, check environment variable
        if [ "$NON_INTERACTIVE" = true ]; then
            if [ "$CF_SKIP_DISK_CHECK" = "true" ] || [ "$CF_SKIP_DISK_CHECK" = "1" ]; then
                print_warning "Continuing despite low disk space (CF_SKIP_DISK_CHECK is set)"
            else
                print_error "Insufficient disk space and CF_SKIP_DISK_CHECK not set"
                print_info "Set CF_SKIP_DISK_CHECK=true to override this check"
                exit 1
            fi
        else
            # Interactive mode - ask user
            while true; do
                read -p "Continue anyway? (yes/no): " response
                case "$response" in
                    yes)
                        break
                        ;;
                    no)
                        print_info "Deployment cancelled by user"
                        exit 1
                        ;;
                    *)
                        print_error "Please enter 'yes' or 'no'"
                        ;;
                esac
            done
        fi
    else
        print_success "Disk space check passed: ${available_gb}GB available"
    fi
}

check_network() {
    print_info "Checking network connectivity..."
    
    local endpoints=(
        "docker.lightbitslabs.com"
        "download.docker.com"
        "github.com"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if ping -c 1 -W 2 "$endpoint" &>/dev/null || curl -s --max-time 5 "https://$endpoint" &>/dev/null; then
            print_success "Network check: $endpoint reachable"
        else
            print_warning "Network check: $endpoint unreachable (may cause issues)"
        fi
    done
}

validate_cloudsmith_credentials() {
    print_info "Validating CloudSmith credentials..."
    
    local response=$(curl -s -u "$CLOUDSMITH_USERNAME:$CLOUDSMITH_API_KEY" \
        "https://docker.lightbitslabs.com/v2/" -w "%{http_code}" -o /dev/null)
    
    if [ "$response" = "200" ]; then
        print_success "CloudSmith credentials valid"
        return 0
    else
        print_error "CloudSmith authentication failed (HTTP $response)"
        print_info "Please check your API key"
        return 1
    fi
}

validate_cf_version() {
    local version=$1
    print_info "Validating CF version: $version"
    
    # Check if the version exists in CloudSmith
    local response=$(curl -s -u "$CLOUDSMITH_USERNAME:$CLOUDSMITH_API_KEY" \
        "https://docker.lightbitslabs.com/v2/cf/cluster-federation/manifests/$version" \
        -w "%{http_code}" -o /dev/null)
    
    if [ "$response" = "200" ]; then
        print_success "CF version $version exists in CloudSmith"
        return 0
    else
        print_error "CF version $version not found in CloudSmith (HTTP $response)"
        print_info "Please check the version and try again"
        return 1
    fi
}

# ============================================================================
# DOCKER INSTALLATION (MULTI-OS)
# ============================================================================

install_docker_ubuntu_debian() {
    print_info "Installing Docker for Ubuntu/Debian..."
    
    # Install prerequisites
    install_package "ca-certificates"
    install_package "curl"
    install_package "gnupg"
    
    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    
    if [ "$OS_ID" = "ubuntu" ]; then
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    else
        curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
    fi
    chmod a+r /etc/apt/keyrings/docker.asc
    
    # Set up the repository
    if [ "$OS_ID" = "ubuntu" ]; then
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          tee /etc/apt/sources.list.d/docker.list > /dev/null
    else
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          tee /etc/apt/sources.list.d/docker.list > /dev/null
    fi
    
    # Update package cache
    apt-get update -qq
    
    # Install Docker packages
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin
    
    print_success "Docker installed for Ubuntu/Debian"
}

install_docker_rhel_based() {
    print_info "Installing Docker for RHEL-based systems..."
    
    # Install prerequisites
    install_package "$PKG_MGR-plugins-core" "DNF plugins"
    install_package "gnupg2" "GnuPG for GPG key verification"
    
    # Add Docker repository
    if [ "$OS_ID" = "fedora" ]; then
        $PKG_MGR config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
    else
        $PKG_MGR config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    fi
    
    # Install Docker packages
    $PKG_MGR install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    print_success "Docker installed for RHEL-based system"
}

install_docker() {
    if command -v docker &>/dev/null; then
        local docker_version=$(docker --version)
        print_success "Docker already installed: $docker_version"
        
        if docker compose version &>/dev/null; then
            local compose_version=$(docker compose version)
            print_success "Docker Compose already installed: $compose_version"
            return 0
        fi
    fi
    
    case "$OS_ID" in
        ubuntu|debian)
            install_docker_ubuntu_debian
            ;;
        almalinux|rhel|centos|rocky|fedora)
            install_docker_rhel_based
            ;;
        *)
            print_error "Unsupported OS for Docker installation: $OS_ID"
            exit 1
            ;;
    esac
    
    # Enable and start Docker
    systemctl enable docker
    systemctl start docker
    
    # Verify installation
    if docker --version && docker compose version; then
        print_success "Docker and Docker Compose installed successfully"
    else
        print_error "Docker installation verification failed"
        exit 1
    fi
    
    # Add ansible-user to docker group (now that docker group exists)
    if ! groups ansible-user | grep -q docker; then
        usermod -aG docker ansible-user
        print_success "User ansible-user added to docker group"
    fi
}

# ============================================================================
# USER MANAGEMENT
# ============================================================================

create_ansible_user() {
    local username=${1:-ansible-user}
    
    if id "$username" &>/dev/null; then
        print_warning "User $username already exists, skipping creation"
    else
        useradd -m -s /bin/bash "$username"
        print_success "User $username created"
    fi
    
    # Set up unlimited sudo access
    if [ ! -f "/etc/sudoers.d/$username" ]; then
        echo "$username ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/$username"
        chmod 0440 "/etc/sudoers.d/$username"
        print_success "Unlimited sudo access granted to $username"
    fi
}

# ============================================================================
# SSH KEY MANAGEMENT
# ============================================================================

setup_ssh_keys() {
    local local_user=$1
    local remote_user=$2
    local remote_host=$3
    local key_type=${4:-rsa}
    local key_path="/home/$local_user/.ssh/id_${key_type}"
    
    print_info "Setting up SSH key authentication..."
    
    # Generate SSH key if it doesn't exist
    su - "$local_user" -c "
        if [ ! -f $key_path ]; then
            mkdir -p ~/.ssh
            chmod 700 ~/.ssh
            
            if [ '$key_type' = 'rsa' ]; then
                ssh-keygen -t rsa -b 4096 -f $key_path -N '' -C 'CF Deployment Key'
            else
                ssh-keygen -t ed25519 -f $key_path -N '' -C 'CF Deployment Key'
            fi
            
            chmod 600 $key_path
            chmod 644 ${key_path}.pub
        fi
    "
    
    print_success "SSH key generated: $key_path"
    
    # Copy public key to remote host
    print_info "Copying SSH key to $remote_host..."
    su - "$local_user" -c "
        sshpass -p 'light' ssh-copy-id -i ${key_path}.pub -o StrictHostKeyChecking=no $remote_user@$remote_host
    "
    
    SSH_KEY_PATH="$key_path"
    print_success "SSH key authentication configured"
    
    # Test connection
    print_info "Testing SSH connection..."
    if su - "$local_user" -c "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 $remote_user@$remote_host 'echo SSH connection successful'" 2>/dev/null; then
        print_success "SSH connection test passed"
    else
        print_error "SSH connection test failed"
        exit 1
    fi
}

# ============================================================================
# CLOUDSMITH VERSION SELECTION
# ============================================================================

select_cf_version() {
    # Install jq for JSON parsing
    install_package "jq" "jq (JSON processor)"
    
    # In non-interactive mode, use CF_VERSION environment variable
    if [ "$NON_INTERACTIVE" = true ]; then
        if [ -z "$CF_VERSION" ]; then
            print_error "CF_VERSION environment variable is required in non-interactive mode"
            print_info "Set CF_VERSION to a specific version (e.g., v0.9.2-0-g628d56a7) or 'latest'"
            exit 1
        fi
        
        # If CF_VERSION is "latest", fetch the latest version
        if [ "$CF_VERSION" = "latest" ]; then
            print_info "Fetching latest CF version from CloudSmith..."
            local tags_json=$(curl -s -u "$CLOUDSMITH_USERNAME:$CLOUDSMITH_API_KEY" \
                "https://docker.lightbitslabs.com/v2/cf/cluster-federation/tags/list" 2>/dev/null)
            
            if [ -z "$tags_json" ] || ! echo "$tags_json" | jq -e '.tags' &>/dev/null; then
                print_error "Could not fetch versions from CloudSmith API"
                exit 1
            fi
            
            # Get the latest version (first in reverse sorted list)
            CF_IMG_VERSION=$(echo "$tags_json" | jq -r '.tags[]' | sort -V -r | head -1)
            
            if [ -z "$CF_IMG_VERSION" ]; then
                print_error "No versions found in CloudSmith"
                exit 1
            fi
            
            print_success "Latest CF version: $CF_IMG_VERSION"
        else
            # Use the specified version
            CF_IMG_VERSION="$CF_VERSION"
            print_info "Using specified CF version: $CF_IMG_VERSION"
            
            # Validate the version exists
            if ! validate_cf_version "$CF_IMG_VERSION"; then
                print_error "CF version $CF_IMG_VERSION not found in CloudSmith"
                exit 1
            fi
        fi
        
        # Extract APP_VERSION from CF_IMG_VERSION
        APP_VERSION=$(echo "$CF_IMG_VERSION" | cut -d'-' -f1)
        print_success "Using Ansible package version: $APP_VERSION"
        return
    fi
    
    # Interactive mode (original behavior)
    print_info "Fetching available CF versions from CloudSmith..."
    
    # Fetch available image tags
    local tags_json=$(curl -s -u "$CLOUDSMITH_USERNAME:$CLOUDSMITH_API_KEY" \
        "https://docker.lightbitslabs.com/v2/cf/cluster-federation/tags/list" 2>/dev/null)
    
    if [ -z "$tags_json" ] || ! echo "$tags_json" | jq -e '.tags' &>/dev/null; then
        print_warning "Could not fetch versions from CloudSmith API"
        read -p "Enter CF image version manually (e.g., v0.9.2-0-g628d56a7): " CF_IMG_VERSION
        print_info "Using CF image version: $CF_IMG_VERSION"
        # Extract APP_VERSION from CF_IMG_VERSION
        APP_VERSION=$(echo "$CF_IMG_VERSION" | cut -d'-' -f1)
        print_info "Using APP_VERSION: $APP_VERSION (Ansible package)"
        return
    fi
    
    # Parse and sort versions
    local versions=$(echo "$tags_json" | jq -r '.tags[]' | sort -V -r)
    local version_count=$(echo "$versions" | wc -l)
    
    if [ "$version_count" -eq 0 ]; then
        print_error "No versions found in CloudSmith"
        exit 1
    fi
    
    print_success "Found $version_count available CF image versions"
    echo ""
    echo "Available CF Image Versions:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Display versions with numbering
    local i=1
    declare -a version_array
    while IFS= read -r version; do
        if [ -n "$version" ]; then
            version_array[$i]="$version"
            # Clean version string for display (remove git hash suffix like -0-g3d1bb1cf)
            local display_version=$(echo "$version" | sed -E 's/-[0-9]+-g[0-9a-f]+$//')
            printf "%3d) %s\n" "$i" "$display_version"
            i=$((i + 1))
        fi
    done <<< "$versions"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "%3d) Enter version manually\n" "$i"
    echo ""
    
    # Get user selection
    while true; do
        read -p "Select CF image version [1-$i]: " selection
        
        if [ "$selection" -eq "$i" ] 2>/dev/null; then
            # Manual version entry with validation
            while true; do
                read -p "Enter CF image version (e.g., v0.9.2-0-g628d56a7): " CF_IMG_VERSION
                if [ -z "$CF_IMG_VERSION" ]; then
                    print_error "Version cannot be empty"
                    continue
                fi
                
                # Validate the version exists
                if validate_cf_version "$CF_IMG_VERSION"; then
                    break
                else
                    print_error "Version $CF_IMG_VERSION does not exist in CloudSmith"
                    while true; do
                        read -p "Try another version? (yes/no): " retry
                        case "$retry" in
                            yes)
                                break
                                ;;
                            no)
                                print_error "Cannot proceed without a valid CF version"
                                exit 1
                                ;;
                            *)
                                print_error "Please enter 'yes' or 'no'"
                                ;;
                        esac
                    done
                fi
            done
            break
        elif [ "$selection" -ge 1 ] 2>/dev/null && [ "$selection" -lt "$i" ]; then
            CF_IMG_VERSION="${version_array[$selection]}"
            break
        else
            print_error "Invalid selection. Please enter a number between 1 and $i"
        fi
    done
    
    # Extract APP_VERSION from CF_IMG_VERSION (e.g., v0.9.2-0-g628d56a7 -> v0.9.2)
    APP_VERSION=$(echo "$CF_IMG_VERSION" | cut -d'-' -f1)
    
    print_success "Selected CF image version: $CF_IMG_VERSION"
    print_success "Using Ansible package version: $APP_VERSION"

}

# ============================================================================
# DOCKER-COMPOSE.YML VERSION OVERRIDE
# ============================================================================

# ============================================================================
# SOURCE VERSION VARIABLES FROM CANONICAL CF.ENV
# ============================================================================

source_version_variables() {
    local canonical_cf_env="$ANSIBLE_DIR/cf.env"
    
    if [ ! -f "$canonical_cf_env" ]; then
        print_error "Canonical cf.env file not found at: $canonical_cf_env"
        print_error "This file should be included in the CF Ansible package"
        exit 1
    fi
    
    print_info "Sourcing version variables from canonical cf.env..."
    
    # Source the file and extract version variables
    # Using a subshell to avoid polluting the current environment
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        
        # Remove any quotes from the value
        value=$(echo "$value" | sed -e "s/^[\"']//; s/[\"']$//")
        
        case "$key" in
            PROMETHEUS_VERSION)
                PROMETHEUS_VERSION="$value"
                ;;
            NODE_EXPORTER_VERSION)
                NODE_EXPORTER_VERSION="$value"
                ;;
            GRAFANA_VERSION)
                GRAFANA_VERSION="$value"
                ;;
            TEMPORAL_ADMIN_TOOLS_VERSION)
                TEMPORAL_ADMIN_TOOLS_VERSION="$value"
                ;;
            TEMPORAL_VERSION)
                TEMPORAL_VERSION="$value"
                ;;
            TEMPORAL_UI_VERSION)
                TEMPORAL_UI_VERSION="$value"
                ;;
            POSTGRESQL_VERSION)
                POSTGRESQL_VERSION="$value"
                ;;
        esac
    done < "$canonical_cf_env"
    
    # Validate that all required versions were sourced
    local missing_versions=()
    [ -z "$PROMETHEUS_VERSION" ] && missing_versions+=("PROMETHEUS_VERSION")
    [ -z "$NODE_EXPORTER_VERSION" ] && missing_versions+=("NODE_EXPORTER_VERSION")
    [ -z "$GRAFANA_VERSION" ] && missing_versions+=("GRAFANA_VERSION")
    [ -z "$TEMPORAL_ADMIN_TOOLS_VERSION" ] && missing_versions+=("TEMPORAL_ADMIN_TOOLS_VERSION")
    [ -z "$TEMPORAL_VERSION" ] && missing_versions+=("TEMPORAL_VERSION")
    [ -z "$TEMPORAL_UI_VERSION" ] && missing_versions+=("TEMPORAL_UI_VERSION")
    [ -z "$POSTGRESQL_VERSION" ] && missing_versions+=("POSTGRESQL_VERSION")
    
    if [ ${#missing_versions[@]} -gt 0 ]; then
        print_error "Missing version variables in cf.env: ${missing_versions[*]}"
        exit 1
    fi
    
    print_success "Version variables sourced successfully:"
    print_info "  PROMETHEUS_VERSION: $PROMETHEUS_VERSION"
    print_info "  NODE_EXPORTER_VERSION: $NODE_EXPORTER_VERSION"
    print_info "  GRAFANA_VERSION: $GRAFANA_VERSION"
    print_info "  TEMPORAL_ADMIN_TOOLS_VERSION: $TEMPORAL_ADMIN_TOOLS_VERSION"
    print_info "  TEMPORAL_VERSION: $TEMPORAL_VERSION"
    print_info "  TEMPORAL_UI_VERSION: $TEMPORAL_UI_VERSION"
    print_info "  POSTGRESQL_VERSION: $POSTGRESQL_VERSION"
}

apply_version_overrides() {
    local compose_file="$ANSIBLE_DIR/docker-compose.yml"
    
    if [ ! -f "$compose_file" ]; then
        print_warning "docker-compose.yml not found, skipping version overrides"
        return
    fi
    
    print_info "Applying version overrides to docker-compose.yml..."
    
    # Create backup
    cp "$compose_file" "${compose_file}.backup"
    print_info "Backup created: ${compose_file}.backup"
    
    # Add environment variables if not already present
    if ! grep -q "APP_VERSION=" "$compose_file"; then
        sed -i '/ANSIBLE_FORCE_COLOR=True/a\    - APP_VERSION=${APP_VERSION}' "$compose_file"
        print_success "Added APP_VERSION to environment"
    fi
    
    if ! grep -q "CF_IMG_VERSION=" "$compose_file"; then
        sed -i '/APP_VERSION=\${APP_VERSION}/a\    - CF_IMG_VERSION=${CF_IMG_VERSION}' "$compose_file"
        print_success "Added CF_IMG_VERSION to environment"
    fi
    
    # Modify ansible-playbook command to include extra-vars
    if grep -q "playbooks/deploy-cf-playbook.yml" "$compose_file"; then
        sed -i "s|playbooks/deploy-cf-playbook.yml -vvv|playbooks/deploy-cf-playbook.yml -e \"APP_VERSION=$APP_VERSION\" -e \"CF_IMG_VERSION=$CF_IMG_VERSION\" -vvv|" "$compose_file"
        print_success "Added version extra-vars to ansible-playbook command"
    fi
    
    # Verify changes
    if grep -q "APP_VERSION=$APP_VERSION" "$compose_file" && grep -q "CF_IMG_VERSION=$CF_IMG_VERSION" "$compose_file"; then
        print_success "Version overrides applied successfully"
    else
        print_warning "Version overrides may not have been applied correctly"
    fi
}

# ============================================================================
# CURL PACKAGE FIX (RHEL-BASED SYSTEMS)
# ============================================================================

fix_curl_package() {
    # Only needed for RHEL-based systems
    case "$OS_ID" in
        almalinux|rhel|centos|rocky|fedora)
            ;;
        *)
            return 0
            ;;
    esac
    
    if [ "$DEPLOY_LOCAL" = true ]; then
        print_info "Checking curl package locally..."
        if rpm -q curl-minimal &>/dev/null; then
            print_info "Swapping curl-minimal with curl..."
            $PKG_MGR swap -y curl-minimal curl
            print_success "curl package fixed locally"
        fi
    else
        print_info "Checking curl package on CF machine..."
        su - "$CF_SSH_USER" -c "ssh -o StrictHostKeyChecking=no $CF_SSH_USER@$CF_HOSTNAME 'sudo bash -s' <<'ENDSSH'
if rpm -q curl-minimal &>/dev/null; then
    echo 'Swapping curl-minimal with curl...'
    dnf swap -y curl-minimal curl || yum swap -y curl-minimal curl
fi
ENDSSH
"
        print_success "curl package fixed on CF machine"
    fi
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

main() {
    # Parse command-line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            --list-versions)
                list_versions
                ;;
            --help)
                show_usage
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                ;;
        esac
    done
    
    # Clear screen if available (optional on minimal systems)
    command -v clear &>/dev/null && clear
    cat <<'EOF'
================================================================================
                                                                              
    Cluster Federation Enhanced Deployment Script                           
    Version: 3.4                                                             
    Multi-OS Support: Ubuntu, Debian, AlmaLinux, Rocky Linux
                                                                              
================================================================================
EOF
    echo ""
    print_info "Log file: $LOG_FILE"
    
    if [ "$NON_INTERACTIVE" = true ]; then
        print_info "Running in NON-INTERACTIVE mode"
    else
        print_info "Running in INTERACTIVE mode"
    fi
    echo ""
    
    # Setup logging first to capture all output
    setup_logging
    
    # Pre-flight checks
    check_root
    detect_os
    get_package_manager
    check_disk_space
    check_network
    
    # ========================================================================
    # STEP 1: Set Local Deployment Mode
    # ========================================================================
    print_step "STEP 1: Deployment Mode"
    
    DEPLOY_LOCAL=true
    CF_HOSTNAME="localhost"
    CF_SSH_USER="ansible-user"
    SSH_KEY_PATH=""
    
    print_info "Deployment mode: Local (same machine)"
    print_info "CF Hostname: $CF_HOSTNAME"
    
    # ========================================================================
    # STEP 2: Create ansible-user
    # ========================================================================
    print_step "STEP 2: Creating ansible-user on local machine"
    
    create_ansible_user "ansible-user"
    
    # ========================================================================
    # STEP 3: Install Docker
    # ========================================================================
    print_step "STEP 3: Installing Docker"
    
    update_package_cache
    install_docker
    
    # ========================================================================
    # STEP 4: Get CloudSmith credentials
    # ========================================================================
    print_step "STEP 4: CloudSmith Configuration"
    
    if [ "$NON_INTERACTIVE" = true ]; then
        # Non-interactive mode: read from environment variable
        if [ -z "$CF_CLOUDSMITH_API_KEY" ]; then
            print_error "CF_CLOUDSMITH_API_KEY environment variable is required in non-interactive mode"
            exit 1
        fi
        CLOUDSMITH_API_KEY="$CF_CLOUDSMITH_API_KEY"
        print_info "Using CloudSmith API key from environment variable"
    else
        # Interactive mode: prompt user
        read -p "Enter CloudSmith API Key: " CLOUDSMITH_API_KEY
    fi
    
    # Validate credentials
    if ! validate_cloudsmith_credentials; then
        exit 1
    fi
    
    # Login to CloudSmith
    print_info "Logging in to CloudSmith..."
    echo "$CLOUDSMITH_API_KEY" | docker login docker.lightbitslabs.com -u $CLOUDSMITH_USERNAME --password-stdin
    su - ansible-user -c "echo '$CLOUDSMITH_API_KEY' | docker login docker.lightbitslabs.com -u $CLOUDSMITH_USERNAME --password-stdin"
    print_success "Logged in to CloudSmith"
    
    # ========================================================================
    # STEP 5: Select CF Version (sets both CF_IMG_VERSION and APP_VERSION)
    # ========================================================================
    print_step "STEP 5: Selecting CF Version"
    
    select_cf_version
    
    # ========================================================================
    # ========================================================================
    # STEP 6: Project name configuration
    # ========================================================================
    print_step "STEP 6: Project Configuration"
    
    if [ "$NON_INTERACTIVE" = true ]; then
        # Non-interactive mode: read from environment variable or use default
        PROJECT_NAME="${CF_PROJECT_NAME:-default}"
        print_info "Project name: $PROJECT_NAME"
    else
        # Interactive mode: prompt user
        read -p "Enter project name for Cluster Federation [default: default]: " PROJECT_NAME
        PROJECT_NAME=${PROJECT_NAME:-default}
        print_info "Project name: $PROJECT_NAME"
    fi
    
    if [ "$PROJECT_NAME" != "default" ]; then
        print_info "Using custom project name: $PROJECT_NAME"
    fi

    # ========================================================================
    # STEP 7: Download CF Ansible package
    # ========================================================================
    print_step "STEP 7: Downloading CF Ansible Package"
    
    DEPLOY_DIR="/home/ansible-user/cf-deployment"
    mkdir -p $DEPLOY_DIR
    chown ansible-user:ansible-user $DEPLOY_DIR
    
    cd $DEPLOY_DIR
    
    DOWNLOAD_FILE="cf-ansible-$APP_VERSION.tar.gz"
    ANSIBLE_DIR="$DEPLOY_DIR/cf-ansible-$APP_VERSION"
    
    # Check if already downloaded and extracted
    if [ -d "$ANSIBLE_DIR" ] && [ -f "$ANSIBLE_DIR/playbooks/deploy-cf-playbook.yml" ]; then
        print_success "CF Ansible package already downloaded and extracted: $ANSIBLE_DIR"
    else
        print_info "Downloading cf-ansible-${APP_VERSION}.tar.gz..."
        
        # Download with error checking
        DOWNLOAD_URL="https://dl.lightbitslabs.com/$CLOUDSMITH_API_KEY/cf/raw/versions/$APP_VERSION/cf-ansible-$APP_VERSION.tar.gz?accept_eula=1"
        
        # Skip download if file already exists and is valid
        if [ -f "$DEPLOY_DIR/$DOWNLOAD_FILE" ] && [ -s "$DEPLOY_DIR/$DOWNLOAD_FILE" ]; then
            print_success "Package file already exists: $DOWNLOAD_FILE"
        else
            su - ansible-user -c "
cd $DEPLOY_DIR
if curl -1sLf '$DOWNLOAD_URL' --output '$DOWNLOAD_FILE'; then
    if [ -f '$DOWNLOAD_FILE' ] && [ -s '$DOWNLOAD_FILE' ]; then
        echo 'Download successful'
    else
        echo 'ERROR: Downloaded file is empty or missing'
        exit 1
    fi
else
    echo 'ERROR: Download failed'
    exit 1
fi
"
            
            if [ $? -ne 0 ]; then
                print_error "Failed to download cf-ansible-${APP_VERSION}.tar.gz"
                print_info "URL: https://dl.cloudsmith.io/.../cf-ansible-${APP_VERSION}.tar.gz"
                print_info "Please verify:"
                print_info "  1. APP_VERSION ($APP_VERSION) is correct"
                print_info "  2. Package exists in CloudSmith repository"
                print_info "  3. API key has download permissions"
                exit 1
            fi
            
            print_success "Package downloaded successfully"
        fi
        
        # Extract with error checking
        print_info "Extracting package..."
        su - ansible-user -c "
cd $DEPLOY_DIR
tar xzf '$DOWNLOAD_FILE'
"
        
        if [ $? -ne 0 ]; then
            print_error "Failed to extract cf-ansible-${APP_VERSION}.tar.gz"
            exit 1
        fi
        
        print_success "CF Ansible package extracted"
    fi
    
    # Verify extraction
    if [ ! -d "$ANSIBLE_DIR" ]; then
        print_error "Expected directory not found: $ANSIBLE_DIR"
        print_info "Available directories:"
        ls -la "$DEPLOY_DIR"
        exit 1
    fi
    
    # Source version variables from the canonical cf.env file
    source_version_variables
    
    # Patch playbook for YAML quoting - different behavior needed for Ubuntu vs RHEL-based systems
    # Ubuntu 24.04: Needs quotes REMOVED to prevent Docker image tag issues
    # RHEL-based (Alma/Rocky): Needs quotes ADDED for proper YAML parsing
    PLAYBOOK_FILE="$ANSIBLE_DIR/playbooks/deploy-cf-playbook.yml"
    if [ -f "$PLAYBOOK_FILE" ]; then
        case "$OS_ID" in
            ubuntu|debian)
                # Ubuntu/Debian: Remove quotes from version strings
                if grep -Fq 'echo "$key: \"$value\""' "$PLAYBOOK_FILE"; then
                    print_info "Applying Ubuntu/Debian YAML quoting fix (removing quotes from version strings)..."
                    # Change from: echo "$key: \"$value\""
                    # To: echo "$key: $value"
                    # This prevents Docker image references like "temporalio/admin-tools:{{ VERSION }}"
                    # from becoming temporalio/admin-tools:"1.27.2" (with quotes in the tag)
                    sed -i 's/echo "\$key: \\"\$value\\"/echo "\$key: \$value"/g' "$PLAYBOOK_FILE"
                    print_success "YAML quoting fix applied for Ubuntu/Debian"
                else
                    print_info "Playbook already patched for Ubuntu/Debian or uses different quoting format"
                fi
                ;;
            almalinux|rhel|centos|rocky|fedora)
                # RHEL-based: Add quotes to values for proper YAML parsing
                if grep -Fq 'echo "$key: $value"' "$PLAYBOOK_FILE"; then
                    print_info "Applying RHEL-based YAML quoting fix (adding quotes to values)..."
                    # Change from: echo "$key: $value"
                    # To: echo "$key: \"$value\""
                    # This ensures proper YAML parsing on RHEL-based systems
                    sed -i 's/echo "\$key: \$value"/echo "\$key: \\"\$value\\""/g' "$PLAYBOOK_FILE"
                    print_success "YAML quoting fix applied for RHEL-based systems"
                else
                    print_info "Playbook already patched for RHEL-based systems or uses different quoting format"
                fi
                ;;
            *)
                print_warning "Unknown OS type for YAML quoting patch: $OS_ID"
                ;;
        esac
        
        # Patch playbook to install gnupg2 and openssl (Rocky Linux 10 compatibility)
        NEEDS_GNUPG2_PATCH=false
        NEEDS_OPENSSL_PATCH=false
        
        # Check if there's a broken patch with literal \n characters
        if grep -q '\\n' "$PLAYBOOK_FILE"; then
            print_info "Detected broken patch with literal \\n characters, cleaning up..."
            # Remove the broken patch lines
            sed -i '/Ensure gnupg2 is installed.*\\n/d' "$PLAYBOOK_FILE"
            sed -i '/Ensure openssl is installed.*\\n/d' "$PLAYBOOK_FILE"
        fi
        
        if ! grep -q "name: gnupg2" "$PLAYBOOK_FILE"; then
            NEEDS_GNUPG2_PATCH=true
        fi
        
        if ! grep -q "name: openssl" "$PLAYBOOK_FILE"; then
            NEEDS_OPENSSL_PATCH=true
        fi
        
        if [ "$NEEDS_GNUPG2_PATCH" = true ] || [ "$NEEDS_OPENSSL_PATCH" = true ]; then
            print_info "Applying Rocky Linux 10 compatibility patch to playbook..."
            
            if [ "$NEEDS_GNUPG2_PATCH" = true ] && [ "$NEEDS_OPENSSL_PATCH" = true ]; then
                # Add both gnupg2 and openssl
                sed -i '/^  roles:/i \
  - name: Ensure gnupg2 is installed (required for Docker GPG key on RHEL-based systems)\
    become: true\
    ansible.builtin.package:\
      name: gnupg2\
      state: present\
    when: ansible_os_family == "RedHat"\
\
  - name: Ensure openssl is installed (required for certificate generation)\
    become: true\
    ansible.builtin.package:\
      name: openssl\
      state: present\
' "$PLAYBOOK_FILE"
            elif [ "$NEEDS_OPENSSL_PATCH" = true ]; then
                # Add only openssl (gnupg2 already present)
                sed -i '/^  roles:/i \
  - name: Ensure openssl is installed (required for certificate generation)\
    become: true\
    ansible.builtin.package:\
      name: openssl\
      state: present\
' "$PLAYBOOK_FILE"
            fi
            
            print_success "Playbook patched for Rocky Linux 10 compatibility"
        else
            print_info "Playbook already includes required packages (patch not needed)"
        fi
    fi
    
    # Patch ansible-cf-role to include gnupg2 (Rocky Linux 10 compatibility)
    CF_ROLE_MAIN="$ANSIBLE_DIR/roles/ansible-cf-role/tasks/main.yml"
    if [ -f "$CF_ROLE_MAIN" ]; then
        # Check if gnupg2 is already in the package list
        if ! grep -q "gnupg2" "$CF_ROLE_MAIN"; then
            print_info "Applying Rocky Linux 10 compatibility patch (adding gnupg2)..."
            # Add gnupg2 to the package list after nvme-cli
            sed -i '/- nvme-cli/a \    - gnupg2' "$CF_ROLE_MAIN"
            print_success "Ansible role patched for Rocky Linux 10 compatibility"
        else
            print_info "Ansible role already includes gnupg2 (patch not needed)"
        fi
    fi
    
    # Patch ansible-cf-role to include gnupg2 (Rocky Linux 10 compatibility)
    CF_ROLE_MAIN="$ANSIBLE_DIR/roles/ansible-cf-role/tasks/main.yml"
    if [ -f "$CF_ROLE_MAIN" ]; then
        # Check if gnupg2 is already in the package list
        if ! grep -q "gnupg2" "$CF_ROLE_MAIN"; then
            print_info "Applying Rocky Linux 10 compatibility patch (adding gnupg2)..."
            # Add gnupg2 to the package list after nvme-cli
            sed -i '/- nvme-cli/a \    - gnupg2' "$CF_ROLE_MAIN"
            print_success "Ansible role patched for Rocky Linux 10 compatibility"
        else
            print_info "Ansible role already includes gnupg2 (patch not needed)"
        fi
    fi
    
    # ========================================================================
    # STEP 8: Install System Ansible
    # ========================================================================
    print_step "STEP 8: Installing Ansible"
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_info "Python version: $PYTHON_VERSION"
    
    # Always ensure Python development tools are installed (needed for pip packages)
    print_info "Ensuring Python development tools are installed..."
    case "$PKG_MGR" in
        apt)
            install_package "python3-pip"
            install_package "python3-dev" "Python development headers"
            install_package "gcc"
            ;;
        dnf|yum)
            install_package "python3-pip"
            install_package "python3-devel" "Python development headers"
            install_package "gcc"
            ;;
    esac
    
    # Determine pip arguments (handle PEP 668 on Ubuntu 24.04+ / Debian 12+)
    PIP_ARGS=""
    if pip3 install --help | grep -q "break-system-packages"; then
        print_info "Detected managed environment, using --break-system-packages for pip"
        PIP_ARGS="--break-system-packages"
    fi

    # Install or verify Ansible
    if ! command -v ansible &>/dev/null; then
        print_info "Installing Ansible 8.x (Python 3.9+ compatible)..."
        
        # Only upgrade pip/setuptools/wheel if NOT in a managed environment
        # In managed environments (Ubuntu 24.04+), these are managed by apt and upgrading via pip causes conflicts
        if [ -z "$PIP_ARGS" ]; then
            pip3 install --upgrade pip setuptools wheel
        else
            print_info "Skipping pip/setuptools/wheel upgrade in managed environment to avoid conflicts"
        fi
        
        pip3 install $PIP_ARGS ansible-core==2.15.13
        pip3 install $PIP_ARGS ansible==8.7.0
        print_success "Ansible 8.7.0 installed"
    else
        print_success "Ansible already installed: $(ansible --version | head -1)"
    fi
    
    # Always ensure Python requests library is installed (required by Ansible Docker modules)
    if ! python3 -c "import requests" &>/dev/null; then
        print_info "Installing Python requests library..."
        pip3 install $PIP_ARGS -q requests
        print_success "Python requests library installed"
    else
        print_success "Python requests library already installed"
    fi
    
    # Install Ansible roles and collections
    print_info "Installing Ansible roles and collections..."
    su - ansible-user -c "
ansible-galaxy role install geerlingguy.docker --force
ansible-galaxy collection install community.general --force
ansible-galaxy collection install community.docker --force
ansible-galaxy collection install ansible.posix --force
cd $ANSIBLE_DIR
ansible-galaxy install -r roles/ansible-docker-role/requirements.yml --force 2>/dev/null || true
ansible-galaxy install -r roles/ansible-observability-role/requirements.yml --force 2>/dev/null || true
"
    print_success "Roles and collections installed"
    
    # ========================================================================
    # STEP 9: Fix curl package (RHEL-based systems)
    # ========================================================================
    print_step "STEP 9: Fixing curl package (RHEL-based systems)"
    
    fix_curl_package
    
    # ========================================================================
    # STEP 10: Configure Ansible inventory
    # ========================================================================
    print_step "STEP 10: Configuring Ansible Inventory"
    
    su - ansible-user -c "mkdir -p $ANSIBLE_DIR/inventory/group_vars"
    
    # Create hosts file
    if [ "$DEPLOY_LOCAL" = true ]; then
        print_info "Creating inventory for local deployment..."
        su - ansible-user -c "
cat <<EOF > $ANSIBLE_DIR/inventory/hosts
cf  ansible_host=localhost \\
     ansible_connection=local \\
     ansible_user=ansible-user \\
     ansible_become_user=root

[cf_servers]
cf
EOF
"
    else
        print_info "Creating inventory for remote deployment..."
        su - ansible-user -c "
cat <<EOF > $ANSIBLE_DIR/inventory/hosts
cf  ansible_host=$CF_HOSTNAME \\
     ansible_connection=ssh \\
     ansible_ssh_user=$CF_SSH_USER \\
     ansible_become_user=root \\
     ansible_ssh_private_key_file=$SSH_KEY_PATH

[cf_servers]
cf
EOF
"
        
        # Uncomment SSH key line in docker-compose.yml if it exists
        if [ -n "$SSH_KEY_PATH" ] && [ -f "$ANSIBLE_DIR/docker-compose.yml" ]; then
            su - ansible-user -c "
cd $ANSIBLE_DIR
sed -i 's/# - \${SSH_KEY_PATH}:\${SSH_KEY_PATH_IN_CONT}/- \${SSH_KEY_PATH}:\${SSH_KEY_PATH_IN_CONT}/' docker-compose.yml 2>/dev/null || true
"
        fi
    fi
    
    print_success "Inventory created"
    
    # Create .env file
    su - ansible-user -c "
cat <<EOF > $ANSIBLE_DIR/.env
UID=$(id -u ansible-user)
GID=$(id -g ansible-user)
UNAME=ansible-user
APP_VERSION=$APP_VERSION
CF_IMG_VERSION=$CF_IMG_VERSION
SSH_KEY_PATH=$SSH_KEY_PATH
SSH_KEY_PATH_IN_CONT=/opt/id_rsa
EOF
"
    
    # Create group_vars with all required variables
    print_info "Creating group_vars with all configuration..."
    su - ansible-user -c "
cat <<EOF > $ANSIBLE_DIR/inventory/group_vars/all.yml
run_observability_services: true
image_registry: docker.lightbitslabs.com
image_registries:
- name: docker.lightbitslabs.com
  url: https://docker.lightbitslabs.com
  security:
    insecure: false
  login:
    username: $CLOUDSMITH_USERNAME
    password: $CLOUDSMITH_API_KEY

docker_users:
- $CF_SSH_USER

# Version variables (unquoted strings for Jinja2 interpolation)
APP_VERSION: $APP_VERSION
CF_IMG_VERSION: $CF_IMG_VERSION

# Component versions (sourced from canonical cf.env)
PROMETHEUS_VERSION: $PROMETHEUS_VERSION
NODE_EXPORTER_VERSION: $NODE_EXPORTER_VERSION
GRAFANA_VERSION: $GRAFANA_VERSION

TEMPORAL_ADMIN_TOOLS_VERSION: $TEMPORAL_ADMIN_TOOLS_VERSION
TEMPORAL_VERSION: $TEMPORAL_VERSION
TEMPORAL_UI_VERSION: $TEMPORAL_UI_VERSION

POSTGRESQL_VERSION: $POSTGRESQL_VERSION

# Image paths - CF from lightbits, others from public registries
# YAML requires quotes when values start with {{ (Jinja2 template syntax)
# The quotes are YAML syntax and are removed during parsing - they don't cause double-quoting
cf_img: \"{{ image_registry }}/cf/cluster-federation:{{ CF_IMG_VERSION }}\"
temporal_img: \"temporalio/auto-setup:{{ TEMPORAL_VERSION }}\"
temporal_admintools_img: \"temporalio/admin-tools:{{ TEMPORAL_ADMIN_TOOLS_VERSION }}\"
temporal_ui_img: \"temporalio/ui:{{ TEMPORAL_UI_VERSION }}\"
postgresql_img: \"postgres:{{ POSTGRESQL_VERSION }}\"
EOF
"
    
    print_success "Configuration created"

    # Update cf.env file in the Ansible package directory with CF version info
    # Note: Component versions (Prometheus, Grafana, Temporal, etc.) are already in the canonical cf.env
    # We only need to update APP_VERSION and CF_IMG_VERSION which are selected during deployment
    print_info "Updating cf.env file with selected CF versions..."
    su - ansible-user -c "
# Update APP_VERSION and CF_IMG_VERSION in the existing cf.env file
sed -i 's/^APP_VERSION=.*/APP_VERSION=$APP_VERSION/' $ANSIBLE_DIR/cf.env
sed -i 's/^CF_IMG_VERSION=.*/CF_IMG_VERSION=$CF_IMG_VERSION/' $ANSIBLE_DIR/cf.env
"
    print_success "cf.env file updated with CF_IMG_VERSION=$CF_IMG_VERSION and APP_VERSION=$APP_VERSION"
    print_info "Component versions are sourced from the canonical cf.env in the Ansible package"

    # Apply version overrides to docker-compose.yml
    apply_version_overrides
    

    # ========================================================================
    # STEP 11: Deploy Cluster Federation
    # ========================================================================
    print_step "STEP 11: Deploying Cluster Federation"
    
    print_warning "This may take 10-20 minutes..."
    echo ""
    
    export SSH_KEY_PATH=$SSH_KEY_PATH
    
    su - ansible-user -c "
cd $ANSIBLE_DIR
if [ -f '$SSH_KEY_PATH' ]; then
    eval \$(ssh-agent -s) > /dev/null
    ssh-add '$SSH_KEY_PATH' 2>/dev/null || true
fi
export ANSIBLE_LOG_PATH=$ANSIBLE_DIR/inventory/logs/ansible.log
export ANSIBLE_FORCE_COLOR=True
mkdir -p $ANSIBLE_DIR/inventory/logs
ansible-playbook -i inventory/hosts playbooks/deploy-cf-playbook.yml -v -e \"project_name=$PROJECT_NAME\"
"
    
    PLAYBOOK_EXIT=$?
    
    # ========================================================================
    # STEP 12: Setup cfcli
    # ========================================================================
    if [ $PLAYBOOK_EXIT -eq 0 ]; then
        print_step "STEP 12: Setting up cfcli"
        
        # Setup cfcli locally
        if ! grep -q "alias cfcli=" /home/ansible-user/.bashrc 2>/dev/null; then
            su - ansible-user -c "
cat >> ~/.bashrc <<'EOF'

# cfcli alias for Cluster Federation CLI
alias cfcli='docker exec -it cluster-federation cfcli'
EOF
"
        fi
        
        su - ansible-user -c "
docker exec cluster-federation cfcli completion bash | sudo tee /etc/bash_completion.d/cfcli.sh > /dev/null
"
        print_success "cfcli configured locally"
        
        # ====================================================================
        # Final Success Message
        # ====================================================================
        echo ""
        print_step "DEPLOYMENT COMPLETE!"
        
        cat <<EOF

================================================================================
                CLUSTER FEDERATION DEPLOYMENT SUCCESSFUL!
================================================================================

   DEPLOYMENT DETAILS:
   • Operating System: $OS_ID $OS_VERSION
   • CF Machine: $CF_HOSTNAME
   • CF Image: cluster-federation:$CF_IMG_VERSION
   • SSH User: $CF_SSH_USER
   • Project: $PROJECT_NAME

   NEXT STEPS:

EOF

        cat <<EOF
1. Login to CF service:
   cfcli login --username admin --password light --base-url https://localhost:443

2. Verify installation:
   cfcli help
   cfcli list clusters

EOF
        
        cat <<EOF
   SERVICES:
   • CF API: https://$CF_HOSTNAME:443
   • Metrics: http://$CF_HOSTNAME:8082
   • Temporal UI: http://$CF_HOSTNAME:8080

   FILES:
   • Deployment: $ANSIBLE_DIR
   • Logs: $ANSIBLE_DIR/inventory/logs/ansible.log
   • Script Log: $LOG_FILE

   TROUBLESHOOTING:
   • Check services: docker ps
   • View logs: docker logs cluster-federation
   • Restart: cd /opt/cf && docker compose restart

   SECURITY RECOMMENDATION:
   Although this deployment was performed as root, it is advisable to create
   a dedicated user for CF operations. To do this:

   1. Create a new user:
      useradd -m -s /bin/bash cfadmin

   2. Add user to docker group:
      usermod -aG docker cfadmin

   3. Set password:
      passwd cfadmin

   4. Switch to the new user for CF operations:
      su - cfadmin

   The cfcli alias and bash completion are already configured for all users.

================================================================================

EOF

    else
        print_error "Deployment failed! Check logs at: $ANSIBLE_DIR/inventory/logs/ansible.log"
        print_info "Script log: $LOG_FILE"
        exit 1
    fi
}

# Run main function
main "$@"
