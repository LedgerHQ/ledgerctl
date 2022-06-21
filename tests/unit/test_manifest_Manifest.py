import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from ledgerwallet.manifest import AppManifest


class ManifestTest(TestCase):
    def setUp(self):
        self.data_dir = Path(__file__).parent / "data"
        self.json_path = self.data_dir / "manifest.json"
        self.assertTrue(self.json_path.is_file())
        self.manifest = AppManifest(str(self.json_path))

    def test___init__(self):
        self.assertEqual(self.manifest.path, str(self.json_path.parent))
        with self.json_path.open() as filee:
            self.assertEqual(self.manifest.json, json.load(filee))

    def test___init__error(self):
        with self.assertRaises(AssertionError):
            AppManifest(str(self.data_dir / "empty_manifest.json"))  # missing key
        with self.assertRaises(FileNotFoundError):
            AppManifest("/this/path/should/not/exist")  # file does not exist (right?)

    def test_app_name(self):
        self.assertEqual(self.manifest.app_name, "some name")

    def test_data_size(self):
        self.assertEqual(self.manifest.data_size, 42)

    def test_get_application_flags(self):
        self.assertEqual(self.manifest.get_application_flags(), 0x9999)

    def test_get_binary(self):
        self.assertEqual(self.manifest.get_binary(), str(self.data_dir / "some binary"))

    def test_get_target_id(self):
        self.assertEqual(self.manifest.get_target_id(), 0x1234)

    def test_properties_with_minimal_manifest(self):
        manifest = AppManifest(str(self.data_dir / "minimal_manifest.json"))
        with self.assertRaises(KeyError):
            manifest.app_name
        self.assertEqual(manifest.data_size, 0)
        self.assertEqual(manifest.get_application_flags(), 0)
        self.assertEqual(manifest.get_binary(), str(self.data_dir / "some binary"))
        self.assertEqual(manifest.get_target_id(), 0x1234)
        self.assertEqual(manifest.serialize_parameters(), b"")

    def test_serialize_parameters(self):
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
        with patch('ledgerwallet.manifest.icon_from_file', lambda x: b'\x01\x02\x03\x04'):
            result = self.manifest.serialize_parameters()
        self.assertEqual(result, expected)
