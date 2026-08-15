# Q2 policy-mean exchangeability correction

## Problem

The formal Q2 workflow permuted six policy-level response means and called the resulting tail fraction an exact selection-adjusted p-value. Those means come from unequal battery counts and unequal within-policy variances, and the charging policies were not randomly assigned. The required exchangeability condition is therefore unavailable.

## Correction

- Retain the 720 label arrangements only as a hypothetical exchangeability sensitivity diagnostic.
- Remove `exact_p_one_sided` and replace it with `hypothetical_exchangeability_tail_fraction`.
- Add machine-readable fields declaring that the artifact is not a confirmatory test and that no confirmatory p-value is available.
- Remove the invalid p-value criterion from the formal model decision. The decision remains descriptive association only.
- Preserve the historical output filename for compatibility, while documenting that its semantics changed.

## Verification

- The 2000-repetition formal bootstrap was rerun with seed `20260814`.
- The diagnostic still enumerates all 720 label arrangements, and every summary row has `confirmatory_p_value_available=false`.
- Q2 formal tests verify that no `exact_p_one_sided` column is published.

## Boundary

The numerical tail fraction 0.065278 is retained for auditability but must not be compared with 0.05 or cited as a p-value. This change does not create a new confirmatory test; the current observational six-policy design does not support one without additional assumptions or data.
