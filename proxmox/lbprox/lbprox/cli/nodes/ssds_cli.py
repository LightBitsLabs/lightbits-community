import json
import click

from lbprox.common import utils


@click.group("ssds")
def nodes_ssds_group():
    pass

@nodes_ssds_group.group("emulated")
def emulated_group():
    pass


@nodes_ssds_group.group("physical")
def ssds_physical_group():
    pass


nodes_ssds_group.add_command(emulated_group)
nodes_ssds_group.add_command(ssds_physical_group)


@emulated_group.command("create")
@click.argument('hostname', required=True)
@click.argument('vmid')
@click.option('--storage-id', required=False, default="lb-local-storage")
@click.option('--disk_count', required=True)
@click.option('--size', required=True)
@click.pass_context
def create_emulated_ssds(ctx, hostname, vmid, storage_id, disk_count, size):
    utils.create_emulated_ssds(ctx.obj.pve, hostname, vmid, storage_id, disk_count, size)


@emulated_group.command("delete")
@click.argument('hostname', required=True)
@click.argument('vmid')
@click.option('-s', '--storage-id', required=False, default="lb-local-storage")
@click.pass_context
def delete_emulated_ssds(ctx, hostname, vmid, storage_id):
    utils.delete_emulated_ssds(ctx.obj.pve, hostname, vmid, storage_id)


@ssds_physical_group.command('unattached')
@click.argument('hostname', required=True)
@click.pass_context
def find_unattached_nvme_ssds(ctx, hostname):
    print(json.dumps(utils.find_unattached_nvme_ssds(ctx.obj.pve, hostname), indent=2))


@ssds_physical_group.command('reattach', help="Reattach the NVMe SSDs to the host")
@click.argument('hostname', required=True)
@click.pass_context
def reclaim_unused_nvme_ssds(ctx, hostname):
    print(json.dumps(utils.reclaim_unused_disks(ctx.obj.pve, hostname), indent=2))
