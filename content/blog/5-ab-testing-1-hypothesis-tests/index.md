+++
date = '2026-11-09T12:00:00-05:00'
draft = true
title = 'A/B testing, part 1: testing for a difference between two groups'
categories = ['A/B testing']
+++

*This is part 1 of a four-part series on A/B testing in e-commerce. Parts 1 and 2 cover a test with two groups: how to determine the winner (this post) and [how long to run the A/B test](/blog/6-ab-testing-2-test-duration/). Parts 3 and 4 cover a test with three or more groups: [how to pick a winner](/blog/7-ab-testing-3-abn-mcb/) and [how long to run the test](/blog/8-ab-testing-4-abn-test-duration/).*

Suppose an online store has redesigned its product page. For two weeks, every session that reached a product page was randomly shown either the current page (group A, the control) or the redesign (group B, the treatment), each with probability one half. The test finishes. Did the redesign change anything? **This is the central question that this post will seek to answer**.

The answer depends on the metric. This post considers two:

- **Conversion rate (CR):** the share of sessions that end in a purchase.
- **Revenue per session (RPS):** revenue divided by the number of sessions.

A **session** is one visit: a period of activity with no pause longer than 30 minutes. The session is the unit of observation that we will consider throughout this series. 

> **Note**: We will not consider the user (or shopper) as the unit of observation. The topic of *identity resolution* - linking multiple sessions or events to the same underlying user - is beyond the scope of this series, and it will suffice to say that in practice, collecting anonymous session data is far easier than reliably tracking users across time. 

