# Validation summary

## Outcome

Module 7.5C concluded `VALIDATED_WITH_MINOR_FIXES`. All identified minor issues were resolved during validation. There were zero critical issues, zero major issues, and no remaining technical blockers.

| Validation area | Result |
|---|---|
| Formulation | 10/10 |
| Units | 10/10 |
| Solver validity | 10/10 |
| Feasibility | 10/10 |
| Objective verification | 10/10 |
| Enumeration | 10/10 |
| Reproducibility | 10/10 |
| Clean-room provenance | PASS |
| Automated tests | 30/30 PASS |

## Reproduced base result

- Pyomo 6.10.1 with `appsi_highs` / HiGHS 1.15.1.
- Solver status `ok`; termination `optimal`; relative MIP gap 0.0.
- Objective: 285,488.90 scenario USD/year.
- Selected facilities: `FAC_NW`, `FAC_NE`, and `FAC_SE`.
- Fixed cost: 214,000.00 scenario USD/year.
- Transport cost: 71,488.90 scenario USD/year.
- Selected-network utilization: 96.9697%.

## Independent checks

The internal Module 7.5C reproduction audit separately confirmed exact demand balance, capacity and closed-facility logic, variable domains, fixed and transport cost arithmetic, objective value, shipment plan, facility utilization, baseline comparison, and all declared sensitivity outcomes.

All \(2^6=64\) facility subsets were considered; 41 were capacity-feasible. The independent enumeration formulation found the same selected network and objective as the Pyomo MILP. A separate solver-engine-free minimum-cost-flow validation path also reproduced the base, baseline, enumeration, and sensitivity results.

The tiny two-facility, two-customer known case has a manually derived optimum of 280. Pyomo and enumeration both reproduced 280.

## Reproducibility note

The canonical command, automated test suite, both notebooks, and all four figures were reproduced. Two generated JSON artifacts differed byte-for-byte only because they record solver elapsed time; the model decisions, costs, validation values, and analytical outputs were unchanged.

The controlled infeasible scenario was rejected safely by the pre-solve capacity check. No technical blocker remains for repository professionalization, subject to the separate Module 8 publication and licensing audit.
