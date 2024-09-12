import os
import re
import ipaddress
import subprocess
import time
import logging
import requests
import sys
import proxmoxer

from lbprox.common.vm_tags import VMTags
from lbprox.common.constants import LAB_ACCESS_NETWORK


def access_network_ip(ip_string):
    return ipaddress.ip_address(ip_string) in LAB_ACCESS_NETWORK


def basicConfig(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')


# write a method that would run subprocess.run with the given command returning the output
def run_cmd(command, input=None, check=True, cwd=None):
    logging.debug(f"running command: {command}")
    return subprocess.run(command,
                          shell=True, input=input,
                          check=check,
                          cwd=cwd,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE).stdout.decode().strip()


def run_cmd_stream_output(command, input=None, check=True, cwd=None):
    logging.debug(f"running command: {command}")
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=cwd)
    for line in iter(proc.stdout.readline, b''):
        sys.stdout.buffer.write(line)
    proc.stdout.close()
    return proc.returncode


def list_allocations_in_cluster(pve):
    vms = list_cluster_vms(pve)
    allocations = {}
    for vm in vms:
        vmid = vm.get('vmid')
        tags = VMTags.parse_tags(vm.get('tags', ""))
        allocation_id = tags.get_allocation()
        if allocation_id not in allocations:
            allocations[allocation_id] = []
        allocations[allocation_id].append({
            "vmid": vmid,
            "name": tags.get_vm_name(),
            "role": tags.get_role(),
            "status": vm.get('status'),
            "tags": tags.str()
        })
    return allocations


def filter_tags(items, tags: VMTags=None):
    if tags is None:
        return items
    return [item for item in items if tags.is_subset(VMTags.parse_tags(item.get('tags', "")))]

def list_cluster_vms(pve, tags: VMTags=None):
    items = pve.cluster().resources.get(type="vm")
    return filter_tags(items, tags)


def list_cluster_nodes(pve, tags: VMTags=None):
    items = pve.cluster().resources.get(type="node")
    return filter_tags(items, tags)


def list_cluster_sdn(pve, tags: VMTags=None):
    items = pve.cluster().resources.get(type="sdn")
    return filter_tags(items, tags)


def list_cluster_storage(pve, tags: VMTags=None):
    items = pve.cluster().resources.get(type="storage")
    return filter_tags(items, tags)


def list_cluster_resources(pve, resource_type, tag=None):
    resources = pve.cluster().resources.get()
    # resources = run_cmd(f"pvesh get /cluster/resources --output-format json")
    # resources = json.loads(resources)
    if tag and resource_type:
        filtered_resources = [res for res in resources if res.get('type') == resource_type and tag in res.get('tags', [])]
    elif tag:
        filtered_resources = [res for res in resources if tag in res.get('tags', [])]
    elif resource_type:
        filtered_resources = [res for res in resources if res.get('type') == resource_type]
    else:
        filtered_resources = resources
    return filtered_resources


def seconds_to_human_readable(seconds):
    seconds = int(seconds)
    days = seconds // (24 * 3600)
    seconds = seconds % (24 * 3600)
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return f"{days}d {hours}h {minutes}m {seconds}s"


