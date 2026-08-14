# Repository Guidelines

## Project Structure & Module Organization

This repository contains MATLAB work for the 2026 Celian Cup A problem on battery fast-charging and degradation. Keep official materials in `A题/` unchanged. Treat `data/raw/` as read-only; write cleaned datasets to `data/processed/`. Put reusable functions in `src/`, executable entry scripts in `scripts/`, and fixed parameters in `configs/`. Dataset checks belong in `tests/`. Generated experiment data goes under `outputs/raw/` or `outputs/summary/`, figures under `figures/`, and paper-ready material under `reports/`. Record supporting documentation in `docs/` and reproducibility notes in `environment/`.

## Build, Test, and Development Commands

Run commands from the repository root with MATLAB R2022b or newer:

```bash
matlab -batch 'run("scripts/plot_raw_figure1.m")'
matlab -batch 'run("scripts/run_a_data_pipeline.m")'
matlab -batch 'run("tests/test_a_data_pipeline.m")'
```

The first command regenerates the raw SOH figure without cleaning. The pipeline validates and enriches the CSV inputs, then writes processed tables, summaries, and figures. Run the pipeline before the tests because tests consume generated files in `data/processed/`.

## Coding Style & Naming Conventions

Follow the existing MATLAB style: four-space indentation, one primary function per `.m` file, `snake_case` filenames and function names, and descriptive `camelCase` local variables. Use string scalars (`"text"`) for paths and table labels, `fullfile` for portable paths, and `arguments` blocks for public function inputs. Prefer small reusable functions in `src/`; keep orchestration in `scripts/`. No automatic formatter or linter is configured, so match surrounding code and avoid unrelated reformatting.

## Testing Guidelines

Tests are assertion-based MATLAB scripts named `test_*.m`. Add checks for row counts, key uniqueness, required fields, train/test boundaries, and numeric tolerances when changing the pipeline. There is no stated coverage threshold; every behavioral change should include a focused regression assertion. Never make a test pass by editing official or raw input data.

## Commit & Pull Request Guidelines

Recent history uses short Conventional Commit-style subjects such as `chore: initialize ...` and `docs: record ...`. Continue with imperative subjects like `feat: add degradation metric` or `test: validate policy mapping`. Pull requests should explain the modeling or data-processing change, list validation commands, identify generated artifacts, and link the relevant issue. Include before/after figures when plot output changes, and confirm that `data/raw/` and official attachments remain untouched.
