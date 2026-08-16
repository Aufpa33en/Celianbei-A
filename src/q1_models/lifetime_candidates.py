"""Monotone candidate families for early-cycle T80 extrapolation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, order=True)
class LifetimeCandidate:
    family: str
    tail_window: int
    shape: float

    @property
    def name(self) -> str:
        return f"{self.family}_w{self.tail_window}_s{self.shape:g}"


def candidate_grid() -> tuple[LifetimeCandidate, ...]:
    rows: list[LifetimeCandidate] = []
    rows.extend(LifetimeCandidate("linear", window, 1.0) for window in (30, 40, 50, 60, 80))
    rows.extend(
        LifetimeCandidate("power", window, exponent)
        for window in (60, 80, 100, 150)
        for exponent in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
    )
    rows.extend(
        LifetimeCandidate("exponential", window, rate)
        for window in (60, 80, 100, 150)
        for rate in (0.001, 0.0025, 0.005, 0.0075, 0.01)
    )
    return tuple(rows)


def _basis(cycles: np.ndarray, candidate: LifetimeCandidate) -> np.ndarray:
    if candidate.family == "linear":
        return cycles
    if candidate.family == "power":
        return np.power(cycles, candidate.shape)
    if candidate.family == "exponential":
        return np.expm1(candidate.shape * cycles)
    raise ValueError(f"unknown lifetime family: {candidate.family}")


def fit_candidate(
    frame: pd.DataFrame,
    end_cycle: int,
    candidate: LifetimeCandidate,
) -> tuple[float, float]:
    prefix = frame.loc[frame["cycle"] <= end_cycle].sort_values("cycle").tail(candidate.tail_window)
    if len(prefix) < candidate.tail_window:
        raise ValueError(
            f"battery has {len(prefix)} rows, fewer than tail window {candidate.tail_window}"
        )
    cycles = prefix["cycle"].to_numpy(dtype=float)
    values = prefix["SOH_clean"].to_numpy(dtype=float)
    basis = _basis(cycles, candidate)
    design = np.column_stack((np.ones(len(prefix)), basis))
    intercept, coefficient = np.linalg.lstsq(design, values, rcond=None)[0]
    return float(intercept), float(min(coefficient, 0.0))


def predict_candidate(
    cycles: np.ndarray,
    intercept: float,
    coefficient: float,
    candidate: LifetimeCandidate,
) -> np.ndarray:
    return intercept + coefficient * _basis(np.asarray(cycles, dtype=float), candidate)


def candidate_t80(
    intercept: float,
    coefficient: float,
    candidate: LifetimeCandidate,
    prefix_cycle: int = 150,
    threshold: float = 0.8,
    slope_epsilon: float = 1e-12,
) -> tuple[float, str]:
    if not np.isfinite(coefficient) or coefficient >= -slope_epsilon:
        return np.nan, "non_decreasing_tail"
    ratio = (threshold - intercept) / coefficient
    if not np.isfinite(ratio) or ratio <= 0:
        return np.nan, "no_positive_crossing_basis"
    if candidate.family == "linear":
        crossing = ratio
    elif candidate.family == "power":
        crossing = ratio ** (1.0 / candidate.shape)
    elif candidate.family == "exponential":
        crossing = np.log1p(ratio) / candidate.shape
    else:
        raise ValueError(f"unknown lifetime family: {candidate.family}")
    if not np.isfinite(crossing):
        return np.nan, "non_finite_crossing"
    if crossing <= prefix_cycle:
        return np.nan, "crossing_not_after_prefix"
    return float(crossing), "finite_extrapolation"
