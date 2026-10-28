from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

from music_project.core.disc import inspect_iso, parse_cue
from music_project.core.pcm import spectrogram
from music_project.ui.shared import cached_analysis, export_json, show_finding

st.caption("Укажите путь на этом компьютере. Аудио обрабатывается локально.")
with st.form("analyze_form"):
    selected = st.text_input("Полный путь к аудиофайлу, CUE или ISO", key="analyzer_path")
    submitted = st.form_submit_button("Анализировать", type="primary")
if submitted:
    st.session_state.analysis_result = None
    source = Path(selected.strip().strip('"')).resolve(strict=True)
    if source.suffix.lower() == ".cue":
        st.session_state.analysis_result = ("cue", parse_cue(source))
    elif source.suffix.lower() == ".iso":
        st.session_state.analysis_result = ("iso", inspect_iso(source, st.session_state.settings))
    else:
        stat = source.stat()
        with st.spinner("Анализируем файл…"):
            result = cached_analysis(
                str(source), stat.st_size, stat.st_mtime_ns, st.session_state.settings
            )
        st.session_state.analysis_result = ("audio", result)

stored = st.session_state.analysis_result
if stored:
    kind, value = stored
    if kind != "audio":
        st.json(value)
        export_json("Скачать отчёт", value, f"{kind}-report.json")
    else:
        result, context = value
        info = result.info
        st.subheader(info.name)
        with st.container(horizontal=True):
            st.metric("Кодек", info.codec, border=True)
            st.metric("Частота, Hz", info.sample_rate, border=True)
            st.metric("Каналы", info.channels, border=True)
            st.metric("PCM bit depth", info.bit_depth or "Not applicable / Unknown", border=True)
        st.text(
            f"Контейнер: {info.container} · Размер: {info.size / 2**20:.2f} MiB · "
            f"Длительность: {info.duration if info.duration is not None else 'Unknown'} с"
        )
        st.caption(f"Bitrate: {info.bitrate or 'Unknown'} bit/s · Layout: {info.channel_layout}")
        st.warning("Историческое происхождение не устанавливается одними измерениями сигнала.")
        st.caption(f"Область спектра/квантования: {result.scope}")
        labels = {
            "peaks": "Пики",
            "loudness": "Громкость",
            "lossy_history": "Lossy history",
            "upsampling": "Upsampling",
            "quantization": "Quantization Structure",
            "dsd": "Native DSD",
        }
        # Essential uncertainty stays visible even when quantization details are collapsed.
        if "quantization" in result.findings:
            st.text(f"Bit-depth: {result.findings['quantization'].status}")
        for key, finding in result.findings.items():
            show_finding(labels[key], finding, advanced=key == "quantization")
        if context is not None:
            if st.toggle("Показать spectrogram", key="spectrum_visible"):
                f, t, p = spectrogram(context)
                fig, ax = plt.subplots(figsize=(10, 4))
                image = ax.pcolormesh(t, f / 1000, p, shading="auto", vmin=-140, vmax=-20)
                ax.set(xlabel="Время, s", ylabel="Частота, kHz")
                fig.colorbar(image, ax=ax, label="PSD, dBFS²/Hz")
                st.pyplot(fig, alt="Спектрограмма анализируемого фрагмента PCM")
                plt.close(fig)
                st.caption(
                    "Hann 2048 (или доступное число кадров), overlap 50%; mean channel power."
                )
            if st.toggle("Аудиопредпрослушивание фрагмента", key="preview_visible"):
                if info.channels <= 2:
                    st.audio(
                        context.samples.T,
                        sample_rate=info.sample_rate,
                        alt="Локальный фрагмент анализируемого файла",
                    )
                    st.caption(
                        "Preview: браузерное WAV-представление; не инструмент проверки идентичности."
                    )
                else:
                    st.info("Preview поддерживает до двух каналов; downmix не выполняется.")
        with st.expander("Метаданные, ffprobe и backend diagnostics", expanded=False):
            st.json(info.raw)
            st.json(result.backends)
        export_json("Скачать JSON-отчёт", result.to_dict(), "audio-analysis.json")
