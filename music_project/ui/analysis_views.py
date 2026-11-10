"""Analyze File modules. Switching modules reads saved results without decoding."""

import streamlit as st

from music_project.core.decoder import PCMContext
from music_project.core.models import Analysis
from music_project.ui.analysis_charts import (
    pcm_spectrogram_data,
    pcm_spectrum_data,
    show_density,
    show_dsd_bands,
)
from music_project.ui.analysis_presentation import (
    MODULES,
    available_modules,
    duration_display,
    integrity_summary,
)
from music_project.ui.presentation import codec_text, container_text, status_text
from music_project.ui.technical_findings import show_technical_findings


def cards(values: list[tuple[str, str]]):
    with st.container(horizontal=True):
        for label, value in values:
            st.metric(label, value, border=True)


def show_overview(result: Analysis):
    info = result.info
    native = result.findings.get("dsd", None)
    rate = (
        f"{info.sample_rate / 1e6:g} MHz"
        if info.kind == "DSD"
        else f"{info.sample_rate / 1000:g} kHz"
    )
    container = result.findings.get("dsd_container")
    name = container.measurements.get("container") if container else container_text(info.container)
    cards(
        [
            ("Codec", codec_text(info.codec)),
            ("Контейнер", name),
            (
                "Native DSD rate" if info.kind == "DSD" else "Sample rate",
                rate if info.sample_rate else "Неизвестно",
            ),
            ("Каналы", str(info.channels)),
        ]
    )
    properties = [duration_display(result), ("Размер", f"{info.size / 2**20:.2f} MiB")]
    if info.bit_depth:
        properties.append(("Bit depth", f"{info.bit_depth}-bit"))
    if native:
        properties.append(("Семейство DSD", native.measurements["dsd_family"]))
        bitrate = native.measurements.get("nominal_native_bitrate_bps")
        if bitrate:
            properties.append(
                ("Bitrate · рассчитано", f"{bitrate / 1000:,.1f} kb/s".replace(",", " "))
            )
    elif info.bitrate:
        properties.append(("Bitrate · ffprobe", f"{info.bitrate / 1000:g} kb/s"))
    cards(properties)
    show_technical_findings(result, controls=False)
    if info.kind == "DSD":
        st.caption(
            "Источник длительности: " + info.duration_source + ". "
            "Вторичные оценки и точные значения — в техническом приложении."
        )
    integrity = integrity_summary(result)
    measured = any(
        f.status == "Measured"
        for k, f in result.findings.items()
        if k in {"peaks", "loudness", "dsd_audible"}
    )
    warnings = integrity["warning_events"]
    cards(
        [
            ("Проверка потока", status_text(integrity["decode_status"])),
            ("Измерения сигнала", "Измерено" if measured else "Недоступны"),
            ("Предупреждения декодера", str(warnings) if warnings is not None else "Не сохранены"),
        ]
    )
    st.text("Историческое происхождение: не установлено.")
    if integrity["fatal_errors"] or integrity["container_errors"]:
        st.error(
            "Проверка выявила ошибку. Категория и затронутые интервалы — в модуле «Целостность»."
        )
    if integrity["container_warnings"]:
        st.caption("Есть замечания к метаданным/источнику длительности. Откройте «Целостность».")
    if info.kind != "DSD":
        st.caption(
            f"Спектр, Sample Peak и quantization: первые {result.scope['decoded_seconds']:g} s. "
            "Loudness/True Peak: полный проход при успешном измерении."
        )


