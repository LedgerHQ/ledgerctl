from .device import Device
from .hid import HidDevice
from .tcp import TcpDevice

DEVICE_CLASSES = [TcpDevice, HidDevice]


def enumerate_devices():
    devices = []
    for cls in DEVICE_CLASSES:
        devices.extend(cls.enumerate_devices())
    return devices


class open_device:
    """Open a device in a context manager."""

    def __init__(self, device: Device):
        self.device = device

    def __enter__(self):
        self.device.open()
        return self.device

    def __exit__(self, *exc_details):
        self.device.close()
