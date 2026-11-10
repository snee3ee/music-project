"""Existing Origin/integrity evidence translated into formal scoped conclusions."""

from music_project.core.conclusion_utils import number


def _integrity_conclusions(info, scope, findings, add):
    finding = findings.get("pcm_integrity") if info.kind != "DSD" else findings.get("dsd_integrity")
    if not finding:
        add(
            "integrity.not-performed",
            "integrity",
            "Проверка целостности",
            "Независимая полная проверка целостности не выполнялась; доступные измерения не заменяют её.",
            "Not validated",
            ["analysis.scope"],
            {},
            {},
            scope,
            "integrity.absent-check",
        )
        return
    m = finding.measurements
    area = m.get("scope", scope)
    if m.get("decode_status", finding.status) == "Passed" and m.get("complete_file"):
        text = f"Первый аудиопоток полностью декодирован: {m.get('decoded_seconds', m.get('successfully_decoded_seconds', 0)):.3f} s."
        stype = "Verified fact"
    elif finding.status == "Failed":
        text = "Проверка не пройдена; исходная диагностика сохранена."
        stype = "Verified fact"
    elif finding.status == "Unsupported":
        text = "Запрошенная проверка не поддерживается в текущей конфигурации."
        stype = "Unsupported"
    else:
        text = "Проверена только указанная часть потока; полный проход не подтверждён."
        stype = "Inconclusive"
    add(
        "integrity.decode",
        "integrity",
        "Результат проверки потока",
        text,
        stype,
        ["pcm_integrity" if info.kind != "DSD" else "dsd_integrity"],
        {"status": finding.status},
        {},
        area,
        "integrity.completed-versus-partial",
        limitations=[
            "Декодирование не аутентифицирует издание и не является проверкой всех полей контейнера."
        ],
    )
    if "flac_md5" in m:
        f = m["flac_md5"]
        text = (
            "MD5 декодированного PCM совпал с STREAMINFO FLAC."
            if f["status"] == "Verified"
            else "MD5 декодированного PCM не совпал с STREAMINFO FLAC."
            if f["status"] == "Failed"
            else f"Проверка FLAC MD5: {f['status']}. {f['reason']}"
        )
        if f["status"] != "Not applicable":
            add(
                "integrity.flac-md5",
                "integrity",
                "Встроенный контроль FLAC",
                text,
                "Verified fact" if f["status"] in {"Verified", "Failed"} else "Inconclusive",
                ["pcm_integrity.flac_md5"],
                f,
                {},
                area,
                "integrity.flac-native-md5",
                limitations=[
                    "Сравнивается встроенный digest; независимость происхождения или архивной копии не установлена."
                ],
            )


