# V1 engineering and validation session — 2026-11-11

Subsequent focused lossy-investigation session (2026-11-12): methods advance to generalv9,
application remains0.2.5.dev0. The ledger below remains the historical engineering run.
Current measurements,106-case actual-encoder matrix, supplied FLAC, explicit abstention,
and current real-ISO unavailability are recorded in [lossy progress](LOSSY_IMPLEMENTATION_PLAN.md)
and [validation](LOSSY_VALIDATION.md). No v1.0 completion is implied.

Application starts this session at 0.2.5.dev0; v1.0 is not declared complete.
The prior results-first UI correction and all pre-existing uncommitted work are retained.
No Collection DNA 2, Compare 3, visual redesign, audio upload, installation or push is planned.

## Persistent execution plan

- [x] Read current instructions, local Audio Forensics skill, development ledger,
  methodology, prior validation and current source/test architecture.
- [x] Run and record an independent baseline with authorized real DSF/SACD fixtures.
- [x] Validate forensic discrimination with positive, negative, ambiguous and adversarial
  ground-truth controls; correct demonstrated overclaims without inventing provenance.
- [x] Audit DSF/DFF structure, native rate/duration/conversion and selected-track precision;
  add regression coverage and correct demonstrated defects.
- [x] Validate loudness, peaks and FLAC integrity against independent calculations or
  implementations, documenting numerical tolerances and limits.
- [x] Exercise authorized real DSF, Aja CUE/DFF and SACD ISO through existing backends;
  record enumeration, selected-track decoding and source preservation separately.
- [x] Complete regression/static/import/startup and Analyze File checks; update the
  validation matrix, methods, reproducible commands and remaining engineering priorities.

## Starting evidence and scope

Previous UI milestone recorded 364 full-suite passes plus 2 subsequent targeted DSD
layout passes. This is historical evidence; a fresh baseline was executed below.
Existing UI has compact Overview, one primary module for each finding, Appendix-only
raw rules/JSON, and both modes use stored Analysis results.

Earlier executed reports establish stereo uncompressed DSD64 Aja CUE/DFF and ISO
enumeration/extraction, and Pink Panther DSD256 duration/decoding; they are not treated
as new executions. Available optional portable sacd_extract is already owner-authorized.
Current session uses only the specific authorized audio paths, read-only. Large source
recordings are not copied into the repository; owned selected-track temporaries may be
created and removed by the existing pipeline.

## Milestone ledger

Baseline executed: **364 passed, 0 failed, 0 skipped; 137.34 seconds**, authorized real
DSF and SACD fixtures enabled. Previous results-first presentation is present.

Reproduction before corrections: new structure/forensic controls returned **9 failed,
1 passed in 1.65 seconds**. Eight failures demonstrated ignored DFF FVER/order/field
bounds (including an unsupported major version reported Passed). One demonstrated
an eligible 20 kHz boundary hidden by a larger, ineligible low-energy notch ratio.
These are confirmed defects in structural checking/candidate selection, not evidence
that an original user recording is corrupt or has a particular history.

Completed corrections: bounded FVER/version/order/CMPR-name checks; candidate ranking
after applying all original guards, preserving thresholds and candidate data.
General method advances to 2026.11-v8 and DSD method to dsd-2026.11-v3 for cache/result
invalidation; application version remains 0.2.5.dev0. Forensic compatibility remains
experimental, with no authenticated codec or sample-rate history claim.

Structure/candidate correction checks: **115 passed, 1 skipped in 8.83 seconds**;
the skip was the opt-in real DSF test in this targeted invocation without its environment
variable (the independent baseline included it). Ruff and affected imports passed.

A second confirmed defect: with prefix scope 2.05 seconds, actual FFmpeg metadata
extended to 2.20 seconds because output `-t` truncated audio after the meter filter.
Regression before correction: **1 failed, 4 passed in 7.71 seconds**. Those four passes
compare Integrated/LRA to an independent SciPy implementation of published BS.1770
48 kHz K-weighting and EBU3342 gating/percentiles; no product/FFmpeg metering code is
used in that reference. Broadband, changing-level/gated, anti-phase and 5.1/LFE controls
passed fixed 0.15 LU Integrated and 0.25 LU LRA tolerances. This is not certification.
The prefix correction trims at native sample indexes before metering; technical method
advances to technical-pcm-2026.11-v2. Full-stream algorithm and numerical models remain.

Post-correction metering/conclusions/source matrix: **97 passed in 32.77 seconds**.
An additional adversarial quantization control reproduced **1 failed, 19 passed in
1.74 seconds**: entropy stride2 missed every off-grid sample of an alternating input
over the sampling budget. Exact grid/zero-byte fraction now checks every active sample
of the already decoded bounded prefix; entropy/unique counts stay bounded to one million
and their channel populations/strides are recorded. Scope never expands to unseen audio.
Forensic/PCM/engineering/observation checks after correction: **69 passed in 3.60 seconds**.

Three seeds each validate sharp cutoff observations, sharp-upsample boundaries, and
negative/ambiguous full-band, broad-polyphase and noise-masked upsample cases. Lossless
filtering also triggers cutoff evidence, while high-entropy dithered16-bit controls
retain known16-bit history. These counterexamples disprove historical identification
from the individual tested feature; no accuracy percentage is inferred from them.

