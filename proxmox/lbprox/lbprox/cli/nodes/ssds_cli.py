import json
import click

from lbprox.common import utils
import lbprox.cli.nodes.cli as nodes_cli


@nodes_cli.nodes_group.group("ssds")
def nodes_ssds_group():
    pass

nodes_cli.nodes_group.add_command(nodes_ssds_group)

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
    print(json.dumps(_find_unattached_nvme_ssds(ctx.obj.pve, hostname), indent=2))


def _find_unattached_nvme_ssds(pve, hostname):
    """return a list of unattached SSD pci devices"""
    all_storage_pci_devices = utils.list_pci_devices(pve, hostname, "storage")
    #logging.info(f"all ssd devices: {[dev.get('id') for dev in all_storage_pci_devices]}")
    blacklisted_devices = ['0000:08:00.0'] # NVMe controller - /dev/nvme0n1 - should be calculated
    # TODO: calculate the used devices:
    # disks = pve.nodes(hostname).disks.list.get()
    # used_devices_dev_path = [disk["devpath"] for disk in disks if disk.get('used', None)]
    # unused_pci_devices_list = [device for device in storage_pci_devices if device.get('id') not in used_devices_dev_path]
    # logging.info(f"used devices: {used_devices_dev_path}")
    # logging.info(f"unused devices: {unused_pci_devices_list}")
    filtered_listed_devices = [device for device in all_storage_pci_devices\
                               if device.get('id') not in blacklisted_devices]
    #logging.info(f"filtered ssd devices: {[dev.get('id') for dev in filtered_listed_devices]}")
    attached_pci_devices_list = utils.attached_pci_devices(pve, hostname)
    attached_pci_device_ids = [device.get('id') for device in attached_pci_devices_list]
    # logging.info(f"attached pci device ids: {attached_pci_device_ids}")
    unattached_devices = [device for device in filtered_listed_devices\
                          if device.get('id') not in attached_pci_device_ids]
    # logging.info(f"unattached ssd devices: {[dev.get('id') for dev in unattached_devices]}")
    return unattached_devices
