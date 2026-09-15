# Cluster Federation Deployment Script

## Overview

`deploy_cf_unified.sh` is an automated deployment script that installs and configures Cluster Federation on a local Linux machine. The script handles all aspects of deployment including user creation, Docker installation, Ansible setup, and CF service configuration.

## Supported Operating Systems

- **Ubuntu**: 20.04, 22.04, 24.04
- **Debian**: 10, 11, 12
- **AlmaLinux**: 8, 9
- **RHEL**: 8, 9
- **CentOS**: 7, 8, Stream
- **Rocky Linux**: 8, 9
- **Fedora**: 37+

## Prerequisites

### System Requirements

- **Root Access**: Script must be run as root
- **Disk Space**: Minimum 20GB free space
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Network**: Internet connectivity required for package downloads

### Required Information

Before running the script, you'll need:

1. **CloudSmith API Key**: Provided by Lightbits for accessing the CF repository
2. **CF Version**: The script will show available versions to choose from

## Quick Start

### 1. Download the Script

```bash
# Copy script to your machine
scp deploy_cf_unified.sh root@<your-machine>:~/
```

### 2. Make Executable

```bash
chmod +x deploy_cf_unified.sh
```

### 3. Run the Script

```bash
./deploy_cf_unified.sh
```

**Note**: Script must be run as root.

### 4. Follow the Prompts

The script will guide you through:
- CloudSmith API key entry
- CF version selection
- Project name configuration

## What the Script Does

### Automated Steps

The script performs 12 automated steps:

#### STEP 1: Deployment Mode
- Sets up local deployment configuration
- Configures hostname as `localhost`

#### STEP 2: User Creation
- Creates `ansible-user` with sudo privileges
- Configures passwordless sudo access
- Sets up home directory and bash shell

#### STEP 3: Docker Installation
- Installs Docker Engine (OS-specific method)
- Installs Docker Compose plugin
- Adds `ansible-user` to docker group
- Enables and starts Docker service

#### STEP 4: CloudSmith Configuration
- Prompts for CloudSmith API key
- Validates credentials
- Logs into CloudSmith Docker registry

#### STEP 5: Version Selection
- Fetches available versions from CloudSmith
- Allows selection of specific version or manual entry
- Validates manually entered versions
- Defaults to latest version if no selection made

#### STEP 6: Project Configuration
- Prompts for project name (default: `default`)
- Updates configuration with selected project name

#### STEP 7: Package Download
- Downloads CF Ansible package
- Extracts to `/home/ansible-user/cf-deployment/`
- Verifies download integrity
- Applies OS-specific YAML quoting patches:
  - Ubuntu/Debian: Removes quotes from playbook env var conversion
  - RHEL-based: Adds quotes to playbook env var conversion
- Installs required packages (gnupg2, openssl) for Rocky Linux 10 compatibility

#### STEP 8: Ansible Installation
- Installs Python development tools
- Installs Ansible Core
- Installs required Python libraries (requests)
- Installs Ansible collections (community.docker, community.general, ansible.posix)
- Installs Ansible roles (geerlingguy.docker)

#### STEP 9: Curl Fix (RHEL-based)
- Checks for curl package conflicts
- Reinstalls curl if necessary to ensure compatibility

#### STEP 10: Inventory Configuration
- Creates Ansible inventory file
- Configures `group_vars` with environment settings
- Applies version overrides to `docker-compose.yml`

#### STEP 11: Deployment
- Runs the main Ansible playbook
- Deploys all services (CF, Temporal, PostgreSQL, etc.)
- Configures firewall rules
- Sets up TLS certificates

#### STEP 12: Post-Deployment
- Configures `cfcli` tool
- Sets up bash completion
- Verifies service health)
  - temporal (workflow engine)
  - temporal-ui
  - postgresql (database)
  - prometheus (metrics)
  - node-exporter
  - grafana

#### STEP 12: CLI Setup
- Configures `cfcli` alias
- Installs bash completion
- Sets up command-line tools

## Interactive Prompts

### CloudSmith API Key
```
Enter CloudSmith API Key: 
```
Enter your CloudSmith API key (provided by Lightbits).

