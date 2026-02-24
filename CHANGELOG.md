# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-02-25

### Added

- Zero-copy shared memory transfer of large Python objects between processes using pickle protocol 5
- `write()` and `read()` functions for serializing/deserializing objects via shared memory tokens
- `SharedData` context manager for write-once, read-many broadcast pattern with per-process caching
- `cleanup()` function and CLI command (`fastshare cleanup`) for orphaned shared memory recovery
- NumPy ndarray zero-copy support with automatic contiguity handling and readonly enforcement
- Automatic size-based routing: small objects use pickle+base64 tokens, large objects use shared memory
- Cross-platform support for Windows, macOS, and Linux (Python 3.10-3.13)
- Exception hierarchy: `FastShareError`, `AllocationError`, `BlockNotFoundError`

[Unreleased]: https://github.com/AwaisAdilKhokhar/fastshare/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/AwaisAdilKhokhar/fastshare/compare/v0.0.0...v1.0.0
