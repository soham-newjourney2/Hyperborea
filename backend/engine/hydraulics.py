"""Shared hydraulic formulas (planning §7). Pure functions — used by pipelines (P06) and the flood engine (P08)."""
import math

MANNING_N = 0.015
MIN_SLOPE = 0.002


def manning_full_circular(d_m: float, slope: float, n: float = MANNING_N) -> float:
    """Full-flow capacity of a circular conduit, Q [m³/s] = (1/n) · A · R^(2/3) · S^(1/2), A = πd²/4, R = d/4."""
    if d_m <= 0 or slope <= 0 or n <= 0:
        raise ValueError("diameter, slope and n must be positive")
    area = math.pi * d_m * d_m / 4
    return (1 / n) * area * (d_m / 4) ** (2 / 3) * math.sqrt(slope)


def rational_runoff(c: float, i_mm_h: float, area_m2: float) -> float:
    """Peak runoff Q [m³/s] = C · i [mm/h] · A [m²] / 3.6e6 (rational method)."""
    return c * i_mm_h * area_m2 / 3.6e6
