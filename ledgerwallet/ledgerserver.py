from abc import ABC, abstractmethod


class LedgerServer(ABC):
    @abstractmethod
    def get_nonce(self) -> bytes:
        pass

    @abstractmethod
    def send_nonce(self, nonce: bytes):
        pass

    @abstractmethod
    def receive_certificate_chain(self):
        pass

    @abstractmethod
    def send_certicate_chain(self, chain):
        pass

    def get_shared_secret(self):
        return None
