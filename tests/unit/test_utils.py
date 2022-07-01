from unittest import TestCase

from ledgerwallet import utils


class UtilsModuleTest(TestCase):
    def test_serialize(self):
        sample = b"some bytes"
        result = utils.serialize(sample)
        self.assertEqual(result[0], len(result) - 1)
        self.assertEqual(result[0], len(sample))

    def test_unserialize(self):
        sample = bytes.fromhex("0304050607")
        result, rest = utils.unserialize(sample)
        self.assertEqual(result, sample[1 : 1 + sample[0]])
        self.assertEqual(rest, sample[1 + sample[0] :])

    def test_unserialize_too_small(self):
        sample = bytes.fromhex("01")
        with self.assertRaises(AssertionError):
            utils.unserialize(sample)

    def test_flags_to_string(self):
        self.assertEqual(
            utils.flags_to_string(5333),
            "issuer,signed,derive_master,global_pin,debug,custom_ca,no_run",
        )
