# Lossy source investigation — executed validation, 2026-11-12

Application0.2.5.dev0; general method2026.11-v9; lossy-investigation-2026.11-v1.
[Method and numerical limits](LOSSY_METHODOLOGY.md) ·
[Persistent plan](LOSSY_IMPLEMENTATION_PLAN.md) ·
[Executed machine-readable snapshot](LOSSY_VALIDATION.json).

## Implementation and changed files

| Files | Change |
| --- | --- |
| `core/lossy_models.py` | Typed measurements/interpretation/scope contract; four classification states, explicit unknown codec/authenticity |
| `core/lossy.py` | Bounded native PCM collector, deterministic window selection, eligibility, measured band/candidate/time evidence, abstention; prefix fallback |
| `core/lossy_spectrum.py` | Adaptive FFT-bin candidate discovery and band-energy/PSD-floor quantiles |
| `core/origin_features.py` | Reuse existing boundary mathematics with optional candidates/rule parameters; original defaults unchanged |
| `core/technical_analysis.py`, `core/analysis.py` | Consume existing native float64 decode; no extra decoder. DSD explicitly Not evaluated; failed technical pass may reuse existing prefix |
| `core/conclusion_lossy.py`, `core/conclusions.py` | Scoped formal conclusion from saved investigation; no loudness/integrity/upsampling inputs |
| `music_project/__init__.py` | General methodv9 invalidates stale cached/index results; application version unchanged |
| `ui/lossy.py`, `ui/origin.py` | Existing Normal/Expert Origin view; per-band/candidate/channel/window/method evidence. Inapplicable older sample-rate hypotheses remain exported and are not shown as six identical rows |
| `tests/test_lossy.py`, `tests/test_lossy_ui.py` |26new measurement, actual encoder, scope, temporal, deterministic, abstention, identity and UI/export tests |
| `tests/test_results_first_ui.py` | Update hierarchy assertion: new meaningful PCM investigation replaces inapplicable generic source-rate summary |
| `tools/lossy_dataset.py`, `tools/validate_lossy.py` | Deterministic original controls, actual local encoders, A/B/C/D matrix and exploratory metric feasibility |

Paths in the table are relative to `music_project/` for core/ui files. README, technical
methods, supported-format scope, development/progress ledgers and these reports are
updated. Other UI pages, source-file decoders, FLAC digest math, bit-depth analysis,
DSD conversion filters, existing Origin hypothesis rules, loudness and True Peak
algorithms are preserved. New PCM investigation does not depend on Hi-Res status.

## What the rules actually establish

Measured properties: per-channel spectral energy/fractions, median/q10/q90density,
local attenuation/slope/transition width, energy above candidates, distance to Nyquist,
reference occupancy, temporal energy variability/concentration and same-frequency
recurrence across selected windows. FFT spacing, support bands and exclusion reasons
are inspectable. Observational thresholds and retention are explicit in the method.

No validated additional family uniquely separates the tested histories. Consequently
a spectral observation yields **Inconclusive**, preserving the measured facts and
the filtering alternative. Adequate tested support with no evaluated observations
yields **No evaluated indicators detected**, not original-lossless certification.
Insufficient/unsupported input yields **Not evaluated**. **Indicators detected** is
reserved for a future independently validated historical-coding rule; this version
does not emit it. Exact codec/encoder/bitrate, authenticity and provenance probability
are not inferred. MD5, LUFS, peaks, rails and limiting are not classifier inputs.

## Controlled population:106 synthetic cases, no recordings downloaded

All references originate from deterministic NumPy signals (seed12026),12seconds,
mono/stereo as specified. Content families are broadband plus time-varying tone,
sparse sustained tones, and gated broadband transients. Unit controls additionally
use independent seeds, noninteger FIR cutoffs, short/silent/nearly silent signals,
changed temporal regions and rates32/44.1/48/88.2/96/176.4/192kHz.

| Group | Cases | Contents / known history | Spectral observations | Recurrent observations |
| --- | ---: | --- | ---: | ---: |
| A |22| Original PCM, FLAC and WAV round-trips;16/24-bit,44.1/48kHz, three content families |0|0|
| B |40| Actual reference→MP3/AAC→FLAC; both rates and all three contents; MP3 96/128/320kbps, AAC96/128/256kbps; additional independent-stereo MP3 and fast AAC configurations |25|25|
| C |20| No perceptual encoder: FIR band-limit, Bessel analog-style filtering, EQ, high-frequency-poor filtering, limiting, clipping, noise, mono, linear-phase filtering; polyphase PCM resampling to96/192kHz |4|4|
| D |24| Known MP3/AAC128 histories followed by gain, EQ, dynamics, resampling, mild filtering or added noise; both input rates |24|22|

