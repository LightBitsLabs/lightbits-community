# Observability

## Requirements

## docker-compose installation

Run the following script to install docker and docker compose on this machine.

Most of these monitoring services will run inside a docker container, using `docker compose`.

```bash
./scripts/install_docker_ubuntu.sh
```

## lbprox CLI

Follow these instructions to install `lbprox` cli:

- [`lbprox` Installation](../lbprox/README.md#lbprox-installation)
- [Setup workdir for lbprox cli](../lbprox/README.md#setup-workdir-for-lbprox-cli)

## lbprox-dashboard service

Following commands will generate a systemd unit-file that will run the `lbprox` dashboard:

```bash
lbprox dashboard unit-file | sudo tee /etc/systemd/system/lbprox-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now lbprox-dashboard
```

## Monitoring Services (Prometheus and Grafana)

```bash
cd lightbits-community/proxmox/observability
docker compose -f docker-compose.yml up -d
```

Previous command will create the following containers:

```bash
docker ps
CONTAINER ID   IMAGE                       COMMAND                  CREATED          STATUS         PORTS                                       NAMES
6cc215082472   grafana/grafana:latest      "sh -euc /run.sh\n"      13 seconds ago   Up 3 seconds   0.0.0.0:3000->3000/tcp, :::3000->3000/tcp   grafana
7cdd0cdba5ca   grafana/loki:3.1.1          "/usr/bin/loki -conf…"   13 seconds ago   Up 3 seconds   0.0.0.0:3100->3100/tcp, :::3100->3100/tcp   loki
8bbf7e8d8e2d   prom/prometheus:latest      "/bin/prometheus --c…"   2 minutes ago    Up 2 minutes   0.0.0.0:9090->9090/tcp, :::9090->9090/tcp   prometheus
de73cbf1de39   prom/node-exporter:latest   "/bin/node_exporter …"   3 minutes ago    Up 3 minutes   9100/tcp                                    node-exporter
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

## Logging

TBD...
