import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

if sys.version_info >= (3, 11):
    import tomllib
else:
    import toml as tomllib

from ledgerwallet.manifest import AppManifestToml


class ManifestTest(TestCase):
    def setUp(self):
        self.data_dir = Path(__file__).parent / "data"
        self.toml_path = self.data_dir / "manifest.toml"
        self.assertTrue(self.toml_path.is_file())
        self.manifest = AppManifestToml(str(self.toml_path))

    def test___init__(self):
        self.assertEqual(self.manifest.path, str(self.toml_path.parent))
        if sys.version_info >= (3, 11):
            with self.toml_path.open("rb") as filee:
                self.assertEqual(self.manifest.toml, tomllib.load(filee))
        else:
            with self.toml_path.open("r") as filee:
                self.assertEqual(self.manifest.toml, tomllib.load(filee))

    def test___init__error(self):
        manifest = AppManifestToml(str(self.data_dir / "missing_binary_manifest.toml"))
        self.assertEqual(manifest.is_device_defined("1234"), False)
        with self.assertRaises(FileNotFoundError):
            AppManifestToml(
                "/this/path/should/not/exist"
            )  # file does not exist (right?)

    def test_app_name(self):
        self.assertEqual(self.manifest.app_name, "some name")

    def test_data_size(self):
        self.assertEqual(self.manifest.data_size("1234"), 42)

    def test_get_application_flags(self):
        self.assertEqual(self.manifest.get_application_flags("1234"), 0x9999)

    def test_get_binary(self):
        self.assertEqual(
            self.manifest.get_binary("1234"), str(self.data_dir / "some binary")
        )

    def test_properties_with_minimal_manifest(self):
        manifest = AppManifestToml(str(self.data_dir / "minimal_manifest.toml"))
        with self.assertRaises(KeyError):
            manifest.app_name
        self.assertEqual(manifest.data_size("1234"), 0)
        self.assertEqual(manifest.get_application_flags("1234"), 0)
        self.assertEqual(
            manifest.get_binary("1234"), str(self.data_dir / "some binary")
        )
        self.assertEqual(manifest.serialize_parameters("1234"), b"")
        self.assertEqual(manifest.is_device_defined("1234"), True)

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
            "ledgerwallet.manifest.icon_from_file", lambda x: b"\x01\x02\x03\x04"
        ):
            result = self.manifest.serialize_parameters("1234")

        self.assertEqual(result, expected)
