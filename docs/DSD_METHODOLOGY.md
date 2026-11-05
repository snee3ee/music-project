# DSD Signal Diagnostics — dsd-2026.11-v2

As of app0.2.3, a separate [Origin Investigator](ORIGIN_METHODOLOGY.md) adds sampled
native PSD and empirical discrete converter-response controls. The conversion-group
measurements below remain PCM-derived; they are not a native-spectrum measurement.
Analyze integration links the executed Origin/profile status in legacy diagnostics.
Statements below about the diagnostics module not validating composite response refer
to `diagnose_dsd` alone. Origin's discrete controls do not certify a continuous passband.

Implemented as a compatible 0.2 extension. Core modules contain no Streamlit imports:
`dsd_container`, `dsd_decoder`, `dsd_spectrum`, `dsd`. Results reuse typed `Finding`,
`Analysis`, `DSDContainer` and `ConversionAttempt`; JSON contains method/scope/commands.

## Applicability and native versus derived evidence

DSF v1, uncompressed DSD, bit order 1 (LSBF) or 8 (MSBF), 4096-byte channel blocks:
bounded header/chunk/file-size validation, channel-type/count consistency, nonzero
rate/sample count, padded payload size and metadata-pointer bounds. Other DSF format
versions/block sizes are Unsupported, not automatically corrupt. Native rate is bits/s
per channel; ffprobe packed-byte sample rate is multiplied by eight for `dsd_*`.
Nominal uncompressed bitrate is native rate × channels (DSD256 stereo: 22,579,200 bps).
The separately labelled ffprobe bitrate may describe stream or container throughput.
Neither bitrate includes a guarantee about provenance; metadata/container overhead
and DST compression must not be conflated with nominal DSD bitrate.

DFF/DSDIFF: big-endian FRM8/PROP/chunk bounds, FS/CHNL/CMPR consistency and uncompressed
DSD payload length divisible by channels; repeated/missing/contradictory required
properties are rejected. Chunk traversal is limited to 10,000 entries per table.
Native sample count = payload bytes × 8 / channels. Unknown chunks are skipped by
bounded seeks. DFF DST is detected by CMPR and the audio chunk, reported Unsupported;
compressed payload/FRTE/DST checksums and actual decoding are not validated. Native
rate from ffprobe DST stays Unknown; header declarations are separately visible.
SACD ISO remains a disc image handled by the existing optional-backend architecture.

Structural inspection reads header bytes and file lengths; it does not inspect the
musical meaning of every payload bit. Arbitrary uncompressed one-bit patterns may be
syntactically decodable. No universal DSD payload checksum or historical authenticity
claim is implied. Interchannel spectral differences are measured, not labelled defects.
Multichannel headers are inspected but conversion/spectra are Unsupported pending
explicit channel-layout validation. Mono and stereo conversion are supported.

## Three duration observations

1. DSF declared sample count / native rate, or DFF uncompressed data-length derivation.
2. ffprobe duration, retained separately; warning when it differs by >10 microseconds
   (a discrepancy display tolerance, not a corruption threshold).
3. Successfully converted PCM frames / verified PCM rate.

Full decoding uses strict FFmpeg errors and must reach EOF successfully. Duration must
be no shorter than expected minus two PCM frames and no longer than expected plus two
PCM frames. DSF additionally permits only exact declared padding:
(payload_bytes ×8 / channels − sample_count) / native_rate. The previous maximum
whole-block allowance is no longer used. That tolerance is disclosed in the report.
Counts need not be a multiple of
eight; packed-byte trimming and resampler rounding can change sub-frame duration.
Quick explicitly limits output with `-t`; it cannot certify EOF even if its only window
covers a short recording. Fatal errors, partial output, warnings and structural
failures are separate results. Timeout/cancellation returns Partial; invalid output
format/non-finite PCM/short output/fatal decoding returns Failed. A missing backend is
Unsupported. Container failure leaves decoding Unknown because it was not attempted.