Actual local FFmpeg9.0.2 encoders and alternative configurations were queried and
executed; **0 corpus cases skipped**. The report records executable versions,
parameters/history, output hashes, observations, scope and classifications. Encoder
availability is not assumed; absent encoders/configurations are recorded as skipped.
These106cases share a small set of synthetic references and are not independent real
music recordings, a held-out corpus or a calibration population.

Bitrate values above are requested encoder targets, not a claim that every AAC output
has exactly that measured average bitrate. They are never inferred for the user's file.

### False positives, false negatives and abstention

If bandwidth observation alone were wrongly treated as a historical lossy classifier:
**49/64 known-lossy cases trigger**, **15/64 do not**, and **4/42 non-lossy cases trigger**.
Those are empirical proxy trigger rates on this population, **not** deployed codec
decisions, confidence or real-world accuracy. The four negative triggers are the
FIR/linear-phase low-pass controls at44.1/48kHz; no perceptual encoder was used.

Known-history Group B observations by codec/bitrate:

| Encoding history | Triggered / cases |
| --- | ---: |
| MP3 96kbps |4/6|
| MP3 128kbps, including alternative configuration |6/8|
| MP3 320kbps |4/6|
| AAC 96kbps |4/6|
| AAC 128kbps, including fast coder |6/8|
| AAC 256kbps |1/6|

Sparse tonal controls often lack eligible excitation and remain inconclusive. High-rate
AAC histories can lack evaluated sharp features. Non-lossy filtering can reproduce
them. Processing tests do not establish survival under arbitrary transformations:
recurrence was lost in one44.1kHz AAC dynamics control and one48kHz MP3 added-noise
control. Some retained features may arise from later processing rather than encoding.
The frequency-specific evidence remains available instead of claiming codec identity.

Production classifications over the106cases: **71 Inconclusive**, **35 No evaluated
indicators detected**,0strong historical indicators. Short/unsupported Not evaluated
behavior is exercised by the separate regression controls. No threshold was adjusted
against the user's file, loudness or listening impression.

## Additional metric feasibility

Positive spectral flux and local pre/post-energy ratios were actually computed in the
validation tool, not added to production classification. On this106-case population,
39/42negative flux values lie inside the positive min/max range;41/42negative local
energy ratios lie inside the positive range. Distributions are retained in JSON.
This overlap and the onset/content/filter ambiguity do not support a diagnostic codec
threshold. The energy ratio is not a validated pre-echo detector; exact onset/reference
alignment is not authenticated. Arbitrary transform patterns, coding noise and MP3
frame detection from decoded PCM are intentionally unsupported.

## Actual authorized “Tochki” file

Read only: `C:\Users\kalos\Downloads\VA - Music History - Russian Rock [7].flac`.
Actual size18,967,763bytes; duration140.293333s; FLAC16-bit44.1kHz stereo. The user
identified the musical content; no authenticated encoding history was supplied.

| Actual observation | Result |
| --- | --- |
| Spectral sampling |32windows,64.00s total;32eligible,0discarded;38other full2s slots not selected |
| Adaptive candidate |21425.537109375Hz;624.462890625Hz below Nyquist |
| Global median side-band contrast, L/R |40.0056 /33.2365dB|
| Maximum measured window contrast, L/R |50.5152 /50.4208dB|
| Temporal recurrence, L/R |32/32eligible windows each|
| Encoding-history result |**Inconclusive**; codec Unknown, authenticity Not established|
| Integrated /LRA |−6.978LUFS /5.29LU|
| Sample Peak /True Peak |0.00dBFS /+0.742088dBTP|
| RMS /Crest |−10.083410dBFS /10.083410dB|
| Digital-rail samples |37left+158right=195|
| Native FLAC MD5 |Verified after actual full decode|

This is an observed near-Nyquist spectral decline; it does not establish a preceding
MP3/AAC encoder or distinguish anti-aliasing/mastering filters. Grid resolution is not
total uncertainty in a physical filter cutoff. No provenance probability is supplied.
The loudness/peak observations agree with the supplied numbers after rounding but do
not contribute evidence of lossy encoding. Source SHA-256 and size/mtime match before
and after analysis; final post-UI hash preservation is recorded in the snapshot.

