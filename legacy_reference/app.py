import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import streamlit as st


# -----------------------------
# НАСТРОЙКА СТРАНИЦЫ
# -----------------------------

st.set_page_config(
    page_title="Music Project — Audio Analyzer",
    page_icon="🎵",
)

st.title("Music Project")
st.write("Audio Analyzer v0.1")


# -----------------------------
# ФУНКЦИИ ФОРМАТИРОВАНИЯ
# -----------------------------

def format_file_size(size_bytes):
    """Переводит размер файла из байтов в MB."""
    return f"{size_bytes / (1024 ** 2):.2f} MB"


def format_duration(seconds):
    """Переводит секунды в формат минуты:секунды."""

    if seconds is None:
        return "Не определено"

    seconds = float(seconds)

    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60

    return f"{minutes}:{remaining_seconds:05.2f}"


def format_sample_rate(sample_rate):
    """Переводит 44100 Hz в 44.1 kHz."""

    if not sample_rate:
        return "Не определено"

    sample_rate = int(sample_rate)

    return f"{sample_rate / 1000:g} kHz"


def format_bitrate(bit_rate):
    """Переводит bit/s в kbps."""

    if not bit_rate:
        return "Не определено"

    bit_rate = int(bit_rate)

    return f"{bit_rate / 1000:.0f} kbps"


# -----------------------------
# BIT DEPTH
# -----------------------------

def get_bit_depth(stream):
    """
    Получает bit depth там, где этот параметр имеет смысл.
    """

    codec = stream.get("codec_name", "").lower()

    lossy_codecs = {
        "mp3",
        "aac",
        "opus",
        "vorbis",
        "ac3",
        "eac3",
    }

    if codec in lossy_codecs:
        return "Не применимо к lossy-кодеку"

    raw_bits = stream.get("bits_per_raw_sample")
    bits = stream.get("bits_per_sample")

    if raw_bits and raw_bits != "0":
        return f"{raw_bits}-bit"

    if bits and bits != "0":
        return f"{bits}-bit"

    return "Не определено"

def create_explanation(codec, bit_depth, sample_rate, bitrate):
    """
    Создаёт простое человеческое объяснение
    технических характеристик аудиофайла.
    """

    codec = codec.lower()

    if codec == "flac":
        return (
            f"Это FLAC {bit_depth} / {sample_rate}. "
            "FLAC — lossless-кодек: при нормальном кодировании "
            "он сохраняет аудиоданные без потерь. "
            "Повышение такого файла до 24-bit / 192 kHz само по себе "
            "не добавит отсутствующую информацию. "
            "При этом сам формат FLAC ещё не доказывает, "
            "что исходник никогда раньше не был lossy."
        )

    if codec == "mp3":
        return (
            f"Это MP3 с bitrate около {bitrate}. "
            "MP3 использует lossy-сжатие: часть информации "
            "удаляется во время кодирования. "
            "Конвертация этого MP3 во FLAC не восстановит "
            "уже потерянные данные."
        )

    if codec.startswith("pcm_"):
        return (
            f"Это несжатый PCM-аудиосигнал: "
            f"{bit_depth}, {sample_rate}. "
            "PCM может хранить звук без потерь, например внутри WAV."
        )

    return (
        f"Обнаружен кодек {codec}. "
        "Сейчас Music Project показывает его технические параметры, "
        "но пока не делает выводов о качестве мастеринга "
        "или происхождении файла."
    )


# -----------------------------
# АНАЛИЗ ЧЕРЕЗ FFPROBE
# -----------------------------

def analyze_audio(file_bytes, original_filename):
    """
    Временно сохраняет аудиофайл,
    запускает ffprobe,
    получает JSON и возвращает его Python.
    """

    suffix = Path(original_filename).suffix.lower()

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    )

    temp_path = temp_file.name

    try:
        temp_file.write(file_bytes)
        temp_file.close()

        command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            (
                "stream="
                "codec_name,"
                "codec_long_name,"
                "sample_rate,"
                "channels,"
                "channel_layout,"
                "bit_rate,"
                "bits_per_sample,"
                "bits_per_raw_sample:"
                "format="
                "format_name,"
                "format_long_name,"
                "duration,"
                "bit_rate"
            ),
            "-of",
            "json",
            temp_path,
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )

        return json.loads(result.stdout)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def analyze_loudness(file_bytes, original_filename):
    """
    Анализирует громкость аудиофайла через FFmpeg loudnorm.

    Возвращает:
    - Integrated LUFS
    - True Peak
    - Loudness Range (LRA)
    """

    suffix = Path(original_filename).suffix.lower()

    temp_audio = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    )

    audio_path = temp_audio.name

    try:
        temp_audio.write(file_bytes)
        temp_audio.close()

        command = [
            "ffmpeg",
            "-hide_banner",
            "-i",
            audio_path,
            "-af",
            "loudnorm=print_format=json",
            "-f",
            "null",
            "-",
        ]
        
        result = subprocess.run(
    command,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    check=True,
)

        output = result.stderr or ""
        
        match = re.search(
    r'\{\s*"input_i".*?\}',
    output,
    re.DOTALL,
        )

        if not match:
            return None

        loudness_data = json.loads(
            match.group(0)
        )

        return {
            "integrated_lufs": float(
                loudness_data["input_i"]
            ),
            "true_peak": float(
                loudness_data["input_tp"]
            ),
            "lra": float(
                loudness_data["input_lra"]
            ),
        }

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
def analyze_clipping(file_bytes, original_filename):
    """
    Проверяет пиковые значения декодированного аудиосигнала
    через FFmpeg astats.

    Это помогает обнаружить признаки sample clipping,
    но не является абсолютным доказательством clipping.
    """

    suffix = Path(original_filename).suffix.lower()

    temp_audio = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    )

    audio_path = temp_audio.name

    try:
        temp_audio.write(file_bytes)
        temp_audio.close()

        command = [
            "ffmpeg",
            "-hide_banner",
            "-i",
            audio_path,
            "-af",
            "astats=metadata=0:reset=0",
            "-f",
            "null",
            "-",
        ]

        result = subprocess.run(
    command,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    check=True,
)

        output = result.stderr or ""

        # Нам нужны итоговые значения Overall,
        # а не статистика отдельного канала.
        if "Overall" in output:
            output = output.split("Overall", 1)[1]

        peak_match = re.search(
            r"Peak level dB:\s*(-?\d+(?:\.\d+)?)",
            output,
        )

        peak_count_match = re.search(
            r"Abs Peak count:\s*(\d+(?:\.\d+)?)",
            output,
        )

        samples_match = re.search(
            r"Number of samples:\s*(\d+(?:\.\d+)?)",
            output,
        )

        if not peak_match:
            return None

        peak_level = float(
            peak_match.group(1)
        )

        peak_count = None

        if peak_count_match:
            peak_count = int(
                float(peak_count_match.group(1))
            )

        number_of_samples = None

        if samples_match:
            number_of_samples = int(
                float(samples_match.group(1))
            )

        return {
            "sample_peak": peak_level,
            "peak_count": peak_count,
            "number_of_samples": number_of_samples,
        }

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

