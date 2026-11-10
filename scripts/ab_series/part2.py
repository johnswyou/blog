"""Part 2: how long a two-group test should run."""
from __future__ import annotations

import numpy as np
from scipy import optimize, stats

from common import *

ALPHA, POWER, LIFT = 0.05, 0.80, 0.05
Z = stats.norm.ppf

# ----------------------------------------------------------------------------
# What the analyst knows before the test: 12 weeks of the current page
# ----------------------------------------------------------------------------
history = daily_sessions()[: HISTORY_WEEKS * 7]
weekly = history.reshape(HISTORY_WEEKS, 7).sum(axis=1)
WEEK_MEDIAN = float(np.median(weekly))
WEEK_SD = 1.4826 * float(np.median(np.abs(weekly - WEEK_MEDIAN)))


def traffic(weeks, quantile=0.10):
    """Forecast of total sessions over `weeks` weeks, at a quantile of its distribution."""
    weeks = np.asarray(weeks, dtype=float)
    return weeks * WEEK_MEDIAN + Z(quantile) * WEEK_SD * np.sqrt(weeks)


def baseline():
    """Conversion rate, mean and sd of revenue per session over the history window."""
    rng = np.random.default_rng(3)
    orders = [order_values(rng, rng.binomial(n, P_CONTROL)) for n in weekly]
    weekly_sd = [np.sqrt((np.square(o).sum() - n * (o.sum() / n) ** 2) / (n - 1)) for o, n in zip(orders, weekly)]
    all_orders, n = np.concatenate(orders), weekly.sum()
    mean = all_orders.sum() / n
    sd = np.sqrt((np.square(all_orders).sum() - n * mean**2) / (n - 1))
    fourth = (((all_orders - mean) ** 4).sum() + (n - all_orders.size) * mean**4) / n
    return all_orders.size / n, mean, sd, weekly_sd, all_orders, fourth / sd**4


# Planning values, rounded from the history (see report()).
P0, RPS0, SD0 = 0.030, 3.00, 24.3
VAR = {"cr": P0 * (1 - P0), "rps": SD0**2}
MEAN = {"cr": P0, "rps": RPS0}
# Kurtosis of one session's value: exact for the 0/1 purchase indicator, from the history for revenue.
KURTOSIS = {"cr": (1 - 3 * P0 * (1 - P0)) / (P0 * (1 - P0)), "rps": 490.0}


# ----------------------------------------------------------------------------
# Sample size, power, minimum detectable effect
# ----------------------------------------------------------------------------
def variances(kpi, lift):
    """Variance in A and in B when B's mean is (1 + lift) times A's."""
    if kpi == "cr":
        p_b = P0 * (1 + lift)
        return VAR["cr"], p_b * (1 - p_b)
    return VAR["rps"], VAR["rps"] * (1 + lift)  # variance moves with the mean


def sessions_per_group(kpi, lift, alpha=ALPHA, power=POWER, equal_var=False):
    var_a, var_b = variances(kpi, 0.0 if equal_var else lift)
    return (Z(1 - alpha / 2) + Z(power)) ** 2 * (var_a + var_b) / (lift * MEAN[kpi]) ** 2


def power_at(kpi, lift, n, alpha=ALPHA):
    var_a, var_b = variances(kpi, lift)
    shift = lift * MEAN[kpi] / np.sqrt((var_a + var_b) / n)
    crit = Z(1 - alpha / 2)
    return stats.norm.sf(crit - shift) + stats.norm.cdf(-crit - shift)


def mde(kpi, n, alpha=ALPHA, power=POWER):
    return optimize.brentq(lambda lift: sessions_per_group(kpi, lift, alpha, power) - n, 1e-4, 1.0)


def weeks_needed(total_sessions, quantile=0.10):
    weeks = 1
    while traffic(weeks, quantile) < total_sessions:
        weeks += 1
    return weeks


# ----------------------------------------------------------------------------
# Looking at the data more than once
# ----------------------------------------------------------------------------
def false_positive_rate(looks: int, reps: int = 400_000, seed: int = 5) -> float:
    """P(some look has |z| > 1.96) when A and B are identical and looks are evenly spaced."""
    rng = np.random.default_rng(seed)
    hit = np.zeros(reps, dtype=bool)
    total = np.zeros(reps)
    for look in range(1, looks + 1):
        total += rng.standard_normal(reps)
        hit |= np.abs(total) / np.sqrt(look) > Z(1 - ALPHA / 2)
    return hit.mean()


