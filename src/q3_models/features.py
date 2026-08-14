"""Prefix-only health feature extraction and fold-local transformation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import CONFIG, Q3Config
from .core import BatteryRecord, slope


def _safe_series(record: BatteryRecord, column: str, L: int) -> np.ndarray:
    return record.cycles.loc[record.cycles["cycle"].le(L), column].to_numpy(float)


def prefix_numeric_features(record: BatteryRecord, L: int, config: Q3Config = CONFIG) -> np.ndarray:
    prefix = record.relative_soh[:L]
    positions = np.linspace(4, L - 1, config.sample_points).round().astype(int)
    sampled = prefix[positions]
    full_slope = slope(prefix)
    local_slopes = []
    for window in config.slope_windows:
        w = min(window, L)
        local_slopes.append(slope(prefix[-w:], np.arange(L - w + 1, L + 1)))
    w = min(20, L // 2)
    prior = prefix[-2 * w : -w] if L >= 2 * w else prefix[:w]
    recent = prefix[-w:]
    curvature = slope(recent) - slope(prior)
    t = np.arange(1, L + 1, dtype=float)
    linear_fit = np.polyval(np.polyfit(t, prefix, 1), t) if L >= 2 else prefix.copy()
    residual_std = float(np.std(prefix - linear_fit, ddof=1)) if L > 2 else 0.0
    recent_range = float(np.ptp(recent)) if recent.size else 0.0

    dynamic: list[float] = []
    for column in ("IR_clean", "Tavg_raw", "chargetime_raw"):
        values = _safe_series(record, column, L)
        dynamic.extend(
            [
                float(np.nanmean(values)),
                float(np.nanmean(values[-min(20, L) :])),
                slope(values),
            ]
        )

    row = record.meta
    c1 = float(row.get("C1", np.nan))
    q1 = float(row.get("Q1", np.nan)) / 100.0
    c2 = float(row.get("C2", np.nan))
    c1_missing = float(not np.isfinite(c1))
    if np.isfinite(c1) and np.isfinite(q1) and np.isfinite(c2):
        J = c1 * q1 + c2 * (0.8 - q1)
        H = 0.5 * (c1 * q1**2 + c2 * (0.8**2 - q1**2))
        high = [c1 * max(q1 - s0, 0) + c2 * (0.8 - max(q1, s0)) for s0 in (0.5, 0.6, 0.7)]
    else:
        J = H = np.nan
        high = [np.nan, np.nan, np.nan]
    return np.asarray(
        list(sampled)
        + [full_slope, *local_slopes, curvature, residual_std, recent_range]
        + dynamic
        + [c1, q1, c2, c1_missing, J, H, *high],
        dtype=float,
    )


@dataclass
class PrefixFeatureTransformer:
    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    keep: np.ndarray
    policies: tuple[str, ...]

    @classmethod
    def fit(cls, records: list[BatteryRecord], L: int) -> "PrefixFeatureTransformer":
        raw = np.vstack([prefix_numeric_features(record, L) for record in records])
        medians = np.nanmedian(raw, axis=0)
        medians = np.where(np.isfinite(medians), medians, 0.0)
        filled = np.where(np.isfinite(raw), raw, medians)
        means = filled.mean(axis=0)
        scales = filled.std(axis=0, ddof=1) if len(records) > 1 else np.ones(raw.shape[1])
        keep = np.isfinite(scales) & (scales > 1e-12)
        scales = np.where(keep, scales, 1.0)
        policies = tuple(sorted({record.policy for record in records}))
        return cls(medians=medians, means=means, scales=scales, keep=keep, policies=policies)

    def transform(self, records: list[BatteryRecord], L: int) -> np.ndarray:
        raw = np.vstack([prefix_numeric_features(record, L) for record in records])
        filled = np.where(np.isfinite(raw), raw, self.medians)
        numeric = ((filled - self.means) / self.scales)[:, self.keep]
        one_hot = np.zeros((len(records), len(self.policies)), dtype=float)
        policy_index = {policy: idx for idx, policy in enumerate(self.policies)}
        for row, record in enumerate(records):
            if record.policy in policy_index:
                one_hot[row, policy_index[record.policy]] = 1.0
        return np.column_stack([numeric, one_hot])
