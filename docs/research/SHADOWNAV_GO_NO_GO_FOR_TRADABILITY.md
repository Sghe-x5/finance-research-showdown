# ShadowNAV go/no-go memo for tradability

Decision: **STOP_SHADOWNAV**

Scope: stop advancing the current, preregistered ShadowNAV rule—an unshrunk transfer of an early lender’s exact-facility mark change into a later lender’s mark—as the leading candidate for a NAV/trading test.

## Evidence

Day 4 produced a promising but statistically inconclusive point estimate. Day 5’s official status is `data_quality_inconclusive`, so it cannot be treated as a confirmatory failure or success. The permitted post-reveal complete-case diagnostic nevertheless answers the engineering decision question adversely:

- SUPPORTING ShadowNAV MAE is about 52.9% worse than persistence.
- STRICT complete-case ShadowNAV MAE is about 124.9% worse, albeit with only 12 clusters.
- The paired-difference sign reverses Day 4 in both layers.
- The reversal persists after leaving out every borrower, every period, and every source-target fund pair.
- Six of seven SUPPORTING periods favor persistence.
- The two missing marks are operationally understandable zero-principal facilities, but fixing them cannot plausibly rescue the observed direction and would require a prospective outcome-definition change.

This meets the supplied `STOP_SHADOWNAV` condition: the Day 5 complete cases materially reverse Day 4 and indicate that the Day 4 benefit did not reproduce under the unchanged mechanism.

## What this does and does not mean

This is a decision about a **facility-mark predictive signal**. It is not evidence that no private-credit information reaches public BDC prices, and it is not a test of tradable equity alpha. No return series, trading cost, execution rule, NAV surprise, or equity-price reaction has been evaluated.

Accordingly, the current ShadowNAV formula should not advance to a NAV/trading test. A genuinely different future project—categorical distress transitions, zero-principal availability states, manager-specific marking behavior, or a prospectively preregistered shrunk transfer—would be a new hypothesis, not a repair or continuation of this experiment.

No profitability claim is made.
