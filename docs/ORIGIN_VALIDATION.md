# Origin Investigator — executed validation, 2026-11-05–06

App 0.2.3; general method 2026.11-v5; Origin origin-2026.11-v1;
calibration dsd-response-2026.11-v1. Local FFmpeg/ffprobe 9.0.2 (Gyan full build).
Baseline before this milestone: 220 passed / 2 conditional skips. No audio was
uploaded, modified or committed. `git check-ignore` confirms `/test_audio/` exclusion.

## New evidence and controlled counterexamples

- Actual controls ran for DSD64/128/256/512 at both output rates: eight real backend
  response profiles, 33 tones each. Cache replay and changed-version identity checked.
  DSD256 / 352800 profile: relative gain −0.0020 dB at96 kHz, −0.1362 at150 kHz,
  −1.3031 at160 kHz. Requesting 352800 Hz therefore does not imply a flat response
  through Nyquist. All six candidate neighborhoods pass in this particular profile.
- Independent SciPy FIR conversion agrees with FFmpeg relative fundamental response
  within the tested 0.1 dB bound for native DSD256 tones at1/24/48/96 kHz.
- Six analytic known-density step boundaries measure the intended40 dB drop.
  Silence, weak excitation, isolated tone, flat and rising controls do not force
  detections. Zero upper power remains explicit and finite-JSON compatible.
- **Actual end-to-end positive:** Gaussian high-rate PCM352800, seed790, sigma0.1,
  1025-tap Kaiser8.6 FIR at22050 Hz → resample_poly → first-order pulse-density DSD256.
  Measured33.9402 dB boundary near22.05 kHz in all3 converted temporal cells and all3
  independent native windows. UI/report evaluate44.1 kHz PCM bandwidth compatibility,
  while historical source remains Unknown. **This chain has no44.1 kHz PCM stage.**
  Thus the boundary is useful evidence of filtering and a counterexample to a unique
  historical-rate interpretation. An analytic steep analog-filter response also
  triggers the feature rule; no PCM-identity verdict is issued.
- Known PCM44100/48000/96000/352800 → first-order DSD64, filtered high-rate PCM,
  input-dither configuration, and PCM44100→DSD64→FFmpeg352800→DSD128 were actually
  generated/decoded/investigated. None supports a unique historical-format result.
  Measured DSD64 drops near22.05/24 kHz are only7.94/10.72 dB for the44.1k control
  and3.48/7.09 dB for48k. These are **false negatives for an earlier PCM-stage
  detector**, not evidence that those known stages were absent. Thresholds were not
  lowered to recover them. DSD25644.1k input-level controls0.02/0.05/0.15 RMS also
  remain below the18 dB rule in these transition neighborhoods.
- PCM-to-DSD, filtered-source and cascaded-DSD controls all produce ultrasonic regime
  transitions. Mapping one transition to an earlier lower DSD rate is not validated;
  that classification is omitted. Synthetic observations are not population accuracy.
- DSF bit orders, channel-block layout, offsets and valid-sample trimming tested;
  DFF interleaving/MSB order and truncation tested. An actual24 kHz two-channel
  bit-identical DSF/DFF control passes the complete Origin pipeline in both containers.
  Recovered channel ratio is checked against the **actual native fundamental**,
  because desired pulse-density input amplitude is not an exact modulation guarantee.
- Native Welch normalization independently checked against SciPy. Temporal collector
  consumes existing DSD periodograms; retained summaries remain bounded at<=64 cells.
  Asymmetric channels, rising onset, plateaus, smooth-slope ambiguity and failed
  calibration blocking historical attribution have explicit tests.
- Actual reference controls verify480-sample lag, inverted polarity, −6.0206 dB gain,
  strong correlation and distinct canonical hashes. Same-file canonical PCM identity
  verifies; a shifted periodic-tone pair remains Ambiguous. Source chronology and
  mastering history are not inferred. No reference is authenticated by its selection.

Numerical snapshot including exact processing chains and performance:
[ORIGIN_VALIDATION.json](ORIGIN_VALIDATION.json). Reproducible control generator:
`tools/validate_origin.py`; further actual controls are in `tests/test_origin.py`.
Offline fixture generation may materialize resampled vectors; application analysis
uses the bounded streaming implementation described in the methodology.

## Supplied real recording

Only repository Pink Panther DSF was present:665751644 bytes, DSD25611289600 Hz,
stereo. FEELS LIKE SUMMER / a real DFF / real DST were not supplied and were not
searched for elsewhere in personal folders.

- Quick decodes15.000 s in three deterministic regions; global/temporal results are
  partial. Independent native scope is0.750 s in three windows.
- Full decodes234.026666667 s through EOF, agrees with DSF native sample count and
  preserves Verified duration selection. Secondary ffprobe235.881361 s estimate
  remains technical diagnostics. Nonfatal bitrate-duration warnings are retained.
- None of the six historical PCM-bandwidth hypotheses receives stable boundary
  compatibility evidence. They remain Inconclusive, with supporting/countermeasurements
  and excitation/chain applicability. This is not a claim of native DSD provenance.
- Converted spectrum has an exploratory regime transition86.915–102.806 kHz in both
  channels; full fitted slopes L−31.815/+154.058 and R−32.922/+154.082 dB/decade.
  Native sampled spectra independently have a transition83.539–99.345 kHz in both
  channels. Intervals overlap. The transition is therefore present in the sampled
  native signal; the current FFmpeg conversion alone does not explain its existence.
  Its historical cause and any earlier DSD rate remain unidentified.
