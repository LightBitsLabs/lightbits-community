#!/usr/bin/env python3
import os
from jinja2 import Template
import subprocess
import logging
from lbprox.common import utils
from lbprox.common.constants import INVENTORIES_DIR


hosts_template = """
{%- for target_name, server_info in data.targets.items() %}
{{ target_name }}    ansible_host={{ server_info.access_ip }}  ansible_connection=ssh  ansible_ssh_user=root  ansible_ssh_pass=light  ansible_become_user=root ansible_become_pass=light
{%- endfor %}
{%- for client_name, initiator_info in data.initiators.items() %}
{{ client_name }}    ansible_host={{ initiator_info.access_ip }}  ansible_connection=ssh  ansible_ssh_user=root  ansible_ssh_pass=light  ansible_become_user=root  ansible_become_pass=light
{%- endfor %}

[duros_nodes]
{% for target_name, server_info in data.targets.items() %}
{{ target_name }}
{%- endfor %}

[etcd]
{% for target_name, server_ip in data.targets.items() %}
{{ target_name }}
{%- endfor %}

[initiators]
{%- for client_name, initiator_info in data.initiators.items() %}
{{ client_name }}
{%- endfor %}

"""

group_vars_template = """
---
enable_iptables: false
persistent_memory: false
start_discovery_service_retries: 5

local_repo_base_url: {{ data.repo_base_url }}

cluster_info:
  clusterId: {{ data.cluster_info.clusterId }}

"""

host_vars_template = """
---
datapath_config: {{ data.profile_name }}
health_state_timeout_ms: '15000'
# lightfieldMode: ''
name: {{ data.server.name }}
nodes:
- instanceID: 0
  data_ip: {{ data.server.data_ip }}
  ec_enabled: {{ data.ec_enabled }}
  failure_domains:
  - {{ data.server.name }}
  storageDeviceLayout:
    allowCrossNumaDevices: true
    deviceMatchers:
    - partition == false
    initialDeviceCount: 4
    maxDeviceCount: 12
  #data_ifaces:
  #- bootproto: static
  #  conn_name: eth1
  #  ifname: eth1
  #  ip4: {{ data.server.data_ip }}/27
"""

docker_compose_template = """---
services:
  lb-ansible: &lb-ansible-base
    image: {{ data.lb_ansible_img }} # (1) update with real image path.
    network_mode: host
    environment:
    - UID=1000      # (2) id retrieved by `id -u`
    - GID=1000      # (3) grp-id retrieved by `id -g`
    - UNAME=myuser  # (4) username retrieved by `id -un`
    - ANSIBLE_LOG_PATH=/inventory/logs/ansible.log
    - ANSIBLE_FORCE_COLOR=True
    working_dir: /ansible
    volumes:
    - ${WORKSPACE_TOP}/light-app:/ansible # (5) contains ansible-playbook and roles
    - ./:/inventory # (6) contains group_vars, host vars and hosts.

  deploy:
    <<: *lb-ansible-base
    container_name: lb-ansible-deploy
    command: >
      sh -c 'mkdir -p /inventory/logs && \\
          ansible-playbook \\
          -i /inventory/hosts \\
          -e system_jwt_path=/inventory/lightos-certificates/lightos_jwt \\
          -e lightos_default_admin_jwt=/inventory/lightos-certificates/lightos_default_admin_jwt \\
          -e certificates_directory=/inventory/lightos-certificates \\
          -e inject_jwt_to_nodes=true \\
          playbooks/deploy-lightos.yml -vvv'

  cleanup:
    <<: *lb-ansible-base
    container_name: lb-ansible-cleanup
    command: >
      sh -c 'mkdir -p /inventory/logs && \\
          ansible-playbook \\
          -i /inventory/hosts \\
          playbooks/cleanup-lightos-playbook.yml --tags=cleanup -vvv'

  deploy-initiator:
    <<: *lb-ansible-base
    container_name: lb-ansible-deploy-initiator
    command: >
      sh -c 'mkdir -p /inventory/logs && \\
          ansible-playbook \\
          -i /inventory/hosts \\
          playbooks/deploy-nvme-tcp-initiator.yml --tags=install-client -vvv'

"""

