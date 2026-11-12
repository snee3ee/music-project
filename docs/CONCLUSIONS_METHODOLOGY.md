# Evidence-Based Conclusions Engine — development methods, 2026-11-10

Current app0.2.5.dev0, general method2026.11-v9. Engine `conclusions-2026.11-v1`,
PCM metering `technical-pcm-2026.11-v2`. This is a development milestone, not v1.0
or a certified metering product. No LLM, network interpretation or quality score is
used at runtime. User audio stays local and read-only.

Added `origin.lossy-investigation`, referring to the saved `lossy_source` measurement,
classification and scope. It never consumes loudness, rail, FLAC MD5 or upsampling
values. Existing metering/integrity rules remain separate. The stronger historical-
indicator category is withheld because the executed controls do not establish codec
specificity. [Lossy measurements/abstention](LOSSY_METHODOLOGY.md),
[executed validation](LOSSY_VALIDATION.md).

## Statements and scope

`Conclusion` records statement/type, input measurement IDs, values/units, scope,
reference/source, rule/version, applicability, validation, limits and optional technical
severity/action. Measured facts, verified checks, mathematical derivations, rule-based
statements, hypotheses and unavailable/unsupported results remain distinct. Input IDs
resolve to `Finding.measurements` paths; Origin array indices are explicit.

`MeasurementScope` records actual start/end/duration, native frames/rate/channels,
total duration when known, complete/partial flag, domain and processing. Origin's
noncontiguous converted ranges and independently sampled native ranges remain separate.
The bounding interval is not presented as continuous coverage. A completed measurement
does not validate a historical explanation.

New full/prefix PCM metrics use one streaming decode, replacing Analyze File's old
whole-stream loudnorm pass. The existing bounded prefix context still supplies spectrum,
quantization and legacy levels. Different scopes are shown rather than silently merged.
Full means successful decoder EOF for the first audio stream. A `-t` prefix does not
certify EOF even if it happens to cover a short file. No entire decoded track is buffered.

Prefix mode additionally applies native-sample `atrim` before ebur128. Output `-t`
alone is insufficient: a2.05s control previously included metadata through2.20s.
The regression compares a separately terminated exact-prefix fixture; later loud
samples cannot enter that prefix's loudness windows or extrema.

True Peak/Sample Peak differences require matching component scopes. PLR requires
matching True Peak/Integrated scopes; an unrelated partial Sample Peak does not prevent
a valid full-scope TP−Integrated calculation. Gain-planning peak predictions/constraints
are withheld when the loudness and TP scopes differ. Invalid/missing values are not
replaced by zero. Silence and unmeasured data have separate states.

## Loudness

FFmpeg 9.0.2 `ebur128=metadata=1:peak=none:framelog=verbose` passes native samples to
float64 WAV output. Output rate/channels/format/mask are verified. Per-frame metadata
is streamed from `ametadata` on stderr, not collected in an unbounded log. Backend
metadata precision is 0.001 LU; its integrated histogram has its own finite resolution.
The backend/method name is not treated as proof of standards compliance.

Momentary uses 400 ms, Short-term3 s; complete-window extrema have actual support
times. Metadata updates are 100 ms. Integrated uses −70 LUFS absolute /−10 LU relative
gating; LRA uses the backend's distinct gating/distribution. Final reported threshold
values are retained when exposed by the log (0.1 LU display precision). No gated
interval is automatically labelled acoustic silence. Exact zero-valued PCM frame count
and duration are a separate digital observation.

LRA is withheld when no complete Short-term measurement exists. It describes variation
according to this algorithm, not all forms of dynamics or compressor identity. Very
short or silence-heavy programmes need contextual interpretation. Short-term min/max
and an **ungated**, finite complete-window distribution are separate from LRA. Quantiles
use a 0.1 LU histogram in [−200,+100] LUFS; out-of-range samples prevent quantile claims.
Central 80% means empirical p10–p90, not a statistical confidence/provenance interval.

File-end LRA centering is not independently certified. Unlike the terminal-silence
convention in the Tech 3342 reference algorithm, this FFmpeg pass does not append 1.5 s
of silence. Selected synthetic LRA controls pass; full conformance remains unestablished.

An independent test-only implementation uses published48kHz K-weighting coefficients,
400ms/100ms integrated windows, absolute/relative gates and3s short-term percentiles.
Broadband, changing-level/gated, anti-phase stereo and5.1/LFE controls match within
0.15LU Integrated and0.25LU LRA. The reference uses no product/FFmpeg meter code and
admits complete windows without appended terminal silence. This selected comparison
does not resolve terminal centering or certify all rates/layouts.

Plots retain at most 2048 min/max envelope cells by adjacent-pair merging. No values
are interpolated across missing readings; all measurements feed extrema/distributions.
Temporal curves are M/S, not an instantaneous version of Integrated LUFS. A selected
Integrated target is labelled as a reference, not an M/S limit.

## Peaks, levels and waveform observations

Native decoded float64 preserves integer 32-bit low bits (actual WAV test). Sample
Peak is max|x|, RMS is sqrt(mean(x²)) over the stated channels/interval; crest is their
amplitude ratio in dB. Channel levels/extrema/timestamps are retained. Pooled RMS
includes all channels; loudness has its documented ITU channel weighting, including
LFE exclusion. Neither quantity is a subjective mastering assessment.

