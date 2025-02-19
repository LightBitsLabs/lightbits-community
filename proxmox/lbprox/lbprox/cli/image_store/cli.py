import click
import re
import logging
from lbprox.common import utils


@click.group('image-store')
def image_store_group():
    pass


@image_store_group.command("create", help="Create a directory storage on all nodes in the cluster")
@click.argument('hostname', required=True)
@click.option('-s', '--storage-id', required=False, default="lb-local-storage",
              help="storage name to create")
@click.option('-d', '--block-device', required=True, type=str,
              help="block device in the form of /dev/sdX")
@click.pass_context
def create_image_storage(ctx, hostname, storage_id, block_device):
    """verify that the block device is valid and exists on all hosts in the cluster before creating the storage
    for each node in the cluster, create a directory storage with the given block device
    after successfully creating the storage on all nodes, add the storage to the cluster
    """
    assert re.match(r'^/dev/[a-zA-Z0-9\/]+$', block_device), f"invalid block device: {block_device}"
    _create_image_storage(ctx.obj.pve, hostname, storage_id, block_device)


# @image_store_group.command("create")
# @click.argument('hostname', required=True)
# @click.option('-s', '--storage-id', required=False, default="lb-local-storage",
#               help="storage name to create")
# @click.option('-d', '--block-device', required=True, type=str,
#               help="block device in the form of /dev/sdX")
# def create_image_storage(hostname, storage_id, block_device):
#     assert re.match(r'^/dev/[a-zA-Z0-9\/]+$', block_device), f"invalid block device: {block_device}"
#     pve = utils.get_proxmox_api(hostname)
#     _create_image_storage(pve, hostname, storage_id, block_device)


@image_store_group.command("delete")
@click.option('-s', '--storage-id', required=False, default="lb-local-storage",
              help="storage name to delete")
@click.pass_context
def delete_image_storage(ctx, storage_id):
    """
    Deletes the image storage with the given storage_id.

    Parameters:
    - ctx: The context object.
    - storage_id: The ID of the image storage to delete.
    """
    _delete_image_storage(ctx.obj.pve, storage_id)


# look at POST https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/disks/directory
def _create_image_storage(pve, nodename, storage_id, block_device):
    if utils.get_storage_info(pve, nodename, storage_id): # storage already exists
        return
    disks = pve.nodes(nodename).disks().list().get()
    devpaths = [disk.get('devpath') for disk in disks]
    if block_device not in devpaths:
        raise ValueError(f"block device {block_device} does not exist on node {nodename}, exists: {devpaths}")

    pve.nodes(nodename).disks().directory.post(name=storage_id,
                                                    device=block_device,
                                                    filesystem="ext4")

    storage_path = utils.get_storage_path(storage_id)
    pve.storage().create(storage=storage_id, path=storage_path,
                         type="dir", content="iso,images,snippets")


# look at DELETE https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/disks/directory/{name}
def _delete_image_storage(pve, storage_id):
    node_list = pve.nodes().get()
    for node in node_list:
        node_name = node['node']
        directories = pve.nodes(node_name).disks().directory().get()
        for directory in directories:
            if storage_id in directory['path']:
                pve.nodes(node_name).disks().directory(storage_id).delete(**{"cleanup-disks": 1, "cleanup-config": 1})
                logging.debug(f"deleting storage {storage_id} on node {node_name}")
                break
    pve.storage(storage_id).delete()
