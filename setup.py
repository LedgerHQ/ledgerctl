import codecs
from os import path

from setuptools import find_packages, setup


def read(rel_path):
    here = path.abspath(path.dirname(__file__))
    with codecs.open(path.join(here, rel_path), "r") as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith("__version__"):
            delimiter = '"' if '"' in line else "'"
            return line.split(delimiter)[1]
    raise RuntimeError("Unable to find version string.")


this_dir = path.abspath(path.dirname(__file__))
with open(path.join(this_dir, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ledgerwallet",
    version=get_version("ledgerwallet/__init__.py"),
    url="https://github.com/LedgerHQ/ledgerctl/",
    python_requires=">=3.7",
    license="MIT",
    description="Python client and library to communicate with Ledger devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "click>=8.0",
        "construct>=2.10",
        "cryptography>=2.5",
        "ecdsa",
        "hidapi",
        "intelhex",
        "Pillow",
        "protobuf>=3.20",
        "requests",
        "tabulate",
    ],
    packages=find_packages(),
    include_package_data=True,
    entry_points={"console_scripts": "ledgerctl = ledgerctl:cli"},
    py_modules=["ledgerctl"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
    ],
)
