import configparser
import os
import re
import sys
from json import JSONDecodeError

import click
from tabulate import tabulate

if sys.version_info >= (3, 11):
    from tomllib import TOMLDecodeError
else:
    from toml.decoder import TomlDecodeError as TOMLDecodeError

from ledgerwallet import utils
from ledgerwallet.client import (
    LEDGER_HSM_KEY,
    LEDGER_HSM_URL,
    CommException,
    LedgerClient,
    LedgerIns,
    NoLedgerDeviceException,
)
from ledgerwallet.crypto.ecc import PrivateKey
from ledgerwallet.manifest import AppManifest
from ledgerwallet.manifest_json import AppManifestJson
from ledgerwallet.manifest_toml import AppManifestToml
from ledgerwallet.transport import FileDevice


class ManifestFormatError(Exception):
    def __init__(
        self, toml_error: TOMLDecodeError, json_error: JSONDecodeError
    ) -> None:
        self.toml = toml_error
        self.json = json_error

    def __str__(self) -> str:
        return "TOML or JSON is expected\nTOML error : {}\nJSON error : {}".format(
            self.toml, self.json
        )


_remote_options = [
    click.option("--url", type=str, default=LEDGER_HSM_URL, help="Server URL."),
    click.option(
        "--key",
        "-k",
        type=str,
        default=LEDGER_HSM_KEY,
        help="Key identifier on the remote server.",
    ),
]


def remote_options(func):
    for option in reversed(_remote_options):
        func = option(func)
    return func


def get_private_key() -> bytes:
    app_path = click.get_app_dir("ledgerctl")
    if not os.path.exists(app_path):
        os.makedirs(app_path)

    cfg_file = os.path.join(app_path, "config.ini")
    try:
        config = configparser.RawConfigParser()
        config.read(cfg_file)

        default_config = config["DEFAULT"]
        private_key = bytes.fromhex(default_config["private_key"])
    except KeyError:
        new_private_key = PrivateKey()
        public_key = new_private_key.pubkey
        pubkey_bytes = public_key.serialize(compressed=False)

        config = configparser.RawConfigParser()
        config["DEFAULT"] = {
            "public_key": pubkey_bytes.hex(),
            "private_key": new_private_key.serialize().hex(),
        }
        with click.open_file(cfg_file, "w") as f:
            config.write(f)
        private_key = bytes.fromhex(new_private_key.serialize().hex())

    return private_key


def get_file_device(output_file, target_id="0x33000004"):
    try:
        return LedgerClient(FileDevice(target_id, out=output_file))
    except NoLedgerDeviceException as exception:
        click.echo(exception)
        sys.exit(0)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Display exchanged APDU.")
@click.pass_context
def cli(ctx, verbose):
    if verbose:
        utils.enable_apdu_log()

    def get_client():
        try:
            return LedgerClient(private_key=get_private_key())
        except NoLedgerDeviceException as exception:
            click.echo(exception)
            sys.exit(0)

    ctx.obj = get_client


@cli.command(help="Send raw data to the device.")
@click.argument("input_file", type=click.File("r"))
@click.pass_obj
def send(get_client, input_file):
    client = get_client()
    while True:
        chunk = input_file.readline()
        if not chunk:
            break
        response = client.raw_exchange(bytes.fromhex(chunk.rstrip()))
        click.echo(response.hex())


@cli.command(help="Check if device is genuine.")
@remote_options
@click.pass_obj
def genuine_check(get_client, url, key):
    if get_client().genuine_check(url, key):
        click.echo("Device is genuine.")
    else:
        click.echo("Device is NOT genuine.")


@cli.command("list", help="List installed applications.")
@click.option("--remote", default=False, is_flag=True)
@remote_options
@click.pass_obj
def list_apps(get_client, remote, url, key):
    client = get_client()
    rows = []

    # Always list apps using a remote server on Nano X, as custom SCP channels
    # cannot be established
    if client.target_id == 0x33000004:
        remote = True
    for app in client.list_apps_remote(url, key) if remote else client.apps:
        rows.append(
            [
                app.name,
                utils.flags_to_string(app.flags),
                app.code_data_hash.hex(),
                app.full_hash.hex(),
            ]
        )
    if len(rows) == 0:
        click.echo("There is no application on the device.")
    else:
        click.echo(tabulate(rows, ("Name", "Flags", "Code/data hash", "Full hash")))


@cli.command("install", help="Install application.")
@click.argument("manifest")
@click.option(
    "-f",
    "--force",
    help="Delete the app with the same name before loading the provided one.",
    is_flag=True,
)
@click.option(
    "-o",
    "--offline",
    help="Dump APDU installation file, do not attempt to connect to a physical device.",
    is_flag=False,
    flag_value="out.apdu",
)
@click.pass_obj
def install_app(get_client, manifest: AppManifest, force, offline):
    try:
        app_manifest: AppManifest = AppManifestToml(manifest)
    except TOMLDecodeError as toml_error:
        try:
            app_manifest = AppManifestJson(manifest)
            click.echo(
                "[WARNING] JSON files will be deprecated in future version", err=True
            )
        except JSONDecodeError as json_error:
            raise ManifestFormatError(toml_error, json_error)

    try:
        if offline:
            try:
                dump_file = open(offline, "w")
            except OSError:
                click.echo("Unable to open file {} for dump.".format(offline))
                sys.exit(1)
            click.echo("Dumping APDU installation file to {}".format(offline))
            client = get_file_device(dump_file, app_manifest.target_id)
            if force:
                client.delete_app(app_manifest.app_name)
        else:
            client = get_client()
            if force:
                client.delete_app(app_manifest.app_name)
                client.close()
                client = get_client()
        client.install_app(app_manifest)
    except CommException as e:
        if e.sw == 0x6985:
            click.echo("Operation has been canceled by the user.")
        elif e.sw == 0x6A80:
            click.echo("An application with the same name is already installed.")
        elif e.sw == 0x6A81:
            click.echo("Application is already installed.")
        else:
            raise


