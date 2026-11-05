"""Everyday and expert presentations of the same saved origin evidence."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from music_project.core.config import backend_identity
from music_project.core.models import AudioError
from music_project.core.origin_models import ORIGIN_VERSION
from music_project.core.origin_reference import investigate_reference
from music_project.ui.file_picker import choose_file
from music_project.ui.presentation import duration_text

HYPOTHESIS_STATUS = {
    "Compatible but not distinguishable": "Совместимо, но неотличимо от альтернатив",
    "Inconclusive": "Неоднозначно",
    "Not testable with available data": "Данных для проверки недостаточно",
    "Supported by measured evidence": "Поддержано измеренными признаками",
    "Contradicted under stated assumptions": "Противоречит указанным предположениям",
}


def _request_full():
    st.session_state.origin_full_requested = True


def _open_reference():
    st.session_state.analysis_view = "expert"
    st.session_state.analysis_module = "provenance"
    st.session_state.origin_reference_visible = True


def show_origin_report(result, *, expert=False):
    finding = result.findings.get("origin_investigation")
    report = finding.measurements if finding else {}
    st.markdown("**Origin Investigation Report**")
    info = result.info
    family = result.findings.get("dsd")
    format_name = family.measurements["dsd_family"] if family else info.codec.upper()
    st.text(f"{format_name} · {info.channels} канала · {duration_text(info.duration)}")
    container = result.findings.get("dsd_container")
    integrity = result.findings.get("dsd_integrity")
    if container and container.status == "Failed":
        st.error(
            "Проверка структуры контейнера не пройдена. Диагностика сохранена в экспертном режиме."
        )
    if integrity and integrity.status == "Failed":
        st.error(
            "Декодирование завершилось ошибкой. Полная проверка не подтверждена; см. модуль «Целостность»."
        )
    if not report:
        st.text(
            "Исследование недоступно: "
            + (finding.summary if finding else "для этого входа нет применимого результата")
        )
        return
    st.markdown("**Что найдено**")
    st.markdown("\n".join("- " + discovery for discovery in report["discoveries"][:5]))
    compatible = [
        h for h in report["hypotheses"] if h["status"] == "Compatible but not distinguishable"
    ]
    st.markdown("**Что это означает**")
    if compatible:
        st.text(
            compatible[0]["title"]
            + ": совместимо с измерениями. Фильтрация и аналоговое ограничение дают похожий результат."
        )
    else:
        st.text(
            "Измерены границы полосы и изменение высокочастотного фона. "
            "Экспертный режим показывает кривые и проверенные объяснения."
        )
    st.caption(
        "Остаётся неизвестным: исторический источник и последовательность преобразований; "
        "формат файла и спектральные признаки этого не доказывают."
    )
    if not expert:
        with st.container(horizontal=True):
            if not result.scope.get("complete_file") and info.kind == "DSD":
                st.button("Проверить весь файл", on_click=_request_full, key="origin_full")
            st.button(
                "Сравнить с референсом", on_click=_open_reference, key="origin_reference_next"
            )
        st.caption(
            "Подробные измерения, проверенные гипотезы и методика доступны в экспертном режиме. "
            "Документы о происхождении издания требуют внешней проверки."
        )
        return
    st.markdown("**Оценённые гипотезы**")
    st.dataframe(
        [
            {
                "Гипотеза": h["title"],
                "Результат": HYPOTHESIS_STATUS.get(h["status"], h["status"]),
                "Поддерживающие признаки": " ".join(h["supporting_evidence"])
                or "Пороговые признаки не обнаружены",
                "Контрпризнаки": " ".join(h["contradicting_evidence"]) or "Не установлены",
            }
            for h in report["hypotheses"]
        ],
        hide_index=True,
        alt="Гипотезы совместимости и фактические свидетельства",
    )
    st.caption(
        "Гипотезы не взаимоисключающие. Контрпризнаки проверяют простую модель видимой постоянной границы, "
        "а не исключают всю историю PCM/DSD. Вероятности не вычисляются."
    )
    show_origin_plots(result, report)
    st.markdown("**Измеренные границы и устойчивость по каналам**")
    st.dataframe(
        [
            {
                "Кандидат, kHz": b["candidate_hz"] / 1000,
                "Канал": c["channel"],
                "Спад, dB": c["attenuation_db"],
                "Наклон, dB/kHz": c["local_slope_db_per_khz"],
                "Середина перехода, Hz": c["transition_midpoint_hz"],
                "Ширина перехода, Hz": c["transition_width_hz"],
                "Погрешность сетки, Hz": c["transition_uncertainty_hz"],
                "Пригоден сигнал": c["eligible"],
                "Контроль преобразования пройден": b["converted_chain_usable"],
                "Ячеек с признаком": b["channel_stability"][c["channel"] - 1]["detected_cells"],
                "Пригодных ячеек": b["channel_stability"][c["channel"] - 1]["eligible_cells"],
            }
            for b in report["boundaries"]
            for c in b["channels"]
        ],
        hide_index=True,
        alt="Измерения каждой кандидатной границы отдельно по каналам",
    )
    if report["noise"].get("status") == "Measured":
        st.markdown("**Ультразвуковой фон · исследовательские режимы**")
        st.caption(
            "Медианы PSD включают шум и тональные компоненты. Наклоны не определяют прежний DSD-rate."
        )
        st.dataframe(
            [
                {
                    "Канал": c["channel"],
                    "Переход, Hz": [c["regime_change"]["low_hz"], c["regime_change"]["high_hz"]]
                    if c.get("regime_change")
                    else None,
                    "Наклоны, dB/декаду": c["regime_change"]["slopes_db_per_decade"]
                    if c.get("regime_change")
                    else None,
                    "Ячеек с переходом": t["regime_change_cells"],
                    "Пригодных ячеек": t["retained_tested_cells"],
                    "Область перехода совпадает с native DSD": t[
                        "native_transition_range_overlaps"
                    ],
                }
                for c, t in zip(
                    report["noise"]["channels"],
                    report["noise"].get("temporal_summary", []),
                    strict=True,
                )
            ],
            hide_index=True,
            alt="Переходы спектрального фона по каналам и временная повторяемость",
        )
    if st.toggle("Проверить по референсу", key="origin_reference_visible"):
        show_reference(result)
    st.markdown("**Метод и ограничения**")
    for limitation in report["limitations"]:
        st.text(limitation)
    for key in ("lossy_history", "upsampling", "quantization"):
        if key in result.findings:
            label = {
                "quantization": "Bit-depth / Padding",
                "upsampling": "Upsampling",
                "lossy_history": "Cutoff",
            }[key]
            st.markdown(f"**Дополнительные PCM-признаки · {label}**")
            for observation in result.findings[key].observations:
                st.text(observation.summary)
    st.caption(
        "Полные контрольные параметры, пороги, численные результаты и исходные предупреждения: Техническое приложение."
    )


def show_origin_plots(result, report):
    st.caption(
        "PCM после явного преобразования и независимый native DSD показаны раздельно; "
        "сглаживание графиков PSD не применяется."
    )
    candidates = report["boundaries"]
    spectrum = result.findings.get("dsd_audible")
    spectrum = spectrum.measurements.get("spectrum") if spectrum else None
    if not spectrum:
        spectrum = report["scope"]["converted"].get("origin_pcm_spectrum")
    native = report.get("native", {})
    plots = []
    if spectrum and spectrum.get("status") == "Measured":
        plots.append(
            (
                "PCM после DSD-to-PCM" if result.info.kind == "DSD" else "Декодированный PCM",
                spectrum["frequencies_hz"],
                spectrum["density_fs2_per_hz"],
            )
        )
    if native.get("aggregate_frequencies_hz"):
        plots.append(
            (
                "Native DSD · ±1",
                native["aggregate_frequencies_hz"],
                native["aggregate_density_fs2_per_hz"],
            )
        )
    for title, frequencies, density in plots:
        f, p = np.asarray(frequencies), np.asarray(density)
        show = f <= 160000
        fig, ax = plt.subplots(figsize=(9, 3.1), layout="constrained")
        for channel in range(p.shape[1]):
            positive = p[:, channel] > 0
            levels = np.full(len(f), np.nan)
            levels[positive] = 10 * np.log10(p[positive, channel])
            ax.plot(f[show] / 1000, levels[show], label=f"Канал {channel + 1}", linewidth=0.8)
        for boundary in candidates:
            if any(c["detected"] for c in boundary.get("native_channels", [])) or (
                boundary.get("converted_chain_usable")
                and any(c["detected"] for c in boundary["channels"])
            ):
                ax.axvspan(
                    (boundary["candidate_hz"] - 2000) / 1000,
                    (boundary["candidate_hz"] + 2000) / 1000,
                    alpha=0.12,
                    color="gray",
                )
                ax.axvline(
                    boundary["candidate_hz"] / 1000, color="black", linewidth=0.7, linestyle=":"
                )
        ax.set(title=title, xlabel="Частота, kHz", ylabel="PSD, dB re FS²/Hz")
        ax.legend()
        st.pyplot(fig, alt="Спектр с отмеченными измеренными областями границ")
        plt.close(fig)
    profile = report["measurement_chain"]
    if profile.get("status") == "Measured":
        controls = profile["controls"]
        fig, ax = plt.subplots(figsize=(9, 2.5), layout="constrained")
        ax.scatter(
            [r["frequency_hz"] / 1000 for r in controls],
            [r["relative_gain_db"] for r in controls],
            s=20,
        )
        ax.axhline(-0.5, color="gray", linestyle=":")
        ax.set(
            xlabel="Контрольная частота, kHz",
            ylabel="Относительно 1 kHz, dB",
            title="Измеренная характеристика анализатора",
        )
        st.pyplot(fig, alt="Дискретные контрольные точки частотной характеристики FFmpeg")
        plt.close(fig)
        st.caption(
            "33 синтетических однобитных тона; измерена амплитуда входа и выхода. "
            "Контрольные точки не сертифицируют непрерывную АЧХ."
        )
    noise = report.get("noise", {})
    if noise.get("status") == "Measured":
        f = np.asarray(noise["frequencies_hz"])
        p = np.asarray(noise["median_density_fs2_per_hz"])
        fig, ax = plt.subplots(figsize=(9, 2.8), layout="constrained")
        for channel in range(p.shape[1]):
            good = p[:, channel] > 0
            ax.scatter(
                f[good] / 1000, 10 * np.log10(p[good, channel]), label=f"Канал {channel + 1}", s=18
            )
        ax.set(
            xlabel="Частота, kHz",
            ylabel="Медианная PSD, dB re FS²/Hz",
            title="Спектральный фон · медианы логарифмических полос",
        )
        ax.legend()
        st.pyplot(fig, alt="Измеренное изменение медианной спектральной плотности по частоте")
        plt.close(fig)
    cells = report["scope"]["temporal"].get("cells", [])
    if cells and candidates:
        candidate = st.selectbox(
            "Граница для проверки по времени",
            [b["candidate_hz"] for b in candidates],
            format_func=lambda f: f"{f / 1000:g} kHz",
            key="origin_timeline_candidate",
        )
        times = []
        drops = []
        for cell in cells:
            row = next(b for b in cell["boundaries"] if b["candidate_hz"] == candidate)
            values = [
                c["attenuation_db"]
                for c in row["channels"]
                if c["eligible"] and c["attenuation_db"] is not None
            ]
            if values:
                times.append((cell["start_seconds"] + cell["end_seconds"]) / 2)
                drops.append(float(np.median(values)))
        if times:
            fig, ax = plt.subplots(figsize=(9, 2.4), layout="constrained")
            ax.scatter(times, drops, s=20)
            ax.axhline(18, color="gray", linestyle=":")
            ax.set(xlabel="Время, s", ylabel="Спад, dB", title="Проверка временной устойчивости")
            st.pyplot(fig, alt="Измеренные спады в сохранённых временных ячейках")
            plt.close(fig)


@st.cache_data(max_entries=2, ttl=600, show_spinner=False)
def cached_reference(
    a, signature_a, b, signature_b, settings, backend_key, method_version, verify_identity, note
):
    return investigate_reference(
        a, b, settings, verify_identity=verify_identity, chronology_note=note
    )


def show_reference(result):
    if st.button("Выбрать референс…", key="choose_origin_reference"):
        try:
            selected = choose_file()
            if selected:
                st.session_state.origin_reference_path = selected
        except AudioError as exc:
            st.warning(str(exc))
    with st.form("origin_reference_form"):
        path = st.text_input("Файл референса", key="origin_reference_path")
        identity = st.checkbox(
            "Дополнительно проверить полные byte/PCM hashes", key="origin_reference_identity"
        )
        note = st.text_input(
            "Документы/сведения об источнике (не проверяются автоматически)",
            key="origin_chronology_note",
        )
        submitted = st.form_submit_button("Сравнить референс")
    st.caption(
        "Референс не считается аутентифицированным. Сравниваются первые до 8 s после явного resampling в 48 kHz float32."
    )
    if submitted:
        try:
            a, b = Path(result.info.path), Path(path.strip().strip('"')).resolve(strict=True)
            sa, sb = a.stat(), b.stat()
            settings = st.session_state.settings
            with st.spinner("Сравниваем указанные фрагменты…"):
                value = cached_reference(
                    str(a),
                    (sa.st_size, sa.st_mtime_ns),
                    str(b),
                    (sb.st_size, sb.st_mtime_ns),
                    settings,
                    backend_identity(settings),
                    ORIGIN_VERSION,
                    identity,
                    note,
                )
            st.session_state.origin_reference_result = value
        except (AudioError, OSError, ValueError) as exc:
            st.error(str(exc))
    value = st.session_state.get("origin_reference_result")
    if value and value.get("source") == result.info.path:
        st.text("Связь содержимого: " + value["same_recording"])
        st.text("Decoded-audio identity: " + value["decoded_audio_identity"])
        st.text("Хронология и направление преобразования: не установлены.")
        measurements = value.get("alignment", {}).get("measurements", {})
        if measurements:
            with st.container(horizontal=True):
                for key, label in (
                    ("correlation", "Корреляция"),
                    ("offset_b_seconds", "Смещение, s"),
                    ("gain_b_over_a_db", "Gain, dB"),
                    ("residual_rms_dbfs_after_gain", "Residual RMS, dBFS"),
                ):
                    number = measurements.get(key)
                    st.metric(
                        label, f"{number:.4g}" if number is not None else "Не интерпретируется"
                    )
        st.json(value)
