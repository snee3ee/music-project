# Verification — 0.2.1 / 2026-11-05

Application 0.2.1; general/PCM method 2026.11-v3; DSD method dsd-2026.11-v1.
This is an explicitly documented extension of 0.2, retaining the 0.3/0.4 roadmap.

## Executed checks

- Before implementation: **126 passed, 0 failed, 1 skipped**, 15.79 s.
- Final full regression: **184 passed, 0 failed, 2 skipped**, 21.58 s; 186 collected.
  No tests were removed. Existing DSD metadata-routing tests now also require integrity
  results, while retaining their metadata and native-PCM exclusion assertions.
- Ruff check: all checks passed. Final Ruff format check: 65 Python files already formatted.
- `compileall -q music_project app.py tools tests` completed successfully.
- `pip check`: no broken requirements. No type checker is configured or claimed.
- Editable 0.2.1 install with `--no-deps --no-build-isolation` succeeded. A pre-existing
  root egg-info 0.2.0 shadowed the new dist-info; regenerated using setuptools egg_info.
  Both `music_project.__version__` and `importlib.metadata.version` now return 0.2.1.
- Actual Streamlit server on a temporary loopback port: `/` and `/_stcore/health`
  both HTTP 200. The test-owned server was terminated afterward. No visual browser
  inspection was performed.
- AppTest verified all eight pages and previous analysis/spectrum/preview, library,
  archive navigation, file selection and comparison workflows. Added actual DSD full
  analysis at 176.4 kHz, collapsed diagnostics, PSD toggle, and missing-FFmpeg behavior
  preserving metadata. AppTest checks behavior, not actual browser rendering.

Exact repeatable checks from the repository root:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m compileall -q music_project app.py tools tests
.venv\Scripts\python.exe -m pip check
```

## Actual decoder versus controlled tests

Local FFmpeg/ffprobe: **9.0.2-full_build-www.gyan.dev**. No backend was downloaded.
`tests/test_dsd.py` contains 46 collected tests, 45 passed and one conditional skip
within the final regression. Real-backend tests actually invoke FFmpeg on generated
DSF DSD64/128/256 stereo, DSD256 mono, both 176400/352800 output settings, generated
DFF DSD64 stereo, DSF LSBF/MSBF pulse-density 2 kHz controls, and deterministic seeked
windows. Changing positive/negative density by time checks that seeking selects the
requested signal position. A malformed input actually fails in the local backend.
These are end-to-end **generated-container** checks, not real recordings.

Separate unit tests inject conversion outputs/failures for wrong output rate/channels,
NaN, empty/incomplete data, premature successful EOF, fatal errors and warning retention.
They validate failure semantics, not decoder fidelity. Welch comparisons use actual
SciPy density output, exact-tone power/Parseval, gain/inverted stereo, silence/tiny
signals, unsupported bands and disjoint-window controls. No provenance accuracy claim.

Skipped tests:

1. Real DSD256 recording: no user-supplied fixture. Set `MUSIC_PROJECT_DSD_FIXTURE`
   explicitly to run the opt-in full-decode test. The Pink Panther file was not located,
   searched for, copied or analyzed.
2. Real SACD integration: no real SACD fixture or validated sacd_extract backend.

Regression coverage includes stereo sampling parity, backend-change reindexing,
cancellation on empty traversal, bounded stderr without deadlock, cancellation of a
backend emitting no stdout, optional malformed loudnorm values, cache parameters,
source identity, preserved integer PCM hashes/duplicates, comparisons and manifests.
SQLite schema remains v1; older records refresh at the next requested scan, with UI notice.

## Executed performance measurements

Command: `.venv\Scripts\python.exe tools/benchmark_dsd.py --seconds 20 240`.
Raw report: [DSD_BENCHMARK.json](DSD_BENCHMARK.json). Only generated repeated-byte
uncompressed DSF was used, on the local warm filesystem. No user audio or speedup
against the prior metadata-only feature is claimed. Python allocator peak is tracemalloc;
RSS is sampled every 5 ms across Python plus active child backends and can miss spikes.

| Fixture / mode | Runtime, s | Python allocator peak, MiB | Sampled Python + children RSS peak, MiB | Decode / total subprocesses |
|---|---:|---:|---:|---:|
| DSD256 20 s, 53.836 MiB / Quick | 0.984 | 6.95 | 147.03 | 3 / 6 |
| Same / cached Quick | 0.0453 | 1.81 | 123.94 | 0 / 0 |
| Same / Full | 1.053 | 6.94 | 149.80 | 1 / 4 |
| DSD256 240 s, 646.000 MiB / Quick | 1.250 | 6.94 | 150.60 | 3 / 6 |
| Same / cached Quick | 0.0459 | 1.81 | 123.96 | 0 / 0 |
| Same / Full | 10.005 | 6.94 | 150.34 | 1 / 4 |

Quick processed exactly 15 s in three windows and returned Partial. Full processed
20/240 s to EOF and returned Passed. Full used one decode; total subprocess counts
also include ffprobe and FFmpeg/ffprobe version queries. Cache hit performed no backend
invocations. Increasing generated duration did not require a whole-track PCM buffer;
the measured allocator peaks remained approximately 6.94 MiB. RSS includes interpreter,
Streamlit, numerical libraries and FFmpeg, so it is not the analysis buffer budget.
These figures are observations on one machine, not guaranteed real-library throughput.

Existing scan benchmark also executed: 32 generated mono 48 kHz / 16-bit / 3 s WAVs,
initial 4.086 s, unchanged rescan 0.0190 s, 32 reused records and zero errors. No valid
before/after percentage comparison or large-library performance claim is available.

## Remaining limitations and next priorities

- Effective composite DSD-decoder/resampler frequency response is **Not validated**.
  Ultrasonic values are measurements of converted PCM; native DSD band preservation
  cannot be inferred. No native DSD authenticity/source-rate detector exists.
- No real recording/DST/SACD corpus, independent certified LUFS/True Peak reference,
  or calibrated provenance error rates. Existing PCM heuristics remain exploratory;
  thresholds were not loosened. No new experimental origin heuristic was introduced.
- DSD multichannel spectra and optional detailed DSD spectrogram are Unsupported/
  not implemented. DST compression is recognized but not decoded by this subsystem.
- UI is synchronous, with progress and timeout. Python cancellation works during
  decoding; a dedicated asynchronous UI Cancel/resume workflow remains future work.
- Size/mtime identities are practical cache guards, not cryptographic identity.
  Bypass cache/force scan for edits preserving these values; use archival hashes.
- No collection-scale crash/concurrency benchmark, rendered-browser/accessibility
  validation or commercial packaging/licensing audit. Existing v1.0 roadmap remains.

Launch locally: `.venv\Scripts\python.exe -m streamlit run app.py`, or
`Music_Project.bat`, then http://127.0.0.1:8501. Exact real-DSD256 steps are in
[README](../README.md#проверка-реального-dsd256). Original audio remains read-only.