Actual complete analysis under tracemalloc took11.051s, Python allocator peak120.675MiB,
excluding backend/RSS. This includes the existing PCMContext/Origin/technical pipeline,
not just the added collector. It is one observed desktop run, not a general latency or
whole-process memory guarantee. Spectral sampling/storage stay bounded at32windows;
the full decoder already reads the stream for existing integrity/metering.

## Regression, rendering and unavailable checks

Fresh baseline:418passed/1failed in137.34s; the failure was an unavailable old Aja ISO
fixture path (WinError3). An intermediate complete run passed444tests with1explicit
real-SACD skip in149.24s. After the final UI applicability correction,9relevant UI tests
passed in9.48s. Final complete results and static checks are recorded in the snapshot.
The actual real DSF test is enabled; this task does not revalidate an unavailable ISO.

Final full regression: **444 passed,0failed,1skipped;142.14s**. After the last caption
clarification distinguishing maximum window contrast from aggregate contrast,
**9 UI tests passed in15.38s** and the supplied-file browser views were rerun and
inspected. Ruff/format113Python files, compileall, pip check and47core imports passed.
Startup root and health both returned HTTP200. Standard Git LF/CRLF notices were not
whitespace failures; Git settings were not changed.

Final plot review labels the existing PCM spectrum's actual prefix scope and hides its
inapplicable timeline candidates; full original data remain exported. The applicable
Origin/results-first/lossy UI matrix then passed9tests in9.45s. The final real-file plot
was rerendered/inspected, and original SHA-256/stat were checked again afterward.

AppTest exercises all four Expert evidence sections/exports with subprocess launching
forbidden and the saved Analysis unchanged. Existing FLAC/DSD/Hi-Res/scope/Library/
Compare/Archive tests remain. Exact returned JSON has finite/null nonfinite states.

Local Edge at1600×1100 with its browser sandbox enabled actually rendered original
lossless FLAC, known MP3 transcode, lossless filtering, short silence, the authorized
FLAC and real DSF. Inspected Normal results and the real file's Expert bands,
candidates, windows, methods and existing Origin spectrum are stored in ignored
`data/lossy-rendered/`. Main views have no raw JSON or application exception. No new
mobile/accessibility/human usability or complete standards claim is made.

The restricted terminal initially prevented Edge's GPU subprocess from starting;
an authorized local rerun kept browser sandbox enabled. Temporary harness Unicode
encoding/selectbox-wait issues were corrected. Those are browser-test limitations,
not decoder outcomes. Only owned validation server/browser processes were closed.

## Reproduce and inspect the supplied file

```powershell
# Existing repository virtual environment; no new packages or recordings needed.
.venv/Scripts/python.exe -m tools.validate_lossy --output data/lossy-validation-final
.venv/Scripts/python.exe -m pytest -q tests/test_lossy.py tests/test_lossy_ui.py

# Full regressions; enable real fixtures only if currently accessible and authorized.
$env:MUSIC_PROJECT_DSD_FIXTURE = (Resolve-Path -LiteralPath 'test_audio/02. The Pink Panther DSD 256fs - 2ch.dsf').Path
Remove-Item Env:MUSIC_PROJECT_SACD_FIXTURE -ErrorAction SilentlyContinue
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check music_project tests tools
.venv/Scripts/python.exe -m ruff format --check music_project tests tools
```

Start with the existing launcher. Analyze File→select the authorized FLAC→Analyze.
Origin Investigator→“Предыдущее lossy-кодирование · исследование” shows actual scope,
candidate and abstention. Expert→“Свидетельства lossy-исследования” offers bands,
transitions, windows and methods. Existing Spectrum & Levels retains spectra/spectrogram.
Technical Appendix retains full JSON and original evidence. Switching views reuses saved
facts. A technical prefix choice limits the investigation explicitly; use Full PCM scope
for the default full-stream integrity check and multi-region sampling over the file.

No source audio was overwritten, uploaded, transcoded into the repository or committed.
No dependencies/executables were installed, no visual identity/framework was changed,
and no push/version1.0 declaration occurred. Remaining needs include a diverse held-out
labelled music corpus, independent artefact families with demonstrated specificity,
broader encoder/rate/DSP testing and full metering/DSD release validation.
