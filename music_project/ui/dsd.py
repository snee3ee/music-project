"""DSD module: native facts, scope, conversion and measured bands without raw logs."""

import streamlit as st

from music_project.core.models import Analysis
from music_project.ui.presentation import status_text


def show_dsd(result: Analysis):
    from music_project.ui.analysis_views import cards

    native = result.findings["dsd"].measurements
    container = result.findings["dsd_container"].measurements
    conversion = result.findings["dsd_conversion"]
    st.markdown("### Native DSD")
    rate = native.get("native_rate_hz")
    bitrate = native.get("nominal_native_bitrate_bps")
    cards(
        [
            ("Контейнер", container.get("container", "Unknown")),
            ("Семейство DSD", native["dsd_family"]),
        ]
    )
    st.caption(
        f"Native rate: {rate / 1e6:g} MHz · каналы: {result.info.channels}"
        if rate
        else f"Частота не установлена · каналы: {result.info.channels}"
    )
    if bitrate:
        st.caption(f"Номинальный bitrate: {bitrate / 1000:.1f} kb/s · Рассчитано.")
    st.text("DST: " + status_text(native["dst_processing"]))
    st.markdown("### Измеренный выход DSD-to-PCM")
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
        ]
    )
    st.caption(
        "Проверка потока — в «Целостности», полосы — в «Спектре и уровнях», параметры метода — в приложении."
    )
