
---
name: audio-forensics
description: Validate audio forensic algorithms, signal-processing methods, technical classifications, and known-ground-truth tests in Music Project.
---

# Audio Forensics Validation

Use this skill when implementing, changing or reviewing:

- lossy-to-lossless transcode detection;
- high-frequency cutoff analysis;
- upsampling detection;
- source-rate classification;
- bit-depth provenance analysis;
- quantization and dithering analysis;
- PCM/DSD analysis;
- clipping and True Peak measurements;
- audio identity and fingerprint comparison.

## Required workflow

1. Identify the measurable signal property.
2. Distinguish direct measurement from inference.
3. State the hypothesis being tested.
4. Define valid input formats and applicability.
5. Document the numerical method and thresholds.
6. Identify potential false positives and false negatives.
7. Generate known-ground-truth synthetic tests.
8. Test cases that should return Ambiguous.
9. Execute tests.
10. Integrate validated output into the UI.
11. Document what the result can and cannot establish.

## Critical rules

A detected codec is not proof of source provenance.

Absence of lossy artifacts is not proof of original lossless audio.

High lower-byte entropy does not establish native 24-bit origin.

DSP, gain, filtering and dither may erase previous quantization structure.

Do not apply ordinary PCM algorithms directly to DSD.

Never report an unsupported inference as a confirmed fact.

Use uncertainty explicitly when historical information is unrecoverable.

## Expected output

For each implemented algorithm provide:

- measurements;
- applicable formats;
- heuristic status;
- evidence;
- confidence where justified;
- limitations;
- automated test results.

If a method fails validation, revise it or classify the result as inconclusive.

Do not invent certainty.