### Version Selection
```
Available CF Image Versions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1) v0.9.2-0-g628d56a7
  2) v0.9.1-0-gaa2f7544
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  3) Enter version manually

Select CF image version [1-3]:
```
Choose a version number or select manual entry.

**Note**: If you enter a version manually, the script will validate that it exists in CloudSmith before proceeding. If the version is invalid, you'll be prompted to try again or exit.

### Project Name
```
Enter project name for Cluster Federation [default: default]:
```
Press Enter for default or specify a custom project name.

## Post-Deployment Steps

After successful deployment, follow these steps:

### 1. Login to CF Service
```bash
cfcli login --username admin --password light --base-url https://localhost:443
```

**Default Credentials:**
- Username: `admin`
- Password: `light`

### 2. Verify Installation
```bash
# Check cfcli help
cfcli help

# List clusters (should be empty initially)
cfcli list clusters
```

### 4. Access Services

- **CF API**: https://localhost:443
- **Metrics**: http://localhost:8082
- **Temporal UI**: http://localhost:8080

## Files and Directories Created

### On Local Machine

```
/home/ansible-user/
├── .bashrc                           # Updated with cfcli alias
└── cf-deployment/
    ├── cf-ansible-v0.8.0.tar.gz     # Downloaded package
    └── cf-ansible-v0.8.0/
        ├── inventory/
        │   ├── hosts                 # Ansible inventory
        │   ├── group_vars/
        │   │   └── all.yml          # Configuration variables
        │   └── logs/
        │       └── ansible.log      # Deployment log
        ├── playbooks/
        ├── roles/
        ├── docker-compose.yml
        └── .env

/opt/cf/
├── cf.yml                           # CF service config
├── docker-compose.yml               # Service orchestration
├── .env                             # Environment variables
├── data/                            # CF data directory
└── temporal_data/                   # Temporal data directory

/etc/sudoers.d/
└── ansible-user                     # Sudo configuration

/etc/bash_completion.d/
└── cfcli.sh                         # CLI autocompletion

/tmp/
└── cf_deploy_YYYYMMDD_HHMMSS.log   # Script execution log
```

## Troubleshooting

### Deployment Failed

**Check Ansible logs:**
```bash
cat /home/ansible-user/cf-deployment/cf-ansible-v0.8.0/inventory/logs/ansible.log
```

**Check script log:**
```bash
cat /tmp/cf_deploy_*.log
```

### Services Not Starting

**Check Docker containers:**
```bash
docker ps
```

**View CF logs:**
```bash
docker logs cluster-federation
```

**Check all services:**
```bash
cd /opt/cf
docker compose ps
```

### cfcli Authentication Error

If you see `invalid auth token` error:

```bash
# Login to CF service first
cfcli login --username admin --password light --base-url https://localhost:443
```

### Docker Permission Denied

If you get permission errors:

```bash
# Logout and login again to refresh group membership
exit
# SSH back in
```

### Port Conflicts

Check if required ports are available:
```bash
ss -tuln | grep -E '443|8080|8082'
```

If ports are in use, stop conflicting services before deployment.

## Advanced Usage

### Viewing Deployment Progress

The script provides real-time progress with color-coded output:
- 🔵 **INFO**: Informational messages
- ✅ **SUCCESS**: Successful operations
- ⚠️ **WARNING**: Warnings (non-fatal)
- ❌ **ERROR**: Errors (fatal)

### Logs Location

All operations are logged to:
- **Script log**: `/tmp/cf_deploy_YYYYMMDD_HHMMSS.log` - **All script output** (stdout and stderr) is captured here
- **Ansible log**: `$ANSIBLE_DIR/inventory/logs/ansible.log`

**Note**: The script log captures all console output with ANSI color codes and special characters stripped for better readability. This makes it a clean, complete record of the deployment process.

### Re-running the Script

The script is now fully idempotent and safe to re-run:
- **Existing users** won't be recreated
- **Installed packages** will be skipped (checked before installation)
- **Docker** won't be reinstalled if present
- **Downloaded packages** won't be re-downloaded if already present
- **Extracted files** won't be re-extracted if directory exists
- **Python dependencies** (pip, requests) are verified and installed only if missing
- **Ansible** won't be reinstalled if already present

