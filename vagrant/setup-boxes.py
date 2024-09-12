#!/usr/bin/env python3
import yaml
import platform


def get_user_input(key, default_value=None):
  """
  Gets user input for a specific key in the YAML structure, with an optional default value.
  """
  prompt = f"Enter {key} (default: {default_value}): "
  value = input(prompt)
  # Handle potential integer conversions
  if key in ["cpus", "ram", "ssh_port", "num_boxes", "num_nvme"]:
    try:
      value = int(value) if value else default_value  # Use default if empty
    except ValueError:
      pass
  elif key == "size":  # Handle size conversion (optional validation)
    value = value or "2G"  # Use default if empty
  return value

def create_network_config(dhcp=True):
  """
  Creates a network configuration dictionary based on DHCP selection.
  """
  return {
      "dev": "eno1",
      "dhcp": dhcp,
      "mode": "bridge",
      "type": "bridge",
  }

def create_nvme_config(name, size="2G"):
  """
  Creates an NVMe configuration dictionary with user-provided name and size.
  """
  return {
      "name": name,
      "id": name,
      "size": size,
  }

def create_box_config(num_boxes):
  """
  Creates a list of box configurations based on user input, with defaults.
  """
  boxes = []
  do_dnf_update = input("Include dnf update in provisioners (y/n)? ").lower() == "y"
  hostname = platform.node()

  for i in range(num_boxes):
    box_config = {}
    name = f"{hostname}-node{i:02}"
    box_config["name"] = get_user_input(f"Node {i+1} Name", name)
    box_config["hostname"] = get_user_input(f"Node {i+1} Hostname", name)
    box_config["description"] = "Duros Node"  # Static value
    box_config["box"] = "rockylinux/9"  # Static value
    box_config["cpus"] = get_user_input("Number of CPUs", 9)
    box_config["cputopology"] = {
        "sockets": get_user_input("Number of Sockets", 1),
        "cores": get_user_input("Cores per Socket", 1),
        "threads": get_user_input("Threads per Core", 1),
    }
    box_config["cpu_execution_cap"] = get_user_input("CPU Execution Cap (%)", 75)
    box_config["ram"] = get_user_input("RAM (MB)", 12000)
    box_config["ssh_port"] = 2201 + i  # Incrementing port number

    # Ask for static IP or DHCP
    use_dhcp = input("Use DHCP for network (y/n)? ").lower() == "y"
    box_config["public_networks"] = [create_network_config(use_dhcp)]

    box_config["provisioners"] = []
    if do_dnf_update:
      box_config["provisioners"].append({"type": "inline", "entries": ["yum update -y"]})

    # Add DHCP specific entry only if DHCP is chosen
    if use_dhcp:
      box_config["provisioners"].append({
          "type": "inline",
          "entries": [
              "nmcli connection modify eth0 ipv4.never-default yes && nmcli connection reload && nmcli device reapply eth0",
          ],
      })

    # Get number of NVMe drives
    num_nvme = int(get_user_input("Number of NVMe drives", 3))
    box_config["nvme"] = []
    for j in range(num_nvme):
      nvme_name = f"{box_config['name']}-nvme{j}.img"
      nvme_size = get_user_input(f"Size of NVMe drive {j+1} (default: 2G)", "2G")
      box_config["nvme"].append(create_nvme_config(nvme_name, nvme_size))
    boxes.append(box_config)
  return boxes


def create_client_config():
  """
  Creates a client configuration based on user input, with defaults.
  """
  client_config = {}
  client_config["name"] = get_user_input("Client Name")
  client_config["hostname"] = get_user_input("Client Hostname")
  client_config["description"] = "NVMe Client"  # Static value
  client_config["box"] = "fedora/39-cloud-base"  # Static value
  client_config["cpus"] = get_user_input("Client CPUs", 3)
  client_config["cpu_execution_cap"] = get_user_input("Client CPU Execution Cap (%)", 75)
  client_config["ram"] = get_user_input("Client RAM (MB)", 2048)
  client_config["ssh_port"] = 2204  # Static value
  client_config["public_networks"] = [
      create_network_config()
  ]

  box_config = create_box_config(num_boxes=3)  # Placeholder for calling the omitted function

  client_config["provisioners"] = []
  do_dnf_update = input("Include dnf update in provisioners (y/n)? ").lower() == "y"
  if do_dnf_update:
    client_config["provisioners"].append({"type": "inline", "entries": ["yum update -y"]})

  # Add DHCP specific entry (assuming logic from previous version)
  if client_config["public_networks"][0]["dhcp"]:
    client_config["provisioners"].append({
        "type": "inline",
        "entries": [
            "nmcli connection modify eth0 ipv4.never-default yes && nmcli connection reload && nmcli device reapply eth0",
        ],
    })

def main():
    # Assuming you'd call create_box_config and create_client_config elsewhere
    box_configs = create_box_config(num_boxes=3)
    client_config = create_client_config()
    print("box_configs: ", yaml.dumps(box_configs))
    print("client_config: ", yaml.dumps(client_config))


if __name__ == '__main__':
    main()

