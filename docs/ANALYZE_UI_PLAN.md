# Analyze File restructuring — implementation plan

Scope: Analyze File only, preserving the current uncommitted 0.2.1 implementation.
Both supplied task documents are byte-identical (19,543 bytes) and end at section
17, “Quick and”; use their complete available requirements without inventing a tail.
One explicit real DSF path was supplied and is readable. No second audio path exists.

1. [x] Read project guidance, audio-forensics, Streamlit references, current models,
   result rendering, cache and development plan; execute baseline UI/DSD tests.
2. [x] Append ONLY FACTS. NO OPINIONS. policy, preserving existing instructions.
3. [x] Separate pure presentation transformations (statuses, warning grouping, scope)
   from result rendering. No changes to analytical thresholds or unrelated pages/DB.
4. [x] Replace fragmented output with persistent module navigation: Overview,
   Integrity, Measurements, Provenance, conditional DSD and Technical Appendix.
   Preserve file selection, quick/full/rate controls, preview and JSON export.
5. [x] Keep logs/commands/exact values in organized appendix; render supported measured
   bands with correct units and no invented floors/interpolation/quality ratings.
6. [x] Validate the explicitly supplied DSD256 read-only (quick/full, actual output
   rates/scope/warnings); preserve local full reports outside Git.
7. [x] Add unit/UI regression and no-redecode/no-repeated-FFT navigation checks;
   run full pytest, static checks and actual startup; document executed results.

Measurement categories: Measured, Verified, Derived, Inferred, Unknown/Ambiguous,
Not applicable, Unsupported, Not validated. Numerical/integrity states are independent
of historical provenance. PCM full integrity must not be invented from a prefix.