Signed integer positive rail is 1−2^(1−bits), negative rail is−1; float/unknown depth
uses±1. Counts include samples reaching/exceeding the applicable rail. v6 fixes the
earlier symmetric negative threshold, which also counted the sample one step above
the negative rail. Rail runs stay separated by polarity; totals/longest event cover
all examined samples. First128 events per channel are retained with a disclosed limit.

Near-ceiling threshold is configurable [−60,0] dBFS, default−1, applied only on the
next explicit analysis. Counts/densities are observations, not a clipping verdict.
Possible flat-top events are≥3 exactly equal samples with |x| above that selected
threshold. Rectangular signals, DC and intentional processing are counterexamples to
a unique clipping interpretation. Historical clipping is never confirmed by this rule.
Low-level/rounded/nonflat limiting may escape it. Negative/positive extrema are retained.

Peak/RMS plots begin as 100 ms bins. Adjacent merges preserve max amplitude and summed
energy/count, so merged RMS is energy-correct, not an average of dB values. Storage is
bounded at 2048 cells. Whole-file sample/run totals do not depend on retained plot rows.

### Reconstructed peak estimator

For 48/88.2/96/176.4/192 kHz: four-phase 48-tap FIR coefficients from ITU-R BS.1770-5
Annex 2, float64 arithmetic. For 44.1 kHz:8× polyphase 385-tap Kaiser 8.6 interpolation,
output 352800 Hz. State spans chunks; filter delay is compensated in timestamps.
Zero-extension is explicit; only reconstructed positions inside the programme range
are considered. Stored sample maxima are also retained so the estimate cannot be
lower than a stored peak. Earliest tied-peak time uses relative 1e−12 tolerance to
avoid chunk-dependent floating-point tie selection. Reported time is a grid estimate,
not an exact continuous-time maximum or acoustic speaker output.

Other rates are **Not validated** for TP; no finite headroom, above-zero verdict or
ceiling guarantee is fabricated. Selected analytical EBU-style controls and independent
SciPy reconstruction comparisons are tested within the published control tolerances.
This does not certify every waveform or complete ITU/EBU compliance. True Peak is an
estimate: a positive value reports the measured exceedance; a negative value reports
its margin. Neither excludes prior clipping or guarantees arbitrary encoding/playback.

The old FFmpeg loudnorm function remains as an independent comparison and compatibility
API. Its 192 kHz path is no longer the sole basis for Analyze File's new peak results.
FFmpeg ebur128 peak metadata is not used numerically: it rounds linear amplitudes to
three decimals, which can create large relative errors for quiet signals.

## Explicit references and gain-only planning

Default: no target. Only custom user-selected LUFS/TP values are implemented; no platform
or broadcasting profile is silently selected. Reference values/source are part of the
derived conclusion. Difference=measured−target LU; target gain=target−measured dB.
Predicted TP=measured TP+gain under the stated linear model. A ceiling imposes
gain<=ceiling−TP. If the target gain exceeds that bound, report that the model cannot
satisfy both simultaneously, and give the ceiling-constrained gain/resulting loudness.

No gain, limiter, compressor or re-encoding is applied. This model assumes unchanged
gating membership; changing absolute-gate membership requires remeasurement. TP accuracy
limits remain applicable. It does not predict an exact streaming-service output.
Reference changes regenerate conclusions from stored facts without decoding or mutation.

## Integrity

Strict decoder success, retained warnings, FLAC digest, declared frame count and container
coverage are separate. Native-FLAC8/16/24/32-bit STREAMINFO MD5 is compared against signed,
interleaved little-endian native PCM packed during the same pass. Nonzero declared sample
counts are checked independently. A matching digest plus wrong declared count reports
**digest matched / frame count failed**. Missing all-zero digest is Unknown, not Verified.
Partial reads do not validate a whole digest. Independently generated RFC9639 verbatim
frames have known signed PCM, independently packed digests and valid CRCs. Actual
FFmpeg decoding verifies mono/stereo low bits/extrema at all four depths. Clean whole-
frame truncation fails the declared count even when decoder EOF succeeds. Other
non-byte-aligned depths remain Not validated; inaccessible native wrappers Unsupported.

An embedded MD5 match does not authenticate an edition or independent archive. Successful
decode does not validate every metadata/artwork field. Scanner/archive/Compare workflows
are not replaced by this Analyze File feature. Source size/mtime is checked before/after;
control tools additionally SHA-256 the generated files. No original audio is written.

## Primary references actually inspected

- [ITU-R BS.1770-5 (2023)](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf):
  loudness/TP framework and Annex 2 interpolation example.
- [EBU R 128 (2023)](https://tech.ebu.ch/docs/r/r128.pdf): broadcast context; no universal
  musical target is inferred from it.
- [EBU Tech 3341 v4 (2023)](https://tech.ebu.ch/docs/tech/tech3341.pdf): M/S time scales
  and selected synthetic minimum-requirement controls.
- [EBU Tech 3342 v4 (2023)](https://tech.ebu.ch/docs/tech/tech3342.pdf): LRA versus other
  dynamics quantities and synthetic LRA controls. Passing selected controls is not certification.
- [FFmpeg n9.0.2 f_ebur128.c](https://github.com/FFmpeg/FFmpeg/blob/n9.0.2/libavfilter/f_ebur128.c):
  metadata precision, channel weighting, windows/gating and internal peak-resampling behavior.
- [RFC 9639](https://www.rfc-editor.org/rfc/rfc9639.html): STREAMINFO sample count and
  MD5 representation. Validation details and actual results are separate below.

[Executed validation and remaining coverage](CONCLUSIONS_VALIDATION.md).
