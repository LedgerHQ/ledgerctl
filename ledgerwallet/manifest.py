import base64
import json
import os

from ledgerwallet import params


class AppManifest(object):
    def __init__(self, filename):
        with open(filename) as f:
            self.path = os.path.dirname(filename)
            self.json = json.load(f)
            assert "targetId" in self.json and "binary" in self.json

    @property
    def app_name(self):
        return self.json["name"]

    @property
    def data_size(self):
        if "dataSize" not in self.json:
            return 0
        else:
            return self.json["dataSize"]

    def get_application_flags(self) -> int:
        if "flags" not in self.json:
            return 0
        else:
            return int(self.json["flags"], 16)

    def get_binary(self) -> str:
        return os.path.join(self.path, self.json["binary"])

    def get_target_id(self) -> int:
        return int(self.json["targetId"], 16)

    def serialize_parameters(self) -> bytes:
        parameters = []
        for entry, value in self.json.items():
            if entry == "name":
                parameters.append({"type_": "BOLOS_TAG_APPNAME", "value": value})
            elif entry == "version":
                parameters.append({"type_": "BOLOS_TAG_APPVERSION", "value": value})
            elif entry == "icon":
                parameters.append(
                    {"type_": "BOLOS_TAG_ICON", "value": base64.b64decode(value)}
                )
            elif entry == "derivationPath":
                derivation_paths = {"paths": None, "curve": None}
                for derivation_entry in value:
                    if derivation_entry == "curves":
                        curves = 0
                        for curve in value["curves"]:
                            if curve == "secp256k1":
                                curves |= params.CURVE_SEPCK256K1
                            elif curve == "prime256r1":
                                curves |= params.CURVE_PRIME256R1
                            elif curve == "ed25519":
                                curves |= params.CURVE_ED25519
                            derivation_paths["curve"] = curves
                    elif derivation_entry == "paths":
                        derivation_paths["paths"] = value["paths"]
                parameters.append(
                    {"type_": "BOLOS_TAG_DERIVEPATH", "value": derivation_paths}
                )
        return params.AppParams.build(parameters)
