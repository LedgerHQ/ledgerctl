import requests

from ledgerwallet.hsmscript import HsmScript
from ledgerwallet.ledgerserver import LedgerServer
from ledgerwallet.proto.LedgerHSMServer_pb2 import Request, Response
from ledgerwallet.utils import serialize


class HsmServer(LedgerServer):
    def __init__(
        self, script: HsmScript, url="https://hsmprod.hardwarewallet.com/hsm/process"
    ):
        self.url = url
        self.script = script

        self.device_nonce = None
        self.server_nonce = None

        self.public_key = None
        self.last_request_id = None
        self.session = requests.Session()

    @staticmethod
    def _query_add_param(request: Request, alias: str, name: str, local: bool = False):
        param = request.remote_parameters.add()
        param.alias = alias
        param.name = name
        param.local = local

    def query(self, data=None, params=None) -> bytes:
        request = Request(
            reference=self.script.name, largeStack=self.script.use_large_stack
        )
        if self.last_request_id is not None:
            request.id = self.last_request_id

        if params:
            for param, value in params.items():
                self._query_add_param(request, param, value)
        elif self.script.default_params:
            for alias, name in self.script.default_params.items():
                self._query_add_param(request, alias, name)

        if data is not None:
            request.parameters = data

        req = self.session.post(self.url, request.SerializeToString())
        response = Response()
        # TODO: handle errors
        response.ParseFromString(req.content)

        self.last_request_id = response.id
        if len(response.exception) != 0:
            raise Exception(f"HSM Error: {response.exception}")
        return response.response

    def send_nonce(self, nonce: bytes):
        assert len(nonce) == 8
        self.device_nonce = nonce

    def get_nonce(self) -> bytes:
        response = self.query()
        self.public_key, self.server_nonce = response[:65], response[65 : 65 + 8]

        return self.server_nonce

    def receive_certificate_chain(self):
        # Get signed public key
        response = self.query(self.device_nonce)
        server_signature = response
        public_key = self.public_key
        return [serialize(public_key) + serialize(server_signature)]

    def send_certicate_chain(self, chain):
        for certificate in chain:
            self.query(certificate)
