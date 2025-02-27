import json
import os
import click
from typing import List
from lbprox.common import proxmox_rest_client
import tempfile
import tarfile
import requests


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
    return cluster_images


def _does_img_exists_on_cluster(pve, storage_id, volid, nodes):
    existing_images = _list_os_images(pve, storage_id, nodes, None)
    for _, images in existing_images.items():
        for image in images:
            if image["volid"] == volid:
                return True
    return False


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
@click.option('--force', default=False, is_flag=True,
              help="in case the image already exists, force update")
@click.pass_context
def create_os_image(ctx, storage_id, url, nodes, force):
    # NOTE: we assume here that the imgfile.tar.gz file contains a single .qcow2 file
    # which has the name imgfile.qcow2. It will be uploaded as imgfile.img
    proxmox_img_name = _proxmox_img_name(url)
    volid = f"{storage_id}:iso/{proxmox_img_name}"
    if _does_img_exists_on_cluster(ctx.obj.pve, storage_id, volid, nodes):
        print(f"image '{proxmox_img_name}' already exists on the cluster. Use --force to update.")
        if not force:
            return
        else:
            print("force update. first delete the image, then create it.")
            _delete_os_image(ctx.obj.pve, storage_id, volid, nodes)
    _create_os_image(ctx, storage_id, url, nodes)



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
    cluster_images = _list_os_images(ctx.obj.pve, storage_id, nodes, content)
    print(json.dumps(cluster_images, indent=2))


def _proxmox_img_name(url):
    basename = extract_basename(url)
    if basename.endswith(".tar.gz"):
        return basename.replace(".tar.gz", ".img")
    elif basename.endswith(".qcow2"):
        return basename.replace(".qcow2", ".img")
    elif basename.endswith(".img"):
        return basename
    elif basename.endswith(".iso"):
        return basename.replace(".iso", ".img")
    else:
        raise RuntimeError(f"unsupported file format: {basename}")



def _create_os_image(ctx, storage_id, url: str, nodes: List):
    # POST /api2/json/nodes/{node}/storage/{storage}/download-url
    # when downloading using the url we can only store .img files - so we rename the file
    # files are stored in /mnt/pve/{storage_id}/templates/iso
    pve = ctx.obj.pve
    node_list = nodes if nodes else pve.nodes.get()
    node_names = [node.get('node') for node in node_list]
    basename = extract_basename(url)
    if basename.endswith(".tar.gz"):
        _handle_tar_gz_file(ctx, node_names, storage_id, url, basename)
    else:
        # image_name is the name of the image under proxmox - usually the same as the file name with .img
        image_name = _proxmox_img_name(url)
        for node_name in node_names:
            pve.nodes(node_name).storage(storage_id).post("download-url",
                                                        url=url, filename=image_name,
                                                        content="iso")


def find_qcow2_file(directory):
    """Recursively searches for a .qcow2 file in the given directory.

    Args:
        directory (str): The directory to search in.

    Returns:
        str: The path to the .qcow2 file if found, otherwise None.
    """

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".qcow2"):
                return os.path.join(root, file)  # Return the full path
    return None  # No .qcow2 file found


def _handle_tar_gz_file(ctx, node_names, storage_id, url, basename):
    """Handle tar.gz files - this will extract and upload the .img file
    the file will be downloaded and extracted in a temporary directory
    and the .img file will be uploaded to the Proxmox node's storage"""

    with tempfile.TemporaryDirectory() as tmpdirname:
        # Download the file to the temporary directory
        response = requests.get(url, stream=True)
        tar_path = os.path.join(tmpdirname, basename)
        with open(tar_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Extract the tar.gz file in the temporary directory
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=tmpdirname)

        # Assuming the extracted file is the one we need to upload
        filename = find_qcow2_file(tmpdirname)
        if not filename:
            raise RuntimeError("No .img file found in the tar.gz archive")
        # rename file ext to .img
        os.rename(filename, filename.replace(".qcow2", ".img"))
        filename = filename.replace(".qcow2", ".img")

        username = ctx.obj.config["username"]
        password = ctx.obj.config["password"]
        for node_name in node_names:
            # we have a special case for the local file upload since
            # proxmoxer does not support it.
            client = proxmox_rest_client.ProxmoxClient(
                node_name=node_name,
                base_url=f"https://{node_name}:8006/api2/json",
                username=username,
                password=password,
                verify_ssl=False
            )

            client.upload(
                node=node_name,
                storage=storage_id,
                file_path=filename  # Filename is extracted automatically
            )

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
