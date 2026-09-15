# Intelligent Cluster Management Deployment Script

## Overview

`deploy_icm_unified.sh` is an automated deployment script that installs and configures Intelligent Cluster Management (ICM) on a local Linux machine. The script handles all aspects of deployment including user creation, Docker installation, Ansible setup, and ICM service configuration.

It supports both an **interactive** mode (guided prompts) and a **non-interactive** mode (driven entirely by environment variables) for automation.

## Supported Operating Systems

ICM's Ansible controller requires **Python ≥ 3.12**, so the supported deploy hosts are:

- **Ubuntu**: 24.04+
- **Debian**: 13+
- **AlmaLinux / Rocky Linux / RHEL**: 9 (via AppStream `python3.12`), 10

> **Not supported**: Ubuntu 22.04 and Debian 12 — their stock `python3` is older than 3.12.

## Prerequisites

### System Requirements

- **Root Access**: Script must be run as root
- **Disk Space**: Minimum 20GB free space on `/` (the check can be bypassed with `ICM_SKIP_DISK_CHECK`)
- **Memory**: Minimum 4GB RAM (8GB recommended) — required by the ICM service stack (not enforced by the script)
- **Network**: Internet connectivity required for package downloads

### Required Information

Before running the script, you'll need:

1. **CloudSmith API Key**: Provided by Lightbits for accessing the ICM repository
2. **ICM Version**: The script will show available versions to choose from

## Quick Start

### 1. Download the Script

```bash
# Copy script to your machine
scp deploy_icm_unified.sh root@<your-machine>:~/
```

### 2. Make Executable

```bash
chmod +x deploy_icm_unified.sh
```

### 3. Run the Script

```bash
./deploy_icm_unified.sh
```

**Note**: Script must be run as root.

### 4. Follow the Prompts

The script will guide you through:
- CloudSmith API key entry
- ICM version selection
- Project name configuration

## Non-Interactive Mode

For automated / unattended deployments, run with `--non-interactive` and supply the inputs via environment variables:

```bash
export ICM_CLOUDSMITH_API_KEY="your-api-key-here"
export ICM_VERSION="v0.9.2-0-g628d56a7"   # a specific version, or "latest"
export ICM_PROJECT_NAME="production"       # optional, defaults to "default"
./deploy_icm_unified.sh --non-interactive
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ICM_CLOUDSMITH_API_KEY` | Yes | CloudSmith API key for authentication |
| `ICM_VERSION` | Yes | ICM version to deploy (e.g. `v0.9.2-0-g628d56a7`) or `latest` |
| `ICM_PROJECT_NAME` | No | Project name (default: `default`) |
| `ICM_SKIP_DISK_CHECK` | No | Set to `true` or `1` to skip the 20GB disk-space check |

`--help` prints the full usage, including these variables.

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
- Prompts for CloudSmith API key (or reads `ICM_CLOUDSMITH_API_KEY`)
- Validates credentials against the ICM registry
- Logs into the CloudSmith Docker registry (`docker.lightbitslabs.com`) as both `root` and `ansible-user`

#### STEP 5: Version Selection
- Fetches available versions from CloudSmith, sorted newest-first (option `1` is the latest)
- Interactive: pick a listed number or choose manual entry; an invalid or empty choice re-prompts (there is no silent default). Non-interactive: `ICM_VERSION` selects the version, and `latest` resolves to the newest
- Validates manually entered versions against CloudSmith
- Derives `APP_VERSION` from the selected image version

#### STEP 6: Project Configuration
- Prompts for project name (default: `default`)
- Updates configuration with the selected project name

#### STEP 7: Package Download
- Downloads the ICM Ansible package (`icm-ansible-<APP_VERSION>.tar.gz`)
- Extracts to `/home/ansible-user/icm-deployment/`
- Checks the archive exists and is non-empty (a presence check, **not** a checksum/signature verification); skips the download/extraction when a valid package and its extracted playbook are already present
- Applies OS-specific YAML quoting patches to the playbook:
  - Ubuntu/Debian: Removes quotes from version strings (prevents malformed Docker image tags)
  - RHEL-based: Adds quotes for proper YAML parsing
- Patches the ICM Ansible role to install `gnupg2` (and `openssl`) for Rocky Linux 10 compatibility

#### STEP 8: Ansible Installation
- Creates a dedicated Python virtual environment for the controller
- Installs a pinned `ansible-core` (2.21.3) and Ansible package (14.3.0)
- Installs required Python libraries and Ansible collections/roles used by the playbook

#### STEP 9: Curl Fix (RHEL-based)
- Checks for `curl` package conflicts
- Reinstalls `curl` if necessary to ensure compatibility

