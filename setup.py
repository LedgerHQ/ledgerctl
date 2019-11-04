from setuptools import find_packages, setup

from os import path

this_dir = path.abspath(path.dirname(__file__))
with open(path.join(this_dir, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ledgerwallet",
    python_requires=">=3.5",
    version="0.1.0",
    license="MIT",
    description="Python client and library to communicate with Ledger devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
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
