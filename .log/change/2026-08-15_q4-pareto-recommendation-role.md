# Q4 Pareto recommendation role

- Problem: 5.0C was labeled a co-primary recommendation although 5.3C is faster and has lower point loss, so 5.0C is strictly dominated in the stated objective plane.
- Fix: keep 5.3C as the point-Pareto fast recommendation; retain 5.0C only as a non-Pareto uncertainty near-tie sensitivity because the paired bootstrap intervals cross zero.
- Outputs: add machine-readable `point_pareto` and distinct decision statuses; update integrity checks, report language, comparison roles, and figure styling.
