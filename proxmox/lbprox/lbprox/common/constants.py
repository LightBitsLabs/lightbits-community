import os
import ipaddress

LAB_ACCESS_NETWORK = ipaddress.ip_network('192.168.16.0/20')

BASE_DIR = os.path.join(os.environ['HOME'], ".local/lbprox")
INVENTORIES_DIR = os.path.join(BASE_DIR, "inventories")
DEFAULT_CONFIG_FILE = os.path.join(BASE_DIR, "lbprox.yml")