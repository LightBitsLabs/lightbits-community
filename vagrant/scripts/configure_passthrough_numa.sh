#!/usr/bin/bash


# Show usage via commandline arguments
usage() {
  echo "Usage: ./$0 <vm_name>"
  echo "If no vm name is provided, the system will find the running vagrant vms with 'node' in the name and update them"
  echo ""
  exit
}

function vm_update {
	vm=$1
	echo "processing VM $vm"
	num_of_devices=`virsh dumpxml playground_node00 | grep -c "hostdev mode"`
	device_per_numa=`echo $(($num_of_devices/2))`
	echo "Found $num_of_devices"
	echo "Adding controllers"
	virt-xml $vm --add-device --controller model=pci-expander-bus,type=pci,address.type=pci,address.domain=0x0000,address.bus=0x00,address.slot=0x10,address.function=0x0,index=3
	virt-xml $vm --add-device --controller model=pci-expander-bus,type=pci,address.type=pci,address.domain=0x0000,address.bus=0x00,address.slot=0x11,address.function=0x0,index=4
	echo "Num of devices: $num_of_devices"
	echo "Devices per numa: $device_per_numa"
	bus="0x03"
	for i in $(seq 1 $num_of_devices) 
       	do
		slot="$i"
		if [[ $i > $device_per_numa ]]
		then
			bus="0x04"
			slot=`echo $(($i-$device_per_numa))`
		fi
		echo "Processing device #$i"
		virt-xml $vm --edit $i --hostdev address.bus=$bus,address.slot=\'0x${slot}\'
	done
}

if [[ ! -z "$1" ]] ;then 
	if [[ $1 == "--help" || $1 == "-h" ]] ; then
		usage
	else
		if [[ `virsh list | grep running | grep -wc $1` -ne "0" ]] ;then 
			vm_update $1
		else
			echo "vm $1 seems to be not running or wrong VM name - Exiting"
			echo "Current relevant running VMs:"
			echo "`virsh list | grep node | grep running | awk '{print $2}'`"
			exit
		fi	
	fi
else
	for vm in `virsh list | grep node | grep running | awk '{print $2}'` ;do
		vm_update $vm
	done;
fi
