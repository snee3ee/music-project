"""Peak/headroom and clipping observations; historical causes are separate."""

from music_project.core.conclusion_utils import measurement_inputs, number, same_scope, scope_text


def peak_rules(info, scope, findings, ref, add) -> None:
    lm, pm, ls, ps = measurement_inputs(findings)
    integrated_scope = lm.get("integrated_scope", ls)
    ls = lm.get("true_peak_scope", ls)
    area = scope_text(ls)
    peak_area = scope_text(ps)
    integrated = lm.get("integrated_lufs")
    tp = lm.get("true_peak_dbtp")
    sp = pm.get("sample_peak_dbfs")
    if number(tp) and isinstance(ls, dict) and ls.get("frames"):
        margin = -tp
        phrase = (
            f"выше 0 dBTP на {tp:.3f} dB"
            if tp > 0
            else f"ниже 0 dBTP на {margin:.3f} dB"
            if tp < 0
            else "на уровне 0 dBTP"
        )
        add(
            "peaks.true-peak",
            "peaks",
            "Реконструированный пик",
            f"Оценка True Peak: {tp:.3f} dBTP, {phrase} ({area}).",
            "Measured fact",
            ["loudness.true_peak_dbtp"],
            {"true_peak_dbtp": tp, "margin_to_zero_db": margin},
            {"true_peak_dbtp": "dBTP", "margin_to_zero_db": "dB"},
            ls,
            "peaks.zero-margin",
            limitations=[
                "Оценка ограничена FIR и частотой дискретизации. Не устанавливает исторический clipping или безопасность любой цепочки воспроизведения."
            ],
            validation="Reconstruction estimator; selected ITU/EBU controls, not blanket standards certification",
            severity="above-zero reconstructed estimate" if tp > 0 else None,
        )
        if ref.peak_ceiling_dbtp is not None:
            delta = ref.peak_ceiling_dbtp - tp
            add(
                "reference.peak-ceiling",
                "reference",
                "Выбранный потолок True Peak",
                f"Относительно выбранного потолка {ref.peak_ceiling_dbtp:.2f} dBTP: {'запас' if delta >= 0 else 'превышение'} {abs(delta):.3f} dB по текущей оценке.",
                "Mathematical derivation",
                ["loudness.true_peak_dbtp"],
                {"margin_db": delta},
                {"margin_db": "dB"},
                ls,
                "reference.ceiling-minus-estimate",
                reference_values={"peak_ceiling_dbtp": ref.peak_ceiling_dbtp},
            )
    elif lm.get("true_peak_state") == "negative infinity":
        add(
            "peaks.true-peak-zero",
            "peaks",
            "Нулевой реконструированный пик",
            "В измеренной области реконструированный пик равен нулю (−∞ dBTP); конечный запас в dB не вычисляется.",
            "Measured fact",
            ["loudness.true_peak_state"],
            {"peak_linear": 0},
            {"peak_linear": "FS"},
            ls,
            "peaks.zero-state",
        )
    if number(sp):
        add(
            "peaks.sample",
            "peaks",
            "Пик отсчётов",
            f"Sample Peak: {sp:.3f} dBFS ({peak_area}).",
            "Measured fact",
            ["full_peaks.sample_peak_dbfs"],
            {"sample_peak_dbfs": sp},
            {"sample_peak_dbfs": "dBFS"},
            ps,
            "peaks.sample-maximum",
        )
    if number(tp) and number(sp):
        if same_scope(ls, ps):
            difference = tp - sp
            add(
                "peaks.intersample-difference",
                "peaks",
                "True Peak и Sample Peak",
                f"Оценка True Peak численно выше Sample Peak на {difference:.3f} dB в той же области.",
                "Mathematical derivation",
                ["loudness.true_peak_dbtp", "full_peaks.sample_peak_dbfs"],
                {
                    "difference_db": difference,
                    "above_zero_intersample_db": tp if tp > 0 and sp <= 0 else None,
                },
                {"difference_db": "dB", "above_zero_intersample_db": "dB"},
                ls,
                "peaks.matched-tp-minus-sp",
            )
        else:
            add(
                "peaks.scope-mismatch",
                "peaks",
                "Области пиков различаются",
                "Разность True Peak и Sample Peak не вычислена: области измерений различаются или не установлены.",
                "Not applicable",
                ["loudness.scope", "full_peaks.scope"],
                {},
                {},
                {"true_peak": ls, "sample_peak": ps},
                "scope.same-signal-required",
            )
    counts = pm.get("full_scale_samples_per_channel")
    if counts is not None:
        total = sum(counts)
        add(
            "peaks.rails",
            "clipping",
            "Отсчёты на цифровом пределе",
            f"Отсчётов, достигших цифрового предела: {total}; по каналам {counts} ({peak_area}).",
            "Measured fact",
            ["full_peaks.full_scale_samples_per_channel"],
            {
                "count": total,
                "per_channel": counts,
                "positive_rail": pm.get("positive_rail"),
                "negative_rail": pm.get("negative_rail"),
            },
            {
                "count": "samples",
                "per_channel": "samples",
                "positive_rail": "FS",
                "negative_rail": "FS",
            },
            ps,
            "peaks.exact-signed-rails",
            limitations=[
                "Нулевое число не исключает ранее выполненное ограничение. Достижение предела не доказывает историческую причину."
            ],
            severity="digital rail samples observed" if total else None,
        )
    flats = pm.get("possible_flat_top_runs", [])
    if flats:
        count = sum(c["count"] for c in flats)
        add(
            "clipping.plateaus",
            "clipping",
            "Постоянные участки около предела",
            f"Найдено {count} постоянных участков из ≥3 одинаковых отсчётов при |sample|≥{pm['near_ceiling_dbfs']:g} dBFS ({peak_area})."
            + (
                " Признак совместим с ограничением, но не уникален для него."
                if count
                else " Пороговый признак не обнаружен."
            ),
            "Rule-based technical conclusion",
            ["full_peaks.possible_flat_top_runs"],
            {"events": count, "threshold_dbfs": pm["near_ceiling_dbfs"]},
            {"events": "events", "threshold_dbfs": "dBFS"},
            ps,
            "clipping.exact-plateau-three",
            limitations=[
                "Прямоугольные/естественно постоянные формы, DC и намеренная обработка также дают такой признак. Исторический clipping не подтверждён."
            ],
        )
    for field, title, unit in [
        ("rms_dbfs", "Среднеквадратичный уровень", "dBFS"),
        ("crest_factor_db", "Crest Factor", "dB"),
    ]:
        value = pm.get(field)
        if number(value):
            add(
                "dynamics." + field,
                "dynamics",
                title,
                f"{title}: {value:.3f} {unit} ({peak_area}).",
                "Measured fact" if field == "rms_dbfs" else "Mathematical derivation",
                ["full_peaks." + field],
                {field: value},
                {field: unit},
                ps,
                "dynamics.same-interval-peak-rms",
                limitations=[
                    "RMS — уровень сигнала, не воспринимаемая громкость. Crest — отношение пика к RMS той же области; не качество мастеринга."
                ],
            )
    if number(tp) and number(integrated):
        if same_scope(ls, integrated_scope):
            add(
                "dynamics.plr",
                "dynamics",
                "Peak-to-loudness ratio",
                f"PLR (True Peak − Integrated): {tp - integrated:.3f} dB, одна область измерения.",
                "Mathematical derivation",
                ["loudness.true_peak_dbtp", "loudness.integrated_lufs"],
                {"plr_db": tp - integrated},
                {"plr_db": "dB"},
                ls,
                "dynamics.matched-tp-minus-loudness",
            )
        else:
            add(
                "dynamics.scope-mismatch",
                "dynamics",
                "Области динамических измерений различаются",
                "PLR с пиковыми измерениями не объединён: не установлена общая область.",
                "Not applicable",
                ["loudness.scope"],
                {},
                {},
                {"integrated": integrated_scope, "true_peak": ls},
                "scope.dynamic-ratios-require-matched-coverage",
            )
