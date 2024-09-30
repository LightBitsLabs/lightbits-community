import logging
import time
import click


@click.group("data-network")
def data_network_group():
    pass


@data_network_group.command("create")
@click.option('--zone-name', default="data0", help="name of the zone (default: data0)")
@click.option('--subnet', default="10.101.1.0/24", help="subnet in CIDR format (default: 10.101.1.0/24)")
@click.option('--gateway', type=str, default="10.101.1.1", help="gateway IP address (default: 10.101.1.1)")
@click.option('--dhcp-range', multiple=True,
              default=["start-address=10.101.1.10,end-address=10.101.1.200"],
              help="dhcp range in start-address=IP,end-address=IP format (default: ['start-address=10.101.1.10,end-address=10.101.1.200']")
@click.option('--nodes', multiple=True, default=None,
              help="list of nodes to add to the zone - (default: all nodes)")
@click.pass_context
def create_data_network(ctx, zone_name, subnet, gateway, dhcp_range, nodes):
    print(_create_data_network(ctx.obj.pve, zone_name, subnet, gateway, dhcp_range, nodes))


@data_network_group.command("delete")
@click.option('--zone-name', default="data0", help="name of the zone (default: data0)")
@click.pass_context
def delete_data_network(ctx, zone_name):
    _delete_data_network(ctx.obj.pve, zone_name)


def _create_data_network(pve, zone_name, subnet: str, gateway: str, dhcp_range: list, nodes: list):
    node_list = nodes if nodes else pve.nodes.get()
    node_names = [node.get('node') for node in node_list]
    existing_zones = pve.cluster.sdn.zones.get()
    existing_zone = next(iter([zone for zone in existing_zones if zone.get('zone') == zone_name]), None)
    if existing_zone:
        logging.debug(f"zone: {zone_name} already exists")
        existing_nodes_list = existing_zone.get('nodes').split(',') if existing_zone.get('nodes') else []
        if set(node_names) == set(existing_nodes_list):
            logging.debug(f"zone: {zone_name} already exists with the same nodes, nothing to do")
            return
        else:
            logging.debug(f"zone: {zone_name} already exists with different nodes, updating it")
            pve.cluster.sdn.zones.put(zone=zone_name, nodes=node_names)
    else:
        logging.debug(f"zone {zone_name} does not exist, creating it")
        pve.cluster.sdn.zones.post(zone=zone_name, type="simple", nodes=node_names, dhcp="dnsmasq", ipam="pve")
        pve.cluster.sdn.vnets.post(zone=zone_name, vnet=zone_name)
        pve.cluster.sdn.vnets(zone_name).subnets.post(**{"dhcp-range": dhcp_range},
                                                    subnet=subnet, type="subnet",
                                                    snat=1, gateway=gateway)
        # apply the changes
        pve.cluster.sdn.put()
        while True:
            active_node_zones = []
            for node_name in node_names:
                if node_name in active_node_zones:
                    continue
                node_zone = pve.nodes(node_name).sdn.zones(zone_name).content.get()
                if node_zone[0].get('status') == "pending":
                    time.sleep(3)
                    break
                elif node_zone[0].get('status') == "error":
                    raise RuntimeError(f"failed to create zone: {zone_name} on node: {node_name}")
                elif node_zone[0].get('status') == "available":
                    active_node_zones.append(node_name)
                    logging.debug(f"zone: {zone_name} created on node: {node_name}")
            if len(active_node_zones) == len(node_names):
                logging.debug(f"zones created and available on all nodes")
                break


def _delete_data_network(pve, zone_name):
    existing_zones = pve.cluster.sdn.zones.get()
    existing_zone = next(iter([zone for zone in existing_zones if zone.get('zone') == zone_name]), None)
    if existing_zone:
        logging.debug(f"deleting {zone_name} zone")
        vnets = pve.cluster.sdn.vnets().get()
        for vnet in vnets:
            if vnet.get('zone') == zone_name:
                vnet_name = vnet.get('vnet')
                subnets = pve.cluster.sdn.vnets(vnet_name).subnets.get()
                for subnet in subnets:
                    pve.cluster.sdn.vnets(vnet_name).subnets(subnet.get('id')).delete()
                pve.cluster.sdn.vnets(vnet_name).delete()
        pve.cluster.sdn.zones(zone_name).delete()
        # apply the changes
        pve.cluster.sdn.put()
