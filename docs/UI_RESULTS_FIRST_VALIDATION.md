# Results first — UI correction, 2026-11-11

Application remains **0.2.5.dev0**, general analytical method **2026.11-v7**.
This is a presentation correction. No new audio method or format capability is claimed.
Existing uncommitted Conclusions/CUE/SACD work and user data were preserved.

## Primary locations

| Result | Primary presentation | Evidence |
| --- | --- | --- |
| Consolidated summary | Overview: two short status lines and Integrated/TP/LRA when available | Optional source metadata; respective result module |
| Decode, digest and count checks | Integrity: one result, scope, warning/error counts | One optional verification section; original diagnostics in Appendix |
| Loudness, peaks, headroom, dynamics | Spectrum & Levels: four compact groups | Expert channel values/distributions and optional time curves |
| Provenance evidence | Origin: found / supported conclusion / unknown | Optional Expert spectral evidence and alternatives |
| Native DSD/output properties | DSD Diagnostics | Native versus converted properties remain distinct |
| Raw conclusions, rules, precision and methodology | Technical Appendix | Original Analysis JSON, findings, backend data, logs, reference result and response controls |

The common Technical Findings report is no longer inserted into Overview, Integrity,
Spectrum or Origin. Its complete rule table lives only in Appendix → Conclusions and
rules. The old mixed Origin discovery list contained decoder summaries and thresholds;
the primary Origin view now selects saved structured Origin statements instead. The
original discovery list remains in the exported data. No threshold or hypothesis rule
was changed. A no-applicable-boundary observation is not converted into provenance proof.

Both modes navigate the same existing modules. Everyday provides essential facts;
Expert adds numerical and spectral evidence, without raw JSON or rule identifiers.
Full JSON and reference comparison reports remain downloadable/inspectable in Appendix.
Reference gain controls are in Levels; full-stream checking remains in Integrity and
the applicable Origin action. Ordinary reference comparison and the existing logical-
track applicability guard are preserved.

The header shows filename, codec, applicable bit depth, rate, channel count and selected
duration. Container remains distinct and accessible in source details. Secondary duration
estimates remain in Appendix. Coverage is labelled by group rather than repeated in
every sentence; incomplete and disjoint coverage is not labelled a complete file.

## Charts and unavailable values

Plots retain their original data, transforms, axes, units and bin aggregation. Main
single charts use a 720-pixel maximum width, bounded by their parent container; DSD
band charts use 540 pixels within responsive columns. Figure proportions are reduced.
Exact metadata/normalization remains in Appendix, with concise chart captions.

Unavailable measurements remain “Not determined”; actual recorded negative infinity
is displayed as −∞. Zero LRA remains 0.00. Silence does not receive invented Integrated
loudness or Crest Factor. An all-zero PSD/peak timeline is explained instead of shown
as an empty graph with an arbitrary near-zero dB axis. This changes presentation only.

## Executed regression checks

Baseline: **359 passed, 0 failed, 0 skipped; 134.31 seconds**, with explicitly authorized
real DSF and Aja ISO fixtures enabled. Full regression: **364 passed, 0 failed,
0 skipped; 123.46 seconds**, with both real fixtures enabled. After the final DSD metric
layout adjustment, **2 targeted DSD UI tests passed in 5.83 seconds**, and the real DSD
browser case was rerun successfully. Ruff check, Ruff format (98 Python files),
compileall and diff whitespace checks passed. Exact results and protected-source hashes
are in the [validation snapshot](UI_RESULTS_FIRST_VALIDATION.json).

New presentation contracts test:

- Module/mode changes with backend launching forbidden, preserving the entire Analysis
  dictionary and exported JSON, including every original conclusion.
- No raw JSON, code blocks or rule/version tables in the main result modules; the full
  conclusion count and original rule identifiers remain accessible in Appendix.
- Applicable Overview numbers, exact zero versus missing versus negative infinity,
  short-silence applicability and noncontiguous track coverage.
- Integrity failures remain failures when PCM decoding or embedded MD5 separately passes;
  logical-track success does not hide a declared-frame-count failure.
- Existing reference/full-check actions, reference JSON moved to Appendix, spectra,
  playback, cached FFTs, native DSD evidence and selected CUE/ISO workflows.

The unchanged broader suite includes Library, Duplicates, Compare, Archive, ordinary
PCM/FLAC, real DSF, real SACD extraction and analytical regressions. Layout assertions
were updated to the requested hierarchy rather than keeping the duplicated reports.

## Actual rendered inspection

Local Streamlit and installed Edge were used; browser sandbox remained enabled and
audio stayed local. The check uses an isolated validation database/profile and only
terminates the processes it creates. Screenshots/DOM text are ignored local artifacts
in `data/ui-results-first/browser/`.

Inputs:

- Generated ordinary stereo FLAC: 48 kHz, 16-bit, 8 seconds.
- Generated high-rate stereo FLAC: 96 kHz, 24-bit, 8 seconds. This describes the file,
  not a historical/native Hi-Res origin classification.
- Generated short silent FLAC: 48 kHz, 16-bit, 0.05 seconds; incomplete loudness windows
  produce unavailable Integrated/LRA, while actual zero amplitude produces −∞ TP/RMS.
- Previously authorized Pink Panther native stereo DSD256 DSF, read-only Quick analysis.

Visually inspected screenshots: normal Overview, Integrity, Levels and Appendix;
high-rate Overview and timelines; short-file Overview and Expert Levels; DSD Overview,
Expert Levels, Origin and native/conversion properties. The last DSD properties layout
was inspected again after the metric layout adjustment. The viewport was 1600 × 1100
CSS pixels. Main time/spectrum charts measured 720 × 267 CSS pixels; DSD band charts
540 × 245. Each of the four overviews contained zero tables; inspected main modules
contained zero raw JSON blocks. Primary measurements remain numerical and scoped. Raw
reports are restricted to Appendix. Browser automation needed adjustments for rerun
timing and Windows console encoding; those failures were not application exceptions
or decoder results. AppTest separately exercises the complete rules selector and JSON.

## Preservation and limits

Before/after SHA-256 checks cover all **53 protected files**: analytical core, decoders,
models, method/version declarations, unchanged source/cache workflow and unrelated
Library/Duplicates/Compare/Archive UI. Matching hashes establish that those source
files were not modified by this task. Original audio was not written, uploaded or
committed; no push occurred. No application version increase was made.

This validates deterministic rendering/behavior and the inspected desktop screens,
not a human usability study or complete accessibility/mobile/browser matrix. Existing
DSD/DST/SACD applicability, Origin inference limits and metering-validation boundaries
remain as documented by their analytical methods. CUE/ISO source selection/processing
and unrelated application pages were outside this correction and remain unchanged.
