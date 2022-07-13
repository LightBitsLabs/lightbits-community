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
