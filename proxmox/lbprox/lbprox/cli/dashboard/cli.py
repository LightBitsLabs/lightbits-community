import click
import sys
from lbprox.common.utils import run_cmd
from lbprox.dashboard import dashboard


@click.group("dashboard")
def dashboard_group():
    pass


@dashboard_group.command("serve")
@click.option('-i', "--interval", required=False, default=30, help="how often to update the dashboard")
@click.option('-p', "--port", required=False, default=9000, help="port to serve the dashboard on")
@click.pass_context
def serve_dashboard(ctx, interval, port):
    dashboard.serve(ctx.obj.pve, port, interval)


@dashboard_group.command("unit-file")
@click.option('-i', "--interval", required=False, default=30, help="how often to update the dashboard")
@click.option('-p', "--port", required=False, default=9000, help="port to serve the dashboard on")
@click.option('-d', "--destination", required=False, default="-",
              help="write to destination a systemd unit file for the dashboard"
              "(may requires sudo - should be /etc/systemd/system/lbprox-dashboard.service)")
def unit_file(interval, port, destination):
    path_to_lbprox_binary = run_cmd("which lbprox")

    file_content = f"""[Unit]
Description=lbprox-dashboard
After=syslog.target network.target

[Service]
Type=simple
User=light
Restart=on-failure
RestartSec=5s
ExecStart={path_to_lbprox_binary} dashboard serve --interval {interval} --port {port}

[Install]
WantedBy=multi-user.target
"""
    if destination == "-":
        sys.stdout.write(file_content)
    else:
        with open(destination, "w") as f:
            f.write(file_content)
