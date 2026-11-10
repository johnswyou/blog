+++
date = '2026-11-09T12:00:00-05:00'
draft = true
title = 'A/B testing, part 1: testing for a difference between two arms'
categories = ['A/B testing']
+++

*This is part 1 of a four-part series on A/B testing in e-commerce. Parts 1 and 2 cover a test with two arms: how to read its result (this post) and [how long to run it](/blog/6-ab-testing-2-test-duration/). Parts 3 and 4 cover a test with three or more arms: [how to pick a winner](/blog/7-ab-testing-3-abn-mcb/) and [how long to run it](/blog/8-ab-testing-4-abn-test-duration/).*

An online store has redesigned its product page. For two weeks, every session that reached a product page was randomly shown either the current page (arm A, the control) or the redesign (arm B, the treatment), each with probability one half. The test is over. Did the redesign change anything?

The answer depends on the metric. This post tests two:

- **Conversion rate (CR):** the share of sessions that end in a purchase.
- **Revenue per session (RPS):** revenue divided by the number of sessions.

A **session** is one visit: a run of activity with no pause longer than 30 minutes. The session, and not the shopper, is the unit of observation throughout this series, because many stores cannot follow a shopper from one visit to the next. Two sessions may belong to the same person and the store has no way to tell. The last section covers what this changes.

The data are simulated, with conversion rates and order values typical of e-commerce. That lets each conclusion be checked against the truth, which is revealed near the end.

## The data

| Arm | Sessions | Orders | CR | RPS | SD |
| :--- | ---: | ---: | ---: | ---: | ---: |
| A (control) | 250,115 | 7,522 | 3.007% | $\\$3.035$ | $\\$24.28$ |
| B (redesign) | 250,449 | 7,852 | 3.135% | $\\$3.138$ | $\\$24.18$ |

SD is the standard deviation of revenue per session. Each session produces one number, the revenue it brought in.

