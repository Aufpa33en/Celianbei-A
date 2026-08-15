# Q2 global permutation boundary

- Problem: the merged late-rate permutation emitted `permutation_p` without stating that fixed protocol groups with unequal sizes and variances are not justified as exchangeable.
- Fix: rename the numerical output to `hypothetical_exchangeability_tail_fraction`, add diagnostic role, explicit assumption, and `confirmatory_p_value_available=False`.
- Paper boundary: `0.000050` is retained as a sensitivity diagnostic under the extra assumption, not as proof that at least one protocol distribution differs.
