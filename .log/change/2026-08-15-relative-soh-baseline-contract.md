# Relative SOH baseline contract

## Decision

All downstream relative-SOH calculations now consume the Q1 cleaning contract: the median cleaned SOH over cycles 1--5, stored in `baseline_soh_cycles_1_5`, with the corresponding series in `SOH_relative_clean`.

## Root cause

Q1 cleaning used the first-five-cycle median, while Q2 and Q3 independently recomputed a first-five-cycle mean. Q4 inherited the Q3 definition. The maximum per-battery mean-minus-median discrepancy was about 0.00110 SOH, so the mismatch changed relative losses and model inputs.

## Verification

- The MATLAB cleaning test now verifies the stored median and every relative-SOH row; it passed.
- Q2 smoke, 2000-repetition formal bootstrap, 720 exact exposure permutations, and 20,000-permutation merged robustness analyses were rerun.
- Q3 completed all 40 outer LOBO folds, nested selection, 5000 bootstrap repetitions, ablation, and nine-battery final prediction in 908.461 seconds. The frozen algorithm still selected `C_ridge`, but its advantage over `D_ensemble` remained uncertain.
- Q4 was rerun with 5000 whole-battery bootstrap repetitions; all 13 integrity checks passed.
- Q2, Q3, and Q4 paper-facing values were updated where they depend on the relative baseline.
- Five Q2/Q3 paper figures were regenerated from the corrected outputs and visually checked for clipping, overlap, and legend placement.

## Boundary

This commit aligns the response definition only. It does not endorse the Q2 strategy-mean permutation test, the Q3 deployment-family rule, or the Q4 continuous-candidate architecture; those are separate review items.
