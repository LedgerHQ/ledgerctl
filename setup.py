from setuptools import find_packages, setup

setup(
    name="ledgerctl",
    python_requires=">=3.5",
    version="0.1",
    py_modules=["ledgerctl"],
    description="Ledger Donjon Python3 client to communicate with Ledger devices",
    install_requires=[
        "click>=7.0",
        "construct>=2.9",
        "cryptography>=2.5",
        "ecdsa",
        "hidapi",
        "intelhex",
        "protobuf>=3.6",
        "Pillow",
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
