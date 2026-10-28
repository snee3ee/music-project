# Technical methodology — 2026.10-v2

Application 0.2.0. Each Analysis and Finding includes method version. Reports include
actual FFmpeg/ffprobe versions, input metadata and analysis scope. None of the methods
establish studio-master provenance or subjective sound quality. No calibrated probability
or heuristic confidence percentage is produced.

## Observations separated from inference — version 0.2

`Finding.status` retains its historical/applicability interpretation. New structured
`observations` describe only the measured property and reported scope. This is not a
reclassification of Ambiguous provenance as confirmed provenance. No historical Codec,
native 24-bit origin or exact Source rate is newly claimed.

- Cutoff / Nyquist boundary: Detected when the existing complete-band thresholds pass;
  Not detected when adequate reference occupancy and lower-band level permit the test,
  but the thresholds do not pass. Otherwise Insufficient data, with the reason displayed.
- Cutoff needs at least one full candidate band (first candidate 14 kHz, upper edge 15.2 kHz).
  Thus Sample rate ≤30.4 kHz is Not applicable, instead of an ambiguous historical conclusion.
  A boundary is excluded if c+1.2 kHz reaches Nyquist; partial upper bands are not used.
  Report and UI list only the actual checked candidates (e.g. 14–20 kHz at 44.1 kHz).
- Upper-band flags classify **median PSD**, not meaningful ultrasonic music content.
  Bands: 22.3–23.7 kHz, and 25 kHz…Nyquist−500 Hz. Above threshold means >−40 dB relative
  to mean reference PSD 1–8 kHz, Below threshold means ≤−40 dB. This reuses the existing
  spectral level threshold, not a calibrated provenance threshold. Narrow tones can be
  missed by a median; silence/missing reference and insufficient bins retain explicit uncertainty.
- 16-bit grid flag uses the unchanged exact 100% low-byte-zero rule and minimum 1,000 active
  samples. It is only a measured grid in the sampled population, not proof of padding history.
- Full-scale samples are counts at the existing digital-rail threshold, never a clipping verdict.
- True Peak above 0 dBTP is flagged from the full-stream backend estimate. Backend −infinity
  is stored separately from missing/NaN data so zero peak can be shown without invented uncertainty.
  Numeric JSON remains finite/null, with a separate state field. Undefined overs status is null.
- Zero Residual RMS after reliable Alignment is displayed as −infinity; a residual withheld
  due to unreliable Alignment is separately labelled, not shown as zero or identical PCM.

Mono Channel layout can be established from a single Channel. Unlabelled two-channel WAV/AIFF
uses their conventional stereo ordering, with `channel_layout_source="container convention"`
and a visible disclosure. Other unknown layouts remain unspecified; no general multichannel
layout inference is performed. Raw ffprobe output is preserved in `AudioInfo.raw`.

The default UI presents observations and explains historical limitations. Detailed tables
and JSON preserve the separate inference status and evidence. Method version incremented
to v2 for result/schema/applicability changes; suspicion thresholds are unchanged.

## Routing and input safety

ffprobe inspects container/codec, first audio stream, rate, layout, duration and tags;
filename extension selects only CUE/ISO handling and scan candidates. Audio extensions
are never proof of codec. PCM tests are blocked for dsd_* and dst. FFmpeg's dsd_* packed-byte
sample rate is multiplied by 8 to display the native bit rate; synthetic DSF/DFF fixtures
verify this with 2,822,400 Hz DSD64. DST native sample rate is Unknown (0 in machine data),
pending dedicated validation. No conversion-derived DSD measurements are implemented.

All subprocess commands use argument arrays, no shell, binary stdout and explicit UTF-8
replacement decoding for diagnostics. A timer kills and waits for timed-out processes.
PCM is streamed in 1 MiB blocks; text output is bounded, stderr kept in a temporary file
and its final 64 KiB read. Error output shown to users is bounded. Only file/pipe protocols
are permitted. Full decoding uses -xerror -err_detect explode, but cannot detect every
possible missing tail if a container tolerates it. Successful decode is not archival proof.

## Scope and numerical representation

PCM context: f64le, native rate, native channel order, no downmix, start at 0, default
30 s, configurable 1–120 s. Buffer at most 128 MiB; channel/rate limits are 32/768 kHz.
These limits bound decoded array size, not total process RAM (FFT/caching adds memory).
Actual frames, seconds and complete-file indicator are reported. Sampled findings never
describe unexamined later passages. Full-stream loudness/hashes may time out independently.

## Peaks and dynamics

Sample Peak = 20 log10(max |sample|); RMS = sqrt(mean(sample²)) over interleaved channels;
crest = 20 log10(peak/RMS). Silence has null dB values (−infinity, not zero dB).
Counts at full scale use threshold 1−2^(1−bits) for known integer PCM, otherwise 1.
These are sample counts, not clipping-event counts or proof of clipping. Positive and
negative integer rails differ by one quantization step; the symmetric threshold includes both.

