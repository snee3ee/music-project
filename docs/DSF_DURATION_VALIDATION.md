# DSF duration discrepancy — verified investigation, 2026-11-05

Application **0.2.2**, general method **2026.11-v4**, DSD method
**dsd-2026.11-v2**, duration policy **dsd-duration-2026.11-v1**.
Only the explicitly supplied repository file was investigated. No audio/artwork was
uploaded, copied to a tracked fixture, edited or committed. Existing work is retained.

## Measured file structure

`test_audio/02. The Pink Panther DSD 256fs - 2ch.dsf`, local FFmpeg/ffprobe 9.0.2:

| Field | Observed value |
|---|---:|
| Actual / declared total size | 665,751,644 bytes / 665,751,644 bytes |
| DSD header / fmt sizes | 28 / 52 bytes |
| Native rate / channels | 11,289,600 Hz / 2 |
| Declared samples per channel | 2,642,067,456 one-bit samples |
| Per-channel block size | 4,096 bytes |
| Data chunk offset | 80 |
| Data chunk length, including 12-byte header | 660,520,972 bytes |
| Audio payload start / end | 92 / 660,521,052 |
| Padded payload | 660,520,960 bytes |
| Valid packed audio bytes from sample count | 660,516,864 bytes |
| Declared block padding | 4,096 bytes total, 2,048 per channel |
| Metadata pointer | 660,521,052, exactly at audio end |
| ID3v2.3 tail length | 5,230,592 bytes |
| Embedded APIC front cover | JPEG, 3000×3000, 5,229,518 encoded bytes |

ID3 header bytes: `49 44 33 03 00 00 02 3f 1f 76`. Mutagen independently parses the
tags/APIC and reports audio duration **234.02666666666667 s**. Pillow identifies
the image format/dimensions from its header; no artwork extraction or image-integrity
certification is claimed. Padding is established by sample count and exact block
capacity, not inferred merely from the existence of a duration discrepancy.
Direct reads also confirmed both declared padding regions: offsets 660,514,908 and
660,519,004, each 2,048 bytes, all zero. No original bytes were changed.

## Cause and numerical accounting

Nominal native byte rate = 11,289,600 × 2 / 8 = **2,822,400 bytes/s**.

```text
audio duration = 2,642,067,456 / 11,289,600
               = 234.02666666666667 s

all bytes after audio start / nominal byte rate
    = (665,751,644 − 92) / 2,822,400
    = 235.8813605442177 s
    → ffprobe reports 235.881361 s (rounded)

metadata contribution = 5,230,592 / 2,822,400 = 1.8532426303854874 s
padding contribution  = 4,096 / 2,822,400     = 0.0014512471655328798 s
sum                   = 1.8546938775510203 s
```

Thus the bitrate estimate includes non-audio ID3/artwork and declared block padding.
The warning “Estimating duration from bitrate, this may be inaccurate” accompanies
the observed decode. The displayed difference 1.854694333 s includes rounding of the
six-decimal ffprobe result. Header and full decoded duration agree; these checks
provide no evidence of truncation or a corrupt audio chunk.

Controlled actual-backend regression tests vary only generated ID3 padding (0,
100,000, 500,000 bytes) and presence of a generated JPEG APIC. Across all six cases,
ffprobe's estimate increases by added metadata bytes / native byte rate (within
six-decimal output precision), while native sample count and full decoded duration
remain 0.15 s. This isolates the cause without modifying the real recording.
Direct retrieval of upstream FFmpeg source was unavailable in this session; internal
implementation details beyond these measured backend effects are not asserted.

## Implemented duration policy

`core/duration.py` returns typed `DurationSelection`; primary value/source/status
and secondary evidence are serialized with `AudioInfo`, `Analysis.scope` and
`dsd_duration` findings. Raw ffprobe JSON remains unmodified.

1. Supported structurally valid DSF: sample count / native DSD rate; exclude all
   metadata and declared capacity beyond the sample count. Initial status **Derived**.
2. Supported uncompressed DFF: audio-chunk payload bytes ×8 / channels / native rate;
   exclude other chunks and chunk headers. Initial status **Derived**.
3. Full decode must successfully reach EOF with a validated actual output rate and
   channel configuration. Consistency permits two PCM frames of output rounding and
   only the **exact declared DSF padding duration**, not an arbitrary whole-block allowance.
   A consistent duration is **Verified**; the exact native duration remains canonical.
4. Quick windows, cancelled/failed decodes and unavailable backends never upgrade
   duration to Verified. Sum of quick-window seconds is not a whole-file comparison.
5. A successfully terminated full decode disagreeing beyond the above bounds gives
   **Ambiguous**, with no selected primary duration; both observations remain available.
6. Failed/unsupported structure, unsupported DSD variants and DST do not promote a
   bitrate estimate into audio duration. Primary is Unknown/Unsupported with null
   seconds, and ffprobe's secondary value is retained. DST duration/native rate
   remain unsupported pending a validated dedicated pipeline.
7. PCM behavior is unchanged. Successful DSD decoding does not establish recording
   provenance or independently prove the semantic correctness of an authored sample count.

New AudioInfo fields have defaults for old JSON/SQLite payloads. No database schema
change. Existing records remain readable; the method version causes revalidation on
the next requested scan. Previously stored estimates are not silently rewritten.
Cache keys include the updated method versions. Spectral/provenance thresholds unchanged.

Overview now displays `3:54.03` with a **verified audio duration** label after full
verification, or a calculated label for Quick. Secondary estimates, precise values,
pointer/size evidence and discrepancies are confined to Technical Appendix/JSON.
Unresolved duration is shown explicitly, without fallback to the misleading estimate.

## Executed verification

- Before changes: **73 passed, 1 skipped**, 18.92 s, relevant DSD/UI/presentation tests.
- Full regression with the explicit real fixture: **221 passed, 0 failed, 1 skipped**,
  40.80 s (222 collected). Sole skip: existing unavailable real SACD fixture/backend.
- Final focused duration/UI/presentation tests after presentation cleanup: **53 passed**,
  20.16 s. New coverage includes six actual ffprobe metadata-size controls, exact
  padding/pointer evidence, DFF extra chunks, unsupported DST, invalid headers, failed/
  partial/mismatching decodes, nonfinite numerical guards, old-record loading, library
  duration propagation, primary UI duration and secondary estimates confined to appendix.
- Real full rechecks: 352800 Hz **8.698 s**, 176400 Hz **5.934 s**. Both selected
  **234.02666666666667 s, Verified**, with identical decoded duration; secondary
  estimate remains 235.881361 s. These are run timings, not comparative benchmarks.
- Real-result AppTest: Overview displays `3:54.03`; appendix retains 235.881361;
  no UI errors/exceptions and no additional decoding to present saved results.
- Ruff check/format, compileall and pip check passed. Editable installation and root
  egg-info regenerated; package and installed version both **0.2.2**.
- Actual Streamlit launch: `/_stcore/health` and `/analyzer` returned HTTP 200.
  Test-owned server was stopped. No new browser visual-inspection claim.
- Source SHA-256 before/after:
  `2495ee118c597cb2cb977e83d24c2217ade07dce8aae4f6e67080326f2ab84f3` — unchanged.

Local detailed reports, excluded from Git: `data/dsf-duration-investigation.json`,
`data/dsf-duration-full-352800.json`, `data/dsf-duration-full-176400.json`.
No actual DFF/DST recording was supplied; DFF regression is generated-fixture validation.
