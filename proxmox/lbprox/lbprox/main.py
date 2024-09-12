#!/usr/bin/env python3

import click
import json
import logging
import os
import yaml

import http.client
import urllib3
http.client.HTTPConnection.debuglevel = 0

from lbprox.common.vm_tags import VMTags
import proxmoxer as proxmox
from lbprox.common import utils

from lbprox.cli.image_store.cli import image_store_group
from lbprox.cli.data_network.cli import data_network_group
from lbprox.cli.nodes.cli import nodes_group
from lbprox.cli.os_images.cli import os_images_group
from lbprox.cli.allocations.cli import allocations_group
from lbprox.cli.dashboard.cli import dashboard_group
from lbprox.cli.prom_discovery.cli import prom_discovery_group
from lbprox.common import constants
from lbprox.ssh import ssh


class AppContext(object):
    def __init__(self, username: str, password: str,
                 config_file: str, debug: bool=False):
        self.debug = debug
        self.username = username
        self.password = password
        self.config_file = config_file
        with open(self.config_file, 'r') as f:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)
        self.pve, last_active_hostname = self.get_proxmox_api(config, username, password)
        assert self.pve, f"failed to create Proxmox API object: {config}"
        # update last know active node
        last_active = config.get("last_active", None)
        if last_active is None or last_active != last_active_hostname:
            config["last_active"] = last_active_hostname
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f)
        assert self.pve, f"failed to create Proxmox API object: {config}"
        # self.ssh_client = ssh.SSHClient(last_active_hostname, "root", "light")
        # assert self.ssh_client, f"failed to create SSH client object: {last_active_hostname}"

    def get_proxmox_api(self, config, username, password, timeout=15):
        # Create a Proxmox API object
        last_active = config.get("last_active", None)
        if last_active:
            try:
                urllib3.HTTPConnectionPool(last_active, maxsize=10, block=True)
                pve = proxmox.ProxmoxAPI(last_active, user=f"{username}@pam",
                                        password=password, verify_ssl=False,
                                        timeout=timeout)
                return pve, last_active
            except Exception as ex:
                logging.debug(f"failed to connect to last active: {last_active}. will look for new active: {ex}")

        for node in config["nodes"]:
            hostname = node.get('hostname')
            try:
                urllib3.HTTPConnectionPool(hostname, maxsize=10, block=True)
                pve = proxmox.ProxmoxAPI(hostname, user=f"{username}@pam",
                                        password=password, verify_ssl=False,
                                        timeout=timeout)
                return pve, hostname
            except Exception as ex:
                logging.debug(f"failed to connect to {hostname}: {ex}. keep looking...")
        return None


@click.group(name="proxmox")
@click.option('-u', '--username', default="root", envvar='PROXMOX_USERNAME')
@click.option('-p', '--password', default="light", hide_input=True, envvar='PROXMOX_PASSWORD')
@click.option('--debug/--no-debug', default=False, envvar='LBPROX_DEBUG')
@click.option('-c', '--config-file', default=constants.DEFAULT_CONFIG_FILE, envvar='LBPROX_CONFIG',
              help=f"config file to use (default: {constants.DEFAULT_CONFIG_FILE})")
@click.pass_context
def cli(ctx, username, password, debug, config_file):
    """
    Command-line interface function for the lbprox application.

    Args:
        ctx (click.Context): The Click context object.
        username (str): The username for authentication.
        password (str): The password for authentication.
        debug (bool): Flag indicating whether to enable debug mode.
        config_file (str): The path to the configuration file.

    Raises:
        RuntimeError: If the config file does not exist.

    Returns:
        None
    """
    if not os.path.exists(config_file):
        raise RuntimeError(f"config file does not exist at {constants.DEFAULT_CONFIG_FILE}")
    ctx.obj = AppContext(username, password, config_file, debug)
    utils.basicConfig(debug)


@cli.command()
@click.option('-t', '--tags', required=False, default=None, multiple=True,
              help="tags to filter the VMs by. ex: --tags=allocation.b178 --tags=vm.s00")
@click.pass_context
def list_cluster_vms(ctx, tags):
    if tags is not None:
        tags = ";".join(tags)
        tags = VMTags.parse_tags(tags)
    print(json.dumps(utils.list_cluster_vms(ctx.obj.pve, tags), indent=2))


def main():
    cli.add_command(nodes_group)
    cli.add_command(allocations_group)
    cli.add_command(data_network_group)
    cli.add_command(image_store_group)
    cli.add_command(os_images_group)
    cli.add_command(dashboard_group)
    cli.add_command(prom_discovery_group)
    cli() # [no-value-for-parameter]


if __name__ == '__main__':
    main()
