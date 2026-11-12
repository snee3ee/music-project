# Evidence-Based Conclusions Engine — executed validation, 2026-11-10

Development version **0.2.4.dev0**, general method `2026.11-v6`, conclusions
`conclusions-2026.11-v1`, PCM metering `technical-pcm-2026.11-v1`. This report records
executed checks; it does not declare v1.0 or complete ITU/EBU conformance.
[Methods and primary references](CONCLUSIONS_METHODOLOGY.md).
[Machine-readable measurement snapshot](CONCLUSIONS_VALIDATION.json).

## Implementation and scope

- Typed, deterministic conclusions are independent of Streamlit. Statements retain
  measurement paths, numerical inputs/units, coverage, rules/versions, reference,
  applicability, validation and limitations. Invalid/nonfinite values are not numbers
  with which to generate a factual comparison.
- Analyze File now obtains full/prefix Integrated, LRA, Momentary/Short-term extrema
  and curves, native Sample Peak/RMS/crest, per-channel peaks/times, rail observations,
  near-ceiling density and reconstructed peaks in one bounded streaming technical pass.
  The existing spectrum/quantization prefix and separate native DSD pipeline remain.
- TP−Sample Peak, PLR and gain planning check the scopes of their actual components.
  Full loudness is not combined with an unrelated prefix peak. Exact-zero frames are
  distinguished from gated loudness and perceptual silence.
- Custom references calculate loudness difference, linear gain, predicted TP and
  simultaneous ceiling constraints. No reference is selected by default. No audio gain
  or other processing is applied; reference changes require no new decode.
- Origin reports applicable boundaries, measured attenuation, counts/fractions of
  eligible retained cells and existing supported hypotheses. These remain evidence
  about signal features, not authenticated historical provenance. Empirical fractions
  are not confidence probabilities.
- Integrity separates EOF decode, retained warnings, native-FLAC digest, declared
  sample count and unperformed independent container checks. A matching embedded MD5
  with the wrong sample count remains a digest match and a sample-count failure.
- Everyday shows concise Russian findings; Expert provides the same facts with
  evidence and plots. Existing navigation and other application workflows remain.
  UI widgets do not run inside cached measurement functions. The full→prefix→cached
  full interaction no longer replays stale progress widgets.

## Checks actually executed

Environment: Windows 11 build 26200, Python 3.13.15, FFmpeg/ffprobe 9.0.2,
Streamlit 1.66.1, NumPy 2.5.4, SciPy 1.18.1. Local virtual environment used throughout.

| Check | Observed result |
| --- | --- |
| Baseline before this milestone | 260 passed, 0 failed, 2 conditional skips; 82.70 s |
| Full regression with real DSF fixture enabled | **319 passed, 0 failed, 1 skipped; 116.04 s** |
| Post-regression chart-axis display correction | All 3 conclusions UI tests passed; 6.80 s |
| Ruff check | Passed |
| Ruff format check | 85 Python files already formatted |
| Python compileall | Passed |
| Git diff whitespace check | Passed; existing Windows LF/CRLF conversion notices |
| `/test_audio/` and generated `data/` exclusion | `git check-ignore` confirmed; no tracked `test_audio` files |

The remaining skipped test is real SACD integration: no authorized image/backend.
The full run includes PCM/FLAC, native DSF, existing DSD duration/routing, Origin,
library, duplicates, comparison, archive and UI regressions. The final chart correction
only removes misleading axis offsets and sets a minimum 1 LU plot span; its UI checks
and rendered-browser checks ran after that correction.

Executed regression command:

```powershell
$env:MUSIC_PROJECT_DSD_FIXTURE = (Resolve-Path -LiteralPath 'test_audio/02. The Pink Panther DSD 256fs - 2ch.dsf').Path
.venv/Scripts/python.exe -m pytest -q
```

### Numerical controls

