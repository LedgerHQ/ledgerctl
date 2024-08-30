import os
import sys
from typing import Optional

from ledgerwallet.manifest import AppManifest, icon_from_file
from ledgerwallet.utils import DeviceNames, get_device_name

if sys.version_info >= (3, 11):
    import tomllib
else:
    import toml as tomllib

from ledgerwallet import params


class AppManifestToml(AppManifest):
    def __init__(self, filename):
        self.path = os.path.dirname(filename)
        if sys.version_info >= (3, 11):
            with open(filename, "rb") as f:
                self.dic = tomllib.load(f)
        else:
            with open(filename, "r") as f:
                self.dic = tomllib.load(f)

    def data_size(self, device: str) -> int:
        return self.dic[device].get("dataSize", 0)

    def get_application_flags(self, device: str) -> int:
        return int(self.dic[device].get("flags", "0"), 16)

    def get_api_level(self, device: str) -> Optional[int]:
        if (
            get_device_name(int(device, 16)) == DeviceNames.LEDGER_NANO_SP.value
            and "apiLevel" in self.dic[device]
        ):
            level = self.dic[device]["apiLevel"]
            if isinstance(level, int):
                return int(level)
            return int(level, 10)
        return None

    def get_binary(self, device: str) -> str:
        return os.path.join(self.path, self.dic[device]["binary"])

    def serialize_parameters(self, device: str) -> bytes:
        parameters = []
        for entry, value in self.dic.items():
            if entry == "name":
                parameters.append({"type_": "BOLOS_TAG_APPNAME", "value": value})
            elif entry == "version":
                parameters.append({"type_": "BOLOS_TAG_APPVERSION", "value": value})
            elif entry == device:
                for device_entry, device_value in self.dic[entry].items():
                    if device_entry == "icon":
                        api_level = self.get_api_level(device)
                        parameters.append(
                            {
                                "type_": "BOLOS_TAG_ICON",
                                "value": icon_from_file(
                                    device_value, device, api_level
                                ),
                            }
                        )
                    elif device_entry == "derivationPath":
                        derivation_paths = self.serialize_derivation_path(device_value)
                        parameters.append(
                            {"type_": "BOLOS_TAG_DERIVEPATH", "value": derivation_paths}
                        )
        return params.AppParams.build(parameters)

    def assert_compatible_device(self, device_id: int):
        if "binary" not in self.dic.get(str(device_id), list()):
            raise ValueError(
                "TOML manifest has no installation information about the current"
                " device : {}".format(get_device_name(device_id))
            )