def analyze_spectral_cutoff(
    file_bytes,
    original_filename,
    sample_rate,
):
    """
    Ищет резкий высокочастотный спад спектра.

    Такой спад может быть одним из признаков того,
    что FLAC раньше был lossy-файлом.

    Это эвристика, а не доказательство.
    """

    if not sample_rate:
        return None

    sample_rate = int(sample_rate)

    # Для первой версии анализируем обычные
    # sample rate: 32–48 kHz.
    if sample_rate < 32000:
        return {
            "supported": False,
            "reason": "Sample rate слишком низкий для этого теста.",
        }

    if sample_rate > 48000:
                return {
            "supported": False,
            "reason": (
                "Lossy-transcode cutoff test не применяется "
                "к sample rate выше 48 kHz. "
                "Для этого файла используется отдельный "
                "Hi-Res / Upsampling analysis."
            ),
        }

    suffix = Path(original_filename).suffix.lower()

    temp_audio = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    )

    audio_path = temp_audio.name

    try:
        temp_audio.write(file_bytes)
        temp_audio.close()

        # FFmpeg декодирует первые 90 секунд
        # в mono 32-bit float PCM.
        command = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            audio_path,
            "-map",
            "0:a:0",
            "-t",
            "90",
            "-ac",
            "1",
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            check=True,
        )

        samples = np.frombuffer(
            result.stdout,
            dtype="<f4",
        )

        # Нужно хотя бы около одной секунды сигнала.
        if samples.size < sample_rate:
            return None

        n_fft = 8192
        hop = n_fft // 2

        window = np.hanning(
            n_fft
        ).astype(np.float32)

        accumulated_power = np.zeros(
            n_fft // 2 + 1,
            dtype=np.float64,
        )

        valid_windows = 0

        for start in range(
            0,
            samples.size - n_fft + 1,
            hop,
        ):
            chunk = samples[
                start:start + n_fft
            ]

            # Почти полную тишину не анализируем.
            if np.max(np.abs(chunk)) < 0.0001:
                continue

            spectrum = np.fft.rfft(
                chunk * window
            )

            power = np.abs(spectrum) ** 2

            accumulated_power += power
            valid_windows += 1

        if valid_windows == 0:
            return None

        average_power = (
            accumulated_power
            / valid_windows
        )

        frequencies = np.fft.rfftfreq(
            n_fft,
            d=1.0 / sample_rate,
        )

        spectrum_db = (
            10
            * np.log10(
                average_power + 1e-20
            )
        )

        nyquist = sample_rate / 2

        # Средние музыкальные частоты используем
        # как относительную точку отсчёта.
        reference_mask = (
            (frequencies >= 200)
            & (frequencies <= 8000)
        )

        reference_level = np.percentile(
            spectrum_db[reference_mask],
            95,
        )

        relative_db = (
            spectrum_db - reference_level
        )

        candidate_cutoffs = [
            14000,
            15000,
            16000,
            17000,
            18000,
            19000,
            20000,
            21000,
        ]

        best_result = None

        for cutoff in candidate_cutoffs:

            # Не анализируем область слишком близко
            # к пределу Nyquist.
            if cutoff + 1200 >= nyquist:
                continue

            below_mask = (
                (frequencies >= cutoff - 1200)
                & (frequencies <= cutoff - 300)
            )

            above_mask = (
                (frequencies >= cutoff + 300)
                & (frequencies <= cutoff + 1200)
            )

            if (
                np.sum(below_mask) < 5
                or np.sum(above_mask) < 5
            ):
                continue

            below_level = np.percentile(
                relative_db[below_mask],
                75,
            )

            above_level = np.percentile(
                relative_db[above_mask],
                75,
            )

            drop_db = (
                below_level - above_level
            )

            high_band_mask = (
                (frequencies >= cutoff + 1000)
                & (frequencies <= nyquist - 200)
            )

            if np.sum(high_band_mask) >= 5:
                high_band_level = np.percentile(
                    relative_db[high_band_mask],
                    75,
                )
            else:
                high_band_level = above_level

            current_result = {
                "cutoff_hz": cutoff,
                "drop_db": float(drop_db),
                "high_band_db": float(high_band_level),
            }

            if (
                best_result is None
                or drop_db > best_result["drop_db"]
            ):
                best_result = current_result

        if best_result is None:
            return None

        cutoff = best_result["cutoff_hz"]
        drop_db = best_result["drop_db"]
        high_band_db = best_result["high_band_db"]

        # Осторожная первая эвристика.
        if (
            cutoff <= 17000
            and drop_db >= 18
            and high_band_db <= -35
        ):
            suspicion = "High"

        elif (
            cutoff <= 20000
            and drop_db >= 12
            and high_band_db <= -30
        ):
            suspicion = "Medium"

        else:
            suspicion = "Low"

        return {
            "supported": True,
            "suspicion": suspicion,
            "cutoff_hz": cutoff,
            "drop_db": drop_db,
            "high_band_db": high_band_db,
        }

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

