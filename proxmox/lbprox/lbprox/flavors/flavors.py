
import os
import yaml

CONFIG_DIRECTORY = "lbprox/config"

def list_machine_types():
    machines_file = os.path.join(CONFIG_DIRECTORY, "flavors/flavors.yml")
    with open(machines_file, 'r') as f:
        return yaml.load(f, Loader=yaml.FullLoader)
