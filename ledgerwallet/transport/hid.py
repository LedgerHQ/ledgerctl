import os
if os.getenv("LEDGERWALLET_HIDRAW", "").lower() in ["1", "true"]:
    import hidraw as hid
else:
    import hid

LEDGER_VENDOR_ID = 0x2C97


class HidDevice(object):
    def __init__(self, path):
        self.path = path
        self.device = None
        self.opened = False

    @classmethod
    def enumerate_devices(cls):
        devices = []
        for hidDevice in hid.enumerate(LEDGER_VENDOR_ID, 0):
            if (
                "interface_number" in hidDevice and hidDevice["interface_number"] == 0
            ) or ("usage_page" in hidDevice and hidDevice["usage_page"] == 0xFFA0):
                hid_device_path = hidDevice["path"]
                devices.append(HidDevice(hid_device_path))
        return devices

    def get_name(self):
        return "hid:{}".format(self.path.decode())

    def open(self):
        self.device = hid.device()
        self.device.open_path(self.path)
        self.device.set_nonblocking(True)
        self.opened = True

    def write(self, data):
        # data is prefixed by its size
        data_to_send = int.to_bytes(len(data), 2, "big") + data
        offset = 0
        seq_idx = 0
        while offset < len(data_to_send):
            # Header: channel (0x101), tag (0x05), sequence index
            header = b"\x01\x01\x05" + seq_idx.to_bytes(2, "big")
            pkt_data = header + data_to_send[offset : offset + 64 - len(header)]

            self.device.write(b"\x00" + pkt_data)
            offset += 64 - len(header)
            seq_idx += 1

    def read(self, timeout: int) -> bytes:
        seq_idx = 0

        self.device.set_nonblocking(False)
        data_chunk = bytes(self.device.read(64 + 1))
        self.device.set_nonblocking(True)

        assert data_chunk[:2] == b"\x01\x01"
        assert data_chunk[2] == 5
        assert data_chunk[3:5] == seq_idx.to_bytes(2, "big")

        data_len = int.from_bytes(data_chunk[5:7], "big")
        data = data_chunk[7:]

        while len(data) < data_len:
            read_bytes = bytes(self.device.read(64 + 1, timeout_ms=timeout))
            data += read_bytes[5:]

        data = data[:data_len]
        return data

    def exchange(self, data: bytes, timeout=1000):
        self.write(data)
        return self.read(timeout)

    def close(self):
        if self.opened:
            try:
                self.device.close()
            except:
                pass
        self.opened = False


"""
def getDongle():
    hid_device_path = None
    for hidDevice in hid.enumerate(LEDGER_VENDOR_ID, 0):
        if ('interface_number' in hidDevice and hidDevice['interface_number'] == 0) or (
                'usage_page' in hidDevice and hidDevice['usage_page'] == 0xffa0):
            hid_device_path = hidDevice['path']
    if hid_device_path is not None:
        dev = hid.device()
        dev.open_path(hid_device_path)
        dev.set_nonblocking(True)
        return HidDevice(dev)
    raise Exception("No dongle found")
"""
