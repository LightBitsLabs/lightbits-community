import getpass
import logging
import os
import yaml

from lbprox.ssh.ssh import SSHClient
import crypt
import bcrypt


class CustomUserDataInfo(object):
    def __init__(self, local_hostname,
                 linux_username,
                 linux_password_encrypted,
                 photon_username,
                 photon_bcrypted_htpasswd):
        self.local_hostname = local_hostname
        self.linux_username = linux_username
        self.linux_password_encrypted = linux_password_encrypted
        self.photon_username = photon_username
        self.photon_bcrypted_htpasswd = photon_bcrypted_htpasswd


class CloudInit(object):
    def __init__(self, ssh_client: SSHClient, storage_id: str):
        self.ssh_client = ssh_client
        self.storage_id = storage_id

    def create_user_data(self, hostname, custom_user_data: CustomUserDataInfo=None):
        user_data = {
            "hostname": hostname,
            "fqdn": hostname,
            "manage_etc_hosts": True,
            "ssh_pwauth": True,
            "disable_root": False
        }
# chpasswd:
#   expire: false
#   list:
#   - light:$6$EblDBBq8DhlH68Ka$QW9HMrNBsq2JomLP9L4LL0Ys5TkoYk7JxLSgRrf.p2v68JMTrlbyjBvLUPFxeYQU.e3Cd01PVTMnhR3VGqCyj.
# disable_root: false
# fqdn: pve-cf-c51a-photon
# hostname: pve-cf-c51a-photon
# manage_etc_hosts: true
# ssh_authorized_keys: null
# ssh_pwauth: true
# write_files:
# - content: $6$4Hj.UnEs5M1PVEpB$TCT6VpGeF5niLUCuVPhSHXKjRMehmfB78KR5dQHTF3ry2BM8xcmtD002HINnF.mteTBeqbFcrqz4k1T8VehTH0
#   owner: light:light
#   path: /home/light/.prism/etc/ray/.htpasswd
#   permissions: '0600'


        if custom_user_data:
            user_data["chpasswd"] = {
                "list": [
                    f"{custom_user_data.linux_username}:{custom_user_data.linux_password_encrypted}"
                ],
                "expire": False
            }
            user_data["write_files"] = [
                {
                    "content": custom_user_data.photon_bcrypted_htpasswd,
                    "path": f"/home/{custom_user_data.linux_username}/.prism/etc/ray/.htpasswd",
                    "owner": f"{custom_user_data.linux_username}:{custom_user_data.linux_username}",
                    "permissions": "0600"
                }
            ]
            user_data["ssh_authorized_keys"] = []
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


def encrypt_password(username, password):
    bcrypted = bcrypt.hashpw(password.encode("utf-8"),
                             bcrypt.gensalt(rounds=12)).decode("utf-8")
    return f"{username}:{bcrypted}"

@staticmethod
def generate_custom_photon_cloud_init() -> CustomUserDataInfo:
    local_hostname = input("Enter local hostname for photon VM (default: photon): ") or "photon"

    linux_username = getpass.getpass("Enter username for VM linux user (default: light): ") or "light"
    linux_password = getpass.getpass("Enter password for VM linux default user (default: light): ") or "light"
    retype_linux_password = getpass.getpass("Retype password for VM linux default user (default: light): ") or "light"
    if linux_password != retype_linux_password:
        raise ValueError("Passwords do not match")

    linux_password_encrypted = crypt.crypt(linux_password, crypt.mksalt(crypt.METHOD_SHA512))

    photon_username = getpass.getpass("Enter username for Photon admin (default: admin): ") or "admin"
    photon_password = getpass.getpass("Enter password for Photon admin (must be at least 8 characters long): ")
    while len(photon_password) < 8:
        photon_password = getpass.getpass("Enter Photon admin password again (must be at least 8 characters long): ")
    retype_photon_password = getpass.getpass("Retype Photon admin password: ")
    if photon_password != retype_photon_password:
        raise ValueError("Passwords do not match")

    photon_bcrypted_htpasswd = encrypt_password(photon_username, photon_password)
    network_scheme = input("Enter simple or advanced settings for photon VM (simple/advanced) (default: simple): ") or "simple"

    if network_scheme not in ["simple", "advanced"]:
        raise ValueError("Invalid network scheme: must be 'simple' or 'advanced'")

    if network_scheme == "advanced":
        raise NotImplementedError("Advanced network scheme is not supported yet")

    return CustomUserDataInfo(
        local_hostname,
        linux_username,
        linux_password_encrypted,
        photon_username,
        photon_bcrypted_htpasswd,
    )
