import sys

from ..utils import LedgerIns, VersionInfo
from .device import Device


class FileDevice(Device):
    def __init__(self, target_id, out=None):
        if out is None:
            out = sys.stdout
        t_id = int(target_id, 16)
        self.version_info = VersionInfo.build(
            dict(target_id=t_id, se_version="0", flags=0, mcu_version="0")
        )
        self.buffer = None
        self.out = out

    @classmethod
    def enumerate_devices(cls):
        return None

    def open(self):
        pass

    def write(self, data: bytes):
        self.buffer = data
        if not self.buffer[1] == LedgerIns.GET_VERSION:
            print(data.hex(), file=self.out)

    def read(self, timeout: int = 0) -> bytes:
        if self.buffer[1] == LedgerIns.GET_VERSION:
            return self.version_info + b"\x90\x00"
        return b"\x00\x00\x00\x02\x90\x00"

    def exchange(self, data: bytes, timeout: int = 0) -> bytes:
        self.write(data)
        return self.read()

    def close(self):
        if self.out:
            self.out.close()