def _origin_conclusions(findings, add):
    finding = findings.get("origin_investigation")
    if not finding or not finding.measurements:
        return
    report = finding.measurements
    rows = report.get("boundaries", [])
    usable = [b for b in rows if b.get("status") == "Measured" and b.get("converted_chain_usable")]
    evidence = [b for b in usable if b.get("historical_compatibility_evidence")]
    original_scope = report.get("scope", {})
    converted = original_scope.get("converted", {})
    ranges = [
        {
            "start_seconds": r["start_seconds"],
            "end_seconds": r["start_seconds"] + r["decoded_seconds"],
        }
        for r in converted.get("ranges", [])
    ]
    area = {
        "start_seconds": min(
            (r["start_seconds"] for r in ranges), default=converted.get("start_seconds", 0)
        ),
        "end_seconds": max(
            (r["end_seconds"] for r in ranges), default=converted.get("decoded_seconds", 0)
        ),
        "analyzed_seconds": converted.get("decoded_seconds", 0),
        "complete_file": converted.get("complete_file", False),
        "ranges": ranges,
        "domain": "Converted PCM and separately sampled native DSD"
        if report.get("native", {}).get("windows")
        else "PCM",
        "native_ranges": [
            {
                "start_seconds": w["start_seconds"],
                "end_seconds": w["start_seconds"] + w["duration_seconds"],
            }
            for w in report.get("native", {}).get("windows", [])
        ],
        "processing": "See Origin measurement-chain profile; native windows are separate from converted coverage",
    }
    if not evidence:
        text = (
            f"Оценено {len(usable)} применимых границ; ни одна не дала устойчивой совместимости по текущему правилу."
            if usable
            else "В доступной полосе нет применимых границ для текущего правила; отсутствие признака не оценивалось."
        )
        add(
            "origin.boundary-summary",
            "origin",
            "Проверенные спектральные границы",
            text,
            "Rule-based technical conclusion" if usable else "Not applicable",
            ["origin_investigation.boundaries"],
            {"usable_boundaries": len(usable), "matched_boundaries": len(evidence)},
            {"usable_boundaries": "boundaries", "matched_boundaries": "boundaries"},
            area,
            "origin.actual-applicable-count",
            limitations=[
                "Отсутствие обнаружения не устанавливает native Hi-Res или исторический источник."
            ],
        )
    for b in usable:
        for c in b.get("channel_stability", []):
            n = c["eligible_cells"]
            d = c["detected_cells"]
            percentage = 100 * d / n if n else None
            measured = next((v for v in b["channels"] if v["channel"] == c["channel"]), {})
            drop = measured.get("attenuation_db")
            text = f"Граница {b['candidate_hz'] / 1000:g} kHz, канал {c['channel']}: правило выполнено в {d}/{n} пригодных сохранённых ячеек"
            if percentage is not None:
                text += f" ({percentage:.1f}%)."
            else:
                text += "; доля не вычисляется."
            if number(drop):
                text += f" Спад глобальной PSD: {drop:.3f} dB."
            add(
                f"origin.boundary-{b['candidate_hz']}-ch{c['channel']}",
                "origin",
                "Измерение границы",
                text,
                "Rule-based technical conclusion",
                [f"origin_investigation.boundaries.{rows.index(b)}"],
                {
                    "candidate_hz": b["candidate_hz"],
                    "detected_cells": d,
                    "eligible_cells": n,
                    "observed_percent": percentage,
                    "attenuation_db": drop,
                },
                {
                    "candidate_hz": "Hz",
                    "detected_cells": "cells",
                    "eligible_cells": "cells",
                    "observed_percent": "% of eligible retained cells",
                    "attenuation_db": "dB",
                },
                area,
                "origin.retained-window-fraction",
                limitations=[
                    "Эмпирическая доля сохранённых ячеек, не вероятность происхождения; при Full действует прогрессивное прореживание. Аналоговые и mastering-фильтры — альтернативы."
                ],
            )
    for index, h in enumerate(report.get("hypotheses", [])):
        if h["status"] == "Compatible but not distinguishable":
            add(
                "origin.hypothesis." + h["code"],
                "origin",
                h["title"],
                h["title"]
                + ": совместимо с измеренными признаками; альтернативные причины не различены.",
                "Evidence-supported hypothesis",
                [f"origin_investigation.hypotheses.{index}"],
                {
                    "supporting_evidence": h["supporting_evidence"],
                    "counterevidence": h["contradicting_evidence"],
                },
                {},
                area,
                "origin.existing-compatibility-hypothesis",
                limitations=h["assumptions"] + h["alternatives"],
                validation="Existing tested Origin compatibility rule; historical identity not verified",
            )
    noise = report.get("noise", {})
    for index, c in enumerate(noise.get("channels", [])):
        change = c.get("regime_change")
        if not change:
            continue
        stability = noise.get("temporal_summary", [])
        stability = stability[index] if len(stability) > index else {}
        statement = f"Канал {c['channel']}: переход спектрального фона {change['low_hz'] / 1000:.2f}–{change['high_hz'] / 1000:.2f} kHz; наклоны {change['slopes_db_per_decade'][0]:.2f}/{change['slopes_db_per_decade'][1]:.2f} dB/декаду."
        if stability.get("native_transition_range_overlaps"):
            statement += " Интервал перекрывается с переходом независимого native DSD спектра выбранных окон."
        add(
            f"origin.noise-regime-ch{c['channel']}",
            "origin",
            "Измеренный спектральный режим",
            statement,
            "Rule-based technical conclusion",
            [f"origin_investigation.noise.channels.{index}"],
            change | stability,
            {"low_hz": "Hz", "high_hz": "Hz", "slopes_db_per_decade": "dB/decade"},
            area,
            "origin.existing-noise-regime",
            limitations=[
                "Спектральный фон включает шум/тоны/фильтрацию. Историческая причина и прежний DSD-rate не идентифицированы."
            ],
            validation="Exploratory shape fit with controlled counterexamples; no historical-rate classifier",
        )
