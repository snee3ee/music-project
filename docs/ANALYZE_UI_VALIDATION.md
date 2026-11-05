# Analyze File restructuring — verification, 2026-11-05

Application remains **0.2.1**; numerical methods remain **2026.11-v3** and
**dsd-2026.11-v1**. This milestone changes presentation and project policy, not DSP
thresholds, decoder settings, database schema or unrelated page behavior. Existing
uncommitted work from the previous milestone was retained.

## Information architecture

One persistent selector renders only the chosen module:

| Module | Content |
|---|---|
| Overview | Format, sourced duration, size, channels, rate/depth/family, derived nominal bitrate, concise verification/measurement status |
| Signal Integrity | Container versus decode status, whole/partial scope, intervals, warning/fatal counts and independent duration observations |
| Spectral & Level Measurements | PCM LUFS/True Peak/LRA/peaks/RMS/crest, PSD/spectrogram/preview, or converted DSD band powers and optional PSD |
| Provenance Evidence | Measured observations, rule interpretation and deduplicated limitations; historical origin remains not established |
| DSD Diagnostics | Conditional native properties, validation, actual PCM conversion header/rate/backend, audible/ultrasonic charts and Unknown historical source |
| Technical Appendix | Organized numerical results, full spectral tables, saved diagnostics, methods/commands, raw ffprobe, exact JSON and exports |

Only one configuration expander remains on the analysis page. Result modules have no
nested expanders. Native Streamlit controls, metric cards and measurement plots are
used; no CSS, decorative scores or global quality rating. Russian is the primary UI
language. ONLY FACTS. NO OPINIONS. was appended to AGENTS.md without removing guidance.

Presentation logic is separate: `analysis_presentation.py` contains pure transformations;
`analysis_views.py`, `analysis_charts.py`, `analysis_appendix.py` and the restructured
`dsd.py` render existing results. Warning groups remove volatile backend addresses for
deduplication, retaining original text, counts and affected intervals. Missing backends
and cancellation are not counted as fatal decoder errors. PCM prefix decoding and
full loudness measurement are not advertised as an independent full-integrity check.

Chart units remain explicit: **FS²** for band power, **FS²/Hz** for PSD, their defined
10-log dB forms, and separate dBFS/dBTP/LUFS for level meters. Unsupported whole bands
have no plotted values. Exact zero is −infinity, with no invented plot floor for DSD.
Band plots use actual per-channel points, without smoothing/interpolation. PCM
spectrogram floor and color limits are explicitly disclosed. Precise linear values
remain in the appendix/JSON rather than being rounded to false zero on the main page.

## Actual real-file validation

Exactly one real audio path was supplied by the owner. Both task-text attachments
are identical, not two audio fixtures. No other personal directory was searched.
Only the explicitly named **02. The Pink Panther DSD 256fs - 2ch.dsf** was read.

| Property | Observed / verified value |
|---|---|
| Container / codec | DSF / dsd_lsbf_planar |
| Native rate / family | 11,289,600 Hz / DSD256 |
| Channels | 2, stereo |
| Native nominal bitrate | 22,579,200 bps, derived from rate × channels |
| File size | 665,751,644 bytes / 634.910244 MiB |
| Declared samples/channel | 2,642,067,456 one-bit samples |
| DSF sample-count duration | 234.026666667 s |
| ffprobe estimated duration | 235.881361 s |
| Full decoded PCM duration | 234.026666667 s at both PCM rates |
| Container check | Passed |
| Historical source | Unknown / Ambiguous |

Local FFmpeg/ffprobe **9.0.2** actually executed:

| Mode / PCM output | Integrity | Decoded duration | Warnings / fatal errors | Observed runtime |
|---|---|---:|---|---:|
| Quick / 352800 Hz | Partial | 15.000000 s, three deterministic windows | 3 / 0 | 1.092 s |
| Full / 352800 Hz | Passed, EOF | 234.026666667 s | 1 / 0 | 8.374 s |
| Full / 176400 Hz | Passed, EOF | 234.026666667 s | 1 / 0 | 5.996 s |

