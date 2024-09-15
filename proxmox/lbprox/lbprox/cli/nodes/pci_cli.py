import json
import click

from lbprox.common import utils
# import lbprox.cli.nodes.cli as nodes_cli

@click.group("pci")
def nodes_pci_group():
    pass


@nodes_pci_group.command("list-devices")
@click.argument('hostname', required=True)
@click.option('-c', "--class", "cls", 
              type=click.Choice(["network", "storage"]),
              default=None,
              help="class of the PCI device, default is all")
@click.pass_context
def list_pci_devices(ctx, hostname, cls):
    print(json.dumps(utils.list_pci_devices(ctx.obj.pve, hostname, cls), indent=2))


@nodes_pci_group.command("list-vfs")
@click.argument('hostname', required=True)
@click.pass_context
def list_vfs(ctx, hostname):
    print(json.dumps(utils.list_network_vfs(ctx.obj.pve, hostname), indent=2))


@nodes_pci_group.command("unattached-vfs")
@click.argument('hostname', required=True)
@click.pass_context
def list_unattached_vfs(ctx, hostname):
    print(json.dumps(utils.find_unattached_vfs(ctx.obj.pve, hostname), indent=2))
