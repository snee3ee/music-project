# Lossy source investigation — lossy-investigation-2026.11-v1

Application0.2.5.dev0, general method2026.11-v9. This extends existing Analysis/Finding
and Origin infrastructure. It does not identify an authenticated historical codec,
encoder, bitrate or master. User listening impressions and loudness are not ground truth.

## Applicability and reuse

Lossless decoded PCM, mono/stereo, native rates32/44.1/48/88.2/96/176.4/192kHz.
The target includes ordinary16-bit44.1/48kHz FLAC/WAV and independently applicable
higher-rate PCM. Unsupported rates/layouts, current lossy streams and native DSD
are explicitly Not evaluated. Native DSD is never converted for this test.

`LossyReport` is a typed serializable contract stored as `findings.lossy_source`.
The collector consumes the existing float64 native PCM technical pass; it does not
start another decoder or write audio. Existing `StreamingWelch` and parameterized
`boundary_features` are reused. Default DSD/Origin candidates and rules are unchanged.
Existing legacy fixed-grid PCM findings remain exported for compatibility; the new
primary investigation is independent of the Hi-Res upsampling result.

When the technical pass fails, the already decoded PCMContext can supply an explicitly
labelled prefix fallback. The original total duration is retained. A prefix does not
verify full-file decoding, FLAC MD5 or unseen sections. Full/native DSD, Hi-Res,
integrity, bit-depth, existing plots and comparison capabilities remain separate.

## Deterministic time selection and bounded memory

Known available duration is partitioned into full2-second native-sample slots. Up to32
slot indexes are chosen by rounded evenly spaced endpoints, including first/last full
slots. Nonmultiple terminal remainders are not silently counted as analyzed. Short
inputs have one partial slot; fewer than1second is excluded from spectral interpretation.
Unknown duration uses the first32two-second slots and discloses that prefix strategy.
Technical prefix mode plans only inside its configured duration. EOF before planned
regions is counted explicitly. No FFT joins disjoint regions.

At most64seconds are analyzed spectrally. The full technical decoder may already read
the whole stream for existing metering/integrity. Runtime/memory are reported separately,
not inferred from sample coverage. Native FFT state is8192frames; up to32per-window
4097×channels PSD arrays are retained internally for common-frequency remeasurement.
That array budget is2,097,664bytes for stereo, plus bounded summaries/Python objects.
The whole application has additional PCMContext/Origin/result/cache memory; this budget
is not a process-RSS guarantee.

Counts distinguish planned/seen/eligible/discarded/unreached windows, unselected slots
and unretained candidate clusters. Exclusion reasons count channel-windows; discarded
windows have no eligible channel. Exact selected ranges/durations are exported.

## Measured spectral properties

Welch: periodic Hann,8192FFT,50%overlap, no detrend, one-sided FS²/Hz, independent
channels, no downmix/resampling. Native spacing is sample_rate/8192Hz. Bands partition
0/1/4/8/12/14/16/18/20kHz and the actual Nyquist, retaining only available boundaries.
Bin-sum energy includes Nyquist exactly once. Report band power/fraction, median,
q10/q90density and median relative to mean1–8kHz density. These quantiles are spectral
floor proxies containing tones/noise/DSP, not separated recording-noise measurements.

Window applicability: exact zero, RMS below−80dBFS, mean1–8kHz PSD≤1e−16, or reference
occupancy below0.5 above mean-reference−30dB are reported separately. These are
engineering excitation guards, not a perceptual noise/silence or source-authenticity test.
Dominant-bin fraction and per-FFT energy coefficient of variation describe concentration
and temporal variability. They do not name instruments, percussion, editing or codecs.

## Adaptive boundary candidates and temporal evidence

Search8–min(24kHz,Nyquist−600Hz), covering the available upper audible band at44.1kHz.
For discovery, smooth per-channel logPSD with an odd median window near100Hz; compare
positions about100Hz to each side. Find local contrast maxima, rank measured contrast,
retain up to6per-window locations separated by600Hz. These are FFT-bin locations,
not fixed integer-kHz or historical sample-rate hypotheses. No two-sided boundary is
asserted in the last600Hz before Nyquist. Distance to Nyquist/upper support are recorded.
An upper-band rolloff does not identify a codec merely because it approaches Nyquist.

Actual contrast is remeasured with existing Origin features in side bands
[c−600,c−200] and[c+200,c+600]Hz. At least5bins per side. The observational guard
retains drop≥18dB, lower median>1e−20FS²/Hz and≥−60dB relative to1–8kHz, lower-side
q90/q10spread≤35dB. Local fitted logPSD slope, crossing width/midpoint,2-bin grid
uncertainty and above-boundary energy/range are retained. Width is a spectral-bin
estimate, not a calibrated physical filter specification. Zero power has explicit
state/null representation rather than invented finite precision.

Window-positive candidates are retained before candidates discovered from the aggregate
PSD, so an intermittent boundary cannot disappear solely because other windows contain
high-frequency energy. At most12distinct600Hz-separated frequencies are retained in
chronology order, then global candidates; omitted positive clusters are counted.
Each retained frequency is remeasured on every saved window PSD without new FFTs.
Per-channel eligible/hit counts, window IDs and maximum measured window contrast are
exported. Recurrence means≥2hits and hits in≥half eligible windows in the same channel.
These are deterministic descriptive criteria, not calibrated codec confidence.
Stereo disagreement/counterexamples remain visible.

## Interpretation and non-identifiability

The report contract distinguishes Indicators detected, No evaluated indicators detected,
Inconclusive and Not evaluated. This method does **not** currently emit the stronger
Indicators detected historical-encoding category: no independently discriminatory
codec-artifact family has been validated. Measured bandwidth suppression remains an
observation compatible with lossy coding **and** non-lossy filtering/band-limited audio.

Any observed candidate, or fewer than2eligible windows, yields Inconclusive. Adequate
support without evaluated abrupt spectral observations yields No evaluated indicators
detected. This does not establish lossless history. No usable spectral window or an
unsupported input yields Not evaluated with its reason. Historical codec stays Unknown;
source authenticity stays Not established. No exact encoder/bitrate or probability is
inferred. The formal Origin conclusion references the saved investigation facts/scope.

FLAC digest/frame checks, Integrated LUFS, LRA, True Peak, full-scale counts and limiting
observations do not enter this interpretation. A correctly encoded FLAC can contain
decoded lossy material; a limited original PCM can be genuinely free of perceptual coding.

## Additional families: evaluated but not deployed as coding evidence

The validation tool measures positive spectral flux from1024-point/512-hop STFT
magnitudes: squared positive magnitude differences divided by the sum of both adjacent
frame squared magnitudes, then averaged. It also compares10ms pre/post energy around
a local energy maximum near a known synthetic fixture region. The latter is not a
reference-free pre-echo or true-onset detector; codec delay/onset ambiguity is a limit.

Actual MP3/AAC controls and non-lossy transient/filter/noise controls overlap in these
descriptors. Content and ordinary processing confound them. No cutoff for historical
classification is fitted. They stay in validation diagnostics only. Production reports
explicitly say time-frequency/transform-pattern, pre-echo and coding-noise attribution
are Unsupported. No decoded-PCM MP3-frame detector is fabricated.

See [executed dataset, false positives/negatives, real file and test commands](LOSSY_VALIDATION.md).
