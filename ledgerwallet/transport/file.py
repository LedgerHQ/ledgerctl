from .device import Device


class FileDevice(Device):
    def __init__(self):
        pass

    def enumerate_devices(self, cls):
        return FileDevice()

    def open(self):
        pass

    def write(self, data: bytes):
        print(data.hex())

    def read(self, timeout: int = 0) -> bytes:
        return b"\x00\x00\x00\x02\x90\x00"

    def exchange(self, data: bytes, timeout: int = 0) -> bytes:
        self.write(data)
        return self.read()

    def close(self):
        pass