Each run validates actual float PCM output rate/channels. The repeated warning is
“Estimating duration from bitrate, this may be inaccurate.” Quick displays one grouped
message with three events and interval references; original messages remain intact.
Container-duration warnings remain separate from decoder warnings.

**Duration discrepancy:** DSF audio starts at byte 92; padded audio payload is
660,520,960 bytes. Its valid sample-count payload is 660,516,864 bytes; the remaining
4,096 bytes are block padding. The metadata pointer is at byte 660,521,052, followed
by a 5,230,592-byte metadata tail. For this file:

```text
(file_size − 92) / (native_rate × channels / 8)
    = 235.881360544 s
declared_sample_count / native_rate
    = 234.026666667 s
decoded_PCM_frames / verified_PCM_rate
    = 234.026666667 s
```

The ffprobe estimate numerically includes all bytes after the header, including
metadata and padding. The UI uses the sourced container duration in Overview and
shows all three observations in Integrity. The metadata estimate is not treated as
corruption. No exact foobar2000 value/version was supplied, so that player comparison
was not reproduced. None of these results establishes native DSD recording history.

PSD and band powers were produced on both rates. At 176400 Hz, 80–100 and 100–140 kHz
whole bands are Unsupported with no values; at 352800 Hz those bands are measurable
in converted PCM. For example, full 352800-Hz conversion gives 20–30 kHz powers of
−85.5611/−87.4888 dB re FS² (L/R), difference 1.9277 dB. This is converted-signal power,
not a quality score, acoustic SPL, musical-information verdict or native-bandwidth proof.
The composite conversion response remains Not validated.

Original size and mtime_ns were unchanged after validation. The code opens the source
read-only and emits PCM to a pipe. No original was copied, renamed, edited or uploaded.
Full local JSON reports are under ignored `data/real-dsd-validation/`; private absolute
paths and tags are not copied into this tracked report.

## Executed automated checks

- Relevant baseline before restructuring: **66 passed, 1 skipped**, 12.51 s.
- Full regression with the explicitly supplied `MUSIC_PROJECT_DSD_FIXTURE`:
  **196 passed, 0 failed, 1 skipped**, 35.90 s; 197 collected. The real DSD256 test
  passed. The sole skip is the existing unavailable real SACD fixture/backend test.
- Final focused verification after appendix presentation changes: **28 passed**,
  15.83 s (UI and pure presentation tests); final Ruff check/format and compileall passed.
- New/updated UI and presentation checks exercise WAV/FLAC, conditional modules,
  quick/full DSD, every appendix section, exact export preservation, short/silent
  semantics, grouped warnings, unavailable bands and failure categories.
- Navigation tests replace analysis/decoder functions with failing sentinels after
  analysis: switching modules does not call them. Separate counted PCM spectrum and
  spectrogram functions each execute **once** across repeated module/toggle changes.
- All six modules and appendix sections were additionally exercised using each of the
  three actual real-file reports, with exact JSON equality and **zero additional decodes**.
- Full Ruff check/format, compileall and pip check executed. Actual Streamlit startup:
  `/_stcore/health` and `/analyzer` returned HTTP 200; the test-owned server was stopped.
- Actual headless Edge screenshot attempt failed before capture with unusable-GPU
  errors. Browser appearance, desktop layout and accessibility are **not visually
  verified**. AppTest checks actual rendering commands and behavior, not browser pixels.

No general speedup or reduced-scroll percentage is claimed. The numerical pipeline
is unchanged; navigation reads saved results and lazily renders the selected module.
The real-run timings above are observations on this machine, not a cross-version
benchmark or throughput guarantee. Large decoded audio is not newly retained for charts.

Repeat from the project root:

```powershell
$env:MUSIC_PROJECT_DSD_FIXTURE = 'E:\your-explicit-folder\02. The Pink Panther DSD 256fs - 2ch.dsf'
.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:MUSIC_PROJECT_DSD_FIXTURE
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m streamlit run app.py
```

Use **Analyze File → choose file → configuration → Analyze**, then switch modules.
Choose Full to request complete stream verification. Raw warnings, exact values and
JSON download are in Technical Appendix. Existing library/duplicates/compare/archive/
tools workflows and schema remain unchanged by this UI task.
