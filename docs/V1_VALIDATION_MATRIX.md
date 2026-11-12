# Engineering validation matrix — 2026-11-11

Application **0.2.5.dev0**, general method **2026.11-v8**, DSD **dsd-2026.11-v3**,
PCM metering **technical-pcm-2026.11-v2**. Origin v1, conversion response v1,
conclusions v1, logical-source v1 and duration policy v1 remain unchanged.
This session does not declare v1.0 complete. The results-first UI is retained.

[Persistent milestone record](V1_ENGINEERING_PROGRESS.md) ·
[Machine-readable executed results](V1_VALIDATION.json).

Fresh baseline: **364 passed, 0 failed, 0 skipped;137.34s**. Final regression:
**419 passed, 0 failed, 0 skipped;136.95s**, real DSF/SACD enabled. Added55 ground-truth
and adversarial cases. Ruff/format104files, compileall, pip check and43core imports
passed. Streamlit root/health returned HTTP200. The JSON records exact runtime inputs,
hash preservation, numerical scope, test results and unavailable validation.

## Confirmed defects corrected

| Trigger | Previous behavior | Corrected behavior | Regression |
| --- | --- | --- | --- |
| Missing/duplicate/late/short DFF FVER, late sound properties, truncated counted CMPR name, too-short PROP | Structurally invalid generated files could report Passed; unknown main version also Passed | Bounded mandatory version/order/name checks; invalid is Failed, unknown major version Unsupported; compatible unknown extensions skipped | `test_v1_structure.py` |
| Larger spectral ratio fails an excitation or upper-level guard, another candidate passes all guards | Valid boundary could be hidden by ranking before applicability | Evaluate every candidate against all original guards, then select strongest passing candidate; retain all candidate values | `test_v1_forensics.py` |
| Alternating grid/off-grid samples exceed entropy budget | Stride2 sampled only grid-compatible positions | Exact grid/zero-byte fraction checks every active decoded-prefix sample; entropy/distinct counts remain bounded and explicitly sampled | `test_v1_forensics.py` |
| Prefix ends at2.05s with louder audio immediately afterward | Output `-t` allowed metering metadata through2.20s | Native sample trim before ebur128; metadata agrees with a physically terminated prefix fixture | `test_v1_metering.py` |

No threshold was tuned against the supplied music. The spectral guard values remain
experimental; the corrected search does not turn compatibility into provenance proof.

## Capability and scientific limits

