import click
import json
import logging
import subprocess
import time
import uuid
import re

from lbprox.common import threadpool
from lbprox.flavors import flavors
from lbprox.cli import mutex
from lbprox.allocations import allocation_descriptors
from prettytable import PrettyTable
from lbprox.common.vm_tags import VMTags

from lbprox.common import utils
from lbprox.ssh import ssh
from lbprox.snippets import ci_snippets
from lbprox.deployment import deploy


@click.group("allocations")
def allocations_group():
    pass


@allocations_group.group("list")
def allocations_list_group():
    pass

@allocations_group.group("deploy")
def allocations_deploy_group():
    pass


allocations_group.add_command(allocations_list_group)
allocations_group.add_command(allocations_deploy_group)


@allocations_list_group.command("flavors", help="list machine flavors")
@click.option('-o', '--output-format', type=click.Choice(['json', 'table']), default='table')
def list_machine_types(output_format):
    machine_type_list = flavors.list_machine_types()
    if output_format == 'table':
        table = PrettyTable(align="l")
        table.field_names = ["index", "name", "cores", "base_memory", "ssds", "ifaces", "numa"]
        types = machine_type_list["machine_types"]
        idx = 1
        for _, machine_type in types.items():
            properties = machine_type['properties']
            ssd_count = properties["ssds"].get("count", 0) if properties.get("ssds") else 0
            table.add_row([idx, machine_type["name"],
                           properties["cores"],
                           properties["base_memory"],
                           ssd_count,
                           len(properties.get("networks", [])),
                           properties["numa"]])
            idx += 1
        print(table)
    else:
        print(json.dumps(machine_type_list, indent=2))


@allocations_list_group.command("descriptors", help="list allocation descriptors available")
@click.option('-o', '--output-format', type=click.Choice(['json', 'table']), default='table')
def list_descriptors(output_format):
    descriptors = allocation_descriptors.list_allocation_descriptors()
    if output_format == 'table':
        table = PrettyTable(align="l")
        table.field_names = ["index", "name", "machine count", "description"]
        idx = 1
        for descriptor in descriptors:
            table.add_row([idx, descriptor["name"], len(descriptor["machines"]),
                           descriptor["description"]])
            idx += 1
        print(table)
    else:
        print(json.dumps(descriptors, indent=2))


@allocations_list_group.command("allocations", help="list allocations currently running in cluster")
@click.option('-o', '--output-format', type=click.Choice(['json', 'table']), default='table')
@click.pass_context
def list_allocation(ctx, output_format):
    allocations = utils.list_allocations_in_cluster(ctx.obj.pve)

    if output_format == 'table':
        table = PrettyTable(align="l")
        table.field_names = ["index", "allocation-id", "machine count", "description"]
        idx = 1
        for allocation_id, allocated_vms in allocations.items():
            description = [f"{vm['name']}:({vm['vmid']}-{vm['role']})" for vm in allocated_vms]
            table.add_row([idx, allocation_id, len(allocated_vms), "; ".join(description)])
            idx += 1
        print(table)
    else:
        print(json.dumps(allocations, indent=2))


@allocations_group.command("create")
@click.argument('hostname', required=True)
@click.option('-s', '--storage-id', required=False, default="lb-local-storage")
@click.option('-n', '--allocation-descriptor-name', required=True, type=str)
@click.option('-t', '--tags', default=None, multiple=True)
@click.option('--start-vm/--no-start-vm', default=True)
@click.option('--wait-for-ip/--no-wait-for-ip', default=True)
@click.pass_context
def create_vms(ctx, hostname, storage_id, allocation_descriptor_name,
                  tags, start_vm, wait_for_ip=True):
    if tags is not None:
        tags = ";".join(tags)
    cluster_vms = _create_vms(ctx.obj.pve,
                               hostname, storage_id,
                               allocation_descriptor_name,
                               start_vm, tags, wait_for_ip,
                               ssh_username=ctx.obj.username,
                               ssh_password=ctx.obj.password)
    if cluster_vms:
        print(json.dumps(cluster_vms, indent=2))


