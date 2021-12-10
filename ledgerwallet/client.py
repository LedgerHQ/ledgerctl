import enum
import logging
import struct
from typing import Union

from construct import (
    Bytes,
    Const,
    FlagsEnum,
    GreedyRange,
    Hex,
    Int8ub,
    Int32ub,
    Int32ul,
    Optional,
    PascalString,
    Rebuild,
    Struct,
    len_,
    this,
)
from intelhex import IntelHex

from ledgerwallet.crypto.ecc import PrivateKey
from ledgerwallet.crypto.scp import SCP
from ledgerwallet.hsmscript import HsmScript
from ledgerwallet.hsmserver import HsmServer
from ledgerwallet.ledgerserver import LedgerServer
from ledgerwallet.manifest import AppManifest
from ledgerwallet.proto.listApps_pb2 import AppList
from ledgerwallet.simpleserver import SimpleServer
from ledgerwallet.transport import enumerate_devices
from ledgerwallet.utils import serialize


class LedgerIns(enum.IntEnum):
    SECUINS = 0
    GET_VERSION = 1
    VALIDATE_TARGET_ID = 4
    INITIALIZE_AUTHENTICATION = 0x50
    VALIDATE_CERTIFICATE = 0x51
    GET_CERTIFICATE = 0x52
    MUTUAL_AUTHENTICATE = 0x53
    RUN_APP = 0xD8
    # Commands for custom endorsement
    ENDORSE_SET_START = 0xC0
    ENDORSE_SET_COMMIT = 0xC2


class LedgerSecureIns(enum.IntEnum):
    SET_LOAD_OFFSET = 5
    LOAD = 6
    FLUSH = 7
    CRC = 8
    COMMIT = 9
    CREATE_APP = 11
    DELETE_APP = 12
    LIST_APPS = 14
    LIST_APPS_CONTINUE = 15
    GET_VERSION = 16
    GET_MEMORY_INFORMATION = 17
    SETUP_CUSTOM_CERTIFICATE = 18
    RESET_CUSTOM_CERTIFICATE = 19
    DELETE_APP_BY_HASH = 21
    MCU_BOOTLOADER = 0xB0


LOAD_SEGMENT_CHUNK_HEADER_LENGTH = 3
MIN_PADDING_LENGTH = 1
SCP_MAC_LENGTH = 0xE

MAX_CHUNK_SIZE = (
    0x10000  # Maximum size of a chunk that can be loaded at once during app install
)

LEDGER_HSM_URL = "https://hsmprod.hardwarewallet.com/hsm/process"
LEDGER_HSM_KEY = "perso_11"


ApduListAppsResponse = Struct(
    Const(b"\x01"),  # Version
    apps=GreedyRange(
        Struct(
            # Application
            # Prefixed by the size of the structure, size included.
            _size=Rebuild(Int8ub, 1 + 4 + 32 + 32 + len_(this.name)),
            flags=Hex(Int32ub),
            code_data_hash=Bytes(32),
            full_hash=Bytes(32),
            name=PascalString(Int8ub, "utf-8"),
        )
    ),
)

VersionInfo = Struct(
    target_id=Hex(Int32ub),
    se_version=PascalString(Int8ub, "utf-8"),
    _flags_len=Const(b"\x04"),
    flags=FlagsEnum(
        Int32ul,
        recovery_mode=1,
        signed_mcu=2,
        is_onboarded=4,
        trust_issuer=8,
        trust_custom_ca=16,
        hsm_initialized=32,
        pin_validated=128,
    ),
    mcu_version=PascalString(Int8ub, "utf-8"),
    mcu_hash=Optional(Bytes(32)),
)


class AppInfo(object):
    def __init__(
        self,
        name: str,
        flags: int,
        code_data_hash: bytes,
        full_hash: bytes,
        data: bytes = None,
    ):
        self.name = name
        self.flags = flags
        self.code_data_hash = code_data_hash
        self.full_hash = full_hash
        self.data = data


class MemoryInfo:
    def __init__(
        self,
        system_size: int,
        applications_size: int,
        free_size: int,
        used_app_slots: int,
        num_app_slots: int,
    ):
        self.system_size = system_size
        self.applications_size = applications_size
        self.free_size = free_size
        self.used_app_slots = used_app_slots
        self.num_app_slots = num_app_slots