Primary `AudioInfo.duration` is now structure-derived (Derived), corroborated only
after consistent full EOF decoding (Verified). ffprobe estimates remain secondary.
A full mismatch beyond known padding/output rounding is Ambiguous with null primary
duration. Failed/unsupported headers do not fall back to ffprobe as canonical audio
duration. UI secondary values are in Technical Appendix. See the complete
[duration selection policy and real-file evidence](DSF_DURATION_VALIDATION.md).

The owner subsequently supplied the Pink Panther DSD256 path. Local full decoding at
both PCM rates matches declared DSF duration 234.026666667 s; ffprobe estimates
235.881361 s with an explicit bitrate-duration warning. Its estimate numerically matches
all bytes after the 92-byte header divided by nominal byte rate, including the metadata
tail. See [actual case and UI verification](ANALYZE_UI_VALIDATION.md). No actual
foobar2000 duration value/backend reproduction was provided, so that player comparison
remains unresolved. Successful full decode does not establish a historical production chain.

## Explicit conversion backend

Local FFmpeg, version recorded in `Analysis.backends`. Input is the original read-only
path, protocol whitelist `file,pipe`, first audio stream only, `-nostdin`, `-xerror`,
`-err_detect explode`, warning-level diagnostics. No shell or temporary audio files.
The actual argument array is exported; advanced UI shows it without shell re-quoting.

Example argument sequence (paths passed as separate arguments):

```text
ffmpeg -hide_banner -nostdin -v level+warning -xerror -err_detect explode
  -protocol_whitelist file,pipe -i <source> -map 0:a:0 -vn
  -af aresample=352800:resampler=swr:filter_size=32:phase_shift=10:linear_interp=0:cutoff=0.97:dither_method=none
  -ar 352800 -ac 2 -channel_layout stereo -c:a pcm_f32le -f wav pipe:1
```

176400 Hz is the other supported setting. `filter_size`, `phase_shift`, `cutoff` and
other explicit options describe **libswresample**, not the internal DSD decoder.
They do not claim a measured composite filter response, attenuation or native DSD
passband. The DSD decoder's internal filtering is backend-specific. Effective native
DSD bandwidth is Unknown / Not validated. Measurements below describe the resulting
PCM representation only: **Derived from DSD-to-PCM conversion.**

Incremental RIFF/WAVE parser verifies actual IEEE float32 sample rate, channel count,
byte rate and block alignment before consuming samples. WAVEFORMATEXTENSIBLE must
also have the float subtype GUID, 32 valid bits and expected mono/stereo channel mask.
Plain IEEE float WAV verifies count only and discloses that layout was explicitly
requested but not present in its header. Empty, partial frames, non-finite samples
and known data-length mismatches are errors. Unseekable WAV length 0xffffffff uses EOF
and independent duration counts. PCM is consumed in 1 MiB blocks; FFT state is fixed.
stderr is concurrently drained into a bounded 64 KiB diagnostic tail, without a
growing disk log. Python API accepts progress and cancellation callbacks; cancellation
is polled in a watcher even when the backend emits no stdout. The UI shows progress
but currently has no dedicated asynchronous Cancel button. Timeout remains configurable.

## Scope and sampling

Quick: if duration ≤15 s, one window [0,D]; otherwise [0,5], [(D−5)/2,(D+5)/2],
[D−5,D]. At most three seeked conversions, no repeated whole-track pass. Each later
window seeks with 0.25 s preroll and output-side trimming; preroll is excluded from
PSD. Verify selected intervals and decoded counts in the scope. Seeking behavior
depends on the demuxer; failures remain visible rather than silently using a prefix.
Full: one sequential conversion to EOF. Does not retain the entire PCM waveform.
Failed/partial segments and successfully decoded seconds remain available.

Quick windows do not characterize every moment or prove whole-file integrity.
Welch never joins disjoint windows. Result caching is bounded (2 entries/10 min),
keyed by resolved source path, size, mtime_ns, settings, method versions and executable
path/size/mtime identities. Source changes during processing are rejected. UI provides
an explicit cache bypass. This is not a cryptographic source identity: edits preserving
size/mtime require bypass, or independent file hashes/archive verification.

