# Result clarity, CUE and SACD — executed validation, 2026-11-10

Application **0.2.5.dev0**, general method **2026.11-v7**. This is a development
milestone, not v1.0. [Methods and applicability](CUE_SACD_METHODS.md).
[Measurement snapshot](CUE_SACD_VALIDATION.json).

## Authorized inputs and actual access

The owner explicitly authorized read-only access to these three Aja files on drive E:.
No private collection was searched. The CUE, DFF and ISO were actually opened locally.

| Input | Actual bytes | Observed format |
| --- | ---: | --- |
| Steely Dan - Aja.cue | 584 | UTF-8-compatible CUE, seven AUDIO tracks |
| Steely Dan - Aja.dff | 1,679,139,970 | DFF, uncompressed `dsd_msbf`, DSD64 2,822,400 Hz, stereo; native payload duration 2379.733333333 s |
| Aja.iso | 1,715,818,496 | 2048-byte SACD image; master TOC v1.20; one TWOCHTOC stereo area, seven tracks, DSD frame format 2 |

Actual backend: `sacd_extract 0.3.9.3-107-g01c90ddafb0256f3eb194d2c62e7ee5ba14b1c12`,
downloaded and run only after explicit owner permission. Archive SHA-256:
`c75f5596070f9fee4f0869cf3d4ebc778ed839c25a4627c17b75feb2c1e860b3`.
Executable SHA-256:
`eeb4b18514ba9cfcb354a9670e7eedf4da646117a4d81edb852e2b9084f92af4`.
No upstream release digest was provided; these hashes record the downloaded bytes.
The binary remains ignored and local; system/PATH configuration was not changed.

The real ISO passed bounded master/primary-area checks. Its primary stereo TOC is
at sector 544, length 8 sectors; audio sector range 624–837721 is inside the actual
837802-sector file. Native rate code 4 and frame format 2 establish the reported
DSD64/DSD area metadata. `-P` independently enumerated the same seven stereo tracks.
No multichannel area exists in this supplied image. DST decompression was not tested
on a real DST recording: this actual image reports uncompressed DSD.

## Seven independently enumerated tracks

Seconds below are derived from the actual CUE integer 75-fps indexes/source EOF and
the actual backend TOC timecodes. The FILE WAVE token did not override the probed DFF.

| Track | CUE/DFF start s | CUE duration s | ISO start s | ISO duration s |
| --- | ---: | ---: | ---: | ---: |
| 1 Black Cow | 0.000000 | 307.986667 | 2.000000 | 307.986667 |
| 2 Aja | 307.986667 | 475.013333 | 311.133333 | 475.013333 |
| 3 Deacon Blues | 783.000000 | 453.426667 | 786.640000 | 453.426667 |
| 4 Peg | 1236.426667 | 236.800000 | 1242.666667 | 236.800000 |
| 5 Home At Last | 1473.226667 | 331.666667 | 1479.933333 | 331.666667 |
| 6 I Got The News | 1804.893333 | 303.053333 | 1813.400000 | 303.053333 |
| 7 Josie | 2107.946667 | 271.786667 | 2119.906667 | 271.800000 |

The two source timelines differ. The last CUE track ends at the actual DFF EOF.
No source equivalence, native-bit identity or mastering identity comparison was made.
Matching rates or selected-track durations are not reported as identity evidence.

## Selected-track analysis actually executed

- CUE/DFF Peg: full selected-track DSD decode **Passed**, 236.800000 s.
- ISO Peg: actual single-track native DSF extraction plus full DSD decode **Passed**,
  236.800000 s. This is actual backend execution, not a mocked enumeration test.
- Current-version validation tool: CUE/DFF Josie full decode **Passed**,
  271.786666667 s; 12.664 s observed wall time, 191774812-byte temporary native DSF.
- Current-version validation tool: ISO Black Cow extraction/full decode **Passed**,
  307.986666667 s; 12.250 s observed wall time, 217317695-byte temporary native DSF.
- Every representation above was created only in an owned OS temporary directory and
  removed after analysis. Source offsets and track-relative measurement scopes were
  retained. Only native DSD representations precede the existing DSD-to-PCM pipeline.

Wall times are single local observations, not a speedup or diverse-corpus performance
claim. Selected tracks are materialized even for Quick windows; no whole ISO is
permanently converted. Native source identity/mastering comparisons remain outside scope.

