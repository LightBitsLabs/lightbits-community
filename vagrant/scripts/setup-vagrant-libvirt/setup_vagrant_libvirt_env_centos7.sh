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
