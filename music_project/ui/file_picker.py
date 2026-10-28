"""Native local file selection. Never reads or copies the chosen audio."""

import json
import shutil
import sys

from music_project.core.models import AudioError
from music_project.core.subprocess_utils import run

WINDOWS_DIALOG = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$dialog = $null
$owner = $null
try {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = 'Music Project — выберите файл для анализа'
    $dialog.Filter = 'Аудиофайлы|*.flac;*.wav;*.wave;*.bwf;*.rf64;*.aif;*.aiff;*.aifc;*.m4a;*.alac;*.wv;*.ape;*.tak;*.tta;*.caf;*.mka;*.mkv;*.mp3;*.aac;*.opus;*.ogg;*.wma;*.dsf;*.dff;*.dsdiff|CUE / ISO|*.cue;*.iso|Все файлы|*.*'
    $dialog.Multiselect = $false
    $dialog.CheckFileExists = $true
    $dialog.RestoreDirectory = $true
    $owner = New-Object System.Windows.Forms.Form
    $owner.TopMost = $true
    $owner.ShowInTaskbar = $false
    $owner.Opacity = 0
    $owner.Show()
    $owner.Activate()
    if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
        @{path = $dialog.FileName} | ConvertTo-Json -Compress
    } else {
        @{path = $null} | ConvertTo-Json -Compress
    }
} catch {
    @{error = $_.Exception.GetType().Name} | ConvertTo-Json -Compress
} finally {
    if ($null -ne $dialog) { $dialog.Dispose() }
    if ($null -ne $owner) { $owner.Dispose() }
}
"""


def choose_file() -> str | None:
    try:
        if sys.platform != "win32":
            raise AudioError("Системный диалог реализован для Windows")
        powershell = shutil.which("powershell.exe")
        if not powershell:
            raise AudioError("Windows PowerShell не найден")
        command = [powershell, "-NoProfile", "-STA", "-Command", WINDOWS_DIALOG]
        response = run(command, timeout=300, max_bytes=65536)
        result = json.loads(response.text)
        if not isinstance(result, dict):
            raise ValueError("Expected object")
        if result.get("error"):
            raise AudioError(f"Windows не открыл окно выбора файла ({result['error']}).")
        path = result.get("path")
        if path is not None and not isinstance(path, str):
            raise ValueError("Expected path")
        return path or None
    except AudioError as exc:
        raise AudioError(f"{exc} Вставьте путь в поле ниже.") from exc
    except ValueError as exc:
        raise AudioError(
            "Окно выбора файла вернуло неожиданный ответ. Вставьте путь в поле ниже."
        ) from exc
