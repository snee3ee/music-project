"""Scoped programme loudness and distribution rules."""

from music_project.core.conclusion_utils import measurement_inputs, number, scope_text


def loudness_rules(info, scope, findings, ref, add) -> None:
    lm, _pm, ls, _ps = measurement_inputs(findings)
    area = scope_text(ls)
    integrated = lm.get("integrated_lufs")
    if number(integrated) and isinstance(ls, dict) and ls.get("frames"):
        add(
            "loudness.integrated",
            "loudness",
            "Интегральная громкость",
            f"Измерено {integrated:.2f} LUFS: {area}.",
            "Measured fact",
            ["loudness.integrated_lufs"],
            {"integrated_lufs": integrated},
            {"integrated_lufs": "LUFS"},
            ls,
            "loudness.valid-integrated",
            limitations=[
                "LUFS характеризует сигнал с частотным взвешиванием и gating; это не положение регулятора и не акустическая громкость."
            ],
        )
    elif info.kind != "DSD":
        add(
            "loudness.unavailable",
            "loudness",
            "Интегральная громкость не определена",
            "Нет пригодного измерения Integrated LUFS в установленной области; тишина, короткий вход или ошибка измерения не заменяются числом.",
            "Inconclusive",
            ["loudness"],
            {},
            {},
            ls,
            "loudness.invalid-or-absent",
        )
    lra = lm.get("lra_lu")
    if number(lra):
        add(
            "dynamics.lra",
            "dynamics",
            "Изменение громкости",
            f"Loudness Range: {lra:.2f} LU ({area}); разброс кратковременной громкости по методу LRA.",
            "Measured fact",
            ["loudness.lra_lu"],
            {"lra_lu": lra},
            {"lra_lu": "LU"},
            ls,
            "loudness.lra",
            limitations=[
                "LRA не является полной оценкой динамического диапазона и не определяет качество или тип компрессии."
            ],
        )
    quantiles = lm.get("short_term_quantiles", {})
    if number(quantiles.get("p10_lufs")) and number(quantiles.get("p90_lufs")):
        low, high = quantiles["p10_lufs"], quantiles["p90_lufs"]
        add(
            "dynamics.short-term",
            "dynamics",
            "Распределение кратковременной громкости",
            f"Центральные 80% пригодных 3-секундных измерений: {low:.1f}–{high:.1f} LUFS; разброс {high - low:.1f} LU ({area}).",
            "Mathematical derivation",
            ["loudness.short_term_distribution"],
            quantiles | {"central_80_range_lu": high - low},
            {
                "p10_lufs": "LUFS",
                "p50_lufs": "LUFS",
                "p90_lufs": "LUFS",
                "central_80_range_lu": "LU",
            },
            ls,
            "loudness.ungated-percentiles",
            limitations=[
                "Полные конечные 3s окна, без LRA gating; гистограмма 0.1 LU. Это эмпирическая доля окон, не вероятность происхождения."
            ],
        )
    for key, title in [
        ("maximum_momentary", "Максимальная моментальная громкость"),
        ("maximum_short_term", "Максимальная кратковременная громкость"),
    ]:
        value = lm.get(key)
        if value and number(value.get("lufs")):
            add(
                "loudness." + key,
                "loudness",
                title,
                f"{title}: {value['lufs']:.2f} LUFS в окне {value['start_seconds']:.3f}–{value['end_seconds']:.3f} s.",
                "Measured fact",
                ["loudness." + key],
                value,
                {"lufs": "LUFS", "start_seconds": "s", "end_seconds": "s"},
                ls,
                "loudness.complete-window-maximum",
            )
