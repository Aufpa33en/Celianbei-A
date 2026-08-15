# Q4 charge-time metric contract

## Decision

Q4 now uses the per-battery `mean_chargetime` from `battery_summary_clean.csv` as its primary charge-time objective, matching Q1 and Q2. The mean of cycle-level charge times over the first 200 cycles remains available only as a coverage-window sensitivity metric.

## Reason

The two fields are not generally interchangeable. For the complete old-structure 4.8C policy, the policy means are 13.082 minutes from the summary field and 10.450 minutes from the first-200-cycle field. Using them as if they were the same metric made the cross-question interpretation inconsistent.

## Verification

- Q4 full validation was rerun with 5000 whole-battery bootstrap repetitions and seed `20260815`.
- All 13 integrity checks passed, including exact agreement between the Q4 primary time and the Q1/Q2 summary-time aggregation.
- The point Pareto set remained unchanged under the cycle-window sensitivity metric, but recommendation frequencies and paper-facing time values were regenerated rather than copied from the old run.
- The Q4 report and model-boundary documentation now state the primary and sensitivity roles explicitly.

## Boundary

This commit resolves the time-objective definition only. It does not validate the relative-SOH baseline, Q2 permutation inference, Q3 model selection, or the adequacy of the Q4 continuous candidate architecture.
