"""Part 1: testing a difference in conversion rate and revenue per session."""
from __future__ import annotations

import numpy as np
from scipy import stats

from common import *


def two_arm_test_stats(x_a, x_b, alpha=0.05):
    """Welch's test for a difference in means; x_a and x_b hold one value per session."""
    n_a, n_b = len(x_a), len(x_b)
    diff = x_b.mean() - x_a.mean()
    se = np.sqrt(x_a.var(ddof=1) / n_a + x_b.var(ddof=1) / n_b)
    z = diff / se
    half = stats.norm.ppf(1 - alpha / 2) * se
    return {"diff": diff, "se": se, "z": z, "p": 2 * stats.norm.sf(abs(z)), "ci": (diff - half, diff + half)}


def relative_lift(x_a, x_b, alpha=0.05):
    """Lift mean_b / mean_a - 1 with a delta-method confidence interval."""
    m_a, m_b = x_a.mean(), x_b.mean()
    ratio = m_b / m_a
    se = ratio * np.sqrt(x_a.var(ddof=1) / (len(x_a) * m_a**2) + x_b.var(ddof=1) / (len(x_b) * m_b**2))
    half = stats.norm.ppf(1 - alpha / 2) * se
    return ratio - 1, (ratio - 1 - half, ratio - 1 + half)


data = two_arm_test()
rev_a, rev_b = data["A"], data["B"]
conv_a, conv_b = rev_a > 0, rev_b > 0
n_a, n_b = rev_a.size, rev_b.size
tests = {"cr": two_arm_test_stats(conv_a, conv_b), "rps": two_arm_test_stats(rev_a, rev_b)}
lifts = {"cr": relative_lift(conv_a, conv_b), "rps": relative_lift(rev_a, rev_b)}


def report() -> None:
    print("== data ==")
    for name, rev in data.items():
        orders = rev[rev > 0]
        print(
            f"{name}: sessions {rev.size:,}  orders {orders.size:,}  CR {orders.size / rev.size:.4%}  "
            f"RPS {rev.mean():.4f}  sd {rev.std(ddof=1):.3f}  AOV {orders.mean():.2f}  median order {np.median(orders):.2f}"
        )
    print(f"total {n_a + n_b:,}; split p-value (binomial) {stats.binomtest(n_a, n_a + n_b, 0.5).pvalue:.3f}")
    chi = (n_a - n_b) ** 2 / (n_a + n_b)
    print(f"split chi-square {chi:.3f}, p {stats.chi2.sf(chi, 1):.3f}")

    print("== tests ==")
    for kpi, t in tests.items():
        lift, ci = lifts[kpi]
        print(
            f"{kpi}: diff {t['diff']:.6f}  se {t['se']:.6f}  z {t['z']:.3f}  p {t['p']:.4f}  "
            f"ci ({t['ci'][0]:.6f}, {t['ci'][1]:.6f})  lift {lift:+.2%} ({ci[0]:+.2%}, {ci[1]:+.2%})"
        )
    p_a, p_b = conv_a.mean(), conv_b.mean()
    pooled = (conv_a.sum() + conv_b.sum()) / (n_a + n_b)
    z_pooled = (p_b - p_a) / np.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    print(f"cr pooled-variance z {z_pooled:.4f} (unpooled {tests['cr']['z']:.4f}), pooled p {pooled:.5f}")
    print(f"scipy welch rps: {stats.ttest_ind(rev_b, rev_a, equal_var=False)}")
    print(f"variances: cr {conv_a.var(ddof=1):.6f} {conv_b.var(ddof=1):.6f}  rps {rev_a.var(ddof=1):.2f} {rev_b.var(ddof=1):.2f}")
    skew = stats.skew(rev_a)
    print(f"skewness of revenue (A) {skew:.2f}; 355*skew^2 = {355 * skew**2:,.0f}")
    print(f"se / mean: cr {tests['cr']['se'] / p_a:.4%}  rps {tests['rps']['se'] / rev_a.mean():.4%}")
    print(f"share of A's revenue from top 1% of orders: {np.sort(rev_a)[-int(0.01 * conv_a.sum()):].sum() / rev_a.sum():.2%}")
    print(f"order value quantiles (A): 90% {np.quantile(rev_a[conv_a], 0.9):.0f}  99% {np.quantile(rev_a[conv_a], 0.99):.0f}  max {rev_a.max():.0f}")


def fig_revenue_per_session() -> None:
    orders = rev_a[conv_a]
    share = conv_a.mean()
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(7.2, 4.5), gridspec_kw={"height_ratios": [0.42, 3.2], "hspace": 0.5}
    )
    top.barh([0], [1 - share], color=GRAY_TINT, height=0.9)
    top.barh([0], [share], left=[1 - share], color=ORANGE, height=0.9)
    top.set_xlim(0, 1)
    top.set_ylim(-0.5, 0.5)
    top.axis("off")
    top.text(0.0, 0.85, f"{1 - share:.1%} of sessions end without a purchase: revenue $0", va="bottom", color=INK)
    top.text(1.0, 0.85, f"{share:.1%} place an order", va="bottom", ha="right", color=INK)

    cap = 600
    bins = np.arange(0, cap + 1, 12.5)
    bottom.hist(orders[orders <= cap], bins=bins, color=ORANGE, edgecolor="white", linewidth=0.6)
    mean, median = orders.mean(), np.median(orders)
    ymax = bottom.get_ylim()[1]
    for value, label, height in ((median, f"median ${median:.0f}", 1.19), (mean, f"mean ${mean:.0f}", 1.07)):
        bottom.plot([value, value], [0, ymax * height], color=INK, linewidth=1.2)
        bottom.text(value + 5, ymax * height, label, va="top", color=INK)
    bottom.set_ylim(0, ymax * 1.22)
    bottom.set_xlim(0, cap)
    bottom.set_title("Order values of the sessions that place an order")
    bottom.set_xlabel("Order value")
    bottom.xaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    bottom.set_ylabel("Orders")
    bottom.yaxis.grid(True)
    bottom.set_axisbelow(True)
    bottom.spines["left"].set_visible(False)
    bottom.text(
        0.99, 0.5, f"{(orders > cap).mean():.1%} of orders exceed ${cap}\nlargest: ${orders.max():,.0f}",
        transform=bottom.transAxes, ha="right", va="top", color=INK2,
    )
    save(fig, 1, "revenue-per-session")


def fig_null_distribution() -> None:
    xs = np.linspace(-4, 4, 801)
    pdf = stats.norm.pdf(xs)
    crit = stats.norm.ppf(0.975)
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.9), sharex=True, gridspec_kw={"hspace": 0.38})
    for ax, kpi, title in zip(axes, ("cr", "rps"), ("Conversion rate", "Revenue per session")):
        color, tint = KPI[kpi]
        z, p = tests[kpi]["z"], tests[kpi]["p"]
        ax.plot(xs, pdf, color=GRAY)
        ax.fill_between(xs, pdf, where=np.abs(xs) >= z, color=color, alpha=0.85, linewidth=0)
        for c in (-crit, crit):
            ax.plot([c, c], [0, 0.30], color=INK2, linewidth=1.0, linestyle=(0, (4, 3)))
            ax.text(c, 0.31, f"{c:.2f}".replace("-", "−"), ha="center", va="bottom", color=INK2, fontsize=9.5)
        ax.plot([z, z], [0, 0.44], color=INK, linewidth=1.4)
        ax.text(z, 0.455, f"observed z = {z:.2f}", ha="center", va="bottom", color=INK)
        ax.text(-3.95, 0.455, f"p = {p:.3f}, the shaded area", va="bottom", color=INK)
        ax.set_title(title)
        ax.set_ylim(0, 0.52)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
    axes[1].set_xlabel("z: difference in means divided by its standard error")
    axes[1].set_xlim(-4, 4)
    save(fig, 1, "null-distribution")


def resample_means(rng, orders, share, n, reps=20_000, chunk=2_000):
    """Sample mean and its estimated standard error for `reps` resamples of n sessions."""
    means, ses = [], []
    for _ in range(reps // chunk):
        counts = rng.binomial(n, share, chunk)
        draws = np.r_[rng.choice(orders, counts.sum()), 0.0]
        starts = np.r_[0, np.cumsum(counts)[:-1]]
        total, squares = np.add.reduceat(draws, starts), np.add.reduceat(draws**2, starts)
        total[counts == 0] = squares[counts == 0] = 0.0
        mean = total / n
        means.append(mean)
        ses.append(np.sqrt((squares - n * mean**2) / (n - 1) / n))
    return np.concatenate(means), np.concatenate(ses)


def fig_clt_check() -> None:
    """Null distribution of two statistics, by resampling arm A's sessions."""
    rng = np.random.default_rng(1)
    orders, share, mean = rev_a[conv_a], conv_a.mean(), rev_a.mean()
    sizes = (500, 5_000, n_a)
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.7), sharex=True, sharey=True, gridspec_kw={"wspace": 0.1, "hspace": 0.32})
    xs = np.linspace(-4, 4, 401)
    bins = np.linspace(-4, 4, 41)
    for col, n in enumerate(sizes):
        m1, se1 = resample_means(rng, orders, share, n)
        m2, se2 = resample_means(rng, orders, share, n)
        with np.errstate(divide="ignore", invalid="ignore"):
            one_arm = np.where(se1 > 0, (m1 - mean) / se1, -np.inf)
            two_arms = (m2 - m1) / np.sqrt(se1**2 + se2**2)
        for row, (z, label) in enumerate(((one_arm, "one arm"), (two_arms, "two arms"))):
            ax = axes[row, col]
            ax.hist(z, bins=bins, weights=np.full(z.size, 1 / (z.size * (bins[1] - bins[0]))), color=ORANGE_TINT, edgecolor="white", linewidth=0.5)
            ax.plot(xs, stats.norm.pdf(xs), color=INK, linewidth=1.4)
            lower, upper = np.mean(z < -1.96), np.mean(z > 1.96)
            ax.text(-3.9, 0.37, f"{lower:.1%}\nbelow −1.96", va="bottom", color=INK2, fontsize=9)
            ax.text(3.9, 0.37, f"{upper:.1%}\nabove 1.96", va="bottom", ha="right", color=INK2, fontsize=9)
            ax.set_xlim(-4, 4)
            ax.set_xticks([-2, 0, 2], ["−2", "0", "2"])
            ax.set_ylim(0, 0.52)
            ax.set_yticks([])
            ax.spines["left"].set_visible(False)
            print(f"clt n={n} {label}: below {lower:.4f}, above {upper:.4f}")
        axes[0, col].set_title(f"{n:,} sessions", loc="center", fontweight="normal")
    axes[0, 0].set_ylabel("One arm's mean", color=INK)
    axes[1, 0].set_ylabel("z for two arms", color=INK)
    axes[1, 1].set_xlabel("Standardized value")
    save(fig, 1, "clt-check")


def fig_lift_intervals() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 2.3))
    rows = (("cr", "Conversion rate", 1), ("rps", "Revenue per session", 0))
    ax.axvline(0, color=AXIS, linewidth=1.0)
    ax.axvline(5, color=INK2, linewidth=1.0, linestyle=(0, (4, 3)))
    ax.text(5, 1.62, "true lift, +5%", ha="center", va="bottom", color=INK2, fontsize=9.5)
    for kpi, label, y in rows:
        color, _ = KPI[kpi]
        lift, (lo, hi) = lifts[kpi]
        ax.plot([100 * lo, 100 * hi], [y, y], color=color, linewidth=2.0)
        ax.plot([100 * lift], [y], "o", color=color, markersize=8, markeredgecolor="white", markeredgewidth=2)
        ax.text(100 * hi + 0.25, y, f"{lift:+.1%}  [{lo:+.1%}, {hi:+.1%}]", va="center", color=INK)
    ax.set_yticks([y for _, _, y in rows], [label for _, label, _ in rows])
    ax.tick_params(axis="y", labelcolor=INK)
    ax.set_ylim(-0.6, 1.6)
    ax.set_xlim(-2.5, 12.5)
    ax.set_xlabel("Lift of B over A, with 95% confidence interval")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:+.0f}%" if v else "0%")
    ax.spines["left"].set_visible(False)
    save(fig, 1, "lift-intervals")


if __name__ == "__main__":
    report()
    fig_revenue_per_session()
    fig_null_distribution()
    fig_clt_check()
    fig_lift_intervals()
