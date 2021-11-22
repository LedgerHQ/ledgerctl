import struct

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import constant_time, hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

BLOCK_SIZE = 16


def iso9797_pad(data: bytes) -> bytes:
    padding_len = BLOCK_SIZE - len(data) % BLOCK_SIZE
    return data + b"\x80" + b"\x00" * (padding_len - 1)


def iso9797_unpad(data: bytes) -> bytes:
    assert len(data) >= BLOCK_SIZE and len(data) % BLOCK_SIZE == 0

    last_block = data[-BLOCK_SIZE:]
    while len(last_block) > 0:
        if last_block[-1] == 0x80:
            return data[:-BLOCK_SIZE] + last_block[:-1]
        elif last_block[-1] != 0:
            raise ValueError("Invalid padding")
        last_block = last_block[:-1]
    raise ValueError("Invalid padding")


class SCP(object):
    SCP_MAC_LENGTH = 14
    VERSION = 3

    def __init__(self, secret: bytes):
        self.enc_key = self._derive_key(secret, 0, 16)
        self.mac_key = self._derive_key(secret, 1, 16)
        self.enc_iv = b"\x00" * BLOCK_SIZE
        self.mac_iv = b"\x00" * BLOCK_SIZE

    @staticmethod
    def _derive_key(secret: bytes, index: int, key_len: int) -> bytes:
        retry = 0

        # secp256k1 curve order
        curve_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        while True:
            digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
            digest.update(struct.pack(">IB", index, retry))
            digest.update(secret)
            md = digest.finalize()

            private_value = int.from_bytes(md, "big")
            if private_value < curve_order and private_value != 0:
                break
            retry += 1

        key = ec.derive_private_key(private_value, ec.SECP256K1(), default_backend())
        public_key = key.public_key()

        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(
            public_key.public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint,
            )
        )
        return digest.finalize()[:key_len]

    def _decrypt_data(self, data: bytes) -> bytes:
        cipher = Cipher(
            algorithms.AES(self.enc_key), modes.CBC(self.enc_iv), default_backend()
        )
        self.enc_iv = data[-BLOCK_SIZE:]
        decrypted_data = cipher.decryptor().update(data)
        return decrypted_data

    def _encrypt_data(self, data: bytes) -> bytes:
        cipher = Cipher(
            algorithms.AES(self.enc_key), modes.CBC(self.enc_iv), default_backend()
        )
        encrypted_data = cipher.encryptor().update(data)
        self.enc_iv = encrypted_data[-16:]
        return encrypted_data

    def _compute_cbc_mac(self, data: bytes) -> bytes:
        cipher = Cipher(
            algorithms.AES(self.mac_key), modes.CBC(self.mac_iv), default_backend()
        )
        encrypted_data = cipher.encryptor().update(data)
        self.mac_iv = encrypted_data[-BLOCK_SIZE:]
        return encrypted_data[-BLOCK_SIZE:]

    def _verify_cbc_mac(self, data: bytes, mac: bytes) -> bool:
        computed_mac = self._compute_cbc_mac(data)
        computed_mac = computed_mac[-len(mac) :]
        return constant_time.bytes_eq(computed_mac, mac)

    def wrap(self, data: bytes) -> bytes:
        padded_data = iso9797_pad(data)
        encrypted_data = self._encrypt_data(padded_data)
        mac_data = self._compute_cbc_mac(encrypted_data)
        encrypted_data += mac_data[
            -self.SCP_MAC_LENGTH :
        ]  # only append part of the mac
        return encrypted_data

    def unwrap(self, data: bytes) -> bytes:
        if len(data) == 0:
            return b""

        encrypted_data, mac = data[: -self.SCP_MAC_LENGTH], data[-self.SCP_MAC_LENGTH :]
        if not self._verify_cbc_mac(encrypted_data, mac):
            raise Exception("Invalid SCP MAC")
        data = self._decrypt_data(encrypted_data)
        return iso9797_unpad(data)
