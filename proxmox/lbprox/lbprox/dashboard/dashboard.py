#!/usr/bin/env python3
import argparse
import http.server
import socketserver
import logging
import os
import sys
import functools

from jinja2 import Template

from threading import Thread
from threading import Event
from lbprox.common import constants
from lbprox.common import utils
from lbprox.common.vm_tags import VMTags


DASHBOARD_BASE_DIR = os.path.join(constants.BASE_DIR, "dashboard")


class RepeatingTimer(Thread):
    def __init__(self, interval_seconds, callback):
        super().__init__()
        self.stop_event = Event()
        self.interval_seconds = interval_seconds
        self.callback = callback

    def run(self):
        while not self.stop_event.wait(self.interval_seconds):
            self.callback()

    def stop(self):
        self.stop_event.set()

# Create a Jinja2 template for the HTML structure
template = """
<!DOCTYPE html>
<html>
<head>
<style>
table {
  border-collapse: collapse;
  width: 100%;
}

th, td {
  text-align: left;
  padding: 8px 4px;
  font-size: 12px;
}

tr:nth-child(even) {
  background-color: #f2f2f2;
}

th {
  background-color: #4CAF50;
  color: pink;
}

.collapsible {
  display: block;
  border: 1px solid #ccc;
  cursor: pointer;
  padding: 18px;
}

.content {
  display: none;
  overflow: hidden;
  transition: max-height 0.2s ease-out;
}

.content.show {
  display: block;
  max-height: 1000px; /* Adjust the maximum height as needed */
}

.plus-minus-button {
  cursor: pointer;
  margin-right: 5px;
}
</style>
</head>
<body>

  <h3>Monitoring Links</h3>
  <ul>
    <li><a href="http://{{ data.hostname }}:9090" target="_blank">Prometheus</a></li>
    <li><a href="http://{{ data.hostname }}:3000" target="_blank">Grafana</a></li>
  </ul>

  <h2>VM Information</h2>
  
  <table id="vm-info-table">
    {% for node_name, clusters_map in data.grouped_vms_by_cluster.items() %}
      <tr class="collapsible">
        <td id="node-{{ node_name }}" style="padding: 2px 4px; font-size: 18px; font-weight: bold;">
          <span class="plus-minus-button" data-target="node-content-{{ node_name }}" style="font-size: 24px; font-weight: bold;">+</span>
          Node: <a href="https://{{ node_name }}:8006/#v1:0:=node%2F{{ node_name }}:4::=contentImages:::52::2" target="_blank" style="font-size: 18px;">{{ node_name }}</a>
        </td>
      </tr>
      <tr class="content" id="node-content-{{ node_name }}">
        <td>
          <table id="allocation-table-{{ node_name }}">
            {% for allocation_id, vms in clusters_map.items() %}
              <tr class="collapsible">
                <td id="allocation-{{ allocation_id }}" style="padding: 2px 4px; font-size: 18px; font-weight: bold;">
                  <span class="plus-minus-button" data-target="allocation-content-{{ allocation_id }}" style="font-size: 18px; font-weight: bold;">+</span>
                  <b>Allocation ID: {{ allocation_id }}</b>
                </td>
              </tr>
              <tr class="content" id="allocation-content-{{ allocation_id }}">
                <td>
                  <table id="vm-table-{{ allocation_id }}">
                    <tr>
                      <th>id</th>
                      <th>name</th>
                      <th>cluster id</th>
                      <th>role</th>
                      <th>status</th>
                      <th>uptime</th>
                      <th>ip addresses</th>
                      <th>lightbits version</th>
                      <th>server dashboard</th>
                      <th>volumes dashboard</th>
                    </tr>
                    {% for vm_metadata in vms %}
                      <tr>
                        <td><a href="https://{{ node_name }}:8006/#v1:0:=qemu%2F{{ vm_metadata['id'] }}:4:=directory:=contentImages:::52::2" target="_blank">{{ vm_metadata['id'] }}</a></td>
                        <td>{{ vm_metadata['name'] }}</td>
                        <td>{{ vm_metadata['cluster_id'] }}</td>
                        <td>{{ vm_metadata['role'] }}</td>
                        <td>{{ vm_metadata['status'] }}</td>
                        <td>{{ vm_metadata['uptime'] }}</td>
                        <td>{{ vm_metadata['ip_addresses'] }}</td>
                        <td>{{ vm_metadata['lightbits_version'] }}</td>
                        <td><a href="{{ vm_metadata['grafana_server_dashboard'] }}" target="_blank">server's dashboard</a></td>
                        <td><a href="{{ vm_metadata['grafana_volumes_dashboard'] }}" target="_blank">volumes dashboard</a></td>
                      </tr>
                    {% endfor %}
                  </table>
                </td>
              </tr>
            {% endfor %}
          </table>
        </td>
      </tr>
    {% endfor %}
  </table>

  <script>
    document.querySelectorAll('.plus-minus-button').forEach(button => {
      button.addEventListener('click', function() {
        const targetId = this.getAttribute('data-target');
        const targetElement = document.getElementById(targetId);
        targetElement.classList.toggle('show');

        // Toggle button text
        const buttonText = this.textContent;
        this.textContent = buttonText === '+' ? '-' : '+';
      });
    });
  </script>

</body>
</html>
"""


