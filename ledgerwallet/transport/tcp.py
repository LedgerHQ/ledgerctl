import socket


class TcpDevice(object):
    def __init__(self, server: str, port: int):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((server, port))

    def write(self, data: bytes):
        # data is prefixed by its size
        data_to_send = int.to_bytes(len(data), 4, 'big') + data
        self.socket.send(data_to_send)

    def read(self) -> bytes:
        packet_len = int.from_bytes(self.socket.recv(4), 'big')
        return self.socket.recv(packet_len + 2)

    def exchange(self, data: bytes):
        self.write(data)
        return self.read()

    def close(self):
        self.socket.close()


def getDongle(server: str = "localhost", port: int = 1237):
    return TcpDevice(server, port)
