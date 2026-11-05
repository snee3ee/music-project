import shutil
import sys
from dataclasses import replace

import numpy as np
import pytest

from music_project.core.compare import compare_pcm
from music_project.core.library import Library
from music_project.core.models import AudioError
from music_project.core.pcm import quantization
from music_project.core.subprocess_utils import run


def test_stereo_quantization_sampling_covers_both_channels(make_context):
    # Baseline interleaved stride 2 selected only the padded left channel.
    x = np.empty((600000, 2))
    x[:, 0] = 1 / 32768
    x[:, 1] = 257 / 2**23
    result = quantization(make_context(x, channel_layout="stereo"))
    assert result.status == "No direct-padding evidence"
    assert result.measurements["active_samples"] <= 1_000_000
    assert result.measurements["zero_lower_byte_percent"] == 50


def test_unknown_multichannel_order_not_compared(make_context):
    samples = np.random.default_rng(5).normal(0, 0.1, (1000, 3))
    context = make_context(samples, channel_layout="Unknown")
    assert compare_pcm(context, context).status == "Not applicable"


@pytest.mark.parametrize("offset", [-1, float("inf"), float("nan")])
def test_invalid_alignment_limit(make_context, offset):
    context = make_context(np.ones(1000))
    assert compare_pcm(context, context, offset).status == "Not applicable"


def test_backend_settings_invalidate_index(tone, tmp_path, settings):
    root = tmp_path / "audio"
    root.mkdir()
    shutil.copyfile(tone, root / "one.wav")
    lib = Library(tmp_path / "index.sqlite3")
    missing = replace(settings, ffmpeg="missing-decoder")
    assert lib.scan(root, missing)["errors"] == 1
    assert lib.scan(root, settings)["modified"] == 1
    assert lib.records()[0]["status"] == "Indexed"
    assert lib.scan(root, settings)["unchanged"] == 1


def test_cancel_empty_traversal_does_not_remove(tone, tmp_path, settings):
    root = tmp_path / "audio"
    root.mkdir()
    path = root / "fixture.wav"
    shutil.copyfile(tone, path)
    lib = Library(tmp_path / "index.sqlite3")
    lib.scan(root, settings)
    path.unlink()  # Generated fixture only.
    assert lib.scan(root, settings, cancelled=lambda: True)["cancelled"]
    assert lib.records()[0]["status"] == "Indexed"
    assert lib.scan(root, settings)["removed"] == 1


def test_stderr_tail_bounded_without_deadlock():
    result = run(
        [sys.executable, "-c", "import sys; sys.stderr.buffer.write(b'x'*2000000); print('done')"]
    )
    assert len(result.stderr) == 65536
    assert result.text.strip() == "done"


def test_cancel_subprocess_without_stdout():
    with pytest.raises(AudioError, match="Cancelled"):
        run([sys.executable, "-c", "import time; time.sleep(30)"], cancelled=lambda: True)


def test_cache_parameter_and_source_identity(tone, settings, monkeypatch):
    from music_project.ui import shared

    shared.clear_analysis_cache()
    calls = []

    def controlled(path, options, **kwargs):
        calls.append(options.dsd_mode)
        return "controlled"

    monkeypatch.setattr(shared, "analyze", controlled)
    stat = tone.stat()
    for _ in range(2):
        assert (
            shared.cached_analysis(str(tone), stat.st_size, stat.st_mtime_ns, settings)
            == "controlled"
        )
    assert calls == ["quick"]
    shared.cached_analysis(
        str(tone), stat.st_size, stat.st_mtime_ns, replace(settings, dsd_mode="full")
    )
    assert calls == ["quick", "full"]
    shared.cached_analysis(
        str(tone), stat.st_size, stat.st_mtime_ns, replace(settings, ffmpeg="missing")
    )
    assert len(calls) == 3
    with pytest.raises(AudioError, match="кэше"):
        shared.cached_analysis(str(tone), stat.st_size + 1, stat.st_mtime_ns, settings)
    shared.clear_analysis_cache()


def test_malformed_loudness_is_optional(tone, settings, monkeypatch):
    from music_project.core.analysis import analyze
    from music_project.core.subprocess_utils import CommandResult

    real_run = run

    def controlled(command, **kwargs):
        if "loudnorm=print_format=json" in command:
            return CommandResult(b"", '{"input_i":"invalid", "input_tp":"0", "input_lra":"0"}')
        return real_run(command, **kwargs)

    monkeypatch.setattr("music_project.core.pcm.run", controlled)
    result, context = analyze(tone, settings)
    assert context is not None
    assert result.findings["loudness"].status == "Unknown"
    assert result.findings["peaks"].status == "Measured"
