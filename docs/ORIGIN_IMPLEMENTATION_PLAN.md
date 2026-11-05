# Audio Origin Investigator — implementation plan

Baseline app 0.2.2, method 2026.11-v4, DSD method v2. Baseline full run:
220 passed / 2 conditional skips (31.61 s, no real-fixture environment configured).
Only Pink Panther DSD256 is currently in test_audio; FEELS LIKE SUMMER and real DFF
are not supplied. Preserve all existing uncommitted work and reserved 0.3/0.4 roadmap.

1. [x] Read full task, guidance, methods, existing DSP/UI/tests and roadmap; run baseline.
2. [~] Read official FFmpeg/SciPy primary material; document derivations and failed
   Analog Devices/TI access. Broader cascaded-modulator literature remains open.
3. [x] Add controlled actual-backend conversion response calibration keyed by backend,
   native/output rates and method. No unmeasured Nyquist-wide passband assumption.
4. [x] Add read-only DSF/uncompressed-DFF native-bit reader and sampled native Welch PSD;
   validate bit order/channel layout/padding and independent spectral comparisons.
5. [x] Collect time-resolved PSD without extra converted audio passes; measure six
   candidate boundaries, slopes/transitions/continuity and noise-profile regimes.
6. [x] Evaluate explicit compatibility hypotheses with alternative causes and limits;
   retain research measurements and reject unreliable historical DSD-rate classification.
7. [x] Add optional reference workflow inside Analyze File with explicit conversions,
   alignment/gain/polarity/residual/spectral evidence; never infer chronology.
8. [x] Implement Everyday default and Expert views of identical results; active Origin
   report, useful plots, one uncertainty summary, actionable next steps and full evidence.
9. [x] Ground-truth/adversarial/unit/actual decoder/UI regression checks; actual DSD64,
   128, 256, 512 generated cases and available real file; before/after performance.
10. [x] Check clean startup and actual Edge-rendered Everyday/Expert UI; document scope,
    limitations, results and product direction. No Library/Compare/Archive UI edits.

Final implemented milestone: app0.2.3 / general method v5 / Origin v1 / calibration v1.
Actual end-to-end high-rate-filter control:33.9402 dB boundary, three temporal cells,
three independent native windows; no44.1k PCM stage. Controlled source-rate identities
are not inferred. Real DSF SHA-256 preserved. Generated120s DSD512646MiB full decode
Passed,14.792s /192.89MiB sampled Python+backend RSS. See ORIGIN_VALIDATION.md/.json.
15-second human comprehension metric remains unverified; rendered inspection executed.
Final full regression with real DSF enabled:261 passed /1 real-SACD skip (86.52s).
Ruff lint/format and compileall passed. Legacy DSD diagnostics now cross-reference
the executed Origin/response profile instead of presenting stale "Not implemented".

Design decisions: six historical PCM-bandwidth hypotheses are compatibility tests, not
source identifications. Native ±1 one-bit PSD is distinct from PCM-derived PSD. Both
capture current signal properties, without PCM bit-depth tests on DSD. Profile changes
are spectral-floor proxies, not unique modulator/source signatures. Full conversion
retains bounded temporal summaries; independent native checks use explicitly sampled
short windows. References are selected by the user and are not authenticated by selection.
