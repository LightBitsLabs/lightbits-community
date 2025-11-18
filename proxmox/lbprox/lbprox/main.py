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
from lbprox.common import utils
from lbprox.common.app_context import AppContext

from lbprox.cli.image_store.cli import image_store_group
from lbprox.cli.data_network.cli import data_network_group
from lbprox.cli.nodes.cli import nodes_group
from lbprox.temporal.proxmox_worker import temporal_group
from lbprox.cli.os_images.cli import os_images_group
from lbprox.cli.allocations.cli import allocations_group
from lbprox.cli.dashboard.cli import dashboard_group
from lbprox.cli.prom_discovery.cli import prom_discovery_group
from lbprox.common import constants


@click.group(name="proxmox")
@click.option('-u', '--username',
              envvar='LBPROX_USERNAME')
@click.option('-p', '--password',
              hide_input=True,
              envvar='LBPROX_PASSWORD')
@click.option('--debug/--no-debug', default=False, envvar='LBPROX_DEBUG')
@click.option('-c', '--config-file',
              type=click.Path(exists=True, dir_okay=False),
              default=constants.DEFAULT_CONFIG_FILE,
              envvar='LBPROX_CONFIG',
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
    utils.basicConfig(debug)
    if ctx.params['username'] is None:
        logging.debug("username not provided.")

    if ctx.params['password'] is None:
        logging.debug("password not provided.")
    ctx.obj = AppContext.create(username, password, config_file, debug)


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
    cli.add_command(temporal_group)
    cli.add_command(allocations_group)
    cli.add_command(data_network_group)
    cli.add_command(image_store_group)
    cli.add_command(os_images_group)
    cli.add_command(dashboard_group)
    cli.add_command(prom_discovery_group)
    cli() # [no-value-for-parameter]


if __name__ == '__main__':
    main()
