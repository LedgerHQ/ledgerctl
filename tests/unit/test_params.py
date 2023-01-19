from unittest import TestCase

from construct import StreamError

from ledgerwallet.params import (
    Asn1Length,
    Bip32Path,
    Dependencies,
    Dependency,
    DerivationPath,
)


class Asn1LengthTest(TestCase):
    sample = {
        0: bytes.fromhex("00"),
        4: bytes.fromhex("04"),
        127: bytes.fromhex("7f"),
        128: bytes.fromhex("8180"),
        160: bytes.fromhex("81a0"),
        255: bytes.fromhex("81ff"),
        256: bytes.fromhex("820100"),
    }

    def test_parse(self):
        for k, v in self.sample.items():
            self.assertEqual(Asn1Length.parse(v), k)

    def test_build(self):
        for k, v in self.sample.items():
            self.assertEqual(Asn1Length.build(k), v)


class Bip32PathTest(TestCase):
    sample = {
        "1": bytes.fromhex("01 00000001"),
        "1'": bytes.fromhex("01 80000001"),
        "0'/0": bytes.fromhex("02 80000000 00000000"),
        "44'/91223'/2": bytes.fromhex("03 8000002c 80016457 00000002"),
        "44'/0'/0'/1/400": bytes.fromhex(
            "05 8000002c 80000000 80000000 00000001 00000190"
        ),
    }

    def test_parse(self):
        for k, v in self.sample.items():
            self.assertEqual(Bip32Path.parse(v), k)

    def test_parse_empty(self):
        # not in sample as not the parse/build behavior is not symmetrical
        self.assertEqual(Bip32Path.parse(bytes.fromhex("00")), str())

    def test_build(self):
        for k, v in self.sample.items():
            self.assertEqual(Bip32Path.build(k), v)

    def test_parse_error(self):
        errors = [
            b"",  # empty string is not parsable
            bytes.fromhex("01"),  # expecting 4 more bytes (Int32ub)
        ]
        for error in errors:
            with self.assertRaises(StreamError):
                Bip32Path.parse(error)


class DerivationPathTest(TestCase):
    def test_parse_empty(self):
        result = DerivationPath.parse(bytes.fromhex("01 00"))
        self.assertFalse(result.curve.secp256k1)
        self.assertFalse(result.curve.prime256r1)
        self.assertFalse(result.curve.ed25519)
        self.assertFalse(result.curve.bls12381g1)
        self.assertFalse(result.paths)

    def test_parse_keys(self):
        # [secp256k1, prime256r1, ed25519, bls12381g1]
        # fmt: off
        keys = [
            [False, False, False, False],
            [True,  False, False, False],
            [False, True,  False, False],
            [True,  True,  False, False],
            [False, False, True,  False],
            [True,  False, True,  False],
            [False, True,  True,  False],
            [True,  True,  True,  False],
            [False, False, False, True],
            [True,  False, False, True],
            [False, True,  False, True],
            [True,  True,  False, True],
            [False, False, True,  True],
            [True,  False, True,  True],
            [False, True,  True,  True],
            [True,  True,  True,  True],
        ]
        # fmt: on
        for i in range(8):
            result = DerivationPath.parse(bytes([1, i]))
            self.assertListEqual(
                [
                    result.curve.secp256k1,
                    result.curve.prime256r1,
                    result.curve.ed25519,
                    result.curve.bls12381g1,
                ],
                keys[i],
            )
        # bls12381g1 store on 5th bit (16), not 4th (8)
        # so there is a bit gap from 8 to 16
        for i in range(16, 24):
            result = DerivationPath.parse(bytes([1, i]))
            self.assertListEqual(
                [
                    result.curve.secp256k1,
                    result.curve.prime256r1,
                    result.curve.ed25519,
                    result.curve.bls12381g1,
                ],
                keys[i - 8],
            )

    def test_parse_with_paths(self):
        path1 = (
            bytes.fromhex("05 8000002c 80000000 80000000 00000001 00000190"),
            "44'/0'/0'/1/400",
        )
        path2 = (bytes.fromhex("03 8000002c 80000000 000000ff"), "44'/0'/255")
        key = bytes.fromhex("11")
        size = len(path1[0]) + len(path2[0]) + len(key)
        result = DerivationPath.parse(bytes([size]) + key + path1[0] + path2[0])
        self.assertTrue(result.curve.secp256k1)
        self.assertFalse(result.curve.prime256r1)
        self.assertFalse(result.curve.ed25519)
        self.assertTrue(result.curve.bls12381g1)
        self.assertEqual(result.paths, [path1[1], path2[1]])

    def test_parse_error(self):
        errors = [
            b"",  # empty string is not parsable
            bytes.fromhex("01"),  # expecting more bytes (curve)
        ]
        for error in errors:
            with self.assertRaises(StreamError):
                DerivationPath.parse(error)


class DependencyTest(TestCase):
    def test_parse_no_version(self):
        name = "name"
        asn1_name = bytes([len(name)]) + name.encode()
        result = Dependency.parse(bytes([len(asn1_name)]) + asn1_name)
        self.assertEqual(result.name, name)
        self.assertIsNone(result.version)

    def test_parse_with_version(self):
        name = "name"
        version = "1.0.1"
        asn1_name = bytes([len(name)]) + name.encode()
        asn1_version = bytes([len(version)]) + version.encode()
        result = Dependency.parse(
            bytes([len(asn1_name + asn1_version)]) + asn1_name + asn1_version
        )
        self.assertEqual(result.name, name)
        self.assertEqual(result.version, version)


class DependenciesTest(TestCase):
    def test_parse(self):
        name1 = "name1"
        version = "1.0.1"
        asn1_name1 = bytes([len(name1)]) + name1.encode()
        asn1_version = bytes([len(version)]) + version.encode()
        dep1 = bytes([len(asn1_name1 + asn1_version)]) + asn1_name1 + asn1_version
        name2 = "name2"
        asn1_name2 = bytes([len(name2)]) + name2.encode()
        dep2 = bytes([len(asn1_name2)]) + asn1_name2
        result = Dependencies.parse(bytes([len(dep1 + dep2)]) + dep1 + dep2)
        self.assertEqual(result[0].name, name1)
        self.assertEqual(result[0].version, version)
        self.assertEqual(result[1].name, name2)
        self.assertIsNone(result[1].version)
