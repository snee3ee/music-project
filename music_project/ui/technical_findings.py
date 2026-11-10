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


def show_technical_findings(result, *, expert=False, controls=True, category=None):
    reference = selected_reference(controls and result.info.kind != "DSD")
    conclusions = build_conclusions(result.info, result.scope, result.findings, reference)
    if category:
        conclusions = [c for c in conclusions if c.category in category]
    st.markdown("**Technical Findings · Технические выводы**")
    if expert:
        st.dataframe(
            [
                {
                    "Вывод": c.title,
                    "Тип": TYPES.get(c.statement_type, c.statement_type),
                    "Утверждение": c.statement,
                    "Область": scope_text(c.analysis_scope),
                    "Правило": c.rule_id,
                }
                for c in conclusions
            ],
            hide_index=True,
            alt="Выводы, типы утверждений, области и детерминированные правила",
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
    else:
        wanted = [
            "loudness.integrated",
            "reference.gain-plan",
            "peaks.true-peak",
            "peaks.true-peak-zero",
            "dynamics.lra",
            "peaks.rails",
            "integrity.flac-md5",
            "integrity.decode",
            "loudness.unavailable",
        ]
        chosen = [c for cid in wanted for c in conclusions if c.conclusion_id == cid]
        if not chosen:
            chosen = conclusions[:3]
        for c in chosen[:7]:
            st.markdown(f"**{c.title}.** {c.statement}")
    if result.info.kind != "DSD":
        st.caption(
            "LUFS: взвешенная громкость с gating. True Peak: оценка пиков между отсчётами. "
            "LRA: изменение громкости, не качество динамики. Достижение цифрового предела не устанавливает прежнее clipping."
        )
        if expert or st.toggle("Громкость и пики по времени", key="technical_timeline_visible"):
            show_timelines(result)


def show_timelines(result):
    loudness = result.findings.get("loudness")
    m = loudness.measurements if loudness else {}
    rows = m.get("timeline", [])
    if rows:
        fig, ax = plt.subplots(figsize=(9, 3), layout="constrained")
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
        ax.legend()
        st.pyplot(
            fig,
            alt="Измеренные Momentary и Short-term Loudness по времени с огибающей минимума и максимума",
        )
        plt.close(fig)
        st.caption(
            scope_text(m.get("scope", {}))
            + ". Данные 10 Hz; при объединении ячеек сохранены min/max. Пропуски не заменяются нулём; кривая S — не Integrated LUFS."
        )
    finding = result.findings.get("full_peaks")
    p = finding.measurements if finding else {}
    rows = p.get("timeline", [])
    if rows:
        fig, ax = plt.subplots(figsize=(9, 3), layout="constrained")
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
            fig, alt="Пики отсчётов по каналам, времени и выбранный порог около цифрового предела"
        )
        plt.close(fig)
        st.caption(
            scope_text(p.get("scope", {}))
            + ". Начальные ячейки 100 ms; объединённые сохраняют максимум и суммарную энергию. Нулевые амплитуды не рисуются как 0 dBFS."
        )