Whole-stream loudness uses FFmpeg loudnorm's **input** measurements only, not its
normalized output: input_i LUFS, input_lra LU and input_tp dBTP. Output goes to null,
source is unchanged. Dynamic loudnorm uses a 192 kHz true-peak pipeline as described in
[FFmpeg filters documentation](https://ffmpeg.org/ffmpeg-filters.html#loudnorm).
This is backend-dependent measurement, not independently certified metering.
True Peak >0 dBTP is reported as an estimate above digital full scale, separate from
Sample Peak. Short/silent inputs may have undefined LUFS; LRA is not useful for all short clips.

## Spectrogram and average spectral evidence

Spectrogram: Hann, N=min(2048, available frames), 50% overlap, PSD density,
mean channel power (opposite-polarity channels do not cancel), time seconds, frequency kHz,
10 log10 PSD relative to a unit-amplitude digital sample, display −140…−20 dB/Hz.
At 48 kHz, Δf=23.4375 Hz; at 96 kHz, Δf=46.875 Hz. No provenance claims from the plot.

Average PSD: Welch Hann N=min(8192, frames), 50% overlap, density, channel powers averaged.
Reference = mean PSD in 1–8 kHz. Reference ≤1e−16 or duration <1 s yields Ambiguous.
Require ≥50% of reference-band bins above −30 dB relative to reference for a broadband control.
Reference occupancy helps reject sparse signals; it is not a music/codec classifier.

For candidates c=14,15,…21 kHz below Nyquist−1.2 kHz, median PSD in
[c−1200,c−300] and [c+300,c+1200] Hz defines adjacent-band drop. At least three bins required.
Strong evidence requires lower band >−35 dB, upper band ≤−40 dB, drop ≥20 dB, occupancy ≥0.5.
The largest-drop candidate is reported with drop/1.5 kHz as a coarse adjacent-band slope.
This is not a fitted physical transition width. Evidence returns **Medium suspicion**;
otherwise **Ambiguous**. High suspicion/Low suspicion are intentionally not emitted by
this single-evidence implementation; no independent codec-artifact detector is validated.

For lossless PCM >48 kHz the same rule tests c=22.05/24 kHz. Also report median relative
PSD 22.3–23.7 kHz and 25 kHz…Nyquist−500 Hz. At ≤48 kHz: Not applicable.
Historical source rate remains Unknown, including when a boundary is detected.
Content above 22.05 kHz may include noise or DSP products and cannot establish 48 kHz origin.

False positives: intentional mastering filters, recording/instrument bandwidth and native
band-limited material. A generated lossless 16 kHz brick-wall control deliberately produces
the same evidence without ever using a lossy codec. False negatives: broad transitions,
high bitrate codecs, noise/dither above a boundary, later DSP and cutoff outside candidate bands.
Default scipy polyphase 44.1/48→96 kHz fixtures return Ambiguous; sharp FFT-resampled
positive controls return Medium suspicion. Silence, tones, short clips and lowpass negative
controls remain uncertain. MP3 128/320→FLAC regression controls do not force historical labels.
Thresholds are exploratory engineering rules, not calibrated on a real-music corpus.

## 24-bit quantization

Only known lossless integer 24-bit PCM. Exact signed integer = round(f64 ×2^23).
Zero samples excluded; deterministic stride caps the interleaved population at 1,000,000.
Fewer than 1,000 active analyzed samples: Ambiguous. Count low byte (integer &255),
zero-byte percentage, distinct low bytes, distinct sample values and Shannon H=−Σp log2(p).
Normalized H=H/8. Entire sampled active population low byte zero → Direct 16→24 padding
evidence, meaning a measured grid compatible with padding, not a proven conversion history.
Otherwise No direct-padding evidence. No tolerance threshold is silently substituted for 100%.

Distinct-level compatibility ≤65,536 is a pooled output-count statistic. It only constrains
some simple global one-to-one maps; per-channel maps, time-dependent processing, filters,
dither and gain invalidate a historical inference. High entropy never proves native 24-bit.
Tests include padded integers, random native-like 24-bit, 16-bit+dither/gain/filter,
silence and small samples. The UI collapses Quantization Structure by default.

## Exact identity, duplicates and storage

File identity: SHA-256 over every byte, 1 MiB chunks. Even undecodable identical files can
be byte duplicates. Decoder success is a separate property.

Canonical identity pcm-s32le-v1: only verified integer lossless encodings with known
8/16/24/32-bit depth. FFmpeg first audio stream → signed left-aligned s32le, same rate,
channel count/order, no gain, resampling, dither or downmix. SHA-256 input is sorted-key JSON
{version, rate, channels, layout}, UTF-8, then NUL byte and all PCM bytes. Source bit depth is
not in header: exact 16-bit padding to 24-bit yields identical canonical samples.
Single-channel layout is normalized to mono; unlabelled two-channel WAV/AIFF uses the
conventional stereo order. Other unknown multi-channel layouts remain distinct, which may
cause conservative false negatives.
Float PCM and WavPack/hybrid identity are not supported. WavPack mode is not assumed lossless
from codec name alone. DSD is excluded. No claim beyond this canonical representation.

Groups deduplicate physical path strings across overlapping indexed roots. Same file hardlinks
and filesystem compression are not recognized, so logical redundant bytes are not guaranteed
physical disk savings. Redundant bytes = sum(size)−min(size) within each group. Byte/PCM groups
overlap; their storage figures must not be added. No removal or cleanup execution exists.

## Incremental indexing and metadata

SQLite stores root/path, size, mtime_ns, UTC index time, method version, actual probe,
file hash, optional PCM hash and full-decode result/error. Incremental reuses records when
size+mtime_ns, method and PCM-hash option match. This can miss edits preserving size/mtime;
use force scan or archive verification for stronger assurance. Backend-setting changes should
also be followed by force scan. File mutation during scan invalidates its hash result.
Removed files remain marked in database. Scan cancellation callback is checked between files;
no UI cancel button yet. Directory access failure aborts before removal reconciliation.
File failures continue and are shown as unreadable/unsupported, never automatically as corruption.

Album grouping is folder+album tag, not release identity. Missing artist/album/title/track,
duplicate literal disc:track tags and differences in codec/rate/depth/layout/channels,
album-artist/date/disc tags are observations. Multi-disc subfolders may stay separate.
Numeral normalization, artwork size/presence, filename consistency and album loudness/
forensic-status audits are pending. Nothing edits tags.

## Integrity manifests

Schema music-project-sha256-v1: relative POSIX path, size, SHA-256, version/time metadata.
All regular files, including covers and CUE, are included; symlinks/junctions are skipped.
Reject parent traversal, drive/UNC/absolute paths, alternate streams, NUL, duplicates and
resolutions outside selected root. Windows casefold is used. No manifest signature or
tamper-proof origin claim; a trusted independent copy is needed against malicious rewriting.
Different size+hash → Modified; same-size changed hash → Hash mismatch; others as labelled.
No optional decoded hash is yet included in archive manifests. Creation fails if a file cannot
be read; it does not silently omit it. Verification reports individual unreadable files.

## Objective comparison

Equal rate/count/layout only. Compare bounded prefixes, no implicit resampling. Most energetic
channel drives FFT cross-correlation, integer lag within min(±2 s, half shorter prefix).
Then use all channels in overlap for least-squares scalar gain, polarity and normalized dot
product. Residual yy−gain·xx is interpreted only for |correlation|≥0.9, |gain|>1e−12 and
alignment peak uniqueness ≥0.01 (or identical complete prefix arrays). Uniqueness compares
strongest competitor outside ±max(2 samples,1 ms) around selected lag. These are documented
engineering guards, not calibrated match confidence. Ambiguous residual values are null.
Correlation itself is still shown with uncertainty. Zero-lag identical arrays and aligned
overlap equality are explicitly separate; neither is a whole-file hash proof.

Periodic inputs, sub-sample offsets, drift, EQ, limited overlap or differing masters can defeat
alignment. Tests cover gain/polarity/offset, EQ/clipping, unrelated signals, periodic ambiguity,
silence and incompatible rates. Whole-file LUFS/TP and prefix peaks have different scopes.
Album comparison and spectral-difference metrics are pending.

## Disc and device boundaries

CUE parser handles UTF-8 BOM or explicit CP1251 fallback (displayed), FILE references under
CUE directory, TITLE/PERFORMER, TRACK, INDEX in integer CD frames (75/s). Missing/escaping
references, invalid timestamps, duplicate track numbers and non-increasing INDEX 01 are flagged.
No extraction, duration validation against audio or logical-track analysis is implemented.

ISO checks 8-byte SACDMTOC at sector 510×2048 and CD001 at sector 16×2048+1 without copying
the image. A signature is recognition evidence, not validated SACD track/TOC support. Raw sectors
and encrypted images remain unverified. Optional sacd_extract command plan uses validated
track range 1…255, distinct output directory and DSF/DST conversion flags from
[upstream command help](https://github.com/netxing/sacd_extract/blob/main/tools/sacd_extract/main.c).
Backend variants have different flags; command planning is tested but execution/temporary
extraction cleanup is pending. No real-backend integration is claimed.

Device profiles check explicit codec, channel count, rate/depth and DSD-rate constraints.
Unknown properties remain Unknown; profiles do not certify actual hardware playback.

## Validation limits

Only generated signals/containers and local backend integration have been used. No private
collection was accessed. No diverse real-recording corpus, metering certification, native
DSD spectral validation, real SACD image, browser rendering test or calibrated classification
study has been performed. See DEVELOPMENT_PLAN.md for actual executed verification.
