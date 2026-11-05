"""Evidence-first Origin Investigator. Historical compatibility is not identification."""

import numpy as np
from scipy.signal import welch

from music_project.core.config import Settings
from music_project.core.dsd_container import inspect_dsd
from music_project.core.dsd_native import native_spectra
from music_project.core.models import AudioError, AudioInfo, Finding
from music_project.core.origin_calibration import (
    boundary_chain_valid,
    calibrate_response,
    controlled_bandwidth,
)
from music_project.core.origin_features import boundary_features, noise_features
from music_project.core.origin_models import ORIGIN_VERSION, Hypothesis, OriginReport
from music_project.core.origin_temporal import OriginCollector


def investigate_origin(
    info: AudioInfo,
    findings: dict,
    scope: dict,
    temporal: dict,
    settings: Settings,
    versions: dict,
    *,
    cancelled=None,
    measured_profile=None,
) -> OriginReport:
    converted = findings.get("dsd_audible")
    spectrum = converted.measurements.get("spectrum") if converted else None
    native = {"status": "Not applicable", "windows": []}
    if info.kind == "DSD":
        try:
            profile = (
                measured_profile
                if measured_profile is not None
                else calibrate_response(
                    info.sample_rate,
                    settings,
                    versions.get("ffmpeg", "Unknown"),
                    cancelled=cancelled,
                )
            )
        except (AudioError, OSError, ValueError) as exc:
            profile = {"status": "Unsupported", "reason": str(exc)}
        try:
            native = native_spectra(info, inspect_dsd(info), cancelled=cancelled)
        except (AudioError, OSError, ValueError) as exc:
            native = {"status": "Unsupported", "reason": str(exc), "windows": []}
    else:
        profile = {
            "status": "Not applicable",
            "reason": "Native-rate decoded PCM; no DSD conversion",
        }
        spectrum = scope.get("origin_pcm_spectrum")
    boundaries = []
    noise = {"status": "Unknown"}
    if spectrum and spectrum.get("status") == "Measured":
        boundaries = boundary_features(spectrum["frequencies_hz"], spectrum["density_fs2_per_hz"])
        noise = noise_features(
            spectrum["frequencies_hz"],
            spectrum["density_fs2_per_hz"],
            controlled_bandwidth(profile) if info.kind == "DSD" else 160000,
        )
        noise["measurement_origin"] = "Converted PCM" if info.kind == "DSD" else "Decoded PCM"
    native_rows = {}
    if native.get("windows"):
        windows = native["windows"]
        weights = np.array([w["segments"] for w in windows])
        density = np.average([w["density_fs2_per_hz"] for w in windows], axis=0, weights=weights)
        native_rows = {
            b["candidate_hz"]: b for b in boundary_features(windows[0]["frequencies_hz"], density)
        }
        native["noise"] = noise_features(windows[0]["frequencies_hz"], density)
        native["aggregate_frequencies_hz"] = windows[0]["frequencies_hz"]
        native["aggregate_density_fs2_per_hz"] = density.tolist()
        for window in windows:
            window["boundaries"] = boundary_features(
                window["frequencies_hz"], window["density_fs2_per_hz"]
            )
    if not boundaries and native_rows:
        boundaries = [dict(b, channels=[]) for b in native_rows.values()]
    cells = temporal.get("cells", [])
    hypotheses = []
    for boundary in boundaries:
        candidate = boundary["candidate_hz"]
        chain_valid = info.kind != "DSD" or boundary_chain_valid(profile, candidate)
        boundary["converted_chain_usable"] = chain_valid
        native_b = native_rows.get(candidate)
        boundary["native_channels"] = native_b["channels"] if native_b else []
        native_detected = []
        for index, window in enumerate(native.get("windows", []), 1):
            row = next(b for b in window["boundaries"] if b["candidate_hz"] == candidate)
            if any(c["detected"] for c in row["channels"]):
                native_detected.append(index)
        tested = []
        detected = []
        for index, cell in enumerate(cells, 1):
            row = next(b for b in cell["boundaries"] if b["candidate_hz"] == candidate)
            if any(c["eligible"] for c in row["channels"]):
                tested.append(index)
            if any(c["detected"] for c in row["channels"]):
                detected.append(index)
        boundary["temporal"] = {
            "eligible_cells": len(tested),
            "detected_cells": len(detected),
            "tested_cell_ids": tested,
            "detected_cell_ids": detected,
            "native_detected_window_ids": native_detected,
        }
        per_channel = []
        for channel in range(info.channels):
            converted_rows = [
                b["channels"][channel]
                for cell in cells
                for b in cell["boundaries"]
                if b["candidate_hz"] == candidate and len(b["channels"]) > channel
            ]
            native_channel_rows = [
                b["channels"][channel]
                for w in native.get("windows", [])
                for b in w["boundaries"]
                if b["candidate_hz"] == candidate and len(b["channels"]) > channel
            ]
            eligible_count = sum(c["eligible"] for c in converted_rows)
            detected_count = sum(c["detected"] for c in converted_rows)
            native_count = sum(c["detected"] for c in native_channel_rows)
            per_channel.append(
                {
                    "channel": channel + 1,
                    "eligible_cells": eligible_count,
                    "detected_cells": detected_count,
                    "native_detected_windows": native_count,
                    "stable_converted": chain_valid
                    and detected_count >= 2
                    and detected_count >= eligible_count / 2,
                    "stable_native": native_count >= 2,
                }
            )
        boundary["channel_stability"] = per_channel
        boundary["all_channels_detected_in_global_spectrum"] = bool(boundary["channels"]) and all(
            c["detected"] for c in boundary["channels"]
        )
        stable_converted = any(c["stable_converted"] for c in per_channel)
        stable_native = any(c["stable_native"] for c in per_channel)
        compatible = any(
            c["stable_converted"] and (c["stable_native"] if info.kind == "DSD" else True)
            for c in per_channel
        )
        boundary["stable_native_boundary"] = stable_native
        boundary["stable_converted_boundary"] = stable_converted
        boundary["historical_compatibility_evidence"] = compatible
        boundary["location_in_chain"] = (
            "Present in sampled native bitstream"
            if stable_native
            else "PCM conversion bandwidth is limited in control tests"
            if not chain_valid
            else "No stable native/converted agreement established"
        )
        support = []
        contradiction = []
        if detected:
            support.append(
                f"Спад ≥18 dB: {len(detected)} из {len(tested)} пригодных временных ячеек."
            )
        if native_detected:
            support.append(f"Прямой DSD: признак присутствует в окнах {native_detected}.")
        if tested and len(detected) < len(tested):
            contradiction.append(
                f"В {len(tested) - len(detected)} пригодных ячейках порог спада не выполнен; постоянная граница не описывает всю выборку."
            )
        status = (
            "Compatible but not distinguishable"
            if compatible
            else "Inconclusive"
            if tested or native_detected
            else "Not testable with available data"
        )
        hypotheses.append(
            Hypothesis(
                f"pcm-bandwidth-{candidate * 2}",
                f"Предыдущее ограничение полосы, совместимое с PCM {candidate * 2 / 1000:g} kHz",
                status,
                support,
                contradiction,
                [boundary["id"]],
                [
                    "Граница должна сохраняться в конечном сигнале и не быть скрыта добавленным шумом/обработкой.",
                    "Контрпризнак относится к простой модели постоянной видимой границы, не исключает всю PCM-историю.",
                ],
                [
                    "Аналоговое ограничение полосы",
                    "Фильтрация при мастеринге",
                    "Текущая модуляция/шумоформирование",
                    "Преобразование анализатора",
                ],
                "Native DSD + calibrated converted PCM"
                if info.kind == "DSD"
                else "Measured PCM scope",
            )
        )
    native_noise = native.get("noise", {})
    if noise.get("status") == "Measured":
        noise["native_comparison"] = native_noise
        valid_cells = [c for c in cells if c["noise"].get("status") == "Measured"]
        transitions = [
            {
                "cell": i + 1,
                "start_seconds": c["start_seconds"],
                "end_seconds": c["end_seconds"],
                "regime_changes": [r.get("regime_change") for r in c["noise"]["channels"]],
            }
            for i, c in enumerate(valid_cells)
        ]
        noise["temporal_regimes"] = transitions
        noise["temporal_summary"] = []
        for channel, measured in enumerate(noise["channels"]):
            changes = [c["noise"]["channels"][channel].get("regime_change") for c in valid_cells]
            changes = [c for c in changes if c]
            current = measured.get("regime_change")
            independent = native_noise.get("channels", [])
            independent = (
                independent[channel].get("regime_change") if len(independent) > channel else None
            )
            noise["temporal_summary"].append(
                {
                    "channel": channel + 1,
                    "retained_tested_cells": len(valid_cells),
                    "regime_change_cells": len(changes),
                    "median_transition_range_hz": [
                        float(np.median([c[k] for c in changes])) for k in ("low_hz", "high_hz")
                    ]
                    if changes
                    else None,
                    "native_transition_range_overlaps": bool(
                        current
                        and independent
                        and max(current["low_hz"], independent["low_hz"])
                        <= min(current["high_hz"], independent["high_hz"])
                    )
                    if info.kind == "DSD"
                    else None,
                }
            )
        noise["historical_rate_evaluation"] = {
            "status": "Not identifiable with this method",
            "reason": "Controlled PCM-to-DSD and filtered controls also produce regime transitions; no unique historical DSD-rate mapping is validated.",
        }
        if len(valid_cells) >= 4:
            audible = np.array([c["noise"]["audible_power_fs2"] for c in valid_cells])
            ultra = np.array([c["noise"]["ultrasonic_power_fs2"] for c in valid_cells])
            noise["audible_ultrasonic_power_correlations"] = [
                float(np.corrcoef(audible[:, i], ultra[:, i])[0, 1])
                if np.std(audible[:, i]) > 0 and np.std(ultra[:, i]) > 0
                else None
                for i in range(info.channels)
            ]
    report = OriginReport(
        "Measured" if boundaries or native.get("windows") else "Unknown",
        {
            "container": info.container,
            "codec": info.codec,
            "kind": info.kind,
            "rate_hz": info.sample_rate,
            "channels": info.channels,
        },
        {
            "converted": scope,
            "temporal": temporal,
            "native": "sampled windows only; not full native-bitstream coverage",
        },
        profile,
        boundaries,
        noise,
        native,
        hypotheses,
    )
    complete = scope.get("complete_file", False)
    report.discoveries.append(
        f"{'Полное декодирование' if complete else 'Проверенные фрагменты'}: {scope.get('decoded_seconds', 0):.3f} s."
    )
    interesting = [b for b in boundaries if b["historical_compatibility_evidence"]]
    for b in interesting[:2]:
        drops = [c["attenuation_db"] for c in b["channels"] if c.get("attenuation_db") is not None]
        report.discoveries.append(
            f"Граница около {b['candidate_hz'] / 1000:g} kHz: "
            + (f"спад {float(np.median(drops)):.1f} dB, " if drops else "")
            + f"в {b['temporal']['detected_cells']} временных ячейках; совместима с ограничением полосы."
        )
    if not interesting:
        usable = sum(b["status"] == "Measured" and b["converted_chain_usable"] for b in boundaries)
        report.discoveries.append(
            f"Проверено {usable} частотных границ в доступной полосе; устойчивого спада по правилам не найдено."
        )
        report.discoveries.append(
            "Порог поиска: спад ≥18 dB при достаточном уровне сигнала. Слабые участки не дают отрицательного заключения."
        )
    regimes = [c["regime_change"] for c in noise.get("channels", []) if c.get("regime_change")]
    for regime in regimes[:1]:
        report.discoveries.append(
            f"Переход ультразвукового фона: {regime['low_hz'] / 1000:.1f}–{regime['high_hz'] / 1000:.1f} kHz."
        )
    if native.get("windows"):
        report.discoveries.append(
            f"Прямой анализ DSD: {len(native['windows'])} коротких окна, суммарно "
            f"{sum(w['duration_seconds'] for w in native['windows']):.3f} s."
        )
    report.next_steps = (
        ["Запустить Full Analysis для полной проверки потока."] if not complete else []
    ) + [
        "Сравнить выбранный референс в этом отчёте.",
        "Проверить документированный источник издания (внешнее свидетельство).",
    ]
    report.limitations = [
        "Сохранность признаков зависит от обработки; спектральные признаки не устанавливают историю записи.",
        "Изменения медианной PSD — исследовательские спектральные режимы, не идентификаторы DSD64/128/256/DXD.",
        "Калибровка измеряет отдельные контрольные частоты; непрерывная АЧХ и профессиональные модуляторы полностью не сертифицированы.",
    ]
    return report


