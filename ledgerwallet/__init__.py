"""Python client and library to communicate with Ledger devices."""

try:
    from ledgerwalet.__version__ import __version__  # noqa
except ImportError:
    __version__ = "unknown version"  # noqa
