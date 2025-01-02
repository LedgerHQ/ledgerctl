from ledgerwallet.transport import open_device
from ledgerwallet.transport.device import Device


class MockDevice(Device):
    @classmethod
    def enumerate_devices(cls):
        """Do nothing."""

    def __init__(self):
        self.is_open = False

    def open(self):
        self.is_open = True

    def write(self, data: bytes):
        """Do nothing."""

    def read(self, timeout: int = 0) -> bytes:
        """Do nothing."""
        return b""

    def exchange(self, data: bytes, timeout: int = 0) -> bytes:
        """Do nothing."""
        return b""

    def close(self):
        self.is_open = False


def test_context_manager():
    dev = MockDevice()
    assert not dev.is_open

    with open_device(dev):
        assert dev.is_open

    assert not dev.is_open
