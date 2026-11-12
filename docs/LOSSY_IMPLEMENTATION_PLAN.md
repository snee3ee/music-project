# Lossy source investigation — 2026-11-12

Extend the existing Analysis/Finding and Origin UI; preserve previous UI and all
DSD/Hi-Res/integrity/loudness behavior. Application remains0.2.5.dev0; method identity
will change for the new measured facts/cache invalidation. User impressions and the
supplied Tochki metering numbers are motivation, not known encoding history.

- [x] Audit instructions, methods, existing PCM/Origin/streaming/UI/result contracts.
- [x] Execute fresh full baseline with existing authorized real DSF/SACD fixtures.
- [x] Add typed bounded native-rate PCM bandwidth/time-window measurements reusing
  Welch/boundary utilities and the existing technical decode. Preserve measured
  facts independently of interpretations; explicit eligibility/exclusion reasons.
- [x] Generate deterministic A/B/C/D dataset: original lossless/round-trips, actual
  available MP3/AAC histories, difficult non-lossy controls, processed known losses.
  Evaluate empirical detection/false positives/abstentions and additional metric
  feasibility; no real-world accuracy or codec confidence inferred from synthetic data.
- [x] Implement only defensible interpretation/abstention, independently of integrity,
  Hi-Res and loudness. Candidate cutoff alone cannot establish previous encoding.
- [x] Integrate Normal/Expert evidence into existing Origin page, retaining plots,
  accessible methods/raw data and no repeated decode on view switches.
- [x] Run regression/static/startup/actual rendered inspections; record performance,
  scope, dataset limitations and reproducible Tochki instructions.

Existing reusable components: PCMContext, native float64 technical streaming pass,
StreamingWelch, boundary_features, per-channel Origin evidence, Finding/Analysis,
versioned cache identity, existing Appendix JSON and two presentation modes.

No original audio changes, uploads, broad personal-drive searches, new dependencies,
untrusted executables, Git history changes or push. Only Pink Panther is present in
test_audio initially; the owner subsequently supplied and authorized the Downloads FLAC.

Baseline executed:418passed/1failed in137.34s. The failure is the stale explicitly set
SACD fixture path `E:\Music (Hi-Res)\Steely Dan\Aja.iso`, now unavailable (WinError3),
not a decoder regression. Final tests will enable real fixtures only when present and
explicitly record the unavailable real-ISO skip. Existing real DSF passed.

Owner supplied and authorized the exact Downloads FLAC. Actual probe:
18,967,763bytes,140.293333s,FLAC16/44.1kHz stereo. It is not assumed to have a known
encoding history. Actual full analysis completed read-only and SHA-256 matched.

Milestones executed:

-16initial measurement/abstention tests passed;80Origin/conclusions/UI tests passed;
 74lossy/source/metering/scope tests passed;26lossy/Expert-navigation tests passed.
-Final A/B/C/D corpus:106cases (A22/B40/C20/D24), both actual MP3/AAC encoders and
 alternate stereo/AAC coder configurations available,0skipped. Spectral observations
 in49/64known-lossy cases and4/42non-lossy cases. Naive historical classification is
 not deployed. Flux/pre-post-energy overlap controls reject additional codec claims.
-Actual supplied FLAC:32/32eligible windows,64s sampled;21425.537109375Hz transition
 candidate, per-channel global contrasts40.0056/33.2365dB, both recur32/32windows.
 Conclusion Inconclusive, historical codec Unknown. Actual Integrated-6.978LUFS,
 LRA5.29LU,TP+0.742088dBTP,SP0dBFS,RMS-10.083410dBFS,Crest10.083410dB and
 rail counts37+158=195. Embedded PCM MD5Verified; original bytes unchanged.
-Full regression:444passed,0failed,1real-ISO skip;149.24s. Real DSF enabled/passed.
 Browser sandbox could not launch GPU under the restricted terminal; authorized
 local Edge rerun retains browser sandbox. Harness Unicode/selectbox waits were
 corrected; six actual inputs rendered successfully, with0main app exceptions/JSON.
-Final complete suite444passed/1explicit real-ISO skip in142.14s. The last caption
 clarifies maximum **window** contrast versus aggregate;9UI tests passed afterward
 in15.38s, and real-file views were rerendered/inspected. Ruff113files/format,
 compileall/pip check/47core imports passed. Streamlit root/health HTTP200.
-Actual Normal views and Expert bands/candidates/windows/methods/existing spectrum
 were inspected. SHA-256/stat of the original FLAC remain unchanged; real DSF hash
 matches prior record. Generated cases/reports/screenshots and test_audio are ignored.
 Docs/JSON contain the complete dataset/limitations, changed files and test commands.

Session complete; this does not establish v1.0, a unique historical codec classifier,
real-world accuracy, or full standards compliance. No additional lossy metric was
forced into production when the controlled experiments did not support attribution.

Final plot scope/applicability review:9UI tests passed in9.45s; the old PCM graph now
states its actual prefix coverage, and no unavailable time-boundary selector is shown.
Real-file spectrum rerendered and visually inspected; source hash/stat unchanged.
