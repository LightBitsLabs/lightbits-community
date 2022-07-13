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
