# DSF/DFF duration correctness — implementation plan

1. [x] Inspect current models/probe/DSD/UI, guidance and baseline tests; read original
   DSF fields and independently inspect ID3/artwork read-only.
2. [x] Verify ffprobe estimation mechanism with controlled backend tests and numerical
   decomposition; preserve source SHA-256 and record evidence.
3. [x] Centralize typed duration evidence and selection for DSF/uncompressed DFF;
   retain secondary ffprobe estimates, distinguish structure-derived from verified
   full decode, avoid promoting quick or failed/unsupported results.
4. [x] Expose selected audio duration and source/status consistently in probe/results/UI;
   place estimates/precise discrepancies in technical diagnostics. Preserve saved models.
5. [x] Add known-ground-truth DSF metadata/padding/artwork and DFF duration tests,
   including invalid metadata, short/failed/mismatching decode and UI regressions.
6. [x] Run real-file full validation, full regressions/static checks and actual startup;
   update methodology/versions/ledger without changing user audio or unrelated work.

Observed original: sample count 2,642,067,456 / 11,289,600 = 234.026666667 s;
payload 660,520,960 bytes, valid packed bytes 660,516,864, padding 4,096 bytes;
metadata at 660,521,052 with 5,230,592 trailing bytes. Mutagen independently reports
234.026666667 s. Embedded APIC front cover is JPEG, 3000x3000, 5,229,518 bytes.
ID3 bytes and artwork are not copied into tracked files or uploaded.

Direct upstream source retrieval was unavailable; no source-level details are claimed.
Cause is established from actual file byte accounting and six controlled backend cases.
Executed results and policy: [DSF_DURATION_VALIDATION.md](DSF_DURATION_VALIDATION.md).