@allocations_group.command("delete")
@click.option('-s', '--storage-id', required=False, default="lb-local-storage")
@click.option('-a', '--allocation-id', prompt=True,
              cls=mutex.Mutex, not_required_if=["mutex"],
              type=str, help="allocation ID to deallocate")
@click.option('-t', '--tags',
              cls=mutex.Mutex, not_required_if=["allocation_id"],
              type=str, help="tags to deallocate - comma separated, ex: cname=c01,vmname=s00")
@click.pass_context
def deallocate_vms(ctx, storage_id, allocation_id=None, tags=None):
    if tags:
        tags = VMTags.parse_tags(tags)
    else:
        tags = VMTags().set_allocation(allocation_id)
    _delete_allocations(ctx.obj.pve, storage_id, ctx.obj.username, ctx.obj.password, tags)



@allocations_deploy_group.command("lightbits")
@click.option('-a', '--allocation-id', required=True, type=str,
              help="allocation id of the machines we want to deploy")
@click.option('-u', '--base-url', required=True, help="full URL for the repository holding lightbits RPMs")
@click.option('-p', '--profile-name', required=False,
              help="profile name to use for the deployment, if not provided will use the default profile")
@click.option('--run-deploy/--no-run-deploy', default=True,
              help="should we deploy the cluster, or just generate the inventory files")
@click.option('--stream-output/--no-stream-output', default=True,
              help="should we stream the ansible output to stdout")
@click.pass_context
def lightbits(ctx, allocation_id, base_url, profile_name, run_deploy, stream_output=True):
    _deploy_lightbits_cluster(ctx.obj.pve, allocation_id,
                              base_url, profile_name,
                              run_deploy, stream_output)


@allocations_deploy_group.command("initiator")
@click.option('-a', '--allocation-id', required=True, type=str,
              help="allocation id of the machines we want to deploy")
@click.option('-u', '--base-url', required=True, help="full URL for the repository holding lightbits RPMs")
@click.option('--run-deploy/--no-run-deploy', default=True,
              help="should we deploy the cluster, or just generate the inventory files")
@click.option('--stream-output/--no-stream-output', default=True,
              help="should we stream the ansible output to stdout")
@click.pass_context
def nvme_initiator(ctx, allocation_id, base_url, run_deploy, stream_output=True):
    _deploy_nvme_initiator(ctx.obj.pve, allocation_id, base_url, run_deploy, stream_output)


