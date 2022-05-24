import asyncio
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
from typing import List

HANDLE_CHAR_ENABLE_NOTIF = 13
HANDLE_CHAR_WRITE = 16
TAG_ID = b"\x05"


queue: asyncio.Queue = asyncio.Queue()


async def ble_discover():
    devices = await BleakScanner.discover(2)
    return devices


def callback(sender, data):
    response = bytes(data)
    queue.put_nowait(response)


async def _get_client(ble_address: str) -> BleakClient:
    device = await BleakScanner.find_device_by_address(ble_address, timeout=2.0)
    if not device:
        raise BleakError(f"Device with address {ble_address} could not be found.")

    client = BleakClient(device)
    await client.connect()

    # register notification callback
    # callback = lambda sender, data: queue.put_nowait(bytes(data))
    await client.start_notify(HANDLE_CHAR_ENABLE_NOTIF, callback)

    # enable notifications
    await client.write_gatt_char(HANDLE_CHAR_WRITE, bytes.fromhex("0001"), True)
    assert await queue.get() == b"\x00\x00\x00\x00\x00"

    # confirm that the MTU is 0x99
    await client.write_gatt_char(HANDLE_CHAR_WRITE, bytes.fromhex("0800000000"), True)
    assert await queue.get() == b"\x08\x00\x00\x00\x01\x99"

    return client


async def _read() -> bytes:
    response = await queue.get()

    assert len(response) >= 5
    assert response[0] == TAG_ID[0]
    assert response[1:3] == b"\x00\x00"
    total_size = int.from_bytes(response[3:5], "big")

    apdu = response[5:]
    i = 1
    if len(apdu) < total_size:
        assert total_size > len(response) - 5

        response = await queue.get()

        assert len(response) >= 3
        assert response[0] == TAG_ID[0]
        assert int.from_bytes(response[1:3], "big") == i
        i += 1
        apdu += response[3:]

    assert len(apdu) == total_size
    return apdu


async def _write(client: BleakClient, data: bytes, mtu: int = 0x99):
    chunks: List[bytes] = []
    buffer = data
    while buffer:
        if not chunks:
            size = 5
        else:
            size = 3
        size = mtu - size
        chunks.append(buffer[:size])
        buffer = buffer[size:]

    for i, chunk in enumerate(chunks):
        header = TAG_ID
        header += i.to_bytes(2, "big")
        if i == 0:
            header += len(data).to_bytes(2, "big")
        await client.write_gatt_char(HANDLE_CHAR_WRITE, header + chunk, True)


class BleDevice(object):
    def __init__(self, device):
        self.device = device
        self.loop = None
        self.client = None
        self.opened = False

    @classmethod
    def enumerate_devices(cls):
        loop = asyncio.get_event_loop()
        discovered_devices = loop.run_until_complete(ble_discover())
        devices = []
        for device in discovered_devices:
            if device.name is not None:
                if device.name.startswith("Nano X"):
                    devices.append(BleDevice(device))
        return devices

    def __str__(self):
        return "[BLE Device] {} ({})".format(self.device.name, self.device.address)

    def open(self):
        self.loop = asyncio.get_event_loop()
        self.client = self.loop.run_until_complete(_get_client(self.device.address))
        self.opened = True

    def close(self):
        if self.opened:
            self.loop.run_until_complete(self.client.disconnect())
            self.opened = False
            self.loop.close()

    def write(self, data: bytes):
        self.loop.run_until_complete(_write(self.client, data))

    def read(self) -> bytes:
        return self.loop.run_until_complete(_read())

    def exchange(self, data: bytes, timeout=1000):
        self.write(data)
        return self.read()
