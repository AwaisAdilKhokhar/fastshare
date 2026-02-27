# Requirements: fastshare

**Defined:** 2026-02-25
**Core Value:** Zero-copy shared memory transfer of large Python objects with a clean, polished public API

## v1.1 Requirements

Requirements for publication and open-source readiness. Each maps to roadmap phases.

### Documentation

- [x] **DOCS-01**: README has project description explaining what fastshare does and why
- [x] **DOCS-02**: README has installation instructions (pip install, optional numpy extra)
- [x] **DOCS-03**: README has quick start example showing write() and read() across processes
- [x] **DOCS-04**: README has SharedData broadcast example with worker pool
- [x] **DOCS-05**: README has API reference section covering all public functions/classes
- [x] **DOCS-06**: README has benchmark comparison vs standard pickle (with numbers)
- [x] **DOCS-07**: README has platform/Python version support matrix
- [x] **DOCS-08**: README has architecture section explaining pickle5 + shared memory approach
- [x] **DOCS-09**: README has badges (PyPI version, Python versions, license, CI status)

### Packaging

- [x] **PKG-01**: pyproject.toml has project.urls (Homepage, Source, Issues)
- [x] **PKG-02**: pyproject.toml classifier updated from Alpha to Beta
- [x] **PKG-03**: pyproject.toml has author/maintainer metadata
- [x] **PKG-04**: CHANGELOG.md documents v1.0.0 release
- [x] **PKG-05**: Git tag v1.0.0 created for hatch-vcs versioning

### Repository

- [x] **REPO-01**: GitHub repo "fastshare" created
- [x] **REPO-02**: All code and history pushed to GitHub remote

### Distribution

- [x] **DIST-01**: Package builds successfully (sdist + wheel)
- [x] **DIST-02**: Package published to TestPyPI and installable
- [x] **DIST-03**: Package published to PyPI
- [x] **DIST-04**: GitHub Actions trusted publisher configured for future releases

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Extended Type Support

- [x] **TYPE-01**: PyArrow table/RecordBatch zero-copy transfer
- **TYPE-02**: Pandas DataFrame zero-copy transfer
- **TYPE-03**: Multi-block >2GB object handling

### High-Level APIs

- **API-01**: SharedQueue drop-in replacement for multiprocessing.Queue
- **API-02**: SharedPool drop-in replacement for multiprocessing.Pool

### Serialization

- **SER-01**: Pydantic model hybrid serialization
- **SER-02**: Dataclass hybrid serialization

## Out of Scope

| Feature | Reason |
|---------|--------|
| Docs site (Sphinx/MkDocs) | Overkill for library this size; README is sufficient |
| CONTRIBUTING.md | Deferred; README covers basics |
| Issue/PR templates | Can add later when community forms |
| Automated release workflow | Trusted publisher covers the OIDC; full automation is future |
| Distributed/multi-machine IPC | Different domain (use Ray/Dask) |
| GPU memory sharing | Different domain (use cupy/torch) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOCS-01 | Phase 6 | Complete |
| DOCS-02 | Phase 6 | Complete |
| DOCS-03 | Phase 6 | Complete |
| DOCS-04 | Phase 6 | Complete |
| DOCS-05 | Phase 6 | Complete |
| DOCS-06 | Phase 6 | Complete |
| DOCS-07 | Phase 6 | Complete |
| DOCS-08 | Phase 6 | Complete |
| DOCS-09 | Phase 6 | Complete |
| PKG-01 | Phase 7 | Complete |
| PKG-02 | Phase 7 | Complete |
| PKG-03 | Phase 7 | Complete |
| PKG-04 | Phase 7 | Complete |
| PKG-05 | Phase 7 | Complete |
| REPO-01 | Phase 8 | Complete |
| REPO-02 | Phase 8 | Complete |
| DIST-01 | Phase 9 | Complete |
| DIST-02 | Phase 9 | Complete |
| DIST-03 | Phase 9 | Complete |
| DIST-04 | Phase 9 | Complete |
| TYPE-01 | Phase 08.1 | Complete |

**Coverage:**
- v1.1 requirements: 21 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-02-25*
*Last updated: 2026-02-26 after 07-01 execution*
