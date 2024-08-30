import json
import os
from typing import Optional

from ledgerwallet import params
from ledgerwallet.manifest import AppManifest, icon_from_file
from ledgerwallet.utils import get_device_name


class AppManifestJson(AppManifest):
    def __init__(self, filename):
        with open(filename) as f:
            self.path = os.path.dirname(filename)
            self.dic = json.load(f)
            assert "targetId" in self.dic and "binary" in self.dic

    def data_size(self, device: str) -> int:
        return int(self.dic.get("dataSize", 0))

    def get_application_flags(self, device: str) -> int:
        return int(self.dic.get("flags", "0"), 16)

    def get_api_level(self, device: str) -> Optional[int]:
        if "apiLevel" not in self.dic:
            return None
        return int(self.dic["apiLevel"], 10)

    def get_binary(self, device: str) -> str:
        return os.path.join(self.path, self.dic["binary"])

    def serialize_parameters(self, device: str) -> bytes:
        parameters = []
        for entry, value in self.dic.items():
            if entry == "name":
                parameters.append({"type_": "BOLOS_TAG_APPNAME", "value": value})
            elif entry == "version":
                parameters.append({"type_": "BOLOS_TAG_APPVERSION", "value": value})
            elif entry == "icon":
                api_level = self.get_api_level(device)
                parameters.append(
                    {
                        "type_": "BOLOS_TAG_ICON",
                        "value": icon_from_file(value, device, api_level),
                    }
                )
            elif entry == "derivationPath":
                derivation_paths = self.serialize_derivation_path(value)
                parameters.append(
                    {"type_": "BOLOS_TAG_DERIVEPATH", "value": derivation_paths}
                )
        return params.AppParams.build(parameters)

    def assert_compatible_device(self, device_id: int):
        if "targetId" in self.dic and int(self.dic["targetId"], 16) == device_id:
            return
        else:
            raise ValueError(
                "JSON manifest has no installation information about the current"
                " device : {}".format(get_device_name(device_id))
            )
