import logging
from enum import Enum, IntEnum

from construct import (
    Bytes,
    Const,
    FlagsEnum,
    Hex,
    Int8ub,
    Int32ub,
    Int32ul,
    Optional,
    PascalString,
    Struct,
)


class DeviceNames(Enum):
    LEDGER_NANO_S = "Ledger Nano S"
    LEDGER_NANO_X = "Ledger Nano X"
    LEDGER_NANO_SP = "Ledger Nano S+"
    LEDGER_BLUE = "Ledger Blue"
    LEDGER_STAX = "Ledger Stax"
    LEDGER_FLEX = "Ledger Flex"
    LEDGER_APEX_P = "Ledger Apex P"
    LEDGER_APEX_M = "Ledger Apex M"


class LedgerIns(IntEnum):
    SECUINS = 0
    GET_VERSION = 1
    VALIDATE_TARGET_ID = 4
    INITIALIZE_AUTHENTICATION = 0x50
    VALIDATE_CERTIFICATE = 0x51
    GET_CERTIFICATE = 0x52
    MUTUAL_AUTHENTICATE = 0x53
    ONBOARD = 0xD0
    RUN_APP = 0xD8
    # Commands for custom endorsement
    ENDORSE_SET_START = 0xC0
    ENDORSE_SET_COMMIT = 0xC2


class LedgerSecureIns(IntEnum):
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


def enable_apdu_log():
    logger = logging.getLogger("ledgerwallet")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


def serialize(buffer: bytes):
    return bytes([len(buffer)]) + buffer


def unserialize(buffer: bytes):
    buffer_len = buffer[0]
    assert len(buffer) >= buffer_len + 1
    return buffer[1 : buffer_len + 1], buffer[buffer_len + 1 :]


def get_device_name(target_id: int) -> str:
    target_ids = {
        0x31100002: DeviceNames.LEDGER_NANO_S.value,  # firmware version <= 1.3.1
        0x31100003: DeviceNames.LEDGER_NANO_S.value,  # firmware version > 1.3.1
        0x31100004: DeviceNames.LEDGER_NANO_S.value,  # firmware version >= 1.5
        0x31000002: DeviceNames.LEDGER_BLUE.value,  # firmware version <= 2.0
        0x31010004: DeviceNames.LEDGER_BLUE.value,  # firmware version > 2.0
        0x33000004: DeviceNames.LEDGER_NANO_X.value,
        0x33100004: DeviceNames.LEDGER_NANO_SP.value,
        0x33200004: DeviceNames.LEDGER_STAX.value,
        0x33300004: DeviceNames.LEDGER_FLEX.value,
        0x33400004: DeviceNames.LEDGER_APEX_P.value,
        0x33500004: DeviceNames.LEDGER_APEX_M.value,
    }
    return target_ids.get(target_id, "Unknown device")


def decode_flags(flags: int):
    flag_values = {
        1: "issuer",
        2: "bolos_upgrade",
        4: "signed",
        8: "bolos_ux",
        16: "derive_master",
        64: "global_pin",
        128: "debug",
        256: "autoboot",
        512: "bolos_settings",
        1024: "custom_ca",
        2048: "library",
        4096: "no_run",
        # "enabled" is always set. no need to display it
        # 32768: "enabled"
    }
    enabled_flags = []
    for f in flag_values:
        if flags & f == f:
            enabled_flags.append(flag_values[f])
    return enabled_flags


def flags_to_string(flags: int):
    return ",".join(decode_flags(flags))
