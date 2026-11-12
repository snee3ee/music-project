# Logical tracks, CUE and SACD ISO — 0.2.5.dev0

General method `2026.11-v7`; logical source method `logical-source-2026.11-v1`.
Existing DSD conversion, duration policy, Origin and PCM signal algorithms remain.
The source layer is independent of Streamlit. Conclusions first, evidence second,
methodology on request is now part of the permanent objective-analysis standard.

## Sources, identity and time

`AudioSource` identifies a selected CUE interval or SACD area/track, with title,
performer, origin, underlying file, integer 75-fps boundaries and path/size/mtime
fingerprints. These fingerprints invalidate caches; they are not audio identity
hashes. Ordinary files retain the original `analyze()` entry point. Logical sources
use `analyze_source()` and return the same reusable Analysis/PCMContext models.

All measurements/plots use track-relative time. Each applicable scope additionally
records the source offset, declared offset, actual time grid, mapping and source
identity. Source time = track time + source offset. Combining scopes also checks the
logical source identity. Complete means the selected track, never the original
album-length file or the whole ISO. This distinction is visible in the overview and
formal decode conclusions. Original-source metadata and temporary representation
properties remain distinguishable in `logical_source` evidence and Technical Appendix.
External-reference comparison of logical tracks is explicitly Unsupported. The ordinary
file reference workflow is preserved; it is never silently run on an entire original
album when a logical track is selected.

## CUE parsing and boundaries

Parser input is bounded at 2 MiB and 99 FILE/TRACK declarations. Supported text:
UTF-8 with/without BOM, BOM-marked UTF-16, disclosed CP1251 fallback; an explicit
UTF-8/UTF-16/CP1251/CP1252 choice is available. Fallback does not authenticate character
encoding. Unresolvable decoding fails explicitly rather than replacing characters.

FILE declarations are advisory. The actual referenced audio is independently probed.
`FILE "Steely Dan - Aja.dff" WAVE` therefore resolves to DSD when the actual DFF
contains DSD; WAVE is not used to assert PCM. TITLE/PERFORMER, TRACK AUDIO and INDEX
01/00 are supported. REM is informational. Extra indexes are retained with explicit
unsupported-subtrack diagnostics. PREGAP/POSTGAP or unknown boundary-changing
constructs are not silently applied. FLAGS/ISRC/CATALOG/CDTEXTFILE are diagnosed,
not interpreted as audio transformations.

MM:SS:FF uses integer CD frames at 75/s; seconds must be below 60, frames below 75.
Track numbers/index ordering, duplicate indexes, INDEX00≤INDEX01, missing starts and
bounds outside actual source duration are checked. A missing next INDEX01 never
turns into an invented end-of-file boundary. Invalid/unavailable tracks are not
selectable. Repeated FILE declarations resolving to one audio file are Ambiguous,
preventing accidental overlapping album totals.

Boundary convention: INDEX01 to the next INDEX01 in the same FILE, or known audio
EOF for the last track of that FILE. Thus the next track's INDEX00 pregap belongs
to the preceding interval; initial pre-INDEX01 material is excluded. INDEX00 and its
duration remain available in evidence. No synthetic pregap audio is inserted.
Multi-file indexes reset per FILE; source durations are never summed twice by an
implicit end-of-album assumption. Boundary precision is the CUE grid, not evidence
of a particular mastering edit.

Paths resolve relative to CUE. Exact names take priority; case/Unicode normalization
fallback requires a unique matching filename. Missing and ambiguous references have
different statuses; no extension/name similarity search is performed. NUL, invalid
path syntax and alternate stream syntax are rejected. Resolved paths, including
symlink/junction destinations, must remain under the CUE directory or explicitly
authorized absolute external directories. The UI requires the user to enter those
external directories; source selection does not grant access to a whole drive.

## Selected representations and cleanup

Only the selected track is materialized in an OS-owned temporary directory, removed
before returning or on failure/cancellation. No original audio is opened for writing.
No full album/ISO is copied to the repository. Temporary capacity is checked against
free disk space with a reserve and a configurable 4 GiB default estimated-track budget.
This uses bounded RAM, but still requires disk space for one native track, including
when Quick analysis examines only windows of that selected track.

