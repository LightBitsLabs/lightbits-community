import logging
import time
import click
from lbprox.common import utils


@click.group("access-network")
def access_network_group():
    pass


@access_network_group.command("create")
@click.option('--bridge-name', default="vmbr0", help="name of the bridge (default: vmbr0)")
@click.option('--nodes', multiple=True, default=None,
              help="list of nodes to create the network - (default: all nodes)")
@click.pass_context
def create_access_bridge(ctx, bridge_name, nodes):
    # HACK: verify we have vmbr0 access network - when we skip the ui install the vmbr is not created
    # only when we deploy the proxmox using ansible on the machine everything is configured correctly
    # when we inaugurate from vm we don't have the real interface yet, so we cant really set this.
    node_list = nodes if nodes else ctx.obj.pve.nodes.get()
    node_names = [node.get('node') for node in node_list]
    ssh_username = ctx.obj.config["username"]
    ssh_password = ctx.obj.config["password"]
    for hostname in node_names:
        utils.get_or_create_access_bridge(ctx.obj.pve, hostname,
                                          bridge_name, ssh_username,
                                          ssh_password)