- Full accumulation measures235 time cells and retains43 after deterministic thinning.
  Those retained-cell proportions are not asserted to represent uniform sampling.
- Source SHA-256 before/after remains
  `2495ee118c597cb2cb977e83d24c2217ade07dce8aae4f6e67080326f2ab84f3`.

## Performance observations

Same-session baseline is existing `diagnose_dsd` without Origin collection/native work,
not a checkout of the previous complete application. Both paths use tracemalloc;
cache/filesystem are warm. No speedup claim. Browser/background work can affect timing.

| Pink Panther | Existing DSD core | With Origin | Python/NumPy allocator peak with Origin |
|---|---:|---:|---:|
| Quick15 s coverage |1.116 s |3.520 s |26.08 MiB |
| Full234.027 s coverage |9.189 s |21.278 s |26.74 MiB |

Baseline core allocator peaks6.92 MiB. Allocator measurements exclude FFmpeg and are
not RSS. Snapshot was captured before final presentation text/summary-field changes;
signal features/rules are the same. Full decode and Origin share the user-audio pass;
native windows use separate bounded direct reads. Calibration adds a generated-control
decode on a previously unseen backend/rate profile, not a second user-audio pass.

Generated stereo DSD512 repeated0x69 controls,352800 Hz conversion:

| Duration / input size | Full time | Allocator peak | Sampled Python+active-backend RSS peak |
|---|---:|---:|---:|
|20 s /107.67 MiB |5.968 s |46.70 MiB |192.08 MiB |
|120 s /646.00 MiB |14.792 s |47.04 MiB |192.89 MiB |

Both full streams Passed; one user-signal decode per full run. Quick cached runs
take0.095/0.099 s and launch zero subprocesses. First20 s Quick took10.555 s and
included a new generated calibration decode; second120 s Quick took5.861 s with the
profile cached. RSS is a5 ms sample, not an exact peak. These generated periodic files
test resource behavior, not the diversity of commercial DSD512 recordings.

Reproduce with `tools/benchmark_dsd.py --rate 22579200 --seconds 20 120`.

## Interface and startup

Streamlit AppTest verifies Everyday default, concise report/no raw JSON, actual Full
action, in-report reference comparison, Expert access and equality of stored results
across mode switches. A failing subprocess-launch stub confirms presentation switches
do not launch decoders/backends. Existing expert navigation matrix remains covered.

Clean localhost Streamlit startup on18510 returned health `ok`. Actual installed
Edge156 rendered the supplied DSF in both modes. DOM check:5 analytical plot images,
3 evidence tables,0 exception/alert elements in Expert Origin. Screenshots inspected:
`data/origin-browser/everyday.png`, `expert.png`, `expert-plots.png`, `expert-tables.png`.
Everyday shows verified-source duration, scope, findings, one uncertainty summary and
two implemented next actions; Expert shows separate native/converted PSD, empirical
response, noise profile, temporal attenuation, hypotheses and numerical tables.

This is an actual rendered-interface review. **A timed15-second comprehension study
with ordinary listeners was not conducted; that acceptance metric remains unverified.**
No subjective usability score is substituted for it.

## Final automated checks

Full suite with `MUSIC_PROJECT_DSD_FIXTURE` pointing to the supplied repository DSF:
**261 passed, 1 skipped** in86.52 s in the final run, including legacy-diagnostic cross-references.
The only skip is real SACD integration: no image or sacd_extract backend. Real DSF
integration ran, not skipped. Full results include PCM/FLAC, Unicode paths, library,
duplicates, Compare, archives, duration discrepancy, DSD, reference and UI checks.
Ruff lint, Ruff formatting (69 Python files) and compileall passed. No test failures
remain in the final run.

Earlier intermediate failures exposed old UI tests assuming Expert as default, a
missing test import and an invalid assumption that desired pulse-density amplitude
equals the actual native fundamental. Default-mode coverage was added separately;
old Expert assertions were retained. The corrected actual-input normalization is
tested. Thresholds were not changed to suppress a failing historical-origin case.

## Restrictions, failures and remaining scope

Restricted Edge processes failed (GPU access/exit−1073741790 or renderer timeout).
Running installed Edge through approved terminal escalation succeeded with browser
sandbox still enabled. CIM process enumeration returned Access Denied; a separate
known-port clean server was used. A development hot reload retained an older Settings
class and produced a stale exception-class error; clean startup/new session worked.
This hot-reload migration case is not claimed fixed by the feature. No permission,
Git or security configuration was changed. No executable was downloaded.

Official FFmpeg n9.0.2 and current DSD source were read. Generic web search timed out;
Analog Devices retrieval timed out and TI retrieval had DNS failure. Broader primary
cascaded-modulator literature research remains incomplete. Exact inspected sources and
scope are listed in the methodology; inaccessible sources are not claimed read.

Further priorities: held-out professional modulation/filter chains, real DFF/DST and
DSD512, a validated noise-only estimator, documentary source authentication, human
comprehension testing, more comprehensive continuous response/alias rejection controls,
fractional-delay/drift-aware reference comparisons and explicit UI cancellation.
