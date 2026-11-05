# Audio Origin Investigator — origin-2026.11-v1

Application 0.2.3 / general method 2026.11-v5. Existing PCM algorithms, DSD conversion
method v2 and duration policy v1 are retained. This is a measured-feature and
compatibility subsystem; it does not reconstruct an authenticated production history.

## Measurement domains and controls

1. Current container/codec/rate/channels come from the existing structural/probe checks.
2. Converted PCM uses the existing FFmpeg path and verified float WAVE output header.
   Actual output rates: 176400 or 352800 Hz, original mono/stereo channel order.
   Resampling: `swr`, filter_size=32, phase_shift=10, linear_interp=0, cutoff=0.97,
   dither_method=none. Full commands/version/output headers/warnings are exported.
3. Native DSD is read without FFmpeg, decimation or PCM bit-depth interpretation.
   DSF: validated 4096-byte planar blocks, LSB-first or MSB-first; declared samples
   exclude block padding. Uncompressed DFF: interleaved channel bytes, MSB-first.
   DST and unvalidated layouts remain Unsupported. Bits map to -1/+1.

Native scope is always sampled, including when converted-stream coverage is Full:
three <=0.25 s windows near the start/middle/end for duration >=1 s; one duration/3
window for shorter files. Welch periodic Hann / 50% overlap / no detrend,
NFFT=next power of two >=native_rate/64, clamped [4096,524288]. One-sided density
in FS²/Hz, retained through 160 kHz. DC is not removed. Bit-one fraction and lag-1
sign product are research diagnostics, not historical format fingerprints. The lag
product is not mean-centered autocorrelation. Native and PCM amplitudes use distinct
measurement chains; they are plotted separately.

### Empirical response calibration — dsd-response-2026.11-v1

Generated mono DSF controls contain 33 sequential tones: 1 kHz, 20–160 kHz in 10 kHz
steps, and each candidate c−2 kHz/c/c+2 kHz. Each tone lasts 0.12 s; first 0.04 s
is discarded. A bounded first-order pulse-density accumulator creates the bits;
the actual native-bit fundamental is measured, not assumed equal to its desired input.
Output fundamental, mean-square power, folded-frequency component and two half-window
amplitudes are measured through the actual configured backend. Relative gain is
referenced to 1 kHz. A control passes if below output Nyquist, |relative gain|<=0.5 dB
and half-window amplitude difference<=0.5 dB. A candidate requires all three adjacent
control frequencies to pass before converted historical compatibility is usable.
Converted noise fitting stops at the highest consecutive passing control.

This checks discrete points, not every intervening frequency. Tonal nonlinearity,
professional modulator behavior and a continuous passband are not certified. Folded
components include modulation products and cannot uniquely quantify aliasing. Cache
identity includes executable path/size/mtime, reported version, native/output rates,
resampling settings and calibration version. First calibration performs one synthetic
decode; later analyses reuse the profile. Cancellation/failure leaves the chain
Unsupported and prevents historical attribution from that converted spectrum.

Independent conversion validation additionally compares generated DSD256 tones
1/24/48/96 kHz through FFmpeg against SciPy Kaiser8.6 polyphase FIR decimation by32.
The regression requires relative fundamental responses to agree within 0.1 dB.
This is a control experiment, not a selectable second decoder in the UI.

## Candidate boundaries

Candidates: 22050/24000/44100/48000/88200/96000 Hz, compatible with Nyquist limits
of 44.1/48/88.2/96/176.4/192 kHz PCM respectively. These are hypotheses, not identities.
No arbitrary historical sample rate is estimated from a general spectral shape.

Each channel uses median PSD in [c−2000,c−500] and [c+500,c+2000] Hz. At least five
bins are required on each side, and the complete upper side must be in the measured
range. Evidence rule: drop>=18 dB, lower-side median>1e−20 FS²/Hz, lower-side median
at least −60 dB relative to the mean 1–8 kHz density, lower-side q90/q10 spread<=35 dB.
These are exploratory guard thresholds, not calibrated probabilities or universal
noise detection limits. Silence, negligible excitation and narrow tones do not become
negative historical findings. Exact-zero upper power is explicit positive infinity;
JSON uses a state field and null numeric value rather than nonfinite numbers.

Local log-PSD is median-smoothed across five bins for a least-squares slope over
c±2 kHz (dB/kHz), maximum adjacent smoothed-bin drop, and 10–90% drop crossings.
Transition location is the midpoint of those crossings; bin-grid uncertainty is 2df.
Zero crossing width means unresolved at FFT spacing, not infinitely sharp physics.
Nonmonotonic/complex transitions may not have a resolved width. Above-boundary energy
integrates PSD from c+500 to min(c+12000, measured upper range); exact ranges are saved.