| Area | Actually executed evidence | Status and limit |
| --- | --- | --- |
| Lossy-to-lossless history | Existing actual MP3 128/320→FLAC controls; three-seed sharp lossless-filter counterexamples | Spectral boundary observation tested. Historical codec classification **Experimental / Unknown**; lossless filtering can produce the same feature |
| PCM upsampling | Three seeds: sharp FFT positive controls, full-band negatives, broad polyphase and noise-masked known-upsample counterexamples | Discriminates selected sharp bandwidth changes; cannot identify historical source rate. Failed detection does not exclude resampling |
| Spectral boundaries | Existing six-candidate Origin controls; new competing-candidate adversaries and all original thresholds | Measured local contrast, not a physical source/filter identity; finite resolution/excitation guards apply |
| Padding/quantization | Known integer16→24 padding, off-grid/random24, gain/filter/dither, stereo, small/silent and periodic-budget controls | Exact grid over decoded prefix; sampled entropy/unique values. Dithered known16-bit origin has high entropy, so native24 history remains Unknown |
| Native DSD / ultrasonic behavior | Existing direct-bit LSBF/MSBF DSF/DFF PSD versus independent SciPy, tone/band power checks, synthetic regime counterexamples | Native measurements distinct from conversion. Regime changes do not identify previous DSD rate or conversion chain |
| DSD conversion response | Actual installed converter controls and existing independent Kaiser polyphase comparison | Discrete point response and selected passband agreement; no continuous passband, professional-modulator or historical-origin certification |
| DSF duration/full decoding | Actual Pink Panther DSD256 full EOF at176400 and352800Hz | **Verified234.026666667s** at both; secondary ffprobe235.881361s retained with warning |
| DFF structure/native rate/duration | Adversarial mandatory chunks plus real stereo DSD64 Aja DFF through CUE | Required structure/rate/payload checks and actual selected-track decoding. Complete optional metadata/artwork audit not claimed |
| CUE single/multi-file | Existing single/multi-file/index/encoding/path tests plus exact native selected samples at32/44.1/88.2/96kHz for FLAC/float64 WAV | Implemented and tested. Native DSF/DFF copy retains bit order/channel order; explicit unsupported references are not guessed |
| Actual Aja CUE/DFF | Seven Ready tracks; selected track4 Peg fully decoded236.8s | Real end-to-end stereo uncompressed DSD64. Other six tracks enumerated, not all decoded by this session |
| Actual Aja SACD ISO | Master/stereo area checks, seven tracks, actual backend extraction and full Peg decoding236.8s | Real end-to-end uncompressed stereo DSD64; no audio/mastering identity comparison against DFF |
| SACD DST/multichannel | Existing generated headers/mocked adapter/error-cleanup tests only | Metadata/protocol coverage; **real DST and multichannel signal validation unavailable**. Native DFF DST reader remains Unsupported |
| Integrated LUFS / LRA | Independent test-only published48kHz K-weighting/gating/percentile calculation; broadband, gated/level-varying, anti-phase and5.1/LFE signals | Fixed tolerances0.15LU Integrated/0.25LU LRA passed. Full ITU/EBU certification, other independent rates and terminal-silence convention remain unvalidated |
| True Peak / Sample Peak / RMS / Crest | Existing30 analytical TP configurations across six rates versus independent32× reconstruction; new exact numerical peak/RMS/Crest checks | Selected TP tolerances retained (analytical−0.4/+0.2dB, independent0.4dB); sample/RMS/Crest controls within1e−10dB. Other TP rates remain Not validated |
| Native FLAC MD5 | Independent RFC9639 verbatim8/16/24/32-bit mono/stereo fixtures, actual FFmpeg decode, exact known PCM and signed-byte MD5, missing/mismatched/partial digests | Byte-aligned four depths now validated. Other depths/wrappers not validated; embedded digest does not authenticate external history |
| Incomplete FLAC | Whole valid frame removed at a clean EOF, original declared count/digest retained | Count check fails even if decoder reaches EOF without a damaged frame; decode/digest/count statuses remain separate |
| Engineering behavior | Existing Unicode, missing backend, timeout/cancellation, bounded stdout/stderr, cache identity/method invalidation and future-schema/index tests | Applicable regression coverage; no universal backend, database concurrency or large-library guarantee |
| Streaming observation | Generated20s and240s stereo24-bit PCM; actual streaming metering with tracemalloc |240s input65.918MiB; Python allocator peak13.948MiB,1376 retained rows per timeline. Excludes FFmpeg/RSS; one session, no general RAM/speedup claim |
| Analyze File / startup | Actual FLAC and real DSF AppTest analyses; both modes/modules with subprocess launching forbidden; HTTP startup checks | Both decode checks Passed; saved results unchanged; zero app exceptions; local root/health HTTP200. AppTest is not a new visual/usability study |
| Library / Compare / Archive / Duplicates | Existing regression suite and page tests retained | No page redesign or source changes in this session; collection-scale profiling remains open |

## Real sources, warnings and preservation

Only the specifically authorized Pink Panther DSF and Aja CUE/DFF/ISO were accessed.
Every original source SHA-256 and size/mtime signature matched after the dedicated
real-file checks. Sources were not opened for writing or uploaded. Large original
recordings were not copied into the repository. Existing selected-track temporary
representations were removed by the pipeline.