def analyze_upsampling(
    file_bytes,
    original_filename,
    sample_rate,
):
    """
    Проверяет Hi-Res файл на признаки upsampling.

    Анализирует:
    - спектральный спад около 22.05 kHz;
    - спектральный спад около 24 kHz;
    - наличие сигнала между 22.05 и 24 kHz.

    Результат является эвристической классификацией.
    """

    if not sample_rate:
        return {
            "supported": False,
            "status": "No sample rate",
            "reason": "Sample rate не определён.",
        }

    sample_rate = int(sample_rate)

    if sample_rate <= 48000:
        return {
            "supported": False,
            "status": "Not Hi-Res",
            "reason": (
                "Sample rate не превышает 48 kHz. "
                "Проверка upsampling этого типа не применяется."
            ),
        }

    suffix = Path(original_filename).suffix.lower()

    temp_audio = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    )

    audio_path = temp_audio.name

    try:
        temp_audio.write(file_bytes)
        temp_audio.close()

        command = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            audio_path,
            "-map",
            "0:a:0",
            "-t",
            "90",
            "-ac",
            "1",
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            check=True,
        )

        if not result.stdout:
            return {
                "supported": False,
                "status": "No decoded audio",
                "reason": "FFmpeg не вернул декодированный PCM.",
            }

        samples = np.frombuffer(
            result.stdout,
            dtype="<f4",
        )

        if samples.size < sample_rate:
            return {
                "supported": False,
                "status": "Too short",
                "reason": (
                    "Для анализа получено менее одной секунды аудио."
                ),
            }

        n_fft = 16384
        hop = n_fft // 2

        window = np.hanning(
            n_fft
        ).astype(np.float32)

        accumulated_power = np.zeros(
            n_fft // 2 + 1,
            dtype=np.float64,
        )

        valid_windows = 0

        for start in range(
            0,
            samples.size - n_fft + 1,
            hop,
        ):
            chunk = samples[
                start:start + n_fft
            ]

            if np.max(np.abs(chunk)) < 0.0001:
                continue

            spectrum = np.fft.rfft(
                chunk * window
            )

            power = np.abs(spectrum) ** 2

            accumulated_power += power
            valid_windows += 1

        if valid_windows == 0:
            return {
                "supported": False,
                "status": "No usable windows",
                "reason": (
                    "Не найдено достаточно участков сигнала "
                    "выше порога анализа."
                ),
            }

        average_power = (
            accumulated_power / valid_windows
        )

        frequencies = np.fft.rfftfreq(
            n_fft,
            d=1.0 / sample_rate,
        )

        spectrum_db = (
            10
            * np.log10(
                average_power + 1e-20
            )
        )

        nyquist = sample_rate / 2

        reference_mask = (
            (frequencies >= 500)
            & (frequencies <= 12000)
        )

        if np.sum(reference_mask) < 5:
            return {
                "supported": False,
                "status": "No reference band",
                "reason": (
                    "Не удалось сформировать опорный "
                    "частотный диапазон."
                ),
            }

        reference_level = np.percentile(
            spectrum_db[reference_mask],
            95,
        )

        relative_db = (
            spectrum_db - reference_level
        )

        # ---------------------------------
        # ОБЩАЯ ПРОВЕРКА UPSAMPLING
        # ---------------------------------

        candidate_boundaries = [
            22050,
            24000,
        ]

        best_result = None

        for boundary in candidate_boundaries:

            if boundary + 4000 >= nyquist:
                continue

            below_mask = (
                (frequencies >= boundary - 1500)
                & (frequencies <= boundary - 250)
            )

            above_mask = (
                (frequencies >= boundary + 250)
                & (frequencies <= boundary + 1500)
            )

            if (
                np.sum(below_mask) < 5
                or np.sum(above_mask) < 5
            ):
                continue

            below_level = np.percentile(
                relative_db[below_mask],
                75,
            )

            above_level = np.percentile(
                relative_db[above_mask],
                75,
            )

            drop_db = (
                below_level - above_level
            )

            ultrasonic_mask = (
                (frequencies >= boundary + 3000)
                & (frequencies <= nyquist - 1000)
            )

            if np.sum(ultrasonic_mask) >= 5:
                ultrasonic_level = np.percentile(
                    relative_db[ultrasonic_mask],
                    75,
                )
            else:
                ultrasonic_level = above_level

            current_result = {
                "boundary_hz": boundary,
                "drop_db": float(drop_db),
                "ultrasonic_db": float(
                    ultrasonic_level
                ),
            }

            if (
                best_result is None
                or drop_db > best_result["drop_db"]
            ):
                best_result = current_result

        if best_result is None:
            return {
                "supported": False,
                "status": "No boundary result",
                "reason": (
                    "Не удалось измерить области "
                    "22.05 и 24 kHz."
                ),
            }

        boundary = best_result["boundary_hz"]
        drop_db = best_result["drop_db"]
        ultrasonic_db = best_result[
            "ultrasonic_db"
        ]

        # ---------------------------------
        # 44.1 vs 48 kHz
        # ---------------------------------

        def get_band_level(low_hz, high_hz):
            mask = (
                (frequencies >= low_hz)
                & (frequencies <= high_hz)
            )

            if np.sum(mask) < 5:
                return None

            return float(
                np.percentile(
                    relative_db[mask],
                    75,
                )
            )

        pre_22 = get_band_level(
            20000,
            21800,
        )

        between_22_24 = get_band_level(
            22300,
            23700,
        )

        above_24 = get_band_level(
            24500,
            26000,
        )

        possible_source_rate = None
        source_rate_confidence = "Ambiguous"

        source_rate_reason = (
            "Недостаточно положительных спектральных "
            "признаков для различения 44.1 и 48 kHz."
        )

        evidence_22_24_db = None
        drop_after_24_db = None

        if (
            pre_22 is not None
            and between_22_24 is not None
            and above_24 is not None
        ):
            evidence_22_24_db = (
                pre_22 - between_22_24
            )

            drop_after_24_db = (
                between_22_24 - above_24
            )

            # Положительное свидетельство в пользу 48 kHz:
            # содержимое выше Nyquist 44.1 kHz присутствует,
            # а после 24 kHz наблюдается спад.

            if (
                between_22_24 > -35
                and evidence_22_24_db < 8
                and drop_after_24_db >= 8
            ):
                possible_source_rate = 48000

                if (
                    between_22_24 > -25
                    and evidence_22_24_db < 4
                    and drop_after_24_db >= 15
                ):
                    source_rate_confidence = "High"
                else:
                    source_rate_confidence = "Medium"

                source_rate_reason = (
                    "Обнаружено спектральное содержимое "
                    "между 22.3 и 23.7 kHz и последующий "
                    "спад выше 24 kHz."
                )

            # Спад выше 22.05 kHz совместим с 44.1 kHz,
            # но не исключает исходник 48 kHz.

            elif (
                evidence_22_24_db >= 10
                and (
                    pre_22 - above_24
                ) >= 20
            ):
                source_rate_reason = (
                    "Сигнал заметно ослабевает выше "
                    "22.05 kHz. Это совместимо с 44.1 kHz, "
                    "но не исключает 48 kHz."
                )

                # ---------------------------------
        # ОБЩАЯ ОЦЕНКА ПРИЗНАКОВ UPSAMPLING
        # ---------------------------------

        evidence_score = 0
        evidence_flags = []

        # Резкость основной обнаруженной границы.
        if drop_db >= 6:
            evidence_score += 1
            evidence_flags.append(
                "boundary_drop>=6dB"
            )

        if drop_db >= 12:
            evidence_score += 1
            evidence_flags.append(
                "boundary_drop>=12dB"
            )

        # Уровень ультразвукового диапазона
        # относительно основного спектра.
        if ultrasonic_db <= -30:
            evidence_score += 1
            evidence_flags.append(
                "ultrasonic_level<=-30dB"
            )

        if ultrasonic_db <= -45:
            evidence_score += 1
            evidence_flags.append(
                "ultrasonic_level<=-45dB"
            )

        # Дополнительный спад выше 24 kHz.
        if (
            drop_after_24_db is not None
            and drop_after_24_db >= 8
        ):
            evidence_score += 1
            evidence_flags.append(
                "drop_above_24k>=8dB"
            )

        # Исходный rate удалось классифицировать
        # по положительным спектральным данным.
        if possible_source_rate is not None:
            evidence_score += 1
            evidence_flags.append(
                "source_rate_classified"
            )

        if source_rate_confidence == "High":
            evidence_score += 1
            evidence_flags.append(
                "source_rate_confidence_high"
            )

        # Формализованная классификация.
        if evidence_score >= 5:
            suspicion = "High"

        elif evidence_score >= 3:
            suspicion = "Medium"

        else:
            suspicion = "Low"
        
        return {
            "supported": True,
            "status": "OK",
            "suspicion": suspicion,
            "boundary_hz": boundary,
            "drop_db": drop_db,
            "ultrasonic_db": ultrasonic_db,
            "possible_source_rate": possible_source_rate,
            "source_rate_confidence": source_rate_confidence,
            "source_rate_reason": source_rate_reason,
            "evidence_22_24_db": evidence_22_24_db,
            "drop_after_24_db": drop_after_24_db,
            "evidence_score": evidence_score,
            "evidence_max_score": 7,
            "evidence_flags": evidence_flags,
        
        }

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

