"""Shared simulation and plot style for the four-part A/B testing series.

Setup:  pip install numpy scipy matplotlib git+https://github.com/johnswyou/mcb.git
Run:    python scripts/ab_series/part1.py      (likewise part2.py, part3.py, part4.py)

Each partN.py prints the numbers quoted in its post and writes that post's figures
into the post's folder under content/blog/.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BLOG = Path(__file__).resolve().parents[2] / "content" / "blog"
POST = {
    1: BLOG / "5-ab-testing-1-hypothesis-tests",
    2: BLOG / "6-ab-testing-2-test-duration",
    3: BLOG / "7-ab-testing-3-abn-mcb",
    4: BLOG / "8-ab-testing-4-abn-test-duration",
}

# ----------------------------------------------------------------------------
# The simulated store
# ----------------------------------------------------------------------------
P_CONTROL = 0.030  # conversion rate of the current product page
AOV = 100.0  # mean order value, dollars
ORDER_CV = 1.0  # sd / mean of order value (lognormal)
_S2 = np.log(1.0 + ORDER_CV**2)
ORDER_MU, ORDER_SIGMA = np.log(AOV) - _S2 / 2.0, np.sqrt(_S2)

BASE_SESSIONS = 36_000  # eligible sessions on an average day
DOW = np.array([1.08, 1.04, 1.00, 0.98, 0.90, 0.92, 1.08])  # Mon..Sun, mean 1
HISTORY_WEEKS = 12
PROMO_DAYS = (32, 33, 34)  # Fri-Sun of history week 5: a sale weekend

# True conversion rates; A is the current page. Order values are identical in every arm.
TWO_ARM = {"A": 0.0300, "B": 0.0315}
FOUR_ARM = {"A": 0.0300, "B": 0.0309, "C": 0.0321, "D": 0.0333}

# Seeds. The two test datasets were picked to illustrate a common outcome (CR resolved,
# RPS not); they are not random draws. Part 2 reports how often the two-arm outcome occurs.
TRAFFIC_SEED, TWO_ARM_SEED, FOUR_ARM_SEED = 12, 290, 129


def rps_moments(p: float) -> tuple[float, float]:
    """True mean and variance of revenue per session at conversion rate p."""
    mean = p * AOV
    return mean, p * AOV**2 * (1.0 + ORDER_CV**2) - mean**2


def daily_sessions(seed: int = TRAFFIC_SEED, weeks: int = 20) -> np.ndarray:
    """Eligible sessions per day: weekday pattern, weekly drift, daily noise, one sale."""
    rng = np.random.default_rng(seed)
    days = weeks * 7
    week_level = np.repeat(rng.lognormal(0.0, 0.03, weeks), 7)
    day_level = rng.lognormal(0.0, 0.05, days)
    sessions = BASE_SESSIONS * np.tile(DOW, weeks) * week_level * day_level
    sessions[list(PROMO_DAYS)] *= 1.40
    return np.round(sessions).astype(int)


def order_values(rng: np.random.Generator, size: int) -> np.ndarray:
    return rng.lognormal(ORDER_MU, ORDER_SIGMA, size)


def two_arm_test() -> dict[str, np.ndarray]:
    """Parts 1-2: A vs B over the two weeks after the history window."""
    n = int(daily_sessions()[84:98].sum())
    return simulate_sessions(np.random.default_rng(TWO_ARM_SEED), n, TWO_ARM)


def four_arm_test() -> dict[str, np.ndarray]:
    """Parts 3-4: A vs B, C, D over four weeks."""
    n = int(daily_sessions()[112:140].sum())
    return simulate_sessions(np.random.default_rng(FOUR_ARM_SEED), n, FOUR_ARM)


def simulate_sessions(rng: np.random.Generator, n: int, arms: dict[str, float]):
    """Revenue of each session (0 if no purchase), grouped by the arm it was randomized to."""
    labels = list(arms)
    arm = rng.integers(0, len(labels), n)
    converted = rng.random(n) < np.array([arms[a] for a in labels])[arm]
    revenue = np.zeros(n)
    revenue[converted] = order_values(rng, int(converted.sum()))
    return {a: revenue[arm == i] for i, a in enumerate(labels)}


def arm_stats(rng: np.random.Generator, n: int, p: float) -> tuple[float, float, float]:
    """(conversion rate, mean revenue, revenue variance) of one simulated arm of n sessions.

    Draws only the orders, so repeating a whole test thousands of times stays cheap.
    """
    orders = order_values(rng, rng.binomial(n, p))
    mean = orders.sum() / n
    var = (np.square(orders).sum() - n * mean**2) / (n - 1)
    return orders.size / n, mean, var


# ----------------------------------------------------------------------------
# Plot style: blue = conversion rate, orange = revenue per session,
# gray = control / null / reference, red = an error.
# ----------------------------------------------------------------------------
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
BLUE, BLUE_TINT = "#2a78d6", "#b7d3f6"
ORANGE, ORANGE_TINT = "#eb6834", "#f8c3ad"
GRAY, GRAY_TINT = "#898781", "#e9e8e3"
RED = "#d03b3b"
KPI = {"cr": (BLUE, BLUE_TINT), "rps": (ORANGE, ORANGE_TINT)}

plt.rcParams.update(
    {
        "font.family": "Inter",
        "font.size": 10.5,
        "mathtext.fontset": "custom",
        "mathtext.rm": "Inter",
        "mathtext.it": "Inter:italic",
        "mathtext.bf": "Inter:bold",
        "text.color": INK,
        "axes.labelcolor": INK2,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 1.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 11,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.titlepad": 10,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2,
        "xtick.major.size": 3,
        "ytick.major.size": 0,
        "grid.color": GRID,
        "grid.linewidth": 1.0,
        "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round",
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def save(fig: plt.Figure, part: int, name: str) -> None:
    POST[part].mkdir(parents=True, exist_ok=True)
    fig.savefig(POST[part] / f"{name}.svg", bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    print(f"wrote {POST[part].name}/{name}.svg")
