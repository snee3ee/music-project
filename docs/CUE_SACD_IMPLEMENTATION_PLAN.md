# Result clarity, CUE and SACD sources — 2026-11-10

Starting point: 0.2.4.dev0, HEAD e14e46a; existing uncommitted Conclusions Engine
changes and probe files preserved. Baseline executed: 319 passed / 1 SACD skip,
124.63 seconds, including explicitly supplied Pink Panther DSF.

- [x] Inspect instructions, skills, methodology, core/decoder/UI/tests and backends.
- [x] Typed logical sources and bounded CUE parser/resolver with explicit diagnostics,
  authorized references, exact frame boundaries and source fingerprints.
- [x] Selected-track PCM/native DSD analysis, explicit time mapping and coverage;
  no source integrity claim based only on a temporary track representation.
- [x] SACD backend capability discovery, bounded validated enumeration and safe
  selected-track extraction; distinguish backend availability from actual validation.
- [x] Compact shared file identity, conclusions/evidence/methodology hierarchy,
  album/track selection in Analyze File; other pages unchanged.
- [x] Synthetic and real authorized Aja CUE/DFF/ISO checks, regressions, startup,
  source-preservation verification and honest validation report.

Authorized Aja paths are supplied explicitly by owner; no music is copied into the
repository, uploaded or committed. Selected-track temporary audio stays in the OS
temporary directory with controlled cleanup. Backend binaries are not auto-installed.
No v1.0 declaration or remote push. Existing Origin and signal algorithms remain.

Completed validation:359 passed /0 failures /0 skips,124.94s with real DSF/ISO;
Ruff/format/compileall and actual Edge rendering. Seven Aja tracks enumerated from
both sources; selected Peg/Josie/Black Cow checks executed, source hashes preserved.
Owner explicitly approved portable official sacd_extract download/run; ignored local
backend, no system/PATH changes. Real DST/multichannel audio and other image/backend
variants remain unvalidated. See CUE_SACD_METHODS.md and CUE_SACD_VALIDATION.md/.json.