def _create_vm_on_proxmox(pve, ssh_client: ssh.SSHClient,
                          hostname, storage_id, vm_name,
                          machine_name, machine_info,
                          tags: VMTags):
    free_vf_pci_id = None
    try:
        # Get the next VM ID
        vmid = pve.cluster().nextid().get()

        os_image_path = f"{utils.get_storage_path(storage_id)}/template/iso/{machine_info['os_image']}.img"

        memory_bytes = utils.convert_size_to_bytes(machine_info['properties']['base_memory'])
        memory_mb = memory_bytes // 1024**2 # convert to MB
        cores = machine_info['properties']['cores']
        # Create the VM
        vm = pve.nodes(hostname).qemu.create(
            vmid=vmid,
            name=vm_name,
            memory=memory_mb,
            cores=cores,
            sockets=1,
            cpu="host",
            onboot=1,
            agent=1,
            tags=tags,
            # net0="virtio,bridge=vmbr0,firewall=1",
            #ide2="none,media=cdrom",
            scsihw="virtio-scsi-pci",
            #scsihw="virtio-scsi-single",
            virtio0=f"{storage_id}:0,import-from={os_image_path}",
            boot="order=virtio0;ide2;net0",
            citype="nocloud",
            ciuser="root",
            ide2=f"{storage_id}:cloudinit",
        )

        utils.wait_for_vm_status(pve, hostname, vmid, "stopped")

        networks = machine_info['properties']['networks']
        for i, network in enumerate(networks):
            if network["type"] == "passthrough":
                free_vfs = utils.find_unattached_vfs(pve, hostname)
                if not free_vfs:
                    raise RuntimeError("No free VF found")
                free_vf_pci_id = free_vfs[0]
                pve.nodes(hostname).qemu(vmid).config.put(**{f"hostpci0": f"{free_vf_pci_id},pcie=0"})
                logging.debug(f"attaching VF: {free_vf_pci_id} to VM: {vmid}")
            elif network["type"] == "bridge":
                # attach virtual network interface
                pve.nodes(hostname).qemu(vmid).config.put(**{network['name']:
                                                             f"virtio,bridge={network['bridge']},firewall=1"})

        ci = ci_snippets.CloudInit(ssh_client, storage_id)
        # vm_hostname = f"{hostname}-{tags.get_allocation()}-{vm_name}"
        user_data = ci.create_user_data(vm_name)
        ci.upload_user_data(vmid, user_data)
        pve.nodes(hostname).qemu(vmid).config.put(**{"cicustom":
                                                     f"user={ci.user_data_volid(vmid)}"})

        ssds = machine_info['properties'].get('ssds', None)
        if ssds:
            if ssds['type'] == "emulated":
                # this must happen before we create the VM since qm create will delete the VMID directory
                size = utils.convert_size_to_bytes(ssds['size'])
                utils.create_emulated_ssds(pve, hostname, vmid, storage_id, ssds["count"], size)
                emulated_disks_args = create_args_string(vmid, ssds["count"],
                                                         storage_id,
                                                         tags.get_allocation(),
                                                         machine_name)
                pve.nodes(hostname).qemu(vmid).config.put(args=emulated_disks_args)
            elif ssds['type'] == "passthrough":
                unattached_ssds = utils.find_unattached_nvme_ssds(pve, hostname)
                if len(unattached_ssds) < ssds["count"]:
                    raise RuntimeError(f"not enough unattached SSDs - have only {len(unattached_ssds)}, require {ssds['count']}")
                for i, pci_device in enumerate(unattached_ssds):
                    if i >= ssds["count"]:
                        break
                    logging.info(f"attaching SSD: {pci_device['id']} to VM: {vmid}")
                    pve.nodes(hostname).qemu(vmid).config.put(**{f"hostpci{i+1}": f"{pci_device['id']},pcie=0"})

        logging.debug(f"created VM {vm_name} with vmid: {vmid}")
    except subprocess.CalledProcessError as ex:
        logging.error(f"failed: {ex.stderr.decode().strip()}")
        raise ex
    except Exception as ex:
        logging.error(f"failed: {ex}")
        if free_vf_pci_id and f"PCI device '{free_vf_pci_id}' already in use by VMID" in str(ex):
            logging.error(f"failed: {ex} - should retry the VM creation")
        raise ex
    return vmid


def _extract_cluster_version(repo_base_url):
    # repo_base_url example: https://pulp02.lbits/pulp/content/releases/lightbits/3.10.1/rhel/9/67/
    # we want to extract the version from the URL which is 3.10.1 in this example using regex
    match = re.search(r'lightbits/(.[^/]+)/', repo_base_url)
    if match is None:
        return "unknown"
    return match.group(1)


