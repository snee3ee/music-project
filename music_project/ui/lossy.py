"""Saved PCM investigation facts in the existing Origin Normal/Expert structure."""

import math

import streamlit as st

LABELS = {
    "Indicators detected": "Обнаружены признаки",
    "No evaluated indicators detected": "Оценённые признаки не обнаружены",
    "Inconclusive": "Неоднозначно",
    "Not evaluated": "Не оценено",
}
ELIGIBILITY = {
    "eligible": "Пригодно",
    "silence": "Нулевой сигнал",
    "low_energy": "Низкий уровень",
    "sparse_band_excitation": "Разреженная опорная полоса",
}


def show_lossy(result, *, expert=False):
    st.markdown("### Предыдущее lossy-кодирование · исследование")
    finding = result.findings.get("lossy_source")
    if not finding:
        st.text("Не оценено в сохранённом результате; повторите анализ для этой проверки.")
        return
    report = finding.measurements
    classification = report.get("classification", "Not evaluated")
    st.text("Результат: " + LABELS[classification])
    if not report.get("performed"):
        if result.info.kind == "PCM" and result.info.channels not in (1, 2):
            st.caption(
                f"Проверка рассчитана на mono/stereo PCM; в этом потоке {result.info.channels} каналов."
            )
        elif result.info.kind == "PCM" and result.info.sample_rate not in {
            32000,
            44100,
            48000,
            88200,
            96000,
            176400,
            192000,
        }:
            st.caption(
                f"Частота {result.info.sample_rate} Hz не входит в проверенные конфигурации этого метода."
            )
        reason = (
            "Проверка рассчитана на lossless mono/stereo PCM; native DSD здесь не преобразуется."
            if result.info.kind != "PCM"
            else "Недостаточно полного FFT-окна длительностью не менее 1 s либо формат/каналы вне применимости."
        )
        st.caption(reason)
    else:
        observed = [
            b
            for b in report.get("candidates", [])
            if any(c["detected"] for c in b["channels"])
            or any(s["detected_windows"] for s in b["stability"])
        ]
        if observed:
            b = max(
                observed, key=lambda b: max(c.get("attenuation_db") or 0 for c in b["channels"])
            )
            drops = [
                c["attenuation_db"]
                for c in b["channels"]
                if c["detected"] and c["attenuation_db"] is not None
            ]
            window_drops = [
                s["maximum_window_drop_db"]
                for s in b["stability"]
                if s.get("maximum_window_drop_db") is not None
            ]
            hits = max((s["detected_windows"] for s in b["stability"]), default=0)
            st.text(
                f"Спектральный спад около {b['candidate_hz'] / 1000:.2f} kHz"
                + (
                    f": максимум {max(window_drops):.1f} dB по окнам"
                    if window_drops
                    else f": {max(drops):.1f} dB в среднем спектре"
                    if drops
                    else ""
                )
                + f"; повторился в {hits} окнах."
            )
            st.caption(
                f"До Nyquist: {b.get('distance_to_nyquist_hz', result.info.sample_rate / 2 - b['candidate_hz']) / 1000:.2f} kHz. Наличие верхнего края полосы само по себе не указывает на lossy-кодек."
            )
            st.caption(
                "Измерено подавление полосы. Фильтрация без lossy-кодирования даёт сходный результат."
            )
        elif report["counts"].get("eligible_windows", 0) >= 2:
            st.text(
                "Оценённых резких спектральных спадов не найдено; lossless-история этим не подтверждается."
            )
        else:
            st.text("Спектр измерен; пригодных окон для проверки устойчивости недостаточно.")
        st.caption(
            f"Проверено {report['scope']['analyzed_seconds']:.2f} s в {report['counts']['seen_windows']} окнах; пригодных {report['counts']['eligible_windows']}, исключённых {report['counts']['discarded_windows']}."
        )
    st.text(
        "Дополнительные признаки кодирования: валидированного определения нет. Исторический кодек неизвестен."
    )
    if expert and st.toggle("Свидетельства lossy-исследования", key="lossy_evidence_visible"):
        _evidence(report)


