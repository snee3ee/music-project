# Evidence-Based Conclusions Engine - implementation plan (2026-11-10)

Baseline app 0.2.3 / general method v5, owner WIP commit4925de7; only probe files
untracked. Baseline executed:260 passed /2 conditional skips,82.70s. Existing Origin
is preserved. Sad Girl is absent from authorized test_audio; only supplied Pink Panther.

1. [x] Read request, AGENTS/audio-forensics/Streamlit skill, audit models/DSP/UI/tests,
   inspect scopes/backend code and official ITU/EBU/FLAC documents, run baseline.
2. [ ] Introduce typed scopes and conclusions with deterministic versioned rules,
   explicit validity, applicability, units, references, evidence and limitations.
3. [ ] Bounded streaming full/prefix PCM metrics: momentary/short-term/integrated/LRA,
   sample peaks/RMS/crest/event counts, reconstructed peaks with validated precision.
4. [ ] Add scope-matched peak/headroom/PLR and non-destructive reference/gain planning.
5. [ ] Add exact clipping observations and possible plateau investigation; retain ambiguity.
6. [ ] Integrate full-pass decoding evidence and native-FLAC STREAMINFO MD5 verification.
7. [ ] Add Technical Findings and optional custom references to Everyday/Expert;
   timeline evidence and scope; preserve modular navigation and Origin.
8. [ ] Ground-truth, independent metering, invalid/absent/mismatched scope, near ceiling,
   natural plateau, Unicode/FLAC/DSD/UI/cache and performance tests; full regression.
9. [ ] Actual startup/rendered verification, at least3 generated real conclusions,
   documentation/policy updates and precise implemented/validated/incomplete report.

Design: preserve legacy prefix measurements and Origin. Full technical analysis reuses
one additional decode (replacing legacy full loudnorm). Full PCM f64 remains bounded;
frame metadata and plot envelopes bounded, counts cover all examined frames. DSD uses
its existing distinct domain; no PCM bit-depth/rail history tests on native DSD. Selected
reference changes only deterministic calculations, not decoded/measurement cache.
No platform target is selected implicitly. Compliance is not inferred from a backend name.