def two_look_rejection(z1, z2, drift=0.0):
    """P(|Z1| > z1 or |Z2| > z2) with looks at half and all of the data; drift = E[Z2]."""
    cov = [[1.0, np.sqrt(0.5)], [np.sqrt(0.5), 1.0]]
    mean = [drift * np.sqrt(0.5), drift]
    inside = stats.multivariate_normal(mean, cov).cdf([z1, z2], lower_limit=[-z1, -z2])
    return 1.0 - inside


def group_sequential():
    """O'Brien-Fleming and Pocock boundaries for one interim look at the halfway point."""
    out = {}
    for name, shape in (("obf", np.sqrt(2.0)), ("pocock", 1.0)):
        c = optimize.brentq(lambda c: two_look_rejection(shape * c, c) - ALPHA, 1.5, 3.0)
        drift = optimize.brentq(lambda d: two_look_rejection(shape * c, c, d) - POWER, 1.0, 5.0)
        out[name] = {"z1": shape * c, "z2": c, "inflation": (drift / (Z(1 - ALPHA / 2) + Z(POWER))) ** 2, "drift": drift}
    return out


def capped_cv2(cap_quantile: float) -> tuple[float, float]:
    """Cap order values at a quantile: (cap, squared CV of capped revenue per session)."""
    cap = np.exp(ORDER_MU + ORDER_SIGMA * Z(cap_quantile))
    below = lambda k: np.exp(k * ORDER_MU + k**2 * ORDER_SIGMA**2 / 2) * stats.norm.cdf(
        (np.log(cap) - ORDER_MU - k * ORDER_SIGMA**2) / ORDER_SIGMA
    )
    m1 = below(1) + cap * (1 - cap_quantile)
    m2 = below(2) + cap**2 * (1 - cap_quantile)
    return cap, (P0 * m2 - (P0 * m1) ** 2) / (P0 * m1) ** 2