def _evidence(report):
    section = st.selectbox(
        "Измерения lossy-исследования",
        ["Полосы", "Переходы", "Окна", "Метод и ограничения"],
        key="lossy_evidence_section",
    )
    if section == "Полосы":
        st.caption(
            "Медианы и квантили PSD включают сигнальные и шумовые компоненты; это прокси спектрального фона."
        )
        st.dataframe(
            [
                {
                    "Канал": r["channel"],
                    "От, Hz": r["low_hz"],
                    "До, Hz": r["high_hz"],
                    "Мощность, FS²": r["power_fs2"],
                    "Доля измеренной энергии": r["fraction_of_measured_power"],
                    "Медиана, dB/Hz": 10 * math.log10(r["median_density_fs2_per_hz"])
                    if r["median_density_fs2_per_hz"] > 0
                    else None,
                    "Медиана к 1–8 kHz, dB": r["median_relative_db"],
                    "q10, FS²/Hz": r["q10_density_fs2_per_hz"],
                    "q90, FS²/Hz": r["q90_density_fs2_per_hz"],
                }
                for r in report["bands"]
            ],
            hide_index=True,
            alt="Энергия и спектральные квантили отдельно по каналам",
        )
    elif section == "Переходы":
        rows = []
        for b in report["candidates"]:
            for c, s in zip(b["channels"], b["stability"], strict=True):
                rows.append(
                    {
                        "Частота, Hz": b["candidate_hz"],
                        "До Nyquist, Hz": b.get("distance_to_nyquist_hz"),
                        "Канал": c["channel"],
                        "Спад, dB": c["attenuation_db"],
                        "Наклон, dB/kHz": c["local_slope_db_per_khz"],
                        "Ширина, Hz": c["transition_width_hz"],
                        "Погрешность сетки, Hz": c["transition_uncertainty_hz"],
                        "Энергия выше, FS²": c["above_boundary_power_fs2"],
                        "Признак измерен": c["detected"],
                        "Окон с признаком": s["detected_windows"],
                        "Пригодных окон": s["eligible_windows"],
                        "Устойчив по правилу": s["recurrent"],
                    }
                )
        st.dataframe(
            rows,
            hide_index=True,
            alt="Адаптивные кандидаты и повторяемость при одинаковой частоте по всем окнам",
        )
        st.caption(
            "Спад и повторяемость — наблюдения, не сила доказательства MP3/AAC. Стереоканалы оцениваются раздельно."
        )
    elif section == "Окна":
        st.dataframe(
            [
                {
                    "Окно": r["window"],
                    "Начало, s": r["start_seconds"],
                    "Конец, s": r["end_seconds"],
                    "Канал": c["channel"],
                    "Применимость": ELIGIBILITY[c["eligibility"]],
                    "RMS, dBFS": c["rms_dbfs"],
                    "Заполнение 1–8 kHz": c["reference_occupancy"],
                    "Изменчивость энергии, CV": c["segment_energy_cv"],
                    "Доля сильнейшего FFT-bin": c["dominant_bin_power_fraction"],
                }
                for r in report["windows"]
                for c in r["channels"]
            ],
            hide_index=True,
            alt="Временные участки, причины исключения и измеренные признаки разреженности и изменчивости",
        )
        st.caption(
            "Разреженность и изменчивость не устанавливают инструменты или артефакты кодека. Исключённые короткие окна сохранены в JSON."
        )
    else:
        st.caption(report["method_version"])
        p = report.get("parameters", {})
        st.text(
            f"Welch: Hann, FFT {p.get('nfft', 'не выполнено')}, 50% overlap, без downmix и resampling."
        )
        st.text(
            "Выборка: до 32 окон по 2 s, равномерные индексы полных слотов по известной длительности; неизвестная длительность — первые 32 слота."
        )
        st.text(
            "Поиск 8–24 kHz в доступной полосе. Последние 600 Hz перед Nyquist не дают двухсторонней проверки границы."
        )
        st.text(
            "Наблюдение: контраст ≥18 dB, достаточный уровень/заполнение нижней полосы; устойчивость ≥2 окон и ≥половины пригодных в том же канале."
        )
        st.text(
            "Пороги наблюдений экспериментальные. Контрольная синтетическая выборка содержит lossy и похожие lossless-примеры; универсальная точность не установлена."
        )
        st.text(
            "LUFS, пики, limiting и FLAC MD5 не используются для вывода об истории кодирования."
        )
        st.text(
            "Пре-эхо, спектральные разрывы и шум кодирования не имеют валидированного определения без независимых свидетельств. Исходная аутентичность не установлена."
        )