class CommException(Exception):
    def __init__(self, message, sw=0x6F00, data=None):
        self.message = message
        self.sw = sw
        self.data = data

    def __str__(self):
        buf = "Exception : " + self.message
        return buf


class NoLedgerDeviceException(Exception):
    pass


LOG = logging.getLogger("ledgerwallet")


class LedgerClient(object):
    def __init__(self, device=None, cla=0xE0, private_key=None):
        if device is None:
            devices = enumerate_devices()
            if len(devices) == 0:
                raise NoLedgerDeviceException("No Ledger device has been found.")
            device = devices[0]
        self.device = device
        self.cla = cla
        self._target_id = None
        self.scp = None
        if private_key is None:
            self.private_key = PrivateKey()
        else:
            self.private_key = PrivateKey(private_key)
        self.device.open()

    def close(self):
        self.device.close()

    def raw_exchange(self, data: bytes) -> bytes:
        LOG.debug("=> " + data.hex())
        output_data = bytes(self.device.exchange(data))
        if len(output_data) > 0:
            LOG.debug("<= " + output_data.hex())
        return output_data

    def apdu_exchange(self, ins, data=b"", p1=0, p2=0):
        apdu = bytes([self.cla, ins, p1, p2])
        apdu += serialize(data)
        response = self.raw_exchange(apdu)

        status_word = int.from_bytes(response[-2:], "big")
        if status_word != 0x9000 and ((status_word >> 8) != 0x61):
            possible_cause = "Unknown reason"
            if status_word == 0x6982:
                possible_cause = (
                    "Have you uninstalled the existing CA with resetCustomCA first?"
                )
            elif status_word == 0x6985:
                possible_cause = "Condition of use not satisfied (denied by the user?)"
            elif status_word == 0x6A84 or status_word == 0x6A85:
                possible_cause = "Not enough space?"
            elif status_word == 0x6A83:
                possible_cause = (
                    "Maybe this app requires a library to be installed first?"
                )
            elif status_word == 0x6484:
                possible_cause = "Are you using the correct targetId?"
            elif status_word == 0x69D5:
                possible_cause = "Cannot create custom secure channels on this device"
            raise CommException(
                "Invalid status %04x (%s)" % (status_word, possible_cause),
                status_word,
                data,
            )

        return response[:-2]

    def apdu_secure_exchange(self, ins, data=b"", p1=0, p2=0):
        if self.scp is None:
            server = SimpleServer(self.private_key)
            secret = self.authenticate(server)
            self.scp = SCP(secret)

        data = self.apdu_exchange(
            LedgerIns.SECUINS, self.scp.wrap(bytes([ins]) + data), p1, p2
        )
        return self.scp.unwrap(data)

    def authenticate(self, server: LedgerServer):
        self.reset()
        if self.target_id & 0xF < 2:
            raise Exception("Target ID does not support SCP V2")

        # Exchange nonce
        server_nonce = server.get_nonce()
        data = self.apdu_exchange(LedgerIns.INITIALIZE_AUTHENTICATION, server_nonce)
        device_nonce = data[4:12]
        server.send_nonce(device_nonce)

        # Get server certificate chain
        server_chain = server.receive_certificate_chain()
        for i in range(len(server_chain)):
            if i == len(server_chain) - 1:
                self.apdu_exchange(
                    LedgerIns.VALIDATE_CERTIFICATE, server_chain[i], p1=0x80
                )
            else:
                self.apdu_exchange(LedgerIns.VALIDATE_CERTIFICATE, server_chain[i])

        # Walk the client chain
        client_chain = []
        for i in range(2):
            if i == 0:
                certificate = self.apdu_exchange(LedgerIns.GET_CERTIFICATE)
            else:
                certificate = self.apdu_exchange(LedgerIns.GET_CERTIFICATE, p1=0x80)
            if len(certificate) == 0:
                break
            client_chain.append(certificate)
        server.send_certicate_chain(client_chain)

        # Mutual authentication done, retrieve shared secret
        self.apdu_exchange(LedgerIns.MUTUAL_AUTHENTICATE)
        return server.get_shared_secret()

    def _load_chunk(self, hex_file: IntelHex, segment, offset: int):
        start_addr, end_addr = segment
        segment_load_address = start_addr - hex_file.minaddr()

        self.apdu_secure_exchange(
            LedgerSecureIns.SET_LOAD_OFFSET,
            struct.pack(">I", segment_load_address + offset),
        )

        load_size = min(end_addr - start_addr - offset, MAX_CHUNK_SIZE)
        # max_load_size = 0xf0 - LOAD_SEGMENT_CHUNK_HEADER_LENGTH - MIN_PADDING_LENGTH - SCP_MAC_LENGTH
        max_load_size = 0x80

        load_address = start_addr + offset
        chunk_offset = start_addr
        while load_size > 0:
            chunk_size = min(load_size, max_load_size)
            data = hex_file.gets(load_address, chunk_size)
            data = struct.pack(">H", chunk_offset - start_addr) + data

            self.apdu_secure_exchange(LedgerSecureIns.LOAD, data)
            load_address += chunk_size
            chunk_offset += chunk_size
            load_size -= chunk_size

    def _load_segment(self, hex_file: IntelHex, segment):
        start_addr, end_addr = segment
        # Load each segment by chunks of 64kB
        for offset in range(0, end_addr - start_addr, MAX_CHUNK_SIZE):
            self._load_chunk(hex_file, segment, offset)

    def install_app(self, app_manifest: AppManifest):
        hex_file = IntelHex(app_manifest.get_binary())
        code_length = hex_file.maxaddr() - hex_file.minaddr() + 1
        data_length = app_manifest.data_size

        code_length -= data_length
        assert code_length % 64 == 0  # code length must be aligned

        flags = app_manifest.get_application_flags()  # not handled yet

        params = app_manifest.serialize_parameters()
        main_address = hex_file.start_addr["EIP"] - hex_file.minaddr()

        data = struct.pack(
            ">IIIII", code_length, data_length, len(params), flags, main_address
        )
        self.apdu_secure_exchange(LedgerSecureIns.CREATE_APP, data)

        hex_file.puts(hex_file.maxaddr() + 1, params)
        for segment in hex_file.segments():
            self._load_segment(hex_file, segment)
        self.apdu_secure_exchange(LedgerSecureIns.COMMIT)

    def delete_app(self, app: Union[str, bytes]):
        if isinstance(app, str):
            self.apdu_secure_exchange(
                LedgerSecureIns.DELETE_APP, serialize(app.encode())
            )
        elif isinstance(app, bytes) and len(app) == 32:
            self.apdu_secure_exchange(LedgerSecureIns.DELETE_APP_BY_HASH, app)
        else:
            raise TypeError("app parameter must be string or digest")

    def install_remote_app(
        self, app_path, key_path, url=LEDGER_HSM_URL, key=LEDGER_HSM_KEY
    ):
        script = HsmScript("distributeFirmware11", {"persoKey": key, "scpv2": "dummy"})
        server = HsmServer(script, url)
        self.authenticate(server)

        application_data = server.query(
            params={"firmware": app_path, "firmwareKey": key_path, "scpv2": "dummy"}
        )
        offset = 0
        while offset < len(application_data):
            apdu_len = application_data[offset + 4]
            self.raw_exchange(application_data[offset : offset + 5 + apdu_len])
            offset += 5 + apdu_len

    def delete_remote_app(
        self, app_path, key_path, url=LEDGER_HSM_URL, key=LEDGER_HSM_KEY
    ):
        return self.install_remote_app(app_path, key_path, url, key)

    def upgrade_firmware(
        self, firmware_name, firmware_key, url=LEDGER_HSM_URL, key=LEDGER_HSM_KEY
    ):
        script = HsmScript(
            "distributeFirmware11_scan", {"persoKey": key, "scpv2": "dummy"}
        )
        server = HsmServer(script, url)
        self.authenticate(server)

        response = b""
        while True:
            app_data = server.query(
                data=None if len(response) < 2 else b"\xff\xff" + response[:-2]
            )
            if len(app_data) == 0:
                break
            response = self.raw_exchange(app_data)

        application_data = server.query(
            params={"firmware": firmware_name, "firmwareKey": firmware_key}
        )
        offset = 0
        while offset < len(application_data):
            apdu_len = application_data[offset + 4]
            self.raw_exchange(application_data[offset : offset + 5 + apdu_len])
            offset += 5 + apdu_len

    def genuine_check(self, url=LEDGER_HSM_URL, key=LEDGER_HSM_KEY):
        script = HsmScript("checkGenuine", {"persoKey": key, "scpv2": "dummy"})
        server = HsmServer(script, url)
        self.authenticate(server)

        client_data = b""
        while True:
            application_data = server.query(client_data[:-2])  # No not send status word
            if len(application_data) < 5:
                break
            client_data = self.raw_exchange(application_data)
        # custom_ui = client_data[0]
        # custom_ca = client_data[1]
        return True

    def endorse(self, key_id: int, url=LEDGER_HSM_URL, key=LEDGER_HSM_KEY):
        script = HsmScript("signEndorsement", {"persoKey": key})
        server = HsmServer(script, url)
        self.authenticate(server)
        server.query()  # Commit agreement

        data = self.apdu_exchange(LedgerIns.ENDORSE_SET_START, p1=key_id)
        certificate = server.query(data, params={"endorsementKey": "attest_1"})

        # Commit endorsement certificate
        self.apdu_exchange(LedgerIns.ENDORSE_SET_COMMIT, certificate)
        return True

    def install_ca(self, name: str, public_key: bytes):
        data = serialize(name.encode()) + serialize(public_key)
        self.apdu_secure_exchange(LedgerSecureIns.SETUP_CUSTOM_CERTIFICATE, data)

    def delete_ca(self):
        return self.apdu_secure_exchange(LedgerSecureIns.RESET_CUSTOM_CERTIFICATE)

    def get_version_info(self):
        data = self.apdu_exchange(LedgerIns.GET_VERSION)
        version_info = VersionInfo.parse(data)
        self._target_id = version_info.target_id
        return version_info

    def get_version_info_secure(self):
        data = self.apdu_secure_exchange(LedgerSecureIns.GET_VERSION)
        version_info = VersionInfo.parse(data)
        self._target_id = version_info.target_id
        return version_info

    def validate_target_id(self, target_id: int):
        self.apdu_exchange(LedgerIns.VALIDATE_TARGET_ID, struct.pack(">I", target_id))

    def reset(self):
        return self.validate_target_id(self.target_id)

    def get_memory_info(self) -> MemoryInfo:
        response = self.apdu_secure_exchange(LedgerSecureIns.GET_MEMORY_INFORMATION)
        assert len(response) == 20

        return MemoryInfo(*struct.unpack(">IIIII", response))

    @property
    def target_id(self):
        if self._target_id is None:
            self.get_version_info()
        return self._target_id

    def list_apps_remote(self, url=LEDGER_HSM_URL, key=LEDGER_HSM_KEY):
        script = HsmScript("listApps", {"persoKey": key, "scpv2": "dummy"})
        server = HsmServer(script, url)
        self.authenticate(server)

        application_data = server.query(params={"scpv2": "dummy"})
        while True:
            if len(application_data) == 0:
                break
            client_data = self.raw_exchange(application_data)
            application_data = server.query(client_data[:-2], params={"scpv2": "dummy"})
        application_data = server.query(params={"scpv2": "dummy"})

        apps = AppList()
        apps.ParseFromString(application_data)
        for app in apps.list:
            yield AppInfo(app.name, app.flags & 0xFFFF, app.hashCodeData, app.hash)

    @property
    def apps(self):
        data = self.apdu_secure_exchange(LedgerSecureIns.LIST_APPS)
        while len(data) != 0:
            response = ApduListAppsResponse.parse(data)
            for app in response.apps:
                yield AppInfo(
                    app.name, app.flags & 0xFFFF, app.code_data_hash, app.full_hash
                )
            data = self.apdu_secure_exchange(LedgerSecureIns.LIST_APPS_CONTINUE)

    def run_app(self, app_name: str):
        return self.apdu_exchange(LedgerIns.RUN_APP, app_name.encode())
