from .hid import HidDevice
from .tcp import TcpDevice


def enumerate_devices():
    devices = []
    for cls in [TcpDevice, HidDevice]:
        devices.extend(cls.enumerate_devices())
    return devices
