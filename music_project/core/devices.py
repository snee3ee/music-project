from dataclasses import dataclass

from music_project.core.models import AudioInfo, Finding


@dataclass(frozen=True)
class DeviceProfile:
    name: str
    codecs: tuple[str, ...]
    max_pcm_rate: int
    bit_depths: tuple[int, ...]
    max_channels: int = 2
    dsd_rates: tuple[int, ...] = ()


def compatibility(info: AudioInfo, profile: DeviceProfile) -> Finding:
    reasons = []
    if info.codec not in profile.codecs:
        reasons.append(f"Codec {info.codec} отсутствует в профиле")
    if info.channels > profile.max_channels:
        reasons.append("Превышено число каналов")
    if info.kind == "DSD":
        if info.sample_rate not in profile.dsd_rates:
            reasons.append("DSD rate отсутствует в профиле")
    else:
        if info.sample_rate > profile.max_pcm_rate:
            reasons.append("Превышена PCM sample rate")
        if info.bit_depth is not None and info.bit_depth not in profile.bit_depths:
            reasons.append("Bit depth отсутствует в профиле")
    unknown = info.sample_rate <= 0 or info.channels <= 0 or info.codec == "unknown"
    return Finding(
        "Incompatible" if reasons else "Unknown" if unknown else "Compatible",
        "; ".join(reasons) or "Свойства соответствуют указанным ограничениям профиля.",
        {"profile": profile.name},
        "Explicit profile constraint checks.",
        ["Не проверяет firmware, transport, container limits или фактическое воспроизведение."],
    )
