"""Gain-only reference planning without modifying measurements or source audio."""

from music_project.core.conclusion_utils import measurement_inputs, number, same_scope


def reference_rules(info, scope, findings, ref, add) -> None:
    lm, _pm, ls, _ps = measurement_inputs(findings)
    tp_scope = lm.get("true_peak_scope", ls)
    ls = lm.get("integrated_scope", ls)
    integrated = lm.get("integrated_lufs")
    tp = lm.get("true_peak_dbtp")
    if (
        ref.loudness_lufs is not None
        and number(integrated)
        and isinstance(ls, dict)
        and ls.get("frames")
    ):
        difference = integrated - ref.loudness_lufs
        gain = -difference
        values = {"difference_lu": difference, "target_gain_db": gain}
        message = f"Относительно выбранного {ref.loudness_lufs:.2f} LUFS: {'выше' if difference >= 0 else 'ниже'} на {abs(difference):.3f} LU. Расчёт линейного gain: {gain:+.3f} dB."
        if number(tp) and same_scope(ls, tp_scope):
            values["predicted_true_peak_dbtp"] = tp + gain
            message += f" Расчётный True Peak после такого gain: {tp + gain:.3f} dBTP."
            if ref.peak_ceiling_dbtp is not None:
                maximum_gain = ref.peak_ceiling_dbtp - tp
                compatible = gain <= maximum_gain
                chosen = min(gain, maximum_gain)
                values.update(
                    maximum_gain_from_ceiling_db=maximum_gain,
                    gain_only_target_achievable=compatible,
                    ceiling_constrained_gain_db=chosen,
                    resulting_loudness_lufs=integrated + chosen,
                )
                if not compatible:
                    message += f" Одним gain цель LUFS и потолок одновременно не достигаются. Gain по потолку: {chosen:+.3f} dB; громкость {integrated + chosen:.3f} LUFS."
                else:
                    message += " По текущей оценке этот gain также соблюдает выбранный потолок."
        elif number(tp):
            message += " Прогноз True Peak и проверка потолка не выполнены: области LUFS и пика различаются."
        add(
            "reference.gain-plan",
            "reference",
            "Расчёт без изменения файла",
            message,
            "Mathematical derivation",
            ["loudness.integrated_lufs", "loudness.true_peak_dbtp"],
            values,
            {
                k: "LU"
                if k == "difference_lu"
                else "LUFS"
                if k.endswith("lufs")
                else "dBTP"
                if k.endswith("dbtp")
                else "boolean"
                if k.endswith("achievable")
                else "dB"
                for k in values
            },
            ls,
            "reference.target-minus-measured-and-ceiling",
            reference_values={
                k: v
                for k, v in {
                    "loudness_lufs": ref.loudness_lufs,
                    "peak_ceiling_dbtp": ref.peak_ceiling_dbtp,
                }.items()
                if v is not None
            },
            limitations=[
                "Только математический линейный gain; файл не изменяется. Не моделируются limiter, кодирование или алгоритм конкретного сервиса.",
                "Прогноз LUFS предполагает неизменный набор gating-блоков. При изменении абсолютного gating требуется повторное измерение результата.",
            ],
        )
