# Roadmap: fastshare

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-02-25)
- 🚧 **v1.1 Publication & Polish** — Phases 6-9 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-5) — SHIPPED 2026-02-25</summary>

- [x] Phase 1: Foundation & Platform (2/2 plans) — completed 2026-02-24
- [x] Phase 2: Core Read/Write Engine (3/3 plans) — completed 2026-02-25
- [x] Phase 3: SharedData Broadcast (2/2 plans) — completed 2026-02-25
- [x] Phase 4: Cleanup Tools (2/2 plans) — completed 2026-02-25
- [x] Phase 5: Integration Tests & CI (3/3 plans) — completed 2026-02-25

See: `.planning/milestones/v1.0-ROADMAP.md` for full details.

</details>

### v1.1 Publication & Polish

**Phase Numbering:**
- Integer phases (6, 7, 8, 9): Planned milestone work
- Decimal phases (7.1, 7.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 6: Documentation** - Comprehensive README with examples, API reference, benchmarks, and badges (gap closure pending)
- [x] **Phase 7: Packaging** - pyproject.toml polish, CHANGELOG, and version tag
- [x] **Phase 8: Repository** - GitHub repo creation and full history push
- [ ] **Phase 9: Distribution** - Build, TestPyPI validation, PyPI publication, and trusted publisher

## Phase Details

### Phase 6: Documentation
**Goal**: Users can understand what fastshare does, how to install and use it, and how it compares to alternatives -- all from the README
**Depends on**: Nothing (can start immediately; uses existing v1.0 codebase as source)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06, DOCS-07, DOCS-08, DOCS-09
**Success Criteria** (what must be TRUE):
  1. A developer reading the README understands what fastshare does and why it exists within the first paragraph
  2. A developer can follow installation instructions to install fastshare with and without NumPy
  3. A developer can copy the quick start example, run it, and see zero-copy transfer working across processes
  4. A developer can find every public function and class documented with signatures and descriptions in the API reference
  5. The README displays badges for PyPI version, supported Python versions, license, and CI status
**Plans**: 3 plans

Plans:
- [x] 06-01-PLAN.md -- README hero content (badges, intro, install, examples, benchmarks)
- [x] 06-02-PLAN.md -- README reference content (API reference, architecture, platform matrix)
- [x] 06-03-PLAN.md -- Gap closure: export CleanupResult as public API symbol

### Phase 7: Packaging
**Goal**: The project has complete, accurate PyPI metadata and a tagged release ready for building
**Depends on**: Nothing (can run in parallel with Phase 6)
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04, PKG-05
**Success Criteria** (what must be TRUE):
  1. pyproject.toml contains Homepage, Source, and Issues URLs pointing to the GitHub repository
  2. pyproject.toml lists correct author/maintainer metadata and Development Status classifier is Beta
  3. CHANGELOG.md documents all v1.0.0 features, and the file exists at the repo root
  4. Git tag v1.0.0 exists and hatch-vcs resolves the version string correctly
**Plans**: 2 plans

Plans:
- [x] 07-01-PLAN.md -- PyPI metadata polish (URLs, author, classifiers, keywords) and CHANGELOG.md creation
- [x] 07-02-PLAN.md -- Annotated git tag v1.0.0 for hatch-vcs versioning

### Phase 8: Repository
**Goal**: The fastshare project is publicly available on GitHub with full commit history
**Depends on**: Phase 7 (tag must exist before push so GitHub shows the release tag)
**Requirements**: REPO-01, REPO-02
**Success Criteria** (what must be TRUE):
  1. The GitHub repository "fastshare" exists and is publicly accessible
  2. All commits, branches, and tags (including v1.0.0) are visible on GitHub
  3. The README renders correctly on the GitHub repository page
**Plans**: 2 plans

Plans:
- [x] 08-01-PLAN.md -- GitHub repo creation, gitignore update, and full history push
- [x] 08-02-PLAN.md -- Gap closure: fix README badge URLs (owner/fastshare -> AwaisAdilKhokhar/fastshare)

### Phase 08.1: PyArrow Zero-Copy Support (INSERTED)

**Goal:** fastshare supports zero-copy shared memory transfer for PyArrow objects (Table, RecordBatch, Array, ChunkedArray) with transparent pandas DataFrame auto-conversion
**Requirements**: TYPE-01
**Depends on:** Phase 8
**Success Criteria** (what must be TRUE):
  1. `write(pa.table(...))` serializes via Arrow IPC into shared memory and `read()` returns the same Table type
  2. All four Arrow types (Table, RecordBatch, Array, ChunkedArray) round-trip through write/read with type preservation
  3. `write(pandas_dataframe)` auto-converts to Arrow Table when pyarrow is installed; read returns Arrow Table
  4. `SharedData(arrow_table)` works with context manager and SharedData.load() returns cached Arrow object
  5. `pip install fastshare[arrow]` installs pyarrow as optional dependency
  6. Small Arrow objects (below threshold) use pickle fallback; the 1MB threshold is consistent
**Plans**: 2 plans

Plans:
- [x] 08.1-01-PLAN.md -- Arrow IPC engine: _arrow_utils.py, _estimator.py Arrow path, _serializer.py Arrow IPC, pyproject.toml [arrow] extra
- [ ] 08.1-02-PLAN.md -- API integration: write/read Arrow detection, SharedData Arrow support, pandas auto-convert, test suite

### Phase 9: Distribution
**Goal**: fastshare is installable from PyPI and future releases can be published via GitHub Actions
**Depends on**: Phase 7 (correct metadata for build), Phase 8 (remote URLs must resolve)
**Requirements**: DIST-01, DIST-02, DIST-03, DIST-04
**Success Criteria** (what must be TRUE):
  1. `python -m build` produces both sdist and wheel artifacts without errors
  2. The package is installable from TestPyPI (`pip install -i https://test.pypi.org/simple/ fastshare`) and imports correctly
  3. The package is installable from PyPI (`pip install fastshare`) and `fastshare --version` shows v1.0.0
  4. GitHub Actions trusted publisher is configured so future releases can publish via OIDC without API tokens
**Plans**: 2 plans

Plans:
- [ ] 09-01-PLAN.md -- Fix orphaned tag, add --version CLI flag, build and validate distribution artifacts
- [ ] 09-02-PLAN.md -- Publish to TestPyPI/PyPI, create publish workflow, configure trusted publisher

## Progress

**Execution Order:**
Phases execute in numeric order: 6 -> 7 -> 8 -> 9
(Phases 6 and 7 may execute in parallel since they are independent.)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Platform | v1.0 | 2/2 | Complete | 2026-02-24 |
| 2. Core Read/Write Engine | v1.0 | 3/3 | Complete | 2026-02-25 |
| 3. SharedData Broadcast | v1.0 | 2/2 | Complete | 2026-02-25 |
| 4. Cleanup Tools | v1.0 | 2/2 | Complete | 2026-02-25 |
| 5. Integration Tests & CI | v1.0 | 3/3 | Complete | 2026-02-25 |
| 6. Documentation | v1.1 | 3/3 | Complete | 2026-02-26 |
| 7. Packaging | v1.1 | 2/2 | Complete | 2026-02-26 |
| 8. Repository | v1.1 | 2/2 | Complete | 2026-02-26 |
| 8.1 PyArrow Support | v1.1 | 1/2 | In Progress | - |
| 9. Distribution | v1.1 | 0/2 | Not started | - |
