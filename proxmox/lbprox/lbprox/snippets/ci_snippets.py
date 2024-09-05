import os
import yaml
import logging
from lbprox.ssh.ssh import SSHClient


class CloudInit(object):
    def __init__(self, ssh_client: SSHClient, storage_id: str):
        self.ssh_client = ssh_client
        self.storage_id = storage_id

    def create_user_data(self, hostname):
        user_data = {
            "hostname": hostname,
            "fqdn": hostname,
            "manage_etc_hosts": True,
            "ssh_pwauth": True,
            "disable_root": False
        }
        return user_data

    def upload_user_data(self, vmid, user_data):
        local_path = f"/tmp/{self.user_data_filename(vmid)}"
        with open(local_path, "w") as f:
            f.write("#cloud-config\n")
            yaml.dump(user_data, f)
        remote_path = f"/mnt/pve/{self.storage_id}/snippets/{self.user_data_filename(vmid)}"
        self.ssh_client.upload_file(local_path, remote_path)
        os.remove(local_path)

    def delete_cloud_init_data_files(self, vmid):
        try:
            self.ssh_client.remove_file(f"/mnt/pve/{self.storage_id}/snippets/{self.user_data_filename(vmid)}")
        except Exception as e:
            if "No such file" not in str(e):
                logging.error(f"Failed to delete user data file: {e}")
        try:
            self.ssh_client.remove_file(f"/mnt/pve/{self.storage_id}/snippets/{self.meta_data_filename(vmid)}")
        except Exception as e:
            if "No such file" not in str(e):
                logging.error(f"Failed to delete user data file: {e}")
        try:
            self.ssh_client.remove_file(f"/mnt/pve/{self.storage_id}/snippets/{self.network_data_filename(vmid)}")
        except Exception as e:
            if "No such file" not in str(e):
                logging.error(f"Failed to delete user data file: {e}")
        try:
            self.ssh_client.remove_file(f"/mnt/pve/{self.storage_id}/snippets/{self.vendor_data_filename(vmid)}")
        except Exception as e:
            if "No such file" not in str(e):
                logging.error(f"Failed to delete user data file: {e}")

    def user_data_filename(self, vmid):
        return f"user-vm-{vmid}.cfg"

    def meta_data_filename(self, vmid):
        return f"meta-vm-{vmid}.cfg"

    def network_data_filename(self, vmid):
        return f"network-vm-{vmid}.cfg"

    def vendor_data_filename(self, vmid):
        return f"vendor-vm-{vmid}.cfg"

    def user_data_volid(self, vmid):
        return f"{self.storage_id}:snippets/{self.user_data_filename(vmid)}"

    def meta_data_volid(self, vmid):
        return f"{self.storage_id}:snippets/{self.meta_data_filename(vmid)}"

    def network_data_volid(self, vmid):
        return f"{self.storage_id}:snippets/{self.network_data_filename(vmid)}"

    def vendor_data_volid(self, vmid):
        return f"{self.storage_id}:snippets/{self.vendor_data_filename(vmid)}"
