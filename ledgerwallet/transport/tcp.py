import os
import socket


class TcpDevice(object):
    LEDGER_PROXY_ADDRESS = "127.0.0.1"
    LEDGER_PROXY_PORT = 1237

    def __init__(self, path: str):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server, port = path.split(":")
        self.server = server
        self.port = int(port)

    @classmethod
    def enumerate_devices(cls):
        if "LEDGER_PROXY_ADDRESS" in os.environ and "LEDGER_PROXY_PORT" in os.environ:
            return [
                TcpDevice(
                    "{0:s}:{1:d}".format(
                        os.environ["LEDGER_PROXY_ADDRESS"],
                        int(os.environ["LEDGER_PROXY_PORT"]),
                    )
                )
            ]
        else:
            return []

    def open(self):
        self.socket.connect((self.server, self.port))

    def write(self, data: bytes):
        # data is prefixed by its size
        data_to_send = int.to_bytes(len(data), 4, "big") + data
        self.socket.send(data_to_send)

    def read(self) -> bytes:
        packet_len = int.from_bytes(self.socket.recv(4), "big")
        return self.socket.recv(packet_len + 2)

    def exchange(self, data: bytes):
        self.write(data)
        return self.read()

    def close(self):
        self.socket.close()
