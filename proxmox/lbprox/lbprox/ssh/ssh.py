import logging
import os
import paramiko

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
        client.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.hostname, username=self.username, password=self.password)
        return client

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
