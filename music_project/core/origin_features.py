"""Measured spectral features and explicit exploratory rules, not source identities."""

import numpy as np
from scipy.ndimage import median_filter

from music_project.core.origin_calibration import CANDIDATES

BOUNDARY_RULE = {
    "drop_db_min": 18.0,
    "below_relative_db_min": -60.0,
    "below_density_min_fs2_per_hz": 1e-20,
    "tonal_spread_db_max": 35.0,
    "side_bands_hz": [-2000, -500, 500, 2000],
    "minimum_bins_per_side": 5,
}
NOISE_RULE = {
    "slope_difference_db_per_decade_min": 12.0,
    "sse_reduction_min": 0.5,
    "fit_rms_db_max": 4.0,
    "minimum_points_per_regime": 4,
}


def db(power):
    return float(10 * np.log10(power)) if power > 0 else None


def boundary_features(frequencies, density) -> list[dict]:
    f, p = np.asarray(frequencies), np.asarray(density)
    if p.ndim == 1:
        p = p[:, None]
    if len(f) < 2 or p.shape[0] != len(f) or not np.isfinite(p).all() or np.any(p < 0):
        raise ValueError("Invalid measured PSD")
    df = float(f[1] - f[0])
    rows = []
    for candidate in CANDIDATES:
        low = (f >= candidate - 2000) & (f <= candidate - 500)
        high = (f >= candidate + 500) & (f <= candidate + 2000)
        applicable = f[-1] >= candidate + 2000 and low.sum() >= 5 and high.sum() >= 5
        row = {
            "id": f"boundary-{candidate}",
            "candidate_hz": candidate,
            "status": "Measured" if applicable else "Unsupported",
            "channels": [],
            "frequency_step_hz": df,
            "rule": BOUNDARY_RULE,
        }
        if applicable:
            ref = (f >= 1000) & (f <= 8000)
            for channel in range(p.shape[1]):
                y = p[:, channel]
                below, above = float(np.median(y[low])), float(np.median(y[high]))
                reference = float(np.mean(y[ref])) if np.any(ref) else 0
                drop = (
                    10 * (np.log10(below) - np.log10(above))
                    if below > 0 and above > 0
                    else np.inf
                    if below > 0
                    else None
                )
                relative = (
                    10 * (np.log10(below) - np.log10(reference))
                    if below > 0 and reference > 0
                    else None
                )
                q10, q90 = np.percentile(y[low], [10, 90])
                spread = 10 * (np.log10(q90) - np.log10(q10)) if q10 > 0 else np.inf
                eligible = (
                    below > BOUNDARY_RULE["below_density_min_fs2_per_hz"]
                    and relative is not None
                    and relative >= -60
                    and spread <= 35
                )
                detected = bool(eligible and drop is not None and drop >= 18)
                local = (f >= candidate - 2000) & (f <= candidate + 2000)
                slope = width = crossing = adjacent_drop = None
                if np.all(y[local] > 0):
                    smoothed = median_filter(10 * np.log10(y[local]), size=5, mode="nearest")
                    local_f = f[local]
                    slope = float(np.polyfit((local_f - candidate) / 1000, smoothed, 1)[0])
                    adjacent_drop = float(np.max(-np.diff(smoothed)))
                    if detected and above > 0:
                        top = 10 * np.log10(below)
                        first = np.flatnonzero(smoothed <= top - 0.1 * drop)
                        last = np.flatnonzero(smoothed <= top - 0.9 * drop)
                        if len(first) and len(last) and last[0] >= first[0]:
                            width = float(local_f[last[0]] - local_f[first[0]])
                            crossing = float((local_f[last[0]] + local_f[first[0]]) / 2)
                above_region = (f >= candidate + 500) & (f <= min(candidate + 12000, f[-1]))
                row["channels"].append(
                    {
                        "channel": channel + 1,
                        "below_density_fs2_per_hz": below,
                        "above_density_fs2_per_hz": above,
                        "attenuation_db": float(drop)
                        if drop is not None and np.isfinite(drop)
                        else None,
                        "attenuation_state": "positive infinity"
                        if drop is not None and np.isinf(drop)
                        else "finite"
                        if drop is not None
                        else "Unknown",
                        "below_relative_db": float(relative) if relative is not None else None,
                        "below_tonal_spread_db": float(spread) if np.isfinite(spread) else None,
                        "eligible": bool(eligible),
                        "detected": detected,
                        "local_slope_db_per_khz": slope,
                        "transition_width_hz": width,
                        "transition_width_state": "unresolved at FFT spacing"
                        if width == 0
                        else "estimated from bin crossings"
                        if width is not None
                        else "Unknown",
                        "max_adjacent_smoothed_drop_db": adjacent_drop,
                        "transition_midpoint_hz": crossing,
                        "transition_uncertainty_hz": 2 * df,
                        "above_boundary_power_fs2": float(np.sum(y[above_region]) * df),
                        "above_boundary_range_hz": [
                            candidate + 500,
                            min(candidate + 12000, float(f[-1])),
                        ],
                        "limitation": "Finite resolution and excitation guard; a measured boundary does not identify its cause",
                    }
                )
        rows.append(row)
    return rows