def update_ui(pve, observability_hostname):
    try:
        grouped_vms_by_cluster = fetch_vms(pve, observability_hostname)
        data = {
            'hostname': observability_hostname,
            'grouped_vms_by_cluster': grouped_vms_by_cluster,
        }
        render_template(data)
    except Exception as e:
        logging.error(e)


def render_template(data):
    # Render the template with the data
    rendered_html = Template(template).render(data=data)
    # Save the rendered HTML to a file
    DASHBOARD_INDEX_HTML = os.path.join(DASHBOARD_BASE_DIR, "index.html")
    with open(DASHBOARD_INDEX_HTML, 'w') as f:
        f.write(rendered_html)
    logging.info(f"HTML file created: {DASHBOARD_INDEX_HTML}")


def fetch_vms(pve, observability_hostname):
    qemu_vms = utils.list_cluster_vms(pve)

    grouped_qemu_vms = {}
    for qemu_vm in qemu_vms:
        node_name = qemu_vm['node']
        if node_name not in grouped_qemu_vms:
            grouped_qemu_vms[node_name] = []
        grouped_qemu_vms[node_name].append(qemu_vm)

    grouped_vms_by_cluster = {}
    for node_name, vms in grouped_qemu_vms.items():
        for vm in vms:
            tags = VMTags.parse_tags(vm.get('tags', ""))
            if node_name not in grouped_vms_by_cluster:
                grouped_vms_by_cluster[node_name] = {}
            allocation_id = tags.get_allocation()
            if allocation_id not in grouped_vms_by_cluster[node_name]:
                grouped_vms_by_cluster[node_name][allocation_id] = []

            vmid = vm['vmid']
            ip_addresses = utils.get_vm_ip_address(pve, node_name, vmid, 0, 0) if vm['status'] == 'running' else []
            access_ip = next(iter([ip_address['ipv4'] for ip_address in ip_addresses if ip_address['purpose'] == 'access']), None)
            ip_addresses_str = [f"{ip_address['ipv4']} ({ip_address['purpose']})" for ip_address in ip_addresses if ip_address != '']
            vm_metadata = {
                'id': vmid,
                'name': vm['name'],
                'status': vm['status'],
                'tags': vm['tags'],
                'allocation_id': tags.get_allocation(),
                'role': tags.get_role(),
                'uptime': utils.seconds_to_human_readable(vm['uptime']),
                'ip_addresses': ", ".join(ip_addresses_str),
                'cluster_id': tags.get_cluster_id(),
                'cluster_name': tags.get_cluster_name(),
                'access_ip': access_ip,
                'lightbits_version': tags.get_version() if tags.get_role() == 'target' else "",
                'ssh_access': f"ssh root@{access_ip}",
                'grafana_server_dashboard': f"http://{observability_hostname}:3000/d/Wb5yjAcGk/lightbits-server-performance-tab?orgId=1&refresh=5s&var-allocation_descriptor=instance%3D%22{access_ip}:8090%22,job%3D%228bb1%22&var-job=8bb1&var-Prometheus=P1809F7CD0C75ACF3&var-exporter_port=8090&var-instance={access_ip}:8090",
                'grafana_volumes_dashboard': f"http://{observability_hostname}:3000/d/TVDUM714z/lightbits-volumes-performance-tab?orgId=1&refresh=1m&var-allocation_descriptor=instance%3D%22{access_ip}:8090%22,job%3D%22346b%22&var-job=346b&var-instance={access_ip}:8090&var-Prometheus=P1809F7CD0C75ACF3&var-exporter_port=8090",
            }

            grouped_vms_by_cluster[node_name][allocation_id].append(vm_metadata)

    return grouped_vms_by_cluster


def run_web_server(port):
    web_dir = DASHBOARD_BASE_DIR
    os.chdir(web_dir)

    Handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", port), Handler)
    print("serving at port", port)
    httpd.serve_forever()

    update_ui_thread.stop()


# write a signal handler that would stop the repeating timer
def signal_handler(sig, frame):
    update_ui_thread.stop()
    sys.exit(0)


def serve(pve, port, refresh_interval, observability_hostname):
    os.makedirs(DASHBOARD_BASE_DIR, exist_ok=True)
    # UPDATE_UI_INTERVAL = 10
    global update_ui_thread
    partial_update_ui = functools.partial(update_ui, pve, observability_hostname)
    update_ui_thread = RepeatingTimer(refresh_interval, partial_update_ui)
    update_ui_thread.start()
    run_web_server(port)


# def main(args):
#     utils.basicConfig(debug=True)
#     pve = utils.get_proxmox_api(args.hostname)
#     serve(pve, args.port,
#           args.refresh_interval,
#           args.observability_hostname)


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--port", type=int, default=9000)
#     parser.add_argument("--refresh-interval", type=int, default=10)
#     parser.add_argument("--observability-hostname", type=str,
#                         required=True,
#                         help="hostname of the observability server")
#     args = parser.parse_args()
#     main(args)
