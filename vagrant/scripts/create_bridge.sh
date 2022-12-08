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
    echo
    echo "create a bridge network using a provided interface"
    echo "usage:"
    echo ""
    echo "  $0 [bridge_name] [iface_name] [bridge_cidr] [gateway]"
    echo ""
    echo "options:"
    echo "bridge_name - our vagrant boxes use br1 as a bridge name."
    echo "iface_name  - name of the interface we want to use under the bridge."
    echo "bridge mode - static or dhcp"
    echo "bridge_cidr - subnet each we will issue data IPs for each provisioned VM."
    echo "gateway     - IP address inside the provided <bridge_cidr>"
    echo ""
    echo "example:"
    echo "For Static IP configuration: ./create_bridge.sh br1 ens1f0np0 static 10.10.230.2/24 10.10.230.1"
    echo "For DHCP configuration: ./create_bridge.sh br1 ens1f0np0 dhcp"
    echo
}

# check whether user had supplied -h or --help . If yes display usage 
if [[ ( $@ == "--help") ||  $@ == "-h" ]]; then
    display_usage
    exit 0
fi 

# if less than three arguments supplied, display usage 
if [ $# -le 2 ]; then
    display_usage
    exit 1
fi

export BRIDGE_NAME=${1}
export BRIDGE_INTERFACE=${2}
export BRIDGE_MODE=${3}
export BRIDGE_ADDRESS_CIDR=${4}
export BRIDGE_GATEWAY=${5}

if [[ $BRIDGE_MODE != "static" && $BRIDGE_MODE != "dhcp" ]] ;then
   printf "\nWrong value for bridge mode, valid values are static or dhcp\n"
   display_usage
   exit 1
fi

install_dependencies

if check_eth $BRIDGE_INTERFACE; then
    echo "The provided link for the bridge is Online!"
else
    echo "ERROR: The provided link for the bridge is Offline..existing" $BRIDGE_INTERFACE
    exit 1
fi


# validate cidr with n & m 
# n - ip format validation, m - subnet format validation
if [[ $BRIDGE_MODE == "static" ]] ; then
    n='([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])'
    m='([0-9]|[12][0-9]|3[012])'
    # CIDR value validation
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
if [[ $BRIDGE_MODE == "static" ]] ; then
    sudo nmcli con modify $BRIDGE_NAME ipv4.addresses $BRIDGE_ADDRESS_CIDR ipv4.method manual
    sudo nmcli con modify $BRIDGE_NAME ipv4.gateway $BRIDGE_GATEWAY
    sudo nmcli con modify $BRIDGE_NAME ipv4.dns $BRIDGE_GATEWAY
else 
        #sudo nmcli con modify $BRIDGE_NAME ipv4.addresses $BRIDGE_ADDRESS_CIDR ipv4.method auto
        sudo nmcli con modify $BRIDGE_NAME ipv4.method auto
fi
sudo nmcli con add type bridge-slave autoconnect yes con-name "$BRIDGE_INTERFACE" ifname "$BRIDGE_INTERFACE" master $BRIDGE_NAME
echo "net.ipv4.ip_forward = 1" | sudo tee /etc/sysctl.d/99-ipforward.conf
sudo sysctl -p /etc/sysctl.d/99-ipforward.conf
sudo nmcli con modify $BRIDGE_NAME connection.autoconnect-slaves 1
sudo nmcli con up $BRIDGE_NAME
sudo systemctl restart NetworkManager
sudo systemctl restart libvirtd
