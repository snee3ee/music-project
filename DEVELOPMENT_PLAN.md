# Music Project — implementation ledger

## Current focus — version 0.2

User accepted 0.1 and narrowed the next milestone to established signal observations,
clear Russian interface with English engineering terms and simpler file selection.
No unrelated product features are added in this milestone. The earlier broad roadmap
below is retained as history; it is not the current execution scope.

Implementation: structured measured observations separate from historical inference,
readable tables/statuses/scope, Windows OpenFileDialog plus manual path fallback,
explicit -infinity vs missing values, declared mono/conventional stereo layout sources.
Method 2026.10-v2, application 0.2.0. See docs/RELEASE_0_2_PLAN.md and
docs/VALIDATION_0_2.md for the current scope and executed checks.

## Scope and acceptance

Build usable local, read-only vertical slices. Preserve AGENTS.md, local skills,
legacy_reference and Git history. No uploads, source edits, cleanup or remote pushes.
Each milestone needs executed tests, Ruff, UI checks and documented limitations.

## Execution plan

1. Foundation: Python 3.13 virtual environment, reproducible packaging, typed models,
   bounded subprocess execution, actual ffprobe routing and Russian Streamlit shell.
2. File analysis: bounded PCM context, loudness, peaks, spectrogram, conservative
   cutoff/upsampling evidence, 24-bit quantization with synthetic controls.
3. Library: SQLite incremental recursive indexing, metadata/album audit, errors,
   progress, full decode verification and streaming file/audio hashes.
4. Integrity: exact/decoded duplicates and portable, safe manifests.
5. Compare: restricted equal-rate/channel alignment, gain/polarity/null metrics.
6. Specialized inputs: CUE validation, DSD routing, ISO recognition and honest
   optional-backend fallback. No native DSD quantization.
7. Extensions: device profiles, JSON reports and independent entitlement policy.
8. Stabilize: regression and Streamlit AppTest checks, launcher, documentation,
   dependency lock and verified launch.

## Initial environment inspection

- Python 3.13.15 found at local Python installation; WindowsApps aliases fail.
- FFmpeg and ffprobe 9.0.2 are available.
- sacd_extract and standalone fpcalc are absent from PATH.
- legacy_reference/app.py inspected: repeated full-file temporary copies/decodes,
  locale-dependent subprocess text, thresholds not supported by tests. Preserved.
- AGENTS.md and audio-forensics skill read and preserved.

## Implemented milestones (0.1.0)

- Foundation: editable Python package, isolated .venv, pinned Windows/Python 3.13
  dependencies, typed results, versioned methods, UTF-8/binary subprocess handling,
  timeout/output limits, streaming PCM without full-file RAM/disk copies.
- File analysis: actual format probe, bounded native-rate f64 context, full-stream
  LUFS/LRA/True Peak, prefix Sample Peak/RMS/crest, spectrogram, conservative cutoff/
  Nyquist evidence and 24-bit grid/entropy. No provenance certainty claims.
- Library: persistent SQLite v1, future-schema rejection, closed connections, recursive
  scanning, incremental/force scans, new/modified/removed records, full decode, per-file
  errors, progress callback, basic metadata/album checks and storage aggregation.
- Integrity: byte/PCM hashes, separate duplicate categories, byte duplicates even of
  unreadable files, portable SHA-256 manifests with safe relative paths.
- Comparison: equal-rate/count/layout prefixes, integer alignment, gain/polarity,
  correlation and guarded null metrics; periodic ambiguity explicitly reported.
- Specialized inputs: synthetic DSF/DFF metadata/routing, CUE validation, ISO signatures,
  sacd_extract command planning (no extraction execution).
- Extensions: explicit device constraints, JSON downloads, independent allow-all
  development entitlement policy; no payments or online identification.
- UI: eight Russian Streamlit pages, collapsed advanced details, graph/preview,
  session backend settings. Local-only server, usage telemetry off, repository-local plot cache.