| Area | Executed controls and acceptance |
| --- | --- |
| Loudness anchor | Actual stereo 1 kHz files at −23/−33 dBFS; expected I/M/S within 0.1 LU of −23/−33 LUFS |
| M/S windows | Changing-level synthetic controls modelled on Tech 3341 cases 9/12; complete 400 ms/3 s support and extrema |
| LRA | Four synthetic Tech 3342 level-change controls; expected 10/5/20/15 LU, tolerance 1 LU |
| Gating/short input | Absolute/relative gates, exact silence, 0.05/0.3/2/4 s files; no finite Integrated for silence and no LRA without a full S window |
| Channels | Actual 5.1 file, LFE exclusion in weighted loudness; separate native channel sample levels |
| Reconstructed peak | 30 controls: synthetic Tech 3341 cases 15–19 at 44.1/48/88.2/96/176.4/192 kHz; expected −6/+3 dBTP, published +0.2/−0.4 dB tolerance |
| Independent reconstruction | Separate SciPy resampling comparison; block-state and earliest tied-peak time tests |
| Waveform facts | Exact signed rails, runs crossing chunks, positive/negative separation, intentionally flat waveforms, counts/positions and no historical-clipping assertion |
| Scope/calculation rules | Full/prefix mismatch, TP/I versus unrelated Sample Peak scope, reference absent, gain constrained by ceiling, missing/nonfinite inputs, unvalidated TP rate |
| Integrity | Actual 16/24-bit native FLAC: matching/wrong/zero MD5, partial read, matching MD5 plus wrong declared count |
| Precision/applicability | Actual 32-bit WAV low bits preserved through f64; 32-bit FLAC header is explicitly Not validated, not a claimed 32-bit FLAC decode |
| Storage/errors | 210 s accumulator control, bounded 2048 plot cells/128 event examples, complete totals, streamed stderr callback failure and bounded diagnostic tail |
| UI/cache | Everyday/Expert facts and reference persistence, unchanged result JSON, charts/reference switches without a backend call, prefix/full/cached-full action |

These are selected standards-based synthetic controls, not a complete official test
corpus or certification. Authentic programme controls and all transient/phase cases
have not been exhausted. The file-end LRA centering/terminal-silence convention in
the Tech 3342 reference algorithm has not been independently reproduced: the current
FFmpeg pass does not append 1.5 s of silence. This is an explicit conformance gap.

## Actual generated conclusions

`tools/validate_conclusions.py --durations 20 240` wrote generated 24-bit stereo
controls in ignored `data/conclusion-validation/`, ran the actual Analyze File engine,
then generated conclusions from its results. They are not hardcoded UI examples.
Every generated source had equal SHA-256 before/after analysis. The snapshot retains
selected complete conclusion records and measured summaries.

| Actual generated control | Observed result and resulting conclusion |
| --- | --- |
|20s1 kHz anchor,48 kHz native FLAC | Integrated **−23.000 LUFS**, complete 960000 frames; measured whole-stream loudness |
| Same anchor | Embedded and calculated PCM MD5 both `0d18238e9dbf04adf60fe0ca2b11a4e8`; declared/decoded frames both 960000; digest and sample count **Verified** |
| Same anchor, explicitly selected−14 LUFS/−1 dBTP reference | Target gain **+9.000 dB**; TP forecast **−13.993304 dBTP**; both constraints satisfied under the linear/unchanged-gate model |
|4s12 kHz phase45° intersample control,48 kHz | Sample Peak **−2.182446 dBFS**, TP **+0.872545 dBTP**, difference **3.054991 dB**, full-scale counts **[0,0]**; above-zero reconstructed peak observed |
|40s1 kHz with20 s at−20 dBFS then20 s at−30 dBFS | Integrated **−22.596 LUFS**, LRA **10.000 LU**; measured variation, with no quality classification |
| 4 s intentionally generated10 Hz rectangular±0.96 waveform | **80 possible flat-top runs per channel**, rail counts **[0,0]**, near-ceiling density **[1,1]** at−1 dBFS; waveform feature, with historical clipping unestablished |

The rectangular control demonstrates why plateau detection cannot prove clipping.
Zero rail hits do not exclude an above-zero reconstructed peak or earlier processing.
No compressor identity, subjective quality label or provenance probability is emitted.

