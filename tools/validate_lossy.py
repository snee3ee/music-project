"""Controlled A/B/C/D dataset and reference-free-indicator feasibility evaluation."""

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import signal

from music_project import METHOD_VERSION, __version__
from music_project.core.config import Settings
from music_project.core.decoder import PCMContext
from music_project.core.files import file_hash
from music_project.core.lossy import bandwidth_observed, investigate_context
from music_project.core.lossy_models import LOSSY_VERSION
from music_project.core.probe import probe
from music_project.core.subprocess_utils import backend_versions
from tools.lossy_dataset import (
    convert,
    encoder_capabilities,
    lossy_chain,
    negative,
    original,
    write_pcm,
)


def exploratory_metrics(x, rate):
    """Not production evidence: flux and pre-transient energy have non-lossy causes."""
    mono = np.mean(x**2, axis=1)
    _, _, z = signal.stft(x[:, 0], fs=rate, nperseg=1024, noverlap=512, boundary=None)
    magnitude = np.abs(z)
    change = np.maximum(np.diff(magnitude, axis=1), 0)
    flux = float(
        np.mean(
            np.sum(change**2, axis=0)
            / np.maximum(np.sum(magnitude[:, 1:] ** 2 + magnitude[:, :-1] ** 2, axis=0), 1e-30)
        )
    )
    # Known fixture onset near0.5s; local energy maximum, not a historical event detector.
    first, last = round(0.45 * rate), round(0.55 * rate)
    peak = first + int(np.argmax(mono[first:last]))
    width = max(1, round(0.01 * rate))
    before = float(np.mean(mono[max(0, peak - width) : peak]))
    after = float(np.mean(mono[peak : peak + width]))
    return {
        "normalized_positive_spectral_flux": flux,
        "pre_post_energy_ratio": before / after if after else None,
        "status": "Exploratory only; no codec decision rule",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/lossy-validation"))
    args = parser.parse_args()
    folder = args.output
    folder.mkdir(parents=True, exist_ok=True)
    settings = Settings(timeout=120, analysis_seconds=20)
    capabilities = encoder_capabilities(settings)
    report = {
        "app_version": __version__,
        "method_version": METHOD_VERSION,
        "lossy_method": LOSSY_VERSION,
        "backend_versions": backend_versions(settings),
        "capabilities": capabilities,
        "cases": [],
        "skipped": [],
        "scope": "Synthetic signals only. Feature trigger rates are not real-world codec-classifier accuracy or confidence.",
    }
    base_cases = {}

    def evaluate(path, group, **metadata):
        start = time.perf_counter()
        info = probe(path, settings)
        context = PCMContext.load(info, settings)
        finding = investigate_context(
            context,
            reason="Controlled fixture fully decoded into bounded context; no private audio",
        )
        m = finding.measurements
        observed = bandwidth_observed(m)
        recurrent = any(s["recurrent"] for b in m["candidates"] for s in b["stability"])
        row = {
            "id": path.stem,
            "group": group,
            **metadata,
            "rate": info.sample_rate,
            "channels": info.channels,
            "current_codec": info.codec,
            "bits": info.bit_depth,
            "file_sha256": file_hash(path),
            "classification": m["classification"],
            "bandwidth_observation": observed,
            "recurrent": recurrent,
            "historical_codec": m["historical_codec"],
            "counts": m["counts"],
            "seconds": time.perf_counter() - start,
            "candidates": [
                {"hz": b["candidate_hz"], "channels": b["channels"], "stability": b["stability"]}
                for b in m["candidates"]
            ],
            "exploratory": exploratory_metrics(context.samples, info.sample_rate),
        }
        report["cases"].append(row)
        return context.samples, info.sample_rate

    for rate in [44100, 48000]:
        for content in ["broadband", "tonal", "transient"]:
            x = original(rate, content)
            name = f"{content}-{rate}"
            source = write_pcm(folder / (name + ".wav"), x, rate)
            base_cases[rate, content] = source
            evaluate(source, "A", content=content, history="Original synthetic PCM")
            target = convert(settings, source, folder / (name + "-roundtrip.flac"), "-c:a", "flac")
            evaluate(target, "A", content=content, history="PCM to FLAC round-trip")
            restored = convert(
                settings, target, folder / (name + "-roundtrip.wav"), "-c:a", "pcm_s24le"
            )
            evaluate(restored, "A", content=content, history="FLAC to WAV round-trip")
            for codec, rates in [("mp3", [96, 128, 320]), ("aac", [96, 128, 256])]:
                if not capabilities[codec]:
                    report["skipped"].append(
                        {
                            "codec": codec,
                            "reason": "Encoder unavailable",
                            "content": content,
                            "rate": rate,
                        }
                    )
                    continue
                for bitrate in rates:
                    target = lossy_chain(
                        settings, source, folder, f"{name}-{codec}-{bitrate}", codec, bitrate
                    )
                    y, decoded_rate = evaluate(
                        target,
                        "B",
                        content=content,
                        history="PCM to perceptual codec to FLAC",
                        historical_codec_ground_truth=codec,
                        bitrate_kbps=bitrate,
                        configuration="default",
                    )
                    if content == "broadband" and bitrate == 128:
                        for processing in [
                            "gain",
                            "equalization",
                            "dynamics",
                            "resampling",
                            "mild-filter",
                            "added-noise",
                        ]:
                            new_rate = decoded_rate
                            if processing == "gain":
                                z = y * 0.6
                            elif processing == "equalization":
                                z = negative(y, new_rate, "equalized")
                            elif processing == "dynamics":
                                z = np.tanh(y * 20) * 0.3
                            elif processing == "resampling":
                                z, new_rate = signal.resample_poly(y, 2, 1, axis=0), new_rate * 2
                            elif processing == "mild-filter":
                                z = signal.sosfilt(
                                    signal.butter(3, 19000, fs=new_rate, output="sos"), y, axis=0
                                )
                            else:
                                z = y + np.random.default_rng(12).normal(0, 0.003, y.shape)
                            intermediate = write_pcm(
                                folder / f"{name}-{codec}-{processing}.wav", z, new_rate
                            )
                            final = convert(
                                settings,
                                intermediate,
                                intermediate.with_suffix(".flac"),
                                "-c:a",
                                "flac",
                            )
                            evaluate(
                                final,
                                "D",
                                content=content,
                                history="Known lossy history followed by processing",
                                historical_codec_ground_truth=codec,
                                bitrate_kbps=bitrate,
                                processing=processing,
                            )
        for bits in [16, 24]:
            path = write_pcm(folder / f"depth-{rate}-{bits}.wav", original(rate), rate, bits)
            evaluate(path, "A", content="broadband", history=f"Original{bits}-bit PCM")
        for kind in [
            "band-limited",
            "analog-style",
            "equalized",
            "hf-poor",
            "limited",
            "clipped",
            "noisy",
            "mono",
            "linear-phase",
        ]:
            path = write_pcm(
                folder / f"negative-{rate}-{kind}.wav", negative(original(rate), rate, kind), rate
            )
            evaluate(path, "C", content=kind, history="No perceptual codec used")
        for codec, configuration in [("mp3", "independent-stereo"), ("aac", "fast")]:
            if capabilities[codec] and capabilities[codec + "_alternate_configuration"]:
                path = lossy_chain(
                    settings,
                    base_cases[rate, "broadband"],
                    folder,
                    f"configuration-{rate}-{codec}",
                    codec,
                    128,
                    configuration=configuration,
                )
                evaluate(
                    path,
                    "B",
                    content="broadband",
                    history="Alternative encoder configuration",
                    historical_codec_ground_truth=codec,
                    bitrate_kbps=128,
                    configuration=configuration,
                )
            else:
                report["skipped"].append(
                    {
                        "codec": codec,
                        "configuration": configuration,
                        "rate": rate,
                        "reason": "Encoder/configuration unavailable",
                    }
                )
    for rate in [96000, 192000]:
        x = signal.resample_poly(original(48000), rate // 48000, 1, axis=0)
        path = write_pcm(folder / f"nonlossy-resampled-{rate}.wav", x, rate)
        evaluate(
            path,
            "C",
            content="nonlossy-resampling",
            history="PCM resampling without perceptual codec",
        )

    groups = defaultdict(list)
    for row in report["cases"]:
        groups[row["group"]].append(row)
    report["group_summary"] = {
        group: {
            "cases": len(rows),
            "bandwidth_observations": sum(r["bandwidth_observation"] for r in rows),
            "recurrent_observations": sum(r["recurrent"] for r in rows),
            "classifications": dict(Counter(r["classification"] for r in rows)),
        }
        for group, rows in groups.items()
    }
    partitions = defaultdict(list)
    for r in report["cases"]:
        key = "/".join(
            str(r.get(k, "all"))
            for k in [
                "group",
                "historical_codec_ground_truth",
                "bitrate_kbps",
                "content",
                "processing",
            ]
        )
        partitions[key].append(r)
    report["stratified_observations"] = {
        key: {
            "n": len(rows),
            "triggers": sum(r["bandwidth_observation"] for r in rows),
            "abstentions": sum(
                r["classification"] in {"Inconclusive", "Not evaluated"} for r in rows
            ),
        }
        for key, rows in partitions.items()
    }
    positives = [r for r in report["cases"] if r["group"] in {"B", "D"}]
    negatives = [r for r in report["cases"] if r["group"] in {"A", "C"}]
    report["naive_bandwidth_as_lossy_classifier"] = {
        "deployed": False,
        "true_positive_count": sum(r["bandwidth_observation"] for r in positives),
        "positive_denominator": len(positives),
        "false_positive_count": sum(r["bandwidth_observation"] for r in negatives),
        "negative_denominator": len(negatives),
        "false_negative_count": sum(not r["bandwidth_observation"] for r in positives),
        "interpretation": "Feature trigger counts only. Non-lossy filtering confounds attribution; no codec score is deployed.",
    }
    report["additional_metrics_decision"] = {
        "flux": "Not deployed: content/transients/editing also change flux",
        "pre_echo": "Not deployed: known reference/onset needed; linear-phase filtering/noise can create similar ratios",
        "diagnostic_codec_classifier": "Unsupported",
    }
    distributions = {}
    for metric in ["normalized_positive_spectral_flux", "pre_post_energy_ratio"]:
        pos = np.array(
            [r["exploratory"][metric] for r in positives if r["exploratory"][metric] is not None]
        )
        neg = np.array(
            [r["exploratory"][metric] for r in negatives if r["exploratory"][metric] is not None]
        )
        distributions[metric] = {
            "positive_min_median_max": np.percentile(pos, [0, 50, 100]).tolist()
            if len(pos)
            else [],
            "negative_min_median_max": np.percentile(neg, [0, 50, 100]).tolist()
            if len(neg)
            else [],
            "negative_values_inside_positive_range": int(
                np.sum((neg >= pos.min()) & (neg <= pos.max()))
            )
            if len(pos)
            else None,
            "decision": "Descriptive overlap on this synthetic population; no classification threshold or codec evidence deployed",
        }
    report["exploratory_control_distributions"] = distributions
    proxy = report["naive_bandwidth_as_lossy_classifier"]
    proxy["positive_trigger_fraction"] = (
        proxy["true_positive_count"] / len(positives) if positives else None
    )
    proxy["negative_trigger_fraction"] = (
        proxy["false_positive_count"] / len(negatives) if negatives else None
    )
    output = folder / "validation.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report["group_summary"], indent=2), flush=True)
    print(json.dumps(report["naive_bandwidth_as_lossy_classifier"], indent=2), flush=True)
    print("Skipped:", len(report["skipped"]), "Saved", str(output), flush=True)


if __name__ == "__main__":
    main()