# write a function that would render the template and save it to a file
def render_template(template, data, output_file):
    rendered_template = Template(template).render(data=data)
    with open(output_file, 'w') as f:
        f.write(rendered_template)


def inventory_directory(allocation_id: str):
    return os.path.join(INVENTORIES_DIR, allocation_id)


def inventory_directory_exists(allocation_id: str):
    return os.path.exists(inventory_directory(allocation_id))


def generate_inventory(allocation_id: str, cluster_info, initiators,
                       repo_base_url: str, profile_name: str=None,
                       ec_enabled: bool=False):
    cluster_inventory_dir = inventory_directory(allocation_id)
    os.makedirs(cluster_inventory_dir, exist_ok=True)

    context = {
        'lb_ansible_img': 'lbdocker:5000/lb-ansible:v9.1.0',
    }
    render_template(docker_compose_template,
                    context,
                    os.path.join(cluster_inventory_dir, 'docker-compose.yml'))

    hosts_path = os.path.join(cluster_inventory_dir, 'hosts')
    data = {
        'targets': cluster_info['servers'],
        'initiators': initiators,
    }
    render_template(hosts_template, data, hosts_path)

    group_vars_info = {
        "cluster_info": {
            "clusterId": cluster_info['clusterId'],
        },
        "repo_base_url": repo_base_url
    }
    group_vars_dir = os.path.join(cluster_inventory_dir, "group_vars")
    group_vars_all_path = os.path.join(group_vars_dir, 'all.yml')
    os.makedirs(group_vars_dir, exist_ok=True)
    render_template(group_vars_template,
                    group_vars_info,
                    group_vars_all_path)

    host_vars_dir = os.path.join(cluster_inventory_dir, "host_vars")
    os.makedirs(host_vars_dir, exist_ok=True)
    for server_name, server_info in cluster_info['servers'].items():
        profile_name = profile_name if profile_name else 'virtual-datapath-templates'
        data = {
            'profile_name': profile_name,
            'server': server_info,
	    'ec_enabled': str(ec_enabled).lower()
        }
        host_file_path = os.path.join(host_vars_dir, f'{server_name}.yml')
        render_template(host_vars_template,
                        data, host_file_path)
    return cluster_inventory_dir


def deploy_cluster(inventory_dir: str, stream_output: bool=True):
    cmd = "docker compose run --rm -i deploy"
    try:
        if stream_output:
            utils.run_cmd_stream_output(cmd, cwd=inventory_dir)
        else:
            utils.run_cmd(cmd, cwd=inventory_dir)
    except subprocess.CalledProcessError as e:
        logging.error(e.stderr.decode().strip())
    except Exception as e:
        logging.error(e)


def deploy_nvme_initiator(inventory_dir: str, stream_output: bool=True):
    cmd = "docker compose run --rm -i deploy-initiator"
    try:
        if stream_output:
            utils.run_cmd_stream_output(cmd, cwd=inventory_dir)
        else:
            utils.run_cmd(cmd, cwd=inventory_dir)
    except subprocess.CalledProcessError as e:
        logging.error(e.stderr.decode().strip())
    except Exception as e:
        logging.error(e)


# def main():
#     repo_base_url = 'https://pulp02/pulp/content/releases/lightbits/3.10.1/rhel/9/67/'
#     cluster_info = {
#         'clusterId': str(uuid.uuid4()),
#         'servers': {
#             'server00': {
#                 'name': 'server00',
#                 'access_ip': '192.168.25.27',
#                 'data_ip': '10.101.1.10'
#             },
#             'server01': {
#                 'name': 'server01',
#                 'access_ip': '192.168.25.28',
#                 'data_ip': '10.101.1.11'
#             },
#             'server02': {
#                 'name': 'server02',
#                 'access_ip': '192.168.25.29',
#                 'data_ip': '10.101.1.12'
#             }
#         }
#     }
#     generate_inventory(cluster_info, repo_base_url)


# if __name__ == '__main__':
#     main()
