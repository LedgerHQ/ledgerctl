from abc import ABC, abstractmethod


class Device(ABC):
    @classmethod
    @abstractmethod
    def enumerate_devices(cls):
        raise NotImplementedError

    @abstractmethod
    def open(self):
        raise NotImplementedError

    @abstractmethod
    def write(self, data: bytes):
        raise NotImplementedError

    @abstractmethod
    def read(self, timeout: int = 0) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def exchange(self, data: bytes, timeout: int = 0) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError
