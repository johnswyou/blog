"""Part 4: how long an A/B/n test should run."""
from __future__ import annotations

import numpy as np
from mcb import (
    constrained_mcb_correct_useful_probability,
    constrained_mcb_sample_size,
    unconstrained_mcb_edwards_hsu_sample_size,
)
from scipy import stats

from common import *
from part2 import KURTOSIS, MEAN, VAR, WEEK_MEDIAN, WEEK_SD, sessions_per_group, traffic, weeks_needed
from part3 import balanced_d, results, run_mcb

ALPHA, TARGET, K = 0.05, 0.90, 4
MARGIN = 0.05  # delta* as a fraction of A's mean
SPREAD = 0.10  # largest lift over A that a redesign could plausibly have
DELTA = {kpi: MARGIN * MEAN[kpi] for kpi in MEAN}


def sigma_noise(kpi, total_sessions):
    """Relative sd of the pooled sd estimate for data with this kurtosis: (1/2) sqrt((kurtosis - 1) / N)."""
    return 0.5 * np.sqrt((KURTOSIS[kpi] - 1) / total_sessions)


def upper_sigma(kpi):
    """A's sd raised to that of a page at the top lift, then by 1.645 sds of the noise in sigma_hat."""
    top = np.sqrt(VAR[kpi] * (1 + SPREAD))
    n0 = 2 * (balanced_d(K) * top / DELTA[kpi]) ** 2
    return top, top * (1 + stats.norm.ppf(0.95) * sigma_noise(kpi, K * n0))


# Planning sds as quoted in the post: upper_sigma() rounded (see report()).
SIGMA = {"cr": 0.1801, "rps": 25.95}


def plan(kpi, k=K, margin=MARGIN, alpha=ALPHA, target=TARGET):
    return constrained_mcb_sample_size(k=k, delta_star=margin * MEAN[kpi], sigma=SIGMA[kpi], alpha=alpha, target=target)


def known_sigma_n(kpi, k=K, margin=MARGIN, alpha=ALPHA, sigma=None):
    return 2 * (balanced_d(k, alpha) * (sigma or SIGMA[kpi]) / (margin * MEAN[kpi])) ** 2


def weeks_exact(total_sessions, quantile=0.10):
    """Weeks (not rounded) at which the traffic forecast reaches the total."""
    b = -stats.norm.ppf(quantile) * WEEK_SD
    return ((b + np.sqrt(b**2 + 4 * WEEK_MEDIAN * total_sessions)) / (2 * WEEK_MEDIAN)) ** 2


def ruled_out_curve(gap_over_delta, k=K, alpha=ALPHA):
    """P(a group this far below the best trails it by w or more) when w = delta*."""
    return stats.norm.cdf(balanced_d(k, alpha) * (np.asarray(gap_over_delta) - 1))


def true_moments(kpi, rates):
    if kpi == "cr":
        return np.array(rates), np.array([p * (1 - p) for p in rates])
    return np.array([rps_moments(p)[0] for p in rates]), np.array([rps_moments(p)[1] for p in rates])


def simulate(rates, n, kpi, reps, seed):
    """Repeat a store test: per-rep sample means, margin w and constrained MCB result."""
    rng = np.random.default_rng(seed)
    d = balanced_d(len(rates))
    for _ in range(reps):
        groups = [group_stats(rng, n, p) for p in rates]
        if kpi == "cr":
            means, variances = [a[0] for a in groups], [a[0] * (1 - a[0]) * n / (n - 1) for a in groups]
        else:
            means, variances = [a[1] for a in groups], [a[2] for a in groups]
        w = d * np.sqrt(np.mean(variances) * 2 / n)
        yield means, w, run_mcb(means, variances, [n] * len(rates), [str(i) for i in range(len(rates))])[1]


def check_plan(kpi, rates, n, reps=4000, seed=8):
    """Shares of simulated tests with: w < delta*; all intervals correct and w < delta*; both conclusions true."""
    truth, _ = true_moments(kpi, rates)
    theta = [t - max(np.delete(truth, i)) for i, t in enumerate(truth)]
    best, delta = truth.max(), DELTA[kpi]
    narrow = correct_useful = both = 0
    for means, w, result in simulate(rates, n, kpi, reps, seed):
        covered = all(lo <= th <= hi for lo, th, hi in zip(result.lower, theta, result.upper))
        win = int(np.argmax(means))
        near = result.lower[win] > -delta and truth[win] > best - delta
        ruled = all(result.upper[i] == 0 for i in range(len(rates)) if truth[i] < best - 2 * delta)
        narrow += w < delta
        correct_useful += covered and w < delta
        both += near and ruled
    return narrow / reps, correct_useful / reps, both / reps


def ruled_out_simulated(kpi, gaps, reps=3000, seed=21):
    """P(a group `gap` deltas below the best is ruled out), in store tests sized so that w = delta* on average."""
    step = MARGIN * P_CONTROL  # delta* on the conversion-rate scale; RPS scales with it
    top = P_CONTROL * (1 + SPREAD)
    out = []
    for gap in gaps:
        rates = [top - 4 * step, top - 4 * step, top - gap * step, top]
        sigma = np.sqrt(true_moments(kpi, rates)[1].mean())
        n = int(round(known_sigma_n(kpi, sigma=sigma)))
        out.append(np.mean([result.upper[2] == 0 for _, _, result in simulate(rates, n, kpi, reps, seed)]))
    return out


def report() -> None:
    d = balanced_d(K)
    print(f"d(k=4) = {d:.4f}; d(k=2) = {balanced_d(2):.4f}; Phi(d) = {stats.norm.cdf(d):.4f}")
    print("== planning sd ==")
    for kpi in ("cr", "rps"):
        top, upper = upper_sigma(kpi)
        n0 = known_sigma_n(kpi, sigma=top)
        print(
            f"{kpi}: A's sd {np.sqrt(VAR[kpi]):.5f}  top-lift sd {top:.5f}  noise in sigma_hat {sigma_noise(kpi, K * n0):.3%} "
            f"(normal theory {0.5 * np.sqrt(2 / (K * n0)):.3%})  upper sd {upper:.5f}  quoted {SIGMA[kpi]}"
        )
    print("== plan ==")
    for kpi in ("cr", "rps"):
        n, approx, two_group = plan(kpi), known_sigma_n(kpi), sessions_per_group(kpi, MARGIN)
        print(
            f"{kpi}: delta* {DELTA[kpi]:.5f}  n/group {n:,}  n0 {approx:,.0f}  total {K * n:,}  weeks {weeks_needed(K * n)} "
            f"(exact {weeks_exact(K * n):.2f})  | two-group total {2 * two_group:,.0f}; ratio {K * n / (2 * two_group):.3f}"
        )
        print(f"   targets 0.80/0.90/0.94: {plan(kpi, target=0.80):,} / {n:,} / {plan(kpi, target=0.94):,}")
        p_at = lambda m: constrained_mcb_correct_useful_probability(K, int(m), DELTA[kpi], SIGMA[kpi], ALPHA)
        print(f"   model probability at n0 {p_at(np.ceil(approx)):.3f}, at 0.99 n0 {p_at(0.99 * approx):.3f}, at 1.01 n0 {p_at(1.01 * approx):.3f}")
        eh = unconstrained_mcb_edwards_hsu_sample_size(K, DELTA[kpi], SIGMA[kpi], ALPHA, TARGET)
        print(f"   edwards-hsu n {eh:,} weeks {weeks_needed(K * eh)}")
    print("alloy example (k=8, delta*/sigma=5/3):", [round(constrained_mcb_correct_useful_probability(8, n, 5000, 3000, 0.05), 3) for n in range(2, 11)])

    print("== sensitivity (weeks at the 10th-percentile traffic forecast) ==")
    like = MARGIN / (1 + stats.norm.ppf(0.80) / d)
    for kpi in ("cr", "rps"):
        for margin in (0.025, like, 0.05, 0.075, 0.10):
            n = plan(kpi, margin=margin)
            print(f"{kpi} delta* {margin:.2%}: n/group {n:,} total {K * n:,} weeks {weeks_needed(K * n)}  vs two-group x{K * n / (2 * sessions_per_group(kpi, MARGIN)):.2f}")
        for k in (2, 3, 4, 5, 6, 8):
            n = plan(kpi, k=k)
            print(f"{kpi} k={k}: d {balanced_d(k):.3f} n/group {n:,} total {k * n:,} weeks {weeks_needed(k * n)} exact {weeks_exact(k * n):.2f}")
        n = plan(kpi, alpha=0.10, target=0.85)
        print(f"{kpi} alpha .10 (target .85): d {balanced_d(K, 0.10):.3f} n/group {n:,} total {K * n:,} weeks {weeks_needed(K * n)}")
        for weeks in (1, 2, 3, 4):
            w = d * SIGMA[kpi] * np.sqrt(2 / (traffic(weeks) / K))
            print(f"{kpi} after {weeks} weeks: n/group {traffic(weeks) / K:,.0f}  w = {w / MEAN[kpi]:.2%} of A's mean")

    print("== translation from power language ==")
    for power in (0.5, 0.8, 0.9):
        print(f"rule out a group g below the best with prob {power}: delta* = {1 / (1 + stats.norm.ppf(power) / d):.3f} g")
    print(f"curve at 0.5, 1, 1.5, 2 delta*: {ruled_out_curve([0.5, 1, 1.5, 2])}")

    print("== the Part 3 test, in hindsight ==")
    for kpi, (summary, result) in results.items():
        w = np.mean(list(result.critical_values.values())) * summary.sigma_hat * np.sqrt(2 / np.mean(summary.ns))
        print(f"{kpi}: sigma_hat {summary.sigma_hat:.5f} vs planning {SIGMA[kpi]}; w {w:.6f} vs delta* {DELTA[kpi]:.6f} ({w / DELTA[kpi]:.3f}); n/group {np.mean(summary.ns):,.0f} vs plan {plan(kpi):,}")

    print("== simulation checks: P(w < delta*), P(all correct and w < delta*), P(both conclusions) ==")
    top = P_CONTROL * (1 + SPREAD)
    for kpi in ("cr", "rps"):
        n = plan(kpi)
        print(f"{kpi} n {n:,}: part 3's pages {check_plan(kpi, list(FOUR_GROUP.values()), n)}")
        print(f"{kpi} n {n:,}: every page near the top lift, one slightly ahead {check_plan(kpi, [top, top, top, top * 1.002], n)}")
        central = int(round(known_sigma_n(kpi, sigma=np.sqrt(VAR[kpi] * (1 + SPREAD / 2)))))
        print(f"{kpi} n {central:,} (central sd, no cushion): part 3's pages {check_plan(kpi, list(FOUR_GROUP.values()), central)}")
        gaps = (0.5, 1.0, 1.5, 2.0, 2.5)
        print(f"   ruled-out probability at gaps {gaps}: sim {np.round(ruled_out_simulated(kpi, gaps), 3)} curve {np.round(ruled_out_curve(gaps), 3)}")


# ----------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------
ZONES = ((0, 1, "good enough", "#dfe9dc"), (1, 2, "gray zone", GRAY_TINT), (2, 3.2, "clearly worse", "#f3dcd9"))


def fig_zones() -> None:
    truth = {a: 100 * p for a, p in FOUR_GROUP.items()}
    best, delta = truth["D"], 100 * DELTA["cr"]
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    for lo, hi, label, color in ZONES:
        ax.axvspan(best - hi * delta, best - lo * delta, color=color, linewidth=0)
        ax.text(best - (lo + min(hi, 3.0)) / 2 * delta, 1.72, label, ha="center", va="center", color=INK, fontweight="semibold")
    notes = ("the group with the highest\nsample mean is in here", "may or may not\nbe ruled out", "ruled out")
    for (lo, hi, _, _), note in zip(ZONES, notes):
        ax.text(best - (lo + min(hi, 3.0)) / 2 * delta, 1.28, note, ha="center", va="center", color=INK2, fontsize=9.5)
    for group, value in truth.items():
        ax.plot([value], [0.45], "o", color=INK, markersize=9, markeredgecolor="white", markeredgewidth=2, zorder=3)
        ax.text(value, 0.72, group, ha="center", va="bottom", color=INK, fontweight="semibold")
    ticks = [best - 3 * delta, best - 2 * delta, best - delta, best]
    ax.set_xticks(ticks, [f"{t:.2f}%" for t in ticks])
    sec = ax.secondary_xaxis("top")
    sec.set_xticks(ticks[1:], ["best − 2δ*", "best − δ*", "best"])
    sec.tick_params(axis="x", length=0, labelcolor=INK)
    sec.spines["top"].set_visible(False)
    ax.set_xlim(best - 3.2 * delta, best + 0.12 * delta)
    ax.set_ylim(0, 2.0)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("True conversion rate")
    save(fig, 4, "zones")


def fig_ruled_out_probability() -> None:
    gaps = np.linspace(0, 3, 301)
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for lo, hi, label, color in ZONES:
        ax.axvspan(lo, min(hi, 3.0), color=color, linewidth=0)
        ax.text((lo + min(hi, 3.0)) / 2, 1.05, label, ha="center", va="bottom", color=INK, fontweight="semibold")
    ax.plot(gaps, ruled_out_curve(gaps), color=INK, label="$\\Phi(d\\,(g/\\delta^* - 1))$")
    sim_gaps = (0.5, 1.0, 1.5, 2.0, 2.5)
    for kpi, label, size in (("cr", "conversion rate", 12), ("rps", "revenue per session", 7)):
        color, _ = KPI[kpi]
        ax.plot(sim_gaps, ruled_out_simulated(kpi, sim_gaps), "o", color=color, markersize=size,
                markeredgecolor="white", markeredgewidth=1.5, zorder=3, label=f"simulated store tests, {label}")
    ax.legend(loc="lower left", handlelength=1.6)
    for g in (1, 2):
        p = float(ruled_out_curve(g))
        ax.text(g + 0.08, p - 0.03, f"{p:.0%}", ha="right", va="top", color=INK)
    ax.set_xlim(3, 0)
    ax.set_ylim(0, 1.0)
    ax.set_xticks([3, 2, 1, 0], ["3δ*", "2δ*", "δ*", "0"])
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("How far the group's true mean is below the best, $g$")
    ax.set_ylabel("Probability the group is ruled out")
    ax.spines["left"].set_visible(False)
    save(fig, 4, "ruled-out-probability")


def fig_probability_vs_n() -> None:
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.3), sharey=True, gridspec_kw={"wspace": 0.1})
    small = np.arange(2, 11)
    alloys = [constrained_mcb_correct_useful_probability(8, n, 5000, 3000, ALPHA) for n in small]
    left.plot(small, alloys, color=INK)
    left.plot(small, alloys, "o", color=INK, markersize=8, markeredgecolor="white", markeredgewidth=2)
    left.set_title("Hsu's example: 8 alloys", fontweight="normal")
    left.set_xlabel("Observations per group")
    left.set_xticks(small)
    approx = known_sigma_n("cr")
    grid = np.linspace(0.96 * approx, 1.04 * approx, 61).astype(int)
    color, _ = KPI["cr"]
    right.plot(grid / 1e3, [constrained_mcb_correct_useful_probability(K, int(n), DELTA["cr"], SIGMA["cr"], ALPHA) for n in grid], color=color)
    right.axvline(approx / 1e3, color=INK2, linewidth=1.0, linestyle=(0, (4, 3)))
    right.text(approx / 1e3 - 0.25, 0.86, "$n_0$", ha="right", va="top", color=INK)
    right.set_title("The store: 4 groups, conversion rate", fontweight="normal")
    right.set_xlabel("Sessions per group")
    right.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}K")
    for ax in (left, right):
        ax.axhline(1 - ALPHA, color=INK2, linewidth=1.0, linestyle=(0, (4, 3)))
        ax.set_ylim(0, 1.0)
        ax.yaxis.grid(True)
        ax.set_axisbelow(True)
        ax.spines["left"].set_visible(False)
    left.text(2.1, 1 - ALPHA + 0.012, "1 − α", va="bottom", color=INK2)
    left.set_ylabel("Probability of correct and useful\ninference under the normal model")
    left.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    save(fig, 4, "probability-vs-n")


def fig_duration_vs_groups() -> None:
    ks = np.arange(2, 9)
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for kpi, label in (("rps", "Revenue per session"), ("cr", "Conversion rate")):
        color, _ = KPI[kpi]
        weeks = np.array([weeks_exact(k * plan(kpi, k=int(k))) for k in ks])
        ax.plot(ks, weeks, color=color)
        ax.plot(ks, weeks, "o", color=color, markersize=8, markeredgecolor="white", markeredgewidth=2)
        ax.text(8.15, weeks[-1], label, va="center", color=INK)
        ax.text(4, weeks[2] + 0.35, f"{weeks[2]:.1f}", ha="center", va="bottom", color=INK)
        print(f"duration vs groups {kpi}: {np.round(weeks, 2)}")
    ax.set_xlim(1.7, 8.1)
    ax.set_ylim(0, 12)
    ax.set_xticks(ks)
    ax.set_yticks(range(0, 13, 2))
    ax.set_xlabel("Number of groups, including the control")
    ax.set_ylabel("Weeks of traffic needed")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    save(fig, 4, "duration-vs-groups")


if __name__ == "__main__":
    report()
    fig_zones()
    fig_ruled_out_probability()
    fig_probability_vs_n()
    fig_duration_vs_groups()
