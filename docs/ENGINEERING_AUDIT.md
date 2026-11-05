# Engineering audit — 2026-11-05

Baseline: app 0.2.0 / PCM method 2026.10-v2. No Audio Time Machine implementation
or snapshot database exists in this checkout. Preserve the reserved roadmap.
Read AGENTS.md, audio-forensics, development plan, all analytical/decoder/index/
archive modules and relevant tests. No user collection inspected.

## Verified defects to address

| Severity | Evidence in baseline | Correction / regression |
|---|---|---|
| High | DSD analysis returns metadata only; combined DST/conversion limitation | Separate structural, decode, conversion, PSD and provenance results |
| High | Library reuses failed/backend-dependent records when decoder settings change | Persist backend identity/settings fingerprint in existing JSON payload; older records refresh explicitly |
| High | Cancellation is checked only inside file loop, so an empty/completed traversal can reconcile removals despite cancellation | Recheck before removal transaction |
| Medium | Quantization strides interleaved samples; even strides can sample only one stereo channel | Sample each channel independently with a documented per-channel budget |
| Medium | Comparison divides by zero if aligned overlap has no energy; unknown multichannel layouts can be compared as if ordered | Guard overlap energies, unknown order and invalid parameters |
| Medium | Decoder stderr is disk-backed and can grow without bound | Drain stderr concurrently into bounded diagnostic tail; preserve fatal/warning separation |
| Medium | Analyzer cache lacks method/backend identity, mutation checks and force bypass | Include identities/settings; verify source stability and provide explicit refresh |
| Medium | Malformed loudnorm JSON/numbers escape the optional-analysis error boundary | Validate backend values and preserve basic metadata/peaks when loudness is Unknown |
| Medium | DSD bitrate display can mix container throughput with nominal 1-bit/channel rate | Label native rate × channels separately from container bitrate |

## Reviewed existing behavior

PCM Welch uses density scaling and channel-power averaging, avoiding inverted-stereo
cancellation. Existing cutoff and Nyquist rules retain Unknown source rate and
documented alternative causes. They remain exploratory, without calibrated
probabilities or real-corpus error rates. Padding/entropy establishes a sampled grid,
not native bit depth. Loudnorm input statistics discard normalized output; no source
edits. True Peak is a backend estimate, not an independently certified meter.

SQLite uses per-file transactions, closed connections and rejects future schemas;
interrupted scans retain committed rows and reconcile removed files only on completed
traversal. Exact byte duplicates include undecodable files; decoded identity is
restricted to lossless integer PCM. Manifest paths reject traversal and originals
are read-only. No schema change or second database is needed.

## Remaining risks / scientific gaps

Size/mtime identity can miss deliberate timestamp-preserving edits; force analysis/
scan and independent archive hashes remain necessary. No real-recording forensic
corpus, certified loudness reference, rendered-browser test, long-collection crash/
concurrency stress test, physical-storage/hardlink accounting or native SACD/DST
validation exists. PCM prefix memory is bounded but temporary DSP arrays exceed the
decoded-buffer budget; do not describe that budget as whole-process RSS.

The above corrections are implemented with regression coverage. Executed checks and
measured performance: [validation ledger](VALIDATION_0_2_1.md). No PCM cutoff/padding
thresholds were loosened and no provenance classification was added.
