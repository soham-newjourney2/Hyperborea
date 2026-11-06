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


PIPE_SIZES_M = [0.6, 0.75, 0.9, 1.05, 1.2, 1.35, 1.5, 1.8, 2.1, 2.4]  # standard circular sizes (P06 D-20, P09 upsize)


def next_pipe_size(d_m: float, steps: int = 1) -> float:
    """Standard size `steps` above d (capped at the largest size)."""
    bigger = [s for s in PIPE_SIZES_M if s > d_m + 1e-9]
    return bigger[min(steps, len(bigger)) - 1] if bigger else PIPE_SIZES_M[-1]
