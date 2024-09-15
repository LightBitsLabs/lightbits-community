# Observability

- [Observability](#observability)
  - [Requirements](#requirements)
  - [docker-compose installation](#docker-compose-installation)
  - [lbprox working directory and configuration](#lbprox-working-directory-and-configuration)
  - [Running Observability services](#running-observability-services)
    - [Running dashboard and prom-discovery on host (less-recommended)](#running-dashboard-and-prom-discovery-on-host-less-recommended)
    - [lbprox-dashboard service](#lbprox-dashboard-service)
    - [lbprox-prom-discovery service](#lbprox-prom-discovery-service)
  - [Logging](#logging)

## Requirements

## docker-compose installation

Run the following script to install docker and docker compose on this machine.

Most of these monitoring services will run inside a docker container, using `docker compose`.

```bash
./scripts/install_docker_ubuntu.sh
```

## lbprox working directory and configuration

Follow these instructions to setup `lbprox` working directory:

- [Setup workdir for lbprox cli](../lbprox/README.md#setup-workdir-for-lbprox-cli)

## Running Observability services

All the observability services are running using `docker compose`

First, clone the project:

```bash
git clone https://github.com/LightBitsLabs/lightbits-community.git
cd lightbits-community/proxmox/observability/
```

Next, create a `.env` file that would contain some of the env-vars we need for compose.

Following command would generate `.env` file and populate it with relevant fields:

```bash
cat <<EOF > .env
UID=$(id -u)
GID=$(id -g)
UNAME=$(whoami)
DOCKER_GID=$(getent group docker | cut -d: -f3)
HOST_IP=$(ip addr show ens18 | grep inet | head -1 | awk '{print $2}' | cut -d/ -f1)
LBPROX_IMG=lbdocker:5000/lbprox:v0.1.0
EOF
```

Now just run:

```bash
docker compose up -d
```

### Running dashboard and prom-discovery on host (less-recommended)

<details>
<summary>Click to expand</summary>

### lbprox-dashboard service

Following commands will generate a systemd unit-file that will run the `lbprox` dashboard:

```bash
lbprox dashboard unit-file | sudo tee /etc/systemd/system/lbprox-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now lbprox-dashboard
```

### lbprox-prom-discovery service

We need to run a side-car service that would query the Proxmox cluster and would construct a targets file for Prometheus to monitor

For that we have the `lbprox prom-discovery` command that would populate a target directory with this information.

You can run this command as a systemd service by following the commands below:

```bash
lbprox prom-discovery unit-file -t /mnt/workspace/lightbits-community/proxmox/observability/etc/prometheus/targets | sudo tee /etc/systemd/system/lbprox-prom-discovery.service
sudo systemctl daemon-reload
sudo systemctl enable --now lbprox-prom-discovery
```
</details>

## Logging

TBD...
