import click
import os
import time
import yaml
import sys
import subprocess
from lbprox.common import utils
from lbprox.common.utils import run_cmd
from lbprox.common.vm_tags import VMTags


@click.group("prom-discovery")
def prom_discovery_group():
    pass


@prom_discovery_group.command("serve")
@click.option('-i', "--interval", required=False, default=60, help="how often to update the dashboard")
@click.option('-t', "--targets-directory", required=True, type=click.Path(exists=True),
              help="directory containing the prometheus target files (ex: /etc/prometheus/targets)")
@click.pass_context
def serve_prom_ds(ctx, interval, targets_directory):
    pve = ctx.obj.pve
    while True:
        all_cluster_vms = utils.list_cluster_vms(pve, VMTags().set_role("target"))
        grouped_qemu_vms_by_allocation_id = {}
        for vm in all_cluster_vms:
            tags = VMTags.parse_tags(vm.get('tags', ""))
            allocation_id = tags.get_allocation()
            if allocation_id not in grouped_qemu_vms_by_allocation_id:
                grouped_qemu_vms_by_allocation_id[allocation_id] = []
            grouped_qemu_vms_by_allocation_id[allocation_id].append(vm)

        clusters_api_service_targets = []
        clusters_exporter_targets = []
        for allocation_id, vms in grouped_qemu_vms_by_allocation_id.items():
            cluster_exporter_targets = {
                "labels": {
                    'job': allocation_id,
                },
                "targets": []
            }
            cluster_api_service_targets = {
                "labels": {
                    'job': allocation_id,
                },
                "targets": []
            }
            for vm in vms:
                # tags = VMTags.parse_tags(vm.get('tags', ""))
                # cluster_exporter_targets['labels']['cluster_id'] = tags.get_cluster_id()
                # cluster_api_service_targets['labels']['cluster_id'] = tags.get_cluster_id()
                vmid = vm['vmid']
                node_name = vm['node']
                ip_addresses = utils.get_vm_ip_address(pve, node_name, vmid, 0, 0) if vm['status'] == 'running' else []
                access_ip = next(iter([ip_address['ipv4'] for ip_address in ip_addresses if ip_address['purpose'] == 'access']), None)
                cluster_exporter_targets["targets"].append(f"{access_ip}:8090")
                cluster_api_service_targets["targets"].append(f"{access_ip}:443")
            clusters_exporter_targets.append(cluster_exporter_targets)
            clusters_api_service_targets.append(cluster_api_service_targets)

        os.makedirs(f"{targets_directory}/lightbox-exporter", exist_ok=True)
        with open(f"{targets_directory}/lightbox-exporter/targets.yaml", "w") as f:
            f.write(yaml.dump(clusters_exporter_targets))

        os.makedirs(f"{targets_directory}/api-service", exist_ok=True)
        with open(f"{targets_directory}/api-service/targets.yaml", "w") as f:
            f.write(yaml.dump(clusters_api_service_targets))
        
        subprocess.run("curl -s -XPOST http://prometheus:9090/-/reload", shell=True)
        time.sleep(interval)

@prom_discovery_group.command("unit-file")
@click.option('-i', "--interval", required=False, default=60, help="how often to update the dashboard")
@click.option('-t', "--targets-directory", required=True, type=click.Path(exists=True),
              help="directory containing the prometheus target files (ex: /etc/prometheus/targets)")
@click.option('-d', "--destination", required=False, default="-",
              help="write to destination a systemd unit file for the dashboard"
              "(may requires sudo - should be /etc/systemd/system/lbprox-dashboard.service)")
def unit_file(interval, targets_directory, destination):
    path_to_lbprox_binary = run_cmd("which lbprox")

    file_content = f"""[Unit]
Description=lbprox-prom-discovery
After=syslog.target network.target

[Service]
Type=simple
User=light
Restart=on-failure
RestartSec=5s
ExecStart={path_to_lbprox_binary} prom-discovery serve --interval {interval} -t {targets_directory}

[Install]
WantedBy=multi-user.target
"""
    if destination == "-":
        sys.stdout.write(file_content)
    else:
        with open(destination, "w") as f:
            f.write(file_content)
