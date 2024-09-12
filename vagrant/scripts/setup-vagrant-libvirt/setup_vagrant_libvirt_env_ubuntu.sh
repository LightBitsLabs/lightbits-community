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