def analyze_bit_depth_padding(
    file_bytes,
    original_filename,
):
    """
    Проверяет 24-bit аудио на признак простого
    расширения 16-bit -> 24-bit.

    Проверяются младшие 8 бит декодированного PCM.
    """

    suffix = Path(original_filename).suffix.lower()

    temp_audio = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    )

    audio_path = temp_audio.name

    try:
        temp_audio.write(file_bytes)
        temp_audio.close()

        command = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            audio_path,
            "-map",
            "0:a:0",
            "-t",
            "90",
            "-f",
            "s24le",
            "-acodec",
            "pcm_s24le",
            "-",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            check=True,
        )

        raw = result.stdout

        if not raw:
            return {
                "supported": False,
                "status": "No decoded PCM",
            }

        data = np.frombuffer(
            raw,
            dtype=np.uint8,
        )

        sample_count = data.size // 3

        if sample_count < 1000:
            return {
                "supported": False,
                "status": "Too few samples",
            }

        data = data[
            :sample_count * 3
        ].reshape(-1, 3)

        # s24le = little-endian:
        # первый байт содержит младшие 8 бит.
        low_byte = data[:, 0]

        values = (
            data[:, 0].astype(np.int32)
            | (
                data[:, 1].astype(np.int32)
                << 8
            )
            | (
                data[:, 2].astype(np.int32)
                << 16
            )
        )

        # unsigned 24-bit -> signed
        negative = (
            values & 0x800000
        ) != 0

        values[negative] -= (
            1 << 24
        )

        # Почти нулевые отсчёты исключаем,
        # чтобы тишина не искажала статистику.
        active_mask = (
            np.abs(values) >= 256
        )

        active_low_byte = low_byte[
            active_mask
        ]

        if active_low_byte.size < 1000:
            return {
                "supported": False,
                "status": "Too little active audio",
            }

        zero_lsb_ratio = float(
            np.mean(
                active_low_byte == 0
            )
        )

        unique_lsb_values = int(
            np.unique(
                active_low_byte
            ).size
        )

        # Формализованные пороги.
        if (
            zero_lsb_ratio >= 0.999
            and unique_lsb_values <= 2
        ):
            suspicion = "High"

        elif (
            zero_lsb_ratio >= 0.98
            and unique_lsb_values <= 16
        ):
            suspicion = "Medium"

        else:
            suspicion = "Low"

        return {
            "supported": True,
            "status": "OK",
            "suspicion": suspicion,
            "zero_lsb_ratio": zero_lsb_ratio,
            "unique_lsb_values": unique_lsb_values,
            "active_samples": int(
                active_low_byte.size
            ),
        }

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)           

