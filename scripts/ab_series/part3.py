"""Part 3: picking a winner among several groups with Hsu's MCB."""
from __future__ import annotations

import numpy as np
from mcb import (
    MCBResult,
    constrained_critical_value,
    constrained_mcb,
    pooled_mse_from_group_stats,
    print_result,
    summarize_from_means_ns_and_mse,
    unconstrained_edwards_hsu_critical_value,
)
from scipy import stats

from common import *

ALPHA = 0.05
GROUPS = list(FOUR_GROUP)
data = four_group_test()
ns = [data[a].size for a in GROUPS]
kpi_stats = {
    "cr": ([(data[a] > 0).mean() for a in GROUPS], [(data[a] > 0).var(ddof=1) for a in GROUPS]),
    "rps": ([data[a].mean() for a in GROUPS], [data[a].var(ddof=1) for a in GROUPS]),
}


def run_mcb(means, variances, sizes=ns, labels=GROUPS, alpha=ALPHA):
    summary = summarize_from_means_ns_and_mse(
        means=means, ns=sizes, mse=pooled_mse_from_group_stats(ns=sizes, variances=variances), labels=labels
    )
    return summary, constrained_mcb(summary, alpha=alpha)


results = {kpi: run_mcb(*kpi_stats[kpi]) for kpi in kpi_stats}


def balanced_d(k: int, alpha: float = ALPHA, nu: float = np.inf) -> float:
    return constrained_critical_value((1 / np.sqrt(2),) * (k - 1), nu, alpha)


# ----------------------------------------------------------------------------
# What goes wrong without a multiple-comparison method
# ----------------------------------------------------------------------------
def naive_error_rates(k: int, reps: int = 400_000, seed: int = 2):
    """All groups identical: P(some unadjusted two-sided 5% z-test rejects)."""
    z = np.random.default_rng(seed).standard_normal((reps, k))
    crit = stats.norm.ppf(1 - ALPHA / 2) * np.sqrt(2)
    versus_control = (np.abs(z[:, 1:] - z[:, :1]) > crit).any(axis=1).mean()
    all_pairs = (z.max(axis=1) - z.min(axis=1) > crit).mean()
    return versus_control, all_pairs


# ----------------------------------------------------------------------------
# Simultaneous coverage under the model and away from it
# ----------------------------------------------------------------------------
def covers(result, truth) -> bool:
    theta = [truth[i] - max(truth[:i] + truth[i + 1 :]) for i in range(len(truth))]
    return all(lo <= th <= hi for lo, th, hi in zip(result.lower, theta, result.upper))


def unpooled_mcb(means, variances, sizes, alpha=ALPHA):
    """MCB with Welch standard errors and a Bonferroni critical value: no equal-variance assumption."""
    means, se2 = np.asarray(means), np.asarray(variances) / np.asarray(sizes)
    k = means.size
    margin = stats.norm.ppf(1 - alpha / (k - 1)) * np.sqrt(se2[:, None] + se2[None, :])
    diff, others = means[:, None] - means[None, :], ~np.eye(k, dtype=bool)
    upper = np.maximum(0, np.where(others, diff + margin, np.inf).min(axis=1))
    lower = np.minimum(0, np.where(others & (upper > 0)[None, :], diff - margin, np.inf).min(axis=1))
    return MCBResult("unpooled", "", alpha, tuple(map(str, range(k))), (), tuple(lower), tuple(upper), {}, ())


def coverage_normal(mu, sigma, sizes, reps=20_000, seed=4, pooled=True):
    """Normal observations with per-group means mu, sds sigma and sample sizes."""
    rng = np.random.default_rng(seed)
    mu, sigma, sizes = map(np.asarray, (mu, sigma, sizes))
    hits = 0
    for _ in range(reps):
        means = rng.normal(mu, sigma / np.sqrt(sizes))
        variances = sigma**2 * rng.chisquare(sizes - 1) / (sizes - 1)
        result = run_mcb(means, variances, list(sizes))[1] if pooled else unpooled_mcb(means, variances, sizes)
        hits += covers(result, list(mu))
    return hits / reps


