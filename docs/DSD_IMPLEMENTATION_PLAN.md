# DSD Signal Diagnostics — implementation plan

Compatible extension of 0.2; preserve the reserved 0.3/0.4 roadmap and all PCM tools.
No Audio Time Machine implementation was found in this checkout; preserve existing code.

1. [x] Inspect instructions, skills, metadata/decoder/models, UI, tests and roadmap.
2. [x] Add bounded DSF/DFF structural inspection and explicit duration evidence.
3. [x] Add streaming, self-describing FFmpeg float PCM conversion; validate output
   rate/channels; separate warnings, fatal errors, scope and container failures.
4. [x] Add streaming Welch PSD and band/channel measurements; retain Unknown/Ambiguous
   provenance. Document conversion dependence and unavailable frequency ranges.
5. [x] Integrate quick/full controls and diagnostics into Analyze File, with caching
   keyed by identity, method, backend and settings; keep PCM analysis intact.
6. [x] Test controlled signals/failures, generated DSF/DFF with actual FFmpeg,
   UI integration and full regressions. Explicitly skip unavailable real recordings.
7. [x] Update methodology, formats, README, versions and validation ledger; verify
   server startup and report exact verified scope and remaining limitations.

Expanded task: [engineering audit](ENGINEERING_AUDIT.md) records verified defects in
PCM sampling, comparison, optional loudness, subprocess diagnostics, index cancellation
and backend/cache identities. Fixes have regression coverage. Generated 20 s and
240 s / 646 MiB DSD256 benchmarks executed, including actual decoder counts and
Python/child RSS sampling. No before/after speedup claim is made.

Design: original files opened read-only; no user audio copied/uploaded. DSF sample
count versus padded blocks and DFF data length are independent duration evidence.
Quick uses three non-overlapping deterministic windows (up to 5 s each), separate
seeked decodes with preroll; full uses one streaming decode to EOF. Header validation
is always whole-container structure, whereas decoding scope is explicit. Welch uses
periodic Hann, fixed FFT length, 50% overlap, linear power averaging per channel and
one-sided density scaling; never PCM bit-depth tests on native DSD. No origin classifier.