def show_integrity(result: Analysis):
    summary = integrity_summary(result)
    cards(
        [
            (
                "Контейнер",
                "Отдельная проверка не выполнялась"
                if result.info.kind != "DSD"
                else status_text(summary["container_status"]),
            ),
            ("Декодирование", status_text(summary["decode_status"])),
            (
                "Полный проход декодера",
                "Проверено" if summary["complete_file"] else "Не подтверждена",
            ),
        ]
    )
    warning_count = summary["warning_events"]
    cards(
        [
            ("Интервалы", str(summary["intervals"])),
            ("Прочитано / преобразовано", f"{summary['decoded_seconds']:.3f} s"),
            ("Предупреждения", str(warning_count) if warning_count is not None else "Не сохранены"),
            (
                "Фатальные ошибки",
                str(len(summary["fatal_errors"]))
                if result.info.kind == "DSD" or "pcm_integrity" in result.findings
                else "Нет отдельной проверки",
            ),
        ]
    )
    if result.info.kind != "DSD":
        show_technical_findings(result, controls=False, category={"integrity"})
        if not summary["complete_file"]:

            def request_pcm_full():
                st.session_state.technical_full_requested = True

            st.button("Измерить весь PCM-поток", key="technical_full", on_click=request_pcm_full)
        st.caption(
            "Декодирование и встроенный FLAC MD5 не аутентифицируют архивную копию. Независимая проверка всех полей контейнера не выполнялась."
        )
        return
    ranges = result.scope.get("ranges", [])
    if ranges:
        st.dataframe(
            [
                {
                    "Интервал": i,
                    "Начало, s": round(r["start_seconds"], 3),
                    "Прочитано, s": round(r["decoded_seconds"], 3),
                    "Статус": status_text(r["status"]),
                }
                for i, r in enumerate(ranges, 1)
            ],
            hide_index=True,
            alt="Область проверки DSD",
        )
    if not summary["complete_file"]:
        st.text("Весь аудиопоток не проверен. Результаты относятся к указанным интервалам.")
    for group in summary["warning_groups"]:
        st.text(
            f"{group.summary} Событий: {group.events}; интервалы: "
            + ", ".join(map(str, group.intervals))
            + "."
        )
    for index, attempt in enumerate(
        result.findings["dsd_integrity"].measurements.get("attempts", []), 1
    ):
        if attempt.get("fatal_error"):
            message = attempt["fatal_error"]
            reason = (
                "FFmpeg недоступен"
                if message.startswith("Backend unavailable")
                else (
                    "Декодирование отменено/ограничено"
                    if attempt["status"] == "Partial"
                    else "Ошибка декодирования/выходного потока"
                )
            )
            st.error(
                f"Интервал {index}: {reason}. Исходная диагностика сохранена в техническом приложении."
            )
    if summary["container_errors"]:
        st.error(
            f"Несогласованность контейнера: {len(summary['container_errors'])} событий. "
            "Исходные сообщения — в техническом приложении."
        )
    st.caption(
        "Источники длительности и вторичные оценки — в техническом приложении. "
        "Разница оценок сама по себе не доказывает повреждение."
    )
    if summary["container_warnings"]:
        st.text(
            "Зафиксированы замечания контейнерной проверки: "
            + str(len(summary["container_warnings"]))
            + ". Текст и точные значения сохранены в приложении."
        )


def _number(values: dict, field: str) -> str:
    value = values.get(field)
    state = values.get(
        {"integrated_lufs": "integrated_lufs_state", "true_peak_dbtp": "true_peak_state"}.get(field)
    )
    if value is not None:
        return f"{value:.2f}"
    return (
        "−∞"
        if state == "negative infinity" or field in {"sample_peak_dbfs", "rms_dbfs"}
        else "Не определено"
    )