Lossless PCM is trimmed at exact native sample indexes and written to lossless native
rate/channel WAV (8/16/24/32-bit integer or float64 as applicable). An integer-second
input seek with preroll avoids decoding an entire PCM album prefix; sample-accurate
trim follows. Non-grid PCM boundaries round upward to the next native sample; actual
frame offsets and times are recorded. Selected-track decoding does not verify an
original album FLAC's whole-file MD5. Lossy CUE reference extraction is Unsupported.

Validated mono/stereo uncompressed DSF/DFF uses bounded packed-byte copying into DSF.
Channel order/native DSD rate are retained; MSB/LSB packing is normalized without PCM
conversion. Declared sample count excludes DSF block padding. Non-byte-aligned native
DSD starts, unvalidated native multichannel copying and DFF DST are Unsupported.
The unchanged DSD pipeline performs any subsequent disclosed PCM-derived measurements.

## SACD ISO and optional backend

2048-byte-sector images require SACDMTOC at sector 510, supported master version,
primary area pointers/sizes within file bounds, TWOCHTOC/MULCHTOC headers and valid
audio sector/count fields. Reads are bounded. This validates selected structural
fields, not every sector, copy, checksum, encryption state or audio packet. Arbitrary
ISO9660 images and signature-only fabricated files do not become validated SACDs.
Raw-sector/encrypted/unusual or backup-only structures remain unsupported/unvalidated.

Area rate/encoding are read from actual header fields, independently of conversion:
supported frequency code 4 means DSD64; frame formats 2/3 are DSD, 0 is DST. Unknown
codes do not receive a guessed native rate. Stereo and multichannel metadata are
separate. Full DSD-derived signal analysis retains its mono/stereo applicability.

The optional `sacd_extract` adapter checks required help capabilities, invokes `-P`
in an isolated temporary working directory, parses track text/start/duration and
cross-checks area/channel/track counts against bounded structure reads. Incomplete,
overlapping or unknown print protocols fail explicitly. Only successful extraction
and subsequent analysis can establish a completed selected-track decode.

Extraction requests one area/track with `-2`/`-m`, `-s -c -t N -i ISO` and the supported
controlled output switch (`-y` on the validated build). Exactly one native DSF must
result. Its structure, rate, channels and duration are checked before the existing
DSD pipeline runs. TOC time precision/tolerance is one CD frame, plus native-sample
rounding. DST metadata recognition is distinct from requested backend decompression
and validated native output; real DST content is not covered by the supplied DSD ISO.
Command/log evidence stays in the appendix. Timeouts, cancellation and output failure
remove the owned temporary directory. No shell interpolation or remote-input mode is used.

The owner explicitly authorized download/execution of the official portable Windows
`sacd_extract 0.3.9.3-107` release. It lives under ignored `data/backends/`; no PATH,
registry, package-manager or system installation change was made. Default lookup uses
that exact project-local location when PATH lacks the tool; a user path can be set in
Settings. There is no automatic downloader in the application.

The release supplied no publisher digest. Recorded SHA-256 identifies downloaded
bytes, not independent publisher authentication. Upstream EuFlo `COPYING` is GPL v2;
source headers state v2-or-later. This is a license observation, not a completed
commercial redistribution audit. The executable is not included in tracked source.
Future distribution requires a reproducible/backend license and notice audit.

Primary sources inspected:

- [Official portable release](https://github.com/sacd-ripper/sacd-ripper/releases/tag/0.3.9.3).
- [Upstream print protocol](https://github.com/sacd-ripper/sacd-ripper/blob/master/libs/libsacd/scarletbook_print.c).
- [Upstream structure definitions](https://github.com/sacd-ripper/sacd-ripper/blob/master/libs/libsacd/scarletbook.h).
- [EuFlo license file](https://github.com/EuFlo/sacd-ripper/blob/master/COPYING).

[Executed synthetic and authorized real-file validation](CUE_SACD_VALIDATION.md).
