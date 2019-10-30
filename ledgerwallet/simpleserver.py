import os

from ledgerwallet.crypto.ecc import PrivateKey, PublicKey
from ledgerwallet.ledgerserver import LedgerServer
from ledgerwallet.utils import serialize, unserialize

CERT_ROLE_SIGNER = 1
CERT_ROLE_DEVICE = 2
CERT_ROLE_SIGNER_EPHEMERAL = 0x11
CERT_ROLE_DEVICE_EPHEMERAL = 0x12


class SimpleServer(LedgerServer):
    def __init__(self, master_private: PrivateKey, cert_chain=None):
        self.device_nonce = None
        self.server_nonce = None
        self.master_private = master_private
        self.master_public = master_private.pubkey.serialize(False)
        self.shared_secret = None
        self.ephemeral_private = None

        self.cert_chain = cert_chain

    def receive_certificate_chain(self):
        cert_chain = []
        if self.cert_chain is not None:
            cert_chain.append(self.cert_chain)
        else:
            data_to_sign = bytes([CERT_ROLE_SIGNER]) + self.master_public
            master_signature = self.master_private.sign(data_to_sign)
            cert_chain.append(
                serialize(self.master_public) + serialize(master_signature)
            )

        # Provide the ephemeral certificate, signed with the master public key
        self.ephemeral_private = PrivateKey()
        ephemeral_public = self.ephemeral_private.pubkey.serialize(compressed=False)
        # print("Using ephemeral key {}".format(ephemeral_public.hex()))

        data_to_sign = (
            bytes([CERT_ROLE_SIGNER_EPHEMERAL])
            + self.server_nonce
            + self.device_nonce
            + ephemeral_public
        )
        signature = self.master_private.sign(data_to_sign)
        cert_chain.append(serialize(ephemeral_public) + serialize(signature))

        return cert_chain

    def send_certicate_chain(self, chain):
        assert len(chain) == 2

        last_dev_pub_key = PublicKey(self.master_public)
        for i, item in enumerate(chain):
            certificate_header, item = unserialize(item)
            certificate_public_key, item = unserialize(item)
            certificate_signature_array, _ = unserialize(item)
            certificate_signature = certificate_signature_array

            # first cert contains a header field which holds the certificate's public key role
            if i == 0:
                # device_public_key = certificate_public_key
                certificate_signed_data = (
                    bytes([CERT_ROLE_DEVICE])
                    + certificate_header
                    + certificate_public_key
                )
            # Could check if the device certificate is signed by the issuer public key
            # ephemeral key certificate
            else:
                certificate_signed_data = (
                    bytes([CERT_ROLE_DEVICE_EPHEMERAL])
                    + self.device_nonce
                    + self.server_nonce
                    + certificate_public_key
                )

            if not last_dev_pub_key.verify(
                certificate_signed_data, certificate_signature
            ):
                """
                if index == 0:
                    # Not an error if loading from user key
                    print("Broken certificate chain - loading from user key")
                else:
                    raise Exception("Broken certificate chain")
                """
                if i != 0:
                    raise Exception("Broken certificate chain")

            last_dev_pub_key = PublicKey(certificate_public_key)
        self.shared_secret = self.ephemeral_private.exchange(last_dev_pub_key)

    def get_nonce(self) -> bytes:
        self.server_nonce = os.urandom(8)
        return self.server_nonce

    def send_nonce(self, nonce: bytes):
        assert len(nonce) == 8
        self.device_nonce = nonce

    def get_shared_secret(self):
        return self.shared_secret
