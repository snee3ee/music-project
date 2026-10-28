import base64
import json
import shutil
import sys

import pytest

from music_project.core.models import AudioError
from music_project.core.subprocess_utils import CommandResult, run
from music_project.ui import file_picker


@pytest.mark.parametrize("path", ["C:/Музыка/日本語.flac", None, ""])
def test_picker_result_and_cancellation(monkeypatch, path):
    monkeypatch.setattr(file_picker.sys, "platform", "win32")
    monkeypatch.setattr(file_picker.shutil, "which", lambda executable: "powershell.exe")

    def fake_run(command, **kwargs):
        assert "-STA" in command and "-NoProfile" in command
        assert "System.Windows.Forms.OpenFileDialog" in command[-1]
        assert kwargs["timeout"] == 300
        return CommandResult(json.dumps({"path": path}).encode("utf-8"), "")

    monkeypatch.setattr(file_picker, "run", fake_run)
    assert file_picker.choose_file() == (path or None)


@pytest.mark.parametrize(
    "response", [b"not-json", b"[]", b'{"path": 123}', b'{"error": "WindowError"}']
)
def test_dialog_failure_has_manual_fallback(monkeypatch, response):
    monkeypatch.setattr(file_picker.sys, "platform", "win32")
    monkeypatch.setattr(file_picker.shutil, "which", lambda executable: "powershell.exe")
    monkeypatch.setattr(file_picker, "run", lambda *a, **kw: CommandResult(response, ""))
    with pytest.raises(AudioError, match="Вставьте путь"):
        file_picker.choose_file()


def test_missing_powershell_has_manual_fallback(monkeypatch):
    monkeypatch.setattr(file_picker.sys, "platform", "win32")
    monkeypatch.setattr(file_picker.shutil, "which", lambda executable: None)
    with pytest.raises(AudioError, match="Вставьте путь"):
        file_picker.choose_file()


def test_timeout_has_manual_fallback(monkeypatch):
    monkeypatch.setattr(file_picker.sys, "platform", "win32")
    monkeypatch.setattr(file_picker.shutil, "which", lambda executable: "powershell.exe")

    def timeout(*args, **kwargs):
        raise AudioError("Превышено время ожидания")

    monkeypatch.setattr(file_picker, "run", timeout)
    with pytest.raises(AudioError, match="Вставьте путь"):
        file_picker.choose_file()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Forms requires Windows")
def test_windows_dialog_dependencies_unicode_and_script_syntax():
    powershell = shutil.which("powershell.exe")
    if not powershell:
        pytest.skip("Windows PowerShell unavailable")
    # Parse the actual dialog script without opening any window. Instantiate and dispose
    # the native component, and exercise the UTF-8 JSON protocol with a Unicode filename.
    encoded = base64.b64encode(file_picker.WINDOWS_DIALOG.encode("utf-8")).decode("ascii")
    script = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$source = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__SCRIPT__'))
$tokens = $null
$parseErrors = $null
$null = [System.Management.Automation.Language.Parser]::ParseInput($source, [ref]$tokens, [ref]$parseErrors)
Add-Type -AssemblyName System.Windows.Forms
$native = New-Object System.Windows.Forms.OpenFileDialog
@{syntax_errors = $parseErrors.Count; type = $native.GetType().FullName; path = 'Музыка 日本語.flac'} | ConvertTo-Json -Compress
$native.Dispose()
""".replace("__SCRIPT__", encoded)
    result = json.loads(
        run([powershell, "-NoProfile", "-STA", "-Command", script], timeout=30).text
    )
    assert result["syntax_errors"] == 0
    assert result["type"] == "System.Windows.Forms.OpenFileDialog"
    assert result["path"] == "Музыка 日本語.flac"