def coverage_store(rates, n, kpi, reps=20_000, seed=4):
    """The store's sessions: conversion rates per group, n sessions per group."""
    rng = np.random.default_rng(seed)
    truth = list(rates) if kpi == "cr" else [rps_moments(p)[0] for p in rates]
    hits = 0
    for _ in range(reps):
        groups = [group_stats(rng, n, p) for p in rates]
        if kpi == "cr":
            means, variances = [a[0] for a in groups], [a[0] * (1 - a[0]) * n / (n - 1) for a in groups]
        else:
            means, variances = [a[1] for a in groups], [a[2] for a in groups]
        hits += covers(run_mcb(means, variances, [n] * len(rates))[1], truth)
    return hits / reps


def outcome_frequencies(reps=3000, seed=77):
    """How often a test of this size leaves D alone on CR, and C and D on RPS."""
    rng = np.random.default_rng(seed)
    n, rates = int(np.mean(ns)), list(FOUR_GROUP.values())
    cr_d = rps_cd = 0
    for _ in range(reps):
        groups = [group_stats(rng, n, p) for p in rates]
        cr_d += run_mcb([a[0] for a in groups], [a[0] * (1 - a[0]) for a in groups], [n] * 4)[1].candidate_best_set == ("D",)
        rps_cd += run_mcb([a[1] for a in groups], [a[2] for a in groups], [n] * 4)[1].candidate_best_set == ("C", "D")
    return cr_d / reps, rps_cd / reps


