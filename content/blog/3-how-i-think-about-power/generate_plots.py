from __future__ import annotations

import math
from pathlib import Path
from statistics import NormalDist

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTPUT_DIR = Path(__file__).parent
STANDARD_NORMAL = NormalDist()

BLACK = "#111111"
DARK = "#404040"
MID = "#6A6A6A"
LIGHT = "#C7C7C7"
FILL = "#DCDCDC"
POWER_FILL = "#AFAFAF"
RED = "#B00000"

plt.rcParams.update(
    {
        "svg.fonttype": "none",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.family": "DejaVu Serif",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def linspace(start: float, stop: float, count: int) -> list[float]:
    if count < 2:
        return [start]
    step = (stop - start) / (count - 1)
    return [start + step * index for index in range(count)]


def normal_pdf(xs: list[float], mean: float = 0.0, sd: float = 1.0) -> list[float]:
    coefficient = 1.0 / (sd * math.sqrt(2.0 * math.pi))
    return [coefficient * math.exp(-0.5 * ((x - mean) / sd) ** 2) for x in xs]


def one_sided_power(delta: float, sigma: float, n: float, alpha: float) -> float:
    z_alpha = STANDARD_NORMAL.inv_cdf(1.0 - alpha)
    noncentrality = delta * math.sqrt(n) / sigma
    return 1.0 - STANDARD_NORMAL.cdf(z_alpha - noncentrality)


def two_tailed_power(delta: float, sigma: float, n: float, alpha: float) -> float:
    z_half = STANDARD_NORMAL.inv_cdf(1.0 - alpha / 2.0)
    noncentrality = delta * math.sqrt(n) / sigma
    near_tail = 1.0 - STANDARD_NORMAL.cdf(z_half - noncentrality)
    far_tail = STANDARD_NORMAL.cdf(-z_half - noncentrality)
    return near_tail + far_tail


def style_axes(ax) -> None:
    ax.tick_params(colors=DARK)
    ax.spines["left"].set_color(DARK)
    ax.spines["bottom"].set_color(DARK)


def save_figure(fig: plt.Figure, filename: str) -> None:
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, bbox_inches="tight")
    plt.close(fig)


def plot_one_sided_geometry() -> None:
    z_alpha = STANDARD_NORMAL.inv_cdf(0.95)
    shift = 2.0
    xs = linspace(-4.0, 6.0, 900)
    null_y = normal_pdf(xs, mean=0.0)
    hp_y = normal_pdf(xs, mean=shift)

    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.plot(xs, null_y, color=BLACK, linewidth=2.0, label=r"$H_0$: $N(0, 1)$")
    ax.plot(
        xs,
        hp_y,
        color=MID,
        linewidth=2.3,
        linestyle="--",
        label=r"$H_P$: $N(\delta\sqrt{n}/\sigma, 1)$",
    )
    ax.fill_between(xs, hp_y, where=[x >= z_alpha for x in xs], color=POWER_FILL, alpha=0.9)
    ax.axvline(z_alpha, color=DARK, linewidth=1.4, linestyle=(0, (4, 3)))

    ax.text(0.0, max(null_y) + 0.03, 
        r"Null distribution"
        "\n"
        r"(centered at 0)", ha="center", color=BLACK)
    ax.text(
        shift + 1.0,
        max(hp_y) + 0.03,
        r"$H_P$ distribution"
        "\n"
        r"(centered at $\delta\sqrt{n}/\sigma$)",
        ha="center",
        color=DARK,
    )
    ax.text(
        (xs[0] + z_alpha) / 2.0,
        -0.10,
        r"Do not reject",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        color=DARK,
        clip_on=False,
    )
    ax.text(
        (z_alpha + xs[-1]) / 2.0,
        -0.10,
        r"Reject $H_0$",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        color=DARK,
        clip_on=False,
    )
    ax.text(
        z_alpha,
        -0.05,
        r"$z_{\alpha}$",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        color=DARK,
        clip_on=False,
    )
    ax.annotate(
        r"Power",
        xy=(2.5, 0.13),
        xytext=(3.7, 0.24),
        color=BLACK,
        arrowprops={"arrowstyle": "->", "color": BLACK, "lw": 1.2},
    )

    ax.set_xlim(xs[0], xs[-1])
    ax.set_ylim(0.0, 0.48)
    ax.set_xlabel(r"Standardized test statistic $z$", labelpad=20)
    ax.set_ylabel(r"Density")
    style_axes(ax)
    ax.legend(frameon=False, loc="upper left")
    save_figure(fig, "one-sided-power-geometry.svg")


def plot_two_tailed_geometry() -> None:
    z_half = STANDARD_NORMAL.inv_cdf(0.975)
    shift = 2.0
    xs = linspace(-5.0, 6.5, 1000)
    null_y = normal_pdf(xs, mean=0.0)
    hp_y = normal_pdf(xs, mean=shift)

    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.plot(xs, null_y, color=BLACK, linewidth=2.0, label=r"$H_0$: $N(0, 1)$")
    ax.plot(
        xs,
        hp_y,
        color=MID,
        linewidth=2.3,
        linestyle="--",
        label=r"$H_P$: $N(\delta\sqrt{n}/\sigma, 1)$",
    )
    ax.fill_between(xs, hp_y, where=[x <= -z_half for x in xs], color=FILL, alpha=0.9)
    ax.fill_between(xs, hp_y, where=[x >= z_half for x in xs], color=POWER_FILL, alpha=0.9)
    ax.axvline(-z_half, color=DARK, linewidth=1.4, linestyle=(0, (4, 3)))
    ax.axvline(z_half, color=DARK, linewidth=1.4, linestyle=(0, (4, 3)))

    ax.text(0.0, max(null_y) + 0.03, "Null distribution\n(centered at 0)", ha="center", color=BLACK)
    ax.text(
        shift + 1.6,
        max(hp_y) + 0.03,
        r"$H_P$ distribution"
        "\n"
        r"(centered at $\delta\sqrt{n}/\sigma$)",
        ha="center",
        color=DARK,
    )
    ax.text(
        -z_half,
        -0.085,
        r"$-z_{\alpha/2}$",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        color=DARK,
        clip_on=False,
    )
    ax.text(
        z_half,
        -0.085,
        r"$z_{\alpha/2}$",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        color=DARK,
        clip_on=False,
    )
    ax.annotate(
        "Far-tail power\n(negligible)",
        xy=(-2.2, 0.003),
        xytext=(-3.6, 0.11),
        ha="center",
        color=DARK,
        arrowprops={"arrowstyle": "->", "color": DARK, "lw": 1.2},
    )
    ax.annotate(
        "Near-tail power",
        xy=(2.7, 0.13),
        xytext=(3.9, 0.24),
        color=BLACK,
        arrowprops={"arrowstyle": "->", "color": BLACK, "lw": 1.2},
    )

    ax.set_xlim(xs[0], xs[-1])
    ax.set_ylim(0.0, 0.48)
    ax.set_xlabel(r"Standardized test statistic $z$", labelpad=20)
    ax.set_ylabel("Density")
    style_axes(ax)
    ax.legend(frameon=False, loc="upper left")
    save_figure(fig, "two-tailed-power-geometry.svg")


def plot_power_function() -> None:
    sigma = 15.0
    n = 36.0
    alpha = 0.05
    deltas = linspace(0.0, 10.0, 400)
    powers = [one_sided_power(delta, sigma, n, alpha) for delta in deltas]

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(deltas, powers, color=BLACK, linewidth=2.3)
    ax.axhline(alpha, color=MID, linewidth=1.4, linestyle=(0, (4, 3)))
    ax.scatter([0.0], [alpha], color=BLACK, s=30, zorder=3)
    ax.annotate(
        r"$\alpha$ when $\delta = 0$",
        xy=(0.005, alpha + 0.005),
        xytext=(1.5, 0.45),
        color=DARK,
        arrowprops={"arrowstyle": "->", "color": RED, "lw": 1.2},
    )
    ax.text(
        0.01,
        -0.17,
        r"Starts at $\alpha$ when $\mu_1 = \mu_0$; rises as the assumed effect size grows.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=DARK,
        clip_on=False,
    )

    ax.set_xlim(0.0, 10.0)
    ax.set_ylim(0.0, 1.02)
    ax.set_xlabel(r"Effect size $\delta = \mu_1 - \mu_0$ (mmHg)")
    ax.set_ylabel("Power")
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.set_yticks([0.0, 0.2, 0.5, 0.8, 1.0])
    style_axes(ax)
    save_figure(fig, "power-function.svg")


def plot_overlap_panel(ax, shift: float, title: str, note: str) -> None:
    z_alpha = STANDARD_NORMAL.inv_cdf(0.95)
    xs = linspace(-4.0, 6.5, 900)
    null_y = normal_pdf(xs, mean=0.0)
    hp_y = normal_pdf(xs, mean=shift)
    overlap_y = [min(y0, y1) for y0, y1 in zip(null_y, hp_y)]

    ax.plot(xs, null_y, color=BLACK, linewidth=2.0, label=r"$H_0$")
    ax.plot(xs, hp_y, color=MID, linewidth=2.3, linestyle="--", label=r"$H_P$")
    ax.fill_between(xs, overlap_y, color=FILL, alpha=0.95)
    ax.axvline(z_alpha, color=DARK, linewidth=1.4, linestyle=(0, (4, 3)))
    ax.text(0.0, max(null_y) + 0.02, r"$H_0$", ha="center", color=BLACK)
    ax.text(shift, max(hp_y) + 0.02, r"$H_P$", ha="center", color=DARK)
    ax.text(
        z_alpha,
        -0.08,
        r"$z_{\alpha}$",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        color=DARK,
        clip_on=False,
    )
    note_x = 0.80 if shift < 2.0 else 0.60
    note_y = 0.11 if shift < 2.0 else 0.08
    ax.text(note_x, note_y, note, ha="center", color=DARK)
    ax.set_title(title, loc="left", fontsize=11, color=BLACK, pad=8)
    ax.set_xlim(xs[0], xs[-1])
    ax.set_ylim(0.0, 0.46)
    ax.set_ylabel("Density")
    style_axes(ax)


def plot_overlap_comparison() -> None:
    delta = 5.0
    sigma = 15.0
    small_n = 16.0
    large_n = 100.0

    fig, axes = plt.subplots(2, 1, figsize=(7.4, 5.8), sharex=True, sharey=True)
    plot_overlap_panel(
        axes[0],
        delta * math.sqrt(small_n) / sigma,
        "Small n (n = 16): heavy overlap -> low power",
        "Overlap\nregion",
    )
    plot_overlap_panel(
        axes[1],
        delta * math.sqrt(large_n) / sigma,
        "Large n (n = 100): minimal overlap -> high power",
        "Minimal overlap",
    )
    axes[0].legend(frameon=False, loc="upper left")
    axes[1].set_xlabel(r"Standardized test statistic $z$", labelpad=20)
    save_figure(fig, "power-overlap-by-sample-size.svg")


def plot_power_vs_sample_size() -> None:
    delta = 5.0
    sigma = 15.0
    alpha = 0.05
    target_power = 0.80
    z_alpha = STANDARD_NORMAL.inv_cdf(1.0 - alpha)
    z_beta = STANDARD_NORMAL.inv_cdf(target_power)
    required_n = math.ceil(((z_alpha + z_beta) * sigma / delta) ** 2)
    n_values = list(range(0, 121))
    powers = [one_sided_power(delta, sigma, n, alpha) for n in n_values]
    required_power = one_sided_power(delta, sigma, required_n, alpha)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(n_values, powers, color=BLACK, linewidth=2.3)
    ax.axhline(alpha, color=LIGHT, linewidth=1.4, linestyle=(0, (2, 3)))
    ax.axhline(target_power, color=MID, linewidth=1.4, linestyle=(0, (4, 3)))
    ax.axvline(required_n, color=MID, linewidth=1.4, linestyle=(0, (4, 3)))
    ax.scatter([required_n], [required_power], color=BLACK, s=32, zorder=3)
    ax.text(118, alpha + 0.02, r"$\alpha$", ha="right", color=DARK)
    ax.text(118, target_power + 0.02, "Target power = 0.80", ha="right", color=DARK)
    ax.annotate(
        r"$n \approx 56$",
        xy=(required_n, required_power),
        xytext=(68, 0.62),
        color=BLACK,
        arrowprops={"arrowstyle": "->", "color": BLACK, "lw": 1.2},
    )

    ax.set_xlim(0, 120)
    ax.set_ylim(0.0, 1.02)
    ax.set_xlabel(r"Sample size $n$")
    ax.set_ylabel("Power")
    ax.set_yticks([0.0, 0.2, 0.5, 0.8, 1.0])
    style_axes(ax)
    save_figure(fig, "power-vs-sample-size.svg")


def main() -> None:
    plot_one_sided_geometry()
    plot_two_tailed_geometry()
    plot_power_function()
    plot_overlap_comparison()
    plot_power_vs_sample_size()

    for filename in [
        "one-sided-power-geometry.svg",
        "two-tailed-power-geometry.svg",
        "power-function.svg",
        "power-overlap-by-sample-size.svg",
        "power-vs-sample-size.svg",
    ]:
        print(f"wrote {OUTPUT_DIR / filename}")


if __name__ == "__main__":
    main()
