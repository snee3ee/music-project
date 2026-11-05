# Music Project — implementation ledger

## Audio Origin Investigator — compatible extension 0.2.3 (2026-11-05)

Implemented end-to-end signal investigation in Analyze File: empirical backend response,
independent native DSF/uncompressed-DFF PSD, six candidate bandwidth compatibility
tests, per-channel temporal evidence, exploratory ultrasonic regimes and optional
reference alignment/gain/polarity/correlation/residual/identity investigation.
Everyday is the default; Expert preserves existing measurements and diagnostics.
View switches use the same stored result. Library/Compare/Duplicates/Archive UI source
was not changed by this milestone; pre-existing uncommitted work was preserved.

App 0.2.3; general method v5; Origin v1; response calibration v1. DSD method v2 and
duration policy v1 retained. Scope and counterexamples: docs/ORIGIN_METHODOLOGY.md;
executed checks/measurements: docs/ORIGIN_VALIDATION.md and ORIGIN_VALIDATION.json.
Roadmap 0.3/0.4 reservations are retained. This milestone validates measurements and
compatibility, not a universal historical-format classifier or release authenticity.

Future modules should provide an ordinary-listener summary and an Expert evidence
view of one result, with implemented verification actions. Further priorities:
held-out professional modulator/filter chains; real DFF/DST and DSD512 recordings;
authenticated reference/chronology evidence; broader primary literature review;
human timed comprehension evaluation and explicit asynchronous UI cancellation.

## DSF/DFF duration correctness — 0.2.2 (2026-11-05)

Investigated the explicit repository DSF read-only. Mutagen/APIC and binary field
inspection established a 5,230,592-byte ID3 tail (5,229,518-byte JPEG front cover)
plus 4,096 bytes of declared block padding. ffprobe's estimate includes these bytes;
controlled generated metadata-size tests isolate that behavior. Native sample count
and full PCM decoding agree at 234.026666667 s on both output rates.

Added typed duration selection, structured source/status/evidence, secondary ffprobe
duration and exact padding accounting. Probe and analysis now select native audio
duration; full consistency is Verified, partial is Derived, unsupported/invalid
structure is not replaced by a bitrate estimate, full mismatch is Ambiguous.
UI displays the selected audio duration; secondary values are in Technical Appendix.
Old records remain readable, SQLite schema unchanged; method-aware rescan refreshes
previous estimates when requested. Existing PCM/provenance thresholds unchanged.

Application 0.2.2; general method 2026.11-v4; DSD method dsd-2026.11-v2; duration
policy dsd-duration-2026.11-v1. Full regression 221 passed / 1 SACD skip, real DSF
full rechecks on 176400/352800 Hz and source SHA-256 preservation verified. Details:
docs/DSF_DURATION_VALIDATION.md and docs/DURATION_POLICY_PLAN.md. No Origin Investigator
classifier implemented; earlier milestones below are historical and preserved.

## Analyze File information architecture — 2026-11-05

Restructured only Analyze File around persistent Overview / Integrity / Measurements /
Provenance / conditional DSD / Technical Appendix navigation. Configuration is a single
collapsed group; raw diagnostics/commands/exact values are centralized. Display navigation
uses saved results, with cached PCM plot FFTs and no audio re-decoding. Native DSF duration
is shown with its source, separately from ffprobe estimation. Warning deduplication preserves
event counts, interval references and original text. Existing PCM prefix/loudness scopes
are retained without inventing an independent full-integrity check.

Permanent ONLY FACTS. NO OPINIONS. policy appended to AGENTS.md. No analytical threshold,
core method, unrelated page behavior or database schema changed in this UI milestone.
Application remains 0.2.1; analysis methods remain 2026.11-v3 / dsd-2026.11-v1.
The earlier 0.3/0.4 roadmap and current uncommitted work are preserved.

One explicitly supplied real DSD256 DSF was checked read-only: Quick 352.8 kHz and
Full 352.8/176.4 kHz; full decoding passed with 234.026666667 s, distinct from estimated
235.881361 s ffprobe metadata. Real-file regression is now executed, not skipped.
See docs/ANALYZE_UI_PLAN.md and docs/ANALYZE_UI_VALIDATION.md for exact results and limits.

## Compatible extension — 0.2.1 (2026-11-05)

Implemented DSD Signal Diagnostics and reliability audit as an explicit extension
of 0.2, preserving the 0.3/0.4 reservations in docs/RELEASE_0_2_PLAN.md. No Audio Time
Machine/snapshot code exists in this checkout; existing pages and SQLite schema v1
are preserved. Application 0.2.1, PCM/general method 2026.11-v3, dedicated DSD method
dsd-2026.11-v1. Earlier verification ledgers below remain historical.

- Native structural DSF/DFF checks are separate from strict complete/partial decode.
- Streaming FFmpeg float32 conversion at 176.4/352.8 kHz validates actual output
  rate/channels/layout mask; exports commands, backend versions, warnings and errors.
- Per-channel streaming Welch PSD, band powers, median density and L−R differences;
  explicit audible/ultrasonic scope and conversion/filter limitations. No origin classifier.
- Quick deterministic multi-position windows; full single-pass decoding to EOF;
  progress callback/UI progress and API cancellation. No asynchronous UI Cancel yet.
- Fixed stereo quantization sampling, optional malformed loudnorm handling, comparison
  guards, bounded stderr, cache identities, backend-aware reindex and cancellation
  before removed-file reconciliation. Existing SQLite records remain readable and
  refresh on the next scan; UI explicitly discloses revalidation.

Evidence and remaining work: docs/ENGINEERING_AUDIT.md, docs/DSD_METHODOLOGY.md,
docs/DSD_IMPLEMENTATION_PLAN.md and docs/VALIDATION_0_2_1.md. DSD256 real-recording
validation, composite conversion response, real DST/SACD and multichannel spectra
remain unverified/unsupported. No original audio modified or uploaded.

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