def analyze_quantization_structure(
    file_bytes,
    original_filename,
):
    """
    Анализирует структуру значений 24-bit PCM.

    Проверяет:
    - число различных амплитудных значений;
    - энтропию младшего байта;
    - совместимость с прямым отображением
      исходных 16-bit значений.

    Тест не способен доказать отсутствие
    16-bit происхождения после dither/DSP.
    """

    suffix = Path(original_filename).suffix.lower()

    temp_audio = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    )

    audio_path = temp_audio.name

    try:
        temp_audio.write(file_bytes)
        temp_audio.close()

        command = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            audio_path,
            "-map",
            "0:a:0",
            "-t",
            "90",
            "-f",
            "s24le",
            "-acodec",
            "pcm_s24le",
            "-",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            check=True,
        )

        raw = result.stdout

        if not raw:
            return {
                "supported": False,
                "status": "No decoded PCM",
            }

        data = np.frombuffer(
            raw,
            dtype=np.uint8,
        )

        sample_count = data.size // 3

        if sample_count < 1000:
            return {
                "supported": False,
                "status": "Too few samples",
            }

        data = data[
            :sample_count * 3
        ].reshape(-1, 3)

        values = (
            data[:, 0].astype(np.int32)
            | (
                data[:, 1].astype(np.int32)
                << 8
            )
            | (
                data[:, 2].astype(np.int32)
                << 16
            )
        )

        negative = (
            values & 0x800000
        ) != 0

        values[negative] -= (
            1 << 24
        )

        active_mask = (
            np.abs(values) >= 256
        )

        active_values = values[
            active_mask
        ]

        active_low_byte = data[
            active_mask,
            0,
        ]

        if active_values.size < 1000:
            return {
                "supported": False,
                "status": "Too little active audio",
            }

        # Для производительности анализируем
        # максимум 1 000 000 samples.
        if active_values.size > 1_000_000:
            step = (
                active_values.size
                // 1_000_000
            )

            analyzed_values = active_values[
                ::step
            ][:1_000_000]

            analyzed_low_byte = active_low_byte[
                ::step
            ][:1_000_000]

        else:
            analyzed_values = active_values
            analyzed_low_byte = active_low_byte

        # ---------------------------------
        # КОЛИЧЕСТВО РАЗЛИЧНЫХ PCM-УРОВНЕЙ
        # ---------------------------------

        unique_sample_values = int(
            np.unique(
                analyzed_values
            ).size
        )

        # Прямой детерминированный переход
        # из одного 16-bit sample в один
        # выходной sample не может иметь
        # больше 65536 входных уровней.
        exceeds_16bit_level_count = (
            unique_sample_values > 65536
        )

        # ---------------------------------
        # ЭНТРОПИЯ МЛАДШЕГО БАЙТА
        # ---------------------------------

        counts = np.bincount(
            analyzed_low_byte,
            minlength=256,
        ).astype(np.float64)

        probabilities = (
            counts / counts.sum()
        )

        nonzero_probabilities = probabilities[
            probabilities > 0
        ]

        low_byte_entropy = float(
            -np.sum(
                nonzero_probabilities
                * np.log2(
                    nonzero_probabilities
                )
            )
        )

        # Максимум для 8 бит = 8.0 bits.
        normalized_entropy = (
            low_byte_entropy / 8.0
        )

        # ---------------------------------
        # СУХАЯ КЛАССИФИКАЦИЯ
        # ---------------------------------

        if exceeds_16bit_level_count:
            direct_mapping_status = (
                "Not consistent"
            )

            direct_mapping_reason = (
                "Обнаружено более 65 536 различных "
                "PCM-значений в анализируемой выборке. "
                "Это несовместимо с простым "
                "детерминированным отображением "
                "одного 16-bit sample в один 24-bit sample."
            )

        else:
            direct_mapping_status = (
                "Compatible"
            )

            direct_mapping_reason = (
                "Количество обнаруженных PCM-значений "
                "не превышает 65 536. Это совместимо "
                "с прямым отображением 16-bit значений, "
                "но не доказывает такое происхождение."
            )

        return {
            "supported": True,
            "status": "OK",
            "unique_sample_values": unique_sample_values,
            "exceeds_16bit_level_count": exceeds_16bit_level_count,
            "low_byte_entropy": low_byte_entropy,
            "normalized_entropy": normalized_entropy,
            "direct_mapping_status": direct_mapping_status,
            "direct_mapping_reason": direct_mapping_reason,
            "analyzed_samples": int(
                analyzed_values.size
            ),
        }

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

