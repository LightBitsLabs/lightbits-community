# LightOS Cluster Vagrant Environment

- [LightOS Cluster Vagrant Environment](#lightos-cluster-vagrant-environment)
  - [Setup Bare-Metal Machine With Vagrant and Libvirt Environment](#setup-bare-metal-machine-with-vagrant-and-libvirt-environment)
    - [Host Hardware Requirements](#host-hardware-requirements)
    - [Host Software Requirements And Setup](#host-software-requirements-and-setup)
      - [Ubuntu 20.04 Hypervisor](#ubuntu-2004-hypervisor)
      - [Fedora Hypervisor](#fedora-hypervisor)
      - [CentOS 7 Hypervisor](#centos-7-hypervisor)
    - [Network Requirements And Setup](#network-requirements-and-setup)
      - [Linux Bridge](#linux-bridge)
  - [Provision VMs](#provision-vms)
    - [Modifying Libvirt Storage-Pool](#modifying-libvirt-storage-pool)
      - [Grant Permissions on Ubuntu](#grant-permissions-on-ubuntu)
      - [Grant Permissions on Fedora](#grant-permissions-on-fedora)
    - [Bringing Up Three VMs](#bringing-up-three-vms)
  - [Installing Lightbits Cluster on Provisioned VMs](#installing-lightbits-cluster-on-provisioned-vms)
    - [Install Ansible and Other Dependencies](#install-ansible-and-other-dependencies)
    - [Extract Ansible playbooks and roles](#extract-ansible-playbooks-and-roles)
    - [Construct Ansible Inventory](#construct-ansible-inventory)
    - [Install LightOS on VMs Using Ansible](#install-lightos-on-vms-using-ansible)
    - [Provision Initiator](#provision-initiator)
    - [Add A New Lightbits Server (`node03`) To Existing Cluster](#add-a-new-lightbits-server-node03-to-existing-cluster)
  - [Destroy Vagrant VMs](#destroy-vagrant-vms)

A guide to deploy a three-server Lightbits cluster on a single bare-metal machine using Vagrant, KVM and Libvirt.

This tutorial will be divided into two parts:

1. Setting up Bare-Metal machine with Vagrant and Libvirt environment.
2. Installing Lightbits Cluster on provisioned virtual machines.

> **NOTE:**
>
> In case you have Vagrant already configured and running you can skip [part-1](#setup-bare-metal-machine-with-vagrant-and-libvirt-environment) and go striate to [part-2](#installing-lightbits-cluster-on-provisioned-vms)

## Setup Bare-Metal Machine With Vagrant and Libvirt Environment

Following section will guide you how to install Vagrant with Libvirt provider
on different Linux distributions.

### Host Hardware Requirements

Lightbits server requires some minimal hardware to function properly

Basically for functional testing we require the following for each Lightbits server:

1. At least 9 CPU cores.
2. At least 8GiB of RAM.
3. A fast network card to access the cluster from external initiator.

This means that we will need a server with at least:

1. At least 32 physical cores.
2. At least 32 GiB of RAM.

In order to run the Lightbits cluster.

### Host Software Requirements And Setup

The setup will need Vagrant with libvirt provider for creating VMs.

The following is a checklist of needed applications before starting the VMs.

If your host machine is already configured with Vagrant and KVM you can skip
[here](#provision-lightos-servers)

#### Ubuntu 20.04 Hypervisor

We provide [`setup_vagrant_libvirt_env_ubuntu.sh`](./scripts/setup-vagrant-libvirt/setup_vagrant_libvirt_env_ubuntu.sh) that setup Vagrant with all needed plugins and libvirt as provider.

<details>
  <summary>Click to expand setup_vagrant_libvirt_env_ubuntu.sh content</summary>

[embedmd]:#(./scripts/setup-vagrant-libvirt/setup_vagrant_libvirt_env_ubuntu.sh)
```sh
#!/usr/bin/env bash

set -a -e

# increase sudo timeout to 10m - otherwise long running update may fail, and require additional password.
echo "Defaults:$USER timestamp_timeout=10" | sudo su -c 'EDITOR="tee" visudo -f /etc/sudoers.d/timeout'

# install general purpose libraries
sudo apt-get update -y
sudo apt-get -y install \
    vim git tree jq curl \
    python3-pip \
    ethtool bridge-utils \
    sshfs sshpass

# install qemu latest version for
sudo apt-get install -y \
    qemu qemu-kvm \
    libvirt-daemon \
    libvirt-clients \
    virt-manager \
    virt-viewer \
    libvirt-dev \
    ruby-dev \
    gcc make
    

sudo systemctl enable --now libvirtd

# install vagrant
sudo apt-get -y install software-properties-common
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update -y && sudo apt-get install vagrant


# install plugins
vagrant plugin install \
               vagrant-libvirt \
               vagrant-sshfs \
               vagrant-hostmanager \
               vagrant-reload

# enable Apparmor creating nvme emulated drives
sudo apt-get install -y apparmor-profiles
echo '/var/lib/libvirt/images/*.img rwk,' | sudo tee -a /etc/apparmor.d/abstractions/libvirt-qemu
sudo systemctl restart apparmor.service

sudo systemctl restart libvirtd

# vagrant may require elevated user on some steps when running `vagrant up`
# to eliminate Vagrant from prompting for sudo password on `vagrant up` follow this [guideline](https://gist.github.com/elvetemedve/c3574e5cadbcddef0b85#file-ubuntu-linux)

sudo tee /etc/sudoers.d/vagrant > /dev/null << EOL
#
# Ubuntu Linux sudoers entries
#

# Allow passwordless startup of Vagrant with vagrant-hostsupdater.
Cmnd_Alias VAGRANT_HOSTS_ADD = /bin/sh -c echo "*" >> /etc/hosts
Cmnd_Alias VAGRANT_HOSTS_REMOVE = /usr/bin/sed -i -e /*/ d /etc/hosts
%sudo ALL=(root) NOPASSWD: VAGRANT_HOSTS_ADD, VAGRANT_HOSTS_REMOVE

# Allow passwordless startup of Vagrant with NFS synced folder option.
Cmnd_Alias VAGRANT_EXPORTS_ADD = /usr/bin/tee -a /etc/exports
Cmnd_Alias VAGRANT_NFSD_CHECK = /etc/init.d/nfs-kernel-server status
Cmnd_Alias VAGRANT_NFSD_START = /etc/init.d/nfs-kernel-server start
Cmnd_Alias VAGRANT_NFSD_APPLY = /usr/sbin/exportfs -ar
Cmnd_Alias VAGRANT_EXPORTS_REMOVE = /bin/sed -r -e * d -ibak /etc/exports
%sudo ALL=(root) NOPASSWD: VAGRANT_EXPORTS_ADD, VAGRANT_NFSD_CHECK, VAGRANT_NFSD_START, VAGRANT_NFSD_APPLY, VAGRANT_EXPORTS_REMOVE
EOL
```

</details>

#### Fedora Hypervisor

We provide [`setup_vagrant_libvirt_env_fedora36.sh`](./scripts/setup-vagrant-libvirt/setup_vagrant_libvirt_env_fedora36.sh) that setup Vagrant with all needed plugins and libvirt as provider.

Following command will deploy Vagrant and Libvirt provider:

```bash
./scripts/setup-vagrant-libvirt/setup_vagrant_libvirt_env_fedora36.sh
```

<details>
  <summary>Click to expand setup_vagrant_libvirt_env_fedora36.sh content</summary>

[embedmd]:#(./scripts/setup-vagrant-libvirt/setup_vagrant_libvirt_env_fedora36.sh)
```sh
#!/usr/bin/env bash
set -e

# increase sudo timeout to 10m - otherwise long running update may fail, and require additional password.
echo "Defaults:$USER timestamp_timeout=10" | sudo su -c 'EDITOR="tee" visudo -f /etc/sudoers.d/timeout'

sudo dnf update -y
# Setup Libvirt
sudo dnf install -y qemu-kvm libvirt libguestfs-tools virt-install rsync \
	libvirt-devel virt-top guestfs-tools \
        python3-pip sshfs sshpass

# Install Vagrant
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/fedora/hashicorp.repo
sudo dnf -y install vagrant

# fedora vagrant installs old vagrant-libvirt package which does not comply with
# latest ruby 3.1 https://github.com/vagrant-libvirt/vagrant-libvirt/issues/1445
# we need to remove the uninstalled system package and and install the new
# latest one by the plugin manager
# a patch that would enable latest vagrant-libvirt plugin installed on fedora:
# [see issue](https://github.com/vagrant-libvirt/vagrant-libvirt/issues/1403)
sudo dnf remove --noautoremove vagrant-libvirt -y
vagrant plugin install \
        vagrant-libvirt \
        vagrant-hostmanager \
        vagrant-sshfs \
        vagrant-reload

# disable SELinux to allow Libvirt to create volumes under /var/lib/libvirt/images (there are safer ways but this one is the quickest)
sudo sh -c "sed -i 's/^SELINUX=.*$/SELINUX=disabled/' /etc/sysconfig/selinux"
sudo setenforce 0

# modify qemu permission to enable image creation under $USER
sudo sed -i 's/#user = "root"/user = '\""$USER"\"'/g' /etc/libvirt/qemu.conf
sudo sed -i 's/#group = "root"/group = '\""$USER"\"'/g' /etc/libvirt/qemu.conf

# note that we set the user/group and mask permissions
sudo setfacl -m u:$USER:rwx /var/lib/libvirt/images
sudo setfacl -m g:$USER:rwx /var/lib/libvirt/images
sudo setfacl -m m::rwx /var/lib/libvirt/images

sudo gpasswd -a ${USER} libvirt

sudo systemctl enable --now libvirtd
sudo systemctl restart libvirtd

# vagrant may require elevated user on some steps when running `vagrant up`
# to eliminate Vagrant from prompting for sudo password on `vagrant up` follow this [guideline](https://gist.github.com/elvetemedve/c3574e5cadbcddef0b85#file-arch-linux-fedora)

sudo tee /etc/sudoers.d/vagrant > /dev/null << EOL
#
# Arch Linux, Fedora sudoers entries
#

# Allow passwordless startup of Vagrant with vagrant-hostsupdater.
Cmnd_Alias VAGRANT_HOSTS_ADD = /bin/sh -c echo "*" >> /etc/hosts
Cmnd_Alias VAGRANT_HOSTS_REMOVE = /usr/bin/sed -i -e /*/ d /etc/hosts
%sudo ALL=(root) NOPASSWD: VAGRANT_HOSTS_ADD, VAGRANT_HOSTS_REMOVE

# Allow passwordless startup of Vagrant with NFS synced folder option.
Cmnd_Alias VAGRANT_EXPOSTS_UPDATE = /usr/bin/chown 0\:0 /tmp/*, /usr/bin/mv -f /tmp/* /etc/exports
Cmnd_Alias VAGRANT_EXPORTS_ADD = /usr/bin/tee -a /etc/exports
Cmnd_Alias VAGRANT_NFSD_CHECK = /usr/bin/systemctl status nfs-server.service, /usr/sbin/systemctl status nfs-server.service
Cmnd_Alias VAGRANT_NFSD_START = /usr/bin/systemctl start nfs-server.service, /usr/sbin/systemctl start nfs-server.service
Cmnd_Alias VAGRANT_NFSD_APPLY = /usr/bin/exportfs -ar, /usr/sbin/exportfs -ar
Cmnd_Alias VAGRANT_EXPORTS_REMOVE = /bin/sed -r -e * d -ibak /tmp/exports, /usr/bin/cp /tmp/exports /etc/exports
%sudo ALL=(root) NOPASSWD: VAGRANT_EXPOSTS_UPDATE, VAGRANT_EXPORTS_ADD, VAGRANT_NFSD_CHECK, VAGRANT_NFSD_START, VAGRANT_NFSD_APPLY, VAGRANT_EXPORTS_REMOVE
EOL
```

</details>

#### CentOS 7 Hypervisor

> NOTE:
>
> On CentOS 7 one can't use emulated NVMe SSDs due to this issue marked as [WONT-FIX](https://bugzilla.redhat.com/show_bug.cgi?id=1595563):
>

We provide [`setup_vagrant_libvirt_env_centos7.sh`](./scripts/setup-vagrant-libvirt/setup_vagrant_libvirt_env_centos7.sh) that setup Vagrant with all needed plugins and libvirt as provider.


<details>
  <summary>Click to expand scripts/setup-vagrant-libvirt/setup_vagrant_libvirt_env_centos7.sh content</summary>

[embedmd]:#(./scripts/setup-vagrant-libvirt/setup_vagrant_libvirt_env_centos7.sh)
```sh
#!/usr/bin/env bash

# Setup Vagrant and Libvirt
sudo yum update -y
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
sudo yum -y install libvirt-daemon-kvm libvirt-client vagrant gcc-c++ make libstdc++-devel libvirt-devel sshfs
sudo systemctl enable --now libvirtd

vagrant plugin install \
        vagrant-libvirt \
        vagrant-sshfs \
        vagrant-hostmanager \
        vagrant-reload

sudo systemctl restart libvirtd

sudo usermod -a -G libvirt $( id -un )
```

</details>

### Network Requirements And Setup

Lightbits Cluster provide fast low-latency storage. To explore Lightbits full potential, it would be best if the Hypervisor has a fast NIC which can serve traffic from initiators outside the hypervisor to the Lightbits cluster.

#### Linux Bridge

To connect to the VMs from outside we will need to setup a bridge network on the hypervisor and slave the fast NIC to this bridge.

The following example makes use of static IPs allocated to the bridge, and each VM.

We will need to define a subnet of private IPs that can serve the cluster and initiators.

Provided script will help you setup bridged network for KVM to connect provisioned VMs to external network

> **NOTE**
>
> bridge's interface should use the fast nic if exists since Lightbits will expose Access/Data traffic over this bridge.
>
> A network subnet (for example: 10.10.230.0/24) to assign the bridge used by Lightbits servers as well as the initiators for data and access communication.

Example invocation of the script:

```bash
./scripts/create_bridge.sh br1 ens1f0np0 10.10.230.2/24 10.10.230.1
```

<details>
  <summary>Click to expand ./scripts/create_bridge.sh content</summary>

[embedmd]:#(./scripts/create_bridge.sh)
```sh
#!/usr/bin/env bash

set -e

# install dependencies:
function install_dependencies {
    if [ -f /etc/os-release ]; then
        # freedesktop.org and systemd
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    fi

    if [[ $OS == "Fedora Linux" ]]; then
            sudo dnf install ethtool bridge-utils -y
    elif [[ $OS == "Ubuntu" ]]; then
            sudo apt-get install ethtool bridge-utils -y
    fi
}

# validate the bridge link user providing is online
function check_eth {
    set -o pipefail # optional.
    /sbin/ethtool "$1" | grep -q "Link detected: yes"
}

function display_usage {
    echo "create a bridge network using a provided interface"
    echo "usage:"
    echo ""
    echo "  $0 [bridge_name] [iface_name] [bridge_cidr] [gateway]"
    echo ""
    echo "options:"
    echo "bridge_name - our vagrant boxes use br1 as a bridge name."
    echo "iface_name  - name of the interface we want to use under the bridge."
    echo "bridge_cidr - subnet each we will issue data IPs for each provisioned VM."
    echo "gateway     - IP address inside the provided <bridge_cidr>"
    echo ""
    echo "example:"
    echo "./create_bridge.sh br1 ens1f0np0 10.10.230.2/24 10.10.230.1"
}

# check whether user had supplied -h or --help . If yes display usage 
if [[ ( $@ == "--help") ||  $@ == "-h" ]]; then
    display_usage
    exit 0
fi 

# if less than five arguments supplied, display usage 
if [ $# -le 3 ]; then
    display_usage
    exit 1
fi

install_dependencies


export BRIDGE_NAME=${1}
export BRIDGE_INTERFACE=${2}
export BRIDGE_ADDRESS_CIDR=${3}
export BRIDGE_GATEWAY=${4}

if check_eth $BRIDGE_INTERFACE; then
    echo "The provided link for the bridge is Online!"
else
    echo "ERROR: The provided link for the bridge is Offline..existing" $BRIDGE_INTERFACE
    exit 1
fi

# n - ip format validation, m - subnet format validation
n='([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])'
m='([0-9]|[12][0-9]|3[012])'

# validate cidr with n & m 
if [[ $BRIDGE_ADDRESS_CIDR =~ ^$n(\.$n){3}/$m$ ]]; then
    printf '"%s" is a valid CIDR\n' "$BRIDGE_ADDRESS_CIDR"
else
    printf 'ERROR: "%s" is not valid CIDR..exiting\n' "$BRIDGE_ADDRESS_CIDR"
    exit 1
fi

# ip format validation
if [[ $BRIDGE_GATEWAY =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf '"%s" is a valid IP\n' "$BRIDGE_GATEWAY"
else
    printf 'ERROR: "%s" is not valid gateway address\n' "$BRIDGE_GATEWAY"
    exit 1
fi

set +e
nmcli con show "$BRIDGE_NAME" &>/dev/null
RESULT=$?
if [ $RESULT -eq 0 ]; then
	echo "bridge $BRIDGE_NAME already exists exiting."
	exit 0
fi

set -e
echo "creating bridge $BRIDGE_NAME"
# start creating the bridge
sudo systemctl stop libvirtd
sudo nmcli con add type bridge ifname $BRIDGE_NAME autoconnect yes con-name $BRIDGE_NAME stp off
sudo nmcli con modify $BRIDGE_NAME ipv4.addresses $BRIDGE_ADDRESS_CIDR ipv4.method manual
sudo nmcli con modify $BRIDGE_NAME ipv4.gateway $BRIDGE_GATEWAY
sudo nmcli con modify $BRIDGE_NAME ipv4.dns $BRIDGE_GATEWAY
sudo nmcli con add type bridge-slave autoconnect yes con-name "$BRIDGE_INTERFACE" ifname "$BRIDGE_INTERFACE" master $BRIDGE_NAME
sudo systemctl restart NetworkManager
sudo systemctl restart libvirtd
echo "net.ipv4.ip_forward = 1" | sudo tee /etc/sysctl.d/99-ipforward.conf
sudo sysctl -p /etc/sysctl.d/99-ipforward.conf
sudo nmcli con up $BRIDGE_NAME
sudo nmcli con modify $BRIDGE_NAME connection.autoconnect-slaves 1
```


</details>

## Provision VMs

Provided with this package is a generic `Vagrantfile` that expects a yaml file
name as `BOXES_VAR` environment variable which allow users to modify many things
in the setup.

We provide the `boxes.yml` file that specify the domains, boxes, network, storage, etc... of the servers for Vagrant to provision.

### Modifying Libvirt Storage-Pool

Libvirt Storage-Pool is where it keeps all images.

By default Libvirt storage-pool is deployed on boot drive at `/var/lib/libvirt/images`.

Sometimes it is useful to use a different storage-pool in case we want a faster/larger storage-drive to place our images.

For example, following commands will create a storage-pool named `my-pool`:

```bash
mkdir -p ~/.local/share/libvirt/images/
virsh --connect qemu:///system pool-define-as --name my-pool --type dir --target ~/.local/share/libvirt/images/

virsh --connect qemu:///system pool-start my-pool
virsh --connect qemu:///system pool-autostart my-pool
```

Verify storage-pool path:

```bash
virsh --connect qemu:///system pool-dumpxml my-pool | grep path
```

More information about creating storage-pool can be found [here](https://ostechnix.com/how-to-change-kvm-libvirt-default-storage-pool-location/)

Our provided `Vagrantfile` is looking at `STORAGE_POOL` env variable, and use it to create the images and emulated-ssds on this pool.

> **NOTE:**
>
> If no storage-pool provided, Vagrant will create emulated SSDs on Libvirt's default storage-pool for VM images `/var/lib/libvirt/images/`

#### Grant Permissions on Ubuntu

On Ubuntu, you will need to grant permissions for Libvirt to access this pool path using the following command:

```bash
echo '/<pool-path>/*.img rwk,' | sudo tee -a /etc/apparmor.d/abstractions/libvirt-qemu
sudo systemctl restart apparmor.service
```

#### Grant Permissions on Fedora

On Ubuntu, you will need to grant permissions for Libvirt to access this pool path by issuing the following command:

```bash
sudo setfacl -m u:$USER:rwx <storage-pool-path>
sudo setfacl -m g:$USER:rwx <storage-pool-path>
sudo setfacl -m m::rwx <storage-pool-path>
sudo systemctl restart libvirtd
```

In order to override default storage-pool (which is defaulted to name `default`), you can issue the following command:

```bash
STORAGE_POOL=my-pool vagrant up node00 node01 node02
```

### Bringing Up Three VMs

```bash
BOXES_VAR=boxes.yml vagrant up node00 node01 node02
```

Verify all three Servers are up:

```bash
BOXES_VAR=boxes.yml vagrant status node00 node01 node02
Current machine states:

node00                    running (libvirt)
node01                    running (libvirt)
node02                    running (libvirt)
```

## Installing Lightbits Cluster on Provisioned VMs

> NOTE:
>
> For detailed information about installing and configuring Lightbits Cluster please see [online-documentation](https://www.lightbitslabs.com/support/).

Once we have 3 servers running `node00`, `node01` and `node02` we are ready to install Lightbits on these VMs.

Lightbits provide an `Ansible` playbook that automates this process.

Please contact Lightbits Support team to get Lightbits Ansible collection.

### Install Ansible and Other Dependencies

We provide a simple script that will install `Ansible` at the supported version and other python3 packages we use during deployment.

This can be installed on any server, we will setup the Hypervisor server as Ansible-Controller.

Example invocation of the script:

```bash
./scripts/install_ansible_and_deps.sh
```

<details>
  <summary>Click to expand ./scripts/install_ansible_and_deps.sh content</summary>

[embedmd]:#(./scripts/install_ansible_and_deps.sh)
```sh
#!/usr/bin/env bash
set -a -x -e

function install_dependencies {
    if [[ -f /etc/os-release ]]; then
        # freedesktop.org and systemd
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    fi

    if [[ $OS == "Fedora Linux" ]]; then
            sudo dnf install python3-pip -y
    elif [[ $OS == "Ubuntu" ]]; then
            sudo apt-get install python3-pip -y
    fi
}

install_dependencies

# install Ansible and python dependencies to run LightOS deployment playbook
LANG=en_US.utf-8 pip3 install --user netaddr selinux ansible==4.2.0 python_jwt
```

</details>

### Extract Ansible playbooks and roles

In order to install LightOS software you will need to obtain `Installation Customer Addendum` from Lightbits.

This Addendum includes a private token granting access the documentation as well as the RPM repository for installing our software.

In this document under the `Ansible Package Download` section you will find instructions to download our ansible-collection.

Extract the tarball `light-app-install-environment<version>.tgz` into `~/light-app` and change into that directory.

### Construct Ansible Inventory

Ansible needs an inventory file to specify the machines to to install against, specify the way to access these machines etc...

Additionally there are some group and host specific variables that we need to define for each LightOS server before we run the ansible playbook.

For that we have the following files:

```bash
inventory
├── group_vars
│   └── all.yml
├── hosts
└── host_vars
    ├── client0.yml
    ├── node00.yml
    ├── node01.yml
    ├── node02.yml
    └── node03.yml
```

<details>
  <summary>Click to expand example inventory file content</summary>

[embedmd]:# (./inventory/hosts ini)
```ini
node00  ansible_host=node00     ansible_connection=ssh  ansible_ssh_user=vagrant ansible_ssh_pass=vagrant ansible_become_user=root ansible_become_pass=vagrant ansible_ssh_common_args='-i ~/.vagrant.d/insecure_private_key'
node01  ansible_host=node01     ansible_connection=ssh  ansible_ssh_user=vagrant ansible_ssh_pass=vagrant ansible_become_user=root ansible_become_pass=vagrant ansible_ssh_common_args='-i ~/.vagrant.d/insecure_private_key'
node02  ansible_host=node02     ansible_connection=ssh  ansible_ssh_user=vagrant ansible_ssh_pass=vagrant ansible_become_user=root ansible_become_pass=vagrant ansible_ssh_common_args='-i ~/.vagrant.d/insecure_private_key'

# new server to add to the cluster
# uncomment following line when applying the add new server to LightOS cluster
# node03        ansible_host=node03     ansible_connection=ssh  ansible_ssh_user=vagrant ansible_ssh_pass=vagrant ansible_become_user=root ansible_become_pass=vagrant ansible_ssh_common_args='-i ~/.vagrant.d/insecure_private_key'

client0 ansible_host=client0    ansible_connection=ssh  ansible_ssh_user=vagrant ansible_ssh_pass=vagrant ansible_become_user=root ansible_become_pass=vagrant ansible_ssh_common_args='-i ~/.vagrant.d/insecure_private_key'

[duros_nodes]
node00
node01
node02
# uncomment following line when applying the add new server to LightOS cluster
# node03

[duros_nodes:vars]
auto_install=true
cluster_identifier=addddeef-897e-4c5b-abef-20234abf6666

[etcd]
node00
node01
node02
# uncomment following line when applying the add new server to LightOS cluster
# node03

[initiators]
client0
```

</details>

> **NOTE:**
>
> You may need to modify the hosts file to point to the correct `private_key` path

Each node has a specific config yml under `host_vars/<node-name>.yml`

Detailed explanation of each machine can be found on [Lightbits Installation Guide](https://www.lightbitslabs.com/LDQdUm8EUnDkm93Z/v2/file/Install-Guide/html/).

> **NOTE:**
>
> In case you modified the `NETWORK_SUBNET` range and chose a different subnet
> you will need to update the IPs of all the nodes in LightOS cluster **BEFORE** running
> the installation. modify each `host_vars/<node-name>.yml` to match a unique IP address
> from the `NETWORK_SUBNET` you chose.

### Install LightOS on VMs Using Ansible

Once we configured all the parameters in the `host_vars` and `hosts` file, issue the following command:

> **NOTE:**
>
> - `path/to/virtual-light` is the path to the extracted `virtual-light.tar.gz`.
> - option `-K` will require you to provide the Ansible-Controller prevailed user password in order to install some binaries on the Ansible-Controller if they are not present.
> - rename all fields enclosed in `<>` according to your environment

Add to `path/to/virtual-light/vagrant/inventory/group_vars/all.yml` the following lines:

```yaml
datapath_config: virtual-datapath-templates
local_repo_base_url: https://dl.lightbitslabs.com/<USERKEY>/lightos-2-<Minor Ver>-x-ga/rpm/el/7/$basearch
```

And invoke our playbook:

```bash
ansible-playbook \
    -i <path/to/virtual-light>/vagrant/inventory/hosts \
    playbooks/deploy-lightos.yml \
    -vvv -K
```

Post successful installation you will see the following files on your Ansible-Controller home directory:

```bash
lightos-certificates/
lightos-default-admin-jwt
lightos-system-jwt
```

`lightos-system-jwt` will serve us to access the API as system-admin

### Provision Initiator

The following example `client_0` shows how one can start a new VM `client_0`
Which will connect and use the new LightOS storage provisioned.

```bash
BOXES_VAR=boxes.yml vagrant up client_0
```

### Add A New Lightbits Server (`node03`) To Existing Cluster

In this example we show how to add a 4th Lightbits server to the cluster.

First we will need to start another VM `node03` by issuing the following command:

```bash
# Bring up 4th server:
BOXES_VAR=boxes.yml vagrant up node03
```

Then we will need to edit `./inventory/hosts` and add `node03` to the cluster. (NOTE: lines to add this server are commented out in `hosts` file example)

Run the playbook targeting the new node and specifying `new_etcd_member=true` as well.

```bash
ansible-playbook \
    -i <path/to/virtual-light>/vagrant/inventory/hosts \
    -e new_etcd_member=true \
    --limit=node03 \
    playbooks/deploy-lightos.yml \
    -vvv -K
```

## Destroy Vagrant VMs

```bash
BOXES_VAR=boxes.yml vagrant destroy -f
```