The reproducible opt-in tool is `tools/validate_sources.py --cue PATH --iso PATH
--cue-track 7 --iso-track 1`. It writes metadata/analysis JSON only to ignored `data/`.
It computes source SHA-256 before/after the actual checks. Results were:

| Source | SHA-256 before = after | Size/mtime unchanged |
| --- | --- | --- |
| CUE | `f72a2c10785ea42b28cb00f6088ad4b6088518e63b9a141290a992b2b4a55987` | Yes |
| DFF | `2ab6d866aabbd7705f1db667b7cd0c2fa96d8ea097e5ff400f9172c0170cce6d` | Yes |
| ISO | `6012d1155907d1bfd39b26803c865b26bb4e5078f0dbf4a99ea67aff452ecbc1` | Yes |

## Automated and rendered checks

Baseline was actually executed with the existing real DSF fixture enabled:
**319 passed, 0 failed, 1 SACD skip; 124.63 s**. Final full run with both real fixtures
enabled: **359 passed, 0 failed, 0 skipped; 124.94 s**. Ruff check, Ruff formatting
(94 Python files) and compileall passed. The machine-readable snapshot records these
executed results. Earlier failing layout assertions and malformed-input checks were
corrected and are included in this final passing run.
After an additional logical-track reference-scope guard, the affected UI matrix passed
again: **29 passed, 0 failed; 31.94 s**. The guard prevents running the ordinary-file
reference comparison on an entire original album instead of the selected track.

New generated controls cover single/multi-file CUE, MM:SS:FF conversion, INDEX00
allocation, unknown/out-of-source/end boundaries, UTF-8/UTF-16/CP1251 and Unicode,
missing/ambiguous/escaping references, malformed encoding/directives, repeated-file
overlap prevention, exact WAV/FLAC selected samples after seek and fractional CD-frame
boundaries, native DSF MSB/LSB and DFF packed-bit preservation across blocks, cache
track/fingerprint separation, cancellation/disk budget and cleanup after decoder,
extra-output and invalid-output failures.

Generated/mock SACD checks cover stereo/multichannel metadata, DSD/DST recognition,
invalid ISO bounds, missing/incompatible backend, incomplete print protocol and safe
failure cleanup. These do not validate real multichannel/DST audio. The former
unconditional SACD skip now becomes an opt-in real end-to-end test when
`MUSIC_PROJECT_SACD_FIXTURE` is explicitly set. It ran against Aja in the final matrix.

AppTest covers album browsing, explicit selection before analysis, selected-track
coverage, hidden stale results after track changes, unchanged data/backend-free view
switches, codec/container distinction, selected DSF duration versus secondary estimates
and an actionable missing-backend message. Old layout-specific card assertions were
updated to check the requested compact identity and retained evidence instead.

An actual local Streamlit server returned healthy. Installed Edge rendered ordinary
FLAC Everyday/Expert and real Aja CUE/ISO selectors and track results. DOM checks found
Technical Findings and the selected Black Cow title for each album source, with zero
app exceptions/alerts. Screenshots were inspected. No browser sandbox was disabled.
Screenshots/DOM text remain ignored under `data/source-browser/`. This is rendering
evidence, not a human comprehension or accessibility study.

## Scope boundaries

Verified: supplied uncompressed stereo DFF/CUE and readable uncompressed stereo SACD
ISO; actual selected-track extraction/full decoding; synthetic WAV/FLAC intervals and
native DSF/DFF copying; ordinary PCM/DSD regressions and browser startup/rendering.

Not validated: real DST decompression, real multichannel SACD signal analysis, raw or
encrypted images, backup-only/damaged TOCs, all extractor forks/print encodings,
all PCM codecs/layouts through CUE, lossless identity between the ISO and DFF, or any
historical source/mastering hypothesis. DSD signal applicability remains mono/stereo;
multichannel metadata tests do not claim multichannel scientific validation.
External-reference comparison for logical tracks is explicitly Unsupported; ordinary
file reference comparison remains available.

Temporary PCM selection is not original album FLAC MD5 verification; track decoding
is not whole-album integrity verification. Header validation is not a full ISO audit.
Inherited Origin research limitations and full ITU/EBU conformance gaps remain.

Before v1.0: wider real DST/multichannel/backend corpus, timing/encoding variants,
human/accessibility and distribution matrices, asynchronous UI cancellation and
commercial dependency/installer/update/license audits remain. Other roadmap work is
unchanged. No Library/Duplicates/Compare/Archive redesign, no Collection DNA2, no push,
no recording upload/commit, and no v1.0 declaration occurred.
