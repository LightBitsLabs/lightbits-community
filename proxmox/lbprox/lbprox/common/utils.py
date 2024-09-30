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


def zero_out_host_bits(cidr):
    """Zeros out the host bits of an IP address based on the given CIDR notation.

    Args:
        cidr (str): The CIDR notation of the IP address.

    Returns:
        ipaddress.IPv4Network: The IP network with zeroed-out host bits.
    """

    network = ipaddress.ip_network(cidr)
    network_mask = network.netmask
    return network.ip & network_mask


def get_vm_ip_address(pve, hostname, vmid, expected_ip_addresses=1, tmo=60, interval=10):
    count = 1 if (tmo == 0 or interval == 0) else (tmo // interval)
    access_bridge_network = pve.nodes(hostname).network.get("vmbr0")
    assert access_bridge_network and access_bridge_network["cidr"], "we assume we have this bridge network as our access network"
    access_network = ipaddress.IPv4Interface(access_bridge_network["cidr"]).network

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
                            purpose = "access" if ipaddress.ip_address(ipv4) in access_network else "data"
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

def find_unattached_nvme_ssds(pve, hostname):
    """return a list of unattached SSD pci devices"""
    all_storage_pci_devices = list_pci_devices(pve, hostname, "storage")
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
    attached_pci_devices_list = attached_pci_devices(pve, hostname)
    attached_pci_device_ids = [device.get('id') for device in attached_pci_devices_list]
    # logging.info(f"attached pci device ids: {attached_pci_device_ids}")
    unattached_devices = [device for device in filtered_listed_devices\
                          if device.get('id') not in attached_pci_device_ids]
    # logging.info(f"unattached ssd devices: {[dev.get('id') for dev in unattached_devices]}")
    return unattached_devices


# we need a way to reattach the ssd to the host after we used it as a passthrough device for the VM
# we can do this by running the following command:
# the device is not visible in the host after the VM is stopped
# note that the device is used by the driver:

# lspci -nnk -s '0000:82:00.0'
# Kernel driver in use: vfio-pci

# we can reattach the device to the host by running the following command:
# echo 0000:82:00.0 > /sys/bus/pci/drivers/vfio-pci/unbind
# echo 0000:82:00.0 > /sys/bus/pci/drivers/nvme/bind
# or
# echo '0000:82:00.0' > /sys/bus/pci/drivers_probe

# now if we run:
# lspci -nnk -s '0000:82:00.0'
# we should see:
#   Kernel driver in use: nvme

# https://stackoverflow.com/questions/36022132/re-enumerate-and-use-pcie-ssd-in-linux-without-shutdown
def reclaim_unused_disks(pve, hostname):
    """
    Reclaims unused disks from guest VMs on a Proxmox node and reassigns them to the host.

    Args:
        hostname: Hostname of the Proxmox node.
    """
    reattached_disks = []
    # Find unattached NVMe SSD devices
    unattached_disks = find_unattached_nvme_ssds(pve, hostname)

    # Check if any unattached disks are found
    if not unattached_disks:
        logging.debug(f"No unattached NVMe SSDs found on node {hostname}")
        return reattached_disks

    # Loop through unattached disks
    for disk in unattached_disks:
        pci_address = disk.get('id')
        logging.debug(f"Reclaiming unused disk with PCI address: {pci_address} on node {hostname}")

        # Unbind the disk from the guest VM (assuming vfio-pci driver)
        try:
            with open(f"/sys/bus/pci/drivers/vfio-pci/unbind", "w") as f:
                f.write(pci_address)
            logging.debug(f"Unbound disk {pci_address} from guest VM")
        except FileNotFoundError:
            logging.debug(f"vfio-pci driver not found, skipping unbind for {pci_address}")

        # Reattach the disk to the host (using nvme driver)
        try:
            with open("/sys/bus/pci/drivers/nvme/bind", "w") as f:
                f.write(pci_address)
            logging.debug(f"Reattached disk {pci_address} to the host")
            reattached_disks.append(pci_address)
        except FileNotFoundError:
            logging.debug(f"nvme driver not found, attempting drivers_probe for {pci_address}")
            try:
                with open("/sys/bus/pci/drivers_probe", "w") as f:
                    f.write(pci_address)
                logging.debug(f"Reattached disk {pci_address} to the host using drivers_probe")
                reattached_disks.append(pci_address)
            except FileNotFoundError:
                logging.debug(f"Failed to reattach disk {pci_address} using drivers_probe")
    return reattached_disks
