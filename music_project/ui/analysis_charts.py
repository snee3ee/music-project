"""Charts of saved measurements; no decoding. PCM plot FFTs use bounded caches."""

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from music_project import METHOD_VERSION
from music_project.core.decoder import PCMContext
from music_project.core.pcm import spectrogram, spectrum
from music_project.ui.analysis_presentation import band_rows


@st.cache_data(max_entries=2, ttl=600, show_spinner=False)
def pcm_spectrum_data(context: PCMContext, method_version: str = METHOD_VERSION):
    return spectrum(context)


@st.cache_data(max_entries=2, ttl=600, show_spinner=False)
def pcm_spectrogram_data(context: PCMContext, method_version: str = METHOD_VERSION):
    return spectrogram(context)


def show_band_chart(bands: list[dict], label: str, *, expert=False):
    available = [b for b in bands if b["status"] == "Measured"]
    if not available:
        st.caption("Нет доступных измерений в этих полосах.")
        return
    fig, ax = plt.subplots(figsize=(6.3, 2.8), layout="constrained")
    positions = np.arange(len(available))
    channels = len(available[0]["power_db_re_fs2"])
    finite_count = 0
    for channel in range(channels):
        values = [b["power_db_re_fs2"][channel] for b in available]
        finite = np.array([v is not None for v in values])
        finite_count += int(finite.sum())
        offset = (channel - (channels - 1) / 2) * 0.28
        # Points, not bars against an arbitrary dB baseline; no interpolation/smoothing.
        ax.scatter(
            positions[finite] + offset,
            np.array(values, dtype=float)[finite],
            label=f"Канал {channel + 1}",
            s=35,
        )
    if finite_count:
        ax.set_xticks(positions, [r["Полоса, kHz"] for r in band_rows(available)])
        ax.set(xlabel="Полоса, kHz", ylabel="Мощность, dB re FS²")
        ax.legend()
        st.pyplot(fig, width=540, alt=label)
    else:
        st.caption("Мощность во всех доступных полосах равна нулю (−∞ dB re FS²).")
    plt.close(fig)
    # Compact dB table retains exact-zero and undefined-ratio semantics.
    rows = band_rows(available)
    for row in rows:
        row.pop("Статус", None)
    if expert:
        st.dataframe(rows, hide_index=True, alt="Мощность полос и различия каналов")
    unavailable = [b for b in bands if b["status"] != "Measured"]
    if unavailable:
        st.caption(
            "Недоступные полосы: "
            + ", ".join(f"{b['low_hz'] / 1000:g}–{b['high_hz'] / 1000:g} kHz" for b in unavailable)
            + ". Значения для них не вычислены."
        )


def show_density(frequencies, density, *, labels: list[str], max_hz: float | None = None):
    f, p = np.asarray(frequencies), np.asarray(density)
    if p.ndim == 1:
        p = p[:, None]
    selected = f <= max_hz if max_hz is not None else np.ones(len(f), dtype=bool)
    if not np.any(np.isfinite(p[selected]) & (p[selected] > 0)):
        st.caption(
            "PSD равна нулю (−∞); конечных значений для графика нет."
            if np.all(p[selected] == 0)
            else "Нет пригодных значений PSD для графика."
        )
        return
    fig, ax = plt.subplots(figsize=(7.2, 2.6), layout="constrained")
    for channel in range(p.shape[1]):
        db = np.full(len(p), np.nan)
        positive = p[:, channel] > 0
        db[positive] = 10 * np.log10(p[positive, channel])
        ax.plot(f[selected] / 1000, db[selected], label=labels[channel], linewidth=1)
    ax.set(xlabel="Частота, kHz", ylabel="PSD, dB re FS²/Hz")
    ax.legend()
    st.pyplot(fig, width=720, alt="Измеренная PSD с указанными частотами и каналами")
    plt.close(fig)


def show_dsd_bands(result, *, expert=False):
    st.caption("Измерен PCM после DSD-to-PCM; native DSD показан отдельно в Origin Investigator.")
    columns = st.columns(2)
    for column, (key, label) in zip(
        columns,
        (
            ("dsd_audible", "Слышимые полосы · Audible-band Spectrum"),
            ("dsd_ultrasonic", "Ультразвуковые полосы · Ultrasonic Noise Profile"),
        ),
        strict=True,
    ):
        with column:
            st.markdown(f"**{label}**")
            show_band_chart(
                result.findings[key].measurements.get("bands", []), label, expert=expert
            )