def report() -> None:
    p_hat, mean, sd, weekly_sd, orders, kurt = baseline()
    print("== history ==")
    print("weekly sessions (k):", " ".join(f"{w / 1e3:.0f}" for w in weekly))
    print(f"daily mean {history.mean():,.0f}; weekday means {' '.join(f'{v / 1e3:.1f}k' for v in history.reshape(-1, 7).mean(0))}")
    print(f"weekly median {WEEK_MEDIAN:,.0f}  robust sd {WEEK_SD:,.0f} ({WEEK_SD / WEEK_MEDIAN:.1%})  plain sd {weekly.std(ddof=1):,.0f}")
    print(f"CR {p_hat:.4%}  RPS {mean:.4f}  sd {sd:.3f}  AOV {orders.mean():.2f}  order sd {orders.std(ddof=1):.2f}")
    print("weekly sd of revenue:", " ".join(f"{v:.1f}" for v in weekly_sd))
    print(f"kurtosis: revenue per session {kurt:.0f} (planning {KURTOSIS['rps']:.0f}); purchase indicator {KURTOSIS['cr']:.1f}")
    for w in (1, 2, 3, 4, 5, 6, 8):
        print(f"traffic {w}w: 10% {traffic(w):,.0f}  median {traffic(w, 0.5):,.0f}  90% {traffic(w, 0.9):,.0f}")
    actual = daily_sessions()
    print(f"actual: weeks 13-14 {actual[84:98].sum():,}; weeks 17-20 {actual[112:140].sum():,}")

    print("== sample size ==")
    zz = (Z(1 - ALPHA / 2) + Z(POWER)) ** 2
    print(f"(z_a/2 + z_b)^2 = {zz:.4f}; z {Z(1 - ALPHA / 2):.4f} {Z(POWER):.4f}")
    for kpi in ("cr", "rps"):
        n = sessions_per_group(kpi, LIFT)
        n_eq = sessions_per_group(kpi, LIFT, equal_var=True)
        va, vb = variances(kpi, LIFT)
        print(
            f"{kpi}: var_a {va:.5f} var_b {vb:.5f} delta {LIFT * MEAN[kpi]:.5f} cv {np.sqrt(VAR[kpi]) / MEAN[kpi]:.3f}  "
            f"n/group {n:,.0f} (equal-var {n_eq:,.0f}, ratio {n / n_eq:.4f})  total {2 * n:,.0f}  weeks {weeks_needed(2 * n)}"
            f"  (median traffic: {weeks_needed(2 * n, 0.5)})  days at median {2 * n / (WEEK_MEDIAN / 7):.1f}"
        )
    print(f"n ratio rps/cr {sessions_per_group('rps', LIFT) / sessions_per_group('cr', LIFT):.3f}; 1 + cv^2/(1-p) = {1 + ORDER_CV**2 / (1 - P0):.3f}")
    p_b = P0 * 1.05
    earlier = (Z(0.975) * np.sqrt(2 * P0 * (1 - P0)) + Z(0.8) * np.sqrt(P0 * (1 - P0) + p_b * (1 - p_b))) ** 2 / (P0 * 0.05) ** 2
    print(f"cr n by the earlier post's formula {earlier:,.0f}")

    print("== what a fixed duration buys ==")
    for w in (1, 2, 3, 4, 6, 8):
        n = traffic(w) / 2
        print(
            f"{w}w: n/group {n:,.0f}  mde cr {mde('cr', n):.2%} rps {mde('rps', n):.2%}  "
            f"power@5% cr {power_at('cr', LIFT, n):.1%} rps {power_at('rps', LIFT, n):.1%}"
        )
    n1 = 250_282  # sessions per group in the Part 1 test
    print(f"Part 1 test (n {n1:,}): power@5% cr {power_at('cr', LIFT, n1):.1%} rps {power_at('rps', LIFT, n1):.1%}")
    # P(CR significant and RPS not) is checked by simulation below.
    rng = np.random.default_rng(11)
    both = np.zeros((4000, 2), dtype=bool)
    for i in range(4000):
        a, b = group_stats(rng, n1, TWO_GROUP["A"]), group_stats(rng, n1, TWO_GROUP["B"])
        z_cr = (b[0] - a[0]) / np.sqrt((a[0] * (1 - a[0]) + b[0] * (1 - b[0])) / n1)
        z_rps = (b[1] - a[1]) / np.sqrt((a[2] + b[2]) / n1)
        both[i] = abs(z_cr) > 1.96, abs(z_rps) > 1.96
    print(
        f"simulated at truth: cr sig {both[:, 0].mean():.1%}  rps sig {both[:, 1].mean():.1%}  "
        f"cr sig & rps not {np.mean(both[:, 0] & ~both[:, 1]):.1%}  neither {np.mean(~both[:, 0] & ~both[:, 1]):.1%}"
    )

    print("== levers (multiplier on sessions needed) ==")
    for label, a, pw in (("alpha .10", 0.10, 0.80), ("power .70", 0.05, 0.70), ("power .90", 0.05, 0.90), ("alpha .10 power .70", 0.10, 0.70)):
        print(f"{label}: {(Z(1 - a / 2) + Z(pw)) ** 2 / zz:.3f}")
    for lift in (0.03, 0.07, 0.10):
        print(f"MDE {lift:.0%}: {sessions_per_group('rps', lift) / sessions_per_group('rps', LIFT):.3f}")
    cv2 = VAR["rps"] / RPS0**2
    for q in (0.99, 0.999):
        cap, cv2_capped = capped_cv2(q)
        print(f"cap orders at {q:.1%} quantile (${cap:,.0f}): {cv2_capped / (((P0 * AOV**2 * 2) - (P0 * AOV) ** 2) / (P0 * AOV) ** 2):.3f}")
    for share in (0.5, 0.7, 0.8, 0.9):
        print(f"split {share:.0%}/{1 - share:.0%}: {1 / (4 * share * (1 - share)):.3f}")

    print("== looking more than once ==")
    for looks in (1, 2, 4, 14, 28):
        print(f"{looks} looks: false positive rate {false_positive_rate(looks):.3f}")
    print(f"two looks, exact: {two_look_rejection(Z(0.975), Z(0.975)):.4f}")
    gs = group_sequential()
    for name, g in gs.items():
        print(f"{name}: z1 {g['z1']:.3f} z2 {g['z2']:.3f} inflation {g['inflation']:.4f}")
        for lift in (0.05, 0.075, 0.10):
            n = traffic(4) / 2
            var_a, var_b = variances("rps", lift)
            drift = lift * RPS0 / np.sqrt((var_a + var_b) / n)
            stop = stats.norm.sf(g["z1"] - drift * np.sqrt(0.5)) + stats.norm.cdf(-g["z1"] - drift * np.sqrt(0.5))
            print(f"   rps lift {lift:.1%}: P(stop at week 2) {stop:.1%}  overall power {two_look_rejection(g['z1'], g['z2'], drift):.1%}")


