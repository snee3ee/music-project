"""Adaptive audible-band observations reusing Origin's measured boundary contract."""

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import find_peaks

from music_project.core.origin_features import BOUNDARY_RULE, boundary_features

LOSSY_BOUNDARY_RULE = {**BOUNDARY_RULE, "side_bands_hz": [-600, -200, 200, 600]}


def adaptive_candidates(f, p, maximum=6):
    """Local maxima of side-median contrast, not fixed integer-kHz hypotheses.

    Only complete +/-600Hz support, 8–24kHz search, >=600Hz separation. Ranking is
    observation selection, not codec confidence. The Nyquist edge has no upper side.
    """
    f, p = np.asarray(f), np.asarray(p)
    df = float(f[1] - f[0])
    if not np.any(p > 0):
        return []
    # Locate the transition inside the excluded +/-200Hz gap, rather than
    # maximizing a wide contrast at an edge that can straddle the reference band.
    size = max(3, round(100 / df) | 1)
    smooth = median_filter(10 * np.log10(np.maximum(p, 1e-30)), size=(size, 1), mode="nearest")
    offset = max(1, round(100 / df))
    contrast = smooth[: -2 * offset] - smooth[2 * offset :]
    centers = np.arange(offset, len(f) - offset)
    allowed = (f[centers] >= 8000) & (f[centers] <= min(24000, f[-1] - 600))
    strengths = np.max(contrast, axis=1)
    ids, _ = find_peaks(np.where(allowed, strengths, -np.inf))
    # Tie-break by frequency, not platform sort instability.
    ordered = sorted(ids, key=lambda i: (-strengths[i], f[centers[i]]))
    selected = []
    for i in ordered:
        frequency = float(f[centers[i]])
        if all(abs(frequency - previous) >= 600 for previous in selected):
            selected.append(frequency)
        if len(selected) >= maximum:
            break
    return sorted(selected)


def measure_candidates(f, p):
    return boundary_features(f, p, candidates=adaptive_candidates(f, p), rule=LOSSY_BOUNDARY_RULE)


def band_measurements(f, p):
    """One-sided bin-sum energy and spectral-floor proxies; not noise separation."""
    f, p = np.asarray(f), np.asarray(p)
    df = float(f[1] - f[0])
    total = p.sum(axis=0) * df
    reference = np.mean(p[(f >= 1000) & (f <= 8000)], axis=0)
    edges = sorted({0, 1000, 4000, 8000, 12000, 14000, 16000, 18000, 20000, float(f[-1])})
    edges = [edge for edge in edges if edge <= f[-1]]
    result = []
    for low, high in zip(edges[:-1], edges[1:], strict=True):
        mask = (f >= low) & ((f < high) | ((f == high) & (high == f[-1])))
        if not mask.any():
            continue
        for ch in range(p.shape[1]):
            values = p[mask, ch]
            energy = float(values.sum() * df)
            q10, median, q90 = np.percentile(values, [10, 50, 90])
            result.append(
                {
                    "channel": ch + 1,
                    "low_hz": low,
                    "high_hz": high,
                    "power_fs2": energy,
                    "fraction_of_measured_power": energy / float(total[ch]) if total[ch] else None,
                    "median_density_fs2_per_hz": float(median),
                    "q10_density_fs2_per_hz": float(q10),
                    "q90_density_fs2_per_hz": float(q90),
                    "median_relative_db": float(10 * np.log10(median / reference[ch]))
                    if median > 0 and reference[ch] > 0
                    else None,
                    "median_state": "finite" if median > 0 else "negative infinity",
                    "bins": int(mask.sum()),
                }
            )
    return result
