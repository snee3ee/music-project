"""Everyday conclusions and expert evidence computed from the same stored measurements."""

from dataclasses import asdict

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from music_project.core.conclusion_models import ReferenceProfile
from music_project.core.conclusions import build_conclusions, scope_text

TYPES = {
    "Measured fact": "Измеренный факт",
    "Verified fact": "Проверенный факт",
    "Mathematical derivation": "Математический расчёт",
    "Rule-based technical conclusion": "Вывод по правилу",
    "Evidence-supported hypothesis": "Гипотеза со свидетельствами",
    "Inconclusive": "Неоднозначно",
    "Not applicable": "Не применяется",
    "Unsupported": "Не поддерживается",
    "Not validated": "Не валидировано",
}


def selected_reference(controls=True):
    saved = st.session_state.get("technical_reference", ReferenceProfile())
    if not controls:
        return saved
    with st.expander("Технический референс", expanded=False):
        mode = st.selectbox(
            "Референс",
            ["none", "custom"],
            index=1
            if saved.loudness_lufs is not None or saved.peak_ceiling_dbtp is not None
            else 0,
            format_func=lambda x: (
                "Без референса — только измерения"
                if x == "none"
                else "Пользовательские LUFS / True Peak"
            ),
            key="technical_reference_widget",
        )
        if mode == "custom":
            use_loudness = st.checkbox(
                "Использовать цель громкости", value=True, key="reference_use_loudness"
            )
            target = st.number_input(
                "Выбранная цель, LUFS",
                value=saved.loudness_lufs if saved.loudness_lufs is not None else -14.0,
                step=0.5,
                key="reference_target",
            )
            use_peak = st.checkbox(
                "Учитывать потолок True Peak", value=True, key="reference_use_peak"
            )
            ceiling = st.number_input(
                "Выбранный потолок, dBTP",
                value=saved.peak_ceiling_dbtp if saved.peak_ceiling_dbtp is not None else -1.0,
                step=0.1,
                key="reference_ceiling",
            )
            saved = ReferenceProfile(
                "Custom", target if use_loudness else None, ceiling if use_peak else None
            )
            st.caption(
                "Пользовательские значения. Не универсальная норма для музыки и не гарантия конкретного сервиса. Gain рассчитывается; файл не изменяется."
            )
        else:
            saved = ReferenceProfile()
        st.session_state.technical_reference = saved
    return saved


def show_technical_findings(result):
    """Complete rules/evidence are rendered exclusively in Technical Appendix."""
    reference = selected_reference(False)
    conclusions = build_conclusions(result.info, result.scope, result.findings, reference)
    st.dataframe(
        [
            {
                "Вывод": c.title,
                "Тип": TYPES.get(c.statement_type, c.statement_type),
                "Утверждение": c.statement,
                "Область": scope_text(c.analysis_scope),
                "Правило": c.rule_id,
                "Версия": c.rule_version,
            }
            for c in conclusions
        ],
        hide_index=True,
        alt="Все выводы, правила, области и версии",
    )
    if (
        st.toggle("Свидетельства выбранного вывода", key="conclusion_evidence_visible")
        and conclusions
    ):
        selected = st.selectbox(
            "Вывод",
            range(len(conclusions)),
            format_func=lambda i: conclusions[i].title,
            key="conclusion_evidence_selection",
        )
        st.json(asdict(conclusions[selected]))


def show_timelines(result):
    loudness = result.findings.get("loudness")
    m = loudness.measurements if loudness else {}
    rows = m.get("timeline", [])
    finite_loudness = [
        r[key]
        for r in rows
        for key in (
            "momentary_min_lufs",
            "momentary_max_lufs",
            "short_term_min_lufs",
            "short_term_max_lufs",
        )
        if r[key] is not None
    ]
    if rows and finite_loudness:
        fig, ax = plt.subplots(figsize=(7.2, 2.6), layout="constrained")
        t = [(r["start_seconds"] + r["end_seconds"]) / 2 for r in rows]
        for prefix, label, color in [
            ("momentary", "Momentary · 400 ms", "gray"),
            ("short_term", "Short-term · 3 s", "tab:blue"),
        ]:
            low = np.array(
                [
                    r[prefix + "_min_lufs"] if r[prefix + "_min_lufs"] is not None else np.nan
                    for r in rows
                ]
            )
            high = np.array(
                [
                    r[prefix + "_max_lufs"] if r[prefix + "_max_lufs"] is not None else np.nan
                    for r in rows
                ]
            )
            ax.plot(t, high, label=label, color=color, linewidth=0.9)
            ax.fill_between(t, low, high, color=color, alpha=0.16)
        reference = st.session_state.get("technical_reference", ReferenceProfile())
        if reference.loudness_lufs is not None:
            ax.axhline(
                reference.loudness_lufs,
                color="black",
                linestyle=":",
                label="Референс Integrated LUFS (не порог M/S)",
            )
        ax.set(xlabel="Время, s", ylabel="Громкость, LUFS", title="Громкость во времени")
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
        if max(finite_loudness) - min(finite_loudness) < 1:
            middle = (max(finite_loudness) + min(finite_loudness)) / 2
            ax.set_ylim(middle - 0.5, middle + 0.5)
        ax.legend()
        st.pyplot(
            fig,
            width=720,
            alt="Измеренные Momentary и Short-term Loudness по времени с огибающей минимума и максимума",
        )
        plt.close(fig)
        st.caption("M: 400 ms · S: 3 s · 10 Hz; объединённые ячейки сохраняют min/max.")
    elif rows:
        st.caption("Нет конечных измерений в полных окнах M/S; график громкости не строится.")
    finding = result.findings.get("full_peaks")
    p = finding.measurements if finding else {}
    rows = p.get("timeline", [])
    if rows and not any(any(value > 0 for value in r["peak_linear"]) for r in rows):
        st.caption("Пики и RMS: нулевая амплитуда (−∞ dBFS); конечных значений для графика нет.")
        return
    if rows:
        fig, ax = plt.subplots(figsize=(7.2, 2.6), layout="constrained")
        t = [(r["start_seconds"] + r["end_seconds"]) / 2 for r in rows]
        channels = result.info.channels
        for ch in range(channels):
            amplitudes = np.array([r["peak_linear"][ch] for r in rows])
            levels = np.full(len(rows), np.nan)
            nonzero = amplitudes > 0
            levels[nonzero] = 20 * np.log10(amplitudes[nonzero])
            ax.plot(t, levels, label=f"Sample Peak · канал {ch + 1}", linewidth=0.9)
            energies = np.array([r["sum_squares"][ch] / r["frames"] for r in rows])
            rms = np.full(len(rows), np.nan)
            nonzero = energies > 0
            rms[nonzero] = 10 * np.log10(energies[nonzero])
            ax.plot(t, rms, label=f"RMS · канал {ch + 1}", linewidth=0.7, linestyle="--")
        ax.axhline(
            p["near_ceiling_dbfs"], color="gray", linestyle=":", label="Выбранный порог dBFS"
        )
        ax.set(
            xlabel="Время, s",
            ylabel="Уровень, dBFS",
            title="Пики и RMS во времени",
        )
        ax.legend()
        st.pyplot(
            fig,
            width=720,
            alt="Пики отсчётов по каналам, времени и выбранный порог около цифрового предела",
        )
        plt.close(fig)
        st.caption("Ячейки 100 ms; объединение сохраняет пики и энергию.")