def report() -> None:
    print("== data ==")
    for a in GROUPS:
        rev = data[a]
        print(
            f"{a}: sessions {rev.size:,}  orders {(rev > 0).sum():,}  CR {(rev > 0).mean():.4%}  RPS {rev.mean():.4f}  "
            f"sd {rev.std(ddof=1):.3f}  var {rev.var(ddof=1):.1f}  cr var {(rev > 0).var(ddof=1):.6f}"
        )
    print(f"total {sum(ns):,}; split chi-square p {stats.chisquare(ns).pvalue:.3f}")
    for kpi, (summary, result) in results.items():
        means, variances = kpi_stats[kpi]
        print(f"-- {kpi}: sigma_hat {summary.sigma_hat:.6f}  df {summary.df:,}  variance ratio max/min {max(variances) / min(variances):.4f}")
        print_result(result, digits=5)
        truth = list(FOUR_GROUP.values()) if kpi == "cr" else [rps_moments(p)[0] for p in FOUR_GROUP.values()]
        print(f"   all intervals contain the truth: {covers(result, truth)}")
        d = np.mean(list(result.critical_values.values()))
        w = d * summary.sigma_hat * np.sqrt(2 / np.mean(ns))
        lead = sorted(means)[-1] - sorted(means)[-2]
        print(f"   w = {w:.6f} ({w / means[0]:.2%} of A's mean); leader's margin {lead:.6f}; se of a difference {summary.sigma_hat * np.sqrt(2 / np.mean(ns)):.6f}")
        i, j = np.argsort(means)[-2:]
        unpooled = np.sqrt(variances[i] / ns[i] + variances[j] / ns[j])
        pooled = summary.sigma_hat * np.sqrt(1 / ns[i] + 1 / ns[j])
        print(f"   top pair se: pooled {pooled:.6f} unpooled {unpooled:.6f} ratio {pooled / unpooled:.4f}")
        # unadjusted pairwise z-tests, for contrast
        for x in range(4):
            for y in range(x + 1, 4):
                z = (means[y] - means[x]) / np.sqrt(variances[x] / ns[x] + variances[y] / ns[y])
                print(f"   z {GROUPS[y]}-{GROUPS[x]} {z:.2f} p {2 * stats.norm.sf(abs(z)):.4f}", end=";")
        print()

    print(f"in repeated tests: P(CR leaves D alone), P(RPS leaves C and D) = {outcome_frequencies()}")

    print("== critical values (nu = inf) ==")
    for k in range(2, 9):
        lam = (1 / np.sqrt(2),) * (k - 1)
        pairs = k * (k - 1) / 2
        print(
            f"k={k}: mcb d {balanced_d(k):.3f}  edwards-hsu {unconstrained_edwards_hsu_critical_value(lam, np.inf, ALPHA):.3f}  "
            f"tukey {stats.studentized_range.ppf(1 - ALPHA, k, 1e6) / np.sqrt(2):.3f}  "
            f"bonferroni all pairs {stats.norm.ppf(1 - ALPHA / (2 * pairs)):.3f}  naive {naive_error_rates(k)}"
        )
    d4 = balanced_d(4)
    print(f"sessions needed relative to MCB at k=4: tukey {(stats.studentized_range.ppf(0.95, 4, 1e6) / np.sqrt(2) / d4) ** 2:.3f}  bonferroni {(stats.norm.ppf(1 - 0.05 / 12) / d4) ** 2:.3f}")
    print(f"d at k=4, alpha .10: {balanced_d(4, 0.10):.3f}; alpha .025: {balanced_d(4, 0.025):.3f}")

    print("== simultaneous coverage, nominal 95% ==")
    rates = list(FOUR_GROUP.values())
    n = int(np.mean(ns))
    print(f"store truth, n {n:,}: cr {coverage_store(rates, n, 'cr', 4000):.4f}  rps {coverage_store(rates, n, 'rps', 4000):.4f}")
    worst = [0.030, 0.030, 0.030, 0.033]  # one group ahead, the rest tied: coverage is exactly 95% under the model
    print(f"normal, equal variance, one ahead: {coverage_normal([0, 0, 0, 1], [10] * 4, [5000] * 4):.4f}")
    print(f"store, one group +10%, n {n:,}: cr {coverage_store(worst, n, 'cr'):.4f}  rps {coverage_store(worst, n, 'rps'):.4f}")
    print(f"store, one group +10%, n 2,000: rps {coverage_store(worst, 2000, 'rps'):.4f}; n 20,000: {coverage_store(worst, 20000, 'rps'):.4f}")
    print(f"store, one group +50%, n {n:,}: rps {coverage_store([0.03, 0.03, 0.03, 0.045], n, 'rps'):.4f}")
    uneven = [70_000, 10_000, 10_000, 10_000]
    print(f"normal, equal variance, 70/10/10/10 split: {coverage_normal([0, 0, 0, 1], [10] * 4, uneven):.4f}")
    print(f"normal, best group sd x1.5, even split: {coverage_normal([0, 0, 0, 1], [10, 10, 10, 15], [25_000] * 4):.4f}")
    print(f"normal, best group sd x1.5, 70/10/10/10 split: {coverage_normal([0, 0, 0, 1], [10, 10, 10, 15], uneven):.4f}")
    print(f"normal, small groups sd x1.5, 70/10/10/10 split: {coverage_normal([0, 0, 0, 1], [10, 15, 15, 15], uneven):.4f}")
    print(f"normal, big group sd x1.5, 70/10/10/10 split: {coverage_normal([0, 0, 0, 1], [15, 10, 10, 10], uneven):.4f}")
    print(f"unpooled variant, critical value {stats.norm.ppf(1 - ALPHA / 3):.3f} (sessions x{(stats.norm.ppf(1 - ALPHA / 3) / balanced_d(4)) ** 2:.3f}):")
    print(f"   equal variance, even split: {coverage_normal([0, 0, 0, 1], [10] * 4, [25_000] * 4, pooled=False):.4f}")
    print(f"   best group sd x1.5, even split: {coverage_normal([0, 0, 0, 1], [10, 10, 10, 15], [25_000] * 4, pooled=False):.4f}")
    print(f"   best group sd x1.5, 70/10/10/10 split: {coverage_normal([0, 0, 0, 1], [10, 10, 10, 15], uneven, pooled=False):.4f}")
    print(f"   small groups sd x1.5, 70/10/10/10 split: {coverage_normal([0, 0, 0, 1], [10, 15, 15, 15], uneven, pooled=False):.4f}")
    lo, hi = unpooled_mcb(kpi_stats["rps"][0], kpi_stats["rps"][1], ns).lower, unpooled_mcb(kpi_stats["rps"][0], kpi_stats["rps"][1], ns).upper
    print(f"   this test, RPS: lower {np.round(lo, 3)} upper {np.round(hi, 3)}")


