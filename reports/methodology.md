# Methodology

## Case scope

The clean-room case models one annual decision horizon in which candidate distribution centers serve customer zones. It is a capacitated facility-location mixed-integer linear program: binary variables select infrastructure and continuous variables allocate flows. A single-echelon formulation was chosen because it creates a real strategic design decision without unsupported product, inventory, or time complexity.

## Clean-room data strategy

The project uses six manually defined synthetic candidate facilities and twelve manually defined synthetic customer zones. All strategic inputs are labeled `SCENARIO_ASSUMPTION`. Coordinates are schematic synthetic distance units. The complete 72-arc cost matrix is deterministically derived from Euclidean distance at 3.20 scenario USD/(unit·SDU), then rounded once to two decimals.

No random generation is used, so a random seed is not applicable. The checked-in workflow contains no random generation, parameter search, or tuning loop; without pre-build version history, the timing of input choices relative to the first diagnostic solve is not independently reconstructable. Historical notebook and workbook coefficients were not reused.

## Mathematical model

For facilities \(i \in F\) and customers \(j \in C\), the model uses binary open variables \(y_i\) and nonnegative annual shipment variables \(x_{ij}\). It minimizes:

\[
\sum_i f_i y_i + \sum_i\sum_j c_{ij}x_{ij}.
\]

Every customer has an exact balance \(\sum_i x_{ij}=d_j\). Each facility has the tight activation and capacity constraint \(\sum_jx_{ij}\le K_i y_i\). There is no redundant Big-M row, facility-count restriction, or arbitrary service rule.

The full formulation and domains are in `docs/mathematical_formulation.md`; units are in `docs/unit_conventions.md`.

## Data and feasibility validation

Before model construction, the loader verifies required columns, unique and nonblank IDs, finite numeric fields, nonnegative demands/capacities/costs, known endpoints, exactly one row for every facility-customer arc, and deterministic agreement with the documented distance-cost formula. A pre-solve gate checks that total potential capacity covers total demand. The controlled infeasible case demonstrates this gate at 2.25× demand.

## Solver

Pyomo 6.10.1 builds a `ConcreteModel`. The primary solver interface is `appsi_highs`, using open-source HiGHS 1.15.1. The workflow refuses to read decisions unless the solver reports an acceptable status and `termination_condition == optimal`; explicit errors cover unavailable, infeasible, unbounded, and other nonoptimal outcomes.

## Independent validation

Post-solve checks are calculated directly from input tables and raw decision values rather than trusting displayed Pyomo rows. They verify:

- exact demand delivery for every customer;
- every facility’s assigned flow against capacity × open value;
- zero flow from closed facilities;
- shipment nonnegativity;
- binary-domain proximity;
- fixed and transport cost recomputation;
- fixed + transport = independently recomputed objective;
- independently recomputed objective = solver objective within documented tolerances.

Because there are only six binary facility variables, the workflow also enumerates all \(2^6=64\) open/closed subsets. Every capacity-feasible subset uses an independently assembled SciPy/HiGHS continuous transportation LP. Forty-one subsets are capacity-feasible, and the best enumerated facility set and objective exactly equal the Pyomo MILP result. This provides a separate formulation path for the small strategic search space; it is not presented as scalable for large networks. Module 7.5C additionally reproduced the results through a solver-engine-free minimum-cost-flow validation path.

## Baseline

`ALL_FACILITIES_OPEN` fixes the strategic decision conceptually to all six facilities open, then finds the least-cost shipment allocation for that network with an independent transportation LP. It is a deliberately defined reference scenario—not an existing company network, current state, or industry baseline. Comparisons use “scenario cost reduction relative to the defined baseline,” never a claim of realized business savings.

## Sensitivity design

Eight declared cases are evaluated: demand at 0.80×, 1.00×, and 1.20×; transport cost at 0.75× and 1.25×; fixed cost at 0.75× and 1.25×; and capacity at 0.90×. Each case reruns input validation, model construction, solver-status checking, and solution validation. The set is intentionally compact and decision-relevant.

## Reproducibility

`run_analysis.py` executes the entire workflow without notebook state. Exact package versions are in `requirements.txt`; installation, test, solver, and output details are in `docs/reproducibility.md`. Results, validation evidence, tables, and four figures are generated under the ignored local `.private_outputs/module_7_25C` directory by default.
