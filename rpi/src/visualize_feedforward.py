"""Visualize feedforward lookup tables and compute an averaged calibration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


Point = Tuple[float, float]
LutMap = Dict[str, List[Point]]

LUT_KEYS = ["forward_left", "forward_right", "backward_left", "backward_right"]
DISPLAY_LABELS = {
    "forward_left": "Forward Left",
    "forward_right": "Forward Right",
    "backward_left": "Backward Left",
    "backward_right": "Backward Right",
}


def _closest_positive_speed(table: Sequence[Point]) -> Optional[float]:
    positives = [speed for speed, _ in table if speed > 0]
    return min(positives) if positives else None


def _closest_negative_speed(table: Sequence[Point]) -> Optional[float]:
    negatives = [speed for speed, _ in table if speed < 0]
    return max(negatives) if negatives else None


def _closest_positive_pwm(table: Sequence[Point]) -> Optional[float]:
    positives = [pwm for _, pwm in table if pwm > 0]
    return min(positives) if positives else None


def _closest_negative_pwm(table: Sequence[Point]) -> Optional[float]:
    negatives = [pwm for _, pwm in table if pwm < 0]
    return max(negatives) if negatives else None


def _to_points(raw_points: Sequence[Sequence[float]]) -> List[Point]:
    points: List[Point] = []
    for pair in raw_points:
        if len(pair) != 2:
            continue
        speed, pwm = pair
        points.append((float(speed), float(pwm)))
    points.sort(key=lambda p: p[0])
    return points


def _linear_interpolate(speed: float, table: Sequence[Point]) -> Optional[float]:
    if len(table) < 2:
        return None
    if speed < table[0][0] or speed > table[-1][0]:
        return None

    for idx in range(len(table) - 1):
        s1, p1 = table[idx]
        s2, p2 = table[idx + 1]
        if s1 <= speed <= s2:
            if s2 == s1:
                return p1
            frac = (speed - s1) / (s2 - s1)
            return p1 + frac * (p2 - p1)
    return None


def _extract_luts(payload: dict) -> Optional[LutMap]:
    luts: LutMap = {}
    for key in LUT_KEYS:
        if key not in payload:
            return None
        raw_points = payload.get(key, [])
        if not isinstance(raw_points, list):
            return None
        luts[key] = _to_points(raw_points)
    return luts


def _plot_luts(luts: LutMap, title: str, output_path: Path, show_plots: bool) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            "matplotlib is required for LUT visualization. Install it with `pip install matplotlib`."
        ) from exc

    plt.figure(figsize=(10, 6))
    for key in LUT_KEYS:
        points = luts.get(key, [])
        if not points:
            continue
        speeds = [pt[0] for pt in points]
        pwms = [pt[1] for pt in points]
        # matplotlib uses linear segments between consecutive points by default.
        plt.plot(speeds, pwms, marker="o", linewidth=1.8, label=DISPLAY_LABELS[key])

    stats = _compute_statistics(luts)
    deadband_zone = stats.get("deadband_zone_speed")
    if deadband_zone:
        deadband_min, deadband_max = deadband_zone
        plt.axvspan(deadband_min, deadband_max, color="#ffd166", alpha=0.22, label="Deadband speed zone")

    plt.title(title)
    plt.xlabel("Speed (m/s)")
    plt.ylabel("PWM")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    if show_plots:
        plt.show()
    plt.close()


def _build_average_luts(all_luts: Sequence[LutMap]) -> LutMap:
    averaged: LutMap = {}
    for key in LUT_KEYS:
        candidate_tables = [luts[key] for luts in all_luts if luts.get(key)]
        if not candidate_tables:
            averaged[key] = []
            continue

        speed_grid = sorted({round(point[0], 8) for table in candidate_tables for point in table})
        avg_points: List[Point] = []
        for speed in speed_grid:
            interpolated_values: List[float] = []
            for table in candidate_tables:
                pwm = _linear_interpolate(speed, table)
                if pwm is not None:
                    interpolated_values.append(pwm)

            if interpolated_values:
                avg_pwm = sum(interpolated_values) / len(interpolated_values)
                avg_points.append((float(speed), float(avg_pwm)))

        averaged[key] = avg_points
    return averaged


def _metrics_from_deltas(deltas: Sequence[float]) -> dict:
    if not deltas:
        return {
            "sample_count": 0,
            "mean_abs_delta": None,
            "max_abs_delta": None,
            "rms_delta": None,
        }

    abs_deltas = [abs(value) for value in deltas]
    rms = (sum(value * value for value in deltas) / len(deltas)) ** 0.5
    return {
        "sample_count": len(deltas),
        "mean_abs_delta": sum(abs_deltas) / len(abs_deltas),
        "max_abs_delta": max(abs_deltas),
        "rms_delta": rms,
    }


def _compare_tables(table_a: Sequence[Point], table_b: Sequence[Point]) -> dict:
    if len(table_a) < 2 or len(table_b) < 2:
        return _metrics_from_deltas([])

    overlap_min = max(table_a[0][0], table_b[0][0])
    overlap_max = min(table_a[-1][0], table_b[-1][0])
    if overlap_min >= overlap_max:
        return _metrics_from_deltas([])

    combined_points = list(table_a) + list(table_b)
    speed_grid = sorted(
        speed
        for speed in {round(point[0], 8) for point in combined_points}
        if overlap_min <= speed <= overlap_max
    )
    deltas: List[float] = []
    for speed in speed_grid:
        a_val = _linear_interpolate(speed, table_a)
        b_val = _linear_interpolate(speed, table_b)
        if a_val is None or b_val is None:
            continue
        deltas.append(a_val - b_val)

    return _metrics_from_deltas(deltas)


def _mirror_backward_table(backward_table: Sequence[Point]) -> List[Point]:
    mirrored = [(abs(speed), abs(pwm)) for speed, pwm in backward_table]
    mirrored.sort(key=lambda p: p[0])
    return mirrored


def _compute_statistics(luts: LutMap) -> dict:
    positive_edges: List[float] = []
    negative_edges: List[float] = []
    per_motor = {
        "left": {
            "forward_min_speed": _closest_positive_speed(luts.get("forward_left", [])),
            "backward_max_speed": _closest_negative_speed(luts.get("backward_left", [])),
            "forward_min_pwm": _closest_positive_pwm(luts.get("forward_left", [])),
            "backward_max_pwm": _closest_negative_pwm(luts.get("backward_left", [])),
        },
        "right": {
            "forward_min_speed": _closest_positive_speed(luts.get("forward_right", [])),
            "backward_max_speed": _closest_negative_speed(luts.get("backward_right", [])),
            "forward_min_pwm": _closest_positive_pwm(luts.get("forward_right", [])),
            "backward_max_pwm": _closest_negative_pwm(luts.get("backward_right", [])),
        },
    }

    for key in LUT_KEYS:
        table = luts.get(key, [])
        pos = _closest_positive_speed(table)
        neg = _closest_negative_speed(table)
        if pos is not None:
            positive_edges.append(pos)
        if neg is not None:
            negative_edges.append(neg)

    deadband_zone_speed = None
    if positive_edges and negative_edges:
        low = max(negative_edges)
        high = min(positive_edges)
        if low < high:
            deadband_zone_speed = [low, high]

    forward_left = luts.get("forward_left", [])
    forward_right = luts.get("forward_right", [])
    backward_left = luts.get("backward_left", [])
    backward_right = luts.get("backward_right", [])

    backward_left_mirror = _mirror_backward_table(backward_left)
    backward_right_mirror = _mirror_backward_table(backward_right)

    discrepancy = {
        "left_right_pwm_by_direction": {
            "forward": _compare_tables(forward_left, forward_right),
            "backward": _compare_tables(backward_left, backward_right),
        },
        "forward_backward_pwm_by_motor": {
            "left": _compare_tables(forward_left, backward_left_mirror),
            "right": _compare_tables(forward_right, backward_right_mirror),
        },
    }

    return {
        "deadband_zone_speed": deadband_zone_speed,
        "per_motor_deadband_edges": per_motor,
        "discrepancy": discrepancy,
    }


def visualize_feedforward(
    output_json_path: Optional[str] = None,
    show_plots: bool = False,
) -> dict:
    """
    Plot every feedforward LUT JSON in calibration_files/feedforward and compute averaged LUTs.

    Returns:
        Averaged calibration payload as a dict.
    """
    base_dir = Path(__file__).parent.parent.parent / "calibration_files" / "feedforward"
    base_dir = base_dir.resolve()

    if not base_dir.exists() or not base_dir.is_dir():
        raise FileNotFoundError(f"Feedforward directory not found: {base_dir}")

    json_files = sorted(path for path in base_dir.glob("*.json") if path.is_file())
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {base_dir}")

    plots_dir = base_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    all_luts: List[LutMap] = []
    used_files: List[str] = []
    per_file_statistics: Dict[str, dict] = {}

    for json_file in json_files:
        with json_file.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        luts = _extract_luts(payload)
        if luts is None:
            continue

        all_luts.append(luts)
        used_files.append(json_file.name)
        per_file_statistics[json_file.name] = _compute_statistics(luts)

        output_plot = plots_dir / f"{json_file.stem}.png"
        _plot_luts(
            luts=luts,
            title=f"Feedforward LUTs: {json_file.name}",
            output_path=output_plot,
            show_plots=show_plots,
        )

    if not all_luts:
        raise ValueError("No valid LUT JSON files found (missing required LUT keys).")

    averaged_luts = _build_average_luts(all_luts)
    average_statistics = _compute_statistics(averaged_luts)
    averaged_payload = {
        "calibration_method": "lookup_table_average_with_linear_interpolation",
        "source_files": used_files,
        "statistics": average_statistics,
        "per_file_statistics": per_file_statistics,
        "forward_left": averaged_luts["forward_left"],
        "forward_right": averaged_luts["forward_right"],
        "backward_left": averaged_luts["backward_left"],
        "backward_right": averaged_luts["backward_right"],
    }

    avg_plot_file = plots_dir / "feedforward_average.png"
    _plot_luts(
        luts=averaged_luts,
        title="Feedforward LUTs: Average Calibration",
        output_path=avg_plot_file,
        show_plots=show_plots,
    )

    output_json = Path(output_json_path) if output_json_path else base_dir / "feedforward_lookup_table_average.json"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as handle:
        json.dump(averaged_payload, handle, indent=2)

    print(json.dumps(averaged_payload, indent=2))
    print(f"Saved per-file and average plots to: {plots_dir}")
    print(f"Saved averaged calibration JSON to: {output_json}")

    return averaged_payload
