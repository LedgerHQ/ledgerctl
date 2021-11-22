import collections
import colorsys
import json
import math
import os
from typing import Dict

from PIL import Image

from ledgerwallet import params

MAX_COLORS = 16


def _image_to_packed_buffer(im: Image, palette: Dict, bits_per_pixel: int) -> bytes:
    width, height = im.size

    current_byte = 0
    current_bit = 0
    image_data = []

    # Row first
    for row in range(height):
        for col in range(width):
            # Return an index in the indexed colors list for indexed address spaces
            # left to right
            # Perform implicit rotation here (0,0) is left top in BAGL, and generally left bottom for various canvas
            color_index = im.getpixel((col, row))

            # Remap index by luminance
            color_index = palette[color_index]

            # le encoded
            current_byte += color_index << current_bit
            current_bit += bits_per_pixel

            if current_bit >= 8:
                image_data.append(current_byte & 0xFF)
                current_bit = 0
                current_byte = 0

        # Handle last byte if any
    if current_bit > 0:
        image_data.append(current_byte & 0xFF)
    return bytes(image_data)


def icon_from_file(image_file: str) -> bytes:
    def is_power2(n):
        return n != 0 and ((n & (n - 1)) == 0)

    im = Image.open(image_file)
    im.load()
    num_colors = len(im.getcolors())

    assert im.mode == "P" and num_colors <= MAX_COLORS

    # Round number of colors to a power of 2
    if not is_power2(num_colors):
        num_colors = int(pow(2, math.ceil(math.log(num_colors, 2))))

    bits_per_pixel = int(math.log(num_colors, 2))

    # Reorder color map by luminance
    palette = im.getpalette()
    opalette = {}
    for i in range(num_colors):
        red, green, blue = palette[3 * i : 3 * i + 3]
        hue, saturation, value = colorsys.rgb_to_hsv(
            red / 255.0, green / 255.0, blue / 255.0
        )

        # Several colors could have the same luminance
        if value * 255.0 not in opalette:
            opalette[value * 255.0] = []
        opalette[value * 255.0].append([i, (red << 16) + (green << 8) + blue])
    opalette = collections.OrderedDict(sorted(opalette.items()))

    # Compute the remapping index
    i = 0
    new_indices = {}
    new_palette = []
    for lum, values in opalette.items():
        # Old index to new index
        for v in values:
            new_indices[v[0]] = i
            new_palette.append(v[1])
            i += 1

    # write BPP
    header = bytes([bits_per_pixel])
    # LE color array, it is meant to be embedded as is in an array
    for i in range(num_colors):
        header += new_palette[i].to_bytes(4, "big")

    image_data = _image_to_packed_buffer(im, new_indices, bits_per_pixel)
    return header + image_data


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
                    {"type_": "BOLOS_TAG_ICON", "value": icon_from_file(value)}
                )
            elif entry == "derivationPath":
                derivation_paths = {"paths": None, "curve": None}
                for derivation_entry in value:
                    if derivation_entry == "curves":
                        curves = 0
                        for curve in value["curves"]:
                            if curve == "secp256k1":
                                curves |= params.CURVE_SECP256K1
                            elif curve == "prime256r1":
                                curves |= params.CURVE_PRIME256R1
                            elif curve == "ed25519":
                                curves |= params.CURVE_ED25519
                            elif curve == "bls12381g1":
                                curves |= params.CURVE_BLS12381G1
                            derivation_paths["curve"] = curves
                    elif derivation_entry == "paths":
                        derivation_paths["paths"] = value["paths"]
                parameters.append(
                    {"type_": "BOLOS_TAG_DERIVEPATH", "value": derivation_paths}
                )
        return params.AppParams.build(parameters)