![Top: a bar showing that 97.0% of arm A's sessions end without a purchase and 3.0% place an order. Bottom: a histogram of the order values of that 3.0%, peaking near 40 dollars with a long right tail; the median order is 72 dollars and the mean is 101 dollars.](revenue-per-session.svg)

In statistical terms, revenue per session is *zero-inflated* (most values are exactly zero) and *right-skewed* (a few large orders pull the mean above the median). Both properties matter when we test RPS.

### Check the split first

Before comparing the arms, check that the randomization produced the split it was designed to produce. If each session is assigned by a fair coin, then

$$\chi^2 = \frac{(n_A - n_B)^2}{n_A + n_B} = \frac{334^2}{500{,}564} = 0.22$$

follows a chi-square distribution with one degree of freedom, which gives $p = 0.64$. The split looks healthy. A very small p-value here is called a *sample ratio mismatch*. It means one arm is losing or gaining sessions for a reason other than chance (a redirect that drops sessions, a bot filter that treats the pages differently), and the KPI comparison cannot be trusted until the cause is found.

## Both KPIs are means

Let $X_i$ be the revenue of session $i$, and let $C_i = 1$ if the session ended in a purchase and $C_i = 0$ if not. Then

$$\text{CR} = \frac{1}{n}\sum_{i=1}^{n} C_i, \qquad \text{RPS} = \frac{1}{n}\sum_{i=1}^{n} X_i.$$

CR is the mean of a 0/1 variable and RPS is the mean of a dollar amount. A test of either KPI is therefore a test of a difference between two means, and one procedure covers both.

## Testing a difference in means

For arm A, write $n_A$ for the number of sessions, $\mu_A$ and $\sigma_A^2$ for the true mean and variance of the per-session value, and $\bar X_A$ and $s_A^2$ for the sample mean and sample variance. Arm B is labeled the same way. The true mean is the value the sample mean would settle on if the arm received unlimited sessions.

The **null hypothesis** is that the redesign changes nothing, and the **alternative hypothesis** is its complement:

$$H_0: \mu_A = \mu_B, \qquad H_1: \mu_A \neq \mu_B.$$

We estimate $\mu_B - \mu_A$ by $\hat\Delta = \bar X_B - \bar X_A$. By the central limit theorem, a sample mean of many independent sessions is approximately normal, so

$$\hat\Delta \approx N\left(\mu_B - \mu_A, \enspace \frac{\sigma_A^2}{n_A} + \frac{\sigma_B^2}{n_B}\right).$$

Replacing the unknown variances by the sample variances gives the **standard error** and the **test statistic**:

$$\text{SE} = \sqrt{\frac{s_A^2}{n_A} + \frac{s_B^2}{n_B}}, \qquad z = \frac{\hat\Delta}{\text{SE}}.$$

If $H_0$ is true, $z$ is approximately standard normal. The **p-value** is the probability, computed under $H_0$, of a $z$ at least as far from zero as the one observed:

$$p = 2\left(1 - \Phi(\vert z \vert)\right),$$

where $\Phi$ is the standard normal distribution function. Before looking at the data we fix a **significance level** $\alpha = 0.05$, and we reject $H_0$ if $p \lt \alpha$, which is the same as $\vert z \vert \gt 1.96$. A test run this way rejects a true $H_0$ in 5% of experiments.

This is Welch's t-test. With hundreds of thousands of sessions per arm, its t distribution is indistinguishable from the normal.

The same quantities give a 95% **confidence interval** for $\mu_B - \mu_A$, namely $\hat\Delta \pm 1.96 \cdot \text{SE}$. The test rejects $H_0$ exactly when this interval excludes zero.

![Two panels, one per KPI, each showing the standard normal density that z follows under the null hypothesis, with dashed lines at plus and minus 1.96. For conversion rate the observed z is 2.62 and the two shaded tails beyond it have total area 0.009. For revenue per session the observed z is 1.50 and the shaded tails have total area 0.134.](null-distribution.svg)

## Conversion rate

The variance of a 0/1 variable is fixed by its mean: $\sigma^2 = p(1-p)$, where $p$ is the true conversion rate. The sample variance is $\hat p(1 - \hat p)$, with $\hat p$ the observed conversion rate. So

$$\text{SE} = \sqrt{\frac{0.03007 \times 0.96993}{250{,}115} + \frac{0.03135 \times 0.96865}{250{,}449}} = 0.000488,$$

$$z = \frac{0.03135 - 0.03007}{0.000488} = 2.62, \qquad p = 0.009.$$

We reject $H_0$: the conversion rates of the two pages differ.

Textbooks usually present this test with a single pooled variance $\hat p(1-\hat p)$, where $\hat p$ is the conversion rate of both arms combined. The reasoning is that under $H_0$ the two conversion rates are equal, and for a 0/1 variable equal means force equal variances. Here the pooled version also gives $z = 2.62$. Equal variances return in [part 3](/blog/7-ab-testing-3-abn-mcb/), where they are an assumption of the method and no longer a consequence of the null hypothesis.

## Revenue per session

For revenue, equal means do not imply equal variances. A redesign could leave RPS unchanged while making orders rarer and larger. Each arm therefore keeps its own variance estimate:

$$\text{SE} = \sqrt{\frac{24.28^2}{250{,}115} + \frac{24.18^2}{250{,}449}} = 0.0685,$$

$$z = \frac{3.138 - 3.035}{0.0685} = 1.50, \qquad p = 0.134.$$

We do not reject $H_0$.

### Is the normal approximation good enough?

The central limit theorem makes a sample mean approximately normal once $n$ is large, and how large depends on how skewed the data are. Revenue per session is very skewed: its skewness in arm A is 14.7, against 0 for a symmetric distribution. The figure resamples arm A's sessions to show two statistics at three sample sizes. The top row is the mean of one arm, standardized with its estimated standard error. The bottom row is the test's $z$ for two arms drawn from the same sessions, so that $H_0$ is true.

![Six histograms in two rows, each with a standard normal curve drawn over it. Top row, the standardized mean of one arm: with 500 sessions 10.6% of values fall below minus 1.96 and 0.3% above 1.96; with 5,000 sessions 4.5% and 1.2%; with 250,115 sessions 2.6% and 2.4%. Bottom row, the z statistic for two arms with no true difference: 2.2% and 2.2% with 500 sessions per arm, 2.4% and 2.5% with 5,000, 2.4% and 2.4% with 250,115.](clt-check.svg)

A normal distribution puts 2.5% in each tail. The mean of one arm is far from that with 500 sessions and close with 250,000. Its lower tail is the heavy one because a sample that happens to contain no large orders has both a low mean and a low estimated standard error. For a single mean, Kohavi et al. (2014) give a rule of thumb: with at least $355\gamma^2$ observations, where $\gamma$ is the skewness, both tail probabilities stay between 2% and 3%. Here that is $355 \times 14.7^2 \approx 77{,}000$ sessions.

The test needs far less. With equal arm sizes and no true difference, swapping the labels of the two arms flips the sign of $z$, so its distribution is symmetric at any sample size, and the skew of one mean cancels the skew of the other. Even 500 sessions per arm put about 2.2% in each tail. The cancellation depends on the even split. With a 90/10 split there is almost none, and the small arm has to meet the single-mean rule.

A rank test such as Mann-Whitney is sometimes proposed for skewed revenue. It tests whether sessions in one arm tend to rank above sessions in the other, which is a different hypothesis. The store is paid in means: revenue is RPS times the number of sessions.

## What the test says

| KPI | $\hat\Delta$ | 95% CI for $\mu_B - \mu_A$ | $z$ | $p$ |
| :--- | ---: | :---: | ---: | ---: |
| CR | 0.128 pp | 0.032 pp to 0.223 pp | 2.62 | 0.009 |
| RPS | $\\$0.103$ | $-\\$0.032$ to $\\$0.237$ | 1.50 | 0.134 |

(pp stands for percentage points.) To compare the two KPIs on one scale, express each difference as a lift, $\hat L = \bar X_B / \bar X_A - 1$. Its standard error follows from the delta method:

$$\text{SE}(\hat L) \approx \frac{\bar X_B}{\bar X_A}\sqrt{\frac{s_A^2}{n_A \bar X_A^2} + \frac{s_B^2}{n_B \bar X_B^2}}.$$

![Estimated lift of B over A with its 95% confidence interval. Conversion rate: plus 4.2%, interval from plus 1.0% to plus 7.5%. Revenue per session: plus 3.4%, interval from minus 1.1% to plus 7.9%. A dashed line marks the true lift of 5%, which both intervals contain.](lift-intervals.svg)

The redesign converts more sessions. For revenue the test is inconclusive: the interval contains zero, and it also contains lifts larger than anything in the CR interval. Failing to reject $H_0$ leaves both possibilities open.

The RPS interval is wider because RPS carries two sources of noise. It inherits the uncertainty in whether a session buys, which is all that CR has, and adds the uncertainty in how much a buyer spends. Relative to the mean, the standard error of $\hat\Delta$ is 1.6% for CR and 2.3% for RPS.

Since the data are simulated, we can look at the truth, marked by the dashed line. The redesign raises the conversion rate from 3.00% to 3.15% and leaves the distribution of order values unchanged, so the true lift is 5% in both KPIs. Both intervals contain it. The CR test detected the lift and the RPS test missed it.

Whether two weeks would be long enough to detect a lift in RPS is a question to settle before a test starts. [Part 2](/blog/6-ab-testing-2-test-duration/) settles it for this store: a two-week test detects a 5% lift in CR about 87% of the time and a 5% lift in RPS about 58% of the time.

## What follows from using sessions

The standard errors above remain valid when one shopper contributes several sessions. They rely on each session's arm being an independent coin flip, and the randomization guarantees that even when two sessions of the same shopper have similar outcomes.

What session-level randomization cannot rule out is carryover. A shopper who saw the redesign on Monday and buys on Wednesday in a session assigned to A is counted as a conversion for A. Carryover of this kind blurs the two arms, so the measured difference usually understates the difference the store would see after showing the redesign to everyone. Other kinds can work in the opposite direction, for example when the redesign only moves a purchase forward from a later session.

The p-values also assume that the two-week duration was fixed before the test began. Checking the results every day and stopping when $p$ dips below 0.05 rejects a true $H_0$ far more often than 5% of the time. Part 2 quantifies this.

## Code

```python
import numpy as np
from scipy import stats

def two_arm_test(x_a, x_b, alpha=0.05):
    """Welch's test for a difference in means. x_a, x_b: one value per session."""
    n_a, n_b = len(x_a), len(x_b)
    diff = x_b.mean() - x_a.mean()
    se = np.sqrt(x_a.var(ddof=1) / n_a + x_b.var(ddof=1) / n_b)
    z = diff / se
    p = 2 * stats.norm.sf(abs(z))
    half = stats.norm.ppf(1 - alpha / 2) * se
    return diff, (diff - half, diff + half), z, p

# revenue_a, revenue_b: revenue of each session, 0 where there was no purchase
two_arm_test(revenue_a > 0, revenue_b > 0)  # conversion rate
two_arm_test(revenue_a, revenue_b)          # revenue per session
```

`scipy.stats.ttest_ind(revenue_b, revenue_a, equal_var=False)` returns the same statistic and p-value. The simulation and the code for every figure in this series are in [`scripts/ab_series`](https://github.com/johnswyou/blog/tree/main/scripts/ab_series).

## References

- Kohavi, R., Deng, A., Longbotham, R., & Xu, Y. (2014). Seven rules of thumb for web site experimenters. *Proceedings of the 20th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 1857-1866.
- Kohavi, R., Tang, D., & Xu, Y. (2020). *Trustworthy Online Controlled Experiments: A Practical Guide to A/B Testing*. Cambridge University Press.
- Welch, B. L. (1947). The generalization of "Student's" problem when several different population variances are involved. *Biometrika*, 34(1-2), 28-35.
