import glob
import os
import yaml


CONFIG_DIRECTORY = "lbprox/config"


def load_allocation_descriptor_from_file(filename: str):
    with open(filename, "r") as f:
        return yaml.load(f.read(), Loader=yaml.FullLoader)


def list_allocation_descriptors():
    descriptors_dir = os.path.join(CONFIG_DIRECTORY, "descriptors")
    paths = glob.glob(os.path.join(descriptors_dir, "*.yml"))
    allocation_descriptors = []
    for descriptor_path in paths:
        allocation_descriptors.append(load_allocation_descriptor_from_file(descriptor_path))
    return allocation_descriptors


def allocation_descriptor_by_name(name: str):
    descriptors = list_allocation_descriptors()
    for descriptor in descriptors:
        if descriptor["name"] == name:
            return descriptor
    return None