def origin_finding(report: OriginReport) -> Finding:
    return Finding(
        report.status,
        "Выполнено исследование полосы, временной устойчивости и спектральных режимов.",
        report.to_dict(),
        method="Native/PCM PSD, controlled conversion response, explicit compatibility rules",
        limitations=report.limitations,
        method_version=ORIGIN_VERSION,
    )


def investigate_pcm_context(context, settings: Settings, versions: dict) -> Finding:
    """Use the existing bounded decoded PCM prefix; no additional audio decode."""
    info = context.info
    nfft = min(16384, len(context.samples))
    if info.channels not in (1, 2) or nfft < 256:
        return Finding(
            "Unsupported",
            "Недостаточно mono/stereo PCM для исследования Origin.",
            method_version=ORIGIN_VERSION,
        )
    collector = OriginCollector(info.sample_rate, info.channels, nfft)
    hop = nfft // 2
    window = np.hanning(nfft + 1)[:-1]
    total = np.zeros((nfft // 2 + 1, info.channels))
    count = 0
    collector.start_window(0)
    for first in range(0, len(context.samples) - nfft + 1, hop):
        _, density = welch(
            context.samples[first : first + nfft],
            info.sample_rate,
            window=window,
            nperseg=nfft,
            noverlap=0,
            detrend=False,
            axis=0,
            scaling="density",
        )
        collector.consume(density)
        total += density
        count += 1
    collector.end_window()
    evidence_scope = context.scope | {
        "origin_pcm_spectrum": {
            "status": "Measured",
            "frequencies_hz": collector.f.tolist(),
            "density_fs2_per_hz": (total / count).tolist(),
        }
    }
    temporal = collector.result()
    temporal["new_fft_computations"] = count
    return origin_finding(
        investigate_origin(info, {}, evidence_scope, temporal, settings, versions)
    )