Pink Panther full decoding retains the nonfatal FFmpeg warning:
`Estimating duration from bitrate, this may be inaccurate`.
Its declared/decoded234.026666667s agree; the235.881361s estimate is secondary.
The previously established metadata/padding explanation is retained; no new corruption
or recording-history conclusion is inferred. No fatal error occurred in these full
decodes. The used FFmpeg/ffprobe build reports9.0.2; actual sacd_extract listing identifies
the already authorized portable0.3.9.3-107 backend. No new executable was installed.

## Reproduce locally (PowerShell)

Use only paths whose owners have authorized local read access. Run from repository root;
all generated outputs below are ignored under `data/`. No command uploads or commits audio.

```powershell
# Current full regression, including the explicitly authorized real fixtures.
$env:MUSIC_PROJECT_DSD_FIXTURE = (Resolve-Path -LiteralPath 'test_audio/02. The Pink Panther DSD 256fs - 2ch.dsf').Path
$env:MUSIC_PROJECT_SACD_FIXTURE = 'E:\Music (Hi-Res)\Steely Dan\Aja.iso'
.venv/Scripts/python.exe -m pytest -q --junitxml=data/v1-validation/pytest-final.xml

# Independent controls only, without private audio.
.venv/Scripts/python.exe -m pytest -q tests/test_v1_forensics.py tests/test_v1_metering.py tests/test_v1_flac.py tests/test_v1_structure.py tests/test_v1_sources.py

# Full native DSD pipeline at both actual output rates; stores measurements/hash checks.
.venv/Scripts/python.exe tools/validate_dsd.py 'test_audio/02. The Pink Panther DSD 256fs - 2ch.dsf'

# Actual catalogs and selected native tracks; preserves the older validation directory.
.venv/Scripts/python.exe tools/validate_sources.py --cue 'E:\Music (Hi-Res)\Steely Dan\DSD DFF\Steely Dan - Aja.cue' --iso 'E:\Music (Hi-Res)\Steely Dan\Aja.iso' --cue-track 4 --iso-track 4 --output data/v1-validation/sources

# Generated metering/streaming observations, not a collection-scale benchmark.
.venv/Scripts/python.exe tools/validate_conclusions.py --durations 20 240 --output data/v1-validation/pcm

.venv/Scripts/python.exe -m ruff check music_project tests tools
.venv/Scripts/python.exe -m ruff format --check music_project tests tools
.venv/Scripts/python.exe -m compileall -q music_project tests tools
```

In the application, select a DSF/DFF under Analyze File and choose Quick or Full.
For CUE/ISO, select the album/image, inspect actual catalog/area/track status, choose one
available track and run analysis. Integrity Full refers to that selected track, not the
whole DFF/album/ISO. Methods, native versus converted data, warning logs, JSON and
secondary duration estimates remain accessible in Technical Appendix. Presentation
switches use the saved result. Missing/incompatible sacd_extract reports an explicit
backend limitation; the application does not download a replacement.

## Remaining engineering priorities / unavailable validation

1. Authorized real DST-compressed and multichannel fixtures; broader DFF/DSF optional
   metadata variants, raw/encrypted/damaged SACD images and other backend versions.
2. Independent metering references across rates/layouts and terminal LRA conventions;
   complete standards conformance requires the full relevant reference matrix.
3. Held-out labelled music/filter/modulator corpora and error characterization before
   any broader historical discriminator; current negative results do not prove origin.
4. Real-library scale/RSS, concurrent/crash/cancellation/recovery checks; signed release,
   dependency/backend redistribution audit and Windows distribution validation.
5. Accessibility/mobile/human comprehension tests. No interface redesign was performed.

No missing fixture stopped the independent controls or available real-file checks.
Standalone fpcalc is absent; no acoustic grouping is claimed. No v1.0 advancement,
Git history change or remote push occurred. No new unresolved defect was established
by the completed controls; the listed validation limits remain.
