import hashlib

import ecdsa.ellipticcurve
import ecdsa.util
from ecdsa.curves import SECP256k1
from ecdsa.keys import SigningKey, VerifyingKey


class PublicKey(object):
    def __init__(self, pubkey: bytes):
        if len(pubkey) != 64 + 1 or pubkey[0] != 0x04:
            raise ValueError

        self.vk = VerifyingKey.from_string(pubkey[1:], SECP256k1, validate_point=True)

    def serialize(self, compressed=True):
        if compressed:
            raise NotImplementedError
        return b"\x04" + self.vk.to_string()

    def verify(
        self, msg: bytes, raw_sig: bytes, raw=False, hashfunc=hashlib.sha256
    ) -> bool:
        try:
            if not raw:
                return self.vk.verify(raw_sig, msg, hashfunc, ecdsa.util.sigdecode_der)
            else:
                return self.vk.verify_digest(raw_sig, msg, ecdsa.util.sigdecode_der)
        except ecdsa.keys.BadSignatureError:
            return False


class PrivateKey(object):
    def __init__(self, sk=None):
        if sk is None:
            self.sk = SigningKey.generate(SECP256k1)
        else:
            self.sk = SigningKey.from_string(sk, SECP256k1)

    @property
    def pubkey(self):
        return PublicKey(b"\x04" + self.sk.get_verifying_key().to_string())

    def serialize(self):
        return self.sk.to_string()

    def sign(self, msg, raw=False, hashfunc=hashlib.sha256):
        if not raw:
            signature = self.sk.sign(
                msg, hashfunc=hashfunc, sigencode=ecdsa.util.sigencode_der_canonize
            )
        else:
            signature = self.sk.sign_digest(
                msg, sigencode=ecdsa.util.sigencode_der_canonize
            )
        return signature

    def exchange(self, public_key: PublicKey) -> bytes:
        # ECDH as computed by libsecpk256k1
        point = self.sk.privkey.secret_multiplier * public_key.vk.pubkey.point
        if point.y() & 1 == 1:
            msg = b"\x03" + ecdsa.util.number_to_string(point.x(), SECP256k1.order)
        else:
            msg = b"\x02" + ecdsa.util.number_to_string(point.x(), SECP256k1.order)
        md = hashlib.sha256(msg)
        return md.digest()
