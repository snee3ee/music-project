
# Music Project — Agent Instructions

## Product

Music Project is a local-first Audio Library Intelligence application.

The goal is to build reliable tools for:
- audio file analysis and verification;
- lossless and Hi-Res forensic analysis;
- library scanning and auditing;
- duplicate detection;
- objective mastering comparisons;
- metadata validation;
- integrity and archival verification;
- PCM, DSD and SACD analysis.

The application should eventually support commercial distribution.

## Core principles

Priority:
1. Technical correctness
2. Reproducibility
3. Honest uncertainty
4. File safety
5. Maintainable architecture
6. User experience
7. Performance
8. Commercial readiness

## No subjective audio judgments

Never describe audio as good, bad, better-sounding, audiophile-quality, or fake.

Separate:
- directly measured facts;
- heuristic evidence;
- unverifiable historical provenance.

Use Ambiguous, Unknown, Not applicable or Unsupported when appropriate.

Never present a heuristic as proof.

## Audio-specific rules

PCM and DSD require different analytical pipelines.

Never apply PCM bit-depth tests to native DSD.

SACD ISO is a disc image, not an ordinary audio codec.

Lossless codec does not prove lossless provenance.

High entropy does not prove native 24-bit origin.

An absent cutoff does not prove original lossless audio.

Do not claim 100% provenance determination from signal analysis alone.

## Architecture

Keep analytical modules independent from Streamlit.

Prefer small, typed and testable Python modules.

Do not create one enormous app.py.

Use reusable structured analysis results.

Keep UI-specific code separate from the analysis engine.

## User interface

Default language: Russian.

Show essential information first.

Hide advanced technical metrics in expandable sections.

All analytical findings must have accessible evidence and methodology.

Do not hide uncertainty or contradictory measurements.

## Testing

Every implemented heuristic requires tests.

Prefer known-ground-truth synthetic fixtures.

Test expected detections and expected ambiguity.

Never tune thresholds only to make one test file pass.

Run applicable tests and static checks after changes.

Never claim a test passed unless it was executed.

## File safety

Never overwrite original music files during analysis.

Never delete user audio automatically.

Do not upload local audio to external services without explicit permission.

Do not commit private music collections, secrets or large user-owned media to Git.

Preserve legacy_reference as reference material.

## Development workflow

For substantial features:

1. Inspect relevant project code.
2. Implement the core logic.
3. Integrate it into the UI.
4. Add or update tests.
5. Run relevant checks.
6. Report verified results and limitations.

For difficult tasks, maintain a persistent implementation plan.

Create Git commits at stable milestones when appropriate.

Do not push to remote repositories without explicit authorization.

Never silently download untrusted executables.

## Documentation

Document analytical thresholds, applicability and limitations.

Keep README and technical documentation consistent with implemented behavior.

The full project specification will be supplied in the main development prompt.
