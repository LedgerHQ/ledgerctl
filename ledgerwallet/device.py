from .client import LedgerClient
from . import utils


def genuine_check(client: LedgerClient):
    custom_ui = False
    custom_ca = False
    genuine = False

    try:
        for app in client.apps:
            if 'bolos_ux' in utils.decode_flags(app.flags):
                custom_ui = True
            if 'custom_ca' in utils.decode_flags(app.flags):
                custom_ca = True
        genuine = True
    except Exception:
        pass

    if not genuine:
        print("Product is NOT genuine")
    else:
        if not custom_ui and not custom_ca:
            print("Product is genuine")
        else:
            if custom_ca:
                print("WARNING: Product is genuine but has a Custom CA loaded")
            if custom_ui:
                print("WARNING: Product is genuine but has a UI application loaded")
    info = client.get_version_info_secure()
    print("SE Version: {}".format(info.se_version))
    print("MCU Version: {}".format(info.mcu_version))
    print("MCU Hash: {}".format(info.mcu_hash.hex()))
