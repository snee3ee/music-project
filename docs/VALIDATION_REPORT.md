# Validation report — 2026-10-28

Scope: Music Project 0.1.0 functional foundation in the existing local repository.
This is not a completion claim for the full master specification.

## Environment

- Windows local execution, Python 3.13.15 in .venv.
- FFmpeg 9.0.2-full_build-www.gyan.dev; ffprobe 9.0.2-full_build-www.gyan.dev.
- Streamlit 1.66.1, NumPy 2.5.4, SciPy 1.18.1, Matplotlib 3.11.2,
  Mutagen 1.48.1, pytest 9.2.0, Ruff 0.17.3. Complete snapshot: requirements-lock.txt.
- Standalone fpcalc and sacd_extract absent; no external executables downloaded.

## Executed checks

```text
python -X utf8 -m pytest -q
89 passed, 1 skipped in 14.74s

python -X utf8 -m ruff check .
All checks passed!

python -X utf8 -m ruff format --check .
43 files already formatted

python -X utf8 -m compileall -q music_project app.py tools
exit 0

python -m pip check
No broken requirements found.
```

Commands used the project's .venv/Scripts/python.exe. The skipped test is real SACD
end-to-end integration, explicitly unverified. No current test failures.

FFmpeg integration: generated WAV/FLAC/MP3/ALAC/AIFF/Vorbis/Opus, Unicode names,
invalid/truncated input, canonical PCM identity and format detection independent of extension.
Synthetic DSF/DFF metadata verified separately from real DSD recording support.
DSP controls include sharp/broad resampling, bandlimited lossless negative history,
silence, sparse tones, padding, dither, gain, filtering, phase inversion and alignment ambiguity.
Library/integrity controls cover recursive/incremental scans, removed/modified/corrupt files,
separate duplicate categories, manifest transfer, unsafe paths and future DB version rejection.

Streamlit AppTest executed every navigation page and exercised analysis/errors, optional
spectrogram and audio preview, collapsed Quantization Structure, scan/dashboard and comparison.
No browser rendering, screen-reader or manual listening validation was performed.

## Runtime and launcher

Both direct Streamlit invocation and actual Music_Project.bat execution started a server.
After the final launcher fixes, GET http://127.0.0.1:8501/ returned HTTP 200 and
GET http://127.0.0.1:8501/_stcore/health returned HTTP 200, body `ok`.
The server binds only 127.0.0.1. Launcher checks the real backends with Python shutil.which.
Plot cache is scoped to data/matplotlib. Runtime data is ignored by Git.

Editable reinstall was executed using --no-deps --no-build-isolation with locked setuptools.
AGENTS.md, repository audio-forensics skill and legacy_reference/app.py have no changes.
No user collection was scanned; generated fixtures only. No push was performed.

## Performance experiment

`tools/benchmark.py` generated 32 identical 3-second mono WAV files (48 kHz, 16-bit),
then indexed them with full decode/canonical hashes. Initial scan: 4.202 s; unchanged
rescan: 0.0061 s. Zero errors; all 32 reused. Report: ignored data/benchmark.json.
This is a small warm-filesystem smoke experiment, not a production-scale benchmark.
Streaming-output test consumed 10,000,000 bytes without accumulating them in result.stdout.
PCM-buffer test confirmed the configured decoded-array limit, not a total-process RAM bound.

## Outstanding validation

Real-music corpus/error rates, independent metering standards fixtures, unusual formats/layouts,
native DSD/DST processing, real SACD extraction/cleanup, acoustic similarity, large-library
recovery/concurrency, browser UX, Windows version matrix and commercial distribution remain
open. Exact follow-up tasks and acceptance criteria are in DEVELOPMENT_PLAN.md.