## PSD, band power and numerical conventions

Per channel: N=16384, periodic Hann w, hop=8192 (50% overlap), no detrending,
no channel downmix, no zero padding, equal linear power averaging of complete windows.
One-sided density P[k] = |FFT(w x)[k]|² / (Fs Σw²), doubled at interior bins only.
DC/Nyquist are not doubled. Units are FS²/Hz; 10 log10(P/(1 FS²/Hz)) for density dB.
Frequency step is Fs/N: 10.7666015625 Hz at 176400, 21.533203125 Hz at 352800.
This is bin spacing, not a claim of exact boundary-estimation accuracy.

Band power = ΣP[k] × Δf for bin centers low ≤ f < high; units FS². Power dB is
10 log10(power/(1 FS²)), so a full-scale sinusoid has −3.0103 dB power, distinct from
its 0 dBFS sample peak. Bands: 20–200 Hz, 200 Hz–2 kHz, 2–5, 5–10, 10–20,
20–30, 30–40, 40–60, 60–80, 80–100, 100–140 kHz. These adjacent bands can be summed
in linear units; do not add dB values. Their powers are not a calibrated acoustic SPL.
PSD is retained from DC to Nyquist; audible band tables omit <20 Hz. The median of
in-band PSD bins is a spectral-density statistic; tones/leakage/noise all affect it,
so it is not a validated stochastic noise-floor or noise-shaping classifier.

Unavailable whole bands (upper edge beyond converted Nyquist, or insufficient bins)
are Unsupported with null measurements; there is no extrapolation or partial-band
substitution. At 176400 Hz, bands 80–100 and 100–140 kHz are unavailable. At 352800,
those are observable in converted PCM; their faithful native-DSD preservation remains
Not validated. Conversion-filter suppression must not be interpreted as a source cutoff.
L−R = 10 log10(powerL/powerR) only if both powers are positive. Silence has zero linear
power and null dB meaning −infinity; undefined ratios remain null. No artificial floor
is inserted for very low-level signals. Plot omits exact-zero bins. Partial FFT tails
are omitted; retained overlap plus incomplete tail is reported in frames. Fewer than
one FFT window returns Unknown. Spectrum is stationary average, not a spectrogram.

Conversion Evidence remains Ambiguous when spectra exist, Unknown otherwise; origin
is always Unknown. No historical source-rate, native-DSD, converter identity, certainty
percentage or native PCM bit-depth test is implemented. Sparse music, intentional
filtering, noise shaping, DSP and conversion can all give similar spectral appearances.
No experimental origin classification is exposed.

## Verified and unverified scope

Actual local FFmpeg 9.0.2 tests cover generated DSF DSD64/128/256 stereo at both PCM
rates and DSD256 mono; DSF LSBF/MSBF pulse-density tone controls; generated uncompressed DFF/DSD64;
seeked position controls and full decoding. Streaming PSD is independently compared
against SciPy Welch, exact-tone power/Parseval, stereo gain/inversion, zero/tiny signals
and frequency-band applicability. Mocked failures validate error reporting only.
Generated patterns validate mechanics, not real-master provenance or forensic accuracy.
One explicitly supplied real DSD256 stereo DSF has now passed full decoding on both PCM
rates; this validates that case, not its historical origin. No real DST stream, SACD
extraction or diverse mastering corpus has been validated. Optional spectrogram and composite filter characterization remain
future work; ordinary PSD and band measurements are implemented.

Primary references: [FFmpeg 9 DSF demuxer](https://ffmpeg.org/doxygen/9.0/dsfdec_8c_source.html),
[FFmpeg 9 DSD decoder](https://ffmpeg.org/doxygen/9.0/dsddec_8c_source.html),
[SciPy Welch density conventions](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html).
Upstream source documents implementation; installed-backend tests establish the local
verified scope. It does not certify arbitrary decoder builds or filter behavior.