#### STEP 10: Inventory Configuration
- Creates the Ansible inventory file
- Writes `inventory/group_vars/all.yml` with the persisted deployment settings — including the **CloudSmith API key** (as the image-registry password) and the service version overrides (Prometheus, node-exporter, Grafana, Temporal, Temporal UI, PostgreSQL). `project_name` is **not** persisted here; it is passed to `ansible-playbook` at runtime as `-e "project_name=<name>"`
- Applies the service version overrides into the deployment configuration

#### STEP 11: Deployment
- Runs the main Ansible playbook (`deploy-icm-playbook.yml`), which imports the docker, ICM, and observability roles
- Deploys the service stack (via docker compose):
  - `intelligent-cluster-management` (ICM service, with an embedded etcd registry)
  - `temporal` (workflow engine), `temporal-admin-tools`, `temporal-ui`, `temporal-postgresql` (database)
  - `node-exporter`, `prometheus`, `grafana` (observability)
- Configures the OS firewall (firewalld on RHEL-based, UFW on Debian/Ubuntu) to open the service ports
- Generates TLS certificates (ICM server cert plus internal mTLS certs for Temporal and etcd)

#### STEP 12: CLI Setup
- Configures the `icmcli` alias for `ansible-user`
- Installs system-wide bash completion (`/etc/bash_completion.d/icmcli.sh`)

(Service health is asserted earlier, by the Ansible playbook during STEP 11, not in this step.)

## Interactive Prompts

### CloudSmith API Key
```
Enter CloudSmith API Key:
```
Enter your CloudSmith API key (provided by Lightbits).

### Version Selection
```
Available ICM Image Versions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1) v0.9.2-0-g628d56a7
  2) v0.9.1-0-gaa2f7544
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  3) Enter version manually

Select ICM image version [1-3]:
```
Choose a version number or select manual entry.

**Note**: If you enter a version manually, the script validates that it exists in CloudSmith before proceeding. If the version is invalid, you'll be prompted to try again or exit.

### Project Name
```
Enter project name for Intelligent Cluster Management [default: default]:
```
Press Enter for default or specify a custom project name.

## Post-Deployment Steps

After successful deployment, follow these steps:

### 1. Login to the ICM Service
```bash
icmcli login --username admin --password light --base-url https://localhost:443
```

**Default Credentials:**
- Username: `admin`
- Password: `light`

### 2. Verify Installation
```bash
# Check icmcli help
icmcli help

# List clusters (should be empty initially)
icmcli list clusters
```

### 3. Access Services

- **ICM API**: https://localhost:443
- **Metrics**: http://localhost:8082
- **Temporal UI**: http://localhost:8080
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090

### 4. (Optional) Use icmcli as Another User

The `icmcli` alias and bash completion are configured for `ansible-user`. To use ICM from a different (non-`ansible-user`) account:

```bash
# 1. Create the user and grant docker access
useradd -m -s /bin/bash icmadmin
usermod -aG docker icmadmin
passwd icmadmin

# 2. Switch to the user
su - icmadmin

# 3. Add the icmcli alias (system-wide bash completion already applies)
echo "alias icmcli='docker exec -it intelligent-cluster-management icmcli'" >> ~/.bashrc && source ~/.bashrc
# or, without an alias:
docker exec -it intelligent-cluster-management icmcli <command>
```

## Files and Directories Created

### On Local Machine

Paths below are shown with the default `persistent_storage_path` (empty), which
roots them at `/`. If a non-empty `persistent_storage_path` is configured, the
`/opt/icm`, `/etc/icm`, and `/opt/observability` trees are prefixed accordingly.

```
/home/ansible-user/
├── .bashrc                              # Updated with icmcli alias
└── icm-deployment/                      # Created by the script
    ├── icm-ansible-<version>.tar.gz     # Downloaded package
    └── icm-ansible-<version>/
        ├── inventory/
        │   ├── hosts                    # Ansible inventory
        │   ├── group_vars/
        │   │   └── all.yml              # Config vars — CONTAINS the CloudSmith API key
        │   └── logs/
        │       └── ansible.log          # Deployment log
        ├── playbooks/
        │   └── deploy-icm-playbook.yml
        ├── roles/
        ├── docker-compose.yml
        └── .env

# Created by the Ansible deployment (STEP 11):

/opt/icm/                                # ICM + Temporal service stack
├── docker-compose.yml                   # Service stack definition
├── .env                                 # Stack environment variables
├── dynamicconfig/                       # Temporal dynamic config
├── postgresql-data/                     # Temporal PostgreSQL data
└── tls/                                 # Stack TLS materials

/etc/icm/                                # ICM configuration + certificates
├── icm.yml                              # ICM service config
├── server.cert                          # ICM server TLS certificate
├── server.key                           # ICM server TLS key
├── keys/                                # ICM keys
├── .htpasswd                            # ICM basic-auth file
├── .temporal_encryption_key             # Temporal payload encryption key
└── temporal/certs/                      # Internal Temporal/etcd mTLS certs

/opt/observability/                      # Observability stack (Prometheus + Grafana)
├── docker-compose.yml
├── .env
├── etc/                                 # Prometheus / Grafana config
├── prometheus-data/                     # Prometheus TSDB
└── var/                                 # Grafana data

/etc/sudoers.d/
└── ansible-user                         # Sudo configuration

/etc/bash_completion.d/
└── icmcli.sh                            # CLI autocompletion

/tmp/
└── icm_deploy_YYYYMMDD_HHMMSS.log       # Script execution log
```

