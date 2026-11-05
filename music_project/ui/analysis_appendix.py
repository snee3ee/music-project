"""One technical area for exact values, saved diagnostics, methods and export."""

import streamlit as st

from music_project.core.decoder import PCMContext
from music_project.core.models import Analysis
from music_project.ui.analysis_charts import pcm_spectrum_data
from music_project.ui.analysis_presentation import CATEGORIES, decoder_warnings, duration_sources
from music_project.ui.presentation import status_text
from music_project.ui.shared import export_json, show_measurements

SECTIONS = {
    "results": "Численные результаты",
    "spectrum": "Полные спектральные таблицы",
    "logs": "Диагностика декодера",
    "methods": "Методы и параметры",
    "metadata": "Метаданные ffprobe",
    "raw": "Полный JSON",
}


def show_appendix(result: Analysis, context: PCMContext | None = None):
    export_json("Скачать полный отчёт JSON", result.to_dict(), "audio-analysis.json")
    section = st.selectbox(
        "Раздел приложения",
        list(SECTIONS),
        format_func=SECTIONS.__getitem__,
        key="analysis_appendix",
    )
    if section == "metadata":
        st.dataframe(
            [{"Tag": key, "Значение": value} for key, value in result.info.tags.items()],
            hide_index=True,
            alt="Прочитанные теги файла",
        )
        st.json(result.info.raw)
    elif section == "raw":
        st.json(result.to_dict())
    elif section == "logs":
        st.caption("Сохранённая диагностика warning/error. Полный verbose-log не собирался.")
        groups = decoder_warnings(result)
        if groups:
            st.dataframe(
                [
                    {
                        "Сообщение": g.message,
                        "Событий": g.events,
                        "Интервалы": ", ".join(map(str, g.intervals)),
                    }
                    for g in groups
                ],
                hide_index=True,
                alt="Сгруппированные предупреждения декодера",
            )
        attempts = result.findings.get("dsd_integrity")
        attempts = attempts.measurements.get("attempts", []) if attempts else []
        for index, attempt in enumerate(attempts, 1):
            st.markdown(f"**Интервал {index} · {status_text(attempt['status'])}**")
            st.text(f"Начало: {attempt['start_seconds']} s; PCM frames: {attempt['frames']}")
            if attempt.get("warnings"):
                st.code("\n".join(attempt["warnings"]), language=None)
            if attempt.get("fatal_error"):
                st.code(attempt["fatal_error"], language=None)
        container = result.findings.get("dsd_container")
        if container:
            st.json({key: container.measurements.get(key, []) for key in ("errors", "warnings")})
        for key, finding in result.findings.items():
            if finding.status in {"Failed", "Unknown", "Unsupported", "Partial"}:
                st.text(f"{key}: {finding.summary}")
    elif section == "methods":
        st.text(f"Приложение {result.app_version} · Общий метод {result.method_version}")
        st.caption(
            "ONLY FACTS. NO OPINIONS. Категория измерения не подтверждает историческое происхождение."
        )
        st.dataframe(
            [{"Категория": key, "Обозначение": value} for key, value in CATEGORIES.items()],
            hide_index=True,
            alt="Раздельные категории фактов, проверки, расчёта и неопределённости",
        )
        st.dataframe(
            [
                {"Backend": key, "Версия / доступность": value}
                for key, value in result.backends.items()
            ],
            hide_index=True,
            alt="Версии backend",
        )
        st.markdown("**Область и параметры анализа**")
        st.json(result.scope)
        if result.info.duration_details:
            st.markdown("**Политика длительности аудио**")
            st.json(result.info.duration_details)
        for key, finding in result.findings.items():
            st.markdown(f"**{key} · {finding.method_version}**")
            st.text(finding.method or "Отдельный метод не указан в сохранённом результате.")
            for limitation in finding.limitations:
                st.text(limitation)
            if finding.evidence:
                st.text("Evidence flags: " + ", ".join(finding.evidence))
        conversion = result.findings.get("dsd_conversion")
        if conversion:
            st.markdown("**Преобразование и фактический выход**")
            st.json(conversion.measurements)
    elif section == "spectrum":
        spectrum = result.findings.get("dsd_audible")
        spectrum = spectrum.measurements.get("spectrum") if spectrum else None
        if spectrum and spectrum.get("status") == "Measured":
            columns = {"Частота, Hz": spectrum["frequencies_hz"]}
            for channel in range(spectrum["channels"]):
                columns[f"Канал {channel + 1}, FS²/Hz"] = [
                    r[channel] for r in spectrum["density_fs2_per_hz"]
                ]
            st.dataframe(
                columns,
                hide_index=True,
                alt="Полная PSD по FFT bins без округления исходных значений",
            )
            st.markdown("**Полосы: точная мощность, медианная PSD, L−R и применимость**")
            st.json(spectrum["bands"])
            st.markdown("**FFT, нормализация и область**")
            st.json(
                {
                    key: value
                    for key, value in spectrum.items()
                    if key not in {"density_fs2_per_hz", "frequencies_hz", "bands"}
                }
            )
        elif context is not None and len(context.samples) >= 256:
            frequencies, density = pcm_spectrum_data(context)
            st.dataframe(
                {"Частота, Hz": frequencies, "Средняя мощность каналов, FS²/Hz": density},
                hide_index=True,
                alt="Полная PCM PSD без округления исходных значений",
            )
            export_json(
                "Скачать спектральные данные JSON",
                {
                    "frequencies_hz": frequencies.tolist(),
                    "density_fs2_per_hz": density.tolist(),
                    "channel_handling": "mean channel power; no downmix",
                    "scope": result.scope,
                    "sample_rate_hz": result.info.sample_rate,
                    "nfft": min(8192, len(context.samples)),
                    "window": "periodic Hann",
                    "overlap": "50%",
                    "detrend": "constant",
                    "method_version": result.method_version,
                },
                "pcm-spectrum.json",
            )
        else:
            st.text(
                "Отдельная PSD-таблица не сохранена в этом результате. "
                "Доступные спектральные признаки и параметры приведены в численных результатах."
            )
    else:
        st.caption(
            "Точные исходные числа сохраняются в JSON. Таблицы интерфейса могут округлять отображение."
        )
        st.markdown("**Длительность**")
        st.json(duration_sources(result))
        if result.info.duration_details:
            st.json(result.info.duration_details)
        for key, finding in result.findings.items():
            st.markdown(f"**{key} · {status_text(finding.status)}**")
            if key == "dsd_audible":
                st.json({k: v for k, v in finding.measurements.items() if k != "spectrum"})
            elif key in {"dsd_integrity", "dsd_conversion"}:
                st.caption(
                    "Исходные сообщения — в диагностике декодера; команды — в методах и параметрах."
                )
                st.json(
                    {
                        k: v
                        for k, v in finding.measurements.items()
                        if k not in {"attempts", "failed_segments", "commands"}
                    }
                )
            elif key.startswith("dsd"):
                # Generic 3-decimal formatting would turn tiny nonzero band powers into 0.
                st.json(finding.measurements)
            else:
                show_measurements(finding.measurements)
            if finding.observations:
                st.json([vars(o) for o in finding.observations])