def _generate_inventory(pve, allocation_id,
                        repo_base_url: str,
                        profile_name: str=None):
    cluster_vms = utils.list_cluster_vms(pve,
                                         VMTags().set_role("target").set_allocation(allocation_id))
    logging.info(f"allocation {allocation_id} has {len(cluster_vms)} VMs with role.target tag")

    # if we already have cid we will reuse it
    cluster_id = None
    for vm in cluster_vms:
        tags = VMTags.parse_tags(vm.get('tags', ""))
        cluster_id = tags.get_cluster_id()
        if cluster_id:
            break
    cluster_info = {
        'clusterId': cluster_id if cluster_id else str(uuid.uuid4()),
    }

    for vm in cluster_vms:
        tags = VMTags.parse_tags(vm.get('tags', ""))
        server_name = tags.get_vm_name()
        vmid = vm.get('vmid')
        hostname = vm.get('node')
        tags.set_cluster_id(cluster_info["clusterId"])
        tags.set_version(_extract_cluster_version(repo_base_url))
        vm_ips = utils.get_vm_ip_address(pve, hostname, vmid)
        if len(vm_ips) == 0:
            raise RuntimeError("must have at least one data IP address")
        elif len(vm_ips) == 1:
            if vm_ips[0]["purpose"] == "access":
                access_ip = vm_ips[0]["ipv4"]
            elif vm_ips[0]["purpose"] == "data":
                data_ip = vm_ips[0]["ipv4"]
        elif len(vm_ips) > 1:
            for vm_ip_info in vm_ips:
                if vm_ip_info["purpose"] == "access":
                    access_ip = vm_ip_info["ipv4"]
                elif vm_ip_info["purpose"] == "data":
                    data_ip = vm_ip_info["ipv4"]
        if not data_ip:
            logging.warning(f"failed to get data IP for VM: {vmid}")
        assert access_ip, f"failed to get access IP for VM: {vmid}"
        if not cluster_info.get("servers", None):
            cluster_info["servers"] = {}

        cluster_info["servers"][server_name] = {
            "name": server_name,
            "data_ip": data_ip,
            "access_ip": access_ip,
            "vmid": vmid,
            "tags": tags.str(),
        }
        if tags.str() != vm.get('tags', ""):
            pve.nodes(hostname).qemu(vmid).config.put(tags=tags.str())

    initiator_vms = utils.list_cluster_vms(pve,
                                           VMTags().set_role("initiator").set_allocation(allocation_id))
    logging.info(f"allocation {allocation_id} has {len(initiator_vms)} VMs with role.initiator tag")
    initiators = {}
    for vm in initiator_vms:
        tags = VMTags.parse_tags(vm.get('tags', ""))
        server_name = tags.get_vm_name()
        vmid = vm.get('vmid')
        hostname = vm.get('node')
        tags.set_cluster_id(cluster_info["clusterId"])
        vm_ips = utils.get_vm_ip_address(pve, hostname, vmid)
        if len(vm_ips) == 0:
            raise RuntimeError("must have at least one data IP address")
        elif len(vm_ips) == 1:
            if vm_ips[0]["purpose"] == "access":
                access_ip = vm_ips[0]["ipv4"]
            elif vm_ips[0]["purpose"] == "data":
                data_ip = vm_ips[0]["ipv4"]
        elif len(vm_ips) > 1:
            for vm_ip_info in vm_ips:
                if vm_ip_info["purpose"] == "access":
                    access_ip = vm_ip_info["ipv4"]
                elif vm_ip_info["purpose"] == "data":
                    data_ip = vm_ip_info["ipv4"]
        if not data_ip:
            logging.warning(f"failed to get data IP for VM: {vmid}")
        assert access_ip, f"failed to get access IP for VM: {vmid}"

        initiators[server_name] = {
            "name": server_name,
            "data_ip": data_ip,
            "access_ip": access_ip,
            "vmid": vmid,
            "tags": tags.str(),
        }
        if tags.str() != vm.get('tags', ""):
            pve.nodes(hostname).qemu(vmid).config.put(tags=tags.str())

    inventory_path = deploy.generate_inventory(allocation_id,
                                               cluster_info, initiators,
                                               repo_base_url, profile_name)
    logging.info(f"Inventory files generated at: {inventory_path}")
    return inventory_path


def _deploy_lightbits_cluster(pve, allocation_id, base_url,
                              profile_name, run_deploy, stream_output):
    inventory_path = _generate_inventory(pve, allocation_id, base_url, profile_name)
    if run_deploy:
        deploy.deploy_cluster(inventory_path, stream_output)


def _deploy_nvme_initiator(pve, allocation_id, base_url, run_deploy, stream_output=None):
    inventory_path = _generate_inventory(pve, allocation_id, base_url)
    if run_deploy:
        deploy.deploy_nvme_initiator(inventory_path, stream_output)


def _start_vm(pve, hostname, vmid, wait_for_ip, expected_ip_addresses=1, tmo=60, interval=5):
    start = time.time()
    ip_address = None
    try:
        pve.nodes(hostname).qemu(vmid).status.start.post()
        logging.debug(f"started VM: {vmid}, waiting for it to be running...")
        status = utils.wait_for_vm_status(pve, hostname, vmid, "running", tmo=tmo, interval=interval)
        if wait_for_ip:
            logging.debug(f"VM: {vmid}, waiting for it to have {expected_ip_addresses} IP addresses...")
            ip_address = utils.get_vm_ip_address(pve, hostname, vmid,
                                                 expected_ip_addresses,
                                                 tmo=120, interval=interval)
    except Exception as ex:
        logging.error(f"failed to start VM {hostname}:{vmid}: {str(ex)}")
        raise ex
    return {
        "vmid": vmid,
        "ip_address": ip_address,
        "status": status,
        "elapsed_time": time.time() - start,
    }


