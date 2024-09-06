import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from ledgerwallet.manifest_json import AppManifestJson


class ManifestTestJson(TestCase):
    def setUp(self):
        self.data_dir = Path(__file__).parent / "data"
        self.json_path = self.data_dir / "manifest.json"
        self.assertTrue(self.json_path.is_file())
        self.json_manifest = AppManifestJson(str(self.json_path))

    def test___init__(self):
        self.assertEqual(self.json_manifest.path, str(self.json_path.parent))
        with self.json_path.open() as filee:
            self.assertEqual(self.json_manifest.dic, json.load(filee))

    def test___init__error(self):
        with self.assertRaises(AssertionError):
            AppManifestJson(str(self.data_dir / "empty_manifest.json"))  # missing key

    def test_app_name(self):
        self.assertEqual(self.json_manifest.app_name, "some name")

    def test_data_size(self):
        self.assertEqual(self.json_manifest.data_size(""), 42)

    def test_get_application_flags(self):
        self.assertEqual(self.json_manifest.get_application_flags(""), 0x9999)

    def test_get_binary(self):
        self.assertEqual(
            self.json_manifest.get_binary(""), str(self.data_dir / "some binary")
        )

    def test_get_target_id(self):
        self.json_manifest.assert_compatible_device(0x1234)

    def test_properties_with_minimal_manifest(self):
        manifest_json = AppManifestJson(str(self.data_dir / "minimal_manifest.json"))
        self.assertEqual(manifest_json.app_name, "")
        self.assertEqual(manifest_json.data_size(""), 0)
        self.assertEqual(manifest_json.get_application_flags(""), 0)
        self.assertEqual(
            manifest_json.get_binary(""), str(self.data_dir / "some binary")
        )
        self.assertEqual(manifest_json.serialize_parameters(""), b"")

    def test_serialize_parameters(self):
        # fmt: off
        expected = bytes.fromhex(
            "01" +  # BolosTag 'AppName'
            "09" + "736f6d65206e616d65" +  # "some name"
            "02" +  # BolosTag 'Version'
            "0b" + "322e392e342d6465627567" +  # 2.9.4-debug
            "03" +  # BolosTag 'Icon'
            "04" + "01020304" +  # mocked icon
            "04" +  # BolosTag 'DerivationPath'
            "23" +  # 35: following size
            "05" +  # secp256k1 (1) + ed25519 (4)
            "03" + "8000002c80000000000000ff" +                # "44'/0'/255"
            "05" + "8000002c80000000800000000000000100000190"  # "44'/0'/0'/1/400"
        )
        # fmt: on
        with patch(
            "ledgerwallet.manifest_json.icon_from_file",
            lambda x, y, z: b"\x01\x02\x03\x04",
        ):
            result_json = self.json_manifest.serialize_parameters("1234")
        self.assertEqual(result_json, expected)
