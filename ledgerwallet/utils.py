import logging


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


def get_device_name(target_id: int):
    target_ids = {
        0x31100002: "Ledger Nano S",  # firmware version <= 1.3.1
        0x31100003: "Ledger Nano S",  # firmware version > 1.3.1
        0x31100004: "Ledger Nano S",  # firmware version >= 1.5
        0x31000002: "Ledger Blue",  # firmware version <= 2.0
        0x31010004: "Ledger Blue",  # firmware version > 2.0
        0x33000004: "Ledger Nano X",
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
