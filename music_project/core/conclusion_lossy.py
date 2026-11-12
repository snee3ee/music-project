"""No integrity, loudness or upsampling value is an input to encoding-history rules."""


def lossy_conclusions(findings, add):
    finding = findings.get("lossy_source")
    if not finding:
        return
    report = finding.measurements
    classification = report.get("classification", "Not evaluated")
    label = {
        "Indicators detected": "Обнаружены признаки",
        "No evaluated indicators detected": "Оценённые признаки не обнаружены",
        "Inconclusive": "Неоднозначно",
        "Not evaluated": "Не оценено",
    }[classification]
    add(
        "origin.lossy-investigation",
        "origin",
        "Предыдущее lossy-кодирование",
        label
        + ". Исторический кодек неизвестен; целостность FLAC не устанавливает историю источника.",
        "Not applicable"
        if classification == "Not evaluated"
        else "Inconclusive"
        if classification == "Inconclusive"
        else "Rule-based technical conclusion",
        ["lossy_source.classification", "lossy_source.counts"],
        {"classification": classification, **report.get("counts", {})},
        {},
        report.get("scope", {}),
        "origin.lossy-measured-observations-with-abstention",
        limitations=report.get("limitations", []),
        validation="Synthetic controls only; bandwidth observations do not uniquely identify perceptual coding",
    )
