import os
import configparser
import sys

import click
from tabulate import tabulate

from ledgerwallet.client import LedgerClient, CommException, LEDGER_HSM_URL, LEDGER_HSM_KEY
from ledgerwallet.transport import enumerate_devices
from ledgerwallet.crypto.ecc import PrivateKey
from ledgerwallet.manifest import AppManifest
from ledgerwallet import utils


_remote_options = [
    click.option('--url', type=str, default=LEDGER_HSM_URL, help="Server URL."),
    click.option('--key', '-k', type=str, default=LEDGER_HSM_KEY, help="Key identifier on the remote server.")
]


def remote_options(func):
    for option in reversed(_remote_options):
        func = option(func)
    return func


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Display exchanged APDU.")
@click.pass_context
def cli(ctx, verbose):
    if verbose:
        utils.enable_apdu_log()

    def get_client():
        app_path = click.get_app_dir("ledgerctl")
        try:
            cfg_file = os.path.join(app_path, "config.ini")
            config = configparser.RawConfigParser()
            config.read(cfg_file)

            default_config = config['DEFAULT']
            private_key = bytes.fromhex(default_config['private_key'])
        except KeyError:
            private_key = bytes.fromhex("5244aa214e6190220583754f80eb80e9d2b04a94c2c551e882f5c37a97077ab2")
        devices = enumerate_devices()
        if len(devices) == 0:
            click.echo("No Ledger device has been found.")
            sys.exit(0)
        return LedgerClient(devices[0], private_key=private_key)
    ctx.obj = get_client


@cli.command(help="Send raw data to the device.")
@click.argument("input_file", type=click.File('r'))
@click.pass_obj
def send(connect, input_file):
    client = connect()
    while True:
        chunk = input_file.readline()
        if not chunk:
            break
        response = client.raw_exchange(bytes.fromhex(chunk))
        click.echo(response.hex())


@cli.command(help="Check if device is genuine.")
@remote_options
@click.pass_obj
def genuine_check(connect, url, key):
    if connect().genuine_check(url, key):
        click.echo("Device is genuine.")
    else:
        click.echo("Device is NOT genuine.")


@cli.command('list', help="List installed applications.")
@click.option('--remote', default=False, is_flag=True)
@remote_options
@click.pass_obj
def list_apps(connect, remote, url, key):
    client = connect()
    rows = []
    for app in client.list_apps_remote(url, key) if remote else client.apps:
        rows.append([app.name, utils.flags_to_string(app.flags), app.code_data_hash.hex(), app.full_hash.hex()])
    if len(rows) == 0:
        click.echo("There is no application on the device.")
    else:
        click.echo(tabulate(rows, ("Name", "Flags", "Code/data hash", "Full hash")))


@cli.command("install", help="Install application.")
@click.argument("manifest")
@click.option("-f", "--force", help="Delete using application hash instead of application name", is_flag=True)
@click.pass_obj
def install_app(connect, manifest: AppManifest, force):
    client = connect()
    app_manifest = AppManifest(manifest)
    try:
        if force:
            client.delete_app(app_manifest.app_name)
        client.install_app(app_manifest)
    except CommException as e:
        if e.sw == 0x6985:
            click.echo("Operation has been canceled by the user.")
        elif e.sw == 0x6a80:
            click.echo("An application with the same name is already installed.")
        elif e.sw == 0x6a81:
            click.echo("Application is already installed.")
        else:
            raise


@cli.command("remote-install", help="Install an application from a remote server.")
@click.argument("app_path")
@click.argument("key_path")
@remote_options
@click.pass_obj
def install_remote_app(connect, app_path, key_path, url, key):
    client = connect()
    client.install_remote_app(app_path, key_path, url, key)


@cli.command("delete", help="Delete application.")
@click.argument("app")
@click.option("--by-hash", help="Delete using application hash instead of application name", is_flag=True)
@click.pass_obj
def delete_app(connect, app, by_hash):
    if by_hash:
        data = bytes.fromhex(app)
    else:
        data = app
    try:
        connect().delete_app(data)
    except CommException as e:
        if e.sw == 0x6985:
            click.echo("Operation has been canceled by the user.")
        else:
            raise