def show_measurements_module(result: Analysis, context: PCMContext | None):
    show_technical_findings(result, expert=True)
    if result.info.kind == "DSD":
        show_dsd_bands(result)
        spectrum = result.findings["dsd_audible"].measurements.get("spectrum")
        if (
            spectrum
            and spectrum.get("status") == "Measured"
            and st.toggle("Показать PSD после DSD-to-PCM", key="dsd_psd")
        ):
            show_density(
                spectrum["frequencies_hz"],
                spectrum["density_fs2_per_hz"],
                labels=[f"Канал {i + 1}" for i in range(spectrum["channels"])],
            )
        return
    loudness = result.findings.get("loudness")
    peak = result.findings["peaks"].measurements
    if loudness and loudness.status == "Measured":
        cards(
            [
                (label, _number(loudness.measurements, key))
                for key, label in (
                    ("integrated_lufs", "Integrated loudness · LUFS"),
                    ("true_peak_dbtp", "True Peak · dBTP"),
                    ("lra_lu", "LRA · LU"),
                )
            ]
        )
        st.caption("Измерено по всему первому аудиопотоку.")
    elif loudness:
        st.text(
            "Loudness/True Peak: " + status_text(loudness.status) + ". Диагностика — в приложении."
        )
    cards(
        [
            ("Sample Peak · dBFS", _number(peak, "sample_peak_dbfs")),
            ("RMS · dBFS", _number(peak, "rms_dbfs")),
            ("Crest factor · dB", _number(peak, "crest_factor_db")),
            ("Full-scale samples", str(sum(peak.get("full_scale_samples_per_channel", [])))),
        ]
    )
    st.caption(
        f"Измерено в первых {result.scope['decoded_seconds']:g} s. Full-scale samples не доказывают clipping."
    )
    if context is None:
        return
    if len(context.samples) >= 256:
        frequencies, density = pcm_spectrum_data(context)
        show_density(frequencies, density, labels=["Средняя мощность каналов"])
        st.caption(
            "Welch PSD: Hann, FFT до 8192, overlap 50%, detrend=constant; усреднение мощности без downmix."
        )
    if st.toggle("Показать Spectrogram", key="spectrum_visible"):
        import matplotlib.pyplot as plt

        from music_project.core.models import AudioError

        try:
            f, t, p = pcm_spectrogram_data(context)
            fig, ax = plt.subplots(figsize=(9, 3.2), layout="constrained")
            image = ax.pcolormesh(t, f / 1000, p, shading="auto", vmin=-140, vmax=-20)
            ax.set(xlabel="Время, s", ylabel="Частота, kHz")
            fig.colorbar(image, ax=ax, label="PSD, dB re FS²/Hz")
            st.pyplot(fig, alt="Спектрограмма измеренного PCM-фрагмента")
            plt.close(fig)
            st.caption(
                "Hann, FFT до 2048, overlap 50%; display floor −200 dB re FS²/Hz, "
                "цветовая шкала −140…−20. Средняя мощность каналов, без downmix."
            )
        except AudioError as exc:
            st.info(str(exc))
    if st.toggle("Прослушать фрагмент", key="preview_visible"):
        if result.info.channels <= 2:
            st.audio(
                context.samples.T,
                sample_rate=result.info.sample_rate,
                alt="PCM-фрагмент для прослушивания",
            )
            st.caption("WAV-представление для браузера; не проверка bit-perfect playback.")
        else:
            st.info("Preview поддерживает до двух каналов; downmix не выполняется.")


def show_provenance(result: Analysis):
    from music_project.ui.origin import show_origin_report

    show_technical_findings(result, expert=True, controls=False, category={"origin"})
    show_origin_report(result, expert=True)


def show_analysis(result: Analysis, context: PCMContext | None):
    st.subheader(result.info.name)
    view = st.segmented_control(
        "Уровень представления",
        ["everyday", "expert"],
        default=None if "analysis_view" in st.session_state else "everyday",
        format_func=lambda v: "Обычный" if v == "everyday" else "Эксперт",
        required=True,
        key="analysis_view",
    )
    if view == "everyday":
        from music_project.ui.origin import show_origin_report

        show_technical_findings(result)
        if result.info.kind == "DSD":
            show_origin_report(result)
        else:
            from music_project.ui.origin import _open_reference

            st.button(
                "Сравнить с референсом", on_click=_open_reference, key="origin_reference_next"
            )
        return
    options = available_modules(result)
    if st.session_state.get("analysis_module") not in options:
        st.session_state.analysis_module = "overview"
    module = st.segmented_control(
        "Модули анализа",
        options,
        format_func=MODULES.__getitem__,
        required=True,
        key="analysis_module",
        width="stretch",
    )
    if module == "overview":
        show_overview(result)
    elif module == "integrity":
        show_integrity(result)
    elif module == "measurements":
        show_measurements_module(result, context)
    elif module == "provenance":
        show_provenance(result)
    elif module == "dsd":
        from music_project.ui.dsd import show_dsd

        show_dsd(result)
    elif module == "appendix":
        from music_project.ui.analysis_appendix import show_appendix

        show_appendix(result, context)