def generate_spectrogram(file_bytes, original_filename):
    """
    Создаёт спектрограмму аудиофайла через FFmpeg
    и возвращает PNG-картинку.
    """

    suffix = Path(original_filename).suffix.lower()

    temp_audio = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    )

    temp_image = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".png",
    )

    audio_path = temp_audio.name
    image_path = temp_image.name

    temp_image.close()

    try:
        temp_audio.write(file_bytes)
        temp_audio.close()

        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            audio_path,
            "-lavfi",
            "showspectrumpic=s=1200x500:legend=1",
            image_path,
        ]

        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )

        with open(image_path, "rb") as image_file:
            return image_file.read()

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

        if os.path.exists(image_path):
            os.remove(image_path) 


# -----------------------------
# ЗАГРУЗКА ФАЙЛА
# -----------------------------

uploaded_file = st.file_uploader(
    "Выбери аудиофайл",
    type=["mp3", "flac", "wav"],
)


# -----------------------------
# ИНТЕРФЕЙС РЕЗУЛЬТАТА
# -----------------------------

if uploaded_file is not None:

    file_bytes = uploaded_file.getvalue()

    st.audio(file_bytes)

    try:
        data = analyze_audio(
            file_bytes,
            uploaded_file.name,
        )

    except FileNotFoundError:
        st.error(
            "ffprobe не найден. "
            "Проверь установку FFmpeg."
        )
        st.stop()

    except subprocess.CalledProcessError:
        st.error(
            "ffprobe не смог проанализировать файл."
        )
        st.stop()

    streams = data.get("streams", [])

    if not streams:
        st.error("В файле не найден аудиопоток.")
        st.stop()

    stream = streams[0]
    format_data = data.get("format", {})

    codec = stream.get(
        "codec_name",
        "Не определено",
    )

    codec_long = stream.get(
        "codec_long_name",
        codec,
    )

    container = format_data.get(
        "format_long_name",
        format_data.get(
            "format_name",
            "Не определено",
        ),
    )

    bitrate = (
        stream.get("bit_rate")
        or format_data.get("bit_rate")
    )

    st.divider()

    st.subheader("Результат анализа")

    st.write(
        f"**Имя файла:** {uploaded_file.name}"
    )

    st.write(
        f"**Контейнер:** {container}"
    )

    st.write(
        f"**Кодек:** {codec_long} (`{codec}`)"
    )

    st.write(
        f"**Bitrate:** {format_bitrate(bitrate)}"
    )

    st.write(
        f"**Sample rate:** "
        f"{format_sample_rate(stream.get('sample_rate'))}"
    )

    st.write(
        f"**Bit depth:** {get_bit_depth(stream)}"
    )

    st.write(
        f"**Каналы:** "
        f"{stream.get('channels', 'Не определено')}"
    )

    st.write(
        f"**Channel layout:** "
        f"{stream.get('channel_layout', 'Не определено')}"
    )

    st.write(
        f"**Длительность:** "
        f"{format_duration(format_data.get('duration'))}"
    )

    st.write(
        f"**Размер:** {format_file_size(len(file_bytes))}"
    )

    st.divider()

    st.subheader("Громкость и пики")

    loudness = None
    clipping = None

    # -----------------------------
    # LUFS / TRUE PEAK / LRA
    # -----------------------------

    try:
        loudness = analyze_loudness(
            file_bytes,
            uploaded_file.name,
        )

        if loudness is not None:
            st.write(
                f"**Integrated loudness:** "
                f"{loudness['integrated_lufs']:.1f} LUFS"
            )

            st.write(
                f"**True Peak:** "
                f"{loudness['true_peak']:.1f} dBTP"
            )

            st.write(
                f"**Loudness Range (LRA):** "
                f"{loudness['lra']:.1f} LU"
            )

        else:
            st.warning(
                "Не удалось получить данные громкости."
            )

    except subprocess.CalledProcessError:
        st.error(
            "FFmpeg не смог выполнить анализ громкости."
        )

    # -----------------------------
    # SAMPLE PEAK / SAMPLE CLIPPING
    # -----------------------------

    try:
        clipping = analyze_clipping(
            file_bytes,
            uploaded_file.name,
        )

        if clipping is not None:
            sample_peak = clipping["sample_peak"]
            peak_count = clipping["peak_count"]

            st.write(
                f"**Sample Peak:** "
                f"{sample_peak:.2f} dBFS"
            )

            if sample_peak < -0.01:
                sample_clipping_text = (
                    "Признаков sample clipping не обнаружено: "
                    "декодированные сэмплы не достигают 0 dBFS."
                )

            elif peak_count is not None and peak_count > 10:
                sample_clipping_text = (
                    "Обнаружено много сэмплов около цифрового потолка. "
                    "Возможен sample clipping, но одного этого признака "
                    "недостаточно для окончательного вывода."
                )

            else:
                sample_clipping_text = (
                    "Сигнал достигает цифрового потолка, "
                    "но этого недостаточно, чтобы утверждать "
                    "наличие sample clipping."
                )

            st.write(
                f"**Sample clipping:** "
                f"{sample_clipping_text}"
            )

    except subprocess.CalledProcessError:
        st.warning(
            "Не удалось выполнить проверку sample clipping."
        )

    # -----------------------------
    # TRUE PEAK HEADROOM
    # -----------------------------

    if loudness is not None:
        true_peak = loudness["true_peak"]

        if true_peak > 0:
            st.warning(
                f"True Peak достигает {true_peak:.1f} dBTP, "
                "то есть превышает 0 dBTP. "
                "Возможны inter-sample overs при воспроизведении, "
                "перекодировании или дальнейшей обработке."
            )

        elif true_peak > -1.0:
            st.info(
                f"True Peak составляет {true_peak:.1f} dBTP. "
                "Пик находится близко к 0 dBTP, "
                "поэтому запас по уровню небольшой."
            )

        else:
            st.info(
                f"True Peak составляет {true_peak:.1f} dBTP. "
                "Измеренный пик остаётся ниже -1 dBTP."
            )
        

    st.divider()

    st.subheader("Простыми словами")
    
    explanation = create_explanation(
    codec=codec,
    bit_depth=get_bit_depth(stream),
    sample_rate=format_sample_rate(
        stream.get("sample_rate")
    ),
    bitrate=format_bitrate(bitrate),
)

    st.info(explanation)
    
    st.divider()

    st.subheader("Анализ происхождения")

    if codec == "flac":

        try:
            spectral_analysis = analyze_spectral_cutoff(
                file_bytes,
                uploaded_file.name,
                stream.get("sample_rate"),
            )

            if spectral_analysis is None:
                st.warning(
                    "Недостаточно данных для спектрального анализа."
                )

            elif not spectral_analysis["supported"]:
                st.info(
                    spectral_analysis["reason"]
                )

            else:
                suspicion = spectral_analysis["suspicion"]


                cutoff_khz = (
                    spectral_analysis["cutoff_hz"] / 1000
                )

                drop_db = spectral_analysis["drop_db"]
                
                st.write(
                    f"**Lossy transcode suspicion:** {suspicion}"
                )

                
                
                if suspicion == "Low":
                    st.info(
                        "Явного резкого высокочастотного cutoff "
                        "не обнаружено. Это не доказывает "
                        "lossless-происхождение файла."
                    )

                elif suspicion == "Medium":
                    st.warning(
                        "Обнаружен заметный высокочастотный спад. "
                        "Он может быть связан с предыдущим lossy-кодированием, "
                        "но возможны и другие причины."
                    )

                elif suspicion == "High":
                    st.warning(
                        "Обнаружен сильный и резкий высокочастотный спад, "
                        "который может быть характерен для некоторых "
                        "lossy-источников. Это не является "
                        "окончательным доказательством transcode."
                    )

                    cutoff_khz = (
                    spectral_analysis["cutoff_hz"] / 1000
                )

                drop_db = spectral_analysis["drop_db"]

                if suspicion == "Low":
                    st.write(
                        "**Выраженный cutoff:** не обнаружен"
                    )

                    st.write(
                        f"**Максимальный найденный перепад:** "
                        f"{drop_db:.1f} dB "
                        f"около {cutoff_khz:.1f} kHz"
                    )

                else:
                    st.write(
                        f"**Предполагаемая область cutoff:** "
                        f"≈ {cutoff_khz:.1f} kHz"
                    )

                    st.write(
                        f"**Резкость перехода:** "
                        f"{drop_db:.1f} dB"
                    )

        except subprocess.CalledProcessError:
            st.warning(
                "Не удалось выполнить спектральный анализ."
            )

    else:
        st.caption(
            "Проверка lossy → lossless сейчас выполняется только для FLAC."
        )
    
    # -----------------------------
    # ПРОВЕРКА UPSAMPLING
    # -----------------------------

    sample_rate_value = stream.get("sample_rate")

    if (
        sample_rate_value
        and int(sample_rate_value) > 48000
    ):
        st.divider()

        st.subheader(
            "Проверка Hi-Res / Upsampling"
        )

        try:
            upsampling_analysis = analyze_upsampling(
                file_bytes,
                uploaded_file.name,
                sample_rate_value,
            )

            if not upsampling_analysis["supported"]:
                st.warning(
                    f"**Status:** "
                    f"{upsampling_analysis['status']}"
                )

                st.write(
                    upsampling_analysis["reason"]
                )

            else:
                suspicion = upsampling_analysis[
                    "suspicion"
                ]

                st.write(
                    f"**Upsampling suspicion:** "
                    f"{suspicion}"
                )

                st.write(
                    f"**Detected boundary:** "
                    f"≈ "
                    f"{upsampling_analysis['boundary_hz'] / 1000:.2f} kHz"
                )

                st.write(
                    f"**Boundary drop:** "
                    f"{upsampling_analysis['drop_db']:.1f} dB"
                )

                st.write(
                    f"**Heuristic evidence score:** "
                    f"{upsampling_analysis['evidence_score']}"
                    f"/{upsampling_analysis['evidence_max_score']}"
                )

                possible_source_rate = upsampling_analysis[
                    "possible_source_rate"
                ]

                if possible_source_rate is not None:
                    st.write(
                        f"**Source-rate classification:** "
                        f"{possible_source_rate / 1000:g} kHz"
                    )
                else:
                    st.write(
                        "**Source-rate classification:** "
                        "Ambiguous (44.1 / 48 kHz)"
                    )

                st.write(
                    f"**Source-rate confidence:** "
                    f"{upsampling_analysis['source_rate_confidence']}"
                )

                st.write(
                    f"**Reason:** "
                    f"{upsampling_analysis['source_rate_reason']}"
                )

                evidence = upsampling_analysis[
                    "evidence_22_24_db"
                ]

                drop_after = upsampling_analysis[
                    "drop_after_24_db"
                ]

                if evidence is not None:
                    st.write(
                        f"**22.3–23.7 kHz attenuation:** "
                        f"{evidence:.1f} dB"
                    )

                if drop_after is not None:
                    st.write(
                        f"**Additional drop above 24 kHz:** "
                        f"{drop_after:.1f} dB"
                    )

                with st.expander(
                    "Evidence flags"
                ):
                    for flag in upsampling_analysis[
                        "evidence_flags"
                    ]:
                        st.code(flag)

        except subprocess.CalledProcessError:
            st.warning(
                "FFmpeg analysis failed."
            )

    else:
        st.divider()

        st.subheader(
            "Проверка Hi-Res / Upsampling"
        )

        st.write(
            "**Status:** Not applicable"
        )

        if sample_rate_value:
            st.write(
                f"**Sample rate:** "
                f"{int(sample_rate_value) / 1000:g} kHz"
            )

        st.write(
            "**Reason:** тест применяется "
            "к файлам с sample rate выше 48 kHz."
        )

        # -----------------------------
    # ПРОВЕРКА BIT DEPTH PADDING
    # -----------------------------

    bit_depth_value = None

    raw_bits = stream.get(
        "bits_per_raw_sample"
    )

    sample_bits = stream.get(
        "bits_per_sample"
    )

    if (
        raw_bits
        and str(raw_bits) != "0"
    ):
        bit_depth_value = int(
            raw_bits
        )

    elif (
        sample_bits
        and str(sample_bits) != "0"
    ):
        bit_depth_value = int(
            sample_bits
        )

    st.divider()

    st.subheader(
        "Проверка 24-bit / Bit-depth padding"
    )

    if bit_depth_value == 24:

        try:
            bit_depth_analysis = (
                analyze_bit_depth_padding(
                    file_bytes,
                    uploaded_file.name,
                )
            )

            if not bit_depth_analysis[
                "supported"
            ]:
                st.write(
                    f"**Status:** "
                    f"{bit_depth_analysis['status']}"
                )

            else:
                st.write(
                    f"**Zero-padding 16 → 24-bit suspicion:** "
                    f"{bit_depth_analysis['suspicion']}"
                )

                st.write(
                    f"**Samples with zero lower 8 bits:** "
                    f"{bit_depth_analysis['zero_lsb_ratio'] * 100:.3f}%"
                )

                st.write(
                    f"**Distinct lower-byte values:** "
                    f"{bit_depth_analysis['unique_lsb_values']} / 256"
                )

                st.write(
                    f"**Active samples analyzed:** "
                    f"{bit_depth_analysis['active_samples']:,}"
                )

                if (
                    bit_depth_analysis[
                        "suspicion"
                    ] == "High"
                ):
                    st.write(
                        "**Rule:** почти все активные "
                        "samples имеют нулевые "
                        "младшие 8 бит."
                    )

                elif (
                    bit_depth_analysis[
                        "suspicion"
                    ] == "Medium"
                ):
                    st.write(
                        "**Rule:** использование "
                        "младших 8 бит ограничено."
                    )

                else:
                    st.write(
                        "**Rule:** младшие 8 бит "
                        "содержат изменяющиеся значения."
                    )

        except subprocess.CalledProcessError:
            st.write(
                "**Status:** FFmpeg analysis failed"
            )

        st.divider()

        st.write(
            "### Quantization structure"
        )

        try:
            quantization_analysis = (
                analyze_quantization_structure(
                    file_bytes,
                    uploaded_file.name,
                )
            )

            if not quantization_analysis[
                "supported"
            ]:
                st.write(
                    f"**Status:** "
                    f"{quantization_analysis['status']}"
                )

            else:
                st.write(
                    f"**Distinct PCM sample values:** "
                    f"{quantization_analysis['unique_sample_values']:,}"
                )

                st.write(
                    "**16-bit level limit:** "
                    "65,536"
                )

                st.write(
                    f"**Direct 16-bit mapping compatibility:** "
                    f"{quantization_analysis['direct_mapping_status']}"
                )

                st.write(
                    f"**Lower-byte entropy:** "
                    f"{quantization_analysis['low_byte_entropy']:.3f} "
                    f"/ 8.000 bits"
                )

                st.write(
                    f"**Lower-byte entropy ratio:** "
                    f"{quantization_analysis['normalized_entropy'] * 100:.2f}%"
                )

                st.write(
                    f"**Samples analyzed:** "
                    f"{quantization_analysis['analyzed_samples']:,}"
                )

                st.write(
                    f"**Reason:** "
                    f"{quantization_analysis['direct_mapping_reason']}"
                )

        except subprocess.CalledProcessError:
            st.write(
                "**Status:** FFmpeg quantization analysis failed"
            )
    
    else:
        st.write(
            "**Status:** Not applicable"
        )

        if bit_depth_value is not None:
            st.write(
                f"**Bit depth:** "
                f"{bit_depth_value}-bit"
            )

        st.write(
            "**Reason:** эта проверка применяется "
            "к 24-bit аудио."
        )
    
    st.divider()
    
    st.subheader("Спектрограмма")

    try:
        spectrogram = generate_spectrogram(
            file_bytes,
            uploaded_file.name,
        )

        st.image(
            spectrogram,
            caption="Спектрограмма всего аудиофайла",
        )

    except subprocess.CalledProcessError:
        st.error(
            "Не удалось построить спектрограмму."
        )
