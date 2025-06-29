import logging
import os
import paramiko
import re


class SSHClient(object):
    def __init__(self, hostname: str, username: str, password: str):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.client = self.connect()

    def reconnect(self):
        self.close()
        self.connect()

    def connect(self):
        client = paramiko.SSHClient()
        known_hosts = os.path.expanduser(os.path.join("~", ".ssh", "known_hosts"))

        # Load known hosts if the file exists
        if os.path.exists(known_hosts):
            client.load_host_keys(known_hosts)

        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(self.hostname, username=self.username, password=self.password)
        except paramiko.ssh_exception.BadHostKeyException:
            # Remove the old host key from known_hosts
            self._remove_host_key(self.hostname, known_hosts)
            # Try connecting again, now the host key will be accepted and saved
            client.load_host_keys(known_hosts)
            client.connect(self.hostname, username=self.username, password=self.password)

        return client

    def _remove_host_key(self, hostname, known_hosts_path):
        if not os.path.exists(known_hosts_path):
            return  # Nothing to do

        with open(known_hosts_path, "r") as f:
            lines = f.readlines()

        # Filter out lines that contain the hostname (as an exact hostname or in a list)
        new_lines = []
        for line in lines:
            if line.strip() == "" or line.startswith("#"):
                new_lines.append(line)
                continue

            # The first field (before space) contains hostnames, possibly comma-separated
            host_field = line.split(" ", 1)[0]
            hostnames = host_field.split(",")

            if hostname not in hostnames:
                new_lines.append(line)

        # Write the updated list back
        with open(known_hosts_path, "w") as f:
            f.writelines(new_lines)

    def close(self):
        if self.client:
            self.client.close()
            self.client = None

    def upload_file(self, local_path: str, remote_path: str):
        """src_path: local file path
        target_path: remote file path
        """
        sftp = self.client.open_sftp()
        sftp.put(localpath=local_path, remotepath=remote_path)
        sftp.close()

    def download_file(self, remote_path: str, local_path: str):
        """remote_path: remote file path
        local_path: local file path
        """
        sftp = self.client.open_sftp()
        sftp.get(remotepath=remote_path, localpath=local_path)
        sftp.close()

    def remove_file(self, remote_path: str):
        """remote_path: remote file path
        """
        sftp = self.client.open_sftp()
        logging.info(f"removing file: {remote_path}")
        sftp.remove(remote_path)
        sftp.close()

    def run_python_script_remotely(self, local_script_path, remote_script_path="/tmp/remote_script.py"):
        # Use SFTP to transfer the script
        sftp = self.client.open_sftp()
        sftp.put(local_script_path, remote_script_path)
        sftp.chmod(remote_script_path, 0o755)  # Ensure script is executable
        sftp.close()

        # Run the script using Python
        stdin, stdout, stderr = self.client.exec_command(f"python3 {remote_script_path}")

        # Print the output
        print("STDOUT:")
        print(stdout.read().decode())
        print("STDERR:")
        print(stderr.read().decode())

        # Clean up if needed (optional)
        # ssh.exec_command(f"rm {remote_script_path}")

    def get_network_info_via_ssh(self):
        # Get default interface and gateway
        stdin, stdout, stderr = self.client.exec_command("ip route show default")
        route_output = stdout.read().decode()
        default_iface = gateway = None

        for line in route_output.splitlines():
            if line.startswith("default"):
                parts = line.split()
                gateway = parts[2]
                default_iface = parts[4]
                break

        # Get CIDR of that interface
        stdin, stdout, stderr = self.client.exec_command(f"ip -j addr show {default_iface}")
        import json
        addr_data = json.loads(stdout.read().decode())

        cidr = None
        for addr_info in addr_data[0].get("addr_info", []):
            if addr_info["family"] == "inet":
                ip = addr_info["local"]
                prefix = addr_info["prefixlen"]
                cidr = f"{ip}/{prefix}"
                break

        return default_iface, cidr, gateway