Converted Welch periodograms are reused without extra DSD FFTs or user-audio decodes.
Approximately one-second cells save per-channel features, FFT support times and window
IDs. At >64 retained cells the list is thinned by two; this is progressive deterministic
thinning, **not uniform random or statistically representative temporal sampling**.
Full global PSD still covers all decoded FFT segments. Reported temporal proportions
describe retained cells only. Stability requires >=2 detected cells and detection in
>=half the eligible cells in the same channel. DSD historical compatibility additionally
requires detection in >=2 native windows of that channel and passing converter controls.
Per-channel counts and counterexamples remain visible. PCM reuses its existing bounded
decoded prefix, computing an additional documented spectral pass without redecoding.

A visible boundary supports only compatibility. Analog bandwidth, mastering filters,
current modulation and other processing remain competing explanations. Additional noise
or filtering can hide a genuine earlier boundary. A failed rule is not proof that a
format never occurred. The six hypotheses are not exhaustive or mutually exclusive.

## Ultrasonic spectral regimes — exploratory

Twenty-four geometric bands between 20 kHz and the applicable upper range retain
median PSD and q90−q20 spread by channel. These medians are spectral-floor proxies;
tones, noise and conversion/filter response can all contribute. They are not a
statistically separated noise-only estimator.

Fit dB density versus log10(f). Compare one line with all two-line splits having
>=4 points on each side. Accept a measured regime change only for slope difference
>=12 dB/decade, SSE reduction>=0.5 and two-line RMS error<=4 dB. The transition interval
is the neighboring geometric-band centers, not a unique physical noise-shaping onset.
Three consecutive local slopes>=12 dB/decade with >=8 dB total rise mark a rising onset;
three |slopes|<6 mark a plateau. These are descriptive rules, not significance tests.
Time-cell recurrence and per-channel native/converted interval overlap are exported.
Pearson musical/ultrasonic power association is measured only for >=4 varying cells;
it is not a causal or provenance test.

Historical lower-DSD-rate classification was rejected: controlled PCM-to-DSD,
filtered high-rate PCM and DSD64→PCM→DSD128 examples also have regime transitions.
There is no validated one-to-one mapping from these features to DSD64/128/256/DXD
history. Filtering/remodulation may erase a previous stage. Only the quantitative
measurements and explicit non-identifiability result are retained.

## Reference investigation

User selects a file inside Analyze File; selection does not authenticate it. Decode
at most the first8 s, additionally bounded by memory budget, through explicit swr
resampling to 48 kHz float32 with output-header/channel verification. No source audio
file is written. Existing integer-lag alignment (<=2 s), gain/polarity, normalized
correlation, alignment uniqueness and residual calculations are reused. Reliable
alignment requires |correlation|>=0.9 and peak uniqueness>=0.01 or identical prefixes.
|correlation|>=0.995 is labelled compatible recording content **within the overlap**,
not whole-recording or edition identity. Aligned gain-compensated Welch spectra are
provided. Offset/fractional delay/drift/time stretch and different edits can defeat this
bounded-prefix method; periodic material remains Ambiguous unless prefixes are identical.

Optional full byte SHA-256 and existing canonical integer lossless PCM hashes are
separate requested operations. DSD and float PCM canonical identity remain Unsupported.
Resampled-prefix equality is not decoded-audio identity. Same/different mastering
history and conversion direction remain unestablished; correlation alone cannot date
an edition. User chronology notes are explicitly unverified external statements.

## Primary sources actually inspected

- [FFmpeg n9.0.2 DSD implementation](https://github.com/FFmpeg/FFmpeg/blob/n9.0.2/libavcodec/dsd.c):
  symmetric 96-tap FIR and table translation, based on dsd2pcm. Its DSD64-specific
  filter comments are not assumed valid unchanged at all native/output rates; actual
  backend controls above decide applicability. Source downloaded/read locally.
- [FFmpeg current DSD implementation](https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/dsd.c):
  observed deprecation path involving swresample. This moving source is not asserted
  to describe the installed n9.0.2 binary. Cache keys therefore include backend identity.
- Installed SciPy `signal.welch` and `signal.resample_poly` docstrings/source; public
  references: [Welch](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html),
  [polyphase resampling](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html).
  Used for normalization checks and an independently implemented FIR control.

Analog Devices MT-022 and TI SBAA094 retrieval attempts failed (timeouts/DNS); those
documents were not read and are not claimed as validation. Broader cascaded-modulator
literature review remains open. No universal source-rate fingerprint is asserted on
the basis of this limited research. Controlled counterexamples above are direct evidence
of non-uniqueness in this implementation, not a population-wide accuracy estimate.
