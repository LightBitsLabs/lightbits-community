
import os
import yaml

CONFIG_DIRECTORY = "lbprox/config"

def list_machine_types():
    machines_file = os.path.join(CONFIG_DIRECTORY, "flavors/flavors.yml")
    return yaml.load(open(machines_file, "r"), Loader=yaml.FullLoader)