# ----------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------
def fig_naive_error_rate() -> None:
    ks = np.arange(2, 9)
    rates = np.array([naive_error_rates(k) for k in ks])
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    ax.axhline(ALPHA, color=INK, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.text(8.1, ALPHA, "the 5% each test\nwas run at", va="center", color=INK)
    for column, color, label in ((1, RED, "every pair of groups"), (0, INK2, "each redesign\nagainst A")):
        ax.plot(ks, rates[:, column], color=color)
        ax.plot(ks, rates[:, column], "o", color=color, markersize=8, markeredgecolor="white", markeredgewidth=2)
        ax.text(8.1, rates[-1, column], label, va="center", color=INK)
    for column in (0, 1):
        ax.text(4, rates[2, column] + 0.022, f"{rates[2, column]:.0%}", ha="center", va="bottom", color=INK)
    ax.set_xlim(1.7, 8.1)
    ax.set_ylim(0, 0.6)
    ax.set_xticks(ks)
    ax.set_xlabel("Number of groups, including the control")
    ax.set_ylabel("Chance of at least one\nfalse “significant” difference")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    save(fig, 3, "naive-error-rate")


def fig_theta() -> None:
    truth = {a: 100 * p for a, p in FOUR_GROUP.items()}
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for row, group in enumerate(reversed(GROUPS)):
        others = max(v for a, v in truth.items() if a != group)
        theta = truth[group] - others
        for a, v in truth.items():
            ax.plot([v], [row], "o", color=GRAY_TINT if a != group else INK, markersize=9, markeredgecolor="white", markeredgewidth=2, zorder=2)
        ax.plot([others], [row], "o", color=GRAY, markersize=9, markeredgecolor="white", markeredgewidth=2, zorder=2)
        ax.annotate(
            "", xy=(truth[group], row + 0.26), xytext=(others, row + 0.26),
            arrowprops={"arrowstyle": "-|>", "color": INK, "lw": 1.3, "shrinkA": 0, "shrinkB": 0},
        )
        ax.text((truth[group] + others) / 2, row + 0.34, f"{theta:+.2f}".replace("-", "−"), ha="center", va="bottom", color=INK)
        ax.text(3.385, row, f"$\\theta_{group}$ = {theta:+.2f} pp".replace("-", "−"), va="center", color=INK)
    for a, v in truth.items():
        ax.text(v, 3.78, a, ha="center", va="bottom", color=INK, fontweight="semibold")
    dot = lambda color, label: plt.Line2D([], [], marker="o", linestyle="", color=color, markersize=8, label=label)
    ax.legend(
        handles=[dot(INK, "the group"), dot(GRAY, "the best of the other groups")],
        loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=2, handletextpad=0.2, columnspacing=1.4,
    )
    ax.set_yticks(range(4), [f"group {a}" for a in reversed(GROUPS)])
    ax.tick_params(axis="y", labelcolor=INK)
    ax.set_ylim(-0.45, 4.1)
    ax.set_xlim(2.96, 3.37)
    ax.set_xticks([3.0, 3.1, 3.2, 3.3])
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.1f}%")
    ax.set_xlabel("True conversion rate")
    ax.spines["left"].set_visible(False)
    save(fig, 3, "theta")


