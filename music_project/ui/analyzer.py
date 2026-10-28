from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

from music_project.core.disc import inspect_iso, parse_cue
from music_project.core.models import AudioError
from music_project.core.pcm import spectrogram
from music_project.ui.file_picker import choose_file
from music_project.ui.presentation import codec_text, container_text, cue_issue_text, duration_text
from music_project.ui.shared import (
    cached_analysis,
    export_json,
    show_finding,
    show_measurements,
    show_observations,
)

st.caption(
    "1. Выберите файл. 2. Нажмите «Анализировать». 3. Откройте подробности нужного измерения."
)
if st.button("Выбрать файл…", icon=":material/folder_open:", key="choose_audio"):
    try:
        selected_path = choose_file()
        if selected_path:
            st.session_state.analyzer_path = selected_path
            st.session_state.analysis_result = None
    except AudioError as exc:
        st.warning(str(exc))
st.caption(
    "Откроется обычное окно выбора файла на этом компьютере. Можно также вставить путь ниже."
)
with st.form("analyze_form"):
    selected = st.text_input(
        "Выбранный файл",
        key="analyzer_path",
        placeholder="Выберите файл кнопкой выше или вставьте полный путь",
    )
    submitted = st.form_submit_button("Анализировать", type="primary")
if submitted:
    st.session_state.analysis_result = None
    if not selected.strip():
        raise AudioError("Сначала выберите файл для анализа.")
    source = Path(selected.strip().strip(chr(34))).resolve(strict=True)
    if source.suffix.lower() == ".cue":
        st.session_state.analysis_result = ("cue", parse_cue(source))
    elif source.suffix.lower() == ".iso":
        st.session_state.analysis_result = ("iso", inspect_iso(source, st.session_state.settings))
    else:
        stat = source.stat()
        with st.spinner("Измеряем параметры файла…"):
            result = cached_analysis(
                str(source), stat.st_size, stat.st_mtime_ns, st.session_state.settings
            )
        st.session_state.analysis_result = ("audio", result)