def get_vm_ip_address(pve, hostname, vmid, expected_ip_addresses=1, tmo=60, interval=10):
    count = 1 if (tmo == 0 or interval == 0) else (tmo // interval)

    ipv4_addresses = []
    for _ in range(count):
        network_interfaces = None
        try:
            network_interfaces = pve.nodes(hostname).qemu(vmid).agent.get("network-get-interfaces")
        except requests.exceptions.ReadTimeout as ex:
            logging.debug(f"failed to get network interfaces for {hostname}:{vmid}: {ex}. will retry in {interval} seconds")
            time.sleep(interval)
            continue
        except proxmoxer.core.ResourceException as ex:
            logging.debug(f"failed to get network interfaces for {hostname}:{vmid}: {ex}. will retry in {interval} seconds")
            time.sleep(interval)
            continue
        except Exception as ex:
            if "is not running" or "No QEMU guest agent configured" in str(ex):
                logging.warn(f"failed to get network interfaces for {hostname}:{vmid}: {ex}. will retry in {interval} seconds")
                time.sleep(interval)
                continue
            else:
                logging.error(f"failed to get network interfaces for {hostname}:{vmid}: {ex}")
                raise ex
        if network_interfaces:
            interfaces = network_interfaces.get('result', [])
            for iface in interfaces:
                iface_name = iface.get('name')
                if iface_name == 'lo':
                    continue
                skip = any([added_interface for added_interface in ipv4_addresses\
                            if iface_name == added_interface['name']])
                if skip:
                    continue
                ip_addresses = iface.get('ip-addresses', [])
                # append the list comprehension to the list of ipv4_addresses
                for ip in ip_addresses:
                    if ip.get('ip-address-type') == 'ipv4':
                        ipv4 = ip.get('ip-address', None)
                        if ipv4:
                            purpose = "access" if access_network_ip(ipv4) else "data"
                            ipv4_addresses.append({"name": iface_name, "ipv4": ipv4, "purpose": purpose})

            logging.debug(f"{hostname}:{vmid} looking for {expected_ip_addresses} ip addresses, found: {len(ipv4_addresses)}")
            if len(ipv4_addresses) >= expected_ip_addresses:
                return ipv4_addresses
        time.sleep(interval)
    return ipv4_addresses


def get_vm_status(pve, hostname, vmid):
    current_status = pve.nodes(hostname).qemu(vmid).status.current.get()
    return current_status["status"]


def wait_for_vm_status(pve, hostname, vmid, desired_status, tmo=60, interval=5):
    count = 1 if (tmo == 0 or interval == 0) else (tmo // interval)
    for _ in range(count):
        try:
            current_status = pve.nodes(hostname).qemu(vmid).status.current.get()
            if current_status["status"] == desired_status:
                return current_status["status"]
            else:
                time.sleep(interval)
        except requests.exceptions.ReadTimeout as ex:
            logging.info(f"failed to get status for {hostname}:{vmid}: {ex}. will retry in {interval} seconds")
            time.sleep(interval)
            continue
        except proxmoxer.core.ResourceException as ex:
            logging.error(f"failed to get status for {hostname}:{vmid}: type: {type(ex)} {ex}")
            time.sleep(interval)
            continue
    logging.warn(f"timed out ({tmo}s) waiting for status {desired_status} on {hostname}:{vmid}")


def get_storage_info(pve, hostname, storage_id):
    try:
        storage_list = pve.nodes(hostname).storage.get()
        return any([storage.get('storage') == storage_id for storage in storage_list])
    except Exception as ex:
        logging.error(f"failed to get storage info {hostname}:{storage_id} : {ex}")
        return False


def convert_size_to_bytes(size_str):
    """
    Converts a human-readable size string (e.g., "12G") to bytes.

    Args:
        size_str (str): The size string to convert.

    Returns:
        int: The equivalent size in bytes.
    """

    units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
    match = re.match(r'(\d+)([A-Z]+)', size_str)
    if match:
        value, unit = match.groups()
        return int(value) * units[unit]
    else:
        raise ValueError(f"Invalid size string: {size_str}")


def get_storage_path(storage_id):
    storage_path = f"/mnt/pve/{storage_id}"
    return storage_path


def get_images_path(storage_id):
    """returns the path to the images directory for the specified storage
    VM images are stored in the /mnt/pve/{storage_id}/images/{VMID} directory of the storage
    """
    local_storage_path = get_storage_path(storage_id)
    return f"{local_storage_path}/images"


# can run only on the proxmox node
def list_pci_devices(pve, hostname, cls=None):
    devices = pve.nodes(hostname).hardware.pci.get(**{"pci-class-blacklist": "05;06;07;08;0b;0c;11;ff"})
    if cls:
        class_code = {
            "network": "0x020000",
            "storage": "0x010802",
        }
        assert cls in class_code, f"invalid class: {cls}"
        return [device for device in devices if device.get('class') == class_code[cls]]
    return devices


# returns a sorted list of network VFs by lexographical order of the pci address
def list_network_vfs(pve, hostname):
    pci_devices = list_pci_devices(pve, hostname, "network")
    vfs = []
    for device in pci_devices:
        if 'Virtual Function' in device.get('device_name'):
            vfs.append(device)
    return vfs


def attached_pci_devices(pve, hostname):
    """returns a list of PCI devices attached to VMs currently allocated on the node"""
    def get_vm_config(pve, hostname, vmid):
        """we see that right after we create a VM, the config is not available
        it has the following state:
        {'digest': 'a7e9f8c42935261b36fcd1d7d6cd8cd41648da49', 'lock': 'create'}
        hence we need to wait for the config to be available
        """
        while True:
            vm_config = pve.nodes(hostname).qemu(vmid).config.get()
            if "lock" in vm_config:
                time.sleep(2)
                continue
            return vm_config
    
    vms = pve.nodes(hostname).qemu.get()
    attached_devices = []
    pci_devices = list_pci_devices(pve, hostname)
    for vm in vms:
        vmid = vm['vmid']
        vm_config = get_vm_config(pve, hostname, vmid)
        hostpci_keys = [key for key in vm_config.keys() if key.startswith('hostpci')]
        for key in hostpci_keys:
            hostpci = vm_config.get(key, None)
            if hostpci:
                attached_device_id = [device for device in pci_devices if device.get('id') in hostpci]
                # logging.info(f"vmid: {vmid} - hostpci key: {hostpci}, attached_device_id: {attached_device_id}")
                attached_devices.extend(attached_device_id)
    return attached_devices


def find_unattached_vfs(pve, hostname):
    """return a list of unattached VFs"""
    vfs_pci_devices = list_network_vfs(pve, hostname)
    attached_pci_device_list = attached_pci_devices(pve, hostname)
    attached_pci_device_ids = [device.get('id') for device in attached_pci_device_list]
    unattached_devices = [device for device in vfs_pci_devices if device.get('id') not in attached_pci_device_ids]
    return unattached_devices


def create_emulated_ssds(pve, hostname, vmid, storage_id, disk_count, size_in_bytes: int):
    """Create emulated SSDs for a VM.
    
    content create API expects size in kilobytes.
    """
    format = "raw"
    drives_info = pve.nodes(hostname).storage(storage_id).content.get(vmid=vmid)

    size_in_kb = size_in_bytes // 1024  # convert to kilobytes
    for i in range(disk_count):
        drive_idx = f"{i:02d}"
        drive_name = f"nvme{drive_idx}.{format}"
        volid = f"{storage_id}:{vmid}/{drive_name}"
        file_path = os.path.join(get_images_path(storage_id), f"{vmid}/{drive_name}")
        exists = False
        for drive_info in drives_info:
            if drive_info["volid"] == volid:
                logging.debug(f"emulated ssd file already exists at: {file_path}")
                exists = True
                break
        if not exists:
            pve.nodes(hostname).storage(storage_id).content.create(vmid=vmid, filename=drive_name, size=size_in_kb, format=format)
            logging.debug(f"created emulated ssd file at: {file_path}")


def delete_emulated_ssds(pve, hostname, vmid, storage_id):
    """Delete emulated SSDs for a VM.
    images filter will return both raw and qcow2 images
    we need to filter out the raw images, since these are the only emulated SSDs
    """
    drives_info = pve.nodes(hostname).storage(storage_id).content.get(content='images',vmid=vmid)
    for volume in drives_info:
        if "raw" == volume["format"]:
            pve.nodes(hostname).storage(storage_id).content(volume["volid"]).delete()
