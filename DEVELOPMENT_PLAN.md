# Music Project — implementation ledger

## Lossy source investigation — 0.2.5.dev0 (2026-11-12)

Added a typed bounded native PCM investigation inside the existing technical decode:
adaptive audible-band candidates, energy/floor proxies, per-channel/time evidence,
explicit exclusions and abstention. Existing Origin boundary utilities and streaming
Welch are reused. Normal/Expert remain the same UI/navigation; all original evidence,
DSD/Hi-Res/integrity/loudness algorithms remain. General methodv9 invalidates stale
results, application version stays0.2.5.dev0.

Executed106synthetic A/B/C/D cases with actual MP3/AAC encoders/configurations:
49/64known-lossy and4/42non-lossy cases trigger spectral observations. No historical
codec classifier/confidence is deployed; flux/pre-post descriptors overlap controls.
Authorized140.293333s16/44.1FLAC measured read-only:32windows/64s, near-Nyquist
21425.537Hz candidate recurrent32/32per channel; Inconclusive, codec Unknown.
MD5Verified and source SHA-256 preserved. Other metering values match supplied numbers
after rounding. Real DSF regression retained; the earlier Aja ISO is unavailable now.

[Persistent plan](docs/LOSSY_IMPLEMENTATION_PLAN.md), [methods](docs/LOSSY_METHODOLOGY.md),
[executed matrix, limitations and commands](docs/LOSSY_VALIDATION.md).
No release1.0 declaration, private-audio copy/upload, dependency installation or push.

## Engineering validation — 0.2.5.dev0 (2026-11-11)

Preserved the results-first UI. Corrected demonstrated DFF mandatory-chunk/version/
field-bound validation, spectral selection before applicability, entropy-stride aliasing
of exact24-bit grid checks, and PCM prefix metering extending beyond the selected scope.
FLAC MD5 expanded to independently decoded known8/16/24/32-bit mono/stereo controls.
General method2026.11-v8 / DSDv3 / technical-PCMv2 invalidate stale results; application
version, Origin rules, conversion filters, TP algorithm and duration policy are retained.

Fresh baseline364passes; final **419 passed,0failed,0skipped;136.95s**, authorized real
DSF/SACD enabled. Independent48kHz K-weighting/gates/LRA controls pass0.15/0.25LU
tolerances. Actual Pink Panther full176.4/352.8kHz outputs agree at234.026666667s;
Aja CUE/DFF and ISO each enumerate7tracks and fully decode Peg236.8s. Original audio
SHA-256 and size/mtime signatures match. Startup HTTP200 and real FLAC/DSF Analyze File
integration completed. Ruff/format104files/compileall/pip check/43core imports passed.

This is selected measurement/engineering validation, not v1.0, general provenance
identification or metering certification. Real DST/multichannel/corpus, broader reference
and distribution validation remain. [Persistent progress](docs/V1_ENGINEERING_PROGRESS.md),
[matrix/commands](docs/V1_VALIDATION_MATRIX.md), [snapshot](docs/V1_VALIDATION.json).

## Logical CUE/SACD tracks and result clarity — 0.2.5.dev0 (2026-11-10)

Analyze File now presents compact source identity before conclusions, with separate
container/codec and native rate/depth/channel/duration fields. Detailed measurements,
rules and methods remain accessible. Added typed fingerprinted logical sources,
bounded CUE parsing/resolution and exact selected-track native PCM/DSD preparation.
Track-relative scopes include explicit source-time mappings; complete-track checks
never stand for complete albums or images. Other application pages are not redesigned.

SACD uses bounded master/primary-area checks plus optional sacd_extract capabilities,
actual TOC enumeration and controlled one-track native DSF extraction/cleanup. Owner
authorized the official portable 0.3.9.3-107 backend in ignored data/backends/; no PATH
or system installation change. No automatic backend downloader is in the application.

Explicitly authorized Aja CUE/DFF and ISO were actually read: seven tracks in each;
stereo DSD64, native DFF and uncompressed DSD ISO area. Peg was fully decoded through
both sources; current-version tool also fully decoded CUE Josie 271.786667 s and ISO
Black Cow 307.986667 s. All original SHA-256 and size/mtime checks matched. Their distinct
timelines are retained; no ISO/DFF audio or mastering identity comparison was made.