When the session is the unit of observation, multiple sessions may belong to the same person and there is no way to tell if this is the case. This is because each session is anonymous. Strictly speaking, sessions from the same person are not independent. However, by randomly routing traffic to either the control group or treatment group, we can still compare the two groups as if the sessions were independent. More on this in [Are sessions independent?](#are-sessions-independent).

The data are simulated, with conversion rates and order values typical of e-commerce. The advantage of simulating data is that we know the true underlying parameter values that define our data generating distributions, which means we can compare the statistical conclusions we draw to the truth.

## The data

| Group | Sessions | Orders | CR | RPS | SD |
| :--- | ---: | ---: | ---: | ---: | ---: |
| A (control) | 250,115 | 7,522 | 3.007% | \$3.035 | \$24.28 |
| B (redesign) | 250,449 | 7,852 | 3.135% | \$3.138 | \$24.18 |

SD is the standard deviation of revenue per session. Each session produces one number, the revenue it brought in.

> Let $X_i$ be the revenue of session $i$ (zero if the session ends without a purchase) and $n$ the number of sessions in the group. Then
>
> $$\text{SD} = \sqrt{\frac{1}{n-1}\sum_{i=1}^{n}\left(X_i - \text{RPS}\right)^2}.$$

Non-zero revenue values are called "order values". Shown below in orange is the observed distribution of order values.

![Top: a bar showing that 97.0% of group A's sessions end without a purchase and 3.0% place an order. Bottom: a histogram of the order values of that 3.0%, peaking near 40 dollars with a long right tail; the median order is 72 dollars and the mean is 101 dollars.](revenue-per-session.svg)

In statistical terms, revenue per session is *zero-inflated* (most values are exactly zero) and *right-skewed* (a few large orders pull the mean above the median). Both properties matter when conducting a hypothesis test, as we will see shortly.

### Preliminary check: Is traffic really being split randomly between groups?

Before comparing the groups, check that traffic really is being routed randomly to each group. If this is the case, then

$$\chi^2 = \frac{(n_A - n_B)^2}{n_A + n_B}$$

approximately follows a chi-square distribution with one degree of freedom.

> **Note**: The above formula assumes a 50/50 traffic split between the control and treatment group. If this is not the case, the general form of the formula is:
>
> $$\chi^2 = \frac{(n_A - rN)^2}{N r (1 - r)},$$
>
> where $N = n_A + n_B$ and $r$ is the share of traffic assigned to group A. Setting $r = 1/2$ recovers the formula above.

If your chi-square statistic takes a value in the upper 5 percentile tail of the chi-square distribution, then there is evidence against your traffic routing being truly random. A very small p-value here is called a *sample ratio mismatch*. It means one group is losing or gaining sessions for a reason other than chance (e.g., a redirect that drops sessions, a bot filter that treats the two groups differently), and the KPI comparison cannot be trusted until the cause is found. In our case, the split looks healthy:

$$\chi^2 = \frac{334^2}{500{,}564} = 0.22$$

which gives a p-value of $P\left(\chi^2_1 \gt 0.22\right)=0.64$, often simplified to just $p = 0.64$.

## Both KPIs are means

Let $X_i$ be the revenue of session $i$, and let $C_i = 1$ if the session ended in a purchase and $C_i = 0$ if not. Then

$$\text{CR} = \frac{1}{n}\sum_{i=1}^{n} C_i, \qquad \text{RPS} = \frac{1}{n}\sum_{i=1}^{n} X_i.$$

CR is the mean of a 0/1 variable and RPS is the mean of a dollar amount. A test of either KPI is therefore a test of a difference between two means, and one procedure covers both.

## Testing for a difference in means

For group A, write $n_A$ for the number of sessions, $\mu_A$ and $\sigma_A^2$ for the true mean and variance of the per-session value, and $\bar X_A$ and $s_A^2$ for the sample mean and sample variance. Group B is labeled the same way. The true mean is the value the sample mean would settle on if the group received unlimited sessions.

The **null hypothesis** is that the redesign changes nothing, and the **alternative hypothesis** is its complement:

$$H_0: \mu_A = \mu_B, \qquad H_1: \mu_A \neq \mu_B.$$

We estimate $\mu_B - \mu_A$ by $\hat\Delta = \bar X_B - \bar X_A$. By the central limit theorem, a sample mean of many independent sessions is approximately normal, so

$$\hat\Delta \approx N\left(\mu_B - \mu_A, \enspace \frac{\sigma_A^2}{n_A} + \frac{\sigma_B^2}{n_B}\right).$$

Replacing the unknown variances by the sample variances gives the **standard error** and the **test statistic**:

$$\text{SE} = \sqrt{\frac{s_A^2}{n_A} + \frac{s_B^2}{n_B}}, \qquad z = \frac{\hat\Delta}{\text{SE}}.$$

If $H_0$ is true, $z$ is approximately standard normal. The **p-value** is the probability, computed under $H_0$, of a $z$ at least as far from zero as the one observed:

$$p = 2\left(1 - \Phi(\vert z \vert)\right),$$

where $\Phi$ is the standard normal distribution function. Before looking at the data we fix a **significance level** $\alpha = 0.05$, and we reject $H_0$ if $p \lt \alpha$, which is the same as $\vert z \vert \gt 1.96$. A test run this way has a 5% probability of rejecting a true $H_0$.

The same quantities give a 95% **confidence interval** for $\mu_B - \mu_A$, namely $\hat\Delta \pm 1.96 \cdot \text{SE}$. The test rejects $H_0$ exactly when this interval excludes zero.

![Two panels, one per KPI, each showing the standard normal density that z follows under the null hypothesis, with dashed lines at plus and minus 1.96. For conversion rate the observed z is 2.62 and the two shaded tails beyond it have total area 0.009. For revenue per session the observed z is 1.50 and the shaded tails have total area 0.134.](null-distribution.svg)

## Conversion rate

The variance of a 0/1 variable is fixed by its mean: $\sigma^2 = p(1-p)$, where $p$ is the true conversion rate. The sample variance is $\hat p(1 - \hat p)$, with $\hat p$ the observed conversion rate. So

$$\text{SE} = \sqrt{\frac{0.03007 \times 0.96993}{250{,}115} + \frac{0.03135 \times 0.96865}{250{,}449}} = 0.000488,$$

$$z = \frac{0.03135 - 0.03007}{0.000488} = 2.62, \qquad p = 0.009.$$

We reject $H_0$: the conversion rates of the two pages differ.

> Textbooks usually present this test with a single pooled variance $\hat p(1-\hat p)$, where $\hat p$ is the conversion rate of both groups combined. The reasoning is that under $H_0$ the two conversion rates are equal, and for a 0/1 variable equal means force equal variances. Here the pooled version also gives $z = 2.62$.

## Revenue per session

For revenue, equal means do not imply equal variances. A redesign could leave RPS unchanged while making orders rarer and larger. Each group therefore keeps its own variance estimate:

$$\text{SE} = \sqrt{\frac{24.28^2}{250{,}115} + \frac{24.18^2}{250{,}449}} = 0.0685,$$

$$z = \frac{3.138 - 3.035}{0.0685} = 1.50, \qquad p = 0.134.$$

We do not reject $H_0$. It is plausible that the two groups (A and B) have the same true RPS.

### Is the normal approximation good enough?

The central limit theorem makes a sample mean approximately normal once $n$ is large, and how large depends on how skewed the data are. Revenue per session $X_i$ is very skewed: its skewness in group A is 14.7, against 0 for a symmetric distribution. 

Because the data are simulated, we can check this in a way that real data would not allow: draw fresh groups of sessions from the underlying data generating distribution, as many times as we like, and see how the statistics vary from one draw to the next. For a group size $n$:

1. Draw a group of $n$ sessions from the distribution that generated group A. Compute its standardized mean $(\bar X - \mu)/(s/\sqrt{n})$, where $\bar X$ and $s$ are the group's sample mean and standard deviation and $\mu$ is the true mean of the distribution.
2. Draw a second group of $n$ sessions from the same distribution and compute the test statistic $z$ for the pair. The two groups have the same true mean, so $H_0$ is true.

Repeating both steps 20,000 times gives 20,000 values of each statistic. The figure below shows their histograms for three values of $n$, with the standardized mean in the top row and $z$ in the bottom row. Where the normal approximation is good, a histogram matches the standard normal curve drawn over it.

![Six histograms in two rows, each with a standard normal curve drawn over it. Top row, the standardized mean of one group: with 50 sessions 34.6% of values fall below minus 1.96 and 0.0% above 1.96; with 500 sessions 11.2% and 0.3%; with 5,000 sessions 4.8% and 1.1%. Bottom row, the z statistic for two groups with no true difference: 0.4% and 0.3% with 50 sessions per group, where the histogram has spikes at minus 1 and plus 1; 2.2% and 2.3% with 500; 2.6% and 2.4% with 5,000.](clt-check.svg)

For a single mean, Kohavi et al. (2014) give a rule of thumb: with at least $355\gamma^2$ observations, where $\gamma$ is the skewness, both tail probabilities stay between 2% and 3%. Here that is $355 \times 14.7^2 \approx 77{,}000$ sessions. Group A has 250,115 sessions collected, which is more than enough.

> A rank test such as Mann-Whitney is sometimes proposed for skewed revenue. It tests whether sessions in one group tend to rank above sessions in the other, which is a different hypothesis.

## Is the redesign better?

| KPI | $\hat\Delta$ | 95% CI for $\mu_B - \mu_A$ | $z$ | $p$ |
| :--- | ---: | :---: | ---: | ---: |
| CR | 0.128 pp | 0.032 pp to 0.223 pp | 2.62 | 0.009 |
| RPS | \$0.103 | −<span>$</span>0.032 to <span>$</span>0.237 | 1.50 | 0.134 |

(pp stands for percentage points.) To compare the two KPIs on one scale, express each difference as a lift, $\hat L = \bar X_B / \bar X_A - 1$. Its standard error follows from the delta method:

$$\text{SE}(\hat L) \approx \frac{\bar X_B}{\bar X_A}\sqrt{\frac{s_A^2}{n_A \bar X_A^2} + \frac{s_B^2}{n_B \bar X_B^2}}.$$

![Estimated lift of B over A with its 95% confidence interval. Conversion rate: plus 4.2%, interval from plus 1.0% to plus 7.5%. Revenue per session: plus 3.4%, interval from minus 1.1% to plus 7.9%. A dashed line marks the true lift of 5%, which both intervals contain.](lift-intervals.svg)

The redesign converts more sessions. For revenue the test is inconclusive: the interval contains zero.

The RPS lift interval is wider because RPS carries two sources of uncertainty:

1. The uncertainty in whether a session will convert, which is the only uncertainty that CR has
2. In addition, the uncertainty in how much a buyer spends.

You can see that the confidence interval for RPS lift is noticeably wider than the confidence interval for CR lift.

Since the data are simulated, we can look at the truth, marked by the dashed line. The redesign (truly) raises the conversion rate from 3.00% to 3.15% and leaves the distribution of order values unchanged, so the true lift is 5% in both KPIs. Both intervals contain it. The CR test detected the lift while the RPS test missed it.

## Complexities that arise in practice

### Are sessions independent?

When a single shopper contributes several sessions, sessions are not independent. Some shoppers buy more often than others, so two sessions from the same shopper are correlated, no matter which group each one is routed to. However, random traffic routing picks the group (A or B) of each session without regard to other sessions, so a shopper with several sessions will usually have some in group A and some in group B. This means the variances of $\bar X_A$ and $\bar X_B$ are larger than $\sigma_A^2/n_A$ and $\sigma_B^2/n_B$, but the two sample means also move up and down together, because the same shoppers contribute to both. Under $H_0$, these two effects cancel exactly in the difference $\hat\Delta$. Its variance is still $\sigma_A^2/n_A + \sigma_B^2/n_B$, so the p-values above remain valid.

### Carryover
What session-level randomization cannot rule out is carryover. A shopper who saw the redesign on, say, Monday (meaning their session on Monday was randomly assigned to the treatment group B), but waits until Wednesday to make a purchase may get their Wednesday session assigned to the control group (group A). Here, the effect of the redesign was "felt" by the shopper in their Monday session, but their actual purchase two days later gives a conversion credit to the control group (the existing design). In this scenario, the control group is wrongly credited for a conversion caused by the treatment group from an earlier session tied to the same user. This is what we call the carryover effect (aka temporal spillover). Carryover of this kind can result in the treatment group's performance being overly pessimistic.

### Peeking
The p-values also assume that the two-week duration was fixed before the test began. Checking the results every day and stopping when $p$ dips below 0.05 rejects a true $H_0$ far more often than 5% of the time. Part 2 quantifies this.

See the following classic blog post by Evan Miller for a more detailed read on this topic: [How not to run an A/B test](https://www.evanmiller.org/how-not-to-run-an-ab-test.html)

## Conclusion

We started this post by asking whether a website redesign improves our KPI of interest. The steps we followed to answer this question apply to any A/B test with two groups and a KPI that takes the form of a mean over sessions:

1. Check that traffic was split randomly as planned (no sample ratio mismatch).
2. Write the KPI as the mean of a per session random variable, as we did for CR and RPS.
3. Compute $\hat\Delta$, its standard error (with a separate variance for each group), $z$ and the p-value. Reject $H_0$ if $p \lt \alpha$.
4. For a skewed KPI such as RPS, check that each group has enough sessions for the normal approximation to hold.
5. Report the confidence interval as well as the p-value. If the interval contains zero, the test is inconclusive: it remains plausible that the change did nothing to move our desired KPI and there is no significant evidence that the change moved the target KPI.

Carryover between a shopper's sessions can bias the comparison, and the p-values assume that the test's duration was fixed before it began. How to choose that duration is the subject of [part 2](/blog/6-ab-testing-2-test-duration/).

## Code

```python
import numpy as np
from scipy import stats

def two_group_test(x_a, x_b, alpha=0.05):
    """Welch's test for a difference in means. x_a, x_b: one value per session."""
    n_a, n_b = len(x_a), len(x_b)
    diff = x_b.mean() - x_a.mean()
    se = np.sqrt(x_a.var(ddof=1) / n_a + x_b.var(ddof=1) / n_b)
    z = diff / se
    p = 2 * stats.norm.sf(abs(z))
    half = stats.norm.ppf(1 - alpha / 2) * se
    return diff, (diff - half, diff + half), z, p

# revenue_a, revenue_b: revenue of each session, 0 where there was no purchase
two_group_test(revenue_a > 0, revenue_b > 0)  # conversion rate
two_group_test(revenue_a, revenue_b)          # revenue per session
```

`scipy.stats.ttest_ind(revenue_b, revenue_a, equal_var=False)` returns the same statistic and p-value. The simulation and the code for every figure in this series are in [`scripts/ab_series`](https://github.com/johnswyou/blog/tree/main/scripts/ab_series).

## References

- Kohavi, R., Deng, A., Longbotham, R., & Xu, Y. (2014). Seven rules of thumb for web site experimenters. *Proceedings of the 20th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 1857-1866.
- Kohavi, R., Tang, D., & Xu, Y. (2020). *Trustworthy Online Controlled Experiments: A Practical Guide to A/B Testing*. Cambridge University Press.
- Welch, B. L. (1947). The generalization of "Student's" problem when several different population variances are involved. *Biometrika*, 34(1-2), 28-35.
