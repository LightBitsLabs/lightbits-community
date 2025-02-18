import json
import os
import click
from lbprox.common import utils


@click.group("os-images")
def os_images_group():
    pass


# look at: https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/storage/{storage}/download-url
@os_images_group.command("create")
@click.option('-s', '--storage-id', required=False, default="lb-local-storage",
              help="storage ID to save the image to")
@click.option('-u', '--url', required=True, help="URL to the image file")
@click.option('--nodes', multiple=True, default=None,
              help="list of nodes to add to the zone - default is all nodes")
@click.pass_context
def create_os_image(ctx, storage_id, url, nodes):
    _create_os_image(ctx.obj.pve, storage_id, url, nodes)


@os_images_group.command("delete")
@click.option('-s', '--storage-id', required=False, default="lb-local-storage",
              help="storage ID to save the image to")
@click.option('--volid', required=True, help="format: {storage_id}:{format}/{name}")
@click.option('--nodes', multiple=True, default=None,
              help="list of nodes to add to the zone - default is all nodes")
@click.pass_context
def delete_os_image(ctx, storage_id, volid, nodes):
    print(_delete_os_image(ctx.obj.pve, storage_id, volid, nodes))


@os_images_group.command("list")
@click.option('-s', '--storage-id', required=False, default="lb-local-storage",
              help="storage ID to save the image to")
@click.option('-n', 'nodes', required=False, multiple=True, help="list images on these nodes")
@click.option('-c', '--content', required=False, default=None, type=click.Choice(["images", "iso"]),
              help="filter images by content")
@click.pass_context
def list_os_images(ctx, storage_id, nodes=None, content=None):
    """
    List the available OS images on the specified storage for the given nodes.

    Args:
        ctx (object): The context object.
        storage_id (str): The ID of the storage.
        nodes (list, optional): The list of nodes to filter the images. Defaults to None.
        content (str, optional): The content of the images to filter. Defaults to None.
    """
    _list_os_images(ctx.obj.pve, storage_id, nodes, content)


def extract_basename(url):
    """
    Extracts the basename (filename) from a URL.

    Args:
        url (str): The URL to parse.

    Returns:
        str: The basename of the URL, or None if parsing fails.
    """
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    if not parsed_url.path:
        return None
    return os.path.basename(parsed_url.path)


def _create_os_image(pve, storage_id, url: str, nodes: list):
    # POST /api2/json/nodes/{node}/storage/{storage}/download-url
    # when downloading using the url we can only store .img files - so we rename the file
    # files are stored in /mnt/pve/{storage_id}/templates/iso
    node_list = nodes if nodes else pve.nodes.get()
    node_names = [node.get('node') for node in node_list]
    for node_name in node_names:
        filename = extract_basename(url).replace(".qcow2", ".img")
        pve.nodes(node_name).storage(storage_id).post("download-url",
                                                      url=url, filename=filename, content="iso")


def _delete_os_image(pve, storage_id, volid: str, nodes: list):
    # volid is of type f"{storage_id}:iso/{name}.img"
    node_list = nodes if nodes else pve.nodes.get()
    node_names = [node.get('node') for node in node_list]
    results = []
    for node_name in node_names:
        volumes = pve.nodes(node_name).storage(storage_id).content.get()
        for volume in volumes:
            if volume["volid"] == volid:
                pve.nodes(node_name).storage(storage_id).content.delete(volid)
                results.append(f"deleted: {volid} from {node_name}")
    return results


def _list_os_images(pve, storage_id, desired_nodes, content):
    cluster_nodes = pve.nodes.get()
    if desired_nodes:
        nodes = [node["node"] for node in cluster_nodes if node["node"] in desired_nodes]
    else:
        nodes = [node["node"] for node in cluster_nodes]
    cluster_images = {}
    for node in nodes:
        if content:
            images = pve.nodes(node).storage(storage_id).content.get(content=content)
        else:
            images = pve.nodes(node).storage(storage_id).content.get()
        cluster_images[node] = images
    print(json.dumps(cluster_images, indent=2))