stored = st.session_state.analysis_result
if stored:
    kind, value = stored
    if kind == "cue":
        st.subheader("CUE: структура альбома")
        show_measurements(
            {
                "Кодировка": value["encoding"].replace(
                    "fallback; verify metadata", "резервная; проверьте метаданные"
                ),
                **value["metadata"],
            }
        )
        st.dataframe(
            [
                {
                    "Файл": f["reference"],
                    "Ссылка допустима": "Да" if f["valid"] else "Нет",
                    "Файл существует": "Да" if f["exists"] else "Нет",
                }
                for f in value["files"]
            ],
            hide_index=True,
            alt="Файлы, указанные в CUE",
        )
        st.dataframe(
            [
                {
                    "Track": t["number"],
                    "Название": t.get("title", ""),
                    "Файл": t["file"] or "Ссылка отсутствует",
                    "INDEX 01, s": t["indexes"].get("01", 0) / 75
                    if "01" in t["indexes"]
                    else "Не указан",
                }
                for t in value["tracks"]
            ],
            hide_index=True,
            alt="Tracks и границы CUE",
        )
        for issue in value["issues"]:
            st.warning(cue_issue_text(issue))
        st.caption("Проверены метаданные и INDEX. Анализ аудио по отдельным Tracks не выполняется.")
        export_json("Скачать отчёт CUE", value, "cue-report.json")
    elif kind == "iso":
        st.subheader("ISO: распознавание образа")
        st.text(
            {
                "SACD signature detected": "Обнаружена сигнатура SACD.",
                "ISO9660; SACD not established": "Обнаружен ISO9660; сигнатура SACD не обнаружена.",
                "Unknown disc image": "Поддерживаемые сигнатуры образа не обнаружены.",
            }[value["type"]]
        )
        st.text(f"Размер: {value['size'] / 2**20:.2f} MiB")
        if value["backend"].startswith("Backend unavailable"):
            st.info("sacd_extract не найден. Чтение списка Tracks в этой версии не выполняется.")
        else:
            st.caption(
                "sacd_extract найден; чтение списка Tracks ещё не проверено и не подключено."
            )
        st.caption("Сигнатура не подтверждает исправность TOC или доступность аудио в образе.")
        export_json("Скачать отчёт ISO", value, "iso-report.json")
    else:
        result, context = value
        info = result.info
        st.subheader(info.name)
        with st.container(horizontal=True):
            st.metric("Codec", codec_text(info.codec), border=True)
            st.metric(
                "Native DSD rate" if info.kind == "DSD" else "Sample rate",
                f"{info.sample_rate / 1000:g} kHz" if info.sample_rate else "Нет данных от ffprobe",
                border=True,
            )
            st.metric("Channels", info.channels, border=True)
            if info.bit_depth:
                st.metric("Bit depth", f"{info.bit_depth}-bit", border=True)
        st.text(
            f"Container: {container_text(info.container)} · Размер: {info.size / 2**20:.2f} MiB · "
            f"Длительность: {duration_text(info.duration)}"
        )
        if info.bitrate:
            st.caption(f"Bitrate: {info.bitrate / 1000:.1f} kb/s")
        if info.channel_layout != "Unknown":
            st.caption(f"Channel layout: {info.channel_layout}")
            if info.channel_layout_source == "container convention":
                st.caption(
                    "Порядок stereo Channels принят по стандартному расположению в этом Container."
                )
        else:
            st.caption("Channel layout не указан в метаданных; порядок Channels не предполагается.")
        if context is not None:
            seconds = result.scope["decoded_seconds"]
            extent = "весь файл" if result.scope["complete_file"] else "часть файла"
            st.info(
                f"Spectrum, Sample Peak и Bit-depth: первые {seconds:g} s ({extent}). "
                "Loudness и True Peak: весь первый аудиопоток при успешном измерении."
            )
        for key, label in (("loudness", "Loudness и True Peak"), ("peaks", "Sample Peak и RMS")):
            if key in result.findings:
                metrics = result.findings[key].measurements
                with st.container(horizontal=True):
                    for field, name in (
                        ("integrated_lufs", "Integrated loudness · LUFS"),
                        ("true_peak_dbtp", "True Peak · dBTP"),
                        ("sample_peak_dbfs", "Sample Peak · dBFS"),
                    ):
                        if field in metrics:
                            number = metrics[field]
                            state_key = {
                                "integrated_lufs": "integrated_lufs_state",
                                "true_peak_dbtp": "true_peak_state",
                            }.get(field)
                            st.metric(
                                name,
                                f"{number:.2f}"
                                if number is not None
                                else "−∞"
                                if metrics.get(state_key) == "negative infinity"
                                else "−∞ (тишина)"
                                if field == "sample_peak_dbfs"
                                else "Нет конечного значения",
                            )
                show_finding(label, result.findings[key])
        for key, label in (
            ("lossy_history", "Cutoff"),
            ("upsampling", "Upsampling"),
            ("dsd", "Native DSD"),
        ):
            if key in result.findings:
                show_finding(label, result.findings[key])
        if "quantization" in result.findings:
            with st.container(border=True):
                st.markdown("**Bit-depth / Padding**")
                show_observations(result.findings["quantization"])
                show_finding(
                    "Quantization Structure", result.findings["quantization"], advanced=True
                )
        if context is not None:
            st.caption(
                "Cutoff / Nyquist boundary не подтверждают исторические Codec или Source rate; "
                "фильтрация даёт сходные признаки. Lower-byte entropy не подтверждает native 24-bit."
            )
            if st.toggle("Показать Spectrogram", key="spectrum_visible"):
                f, t, p = spectrogram(context)
                fig, ax = plt.subplots(figsize=(10, 4))
                image = ax.pcolormesh(t, f / 1000, p, shading="auto", vmin=-140, vmax=-20)
                ax.set(xlabel="Время, s", ylabel="Frequency, kHz")
                fig.colorbar(image, ax=ax, label="PSD, dB/Hz")
                st.pyplot(fig, alt="Spectrogram проверенного фрагмента PCM")
                plt.close(fig)
                st.caption(
                    "Window Hann, FFT 2048 или доступное число frames, Overlap 50%; "
                    "средняя мощность Channels без Downmix."
                )
            if st.toggle("Прослушать фрагмент", key="preview_visible"):
                if info.channels <= 2:
                    st.audio(
                        context.samples.T,
                        sample_rate=info.sample_rate,
                        alt="Проверенный фрагмент аудиофайла",
                    )
                    st.caption(
                        "Preview: WAV-представление для браузера; не проверка bit-perfect playback."
                    )
                else:
                    st.info("Preview поддерживает до двух Channels; Downmix не выполняется.")
        with st.expander("Метаданные и техническая диагностика", expanded=False):
            st.dataframe(
                [{"Tag": tag, "Значение": text} for tag, text in info.tags.items()],
                hide_index=True,
                alt="Метаданные файла",
            )
            st.dataframe(
                [
                    {
                        "Backend": name,
                        "Состояние": text.replace("Backend unavailable", "Не найден")
                        .replace("Available:", "Найден:")
                        .replace("version unverified", "версия не проверена"),
                    }
                    for name, text in result.backends.items()
                ],
                hide_index=True,
                alt="Состояние программ анализа",
            )
            show_measurements(result.scope, label="Область анализа")
            with st.expander("Исходные данные ffprobe (JSON)", expanded=False):
                st.json(info.raw)
        export_json("Скачать полный отчёт JSON", result.to_dict(), "audio-analysis.json")
