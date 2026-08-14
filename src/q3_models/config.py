"""Frozen smoke-test configuration for Question 3."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Q3Config:
    version: str = "q3_smoke_v1"
    seed: int = 20260814
    early_lengths: tuple[int, ...] = (50, 100, 150)
    future_start: int = 151
    future_end: int = 200
    smoke_battery_ids: tuple[int, ...] = (1, 35, 8, 17, 29, 48, 21, 15, 6)
    power_grid: tuple[float, ...] = tuple(0.25 + i * (2.75 / 23) for i in range(24))
    lambda_gamma_grid: tuple[float, ...] = (0.1, 1.0, 10.0)
    gamma_bounds: tuple[float, float] = (0.0, 3.0)
    k_grid: tuple[int, ...] = (1, 2, 3, 5)
    alpha_grid: tuple[float, ...] = (1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0)
    ensemble_weight_grid: tuple[float, ...] = tuple(i / 10 for i in range(11))
    soh_bounds: tuple[float, float] = (0.75, 1.05)
    eol_max_cycle: int = 5000
    runtime_limit_seconds: float = 120.0
    tie_relative_tolerance: float = 0.02
    sample_points: int = 20
    slope_windows: tuple[int, ...] = (20, 50)


CONFIG = Q3Config()