## Troubleshooting

### Deployment Failed

**Check Ansible logs:**
```bash
cat /home/ansible-user/icm-deployment/icm-ansible-*/inventory/logs/ansible.log
```

**Check script log:**
```bash
cat /tmp/icm_deploy_*.log
```

### Services Not Starting

**Check Docker containers:**
```bash
docker ps
```

**View ICM logs:**
```bash
docker logs intelligent-cluster-management
```

**Check all services:**
```bash
cd /opt/icm
docker compose ps
```

### icmcli Authentication Error

If you see an `invalid auth token` error:

```bash
# Login to the ICM service first
icmcli login --username admin --password light --base-url https://localhost:443
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

The script provides real-time progress with color-coded, tagged output:
- `[INFO]` (blue): Informational messages
- `[SUCCESS]` (green): Successful operations
- `[WARNING]` (yellow): Warnings (non-fatal)
- `[ERROR]` (red): Errors (fatal)

### Logs Location

All operations are logged to:
- **Script log**: `/tmp/icm_deploy_YYYYMMDD_HHMMSS.log` — **all script output** (stdout and stderr) is captured here, with ANSI color codes stripped for readability
- **Ansible log**: `<ANSIBLE_DIR>/inventory/logs/ansible.log`

### Re-running the Script

The script is idempotent and safe to re-run:
- **Existing users** won't be recreated
- **Installed packages** will be skipped (checked before installation)
- **Docker** won't be reinstalled if present
- **Downloaded packages** won't be re-downloaded if already present
- **Extracted files** won't be re-extracted if the directory exists
- **Ansible** (venv) won't be rebuilt if already present

The Ansible playbook will redeploy ICM services, which is the intended behavior for updates.

## Deployment Timeline

| Step  | Duration    | Description |
|-------|-------------|-------------|
| 1-3   | 1-2 min     | User setup + Docker install |
| 4-7   | < 1 min     | CloudSmith, version selection, package download |
| 8     | 3-5 min     | Ansible venv install (ansible-core install dominates) |
| 9-10  | < 1 min     | curl fix (RHEL only) + inventory |
| 11    | 3-15 min    | ICM deployment — dominated by container-image pulls (network-bound) |
| 12    | < 1 min     | CLI setup |

**Total**: ~10-20 minutes (≈8 minutes observed on a fast-network lab VM; STEP 11's image-pull time dominates and scales with network speed).

## Security Considerations

### CloudSmith API Key on Disk

The script writes your CloudSmith API key into
`/home/ansible-user/icm-deployment/icm-ansible-<version>/inventory/group_vars/all.yml`
(as the image-registry password) and leaves that file in the deployment directory
after the run. Treat it as a secret:
- Restrict access (e.g. `chmod 600` the file / `700` the deployment dir) and do not share or commit it.
- **Rotate the key immediately** in CloudSmith if the file is exposed.
- Remove it when no longer needed for re-runs.

### Default Credentials

The script creates users with default credentials:
- **ansible-user**: Passwordless sudo (for deployment)
- **ICM admin**: username=`admin`, password=`light`

**⚠️ Important**: Change these credentials in production environments.

### Sudo Access

The `ansible-user` is configured with `NOPASSWD:ALL` sudo access. Consider removing or restricting this after deployment:

```bash
rm /etc/sudoers.d/ansible-user
```

### Network Security

The deployment opens these service ports in the OS firewall:
- Port 443 (HTTPS) — ICM API
- Port 8080 (HTTP) — Temporal UI
- Port 8082 (HTTP) — ICM Metrics
- Port 3000 (HTTP) — Grafana
- Port 9090 (HTTP) — Prometheus

Restrict these rules as needed for your environment.

## Getting Help

### Common Commands

**Check service status:**
```bash
docker ps
```

**View logs:**
```bash
docker logs intelligent-cluster-management
docker logs temporal
docker logs temporal-postgresql
```

**Restart / stop / start all services:**
```bash
cd /opt/icm
docker compose restart
docker compose down
docker compose up -d
```

### Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs in `/tmp/icm_deploy_*.log`
3. Contact Lightbits support with log files

## Version Information

- **Script Version**: 1.0
- **Ansible Core**: 2.21.3
- **Ansible Package**: 14.3.0
- **Python Requirement**: 3.12+
- **CloudSmith Registry**: `docker.lightbitslabs.com`

## License

Copyright © Lightbits Labs. All rights reserved.
