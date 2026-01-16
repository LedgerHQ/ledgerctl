import enum

from construct import (
    Adapter,
    Byte,
    Construct,
    Default,
    Enum,
    FlagsEnum,
    GreedyBytes,
    GreedyRange,
    Int32ub,
    IntegerError,
    Optional,
    PascalString,
    Prefixed,
    PrefixedArray,
    Struct,
    Switch,
)
from construct.core import (
    byte2int,
    singleton,
    stream_read,
    stream_write,
    swapbytes,
    this,
)
from construct.lib import int2byte, integertypes


# noinspection PyAbstractClass
@singleton
class Asn1Length(Construct):
    def _parse(self, stream, context, path):
        byte = byte2int(stream_read(stream, 1, path))
        if byte & 0x80 == 0:
            return byte

        num_bytes = byte & ~0x80
        encoded_len = stream_read(stream, num_bytes, path)
        num = 0
        for len_byte in encoded_len:
            num = (num << 8) + len_byte
        return num

    def _build(self, obj, stream, context, path):
        if not isinstance(obj, integertypes):
            raise IntegerError("value is not an integer")
        if obj < 0:
            raise IntegerError(
                "asn1length cannot build from negative number: %r" % (obj,)
            )
        num = obj
        if num < 0x80:
            stream_write(stream, int2byte(num), 1, path)
        else:
            acc = b""
            while num != 0:
                acc += int2byte(num & 0xFF)
                num >>= 8
            stream_write(stream, int2byte(0x80 | len(acc)), 1, path)
            stream_write(stream, swapbytes(acc), len(acc), path)
        return obj

    def _emitprimitivetype(self, ksy, bitwise):
        return "asn1_der_len"


# A byte with value < 0x80
@singleton
class LowByte(Construct):
    def _parse(self, stream, context, path):
        b = byte2int(stream_read(stream, 1, path))
        if b >= 0x80:
            raise IntegerError("BIP32 path length prefix must be < 0x80")
        return b

    def _build(self, obj, stream, context, path):
        if not isinstance(obj, int):
            raise IntegerError("length must be an integer")
        if not (0 <= obj < 0x80):
            raise IntegerError("BIP32 path length must be < 0x80")
        stream_write(stream, int2byte(obj), 1, path)
        return obj


# A byte with value >= 0x80, decoded as (byte - 0x80)
# This is used to encode the length of SLIP-21 paths
@singleton
class Slip21LenByte(Construct):
    def _parse(self, stream, context, path):
        b = byte2int(stream_read(stream, 1, path))
        if b < 0x80:
            raise IntegerError("SLIP-21 length prefix must be >= 0x80")
        return b - 0x80

    def _build(self, obj, stream, context, path):
        if not isinstance(obj, int):
            raise IntegerError("length must be an integer")
        if not (0 <= obj <= 0x7F):
            raise IntegerError("SLIP-21 decoded length must be in [0, 0x7F]")
        stream_write(stream, int2byte(0x80 + obj), 1, path)
        return obj


class Slip21PathAdapter(Adapter):
    def _decode(self, obj, context, path):
        # obj is now a list/array of bytes (ints 0–255)
        if not obj:
            return str()

        # First byte must be zero prefix
        if obj[0] != 0x00:
            raise IntegerError("invalid SLIP-21 path prefix")

        # Remaining bytes are UTF-8 chars
        return bytes(obj[1:]).decode("utf-8")

    def _encode(self, obj, context, path):
        if not isinstance(obj, str):
            raise IntegerError("SLIP-21 path must be a string")

        payload = b"\0" + obj.encode("utf-8")
        length = len(payload)
        if length > 0x7F:
            raise IntegerError("SLIP-21 path too long")

        # Return list of ints so PrefixedArray(Slip21LenByte, Byte) can handle it
        return list(payload)


# noinspection PyAbstractClass
class Bip32PathAdapter(Adapter):
    def _decode(self, obj, context, path):
        out = list()
        for element in obj:
            if element & 0x80000000:
                out.append(str(element & 0x7FFFFFFF) + "'")
            else:
                if element == 0x7FFFFFFF:
                    out.append("*")
                else:
                    out.append(str(element))
        return "/".join(out)

    def _encode(self, obj, context, path):
        if obj == "":
            # empty path
            return list()
        out = list()
        elements = obj.split("/")
        if elements[0] == "m":
            elements = elements[1:]
        for element in elements:
            if element.endswith("'"):
                out.append(0x80000000 | int(element[:-1]))
            elif element == "*":
                out.append(0x7FFFFFFF)
            else:
                value = int(element)
                if value == 0x7FFFFFFF:
                    raise ValueError(
                        f"Invalid BIP32 path: {element} value is reserved for wildcard"
                        " symbol"
                    )
                elif value > 0x7FFFFFFF:
                    raise ValueError(
                        f"Invalid BIP32 path: {element} value is too large. For"
                        " hardened paths, use the quote symbol"
                    )
                out.append(value)
        return out


Bip32Path = Bip32PathAdapter(PrefixedArray(LowByte, Int32ub))
Slip21Path = Slip21PathAdapter(PrefixedArray(Slip21LenByte, Byte))

PrefixedString = PascalString(Asn1Length, "utf8")

AppName = PrefixedString
Version = PrefixedString
Icon = Prefixed(Asn1Length, GreedyBytes)

CURVE_SECP256K1 = 1
CURVE_PRIME256R1 = 2
CURVE_ED25519 = 4
CURVE_SLIP21 = (
    8  # not really a curve, but used to indicate the presence of SLIP-21 paths
)
CURVE_BLS12381G1 = 16

Curve = FlagsEnum(
    Byte,
    secp256k1=CURVE_SECP256K1,
    prime256r1=CURVE_PRIME256R1,
    ed25519=CURVE_ED25519,
    slip21=CURVE_SLIP21,
    bls12381g1=CURVE_BLS12381G1,
)

DerivationPath = Prefixed(
    Asn1Length,
    Struct(
        curve=Curve,
        paths=Default(GreedyRange(Bip32Path), []),
        paths_slip21=Default(GreedyRange(Slip21Path), []),
    ),
)

Dependency = Prefixed(
    Asn1Length, Struct(name=PrefixedString, version=Optional(PrefixedString))
)

Dependencies = Prefixed(Asn1Length, GreedyRange(Dependency))


class BolosTag(enum.IntEnum):
    BOLOS_TAG_APPNAME = 1
    BOLOS_TAG_APPVERSION = 2
    BOLOS_TAG_ICON = 3
    BOLOS_TAG_DERIVEPATH = 4
    BOLOS_TAG_DEPENDENCY = 6


Param = Struct(
    type_=Enum(Byte, BolosTag),
    value=Switch(
        this.type_,
        {
            "BOLOS_TAG_APPNAME": AppName,
            "BOLOS_TAG_APPVERSION": Version,
            "BOLOS_TAG_ICON": Icon,
            "BOLOS_TAG_DERIVEPATH": DerivationPath,
            "BOLOS_TAG_DEPENDENCY": Dependencies,
        },
    ),
)

AppParams = GreedyRange(Param)
