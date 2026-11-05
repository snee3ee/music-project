"""DSD module: native facts, scope, conversion and measured bands without raw logs."""

import streamlit as st

from music_project.core.models import Analysis
from music_project.ui.analysis_charts import show_dsd_bands
from music_project.ui.analysis_presentation import integrity_summary
from music_project.ui.presentation import status_text


def show_dsd(result: Analysis):
    from music_project.ui.analysis_views import cards

    native = result.findings["dsd"].measurements
    container = result.findings["dsd_container"].measurements
    integrity = integrity_summary(result)
    conversion = result.findings["dsd_conversion"]
    st.markdown("**A / Свойства Native DSD**")
    rate = native.get("native_rate_hz")
    bitrate = native.get("nominal_native_bitrate_bps")
    cards(
        [
            ("Контейнер", container.get("container", "Unknown")),
            ("Семейство DSD", native["dsd_family"]),
            ("Native rate", f"{rate / 1e6:g} MHz" if rate else "Unknown"),
            ("Каналы", str(result.info.channels)),
        ]
    )
    if bitrate:
        st.caption(f"Номинальный bitrate: {bitrate / 1000:.1f} kb/s · Рассчитано.")
    st.text("DST processing: " + native["dst_processing"])
    st.markdown("**B / Проверка потока**")
    cards(
        [
            ("Декодирование", status_text(integrity["decode_status"])),
            ("Интервалы", str(integrity["intervals"])),
            ("Прочитанный PCM", f"{integrity['decoded_seconds']:.3f} s"),
            ("Предупреждения", str(integrity["warning_events"])),
        ]
    )
    st.caption(
        "Интервалы и источники длительности — в модуле «Целостность». "
        "Исходная диагностика — в техническом приложении."
    )
    st.markdown("**C / DSD-to-PCM**")
    headers = conversion.measurements.get("output_headers", [])
    verified = [h for h in headers if h]
    cards(
        [
            ("Преобразование", status_text(conversion.status)),
            (
                "Фактическая PCM rate",
                ", ".join(
                    f"{rate / 1000:g} kHz"
                    for rate in sorted({h["sample_rate_hz"] for h in verified})
                )
                if verified
                else "Не валидировано",
            ),
            ("Метод", conversion.method_version),
        ]
    )
    st.caption(result.backends.get("ffmpeg", "Unknown"))
    st.markdown("**D–E / Слышимые и ультразвуковые полосы**")
    show_dsd_bands(result)
    st.markdown("**F / Свидетельства преобразований**")
    st.text("Исторический источник: Unknown.")
    st.caption("Спектр после преобразования не устанавливает исходную цепочку PCM/DSD/analog.")
