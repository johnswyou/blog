+++
date = '2026-11-09T12:02:00-05:00'
draft = true
title = "A/B testing, part 3: picking a winner among several arms with Hsu's MCB"
categories = ['A/B testing']
+++

*This is part 3 of a four-part series on A/B testing in e-commerce. Parts [1](/blog/5-ab-testing-1-hypothesis-tests/) and [2](/blog/6-ab-testing-2-test-duration/) analyzed and planned a test with two arms. This post analyzes a test with four, and [part 4](/blog/8-ab-testing-4-abn-test-duration/) plans one.*

Parts 1 and 2 compared one redesigned product page with the current one. Design teams rarely have a single idea. Suppose this team had three candidate redesigns, B, C and D, and tested all of them against the current page A in one four-week test, with each session assigned to one of the four pages at random with equal probability. A test with more than two arms is called an A/B/n test.

The question is now which page is the best, on conversion rate (CR) and on revenue per session (RPS). This post explains why the two-arm test cannot answer it, presents a method that can (Hsu's multiple comparisons with the best), states what the method assumes, and applies it with the [`mcb`](https://github.com/johnswyou/mcb) Python package.

## The data

| Arm | Sessions | Orders | CR | RPS | SD |
| :--- | ---: | ---: | ---: | ---: | ---: |
| A (control) | 256,162 | 7,726 | 3.016% | $\\$2.997$ | $\\$24.24$ |
| B | 255,663 | 7,905 | 3.092% | $\\$3.051$ | $\\$24.25$ |
| C | 256,634 | 8,265 | 3.221% | $\\$3.213$ | $\\$25.82$ |
| D | 256,000 | 8,583 | 3.353% | $\\$3.320$ | $\\$25.74$ |

SD is the standard deviation of revenue per session. The four arm sizes are consistent with an even split (chi-square test, $p = 0.59$).

## Why the two-arm test does not extend

Four arms make six pairs. There are three common ways to handle them with familiar tools.

**Test every pair at $\alpha = 0.05$.** Each test rejects 5% of the time when its two arms are equal, so the chance that at least one of several tests rejects is higher.

![Chance of at least one false significant difference when all arms are identical and each comparison is an unadjusted test at 5%, for 2 to 8 arms. Comparing each redesign with A: 12% at four arms, 23% at eight. Comparing every pair of arms: 20% at four arms, 51% at eight.](naive-error-rate.svg)

With four identical pages, a store that tests each redesign against A finds a "significant" redesign 12% of the time, and one that tests all six pairs finds a "significant" difference 20% of the time. The probability that a procedure makes at least one false statement, among all the statements it makes, is its **familywise error rate**. A multiple-comparison method is a procedure that holds this rate at or below $\alpha$. Choosing the pair after seeing the data, for instance the leader against the runner-up, does not escape the problem, because the data picked that pair out of six.

**Test every pair with a correction.** Bonferroni's correction runs each of the six tests at level $\alpha/6$, and Tukey's method does the same job somewhat more efficiently. Both hold the familywise error rate at $\alpha$. Both also spend sessions on questions nobody asked: whether B differs from A is irrelevant when both are far behind D. Covering all six comparisons widens every interval, including the ones that matter. A later section measures the cost.

**Run an omnibus test.** The ANOVA F-test, or the chi-square test for conversions, tests the single hypothesis that all four pages are equal. Rejecting it says that some difference exists and nothing about which page is best.

## Comparing each arm with the best

Jason Hsu's observation is that choosing a winner needs only comparisons with the best arm. For each arm $i$ define

$$\theta_i = \mu_i - \max_{j \neq i} \mu_j,$$

the arm's true mean minus the largest true mean among the other arms.

![The four true conversion rates on an axis: A 3.00%, B 3.09%, C 3.21%, D 3.33%. One row per arm with an arrow from the best of the other arms to the arm. For A, B and C the best of the others is D and the arrows point left: theta is minus 0.33, minus 0.24 and minus 0.12 percentage points. For D the best of the others is C and the arrow points right: theta is plus 0.12.](theta.svg)

The figure uses the four pages' true conversion rates, which the simulation knows and an analyst never does. If $\theta_i \gt 0$, arm $i$ is the best and $\theta_i$ is its lead over the runner-up. If $\theta_i \lt 0$, arm $i$ is not the best and $-\theta_i$ is its distance below the best. At most one $\theta_i$ is positive.

**Multiple comparisons with the best (MCB)** produces one confidence interval per arm, for $\theta_i$. The intervals are **simultaneous**: the probability that all $k$ of them contain their true values at once is at least $1-\alpha$. Every statement read off the intervals is then covered by one familywise error rate of $\alpha$.

## The model

MCB is derived for the **one-way normal model**: the observations in arm $i$ are independent draws from a normal distribution with mean $\mu_i$ and a variance $\sigma^2$ that is the same in every arm. Larger means are better.

Part 1 gave each arm its own variance. Under this model there is one, estimated by the **pooled variance**

$$\hat\sigma^2 = \frac{1}{\nu}\sum_{i=1}^{k}(n_i - 1)s_i^2, \qquad \nu = \sum_{i=1}^{k}(n_i - 1),$$

where $n_i$ and $s_i^2$ are the size and sample variance of arm $i$ and $\nu$ is the degrees of freedom. Session data do not satisfy the model exactly. The section on assumptions examines how much that matters.

## The intervals

Take equal arm sizes $n$ first. The standard error of a difference between two sample means is $\hat\sigma\sqrt{2/n}$. MCB uses one margin for all arms,

$$w = d\hat\sigma\sqrt{2/n},$$

where $d$ is a critical value explained below (2.062 for four arms and $\alpha = 0.05$). The interval for $\theta_i$ runs from $D_i^-$ to $D_i^+$:

$$D_i^- = \min\left(0, \enspace \hat\mu_i - \max_{j \neq i}\hat\mu_j - w\right), \qquad D_i^+ = \max\left(0, \enspace \hat\mu_i - \max_{j \neq i}\hat\mu_j + w\right).$$

This is the estimate of $\theta_i$ plus and minus $w$, extended if necessary so that it contains 0. Because they always contain 0, these are called **constrained** MCB intervals. An interval has one of three shapes:

| Interval | Reading |
| :--- | :--- |
| $D_i^- \lt 0$ and $D_i^+ = 0$ | Arm $i$ is not the best. It is at most $-D_i^-$ below the best. |
| $D_i^- = 0$ and $D_i^+ \gt 0$ | Arm $i$ is the best. It leads the runner-up by at most $D_i^+$. |
| $D_i^- \lt 0 \lt D_i^+$ | Arm $i$ could be the best. It is at most $-D_i^-$ below the best of the others and at most $D_i^+$ above it. |

An arm whose upper bound is 0 is **ruled out**. The remaining arms form the candidate set $G = \lbrace i : D_i^+ \gt 0 \rbrace$, which contains the best arm with probability at least $1-\alpha$. From the formula, $D_i^+ = 0$ exactly when $\hat\mu_i \le \max_{j \neq i}\hat\mu_j - w$: an arm is ruled out when its sample mean trails the leader's by $w$ or more.

### Conversion rate

The pooled standard deviation of the 0/1 purchase indicator is $\hat\sigma = 0.1752$, and the arms average 256,115 sessions, so

$$w = 2.062 \times 0.1752 \times \sqrt{2/256{,}115} = 0.00101,$$

or 0.101 percentage points.

![Left: the four sample conversion rates, A 3.02%, B 3.09%, C 3.22%, D 3.35%, with a shaded band of width w equal to 0.101 percentage points behind the leader D. A, B and C lie outside the band and are ruled out. Right: the MCB intervals in percentage points. A: minus 0.438 to 0. B: minus 0.362 to 0. C: minus 0.233 to 0. D: 0 to 0.233.](mcb-conversion-rate.svg)

D leads C by 0.132 percentage points, which is more than $w$. With a familywise error rate of 5%: D is the best page for conversion, its lead over the runner-up is at most 0.233 points, and A is at most 0.438 points below it.

### Revenue per session

For revenue $\hat\sigma = \\$25.02$ and $w = \\$0.144$.

![Left: the four sample values of revenue per session, A 3.00 dollars, B 3.05, C 3.21, D 3.32, with a shaded band of width w equal to 0.144 dollars behind the leader D. C lies inside the band and is kept. A and B are ruled out. Right: the MCB intervals in dollars. A: minus 0.468 to 0. B: minus 0.414 to 0. C: minus 0.251 to 0.037. D: minus 0.037 to 0.251.](mcb-revenue-per-session.svg)

D leads C by $\\$0.107$, less than $w$, so the data cannot separate them. A and B are ruled out. The intervals still support a decision, because D's lower bound says that D is at most $\\$0.037$ below the best page. Shipping D gives up about 1% of RPS in the worst case.

As in part 1, the same sessions resolve CR more sharply than RPS.

## Where $d$ comes from and why the intervals hold

Suppose we knew which arm is truly the best, and call it $b$. Comparing every other arm with $b$ would be a classical problem, Dunnett's one-sided comparison of several treatments with a control, with $b$ playing the control. Its critical value $d$ is the number for which the event

$$E = \lbrace \hat\mu_b - \mu_b \gt \hat\mu_i - \mu_i - w \enspace \text{for all } i \neq b \rbrace$$

has probability exactly $1-\alpha$. In words: no arm's sample mean overshoots its true mean by $w$ or more beyond the overshoot of arm $b$. The value of $d$ depends on the number of arms $k$, on $\alpha$ and on $\nu$. For $k = 2$ it is the one-sided $t$ quantile, 1.645 when $\nu$ is large. For $k = 4$ it is 2.062.

MCB never learns which arm is $b$ and does not need to. Whenever $E$ occurs, every interval contains its $\theta_i$:

- **An arm $i \neq b$.** Here $\theta_i = \mu_i - \mu_b$. Rearranging $E$ gives $\mu_i - \mu_b \gt \hat\mu_i - \hat\mu_b - w$, and $\hat\mu_b \le \max_{j \neq i}\hat\mu_j$ because $b$ is one of the other arms. So $\theta_i \gt \hat\mu_i - \max_{j \neq i}\hat\mu_j - w \ge D_i^-$. The upper bound needs no data: $\theta_i \le 0 \le D_i^+$.
- **Arm $b$.** Let $m$ be the arm with the highest sample mean among the others. Rearranging $E$ gives $\mu_b - \mu_m \lt \hat\mu_b - \hat\mu_m + w$, and $\theta_b \le \mu_b - \mu_m$ by the definition of $\theta_b$. So $\theta_b \lt \hat\mu_b - \max_{j \neq b}\hat\mu_j + w \le D_b^+$. The lower bound needs no data: $\theta_b \ge 0 \ge D_b^-$.

Therefore all $k$ intervals contain their true values with probability at least $P(E) = 1 - \alpha$, whichever arm is the best. This is Theorem 4.1.1 of Hsu (1996). Two of the four bounds held without using the data, because the sign of $\theta_i$ is known once we know whether arm $i$ is the best. Building the intervals to contain 0 is what lets MCB skip paying for those bounds.

For two arms, MCB declares B the best when $\hat\mu_B - \hat\mu_A \gt 1.645 \cdot \text{SE}$, where part 1's two-sided test required 1.96. The two procedures control different errors. Part 1 limits the chance of declaring a difference when the pages are exactly equal. MCB limits the chance of a false statement about which arm is best or how far an arm is from the best, and when two arms are exactly equal, calling either one a best arm is not false. If exact ties are considered possible, read a lower bound of 0 as "one of the best" and an upper bound of 0 as "at most tied for the best".

## What comparing every pair costs

Tukey's and Bonferroni's intervals have the same form as MCB's: a difference of two sample means, plus or minus a critical value times its standard error. Only the critical value differs.

![Critical values for 2 to 8 arms at a familywise error rate of 5% with large samples. MCB rises from 1.64 at two arms to 2.06 at four and 2.34 at eight. Tukey's method for every pair rises from 1.96 to 2.57 at four arms and 3.03 at eight. Bonferroni's correction for every pair is slightly above Tukey's: 2.64 at four arms and 3.12 at eight.](critical-values.svg)

The margin is proportional to the critical value, and the sessions needed to reach a given margin are proportional to its square. With four arms, Tukey's method needs $(2.569/2.062)^2 = 1.55$ times the sessions MCB needs, and Bonferroni's needs 1.64 times. MCB's value is lower because it makes $k-1$ one-sided comparisons, each with the best arm, where the all-pairs methods make $k(k-1)/2$ two-sided ones.

## Unequal arm sizes

Real arms are never exactly equal in size, and some tests are deliberately uneven. Hsu's general formulas give each arm its own critical value $d^i$, Dunnett's value when arm $i$ is the control, and use the standard error of each pair, $s_{ij} = \hat\sigma\sqrt{1/n_i + 1/n_j}$:

$$D_i^+ = \max\left(0, \enspace \min_{j \neq i}\left(\hat\mu_i - \hat\mu_j + d^i s_{ij}\right)\right), \qquad G = \lbrace i : D_i^+ \gt 0 \rbrace,$$

$$D_i^- = \min_{j \in G, \thinspace j \neq i}\left(\hat\mu_i - \hat\mu_j - d^j s_{ij}\right), \quad \text{or } 0 \text{ if } G = \lbrace i \rbrace.$$

The `mcb` package implements these. In this test the four critical values agree to three decimals, and the results above are the general formulas' output.

## Assumptions

The guarantee is exact under the one-way normal model, at any sample size. Session data depart from the model on every count, so each assumption needs a check.

**Normality.** One session's revenue is nowhere near normal. With large arms the method needs less: approximately normal arm means, which part 1 verified at this sample size.

**Equal variances.** Part 2 showed that the variance of both KPIs rises with the mean, so pages with different means have different variances by construction. The sample variances of revenue per session are 587, 588, 667 and 662 for A to D, a ratio of 1.14 between the largest and the smallest. For the purchase indicator the ratio is 1.11. The pooled variance averages over all arms, and the comparison that decides the winner is between the top arms, which have the largest variances. The pooled standard error is therefore too small for the comparison that matters most. For D against C it is 1.7% smaller than Welch's for CR and 2.9% smaller for RPS.

**Independence.** Assignment is independent across sessions, as in part 1, and carryover is again the weak point. With four pages a returning shopper is more likely to meet two of them.

To see what the departures do, the table below reports how often all four intervals contain their true values in simulated tests with a nominal level of 95%. Each scenario has one arm ahead of three tied arms, the configuration in which the model's coverage is exactly 95%.

| Scenario | Simultaneous coverage |
| :--- | ---: |
| Normal data, equal variances, equal arm sizes | 95% |
| The store's RPS, 256K sessions per arm, best arm lifted 10% | 95% |
| The store's RPS, 2,000 sessions per arm (about 60 orders each) | 94% |
| The store's RPS, 256K sessions per arm, best arm lifted 50% | 94% |
| Normal data, best arm's SD 1.5 times the others', equal arm sizes | 93% |
| The same, with 70% of the traffic in one of the tied arms | 90% |

At the scale and effect sizes of this test, skewed revenue and a variance ratio near 1.1 cost nothing measurable. A lift of 50% makes the ratio 1.5 and costs about one point of coverage. A ratio of 2.25 costs two points with equal arms and five when 70% of the traffic sits in a low-variance arm. When the large arm is the high-variance one, the error runs the other way and the intervals are wider than they need to be.

In practice:

- Compare the per-arm sample variances before trusting the pooled one. With samples this large any formal test of equal variances rejects, so judge the ratio itself.
- Keep the arm sizes equal. Balance is the cheapest protection against unequal variances.
- If a redesign changes the spread of order values enough to push the ratio well past 1.5, do not pool. The proof above used the pooled variance only through the event $E$, and it goes through with a separate standard error for each pair. In the formulas for unequal arm sizes, use Welch's standard error from part 1, $s_{ij} = \sqrt{s_i^2/n_i + s_j^2/n_j}$, and replace every $d^i$ by $c$, the upper $\alpha/(k-1)$ quantile of the standard normal (2.128 for four arms). By Bonferroni's inequality $E$ still has probability at least $1-\alpha$ in large samples. The price is $(2.128/2.062)^2 = 1.065$, that is, 6.5% more sessions for the same margin. In the last two scenarios of the table this version covers 96% of the time. The `mcb` package does not include it. A short implementation is in this series' [`part3.py`](https://github.com/johnswyou/blog/tree/main/scripts/ab_series/part3.py).

Two further conditions concern the design. The arms, the KPI, $\alpha$ and the duration are fixed before the test, as in part 2. Dropping the weakest arm halfway and redirecting its traffic is a different, multi-stage procedure with different critical values. And MCB treats the control as one more candidate. If A is ruled out, as it is here, some redesign beats it. If changing the page carries a cost, so that the question becomes which redesigns beat A, the matching method is Dunnett's comparison with a control.

## Using the `mcb` package

Install it from GitHub. The package called `mcb` on PyPI is unrelated.

```bash
pip install git+https://github.com/johnswyou/mcb.git
```

The analysis needs three numbers per arm, all of which one `GROUP BY` query can return.

```python
from mcb import (
    constrained_mcb,
    pooled_mse_from_group_stats,
    print_result,
    summarize_from_means_ns_and_mse,
)

ns = [256_162, 255_663, 256_634, 256_000]  # sessions per arm
means = [2.9967, 3.0507, 3.2134, 3.3201]   # revenue per session
variances = [587.4, 588.0, 666.8, 662.4]   # sample variance of revenue per session

summary = summarize_from_means_ns_and_mse(
    means=means,
    ns=ns,
    mse=pooled_mse_from_group_stats(ns=ns, variances=variances),
    labels=["A", "B", "C", "D"],
)
result = constrained_mcb(summary, alpha=0.05)
print_result(result, digits=3)
```

```text
Hsu constrained MCB (unbalanced one-way)
Parameter: mu_i - max_{j != i} mu_j
Familywise alpha: 0.05
Candidate-best set: ('C', 'D')
Critical values:
  A: 2.062
  B: 2.062
  C: 2.062
  D: 2.062
Intervals:
  A                  estimate=-0.323  CI=[-0.468, 0.000]
  B                  estimate=-0.269  CI=[-0.414, 0.000]
  C                  estimate=-0.107  CI=[-0.251, 0.037]
  D                  estimate=0.107  CI=[-0.037, 0.251]
```

For conversion rate, pass the conversion rates as `means` and $\hat p_i(1-\hat p_i)$ as `variances`. With one value per session in memory, `summarize_from_samples({"A": revenue_a, "B": revenue_b, ...})` builds the summary directly. The result object exposes `candidate_best_set`, `lower` and `upper`. The package also implements the unconstrained intervals of Edwards and Hsu, which can state that an arm is at least some amount below the best, at the price of a larger critical value. Its [documentation](https://mcb.readthedocs.io/en/latest/) covers both.

## What the test found

On conversion, D is the best page. On revenue, A and B are ruled out and D is either the best or within $\\$0.037$ of it. The truth behind the simulation is that the redesigns lift conversion by 3%, 7% and 11% and leave order values unchanged, so D is the best page on both KPIs. All eight intervals contain their true values. In repeated simulations of this test, D is the only candidate on CR about 65% of the time, and C and D are the two candidates on RPS about 56% of the time.

The margin $w$ set what this test could resolve: 0.101 percentage points of CR and $\\$0.144$ of RPS after four weeks. [Part 4](/blog/8-ab-testing-4-abn-test-duration/) turns this around and asks how long an A/B/n test must run to reach a chosen margin.

## References

- Dunnett, C. W. (1955). A multiple comparison procedure for comparing several treatments with a control. *Journal of the American Statistical Association*, 50, 1096-1121.
- Edwards, D. G., & Hsu, J. C. (1983). Multiple comparisons with the best treatment. *Journal of the American Statistical Association*, 78, 965-971.
- Hsu, J. C. (1984). Constrained simultaneous confidence intervals for multiple comparisons with the best. *The Annals of Statistics*, 12, 1136-1144.
- Hsu, J. C. (1996). *Multiple Comparisons: Theory and Methods*. Chapman & Hall. Chapter 4 covers MCB.
