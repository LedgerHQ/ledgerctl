import requests
from requests.compat import urljoin


SERVER = "http://localhost:8080"


class BridgeDevice(object):
    def __init__(self, path: str):
        requests.post(urljoin(SERVER, "open"), json={"path": path})

    def write(self, data: bytes):
        # print("Writing {}".format(data.hex()))
        requests.post(urljoin(SERVER, "write"), json={"data": data.hex()})

    def read(self, timeout: int) -> bytes:
        req = requests.get(urljoin(SERVER, "read"))
        data = bytes.fromhex(req.json()['data'])
        # print("Read {}".format(data.hex()))
        return data

    def exchange(self, data: bytes, timeout=1000):
        self.write(data)
        return self.read(timeout)


def getDongle():
    req = requests.get(urljoin(SERVER, "enumerate"))
    data = req.json()
    if 'devices' in data and len(data['devices']) > 0:
        path = data['devices'][0]
        return BridgeDevice(path)
