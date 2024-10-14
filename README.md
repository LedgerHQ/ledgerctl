# ledgerwallet

A Python library to control Ledger devices

## Install

This package provides ledgerwallet, a library to interact with Ledger devices, and ledgerctl, a command line tool based on that library to easily perform operations on the devices.

Supported devices are Ledger Blue, Ledger Nano S, Ledger Nano X and Ledger Nano S Plus.

### Quick install

ledgerctl and the ledgerwallet library can be installed using pip:

```shell
pip3 install --upgrade protobuf setuptools ecdsa
pip3 install ledgerwallet
```

Under a Debian or Ubuntu based system, compiling HIDAPI requires to install additional packages:

```shell
sudo apt install python3-dev libusb-1.0-0-dev libudev-dev
```

### Install from source

```shell
git clone https://github.com/LedgerHQ/ledgerctl.git
pip3 install --upgrade protobuf setuptools ecdsa
cd ledgerctl
pip install -e .
```

### Device configuration

> **ATTENTION:** This step is optional and only advised for **developers**. It
> will allow the installation of apps, that weren't reviewed by Ledger, without
> user interaction.

You should install a custom certificate authority (CA) on the device to make the usage of ledgerctl easier. This certificate is used to establish a custom secure channel between the computer and the device, and identifies ledgerctl as a "trusted manager" on the device.

To install a custom CA, boot the device in "Recovery" mode by pressing the right button at boot time.
There are no visual indicators of recovery mode.
Then run:

```shell
ledgerctl install-ca <NAME>
```

where \<NAME\> is the name that will be displayed on the device to identify the CA. It can be any label, like "ledgerctl", "Dev", or "CA".

You are now ready to use ledgerctl.

## Usage

To display the commands supported by ledgerctl, run `ledgerctl` or `ledgerctl --help`. Help for each command can be displayed by running `ledgerctl <command> --help`.

Supported commands include retrieving basic device information, installing and removing apps, viewing available space on the device, etc.

Here are a few examples:

- Displaying available space on the device

```shell
ledgerctl meminfo
```

- Listing installed applications

```shell
ledgerctl list
```

- Deleting the Bitcoin application

```shell
ledgerctl delete Bitcoin
```

### Installing custom apps

Loading an application on the device is currently bound to the SDK and to the build process.

Installation of custom apps differ from the way provided by the SDK. To keep the install process simple, we chose to use "Manifest" files for applications. Manifests are JSON files which contain the required parameters to install the application. You can find an example manifest in the tests/app directory.

Manifest entries are pretty straightforward if you are familiar with the BOLOS SDK, except one of them: `dataSize`. That entry specifies the size of the writable area of the application. This is the size needed by the application to save persistent data. Its value seldom changes.

You can use an ugly one-liner to retrieve it:

```shell
echo $(($(grep _envram_data debug/app.map | awk '{ print $1 }') - $(grep _nvram_data debug/app.map | awk '{ print $1 }')))
```

As an example, the standard way to install the [Bitcoin application]( https://github.com/LedgerHQ/ledger-app-btc ) you compiled is to run `make load` with the BOLOS SDK. It launches the following command:

```shell
python3 -m ledgerblue.loadApp --curve secp256k1 --tlv --targetId 0x31100004 --targetVersion="1.6.0" --delete --fileName bin/app.hex --appName "Bitcoin" --appVersion 1.3.13 --dataSize $((0x`cat debug/app.map |grep _envram_data | tr -s ' ' | cut -f2 -d' '|cut -f2 -d'x'` - 0x`cat debug/app.map |grep _nvram_data | tr -s ' ' | cut -f2 -d' '|cut -f2 -d'x'`)) `ICONHEX=\`python3 /home/dev/sdk/icon3.py --hexbitmaponly nanos_app_bitcoin.gif  2>/dev/null\` ; [ ! -z "$ICONHEX" ] && echo "--icon $ICONHEX"`  --path "" --appFlags 0xa50 --offline bin/app.apdu | grep "Application" | cut -f5 -d' ' > bin/app.sha256
```

To install it with ledgerctl:

1. Retrieve `dataSize` using the above one-liner.
2. Create a manifest file app.toml in the ledger-app-btc directory:

```toml
name = "Bitcoin"
version = "1.3.13"

[0x31100004] #NanoS
icon = "nanos_app_bitcoin.gif"
flags = "0xA50"
derivationPath = {curves = ["secp256k1"]}
binary = "bin/app.hex"
dataSize = 64

[0x33100004] #NanoSP
icon = "nanosp_app_bitcoin.gif"
flags = "0xA50"
derivationPath = {curves = ["secp256k1"]}
binary = "bin/app_nanosp.hex"
dataSize = 64
```

3. Install with `ledgerctl install app.json`.

If you want to force the deletion of the previous version, run the previous command with the `-f` flag.

### Viewing APDUs

Communication between the host and the device use Application Protocol Data Unit (APDUs). To display the raw APDUs, usually for debugging purposes, run ledgerctl with the `-v` switch on any command. For example, here are the APDUs exchanged to run the Bitcoin application:

```shell
$ ledgerctl -v run Bitcoin
=> e0d8000007426974636f696e
<= 9000
```

## Contributing

### Rebuild the proto files

```shell
for file in ledgerwallet/proto/*.proto; do \
    python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. $file; \
done
```

### Pre-commit checks

> **Note:** It's advised to install `pre-commit` using
> [`pipx`](https://github.com/pypa/pipx)

Before submitting your pull-request, please make sure that all
[pre-commit](https://pre-commit.com/) hooks are passing. They can be locally
installed with the following command:

```console
pre-commit install
```

And executed with:

```console
pre-commit run --all-files
```