# ----------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------
def fig_traffic_history() -> None:
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(7.2, 4.9), gridspec_kw={"height_ratios": [1.25, 1], "hspace": 0.5})
    days = np.arange(history.size)
    promo = list(PROMO_DAYS)
    sale_week = PROMO_DAYS[0] // 7
    top.plot(days, history / 1e3, color=INK2, linewidth=1.4)
    for week in range(HISTORY_WEEKS + 1):
        top.axvline(week * 7 - 0.5, color=GRID, linewidth=1.0, zorder=0)
    top.plot(promo, history[promo] / 1e3, color=RED, linewidth=1.8)
    top.text(promo[-1] + 1.5, history[promo].max() / 1e3, "sale weekend", va="top", color=INK)
    top.set_title("Eligible sessions per day")
    top.set_xlim(-0.5, history.size - 0.5)
    top.set_ylim(25, 68)
    top.set_yticks([30, 40, 50, 60])
    top.set_xticks(np.arange(HISTORY_WEEKS) * 7 + 3, [f"{w}" for w in range(1, HISTORY_WEEKS + 1)])
    top.tick_params(axis="x", length=0)
    top.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}K")
    top.spines["left"].set_visible(False)

    weeks = np.arange(HISTORY_WEEKS) + 1
    bottom.axhline(WEEK_MEDIAN / 1e3, color=INK, linewidth=1.2, linestyle=(0, (4, 3)))
    bottom.text(HISTORY_WEEKS + 0.45, WEEK_MEDIAN / 1e3 + 4, f"median {WEEK_MEDIAN / 1e3:.0f}K", ha="right", va="bottom", color=INK)
    bottom.plot(weeks, weekly / 1e3, color=AXIS, linewidth=1.2, zorder=1)
    regular = weeks != sale_week + 1
    bottom.plot(weeks[regular], weekly[regular] / 1e3, "o", color=INK2, markersize=8, markeredgecolor="white", markeredgewidth=2)
    bottom.plot(weeks[~regular], weekly[~regular] / 1e3, "o", color=RED, markersize=8, markeredgecolor="white", markeredgewidth=2)
    bottom.set_title("Eligible sessions per week")
    bottom.set_xlim(0.5, HISTORY_WEEKS + 0.5)
    bottom.set_ylim(220, 330)
    bottom.set_yticks([225, 250, 275, 300, 325])
    bottom.set_xticks(weeks)
    bottom.tick_params(axis="x", length=0)
    bottom.set_xlabel("Week")
    bottom.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}K")
    bottom.yaxis.grid(True)
    bottom.set_axisbelow(True)
    bottom.spines["left"].set_visible(False)
    save(fig, 2, "traffic-history")


def fig_sessions_vs_mde() -> None:
    lifts = np.linspace(0.02, 0.12, 201)
    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    for kpi, label in (("rps", "Revenue per session"), ("cr", "Conversion rate")):
        color, _ = KPI[kpi]
        n = np.array([sessions_per_group(kpi, lift) for lift in lifts])
        ax.plot(100 * lifts, n, color=color)
        ax.text(100 * lifts[-1] + 0.15, n[-1], label, va="center", color=INK)
        n5 = sessions_per_group(kpi, LIFT)
        ax.plot([5], [n5], "o", color=color, markersize=8, markeredgecolor="white", markeredgewidth=2, zorder=3)
        ax.text(5.2, n5 * 1.06, f"{n5 / 1e3:,.0f}K", va="bottom", color=INK)
    ax.set_yscale("log")
    ax.set_xlim(2, 12)
    ax.set_ylim(3e4, 3e6)
    ax.set_yticks([5e4, 1e5, 2e5, 5e5, 1e6, 2e6], ["50K", "100K", "200K", "500K", "1M", "2M"])
    ax.minorticks_off()
    ax.set_xlabel("Minimum detectable effect, as a lift over A")
    ax.set_ylabel("Sessions needed per group")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    save(fig, 2, "sessions-vs-mde")