def noise_features(frequencies, density, maximum_hz: float = 160000) -> dict:
    f, p = np.asarray(frequencies), np.asarray(density)
    if p.ndim == 1:
        p = p[:, None]
    upper = min(float(f[-1]), maximum_hz)
    if upper < 30000:
        return {"status": "Unsupported", "reason": "Ultrasonic bandwidth too small"}
    edges = np.geomspace(20000, upper, 25)
    centers, medians, spreads = [], [], []
    for low, high in zip(edges[:-1], edges[1:], strict=True):
        bins = (f >= low) & (f < high)
        if bins.sum() < 3:
            continue
        centers.append(float(np.sqrt(low * high)))
        medians.append(np.median(p[bins], axis=0))
        q20, q90 = np.percentile(p[bins], [20, 90], axis=0)
        spreads.append(
            [float(10 * np.log10(b / a)) if a > 0 else None for a, b in zip(q20, q90, strict=True)]
        )
    if len(centers) < 8:
        return {"status": "Unknown", "reason": "Insufficient ultrasonic bins"}
    values = np.asarray(medians)
    channels = []
    x = np.log10(centers)
    for channel in range(p.shape[1]):
        y = values[:, channel]
        valid = y > 1e-24
        row = {
            "channel": channel + 1,
            "status": "Measured" if valid.sum() >= 8 else "Unknown",
            "regime_change": None,
            "rising_onset_hz": None,
            "plateaus_hz": [],
        }
        if np.all(valid):
            z = 10 * np.log10(y)
            whole = np.polyfit(x, z, 1)
            whole_sse = float(np.sum((z - np.polyval(whole, x)) ** 2))
            best = None
            for split in range(4, len(x) - 3):
                left, right = (
                    np.polyfit(x[:split], z[:split], 1),
                    np.polyfit(x[split:], z[split:], 1),
                )
                sse = float(
                    np.sum((z[:split] - np.polyval(left, x[:split])) ** 2)
                    + np.sum((z[split:] - np.polyval(right, x[split:])) ** 2)
                )
                if best is None or sse < best[0]:
                    best = (sse, split, left, right)
            slopes = np.diff(z) / np.diff(x)
            row["whole_slope_db_per_decade"] = float(whole[0])
            row["local_slopes_db_per_decade"] = slopes.tolist()
            sse, split, left, right = best
            reduction = 1 - sse / whole_sse if whole_sse > 1e-12 else 0
            row["two_regime_fit"] = {
                "candidate_hz": centers[split],
                "sse_reduction": reduction,
                "fit_rms_db": float(np.sqrt(sse / len(x))),
                "slopes_db_per_decade": [float(left[0]), float(right[0])],
            }
            if abs(left[0] - right[0]) >= 12 and reduction >= 0.5 and np.sqrt(sse / len(x)) <= 4:
                row["regime_change"] = {
                    "low_hz": centers[split - 1],
                    "high_hz": centers[split + 1],
                    "slopes_db_per_decade": [float(left[0]), float(right[0])],
                }
            for i in range(len(slopes) - 2):
                if np.all(slopes[i : i + 3] >= 12) and z[i + 3] - z[i] >= 8:
                    row["rising_onset_hz"] = centers[i]
                    break
            for i in range(len(slopes) - 2):
                if np.all(np.abs(slopes[i : i + 3]) < 6):
                    row["plateaus_hz"].append([centers[i], centers[i + 3]])
        channels.append(row)
    df = float(f[1] - f[0])
    audible = (f >= 20) & (f < 20000)
    ultra = (f >= 20000) & (f <= upper)
    return {
        "status": "Measured",
        "frequencies_hz": centers,
        "median_density_fs2_per_hz": values.tolist(),
        "q90_minus_q20_db": spreads,
        "channels": channels,
        "rule": NOISE_RULE,
        "audible_power_fs2": (p[audible].sum(axis=0) * df).tolist(),
        "ultrasonic_power_fs2": (p[ultra].sum(axis=0) * df).tolist(),
        "range_hz": [20000, upper],
        "interpretation": "Spectral-floor proxy includes noise, tones and conversion; not a unique noise-shaping signature",
    }
