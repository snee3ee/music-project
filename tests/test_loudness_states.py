import json

import numpy as np
import pytest

from music_project.core import pcm
from music_project.core.pcm import loudness
from music_project.core.probe import probe
from music_project.core.subprocess_utils import CommandResult
from music_project.ui.presentation import measurement_rows


@pytest.mark.parametrize("case", ["over", "under", "silence"])
def test_true_peak_flags_and_silence_state(tmp_path, write_wav, settings, case):
    x = np.tile([1, 1, -1, -1], 48000 * 2 // 4) * 0.9
    if case == "under":
        x *= 0.5
    elif case == "silence":
        x *= 0
    path = write_wav(tmp_path / f"{case}.wav", x)
    finding = loudness(probe(path, settings), settings)
    flag = next(o for o in finding.observations if o.code == "TRUE_PEAK_OVER")
    assert flag.status == ("Detected" if case == "over" else "Not detected")
    if case == "silence":
        assert finding.measurements["true_peak_state"] == "negative infinity"
        assert "−∞" in flag.summary
        rows = measurement_rows(finding.measurements)
        assert next(r["Значение"] for r in rows if r["Показатель"] == "True Peak, dBTP") == "−∞"


def test_undefined_backend_value_is_not_negative_detection(monkeypatch, info, settings):
    response = json.dumps({"input_i": "nan", "input_tp": "nan", "input_lra": "nan"})
    monkeypatch.setattr(pcm, "run", lambda *args, **kwargs: CommandResult(b"", response))
    finding = loudness(info, settings)
    assert finding.observations[0].status == "Insufficient data"
    assert finding.measurements["true_peak_above_0_dbtp"] is None