def fig_duration() -> None:
    weeks = np.arange(1, 7)
    forecast = traffic(weeks) / 1e3
    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    ax.plot(np.r_[0, weeks], np.r_[0, forecast], color=AXIS, linewidth=1.2, zorder=1)
    ax.plot(weeks, forecast, "o", color=INK2, markersize=8, markeredgecolor="white", markeredgewidth=2, zorder=2)
    ax.text(4.85, forecast[4] + 40, "sessions forecast by the end\nof each week (10th percentile)", ha="right", va="bottom", color=INK2)
    for kpi, label in (("cr", "Conversion rate"), ("rps", "Revenue per session")):
        color, _ = KPI[kpi]
        total = 2 * sessions_per_group(kpi, LIFT) / 1e3
        done = weeks_needed(total * 1e3)
        ax.axhline(total, color=color, linewidth=2.0, zorder=1)
        ax.text(6.25, total + 18, f"{label} needs {total:,.0f}K", ha="right", va="bottom", color=INK)
        ax.plot([done], [forecast[done - 1]], "o", color=color, markersize=10, markeredgecolor="white", markeredgewidth=2, zorder=3)
        ax.text(done - 0.12, forecast[done - 1] + 25, f"week {done}: {forecast[done - 1]:,.0f}K", ha="right", va="bottom", color=INK)
    ax.set_xlim(0, 6.3)
    ax.set_ylim(0, 1600)
    ax.set_xticks(range(7))
    ax.set_xlabel("Weeks since the test started")
    ax.set_ylabel("Cumulative eligible sessions")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}K" if v else "0")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    save(fig, 2, "duration")


def fig_power_at_two_weeks() -> None:
    n = traffic(2) / 2
    lifts = np.linspace(0.0, 0.10, 201)
    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    ax.axhline(POWER, color=INK2, linewidth=1.0, linestyle=(0, (4, 3)))
    ax.text(0.15, POWER + 0.015, "80% power", va="bottom", color=INK2)
    for kpi, label, dx in (("cr", "Conversion rate", -0.2), ("rps", "Revenue per session", 0.2)):
        color, _ = KPI[kpi]
        ax.plot(100 * lifts, [power_at(kpi, lift, n) for lift in lifts], color=color)
        at5 = power_at(kpi, LIFT, n)
        ax.plot([5], [at5], "o", color=color, markersize=8, markeredgecolor="white", markeredgewidth=2, zorder=3)
        ax.text(5 + dx, at5 + (0.03 if kpi == "cr" else -0.03), f"{at5:.0%}", ha="right" if dx < 0 else "left",
                va="bottom" if kpi == "cr" else "top", color=INK)
        reach = mde(kpi, n)
        ax.plot([100 * reach] * 2, [0, POWER], color=color, linewidth=1.2, linestyle=(0, (4, 3)))
        ax.text(100 * reach + 0.12, 0.03, f"{reach:.1%}", va="bottom", color=INK)
    ax.text(2.9, 0.66, "Conversion rate", ha="right", color=INK)
    ax.text(7.0, 0.70, "Revenue per session", ha="left", color=INK)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("True lift of B over A")
    ax.set_ylabel(f"Power with {n / 1e3:.0f}K sessions per group")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    save(fig, 2, "power-at-two-weeks")


def fig_peeking() -> None:
    looks = (1, 2, 4, 14, 28)
    labels = ("once,\nat the end", "twice", "weekly\nfor 4 weeks", "daily\nfor 2 weeks", "daily\nfor 4 weeks")
    rates = [false_positive_rate(k) for k in looks]
    fig, ax = plt.subplots(figsize=(7.2, 3.5))
    ax.bar(range(len(looks)), rates, width=0.32, color=[GRAY] + [RED] * 4)
    for x, rate in enumerate(rates):
        ax.text(x, rate + 0.006, f"{rate:.0%}", ha="center", va="bottom", color=INK)
    ax.axhline(ALPHA, color=INK, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.text(len(looks) - 0.72, ALPHA + 0.006, "α = 5%", va="bottom", color=INK)
    ax.set_xlim(-0.5, len(looks) - 0.2)
    ax.set_xticks(range(len(looks)), labels)
    ax.tick_params(axis="x", length=0, labelcolor=INK)
    ax.set_ylim(0, 0.32)
    ax.set_yticks([0, 0.1, 0.2, 0.3])
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_ylabel("Tests that declare a difference\nwhen there is none")
    ax.set_xlabel("How often the test is checked, stopping at the first p < 0.05")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    save(fig, 2, "peeking")


if __name__ == "__main__":
    report()
    fig_traffic_history()
    fig_sessions_vs_mde()
    fig_duration()
    fig_power_at_two_weeks()
    fig_peeking()
