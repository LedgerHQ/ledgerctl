from unittest import TestCase

from ledgerwallet.crypto import ecc

RAW_PRIVATE = bytes.fromhex(
    "c2cdf0a8b0a83b35ace53f097b5e6e6a0a1f2d40535eff1cf434f52a43d59d8f"
)
RAW_PUBLIC = bytes.fromhex(
    "6fcc37ea5e9e09fec6c83e5fbd7a745e3eee81d16ebd861c9e66f55518c19798"
    + "4e9f113c07f875691df8afc1029496fc4cb9509b39dcd38f251a83359cc8b4f7"
)


class PrivateKeyTest(TestCase):
    def setUp(self):
        self.key = ecc.PrivateKey(RAW_PRIVATE)

    def test_pubkey(self):
        self.assertEqual(
            self.key.pubkey.serialize(compressed=False), bytes([0x04]) + RAW_PUBLIC
        )

    def test_serialize(self):
        self.assertEqual(self.key.serialize(), RAW_PRIVATE)

    def test_sign(self):
        blob = b"someblobofdata"
        signature = self.key.sign(blob)
        self.assertTrue(self.key.pubkey.verify(blob, signature))


class PublickKeyTest(TestCase):
    def setUp(self):
        self.public = bytes([0x04]) + RAW_PUBLIC
        self.key = ecc.PublicKey(self.public)

    def test___init__fail(self):
        with self.assertRaises(ValueError):
            ecc.PublicKey(b"")  # not 65-bytes long
        with self.assertRaises(ValueError):
            self.public = bytes([0x00]) + self.public[1:]
            ecc.PublicKey(self.public)  # must start with 0x04

    def test_serialize_uncompressed(self):
        self.assertEqual(self.key.serialize(compressed=False), self.public)

    def test_serialize_compressed(self):
        with self.assertRaises(NotImplementedError):
            self.key.serialize()