### Real supplied DSD regression

The explicitly supplied Pink Panther DSD256 DSF was fully processed again, read-only.
Decode **Passed**; selected duration **234.026666667 s, Verified**, while ffprobe's
**235.881361 s** estimate remains secondary evidence. 16 formal conclusions were
generated; their measurement paths resolved. Native DSD and conversion-derived scopes
remain separate. No PCM quantization/bit-depth/rail test was applied to native DSD.

Source SHA-256 before/after matched:
`2495ee118c597cb2cb977e83d24c2217ade07dce8aae4f6e67080326f2ab84f3`.

`06 Sad Girl.flac` is absent from authorized `test_audio/`. Its supplied observations
were used only as a deterministic arithmetic/scope fixture. They were not independently
remeasured and are not presented as verified results for that recording.

## Startup and rendered interface

An actual local Streamlit server passed its health check. Installed Microsoft Edge
rendered Everyday and Expert against the generated anchor FLAC. DOM checks observed
the application version, Technical Findings, 3 images, 1 evidence table and **0 app
exceptions**. Screenshots were inspected after the axis correction: the constant
loudness line reads−23 LUFS, with dBFS peak/RMS axes and actual measurement coverage.

Screenshots and DOM text are local ignored artifacts in `data/conclusion-browser/`;
the tracked JSON contains compact DOM results. The browser process used a separate
local profile and kept its sandbox enabled. Restricted execution initially prevented
Edge GPU/renderer startup; the approved local browser check succeeded. Only processes
started by the check were terminated. No user recordings were served to an external host.
This is startup/rendering evidence, not a human comprehension or accessibility study.

## Performance observations, not a speedup claim

Both paths below used `tracemalloc` in the same session. The old path is the standalone
legacy loudnorm component, not the previous complete application. The new path also
computes all the extra native sample statistics and reconstructed peaks.

| Generated stereo 48 kHz/24-bit WAV | Legacy component seconds / Python peak MiB | New technical pass seconds / Python peak MiB | Retained plot cells each |
| --- | --- | --- | --- |
| 20 s /5.493 MiB |0.553 /1.036 |0.532 /12.630 |200 |
| 240 s /65.918 MiB |6.355 /1.040 |5.617 /13.946 |1376 |

Python allocator peaks exclude FFmpeg memory and total process RSS. These are single
observations on generated files, not a broad real-library benchmark. Plot/event storage
is bounded; changing a reference, presentation mode or chart visibility did not decode
again in the interaction tests. Existing prefix/Origin passes still have their own cost.

## Validation boundaries and remaining release work

Implemented and tested: deterministic statements, scoped loudness/peak/dynamic facts,
custom reference math, bounded streaming PCM, native-FLAC 16/24-bit MD5 and sample counts,
Origin evidence integration and Everyday/Expert presentation.

Exploratory: inherited Origin shape/provenance hypotheses; possible-flat-top rule as a
waveform observation. Neither is a calibrated historical-source/clipping classifier.

Not validated or incomplete:

- Complete ITU/EBU conformance and all official programme/transient/layout cases;
  TP rates beyond the six listed; full file-end LRA convention validation.
- 8/32-bit native-FLAC MD5 and nonnative FLAC wrappers. The local FFmpeg request for
 32-bit FLAC actually encoded 24 bits; it is not evidence of 32-bit FLAC support.
- Real Sad Girl measurements, real DFF/DST/DSD512 corpus and real SACD integration.
- Authentication of embedded digests/editions, every container/artwork field and
  historical clipping/mastering provenance.
- Asynchronous user cancellation in Analyze File, collection-scale profiling and
  human comprehension/accessibility/Windows distribution matrices.
- Existing comparison drift/fractional-delay and archive trust/recovery work, signed
  installer/update/dependency licensing and other release requirements in the ledger.

Existing ledger entries remain historical. This milestone does not complete all v1.0
requirements; a stable release still requires explicit owner approval. Collection DNA 2
and the major Audio Comparison 3 project were not begun. No audio was uploaded or
committed, no source audio was changed and no push was performed.