- Windows launcher implemented and executed with the actual .venv.

## Verification ledger — 2026-10-28

Final complete run: **89 passed, 0 failed, 1 skipped**, 14.74 s. The skip is explicitly
real SACD integration without a real fixture/backend. Tests include stereo canonicalization
and future SQLite schema preservation.

- Ruff check/format, Python compileall and pip check passed.
- Final Ruff format check: 43 Python files already formatted.
- AppTest: all eight pages, valid/invalid analysis, collapsed quantization, spectrogram/
  preview, scan/dashboard and identical-track comparison. No rendered-browser test performed.
- Direct server and Windows launcher: http://127.0.0.1:8501/ and /_stcore/health returned 200.
- Editable installation with locked setuptools and --no-deps --no-build-isolation executed.
- Small scan benchmark: 32 generated 3 s / 48 kHz / 16-bit mono WAV, 4.202 s initial,
  0.0061 s unchanged rescan, zero errors. Not a large-library performance claim.
- Only generated fixtures used; no user collection accessed or uploaded.
- AGENTS.md, local audio-forensics skill and legacy_reference/app.py unchanged.

## Exact remaining tasks and acceptance criteria

1. Forensics: labelled diverse real-recording corpus, codec artifacts beyond bandwidth,
   fitted transition widths/additional candidates and documented error rates before broader
   suspicion/confidence claims. Current thresholds are exploratory and conservative.
2. Metering: independent LUFS/LRA/TP reference fixtures and unusual layout validation.
3. Index: schema migrations, backend/settings-aware automatic invalidation, stored deep
   forensic/loudness results, background/cancel UI and crash recovery. Test long scans,
   inaccessible subtrees and concurrency at collection scale. Cancellation callback currently
   operates only between files; UI scan is synchronous.
4. Metadata: numeral normalization, multi-disc grouping, artwork presence/size, filename
   checks, album loudness/forensic-status differences, with tests for every heuristic.
5. Duplicates: optional fpcalc adapter and validated acoustic similarity, separate from
   identity; hardlink recognition before physical savings claims; more PCM/channel variants.
6. Compare: spectral-difference metrics, fractional delay, drift, disclosed resampling and
   album/edition matching. Validate alignment uncertainty on real signals.
7. Archive: optional canonical hashes, per-file creation-error policy, trusted/signed
   manifest workflows and scalability. Current SHA-256 manifests remain usable.
8. DSD/DST: real fixtures, native metadata variants and explicitly filtered conversion-derived
   measurements with parameters; never native PCM bit tests.
9. SACD: trusted optional backend/legal real fixture, fork/version validation, TOC/areas/tracks,
   controlled temporary extraction and cleanup on failure. Command-plan unit tests are not
   end-to-end validation. No executables auto-installed.
10. CUE: referenced-audio duration bounds, logical-track analysis and multi-file playback.
11. Safe actions: concrete preview/logging and original-preservation pipeline for tag repair,
    rename, recompression, conversion and cleanup. No source modifications exist now.
12. Optional MusicBrainz/AcoustID adapters: opt-in privacy, API limits and identity/provenance
    separation. No network identification enabled now.
13. Commercial: signed installer/update system, artifact-hashed release builds, dependency/
    backend redistribution audit, third-party notices, chosen license, migration/recovery
    policy and secure licensing beyond the development allow-all boundary.
14. Release UX: real-browser/accessibility/manual Windows 10/11 matrix, larger-library
    profiling and privacy review. AppTest checks behavior, not browser rendering.

## Blockers and scope boundary

sacd_extract and standalone fpcalc are missing. Real music, native DSD/DST recordings and
real SACD fixtures are unavailable; none downloaded. Their absence does not prevent the
implemented PCM/index/duplicate/compare/archive workflows. This is a runnable foundation,
not completion of every phase or commercial Music Project v1.
