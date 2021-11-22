import enum

from construct import (
    Adapter,
    Byte,
    Construct,
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
            num = num << 8 + len_byte
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


# noinspection PyAbstractClass
class Bip32PathAdapter(Adapter):
    def _decode(self, obj, context, path):
        out = list()
        for element in obj:
            if element & 0x80000000:
                out.append(str(element & 0x7FFFFFFF) + "'")
            else:
                out.append(str(element))
        return "/".join(out)

    def _encode(self, obj, context, path):
        out = list()
        elements = obj.split("/")
        if elements[0] == "m":
            elements = elements[1:]
        for element in elements:
            if element.endswith("'"):
                out.append(0x80000000 | int(element[:-1]))
            else:
                out.append(int(element))
        return out


Bip32Path = Bip32PathAdapter(PrefixedArray(Byte, Int32ub))

PrefixedString = PascalString(Asn1Length, "utf8")

AppName = PrefixedString
Version = PrefixedString
Icon = Prefixed(Asn1Length, GreedyBytes)

CURVE_SECP256K1 = 1
CURVE_PRIME256R1 = 2
CURVE_ED25519 = 4
CURVE_BLS12381G1 = 16

Curve = FlagsEnum(
    Byte,
    secp256k1=CURVE_SECP256K1,
    prime256r1=CURVE_PRIME256R1,
    ed25519=CURVE_ED25519,
    bls12381g1=CURVE_BLS12381G1,
)

DerivationPath = Prefixed(
    Asn1Length, Struct(curve=Curve, paths=Optional(GreedyRange(Bip32Path)))
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


def main():
    params1 = AppParams.build(
        [
            {"type_": "BOLOS_TAG_APPNAME", "value": "SSH/PGP Agent"},
            {"type_": "BOLOS_TAG_APPVERSION", "value": "0.0.4"},
            {
                "type_": "BOLOS_TAG_ICON",
                "value": b"\x01\x00\x00\x00\x00\xFF\xFF\xFF\x00\x00\x18\xFC\x24\x02"
                b"\x24\x0A\x24\x1A\x7E\x32\x66\x62\x6E\x62\x7E\x32\x00\x1A"
                b"\x40\x0A\x5F\x02\x5F\x02\x40\x02\x40\xFE\x7F\x00\x00",
            },
            {
                "type_": "BOLOS_TAG_DERIVEPATH",
                "value": {
                    "curve": Curve.prime256r1 | Curve.ed25519,
                    "paths": ["44'/535348'", "13'", "17'"],
                },
            },
        ]
    )

    params2 = (
        b"\x01\x0D\x53\x53\x48\x2F\x50\x47\x50\x20\x41\x67\x65\x6E\x74"
        b"\x02\x05\x30\x2E\x30\x2E\x34\x03\x29\x01\x00\x00\x00\x00\xFF"
        b"\xFF\xFF\x00\x00\x18\xFC\x24\x02\x24\x0A\x24\x1A\x7E\x32\x66"
        b"\x62\x6E\x62\x7E\x32\x00\x1A\x40\x0A\x5F\x02\x5F\x02\x40\x02"
        b"\x40\xFE\x7F\x00\x00\x04\x14\x06\x02\x80\x00\x00\x2C\x80\x08"
        b"\x2B\x34\x01\x80\x00\x00\x0D\x01\x80\x00\x00\x11"
    )
    assert params1 == params2


if __name__ == "__main__":
    main()
