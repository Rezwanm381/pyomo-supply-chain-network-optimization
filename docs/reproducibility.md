# Reproducibility

## Environment

The validated environment uses Python 3.12 with:

- Pyomo 6.10.1;
- HiGHS 1.15.1 through the `highspy` package and Pyomo's `appsi_highs` interface;
- pandas 3.0.1 and NumPy 2.3.5;
- SciPy 1.18.1 for the separate transportation formulation; the checked-in Pyomo and SciPy paths share HiGHS;
- Matplotlib 3.11.1 for figures;
- pytest 9.1.1 for tests.

Exact project dependencies are listed in `requirements.txt`.

## Installation

From the repository candidate root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

The workflow requires a working `appsi_highs` solver interface. The pinned `highspy` package supplies HiGHS in the validated environment.

## One-command analysis

Run the complete analysis from the repository candidate root:

```powershell
python run_analysis.py
```

The command:

1. loads and validates the synthetic scenario data;
2. builds the Pyomo MILP;
3. checks solver availability and solves the base case;
4. independently validates feasibility, domains, and objective arithmetic;
5. computes the defined all-facilities-open reference scenario;
6. enumerates all 64 facility subsets;
7. runs the declared sensitivity cases and controlled infeasibility check;
8. runs the tiny known-answer case;
9. writes tables, structured results, reports, and four figures.

The workflow does not depend on notebook state.

## Tests

Run the validated 30-test suite:

```powershell
python -m pytest -q
```

The suite covers data schemas and derived costs, model structure, solver behavior, solution arithmetic, enumeration, the tiny known case, sensitivities, infeasibility handling, and generated artifacts.

## Notebooks

The notebooks are presentation layers over the reusable modules:

- `notebooks/01_network_overview.ipynb`
- `notebooks/02_optimization_analysis.ipynb`

They can be executed top-to-bottom after installing the requirements. They do not contain a duplicate model implementation and are not required by `run_analysis.py`.

## Output locations

The default output root is an ignored local directory at:

```text
.private_outputs/module_7_25C/
```

It contains:

- JSON solver, validation, and summary files directly in the output root;
- `tables/` for decision, shipment, baseline, enumeration, sensitivity, and validation CSV files;
- `figures/` for the four PNG figures;
- `analysis_summary.md` directly in the output root.

Jupyter and IPython are optional notebook-only runtime dependencies; neither is required by `run_analysis.py` or the test suite.

## Expected behavior

A successful base run reports solver status `ok`, termination `optimal`, objective 285,488.90 scenario USD/year, selected facilities `FAC_NW`, `FAC_NE`, and `FAC_SE`, and relative MIP gap 0.0. Fixed and transport costs reconcile to 214,000.00 and 71,488.90 respectively.

If `appsi_highs` is unavailable, the workflow stops before reading solution values and provides an installation-oriented error. Infeasible, unbounded, or otherwise nonoptimal termination also produces an explicit error instead of emitting a result as valid.

Platform-level elapsed solver time may differ between runs. Decision values, objective values, and the validated analytical artifacts should remain reproducible.