Final full matrix: **359 passed, 0 failed, 0 skipped; 124.94 s**, real DSF and ISO enabled.
Ruff/format (94 files)/compileall passed. Actual local Edge rendered ordinary FLAC and
real CUE/ISO selection/results with 0 app exceptions. Mocked DST/multichannel tests
are explicitly separate from real uncompressed stereo end-to-end validation.

App 0.2.5.dev0 / general method v7 / logical-source v1; analytical DSP/method families
remain unchanged. Methods/results: docs/CUE_SACD_METHODS.md, CUE_SACD_VALIDATION.md/.json.
Real DST, multichannel signal analysis, raw/encrypted/damaged image variants, other
backend protocols/encodings and commercial redistribution/release validation remain.
No Collection DNA 2/major Compare 3 work, audio upload/commit, push or v1.0 declaration.

Post-scope-guard UI matrix: 29 passed, 0 failed, 31.94 s; logical-track external
reference comparison explicitly unsupported rather than analyzing the whole album.

## Evidence-Based Conclusions Engine — 0.2.4.dev0 (2026-11-10)

Implemented reusable deterministic typed statements with measurement references,
component scopes, versioned rules, applicability and limits. Analyze File now uses
one bounded full/prefix technical PCM decode for Integrated/LRA/M/S, reconstructed
peaks, native sample/RMS/crest/rail/plateau facts and native-FLAC 16/24-bit MD5/count
checks. Existing spectrum prefix, Origin and distinct native DSD pipeline remain.
Custom reference gain/ceiling math never modifies audio or silently selects a target.
Everyday Russian Technical Findings and Expert evidence/curves share saved facts.
Cache progress is emitted outside cached functions; view/reference reruns do not decode.

Application 0.2.4.dev0 / general method v6; conclusions v1 / technical-pcm v1.
Origin v1, DSD v2 and duration v1 retained. Permanent objective-analysis standard now
requires supported interpretation without exceeding evidence. Methods and executed
matrix: docs/CONCLUSIONS_METHODOLOGY.md, CONCLUSIONS_VALIDATION.md/.json.

Executed full regression: 319 passed, 0 failed, 1 real SACD skip in 116.04 s; real DSF
enabled. After the final chart-axis display correction, all 3 relevant UI tests passed
in 6.80 s. Ruff/format/compileall passed; actual local Edge rendering had 0 app exceptions.
Generated controls establish whole-stream −23 LUFS, matched FLAC MD5 and above-zero TP
with zero rail hits. Supplied Pink Panther source SHA-256 stayed unchanged and duration
remains 234.026666667 s Verified. Sad Girl is unavailable and was not remeasured.

Selected synthetic standards controls passed; complete ITU/EBU conformance, terminal
LRA convention, other TP rates/layouts, 8/32-bit FLAC MD5, real DFF/DST/SACD corpus and
authenticated provenance remain open. Real-library profiling, asynchronous UI cancel,
human/accessibility/Windows release validation and commercial distribution work remain.
Single-session 240 s synthetic PCM observation: 5.617 s technical pass, 13.946 MiB Python
allocator peak excluding FFmpeg/RSS; not a general performance improvement claim.

Roadmap 0.3/0.4 reservations and older ledger history are preserved. Collection DNA 2 and
major Audio Comparison 3 are not started. This is not v1.0; stable release still requires
explicit owner approval. No original audio changes, audio commits/uploads or remote push.

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

## UI correction verification — 2026-11-11

The ledger above records the original foundation milestone and its historical limits.
This presentation correction retains application 0.2.5.dev0 and analytical method
2026.11-v7. Overview is compact; Integrity, Levels and Origin each own their findings;
raw rules, JSON and logs are available in Technical Appendix. Modes share saved results.
No analytical core, decoder, CUE/ISO processing or unrelated page source changed during
this correction (53 matching protected-file hashes).

Executed: 364 full-suite tests passed with authorized real DSF/SACD fixtures; 2 targeted
DSD UI tests passed after the final layout adjustment; Ruff, formatting and compileall
passed. Actual Edge desktop inspection covered ordinary/high-rate FLAC, short silence
with unavailable loudness measurements, and the authorized DSF. Mobile, accessibility
and a human usability study remain unvalidated by this correction.
See [scope and validation](docs/UI_RESULTS_FIRST_VALIDATION.md).
