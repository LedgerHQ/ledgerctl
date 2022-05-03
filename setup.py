from setuptools import find_packages, setup

from os import path

this_dir = path.abspath(path.dirname(__file__))
with open(path.join(this_dir, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ledgerwallet",
    version="0.1.3",
    url="https://github.com/LedgerHQ/ledgerctl/",
    python_requires=">=3.6",
    license="MIT",
    description="Python client and library to communicate with Ledger devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "click>=7.0",
        "construct>=2.10",
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
    entry_points={"console_scripts": "ledgerctl = ledgerctl:cli"},
    py_modules=["ledgerctl"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
    ],
)