The Ansible playbook will redeploy CF services, which is the intended behavior for updates.

## Deployment Timeline

| Step | Duration | Description |
|------|----------|-------------|
| 1-2  | 1 min    | User setup |
| 3    | 2-3 min  | Docker installation |
| 4-5  | 1-2 min  | CloudSmith, version selection |
| 6    | 1-2 min  | Package download |
| 7    | 3-5 min  | Ansible installation |
| 8-10 | 1 min    | Configuration |
| 11   | 10-20 min| CF deployment |
| 12   | 1 min    | CLI setup |

**Total**: 20-35 minutes

## Security Considerations

### Default Credentials

The script creates users with default credentials:
- **ansible-user**: Passwordless sudo (for deployment)
- **CF admin**: username=`admin`, password=`light`

**⚠️ Important**: Change these credentials in production environments.

### Sudo Access

The `ansible-user` is configured with `NOPASSWD:ALL` sudo access. Consider removing or restricting this after deployment:

```bash
rm /etc/sudoers.d/ansible-user
```

### Network Security

CF services listen on:
- Port 443 (HTTPS) - CF API
- Port 8080 (HTTP) - Temporal UI
- Port 8082 (HTTP) - Metrics

Configure firewall rules as needed for your environment.

## Getting Help

### Common Commands

**Check service status:**
```bash
docker ps
```

**View logs:**
```bash
docker logs cluster-federation
docker logs temporal
docker logs postgresql
```

**Restart services:**
```bash
cd /opt/cf
docker compose restart
```

**Stop all services:**
```bash
cd /opt/cf
docker compose down
```

**Start all services:**
```bash
cd /opt/cf
docker compose up -d
```

### Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs in `/tmp/cf_deploy_*.log`
3. Contact Lightbits support with log files

## Version Information

- **Script Version**: 3.2
- **Ansible Version**: 8.7.0
- **Ansible Core**: 2.15.13
- **Python Requirement**: 3.9+
- **Docker Compose**: v2.23.3+

## Changelog

### Version 3.2
- **Multi-OS YAML Quoting Compatibility**: Fixed deployment to support both Ubuntu 24.04 and RHEL-based systems simultaneously
  - OS-aware playbook patching: Ubuntu/Debian removes quotes, RHEL-based adds quotes
  - Unified group_vars generation with proper Jinja2 template quoting for all OS types
  - Resolves "invalid reference format" errors on Ubuntu 24.04
  - Restores YAML parsing compatibility on Alma Linux 9.7, Rocky Linux, and other RHEL-based systems
- **Enhanced Documentation**: Updated README to reflect OS-specific YAML quoting behavior

### Version 3.1
- **Enhanced Logging**: All script output (stdout/stderr) now captured in log file with ANSI color codes stripped for readability
- **Version Validation**: Manual version entries are validated against CloudSmith before proceeding
- **Stricter Prompts**: User confirmation prompts now require full "yes" or "no" responses for better security
- **Full Idempotency**: Script now properly skips already-completed steps on re-runs
  - Package downloads skipped if file already exists
  - Package extraction skipped if directory already exists
  - Python dependencies (pip, requests) verified on every run
- **Python Requests Library**: Explicitly installed to prevent Ansible Docker module failures
- **AlmaLinux 9.7 Compatibility**: Automatic patch for YAML parsing issue with environment variables
- **Improved Error Messages**: Better feedback for invalid version entries and missing dependencies
- Early failure on invalid versions prevents wasted deployment time
- Updated example command from `cfcli version` to `cfcli help`

### Version 3.0
- Multi-OS support (Ubuntu, Debian, AlmaLinux, RHEL, CentOS, Rocky, Fedora)
- Enhanced CloudSmith version selection
- Automatic version override for docker-compose.yml
- Improved error handling and validation
- Local deployment only (simplified)
- Fixed graphics for universal terminal compatibility
- Added cfcli login instructions

## License

Copyright © Lightbits Labs. All rights reserved.
