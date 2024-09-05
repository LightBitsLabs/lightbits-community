import json
import click

from lbprox.common.vm_tags import VMTags
from lbprox.common import utils



@click.group("nodes")
def nodes_group():
    pass


@nodes_group.command("list")
@click.option('-t', '--tags', required=False, default=None, multiple=True,
              help="tags to filter the VMs by. ex: --tags=allocation.b178 --tags=vm.s00")
@click.pass_context
def list_cluster_nodes(ctx, tags):
    if tags is not None:
        tags = ";".join(tags)
        tags = VMTags.parse_tags(tags)
    print(json.dumps(utils.list_cluster_vms(ctx.obj.pve, tags), indent=2))