@cli.command("remote-install", help="Install an application from a remote server.")
@click.argument("app_path")
@click.argument("key_path")
@remote_options
@click.pass_obj
def install_remote_app(get_client, app_path, key_path, url, key):
    client = get_client()
    client.install_remote_app(app_path, key_path, url, key)


@cli.command("delete", help="Delete application.")
@click.argument("app")
@click.option(
    "--by-hash",
    help="Delete using application hash instead of application name",
    is_flag=True,
)
@click.option(
    "-o",
    "--offline",
    help=(
        "Dump APDU delete command file, do not attempt to connect to a physical device."
    ),
    is_flag=False,
    flag_value="out_delete.apdu",
)
@click.pass_obj
def delete_app(get_client, app, by_hash, offline):
    if by_hash:
        data = bytes.fromhex(app)
    else:
        data = app

    if offline:
        try:
            dump_file = open(offline, "w")
        except OSError:
            click.echo("Unable to open file {} for dump.".format(offline))
            sys.exit(1)
        click.echo("Dumping APDU delete command file to {}".format(offline))
        client = get_file_device(dump_file)
    else:
        client = get_client()
    try:
        client.delete_app(data)
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
def delete_app_remote(get_client, app_path, key_path, url, key):
    client = get_client()
    client.delete_remote_app(app_path, key_path, url, key)


@cli.command(help="Run specified application.")
@click.argument("app_name")
@click.pass_obj
def run(get_client, app_name: str):
    try:
        get_client().run_app(app_name)
    except CommException as e:
        if e.sw == 0x6984:
            click.echo("Application {} is not installed.".format(app_name))
        else:
            raise


@cli.command(help="Install a custom certificate authority on the device.")
@click.argument("name")
@click.argument("public_key", required=False)
@click.pass_obj
def install_ca(get_client, name, public_key):
    if public_key is None:
        raw_private_key = get_private_key()
        pubkey_bytes = PrivateKey(raw_private_key).pubkey.serialize(compressed=False)
    else:
        pubkey_bytes = bytes.fromhex(public_key)

    try:
        get_client().install_ca(name, pubkey_bytes)
        click.echo("Custom certificate has been successfully installed.")
    except CommException as e:
        if e.sw == 0x6982:
            click.echo("A certificate is already installed on the device.")
        elif e.sw == 0x6802:  # INVALID_PARAMETER
            click.echo("The provided certificate is invalid.")
        elif e.sw == 0x661E:
            click.echo("The device is not in recovery mode.")
        else:
            raise


@cli.command(help="Delete custom certificate authority.")
@click.pass_obj
def delete_ca(get_client):
    try:
        get_client().delete_ca()
        click.echo("Custom certificate has been deleted.")
    except CommException as e:
        if e.sw == 0x6A84:
            click.echo(
                "No custom certificate is installed. There is nothing to delete."
            )
        else:
            raise


# Taken from
# https://web.archive.org/web/20111010015624/http://blogmag.net/blog/read/38/Print_human_readable_file_size
def sizeof_fmt(num, suffix="B"):
    for unit in ("", "K", "M"):
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "G", suffix)


@cli.command(help="Display device memory usage.")
@click.pass_obj
def meminfo(get_client):
    def format_entry(name: str, size: int, max_size: int):
        return "- {0:s}: {1:s} ({2:.2f}%)".format(
            name, sizeof_fmt(size), size / max_size * 100
        )

    memory_info = get_client().get_memory_info()

    total_size = (
        memory_info.system_size + memory_info.applications_size + memory_info.free_size
    )
    click.echo("Memory usage:")
    click.echo(format_entry("System", memory_info.system_size, total_size))
    click.echo(format_entry("Applications", memory_info.applications_size, total_size))
    click.echo(format_entry("Available space", memory_info.free_size, total_size))

    click.echo("")
    click.echo(
        "Installed apps: {} (max: {})".format(
            memory_info.used_app_slots, memory_info.num_app_slots
        )
    )


@cli.command(help="Display device information.")
@click.pass_obj
def info(get_client):
    version_info = get_client().get_version_info()

    click.echo(
        "Device: {} ({})".format(
            utils.get_device_name(version_info.target_id), version_info.target_id
        )
    )
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
def upgrade_firmware(get_client, firmware_name, firmware_key, url, key):
    client = get_client()
    client.upgrade_firmware(firmware_name, firmware_key, url, key)


@cli.command(
    help="Perform quick onboarding from command line. Device must be reset and booted in recovery mode (press some buttons during the boot)."  # noqa
)
@click.argument("pin")
@click.argument("words")
@click.option(
    "--id", help="Identity number to initialize", default=0, type=click.IntRange(0, 2)
)
@click.option("--prefix", help="Derivation prefix")
@click.option("--passphrase", help="Derivation passphrase")
@click.pass_obj
def onboard(connect, pin, passphrase, words, id, prefix):
    # Check pin argument
    if not re.match("^[0-9]{4,8}$", pin):
        raise ValueError("Invalid PIN format")

    data = bytearray()
    for string in (pin, prefix, passphrase, words):
        if string:
            as_bytes = string.encode()
            data.append(len(as_bytes))
            data += as_bytes
        else:
            data.append(0)

    client = connect()
    try:
        client.apdu_exchange(LedgerIns.ONBOARD, data, p1=id)
    except CommException as e:
        raise RuntimeError(
            "Onboarding failed (are you in recovery mode?): {:#x}".format(e.sw)
        )


if __name__ == "__main__":
    cli()
