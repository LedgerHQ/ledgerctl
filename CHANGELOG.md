# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.4] - 2023-03-02

### Fixed

- Script entry point was broken

## [0.2.3] - 2023-02-09

### Fixed

- Force protobuf dependency version to be in [3.20, 4[

## [0.2.2] - 2023-02-08

Artifical version bump in order to be able to deploy on test.pypi.org, as previous version number
were already submitted

## [0.2.0] - 2023-02-08

### Add

- TOML manifests can be used, on top of already valid JSON manifests

### Changed

- Packaging system is now managed with Flit, and moved from setup.py to pyproject.toml

## [0.1.4] - 2022-09-12

### Added

- 'onboard' new CLI command. This will automatically onboard a device, given it is reset and booted
  in recovery mode
- Abstract class 'Device' defines an interface to be implemented by 'HidDevice' and 'TcpDevice'
  classes

### Changed

- Some error management improvement
- Some code typing

## [0.1.3] - 2022-05-03

## [0.1.2] - 2019-11-25

## [0.1.1] - 2019-11-25

Initial release
