"""Scoped signal groups: numbers first, concise explanation, optional evidence."""

import streamlit as st

from music_project.core.conclusion_models import ReferenceProfile
from music_project.core.conclusions import build_conclusions
from music_project.ui.analysis_charts import (
    pcm_spectrogram_data,
    pcm_spectrum_data,
    show_density,
    show_dsd_bands,
)
from music_project.ui.result_summary import number_text, scope_label, signal_values
from music_project.ui.technical_findings import selected_reference, show_timelines

METRIC_HELP = {
    "Integrated · LUFS": "Громкость программы с частотным взвешиванием и gating; не положение регулятора громкости.",
    "True Peak · dBTP": "Оценка реконструированного пика, включая пики между отсчётами.",
    "LRA · LU": "Изменение громкости по методу LRA; не оценка качества динамики.",
    "Crest Factor · dB": "Разность Sample Peak и RMS одной области измерения.",
}


def metric_row(values):
    cols = st.columns(len(values))
    for col, (label, value) in zip(cols, values, strict=True):
        col.metric(label, value, help=METRIC_HELP.get(label), border=False)


def show_levels(result, context, *, expert=False):
    if result.info.kind == "DSD":
        st.markdown("### Спектр после преобразования DSD")
        show_dsd_bands(result, expert=expert)
        spectrum = result.findings.get("dsd_audible")
        spectrum = spectrum.measurements.get("spectrum") if spectrum else None
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
        st.caption(scope_label(result.scope, logical="logical_source" in result.findings))
        return
    loud, peak = signal_values(result)
    reference = st.session_state.get("technical_reference", ReferenceProfile())
    conclusions = {
        c.conclusion_id: c
        for c in build_conclusions(result.info, result.scope, result.findings, reference)
    }
    st.markdown("**Громкость**")
    metric_row(
        [
            (label, number_text(loud, key))
            for key, label in [("integrated_lufs", "Integrated · LUFS"), ("lra_lu", "LRA · LU")]
        ]
    )
    st.caption(scope_label(loud.get("scope", {})))
    st.text("LRA описывает изменение громкости по времени.")
    if (
        not loud
        or loud.get("integrated_lufs") is None
        and loud.get("integrated_lufs_state") != "negative infinity"
    ):
        st.text(
            "Для Integrated нет пригодного измерения; отсутствующее значение не заменяется нулём."
        )
    gain = conclusions.get("reference.gain-plan")
    if gain:
        st.text(gain.statement)
    # The controls follow the results. Widget state is processed before the next rerun.
    previous = reference
    selected_reference()
    current = st.session_state.get("technical_reference", ReferenceProfile())
    if current != previous:
        st.rerun()
    st.markdown("**Пики и запас**")
    silence = bool(peak and peak.get("sample_peak_dbfs") is None)
    metric_row(
        [
            ("Sample Peak · dBFS", number_text(peak, "sample_peak_dbfs", zero_is_silence=silence)),
            ("True Peak · dBTP", number_text(loud, "true_peak_dbtp")),
        ]
    )
    area = scope_label(peak.get("scope", {}))
    st.caption("Пики отсчётов: " + area)
    tp = conclusions.get("peaks.true-peak")
    if tp:
        value = tp.measured_values["true_peak_dbtp"]
        st.text(
            f"Выше 0 dBTP на {value:.3f} dB."
            if value > 0
            else f"Ниже 0 dBTP на {-value:.3f} dB; превышения не обнаружены."
            if value < 0
            else "На 0 dBTP; превышения не обнаружены."
        )
    elif loud.get("true_peak_state") == "negative infinity":
        st.text("Реконструированный пик равен нулевой амплитуде (−∞ dBTP).")
    else:
        st.text("Нет пригодной оценки True Peak.")
    delta = conclusions.get("peaks.intersample-difference")
    if delta:
        st.text(
            f"True Peak выше Sample Peak на {delta.measured_values['difference_db']:.3f} dB в той же области."
        )
    counts = peak.get("full_scale_samples_per_channel")
    if counts is not None:
        st.text(
            f"Отсчётов на цифровом пределе: {sum(counts)}. Историческое clipping этим не устанавливается."
        )
    plateau = conclusions.get("clipping.plateaus")
    if plateau and plateau.measured_values.get("events"):
        st.text(
            f"Возможных постоянных участков около предела: {plateau.measured_values['events']}; причина не установлена."
        )
    ceiling = conclusions.get("reference.peak-ceiling")
    if ceiling:
        st.text(ceiling.statement)
    st.markdown("**Динамические измерения**")
    metric_row(
        [
            ("RMS · dBFS", number_text(peak, "rms_dbfs", zero_is_silence=silence)),
            ("Crest Factor · dB", number_text(peak, "crest_factor_db")),
        ]
    )
    st.caption(area)
    st.text("Crest Factor показывает, насколько пик выше RMS в этой области.")
    if expert:
        plr = conclusions.get("dynamics.plr")
        if plr:
            st.text(f"True Peak − Integrated (PLR): {plr.measured_values['plr_db']:.3f} dB.")
        rows = [
            {
                "Канал": i + 1,
                "Пик, dBFS": v,
                "Положение, s": peak.get("sample_peak_time_seconds", [None] * result.info.channels)[
                    i
                ],
                "RMS, dBFS": peak.get("rms_per_channel_dbfs", [None] * result.info.channels)[i],
            }
            for i, v in enumerate(peak.get("sample_peak_per_channel_dbfs", []))
        ]
        if rows:
            st.dataframe(rows, hide_index=True, alt="Пики, время пиков и RMS отдельных каналов")
        distribution = loud.get("short_term_quantiles", {})
        if distribution.get("p10_lufs") is not None:
            st.text(
                f"Центральные 80% полных 3-секундных окон: {distribution['p10_lufs']:.1f}–{distribution['p90_lufs']:.1f} LUFS."
            )
    if st.toggle("Громкость и пики по времени", key="technical_timeline_visible", value=expert):
        show_timelines(result)
    st.markdown("**Спектр**")
    if context is not None and len(context.samples) >= 256:
        f, p = pcm_spectrum_data(context)
        show_density(f, p, labels=["Средняя мощность каналов"])
        st.caption("Спектр: " + scope_label(result.scope))
    if context is None:
        return
    if st.toggle("Показать Spectrogram", key="spectrum_visible"):
        import matplotlib.pyplot as plt

        from music_project.core.models import AudioError

        try:
            f, t, p = pcm_spectrogram_data(context)
            fig, ax = plt.subplots(figsize=(7.2, 2.6), layout="constrained")
            image = ax.pcolormesh(t, f / 1000, p, shading="auto", vmin=-140, vmax=-20)
            ax.set(xlabel="Время, s", ylabel="Частота, kHz")
            fig.colorbar(image, ax=ax, label="PSD, dB re FS²/Hz")
            st.pyplot(fig, width=720, alt="Спектрограмма измеренного PCM-интервала")
            plt.close(fig)
        except AudioError as exc:
            st.info(str(exc))
    if st.toggle("Прослушать фрагмент", key="preview_visible"):
        if result.info.channels <= 2:
            st.audio(
                context.samples.T,
                sample_rate=result.info.sample_rate,
                alt="Измеренный PCM-фрагмент",
            )
        else:
            st.info("Прослушивание поддерживает до двух каналов; downmix не выполняется.")