@cli.command("remote-delete", help="Delete an application using a remote server.")
@click.argument("app_path")
@click.argument("key_path")
@remote_options
@click.pass_obj
def delete_app_remote(connect, app_path, key_path, url, key):
    client = connect()
    client.delete_remote_app(app_path, key_path, url, key)


@cli.command(help="Run specified application.")
@click.argument("app_name")
@click.pass_obj
def run(connect, app_name: str):
    try:
        connect().run_app(app_name)
    except CommException as e:
        if e.sw == 0x6984:
            click.echo("Application {} is not installed.".format(app_name))
        else:
            raise


@cli.command(help="Install a custom certificate authority on the device.")
@click.argument("name")
@click.argument("public_key", required=False)
@click.pass_obj
def install_ca(connect, name, public_key):
    if public_key is None:
        click.echo("Generating certificate authority...")

        private_key = PrivateKey()
        public_key = private_key.pubkey
        pubkey_bytes = public_key.serialize(compressed=False)

        app_path = click.get_app_dir("ledgerctl")
        if not os.path.exists(app_path):
            os.mkdir(app_path)

        cfg_file = os.path.join(app_path, "config.ini")
        config = configparser.RawConfigParser()
        config['DEFAULT'] = {
            "public_key": pubkey_bytes.hex(),
            "private_key": private_key.serialize().hex()
        }
        with click.open_file(cfg_file, "w") as f:
            config.write(f)
    else:
        pubkey_bytes = bytes.fromhex(public_key)

    try:
        connect().install_ca(name, pubkey_bytes)
        click.echo("Custom certificate has been successfully installed.")
    except CommException as e:
        if e.sw == 0x6982:
            click.echo("A certificate is already installed on the device.")
        elif e.sw == 0x6802:  # INVALID_PARAMETER
            click.echo("The provided certificate is invalid.")
        else:
            raise


@cli.command(help="Delete custom certificate authority.")
@click.pass_obj
def delete_ca(connect):
    try:
        connect().delete_ca()
        click.echo("Custom certificate has been deleted.")
    except CommException as e:
        if e.sw == 0x6a84:
            click.echo("No custom certificate is installed. There is nothing to delete.")
        else:
            raise


# Taken from https://web.archive.org/web/20111010015624/http://blogmag.net/blog/read/38/Print_human_readable_file_size
def sizeof_fmt(num, suffix='B'):
    for unit in ('', 'K', 'M'):
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'G', suffix)


@cli.command(help="Display device memory usage.")
@click.pass_obj
def meminfo(connect):
    def format_entry(name: str, size: int, max_size: int):
        return "- {0:s}: {1:s} ({2:.2f}%)".format(name, sizeof_fmt(size), size / max_size * 100)

    memory_info = connect().get_memory_info()

    total_size = memory_info.system_size + memory_info.applications_size + memory_info.free_size
    click.echo("Memory usage:")
    click.echo(format_entry("System", memory_info.system_size, total_size))
    click.echo(format_entry("Applications", memory_info.applications_size, total_size))
    click.echo(format_entry("Available space", memory_info.free_size, total_size))

    click.echo("")
    click.echo("Installed apps: {} (max: {})".format(memory_info.used_app_slots, memory_info.num_app_slots))


@cli.command(help="Display device information.")
@click.pass_obj
def info(connect):
    version_info = connect().get_version_info_secure()

    click.echo("Device: {} ({})".format(utils.get_device_name(version_info.target_id), version_info.target_id))
    click.echo("SE version: {}".format(version_info.se_version))
    click.echo("MCU version: {}".format(version_info.mcu_version))

    if version_info.flags["is_onboarded"]:
        click.echo("Device is onboarded.")

    if version_info.flags["recovery_mode"]:
        click.echo("Device is running in RECOVERY mode.")


@cli.command("upgrade-firmware", help="Upgrade firmware.")
@click.argument("firmware_name")
@click.argument("firmware_key")
@remote_options
@click.pass_obj
def upgrade_firmware(connect, firmware_name, firmware_key, url, key):
    client = connect()
    client.upgrade_firmware(firmware_name, firmware_key, url, key)


if __name__ == '__main__':
    cli()
