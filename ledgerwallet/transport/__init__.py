from contextlib import contextmanager

from .device import Device
from .file import FileDevice
from .hid import HidDevice
from .tcp import TcpDevice

DEVICE_CLASSES = [TcpDevice, HidDevice]

__all__ = [
    "FileDevice",
]


def enumerate_devices():
    devices = []
    for cls in DEVICE_CLASSES:
        devices.extend(cls.enumerate_devices())
    return devices


@contextmanager
def open_device(dev: Device):
    """Open a device in a context manager."""
    try:
        dev.open()
        yield dev
    finally:
        dev.close()