def fig_means_and_intervals(kpi: str, name: str) -> None:
    color, tint = KPI[kpi]
    summary, result = results[kpi]
    means = np.array(summary.means)
    scale, unit = (100, " pp") if kpi == "cr" else (1, "")
    fmt = (lambda v: f"{v:.2f}%") if kpi == "cr" else (lambda v: f"${v:.2f}")
    d = np.mean(list(result.critical_values.values()))
    w = d * summary.sigma_hat * np.sqrt(2 / np.mean(ns)) * scale
    means_s, top = means * scale, means.max() * scale
    rows = np.arange(len(GROUPS))[::-1]
    keep = [a in result.candidate_best_set for a in GROUPS]

    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.3), sharey=True, gridspec_kw={"wspace": 0.12})
    left.axvspan(top - w, top, color=tint, alpha=0.45, linewidth=0)
    left.axvline(top - w, color=color, linewidth=1.2)
    for y, m, k in zip(rows, means_s, keep):
        left.plot([m], [y], "o", color=color if k else GRAY, markersize=9, markeredgecolor="white", markeredgewidth=2, zorder=3)
    left.annotate("", xy=(top - w, 3.6), xytext=(top, 3.6), arrowprops={"arrowstyle": "<|-|>", "color": INK, "lw": 1.1, "shrinkA": 0, "shrinkB": 0})
    left.text(top - w - 0.04 * (top - means_s.min()), 3.6, f"w = {w:.3f} pp" if kpi == "cr" else f"w = \\${w:.3f}", ha="right", va="center", color=INK)
    left.text(top - w / 2, -0.62, "kept", ha="center", va="top", color=INK2, fontsize=9.5)
    left.text((means_s.min() + top - w) / 2, -0.62, "ruled out", ha="center", va="top", color=INK2, fontsize=9.5)
    left.set_title("Sample means")
    left.set_yticks(rows, [f"{a}   {fmt(m)}" for a, m in zip(GROUPS, means_s)])
    left.tick_params(axis="y", labelcolor=INK)
    left.set_ylim(-0.95, 4.0)
    span = top - means_s.min()
    left.set_xlim(means_s.min() - 0.12 * span, top + 0.1 * span)
    left.xaxis.set_major_formatter(lambda v, _: fmt(v) if kpi == "rps" else f"{v:.1f}%")
    left.spines["left"].set_visible(False)

    lo, hi = np.array(result.lower) * scale, np.array(result.upper) * scale
    right.axvline(0, color=INK2, linewidth=1.0)
    for y, a, b, est, k in zip(rows, lo, hi, np.array(result.estimates) * scale, keep):
        c = color if k else GRAY
        right.plot([a, b], [y, y], color=c, linewidth=2.0)
        for end in (a, b):
            right.plot([end, end], [y - 0.11, y + 0.11], color=c, linewidth=2.0)
        right.plot([est], [y], "o", color=c, markersize=9, markeredgecolor="white", markeredgewidth=2, zorder=3)
        label = f"[{a:.3f}, {b:.3f}]".replace("-", "−").replace("0.000", "0")
        right.text((a + b) / 2, y - 0.22, label, ha="center", va="top", color=INK, fontsize=9.5,
                   bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0})
    right.set_title("MCB intervals for $\\theta_i$, in " + ("percentage points" if kpi == "cr" else "dollars"))
    reach = max(abs(lo.min()), hi.max())
    right.set_xlim(lo.min() - 0.08 * reach, hi.max() + 0.12 * reach)
    right.xaxis.set_major_formatter(lambda v, _: f"{v:.1f}".replace("-", "−") if abs(v) > 1e-9 else "0")
    right.spines["left"].set_visible(False)
    right.tick_params(axis="y", length=0)
    save(fig, 3, name)


def fig_critical_values() -> None:
    ks = np.arange(2, 9)
    lines = (
        ("Bonferroni, every pair", [stats.norm.ppf(1 - ALPHA / (k * (k - 1))) for k in ks], GRAY, 1),
        ("Tukey, every pair", [stats.studentized_range.ppf(1 - ALPHA, k, 1e6) / np.sqrt(2) for k in ks], INK2, -1),
        ("MCB", [balanced_d(k) for k in ks], INK, 0),
    )
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    for label, values, color, side in lines:
        ax.plot(ks, values, color=color, linewidth=2.6 if label == "MCB" else 1.8)
        ax.plot(ks, values, "o", color=color, markersize=8, markeredgecolor="white", markeredgewidth=2)
        ax.text(8.15, values[-1] + 0.045 * side, label, va="center", color=INK, fontweight="semibold" if label == "MCB" else "normal")
        ax.text(4, values[2] + (0.06 if side >= 0 else -0.06), f"{values[2]:.2f}", ha="center", va="bottom" if side >= 0 else "top", color=INK)
    ax.set_xlim(1.7, 8.1)
    ax.set_ylim(1.5, 3.4)
    ax.set_xticks(ks)
    ax.set_xlabel("Number of groups, including the control")
    ax.set_ylabel("Critical value: standard errors\nneeded to separate two groups")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    save(fig, 3, "critical-values")


if __name__ == "__main__":
    report()
    fig_naive_error_rate()
    fig_theta()
    fig_means_and_intervals("cr", "mcb-conversion-rate")
    fig_means_and_intervals("rps", "mcb-revenue-per-session")
    fig_critical_values()