def generate_vm_name(node_name, allocation_id, machine_name):
    return f"{node_name}-{allocation_id}-{machine_name}"

def _create_vms(pve, hostname, storage_id, allocation_descriptor_name,
                 start_vm, tags, wait_for_ip,
                 ssh_username, ssh_password):
    allocation_info = {
        "allocation_id": str(uuid.uuid4())[:4],
        "servers": []
    }

    allocation_descriptor = allocation_descriptors.allocation_descriptor_by_name(allocation_descriptor_name)
    if not allocation_descriptor:
        logging.error(f"allocation descriptor not found: {allocation_descriptor_name}")
        return None

    ssh_client = ssh.SSHClient(hostname, ssh_username, ssh_password)
    vmids = []
    types = flavors.list_machine_types()
    for machine in allocation_descriptor["machines"]:
        machine_type = machine["machine_type"]
        machine_info = types['machine_types'][machine_type]

        vm_hostname = generate_vm_name(hostname, allocation_info["allocation_id"], machine["name"])

        new_tags = VMTags().\
            set_node(hostname).\
            set_vm_name(vm_hostname).\
            set_role(machine["role"]).\
            set_allocation(allocation_info["allocation_id"])

        # Get the next VM ID
        vmid = _create_vm_on_proxmox(pve, ssh_client, hostname,
                                     storage_id, vm_hostname,
                                     machine["name"], machine_info, new_tags)
        if not vmid:
            logging.error(f"failed to allocate VM: {vm_hostname}")
            return None
        vmids.append(vmid)

    if start_vm or wait_for_ip:
        expected_ip_addresses = 2
        args = [(pve, hostname, vmid, wait_for_ip, expected_ip_addresses) for vmid in vmids]
        vm_info = threadpool.run_with_threadpool(_start_vm, args,
                                                 desc="starting VMs", max_workers=10)
        allocation_info["servers"].extend(vm_info)
    else:
        for vmid in vmids:
            allocation_info["servers"].append({"vmid": vmid})

    ssh_client.close()
    return allocation_info


def _delete_allocations(pve, storage_id, ssh_username, ssh_password, tags: VMTags):
    vms = utils.list_cluster_vms(pve, tags)

    def _del_allocation(vm):
        vmid = vm.get('vmid')
        hostname = vm.get('node')
        ssh_client = ssh.SSHClient(hostname, ssh_username, ssh_password)
        _delete_allocation(pve, ssh_client, hostname, storage_id, vmid)
        ssh_client.close()

    args = [(vm,) for vm in vms]
    threadpool.run_with_threadpool(_del_allocation,
                                   args,
                                   desc="deleting VMs", max_workers=10)


def create_args_string(vmid, disk_count, storage_id, allocation_id, vm_name):
    images_path = utils.get_images_path(storage_id)
    args = ""
    for i in range(disk_count):
        idx = f"{i:02d}"
        serial_number = f"{allocation_id}-{vm_name}"
        args += f" -drive file={images_path}/{vmid}/nvme{idx}.raw,if=none,id=nvme{idx} -device nvme,drive=nvme{idx},serial={serial_number}-nvme{idx}"
    return args


def _delete_allocation(pve, ssh_client: ssh.SSHClient, hostname, storage_id, vmid):
    # stop the VM if started
    try:
        pve.nodes(hostname).qemu(vmid).status.stop.post(timeout=60)
        utils.wait_for_vm_status(pve, hostname, vmid, "stopped")
        utils.delete_emulated_ssds(pve, hostname, vmid, storage_id)
        pve.nodes(hostname).qemu(vmid).delete()

        ci = ci_snippets.CloudInit(ssh_client, storage_id)
        ci.delete_cloud_init_data_files(vmid)
    except Exception as ex:
        logging.error(f"failed to delete allocation {hostname}:{vmid}: {str(ex)}")
