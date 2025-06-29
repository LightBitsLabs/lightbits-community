import glob
import os
import yaml


CONFIG_DIRECTORY = "lbprox/config"


def load_allocation_descriptor_from_file(filename: str):
    with open(filename, "r", encoding="utf-8") as f:
        return yaml.load(f.read(), Loader=yaml.FullLoader)


def list_allocation_descriptors():
    descriptors_dir = os.path.join(CONFIG_DIRECTORY, "descriptors")
    paths = glob.glob(os.path.join(descriptors_dir, "*.yml"))
    allocation_descriptors = []
    for descriptor_path in paths:
        allocation_descriptors.append(load_allocation_descriptor_from_file(descriptor_path))
    return allocation_descriptors


def allocation_descriptor_by_name(name: str):
    """
    Retrieve an allocation descriptor by its name.

    This function searches through a list of allocation descriptors and
    returns the descriptor that matches the given name. If no descriptor
    with the specified name is found, the function returns None.

    Args:
        name (str): The name of the allocation descriptor to search for.

    Returns:
        dict or None: The allocation descriptor with the matching name,
        or None if no match is found.
    """
    descriptors = list_allocation_descriptors()
    for descriptor in descriptors:
        if descriptor["name"] == name:
            return descriptor
    return None
