# Q4 paper figures

## Scope

Added three paper-facing figures generated only from the frozen `q4_full_v4` artifacts. This change does not rerun models, bootstrap samples, or policy selection.

## Figures

- `fig_q4_pareto_uncertainty.png` shows all nine observed policies, whole-battery bootstrap intervals, a zoomed fast/low-loss panel, and the two-policy fast candidate set.
- `fig_q4_fast_pair_comparison.png` shows the 5.3C-minus-5.0C time and loss difference intervals against zero together with the decision probabilities and 0.95 threshold.
- `fig_q4_m1_validation.png` compares single-J ridge and constant-baseline RMSE for each held-out coordinate, making the 1/7 improvement count visible without generalizing beyond the tested model.

## Verification

- Figure generation completed from the authoritative CSV files.
- The Q4 figure integrity test verified PNG format, minimum dimensions, and nontrivial file size.
- All three figures were visually inspected; legends are outside the data region and the two fast-policy labels were separated to avoid overlap.

## Boundary

The error bars are strategy-mean whole-battery bootstrap intervals, not causal confidence intervals for C1, Q1, or C2. The M1 figure demonstrates failure of the tested single-J ridge proxy only.
