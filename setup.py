from setuptools import find_packages, setup

setup(
    name="ledgerwallet",
    python_requires=">=3.5",
    version="0.1",
    license="MIT",
    description="Ledger Donjon Python3 client to communicate with Ledger devices",
    install_requires=[
        "click>=7.0",
        "construct>=2.9",
        "cryptography>=2.5",
        "ecdsa",
        "hidapi",
        "intelhex",
        "Pillow",
        "protobuf>=3.6",
        "requests",
        "tabulate",
    ],
    packages=find_packages(),
    include_package_data=True,
    entry_points="""
        [console_scripts]
        ledgerctl=ledgerctl:cli
    """,
)
