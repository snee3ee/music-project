# Supported formats — 0.2.5.dev0

Verified means an automated synthetic fixture was actually probed/decoded with the local
FFmpeg 9.0.2 backend. It does not establish every variant, bit depth or channel layout.
No support is claimed from a filename extension. Scanner extensions are candidate filters.

Lossy source investigation now includes lossless mono/stereo native PCM at
32/44.1/48/88.2/96/176.4/192kHz, independently of Hi-Res status. Native DSD/current
lossy streams and other rates/layouts are explicitly Not evaluated for this PCM-only
question. Per-band/adaptive-window observations do not prove codec history; actual
MP3/AAC and legitimate non-lossy controls expose false positives/negatives.
[Scope, empirical matrix and supplied16/44.1 FLAC](docs/LOSSY_VALIDATION.md).

Analyze File now adds full/prefix native-rate PCM technical metrics for known mono,
stereo, 5.0/5.1 layouts (actual multichannel integration:5.1). Reconstructed True Peak
is tested at44.1/48/88.2/96/176.4/192 kHz; other rates retain applicable levels/loudness
but TP/headroom remain Not validated. Native FLAC STREAMINFO MD5 is verified for
8/16/24/32-bit mono/stereo known-PCM controls. Independent RFC9639 verbatim fixtures,
rather than an encoder's requested setting, establish actual depth and decoded low bits.
Non-byte-aligned depths and non-native/unsupported FLAC wrappers remain explicitly
unvalidated/unsupported. Full decode, embedded digest and container coverage are
separate statuses; missing digest and clean whole-frame truncation are tested.

| Format | Verified scope | Limitations |
|---|---|---|
| WAV / integer PCM | 16/24-bit mono generated files, decode, Unicode paths, hashes, measurements | RF64/BWF and other channel/depth variants untested |
| FLAC | Encode/decode16/24-bit; independent verbatim8/16/24/32-bit mono/stereo actual decoding, exact PCM/MD5/count; tags, PCM identity, MP3→FLAC controls | No proof of earlier lossless history; non-byte-aligned MD5 and unusual wrappers unvalidated |
| MP3 | libmp3lame 128/320 kbps generated controls, full decode | No exact PCM duplicate hash, PCM bit-depth N/A |
| ALAC / M4A | Generated ALAC encode/decode | Other M4A streams are detected by actual codec; AAC variant untested |
| AIFF | Generated signed 16-bit big endian decode | AIFC variants untested |
| Ogg Vorbis | Generated encode/decode | No exact PCM hash, bitrate is not a quality score |
| Opus | Generated encode/decode | No exact PCM hash |
| DSF | Generated DSD64/128/256/512; one real DSD256 stereo DSF; strict structure/full/seeked decode; 176.4/352.8 kHz output headers and 33-point response controls for each rate; LSBF/MSBF native reads and independent native PSD; bandwidth/noise investigations | Discrete response controls do not certify a continuous passband; no historical-rate identity classifier; multichannel investigation Unsupported; no playback |
| DFF / DSDIFF | Generated native controls and supplied Aja uncompressed stereo DSD64 DFF, native structure/duration, actual selected-track full decode through CUE | Real DFF DST decoding remains unvalidated/unsupported; metadata recognition is distinct from decoding |
| CUE | Single/multi-file resolver, UTF-8/UTF-16/CP1251, Unicode, INDEX01/00 and 75-fps boundaries; actual WAV/FLAC interval analysis, DSF/DFF native-bit copy, real seven-track Aja DFF/CUE analysis | External references require explicit directory authorization; ambiguous/unsupported bounds are not guessed; lossy references and DFF DST track extraction unsupported |
| SACD ISO | Real Aja master/area checks, actual seven-track stereo DSD64 enumeration, native single-track extraction and full DSD pipeline with authorized sacd_extract 0.3.9.3-107 | Real DST and multichannel signal analysis unvalidated; raw/encrypted/backup-only structures unsupported; header checks are not a full ISO audit |
| ISO9660 / other ISO | Signature or Unknown image | Never treated as an ordinary audio codec |

Backend-dependent, **untested**: WavPack, APE, TAK, TTA, CAF, Matroska audio,
AAC, WMA, BWF, RF64, AIFC, DST and unusual sample formats. They may probe/decode if the
installed FFmpeg supports their actual streams. WavPack's lossless/hybrid mode is not
inferred from codec name, so forensic lossless/canonical-identity claims are excluded.
Float PCM can be measured but is excluded from integer bit-depth/canonical hash tests.

Other ffprobe-readable audio files can be entered manually in the file analyzer;
the recursive scanner uses the documented extension set in `core/files.py`.
Unknown or missing decoders produce explicit messages. Unsupported containers are
not automatically described as corrupted.

Optional backends:

- **sacd_extract:** optional compatible CLI. Actual 0.3.9.3-107 portable Windows execution
  validated against explicitly authorized Aja ISO; downloaded only with owner permission
  into ignored data/backends/, without PATH/system changes. No in-app automatic download.
  Other installations can set a path in Settings. Missing/incompatible protocols fail explicitly.
- **fpcalc / Chromaprint:** standalone executable absent. No acoustic grouping currently.
  The FFmpeg build advertises Chromaprint, but the application does not equate that with
  a validated similarity feature.
- **MusicBrainz / AcoustID:** no network adapter enabled.

Commercial distribution requires a dependency/tool license and redistribution audit.
The inspected Gyan FFmpeg build is configured with GPL/version3 flags; it must not be
assumed suitable for arbitrary proprietary bundling without review.

See [DSD methodology](docs/DSD_METHODOLOGY.md) for exact pipeline, frequency-band
applicability, duration tolerances, scope, warning semantics and known validation gaps.
No DSD origin classifier, native DSD bit-depth test or source-rate detector is claimed.
Logical-source methods and executed matrix: [CUE/SACD methods](docs/CUE_SACD_METHODS.md),
[validation](docs/CUE_SACD_VALIDATION.md).
Current engineering controls, real-file rechecks, unsupported capabilities and commands:
[V1 validation matrix](docs/V1_VALIDATION_MATRIX.md).
Real DSD256 and restructured UI verification: [Analyze File validation](docs/ANALYZE_UI_VALIDATION.md).
Duration policy now selects validated DSF sample-count / uncompressed DFF audio-payload
duration, independently retaining ffprobe's secondary estimate; full decode can corroborate
the result as Verified. Details: [DSF duration investigation](docs/DSF_DURATION_VALIDATION.md).