Logical-source precision: **8 passed in 5.10 seconds**, exact selected PCM samples at
32/44.1/88.2/96 kHz from FLAC and float64 WAV, including ceiling-rounded nonintegral
75-fps boundaries, source hashes and end-to-end track-relative scope/temporary cleanup.
No CUE extraction or SACD decoding algorithm change was required by these controls.
Authorized Aja CUE currently resolves all seven tracks Ready; its DFF is stereo native
DSD64, duration2379.733333333 seconds. Completed selected-track real CUE/ISO validation
is recorded in the separate ignored `data/v1-validation/sources` report directory.

## Additional completed milestones

- Actual Aja run: CUE track4 Peg and ISO stereo track4 Peg both fully decoded,
  duration236.8 seconds; **12.078 s / 9.559 s** respectively. All original CUE, DFF
  and ISO SHA-256 and size/mtime signatures matched after testing. Seven tracks were
  enumerated independently per catalog. This is uncompressed stereo DSD64, not DST
  or multichannel signal validation. Reports: `data/v1-validation/sources/`.
- Independent RFC9639 verbatim fixtures establish exact decoded samples at8/16/24/32
  bits, mono/stereo, including negative rail/positive maximum/low-order bits. Prior
  8/32-bit MD5 applicability was explicitly Not validated; it was enabled only after
  actual decoding and known independent digests. Embedded digest checking now covers
  byte-aligned8/16/24/32 depths. Non-byte-aligned FLAC depths remain Not validated.
  Missing/corrupt/partial digests retain separate states. FLAC/conclusions matrix:
  **65 passed in 24.97 seconds**. The pre-enable6fail/4pass run measured an intentional
  capability gap, not six previously concealed decoder defects.
- Authorized Pink Panther DSF: complete EOF at176400/352800Hz, both234.026666667s
  Verified, **10.056s / 12.649s**. Original SHA-256 and size/mtime signatures matched.
  Nonfatal bitrate-duration estimate warning retained; secondary235.881361s unchanged.
- Native FLAC clean whole-frame truncation checks: **12 passed in4.32s** for the full
  new FLAC matrix, including8/32-bit count failures despite decodable first frames.
- A second spectral adversary reproduced1failure/20passes in2.28s: excitation passed
  but the strongest-drop candidate failed the upper-level threshold. Candidate ranking
  now follows **all** guards; forensic/PCM/observation matrix then **59 passed in2.00s**.
- Intermediate full regression:418passed in146.31s before the last candidate-selection
  extension; final full regression after it: **419 passed,0failed,0skipped;136.95s**,
  real DSF and SACD enabled. JUnit stored at `data/v1-validation/pytest-final.xml`.
- Ruff check/format (**104 Python files**), compileall, pip check and imports of all
  **43 core modules** passed. Diff whitespace check passed; standard LF/CRLF notices
  were emitted without any Git configuration change.
- Actual Streamlit root/health HTTP200; actual Analyze File FLAC and real full DSF
  AppTest completed with0app exceptions. Both modes and main modules preserved the
  saved result with all subprocess launches forbidden. An auxiliary PowerShell stderr
  redirect classified bare-mode Streamlit logger warnings as a shell error; the completed
  two-case JSON was independently read back and its assertions verified.
- Generated20s/240s streaming controls completed;240s input65.918MiB, Python allocator
  peak13.948MiB,1376retained rows per timeline. Excludes FFmpeg/RSS; no general speedup
  or whole-application memory claim. Generated FLAC/loudness/peak controls were unchanged.
- Final post-integration SHA-256 and size/mtime rechecks matched for all four authorized
  original DSF/CUE/DFF/ISO files. `git check-ignore` confirmed test audio and generated
  reports excluded. Eight earlier protected unrelated UI/configuration file hashes
  match. Validation JSON was written/read back and new documentation links checked.

Session deliverables completed: [matrix and test commands](V1_VALIDATION_MATRIX.md),
[executed JSON snapshot](V1_VALIDATION.json), updated technical methods/format scope.
Checked session tasks above do not mean completion of the v1.0 release priorities below.

## Unverified capabilities and remaining release work

- Universal lossy/source-rate/bit-depth historical classification and authenticated
  provenance are not established by signal properties.
- Complete ITU/EBU metering certification, held-out diverse real-recording accuracy,
  professional DSD modulator/filter chains and broad backend/version matrices remain.
- Real DST-compressed and multichannel SACD signal analysis, encrypted/raw-sector and
  damaged image variants are separate from the available stereo uncompressed fixture.
- Mobile/accessibility/human usability, large real-library profiling, asynchronous UI
  cancellation, signed distribution and commercial redistribution validation remain.

## Blockers requiring intervention

No permission or filesystem blocker prevented the completed work. No new executable
was downloaded or installed. Standalone fpcalc is unavailable. Real DST/multichannel
fixtures, independent complete metering reference sets and held-out authenticated
source-history corpora are unavailable for their respective validation goals; the
implemented independent controls and authorized stereo files were completed regardless.
See [validation matrix and reproducible commands](V1_VALIDATION_MATRIX.md) for the
remaining release priorities. Version remains0.2.5.dev0; v1.0 is not declared complete.
