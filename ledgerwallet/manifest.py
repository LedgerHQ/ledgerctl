import collections
import colorsys
import gzip
import math
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from PIL import Image, ImageOps

from ledgerwallet import params
from ledgerwallet.utils import DeviceNames, get_device_name

MAX_COLORS = 16


def is_power2(n):
    return n != 0 and ((n & (n - 1)) == 0)


def _image_to_buffer_nbgl(im: Image, compress: bool, reverse_1bpp: bool) -> bytes:
    im = im.convert("L")
    nb_colors = len(im.getcolors())

    # Compute bits_per_pixel
    # Round number of colors to a power of 2
    if not is_power2(nb_colors):
        nb_colors = int(pow(2, math.ceil(math.log(nb_colors, 2))))

    bpp = int(math.log(nb_colors, 2))
    # 2 or 3 BPP are not supported
    if bpp > 1:
        bpp = 4

    if bpp == 0:
        bpp = 1

    # Invert if bpp is 1
    if bpp == 1:
        im = ImageOps.invert(im)

    width, height = im.size

    current_byte = 0
    current_bit = 0
    image_data = []
    base_threshold = int(256 / nb_colors)
    half_threshold = int(base_threshold / 2)

    # col first
    for col in reversed(range(width)):
        for row in range(height):
            # Return an index in the indexed colors list
            # top to bottom
            # Perform implicit rotation here (0,0) is left top in NBGL,
            # and generally left bottom for various canvas
            color_index = im.getpixel((col, row))
            color_index = int((color_index + half_threshold) / base_threshold)

            if color_index >= nb_colors:
                color_index = nb_colors - 1

            if bpp == 1 and reverse_1bpp:
                color_index = (color_index + 1) & 0x1

            # le encoded
            current_byte += color_index << ((8 - bpp) - current_bit)
            current_bit += bpp

            if current_bit >= 8:
                image_data.append(current_byte & 0xFF)
                current_bit = 0
                current_byte = 0

    # Handle last byte if any
    if current_bit > 0:
        image_data.append(current_byte & 0xFF)

    if not compress:
        output_buffer = image_data
    else:
        # Compress buffer into a gzip file
        output_buffer = []
        # cut into chunks of 2048 bytes max of uncompressed data
        # (because decompression needs the full buffer)
        full_uncompressed_size = len(image_data)
        i = 0
        while full_uncompressed_size > 0:
            chunk_size = min(2048, full_uncompressed_size)
            tmp = bytes(image_data[i : i + chunk_size])
            compressed_buffer = gzip.compress(tmp, mtime=0)
            output_buffer += [
                len(compressed_buffer) & 0xFF,
                (len(compressed_buffer) >> 8) & 0xFF,
            ]
            output_buffer += compressed_buffer
            full_uncompressed_size -= chunk_size
            i += chunk_size

    # Add metadata
    BPP_FORMATS = {1: 0, 2: 1, 4: 2}

    result = [
        width & 0xFF,
        width >> 8,
        height & 0xFF,
        height >> 8,
        (BPP_FORMATS[bpp] << 4)
        | (1 if compress else 0),  # 0 is no compression, 1 is gzip compression type
        len(output_buffer) & 0xFF,
        (len(output_buffer) >> 8) & 0xFF,
        (len(output_buffer) >> 16) & 0xFF,
    ]

    result.extend(output_buffer)

    return bytes(bytearray(result))


def _image_to_packed_buffer_bagl(im: Image) -> bytes:
    width, height = im.size
    num_colors = len(im.getcolors())

    # Round number of colors to a power of 2
    if not is_power2(num_colors):
        num_colors = int(pow(2, math.ceil(math.log(num_colors, 2))))

    bits_per_pixel = int(math.log(num_colors, 2))

    current_byte = 0
    current_bit = 0
    image_data = []

    # Reorder color map by luminance
    palette = im.getpalette()
    opalette: Dict[float, List] = {}
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

    palette = new_indices

    # write BPP
    header = bytes([bits_per_pixel])
    # LE color array, it is meant to be embedded as is in an array
    for i in range(num_colors):
        header += new_palette[i].to_bytes(4, "big")

    # Row first
    for row in range(height):
        for col in range(width):
            # Return an index in the indexed colors list for indexed address
            # spaces left to right.
            #
            # Perform implicit rotation here (0,0) is left top in BAGL, and
            # generally left bottom for various canvas.
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
    return header + bytes(image_data)


def icon_from_file(image_file: str, device: str, api_level: Optional[int]) -> bytes:
    im = Image.open(image_file)
    im.load()

    assert im.mode == "P" and len(im.getcolors()) <= MAX_COLORS

    if get_device_name(int(device, 16)) in [
        DeviceNames.LEDGER_STAX.value,
        DeviceNames.LEDGER_FLEX.value,
        DeviceNames.LEDGER_APEX_P.value,
        DeviceNames.LEDGER_APEX_M.value,
    ]:
        image_data = _image_to_buffer_nbgl(im, True, False)

    elif (
        get_device_name(int(device, 16))
        in [
            DeviceNames.LEDGER_NANO_SP.value,
            DeviceNames.LEDGER_NANO_X.value,
        ]
        and api_level is not None
        and api_level > 5
    ):
        image_data = _image_to_buffer_nbgl(im, False, True)
    else:
        image_data = _image_to_packed_buffer_bagl(im)

    return image_data


class AppManifest(ABC):
    dic: Dict = {}

    @property
    def app_name(self) -> str:
        return self.dic.get("name", "")

    @property
    def target_id(self) -> str:
        return self.dic.get("targetId", "")

    @abstractmethod
    def data_size(self, device: str) -> int:
        pass

    @abstractmethod
    def get_application_flags(self, device: str) -> int:
        pass

    @abstractmethod
    def get_api_level(self, device: str) -> Optional[int]:
        pass

    @abstractmethod
    def get_binary(self, device: str) -> str:
        pass

    @abstractmethod
    def serialize_parameters(self, device: str) -> bytes:
        pass

    @abstractmethod
    def assert_compatible_device(self, device_id: int):
        pass

    def serialize_derivation_path(self, value):
        derivation_paths: Dict[str, Optional[int]] = {
            "paths": None,
            "curve": None,
        }
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
        return derivation_paths
