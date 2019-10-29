from .hid import HidDevice
from .tcp import TcpDevice

DEVICE_CLASSES = [TcpDevice, HidDevice]


def enumerate_devices():
    devices = []
    for cls in DEVICE_CLASSES:
        devices.extend(cls.enumerate_devices())
    return devices
