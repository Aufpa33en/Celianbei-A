# Q4 set-valued recommendation and model-scope correction

## Problem

The previous report promoted the 5.3C policy as the single fast tradeoff recommendation even though its time and loss intervals overlap those of the 5.0C policy. It also described failure of one single-exposure ridge model as rejection of continuous optimization in general. Finally, Q3's conditional trajectory predictor needed an explicit non-counterfactual boundary in the executable Q4 artifacts.

## Correction

- Compare the two practically fastest observed policies with paired bootstrap-replicate differences.
- Require both at least 0.95 pairwise loss-superiority probability and at least 0.95 probability of not being slower by more than 0.01 minute before issuing a unique fast recommendation; otherwise publish a candidate set.
- Publish `fast_pair_comparison.csv` with marginal intervals, difference intervals, Pareto frequencies, and superiority probabilities.
- Reclassify M1 as a failed single-J ridge proxy that does not activate continuous search; broader continuous model classes remain untested rather than disproved.
- Record that Q3 is not used as a new-policy counterfactual because such a policy has no observed 1-150-cycle individual trajectory.

## Verification

- Reran 5000 whole-battery bootstrap repetitions under `q4_full_v4`.
- The 5.3C-minus-5.0C time difference 95% interval is [-0.030139, 0.029179] minutes; the loss difference interval is [-0.001512, 0.001150].
- The probability that 5.3C has lower loss is 0.6228, below the 0.95 unique-recommendation threshold; both policies are retained as co-primary fast tradeoff candidates.
- All 16 integrity checks, the Q4 protocol test, and the authoritative manifest hash check passed.

## Boundary

The candidate set applies only to the nine observed policies and the current battery/experiment conditions. It is not a causal ranking of C1, Q1, or C2, and it does not validate an unseen continuous policy. The point-estimate Pareto front remains useful but must be reported together with bootstrap membership uncertainty.
