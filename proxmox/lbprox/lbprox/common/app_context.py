import logging
import os
import yaml

import http.client
import urllib3
http.client.HTTPConnection.debuglevel = 0

import proxmoxer as proxmox

HOME_DIR = os.path.expanduser("~")
LBPROX_YAML_DEFAULT_PATH = os.path.join(HOME_DIR, ".local", "lbprox", "lbprox.yml")

class TemporalConfig(object):
    def __init__(self, config: dict):
        temporal_config = config.get("temporal", {})
        self.endpoint = temporal_config.get("endpoint")
        tls_config = temporal_config.get("tls", None)
        self.ca_cert = tls_config.get("ca_cert")
        self.client_pem = tls_config.get("client_pem")
        self.client_key = tls_config.get("client_key")

class AppContext(object):
    _instance = None

    def __init__(self, username: str=None, password: str=None,
                 config_file: str=LBPROX_YAML_DEFAULT_PATH, debug: bool=False):
        self.debug = debug
        self.config_file = config_file
        config_from_file = self.load_config(config_file)
        if username is not None:
            config_from_file["username"] = username
        if password is not None:
            config_from_file["password"] = password
        config_from_file["debug"] = debug
        # if config_from_file.get("light_app_path", None) is None:
        #     workspace_top = os.environ.get("WORKSPACE_TOP", None)
        #     assert workspace_top,\
        #         "light_app_path not provided, please provide it in the config file or as an environment variable: WORKSPACE_TOP"
        #     light_app_path = os.path.join(workspace_top, "light-app")
        #     assert os.path.exists(light_app_path), \
        #         f"light-app path does not exist: '{light_app_path}'."\
        #         " Please provide it in the config file or as an environment variable: WORKSPACE_TOP"
            # config_from_file["light_app_path"] = light_app_path
        assert config_from_file.get("username", None),\
            "username not provided, please provide it in the config file or as a command line argument"
        assert config_from_file.get("password", None),\
            "password not provided, please provide it in the config file or as a command line argument"

        self.config = config_from_file
        logging.debug(f"loaded config from: {config_file} merged config: {self.config}")
        self.pve, last_active_hostname = self.get_proxmox_api(self.config)
        self.temporal_config = self._get_temporal_config(self.config)
        assert self.pve, f"failed to create Proxmox API object: {self.config}"
        # update last know active node
        last_active = self.config.get("last_active", None)
        if last_active is None or last_active != last_active_hostname:
            self.config["last_active"] = last_active_hostname
            self.save_config(config_file, self.config)
        assert self.pve, f"failed to create Proxmox API object: {self.config}"
        # self.ssh_client = ssh.SSHClient(last_active_hostname, "root", "light")
        # assert self.ssh_client, f"failed to create SSH client object: {last_active_hostname}"


    def _get_temporal_config(self, config: dict) -> TemporalConfig:
        return TemporalConfig(config)
    
    def load_config(self, config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.load(f.read(), Loader=yaml.FullLoader)

    def save_config(self, config_file, config):
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

    def get_proxmox_api(self, config, timeout=15):
        # Create a Proxmox API object
        last_active = config.get("last_active", None)
        if last_active:
            try:
                urllib3.HTTPConnectionPool(last_active, maxsize=10, block=True)
                pve = proxmox.ProxmoxAPI(host=last_active,
                                         user=f"{config['username']}@pam",
                                         password=config['password'],
                                         verify_ssl=False,
                                         timeout=timeout)
                return pve, last_active
            except Exception as ex:
                logging.warning(f"failed to connect to last active: {last_active}. will look for new active: {ex}")

        for node in config["nodes"]:
            hostname = node.get('hostname')
            try:
                urllib3.HTTPConnectionPool(hostname, maxsize=10, block=True)
                pve = proxmox.ProxmoxAPI(host=hostname,
                                         user=f"{config['username']}@pam",
                                         password=config['password'],
                                         verify_ssl=False,
                                         timeout=timeout)
                return pve, hostname
            except Exception as ex:
                logging.warning(f"failed to connect to {hostname}: {ex}. keep looking...")
        return None, None

    @classmethod
    def create(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = cls(*args, **kwargs)
        return cls._instance
