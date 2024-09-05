#!/usr/bin/env python3
import http.server
import socketserver
import logging
import os
import sys
import functools

from jinja2 import Template

from threading import Thread
from threading import Event
from lbprox.common import utils
from lbprox.common.vm_tags import VMTags


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
  padding: 16px;
}

tr:nth-child(even) {
  background-color: #f2f2f2;
}

th {
  background-color: #4CAF50;
  color: pink;   

};
</style>
</head>
<body>

  <h2>VM Information</h2>

  <table>
    {% for node_name, clusters_map in data.items() %}
      <tr>
        <td>Node: <a href="https://{{ node_name }}:8006/#v1:0:=node%2F{{ node_name }}:4::=contentImages:::52::2">{{ node_name }}</a></td>
      </tr>
      <tr>
        <td>
          <table>
            {% for allocation_id, vms in clusters_map.items() %}
              <tr>
                <td><b>Allocation ID: {{ allocation_id }}</b></td>
              </tr>
              <tr>
                <td>
                  <table>
                    <tr>
                      <th>id</th>
                      <th>name</th>
                      <th>cluster id</th>
                      <th>role</th>
                      <th>status</th>
                      <th>uptime</th>
                      <th>ip addresses</th>
                      <th>tags</th>
                    </tr>
                    {% for vm_metadata in vms %}
                      <tr>
                        <td><a href="https://{{ node_name }}:8006/#v1:0:=qemu%2F{{ vm_metadata['id'] }}:4:=directory:=contentImages:::52::2">{{ vm_metadata['id'] }}</a></td>
                        <td>{{ vm_metadata['name'] }}</td>
                        <td>{{ vm_metadata['cluster_id'] }}</td>
                        <td>{{ vm_metadata['role'] }}</td>
                        <td>{{ vm_metadata['status'] }}</td>
                        <td>{{ vm_metadata['uptime'] }}</td>
                        <td>{{ vm_metadata['ip_addresses'] }}</td>
                        <td>{{ vm_metadata['tags'] }}</td>
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
    function copyToClipboard() {
        var selectedText = window.getSelection().toString();
        if (selectedText.length > 0) {
            navigator.clipboard.writeText(selectedText)
                .then(() => {
                    alert("Text copied to clipboard!");
                })
                .catch((err) => {
                    console.error("Error copying text to clipboard:", err);
                });
        } else {
            alert("Please select some text first.");
        }
    }
  </script>

</body>
</html>
"""


def update_ui(pve):
    try:
        grouped_qemu_vms_by_cluster = fetch_vms(pve)
        render_template(grouped_qemu_vms_by_cluster)
    except Exception as e:
        logging.error(e)


def render_template(data):
    # Render the template with the data
    rendered_html = Template(template).render(data=data)
    # Save the rendered HTML to a file
    with open('index.html', 'w') as f:
        f.write(rendered_html)
    print("HTML file created: index.html")


def fetch_vms(pve):
    qemu_vms = utils.list_cluster_resources(pve, 'qemu')

    grouped_qemu_vms = {}
    for qemu_vm in qemu_vms:
        node_name = qemu_vm['node']
        if node_name not in grouped_qemu_vms:
            grouped_qemu_vms[node_name] = []
        grouped_qemu_vms[node_name].append(qemu_vm)

    grouped_qemu_vms_by_cluster = {}
    for node_name, vms in grouped_qemu_vms.items():
        for vm in vms:
            tags = VMTags.parse_tags(vm.get('tags', ""))
            if node_name not in grouped_qemu_vms_by_cluster:
                grouped_qemu_vms_by_cluster[node_name] = {}
            allocation_id = tags.get_allocation()
            if allocation_id not in grouped_qemu_vms_by_cluster[node_name]:
                grouped_qemu_vms_by_cluster[node_name][allocation_id] = []

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
                'ssh_access': f"ssh root@{access_ip}",
            }

            grouped_qemu_vms_by_cluster[node_name][allocation_id].append(vm_metadata)

    return grouped_qemu_vms_by_cluster


def run_web_server(port):
    web_dir = os.path.join(os.path.dirname(__file__), '.')
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


def serve(pve, port, refresh_interval):
    utils.basicConfig(debug=True)
    # UPDATE_UI_INTERVAL = 10
    global update_ui_thread
    partial_update_ui = functools.partial(update_ui, pve)
    update_ui_thread = RepeatingTimer(refresh_interval, partial_update_ui)
    update_ui_thread.start()
    run_web_server(port)


def main(args):
    pve = utils.get_proxmox_api(args.hostname)
    serve(pve, args.port, args.refresh_interval)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--refresh-interval", type=int, default=10)
    parser.add_argument("--hostname", type=str, default="localhost")
    args = parser.parse_args()
    main(args)
