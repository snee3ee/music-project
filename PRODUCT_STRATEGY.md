# Product strategy

Music Project is a local-first Audio Library Intelligence application. Its recurring value
is maintaining a trustworthy inventory: incremental audits after additions, byte/PCM duplicate
inspection, device constraint checks, backup/transfer verification and objective release comparison.
The product does not assign subjective sound scores or certify signal provenance.

## Users and workflows

Collectors: understand formats, tags, storage and repeated copies. Archivists: create portable
manifests and verify transfers. Engineers: inspect scope-aware measurements and compare versions.
DSD/SACD users: eventually inspect disc structures with separately validated backends.

The current foundation includes functional local scan/analyze/compare/verify slices with a
Russian UI. It is not commercially finished. See DEVELOPMENT_PLAN.md for explicit gaps.

## Future editions and boundaries

Possible Free edition: single-file overview, basic spectrum and small collection integrity.
Possible Pro edition: large persistent libraries, acoustic grouping, archive automation,
album comparison, watch folders, device conversion planning and validated DSD/SACD workflows.
No payments, advertising, cloud login or artificial limitations are implemented now.

`core/entitlements.py` exposes an independent policy object permitting all development
capabilities. Future UI/workflow policy may consult entitlements; analytical methods must
remain independent and produce the same truthful result in every edition. Licensing must
never alter measurements, uncertainty or technical conclusions. The present object is a
boundary for future work, not a secure licensing system.

## Architecture and persistence

Typed dataclasses and core services are independent from Streamlit. A future desktop/API
frontend can use the same engine. SQLite stores local indexes; JSON provides portable reports
and manifests with application/method versions. Future schema migrations need fixtures and
upgrade/rollback planning; current schema is v1 only.

## Privacy and safe operations

Default operation is local and read-only. No mandatory telemetry/accounts or online music
identification. Optional online services must disclose exactly what is sent and require an
explicit user decision. Recording identity never proves a file's mastering history.

Future writes need a concrete preview, affected-file list, PCM-change disclosure, preserved
originals, explicit execution, no silent overwrite and operation logs. Duplicate cleanup and
conversion execution are deliberately absent until these safeguards are implemented.

## Readiness work

- Broader real-world and labelled signal validation; measured error rates before confidence claims.
- Native DSD/DST and real SACD fixtures; metering reference validation.
- Licensing/redistribution review for FFmpeg, sacd_extract, Chromaprint and other dependencies.
- Signed installers, binary provenance, updates, code signing and reproducible release builds.
- Long scans, cancellation UI, recovery, large-library performance and concurrency testing.
- Database migration/version invalidation and stable public report schemas.
- Accessibility/browser/manual UX review, Russian/English terminology consistency.
- Support policy, third-party notices, privacy documentation and chosen project license.

No commercial license or third-party redistribution rights are granted by this strategy document.
