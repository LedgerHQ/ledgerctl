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

    def test_version_info_extended_build_and_parse(self):
        # Build an extended VersionInfo with optional fields present
        payload = utils.VersionInfo.build(
            dict(
                target_id=0x33000004,  # NANO_X
                se_version="1.2.3",
                flags=0,
                mcu_version="2.3.4",
                mcu_bl_version="5.6.7",
                hw_version="\x01",  # 01.00
                language="\x00",  # en
                _recover_state_len=0x01,
                recover_state=0x02,
            )
        )

        parsed = utils.VersionInfo.parse(payload)
        self.assertEqual(int(parsed.target_id), 0x33000004)
        self.assertEqual(parsed.se_version, "1.2.3")
        self.assertEqual(parsed.mcu_version, "2.3.4")
        self.assertEqual(parsed.mcu_bl_version, "5.6.7")
        self.assertEqual(parsed.hw_version, "\x01")
        self.assertEqual(parsed.language, "\x00")
        self.assertEqual(parsed._recover_state_len, 0x01)
        self.assertEqual(parsed.recover_state, 0x02)

    def test_version_info_minimal_build_and_parse(self):
        # Build a minimal VersionInfo with only required fields
        payload = utils.VersionInfo.build(
            dict(
                target_id=0x31100004,
                se_version="0",
                flags=0,
                mcu_version="0",
            )
        )

        parsed = utils.VersionInfo.parse(payload)
        self.assertEqual(int(parsed.target_id), 0x31100004)
        self.assertEqual(parsed.se_version, "0")
        self.assertEqual(parsed.mcu_version, "0")
        self.assertIsNone(parsed.mcu_bl_version)
        # When target_id is not Nano X, hw_version is an empty bytes Const
        self.assertEqual(parsed.hw_version, b"")
        self.assertIsNone(parsed.language)
        self.assertIsNone(parsed._recover_state_len)
        self.assertIsNone(parsed.recover_state)
