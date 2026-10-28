# Supported formats — 0.2.0

Verified means an automated synthetic fixture was actually probed/decoded with the local
FFmpeg 9.0.2 backend. It does not establish every variant, bit depth or channel layout.
No support is claimed from a filename extension. Scanner extensions are candidate filters.

| Format | Verified scope | Limitations |
|---|---|---|
| WAV / integer PCM | 16/24-bit mono generated files, decode, Unicode paths, hashes, measurements | RF64/BWF and other channel/depth variants untested |
| FLAC | Encode/decode 16-bit, tags, PCM identity, MP3→FLAC controls | No proof of earlier lossless history |
| MP3 | libmp3lame 128/320 kbps generated controls, full decode | No exact PCM duplicate hash, PCM bit-depth N/A |
| ALAC / M4A | Generated ALAC encode/decode | Other M4A streams are detected by actual codec; AAC variant untested |
| AIFF | Generated signed 16-bit big endian decode | AIFC variants untested |
| Ogg Vorbis | Generated encode/decode | No exact PCM hash, bitrate is not a quality score |
| Opus | Generated encode/decode | No exact PCM hash |
| DSF | Synthetic DSD64 stereo container metadata, native-rate calculation/routing | No real recordings or DSD measurements; no playback |
| DFF / DSDIFF | Synthetic uncompressed DSD64 stereo metadata/routing | DST-compressed DFF untested; native DST rate Unknown |
| CUE | UTF-8 metadata, file references, 75-fps INDEX validation | Audio resolution/splitting and logical-track analysis pending; CP1251 fallback is disclosed |
| SACD ISO | Synthetic signature recognition and command-plan/missing-backend tests | Actual TOC/areas/tracks/extraction unsupported in UI; real integration skipped |
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

- **sacd_extract:** absent in the inspected environment. No automatic download. Adapter
  currently recognizes status and produces a command plan; real execution remains unverified.
- **fpcalc / Chromaprint:** standalone executable absent. No acoustic grouping currently.
  The FFmpeg build advertises Chromaprint, but the application does not equate that with
  a validated similarity feature.
- **MusicBrainz / AcoustID:** no network adapter enabled.

Commercial distribution requires a dependency/tool license and redistribution audit.
The inspected Gyan FFmpeg build is configured with GPL/version3 flags; it must not be
assumed suitable for arbitrary proprietary bundling without review.
